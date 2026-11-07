import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import Combo, Food, FoodCategory, MealBox
from app.services import disponibilidade_service as disponibilidade

_CENTAVOS = Decimal("0.01")
GRUPOS = ("prato", "bebida")


def preco_referencia_combo(combo: Combo) -> Decimal | None:
    """Soma dos itens avulsos do combo (preco x quantidade).

    Marmita usa `price`; alimento usa `standalone_price` (Food.base_price e
    legado e e ignorado). Devolve None quando algum item nao tem preco ou
    quando a economia (soma - preco do combo) e <= 0: nesses casos o
    cliente nao ve preco "de referencia".
    """
    total = Decimal("0")
    for item in combo.meal_box_items:
        total += item.meal_box.price * item.quantity
    for item in combo.food_items:
        if item.food.standalone_price is None:
            return None
        total += item.food.standalone_price * item.quantity

    total = total.quantize(_CENTAVOS)
    if total - combo.price <= 0:
        return None
    return total


def _visiveis(db: Session, modelo: type, objetos: list, hoje: date) -> list:
    """Dos objetos informados, os que servem hoje e nao estao esgotados."""
    servem = disponibilidade.servem_hoje(db, modelo, [o.id for o in objetos], hoje)
    return [
        o for o in objetos
        if o.id in servem and not disponibilidade.esgotado_hoje(o, hoje)
    ]


def _marmitas(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    caixas = db.scalars(
        select(MealBox)
        .where(MealBox.restaurant_id == restaurant_id, MealBox.is_active.is_(True))
        .order_by(MealBox.name)
    ).all()
    return [
        {
            "id": m.id,
            "nome": m.name,
            "descricao": m.description,
            "tipo": m.kind,
            "tamanho": m.size,
            "preco": m.price,
            "imagem_url": m.image_url,
            "destaque": m.is_featured,
        }
        for m in _visiveis(db, MealBox, list(caixas), hoje)
    ]


def _combos(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    combos = db.scalars(
        select(Combo)
        .where(Combo.restaurant_id == restaurant_id, Combo.is_active.is_(True))
        .order_by(Combo.name)
    ).all()
    # so item INATIVO derruba o combo; componente esgotado/fora do dia nao (Fase 6)
    combos = [c for c in combos if not c.has_inactive_items]
    return [
        {
            "id": c.id,
            "nome": c.name,
            "descricao": c.description,
            "preco": c.price,
            "preco_referencia": preco_referencia_combo(c),
            "imagem_url": c.image_url,
            "destaque": c.is_featured,
        }
        for c in _visiveis(db, Combo, combos, hoje)
    ]


def _produto(alimento: Food) -> dict:
    return {
        "id": alimento.id,
        "nome": alimento.name,
        "descricao": alimento.description,
        "preco": alimento.standalone_price,
        "imagem_url": alimento.image_url,
        "destaque": alimento.is_featured,
    }


def _secoes(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    # join com ON explicito: Food tem 3 FKs para FoodCategory
    linhas = db.execute(
        select(Food, FoodCategory)
        .join(FoodCategory, Food.sale_category_id == FoodCategory.id)
        .where(
            Food.restaurant_id == restaurant_id,
            Food.is_active.is_(True),
            Food.is_sellable_alone.is_(True),
            FoodCategory.restaurant_id == restaurant_id,
            FoodCategory.type == "venda",
            FoodCategory.is_active.is_(True),
        )
        .order_by(FoodCategory.display_order, FoodCategory.name, Food.name)
    ).all()
    visiveis = {f.id for f in _visiveis(db, Food, [f for f, _ in linhas], hoje)}

    por_grupo: dict[str, dict[uuid.UUID, dict]] = {g: {} for g in GRUPOS}
    for alimento, categoria in linhas:
        if alimento.id not in visiveis or categoria.group not in por_grupo:
            continue
        secao = por_grupo[categoria.group].setdefault(
            categoria.id, {"id": categoria.id, "nome": categoria.name, "itens": []}
        )
        secao["itens"].append(_produto(alimento))

    # categoria e secao vazias nem chegam a ser criadas
    return [
        {"grupo": grupo, "categorias": list(categorias.values())}
        for grupo, categorias in por_grupo.items()
        if categorias
    ]


def montar_home(db: Session, restaurant_id: uuid.UUID, hoje: date | None = None) -> dict:
    hoje = hoje or hoje_local()
    return {
        "marmitas": _marmitas(db, restaurant_id, hoje),
        "combos": _combos(db, restaurant_id, hoje),
        "secoes": _secoes(db, restaurant_id, hoje),
    }