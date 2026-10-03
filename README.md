# 🎟️ Tadbir Chiptalari API & Vebsayt Tizimi (Event Ticket System)

Ushbu loyiha **Python FastAPI** va **PostgreSQL** (yoki SQLite) yordamida yaratilgan bo'lib, tadbirlar uchun chiptalarni onlayn sotish, 10 daqiqalik xavfsiz joy rezervatsiyasi (concurrency / race condition himoyasi), idempotent to'lovlar, QR kodli chiptalar va kirish nazorati (Controller) tizimini o'z ichiga oladi.

Loyiha nafaqat kuchli **REST API** backend qismiga, balki zamonaviy va chiroyli **Interaktiv Vebsayt (Frontend)** qismiga ham ega!

---

## 🌟 Asosiy Imkoniyatlar va Biznes Qoidalari

### 1. Rollar va Avtorizatsiya (RBAC)
- 👑 **ADMIN (Bosh Administrator)**:
  - Tizim boshqaruvchisi.
  - Standart Login: `admin` | Parol: `sobirjon123`.
  - Yangi tashkilotlarni (Organizers) ro'yxatga oladi va ularga login/parol taqdim etadi.
  - Yangi tekshiruvchilarni (Controllers) yaratadi.
- 🏢 **Tashkilot (Organizer)**:
  - O'z-o'zidan ro'yxatdan o'ta olmaydi (faqat Admin yaratadi).
  - O'z tadbirlarini e'lon qiladi, narx sektorlarini va joylarni (yakka yoki ommaviy avto-generatsiya: masalan, 5 qator x 10 joy) boshqaradi.
  - Tahliliy hisobotlarni (tushum, bandlik foizi, kirish nazorati) ko'radi.
- 🎟️ **Mijoz (Customer)**:
  - Mustaqil ro'yxatdan o'tadi va tizimga kiradi.
  - Tadbirlarni ko'radi, interaktiv 2D xaritadan joy tanlaydi.
  - Joyni 10 daqiqaga qulflab band qiladi.
  - Soxta to'lov simulyatsiyasi orqali xarid qiladi va unikal QR kodli elektron chiptaga ega bo'ladi.
  - Faqat o'z chiptalarini ko'ra oladi.
- 🔍 **Tekshiruvchi (Controller)**:
  - Kirish darvozalarida chipta tokenlarini (UUID/QR) tekshiruvchi xodim.
  - Tokenni tekshiradi va tasdiqlaydi.

---

### 2. Kritik Biznes Talablari (Qat'iy Ta'minlangan)

1. ⏱️ **Joyni 10 daqiqaga rezerv qilish va Race Condition himoyasi**:
   - Mijoz joy tanlaganda, tizim joyni atomik tarzda `reserved` holatiga o'tkazadi va 10 daqiqalik vaqt hisobini boshlaydi (`expires_at = now + 10 min`).
   - Concurrency (parallel xaridlar) oldini olish uchun bazada qator darajasida blokirovka (`with_for_update` / atomic locking) qo'llaniladi. Bir vaqtda ikkita foydalanuvchi bitta joyni ololmaydi (`409 Conflict`).
   - Vaqt tugasa, joy avtomatik ravishda boshqa foydalanuvchilar uchun `available` holatiga qaytariladi (fon vazifasi + real vaqt tekshiruvi).

2. 💳 **Soxta To'lov va Idempotency**:
   - To'lov callback endpointi: `POST /api/payments/callback`.
   - Bir xil `idempotency_key` bilan bir necha bor so'rov yuborilsa ham, to'lov takroran olinmaydi va yangi chipta yaratilmaydi.
   - Tizim avvalgi yaratilgan chiptani qaytaradi (`is_duplicate_call: true`).

3. 🎫 **Chiptani tekshirish (Bir martalik kafolat)**:
   - Endpoint: `POST /api/tickets/verify`.
   - Controller chipta tokenini tekshirganda, u faqat **bir marta** tasdiqlanadi va `used` holatiga o'tkaziladi.
   - Ikkinchi marta tekshirilganda, tizim qat'iy ogohlantirish beradi: `"DIQQAT: Ushbu chipta allaqachon ishlatilgan! Ishlatilgan vaqt: ..."`
   - Bekor qilingan (`cancelled`) chiptalar ham rad etiladi.

4. 📊 **Hisobotlar va Sektor Bo'yicha Filtr**:
   - Endpoint: `GET /api/reports/events/{event_id}?sector_id=...`.
   - Umumiy tushum, bandlik foizi (`occupancy_rate`), sotilgan joylar va kirish foizi (`check_in_rate`).
   - Sektor bo'yicha saralash va har bir sektorning alohida statistikasi.

---

## 💻 Loyiha Tuzilmasi

