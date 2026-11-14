from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.painel_schemas import AvisosOut, HojeOut
from app.services import painel_avisos_service, painel_hoje_service

router = APIRouter(prefix="/painel", tags=["Painel"])

require_admin = require_role("admin")
operador = require_role("admin", "atendente")


@router.get("/hoje", response_model=HojeOut)
def painel_hoje(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return painel_hoje_service.montar_hoje(db, admin.restaurant_id)


@router.get("/avisos", response_model=AvisosOut)
def painel_avisos(
    limite: int = Query(painel_avisos_service.LIMITE_PADRAO, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(operador),
):
    return painel_avisos_service.avisos_do_painel(db, usuario.restaurant_id, limite)