import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import AuthenticatedClient, require_role, get_current_client
from app.model.models import Client, CustomerAddress
from app.api.depedencias import require_role, get_current_client
from app.schemas.autenticacao_schemas import AuthenticatedUser
from app.schemas.endereco_schemas import EnderecoCreate, EnderecoOut, EnderecoUpdate


def _get_cliente_ou_404(cliente_id: uuid.UUID, db: Session) -> Client:
    cliente = db.get(Client, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return cliente


def _get_endereco_ou_404(cliente_id: uuid.UUID, endereco_id: uuid.UUID, db: Session) -> CustomerAddress:
    endereco = (
        db.query(CustomerAddress)
        .filter(CustomerAddress.id == endereco_id, CustomerAddress.client_id == cliente_id)
        .first()
    )
    if endereco is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endereço não encontrado para este cliente")
    return endereco


def _definir_padrao(cliente_id: uuid.UUID, endereco: CustomerAddress, db: Session) -> CustomerAddress:
    """Marca `endereco` como principal, tirando o padrão anterior — numa única transação."""
    if not endereco.primary_address:
        db.query(CustomerAddress).filter(
            CustomerAddress.client_id == cliente_id,
            CustomerAddress.id != endereco.id,
            CustomerAddress.primary_address.is_(True),
        ).update({"primary_address": False}, synchronize_session=False)
        endereco.primary_address = True
        db.commit()
        db.refresh(endereco)
    return endereco

# ---------------------------------------------------------------------------
# Rotas do cliente logado (self-service) — sem cliente_id na URL, escopado pelo token
# ---------------------------------------------------------------------------
me_router = APIRouter(prefix="/clientes/me/enderecos", tags=["Endereços (cliente)"])


@me_router.get("/", response_model=list[EnderecoOut])
def listar_meus_enderecos(
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    return db.query(CustomerAddress).filter(CustomerAddress.client_id == cliente.id).all()


@me_router.post("/", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_meu_endereco(
    endereco: EnderecoCreate,
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    novo_endereco = CustomerAddress(client_id=cliente.id, **endereco.model_dump())
    db.add(novo_endereco)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um endereço principal cadastrado")
    db.refresh(novo_endereco)
    return novo_endereco


@me_router.put("/{endereco_id}", response_model=EnderecoOut)
def atualizar_meu_endereco(
    endereco_id: uuid.UUID,
    dados: EnderecoUpdate,
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    endereco = _get_endereco_ou_404(cliente.id, endereco_id, db)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(endereco, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um endereço principal cadastrado",
        )

    db.refresh(endereco)
    return endereco


@me_router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_meu_endereco(
    endereco_id: uuid.UUID,
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    endereco = _get_endereco_ou_404(cliente.id, endereco_id, db)
    db.delete(endereco)
    db.commit()


@me_router.patch("/{endereco_id}/padrao", response_model=EnderecoOut)
def definir_meu_endereco_padrao(
    endereco_id: uuid.UUID,
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    endereco = _get_endereco_ou_404(cliente.id, endereco_id, db)
    return _definir_padrao(cliente.id, endereco, db)

# ---------------------------------------------------------------------------
# Rotas administrativas (staff) — cliente_id explícito na URL
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/clientes/{cliente_id}/enderecos", tags=["Endereços (staff)"])


@router.post("/", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco_staff(
    cliente_id: uuid.UUID,
    endereco: EnderecoCreate,
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    _get_cliente_ou_404(cliente_id, db)
    novo_endereco = CustomerAddress(client_id=cliente_id, **endereco.model_dump())
    db.add(novo_endereco)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um endereço principal cadastrado para este cliente")
    db.refresh(novo_endereco)
    return novo_endereco


@router.get("/", response_model=list[EnderecoOut])
def listar_enderecos_staff(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    _get_cliente_ou_404(cliente_id, db)
    return db.query(CustomerAddress).filter(CustomerAddress.client_id == cliente_id).all()


@router.put("/{endereco_id}", response_model=EnderecoOut)
def atualizar_endereco_staff(
    cliente_id: uuid.UUID,
    endereco_id: uuid.UUID,
    dados: EnderecoUpdate,
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
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
def deletar_endereco_staff(
    cliente_id: uuid.UUID,
    endereco_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: AuthenticatedUser = Depends(require_role("admin", "atendente", "caixa")),
):
    _get_cliente_ou_404(cliente_id, db)
    endereco = _get_endereco_ou_404(cliente_id, endereco_id, db)
    db.delete(endereco)
    db.commit()