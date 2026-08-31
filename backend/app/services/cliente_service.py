import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.seguranca import hash_password
from app.model.models import Client


def criar_cliente(db: Session, name: str, phone: str, hashed_password: str | None = None) -> Client:
    existente = db.query(Client).filter(Client.phone == phone).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe cliente com esse telefone")

    novo_cliente = Client(name=name, phone=phone)
    novo_cliente.hashed_password = hashed_password or hash_password(uuid.uuid4().hex)

    db.add(novo_cliente)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        constraint = getattr(getattr(e.orig, "diag", None), "constraint_name", "") or ""
        if "telefone" in constraint or "phone" in constraint:
            raise HTTPException(status_code=409, detail="Já existe cliente com esse telefone")
        raise

    db.refresh(novo_cliente)
    return novo_cliente