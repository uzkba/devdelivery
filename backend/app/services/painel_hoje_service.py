import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.tempo import agora_local
from app.model.models import RestaurantHours
from app.schemas.painel_schemas import (
    AlertaOut,
    FilaHojeOut,
    HojeOut,
    MaisVendidoOut,
    PedidoEmAndamentoOut,
    RestauranteHojeOut,
    ResumoDiaOut,
)
from app.services import (
    estado_restaurante_service as estado_service,
    painel_alertas_service,
    painel_pedidos_service,
    painel_ranking_service,
    painel_resumo_service,
)
from app.services.restaurante_admin_service import buscar_restaurante
from app.services.restaurante_publico_service import montar_estado


def _fecha_as(faixas: list[RestaurantHours], momento: datetime) -> str | None:
    hora = momento.time()
    for faixa in faixas:
        if faixa.weekday == momento.weekday() and faixa.opens_at <= hora < faixa.closes_at:
            return faixa.closes_at.strftime("%H:%M")
    return None


def montar_hoje(
    db: Session, restaurant_id: uuid.UUID, agora: datetime | None = None
) -> HojeOut:
    momento = agora_local(agora)
    restaurante = buscar_restaurante(db, restaurant_id)
    faixas = estado_service.buscar_faixas(db, restaurante.id)
    estado = estado_service.calcular_estado(restaurante, faixas, momento)

    atrasos = painel_alertas_service.atrasos_dos_pedidos(db, restaurant_id, momento)

    return HojeOut(
        data=momento.date(),
        restaurante=RestauranteHojeOut(
            nome=restaurante.trade_name,
            estado=montar_estado(estado),
            fecha_as=_fecha_as(faixas, momento),
        ),
        fila=FilaHojeOut.model_validate(
            painel_pedidos_service.fila_do_dia(db, restaurant_id, momento)
        ),
        em_andamento=[
            PedidoEmAndamentoOut.model_validate(cartao)
            for cartao in painel_pedidos_service.em_andamento(
                db, restaurant_id, agora=momento, atrasos=atrasos
            )
        ],
        atencao=[
            AlertaOut.model_validate(alerta)
            for alerta in painel_alertas_service.alertas_de_atencao(
                db, restaurant_id, momento, atrasos
            )
        ],
        resumo=ResumoDiaOut.model_validate(
            painel_resumo_service.resumo_do_dia(db, restaurant_id, momento)
        ),
        mais_vendidos=[
            MaisVendidoOut.model_validate(item)
            for item in painel_ranking_service.mais_vendidos_hoje(
                db, restaurant_id, agora=momento
            )
        ],
    )