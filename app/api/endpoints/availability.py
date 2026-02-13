from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat import AvailabilityCreate, AvailabilityResponse, AvailabilityUpdate
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, Availability

router = APIRouter()


@router.post("/", response_model=AvailabilityResponse)
async def create_availability(
    slot_in: AvailabilityCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Professional creates a time slot."""
    if current_user.role != "pro":
        raise HTTPException(status_code=400, detail="Only professionals can set availability")

    slot = Availability(
        professional_id=current_user.id,
        date=slot_in.date,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        is_recurring=slot_in.is_recurring,
        recurrence_pattern=slot_in.recurrence_pattern,
    )
    db.add(slot)
    await db.flush()
    await db.refresh(slot)
    return slot


@router.get("/me", response_model=List[AvailabilityResponse])
async def read_my_availability(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get own availability slots."""
    result = await db.execute(
        select(Availability)
        .where(Availability.professional_id == current_user.id)
        .order_by(Availability.date, Availability.start_time)
    )
    return result.scalars().all()


@router.get("/{pro_id}", response_model=List[AvailabilityResponse])
async def read_professional_availability(
    pro_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a professional's public availability."""
    result = await db.execute(
        select(Availability)
        .where(
            Availability.professional_id == pro_id,
            Availability.is_booked == False,
        )
        .order_by(Availability.date, Availability.start_time)
    )
    return result.scalars().all()


@router.put("/{slot_id}", response_model=AvailabilityResponse)
async def update_availability(
    slot_id: str,
    update: AvailabilityUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an availability slot."""
    result = await db.execute(select(Availability).where(Availability.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.professional_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slot, field, value)

    await db.flush()
    await db.refresh(slot)
    return slot


@router.delete("/{slot_id}")
async def delete_availability(
    slot_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete an availability slot."""
    result = await db.execute(select(Availability).where(Availability.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.professional_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(slot)
    return {"message": "Slot deleted"}
