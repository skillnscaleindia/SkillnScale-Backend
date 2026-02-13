from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RequestStatus(str, Enum):
    OPEN = "open"
    MATCHED = "matched"
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestUrgency(str, Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ─── Service Request Schemas ─────────────────────────────────────────

class ServiceRequestCreate(BaseModel):
    category_id: str
    title: str
    description: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_at: Optional[datetime] = None
    urgency: RequestUrgency = RequestUrgency.IMMEDIATE
    photos: List[str] = []


class ServiceRequestResponse(BaseModel):
    id: str
    customer_id: str
    category_id: str
    title: str
    description: str
    photos: List[str] = []
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_at: Optional[datetime] = None
    urgency: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServiceRequestUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None


# ─── Booking Schemas ─────────────────────────────────────────────────

class BookingCreate(BaseModel):
    """Created automatically when a price is accepted in chat."""
    request_id: str
    professional_id: str
    agreed_price: float
    scheduled_at: Optional[datetime] = None


class BookingResponse(BaseModel):
    id: str
    request_id: str
    customer_id: str
    professional_id: str
    agreed_price: float
    status: str
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


# ─── Legacy Booking Schemas (backward compat) ────────────────────────

class LegacyBookingCreate(BaseModel):
    """For backward compatibility with existing frontend."""
    service_id: str
    scheduled_at: datetime
    address: str
    notes: Optional[str] = None


class LegacyBookingResponse(BaseModel):
    id: str
    user_id: str
    pro_id: Optional[str] = None
    service_id: str
    scheduled_at: datetime
    address: str
    notes: Optional[str] = None
    status: str
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True
