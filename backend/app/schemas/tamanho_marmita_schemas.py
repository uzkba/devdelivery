import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TamanhoMarmitaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=30)
    ordem_exibicao: int = 0


class TamanhoMarmitaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=30)
    ordem_exibicao: Optional[int] = None
    ativo: Optional[bool] = None


class TamanhoMarmitaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    ordem_exibicao: int
    ativo: bool

    @classmethod
    def from_model(cls, tamanho) -> "TamanhoMarmitaResponse":
        return cls(
            id=tamanho.id,
            nome=tamanho.name,
            ordem_exibicao=tamanho.display_order,
            ativo=tamanho.is_active,
        )


class LimiteCategoriaTamanhoSet(BaseModel):
    categoria_id: uuid.UUID
    quantidade_maxima: int = Field(..., ge=0)


class LimiteCategoriaTamanhoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    categoria_id: uuid.UUID
    quantidade_maxima: int

    @classmethod
    def from_model(cls, limite) -> "LimiteCategoriaTamanhoResponse":
        return cls(
            id=limite.id,
            categoria_id=limite.category_id,
            quantidade_maxima=limite.max_quantity,
        )