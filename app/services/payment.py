import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import (
    Reservation, ReservationStatus,
    Seat, SeatStatus,
    Ticket, TicketStatus,
    PaymentTransaction,
    User, Sector, Event
)
from app.services.reservation import get_current_utc_time, release_expired_reservations

def get_ticket_details(db: Session, ticket: Ticket) -> dict:
    """Chipta ma'lumotlarini to'liq shakllantirib beradi"""
    seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
    sector = db.query(Sector).filter(Sector.id == seat.sector_id).first() if seat else None
    event = db.query(Event).filter(Event.id == sector.event_id).first() if sector else None
    user = db.query(User).filter(User.id == ticket.user_id).first()

    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "seat_id": ticket.seat_id,
        "token": ticket.token,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "used_at": ticket.used_at,
        "event_title": event.title if event else "Noma'lum tadbir",
        "event_date": event.date if event else None,
        "location": event.location if event else None,
        "sector_name": sector.name if sector else None,
        "seat_number": seat.seat_number if seat else None,
        "price": sector.price if sector else 0.0,
        "attendee_name": user.username if user else "Mijoz"
    }

def process_mock_payment_callback(
    db: Session,
    reservation_id: int,
    idempotency_key: str,
    amount: float,
    user_id: int = None
) -> dict:
    """
    To'lov callback'i (Idempotent bo'lishi ta'minlangan).
    Agar bir xil idempotency_key bilan takroriy so'rov kelsa,
    baza o'zgarmaydi va avvalgi yaratilgan chipta qaytariladi.
    """
    # 1. Idempotency tekshiruvi
    existing_tx = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.idempotency_key == idempotency_key)
        .first()
    )

    if existing_tx:
        # Avvalgi chiptani topamiz
        ticket = db.query(Ticket).filter(Ticket.id == existing_tx.ticket_id).first()
        if not ticket:
            ticket = db.query(Ticket).filter(Ticket.seat_id == existing_tx.reservation_id).first()

        ticket_details = get_ticket_details(db, ticket) if ticket else None
        return {
            "status": "success",
            "message": "Idempotent javob: Ushbu to'lov tranzaksiyasi avval ro'yxatdan o'tgan, takroriy to'lov olinmadi.",
            "is_duplicate_call": True,
            "transaction_id": existing_tx.id,
            "ticket": ticket_details
        }

    # 2. Eskirgan rezervatsiyalarni tozalash
    release_expired_reservations(db)

    # 3. Rezervatsiyani tekshirish
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bunday rezervatsiya topilmadi"
        )

    now = get_current_utc_time()
    if reservation.status != ReservationStatus.PENDING.value or reservation.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rezervatsiya muddati (10 daqiqa) tugagan yoki yaroqsiz! Iltimos, joyni qaytadan tanlang."
        )

    # 4. Joyni tekshirish
    seat = db.query(Seat).filter(Seat.id == reservation.seat_id).first()
    if not seat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Joy topilmadi"
        )

    if seat.status == SeatStatus.SOLD.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu joy allaqachon sotilgan"
        )

    # 5. Muvaffaqiyatli xarid: Joy holatini 'sold' ga, rezervatsiyani 'completed' ga o'tkazish
    seat.status = SeatStatus.SOLD.value
    reservation.status = ReservationStatus.COMPLETED.value

    # 6. Unikal chipta tokenini (UUID) hosil qilish
    ticket_token = str(uuid.uuid4())

    new_ticket = Ticket(
        user_id=reservation.user_id,
        seat_id=seat.id,
        token=ticket_token,
        status=TicketStatus.ACTIVE.value,
        created_at=now
    )
    db.add(new_ticket)
    db.flush() # id olish uchun

    # 7. Idempotent tranzaksiya yozuvini kiritish
    new_tx = PaymentTransaction(
        idempotency_key=idempotency_key,
        reservation_id=reservation.id,
        ticket_id=new_ticket.id,
        amount=amount,
        status="success",
        created_at=now
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_ticket)
    db.refresh(new_tx)

    ticket_details = get_ticket_details(db, new_ticket)

    return {
        "status": "success",
        "message": "To'lov muvaffaqiyatli qabul qilindi va elektron chipta shakllantirildi!",
        "is_duplicate_call": False,
        "transaction_id": new_tx.id,
        "ticket": ticket_details
    }
