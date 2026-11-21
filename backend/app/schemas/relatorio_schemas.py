from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class StatusResumoOut(BaseModel):
    status: str
    quantidade: int
    valor_total: Decimal


class RelatorioPedidosOut(BaseModel):
    quantidade_pedidos: int
    valor_total: Decimal
    ticket_medio: Decimal
    por_status: list[StatusResumoOut]


class VendaDiaOut(BaseModel):
    data: date
    quantidade_pedidos: int
    total_vendas: Decimal
    ticket_medio: Decimal


class VendaFormaOut(BaseModel):
    forma: str
    quantidade_pedidos: int
    total_vendas: Decimal


class VendaTipoOut(BaseModel):
    tipo_atendimento: str
    quantidade_pedidos: int
    total_vendas: Decimal


class RelatorioVendasOut(BaseModel):
    data_inicio: date
    data_fim: date
    quantidade_pedidos: int
    total_vendas: Decimal
    ticket_medio: Decimal
    por_dia: list[VendaDiaOut]
    por_forma_pagamento: list[VendaFormaOut]
    por_tipo_atendimento: list[VendaTipoOut]


class ItemCampeaoOut(BaseModel):
    posicao: int
    tipo: str
    item_id: UUID | None = None
    nome: str
    quantidade: int


class ItensCampeoesOut(BaseModel):
    data_inicio: date
    data_fim: date
    items: list[ItemCampeaoOut]


class HoraDePicoOut(BaseModel):
    hora: int
    quantidade_pedidos: int
    total_vendas: Decimal


class HorariosDePicoOut(BaseModel):
    data_inicio: date
    data_fim: date
    horas: list[HoraDePicoOut]
    picos: list[HoraDePicoOut]