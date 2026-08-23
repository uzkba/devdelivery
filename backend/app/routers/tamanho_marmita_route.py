"""
app/routers/tamanho_marmita_route.py

Endpoints:
POST   /tamanhos-marmita
GET    /tamanhos-marmita
PUT    /tamanhos-marmita/{tamanho_id}
DELETE /tamanhos-marmita/{tamanho_id}
POST   /tamanhos-marmita/{tamanho_id}/limites  — define/atualiza o limite
       de quantidade de uma categoria para esse tamanho
GET    /tamanhos-marmita/{tamanho_id}/limites  — lista os limites do tamanho

Mesma ressalva de escopo/papéis já sinalizada em categoria_alimento_route.py
e cardapio_route.py.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.depedencias import AuthenticatedUser, require_role
from backend.app.core.database import get_db
from backend.app.schemas.tamanho_marmita_schemas import (
    LimiteCategoriaTamanhoResponse,
    LimiteCategoriaTamanhoSet,
    TamanhoMarmitaCreate,
    TamanhoMarmitaResponse,
    TamanhoMarmitaUpdate,
)
from backend.app.services import tamanho_marmita_service as service

router = APIRouter(prefix="/tamanhos-marmita", tags=["Tamanhos de Marmita"])


@router.post("", response_model=TamanhoMarmitaResponse, status_code=status.HTTP_201_CREATED)
def criar_tamanho(
    dados: TamanhoMarmitaCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return TamanhoMarmitaResponse.from_model(service.criar_tamanho(db, current_user.restaurant_id, dados))


@router.get("", response_model=list[TamanhoMarmitaResponse])
def listar_tamanhos(
    apenas_ativos: bool = Query(False, description="Se true, retorna apenas tamanhos ativos"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    tamanhos = service.listar_tamanhos(db, current_user.restaurant_id, apenas_ativos=apenas_ativos)
    return [TamanhoMarmitaResponse.from_model(t) for t in tamanhos]


@router.put("/{tamanho_id}", response_model=TamanhoMarmitaResponse)
def atualizar_tamanho(
    tamanho_id: uuid.UUID,
    dados: TamanhoMarmitaUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return TamanhoMarmitaResponse.from_model(
        service.atualizar_tamanho(db, current_user.restaurant_id, tamanho_id, dados)
    )


@router.delete("/{tamanho_id}", response_model=TamanhoMarmitaResponse)
def remover_tamanho(
    tamanho_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return TamanhoMarmitaResponse.from_model(service.remover_tamanho(db, current_user.restaurant_id, tamanho_id))


@router.post("/{tamanho_id}/limites", response_model=LimiteCategoriaTamanhoResponse)
def definir_limite(
    tamanho_id: uuid.UUID,
    dados: LimiteCategoriaTamanhoSet,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin")),
):
    return LimiteCategoriaTamanhoResponse.from_model(
        service.definir_limite(db, current_user.restaurant_id, tamanho_id, dados)
    )


@router.get("/{tamanho_id}/limites", response_model=list[LimiteCategoriaTamanhoResponse])
def listar_limites(
    tamanho_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    limites = service.listar_limites(db, current_user.restaurant_id, tamanho_id)
    return [LimiteCategoriaTamanhoResponse.from_model(l) for l in limites]