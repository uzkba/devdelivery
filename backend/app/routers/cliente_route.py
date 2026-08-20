from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.depedencias import require_role
from backend.app.model.models import Client
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser
from backend.app.schemas.cliente_schemas import ClienteCreate, ClienteOut

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
    admin: AuthenticatedUser = Depends(require_role("admin")),
):
    existente = db.query(Client).filter(Client.phone == cliente.phone).first()
    if existente:
        raise HTTPException(status_code=400, detail="Já existe cliente com esse telefone")

    novo_cliente = Client(name=cliente.name, phone=cliente.phone)
    db.add(novo_cliente)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe cliente com esse telefone",
        )

    db.refresh(novo_cliente)
    return novo_cliente