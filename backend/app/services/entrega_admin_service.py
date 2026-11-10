import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    RestaurantDeliverySettings,
)
from app.schemas.entrega_admin_schemas import ConfiguracaoEntregaIn


def _buscar(db: Session, restaurant_id: uuid.UUID) -> RestaurantDeliverySettings | None:
    return (
        db.query(RestaurantDeliverySettings)
        .filter(RestaurantDeliverySettings.restaurant_id == restaurant_id)
        .first()
    )


def _contar_bairros_ativos(db: Session, restaurant_id: uuid.UUID) -> int:
    return (
        db.query(func.count(DeliveryRuleNeighborhood.id))
        .filter(
            DeliveryRuleNeighborhood.restaurant_id == restaurant_id,
            DeliveryRuleNeighborhood.is_active.is_(True),
        )
        .scalar()
    )


def obter_configuracao(db: Session, restaurant_id: uuid.UUID) -> RestaurantDeliverySettings:
    config = _buscar(db, restaurant_id)
    if config is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "A configuração de entrega ainda não foi definida."
        )
    return config


def salvar_configuracao(
    db: Session, restaurant_id: uuid.UUID, payload: ConfiguracaoEntregaIn
) -> RestaurantDeliverySettings:
    if payload.modo == DeliveryChargeMode.BAIRRO and _contar_bairros_ativos(db, restaurant_id) == 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Cadastre ao menos um bairro ativo antes de usar a cobrança por bairro.",
        )

    config = _buscar(db, restaurant_id)
    if config is None:
        config = RestaurantDeliverySettings(restaurant_id=restaurant_id)
        db.add(config)

    config.delivery_enabled = payload.entrega_ativa
    config.pickup_enabled = payload.retirada_ativa
    config.charge_mode = payload.modo
    config.fixed_fee = payload.valor_fixo if payload.modo == DeliveryChargeMode.FIXO else None
    config.free_delivery_from = payload.frete_gratis_a_partir_de or None
    config.min_order_value = payload.valor_minimo or None
    config.delivery_time_minutes = payload.tempo_entrega_min
    config.pickup_time_minutes = payload.tempo_retirada_min

    db.commit()
    db.refresh(config)
    return config