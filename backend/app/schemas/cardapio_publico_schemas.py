import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.model.models import MealBoxKind


class MarmitaCardOut(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None = None
    tipo: MealBoxKind
    tamanho: str | None = None
    preco: Decimal
    imagem_url: str | None = None
    destaque: bool


class ComboCardOut(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None = None
    preco: Decimal
    preco_referencia: Decimal | None = None
    imagem_url: str | None = None
    destaque: bool


class ProdutoCardOut(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None = None
    preco: Decimal
    imagem_url: str | None = None
    destaque: bool


class CategoriaSecaoOut(BaseModel):
    id: uuid.UUID
    nome: str
    itens: list[ProdutoCardOut]


class SecaoOut(BaseModel):
    grupo: Literal["prato", "bebida"]
    categorias: list[CategoriaSecaoOut]


class CardapioHomeOut(BaseModel):
    marmitas: list[MarmitaCardOut]
    combos: list[ComboCardOut]
    secoes: list[SecaoOut]