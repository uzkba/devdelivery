from datetime import date as date_type
from typing import Annotated
from uuid import UUID
 
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
 
from backend.app.core.database import get_db
from backend.app.model.models import Food, FoodCategory, Menu, MenuItem
 
router = APIRouter()
 
 
@router.get("/restaurantes/{restaurante_id}/cardapio-do-dia")
def get_cardapio_do_dia(
    restaurante_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    hoje = date_type.today()
 
    stmt = (
        select(MenuItem, Food, FoodCategory)
        .join(Food, MenuItem.food_id == Food.id)
        .join(FoodCategory, Food.category_id == FoodCategory.id)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .where(
            Menu.restaurant_id == restaurante_id,
            Menu.date == hoje,
            # duas condições: item precisa estar disponível NO CARDÁPIO
            # (única fonte de verdade sobre estoque/disponibilidade desde
            # o PR #23) E o alimento não pode ter sido soft-deleted
            MenuItem.is_available.is_(True),
            Food.is_active.is_(True),
        )
        .order_by(FoodCategory.display_order, FoodCategory.name, Food.name)
    )
 
    resultados = db.execute(stmt).all()
 
    categorias: dict[UUID, dict] = {}
    for item, food, categoria in resultados:
        cat = categorias.setdefault(
            categoria.id,
            {
                "categoria_id": str(categoria.id),
                "categoria_nome": categoria.name,
                "itens": [],
            },
        )
        preco = item.day_price if item.day_price is not None else food.base_price
        cat["itens"].append(
            {
                "item_id": str(item.id),
                "alimento_id": str(food.id),
                "nome": food.name,
                "descricao": food.description,
                "preco": str(preco),
            }
        )
 
    return {
        "data": hoje.isoformat(),
        "categorias": list(categorias.values()),
    }
 
