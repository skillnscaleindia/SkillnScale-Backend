from typing import Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models.booking import Booking, BookingCreate, BookingStatus
from app.models.user import User
from app.api import deps
from app.db.mock_db import db

router = APIRouter()

@router.get("/", response_model=List[Booking])
def read_bookings(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve bookings for current user. 
    If Pro, return their accepted jobs.
    If Customer, return their requested jobs.
    """
    if current_user.role == "pro":
         return [b for b in db.bookings if b.get("pro_id") == current_user.id]
    return [b for b in db.bookings if b["user_id"] == current_user.id]

@router.get("/pending", response_model=List[Booking])
def read_pending_bookings(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all pending bookings (For Pros to browse).
    """
    if current_user.role != "pro":
        raise HTTPException(status_code=400, detail="Only professionals can view pending bookings")
        
    return [b for b in db.bookings if b["status"] == "pending"]

@router.post("/", response_model=Booking)
def create_booking(
    *,
    booking_in: BookingCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new booking.
    """
    booking_data = booking_in.model_dump()
    new_booking = {
        **booking_data,
        "id": f"bk_{len(db.bookings) + 1}",
        "user_id": current_user.id,
        "status": "pending",
        "total_amount": 100.0, # Mock Logic
        "created_at": datetime.utcnow(),
    }
    db.bookings.append(new_booking)
    return new_booking

@router.post("/{booking_id}/accept", response_model=Booking)
def accept_booking(
    booking_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Accept a booking (Pro only).
    """
    if current_user.role != "pro":
        raise HTTPException(status_code=400, detail="Only professionals can accept bookings")

    booking = next((b for b in db.bookings if b["id"] == booking_id), None)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking["status"] != "pending":
        raise HTTPException(status_code=400, detail="Booking already taken")

    booking["status"] = "accepted"
    booking["pro_id"] = current_user.id
    return booking
