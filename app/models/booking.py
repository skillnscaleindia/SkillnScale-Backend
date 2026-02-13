from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class BookingStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class BookingCreate(BaseModel):
    service_id: str
    scheduled_at: datetime
    address: str
    notes: Optional[str] = None

class Booking(BookingCreate):
    id: str
    user_id: int
    pro_id: Optional[int] = None
    status: BookingStatus = BookingStatus.PENDING
    total_amount: float
    created_at: datetime
