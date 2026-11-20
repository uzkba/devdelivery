import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.core import periodo
from app.core.tempo import FUSO_LOCAL
from app.model.models import Order, OrderStatus, PaymentMethod
from app.schemas.relatorio_schemas import (
    HoraDePicoOut,
    HorariosDePicoOut,
    ItemCampeaoOut,
    ItensCampeoesOut,
    RelatorioVendasOut,
    VendaDiaOut,
    VendaFormaOut,
    VendaTipoOut,
)
from app.services import painel_ranking_service
from app.services.painel_resumo_service import NAO_FATURAVEIS

MAX_DIAS = 366
CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")
QUANTIDADE_PICOS = 3

MOMENTO_LOCAL = func.timezone(str(FUSO_LOCAL), func.timezone("UTC", Order.order_datetime))


def _erro(mensagem: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensagem)


def _dinheiro(valor) -> Decimal:
    return Decimal(valor).quantize(CENTAVO)


def _ticket(total: Decimal, quantidade: int) -> Decimal:
    if quantidade == 0:
        return ZERO
    return (total / quantidade).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _janela(data_inicio: date, data_fim: date) -> tuple[datetime, datetime]:
    if data_fim < data_inicio:
        raise _erro("data_fim não pode ser anterior a data_inicio.")
    if (data_fim - data_inicio).days + 1 > MAX_DIAS:
        raise _erro(f"O período deve ter no máximo {MAX_DIAS} dias.")
    inicio = periodo.intervalo_do_dia_em_utc(data_inicio)[0]
    fim = periodo.intervalo_do_dia_em_utc(data_fim)[1]
    return inicio, fim


def _base(db: Session, restaurant_id: uuid.UUID, inicio: datetime, fim: datetime, *colunas):
    return (
        db.query(*colunas)
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.notin_(NAO_FATURAVEIS),
        )
    )


def vendas_por_periodo(
    db: Session, restaurant_id: uuid.UUID, data_inicio: date, data_fim: date
) -> RelatorioVendasOut:
    inicio, fim = _janela(data_inicio, data_fim)

    dia_local = cast(MOMENTO_LOCAL, Date)
    linhas_dia = (
        _base(
            db,
            restaurant_id,
            inicio,
            fim,
            dia_local,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .group_by(dia_local)
        .all()
    )
    por_data = {dia: (quantidade, _dinheiro(total)) for dia, quantidade, total in linhas_dia}

    por_dia = []
    dia = data_inicio
    while dia <= data_fim:
        quantidade, total = por_data.get(dia, (0, ZERO))
        por_dia.append(
            VendaDiaOut(
                data=dia,
                quantidade_pedidos=quantidade,
                total_vendas=total,
                ticket_medio=_ticket(total, quantidade),
            )
        )
        dia += timedelta(days=1)

    quantidade_total = sum(item.quantidade_pedidos for item in por_dia)
    total_vendas = sum((item.total_vendas for item in por_dia), ZERO)

    linhas_forma = (
        _base(
            db,
            restaurant_id,
            inicio,
            fim,
            PaymentMethod.code,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .join(PaymentMethod, PaymentMethod.id == Order.payment_method_id)
        .group_by(PaymentMethod.code)
        .order_by(func.sum(Order.total_amount).desc(), PaymentMethod.code)
        .all()
    )

    linhas_tipo = (
        _base(
            db,
            restaurant_id,
            inicio,
            fim,
            Order.service_type,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .group_by(Order.service_type)
        .order_by(func.sum(Order.total_amount).desc())
        .all()
    )

    return RelatorioVendasOut(
        data_inicio=data_inicio,
        data_fim=data_fim,
        quantidade_pedidos=quantidade_total,
        total_vendas=total_vendas,
        ticket_medio=_ticket(total_vendas, quantidade_total),
        por_dia=por_dia,
        por_forma_pagamento=[
            VendaFormaOut(forma=codigo, quantidade_pedidos=quantidade, total_vendas=_dinheiro(total))
            for codigo, quantidade, total in linhas_forma
        ],
        por_tipo_atendimento=[
            VendaTipoOut(
                tipo_atendimento=getattr(tipo, "value", tipo),
                quantidade_pedidos=quantidade,
                total_vendas=_dinheiro(total),
            )
            for tipo, quantidade, total in linhas_tipo
        ],
    )


def itens_campeoes(
    db: Session, restaurant_id: uuid.UUID, data_inicio: date, data_fim: date, limite: int
) -> ItensCampeoesOut:
    inicio, fim = _janela(data_inicio, data_fim)
    itens = painel_ranking_service.mais_vendidos_no_periodo(db, restaurant_id, inicio, fim, limite)
    return ItensCampeoesOut(
        data_inicio=data_inicio,
        data_fim=data_fim,
        items=[
            ItemCampeaoOut(
                posicao=posicao,
                tipo=item.tipo,
                item_id=item.item_id,
                nome=item.nome,
                quantidade=item.quantidade,
            )
            for posicao, item in enumerate(itens, start=1)
        ],
    )


def horarios_de_pico(
    db: Session, restaurant_id: uuid.UUID, data_inicio: date, data_fim: date
) -> HorariosDePicoOut:
    inicio, fim = _janela(data_inicio, data_fim)

    hora_local = func.extract("hour", MOMENTO_LOCAL)
    linhas = (
        _base(
            db,
            restaurant_id,
            inicio,
            fim,
            hora_local,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .group_by(hora_local)
        .all()
    )
    por_hora = {int(hora): (quantidade, _dinheiro(total)) for hora, quantidade, total in linhas}

    horas = []
    for hora in range(24):
        quantidade, total = por_hora.get(hora, (0, ZERO))
        horas.append(HoraDePicoOut(hora=hora, quantidade_pedidos=quantidade, total_vendas=total))

    picos = sorted(
        (item for item in horas if item.quantidade_pedidos > 0),
        key=lambda item: (-item.quantidade_pedidos, item.hora),
    )[:QUANTIDADE_PICOS]

    return HorariosDePicoOut(data_inicio=data_inicio, data_fim=data_fim, horas=horas, picos=picos)