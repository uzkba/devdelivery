import uuid
from datetime import date
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.app.model.models import AuditLog, Food, FoodCategory, Menu, MenuItem
from backend.app.schemas.cardapio_schemas import CardapioCreate, CardapioItensCreate


def obter_cardapio_do_dia(db: Session, restaurant_id: uuid.UUID, dia: date) -> Menu | None:
    return (
        db.query(Menu)
        .filter(Menu.restaurant_id == restaurant_id, Menu.date == dia)
        .first()
    )


def listar_itens_disponiveis(db: Session, menu_id: uuid.UUID) -> list[dict]:
    resultados = (
        db.query(MenuItem, Food, FoodCategory)
        .join(Food, MenuItem.food_id == Food.id)
        .join(FoodCategory, Food.category_id == FoodCategory.id)
        .filter(MenuItem.menu_id == menu_id, MenuItem.is_available.is_(True))
        .order_by(FoodCategory.display_order)
        .all()
    )
    itens = []
    for menu_item, food, category in resultados:
        itens.append(
            {
                "id": menu_item.id,
                "food_id": food.id,
                "nome": food.name,
                "categoria": category.name,
                "disponivel": menu_item.is_available,
                "preco": menu_item.day_price if menu_item.day_price is not None else food.base_price,
            }
        )
    return itens


def marcar_disponibilidade(
    db: Session,
    menu_id: uuid.UUID,
    menu_item_id: uuid.UUID,
    is_available: bool,
    restaurant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> MenuItem:
    resultado = (
        db.query(MenuItem, Menu)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .filter(
            MenuItem.id == menu_item_id,
            MenuItem.menu_id == menu_id,
            Menu.restaurant_id == restaurant_id,
        )
        .first()
    )
    if resultado is None:
        raise ValueError("Item não encontrado neste cardápio")
    item, menu = resultado
    disponibilidade_anterior = item.is_available
    item.is_available = is_available
    db.commit()
    db.refresh(item)
    if disponibilidade_anterior != is_available:
        db.add(
            AuditLog(
                restaurant_id=menu.restaurant_id,
                user_id=user_id,
                entity="cardapio_item",
                entity_id=str(item.id),
                action="ALTERACAO_DISPONIBILIDADE",
                previous_data={"is_available": disponibilidade_anterior},
                new_data={"is_available": is_available},
            )
        )
        db.commit()
    return item

def _buscar_cardapio_por_data(db: Session, restaurant_id: uuid.UUID, dia: date):
    return (
        db.query(Menu)
        .filter(Menu.restaurant_id == restaurant_id, Menu.date == dia)
        .first()
    )


def criar_cardapio(
    db: Session, restaurant_id: uuid.UUID, criado_por: uuid.UUID, dados: CardapioCreate
) -> Menu:
    if _buscar_cardapio_por_data(db, restaurant_id, dados.data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe um cardápio cadastrado para a data {dados.data}.",
        )

    cardapio = Menu(restaurant_id=restaurant_id, date=dados.data, created_by=criado_por)
    db.add(cardapio)
    db.commit()
    db.refresh(cardapio)
    return cardapio


def buscar_cardapio_por_id(db: Session, restaurant_id: uuid.UUID, menu_id: uuid.UUID) -> Menu:
    cardapio = (
        db.query(Menu)
        .options(selectinload(Menu.items))
        .filter(Menu.id == menu_id, Menu.restaurant_id == restaurant_id)
        .first()
    )
    if not cardapio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cardápio {menu_id} não encontrado.",
        )
    return cardapio


def adicionar_itens(
    db: Session, restaurant_id: uuid.UUID, menu_id: uuid.UUID, dados: CardapioItensCreate
) -> Menu:
    cardapio = buscar_cardapio_por_id(db, restaurant_id, menu_id)

    alimento_ids_payload = [item.alimento_id for item in dados.itens]
    if len(alimento_ids_payload) != len(set(alimento_ids_payload)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O mesmo alimento foi enviado mais de uma vez no payload.",
        )

    alimentos_existentes: List[Food] = (
        db.query(Food)
        .filter(Food.id.in_(set(alimento_ids_payload)), Food.restaurant_id == restaurant_id)
        .all()
    )
    alimentos_por_id = {a.id: a for a in alimentos_existentes}

    faltando = set(alimento_ids_payload) - alimentos_por_id.keys()
    if faltando:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alimento(s) não encontrado(s) neste restaurante: {', '.join(str(i) for i in faltando)}.",
        )

    inativos = [a.id for a in alimentos_existentes if not a.is_active]
    if inativos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alimento(s) inativo(s) não podem ser adicionados ao cardápio: {', '.join(str(i) for i in inativos)}.",
        )

    ja_no_cardapio = {item.food_id for item in cardapio.items}
    duplicados = set(alimento_ids_payload) & ja_no_cardapio
    if duplicados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um ou mais alimentos enviados já estão cadastrados neste cardápio.",
        )

    for item in dados.itens:
        cardapio.items.append(
            MenuItem(
                food_id=item.alimento_id,
                day_price=item.preco_dia,
                is_available=item.disponivel,
            )
        )

    db.commit()
    db.refresh(cardapio)
    return cardapio