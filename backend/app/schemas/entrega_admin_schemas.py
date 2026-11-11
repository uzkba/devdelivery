from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.model.models import DeliveryChargeMode


class ConfiguracaoEntregaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entrega_ativa: bool = Field(validation_alias="delivery_enabled")
    retirada_ativa: bool = Field(validation_alias="pickup_enabled")
    modo: DeliveryChargeMode = Field(validation_alias="charge_mode")
    valor_fixo: Optional[Decimal] = Field(default=None, validation_alias="fixed_fee")
    frete_gratis_a_partir_de: Optional[Decimal] = Field(
        default=None, validation_alias="free_delivery_from"
    )
    valor_minimo: Optional[Decimal] = Field(default=None, validation_alias="min_order_value")
    tempo_entrega_min: Optional[int] = Field(default=None, validation_alias="delivery_time_minutes")
    tempo_retirada_min: Optional[int] = Field(default=None, validation_alias="pickup_time_minutes")


class ConfiguracaoEntregaIn(BaseModel):
    entrega_ativa: bool
    retirada_ativa: bool
    modo: DeliveryChargeMode
    valor_fixo: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    frete_gratis_a_partir_de: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    valor_minimo: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    tempo_entrega_min: Optional[int] = Field(default=None, ge=1, le=480)
    tempo_retirada_min: Optional[int] = Field(default=None, ge=1, le=480)

    @model_validator(mode="after")
    def _validar_configuracao(self) -> "ConfiguracaoEntregaIn":
        if not (self.entrega_ativa or self.retirada_ativa):
            raise ValueError("Ative ao menos uma forma de atendimento: entrega ou retirada.")
        if self.modo == DeliveryChargeMode.FIXO and not self.valor_fixo:
            raise ValueError(
                "Informe o valor da taxa fixa, maior que zero. "
                "Para entrega sem taxa, use o modo GRATIS."
            )
        return self