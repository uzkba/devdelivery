from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.model.models import AuditLog

ACAO_CRIACAO = "CRIACAO"
ACAO_EDICAO = "EDICAO"
ACAO_EXCLUSAO = "EXCLUSAO"

# Campos que NUNCA devem ir pro snapshot, por entidade.
CAMPOS_EXCLUIDOS: dict[str, set[str]] = {
    "alimento": set(),
    "pedido": set(),
}


def serializar_entidade(entidade: Any, nome_entidade: str) -> dict:
    excluidos = CAMPOS_EXCLUIDOS.get(nome_entidade, set())
    dados = {}
    for attr in inspect(entidade).mapper.column_attrs:
        nome_attr = attr.key
        if nome_attr in excluidos:
            continue
        valor = getattr(entidade, nome_attr)
        if isinstance(valor, UUID):
            valor = str(valor)
        elif isinstance(valor, datetime):
            valor = valor.isoformat()
        elif isinstance(valor, Decimal):
            valor = str(valor)
        dados[nome_attr] = valor
    return dados


def registrar_log_auditoria(
    db: Session,
    *,
    restaurant_id: UUID,
    user_id: UUID | None,
    entidade: str,
    entidade_id: UUID | str,
    acao: str,
    dados_anteriores: Any | None = None,
    dados_novos: Any | None = None,
) -> AuditLog:
    def _norm(dado):
        if dado is None or isinstance(dado, dict):
            return dado
        return serializar_entidade(dado, entidade)

    log = AuditLog(
        restaurant_id=restaurant_id,
        user_id=user_id,
        entity=entidade,
        entity_id=str(entidade_id),
        action=acao,
        previous_data=_norm(dados_anteriores),
        new_data=_norm(dados_novos),
    )
    db.add(log)
    return log