import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.bairro_entrega_schemas import BairroIn, BairroOut
from app.services import bairro_entrega_service as service

router = APIRouter(prefix="/admin/restaurante/entrega/bairros", tags=["Admin - Entrega"])

require_admin = require_role("admin")


@router.get("", response_model=list[BairroOut])
def listar_bairros(
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.listar_bairros(db, admin.restaurant_id)


@router.post("", response_model=BairroOut, status_code=status.HTTP_201_CREATED)
def criar_bairro(
    payload: BairroIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.criar_bairro(db, admin.restaurant_id, payload)


@router.put("/{bairro_id}", response_model=BairroOut)
def atualizar_bairro(
    bairro_id: uuid.UUID,
    payload: BairroIn,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    return service.atualizar_bairro(db, admin.restaurant_id, bairro_id, payload)


@router.delete("/{bairro_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_bairro(
    bairro_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_admin),
):
    service.remover_bairro(db, admin.restaurant_id, bairro_id)