import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session, selectinload

from app.core import periodo
from app.model.models import (
    Order,
    OrderItem,
    OrderServiceType,
    OrderStatus,
    OrderStatusHistory,
)
from app.services import pedido_fluxo
from app.services.painel_alertas_service import STATUS_ATIVOS, AtrasoPedido, atrasos_dos_pedidos

ETAPA_NOVOS = "novos"
ETAPA_PREPARO = "preparo"
ETAPA_SAINDO = "saindo"

ETAPAS = {
    ETAPA_NOVOS: frozenset({pedido_fluxo.CRIADO}),
    ETAPA_PREPARO: frozenset(
        {pedido_fluxo.CONFIRMADO, pedido_fluxo.EM_PREPARO, pedido_fluxo.PRONTO}
    ),
    ETAPA_SAINDO: frozenset({pedido_fluxo.SAIU_PARA_ENTREGA}),
}
ETAPA_POR_STATUS = {
    codigo: etapa for etapa, codigos in ETAPAS.items() for codigo in codigos
}
CONCLUIDOS = (pedido_fluxo.ENTREGUE, pedido_fluxo.RETIRADO)

LIMITE_PADRAO = 4
ITENS_NO_RESUMO = 3


@dataclass(frozen=True)
class FilaDoDia:
    novos: int
    preparo: int
    saindo: int
    entregues: int
    espera_mais_antiga_min: int | None


@dataclass(frozen=True)
class PedidoEmAndamento:
    pedido_id: uuid.UUID
    numero_pedido: int
    cliente_nome: str
    etapa: str
    status: str
    status_rotulo: str
    tipo_atendimento: OrderServiceType
    itens_resumo: str
    bairro: str | None
    minutos: int
    atrasado: bool
    valor_total: Decimal
    acoes_disponiveis: list[str]


def _minutos(momento: datetime, desde: datetime) -> int:
    return max(0, int((momento - desde).total_seconds() // 60))


def fila_do_dia(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> FilaDoDia:
    momento = periodo.agora_em_utc(agora)
    dia = periodo.janelas_comparaveis(agora)[0].dia
    inicio_dia, fim_dia = periodo.intervalo_do_dia_em_utc(dia)

    por_codigo = dict(
        db.query(OrderStatus.code, func.count(Order.id))
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(Order.restaurant_id == restaurant_id, OrderStatus.code.in_(STATUS_ATIVOS))
        .group_by(OrderStatus.code)
        .all()
    )
    contagem = {
        etapa: sum(por_codigo.get(codigo, 0) for codigo in codigos)
        for etapa, codigos in ETAPAS.items()
    }

    mais_antigo = (
        db.query(func.min(Order.order_datetime))
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(Order.restaurant_id == restaurant_id, OrderStatus.code == pedido_fluxo.CRIADO)
        .scalar()
    )
    espera = _minutos(momento, mais_antigo) if mais_antigo is not None else None

    entregues = (
        db.query(func.count(distinct(OrderStatusHistory.order_id)))
        .select_from(OrderStatusHistory)
        .join(Order, Order.id == OrderStatusHistory.order_id)
        .join(OrderStatus, OrderStatus.id == OrderStatusHistory.new_status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            OrderStatus.code.in_(CONCLUIDOS),
            OrderStatusHistory.changed_at >= inicio_dia,
            OrderStatusHistory.changed_at < fim_dia,
        )
        .scalar()
    )

    return FilaDoDia(
        novos=contagem[ETAPA_NOVOS],
        preparo=contagem[ETAPA_PREPARO],
        saindo=contagem[ETAPA_SAINDO],
        entregues=int(entregues or 0),
        espera_mais_antiga_min=espera,
    )


def _resumo_itens(itens: list[OrderItem]) -> str:
    ordenados = sorted(itens, key=lambda item: (-item.subtotal, item.food_name))
    textos = [f"{item.quantity}x {item.food_name}" for item in ordenados[:ITENS_NO_RESUMO]]
    resumo = ", ".join(textos)
    restantes = len(ordenados) - ITENS_NO_RESUMO
    if restantes > 0:
        resumo += f" e mais {restantes}"
    return resumo


def em_andamento(
    db: Session,
    restaurant_id: uuid.UUID,
    limite: int = LIMITE_PADRAO,
    agora: datetime | None = None,
    atrasos: dict[uuid.UUID, AtrasoPedido] | None = None,
) -> list[PedidoEmAndamento]:
    if atrasos is None:
        atrasos = atrasos_dos_pedidos(db, restaurant_id, agora)
    momento = periodo.agora_em_utc(agora)

    pedidos = (
        db.query(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .options(selectinload(Order.items))
        .filter(Order.restaurant_id == restaurant_id, OrderStatus.code.in_(STATUS_ATIVOS))
        .order_by(Order.order_datetime.asc(), Order.order_number.asc())
        .limit(limite)
        .all()
    )

    return [
        PedidoEmAndamento(
            pedido_id=pedido.id,
            numero_pedido=pedido.order_number,
            cliente_nome=pedido.client.name,
            etapa=ETAPA_POR_STATUS[pedido.status.code],
            status=pedido.status.code,
            status_rotulo=pedido_fluxo.rotulo(
                pedido.service_type, pedido.status.code, pedido.status.name
            ),
            tipo_atendimento=pedido.service_type,
            itens_resumo=_resumo_itens(pedido.items),
            bairro=pedido.address_neighborhood,
            minutos=_minutos(momento, pedido.order_datetime),
            atrasado=pedido.id in atrasos,
            valor_total=pedido.total_amount,
            acoes_disponiveis=pedido_fluxo.acoes_disponiveis(
                pedido.service_type, pedido.status.code
            ),
        )
        for pedido in pedidos
    ]