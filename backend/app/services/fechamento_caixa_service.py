import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.model.models import CashClosing, Order, OrderStatus, PaymentMethod
from backend.app.schemas.fechamento_caixa_schemas import CashClosingCreate

_PAYMENT_CODE_TO_COLUMN = {
    "PIX": "total_pix",
    "DINHEIRO": "total_cash",
    "CARTAO_DEBITO": "total_debit",
    "CARTAO_CREDITO": "total_credit",
}


def _periodo_para_intervalo(start_date: date, end_date: date):
    inicio = datetime.combine(start_date, time.min)
    fim = datetime.combine(end_date, time.min) + timedelta(days=1)
    return inicio, fim


def _pedidos_pagos_query(db: Session, restaurant_id: uuid.UUID, start_date: date, end_date: date):
    inicio, fim = _periodo_para_intervalo(start_date, end_date)
    return (
        db.query(Order)
        .join(OrderStatus, Order.status_id == OrderStatus.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            OrderStatus.is_paid.is_(True),
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
        )
    )


def gerar_fechamento(db: Session, payload: CashClosingCreate, closed_by: uuid.UUID) -> CashClosing:
    if payload.data_fim < payload.data_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="data_fim não pode ser anterior a data_inicio.",
        )

    pedidos = _pedidos_pagos_query(db, payload.restaurante_id, payload.data_inicio, payload.data_fim).all()

    payment_methods = {pm.id: pm.code for pm in db.query(PaymentMethod).all()}

    totals = {
        "total_pix": Decimal("0"),
        "total_cash": Decimal("0"),
        "total_debit": Decimal("0"),
        "total_credit": Decimal("0"),
        "total_other": Decimal("0"),
    }
    total_cash_paid = Decimal("0")
    total_change = Decimal("0")
    total_sales = Decimal("0")

    for pedido in pedidos:
        code = payment_methods.get(pedido.payment_method_id)
        coluna = _PAYMENT_CODE_TO_COLUMN.get(code, "total_other")
        totals[coluna] += pedido.total_amount
        total_sales += pedido.total_amount
        if code == "DINHEIRO":
            total_cash_paid += pedido.cash_paid_amount or Decimal("0")
            total_change += pedido.change_amount or Decimal("0")

    inicio, fim = _periodo_para_intervalo(payload.data_inicio, payload.data_fim)
    cancelled_count = (
        db.query(func.count(Order.id))
        .join(OrderStatus, Order.status_id == OrderStatus.id)
        .filter(
            Order.restaurant_id == payload.restaurante_id,
            OrderStatus.code == "CANCELADO",
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
        )
        .scalar()
    ) or 0

    expected_amount = totals["total_cash"]
    difference = payload.reported_amount - expected_amount

    fechamento = CashClosing(
        restaurant_id=payload.restaurante_id,
        start_date=payload.data_inicio,
        end_date=payload.data_fim,
        total_sales=total_sales,
        total_pix=totals["total_pix"],
        total_cash=totals["total_cash"],
        total_debit=totals["total_debit"],
        total_credit=totals["total_credit"],
        total_other=totals["total_other"],
        total_cash_paid=total_cash_paid,
        total_change=total_change,
        order_count=len(pedidos),
        cancelled_count=cancelled_count,
        expected_amount=expected_amount,
        reported_amount=payload.reported_amount,
        difference=difference,
        closed_by=closed_by,
        notes=payload.observacoes,
    )

    db.add(fechamento)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um fechamento de caixa para esse restaurante e período.",
        )
    db.refresh(fechamento)
    return fechamento


def listar_fechamentos(db: Session, restaurant_id: uuid.UUID, page: int, page_size: int):
    query = db.query(CashClosing).filter(CashClosing.restaurant_id == restaurant_id)
    total = query.count()
    items = (
        query.order_by(CashClosing.start_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def buscar_fechamento_por_id(db: Session, fechamento_id: uuid.UUID, restaurant_id: uuid.UUID) -> CashClosing:
    fechamento = (
        db.query(CashClosing)
        .filter(CashClosing.id == fechamento_id, CashClosing.restaurant_id == restaurant_id)
        .first()
    )
    if not fechamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento de caixa não encontrado.")
    return fechamento