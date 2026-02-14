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
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str = "customer"
    profile_photo: Optional[str] = None
    documents: List[str] = []

class UserCreate(UserBase):
    password: str
    phone: str
    service_category: Optional[str] = None

class CustomerCreate(BaseModel):
    phone: str
    password: str
    full_name: str
    email: Optional[EmailStr] = None
    delivery_method: str = "sms"  # "sms" or "whatsapp"

class ProfessionalCreate(BaseModel):
    phone: str
    password: str
    full_name: str
    service_category: str
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    delivery_method: str = "sms"  # "sms" or "whatsapp"

class OTPVerify(BaseModel):
    phone: str
    otp_code: str

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

class AuthResponse(BaseModel):
    user: UserResponse
    tokens: Token

class UserLogin(BaseModel):
    phone: str
    password: str

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
