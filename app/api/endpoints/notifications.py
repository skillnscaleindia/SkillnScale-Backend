from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.database import get_db
from app.db.db_models import User, DeviceToken
from app.models.notification import DeviceTokenCreate, DeviceTokenResponse

router = APIRouter()

@router.post("/device-token", response_model=DeviceTokenResponse)
async def register_device_token(
    token_in: DeviceTokenCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a device token for push notifications."""
    # Check if token exists
    result = await db.execute(select(DeviceToken).where(DeviceToken.token == token_in.token))
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update user if different
        if existing.user_id != current_user.id:
            existing.user_id = current_user.id
            await db.flush()
        return existing

    # Create new token
    device_token = DeviceToken(
        user_id=current_user.id,
        token=token_in.token,
        platform=token_in.platform,
    )
    db.add(device_token)
    await db.flush()
    await db.refresh(device_token)
    return device_token
