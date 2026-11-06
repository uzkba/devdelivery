import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class CategoriaAlimentoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60, description="Nome da categoria (ex: Bebidas)")
    descricao: Optional[str] = Field(None, description="Descrição opcional da categoria")
    ordem_exibicao: int = Field(0, ge=0, description="Ordem de exibição no cardápio")
    tipo: Literal["composicao", "venda"] = Field(
        "composicao",
        description="composicao = monta marmitas (arroz, proteína...); venda = produtos avulsos (pratos, bebidas...)",
    )

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O nome da categoria não pode ser vazio.")
        return v

    @field_validator("descricao")
    @classmethod
    def descricao_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v or None
        return v


class CategoriaAlimentoCreate(CategoriaAlimentoBase):
    grupo: Optional[Literal["prato", "bebida"]] = Field(
        None, description="Só categoria de venda. Padrão: prato."
    )

    @model_validator(mode="after")
    def validar_grupo(self):
        if self.tipo == "venda":
            if self.grupo is None:
                self.grupo = "prato"
        elif self.grupo is not None:
            raise ValueError("Apenas categorias de venda possuem grupo.")
        return self


class CategoriaAlimentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=60)
    descricao: Optional[str] = None
    ordem_exibicao: Optional[int] = Field(None, ge=0)
    ativo: Optional[bool] = None
    grupo: Optional[Literal["prato", "bebida"]] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_vazio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("O nome da categoria não pode ser vazio.")
        return v

    @field_validator("grupo")
    @classmethod
    def grupo_nao_nulo(cls, v):
        if v is None:
            raise ValueError("grupo não pode ser null.")
        return v


class CategoriaAlimentoResponse(BaseModel):
    id: uuid.UUID
    restaurante_id: uuid.UUID = Field(..., validation_alias="restaurant_id")
    nome: str = Field(..., validation_alias="name")
    descricao: Optional[str] = Field(None, validation_alias="description")
    ordem_exibicao: int = Field(..., validation_alias="display_order")
    ativo: bool = Field(..., validation_alias="is_active")
    tipo: str = Field(..., validation_alias="type")
    grupo: Optional[str] = Field(None, validation_alias="group")
    model_config = {"from_attributes": True, "populate_by_name": True}


class CategoriaAlimentoUpdateResponse(CategoriaAlimentoResponse):
    """Resposta do PUT: informa quantos itens mudaram de seção ao trocar o grupo."""
    itens_movidos: int = 0