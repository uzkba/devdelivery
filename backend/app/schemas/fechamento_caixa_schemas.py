import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class CashClosingCreate(BaseModel):
    restaurante_id: uuid.UUID
    data_inicio: date
    data_fim: date
    reported_amount: Decimal = Field(..., ge=0, description="Valor de dinheiro contado pelo operador")
    observacoes: Optional[str] = None


class CashClosingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurante_id: uuid.UUID
    data_inicio: date
    data_fim: date
    total_vendas: Decimal
    quantidade_pedidos: int
    quantidade_cancelados: int
    totais_por_forma_pagamento: Dict[str, Decimal]
    total_dinheiro_recebido: Decimal
    total_troco: Decimal
    valor_esperado: Decimal
    valor_informado: Decimal
    diferenca: Decimal
    fechado_por: uuid.UUID
    fechado_em: datetime
    observacoes: Optional[str] = None


class PaginatedCashClosingsOut(BaseModel):
    items: list[CashClosingOut]
    total: int
    page: int
    page_size: int
    total_pages: int