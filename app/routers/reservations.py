from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, Reservation, ReservationStatus, Seat, Sector, Event
from app.schemas import ReservationCreate, ReservationResponse
from app.auth import get_current_user
from app.services.reservation import reserve_seat, cancel_reservation, get_current_utc_time, release_expired_reservations

router = APIRouter(prefix="/api/reservations", tags=["Rezervatsiya (10 daqiqalik band qilish)"])

def format_reservation_response(res: Reservation, db: Session) -> ReservationResponse:
    now = get_current_utc_time()
    diff = (res.expires_at - now).total_seconds()
    seconds_left = max(0, int(diff))

    seat = db.query(Seat).filter(Seat.id == res.seat_id).first()
    sector = db.query(Sector).filter(Sector.id == seat.sector_id).first() if seat else None
    event = db.query(Event).filter(Event.id == sector.event_id).first() if sector else None

    return ReservationResponse(
        id=res.id,
        user_id=res.user_id,
        seat_id=res.seat_id,
        expires_at=res.expires_at,
        status=res.status,
        created_at=res.created_at,
        seconds_left=seconds_left,
        seat_number=seat.seat_number if seat else "N/A",
        sector_name=sector.name if sector else "N/A",
        event_title=event.title if event else "N/A",
        price=sector.price if sector else 0.0
    )

@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def make_reservation(
    req: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kritik talab 1: Joyni 10 daqiqaga band qilish.
    Konkurensiya (race condition) oldi olingan holda joy holati 'reserved' ga o'tadi.
    10 daqiqadan so'ng avtomatik bekor bo'ladi.
    """
    res = reserve_seat(db, user_id=current_user.id, seat_id=req.seat_id)
    return format_reservation_response(res, db)

@router.get("/my", response_model=List[ReservationResponse])
def get_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mijozning hozirgi faol (pending) rezervatsiyalari va qolgan vaqti"""
    release_expired_reservations(db)
    now = get_current_utc_time()

    reservations = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == current_user.id,
            Reservation.status == ReservationStatus.PENDING.value,
            Reservation.expires_at > now
        )
        .order_by(Reservation.expires_at.desc())
        .all()
    )

    return [format_reservation_response(r, db) for r in reservations]

@router.delete("/{reservation_id}", status_code=status.HTTP_200_OK)
def cancel_my_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rezervatsiyani bekor qilish va joyni boshqalarga ochib berish"""
    success = cancel_reservation(db, reservation_id, current_user.id)
    return {"success": success, "message": "Rezervatsiya bekor qilindi, joy bo'shatildi."}
