from pydantic import BaseModel
from typing import List, Optional

class ServiceCategory(BaseModel):
    id: str
    name: str
    icon: str
    color: str

class ServiceItem(BaseModel):
    id: str
    name: str
    price: float
    description: Optional[str] = None
    category_id: str
