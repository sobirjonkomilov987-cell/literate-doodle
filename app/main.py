import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.config import settings
from app.database import engine, Base, SessionLocal, migrate_database
from app.models import User, UserRole, Event, Sector, Seat, SeatStatus, ActivityLog, AdminNotification
from app.auth import get_password_hash
from app.services.reservation import release_expired_reservations
from app.routers import auth, admin, events, reservations, payments, tickets, reports

def seed_initial_data():
    """Boshlang'ich Admin va namunaviy ma'lumotlarni bazaga kiritish"""
    db = SessionLocal()
    try:
        # 1. Bosh Adminni tekshirish va yaratish / yangilash (Parol: sobirjon123)
        admin_user = db.query(User).filter(User.username == settings.ADMIN_DEFAULT_USERNAME).first()
        if not admin_user:
            admin_user = User(
                name="Sobirjon Bosh Administrator",
                username=settings.ADMIN_DEFAULT_USERNAME,
                email="admin@tadbirchipta.uz",
                phone="+998 90 123 45 67",
                password_hash=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                role=UserRole.ADMIN.value,
                avatar="https://api.dicebear.com/7.x/bottts/svg?seed=admin",
                organization_name="Bosh Ma'muriyat (System Admin)"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[INIT] Bosh admin yaratildi: {settings.ADMIN_DEFAULT_USERNAME} / {settings.ADMIN_DEFAULT_PASSWORD}")
        else:
            # Mavjud admin profilini boyitish
            if not admin_user.name:
                admin_user.name = "Sobirjon Bosh Administrator"
            if not admin_user.email:
                admin_user.email = "admin@tadbirchipta.uz"
            if not admin_user.phone:
                admin_user.phone = "+998 90 123 45 67"
            if not admin_user.avatar:
                admin_user.avatar = "https://api.dicebear.com/7.x/bottts/svg?seed=admin"
            db.commit()

        # Boshlang'ich bildirishnomalar va faoliyatlar
        if db.query(AdminNotification).count() == 0:
            db.add_all([
                AdminNotification(
                    title="Tizimga Xush Kelibsiz!",
                    message="Professional Admin Authentication va Boshqaruv tizimi muvaffaqiyatli ishga tushirildi.",
                    type="success"
                ),
                AdminNotification(
                    title="Xavfsizlik Himoyasi Faol",
                    message="Barcha admin yo'nalishlari JWT token va rol tekshiruvi bilan himoyalangan.",
                    type="info"
                )
            ])
            db.commit()

        if db.query(ActivityLog).count() == 0:
            db.add(ActivityLog(
                user_id=admin_user.id,
                username=admin_user.username,
                action="Tizim Ishga Tushirildi",
                details="Admin Boshqaruv Markazi va xavfsizlik audit logi faollashtirildi."
            ))
            db.commit()

        # 2. Demo Tashkilotchi (Organizer)
        demo_org = db.query(User).filter(User.username == "art_palace").first()
        if not demo_org:
            demo_org = User(
                username="art_palace",
                password_hash=get_password_hash("organizer123"),
                role=UserRole.ORGANIZER.value,
                organization_name="Xalqlar Do'stligi San'at Saroyi"
            )
            db.add(demo_org)
            db.commit()
            db.refresh(demo_org)

        # 3. Demo Tekshiruvchi (Controller)
        demo_ctrl = db.query(User).filter(User.username == "gate_controller").first()
        if not demo_ctrl:
            demo_ctrl = User(
                username="gate_controller",
                password_hash=get_password_hash("controller123"),
                role=UserRole.CONTROLLER.value,
                organization_name="1-Kirish Darvozasi Nazorati"
            )
            db.add(demo_ctrl)
            db.commit()
            db.refresh(demo_ctrl)

        # 4. Demo Mijoz (Customer)
        demo_cust = db.query(User).filter(User.username == "mijoz1").first()
        if not demo_cust:
            demo_cust = User(
                username="mijoz1",
                password_hash=get_password_hash("mijoz123"),
                role=UserRole.CUSTOMER.value,
                organization_name=None
            )
            db.add(demo_cust)
            db.commit()
            db.refresh(demo_cust)

        # 5. Namunaviy tadbir va joylarni yaratish
        existing_event = db.query(Event).first()
        if not existing_event and demo_org:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            ev1 = Event(
                title="Yulduzlar Yog'dusi - Jonli Konsert 2026",
                description="O'zbekistonning eng sara san'atkorlari ishtirokidagi unutilmas katta jonli konsert dasturi.",
                date=now + timedelta(days=10, hours=4),
                location="Toshkent, 'Xalqlar Do'stligi' san'at saroyi",
                organizer_id=demo_org.id
            )
            db.add(ev1)
            db.commit()
            db.refresh(ev1)

            # Sektorlar
            vip_sec = Sector(event_id=ev1.id, name="VIP Parter", price=350000.0)
            std_sec = Sector(event_id=ev1.id, name="Standart Qatorlar", price=180000.0)
            balc_sec = Sector(event_id=ev1.id, name="Balkon", price=90000.0)
            db.add_all([vip_sec, std_sec, balc_sec])
            db.commit()
            db.refresh(vip_sec)
            db.refresh(std_sec)
            db.refresh(balc_sec)

            # Joylar (VIP: 12 ta joy, Standart: 18 ta joy, Balkon: 12 ta joy)
            seats = []
            for i in range(1, 13):
                seats.append(Seat(sector_id=vip_sec.id, seat_number=f"VIP-{i}", status=SeatStatus.AVAILABLE.value))
            for i in range(1, 19):
                seats.append(Seat(sector_id=std_sec.id, seat_number=f"S-{i}", status=SeatStatus.AVAILABLE.value))
            for i in range(1, 13):
                seats.append(Seat(sector_id=balc_sec.id, seat_number=f"B-{i}", status=SeatStatus.AVAILABLE.value))

            db.add_all(seats)
            db.commit()
            print("[INIT] Namunaviy tadbir, sektorlar va joylar muvaffaqiyatli shakllantirildi.")

    except Exception as e:
        print(f"[INIT XATO]: {e}")
        db.rollback()
    finally:
        db.close()

async def background_reservation_cleaner():
    """Har 30 soniyada 10 daqiqalik muddati o'tgan rezervatsiyalarni avtomatik tozalovchi vazifa"""
    while True:
        try:
            await asyncio.sleep(30)
            db = SessionLocal()
            try:
                freed = release_expired_reservations(db)
                if freed > 0:
                    print(f"[CLEANER] {freed} ta muddati tugagan rezervatsiya bekor qilindi va joylar bo'shatildi.")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[CLEANER XATO]: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dastur ishga tushganda:
    migrate_database()
    seed_initial_data()
    cleaner_task = asyncio.create_task(background_reservation_cleaner())
    yield
    # Dastur to'xtaganda:
    cleaner_task.cancel()
    try:
        await cleaner_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Tadbir chiptalari API - Rollar, 10 daqiqalik qulflangan rezervatsiya, Idempotent to'lov va Nazorat tizimi",
    lifespan=lifespan
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routerlarini ulash
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(events.router)
app.include_router(reservations.router)
app.include_router(payments.router)
app.include_router(tickets.router)
app.include_router(reports.router)

# Static fayllar (Vebsayt frontend)
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    """Asosiy vebsayt sahifasini ochish"""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Tadbir chiptalari API ishga tushdi. OpenAPI hujjatlari: /docs"}

@app.get("/admin")
@app.get("/admin/login")
@app.get("/admin/register")
@app.get("/admin/dashboard")
@app.get("/admin/profile")
def read_admin_portal():
    """Admin boshqaruv portali sahifalarini ochish"""
    admin_file = os.path.join(static_dir, "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    return FileResponse(os.path.join(static_dir, "index.html"))
