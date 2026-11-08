import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.model.models import MealBoxKind

MotivoIndisponivel = Literal["fora_do_dia", "esgotado_hoje", "item_indisponivel", "sem_opcoes"]


class NutricaoOut(BaseModel):
    calorias_kcal: int | None = None
    proteina_g: Decimal | None = None
    carboidrato_g: Decimal | None = None
    gordura_g: Decimal | None = None


class _DetalheBase(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None = None
    preco: Decimal
    imagem_url: str | None = None
    disponivel: bool
    motivo_indisponivel: MotivoIndisponivel | None = None


# ------------------------------ marmita ------------------------------
class ComposicaoItemOut(BaseModel):
    alimento_id: uuid.UUID
    nome: str
    descricao: str | None = None
    quantidade: int


class OpcaoOut(BaseModel):
    alimento_id: uuid.UUID
    nome: str
    descricao: str | None = None
    imagem_url: str | None = None


class CategoriaEscolhaOut(BaseModel):
    categoria_id: uuid.UUID
    nome: str
    quantidade_exigida: int
    opcoes: list[OpcaoOut]


class MarmitaDetalheOut(_DetalheBase):
    tipo: MealBoxKind
    tamanho: str | None = None
    nutricao: NutricaoOut | None = None
    composicao: list[ComposicaoItemOut]
    categorias: list[CategoriaEscolhaOut]


# ------------------------------ combo ------------------------------
class ComboItemMarmitaOut(BaseModel):
    marmita_id: uuid.UUID
    nome: str
    tipo: MealBoxKind
    quantidade: int


class ComboItemAlimentoOut(BaseModel):
    alimento_id: uuid.UUID
    nome: str
    quantidade: int


class ComboDetalheOut(_DetalheBase):
    preco_referencia: Decimal | None = None
    economia: Decimal | None = None
    possui_marmita_personalizavel: bool
    itens_marmita: list[ComboItemMarmitaOut]
    itens_alimento: list[ComboItemAlimentoOut]


# ------------------------------ produto avulso ------------------------------
class CategoriaProdutoOut(BaseModel):
    id: uuid.UUID
    nome: str


class PorcaoOut(BaseModel):
    quantidade: Decimal
    unidade: str


class ComponenteOut(BaseModel):
    nome: str
    descricao: str | None = None


class ProdutoDetalheOut(_DetalheBase):
    grupo: Literal["prato", "bebida"]
    categoria: CategoriaProdutoOut
    serve_pessoas: int | None = None
    porcao: PorcaoOut | None = None
    tempo_preparo_minutos: int | None = None
    nutricao: NutricaoOut | None = None
    componentes: list[ComponenteOut]