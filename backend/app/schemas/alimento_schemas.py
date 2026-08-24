import uuid
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ModifierOptionCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60)
    preco_adicional: Decimal = Field(default=Decimal("0.00"))
    disponivel: bool = True

    @field_validator("preco_adicional")
    @classmethod
    def preco_nao_negativo(cls, v):
        if v < 0:
            raise ValueError("preco_adicional não pode ser negativo")
        return v

class ModifierOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    preco_adicional: Decimal = Field(validation_alias="extra_price")
    disponivel: bool = Field(validation_alias="is_available")


class ModifierGroupCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60)
    escolhas_minimas: int = Field(default=0, ge=0)
    escolhas_maximas: int = Field(..., gt=0)
    opcoes: List[ModifierOptionCreate] = []

    @field_validator("escolhas_maximas")
    @classmethod
    def validar_limites(cls, v, info):
        valores = info.data
        if "escolhas_minimas" in valores and v < valores["escolhas_minimas"]:
            raise ValueError("escolhas_maximas deve ser maior ou igual a escolhas_minimas")
        return v

class ModifierGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    escolhas_minimas: int = Field(validation_alias="min_choices")
    escolhas_maximas: int = Field(validation_alias="max_choices")
    opcoes: List[ModifierOptionOut] = Field(default=[], validation_alias="options")

class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = None
    preco_base: Decimal
    categoria_id: uuid.UUID
    grupos_complemento: Optional[List[ModifierGroupCreate]] = None

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
    nome: str = Field(validation_alias="name")
    descricao: Optional[str] = Field(default=None, validation_alias="description")
    preco_base: Decimal = Field(validation_alias="base_price")
    categoria_id: uuid.UUID = Field(validation_alias="category_id")
    ativo: bool = Field(validation_alias="is_active")
    disponivel: bool = Field(validation_alias="is_available")
    grupos_complemento: List[ModifierGroupOut] = Field(default=[], validation_alias="modifier_groups")