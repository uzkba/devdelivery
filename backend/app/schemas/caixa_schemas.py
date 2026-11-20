import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AbrirCaixaIn(BaseModel):
    data: date | None = None


class AcertoEntregadorIn(BaseModel):
    entregador_id: uuid.UUID
    valor_repassado: Decimal


class FecharCaixaIn(BaseModel):
    data: date | None = None
    contagem: dict[str, Decimal] = Field(default_factory=dict)
    acertos: list[AcertoEntregadorIn] = Field(default_factory=list)
    observacoes: str | None = None


class ReabrirCaixaIn(BaseModel):
    data: date


class FormaOut(BaseModel):
    forma: str
    quantidade_pedidos: int
    valor_esperado: Decimal
    valor_contado: Decimal | None = None
    diferenca: Decimal | None = None


class EntregadorOut(BaseModel):
    entregador_id: uuid.UUID
    nome: str
    quantidade_entregas: int
    valor_esperado: Decimal
    valor_repassado: Decimal | None = None
    diferenca: Decimal | None = None


class CaixaDiaOut(BaseModel):
    data: date
    status: str
    aberto_por: uuid.UUID | None = None
    aberto_em: datetime | None = None
    fechado_por: uuid.UUID | None = None
    fechado_em: datetime | None = None
    reaberto_por: uuid.UUID | None = None
    reaberto_em: datetime | None = None
    reaberturas: int
    fechamento_id: uuid.UUID | None = None
    pode_fechar: bool
    pedidos_em_aberto: int
    quantidade_pedidos: int
    quantidade_cancelados: int
    total_vendas: Decimal
    total_dinheiro_recebido: Decimal
    total_troco: Decimal
    diferenca_total: Decimal | None = None
    observacoes: str | None = None
    formas: list[FormaOut]
    entregadores: list[EntregadorOut]