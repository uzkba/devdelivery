import uuid
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.depedencias import AuthenticatedUser, require_role
from app.core.database import get_db
from app.model.models import Food
from app.schemas.alimento_schemas import AlimentoCreate, AlimentoUpdate, AlimentoOut
from app.services import alimento_service, disponibilidade_service as disponibilidade

router = APIRouter(prefix="/alimentos", tags=["Alimentos"])


@router.post("", response_model=AlimentoOut, status_code=status.HTTP_201_CREATED)
def criar_alimento(
    payload: AlimentoCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    alimento = alimento_service.criar_alimento(db, payload, current_user.restaurant_id)
    return disponibilidade.anotar_um(db, alimento)


@router.get("", response_model=List[AlimentoOut])
def listar_alimentos(
    categoria_id: Optional[uuid.UUID] = None,
    categoria_venda_id: Optional[uuid.UUID] = None,
    vendavel_avulso: Optional[bool] = None,
    grupo: Optional[Literal["prato", "bebida"]] = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    alimentos = alimento_service.listar_alimentos(
        db,
        current_user.restaurant_id,
        categoria_id=categoria_id,
        incluir_inativos=incluir_inativos,
        vendavel_avulso=vendavel_avulso,
        categoria_venda_id=categoria_venda_id,
        grupo=grupo,
    )
    return disponibilidade.anotar_estado_hoje(db, Food, alimentos)


@router.get("/{alimento_id}", response_model=AlimentoOut)
def detalhar_alimento(
    alimento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    alimento = alimento_service.get_alimento_por_id(db, alimento_id, current_user.restaurant_id)
    return disponibilidade.anotar_um(db, alimento)


@router.put("/{alimento_id}", response_model=AlimentoOut)
def atualizar_alimento(
    alimento_id: uuid.UUID,
    payload: AlimentoUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    alimento = alimento_service.atualizar_alimento(db, alimento_id, payload, current_user.restaurant_id)
    return disponibilidade.anotar_um(db, alimento)


@router.delete("/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_alimento(
    alimento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    alimento_service.desativar_alimento(db, alimento_id, current_user.restaurant_id)