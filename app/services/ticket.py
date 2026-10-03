from sqlalchemy.orm import Session
from app.models import Ticket, TicketStatus
from app.services.payment import get_ticket_details
from app.services.reservation import get_current_utc_time

def verify_ticket_token(db: Session, token: str) -> dict:
    """
    Chiptani tekshirish (Controller roli uchun):
    - Token bir marta ishlatiladi (used)
    - Ikkinchi marta o'tmaydi (allaqachon ishlatilgan xabari)
    - Bekor qilingan chiptalar (cancelled) o'tmaydi
    """
    clean_token = token.strip()
    ticket = db.query(Ticket).filter(Ticket.token == clean_token).first()

    if not ticket:
        return {
            "valid": False,
            "status": "not_found",
            "message": "Xatolik: Tizimda bunday tokenli chipta topilmadi! (Soxta yoki noto'g'ri kod)",
            "ticket": None
        }

    details = get_ticket_details(db, ticket)

    # 1. Allaqachon ishlatilgan holat
    if ticket.status == TicketStatus.USED.value:
        used_time_str = ticket.used_at.strftime("%Y-%m-%d %H:%M:%S") if ticket.used_at else "Noma'lum"
        return {
            "valid": False,
            "status": "used",
            "message": f"RAD ETILDI! Ushbu chipta allaqachon ishlatilgan! Ishlatilgan vaqt: {used_time_str}",
            "ticket": details
        }

    # 2. Bekor qilingan holat
    if ticket.status == TicketStatus.CANCELLED.value:
        return {
            "valid": False,
            "status": "cancelled",
            "message": "RAD ETILDI! Ushbu chipta bekor qilingan (chipta haqiqiy emas).",
            "ticket": details
        }

    # 3. Faol chipta - qabul qilinadi va 'used' qilib belgilanadi
    if ticket.status == TicketStatus.ACTIVE.value:
        now = get_current_utc_time()
        ticket.status = TicketStatus.USED.value
        ticket.used_at = now
        db.commit()
        db.refresh(ticket)

        details["status"] = TicketStatus.USED.value
        details["used_at"] = now

        return {
            "valid": True,
            "status": "success",
            "message": "KIRISHGA RUXSAT BERILDI! Chipta haqiqiy va muvaffaqiyatli qabul qilindi.",
            "ticket": details
        }

    return {
        "valid": False,
        "status": "invalid",
        "message": f"Noma'lum chipta holati: {ticket.status}",
        "ticket": details
    }
