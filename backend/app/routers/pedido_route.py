import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.depedencias import get_current_user
from backend.app.schemas.pedido_schemas import OrderCreate, OrderOut
from backend.app.services import pedido_service
from backend.app.api.depedencias import get_current_client, AuthenticatedClient

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    return pedido_service.criar_pedido(db, payload, current_client)

@router.get("/{pedido_id}", response_model=OrderOut)
def buscar_pedido(
    pedido_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    pedido = pedido_service.buscar_pedido_por_id(db, pedido_id, current_user.restaurant_id)
    return pedido