import uuid

from typing import Optional
from pydantic import BaseModel, ConfigDict


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    trade_name: str
    phone: Optional[str] = None
    is_active: bool
