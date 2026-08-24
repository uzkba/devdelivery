import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.depedencias import get_current_user
from backend.app.schemas.pedido_schemas import OrderCreate, OrderOut
from backend.app.services import pedido_service
from backend.app.api.depedencias import require_role
from backend.app.schemas.pedido_schemas import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    payload: OrderCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    pedido = pedido_service.criar_pedido(db, payload, current_user.restaurant_id)
    return pedido

@router.get("/{pedido_id}", response_model=OrderOut)
def buscar_pedido(
    pedido_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    pedido = pedido_service.buscar_pedido_por_id(db, pedido_id, current_user.restaurant_id)
    return pedido

@router.patch("/{pedido_id}/status", response_model=OrderOut)
def atualizar_status_pedido(
    pedido_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin", "atendente")),
):
    return pedido_service.atualizar_status_pedido(
        db, pedido_id, payload.novo_status, current_user.restaurant_id, current_user.id
    )