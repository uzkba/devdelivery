import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.depedencias import AuthenticatedClient
from app.api.dependencias_publicas import get_restaurante_publico
from app.core.tempo import hoje_local
from app.model.models import (
    AdminUser,
    Client,
    CustomerAddress,
    Order,
    OrderItem,
    OrderServiceType,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
)
from app.schemas.pedido_schemas import OrderCreate
from app.services import entrega_service, pagamento_service, pedido_fluxo
from app.services.estado_restaurante_service import garantir_aceita_pedidos
from app.services.pedido_snapshot_service import montar_item_pedido


def _buscar_status_inicial(db: Session) -> OrderStatus:
    status_inicial = db.query(OrderStatus).order_by(OrderStatus.order.asc()).first()
    if not status_inicial:
        raise HTTPException(status_code=500, detail="Nenhum status de pedido configurado no banco.")
    return status_inicial


def _buscar_endereco_do_cliente(db: Session, endereco_id, client_id) -> CustomerAddress:
    endereco = db.query(CustomerAddress).filter_by(id=endereco_id, client_id=client_id).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado para este cliente.")
    return endereco


def _buscar_forma_pagamento(db: Session, codigo: str) -> PaymentMethod:
    forma_pagamento = db.query(PaymentMethod).filter_by(code=codigo).first()
    if not forma_pagamento:
        raise HTTPException(status_code=422, detail="Forma de pagamento inválida.")
    return forma_pagamento


def _validar_valor_pago_dinheiro(forma_pagamento_codigo: str, valor_pago_dinheiro) -> None:
    if forma_pagamento_codigo == "DINHEIRO" and valor_pago_dinheiro is None:
        raise HTTPException(status_code=422, detail="Informe o valor pago em dinheiro.")
    if forma_pagamento_codigo != "DINHEIRO" and valor_pago_dinheiro is not None:
        raise HTTPException(
            status_code=422, detail="valor_pago_dinheiro só é válido para pagamento em DINHEIRO."
        )


def criar_pedido(db: Session, payload: OrderCreate, current_client: AuthenticatedClient) -> Order:
    restaurante = get_restaurante_publico(payload.restaurante_slug, db)
    garantir_aceita_pedidos(db, restaurante)

    retirada = payload.tipo_atendimento == OrderServiceType.PICKUP
    config_entrega = entrega_service.buscar_configuracao(db, restaurante.id)
    if retirada:
        entrega_service.garantir_retirada_ativa(config_entrega)
        endereco = None
        taxa_base = Decimal("0.00")
    else:
        entrega_service.garantir_entrega_ativa(config_entrega)
        endereco = _buscar_endereco_do_cliente(db, payload.endereco_id, current_client.id)
        taxa_base = entrega_service.calcular_taxa_entrega(
            db, restaurante, endereco, config_entrega
        )

    forma_pagamento = _buscar_forma_pagamento(db, payload.forma_pagamento)
    _validar_valor_pago_dinheiro(payload.forma_pagamento, payload.valor_pago_dinheiro)
    pagamento_service.garantir_forma_aceita(db, restaurante.id, forma_pagamento)
    status_inicial = _buscar_status_inicial(db)

    hoje = hoje_local()
    itens = [montar_item_pedido(db, restaurante.id, item, hoje) for item in payload.itens]

    valor_itens = sum((item.subtotal for item in itens), Decimal("0.00"))
    entrega_service.validar_valor_minimo(config_entrega, valor_itens)
    taxa_entrega = entrega_service.aplicar_frete_gratis(config_entrega, valor_itens, taxa_base)
    valor_total = valor_itens + taxa_entrega

    troco = None
    if payload.valor_pago_dinheiro is not None:
        if payload.valor_pago_dinheiro < valor_total:
            raise HTTPException(
                status_code=400, detail="Valor pago em dinheiro é menor que o total do pedido."
            )
        troco = payload.valor_pago_dinheiro - valor_total

    novo_pedido = Order(
        restaurant_id=restaurante.id,
        client_id=current_client.id,
        status_id=status_inicial.id,
        payment_method_id=forma_pagamento.id,
        service_type=payload.tipo_atendimento,
        address_name=current_client.name,
        address_phone=current_client.phone,
        address_street=endereco.street if endereco else None,
        address_number=endereco.number if endereco else None,
        address_neighborhood=endereco.neighborhood if endereco else None,
        address_complement=endereco.complement if endereco else None,
        notes=payload.observacoes,
        items_amount=valor_itens,
        delivery_fee=taxa_entrega,
        total_amount=valor_total,
        cash_paid_amount=payload.valor_pago_dinheiro,
        change_amount=troco,
    )
    for item in itens:
        novo_pedido.items.append(
            OrderItem(
                food_id=item.food_id,
                meal_box_id=item.meal_box_id,
                combo_id=item.combo_id,
                food_name=item.nome,
                quantity=item.quantidade,
                base_price=item.preco_unitario,
                subtotal=item.subtotal,
                notes=item.observacao,
                snapshot=item.snapshot,
            )
        )

    try:
        db.add(novo_pedido)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar o pedido.")

    db.refresh(novo_pedido)
    return novo_pedido


