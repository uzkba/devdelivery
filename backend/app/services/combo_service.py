"""NexusDelivery - Fase 1: regras de negocio de combo."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.model.models import Combo, ComboFoodItem, ComboMealBoxItem, Food, MealBox
from app.schemas.combo_schemas import ComboIn


def _unprocessable(msg: str) -> HTTPException:
    return HTTPException(422, msg)


def _validate_refs(db: Session, restaurant_id: uuid.UUID, payload: ComboIn) -> None:
    meal_box_ids = {i.marmita_id for i in payload.itens_marmita}
    if meal_box_ids:
        found = db.scalars(
            select(MealBox).where(
                MealBox.id.in_(meal_box_ids), MealBox.restaurant_id == restaurant_id
            )
        ).all()
        missing = meal_box_ids - {m.id for m in found}
        if missing:
            raise _unprocessable(
                "Marmitas não encontradas: " + ", ".join(sorted(map(str, missing))) + "."
            )
        inactive = [m.name for m in found if not m.is_active]
        if inactive:
            raise _unprocessable(
                "Marmitas inativas não podem entrar no combo: " + ", ".join(inactive) + "."
            )

    food_ids = {i.alimento_id for i in payload.itens_alimento}
    if food_ids:
        found_foods = db.scalars(
            select(Food).where(Food.id.in_(food_ids), Food.restaurant_id == restaurant_id)
        ).all()
        missing = food_ids - {f.id for f in found_foods}
        if missing:
            raise _unprocessable(
                "Alimentos não encontrados: " + ", ".join(sorted(map(str, missing))) + "."
            )
        inactive = [f.name for f in found_foods if not f.is_active]
        if inactive:
            raise _unprocessable(
                "Alimentos inativos não podem entrar no combo: " + ", ".join(inactive) + "."
            )


def _apply_fields(combo: Combo, payload: ComboIn) -> None:
    combo.name = payload.nome
    combo.description = payload.descricao
    combo.price = payload.preco
    combo.is_active = payload.ativo
    combo.is_featured = payload.destaque


def _apply_children(combo: Combo, payload: ComboIn) -> None:
    combo.meal_box_items = [
        ComboMealBoxItem(meal_box_id=i.marmita_id, quantity=i.quantidade, position=pos)
        for pos, i in enumerate(payload.itens_marmita)
    ]
    combo.food_items = [
        ComboFoodItem(food_id=i.alimento_id, quantity=i.quantidade, position=pos)
        for pos, i in enumerate(payload.itens_alimento)
    ]


def create_combo(db: Session, restaurant_id: uuid.UUID, payload: ComboIn) -> Combo:
    _validate_refs(db, restaurant_id, payload)
    combo = Combo(restaurant_id=restaurant_id)
    _apply_fields(combo, payload)
    _apply_children(combo, payload)
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo


def get_combo(db: Session, restaurant_id: uuid.UUID, combo_id: uuid.UUID) -> Combo:
    combo = db.scalar(
        select(Combo).where(Combo.id == combo_id, Combo.restaurant_id == restaurant_id)
    )
    if combo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Combo não encontrado.")
    return combo


def list_combos(
    db: Session,
    restaurant_id: uuid.UUID,
    *,
    active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Combo], int]:
    conditions = [Combo.restaurant_id == restaurant_id]
    if active is not None:
        conditions.append(Combo.is_active == active)
    if search:
        conditions.append(Combo.name.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count()).select_from(Combo).where(*conditions)) or 0
    items = db.scalars(
        select(Combo)
        .where(*conditions)
        .order_by(Combo.is_active.desc(), Combo.name)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total


def update_combo(
    db: Session, restaurant_id: uuid.UUID, combo_id: uuid.UUID, payload: ComboIn
) -> Combo:
    combo = get_combo(db, restaurant_id, combo_id)
    _validate_refs(db, restaurant_id, payload)
    _apply_fields(combo, payload)
    # limpa e persiste antes de recriar (INSERT roda antes de DELETE no flush)
    combo.meal_box_items.clear()
    combo.food_items.clear()
    db.flush()
    _apply_children(combo, payload)
    db.commit()
    db.refresh(combo)
    return combo


def set_combo_active(
    db: Session, restaurant_id: uuid.UUID, combo_id: uuid.UUID, active: bool
) -> Combo:
    combo = get_combo(db, restaurant_id, combo_id)
    combo.is_active = active
    db.commit()
    db.refresh(combo)
    return combo


def delete_combo(db: Session, restaurant_id: uuid.UUID, combo_id: uuid.UUID) -> None:
    combo = get_combo(db, restaurant_id, combo_id)
    try:
        db.delete(combo)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este combo já é usado em pedidos. Desative-o em vez de excluir.",
        )