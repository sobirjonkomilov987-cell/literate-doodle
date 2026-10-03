from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import time
from collections import defaultdict
from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, Token,
    AdminRegisterRequest, AdminLoginRequest, ForgotPasswordRequest
)
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

# Brute-force hujumlaridan himoya tizimi (Rate Limiting & Lockout)
LOGIN_ATTEMPTS = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300 # 5 daqiqa bloklash

def check_brute_force(key: str):
    """5 marta xato urinishdan so'ng 5 daqiqaga bloklash"""
    now = time.time()
    LOGIN_ATTEMPTS[key] = [t for t in LOGIN_ATTEMPTS[key] if now - t < LOCKOUT_DURATION]
    if len(LOGIN_ATTEMPTS[key]) >= MAX_LOGIN_ATTEMPTS:
        remaining = int(LOCKOUT_DURATION - (now - LOGIN_ATTEMPTS[key][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Xavfsizlik: Ko'p marotaba noto'g'ri urinish amalga oshirildi (Brute-force himoyasi). Hisobingiz {remaining} soniyaga bloklandi."
        )

def record_failed_attempt(key: str):
    LOGIN_ATTEMPTS[key].append(time.time())

def clear_failed_attempts(key: str):
    LOGIN_ATTEMPTS.pop(key, None)

router = APIRouter(prefix="/api/auth", tags=["Autentifikatsiya (Auth)"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_customer(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Mijoz (Customer) uchun ro'yxatdan o'tish.
    Xavfsizlik qoidasi: Tashkilotchi (Organizer) va Admin o'z-o'zidan ro'yxatdan o'ta olmaydi.
    Ushbu endpoint orqali faqat 'customer' roli beriladi.
    """
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu login (username) band. Boshqa login tanlang."
        )

    # Tashkilotchi yoki boshqa maxsus rollarni o'zboshimchalik bilan ololmaydi
    new_user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        role=UserRole.CUSTOMER.value,
        organization_name=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    """
    Barcha foydalanuvchilar (Admin, Organizer, Customer, Controller) uchun login qilish.
    Muvaffaqiyatli bo'lsa JWT token qaytaradi.
    """
    user = db.query(User).filter(User.username == login_req.username).first()
    if not user or not verify_password(login_req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Joriy tizimga kirgan foydalanuvchi ma'lumotlarini olish"""
    return current_user

# ================= ADMIN AUTHENTICATION =================

@router.post("/admin/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_admin(admin_in: AdminRegisterRequest, db: Session = Depends(get_db)):
    """
    Admin uchun maxsus ro'yxatdan o'tish endpointi.
    Barcha maydonlar qat'iy tekshiriladi:
    - Email formati
    - Parol uzunligi (kamida 8 ta)
    - Parollar mosligi
    - Username va Email unikalligi
    """
    import re
    # 1. Email formatini tekshirish
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, admin_in.email.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email formati noto'g'ri. Masalan: admin@example.com"
        )

    # 2. Parol uzunligini tekshirish
    if len(admin_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parol kamida 8 ta belgidan iborat bo'lishi shart."
        )

    # 3. Parollarning bir xilligini tekshirish
    if admin_in.password != admin_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kiritilgan parollar bir-biriga mos kelmadi."
        )

    # 4. Username unikalligini tekshirish
    existing_username = db.query(User).filter(User.username == admin_in.username.strip()).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{admin_in.username}' logini allaqachon band. Boshqa username tanlang."
        )

    # 5. Email unikalligini tekshirish
    existing_email = db.query(User).filter(User.email == admin_in.email.strip()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{admin_in.email}' elektron pochtasi allaqachon ro'yxatdan o'tgan."
        )

    # 6. Admin yaratish
    avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={admin_in.username.strip()}"
    new_admin = User(
        name=admin_in.name.strip(),
        username=admin_in.username.strip(),
        email=admin_in.email.strip().lower(),
        phone=admin_in.phone.strip(),
        password_hash=get_password_hash(admin_in.password),
        role=UserRole.ADMIN.value,
        avatar=avatar_url,
        organization_name="Boshqaruv Ma'muriyati"
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    # Audit log va bildirishnoma qo'shish
    try:
        from app.models import ActivityLog, AdminNotification
        log_entry = ActivityLog(
            user_id=new_admin.id,
            username=new_admin.username,
            action="Admin Ro'yxatdan O'tish",
            details=f"Yangi administrator ro'yxatdan o'tdi: {new_admin.name} ({new_admin.email})"
        )
        notif = AdminNotification(
            title="Yangi Admin Ro'yxatdan O'tdi",
            message=f"'{new_admin.name}' ({new_admin.username}) tizimga muvaffaqiyatli qo'shildi.",
            type="success"
        )
        db.add_all([log_entry, notif])
        db.commit()
    except Exception:
        db.rollback()

    # JWT token yaratish
    access_token = create_access_token(
        data={"sub": new_admin.username, "role": new_admin.role, "id": new_admin.id}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_admin)
    )

@router.post("/admin/login", response_model=Token)
def admin_login(login_in: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Alohida /admin/login endpointi:
    - Email yoki username orqali kirish (sobirjon@admin)
    - Parolni tekshirish (sobirjon@)
    - Faqat 'admin' roliga ruxsat beriladi
    - Brute-force himoyasi: 5 marta xatodan so'ng 5 daqiqa bloklanadi
    - Xavfsizlik audit logi yuritiladi
    """
    login_val = login_in.login.strip()
    key = f"admin_{login_val.lower()}"
    
    # 1. Brute-force hujumini tekshirish
    check_brute_force(key)

    user = db.query(User).filter(
        (User.username == login_val) | (User.email == login_val.lower())
    ).first()

    from app.models import ActivityLog
    if not user or not verify_password(login_in.password, user.password_hash):
        record_failed_attempt(key)
        try:
            fail_log = ActivityLog(
                username=login_val,
                action="Muvaffaqiyatsiz Admin Login",
                details=f"'{login_val}' orqali noto'g'ri login yoki parol urinishi (Urinish qayd etildi)"
            )
            db.add(fail_log)
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login/Email yoki parol noto'g'ri. Iltimos qayta tekshiring.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ROL TEKSHIRUVI: Faqat 'admin' roliga ruxsat!
    if user.role != UserRole.ADMIN.value:
        record_failed_attempt(key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kirish taqiqlangan! Faqat administratorlar ushbu bo'limga kira oladi."
        )

    # Muvaffaqiyatli kirish - xatoliklar hisoblagichini tozalash
    clear_failed_attempts(key)


    # Muvaffaqiyatli login jurnali
    try:
        success_log = ActivityLog(
            user_id=user.id,
            username=user.username,
            action="Admin Tizimga Kirdi",
            details=f"Admin '{user.username}' tizim boshqaruviga kirdi."
        )
        db.add(success_log)
        db.commit()
    except Exception:
        db.rollback()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/admin/forgot-password")
def admin_forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Admin uchun parolni tiklash"""
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak."
        )

    login_val = req.login.strip()
    user = db.query(User).filter(
        (User.username == login_val) | (User.email == login_val.lower())
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kiritilgan login yoki email bo'yicha admin hisobi topilmadi."
        )

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat administrator hisoblari uchun parolni tiklash mumkin."
        )

    user.password_hash = get_password_hash(req.new_password)
    db.commit()

    try:
        from app.models import ActivityLog
        db.add(ActivityLog(
            user_id=user.id,
            username=user.username,
            action="Parol Tiklandi",
            details="Admin paroli 'Parolni unutdingizmi?' orqali yangilandi."
        ))
        db.commit()
    except Exception:
        db.rollback()

    return {"success": True, "message": "Parolingiz muvaffaqiyatli yangilandi! Yangi parol bilan kirishingiz mumkin."}
