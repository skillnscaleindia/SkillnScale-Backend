from typing import Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.booking import (
    BookingResponse, BookingStatusUpdate,
    LegacyBookingCreate, LegacyBookingResponse,
)
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, Booking, ServiceRequest

router = APIRouter()


@router.get("/", response_model=List[LegacyBookingResponse])
async def read_bookings(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve bookings for current user (legacy format for backward compat)."""
    if current_user.role == "pro":
        result = await db.execute(
            select(Booking).where(Booking.professional_id == current_user.id)
        )
    else:
        result = await db.execute(
            select(Booking).where(Booking.customer_id == current_user.id)
        )

    bookings = result.scalars().all()

    # Map to legacy format
    legacy = []
    for b in bookings:
        req_result = await db.execute(
            select(ServiceRequest).where(ServiceRequest.id == b.request_id)
        )
        req = req_result.scalar_one_or_none()
        legacy.append(LegacyBookingResponse(
            id=b.id,
            user_id=b.customer_id,
            pro_id=b.professional_id,
            service_id=req.category_id if req else "general",
            scheduled_at=b.scheduled_at or b.created_at,
            address=req.location if req else "",
            notes=f"{req.title}: {req.description}" if req else "",
            status=b.status,
            total_amount=b.agreed_price,
            created_at=b.created_at,
        ))
    return legacy


@router.post("/", response_model=LegacyBookingResponse)
async def create_booking_legacy(
    booking_in: LegacyBookingCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create booking (legacy format — creates a service request + booking)."""
    # Create a service request first
    service_request = ServiceRequest(
        customer_id=current_user.id,
        category_id=booking_in.service_id,
        title=booking_in.service_id.capitalize(),
        description=booking_in.notes or "Service requested",
        location=booking_in.address,
        scheduled_at=booking_in.scheduled_at,
        urgency="scheduled",
        status="booked",
    )
    db.add(service_request)
    await db.flush()

    # Create the booking
    new_booking = Booking(
        request_id=service_request.id,
        customer_id=current_user.id,
        professional_id=current_user.id,  # Placeholder — will be assigned later
        agreed_price=0.0,  # Negotiation pending
        status="confirmed",
        scheduled_at=booking_in.scheduled_at,
    )
    db.add(new_booking)
    await db.flush()
    await db.refresh(new_booking)

    return LegacyBookingResponse(
        id=new_booking.id,
        user_id=current_user.id,
        pro_id=None,
        service_id=booking_in.service_id,
        scheduled_at=booking_in.scheduled_at,
        address=booking_in.address,
        notes=booking_in.notes,
        status=new_booking.status,
        total_amount=new_booking.agreed_price,
        created_at=new_booking.created_at,
    )


@router.get("/pending", response_model=List[LegacyBookingResponse])
async def read_pending_bookings(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve all pending/open requests (For Pros to browse)."""
    if current_user.role != "pro":
        raise HTTPException(status_code=400, detail="Only professionals can view pending bookings")

    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.status == "open")
    )
    requests = result.scalars().all()

    legacy = []
    for req in requests:
        legacy.append(LegacyBookingResponse(
            id=req.id,
            user_id=req.customer_id,
            pro_id=None,
            service_id=req.category_id,
            scheduled_at=req.scheduled_at or req.created_at,
            address=req.location,
            notes=f"{req.title}: {req.description}",
            status="pending",
            total_amount=0.0,
            created_at=req.created_at,
        ))
    return legacy


@router.post("/{booking_id}/accept", response_model=LegacyBookingResponse)
async def accept_booking(
    booking_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Accept a booking (Pro only)."""
    if current_user.role != "pro":
        raise HTTPException(status_code=400, detail="Only professionals can accept bookings")

    # Check if it's a service request (from pending endpoint)
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == booking_id))
    service_req = result.scalar_one_or_none()

    if service_req:
        service_req.status = "booked"
        new_booking = Booking(
            request_id=service_req.id,
            customer_id=service_req.customer_id,
            professional_id=current_user.id,
            agreed_price=0.0,
            status="confirmed",
            scheduled_at=service_req.scheduled_at,
        )
        db.add(new_booking)
        await db.flush()
        await db.refresh(new_booking)

        # Add notification for customer
        from app.services.notification_service import send_notification_to_user
        await send_notification_to_user(
            db, 
            service_req.customer_id, 
            "Booking Accepted!", 
            f"Your request '{service_req.title}' has been accepted.",
            {"booking_id": new_booking.id, "type": "booking_accepted"}
        )

        return LegacyBookingResponse(
            id=new_booking.id,
            user_id=service_req.customer_id,
            pro_id=current_user.id,
            service_id=service_req.category_id,
            scheduled_at=service_req.scheduled_at or service_req.created_at,
            address=service_req.location,
            notes=f"{service_req.title}: {service_req.description}",
            status="accepted",
            total_amount=new_booking.agreed_price,
            created_at=new_booking.created_at,
        )

    # Fallback: check real bookings
    booking_result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.professional_id = current_user.id
    booking.status = "confirmed"
    await db.flush()

    return LegacyBookingResponse(
        id=booking.id,
        user_id=booking.customer_id,
        pro_id=current_user.id,
        service_id="general",
        scheduled_at=booking.scheduled_at or booking.created_at,
        address="",
        notes="",
        status="accepted",
        total_amount=booking.agreed_price,
        created_at=booking.created_at,
    )


@router.patch("/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: str,
    status_update: BookingStatusUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update booking status (e.g., in_progress → completed)."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Only participants can update
    if current_user.id not in [booking.customer_id, booking.professional_id]:
        raise HTTPException(status_code=403, detail="Not authorized")

    booking.status = status_update.status.value
    if status_update.status.value == "completed":
        booking.completed_at = datetime.utcnow()

    await db.flush()
    await db.refresh(booking)
    return booking


@router.get("/{booking_id}/location", response_model=dict)
async def get_booking_location(
    booking_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get the real-time location of the professional for a booking."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Only participants can view location
    if current_user.id not in [booking.customer_id, booking.professional_id]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get professional's location
    if booking.professional_id:
        pro_result = await db.execute(select(User).where(User.id == booking.professional_id))
        pro = pro_result.scalar_one_or_none()
        if pro and pro.latitude and pro.longitude:
            return {
                "latitude": pro.latitude,
                "longitude": pro.longitude,
                "last_updated": pro.updated_at if hasattr(pro, 'updated_at') else None
            }
    
    # Return default or empty if not available
    return {"latitude": None, "longitude": None}
