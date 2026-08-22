import uuid
from datetime import date

from sqlalchemy.orm import Session

from backend.app.model.models import AuditLog, Food, FoodCategory, Menu, MenuItem


def obter_cardapio_do_dia(db: Session, restaurant_id: uuid.UUID, dia: date) -> Menu | None:
    return (
        db.query(Menu)
        .filter(Menu.restaurant_id == restaurant_id, Menu.date == dia)
        .first()
    )


def listar_itens_disponiveis(db: Session, menu_id: uuid.UUID) -> list[dict]:
    """Retorna só os itens DISPONÍVEIS do cardápio — é o que o cliente deve ver.
    Resolve o preço do dia (day_price) com fallback para o base_price do alimento."""
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
    """Usado quando o restaurante marca um item como indisponível durante o expediente
    (ex.: acabou o frango). Isso NÃO desativa o alimento no catálogo — só some do
    cardápio de hoje (RN06 na documentação).

    `menu_id` é exigido junto com `menu_item_id` para garantir que o item
    realmente pertence ao cardápio informado na rota. `restaurant_id` (vindo do
    usuário autenticado) garante ainda que ninguém altera um item de OUTRO
    restaurante — importante já que o schema é multi-tenant desde já.

    Toda alteração efetiva de disponibilidade gera uma linha em `log_auditoria`
    (RN25), com o usuário responsável e o valor antes/depois.
    """
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

    # só registra auditoria quando o valor realmente mudou
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