from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class EnderecoPublicoOut(BaseModel):
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None


class TaxaEntregaOut(BaseModel):
    modo: str  # GRATIS | FIXO | BAIRRO
    valor_fixo: Optional[Decimal] = None
    taxa_minima: Optional[Decimal] = None
    taxa_maxima: Optional[Decimal] = None


class EntregaPublicaOut(BaseModel):
    entrega_ativa: bool
    retirada_ativa: bool
    valor_minimo: Optional[Decimal] = None
    tempo_entrega_min: Optional[int] = None
    tempo_retirada_min: Optional[int] = None
    taxa: TaxaEntregaOut


class FaixaHorarioOut(BaseModel):
    abre_as: str  # "HH:MM"
    fecha_as: str  # "HH:MM"


class HorarioDiaOut(BaseModel):
    dia_semana: int  # 0 = segunda ... 6 = domingo
    faixas: list[FaixaHorarioOut]  # lista vazia = fechado nesse dia


class ProximaAberturaOut(BaseModel):
    em_dias: int  # 0 = hoje, 1 = amanha ...
    dia_semana: int
    abre_as: str


class EstadoOperacaoOut(BaseModel):
    estado: str  # ABERTO | PAUSADO | FECHADO
    aceita_pedidos: bool
    horario_definido: bool
    motivo: Optional[str] = None
    pausado_ate: Optional[datetime] = None
    proxima_abertura: Optional[ProximaAberturaOut] = None


class RestaurantePublicoOut(BaseModel):
    slug: str
    nome: str
    telefone: Optional[str] = None
    endereco: EnderecoPublicoOut
    estado: EstadoOperacaoOut
    horarios: list[HorarioDiaOut]
    entrega: Optional[EntregaPublicaOut] = None