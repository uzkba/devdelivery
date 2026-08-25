import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from backend.app.core.seguranca import hash_password
from backend.app.model.models import Client, CustomerAddress


def test_criar_cliente(db):
    novo_cliente = Client(
        id=uuid.uuid4(),
        name="Gabriel Teste",
        phone="11999999999",
        hashed_password=hash_password("senha123"),
    )
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)

    assert novo_cliente.id is not None
    assert novo_cliente.name == "Gabriel Teste"


def test_endereco_principal_unico_por_cliente(db):
    cliente_id = uuid.uuid4()

    cliente = Client(
        id=cliente_id,
        name="Cliente Teste",
        phone="11888888888",
        hashed_password=hash_password("senha123"),
    )
    db.add(cliente)
    db.commit()

    end1 = CustomerAddress(
        id=uuid.uuid4(),
        client_id=cliente_id,
        street="Rua A",
        number="123",
        neighborhood="Centro",
        primary_address=True
    )
    db.add(end1)
    db.commit()

    end2 = CustomerAddress(
        id=uuid.uuid4(),
        client_id=cliente_id,
        street="Rua B",
        number="456",
        neighborhood="Centro",
        primary_address=True
    )
    db.add(end2)

    with pytest.raises(IntegrityError):
        db.commit()