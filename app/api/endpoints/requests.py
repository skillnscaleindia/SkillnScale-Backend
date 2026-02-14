from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from app.models.booking import ServiceRequestCreate, ServiceRequestResponse, ServiceRequestUpdate
from app.models.user import ProProfile
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, ServiceRequest, Availability, Review, Booking
from app.services.validate_service import validate_service_description
from sqlalchemy import func

router = APIRouter()


class DescriptionValidation(BaseModel):
    category_id: str
    description: str


@router.post("/validate-description")
async def validate_description(data: DescriptionValidation) -> Any:
    """Validate whether a service description is relevant to the category."""
    return validate_service_description(data.category_id, data.description)


@router.post("/", response_model=ServiceRequestResponse)
async def create_service_request(
    request_in: ServiceRequestCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Customer creates a service request with problem description."""
    new_request = ServiceRequest(
        customer_id=current_user.id,
        category_id=request_in.category_id,
        title=request_in.title,
        description=request_in.description,
        photos=request_in.photos,
        location=request_in.location,
        latitude=request_in.latitude,
        longitude=request_in.longitude,
        scheduled_at=request_in.scheduled_at,
        urgency=request_in.urgency.value,
        status="open",
    )
    db.add(new_request)
    await db.flush()
    await db.refresh(new_request)
    return new_request


@router.get("/", response_model=List[ServiceRequestResponse])
async def read_my_requests(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List current user's service requests."""
    result = await db.execute(
        select(ServiceRequest)
        .where(ServiceRequest.customer_id == current_user.id)
        .order_by(ServiceRequest.created_at.desc())
    )
    return result.scalars().all()


@router.get("/open", response_model=List[ServiceRequestResponse])
async def read_open_requests(
    category: str = None,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List open service requests (for professionals to browse)."""
    query = select(ServiceRequest).where(ServiceRequest.status == "open")
    if category:
        query = query.where(ServiceRequest.category_id == category)
    query = query.order_by(ServiceRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{request_id}", response_model=ServiceRequestResponse)
async def read_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific service request."""
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.get("/{request_id}/matches", response_model=List[ProProfile])
async def get_matched_professionals(
    request_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """AI-powered smart matching for service requests.
    
    Scores professionals based on:
    1. Keyword relevance (description vs bio/skills) — 40%
    2. Rating score — 25%
    3. Availability overlap — 20%
    4. Experience (completed jobs) — 15%
    
    Returns sorted by match_score descending.
    """
    # Get the request
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    service_request = result.scalar_one_or_none()
    if not service_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Find professionals in the same category
    query = select(User).where(
        and_(
            User.role == "pro",
            User.is_active == True,
            User.service_category == service_request.category_id,
        )
    )
    result = await db.execute(query)
    professionals = result.scalars().all()

    # AI scoring helper
    def compute_keyword_score(description: str, bio: str) -> tuple[float, list[str]]:
        """Score keyword overlap between request description and pro bio."""
        if not description or not bio:
            return 0.0, []
        
        # Common service keywords to match against
        service_keywords = {
            "leak", "pipe", "faucet", "drain", "tap", "sink", "toilet", "shower",
            "wire", "switch", "socket", "light", "fan", "circuit", "board", "mcb",
            "paint", "wall", "ceiling", "waterproof", "primer", "color",
            "clean", "deep", "kitchen", "bathroom", "floor", "carpet", "sofa",
            "ac", "cooling", "gas", "compressor", "filter", "split", "window",
            "pest", "cockroach", "termite", "rat", "mosquito", "bug",
            "wood", "furniture", "door", "cabinet", "shelf", "table",
            "hair", "facial", "makeup", "spa", "massage", "nail", "wax",
            "repair", "install", "fix", "replace", "maintain", "service",
            "urgent", "emergency", "quick", "fast", "today", "asap",
        }
        
        desc_words = set(description.lower().split())
        bio_words = set(bio.lower().split())
        
        # Find matching keywords
        desc_keywords = desc_words & service_keywords
        bio_keywords = bio_words & service_keywords
        matched = desc_keywords & bio_keywords
        
        # Also check for direct word overlap (beyond keywords)
        direct_overlap = desc_words & bio_words - {"a", "an", "the", "is", "are", "in", "on", "at", "to", "for", "and", "or", "i", "my", "can", "you"}
        
        if not desc_keywords:
            return min(len(direct_overlap) * 15, 100), list(matched | direct_overlap)[:3]
        
        score = (len(matched) / max(len(desc_keywords), 1)) * 100
        return min(score, 100), list(matched | direct_overlap)[:3]

    # Build scored profiles
    profiles = []
    for pro in professionals:
        # 1. Keyword score (40%)
        keyword_score, matched_keywords = compute_keyword_score(
            service_request.description or service_request.title,
            pro.bio or ""
        )

        # 2. Rating score (25%) 
        rating_result = await db.execute(
            select(func.avg(Review.rating), func.count(Review.id))
            .where(Review.reviewee_id == pro.id)
        )
        row = rating_result.one()
        avg_rating = float(row[0]) if row[0] else 0.0
        reviews_count = row[1]
        rating_score = (avg_rating / 5.0) * 100 if avg_rating > 0 else 50  # Default 50 for new pros

        # 3. Availability score (20%)
        avail_result = await db.execute(
            select(func.count(Availability.id)).where(
                and_(
                    Availability.professional_id == pro.id,
                    Availability.is_booked == False,
                )
            )
        )
        avail_count = avail_result.scalar() or 0
        availability_score = min(avail_count * 33, 100)  # 3+ slots = full score

        # 4. Experience score (15%)
        jobs_result = await db.execute(
            select(func.count(Booking.id))
            .where(Booking.professional_id == pro.id, Booking.status == "completed")
        )
        jobs_completed = jobs_result.scalar() or 0
        experience_score = min(jobs_completed * 20, 100)  # 5+ jobs = full score

        # Weighted total
        total_score = (
            keyword_score * 0.40 +
            rating_score * 0.25 +
            availability_score * 0.20 +
            experience_score * 0.15
        )

        # Build match reason
        reasons = []
        if avg_rating > 0:
            reasons.append(f"⭐ {avg_rating:.1f} rated")
        if jobs_completed > 0:
            reasons.append(f"{jobs_completed} job{'s' if jobs_completed > 1 else ''} done")
        if matched_keywords:
            reasons.append(f"Expert in {', '.join(matched_keywords[:2])}")
        if avail_count > 0:
            reasons.append("Available now")
        if not reasons:
            reasons.append("Category match")

        profiles.append(ProProfile(
            id=pro.id,
            email=pro.email,
            full_name=pro.full_name,
            phone=pro.phone,
            role=pro.role,
            service_category=pro.service_category,
            bio=pro.bio,
            address=pro.address,
            is_active=pro.is_active,
            created_at=pro.created_at,
            rating=round(avg_rating, 1),
            jobs_completed=jobs_completed,
            reviews_count=reviews_count,
            match_score=round(total_score, 1),
            match_reason=" · ".join(reasons),
        ))

    # Sort by score descending
    profiles.sort(key=lambda p: p.match_score or 0, reverse=True)
    return profiles


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
async def update_request(
    request_id: str,
    update: ServiceRequestUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update a service request."""
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    service_request = result.scalar_one_or_none()
    if not service_request:
        raise HTTPException(status_code=404, detail="Request not found")

    if service_request.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service_request, field, value)

    await db.flush()
    await db.refresh(service_request)
    return service_request
