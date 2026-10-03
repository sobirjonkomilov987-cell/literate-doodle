from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Event, Sector, Seat, SeatStatus, User, UserRole
from app.schemas import (
    EventCreate, EventResponse,
    SectorCreate, SectorResponse,
    SeatCreate, BatchSeatsCreate, SeatResponse
)
from app.auth import get_current_user, require_organizer_or_admin
from app.services.reservation import release_expired_reservations

router = APIRouter(prefix="/api/events", tags=["Tadbirlar, Sektorlar va Joylar"])

@router.get("", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    """Barcha faol tadbirlar ro'yxatini olish (Har kim ko'rishi mumkin)"""
    release_expired_reservations(db)
    events = db.query(Event).order_by(Event.date.asc()).all()

    result = []
    for ev in events:
        sectors_res = []
        for sec in ev.sectors:
            total_seats = len(sec.seats)
            available_seats = sum(1 for s in sec.seats if s.status == SeatStatus.AVAILABLE.value)
            sec_dict = SectorResponse(
                id=sec.id,
                event_id=sec.event_id,
                name=sec.name,
                price=sec.price,
                total_seats=total_seats,
                available_seats=available_seats
            )
            sectors_res.append(sec_dict)

        ev_res = EventResponse(
            id=ev.id,
            title=ev.title,
            description=ev.description,
            date=ev.date,
            location=ev.location,
            organizer_id=ev.organizer_id,
            organizer_name=ev.organizer.organization_name or ev.organizer.username if ev.organizer else "Noma'lum",
            created_at=ev.created_at,
            sectors=sectors_res
        )
        result.append(ev_res)

    return result

@router.get("/organizer/my-events", response_model=List[EventResponse])
def list_organizer_my_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """
    Faqat joriy tashkilotchining O'Z tadbirlari ro'yxati.
    Boshqa tashkilotchilarning tadbirlarini ko'ra olmaydi va boshqara olmaydi.
    """
    release_expired_reservations(db)
    query = db.query(Event)
    if current_user.role != UserRole.ADMIN.value:
        query = query.filter(Event.organizer_id == current_user.id)
    events = query.order_by(Event.date.desc()).all()

    result = []
    for ev in events:
        sectors_res = []
        for sec in ev.sectors:
            total_seats = len(sec.seats)
            available_seats = sum(1 for s in sec.seats if s.status == SeatStatus.AVAILABLE.value)
            sectors_res.append(SectorResponse(
                id=sec.id,
                event_id=sec.event_id,
                name=sec.name,
                price=sec.price,
                total_seats=total_seats,
                available_seats=available_seats
            ))

        ev_res = EventResponse(
            id=ev.id,
            title=ev.title,
            description=ev.description,
            date=ev.date,
            location=ev.location,
            organizer_id=ev.organizer_id,
            organizer_name=ev.organizer.organization_name or ev.organizer.username if ev.organizer else "Noma'lum",
            created_at=ev.created_at,
            sectors=sectors_res
        )
        result.append(ev_res)

    return result

@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):

    """Bitta tadbir haqida to'liq ma'lumot va uning sektorlari"""
    release_expired_reservations(db)
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi")

    sectors_res = []
    for sec in ev.sectors:
        total_seats = len(sec.seats)
        available_seats = sum(1 for s in sec.seats if s.status == SeatStatus.AVAILABLE.value)
        sectors_res.append(SectorResponse(
            id=sec.id,
            event_id=sec.event_id,
            name=sec.name,
            price=sec.price,
            total_seats=total_seats,
            available_seats=available_seats
        ))

    return EventResponse(
        id=ev.id,
        title=ev.title,
        description=ev.description,
        date=ev.date,
        location=ev.location,
        organizer_id=ev.organizer_id,
        organizer_name=ev.organizer.organization_name or ev.organizer.username if ev.organizer else "Noma'lum",
        created_at=ev.created_at,
        sectors=sectors_res
    )

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    ev_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """
    Yangi tadbir yaratish (Faqat Tashkilotchi va Admin).
    Tashkilotchi o'z tadbirini yaratadi.
    """
    new_event = Event(
        title=ev_in.title,
        description=ev_in.description,
        date=ev_in.date,
        location=ev_in.location,
        organizer_id=current_user.id
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return EventResponse(
        id=new_event.id,
        title=new_event.title,
        description=new_event.description,
        date=new_event.date,
        location=new_event.location,
        organizer_id=new_event.organizer_id,
        organizer_name=current_user.organization_name or current_user.username,
        created_at=new_event.created_at,
        sectors=[]
    )

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """Tadbirni o'chirish"""
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi")

    if current_user.role != UserRole.ADMIN.value and ev.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Siz faqat o'zingizning tadbiringizni o'chira olasiz")

    db.delete(ev)
    db.commit()
    return None

# ----------------- SEKTORLAR VA JOYLAR -----------------

@router.post("/{event_id}/sectors", response_model=SectorResponse, status_code=status.HTTP_201_CREATED)
def add_sector(
    event_id: int,
    sec_in: SectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """Tadbirga yangi sektor va narx belgilash"""
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi")

    if current_user.role != UserRole.ADMIN.value and ev.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Siz faqat o'z tadbiringizga sektor qo'sha olasiz")

    new_sec = Sector(
        event_id=event_id,
        name=sec_in.name,
        price=sec_in.price
    )
    db.add(new_sec)
    db.commit()
    db.refresh(new_sec)

    return SectorResponse(
        id=new_sec.id,
        event_id=new_sec.event_id,
        name=new_sec.name,
        price=new_sec.price,
        total_seats=0,
        available_seats=0
    )

@router.post("/sectors/{sector_id}/seats/batch", response_model=List[SeatResponse], status_code=status.HTTP_201_CREATED)
def batch_create_seats(
    sector_id: int,
    batch_in: BatchSeatsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """
    Sektorga ommaviy (batch) tarzda joylarni avtomatik yaratish:
    Masalan: rows=3, seats_per_row=5, prefix='A' -> A1..A15
    """
    sec = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Sektor topilmadi")

    ev = db.query(Event).filter(Event.id == sec.event_id).first()
    if current_user.role != UserRole.ADMIN.value and ev.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Siz faqat o'z tadbiringiz sektoriga joy qo'sha olasiz")

    created_seats = []
    # Qatorlar bo'yicha: A-1, A-2, B-1, B-2...
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(batch_in.rows):
        row_letter = letters[r % len(letters)] if batch_in.rows > 1 else batch_in.prefix
        for s in range(1, batch_in.seats_per_row + 1):
            seat_num = f"{batch_in.prefix}-{row_letter}{s}" if batch_in.rows > 1 else f"{batch_in.prefix}-{s}"
            seat = Seat(
                sector_id=sector_id,
                seat_number=seat_num,
                status=SeatStatus.AVAILABLE.value
            )
            db.add(seat)
            created_seats.append(seat)

    db.commit()

    return [
        SeatResponse(
            id=s.id,
            sector_id=s.sector_id,
            seat_number=s.seat_number,
            status=s.status,
            price=sec.price,
            sector_name=sec.name
        ) for s in created_seats
    ]

@router.get("/sectors/{sector_id}/seats", response_model=List[SeatResponse])
def get_sector_seats(sector_id: int, db: Session = Depends(get_db)):
    """Sektordagi barcha joylar va ularning real vaqtdagi holati (available, reserved, sold)"""
    release_expired_reservations(db)
    sec = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Sektor topilmadi")

    seats = db.query(Seat).filter(Seat.sector_id == sector_id).order_by(Seat.id.asc()).all()
    return [
        SeatResponse(
            id=s.id,
            sector_id=s.sector_id,
            seat_number=s.seat_number,
            status=s.status,
            price=sec.price,
            sector_name=sec.name
        ) for s in seats
    ]
