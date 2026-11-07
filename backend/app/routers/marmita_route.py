import uuid
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from app.model.models import MealBox, MealBoxKind
from app.core.database import get_db
from app.api.depedencias import require_role
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.marmita_schemas import (
    AtivoIn,
    MarmitaIn,
    MarmitaListOut,
    MarmitaOut,
)
from app.services import marmita_service as service, disponibilidade_service as disponibilidade

router = APIRouter(prefix="/admin/marmitas", tags=["Admin - Marmitas"])

require_admin = require_role("admin")


@router.post("", response_model=MarmitaOut, status_code=status.HTTP_201_CREATED)
def criar_marmita(
    payload: MarmitaIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    marmita = service.create_meal_box(db, admin.restaurant_id, payload)
    return disponibilidade.anotar_um(db, marmita)


@router.get("", response_model=MarmitaListOut)
def listar_marmitas(
    tipo: MealBoxKind | None = None,
    ativo: bool | None = None,
    busca: str | None = Query(default=None, max_length=80),
    limite: int = Query(default=50, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    items, total = service.list_meal_boxes(
        db,
        admin.restaurant_id,
        kind=tipo,
        active=ativo,
        search=busca,
        limit=limite,
        offset=deslocamento,
    )
    disponibilidade.anotar_estado_hoje(db, MealBox, items)
    return {"itens": items, "total": total}


@router.get("/{marmita_id}", response_model=MarmitaOut)
def buscar_marmita(
    marmita_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    marmita = service.get_meal_box(db, admin.restaurant_id, marmita_id)
    return disponibilidade.anotar_um(db, marmita)


@router.put("/{marmita_id}", response_model=MarmitaOut)
def atualizar_marmita(
    marmita_id: uuid.UUID,
    payload: MarmitaIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    marmita = service.update_meal_box(db, admin.restaurant_id, marmita_id, payload)
    return disponibilidade.anotar_um(db, marmita)


@router.patch("/{marmita_id}/ativo", response_model=MarmitaOut)
def alternar_marmita_ativa(
    marmita_id: uuid.UUID,
    payload: AtivoIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    marmita = service.set_meal_box_active(db, admin.restaurant_id, marmita_id, payload.ativo)
    return disponibilidade.anotar_um(db, marmita)


@router.delete("/{marmita_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_marmita(
    marmita_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    service.delete_meal_box(db, admin.restaurant_id, marmita_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)