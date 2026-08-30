# backend/app/api/routers/delivery_rules.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from backend.app.core.database import get_db
from backend.app.api.depedencias import get_current_user, require_role
from backend.app.schemas.regras_delivery_schemas import DeliveryRuleCreate, DeliveryRuleOut
from backend.app.services import regras_delivery_service

router = APIRouter(prefix="/admin/regras-entrega", tags=["Admin - Taxas de Entrega"])

@router.post("", response_model=DeliveryRuleOut, status_code=status.HTTP_201_CREATED)
def criar_regra(
    payload: DeliveryRuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    return regras_delivery_service.criar_regra_entrega(db, payload, current_user.restaurant_id)


@router.get("", response_model=List[DeliveryRuleOut])
def listar_regras(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    return regras_delivery_service.listar_regras(db, current_user.restaurant_id)


@router.delete("/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_regra(
    regra_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    regras_delivery_service.desativar_regra(db, regra_id, current_user.restaurant_id)
    return None