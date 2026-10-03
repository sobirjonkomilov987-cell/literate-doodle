import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app, seed_initial_data
from app.database import Base, get_db
from app.models import Seat, SeatStatus, Reservation, ReservationStatus, Ticket, TicketStatus
from app.services.reservation import get_current_utc_time

# Test uchun in-memory yoki alohida SQLite bazasi
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ticket_system.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Init seed
    from app.database import SessionLocal
    # Override SessionLocal in seed
    db = TestingSessionLocal()
    from app.models import User, UserRole
    from app.auth import get_password_hash
    admin = User(
        username="admin",
        password_hash=get_password_hash("sobirjon123"),
        role=UserRole.ADMIN.value,
        organization_name="System Admin"
    )
    db.add(admin)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_admin_login():
    """Admin 'sobirjon123' paroli bilan tizimga muvaffaqiyatli kirishi kerak"""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "sobirjon123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"

def test_admin_creates_organizer_and_controller():
    """Admin yangi tashkilotchi va tekshiruvchi yarata olishi kerak"""
    # 1. Admin login
    admin_token = client.post("/api/auth/login", json={"username": "admin", "password": "sobirjon123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Organizer yaratish
    resp_org = client.post("/api/admin/organizers", json={
        "username": "tashkilot1",
        "password": "org_password_1",
        "organization_name": "Yoshlar Markazi"
    }, headers=headers)
    assert resp_org.status_code == 201
    assert resp_org.json()["role"] == "organizer"

    # 3. Controller yaratish
    resp_ctrl = client.post("/api/admin/controllers", json={
        "username": "tekshiruvchi1",
        "password": "ctrl_password_1"
    }, headers=headers)
    assert resp_ctrl.status_code == 201
    assert resp_ctrl.json()["role"] == "controller"

def test_organizer_creates_event_sector_seats():
    """Tashkilotchi o'z tadbirini, sektorini va joylarini yarata olishi kerak"""
    # Organizer login
    org_token = client.post("/api/auth/login", json={"username": "tashkilot1", "password": "org_password_1"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {org_token}"}

    # Tadbir yaratish
    ev_resp = client.post("/api/events", json={
        "title": "IT Konferensiya 2026",
        "description": "Eng so'nggi texnologiyalar forumi",
        "date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "location": "IT Park Binosi"
    }, headers=headers)
    assert ev_resp.status_code == 201
    event_id = ev_resp.json()["id"]

    # Sektor qo'shish
    sec_resp = client.post(f"/api/events/{event_id}/sectors", json={
        "name": "VIP Sektor",
        "price": 200000.0
    }, headers=headers)
    assert sec_resp.status_code == 201
    sector_id = sec_resp.json()["id"]

    # Joylar yaratish (A-1, A-2, A-3)
    seats_resp = client.post(f"/api/events/sectors/{sector_id}/seats/batch", json={
        "prefix": "A",
        "rows": 1,
        "seats_per_row": 3
    }, headers=headers)
    assert seats_resp.status_code == 201
    assert len(seats_resp.json()) == 3

def test_customer_registration_and_reservation():
    """Mijoz ro'yxatdan o'tishi va joyni 10 daqiqaga rezerv qila olishi kerak"""
    # 1. Customer ro'yxatdan o'tishi
    cust_resp = client.post("/api/auth/register", json={
        "username": "ali_mijoz",
        "password": "alipassword123"
    })
    assert cust_resp.status_code == 201

    # 2. Login
    cust_token = client.post("/api/auth/login", json={"username": "ali_mijoz", "password": "alipassword123"}).json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    # 3. Joylarni olish
    events = client.get("/api/events").json()
    event_id = events[0]["id"]
    sector_id = events[0]["sectors"][0]["id"]
    seats = client.get(f"/api/events/sectors/{sector_id}/seats").json()
    target_seat = seats[0]
    assert target_seat["status"] == "available"

    # 4. Joyni 10 daqiqaga band qilish (Reservation)
    res_resp = client.post("/api/reservations", json={"seat_id": target_seat["id"]}, headers=cust_headers)
    assert res_resp.status_code == 201
    res_data = res_resp.json()
    assert res_data["status"] == "pending"
    assert res_data["seconds_left"] > 500 # taxminan 600 soniya (10 daqiqa)

    # 5. Konkurensiya testi: boshqa foydalanuvchi xuddi shu joyni ololmasligi kerak
    cust2_token = client.post("/api/auth/register", json={"username": "vali_mijoz", "password": "valipassword"}).json()
    cust2_token = client.post("/api/auth/login", json={"username": "vali_mijoz", "password": "valipassword"}).json()["access_token"]
    cust2_headers = {"Authorization": f"Bearer {cust2_token}"}

    conflict_resp = client.post("/api/reservations", json={"seat_id": target_seat["id"]}, headers=cust2_headers)
    assert conflict_resp.status_code == 409 # Conflict! Joy band!

def test_idempotent_payment():
    """To'lov callback'i idempotent bo'lishi va takroriy so'rovda yangi chipta yaratmasligi kerak"""
    # 1. Ali foydalanuvchisi va uning rezervatsiyasi
    cust_token = client.post("/api/auth/login", json={"username": "ali_mijoz", "password": "alipassword123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {cust_token}"}

    my_res = client.get("/api/reservations/my", headers=headers).json()
    assert len(my_res) > 0
    reservation_id = my_res[0]["id"]

    idempotency_key = f"pay_tx_{uuid.uuid4()}"
    payment_payload = {
        "reservation_id": reservation_id,
        "idempotency_key": idempotency_key,
        "amount": 200000.0
    }

    # Birinchi to'lov so'rovi
    resp1 = client.post("/api/payments/callback", json=payment_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_duplicate_call"] is False
    assert data1["ticket"]["status"] == "active"
    token_str = data1["ticket"]["token"]
    ticket_id = data1["ticket"]["id"]

    # Ikkinchi so'rov (Xuddi shu idempotency_key bilan takroriy kelganda)
    resp2 = client.post("/api/payments/callback", json=payment_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_duplicate_call"] is True
    assert data2["ticket"]["id"] == ticket_id
    assert data2["ticket"]["token"] == token_str

def test_ticket_verification_controller():
    """Controller chiptani faqat bir marta tekshira olishi, ikkinchi marta o'tmasligi kerak"""
    # 1. Controller login
    ctrl_token = client.post("/api/auth/login", json={"username": "tekshiruvchi1", "password": "ctrl_password_1"}).json()["access_token"]
    ctrl_headers = {"Authorization": f"Bearer {ctrl_token}"}

    # 2. Ali foydalanuvchisining chiptasi
    ali_token = client.post("/api/auth/login", json={"username": "ali_mijoz", "password": "alipassword123"}).json()["access_token"]
    ali_headers = {"Authorization": f"Bearer {ali_token}"}
    tickets = client.get("/api/tickets/my-tickets", headers=ali_headers).json()
    assert len(tickets) > 0
    ticket_token = tickets[0]["token"]

    # 3. Birinchi skaner / tekshirish (Muvaffaqiyatli)
    scan1 = client.post("/api/tickets/verify", json={"token": ticket_token}, headers=ctrl_headers)
    assert scan1.status_code == 200
    res1 = scan1.json()
    assert res1["valid"] is True
    assert res1["status"] == "success"

    # 4. Ikkinchi skaner / tekshirish (RAD ETILISHI SHART - Allaqachon ishlatilgan)
    scan2 = client.post("/api/tickets/verify", json={"token": ticket_token}, headers=ctrl_headers)
    assert scan2.status_code == 200
    res2 = scan2.json()
    assert res2["valid"] is False
    assert res2["status"] == "used"
    assert "allaqachon ishlatilgan" in res2["message"].lower()

def test_reports_with_sector_filter():
    """Tadbir hisoboti va sektor bo'yicha filtr to'g'ri ishlashi kerak"""
    org_token = client.post("/api/auth/login", json={"username": "tashkilot1", "password": "org_password_1"}).json()["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    events = client.get("/api/events").json()
    event_id = events[0]["id"]
    sector_id = events[0]["sectors"][0]["id"]

    # Umumiy tadbir hisoboti
    rep_all = client.get(f"/api/reports/events/{event_id}", headers=org_headers)
    assert rep_all.status_code == 200
    data_all = rep_all.json()
    assert data_all["total_seats"] == 3
    assert data_all["sold_seats"] == 1
    assert data_all["total_checked_in"] == 1
    assert data_all["total_revenue"] == 200000.0

    # Sektor bo'yicha filtr
    rep_sec = client.get(f"/api/reports/events/{event_id}?sector_id={sector_id}", headers=org_headers)
    assert rep_sec.status_code == 200
    data_sec = rep_sec.json()
    assert len(data_sec["sectors"]) == 1
    assert data_sec["sectors"][0]["sector_id"] == sector_id
    assert data_sec["sectors"][0]["sold_seats"] == 1
    assert data_sec["sectors"][0]["checked_in_count"] == 1

def test_admin_authentication_and_security():
    """Admin Ro'yxatdan o'tish, Login, Xavfsizlik, Profil va Dashboard testlari"""
    # 1. Parol uzunligi kamida 8 ta bo'lishi kerak (kamida 8 ta belgi qoidasi)
    short_pass = client.post("/api/auth/admin/register", json={
        "name": "Test Admin",
        "username": "short_admin",
        "email": "short@admin.uz",
        "phone": "+998901112233",
        "password": "short",
        "confirm_password": "short"
    })
    assert short_pass.status_code in [400, 422]

    # 2. Parollar mos kelishi shart
    mismatch_pass = client.post("/api/auth/admin/register", json={
        "name": "Test Admin",
        "username": "mismatch_admin",
        "email": "mismatch@admin.uz",
        "phone": "+998901112233",
        "password": "validpassword123",
        "confirm_password": "differentpassword"
    })
    assert mismatch_pass.status_code == 400
    assert "mos kelmadi" in mismatch_pass.json()["detail"]

    # 3. Email formati to'g'ri bo'lishi kerak
    bad_email = client.post("/api/auth/admin/register", json={
        "name": "Test Admin",
        "username": "bad_email_admin",
        "email": "notanemail",
        "phone": "+998901112233",
        "password": "validpassword123",
        "confirm_password": "validpassword123"
    })
    assert bad_email.status_code == 400
    assert "Email formati" in bad_email.json()["detail"]

    # 4. Muvaffaqiyatli Admin Ro'yxatdan O'tish
    valid_reg = client.post("/api/auth/admin/register", json={
        "name": "Yangi Administrator",
        "username": "new_super_admin",
        "email": "newadmin@tadbir.uz",
        "phone": "+998901234567",
        "password": "secureadminpass123",
        "confirm_password": "secureadminpass123"
    })
    assert valid_reg.status_code == 201
    reg_data = valid_reg.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["role"] == "admin"
    assert reg_data["user"]["name"] == "Yangi Administrator"

    # 5. Email orqali Admin Login
    login_by_email = client.post("/api/auth/admin/login", json={
        "login": "newadmin@tadbir.uz",
        "password": "secureadminpass123"
    })
    assert login_by_email.status_code == 200
    admin_token = login_by_email.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 6. Oddiy user Admin Login qila olmasligi kerak (403 Forbidden)
    user_login = client.post("/api/auth/admin/login", json={
        "login": "ali_mijoz",
        "password": "alipassword123"
    })
    assert user_login.status_code == 403
    assert "Kirish taqiqlangan" in user_login.json()["detail"]

    # 7. Admin Dashboard statistikasi
    dash_stats = client.get("/api/admin/dashboard/stats", headers=admin_headers)
    assert dash_stats.status_code == 200
    s_data = dash_stats.json()
    assert "total_users" in s_data
    assert "total_orders" in s_data
    assert "total_products" in s_data
    assert "total_revenue" in s_data
    assert "chart_data" in s_data
    assert "notifications" in s_data

    # 8. Admin Profilini tahrirlash (PUT /api/admin/profile)
    update_prof = client.put("/api/admin/profile", json={
        "name": "Boshliq Sobirjon",
        "phone": "+998998887766"
    }, headers=admin_headers)
    assert update_prof.status_code == 200
    assert update_prof.json()["name"] == "Boshliq Sobirjon"
    assert update_prof.json()["phone"] == "+998998887766"

    # 9. Admin Parolini o'zgartirish (PUT /api/admin/profile/change-password)
    change_pass = client.put("/api/admin/profile/change-password", json={
        "current_password": "secureadminpass123",
        "new_password": "brandnewpassword999",
        "confirm_new_password": "brandnewpassword999"
    }, headers=admin_headers)
    assert change_pass.status_code == 200
    assert change_pass.json()["success"] is True

    # 10. Yangi parol bilan kirish
    new_login = client.post("/api/auth/admin/login", json={
        "login": "new_super_admin",
        "password": "brandnewpassword999"
    })
    assert new_login.status_code == 200
