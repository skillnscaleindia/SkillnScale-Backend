from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.api import deps

router = APIRouter()

@router.get("/me", response_model=User)
def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
