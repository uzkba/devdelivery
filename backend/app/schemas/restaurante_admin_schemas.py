from datetime import time
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.disponibilidade_schemas import DiaDaSemana
from app.schemas.restaurante_publico_schemas import (
    EnderecoPublicoOut,
    EstadoOperacaoOut,
    HorarioDiaOut,
)


# --------------------------------- saida ---------------------------------
class RestauranteAdminOut(BaseModel):
    slug: str
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    endereco: EnderecoPublicoOut
    estado: EstadoOperacaoOut
    horarios: list[HorarioDiaOut]


class SlugDisponivelOut(BaseModel):
    slug: str
    disponivel: bool
    motivo: Optional[str] = None


# ------------------------------ dados e link ------------------------------
def _limpar(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class EnderecoIn(BaseModel):
    rua: Optional[str] = Field(default=None, max_length=150)
    numero: Optional[str] = Field(default=None, max_length=20)
    bairro: Optional[str] = Field(default=None, max_length=100)
    cidade: Optional[str] = Field(default=None, max_length=100)

    @field_validator("rua", "numero", "bairro", "cidade")
    @classmethod
    def _limpar_texto(cls, valor: Optional[str]) -> Optional[str]:
        return _limpar(valor)


class RestauranteAtualizarIn(BaseModel):
    nome: Optional[str] = Field(default=None, max_length=150)
    telefone: Optional[str] = Field(default=None, max_length=20)
    slug: Optional[str] = Field(default=None, max_length=60)
    endereco: Optional[EnderecoIn] = None

    @field_validator("nome")
    @classmethod
    def _validar_nome(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        valor = valor.strip()
        if len(valor) < 2:
            raise ValueError("O nome deve ter ao menos 2 caracteres.")
        return valor

    @field_validator("telefone")
    @classmethod
    def _validar_telefone(cls, valor: Optional[str]) -> Optional[str]:
        return _limpar(valor)

    @field_validator("slug")
    @classmethod
    def _normalizar_slug(cls, valor: Optional[str]) -> Optional[str]:
        return None if valor is None else valor.strip().lower()

    @model_validator(mode="after")
    def _nome_e_slug_nao_aceitam_nulo(self) -> "RestauranteAtualizarIn":
        for campo in ("nome", "slug"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


# --------------------------------- horarios --------------------------------
class FaixaIn(BaseModel):
    abre_as: time
    fecha_as: time

    @field_validator("abre_as", "fecha_as")
    @classmethod
    def _formato_hhmm(cls, valor: time) -> time:
        if valor.tzinfo is not None or valor.second or valor.microsecond:
            raise ValueError("Use o formato HH:MM, sem segundos nem fuso.")
        return valor

    @model_validator(mode="after")
    def _fechar_depois_de_abrir(self) -> "FaixaIn":
        if self.fecha_as <= self.abre_as:
            raise ValueError(
                "O horário de fechar deve ser depois do de abrir. "
                "Não é possível cruzar a meia-noite: para fechar à meia-noite, use 23:59."
            )
        return self


class HorarioDiaIn(BaseModel):
    dia_semana: DiaDaSemana
    faixas: list[FaixaIn] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _sem_sobreposicao(self) -> "HorarioDiaIn":
        ordenadas = sorted(self.faixas, key=lambda f: f.abre_as)
        for anterior, atual in zip(ordenadas, ordenadas[1:]):
            if atual.abre_as < anterior.fecha_as:
                raise ValueError("Há faixas de horário sobrepostas no mesmo dia.")
        return self


class HorariosIn(BaseModel):
    dias: list[HorarioDiaIn] = Field(max_length=7)

    @model_validator(mode="after")
    def _validar_grade(self) -> "HorariosIn":
        dias = [d.dia_semana for d in self.dias]
        if len(set(dias)) != len(dias):
            raise ValueError("Dia da semana repetido.")
        if not any(d.faixas for d in self.dias):
            raise ValueError(
                "Cadastre ao menos uma faixa de funcionamento "
                "(para parar de receber pedidos, use a pausa)."
            )
        return self


# ---------------------------------- pausa ----------------------------------
class PausaIn(BaseModel):
    pausado: bool
    minutos: Optional[int] = Field(default=None, ge=1, le=10080)

    @model_validator(mode="after")
    def _minutos_so_ao_pausar(self) -> "PausaIn":
        if not self.pausado and self.minutos is not None:
            raise ValueError("'minutos' só vale ao pausar.")
        return self