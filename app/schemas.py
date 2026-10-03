from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ----------------- USER & AUTH SCHEMAS -----------------
class UserBase(BaseModel):
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str
    confirm_password: Optional[str] = None
    role: Optional[str] = "customer"
    organization_name: Optional[str] = None

class OrganizerCreate(BaseModel):
    username: str
    password: str
    organization_name: str

class ControllerCreate(BaseModel):
    username: str
    password: str

class UserPasswordReset(BaseModel):
    new_password: str

class AdminRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Ism va familiya")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email formati")
    phone: str = Field(..., min_length=7, max_length=30, description="Telefon raqami")
    password: str = Field(..., min_length=8, description="Kamida 8 ta belgili parol")
    confirm_password: str

class AdminLoginRequest(BaseModel):
    login: str = Field(..., description="Email yoki username")
    password: str = Field(..., description="Parol")

class ForgotPasswordRequest(BaseModel):
    login: str
    new_password: str = Field(..., min_length=8)

class AdminProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None

class AdminPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    action: str
    details: Optional[str] = None
    created_at: datetime

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    message: str
    type: str
    is_read: int
    created_at: datetime

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    avatar: Optional[str] = None
    organization_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None

# ----------------- SECTOR & SEAT SCHEMAS -----------------
class SeatBase(BaseModel):
    seat_number: str

class SeatCreate(SeatBase):
    pass

class BatchSeatsCreate(BaseModel):
    prefix: str = "A"
    rows: int = Field(default=5, ge=1, le=50)
    seats_per_row: int = Field(default=10, ge=1, le=50)

class SeatResponse(SeatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sector_id: int
    status: str
    price: Optional[float] = None
    sector_name: Optional[str] = None

class SectorBase(BaseModel):
    name: str
    price: float

class SectorCreate(SectorBase):
    pass

class SectorResponse(SectorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    seats: Optional[List[SeatResponse]] = None
    total_seats: Optional[int] = 0
    available_seats: Optional[int] = 0

# ----------------- EVENT SCHEMAS -----------------
class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: datetime
    location: Optional[str] = "Toshkent, Asosiy Saroy"

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organizer_id: int
    organizer_name: Optional[str] = None
    created_at: datetime
    sectors: Optional[List[SectorResponse]] = None

# ----------------- RESERVATION SCHEMAS -----------------
class ReservationCreate(BaseModel):
    seat_id: int

class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    seat_id: int
    expires_at: datetime
    status: str
    created_at: datetime
    seconds_left: int
    seat_number: Optional[str] = None
    sector_name: Optional[str] = None
    event_title: Optional[str] = None
    price: Optional[float] = None

# ----------------- PAYMENT SCHEMAS (IDEMPOTENT) -----------------
class PaymentCallbackRequest(BaseModel):
    reservation_id: int
    idempotency_key: str
    amount: float

class TicketDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    seat_id: int
    token: str
    status: str
    created_at: datetime
    used_at: Optional[datetime] = None
    event_title: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    sector_name: Optional[str] = None
    seat_number: Optional[str] = None
    price: Optional[float] = None
    attendee_name: Optional[str] = None

class PaymentResponse(BaseModel):
    status: str
    message: str
    is_duplicate_call: bool = False
    transaction_id: int
    ticket: TicketDetail

# ----------------- TICKET & CHECK-IN SCHEMAS -----------------
class TicketVerifyRequest(BaseModel):
    token: str

class TicketVerifyResponse(BaseModel):
    valid: bool
    status: str
    message: str
    ticket: Optional[TicketDetail] = None

# ----------------- REPORT SCHEMAS -----------------
class SectorReportItem(BaseModel):
    sector_id: int
    sector_name: str
    price: float
    total_seats: int
    available_seats: int
    reserved_seats: int
    sold_seats: int
    occupancy_rate: float
    revenue: float
    checked_in_count: int

class EventReportResponse(BaseModel):
    event_id: int
    event_title: str
    event_date: datetime
    total_seats: int
    available_seats: int
    reserved_seats: int
    sold_seats: int
    occupancy_rate: float
    total_revenue: float
    total_checked_in: int
    check_in_rate: float
    sectors: List[SectorReportItem]
