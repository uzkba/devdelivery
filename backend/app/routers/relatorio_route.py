from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.depedencias import get_current_user, get_db
from app.services import relatorio_service
from app.schemas.relatorio_schemas import RelatorioPedidosOut

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@router.get("/pedidos", response_model=RelatorioPedidosOut)
def relatorio_pedidos(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    cliente_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data_fim < data_inicio:
        raise HTTPException(
            status_code=422,
            detail="data_fim deve ser maior ou igual a data_inicio",
        )

    try:
        return relatorio_service.get_relatorio_pedidos(
            db=db,
            restaurant_id=current_user.restaurant_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            cliente_id=cliente_id,
        )
    except relatorio_service.ClienteNaoEncontrado:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")