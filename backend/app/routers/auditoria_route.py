from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import require_role
from app.model.models import AuditLog
from app.schemas.auditoria_schemas import AuditLogOut

router = APIRouter(prefix="/logs-auditoria", tags=["auditoria"])


@router.get("", response_model=list[AuditLogOut])
def listar_logs_auditoria(
    entidade: str | None = None,
    usuario_responsavel: UUID | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    if data_inicio and data_fim and data_fim < data_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_fim não pode ser anterior a data_inicio.",
        )

    query = db.query(AuditLog).filter(
        AuditLog.restaurant_id == current_user.restaurant_id
    )
    if entidade:
        query = query.filter(AuditLog.entity == entidade)
    if usuario_responsavel:
        query = query.filter(AuditLog.user_id == usuario_responsavel)
    if data_inicio:
        query = query.filter(AuditLog.created_at >= data_inicio)
    if data_fim:
        query = query.filter(AuditLog.created_at < data_fim)

    return (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )