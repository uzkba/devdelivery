from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.entrega_admin_schemas import ConfiguracaoEntregaIn, ConfiguracaoEntregaOut
from app.services import entrega_admin_service as service

router = APIRouter(prefix="/admin/restaurante/entrega", tags=["Admin - Entrega"])

require_admin = require_role("admin")


@router.get("", response_model=ConfiguracaoEntregaOut)
def buscar_configuracao(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.obter_configuracao(db, admin.restaurant_id)


@router.put("", response_model=ConfiguracaoEntregaOut)
def salvar_configuracao(
    payload: ConfiguracaoEntregaIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.salvar_configuracao(db, admin.restaurant_id, payload)