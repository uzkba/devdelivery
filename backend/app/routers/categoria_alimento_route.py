import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.depedencias import AuthenticatedUser, require_role
from app.core.database import get_db
from app.schemas.categoria_alimento_schemas import (
    CategoriaAlimentoCreate,
    CategoriaAlimentoResponse,
    CategoriaAlimentoUpdate,
    CategoriaAlimentoUpdateResponse,
)
from app.services import categoria_alimento_service as service

router = APIRouter(prefix="/categorias", tags=["Categorias de Alimento"])


@router.post("", response_model=CategoriaAlimentoResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    dados: CategoriaAlimentoCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return service.criar_categoria(db, current_user.restaurant_id, dados)


@router.get("", response_model=list[CategoriaAlimentoResponse])
def listar_categorias(
    apenas_ativas: bool = Query(False, description="Se true, retorna apenas categorias ativas"),
    tipo: Optional[Literal["composicao", "venda"]] = Query(None, description="Filtra pelo tipo da categoria"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    return service.listar_categorias(db, current_user.restaurant_id, apenas_ativas=apenas_ativas, tipo=tipo)


@router.get("/{categoria_id}", response_model=CategoriaAlimentoResponse)
def buscar_categoria(
    categoria_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    return service.buscar_categoria_por_id(db, current_user.restaurant_id, categoria_id)


@router.put("/{categoria_id}", response_model=CategoriaAlimentoUpdateResponse)
def atualizar_categoria(
    categoria_id: uuid.UUID,
    dados: CategoriaAlimentoUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return service.atualizar_categoria(db, current_user.restaurant_id, categoria_id, dados)


@router.delete("/{categoria_id}", response_model=CategoriaAlimentoResponse)
def remover_categoria(
    categoria_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return service.remover_categoria(db, current_user.restaurant_id, categoria_id)