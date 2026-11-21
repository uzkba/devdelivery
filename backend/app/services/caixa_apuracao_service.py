import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import periodo
from app.model.models import Order, OrderStatus, PaymentMethod

STATUS_VENDA = ("ENTREGUE", "RETIRADO")
STATUS_CANCELADO = "CANCELADO"

FORMA_DINHEIRO = "DINHEIRO"
FORMA_OUTROS = "OUTROS"
FORMAS = ("DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO")
CHAVES_FORMA = (*FORMAS, FORMA_OUTROS)

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class TotalForma:
    codigo: str
    quantidade: int
    total: Decimal


@dataclass(frozen=True)
class Apuracao:
    dia: date
    quantidade_pedidos: int
    quantidade_cancelados: int
    total_vendas: Decimal
    por_forma: dict[str, TotalForma]
    total_dinheiro_recebido: Decimal
    total_troco: Decimal


def apurar_dia(db: Session, restaurant_id: uuid.UUID, dia: date) -> Apuracao:
    inicio, fim = periodo.intervalo_do_dia_em_utc(dia)

    linhas = (
        db.query(
            OrderStatus.code,
            PaymentMethod.code,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.sum(Order.cash_paid_amount), 0),
            func.coalesce(func.sum(Order.change_amount), 0),
        )
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .join(PaymentMethod, PaymentMethod.id == Order.payment_method_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.in_((*STATUS_VENDA, STATUS_CANCELADO)),
        )
        .group_by(OrderStatus.code, PaymentMethod.code)
        .all()
    )

    quantidades = {chave: 0 for chave in CHAVES_FORMA}
    totais = {chave: ZERO for chave in CHAVES_FORMA}
    cancelados = 0
    recebido = ZERO
    troco = ZERO

    for status_codigo, forma_codigo, quantidade, total, pago, devolvido in linhas:
        if status_codigo == STATUS_CANCELADO:
            cancelados += quantidade
            continue
        chave = forma_codigo if forma_codigo in FORMAS else FORMA_OUTROS
        quantidades[chave] += quantidade
        totais[chave] += Decimal(total)
        if forma_codigo == FORMA_DINHEIRO:
            recebido += Decimal(pago)
            troco += Decimal(devolvido)

    por_forma = {
        chave: TotalForma(codigo=chave, quantidade=quantidades[chave], total=totais[chave])
        for chave in CHAVES_FORMA
    }

    return Apuracao(
        dia=dia,
        quantidade_pedidos=sum(quantidades.values()),
        quantidade_cancelados=cancelados,
        total_vendas=sum(totais.values(), ZERO),
        por_forma=por_forma,
        total_dinheiro_recebido=recebido,
        total_troco=troco,
    )