from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date as date_type

from backend.app.core.database import get_db
from backend.app.model.models import Menu, MenuItem, Food
from backend.app.schemas.admin_cardapio_schema import MenuCreate, MenuItemUpdate
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser
from backend.app.api.depedencias import get_current_user

router = APIRouter(prefix="/admin/cardapio", tags=["Admin Cardapio"])

@router.post("/gerar", status_code=status.HTTP_201_CREATED)
def gerar_cardapio_do_dia(
    payload: MenuCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Cria o cardápio do dia copiando TODOS os alimentos ativos do catálogo principal.
    """
    # 1. Verifica se já existe um cardápio para hoje neste restaurante
    menu_existente = db.scalar(
        select(Menu).where(
            Menu.restaurant_id == current_user.restaurant_id,
            Menu.date == payload.data
        )
    )
    if menu_existente:
        raise HTTPException(
            status_code=400, 
            detail="Já existe um cardápio criado para esta data."
        )

    # 2. Cria o registro "Pai" (Menu)
    novo_menu = Menu(
        restaurant_id=current_user.restaurant_id,
        date=payload.data,
        created_by=current_user.id  # ID do usuário logado que vem do JWT
    )
    db.add(novo_menu)
    db.flush() # Salva no banco temporariamente para gerar o novo_menu.id

    # 3. Busca todos os alimentos ativos do restaurante no catálogo
    alimentos_ativos = db.scalars(
        select(Food).where(
            Food.restaurant_id == current_user.restaurant_id,
            Food.is_active.is_(True)
        )
    ).all()

    if not alimentos_ativos:
        raise HTTPException(status_code=400, detail="Nenhum alimento ativo no catálogo.")

    # 4. Cria os "Filhos" (MenuItem) vinculando os alimentos ao cardápio de hoje
    itens_cardapio = [
        MenuItem(
            menu_id=novo_menu.id,
            food_id=alimento.id,
            is_available=True, # Nasce disponível por padrão
            day_price=None     # Usa o preco_base original, a menos que seja editado depois
        )
        for alimento in alimentos_ativos
    ]
    
    db.add_all(itens_cardapio)
    db.commit()

    return {"message": "Cardápio gerado com sucesso com todos os itens ativos!", "menu_id": novo_menu.id}


@router.patch("/item/{item_id}")
def atualizar_item_cardapio(
    item_id: UUID,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Altera a disponibilidade (acabou na cozinha) ou faz uma promoção (muda o preço do dia).
    """
    # 1. Busca o item GARANTINDO que ele pertence ao restaurante do usuário logado
    # Fazemos um JOIN com Menu para checar o restaurant_id
    stmt = select(MenuItem).join(Menu).where(
        MenuItem.id == item_id,
        Menu.restaurant_id == current_user.restaurant_id
    )
    item = db.scalar(stmt)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item do cardápio não encontrado.")

    # 2. Aplica as alterações apenas se elas foram enviadas na requisição
    if payload.is_available is not None:
        item.is_available = payload.is_available
        
    if payload.day_price is not None:
        item.day_price = payload.day_price

    db.commit()
    db.refresh(item)
    
    status_disponibilidade = "Disponível" if item.is_available else "Esgotado"
    
    return {
        "message": "Item atualizado com sucesso.", 
        "status": status_disponibilidade
    }