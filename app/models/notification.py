from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeviceTokenCreate(BaseModel):
    token: str
    platform: str

class DeviceTokenResponse(BaseModel):
    id: str
    user_id: str
    token: str
    platform: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Notification(BaseModel):
    title: str
    body: str
    data: Optional[dict] = None
