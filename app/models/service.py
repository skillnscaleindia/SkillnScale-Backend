from pydantic import BaseModel
from typing import List, Optional

class ServiceCategoryResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
