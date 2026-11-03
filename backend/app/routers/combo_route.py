"""NexusDelivery - Fase 1: rotas admin de combo (/admin/combos)."""
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import require_role  # AJUSTE: modulo onde esta require_role
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.combo_schemas import ComboIn, ComboListOut, ComboOut
from app.schemas.marmita_schemas import AtivoIn
from app.services import combo_service as service

router = APIRouter(prefix="/admin/combos", tags=["Admin - Combos"])

require_admin = require_role("admin")


@router.post("", response_model=ComboOut, status_code=status.HTTP_201_CREATED)
def criar_combo(
    payload: ComboIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.create_combo(db, admin.restaurant_id, payload)


@router.get("", response_model=ComboListOut)
def listar_combos(
    ativo: bool | None = None,
    busca: str | None = Query(default=None, max_length=80),
    limite: int = Query(default=50, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    items, total = service.list_combos(
        db,
        admin.restaurant_id,
        active=ativo,
        search=busca,
        limit=limite,
        offset=deslocamento,
    )
    return {"itens": items, "total": total}


@router.get("/{combo_id}", response_model=ComboOut)
def buscar_combo(
    combo_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.get_combo(db, admin.restaurant_id, combo_id)


@router.put("/{combo_id}", response_model=ComboOut)
def atualizar_combo(
    combo_id: uuid.UUID,
    payload: ComboIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.update_combo(db, admin.restaurant_id, combo_id, payload)


@router.patch("/{combo_id}/ativo", response_model=ComboOut)
def alternar_combo_ativo(
    combo_id: uuid.UUID,
    payload: AtivoIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.set_combo_active(db, admin.restaurant_id, combo_id, payload.ativo)


@router.delete("/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_combo(
    combo_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    service.delete_combo(db, admin.restaurant_id, combo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)