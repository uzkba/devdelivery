import uuid
from decimal import Decimal
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.model.models import OrderServiceType

OBSERVACAO_ITEM_MAX = 140


class _Entrada(BaseModel):
    # campo desconhecido (ex.: restaurante_id antigo, preco) vira 422 explicito
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Configuracao de marmita personalizavel
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Itens do pedido (discriminados por "tipo")
# ---------------------------------------------------------------------------
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
    # PRONTA: vazio. PERSONALIZAVEL: uma entrada por categoria com quantidade exigida > 0.
    selecoes: List[SelecaoCategoriaIn] = Field(default_factory=list)

    _validar_selecoes = field_validator("selecoes")(_categorias_unicas)


class MarmitaDoComboIn(_Entrada):
    marmita_id: uuid.UUID
    selecoes: List[SelecaoCategoriaIn] = Field(default_factory=list)

    _validar_selecoes = field_validator("selecoes")(_categorias_unicas)


class ItemComboIn(_ItemBase):
    tipo: Literal["COMBO"]
    combo_id: uuid.UUID
    # Uma entrada por UNIDADE de marmita personalizavel do combo (marmita pronta nao precisa).
    marmitas: List[MarmitaDoComboIn] = Field(default_factory=list)


class ItemAvulsoIn(_ItemBase):
    tipo: Literal["AVULSO"]
    alimento_id: uuid.UUID


ItemPedidoIn = Annotated[
    Union[ItemMarmitaIn, ItemComboIn, ItemAvulsoIn], Field(discriminator="tipo")
]


# ---------------------------------------------------------------------------
# Pedido
# ---------------------------------------------------------------------------
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
