import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.depedencias import require_role
from backend.app.core.database import get_db
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser
from backend.app.schemas.cardapio_schemas import MenuItemAvailabilityUpdate, MenuItemOut
from backend.app.services import cardapio_service

router = APIRouter(prefix="/cardapio", tags=["cardapio"])

# TODO: ainda não há contexto de restaurante para rotas públicas (config.py está
# vazio e falta a seleção de restaurante). Placeholder até isso ser definido.
RESTAURANTE_ID_PADRAO = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Papéis autorizados a alterar disponibilidade de item do cardápio (seção 3 da documentação).
PAPEIS_PODEM_ALTERAR_DISPONIBILIDADE = ("admin", "atendente")


@router.get("/hoje")
def cardapio_de_hoje(db: Session = Depends(get_db)):
    """Endpoint que o CLIENTE consome — só retorna itens disponíveis. Rota pública."""
    menu = cardapio_service.obter_cardapio_do_dia(db, RESTAURANTE_ID_PADRAO, date.today())
    if menu is None:
        raise HTTPException(status_code=404, detail="Cardápio de hoje ainda não foi cadastrado")
    itens = cardapio_service.listar_itens_disponiveis(db, menu.id)
    return {"data": str(menu.date), "itens": itens}


@router.patch("/{menu_id}/itens/{menu_item_id}/disponibilidade", response_model=MenuItemOut)
def alterar_disponibilidade(
    menu_id: uuid.UUID,
    menu_item_id: uuid.UUID,
    dados: MenuItemAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(*PAPEIS_PODEM_ALTERAR_DISPONIBILIDADE)),
):
    """Endpoint do RESTAURANTE — usado quando acaba um ingrediente durante o expediente.

    Requer token JWT válido de um AdminUser com papel 'admin' ou 'atendente'.
    Só altera itens do restaurante do próprio usuário logado.
    """
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