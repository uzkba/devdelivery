import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import periodo
from app.core.tempo import hoje_local
from app.model.models import (
    Combo,
    Food,
    MealBox,
    Order,
    OrderServiceType,
    OrderStatus,
    OrderStatusHistory,
    RestaurantDeliverySettings,
)
from app.services import pedido_fluxo
from app.services.painel_ranking_service import TIPO_AVULSO, TIPO_COMBO, TIPO_MARMITA

ALERTA_PEDIDO_ATRASADO = "PEDIDO_ATRASADO"
ALERTA_ITENS_INDISPONIVEIS = "ITENS_INDISPONIVEIS"

GRAVIDADE_CRITICO = "CRITICO"
GRAVIDADE_AVISO = "AVISO"

DESTINO_PEDIDOS = "pedidos"
DESTINO_CARDAPIO = "cardapio"

MOTIVO_PARADO = "PARADO"
MOTIVO_TEMPO_ESTIMADO = "TEMPO_ESTIMADO"

MOTIVO_ESGOTADO_HOJE = "ESGOTADO_HOJE"
MOTIVO_COMPONENTE_INATIVO = "COMPONENTE_INATIVO"

LIMITE_PARADO_MIN = {
    pedido_fluxo.CRIADO: 10,
    pedido_fluxo.CONFIRMADO: 10,
    pedido_fluxo.PRONTO: 10,
}
LIMITE_SEM_ESTIMATIVA_MIN = {
    pedido_fluxo.EM_PREPARO: 30,
    pedido_fluxo.SAIU_PARA_ENTREGA: 45,
}
STATUS_ATIVOS = pedido_fluxo.ABAS["novos"] | pedido_fluxo.ABAS["em_andamento"]


@dataclass(frozen=True)
class AtrasoPedido:
    pedido_id: uuid.UUID
    numero_pedido: int
    status: str
    motivo: str
    minutos: int
    limite_min: int


@dataclass(frozen=True)
class ItemIndisponivel:
    tipo: str
    item_id: uuid.UUID
    nome: str
    motivo: str


@dataclass(frozen=True)
class Alerta:
    codigo: str
    gravidade: str
    titulo: str
    detalhe: str
    destino: str
    quantidade: int


def _estimativa(config: RestaurantDeliverySettings | None, tipo: OrderServiceType) -> int | None:
    if config is None:
        return None
    if tipo == OrderServiceType.PICKUP:
        return config.pickup_time_minutes
    return config.delivery_time_minutes


