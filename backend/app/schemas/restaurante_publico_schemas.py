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


class RestaurantePublicoOut(BaseModel):
    slug: str
    nome: str
    telefone: Optional[str] = None
    endereco: EnderecoPublicoOut
    entrega: Optional[EntregaPublicaOut] = None