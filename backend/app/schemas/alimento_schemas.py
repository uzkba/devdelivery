import uuid
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ── Complementos (LEGADO: remover na limpeza final) ──────────────────────────
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


# ── Regra do produto avulso (compartilhada com o service no PUT) ─────────────
def validar_regras_avulso(
    vendavel: bool,
    preco_avulso: Optional[Decimal],
    categoria_venda_id: Optional[uuid.UUID],
    categoria_composicao_id: Optional[uuid.UUID],
) -> None:
    """Levanta ValueError se o estado do alimento for inválido.
    - vendavel_avulso=True exige preco_avulso e categoria_venda_id
    - vendavel_avulso=False não pode ter nenhum dos dois
    - precisa ter ao menos uma categoria (composição e/ou venda)"""
    if vendavel:
        if preco_avulso is None or categoria_venda_id is None:
            raise ValueError("Produto avulso exige preco_avulso e categoria_venda_id.")
    elif preco_avulso is not None or categoria_venda_id is not None:
        raise ValueError("preco_avulso e categoria_venda_id só são permitidos quando vendavel_avulso=true.")
    if categoria_composicao_id is None and categoria_venda_id is None:
        raise ValueError("Informe categoria_id (composição) e/ou categoria_venda_id.")


# ── Alimento ─────────────────────────────────────────────────────────────────
class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = None
    preco_base: Decimal = Decimal("0")  # LEGADO: avulso puro não precisa informar
    categoria_id: Optional[uuid.UUID] = None  # categoria de composição
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: bool = False
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: bool = False
    grupos_complemento: Optional[List[ModifierGroupCreate]] = None  # LEGADO

    @field_validator("preco_base")
    @classmethod
    def preco_nao_negativo(cls, v):
        if v < 0:
            raise ValueError("preco_base não pode ser negativo")
        return v

    @model_validator(mode="after")
    def validar_avulso(self):
        validar_regras_avulso(
            self.vendavel_avulso, self.preco_avulso, self.categoria_venda_id, self.categoria_id
        )
        return self


class AlimentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    preco_base: Optional[Decimal] = None
    categoria_id: Optional[uuid.UUID] = None
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: Optional[bool] = None
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: Optional[bool] = None

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
    categoria_id: Optional[uuid.UUID] = Field(default=None, validation_alias="category_id")
    categoria_venda_id: Optional[uuid.UUID] = Field(default=None, validation_alias="sale_category_id")
    vendavel_avulso: bool = Field(validation_alias="is_sellable_alone")
    preco_avulso: Optional[Decimal] = Field(default=None, validation_alias="standalone_price")
    destaque: bool = Field(validation_alias="is_featured")
    imagem_url: Optional[str] = Field(default=None, validation_alias="image_url")
    ativo: bool = Field(validation_alias="is_active")
    disponivel: bool = Field(validation_alias="is_available")
    grupos_complemento: List[ModifierGroupOut] = Field(default=[], validation_alias="modifier_groups")