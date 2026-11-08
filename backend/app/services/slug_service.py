import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.slug import (
    SLUG_MAX,
    SLUG_MIN,
    SLUGS_RESERVADOS,
    motivo_slug_invalido,
    normalizar_slug,
)
from app.model.models import Restaurant


def slug_disponivel(
    db: Session, slug: str, excluir_restaurante_id: uuid.UUID | None = None
) -> bool:
    query = db.query(Restaurant.id).filter(Restaurant.slug == slug)
    if excluir_restaurante_id is not None:
        query = query.filter(Restaurant.id != excluir_restaurante_id)
    return query.first() is None


def gerar_slug_unico(db: Session, base: str) -> str:
    slug_base = normalizar_slug(base)
    if len(slug_base) < SLUG_MIN:
        slug_base = "restaurante"
    elif slug_base in SLUGS_RESERVADOS:
        slug_base = f"{slug_base}-restaurante"

    candidato = slug_base
    contador = 2
    while not slug_disponivel(db, candidato):
        sufixo = f"-{contador}"
        candidato = f"{slug_base[: SLUG_MAX - len(sufixo)].rstrip('-')}{sufixo}"
        contador += 1
    return candidato


def garantir_slug_valido_e_livre(
    db: Session, slug: str, excluir_restaurante_id: uuid.UUID | None = None
) -> str:
    motivo = motivo_slug_invalido(slug)
    if motivo is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, motivo)
    if not slug_disponivel(db, slug, excluir_restaurante_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este link já está em uso por outro restaurante.")
    return slug