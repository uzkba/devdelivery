from decimal import Decimal
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