def buscar_pedido_por_id(db: Session, pedido_id: uuid.UUID, restaurant_id: uuid.UUID) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, restaurant_id=restaurant_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido


def listar_pedidos(
    db: Session,
    restaurant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Order, str, OrderStatus]], int]:
    query = (
        db.query(Order, Client.name, OrderStatus)
        .join(Client, Client.id == Order.client_id)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(Order.restaurant_id == restaurant_id)
    )
    total = query.count()
    resultados = (
        query.order_by(Order.order_datetime.asc(), Order.order_number.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return resultados, total


def listar_pedidos_cliente(
    db: Session,
    client_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Order, str, OrderStatus]], int]:
    query = (
        db.query(Order, Client.name, OrderStatus)
        .join(Client, Client.id == Order.client_id)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(Order.client_id == client_id)
    )
    total = query.count()
    resultados = (
        query.order_by(Order.order_datetime.desc(), Order.order_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return resultados, total


def buscar_pedido_do_cliente(db: Session, pedido_id: uuid.UUID, client_id: uuid.UUID) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, client_id=client_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido


MOTIVO_MIN = 3
MOTIVO_MAX = 300


def _erro_422(detalhe: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detalhe)


def _normalizar_motivo(novo_codigo: str, motivo: str | None) -> str | None:
    texto = motivo.strip() if motivo else ""
    if novo_codigo not in pedido_fluxo.COM_MOTIVO:
        if texto:
            raise _erro_422("O motivo só vale para recusa ou cancelamento.")
        return None
    if not MOTIVO_MIN <= len(texto) <= MOTIVO_MAX:
        raise _erro_422(f"Informe o motivo ({MOTIVO_MIN} a {MOTIVO_MAX} caracteres).")
    return texto


def _buscar_entregador(
    db: Session, restaurant_id: uuid.UUID, entregador_id: uuid.UUID | None
) -> AdminUser:
    if entregador_id is None:
        raise _erro_422("Escolha o entregador para enviar o pedido.")
    entregador = (
        db.query(AdminUser)
        .filter_by(id=entregador_id, restaurant_id=restaurant_id, role="entregador")
        .first()
    )
    if not entregador:
        raise _erro_422("Entregador não encontrado neste restaurante.")
    if not entregador.is_active:
        raise _erro_422(f"O entregador '{entregador.name}' está inativo.")
    return entregador


def transicionar_pedido(
    db: Session,
    pedido_id: uuid.UUID,
    restaurant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    novo_codigo: str,
    motivo: str | None = None,
    entregador_id: uuid.UUID | None = None,
) -> Order:
    pedido = (
        db.query(Order)
        .filter_by(id=pedido_id, restaurant_id=restaurant_id)
        .with_for_update(of=Order)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    novo_status = db.query(OrderStatus).filter_by(code=novo_codigo).first()
    if not novo_status:
        raise HTTPException(
            status_code=500, detail=f"Status '{novo_codigo}' não configurado no banco."
        )

    status_atual = pedido.status
    if status_atual.id == novo_status.id:
        raise _erro_422("O pedido já está neste status.")
    if not pedido_fluxo.pode_transitar(pedido.service_type, status_atual.code, novo_codigo):
        if status_atual.is_final:
            raise _erro_422(
                f"O pedido já foi finalizado ('{status_atual.name}') e não pode mais mudar."
            )
        raise _erro_422(
            f"Não é possível mudar o pedido de '{status_atual.name}' para '{novo_status.name}'."
        )

    motivo_limpo = _normalizar_motivo(novo_codigo, motivo)

    entregador = None
    if novo_codigo == pedido_fluxo.SAIU_PARA_ENTREGA:
        entregador = _buscar_entregador(db, restaurant_id, entregador_id)
    elif entregador_id is not None:
        raise _erro_422("O entregador só é informado ao enviar o pedido.")

    db.add(
        OrderStatusHistory(
            order_id=pedido.id,
            previous_status_id=status_atual.id,
            new_status_id=novo_status.id,
            changed_by=usuario_id,
            note=motivo_limpo,
        )
    )
    pedido.status = novo_status
    if motivo_limpo:
        pedido.status_reason = motivo_limpo
    if entregador:
        pedido.driver = entregador

    db.commit()
    db.refresh(pedido)
    return pedido