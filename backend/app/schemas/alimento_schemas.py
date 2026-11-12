import uuid
from decimal import Decimal
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


def validar_regras_avulso(
    vendavel: bool,
    preco_avulso: Optional[Decimal],
    categoria_venda_id: Optional[uuid.UUID],
    categoria_composicao_id: Optional[uuid.UUID],
) -> None:
    if vendavel:
        if preco_avulso is None or categoria_venda_id is None:
            raise ValueError("Produto avulso exige preco_avulso e categoria_venda_id.")
    elif preco_avulso is not None or categoria_venda_id is not None:
        raise ValueError("preco_avulso e categoria_venda_id só são permitidos quando vendavel_avulso=true.")
    if categoria_composicao_id is None and categoria_venda_id is None:
        raise ValueError("Informe categoria_id (composição) e/ou categoria_venda_id.")


class UnidadePorcao(str, Enum):
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"


MAX_COMPONENTES = 10

ServePessoas = Annotated[int, Field(ge=1, le=50)]
TempoPreparo = Annotated[int, Field(ge=1, le=480)]
PorcaoQuantidade = Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)]
Calorias = Annotated[int, Field(ge=0, le=10000)]
Macro = Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=1)]


def validar_porcao(quantidade: Optional[Decimal], unidade: Optional[UnidadePorcao]) -> None:
    if (quantidade is None) != (unidade is None):
        raise ValueError("porcao_quantidade e porcao_unidade devem ser informadas juntas.")


class ComponenteIn(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    descricao: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]] = None

    @field_validator("descricao")
    @classmethod
    def descricao_vazia_vira_nulo(cls, v):
        return v or None


class ComponenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nome: str = Field(validation_alias="name")
    descricao: Optional[str] = Field(default=None, validation_alias="description")


class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=300)
    categoria_id: Optional[uuid.UUID] = None
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: bool = False
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: bool = False

    serve_pessoas: Optional[ServePessoas] = None
    porcao_quantidade: Optional[PorcaoQuantidade] = None
    porcao_unidade: Optional[UnidadePorcao] = None
    tempo_preparo_minutos: Optional[TempoPreparo] = None
    calorias_kcal: Optional[Calorias] = None
    proteina_g: Optional[Macro] = None
    carboidrato_g: Optional[Macro] = None
    gordura_g: Optional[Macro] = None
    componentes: List[ComponenteIn] = Field(default_factory=list, max_length=MAX_COMPONENTES)

    @model_validator(mode="after")
    def validar_avulso(self):
        validar_regras_avulso(
            self.vendavel_avulso, self.preco_avulso, self.categoria_venda_id, self.categoria_id
        )
        validar_porcao(self.porcao_quantidade, self.porcao_unidade)
        return self


class AlimentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=300)
    categoria_id: Optional[uuid.UUID] = None
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: Optional[bool] = None
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: Optional[bool] = None

    serve_pessoas: Optional[ServePessoas] = None
    porcao_quantidade: Optional[PorcaoQuantidade] = None
    porcao_unidade: Optional[UnidadePorcao] = None
    tempo_preparo_minutos: Optional[TempoPreparo] = None
    calorias_kcal: Optional[Calorias] = None
    proteina_g: Optional[Macro] = None
    carboidrato_g: Optional[Macro] = None
    gordura_g: Optional[Macro] = None
    componentes: Optional[List[ComponenteIn]] = Field(None, max_length=MAX_COMPONENTES)

    @field_validator("componentes")
    @classmethod
    def componentes_nao_nulo(cls, v):
        if v is None:
            raise ValueError("componentes não pode ser null; envie [] para limpar a lista.")
        return v


class AlimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    descricao: Optional[str] = Field(default=None, validation_alias="description")
    categoria_id: Optional[uuid.UUID] = Field(default=None, validation_alias="composition_category_id")
    categoria_venda_id: Optional[uuid.UUID] = Field(default=None, validation_alias="sale_category_id")
    vendavel_avulso: bool = Field(validation_alias="is_sellable_alone")
    preco_avulso: Optional[Decimal] = Field(default=None, validation_alias="standalone_price")
    destaque: bool = Field(validation_alias="is_featured")
    imagem_url: Optional[str] = Field(default=None, validation_alias="image_url")
    ativo: bool = Field(validation_alias="is_active")
    serve_pessoas: Optional[int] = Field(default=None, validation_alias="serves_people")
    porcao_quantidade: Optional[Decimal] = Field(default=None, validation_alias="portion_amount")
    porcao_unidade: Optional[UnidadePorcao] = Field(default=None, validation_alias="portion_unit")
    tempo_preparo_minutos: Optional[int] = Field(default=None, validation_alias="prep_time_minutes")
    calorias_kcal: Optional[int] = Field(default=None, validation_alias="calories_kcal")
    proteina_g: Optional[Decimal] = Field(default=None, validation_alias="protein_g")
    carboidrato_g: Optional[Decimal] = Field(default=None, validation_alias="carbs_g")
    gordura_g: Optional[Decimal] = Field(default=None, validation_alias="fat_g")
    componentes: List[ComponenteOut] = Field(default=[], validation_alias="components")
    serve_hoje: bool = Field(validation_alias="serves_today")
    esgotado_hoje: bool = Field(validation_alias="sold_out_today")