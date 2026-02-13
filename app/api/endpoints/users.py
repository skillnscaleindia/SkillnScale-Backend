from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import UserResponse, UserUpdate, ProProfile
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, Review, Booking

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get current user."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update current user profile."""
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=ProProfile)
async def read_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a user's public profile (mainly for viewing pros)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate rating and jobs completed
    rating_result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.reviewee_id == user_id)
    )
    row = rating_result.one()
    avg_rating = float(row[0]) if row[0] else 0.0
    reviews_count = row[1]

    jobs_result = await db.execute(
        select(func.count(Booking.id))
        .where(Booking.professional_id == user_id, Booking.status == "completed")
    )
    jobs_completed = jobs_result.scalar() or 0

    return ProProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        service_category=user.service_category,
        bio=user.bio,
        address=user.address,
        is_active=user.is_active,
        created_at=user.created_at,
        rating=round(avg_rating, 1),
        jobs_completed=jobs_completed,
        reviews_count=reviews_count,
    )
