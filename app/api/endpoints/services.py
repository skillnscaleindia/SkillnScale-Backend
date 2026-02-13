from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.service import ServiceCategoryResponse
from app.db.database import get_db
from app.db.db_models import ServiceCategory

router = APIRouter()


@router.get("/categories", response_model=List[ServiceCategoryResponse])
async def read_service_categories(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve service categories."""
    result = await db.execute(select(ServiceCategory))
    return result.scalars().all()


@router.get("/popular", response_model=List[ServiceCategoryResponse])
async def read_popular_services(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve popular services (first 4)."""
    result = await db.execute(select(ServiceCategory).limit(4))
    return result.scalars().all()
