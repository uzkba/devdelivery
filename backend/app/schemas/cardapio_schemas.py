import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MenuItemAvailabilityUpdate(BaseModel):
    """Corpo do PATCH que altera a disponibilidade de um item do cardápio do dia."""
    is_available: bool


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    food_id: uuid.UUID
    is_available: bool
    day_price: Decimal | None