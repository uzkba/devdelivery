import uuid
import math
from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import get_current_user
from app.schemas.pedido_schemas import (
    OrderCreate, OrderOut, OrderListItemOut, PaginatedOrdersOut,
)
from backend.app.services import pedido_service
from backend.app.api.depedencias import require_role
from backend.app.schemas.pedido_schemas import OrderCreate, OrderOut, OrderStatusUpdate
from backend.app.api.depedencias import get_current_client, AuthenticatedClient
from backend.app.core.websockets import manager

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,  # <-- Injeção do FastAPI para tarefas em 2º plano
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    # 1. O service processa o carrinho, calcula totais e salva no banco (Síncrono)
    novo_pedido = pedido_service.criar_pedido(db, payload, current_client)
    
    # 2. Monta o pacote de dados leve que será enviado ao painel do restaurante
    evento_ws = {
        "tipo": "NOVO_PEDIDO",
        "pedido_id": str(novo_pedido.id),
        "numero_pedido": novo_pedido.order_number,
        "valor_total": float(novo_pedido.total_amount)
    }

    # 3. Agenda a notificação WebSocket sem travar a resposta HTTP do cliente (Assíncrono)
    background_tasks.add_task(
        manager.broadcast_to_restaurant, 
        novo_pedido.restaurant_id, 
        evento_ws
    )

    # 4. Retorna o schema OrderOut normalmente para o frontend do cliente
    return novo_pedido


@router.get("", response_model=PaginatedOrdersOut)
def listar_pedidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    resultados, total = pedido_service.listar_pedidos(
        db, current_user.restaurant_id, page, page_size
    )
    items = [
        OrderListItemOut(
            id=pedido.id, numero_pedido=pedido.order_number, cliente_id=pedido.client_id,
            cliente_nome=nome, status_id=pedido.status_id, data_hora=pedido.order_datetime,
            valor_total=pedido.total_amount,
        )
        for pedido, nome in resultados
    ]
    return PaginatedOrdersOut(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/me", response_model=PaginatedOrdersOut)
def listar_meus_pedidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    resultados, total = pedido_service.listar_pedidos_cliente(
        db, current_client.id, page, page_size
    )
    
    items = [
        OrderListItemOut(
            id=pedido.id, numero_pedido=pedido.order_number, cliente_id=pedido.client_id,
            cliente_nome=nome, status_id=pedido.status_id, data_hora=pedido.order_datetime,
            valor_total=pedido.total_amount,
        )
        for pedido, nome in resultados
    ]
    
    return PaginatedOrdersOut(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/cliente/{pedido_id}", response_model=OrderOut)
def buscar_pedido_do_cliente(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    pedido = pedido_service.buscar_pedido_do_cliente(db, pedido_id, current_client.id)
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