"""NexusDelivery - Fase 1: schemas de combo."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.model.models import MealBoxKind
from app.schemas.marmita_schemas import Descricao, Nome, Preco


# ---------------------------- entrada ----------------------------
class ComboItemMarmitaIn(BaseModel):
    marmita_id: uuid.UUID
    # Em marmita personalizavel, cada unidade sera configurada pelo cliente
    quantidade: int = Field(ge=1, le=20)


class ComboItemAlimentoIn(BaseModel):
    alimento_id: uuid.UUID
    quantidade: int = Field(ge=1, le=20)


class ComboIn(BaseModel):
    nome: Nome
    descricao: Descricao | None = None
    preco: Preco  # preco proprio, independente da soma dos itens
    ativo: bool = True
    destaque: bool = False
    itens_marmita: list[ComboItemMarmitaIn] = Field(default_factory=list)
    itens_alimento: list[ComboItemAlimentoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_itens(self) -> "ComboIn":
        if not self.itens_marmita and not self.itens_alimento:
            raise ValueError("O combo precisa de ao menos um item.")
        marmitas = [i.marmita_id for i in self.itens_marmita]
        if len(marmitas) != len(set(marmitas)):
            raise ValueError(
                "Marmita repetida no combo; aumente a quantidade do item existente."
            )
        alimentos = [i.alimento_id for i in self.itens_alimento]
        if len(alimentos) != len(set(alimentos)):
            raise ValueError(
                "Alimento repetido no combo; aumente a quantidade do item existente."
            )
        return self


# ----------------------------- saida -----------------------------
class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ComboItemMarmitaOut(_Out):
    marmita_id: uuid.UUID = Field(validation_alias="meal_box_id")
    marmita_nome: str = Field(validation_alias="meal_box_name")
    marmita_tipo: MealBoxKind = Field(validation_alias="meal_box_kind")
    quantidade: int = Field(validation_alias="quantity")


class ComboItemAlimentoOut(_Out):
    alimento_id: uuid.UUID = Field(validation_alias="food_id")
    alimento_nome: str = Field(validation_alias="food_name")
    quantidade: int = Field(validation_alias="quantity")


class ComboResumoOut(_Out):
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    preco: Decimal = Field(validation_alias="price")
    ativo: bool = Field(validation_alias="is_active")
    destaque: bool = Field(validation_alias="is_featured")
    imagem_url: str | None = Field(default=None, validation_alias="image_url")
    possui_marmita_personalizavel: bool = Field(validation_alias="has_customizable_meal_box")
    possui_item_inativo: bool = Field(validation_alias="has_inactive_items")
    serve_hoje: bool = Field(validation_alias="serves_today")
    esgotado_hoje: bool = Field(validation_alias="sold_out_today")


class ComboOut(ComboResumoOut):
    descricao: str | None = Field(default=None, validation_alias="description")
    itens_marmita: list[ComboItemMarmitaOut] = Field(default_factory=list, validation_alias="meal_box_items")
    itens_alimento: list[ComboItemAlimentoOut] = Field(default_factory=list, validation_alias="food_items")


class ComboListOut(BaseModel):
    itens: list[ComboResumoOut]
    total: int