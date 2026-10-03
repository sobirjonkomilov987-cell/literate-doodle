from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models import Event, Sector, Seat, SeatStatus, Ticket, TicketStatus, User, UserRole
from app.schemas import EventReportResponse, SectorReportItem
from app.auth import require_organizer_or_admin
from app.services.reservation import release_expired_reservations

router = APIRouter(prefix="/api/reports", tags=["Hisobotlar va Tahlillar (Reports)"])

@router.get("/events/{event_id}", response_model=EventReportResponse)
def get_event_report(
    event_id: int,
    sector_id: Optional[int] = Query(None, description="Sektor bo'yicha filtr"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    """
    Kritik talab 4: Tadbir bo'yicha hisobotlar.
    - Bandlik (occupancy rate)
    - Kirish hisoboti (admissions / checked-in rate)
    - Sektor bo'yicha filtr
    - Tashkilotchi faqat o'z tadbirini, Admin esa istalgan tadbirni ko'radi
    """
    release_expired_reservations(db)

    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi")

    # Xavfsizlik: Tashkilotchi faqat o'z tadbiri hisobotini ko'ra oladi
    if current_user.role != UserRole.ADMIN.value and ev.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz faqat o'zingizning tadbirlaringiz hisobotini ko'ra olasiz"
        )

    # Sektorlar so'rovi (agar sector_id berilsa, filtrlaymiz)
    sectors_query = db.query(Sector).filter(Sector.event_id == event_id)
    if sector_id:
        sectors_query = sectors_query.filter(Sector.id == sector_id)

    sectors = sectors_query.all()

    sector_items: List[SectorReportItem] = []
    total_event_seats = 0
    total_event_sold = 0
    total_event_available = 0
    total_event_reserved = 0
    total_event_revenue = 0.0
    total_event_checked_in = 0

    for sec in sectors:
        seats = db.query(Seat).filter(Seat.sector_id == sec.id).all()
        sec_total = len(seats)
        sec_sold = sum(1 for s in seats if s.status == SeatStatus.SOLD.value)
        sec_available = sum(1 for s in seats if s.status == SeatStatus.AVAILABLE.value)
        sec_reserved = sum(1 for s in seats if s.status == SeatStatus.RESERVED.value)
        sec_occupancy = round((sec_sold / sec_total * 100), 2) if sec_total > 0 else 0.0
        sec_revenue = float(sec_sold * sec.price)

        # Ushbu sektordagi ishlatilgan (used) chiptalar soni (kirish hisoboti)
        seat_ids = [s.id for s in seats]
        sec_checked_in = 0
        if seat_ids:
            sec_checked_in = (
                db.query(Ticket)
                .filter(
                    Ticket.seat_id.in_(seat_ids),
                    Ticket.status == TicketStatus.USED.value
                )
                .count()
            )

        sector_items.append(SectorReportItem(
            sector_id=sec.id,
            sector_name=sec.name,
            price=sec.price,
            total_seats=sec_total,
            available_seats=sec_available,
            reserved_seats=sec_reserved,
            sold_seats=sec_sold,
            occupancy_rate=sec_occupancy,
            revenue=sec_revenue,
            checked_in_count=sec_checked_in
        ))

        total_event_seats += sec_total
        total_event_sold += sec_sold
        total_event_available += sec_available
        total_event_reserved += sec_reserved
        total_event_revenue += sec_revenue
        total_event_checked_in += sec_checked_in

    overall_occupancy = round((total_event_sold / total_event_seats * 100), 2) if total_event_seats > 0 else 0.0
    overall_check_in_rate = round((total_event_checked_in / total_event_sold * 100), 2) if total_event_sold > 0 else 0.0

    return EventReportResponse(
        event_id=ev.id,
        event_title=ev.title,
        event_date=ev.date,
        total_seats=total_event_seats,
        available_seats=total_event_available,
        reserved_seats=total_event_reserved,
        sold_seats=total_event_sold,
        occupancy_rate=overall_occupancy,
        total_revenue=total_event_revenue,
        total_checked_in=total_event_checked_in,
        check_in_rate=overall_check_in_rate,
        sectors=sector_items
    )
