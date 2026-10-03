from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Tadbir Chiptalari API"
    VERSION: str = "1.0.0"
    
    # Ma'lumotlar bazasi URL (PostgreSQL yoki SQLite)
    DATABASE_URL: str = "sqlite:///./ticket_system.db"
    
    # JWT Sozlamalari
    SECRET_KEY: str = "super_secret_jwt_key_sobirjon_ticket_api_2026_secure_key_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 soat
    
    # Bosh Admin Sozlamalari
    ADMIN_DEFAULT_USERNAME: str = "admin"
    ADMIN_DEFAULT_PASSWORD: str = "sobirjon123"
    
    # Rezervatsiya vaqti (daqiqalarda)
    RESERVATION_TIMEOUT_MINUTES: int = 10

settings = Settings()
