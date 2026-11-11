import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.texto import limpar_espacos


class BairroIn(BaseModel):
    bairro: str = Field(min_length=1, max_length=120)
    taxa: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    ativo: bool = True

    @field_validator("bairro")
    @classmethod
    def _limpar_nome(cls, valor: str) -> str:
        valor = limpar_espacos(valor)
        if not valor:
            raise ValueError("Informe o nome do bairro.")
        return valor


class BairroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bairro: str = Field(validation_alias="neighborhood")
    taxa: Decimal = Field(validation_alias="fee")
    ativo: bool = Field(validation_alias="is_active")