from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.app.core.database import get_db
from backend.app.api.depedencias import require_role
from backend.app.core.seguranca import (
    hash_password,
    verify_password,
    create_access_token as create_access_token_cliente,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser, TokenResponse
from backend.app.schemas.cliente_schemas import (
    ClienteCreate,
    ClienteOut,
    ClienteRegistrarIn,
    ClienteLoginIn,
)
from backend.app.model.models import Client
from backend.app.services import cliente_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_role("admin")),
):
    return cliente_service.criar_cliente(db, cliente.name, cliente.phone)


@router.post("/registrar", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def registrar_cliente(
    payload: ClienteRegistrarIn,
    db: Session = Depends(get_db),
):
    return cliente_service.criar_cliente(
        db, payload.name, payload.phone, hashed_password=hash_password(payload.password)
    )


@router.post("/login", response_model=TokenResponse)
def login_cliente(payload: ClienteLoginIn, db: Session = Depends(get_db)) -> TokenResponse:
    cliente = db.scalar(select(Client).where(Client.phone == payload.phone))

    if cliente is None or not verify_password(payload.password, cliente.hashed_password):
        raise HTTPException(status_code=401, detail="Telefone ou senha inválidos.")

    if not cliente.is_active:
        raise HTTPException(status_code=403, detail="Cliente inativo.")

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token_cliente(
        data={"sub": str(cliente.id), "type": "client"},
        expires_delta=expires,
    )

    return TokenResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
    )