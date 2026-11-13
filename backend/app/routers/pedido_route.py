import math
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.depedencias import (
    AuthenticatedClient,
    get_current_client,
    get_current_user,
    require_role,
)
from app.core.database import get_db
from app.core.websockets import manager
from app.schemas.pedido_schemas import (
    OrderCreate,
    OrderListItemOut,
    OrderNoticeOut,
    OrderOut,
    OrderReasonIn,
    OrderSendIn,
    OrderPaymentHistoryOut,
    OrderPaymentUpdate,
    PaginatedOrdersOut,
    ReorderOut,
)
from app.services import notificacao_service, pedido_fluxo, pedido_service, pedir_de_novo_service

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

operador = require_role("admin", "atendente")


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    novo_pedido = pedido_service.criar_pedido(db, payload, current_client)

    evento_ws = {
        "tipo": "NOVO_PEDIDO",
        "pedido_id": str(novo_pedido.id),
        "numero_pedido": novo_pedido.order_number,
        "tipo_atendimento": novo_pedido.service_type.value,
        "valor_total": float(novo_pedido.total_amount),
    }

    background_tasks.add_task(
        manager.broadcast_to_restaurant,
        novo_pedido.restaurant_id,
        evento_ws,
    )

    return novo_pedido


@router.get("", response_model=PaginatedOrdersOut)
def listar_pedidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resultados, total = pedido_service.listar_pedidos(
        db, current_user.restaurant_id, page, page_size
    )
    items = [
        OrderListItemOut(
            id=pedido.id, numero_pedido=pedido.order_number, cliente_id=pedido.client_id,
            cliente_nome=nome, status=status_obj, data_hora=pedido.order_datetime,
            tipo_atendimento=pedido.service_type, valor_total=pedido.total_amount,
        )
        for pedido, nome, status_obj in resultados
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
            cliente_nome=nome, status=status_obj, data_hora=pedido.order_datetime,
            tipo_atendimento=pedido.service_type, valor_total=pedido.total_amount,
        )
        for pedido, nome, status_obj in resultados
    ]

    return PaginatedOrdersOut(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/me/avisos", response_model=List[OrderNoticeOut])
def listar_meus_avisos(
    limite: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    avisos = pedido_service.listar_avisos_cliente(db, current_client.id, limite)
    return [
        OrderNoticeOut(
            pedido_id=pedido.id,
            numero_pedido=pedido.order_number,
            status=novo_status.code,
            rotulo=pedido_fluxo.rotulo(pedido.service_type, novo_status.code, novo_status.name),
            motivo=historico.note,
            data_hora=historico.changed_at,
        )
        for historico, pedido, novo_status in avisos
    ]


@router.get("/cliente/{pedido_id}", response_model=OrderOut)
def buscar_pedido_do_cliente(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    return pedido_service.buscar_pedido_do_cliente(db, pedido_id, current_client.id)


@router.get("/cliente/{pedido_id}/repetir", response_model=ReorderOut)
def repetir_pedido(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_client: AuthenticatedClient = Depends(get_current_client),
):
    return pedir_de_novo_service.montar_repeticao(db, pedido_id, current_client.id)


@router.get("/{pedido_id}", response_model=OrderOut)
def buscar_pedido(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return pedido_service.buscar_pedido_por_id(db, pedido_id, current_user.restaurant_id)


def _transicionar(
    db: Session,
    background_tasks: BackgroundTasks,
    pedido_id: uuid.UUID,
    usuario,
    codigo: str,
    **extra,
):
    pedido = pedido_service.transicionar_pedido(
        db, pedido_id, usuario.restaurant_id, usuario.id, codigo, **extra
    )
    background_tasks.add_task(
        notificacao_service.publicar,
        pedido.restaurant_id,
        pedido.client_id,
        notificacao_service.montar_evento_status(pedido),
    )
    return pedido


@router.post("/{pedido_id}/aceitar", response_model=OrderOut)
def aceitar_pedido(
    pedido_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(db, background_tasks, pedido_id, usuario, pedido_fluxo.CONFIRMADO)


@router.post("/{pedido_id}/recusar", response_model=OrderOut)
def recusar_pedido(
    pedido_id: uuid.UUID,
    payload: OrderReasonIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(
        db, background_tasks, pedido_id, usuario, pedido_fluxo.RECUSADO, motivo=payload.motivo
    )


@router.post("/{pedido_id}/preparo", response_model=OrderOut)
def iniciar_preparo(
    pedido_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(db, background_tasks, pedido_id, usuario, pedido_fluxo.EM_PREPARO)


@router.post("/{pedido_id}/pronto", response_model=OrderOut)
def marcar_pronto(
    pedido_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(db, background_tasks, pedido_id, usuario, pedido_fluxo.PRONTO)


@router.post("/{pedido_id}/enviar", response_model=OrderOut)
def enviar_pedido(
    pedido_id: uuid.UUID,
    payload: OrderSendIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(
        db,
        background_tasks,
        pedido_id,
        usuario,
        pedido_fluxo.SAIU_PARA_ENTREGA,
        entregador_id=payload.entregador_id,
    )


@router.post("/{pedido_id}/entregue", response_model=OrderOut)
def marcar_entregue(
    pedido_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(db, background_tasks, pedido_id, usuario, pedido_fluxo.ENTREGUE)


@router.post("/{pedido_id}/retirado", response_model=OrderOut)
def marcar_retirado(
    pedido_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(db, background_tasks, pedido_id, usuario, pedido_fluxo.RETIRADO)


@router.post("/{pedido_id}/cancelar", response_model=OrderOut)
def cancelar_pedido(
    pedido_id: uuid.UUID,
    payload: OrderReasonIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    return _transicionar(
        db, background_tasks, pedido_id, usuario, pedido_fluxo.CANCELADO, motivo=payload.motivo
    )


@router.patch("/{pedido_id}/pagamento", response_model=OrderOut)
def trocar_forma_pagamento(
    pedido_id: uuid.UUID,
    payload: OrderPaymentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    pedido = pedido_service.trocar_forma_pagamento(
        db,
        pedido_id,
        usuario.restaurant_id,
        usuario.id,
        payload.forma_pagamento,
        payload.valor_pago_dinheiro,
    )
    background_tasks.add_task(
        notificacao_service.publicar,
        pedido.restaurant_id,
        pedido.client_id,
        notificacao_service.montar_evento_pagamento(pedido),
    )
    return pedido


@router.get("/{pedido_id}/pagamento/historico", response_model=List[OrderPaymentHistoryOut])
def listar_historico_pagamento(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario=Depends(operador),
):
    registros = pedido_service.listar_historico_pagamento(db, pedido_id, usuario.restaurant_id)
    return [
        OrderPaymentHistoryOut(
            forma_anterior=anterior,
            forma_nova=nova,
            alterado_por=nome,
            alterado_em=historico.changed_at,
        )
        for historico, anterior, nova, nome in registros
    ]