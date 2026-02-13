from typing import Any, List
from fastapi import APIRouter, Depends
from app.models.service import ServiceCategory, ServiceItem
from app.db.mock_db import db

router = APIRouter()

@router.get("/categories", response_model=List[ServiceCategory])
def read_service_categories() -> Any:
    """
    Retrieve service categories.
    """
    return db.services

@router.get("/popular", response_model=List[ServiceCategory])
def read_popular_services() -> Any:
    """
    Retrieve popular services (mock logic: just return first 2).
    """
    return db.services[:2]
