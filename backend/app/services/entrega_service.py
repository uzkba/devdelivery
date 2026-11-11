from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.texto import chave_comparacao
from app.model.models import (
    CustomerAddress,
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    Restaurant,
    RestaurantDeliverySettings,
)


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
        if not endereco.neighborhood or not endereco.neighborhood.strip():
            raise HTTPException(status_code=400, detail="Endereço sem bairro informado.")
        chave = chave_comparacao(endereco.neighborhood)
        regras = (
            db.query(DeliveryRuleNeighborhood)
            .filter(
                DeliveryRuleNeighborhood.restaurant_id == restaurante.id,
                DeliveryRuleNeighborhood.is_active.is_(True),
            )
            .order_by(DeliveryRuleNeighborhood.neighborhood)
            .all()
        )
        regra = next((r for r in regras if chave_comparacao(r.neighborhood) == chave), None)
        if regra is None:
            raise HTTPException(
                status_code=422, detail=f"O bairro '{endereco.neighborhood}' está fora da área de entrega."
            )
        return Decimal(str(regra.fee))

    raise HTTPException(status_code=500, detail="Modo de cobrança de entrega inválido.")


def aplicar_frete_gratis(
    config: RestaurantDeliverySettings, valor_itens: Decimal, taxa: Decimal
) -> Decimal:
    if (
        config.charge_mode != DeliveryChargeMode.GRATIS
        and config.free_delivery_from is not None
        and valor_itens >= config.free_delivery_from
    ):
        return Decimal("0.00")
    return taxa


def garantir_retirada_ativa(config: RestaurantDeliverySettings) -> None:
    if not config.pickup_enabled:
        raise HTTPException(
            status_code=422, detail="Este restaurante não realiza retiradas no momento."
        )