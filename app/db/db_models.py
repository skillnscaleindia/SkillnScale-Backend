import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


# ─── Enums ───────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    PRO = "pro"


class RequestStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestUrgency(str, enum.Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageType(str, enum.Enum):
    TEXT = "text"
    PRICE_PROPOSAL = "price_proposal"
    PRICE_ACCEPT = "price_accept"
    PRICE_REJECT = "price_reject"
    SYSTEM = "system"
    VOICE = "voice"
    IMAGE = "image"


class ChatRoomStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"





class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ─── Helper ──────────────────────────────────────────────────────────

def generate_uuid():
    return str(uuid.uuid4())


# ─── Models ──────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default=UserRole.CUSTOMER.value)
    service_category = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(255), nullable=True)
    profile_photo = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    service_requests = relationship("ServiceRequest", back_populates="customer", foreign_keys="ServiceRequest.customer_id")
    availability_slots = relationship("Availability", back_populates="professional")
    sent_messages = relationship("Message", back_populates="sender")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    device_tokens = relationship("DeviceToken", back_populates="user")


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(50), nullable=False)
    color = Column(String(20), nullable=False)
    description = Column(String(255), nullable=True)

    # Relationships
    service_requests = relationship("ServiceRequest", back_populates="category")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("service_categories.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    photos = Column(JSON, default=list)
    location = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    urgency = Column(String(20), default=RequestUrgency.IMMEDIATE.value)
    status = Column(String(20), default=RequestStatus.OPEN.value, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("User", back_populates="service_requests", foreign_keys=[customer_id])
    category = relationship("ServiceCategory", back_populates="service_requests")
    chat_rooms = relationship("ChatRoom", back_populates="service_request")
    booking = relationship("Booking", back_populates="service_request", uselist=False)


class Availability(Base):
    __tablename__ = "availability"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    professional_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)  # HH:MM
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(20), nullable=True)
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    professional = relationship("User", back_populates="availability_slots")


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    professional_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default=ChatRoomStatus.ACTIVE.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="chat_rooms")
    customer = relationship("User", foreign_keys=[customer_id])
    professional = relationship("User", foreign_keys=[professional_id])
    messages = relationship("Message", back_populates="chat_room", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_room_id = Column(String(36), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default=MessageType.TEXT.value)
    proposed_price = Column(Float, nullable=True)
    media_url = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, unique=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="review")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    professional_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    agreed_price = Column(Float, default=0.0)
    status = Column(String(20), default=BookingStatus.CONFIRMED.value, index=True)
    scheduled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="booking")
    customer = relationship("User", foreign_keys=[customer_id])
    professional = relationship("User", foreign_keys=[professional_id])

    review = relationship("Review", back_populates="booking", uselist=False)
    payment = relationship("Payment", back_populates="booking", uselist=False)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    platform = Column(String(10), nullable=False)  # android, ios, web
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="device_tokens")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="inr")
    status = Column(String(20), default=PaymentStatus.PENDING.value)
    stripe_payment_intent_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="payment")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(15), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