def _avaliar(
    pedido_id: uuid.UUID,
    numero: int,
    codigo: str,
    tipo: OrderServiceType,
    criado_em: datetime,
    ultima_mudanca: datetime | None,
    agora: datetime,
    config: RestaurantDeliverySettings | None,
) -> AtrasoPedido | None:
    referencia = ultima_mudanca or criado_em

    if codigo in LIMITE_PARADO_MIN:
        if codigo == pedido_fluxo.PRONTO and tipo == OrderServiceType.PICKUP:
            return None
        motivo, inicio, limite = MOTIVO_PARADO, referencia, LIMITE_PARADO_MIN[codigo]
    else:
        estimativa = _estimativa(config, tipo)
        if estimativa is not None:
            motivo, inicio, limite = MOTIVO_TEMPO_ESTIMADO, criado_em, estimativa
        else:
            motivo, inicio, limite = MOTIVO_PARADO, referencia, LIMITE_SEM_ESTIMATIVA_MIN[codigo]

    decorrido = agora - inicio
    if decorrido <= timedelta(minutes=limite):
        return None
    return AtrasoPedido(
        pedido_id=pedido_id,
        numero_pedido=numero,
        status=codigo,
        motivo=motivo,
        minutos=int(decorrido.total_seconds() // 60),
        limite_min=limite,
    )


def atrasos_dos_pedidos(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> dict[uuid.UUID, AtrasoPedido]:
    momento = periodo.agora_em_utc(agora)
    config = (
        db.query(RestaurantDeliverySettings)
        .filter(RestaurantDeliverySettings.restaurant_id == restaurant_id)
        .first()
    )
    ultima_mudanca = (
        db.query(func.max(OrderStatusHistory.changed_at))
        .filter(OrderStatusHistory.order_id == Order.id)
        .correlate(Order)
        .scalar_subquery()
    )
    linhas = (
        db.query(
            Order.id,
            Order.order_number,
            Order.service_type,
            Order.order_datetime,
            OrderStatus.code,
            ultima_mudanca.label("ultima_mudanca"),
        )
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(Order.restaurant_id == restaurant_id, OrderStatus.code.in_(STATUS_ATIVOS))
        .all()
    )

    atrasos = {}
    for pedido_id, numero, tipo, criado_em, codigo, ultima in linhas:
        atraso = _avaliar(pedido_id, numero, codigo, tipo, criado_em, ultima, momento, config)
        if atraso is not None:
            atrasos[pedido_id] = atraso
    return atrasos


def itens_indisponiveis_hoje(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> list[ItemIndisponivel]:
    hoje = hoje_local(agora)
    itens: dict[uuid.UUID, ItemIndisponivel] = {}

    marmitas = db.query(MealBox).filter(
        MealBox.restaurant_id == restaurant_id,
        MealBox.is_active.is_(True),
        MealBox.sold_out_on == hoje,
    )
    for marmita in marmitas:
        itens[marmita.id] = ItemIndisponivel(
            TIPO_MARMITA, marmita.id, marmita.name, MOTIVO_ESGOTADO_HOJE
        )

    alimentos = db.query(Food).filter(
        Food.restaurant_id == restaurant_id,
        Food.is_active.is_(True),
        Food.sold_out_on == hoje,
    )
    for alimento in alimentos:
        itens[alimento.id] = ItemIndisponivel(
            TIPO_AVULSO, alimento.id, alimento.name, MOTIVO_ESGOTADO_HOJE
        )

    combos = db.query(Combo).filter(Combo.restaurant_id == restaurant_id, Combo.is_active.is_(True))
    for combo in combos:
        if combo.sold_out_on == hoje:
            itens[combo.id] = ItemIndisponivel(
                TIPO_COMBO, combo.id, combo.name, MOTIVO_ESGOTADO_HOJE
            )
        elif combo.has_inactive_items:
            itens[combo.id] = ItemIndisponivel(
                TIPO_COMBO, combo.id, combo.name, MOTIVO_COMPONENTE_INATIVO
            )

    return sorted(itens.values(), key=lambda item: item.nome.lower())


def _listar(textos: list[str]) -> str:
    if len(textos) > 3:
        return f"{textos[0]}, {textos[1]} e mais {len(textos) - 2}"
    if len(textos) == 1:
        return textos[0]
    return ", ".join(textos[:-1]) + " e " + textos[-1]


def _titulo(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _alertas_de_pedidos(atrasos: dict[uuid.UUID, AtrasoPedido]) -> list[Alerta]:
    if not atrasos:
        return []
    ordenados = sorted(atrasos.values(), key=lambda a: (-a.minutos, a.numero_pedido))
    if len(ordenados) == 1:
        unico = ordenados[0]
        if unico.motivo == MOTIVO_TEMPO_ESTIMADO:
            detalhe = f"#{unico.numero_pedido} passou do tempo estimado de {unico.limite_min} min"
        else:
            detalhe = f"#{unico.numero_pedido} está parado há {unico.minutos} min"
    else:
        numeros = [f"#{a.numero_pedido}" for a in ordenados]
        detalhe = f"{_listar(numeros)} passaram do tempo esperado"
    return [
        Alerta(
            codigo=ALERTA_PEDIDO_ATRASADO,
            gravidade=GRAVIDADE_CRITICO,
            titulo=_titulo(len(ordenados), "pedido atrasado", "pedidos atrasados"),
            detalhe=detalhe,
            destino=DESTINO_PEDIDOS,
            quantidade=len(ordenados),
        )
    ]


def _alertas_de_itens(itens: list[ItemIndisponivel]) -> list[Alerta]:
    if not itens:
        return []
    return [
        Alerta(
            codigo=ALERTA_ITENS_INDISPONIVEIS,
            gravidade=GRAVIDADE_AVISO,
            titulo=_titulo(len(itens), "item indisponível hoje", "itens indisponíveis hoje"),
            detalhe=_listar([item.nome for item in itens]),
            destino=DESTINO_CARDAPIO,
            quantidade=len(itens),
        )
    ]


def _alertas_de_caixa(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None
) -> list[Alerta]:
    return []


def alertas_de_atencao(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> list[Alerta]:
    return [
        *_alertas_de_pedidos(atrasos_dos_pedidos(db, restaurant_id, agora)),
        *_alertas_de_itens(itens_indisponiveis_hoje(db, restaurant_id, agora)),
        *_alertas_de_caixa(db, restaurant_id, agora),
    ]