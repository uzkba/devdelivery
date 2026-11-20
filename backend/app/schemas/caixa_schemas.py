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


class FechamentoResumoOut(BaseModel):
    id: uuid.UUID
    data_inicio: date
    data_fim: date
    total_vendas: Decimal
    quantidade_pedidos: int
    quantidade_cancelados: int
    valor_esperado: Decimal
    valor_informado: Decimal
    diferenca: Decimal
    tem_diferenca: bool
    fechado_por: uuid.UUID
    fechado_por_nome: str | None = None
    fechado_em: datetime
    observacoes: str | None = None


class FechamentoDetalheOut(FechamentoResumoOut):
    total_dinheiro_recebido: Decimal
    total_troco: Decimal
    formas: list[FormaOut]
    entregadores: list[EntregadorOut]


class HistoricoOut(BaseModel):
    items: list[FechamentoResumoOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class MovimentoOut(BaseModel):
    pedido_id: uuid.UUID
    numero_pedido: int
    data_hora: datetime
    cliente: str
    status: str
    status_nome: str
    tipo_atendimento: str
    forma_pagamento: str
    total: Decimal
    entregador_id: uuid.UUID | None = None
    entregador_nome: str | None = None
    conta_no_caixa: bool


class MovimentosOut(BaseModel):
    data: date
    items: list[MovimentoOut]
    total: int
    page: int
    page_size: int
    total_pages: int