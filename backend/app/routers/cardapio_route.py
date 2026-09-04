import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.cardapio_schemas import (
    CardapioCreate,
    CardapioItensCreate,
    CardapioResponse,
    MenuItemAvailabilityUpdate,
    MenuItemOut,
)
from app.services import cardapio_service

router = APIRouter(prefix="/cardapio", tags=["cardapio"])

# TODO: ainda não há contexto de restaurante para rotas públicas (config.py está
# vazio e falta a seleção de restaurante). Placeholder até isso ser definido.
RESTAURANTE_ID_PADRAO = uuid.UUID("00000000-0000-0000-0000-000000000000")

PAPEIS_PODEM_ALTERAR_DISPONIBILIDADE = ("admin", "atendente")


@router.get("/hoje")
def cardapio_de_hoje(db: Session = Depends(get_db)):
    """Endpoint que o CLIENTE consome — só retorna itens disponíveis. Rota pública."""
    menu = cardapio_service.obter_cardapio_do_dia(db, RESTAURANTE_ID_PADRAO, date.today())
    if menu is None:
        raise HTTPException(status_code=404, detail="Cardápio de hoje ainda não foi cadastrado")
    itens = cardapio_service.listar_itens_disponiveis(db, menu.id)
    return {"data": str(menu.date), "itens": itens}


@router.post("", response_model=CardapioResponse, status_code=status.HTTP_201_CREATED)
def criar_cardapio(
    dados: CardapioCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    cardapio = cardapio_service.criar_cardapio(db, current_user.restaurant_id, current_user.id, dados)
    return CardapioResponse.from_model(cardapio)


@router.get("/{menu_id}", response_model=CardapioResponse)
def buscar_cardapio(
    menu_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    cardapio = cardapio_service.buscar_cardapio_por_id(db, current_user.restaurant_id, menu_id)
    return CardapioResponse.from_model(cardapio)


@router.post("/{menu_id}/itens", response_model=CardapioResponse, status_code=status.HTTP_201_CREATED)
def adicionar_itens(
    menu_id: uuid.UUID,
    dados: CardapioItensCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    cardapio = cardapio_service.adicionar_itens(db, current_user.restaurant_id, menu_id, dados)
    return CardapioResponse.from_model(cardapio)


@router.patch("/{menu_id}/itens/{menu_item_id}/disponibilidade", response_model=MenuItemOut)
def alterar_disponibilidade(
    menu_id: uuid.UUID,
    menu_item_id: uuid.UUID,
    dados: MenuItemAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(*PAPEIS_PODEM_ALTERAR_DISPONIBILIDADE)),
):
    try:
        return cardapio_service.marcar_disponibilidade(
            db,
            menu_id=menu_id,
            menu_item_id=menu_item_id,
            is_available=dados.is_available,
            restaurant_id=current_user.restaurant_id,
            user_id=current_user.id,
        )
    except ValueError as erro:
        raise HTTPException(status_code=404, detail=str(erro))