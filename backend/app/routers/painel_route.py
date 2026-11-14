from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.painel_schemas import HojeOut
from app.services import painel_hoje_service

router = APIRouter(prefix="/painel", tags=["Painel"])

require_admin = require_role("admin")


@router.get("/hoje", response_model=HojeOut)
def painel_hoje(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return painel_hoje_service.montar_hoje(db, admin.restaurant_id)