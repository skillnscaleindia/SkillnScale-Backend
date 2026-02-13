from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core import security
from app.models.user import Token, User, UserCreate, UserLogin
from app.db.mock_db import db

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = None
    for u in db.users:
        if u["email"] == form_data.username:
            user = u
            break
    
    if not user or not security.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user["id"], expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
    
@router.post("/login/json", response_model=Token)
def login_json(user_in: UserLogin) -> Any:
    """
    JSON based login for Flutter Mobile
    """
    user = None
    for u in db.users:
        if u["email"] == user_in.email:
            user = u
            break
            
    if not user or not security.verify_password(user_in.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    return {
        "access_token": security.create_access_token(user["id"]),
        "token_type": "bearer",
    }

@router.post("/signup", response_model=User)
def create_user(user_in: UserCreate) -> Any:
    """
    Create new user without the need for authentication
    """
    for u in db.users:
        if u["email"] == user_in.email:
            raise HTTPException(
                status_code=400,
                detail="The user with this username already exists in the system.",
            )
            
    new_user = user_in.model_dump()
    new_user["id"] = len(db.users) + 1
    new_user["password_hash"] = security.get_password_hash(user_in.password)
    del new_user["password"]
    
    db.users.append(new_user)
    return new_user
