from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    id: UUID
    usuario_id: UUID | None = Field(validation_alias="user_id")
    entidade: str = Field(validation_alias="entity")
    entidade_id: str = Field(validation_alias="entity_id")
    acao: str = Field(validation_alias="action")
    dados_anteriores: dict | None = Field(validation_alias="previous_data")
    dados_novos: dict | None = Field(validation_alias="new_data")
    criado_em: datetime = Field(validation_alias="created_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)