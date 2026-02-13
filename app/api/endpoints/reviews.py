from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat import ReviewCreate, ReviewResponse
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, Review, Booking

router = APIRouter()


@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_in: ReviewCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit a review for a completed booking."""
    # Verify booking exists and is completed
    result = await db.execute(select(Booking).where(Booking.id == review_in.booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")

    # Determine reviewee
    if current_user.id == booking.customer_id:
        reviewee_id = booking.professional_id
    elif current_user.id == booking.professional_id:
        reviewee_id = booking.customer_id
    else:
        raise HTTPException(status_code=403, detail="Not authorized to review this booking")

    # Check for existing review
    existing = await db.execute(
        select(Review).where(
            Review.booking_id == review_in.booking_id,
            Review.reviewer_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already reviewed this booking")

    # Validate rating
    if not 1 <= review_in.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = Review(
        booking_id=review_in.booking_id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    return ReviewResponse(
        id=review.id,
        booking_id=review.booking_id,
        reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        reviewer_name=current_user.full_name,
    )


@router.get("/{user_id}", response_model=List[ReviewResponse])
async def get_user_reviews(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get reviews for a user (mainly for professionals)."""
    result = await db.execute(
        select(Review)
        .where(Review.reviewee_id == user_id)
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()

    responses = []
    for review in reviews:
        # Get reviewer name
        reviewer_result = await db.execute(select(User).where(User.id == review.reviewer_id))
        reviewer = reviewer_result.scalar_one_or_none()
        responses.append(ReviewResponse(
            id=review.id,
            booking_id=review.booking_id,
            reviewer_id=review.reviewer_id,
            reviewee_id=review.reviewee_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            reviewer_name=reviewer.full_name if reviewer else None,
        ))
    return responses
