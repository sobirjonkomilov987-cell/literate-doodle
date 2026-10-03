from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Ticket, User, UserRole
from app.schemas import TicketDetail, TicketVerifyRequest, TicketVerifyResponse
from app.auth import get_current_user, require_controller_or_admin
from app.services.payment import get_ticket_details
from app.services.ticket import verify_ticket_token

router = APIRouter(prefix="/api/tickets", tags=["Chiptalar va Nazorat (Tickets & Controller)"])

@router.get("/my-tickets", response_model=List[TicketDetail])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Qoida: Mijozlar faqat o'z chiptalarini ko'radi.
    Chiptada QR token, tadbir, sektor, joy raqami va narx mavjud.
    """
    tickets = (
        db.query(Ticket)
        .filter(Ticket.user_id == current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return [get_ticket_details(db, t) for t in tickets]

@router.post("/verify", response_model=TicketVerifyResponse)
def verify_ticket(
    req: TicketVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_controller: User = Depends(require_controller_or_admin)
):
    """
    Kritik talab 3: Chiptani tekshirish (Tekshiruvchi/Controller uchun).
    - Token faqat bir marta ishlatiladi ('used' bo'ladi)
    - Ikkinchi marta tekshirilganda RAD etiladi
    - Bekor qilingan chiptalar rad etiladi
    - Har bir tekshiruv controller shaxsi va IP bilan audit jurnaliga yoziladi
    """
    client_ip = request.client.host if request.client else "unknown"
    result = verify_ticket_token(
        db=db,
        token=req.token,
        controller_user=current_controller,
        ip_address=client_ip
    )
    return TicketVerifyResponse(
        valid=result["valid"],
        status=result["status"],
        message=result["message"],
        ticket=result.get("ticket")
    )

@router.get("/{token}", response_model=TicketDetail)
def get_ticket_by_token(token: str, db: Session = Depends(get_db)):
    """Token orqali chipta ma'lumotlarini tekshirish / ko'rish"""
    ticket = db.query(Ticket).filter(Ticket.token == token.strip()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chipta topilmadi")
    return get_ticket_details(db, ticket)
