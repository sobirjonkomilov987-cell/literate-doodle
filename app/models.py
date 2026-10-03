from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    ORGANIZER = "organizer"
    CUSTOMER = "customer"
    CONTROLLER = "controller"

class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"

class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    EXPIRED = "expired"
    COMPLETED = "completed"

class TicketStatus(str, enum.Enum):
    ACTIVE = "active"
    USED = "used"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.CUSTOMER.value, nullable=False, index=True)
    avatar = Column(Text, nullable=True)
    organization_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    events = relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="user", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    organizer = relationship("User", back_populates="events")
    sectors = relationship("Sector", back_populates="event", cascade="all, delete-orphan")

class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="sectors")
    seats = relationship("Seat", back_populates="sector", cascade="all, delete-orphan")

class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    seat_number = Column(String(50), nullable=False)
    status = Column(String(50), default=SeatStatus.AVAILABLE.value, nullable=False, index=True)

    # Relationships
    sector = relationship("Sector", back_populates="seats")
    reservations = relationship("Reservation", back_populates="seat", cascade="all, delete-orphan")
    ticket = relationship("Ticket", back_populates="seat", uselist=False)

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default=ReservationStatus.PENDING.value, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="reservations")
    seat = relationship("Seat", back_populates="reservations")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False, unique=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), default=TicketStatus.ACTIVE.value, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tickets")
    seat = relationship("Seat", back_populates="ticket")

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="success", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info") # info, success, warning, danger
    is_read = Column(Integer, default=0) # 0: unread, 1: read
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
