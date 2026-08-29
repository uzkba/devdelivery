from datetime import date as date_type
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

class MenuItemUpdate(BaseModel):
    is_available: Optional[bool] = None
    day_price: Optional[Decimal] = None

class MenuCreate(BaseModel):
    data: date_type