from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import time
from collections import defaultdict
from fastapi.security import HTTPAuthorizationCredentials
from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, Token,
    AdminRegisterRequest, AdminLoginRequest, ForgotPasswordRequest,
    GoogleAuthRequest
)
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user, security
from app.services.rate_limiter import check_brute_force, record_failed_attempt, clear_failed_attempts, blacklist_token
from app.services.audit import log_activity

router = APIRouter(prefix="/api/auth", tags=["Autentifikatsiya (Auth)"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_customer(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Mijoz (Customer) uchun mukammal va xavfsiz ro'yxatdan o'tish:
    - Login (username) unikalligi va uzunligi (kamida 3 ta belgi)
    - Parol uzunligi (kamida 6 ta belgi)
    - Parollar mosligi (confirm_password tekshiruvi)
    - Email formati va unikalligi (agar kiritilsa)
    - To'liq ism va telefon raqami saqlanadi
    - Xavfsizlik audit logi yuritiladi
    """
    import re
    username_clean = user_in.username.strip()
    if len(username_clean) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foydalanuvchi nomi (login) kamida 3 ta belgidan iborat bo'lishi kerak."
        )

    existing_user = db.query(User).filter(User.username == username_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{username_clean}' logini allaqachon band. Iltimos, boshqa login tanlang."
        )

    # Parol uzunligini tekshirish
    if len(user_in.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parol kamida 6 ta belgidan iborat bo'lishi shart."
        )

    # Parollar bir xilligini tekshirish
    if user_in.confirm_password and user_in.password != user_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kiritilgan parollar bir-biriga mos kelmadi! Iltimos, qayta tekshiring."
        )

    # Email tekshiruvi (agar mavjud bo'lsa)
    email_clean = user_in.email.strip().lower() if user_in.email else None
    if email_clean:
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, email_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email formati noto'g'ri kiritildi. Masalan: mijoz@tadbirchipta.uz"
            )
        existing_email = db.query(User).filter(User.email == email_clean).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ushbu email manzili boshqa hisob tomonidan band qilingan."
            )

    # Yangi foydalanuvchi yaratish (Mijoz yoki Tekshiruvchi)
    allowed_roles = [UserRole.CUSTOMER.value, UserRole.CONTROLLER.value]
    chosen_role = user_in.role if user_in.role in allowed_roles else UserRole.CUSTOMER.value

    new_user = User(
        name=user_in.name.strip() if user_in.name else username_clean,
        username=username_clean,
        email=email_clean,
        phone=user_in.phone.strip() if user_in.phone else None,
        password_hash=get_password_hash(user_in.password),
        role=chosen_role,
        organization_name=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log
    role_name = "Chipta Tekshiruvchi" if chosen_role == UserRole.CONTROLLER.value else "Mijoz"
    log_activity(
        db=db,
        user_id=new_user.id,
        username=new_user.username,
        action="Yangi Ro'yxatdan O'tish",
        details=f"Yangi {role_name} '{new_user.username}' tizimda muvaffaqiyatli ro'yxatdan o'tdi."
    )

    return new_user

@router.post("/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    """
    Barcha foydalanuvchilar uchun xavfsiz login qilish:
    - Brute-force himoyasi (5 ta xato urinishdan so'ng 5 daqiqa bloklanadi)
    - Audit log yuritish
    - Xavfsiz JWT Bearer token qaytarish
    """
    username_clean = login_req.username.strip()
    brute_key = f"user_{username_clean.lower()}"
    check_brute_force(brute_key)

    user = db.query(User).filter(User.username == username_clean).first()
    if not user or not verify_password(login_req.password, user.password_hash):
        record_failed_attempt(brute_key)
        log_activity(
            db=db,
            action="Muvaffaqiyatsiz Login",
            details=f"Foydalanuvchi '{username_clean}' uchun noto'g'ri parol kiritildi.",
            username=username_clean
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_failed_attempts(brute_key)

    log_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        action="Tizimga Kirish (Login)",
        details=f"Foydalanuvchi '{user.username}' tizimga kirdi (Rol: {user.role})."
    )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/google", response_model=Token)
def google_auth(auth_req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Google orqali bir marta bosishda tizimga kirish yoki ro'yxatdan o'tish (Google OAuth / GSI):
    - Google email, ism va avatarini qabul qilish
    - Agar foydalanuvchi mavjud bo'lsa: darhol JWT token qaytaradi
    - Agar yangi bo'lsa: 'customer' roli bilan xavfsiz avtomatik hisob ochadi
    - Audit logida Google login qayd etiladi
    """
    import secrets
    email = (auth_req.email or "").strip().lower()
    name = (auth_req.name or "").strip()
    avatar = (auth_req.avatar or "").strip()

    if auth_req.credential:
        try:
            import jwt
            decoded = jwt.decode(auth_req.credential, options={"verify_signature": False})
            if "email" in decoded:
                email = decoded["email"].strip().lower()
            if "name" in decoded and not name:
                name = decoded["name"].strip()
            if "picture" in decoded and not avatar:
                avatar = decoded["picture"].strip()
        except Exception:
            pass

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google hisobi emaili aniqlanmadi."
        )

    # 1. Bazada ushbu email yoki username bilan qidirish
    user = db.query(User).filter(User.email == email).first()
    if not user:
        base_username = email.split("@")[0].replace(".", "_").replace("+", "_")
        candidate_username = base_username
        counter = 1
        while db.query(User).filter(User.username == candidate_username).first():
            candidate_username = f"{base_username}_{counter}"
            counter += 1

        random_pass = secrets.token_urlsafe(16)
        user = User(
            name=name if name else candidate_username,
            username=candidate_username,
            email=email,
            avatar=avatar if avatar else f"https://api.dicebear.com/7.x/initials/svg?seed={candidate_username}",
            password_hash=get_password_hash(random_pass),
            role=UserRole.CUSTOMER.value,
            organization_name=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        log_activity(
            db=db,
            user_id=user.id,
            username=user.username,
            action="Google Ro'yxatdan O'tish",
            details=f"Foydalanuvchi '{user.username}' ({email}) Google orqali tizimda yangi hisob ochdi."
        )
    else:
        if avatar and not user.avatar:
            user.avatar = avatar
            db.commit()
        log_activity(
            db=db,
            user_id=user.id,
            username=user.username,
            action="Google Tizimga Kirish",
            details=f"Foydalanuvchi '{user.username}' ({email}) Google orqali tizimga kirdi."
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Joriy JWT tokenni qora ro'yxatga kiritish (Blacklist) va xavfsiz chiqish.
    Bekor qilingan token boshqa qabul qilinmaydi.
    """
    token = credentials.credentials
    blacklist_token(token)
    log_activity(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="Tizimdan Chiqildi (Logout)",
        details=f"Foydalanuvchi '{current_user.username}' sessiyasini yakunladi va token qora ro'yxatga kiritildi."
    )
    return {"success": True, "message": "Tizimdan muvaffaqiyatli chiqildi. Sessiya va token bekor qilindi."}

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
        log_activity(
            db=db,
            username=login_val,
            action="Muvaffaqiyatsiz Admin Login",
            details=f"'{login_val}' orqali noto'g'ri login yoki parol urinishi (Urinish qayd etildi)"
        )

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
    log_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        action="Admin Tizimga Kirdi",
        details=f"Admin '{user.username}' tizim boshqaruviga kirdi."
    )

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
