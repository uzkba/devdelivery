from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class ModoDisponibilidade(str, Enum):
    TODOS_OS_DIAS = "TODOS_OS_DIAS"
    PERSONALIZADO = "PERSONALIZADO"


DiaDaSemana = Annotated[int, Field(ge=0, le=6)]  # 0 = segunda ... 6 = domingo


class RegraIn(BaseModel):
    modo: ModoDisponibilidade
    dias: list[DiaDaSemana] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_dias(self) -> "RegraIn":
        if len(set(self.dias)) != len(self.dias):
            raise ValueError("Dia da semana repetido.")
        if self.modo == ModoDisponibilidade.PERSONALIZADO and not self.dias:
            raise ValueError(
                "Informe ao menos um dia da semana (para parar de vender, desative o item)."
            )
        if self.modo == ModoDisponibilidade.TODOS_OS_DIAS and self.dias:
            raise ValueError("O modo TODOS_OS_DIAS não aceita dias.")
        return self


class ExcecaoIn(BaseModel):
    disponivel: bool


class EsgotadoIn(BaseModel):
    esgotado: bool


class ExcecaoOut(BaseModel):
    data: date
    disponivel: bool


class DisponibilidadeOut(BaseModel):
    modo: ModoDisponibilidade
    dias: list[int]
    excecoes: list[ExcecaoOut]
    serve_hoje: bool
    esgotado_hoje: bool