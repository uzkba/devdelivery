from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.restaurante_admin_schemas import (
    HorariosIn,
    PausaIn,
    RestauranteAdminOut,
    RestauranteAtualizarIn,
    SlugDisponivelOut,
)
from app.schemas.restaurante_publico_schemas import EstadoOperacaoOut
from app.services import restaurante_admin_service as service

router = APIRouter(prefix="/admin/restaurante", tags=["Admin - Restaurante"])

require_admin = require_role("admin")


@router.get("", response_model=RestauranteAdminOut)
def buscar_restaurante(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.buscar_dados(db, admin.restaurant_id)


@router.patch("", response_model=RestauranteAdminOut)
def atualizar_restaurante(
    payload: RestauranteAtualizarIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.atualizar_dados(db, admin.restaurant_id, payload)


@router.get("/slug-disponivel", response_model=SlugDisponivelOut)
def slug_disponivel(
    slug: str = Query(min_length=1, max_length=60),
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.verificar_slug(db, admin.restaurant_id, slug)


@router.put("/horarios", response_model=RestauranteAdminOut)
def substituir_horarios(
    payload: HorariosIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.substituir_horarios(db, admin.restaurant_id, payload)


@router.patch("/pausa", response_model=EstadoOperacaoOut)
def alterar_pausa(
    payload: PausaIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.alterar_pausa(db, admin.restaurant_id, payload)