from fastapi import APIRouter, Depends

from backend.app.api.depedencias import require_role
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser

router = APIRouter(tags=["teste"])


@router.get("/teste-admin")
def rota_protegida(current_user: AuthenticatedUser = Depends(require_role("admin"))):
    return {"mensagem": f"Acesso liberado! Você é {current_user.name} ({current_user.role})"}