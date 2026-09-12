import uuid
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ReceivingAccountBase(BaseModel):
    pix_key: str = Field(..., min_length=1, max_length=140)
    pix_key_type: Literal["CPF", "CNPJ", "EMAIL", "TELEFONE", "ALEATORIA"]
    account_holder: str = Field(..., min_length=1, max_length=150)
    city: str = Field(
        ..., min_length=1, max_length=15,
        description="Cidade do titular, exigida pelo padrão Pix (máx. 15 caracteres)",
    )


class ReceivingAccountIn(ReceivingAccountBase):
    pass


class ReceivingAccountOut(ReceivingAccountBase):
    id: uuid.UUID
    active: bool

    class Config:
        from_attributes = True


class PixGenerateIn(BaseModel):
    amount: Decimal = Field(..., gt=0)


class PixGenerateOut(BaseModel):
    copy_and_paste_code: str
    pix_key: str
    account_holder: str
    amount: Decimal


class PaymentCardIn(BaseModel):
    method: Literal["CARTAO_CREDITO", "CARTAO_DEBITO"]
    number: str = Field(..., min_length=13, max_length=19)
    name: str = Field(..., min_length=3, max_length=150)
    expiration: str = Field(..., pattern=r"^\d{2}/\d{2}$", description="Formato MM/AA")
    cvv: str = Field(..., min_length=3, max_length=4)
    amount: Decimal = Field(..., gt=0)

    @field_validator("number")
    @classmethod
    def digits_only(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            raise ValueError("Número de cartão inválido")
        return digits

    @field_validator("cvv")
    @classmethod
    def cvv_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("CVV inválido")
        return v


class PaymentResultOut(BaseModel):
    status: Literal["APROVADO", "RECUSADO"]
    transaction_id: Optional[uuid.UUID] = None
    message: str