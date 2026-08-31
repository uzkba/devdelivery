import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import require_role
from app.model.models import CashClosing
from app.schemas.fechamento_caixa_schemas import (
    CashClosingCreate, CashClosingOut, PaginatedCashClosingsOut,
)
from app.services import fechamento_caixa_service

router = APIRouter(prefix="/fechamento-caixa", tags=["Fechamento de Caixa"])


def _to_out(fechamento: CashClosing) -> CashClosingOut:
    return CashClosingOut(
        id=fechamento.id,
        restaurante_id=fechamento.restaurant_id,
        data_inicio=fechamento.start_date,
        data_fim=fechamento.end_date,
        total_vendas=fechamento.total_sales,
        quantidade_pedidos=fechamento.order_count,
        quantidade_cancelados=fechamento.cancelled_count,
        totais_por_forma_pagamento={
            "PIX": fechamento.total_pix,
            "DINHEIRO": fechamento.total_cash,
            "CARTAO_DEBITO": fechamento.total_debit,
            "CARTAO_CREDITO": fechamento.total_credit,
            "OUTROS": fechamento.total_other,
        },
        total_dinheiro_recebido=fechamento.total_cash_paid,
        total_troco=fechamento.total_change,
        valor_esperado=fechamento.expected_amount,
        valor_informado=fechamento.reported_amount,
        diferenca=fechamento.difference,
        fechado_por=fechamento.closed_by,
        fechado_em=fechamento.closed_at,
        observacoes=fechamento.notes,
    )


@router.post("", response_model=CashClosingOut, status_code=status.HTTP_201_CREATED)
def gerar_fechamento(
    payload: CashClosingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    fechamento = fechamento_caixa_service.gerar_fechamento(db, payload, current_user.id)
    return _to_out(fechamento)


@router.get("", response_model=PaginatedCashClosingsOut)
def listar_fechamentos(
    restaurante_id: uuid.UUID | None = Query(
        None, description="Reservado para uso futuro com múltiplos restaurantes por usuário; hoje ignorado."
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    items, total = fechamento_caixa_service.listar_fechamentos(
        db, current_user.restaurant_id, page, page_size
    )
    return PaginatedCashClosingsOut(
        items=[_to_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/{fechamento_id}", response_model=CashClosingOut)
def buscar_fechamento(
    fechamento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    fechamento = fechamento_caixa_service.buscar_fechamento_por_id(
        db, fechamento_id, current_user.restaurant_id
    )
    return _to_out(fechamento)