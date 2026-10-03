from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_database():
    """Jadval ustunlari va yangi jadvallarni xavfsiz yangilash"""
    import app.models  # Modellar Base.metadata ga ro'yxatdan o'tishi uchun
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # 1. Yangi jadvallarni yaratish
    Base.metadata.create_all(bind=engine)
    
    # 2. Users jadvali ustunlarini tekshirish va qo'shish
    if "users" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("users")]
        with engine.begin() as conn:
            if "name" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(255)"))
            if "email" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
            if "phone" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
            if "avatar" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN avatar TEXT"))
            if "updated_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))
