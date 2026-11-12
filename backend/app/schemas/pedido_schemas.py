import uuid
from decimal import Decimal
from datetime import datetime
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.model.models import OrderServiceType
from app.services import pedido_fluxo

from app.model.models import OrderServiceType

OBSERVACAO_ITEM_MAX = 140


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AlimentoSelecionadoIn(_Entrada):
    alimento_id: uuid.UUID
    quantidade: int = Field(default=1, ge=1, le=20)


class SelecaoCategoriaIn(_Entrada):
    categoria_id: uuid.UUID
    alimentos: List[AlimentoSelecionadoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sem_alimento_repetido(self) -> "SelecaoCategoriaIn":
        ids = [a.alimento_id for a in self.alimentos]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "Alimento repetido na mesma categoria: use a quantidade em uma única linha."
            )
        return self


def _categorias_unicas(selecoes: List[SelecaoCategoriaIn]) -> List[SelecaoCategoriaIn]:
    ids = [s.categoria_id for s in selecoes]
    if len(ids) != len(set(ids)):
        raise ValueError("Categoria repetida nas seleções.")
    return selecoes


class _ItemBase(_Entrada):
    quantidade: int = Field(default=1, ge=1, le=99)
    observacao: Optional[str] = Field(default=None, max_length=OBSERVACAO_ITEM_MAX)

    @field_validator("observacao", mode="before")
    @classmethod
    def _limpar_observacao(cls, valor):
        if isinstance(valor, str):
            valor = valor.strip()
            return valor or None
        return valor


class ItemMarmitaIn(_ItemBase):
    tipo: Literal["MARMITA"]
    marmita_id: uuid.UUID
    selecoes: List[SelecaoCategoriaIn] = Field(default_factory=list)

    @field_validator("selecoes")
    @classmethod
    def _selecoes_unicas(cls, valor):
        return _categorias_unicas(valor)


class MarmitaDoComboIn(_Entrada):
    marmita_id: uuid.UUID
    selecoes: List[SelecaoCategoriaIn] = Field(default_factory=list)

    @field_validator("selecoes")
    @classmethod
    def _selecoes_unicas(cls, valor):
        return _categorias_unicas(valor)


class ItemComboIn(_ItemBase):
    tipo: Literal["COMBO"]
    combo_id: uuid.UUID
    marmitas: List[MarmitaDoComboIn] = Field(default_factory=list)


class ItemAvulsoIn(_ItemBase):
    tipo: Literal["AVULSO"]
    alimento_id: uuid.UUID


ItemPedidoIn = Annotated[
    Union[ItemMarmitaIn, ItemComboIn, ItemAvulsoIn], Field(discriminator="tipo")
]


class OrderCreate(_Entrada):
    restaurante_slug: str = Field(min_length=3, max_length=60, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    tipo_atendimento: OrderServiceType = OrderServiceType.DELIVERY
    endereco_id: Optional[uuid.UUID] = None
    forma_pagamento: Literal["DINHEIRO", "PIX", "CARTAO_CREDITO", "CARTAO_DEBITO"]
    valor_pago_dinheiro: Optional[Decimal] = Field(default=None, ge=0)
    itens: List[ItemPedidoIn] = Field(..., min_length=1, max_length=50)
    observacoes: Optional[str] = None

    @model_validator(mode="after")
    def _exigir_endereco_na_entrega(self) -> "OrderCreate":
        if self.tipo_atendimento == OrderServiceType.DELIVERY and self.endereco_id is None:
            raise ValueError("Informe o endereço de entrega.")
        return self


class OrderReasonIn(_Entrada):
    motivo: str


class OrderSendIn(_Entrada):
    entregador_id: uuid.UUID


class ClientSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str = Field(validation_alias="name")
    telefone: str = Field(validation_alias="phone")


class OrderStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codigo: str = Field(validation_alias="code")
    nome: str = Field(validation_alias="name")
    pago: bool = Field(validation_alias="is_paid")
    final: bool = Field(validation_alias="is_final")


class PaymentMethodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codigo: str = Field(validation_alias="code")
    nome: str = Field(validation_alias="name")


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alimento_id: Optional[uuid.UUID] = Field(default=None, validation_alias="food_id")
    marmita_id: Optional[uuid.UUID] = Field(default=None, validation_alias="meal_box_id")
    combo_id: Optional[uuid.UUID] = None
    nome: str = Field(validation_alias="food_name")
    preco_unitario: Decimal = Field(validation_alias="base_price")
    quantidade: int = Field(validation_alias="quantity")
    subtotal: Decimal
    observacao: Optional[str] = Field(default=None, validation_alias="notes")
    snapshot: Optional[dict] = None


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str = Field(validation_alias="name")


class _StatusDoFluxo(BaseModel):
    @computed_field
    @property
    def status_rotulo(self) -> str:
        return pedido_fluxo.rotulo(self.tipo_atendimento, self.status.codigo, self.status.nome)

    @computed_field
    @property
    def acoes_disponiveis(self) -> List[str]:
        return pedido_fluxo.acoes_disponiveis(self.tipo_atendimento, self.status.codigo)


class OrderOut(_StatusDoFluxo):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    numero_pedido: int = Field(validation_alias="order_number")
    cliente_id: uuid.UUID = Field(validation_alias="client_id")
    cliente: ClientSummaryOut = Field(validation_alias="client")
    status: OrderStatusOut
    forma_pagamento: PaymentMethodOut = Field(validation_alias="payment_method")
    data_hora: datetime = Field(validation_alias="order_datetime")
    tipo_atendimento: OrderServiceType = Field(validation_alias="service_type")
    motivo: Optional[str] = Field(default=None, validation_alias="status_reason")
    entregador: Optional[DriverOut] = Field(default=None, validation_alias="driver")
    endereco_rua: Optional[str] = Field(default=None, validation_alias="address_street")
    endereco_numero: Optional[str] = Field(default=None, validation_alias="address_number")
    endereco_bairro: Optional[str] = Field(default=None, validation_alias="address_neighborhood")

    observacoes: Optional[str] = Field(default=None, validation_alias="notes")
    valor_itens: Decimal = Field(validation_alias="items_amount")
    valor_entrega: Decimal = Field(validation_alias="delivery_fee")
    valor_total: Decimal = Field(validation_alias="total_amount")
    valor_troco: Optional[Decimal] = Field(default=None, validation_alias="change_amount")

    itens: List[OrderItemOut] = Field(default=[], validation_alias="items")


class OrderListItemOut(_StatusDoFluxo):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: uuid.UUID
    numero_pedido: int = Field(validation_alias="order_number")
    cliente_id: uuid.UUID = Field(validation_alias="client_id")
    cliente_nome: str
    status: OrderStatusOut
    data_hora: datetime = Field(validation_alias="order_datetime")
    tipo_atendimento: OrderServiceType = Field(validation_alias="service_type")
    valor_total: Decimal = Field(validation_alias="total_amount")
    itens: List[OrderItemOut] = Field(default=[], validation_alias="items")


class PaginatedOrdersOut(BaseModel):
    items: List[OrderListItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int