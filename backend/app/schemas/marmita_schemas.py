from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.model.models import MealBoxKind

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Descricao = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Preco = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


# ---------------------------- entrada ----------------------------
class MarmitaCategoriaIn(BaseModel):
    categoria_alimento_id: uuid.UUID
    quantidade_exigida: int = Field(ge=0, le=50)  # zero e permitido


class MarmitaComposicaoIn(BaseModel):
    alimento_id: uuid.UUID
    quantidade_fixa: int = Field(ge=1, le=50)


class MarmitaIn(BaseModel):
    nome: Nome
    descricao: Descricao | None = None
    tipo: MealBoxKind
    tamanho: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    preco: Preco
    ativo: bool = True
    destaque: bool = False

    # informacao nutricional opcional
    calorias_kcal: int | None = Field(default=None, ge=0, le=10000)
    proteina_g: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=1)
    carboidrato_g: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=1)
    gordura_g: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=1)

    categorias: list[MarmitaCategoriaIn] = Field(default_factory=list)
    composicao: list[MarmitaComposicaoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_tipo(self) -> "MarmitaIn":
        if self.tipo == MealBoxKind.CUSTOMIZABLE:
            if self.composicao:
                raise ValueError(
                    "Marmita personalizável não pode ter composição fixa."
                )
            if not self.categorias:
                raise ValueError(
                    "Marmita personalizável precisa de ao menos uma categoria."
                )
            ids = [c.categoria_alimento_id for c in self.categorias]
            if len(ids) != len(set(ids)):
                raise ValueError("Categoria repetida na marmita.")
            if sum(c.quantidade_exigida for c in self.categorias) == 0:
                raise ValueError(
                    "Ao menos uma categoria deve ter quantidade maior que zero."
                )
        else:  # PRONTA
            if self.categorias:
                raise ValueError(
                    "Marmita pronta não usa categorias; informe a composição fixa."
                )
            if not self.composicao:
                raise ValueError(
                    "Marmita pronta precisa de ao menos um alimento na composição."
                )
            ids = [c.alimento_id for c in self.composicao]
            if len(ids) != len(set(ids)):
                raise ValueError("Alimento repetido na composição.")
        return self


class AtivoIn(BaseModel):
    ativo: bool


# ----------------------------- saida -----------------------------
class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MarmitaCategoriaOut(_Out):
    categoria_alimento_id: uuid.UUID = Field(validation_alias="food_category_id")
    categoria_nome: str = Field(validation_alias="food_category_name")
    quantidade_exigida: int = Field(validation_alias="required_quantity")


class MarmitaComposicaoOut(_Out):
    alimento_id: uuid.UUID = Field(validation_alias="food_id")
    alimento_nome: str = Field(validation_alias="food_name")
    quantidade_fixa: int = Field(validation_alias="fixed_quantity")


class MarmitaResumoOut(_Out):
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    tipo: MealBoxKind = Field(validation_alias="kind")
    tamanho: str | None = Field(default=None, validation_alias="size")
    preco: Decimal = Field(validation_alias="price")
    ativo: bool = Field(validation_alias="is_active")
    destaque: bool = Field(validation_alias="is_featured")
    imagem_url: str | None = Field(default=None, validation_alias="image_url")
    serve_hoje: bool = Field(validation_alias="serves_today")
    esgotado_hoje: bool = Field(validation_alias="sold_out_today")


class MarmitaOut(MarmitaResumoOut):
    descricao: str | None = Field(default=None, validation_alias="description")
    calorias_kcal: int | None = Field(default=None, validation_alias="calories_kcal")
    proteina_g: Decimal | None = Field(default=None, validation_alias="protein_g")
    carboidrato_g: Decimal | None = Field(default=None, validation_alias="carbs_g")
    gordura_g: Decimal | None = Field(default=None, validation_alias="fat_g")
    categorias: list[MarmitaCategoriaOut] = Field(default_factory=list, validation_alias="categories")
    composicao: list[MarmitaComposicaoOut] = Field(default_factory=list, validation_alias="composition")


class MarmitaListOut(BaseModel):
    itens: list[MarmitaResumoOut]
    total: int