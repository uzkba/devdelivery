import uuid
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional, List
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator, ConfigDict

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


# ── Campos opcionais do produto avulso ───────────────────────────────────────
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
    """Quantidade e unidade da porção são preenchidas juntas ou ficam ambas nulas."""
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


# ── Alimento ─────────────────────────────────────────────────────────────────
class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=300)
    preco_base: Decimal = Decimal("0")  # LEGADO: avulso puro não precisa informar
    categoria_id: Optional[uuid.UUID] = None  # categoria de composição
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: bool = False
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: bool = False
    grupos_complemento: Optional[List[ModifierGroupCreate]] = None  # LEGADO

    # informações opcionais
    serve_pessoas: Optional[ServePessoas] = None
    porcao_quantidade: Optional[PorcaoQuantidade] = None
    porcao_unidade: Optional[UnidadePorcao] = None
    tempo_preparo_minutos: Optional[TempoPreparo] = None
    calorias_kcal: Optional[Calorias] = None
    proteina_g: Optional[Macro] = None
    carboidrato_g: Optional[Macro] = None
    gordura_g: Optional[Macro] = None
    componentes: List[ComponenteIn] = Field(default_factory=list, max_length=MAX_COMPONENTES)

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
        validar_porcao(self.porcao_quantidade, self.porcao_unidade)
        return self


class AlimentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=300)
    preco_base: Optional[Decimal] = None
    categoria_id: Optional[uuid.UUID] = None
    categoria_venda_id: Optional[uuid.UUID] = None
    vendavel_avulso: Optional[bool] = None
    preco_avulso: Optional[Decimal] = Field(None, ge=0)
    destaque: Optional[bool] = None

    # informações opcionais: null explícito limpa o campo; ausente preserva
    serve_pessoas: Optional[ServePessoas] = None
    porcao_quantidade: Optional[PorcaoQuantidade] = None
    porcao_unidade: Optional[UnidadePorcao] = None
    tempo_preparo_minutos: Optional[TempoPreparo] = None
    calorias_kcal: Optional[Calorias] = None
    proteina_g: Optional[Macro] = None
    carboidrato_g: Optional[Macro] = None
    gordura_g: Optional[Macro] = None
    # presente (mesmo []) substitui a lista inteira; ausente preserva
    componentes: Optional[List[ComponenteIn]] = Field(None, max_length=MAX_COMPONENTES)

    @field_validator("preco_base")
    @classmethod
    def preco_nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("preco_base não pode ser negativo")
        return v

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

    serve_pessoas: Optional[int] = Field(default=None, validation_alias="serves_people")
    porcao_quantidade: Optional[Decimal] = Field(default=None, validation_alias="portion_amount")
    porcao_unidade: Optional[UnidadePorcao] = Field(default=None, validation_alias="portion_unit")
    tempo_preparo_minutos: Optional[int] = Field(default=None, validation_alias="prep_time_minutes")
    calorias_kcal: Optional[int] = Field(default=None, validation_alias="calories_kcal")
    proteina_g: Optional[Decimal] = Field(default=None, validation_alias="protein_g")
    carboidrato_g: Optional[Decimal] = Field(default=None, validation_alias="carbs_g")
    gordura_g: Optional[Decimal] = Field(default=None, validation_alias="fat_g")
    componentes: List[ComponenteOut] = Field(default=[], validation_alias="components")