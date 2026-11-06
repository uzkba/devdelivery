import uuid
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import (
    AvailabilityException,
    AvailabilityRule,
    Combo,
    Food,
    MealBox,
)

Alvo = MealBox | Combo | Food

MODO_PERSONALIZADO = "PERSONALIZADO"

# modelo -> atributo (nas tabelas de regra e de excecao) que aponta para ele
_ATRIBUTO_ALVO = {MealBox: "meal_box_id", Combo: "combo_id", Food: "food_id"}


@dataclass(frozen=True)
class EstadoDisponibilidade:
    serve_hoje: bool
    esgotado_hoje: bool


def esgotado_hoje(alvo: Alvo, hoje: date | None = None) -> bool:
    hoje = hoje or hoje_local()
    return alvo.sold_out_on == hoje


def servem_hoje(
    db: Session, modelo: type, ids: Iterable[uuid.UUID], hoje: date | None = None
) -> set[uuid.UUID]:
    """Dos ids informados (todos do mesmo `modelo`), devolve os que servem hoje.
    Duas consultas no maximo, independente da quantidade de itens."""
    ids = set(ids)
    if not ids:
        return set()
    hoje = hoje or hoje_local()

    atributo = _ATRIBUTO_ALVO[modelo]
    coluna_regra = getattr(AvailabilityRule, atributo)
    coluna_excecao = getattr(AvailabilityException, atributo)

    excecoes = {
        alvo_id: disponivel
        for alvo_id, disponivel in db.execute(
            select(coluna_excecao, AvailabilityException.is_available).where(
                coluna_excecao.in_(ids), AvailabilityException.exception_date == hoje
            )
        )
    }
    regras = {
        getattr(regra, atributo): regra
        for regra in db.scalars(select(AvailabilityRule).where(coluna_regra.in_(ids)))
    }

    servem: set[uuid.UUID] = set()
    for alvo_id in ids:
        if alvo_id in excecoes:
            serve = excecoes[alvo_id]
        else:
            regra = regras.get(alvo_id)
            serve = (
                regra is None
                or regra.mode != MODO_PERSONALIZADO
                or hoje.weekday() in {dia.weekday for dia in regra.days}
            )
        if serve:
            servem.add(alvo_id)
    return servem


def serve_hoje(db: Session, alvo: Alvo, hoje: date | None = None) -> bool:
    return alvo.id in servem_hoje(db, type(alvo), [alvo.id], hoje)


def estado_hoje(db: Session, alvo: Alvo, hoje: date | None = None) -> EstadoDisponibilidade:
    hoje = hoje or hoje_local()
    return EstadoDisponibilidade(
        serve_hoje=serve_hoje(db, alvo, hoje),
        esgotado_hoje=esgotado_hoje(alvo, hoje),
    )