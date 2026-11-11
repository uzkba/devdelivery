from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.pagamento_admin_schemas import FormaPagamentoAdminOut, FormasPagamentoIn
from app.services import pagamento_service as service

router = APIRouter(prefix="/admin/restaurante/pagamentos", tags=["Admin - Pagamentos"])

require_admin = require_role("admin")


@router.get("", response_model=list[FormaPagamentoAdminOut])
def listar_formas_de_pagamento(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.listar_para_admin(db, admin.restaurant_id)


@router.put("", response_model=list[FormaPagamentoAdminOut])
def salvar_formas_de_pagamento(
    payload: FormasPagamentoIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.salvar_aceitas(db, admin.restaurant_id, payload)