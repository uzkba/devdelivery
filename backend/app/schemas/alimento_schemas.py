import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = None
    preco_base: Decimal
    categoria_id: uuid.UUID

    @field_validator("preco_base")
    @classmethod
    def preco_nao_negativo(cls, v):
        if v < 0:
            raise ValueError("preco_base não pode ser negativo")
        return v


class AlimentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    preco_base: Optional[Decimal] = None
    categoria_id: Optional[uuid.UUID] = None

    @field_validator("preco_base")
    @classmethod
    def preco_nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("preco_base não pode ser negativo")
        return v


class AlimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    descricao: Optional[str]
    preco_base: Decimal
    categoria_id: uuid.UUID
    ativo: bool
    disponivel: bool