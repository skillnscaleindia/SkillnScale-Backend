from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, ServiceRequest, Booking, Availability, Review
from app.models.booking import ServiceRequestResponse, BookingResponse
from app.models.user import ProProfile
from pydantic import BaseModel

router = APIRouter()

class ProDashboardStats(BaseModel):
    active_jobs: int
    pending_requests: int
    completed_jobs: int
    total_earnings: float
    rating: float
    reviews_count: int

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

class AvailabilityUpdate(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str # HH:MM
    end_time: str   # HH:MM
    is_available: bool

@router.get("/dashboard", response_model=ProDashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(deps.get_current_professional),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get professional dashboard statistics."""
    # Active jobs (confirmed/in_progress)
    active_result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.professional_id == current_user.id,
                Booking.status.in_(["confirmed", "in_progress"])
            )
        )
    )
    active_jobs = active_result.scalar() or 0

    # Pending requests (open in my category)
    pending_result = await db.execute(
        select(func.count(ServiceRequest.id)).where(
            and_(
                ServiceRequest.category_id == current_user.service_category,
                ServiceRequest.status == "open"
            )
        )
    )
    pending_requests = pending_result.scalar() or 0

    # Completed jobs
    completed_result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.professional_id == current_user.id,
                Booking.status == "completed"
            )
        )
    )
    completed_jobs = completed_result.scalar() or 0

    # Total earnings
    earnings_result = await db.execute(
        select(func.sum(Booking.agreed_price)).where(
            and_(
                Booking.professional_id == current_user.id,
                Booking.status == "completed"
            )
        )
    )
    total_earnings = earnings_result.scalar() or 0.0

    # Rating
    rating_result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.reviewee_id == current_user.id)
    )
    row = rating_result.one()
    avg_rating = float(row[0]) if row[0] else 0.0
    reviews_count = row[1]

    return {
        "active_jobs": active_jobs,
        "pending_requests": pending_requests,
        "completed_jobs": completed_jobs,
        "total_earnings": total_earnings,
        "rating": round(avg_rating, 1),
        "reviews_count": reviews_count,
    }

@router.get("/requests", response_model=List[ServiceRequestResponse])
async def get_available_requests(
    current_user: User = Depends(deps.get_current_professional),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get open service requests matching professional's category."""
    result = await db.execute(
        select(ServiceRequest)
        .where(
            and_(
                ServiceRequest.category_id == current_user.service_category,
                ServiceRequest.status == "open"
            )
        )
        .order_by(ServiceRequest.created_at.desc())
    )
    return result.scalars().all()

@router.get("/bookings", response_model=List[BookingResponse])
async def get_my_bookings(
    current_user: User = Depends(deps.get_current_professional),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all bookings assigned to the professional."""
    result = await db.execute(
        select(Booking)
        .where(Booking.professional_id == current_user.id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()

@router.put("/location")
async def update_location(
    location: LocationUpdate,
    current_user: User = Depends(deps.get_current_professional),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update professional's real-time location."""
    current_user.latitude = location.latitude
    current_user.longitude = location.longitude
    # TODO: Add to LocationUpdate history table later
    await db.flush()
    return {"status": "updated", "lat": location.latitude, "lng": location.longitude}

@router.get("/profile", response_model=ProProfile)
async def get_profile(
    current_user: User = Depends(deps.get_current_professional),
) -> Any:
    """Get professional profile."""
    # Note: Stats fields (rating, jobs_completed) will be 0/null here unless we compute them
    # For now returning the user object, enhanced frontend can fetch dashboard stats separately
    return current_user
