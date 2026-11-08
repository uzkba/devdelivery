from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    Restaurant,
    RestaurantDeliverySettings,
)
from app.schemas.restaurante_publico_schemas import (
    EnderecoPublicoOut,
    EntregaPublicaOut,
    RestaurantePublicoOut,
    TaxaEntregaOut,
)


def _montar_taxa(
    db: Session, restaurante: Restaurant, config: RestaurantDeliverySettings
) -> TaxaEntregaOut:
    taxa = TaxaEntregaOut(modo=config.charge_mode.value)

    if config.charge_mode == DeliveryChargeMode.FIXO:
        taxa.valor_fixo = config.fixed_fee
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

    return taxa


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
        entrega=entrega,
    )