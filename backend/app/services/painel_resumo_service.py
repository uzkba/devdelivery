import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core import periodo
from app.model.models import Order, OrderStatus, OrderStatusHistory
from app.services import pedido_fluxo

NAO_FATURAVEIS = (pedido_fluxo.CANCELADO, pedido_fluxo.RECUSADO)
CENTAVOS = Decimal("0.01")
UMA_CASA = Decimal("0.1")
INTEIRO = Decimal("1")


@dataclass(frozen=True)
class ResumoDoPeriodo:
    vendas: Decimal
    pedidos: int
    ticket_medio: Decimal
    entrega_media_min: int | None


@dataclass(frozen=True)
class ResumoComparado:
    dia: date
    comparado_com: date
    rotulo_comparacao: str
    atual: ResumoDoPeriodo
    anterior: ResumoDoPeriodo
    variacao_vendas_pct: Decimal | None
    diferenca_pedidos: int
    diferenca_ticket_medio: Decimal
    diferenca_entrega_min: int | None


def _vendas_e_pedidos(
    db: Session, restaurant_id: uuid.UUID, inicio: datetime, fim: datetime
) -> tuple[Decimal, int]:
    pedidos, vendas = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0))
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.notin_(NAO_FATURAVEIS),
        )
        .one()
    )
    return Decimal(vendas).quantize(CENTAVOS, ROUND_HALF_UP), int(pedidos)


def _entrega_media_min(
    db: Session, restaurant_id: uuid.UUID, inicio: datetime, fim: datetime
) -> int | None:
    segundos = (
        db.query(
            func.avg(extract("epoch", OrderStatusHistory.changed_at - Order.order_datetime))
        )
        .select_from(OrderStatusHistory)
        .join(Order, Order.id == OrderStatusHistory.order_id)
        .join(OrderStatus, OrderStatus.id == OrderStatusHistory.new_status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            OrderStatus.code == pedido_fluxo.ENTREGUE,
            OrderStatusHistory.changed_at >= inicio,
            OrderStatusHistory.changed_at < fim,
        )
        .scalar()
    )
    if segundos is None:
        return None
    minutos = Decimal(str(segundos)) / 60
    return int(minutos.quantize(INTEIRO, ROUND_HALF_UP))


def resumo_do_periodo(
    db: Session, restaurant_id: uuid.UUID, inicio: datetime, fim: datetime
) -> ResumoDoPeriodo:
    vendas, pedidos = _vendas_e_pedidos(db, restaurant_id, inicio, fim)
    ticket = (
        (vendas / pedidos).quantize(CENTAVOS, ROUND_HALF_UP) if pedidos else Decimal("0.00")
    )
    return ResumoDoPeriodo(
        vendas=vendas,
        pedidos=pedidos,
        ticket_medio=ticket,
        entrega_media_min=_entrega_media_min(db, restaurant_id, inicio, fim),
    )


def _variacao_pct(atual: Decimal, anterior: Decimal) -> Decimal | None:
    if anterior == 0:
        return None
    return ((atual - anterior) / anterior * 100).quantize(UMA_CASA, ROUND_HALF_UP)


def _diferenca_entrega(atual: int | None, anterior: int | None) -> int | None:
    if atual is None or anterior is None:
        return None
    return atual - anterior


def resumo_do_dia(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> ResumoComparado:
    janela_atual, janela_anterior = periodo.janelas_comparaveis(agora)
    atual = resumo_do_periodo(db, restaurant_id, janela_atual.inicio, janela_atual.fim)
    anterior = resumo_do_periodo(
        db, restaurant_id, janela_anterior.inicio, janela_anterior.fim
    )
    return ResumoComparado(
        dia=janela_atual.dia,
        comparado_com=janela_anterior.dia,
        rotulo_comparacao=periodo.rotulo_semana_passada(janela_anterior.dia),
        atual=atual,
        anterior=anterior,
        variacao_vendas_pct=_variacao_pct(atual.vendas, anterior.vendas),
        diferenca_pedidos=atual.pedidos - anterior.pedidos,
        diferenca_ticket_medio=atual.ticket_medio - anterior.ticket_medio,
        diferenca_entrega_min=_diferenca_entrega(
            atual.entrega_media_min, anterior.entrega_media_min
        ),
    )