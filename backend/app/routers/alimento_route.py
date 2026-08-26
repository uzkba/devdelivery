import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.depedencias import get_current_user
from backend.app.schemas.alimento_schemas import AlimentoCreate, AlimentoUpdate, AlimentoOut
from backend.app.services import alimento_service 

router = APIRouter(prefix="/alimentos", tags=["Alimentos"])

def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user

@router.post("", response_model=AlimentoOut, status_code=status.HTTP_201_CREATED)
def criar_alimento(payload: AlimentoCreate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return alimento_service.criar_alimento(db, payload, current_user.restaurant_id)

@router.get("", response_model=List[AlimentoOut])
def listar_alimentos(
    categoria_id: Optional[uuid.UUID] = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return alimento_service.listar_alimentos(db, current_user.restaurant_id, categoria_id, incluir_inativos)

@router.get("/{alimento_id}", response_model=AlimentoOut)
def detalhar_alimento(alimento_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return alimento_service.get_alimento_por_id(db, alimento_id, current_user.restaurant_id)

@router.put("/{alimento_id}", response_model=AlimentoOut)
def atualizar_alimento(
    alimento_id: uuid.UUID,
    payload: AlimentoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return alimento_service.atualizar_alimento(db, alimento_id, payload, current_user.restaurant_id)

@router.delete("/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_alimento(alimento_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    alimento_service.desativar_alimento(db, alimento_id, current_user.restaurant_id)