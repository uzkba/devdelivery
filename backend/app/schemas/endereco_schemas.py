import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnderecoCreate(BaseModel):
    street: str
    number: str
    neighborhood: str
    complement: str | None = None
    reference_point: str | None = None
    primary_address: bool = False


class EnderecoOut(EnderecoCreate):
    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnderecoUpdate(BaseModel):
    street: str | None = None
    number: str | None = None
    neighborhood: str | None = None
    complement: str | None = None
    reference_point: str | None = None
    primary_address: bool | None = None