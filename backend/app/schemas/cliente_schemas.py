# backend/app/schemas/cliente_schemas.py
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

class ClienteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=8, max_length=20)

class ClienteOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)