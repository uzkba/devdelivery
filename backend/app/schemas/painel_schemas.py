import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.model.models import OrderServiceType
from app.schemas.restaurante_publico_schemas import EstadoOperacaoOut


class _Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RestauranteHojeOut(_Saida):
    nome: str
    estado: EstadoOperacaoOut
    fecha_as: Optional[str] = None


class FilaHojeOut(_Saida):
    novos: int
    preparo: int
    saindo: int
    entregues: int
    espera_mais_antiga_min: Optional[int] = None


class PedidoEmAndamentoOut(_Saida):
    pedido_id: uuid.UUID
    numero_pedido: int
    cliente_nome: str
    etapa: str
    status: str
    status_rotulo: str
    tipo_atendimento: OrderServiceType
    itens_resumo: str
    bairro: Optional[str] = None
    minutos: int
    atrasado: bool
    valor_total: Decimal
    acoes_disponiveis: List[str]


class AlertaOut(_Saida):
    codigo: str
    gravidade: str
    titulo: str
    detalhe: str
    destino: str
    quantidade: int


class ResumoPeriodoOut(_Saida):
    vendas: Decimal
    pedidos: int
    ticket_medio: Decimal
    entrega_media_min: Optional[int] = None


class ResumoDiaOut(_Saida):
    dia: date
    comparado_com: date
    rotulo_comparacao: str
    atual: ResumoPeriodoOut
    anterior: ResumoPeriodoOut
    variacao_vendas_pct: Optional[Decimal] = None
    diferenca_pedidos: int
    diferenca_ticket_medio: Decimal
    diferenca_entrega_min: Optional[int] = None


class MaisVendidoOut(_Saida):
    tipo: str
    item_id: Optional[uuid.UUID] = None
    nome: str
    quantidade: int


class HojeOut(_Saida):
    data: date
    restaurante: RestauranteHojeOut
    fila: FilaHojeOut
    em_andamento: List[PedidoEmAndamentoOut]
    atencao: List[AlertaOut]
    resumo: ResumoDiaOut
    mais_vendidos: List[MaisVendidoOut]


class AvisoOut(_Saida):
    tipo: str
    gravidade: str
    titulo: str
    detalhe: str
    destino: str
    quantidade: int
    pedido_id: Optional[uuid.UUID] = None
    numero_pedido: Optional[int] = None
    minutos: Optional[int] = None


class AvisosOut(_Saida):
    total: int
    avisos: List[AvisoOut]