import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import periodo
from app.core.tempo import agora_local
from app.model.models import Client, Order, OrderServiceType, OrderStatus
from app.services import pedido_fluxo
from app.services.painel_alertas_service import (
    DESTINO_PEDIDOS,
    GRAVIDADE_AVISO,
    GRAVIDADE_CRITICO,
    Alerta,
    alertas_de_atencao,
    atrasos_dos_pedidos,
)

TIPO_PEDIDO_NOVO = "PEDIDO_NOVO"
LIMITE_PADRAO = 20

_ROTULO_ATENDIMENTO = {
    OrderServiceType.DELIVERY: "Entrega",
    OrderServiceType.PICKUP: "Retirada",
}


@dataclass(frozen=True)
class Aviso:
    tipo: str
    gravidade: str
    titulo: str
    detalhe: str
    destino: str
    quantidade: int
    pedido_id: uuid.UUID | None = None
    numero_pedido: int | None = None
    minutos: int | None = None


@dataclass(frozen=True)
class Avisos:
    total: int
    avisos: list[Aviso]


def _minutos(momento: datetime, desde: datetime) -> int:
    return max(0, int((momento - desde).total_seconds() // 60))


def _aviso_de_alerta(alerta: Alerta) -> Aviso:
    return Aviso(
        tipo=alerta.codigo,
        gravidade=alerta.gravidade,
        titulo=alerta.titulo,
        detalhe=alerta.detalhe,
        destino=alerta.destino,
        quantidade=alerta.quantidade,
    )


def _filtros_novos(restaurant_id: uuid.UUID):
    return (Order.restaurant_id == restaurant_id, OrderStatus.code == pedido_fluxo.CRIADO)


def avisos_do_painel(
    db: Session,
    restaurant_id: uuid.UUID,
    limite: int = LIMITE_PADRAO,
    agora: datetime | None = None,
) -> Avisos:
    momento = agora_local(agora)
    momento_utc = periodo.agora_em_utc(momento)

    atrasos = atrasos_dos_pedidos(db, restaurant_id, momento)
    alertas = alertas_de_atencao(db, restaurant_id, momento, atrasos)

    novos_total = int(
        db.query(func.count(Order.id))
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(*_filtros_novos(restaurant_id))
        .scalar()
        or 0
    )
    linhas = (
        db.query(
            Order.id,
            Order.order_number,
            Order.order_datetime,
            Order.service_type,
            Client.name,
        )
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .join(Client, Client.id == Order.client_id)
        .filter(*_filtros_novos(restaurant_id))
        .order_by(Order.order_datetime.asc(), Order.order_number.asc())
        .limit(limite)
        .all()
    )

    novos = [
        Aviso(
            tipo=TIPO_PEDIDO_NOVO,
            gravidade=GRAVIDADE_CRITICO if pedido_id in atrasos else GRAVIDADE_AVISO,
            titulo=f"Pedido #{numero} aguardando aceite",
            detalhe=f"{cliente} · {_ROTULO_ATENDIMENTO[tipo]}",
            destino=DESTINO_PEDIDOS,
            quantidade=1,
            pedido_id=pedido_id,
            numero_pedido=numero,
            minutos=_minutos(momento_utc, criado_em),
        )
        for pedido_id, numero, criado_em, tipo, cliente in linhas
    ]

    criticos = [_aviso_de_alerta(a) for a in alertas if a.gravidade == GRAVIDADE_CRITICO]
    demais = [_aviso_de_alerta(a) for a in alertas if a.gravidade != GRAVIDADE_CRITICO]

    return Avisos(total=novos_total + len(alertas), avisos=[*criticos, *novos, *demais])