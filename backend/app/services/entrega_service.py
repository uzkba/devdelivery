from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model.models import (
    CustomerAddress,
    DeliveryChargeMode,
    DeliveryRule,
    DeliveryRuleNeighborhood,
    Restaurant,
    RestaurantDeliverySettings,
)
from app.utils.geo import calcular_distancia_km


def buscar_configuracao(db: Session, restaurante_id) -> RestaurantDeliverySettings:
    config = db.query(RestaurantDeliverySettings).filter_by(restaurant_id=restaurante_id).first()
    if not config:
        raise HTTPException(
            status_code=500, detail="Restaurante não possui configuração de entrega definida."
        )
    return config


def garantir_entrega_ativa(config: RestaurantDeliverySettings) -> None:
    if not config.delivery_enabled:
        raise HTTPException(
            status_code=422, detail="Este restaurante não realiza entregas no momento."
        )


def validar_valor_minimo(config: RestaurantDeliverySettings, valor_itens: Decimal) -> None:
    if config.min_order_value is not None and valor_itens < config.min_order_value:
        raise HTTPException(
            status_code=422,
            detail=f"O valor mínimo do pedido é de R$ {config.min_order_value:.2f}.",
        )


def calcular_taxa_entrega(
    db: Session,
    restaurante: Restaurant,
    endereco: CustomerAddress,
    config: RestaurantDeliverySettings,
) -> Decimal:
    if config.charge_mode == DeliveryChargeMode.GRATIS:
        return Decimal("0.00")

    if config.charge_mode == DeliveryChargeMode.FIXO:
        if config.fixed_fee is None:
            raise HTTPException(status_code=500, detail="Taxa fixa de entrega não configurada.")
        return Decimal(str(config.fixed_fee))

    if config.charge_mode == DeliveryChargeMode.BAIRRO:
        if not endereco.neighborhood:
            raise HTTPException(status_code=400, detail="Endereço sem bairro informado.")
        regra = (
            db.query(DeliveryRuleNeighborhood)
            .filter(
                DeliveryRuleNeighborhood.restaurant_id == restaurante.id,
                DeliveryRuleNeighborhood.is_active.is_(True),
                func.lower(DeliveryRuleNeighborhood.neighborhood) == endereco.neighborhood.strip().lower(),
            )
            .first()
        )
        if not regra:
            raise HTTPException(
                status_code=422, detail=f"O bairro '{endereco.neighborhood}' está fora da área de entrega."
            )
        return Decimal(str(regra.fee))

    if config.charge_mode == DeliveryChargeMode.DISTANCIA:
        if not restaurante.latitude or not restaurante.longitude:
            raise HTTPException(status_code=500, detail="Restaurante não possui coordenadas configuradas.")
        if endereco.latitude is None or endereco.longitude is None:
            raise HTTPException(status_code=400, detail="Endereço de entrega não possui coordenadas válidas.")

        distancia_km = calcular_distancia_km(
            float(restaurante.latitude), float(restaurante.longitude),
            float(endereco.latitude), float(endereco.longitude),
        )
        regra_entrega = (
            db.query(DeliveryRule)
            .filter(
                DeliveryRule.restaurant_id == restaurante.id,
                DeliveryRule.is_active.is_(True),
                DeliveryRule.min_distance_km <= distancia_km,
                DeliveryRule.max_distance_km >= distancia_km,
            )
            .first()
        )
        if not regra_entrega:
            raise HTTPException(
                status_code=422,
                detail=f"O endereço selecionado está fora da área de entrega (Distância: {distancia_km:.1f}km).",
            )
        return Decimal(str(regra_entrega.fee))

    raise HTTPException(status_code=500, detail="Modo de cobrança de entrega inválido.")