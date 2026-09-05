import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.depedencias import require_role
from backend.app.model.models import Client, CustomerAddress
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser
from backend.app.schemas.endereco_schemas import EnderecoCreate, EnderecoOut, EnderecoUpdate

router = APIRouter(prefix="/clientes/{cliente_id}/enderecos", tags=["Endereços"])


def _get_cliente_ou_404(cliente_id: uuid.UUID, db: Session) -> Client:
    cliente = db.get(Client, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return cliente


@router.post("/", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco(
    cliente_id: uuid.UUID,
    endereco: EnderecoCreate,
    db: Session = Depends(get_db),
):
    _get_cliente_ou_404(cliente_id, db)

    novo_endereco = CustomerAddress(client_id=cliente_id, **endereco.model_dump())
    db.add(novo_endereco)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um endereço principal cadastrado para este cliente",
        )

    db.refresh(novo_endereco)
    return novo_endereco


@router.get("/", response_model=list[EnderecoOut])
def listar_enderecos(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    _get_cliente_ou_404(cliente_id, db)

    return (
        db.query(CustomerAddress)
        .filter(CustomerAddress.client_id == cliente_id)
        .all()
    )

def _get_endereco_ou_404(cliente_id: uuid.UUID, endereco_id: uuid.UUID, db: Session) -> CustomerAddress:
    endereco = (
        db.query(CustomerAddress)
        .filter(
            CustomerAddress.id == endereco_id,
            CustomerAddress.client_id == cliente_id,
        )
        .first()
    )
    if endereco is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado para este cliente",
        )
    return endereco


@router.put("/{endereco_id}", response_model=EnderecoOut)
def atualizar_endereco(
    cliente_id: uuid.UUID,
    endereco_id: uuid.UUID,
    dados: EnderecoUpdate,
    db: Session = Depends(get_db),
):
    _get_cliente_ou_404(cliente_id, db)
    endereco = _get_endereco_ou_404(cliente_id, endereco_id, db)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(endereco, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um endereço principal cadastrado para este cliente",
        )

    db.refresh(endereco)
    return endereco


@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_endereco(
    cliente_id: uuid.UUID,
    endereco_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _get_cliente_ou_404(cliente_id, db)
    endereco = _get_endereco_ou_404(cliente_id, endereco_id, db)

    db.delete(endereco)
    db.commit()