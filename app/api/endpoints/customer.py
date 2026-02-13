from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, ServiceRequest, Booking
from app.models.booking import ServiceRequestResponse, BookingResponse
from app.models.user import UserResponse
from pydantic import BaseModel

router = APIRouter()

class CustomerDashboardStats(BaseModel):
    active_requests: int
    upcoming_bookings: int
    completed_bookings: int
    total_spent: float

@router.get("/dashboard", response_model=CustomerDashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(deps.get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get customer dashboard statistics."""
    # Active requests (open or matched)
    active_req_result = await db.execute(
        select(func.count(ServiceRequest.id)).where(
            and_(
                ServiceRequest.customer_id == current_user.id,
                ServiceRequest.status.in_(["open", "matched"])
            )
        )
    )
    active_requests = active_req_result.scalar() or 0

    # Upcoming bookings (confirmed/in_progress)
    upcoming_result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.customer_id == current_user.id,
                Booking.status.in_(["confirmed", "in_progress"])
            )
        )
    )
    upcoming_bookings = upcoming_result.scalar() or 0

    # Completed bookings
    completed_result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.customer_id == current_user.id,
                Booking.status == "completed"
            )
        )
    )
    completed_bookings = completed_result.scalar() or 0

    # Total spent
    spent_result = await db.execute(
        select(func.sum(Booking.agreed_price)).where(
            and_(
                Booking.customer_id == current_user.id,
                Booking.status == "completed"
            )
        )
    )
    total_spent = spent_result.scalar() or 0.0

    return {
        "active_requests": active_requests,
        "upcoming_bookings": upcoming_bookings,
        "completed_bookings": completed_bookings,
        "total_spent": total_spent,
    }

@router.get("/requests", response_model=List[ServiceRequestResponse])
async def get_my_requests(
    current_user: User = Depends(deps.get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all service requests made by the customer."""
    result = await db.execute(
        select(ServiceRequest)
        .where(ServiceRequest.customer_id == current_user.id)
        .order_by(ServiceRequest.created_at.desc())
    )
    return result.scalars().all()

@router.get("/bookings", response_model=List[BookingResponse])
async def get_my_bookings(
    current_user: User = Depends(deps.get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all bookings for the customer."""
    result = await db.execute(
        select(Booking)
        .where(Booking.customer_id == current_user.id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(deps.get_current_customer),
) -> Any:
    """Get customer profile."""
    return current_user
