from sqlalchemy.orm import Session
from app.models import Ticket, TicketStatus, User
from app.services.payment import get_ticket_details
from app.services.reservation import get_current_utc_time
from app.services.audit import log_activity

def verify_ticket_token(db: Session, token: str, controller_user: User = None, ip_address: str = None) -> dict:
    """
    Chiptani tekshirish (Controller roli uchun):
    - Token bir marta ishlatiladi (used)
    - Ikkinchi marta o'tmaydi (allaqachon ishlatilgan xabari)
    - Bekor qilingan chiptalar (cancelled) o'tmaydi
    - Har bir tekshiruv va natija Audit jurnali (ActivityLog)da saqlanadi
    """
    clean_token = token.strip()
    ticket = db.query(Ticket).filter(Ticket.token == clean_token).first()
    ctrl_id = controller_user.id if controller_user else None
    ctrl_name = controller_user.username if controller_user else "Tekshiruvchi"

    if not ticket:
        log_activity(
            db=db,
            user_id=ctrl_id,
            username=ctrl_name,
            action="Chipta Tekshiruvi Rad Etildi (Soxta)",
            details=f"Tekshiruvchi '{ctrl_name}' mavjud bo'lmagan tokenni tekshirdi: '{clean_token[:12]}...'",
            ip_address=ip_address
        )
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
        log_activity(
            db=db,
            user_id=ctrl_id,
            username=ctrl_name,
            action="Chipta Tekshiruvi Rad Etildi (Ishlatilgan)",
            details=f"Chipta #{ticket.id} qayta ishlatilishiga urinish bo'ldi! Ilk ishlatilgan vaqt: {used_time_str}.",
            ip_address=ip_address
        )
        return {
            "valid": False,
            "status": "used",
            "message": f"RAD ETILDI! Ushbu chipta allaqachon ishlatilgan! Ishlatilgan vaqt: {used_time_str}",
            "ticket": details
        }

    # 2. Bekor qilingan holat
    if ticket.status == TicketStatus.CANCELLED.value:
        log_activity(
            db=db,
            user_id=ctrl_id,
            username=ctrl_name,
            action="Chipta Tekshiruvi Rad Etildi (Bekor Qilingan)",
            details=f"Chipta #{ticket.id} bekor qilingan holatda taqdim etildi.",
            ip_address=ip_address
        )
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

        log_activity(
            db=db,
            user_id=ctrl_id,
            username=ctrl_name,
            action="Chipta Tekshirildi (Muvaffaqiyatli)",
            details=f"Tekshiruvchi '{ctrl_name}' tomonidan Chipta #{ticket.id} tasdiqlandi. Tadbir: '{details.get('event_title')}', Joy: #{details.get('seat_number')}.",
            ip_address=ip_address
        )

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
