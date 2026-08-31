"""
app/routers/categoria_alimento_route.py

Endpoints:
POST   /categorias
GET    /categorias
GET    /categorias/{categoria_id}
PUT    /categorias/{categoria_id}
DELETE /categorias/{categoria_id}

Escopo por restaurante: restaurant_id vem do usuário admin autenticado
(current_user.restaurant_id), nunca é enviado pelo client — assim um admin
de um restaurante não consegue ler/editar categoria de outro.

ATENÇÃO / ajustar conforme o depedencias.py real:
- Assumi que AuthenticatedUser tem o atributo `restaurant_id`. Se o nome
  real for outro (ex: `restaurante_id`), ajuste as referências abaixo.
- Assumi papéis "admin" para escrita e "admin"/"atendente"/"caixa" para
  leitura, no mesmo espírito do que já foi usado nos endpoints de
  endereço de cliente. Ajuste conforme a regra real do time.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.depedencias import AuthenticatedUser, require_role
from app.core.database import get_db
from app.schemas.categoria_alimento_schemas import (
    CategoriaAlimentoCreate,
    CategoriaAlimentoResponse,
    CategoriaAlimentoUpdate,
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
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    return service.listar_categorias(db, current_user.restaurant_id, apenas_ativas=apenas_ativas)


@router.get("/{categoria_id}", response_model=CategoriaAlimentoResponse)
def buscar_categoria(
    categoria_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    return service.buscar_categoria_por_id(db, current_user.restaurant_id, categoria_id)


@router.put("/{categoria_id}", response_model=CategoriaAlimentoResponse)
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