from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Seat, SeatStatus, Reservation, ReservationStatus, Event, Sector
from app.config import settings

def get_current_utc_time() -> datetime:
    """Hozirgi UTC vaqtni qaytaradi (bazaga moslashuvchan)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def release_expired_reservations(db: Session) -> int:
    """
    10 daqiqalik muddati o'tgan rezervatsiyalarni tekshiradi va
    joylarni avtomatik ravishda qayta bo'shatadi (available holatiga o'tkazadi).
    """
    now = get_current_utc_time()
    expired_reservations = (
        db.query(Reservation)
        .filter(
            Reservation.status == ReservationStatus.PENDING.value,
            Reservation.expires_at <= now
        )
        .all()
    )

    count = 0
    for res in expired_reservations:
        res.status = ReservationStatus.EXPIRED.value
        seat = db.query(Seat).filter(Seat.id == res.seat_id).first()
        if seat and seat.status == SeatStatus.RESERVED.value:
            seat.status = SeatStatus.AVAILABLE.value
        count += 1

    if count > 0:
        db.commit()
    return count

def reserve_seat(db: Session, user_id: int, seat_id: int) -> Reservation:
    """
    Joyni 10 daqiqaga band qiladi.
    Konkurensiya (race condition) oldini olish uchun bazada qulf (row lock) yoki
    atomik update amali bajariladi.
    """
    # 1. Avval muddati o'tganlarini tozalab olamiz
    release_expired_reservations(db)

    # 2. Joyni tekshiramiz va atomik ravishda band qilamiz
    # Concurrency / Race Condition oldini olish:
    # Qator darajasida 'with_for_update' yoki tekshiruv bilan atomik yangilash
    try:
        seat = (
            db.query(Seat)
            .filter(Seat.id == seat_id)
            .with_for_update()
            .first()
        )
    except Exception:
        # SQLite ba'zan with_for_update ni qo'llamasligi mumkin, fallback:
        seat = db.query(Seat).filter(Seat.id == seat_id).first()

    if not seat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bunday joy topilmadi"
        )

    if seat.status == SeatStatus.SOLD.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ushbu joy allaqachon sotilgan!"
        )

    if seat.status == SeatStatus.RESERVED.value:
        # Tekshirib ko'ramiz, ehtimol bu rezervatsiya muddati tugagan bo'lishi mumkin
        active_res = (
            db.query(Reservation)
            .filter(
                Reservation.seat_id == seat_id,
                Reservation.status == ReservationStatus.PENDING.value
            )
            .first()
        )
        if active_res and active_res.expires_at > get_current_utc_time():
            if active_res.user_id == user_id:
                # Foydalanuvchining o'zining faol rezervatsiyasi
                return active_res
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ushbu joy ayni paytda boshqa foydalanuvchi tomonidan 10 daqiqaga band qilingan!"
            )
        elif active_res:
            active_res.status = ReservationStatus.EXPIRED.value

    # Joyni 'reserved' holatiga o'tkazish
    seat.status = SeatStatus.RESERVED.value

    now = get_current_utc_time()
    expires_at = now + timedelta(minutes=settings.RESERVATION_TIMEOUT_MINUTES)

    new_reservation = Reservation(
        user_id=user_id,
        seat_id=seat.id,
        expires_at=expires_at,
        status=ReservationStatus.PENDING.value,
        created_at=now
    )

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation

def cancel_reservation(db: Session, reservation_id: int, user_id: int) -> bool:
    """Rezervatsiyani bekor qilish va joyni bo'shatish"""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Rezervatsiya topilmadi")
    if res.user_id != user_id:
        raise HTTPException(status_code=403, detail="Siz faqat o'z rezervatsiyangizni bekor qila olasiz")

    if res.status == ReservationStatus.PENDING.value:
        res.status = ReservationStatus.EXPIRED.value
        seat = db.query(Seat).filter(Seat.id == res.seat_id).first()
        if seat and seat.status == SeatStatus.RESERVED.value:
            seat.status = SeatStatus.AVAILABLE.value
        db.commit()
        return True
    return False
