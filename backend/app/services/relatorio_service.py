from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model.models import Order, OrderStatus

STATUS_CANCELADO_CODIGO = "CANCELADO"

class ClienteNaoEncontrado(Exception):
    pass


def get_relatorio_pedidos(
    db: Session,
    restaurant_id: UUID,
    data_inicio: date,
    data_fim: date,
    cliente_id: UUID | None = None,
) -> dict:
    if data_fim < data_inicio:
        raise ValueError("data_fim deve ser maior ou igual a data_inicio")

    if cliente_id is not None:
        tem_pedido_no_restaurante = (
            db.query(Order.id)
            .filter(Order.client_id == cliente_id, Order.restaurant_id == restaurant_id)
            .first()
        )
        if tem_pedido_no_restaurante is None:
            raise ClienteNaoEncontrado()

    inicio_dt = datetime.combine(data_inicio, time.min)
    fim_dt = datetime.combine(data_fim + timedelta(days=1), time.min)

    filtros = [
        Order.restaurant_id == restaurant_id,
        Order.order_datetime >= inicio_dt,
        Order.order_datetime < fim_dt,
    ]
    if cliente_id is not None:
        filtros.append(Order.client_id == cliente_id)

    por_status = (
        db.query(
            OrderStatus.code.label("codigo"),
            OrderStatus.name.label("status"),
            func.count(Order.id).label("quantidade"),
            func.coalesce(func.sum(Order.total_amount), 0).label("valor_total"),
        )
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(*filtros)
        .group_by(OrderStatus.code, OrderStatus.name)
        .all()
    )

    quantidade_pedidos = sum(linha.quantidade for linha in por_status)
    faturaveis = [linha for linha in por_status if linha.codigo != STATUS_CANCELADO_CODIGO]
    valor_total = sum(linha.valor_total for linha in faturaveis)
    pedidos_faturaveis = sum(linha.quantidade for linha in faturaveis)
    ticket_medio = (valor_total / pedidos_faturaveis) if pedidos_faturaveis else 0

    return {
        "quantidade_pedidos": quantidade_pedidos,
        "valor_total": valor_total,
        "ticket_medio": round(ticket_medio, 2),
        "por_status": [
            {"status": linha.status, "quantidade": linha.quantidade, "valor_total": linha.valor_total}
            for linha in por_status
        ],
    }