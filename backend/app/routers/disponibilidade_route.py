import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.depedencias import require_role
from app.core.database import get_db
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.disponibilidade_schemas import (
    DisponibilidadeOut,
    EsgotadoIn,
    ExcecaoIn,
    RegraIn,
)
from app.services import alimento_service, combo_service, marmita_service
from app.services import disponibilidade_service as service

require_admin = require_role("admin")
require_esgotar = require_role("admin", "atendente")  # o atendente esgota no balcao


def _criar_router(prefixo: str, tag: str, buscar) -> APIRouter:
    """`buscar(db, restaurant_id, alvo_id)` devolve o item do restaurante ou levanta 404."""
    router = APIRouter(prefix=prefixo, tags=[tag])

    @router.get("/{alvo_id}/disponibilidade", response_model=DisponibilidadeOut)
    def ler_disponibilidade(
        alvo_id: uuid.UUID,
        db: Session = Depends(get_db),
        admin: AuthenticatedUser = Depends(require_admin),
    ):
        alvo = buscar(db, admin.restaurant_id, alvo_id)
        return service.ler_disponibilidade(db, alvo)

    @router.put("/{alvo_id}/disponibilidade", response_model=DisponibilidadeOut)
    def salvar_regra(
        alvo_id: uuid.UUID,
        payload: RegraIn,
        db: Session = Depends(get_db),
        admin: AuthenticatedUser = Depends(require_admin),
    ):
        alvo = buscar(db, admin.restaurant_id, alvo_id)
        service.definir_regra(db, alvo, payload.modo.value, payload.dias)
        return service.ler_disponibilidade(db, alvo)

    @router.put("/{alvo_id}/disponibilidade/excecoes/{data}", response_model=DisponibilidadeOut)
    def salvar_excecao(
        alvo_id: uuid.UUID,
        data: date,
        payload: ExcecaoIn,
        db: Session = Depends(get_db),
        admin: AuthenticatedUser = Depends(require_admin),
    ):
        alvo = buscar(db, admin.restaurant_id, alvo_id)
        service.definir_excecao(db, alvo, data, payload.disponivel)
        return service.ler_disponibilidade(db, alvo)

    @router.delete(
        "/{alvo_id}/disponibilidade/excecoes/{data}", status_code=status.HTTP_204_NO_CONTENT
    )
    def remover_excecao(
        alvo_id: uuid.UUID,
        data: date,
        db: Session = Depends(get_db),
        admin: AuthenticatedUser = Depends(require_admin),
    ):
        alvo = buscar(db, admin.restaurant_id, alvo_id)
        service.remover_excecao(db, alvo, data)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.patch("/{alvo_id}/esgotado", response_model=DisponibilidadeOut)
    def esgotar_ou_liberar(
        alvo_id: uuid.UUID,
        payload: EsgotadoIn,
        db: Session = Depends(get_db),
        usuario: AuthenticatedUser = Depends(require_esgotar),
    ):
        alvo = buscar(db, usuario.restaurant_id, alvo_id)
        service.definir_esgotado(db, alvo, payload.esgotado)
        return service.ler_disponibilidade(db, alvo)

    return router


routers = [
    _criar_router("/admin/marmitas", "Admin - Marmitas", marmita_service.get_meal_box),
    _criar_router("/admin/combos", "Admin - Combos", combo_service.get_combo),
    _criar_router(
        "/alimentos",
        "Alimentos",
        # get_alimento_por_id recebe (db, alimento_id, restaurant_id): ordem diferente
        lambda db, restaurant_id, alvo_id: alimento_service.get_alimento_por_id(
            db, alvo_id, restaurant_id
        ),
    ),
]