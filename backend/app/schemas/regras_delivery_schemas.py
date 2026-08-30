import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class DeliveryRuleBase(BaseModel):
    min_distance_km: Decimal = Field(..., ge=0, description="Distância mínima em KM")
    max_distance_km: Decimal = Field(..., gt=0, description="Distância máxima em KM")
    fee: Decimal = Field(..., ge=0, description="Valor da taxa de entrega")
    is_active: bool = True

class DeliveryRuleCreate(DeliveryRuleBase):
    @model_validator(mode='after')
    def check_distances(self) -> 'DeliveryRuleCreate':
        if self.min_distance_km >= self.max_distance_km:
            raise ValueError('A distância mínima deve ser estritamente menor que a distância máxima.')
        return self

class DeliveryRuleOut(DeliveryRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurant_id: uuid.UUID