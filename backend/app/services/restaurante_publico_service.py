from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    Restaurant,
    RestaurantDeliverySettings,
    RestaurantHours,
)
from app.schemas.restaurante_publico_schemas import (
    EnderecoPublicoOut,
    EntregaPublicaOut,
    EstadoOperacaoOut,
    FaixaHorarioOut,
    HorarioDiaOut,
    ProximaAberturaOut,
    RestaurantePublicoOut,
    TaxaEntregaOut,
    FormaPagamentoPublicaOut,
)
from app.services import estado_restaurante_service as estado_service, pagamento_service


def _montar_taxa(
    db: Session, restaurante: Restaurant, config: RestaurantDeliverySettings
) -> TaxaEntregaOut:
    taxa = TaxaEntregaOut(modo=config.charge_mode.value)

    if config.charge_mode == DeliveryChargeMode.FIXO:
        taxa.valor_fixo = config.fixed_fee
        taxa.frete_gratis_a_partir_de = config.free_delivery_from
    elif config.charge_mode == DeliveryChargeMode.BAIRRO:
        minimo, maximo = (
            db.query(
                func.min(DeliveryRuleNeighborhood.fee),
                func.max(DeliveryRuleNeighborhood.fee),
            )
            .filter(
                DeliveryRuleNeighborhood.restaurant_id == restaurante.id,
                DeliveryRuleNeighborhood.is_active.is_(True),
            )
            .one()
        )
        taxa.taxa_minima = minimo
        taxa.taxa_maxima = maximo
        taxa.frete_gratis_a_partir_de = config.free_delivery_from

    return taxa


def _hhmm(valor) -> str:
    return valor.strftime("%H:%M")


def montar_horarios(faixas: list[RestaurantHours]) -> list[HorarioDiaOut]:
    por_dia: dict[int, list[FaixaHorarioOut]] = {dia: [] for dia in range(7)}
    for faixa in faixas:
        por_dia[faixa.weekday].append(
            FaixaHorarioOut(abre_as=_hhmm(faixa.opens_at), fecha_as=_hhmm(faixa.closes_at))
        )
    return [HorarioDiaOut(dia_semana=dia, faixas=por_dia[dia]) for dia in range(7)]


def montar_estado(estado: estado_service.EstadoOperacao) -> EstadoOperacaoOut:
    proxima = None
    if estado.proxima_abertura is not None:
        proxima = ProximaAberturaOut(
            em_dias=estado.proxima_abertura.em_dias,
            dia_semana=estado.proxima_abertura.dia_semana,
            abre_as=_hhmm(estado.proxima_abertura.abre_as),
        )
    return EstadoOperacaoOut(
        estado=estado.estado,
        aceita_pedidos=estado.aceita_pedidos,
        horario_definido=estado.horario_definido,
        motivo=estado.motivo,
        pausado_ate=estado.pausado_ate,
        proxima_abertura=proxima,
    )


def montar_restaurante_publico(db: Session, restaurante: Restaurant) -> RestaurantePublicoOut:
    config = (
        db.query(RestaurantDeliverySettings)
        .filter(RestaurantDeliverySettings.restaurant_id == restaurante.id)
        .first()
    )

    entrega = None
    if config is not None:
        entrega = EntregaPublicaOut(
            entrega_ativa=config.delivery_enabled,
            retirada_ativa=config.pickup_enabled,
            valor_minimo=config.min_order_value,
            tempo_entrega_min=config.delivery_time_minutes,
            tempo_retirada_min=config.pickup_time_minutes,
            taxa=_montar_taxa(db, restaurante, config),
        )

    faixas = estado_service.buscar_faixas(db, restaurante.id)
    estado = estado_service.buscar_estado(db, restaurante)

    return RestaurantePublicoOut(
        slug=restaurante.slug,
        nome=restaurante.trade_name,
        telefone=restaurante.phone,
        endereco=EnderecoPublicoOut(
            rua=restaurante.street,
            numero=restaurante.number,
            bairro=restaurante.neighborhood,
            cidade=restaurante.city,
        ),
        estado=montar_estado(estado),
        horarios=montar_horarios(faixas),
        entrega=entrega,
        formas_pagamento=[
            FormaPagamentoPublicaOut(codigo=forma.code, nome=forma.name)
            for forma in pagamento_service.listar_aceitas(db, restaurante.id)
        ],
    )