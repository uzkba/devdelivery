import math
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from app.core import periodo
from app.core.tempo import hoje_local
from app.model.models import (
    AdminUser,
    CashClosing,
    CashClosingDriver,
    CashClosingMethod,
    Order,
    OrderStatus,
    PaymentMethod,
)
from app.schemas.caixa_schemas import (
    EntregadorOut,
    FechamentoDetalheOut,
    FechamentoResumoOut,
    FormaOut,
    HistoricoOut,
    MovimentoOut,
    MovimentosOut,
)
from app.services import caixa_apuracao_service as apuracao_service
from app.services import caixa_fechamento_service as fechamento_service

STATUS_MOVIMENTO = (*apuracao_service.STATUS_VENDA, apuracao_service.STATUS_CANCELADO)

TEM_DIFERENCA = or_(
    CashClosing.difference != 0,
    exists()
    .where(CashClosingMethod.closing_id == CashClosing.id, CashClosingMethod.difference != 0)
    .correlate(CashClosing),
    exists()
    .where(CashClosingDriver.closing_id == CashClosing.id, CashClosingDriver.difference != 0)
    .correlate(CashClosing),
)


def _erro(codigo: int, mensagem: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=mensagem)


def _consulta(db: Session, restaurant_id: uuid.UUID):
    return (
        db.query(CashClosing, AdminUser.name, TEM_DIFERENCA.label("tem_diferenca"))
        .outerjoin(AdminUser, AdminUser.id == CashClosing.closed_by)
        .filter(CashClosing.restaurant_id == restaurant_id)
    )


def _dados_resumo(fechamento: CashClosing, nome: str | None, tem_diferenca: bool) -> dict:
    return dict(
        id=fechamento.id,
        data_inicio=fechamento.start_date,
        data_fim=fechamento.end_date,
        total_vendas=fechamento.total_sales,
        quantidade_pedidos=fechamento.order_count,
        quantidade_cancelados=fechamento.cancelled_count,
        valor_esperado=fechamento.expected_amount,
        valor_informado=fechamento.reported_amount,
        diferenca=fechamento.difference,
        tem_diferenca=bool(tem_diferenca),
        fechado_por=fechamento.closed_by,
        fechado_por_nome=nome,
        fechado_em=fechamento.closed_at,
        observacoes=fechamento.notes,
    )


def listar_historico(
    db: Session,
    restaurant_id: uuid.UUID,
    page: int,
    page_size: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    com_diferenca: bool | None = None,
) -> HistoricoOut:
    if data_inicio is not None and data_fim is not None and data_fim < data_inicio:
        raise _erro(422, "data_fim não pode ser anterior a data_inicio.")

    consulta = _consulta(db, restaurant_id)
    if data_inicio is not None:
        consulta = consulta.filter(CashClosing.end_date >= data_inicio)
    if data_fim is not None:
        consulta = consulta.filter(CashClosing.start_date <= data_fim)
    if com_diferenca is True:
        consulta = consulta.filter(TEM_DIFERENCA)
    elif com_diferenca is False:
        consulta = consulta.filter(~TEM_DIFERENCA)

    total = consulta.count()
    linhas = (
        consulta.order_by(CashClosing.start_date.desc(), CashClosing.closed_at.desc(), CashClosing.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return HistoricoOut(
        items=[
            FechamentoResumoOut(**_dados_resumo(fechamento, nome, tem_diferenca))
            for fechamento, nome, tem_diferenca in linhas
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


def detalhe_fechamento(
    db: Session, restaurant_id: uuid.UUID, fechamento_id: uuid.UUID
) -> FechamentoDetalheOut:
    linha = _consulta(db, restaurant_id).filter(CashClosing.id == fechamento_id).first()
    if linha is None:
        raise _erro(404, "Fechamento de caixa não encontrado.")
    fechamento, nome, tem_diferenca = linha

    formas = [
        FormaOut(
            forma=item.method_code,
            quantidade_pedidos=item.order_count,
            valor_esperado=item.expected_amount,
            valor_contado=item.counted_amount,
            diferenca=item.difference,
        )
        for item in fechamento_service.formas_do_fechamento(db, fechamento.id)
    ]
    entregadores = [
        EntregadorOut(
            entregador_id=item.driver_id,
            nome=item.driver_name,
            quantidade_entregas=item.delivery_count,
            valor_esperado=item.expected_amount,
            valor_repassado=item.handed_amount,
            diferenca=item.difference,
        )
        for item in fechamento_service.entregadores_do_fechamento(db, fechamento.id)
    ]

    return FechamentoDetalheOut(
        **_dados_resumo(fechamento, nome, tem_diferenca),
        total_dinheiro_recebido=fechamento.total_cash_paid,
        total_troco=fechamento.total_change,
        formas=formas,
        entregadores=entregadores,
    )


def listar_movimentos(
    db: Session, restaurant_id: uuid.UUID, dia: date | None, page: int, page_size: int
) -> MovimentosOut:
    alvo = dia or hoje_local()
    inicio, fim = periodo.intervalo_do_dia_em_utc(alvo)

    consulta = (
        db.query(
            Order.id,
            Order.order_number,
            Order.order_datetime,
            Order.address_name,
            OrderStatus.code,
            OrderStatus.name,
            Order.service_type,
            PaymentMethod.code,
            Order.total_amount,
            AdminUser.id,
            AdminUser.name,
        )
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .join(PaymentMethod, PaymentMethod.id == Order.payment_method_id)
        .outerjoin(AdminUser, AdminUser.id == Order.driver_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.in_(STATUS_MOVIMENTO),
        )
    )

    total = consulta.count()
    linhas = (
        consulta.order_by(Order.order_datetime.desc(), Order.order_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    itens = [
        MovimentoOut(
            pedido_id=pedido_id,
            numero_pedido=numero,
            data_hora=momento,
            cliente=cliente,
            status=status_codigo,
            status_nome=status_nome,
            tipo_atendimento=getattr(tipo, "value", tipo),
            forma_pagamento=forma,
            total=valor,
            entregador_id=entregador_id,
            entregador_nome=entregador_nome,
            conta_no_caixa=status_codigo in apuracao_service.STATUS_VENDA,
        )
        for (
            pedido_id,
            numero,
            momento,
            cliente,
            status_codigo,
            status_nome,
            tipo,
            forma,
            valor,
            entregador_id,
            entregador_nome,
        ) in linhas
    ]

    return MovimentosOut(
        data=alvo,
        items=itens,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )