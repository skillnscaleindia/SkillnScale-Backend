from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    PRICE_PROPOSAL = "price_proposal"
    PRICE_ACCEPT = "price_accept"
    PRICE_REJECT = "price_reject"
    SYSTEM = "system"
    VOICE = "voice"
    IMAGE = "image"


# ─── Chat Room Schemas ───────────────────────────────────────────────

class ChatRoomCreate(BaseModel):
    request_id: str
    professional_id: str


class ChatRoomResponse(BaseModel):
    id: str
    request_id: str
    customer_id: str
    professional_id: str
    status: str
    created_at: datetime
    # Include last message preview
    last_message: Optional[str] = None
    professional_name: Optional[str] = None
    customer_name: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Message Schemas ─────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    proposed_price: Optional[float] = None  # Required for price_proposal
    media_url: Optional[str] = None
    duration: Optional[float] = None


class MessageResponse(BaseModel):
    id: str
    chat_room_id: str
    sender_id: str
    content: str
    message_type: str
    proposed_price: Optional[float] = None
    media_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Availability Schemas ────────────────────────────────────────────

class AvailabilityCreate(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, weekdays


class AvailabilityResponse(BaseModel):
    id: str
    professional_id: str
    date: str
    start_time: str
    end_time: str
    is_recurring: bool
    recurrence_pattern: Optional[str] = None
    is_booked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AvailabilityUpdate(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None


# ─── Review Schemas ──────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    booking_id: str
    rating: int  # 1-5
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    booking_id: str
    reviewer_id: str
    reviewee_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True
