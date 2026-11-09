import uuid
from dataclasses import dataclass
from datetime import datetime, time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.tempo import agora_local
from app.model.models import Restaurant, RestaurantHours

ABERTO = "ABERTO"
PAUSADO = "PAUSADO"
FECHADO = "FECHADO"

MOTIVO_FORA_DO_HORARIO = "FORA_DO_HORARIO"
MOTIVO_PAUSA_MANUAL = "PAUSA_MANUAL"

_MENSAGENS_BLOQUEIO = {
    MOTIVO_FORA_DO_HORARIO: "O restaurante está fechado no momento.",
    MOTIVO_PAUSA_MANUAL: "O restaurante pausou os pedidos temporariamente. Tente novamente em alguns minutos.",
}


@dataclass(frozen=True)
class ProximaAbertura:
    em_dias: int
    dia_semana: int
    abre_as: time


@dataclass(frozen=True)
class EstadoOperacao:
    estado: str
    aceita_pedidos: bool
    horario_definido: bool
    motivo: str | None = None
    pausado_ate: datetime | None = None
    proxima_abertura: ProximaAbertura | None = None


def buscar_faixas(db: Session, restaurant_id: uuid.UUID) -> list[RestaurantHours]:
    return (
        db.query(RestaurantHours)
        .filter(RestaurantHours.restaurant_id == restaurant_id)
        .order_by(RestaurantHours.weekday, RestaurantHours.opens_at)
        .all()
    )


def _pausa_ativa(restaurante: Restaurant, agora: datetime) -> bool:
    if not restaurante.is_paused:
        return False
    return restaurante.paused_until is None or restaurante.paused_until > agora


def _proxima_abertura(faixas: list[RestaurantHours], agora: datetime) -> ProximaAbertura | None:
    hoje = agora.weekday()
    hora = agora.time()
    for em_dias in range(0, 8):
        dia = (hoje + em_dias) % 7
        aberturas = sorted(
            f.opens_at
            for f in faixas
            if f.weekday == dia and (em_dias > 0 or f.opens_at > hora)
        )
        if aberturas:
            return ProximaAbertura(em_dias=em_dias, dia_semana=dia, abre_as=aberturas[0])
    return None


def calcular_estado(
    restaurante: Restaurant, faixas: list[RestaurantHours], agora: datetime
) -> EstadoOperacao:
    pausa = _pausa_ativa(restaurante, agora)
    pausado_ate = restaurante.paused_until if pausa else None

    if not faixas:
        if pausa:
            return EstadoOperacao(PAUSADO, False, False, MOTIVO_PAUSA_MANUAL, pausado_ate)
        return EstadoOperacao(ABERTO, True, False)

    hora = agora.time()
    dentro_do_horario = any(
        f.weekday == agora.weekday() and f.opens_at <= hora < f.closes_at for f in faixas
    )

    if not dentro_do_horario:
        return EstadoOperacao(
            FECHADO,
            False,
            True,
            MOTIVO_FORA_DO_HORARIO,
            None,
            _proxima_abertura(faixas, agora),
        )
    if pausa:
        return EstadoOperacao(PAUSADO, False, True, MOTIVO_PAUSA_MANUAL, pausado_ate)
    return EstadoOperacao(ABERTO, True, True)


def buscar_estado(
    db: Session, restaurante: Restaurant, agora: datetime | None = None
) -> EstadoOperacao:
    momento = agora if agora is not None else agora_local()
    return calcular_estado(restaurante, buscar_faixas(db, restaurante.id), momento)


def garantir_aceita_pedidos(db: Session, restaurante: Restaurant) -> None:
    estado = buscar_estado(db, restaurante)
    if not estado.aceita_pedidos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, _MENSAGENS_BLOQUEIO[estado.motivo]
        )