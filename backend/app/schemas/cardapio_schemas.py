import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class MenuItemAvailabilityUpdate(BaseModel):
    is_available: bool

class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    food_id: uuid.UUID
    is_available: bool
    day_price: Decimal | None

class CardapioCreate(BaseModel):
    data: date

class CardapioItemCreate(BaseModel):
    alimento_id: uuid.UUID
    # REMOVIDO: tamanho_id
    preco_dia: Optional[Decimal] = None
    disponivel: bool = True

    @field_validator("preco_dia")
    @classmethod
    def preco_dia_nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("preco_dia nÃ£o pode ser negativo")
        return v

class CardapioItensCreate(BaseModel):
    itens: List[CardapioItemCreate] = Field(..., min_length=1)

class CardapioItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alimento_id: uuid.UUID
    # REMOVIDO: tamanho_id
    disponivel: bool
    preco_dia: Optional[Decimal]

    @classmethod
    def from_model(cls, item) -> "CardapioItemResponse":
        return cls(
            id=item.id,
            alimento_id=item.food_id,
            disponivel=item.is_available,
            preco_dia=item.day_price,
        )

class CardapioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurante_id: uuid.UUID
    data: date
    criado_por: Optional[uuid.UUID]
    criado_em: datetime
    itens: List[CardapioItemResponse] = []

    @classmethod
    def from_model(cls, cardapio) -> "CardapioResponse":
        return cls(
            id=cardapio.id,
            restaurante_id=cardapio.restaurant_id,
            data=cardapio.date,
            criado_por=cardapio.created_by,
            criado_em=cardapio.created_at,
            itens=[CardapioItemResponse.from_model(i) for i in cardapio.items],
        )