import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.model.models import (
    Food,
    FoodCategory,
    MealBox,
    MealBoxCategory,
    MealBoxComposition,
    MealBoxKind,
)
from app.schemas.marmita_schemas import MarmitaIn

COMPOSITION_CATEGORY_TYPE = "composicao"  # RN-C01


def _unprocessable(msg: str) -> HTTPException:
    return HTTPException(422, msg)


def _validate_refs(db: Session, restaurant_id: uuid.UUID, payload: MarmitaIn) -> None:
    if payload.tipo == MealBoxKind.CUSTOMIZABLE:
        ids = {c.categoria_alimento_id for c in payload.categorias}
        found = db.scalars(
            select(FoodCategory).where(
                FoodCategory.id.in_(ids), FoodCategory.restaurant_id == restaurant_id
            )
        ).all()
        missing = ids - {c.id for c in found}
        if missing:
            raise _unprocessable(
                "Categorias não encontradas: " + ", ".join(sorted(map(str, missing))) + "."
            )
        sale_only = [c.name for c in found if c.type != COMPOSITION_CATEGORY_TYPE]
        if sale_only:
            raise _unprocessable(
                "Categorias de venda avulsa não podem compor marmita: "
                + ", ".join(sale_only)
                + "."
            )
        inactive = [c.name for c in found if not c.is_active]
        if inactive:
            raise _unprocessable(
                "Categorias inativas não podem compor marmita: " + ", ".join(inactive) + "."
            )
    else:
        ids = {c.alimento_id for c in payload.composicao}
        found_foods = db.scalars(
            select(Food).where(Food.id.in_(ids), Food.restaurant_id == restaurant_id)
        ).all()
        missing = ids - {f.id for f in found_foods}
        if missing:
            raise _unprocessable(
                "Alimentos não encontrados: " + ", ".join(sorted(map(str, missing))) + "."
            )
        inactive = [f.name for f in found_foods if not f.is_active]
        if inactive:
            raise _unprocessable(
                "Alimentos inativos não podem entrar na composição: "
                + ", ".join(inactive)
                + "."
            )
        no_composition = [f.name for f in found_foods if f.composition_category_id is None]
        if no_composition:
            raise _unprocessable(
                "Alimentos sem categoria de composição não podem entrar em marmita: "
                + ", ".join(no_composition)
                + "."
            )


def _apply_fields(box: MealBox, payload: MarmitaIn) -> None:
    box.name = payload.nome
    box.description = payload.descricao
    box.kind = payload.tipo
    box.size = payload.tamanho
    box.price = payload.preco
    box.is_active = payload.ativo
    box.is_featured = payload.destaque
    box.calories_kcal = payload.calorias_kcal
    box.protein_g = payload.proteina_g
    box.carbs_g = payload.carboidrato_g
    box.fat_g = payload.gordura_g


def _apply_children(box: MealBox, payload: MarmitaIn) -> None:
    if payload.tipo == MealBoxKind.CUSTOMIZABLE:
        box.categories = [
            MealBoxCategory(
                food_category_id=c.categoria_alimento_id,
                required_quantity=c.quantidade_exigida,
                position=pos,
            )
            for pos, c in enumerate(payload.categorias)
        ]
        box.composition = []
    else:
        box.composition = [
            MealBoxComposition(
                food_id=c.alimento_id, fixed_quantity=c.quantidade_fixa, position=pos
            )
            for pos, c in enumerate(payload.composicao)
        ]
        box.categories = []


def create_meal_box(db: Session, restaurant_id: uuid.UUID, payload: MarmitaIn) -> MealBox:
    _validate_refs(db, restaurant_id, payload)
    box = MealBox(restaurant_id=restaurant_id)
    _apply_fields(box, payload)
    _apply_children(box, payload)
    db.add(box)
    db.commit()
    db.refresh(box)
    return box


def get_meal_box(db: Session, restaurant_id: uuid.UUID, meal_box_id: uuid.UUID) -> MealBox:
    box = db.scalar(
        select(MealBox).where(
            MealBox.id == meal_box_id, MealBox.restaurant_id == restaurant_id
        )
    )
    if box is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marmita não encontrada.")
    return box


def list_meal_boxes(
    db: Session,
    restaurant_id: uuid.UUID,
    *,
    kind: MealBoxKind | None = None,
    active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[MealBox], int]:
    conditions = [MealBox.restaurant_id == restaurant_id]
    if kind is not None:
        conditions.append(MealBox.kind == kind)
    if active is not None:
        conditions.append(MealBox.is_active == active)
    if search:
        conditions.append(MealBox.name.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count()).select_from(MealBox).where(*conditions)) or 0
    items = db.scalars(
        select(MealBox)
        .where(*conditions)
        .order_by(MealBox.is_active.desc(), MealBox.name)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total


def update_meal_box(
    db: Session, restaurant_id: uuid.UUID, meal_box_id: uuid.UUID, payload: MarmitaIn
) -> MealBox:
    box = get_meal_box(db, restaurant_id, meal_box_id)
    _validate_refs(db, restaurant_id, payload)
    _apply_fields(box, payload)
    # Limpa e persiste antes de recriar: o UnitOfWork do SQLAlchemy faz
    # INSERT antes de DELETE, o que violaria as constraints de unicidade.
    box.categories.clear()
    box.composition.clear()
    db.flush()
    _apply_children(box, payload)
    db.commit()
    db.refresh(box)
    return box


def set_meal_box_active(
    db: Session, restaurant_id: uuid.UUID, meal_box_id: uuid.UUID, active: bool
) -> MealBox:
    box = get_meal_box(db, restaurant_id, meal_box_id)
    box.is_active = active
    db.commit()
    db.refresh(box)
    return box


def delete_meal_box(db: Session, restaurant_id: uuid.UUID, meal_box_id: uuid.UUID) -> None:
    box = get_meal_box(db, restaurant_id, meal_box_id)
    try:
        db.delete(box)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta marmita já é usada em combos ou pedidos. Desative-a em vez de excluir.",
        )