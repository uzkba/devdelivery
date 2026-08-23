"""
app/schemas/categoria_alimento_schemas.py

Schemas do CRUD de categoria de alimento, alinhados ao model FoodCategory:
- atributos Python do model são em inglês (name, description, display_order,
  is_active, restaurant_id), com as colunas do banco em português via
  mapped_column("nome_coluna", ...).
- os schemas de RESPOSTA usam `validation_alias` para ler o atributo Python
  correto do objeto ORM, mas mantêm o nome do campo (e portanto a chave no
  JSON de saída) em português — sem validation_alias, o Pydantic tentaria
  ler um atributo "descricao"/"ordem_exibicao"/"ativo" que não existe no
  objeto Python (esse foi o bug do ResponseValidationError).
- os schemas de ENTRADA (Create/Update) não vêm de um objeto ORM, então
  não precisam de alias — o service.py já faz a tradução manual
  (dados.nome -> name=..., etc.) na hora de montar o FoodCategory.
"""
import uuid
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CategoriaAlimentoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60, description="Nome da categoria (ex: Bebidas)")
    descricao: Optional[str] = Field(None, description="Descrição opcional da categoria")
    ordem_exibicao: int = Field(0, ge=0, description="Ordem de exibição no cardápio")

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
    """Payload para POST /categorias. restaurante_id vem do usuário autenticado."""
    pass


class CategoriaAlimentoUpdate(BaseModel):
    """Payload para PUT /categorias/:id. Todos os campos opcionais."""
    nome: Optional[str] = Field(None, min_length=1, max_length=60)
    descricao: Optional[str] = None
    ordem_exibicao: Optional[int] = Field(None, ge=0)
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_vazio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("O nome da categoria não pode ser vazio.")
        return v


class CategoriaAlimentoResponse(BaseModel):
    id: uuid.UUID
    restaurante_id: uuid.UUID = Field(..., validation_alias="restaurant_id")
    nome: str = Field(..., validation_alias="name")
    descricao: Optional[str] = Field(None, validation_alias="description")
    ordem_exibicao: int = Field(..., validation_alias="display_order")
    ativo: bool = Field(..., validation_alias="is_active")

    model_config = {"from_attributes": True, "populate_by_name": True}