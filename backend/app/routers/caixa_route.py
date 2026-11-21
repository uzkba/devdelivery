import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.caixa_schemas import (
    AbrirCaixaIn,
    CaixaDiaOut,
    FechamentoDetalheOut,
    FecharCaixaIn,
    HistoricoOut,
    MovimentosOut,
    ReabrirCaixaIn,
)
from app.services import caixa_dia_service, caixa_historico_service

router = APIRouter(prefix="/caixa", tags=["Caixa"])


@router.post("/abrir", response_model=CaixaDiaOut, status_code=status.HTTP_201_CREATED)
def abrir_caixa(
    payload: AbrirCaixaIn | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    dia = payload.data if payload else None
    caixa = caixa_dia_service.abrir_caixa(db, current_user.restaurant_id, dia, current_user.id)
    return caixa_dia_service.resumo_do_dia(db, current_user.restaurant_id, caixa.business_date)


@router.get("/dia", response_model=CaixaDiaOut)
def caixa_do_dia(
    data: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    return caixa_dia_service.resumo_do_dia(db, current_user.restaurant_id, data)


@router.post("/fechar", response_model=CaixaDiaOut)
def fechar_caixa(
    payload: FecharCaixaIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    return caixa_dia_service.fechar(db, current_user.restaurant_id, payload, current_user.id)


@router.post("/reabrir", response_model=CaixaDiaOut)
def reabrir_caixa(
    payload: ReabrirCaixaIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    caixa = caixa_dia_service.reabrir_caixa(
        db, current_user.restaurant_id, payload.data, current_user.id
    )
    return caixa_dia_service.resumo_do_dia(db, current_user.restaurant_id, caixa.business_date)


@router.get("/movimentos", response_model=MovimentosOut)
def movimentos_do_dia(
    data: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    return caixa_historico_service.listar_movimentos(
        db, current_user.restaurant_id, data, page, page_size
    )


@router.get("/historico", response_model=HistoricoOut)
def historico_de_fechamentos(
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    com_diferenca: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    return caixa_historico_service.listar_historico(
        db, current_user.restaurant_id, page, page_size, data_inicio, data_fim, com_diferenca
    )


@router.get("/historico/{fechamento_id}", response_model=FechamentoDetalheOut)
def detalhe_do_fechamento(
    fechamento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "caixa")),
):
    return caixa_historico_service.detalhe_fechamento(
        db, current_user.restaurant_id, fechamento_id
    )