```text
loyiha  1/
├── app/
│   ├── config.py             # Sozlamalar va muhit o'zgaruvchilari (Pydantic Settings)
│   ├── database.py           # SQLAlchemy dvigateli, sessiya va dastlabki admin seeder
│   ├── models.py             # User, Event, Sector, Seat, Reservation, Ticket, Payment modellar
│   ├── schemas.py            # Pydantic so'rov va javob modellari (V2)
│   ├── auth.py               # Parollarni xeshlash (bcrypt), JWT yaratish va Rollar himoyasi
│   ├── services/
│   │   ├── reservation.py    # 10 daqiqalik qulflangan rezervatsiya & avto-tozalash
│   │   ├── payment.py        # Idempotent to'lov va chipta generatsiyasi
│   │   └── ticket.py         # Chipta tokenini bir martalik tekshirish logikasi
│   ├── routers/
│   │   ├── auth.py           # Login, Register, Me
│   │   ├── admin.py          # Tashkilotchilar va Tekshiruvchilarni yaratish
│   │   ├── events.py         # Tadbirlar, sektorlar, joylar CRUD
│   │   ├── reservations.py   # 10 daqiqalik rezervatsiya qilish va bekor qilish
│   │   ├── payments.py       # Idempotent to'lov callback
│   │   ├── tickets.py        # Mening chiptalarim va Tekshirish (verify)
│   │   └── reports.py        # Tahliliy hisobotlar va sektor filtri
│   └── main.py               # FastAPI ilovasi, fon tozalovchi vazifasi va statik fayllar
├── static/
│   ├── index.html            # Interaktiv zamonaviy Vebsayt (SPA)
│   ├── app.js                # Frontend mantiqi, QR kodlar, 2D joylar xaritasi, taymer
│   └── style.css             # Glassmorphism, chipta kesimlari va animatsiyalar
├── tests/
│   └── test_api.py           # Barcha biznes talablar uchun avtomatlashtirilgan testlar (100% PASS)
├── .env                      # Muhit sozlamalari
├── requirements.txt          # Kerakli kutubxonalar
├── run.py                    # Dasturni bir buyruq bilan ishga tushirish skripti
└── README.md                 # Loyiha hujjatlari
```

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Kutubxonalarni o'rnatish:
```bash
pip install -r requirements.txt
```

### 2. Ma'lumotlar bazasini sozlash (`.env` fayli):
Loyiha sukut bo'yicha tezkor ishga tushish uchun SQLite (`sqlite:///./ticket_system.db`) bilan ishlaydi. 
Agar **PostgreSQL** ulamoqchi bo'lsangiz, `.env` faylida quyidagicha yozing:
```env
DATABASE_URL=postgresql://postgres:parol@localhost:5432/ticket_db
```

### 3. Veb-sayt va API-ni ishga tushirish:
```bash
python run.py
```
yoki to'g'ridan-to'g'ri uvicorn orqali:
```bash
uvicorn app.main:app --reload --port 8000
```

Brauzerda oching:
- 🌐 **Interaktiv Vebsayt**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📖 **Swagger / OpenAPI Hujjatlari**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 📄 **ReDoc Hujjatlari**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔑 Sinov Uchun Tayyor Akkountlar (Demo Hisoblar)

Veb-sayt interfeysida **"Tezkor Demo Login"** tugmalari mavjud. Siz qo'lda yozmasdan, bitta tugma bilan quyidagi rollarga kirishingiz mumkin:

| Rol | Login | Parol | Huquqi |
| :--- | :--- | :--- | :--- |
| **Bosh Admin** | `admin` | `sobirjon123` | Tashkilotchilar va Tekshiruvchilarni yaratish, butun tizim nazorati |
| **Tashkilotchi** | `art_palace` | `organizer123` | Tadbir, sektor va joylar yaratish, sotuv hisobotlarini ko'rish |
| **Tekshiruvchi** | `gate_controller` | `controller123` | Kirish darvozasida chipta QR/tokenlarini tekshirish |
| **Mijoz** | `mijoz1` | `mijoz123` | Joy tanlash, 10 daqiqaga band qilish, to'lash, QR chiptalarni ko'rish |

---

## 🧪 Avtomatlashtirilgan Testlarni Ishga Tushirish

Barcha talablar (admin login, tashkilotchi yaratish, tadbir/sektor/joy, 10 daqiqalik qulflangan rezervatsiya, race condition himoyasi, idempotent to'lov, chiptani bir martalik tekshirish, sektorli hisobotlar) to'liq test qilingan:

```bash
python -m pytest tests/test_api.py -v
```

Natija:
```text
tests/test_api.py::test_admin_login PASSED
tests/test_api.py::test_admin_creates_organizer_and_controller PASSED
tests/test_api.py::test_organizer_creates_event_sector_seats PASSED
tests/test_api.py::test_customer_registration_and_reservation PASSED
tests/test_api.py::test_idempotent_payment PASSED
tests/test_api.py::test_ticket_verification_controller PASSED
tests/test_api.py::test_reports_with_sector_filter PASSED

======================== 7 passed in 10.91s ========================
```
