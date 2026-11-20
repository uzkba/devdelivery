import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.core import periodo
from app.model.models import Order, OrderItem, OrderStatus
from app.services.painel_resumo_service import NAO_FATURAVEIS

TIPO_MARMITA = "MARMITA"
TIPO_COMBO = "COMBO"
TIPO_AVULSO = "AVULSO"


@dataclass(frozen=True)
class ItemMaisVendido:
    tipo: str
    item_id: uuid.UUID | None
    nome: str
    quantidade: int


def _tipo_e_id(meal_box_id, combo_id, food_id) -> tuple[str, uuid.UUID | None]:
    if meal_box_id is not None:
        return TIPO_MARMITA, meal_box_id
    if combo_id is not None:
        return TIPO_COMBO, combo_id
    return TIPO_AVULSO, food_id


def mais_vendidos_no_periodo(
    db: Session,
    restaurant_id: uuid.UUID,
    inicio: datetime,
    fim: datetime,
    limite: int = 3,
) -> list[ItemMaisVendido]:
    nome_do_orfao = case(
        (
            and_(
                OrderItem.meal_box_id.is_(None),
                OrderItem.combo_id.is_(None),
                OrderItem.food_id.is_(None),
            ),
            OrderItem.food_name,
        ),
        else_=None,
    )
    quantidade = func.sum(OrderItem.quantity)
    nome = func.max(OrderItem.food_name)

    linhas = (
        db.query(
            OrderItem.meal_box_id,
            OrderItem.combo_id,
            OrderItem.food_id,
            nome.label("nome"),
            quantidade.label("quantidade"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.notin_(NAO_FATURAVEIS),
        )
        .group_by(
            OrderItem.meal_box_id, OrderItem.combo_id, OrderItem.food_id, nome_do_orfao
        )
        .order_by(quantidade.desc(), nome)
        .limit(limite)
        .all()
    )

    resultado = []
    for meal_box_id, combo_id, food_id, nome_item, total in linhas:
        tipo, item_id = _tipo_e_id(meal_box_id, combo_id, food_id)
        resultado.append(
            ItemMaisVendido(tipo=tipo, item_id=item_id, nome=nome_item, quantidade=int(total))
        )
    return resultado


def mais_vendidos_hoje(
    db: Session,
    restaurant_id: uuid.UUID,
    limite: int = 3,
    agora: datetime | None = None,
) -> list[ItemMaisVendido]:
    janela, _ = periodo.janelas_comparaveis(agora)
    return mais_vendidos_no_periodo(db, restaurant_id, janela.inicio, janela.fim, limite)