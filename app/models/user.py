from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "customer"
    profile_photo: Optional[str] = None
    documents: List[str] = []

class UserCreate(UserBase):
    password: str
    phone: Optional[str] = None
    service_category: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    phone: Optional[str] = None
    service_category: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Pro Specific
class ProProfile(UserResponse):
    rating: float = 0.0
    jobs_completed: int = 0
    reviews_count: int = 0
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
