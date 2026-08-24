import uuid
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
class OrderItemOptionCreate(BaseModel):
    opcao_complemento_id: uuid.UUID
    quantidade: int = Field(default=1, gt=0)

class OrderItemCreate(BaseModel):
    alimento_id: uuid.UUID
    quantidade: int = Field(default=1, gt=0)
    observacoes: Optional[str] = None
    opcoes_selecionadas: List[OrderItemOptionCreate] = []

class OrderCreate(BaseModel):
    cliente_id: uuid.UUID
    endereco_id: uuid.UUID
    forma_pagamento_id: uuid.UUID
    valor_entrega: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_pago_dinheiro: Optional[Decimal] = Field(default=None, ge=0) 
    itens: List[OrderItemCreate] = Field(..., min_length=1)
    observacoes: Optional[str] = None

class OrderItemOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    opcao_complemento_id: Optional[uuid.UUID] = Field(validation_alias="modifier_option_id")
    nome_opcao: str = Field(validation_alias="option_name")
    preco_adicional_unitario: Decimal = Field(validation_alias="extra_price")
    quantidade: int = Field(validation_alias="quantity")  

class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alimento_id: Optional[uuid.UUID] = Field(validation_alias="food_id")
    nome_alimento: str = Field(validation_alias="food_name")
    preco_base_unitario: Decimal = Field(validation_alias="base_price")
    quantidade: int = Field(validation_alias="quantity")  # <-- CORRIGIDO AQUI!
    subtotal: Decimal
    observacoes: Optional[str] = Field(default=None, validation_alias="notes")
    opcoes_selecionadas: List[OrderItemOptionOut] = Field(default=[], validation_alias="selected_options")

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    numero_pedido: int = Field(validation_alias="order_number")
    cliente_id: uuid.UUID = Field(validation_alias="client_id")
    status_id: uuid.UUID = Field(validation_alias="status_id")
    data_hora: datetime = Field(validation_alias="order_datetime")

    endereco_rua: str = Field(validation_alias="address_street")
    endereco_numero: str = Field(validation_alias="address_number")
    endereco_bairro: str = Field(validation_alias="address_neighborhood")

    valor_itens: Decimal = Field(validation_alias="items_amount")
    valor_entrega: Decimal = Field(validation_alias="delivery_fee")
    valor_total: Decimal = Field(validation_alias="total_amount")
    valor_troco: Optional[Decimal] = Field(default=None, validation_alias="change_amount") # <-- CORRIGIDO AQUI!

    itens: List[OrderItemOut] = Field(default=[], validation_alias="items")