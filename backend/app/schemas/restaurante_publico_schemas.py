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
    modo: str
    valor_fixo: Optional[Decimal] = None
    taxa_minima: Optional[Decimal] = None
    taxa_maxima: Optional[Decimal] = None
    frete_gratis_a_partir_de: Optional[Decimal] = None


class EntregaPublicaOut(BaseModel):
    entrega_ativa: bool
    retirada_ativa: bool
    valor_minimo: Optional[Decimal] = None
    tempo_entrega_min: Optional[int] = None
    tempo_retirada_min: Optional[int] = None
    taxa: TaxaEntregaOut


class FaixaHorarioOut(BaseModel):
    abre_as: str
    fecha_as: str


class HorarioDiaOut(BaseModel):
    dia_semana: int
    faixas: list[FaixaHorarioOut]


class ProximaAberturaOut(BaseModel):
    em_dias: int
    dia_semana: int
    abre_as: str


class EstadoOperacaoOut(BaseModel):
    estado: str
    aceita_pedidos: bool
    horario_definido: bool
    motivo: Optional[str] = None
    pausado_ate: Optional[datetime] = None
    proxima_abertura: Optional[ProximaAberturaOut] = None


class FormaPagamentoPublicaOut(BaseModel):
    codigo: str
    nome: str


class RestaurantePublicoOut(BaseModel):
    slug: str
    nome: str
    telefone: Optional[str] = None
    endereco: EnderecoPublicoOut
    estado: EstadoOperacaoOut
    horarios: list[HorarioDiaOut]
    entrega: Optional[EntregaPublicaOut] = None
    formas_pagamento: list[FormaPagamentoPublicaOut]