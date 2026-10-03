from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import ActivityLog

def log_activity(
    db: Session,
    action: str,
    details: str,
    user_id: int = None,
    username: str = "Tizim",
    ip_address: str = None
) -> ActivityLog:
    """
    Xavfsizlik va audit jurnali yozuvini kiritish (Audit Trail).
    Har bir muhim amal (chipta tekshirish, rezervatsiya, to'lov, admin amallari)
    vaqt tamg'asi (timestamp) va IP manzili bilan saqlanadi.
    """
    try:
        log_entry = ActivityLog(
            user_id=user_id,
            username=username or "Tizim",
            action=action,
            details=details,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG ERROR]: {e}")
        return None
