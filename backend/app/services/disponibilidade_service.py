import uuid
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import (
    AvailabilityException,
    AvailabilityRule,
    AvailabilityRuleDay,
    Combo,
    Food,
    MealBox,
)

Alvo = MealBox | Combo | Food

MODO_PERSONALIZADO = "PERSONALIZADO"
MODO_TODOS_OS_DIAS = "TODOS_OS_DIAS"

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


# ---------------------------- leitura e escrita (admin) ----------------------------
def anotar_estado_hoje(
    db: Session, modelo: type, objetos: Iterable[Alvo], hoje: date | None = None
) -> list[Alvo]:
    objetos = list(objetos)
    if not objetos:
        return objetos
    hoje = hoje or hoje_local()
    servem = servem_hoje(db, modelo, [o.id for o in objetos], hoje)
    for objeto in objetos:
        objeto.serves_today = objeto.id in servem
        objeto.sold_out_today = esgotado_hoje(objeto, hoje)
    return objetos


def anotar_um(db: Session, objeto: Alvo, hoje: date | None = None) -> Alvo:
    anotar_estado_hoje(db, type(objeto), [objeto], hoje)
    return objeto


def _coluna(tabela, alvo: Alvo):
    return getattr(tabela, _ATRIBUTO_ALVO[type(alvo)])


def ler_disponibilidade(db: Session, alvo: Alvo, hoje: date | None = None) -> dict:
    hoje = hoje or hoje_local()
    regra = db.scalar(select(AvailabilityRule).where(_coluna(AvailabilityRule, alvo) == alvo.id))
    personalizado = regra is not None and regra.mode == MODO_PERSONALIZADO
    excecoes = db.scalars(
        select(AvailabilityException)
        .where(
            _coluna(AvailabilityException, alvo) == alvo.id,
            AvailabilityException.exception_date >= hoje,
        )
        .order_by(AvailabilityException.exception_date)
    ).all()
    estado = estado_hoje(db, alvo, hoje)
    return {
        "modo": regra.mode if regra else MODO_TODOS_OS_DIAS,
        "dias": sorted(d.weekday for d in regra.days) if personalizado else [],
        "excecoes": [
            {"data": e.exception_date, "disponivel": e.is_available} for e in excecoes
        ],
        "serve_hoje": estado.serve_hoje,
        "esgotado_hoje": estado.esgotado_hoje,
    }


def definir_regra(db: Session, alvo: Alvo, modo: str, dias: list[int]) -> None:
    regra = db.scalar(select(AvailabilityRule).where(_coluna(AvailabilityRule, alvo) == alvo.id))
    if regra is None:
        regra = AvailabilityRule(**{_ATRIBUTO_ALVO[type(alvo)]: alvo.id}, mode=modo)
        db.add(regra)
    else:
        regra.mode = modo
        regra.days.clear()
        db.flush()
    regra.days.extend(AvailabilityRuleDay(weekday=d) for d in sorted(dias))
    db.commit()


def definir_excecao(
    db: Session, alvo: Alvo, dia: date, disponivel: bool, hoje: date | None = None
) -> None:
    hoje = hoje or hoje_local()
    if dia < hoje:
        raise HTTPException(422, "A data da exceção não pode estar no passado.")
    excecao = db.scalar(
        select(AvailabilityException).where(
            _coluna(AvailabilityException, alvo) == alvo.id,
            AvailabilityException.exception_date == dia,
        )
    )
    if excecao is None:
        db.add(
            AvailabilityException(
                **{_ATRIBUTO_ALVO[type(alvo)]: alvo.id},
                exception_date=dia,
                is_available=disponivel,
            )
        )
    else:
        excecao.is_available = disponivel
    db.commit()


def remover_excecao(db: Session, alvo: Alvo, dia: date) -> None:
    excecao = db.scalar(
        select(AvailabilityException).where(
            _coluna(AvailabilityException, alvo) == alvo.id,
            AvailabilityException.exception_date == dia,
        )
    )
    if excecao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exceção não encontrada para esta data.")
    db.delete(excecao)
    db.commit()


def definir_esgotado(
    db: Session, alvo: Alvo, esgotado: bool, hoje: date | None = None
) -> None:
    hoje = hoje or hoje_local()
    alvo.sold_out_on = hoje if esgotado else None
    db.commit()
    db.refresh(alvo)