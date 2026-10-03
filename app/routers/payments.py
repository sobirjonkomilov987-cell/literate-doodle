from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PaymentCallbackRequest, PaymentResponse
from app.services.payment import process_mock_payment_callback

router = APIRouter(prefix="/api/payments", tags=["To'lov Tizimi (Idempotent Callback)"])

@router.post("/callback", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
def payment_callback(
    req: PaymentCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Kritik talab 2: Soxta to'lov va Idempotency.
    To'lov provayderi (Payme/Click/Stripe va h.k.) yoki front-end tomonidan callback yuboriladi.
    Bir xil 'idempotency_key' bilan takroran chaqirilsa ham:
    - Takroriy chipta yaratilmaydi
    - Takroriy mablag' yozilmaydi
    - Avvalgi yaratilgan chipta ma'lumotlari xavfsiz qaytariladi ('is_duplicate_call': True)
    """
    result = process_mock_payment_callback(
        db=db,
        reservation_id=req.reservation_id,
        idempotency_key=req.idempotency_key,
        amount=req.amount
    )
    return result
