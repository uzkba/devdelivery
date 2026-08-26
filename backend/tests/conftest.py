from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.model.models import Base, AdminUser, Order, OrderStatus, PaymentMethod, Restaurant
import os
from dotenv import load_dotenv

from fastapi.testclient import TestClient

from backend.app.core.database import get_db
from backend.app.core.seguranca import hash_password, create_access_token as create_access_token_cliente
from backend.main import app
from backend.app.model.models import Client, CustomerAddress
from backend.app.routers.autenticacao_route import create_access_token

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def token_para_cliente(db):
    def _token_para_cliente(cliente) -> str:
        return create_access_token(data={"sub": str(cliente.id), "type": "client"})
    return _token_para_cliente

@pytest.fixture(scope="session", autouse=True)
def _aplicar_migrations():
    project_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db():
    """Cria uma conexão e uma transação isolada para cada teste."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def restaurante(db):
    r = Restaurant(trade_name="Marmitas da Vovó")
    db.add(r)
    db.flush()
    db.refresh(r)
    return r


@pytest.fixture()
def admin_user(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Maria Admin",
        login="maria.admin",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture()
def inactive_admin_user(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="João Inativo",
        login="joao.inativo",
        password_hash=hash_password("senha123"),
        role="atendente",
        is_active=False,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user

@pytest.fixture()
def inactive_admin_with_admin_role(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Carlos Desativado",
        login="carlos.desativado",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=False,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user

@pytest.fixture()
def cliente(db):
    c = Client(
        name="José da Silva",
        phone="11999990000",
        hashed_password=hash_password("senha123"),
    )
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def outro_cliente(db):
    c = Client(
        name="Ana Souza",
        phone="11988880000",
        hashed_password=hash_password("senha123"),
    )
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def endereco(db, cliente):
    e = CustomerAddress(
        client_id=cliente.id,
        street="Rua das Flores",
        number="123",
        neighborhood="Centro",
        primary_address=True,
    )
    db.add(e)
    db.flush()
    db.refresh(e)
    return e


@pytest.fixture()
def endereco_secundario(db, cliente):
    e = CustomerAddress(
        client_id=cliente.id,
        street="Rua Secundária",
        number="456",
        neighborhood="Bairro Novo",
        primary_address=False,
    )
    db.add(e)
    db.flush()
    db.refresh(e)
    return e


@pytest.fixture()
def atendente_user(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Ana Atendente",
        login="ana.atendente",
        password_hash=hash_password("senha123"),
        role="atendente",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture()
def caixa_user(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Carlos Caixa",
        login="carlos.caixa",
        password_hash=hash_password("senha123"),
        role="caixa",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture()
def entregador_user(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Pedro Entregador",
        login="pedro.entregador",
        password_hash=hash_password("senha123"),
        role="entregador",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user

@pytest.fixture()
def token_para(db):
    def _token_para(user) -> str:
        return create_access_token(
            data={
                "sub": str(user.id),
                "login": user.login,
                "name": user.name,
                "role": user.role,
                "restaurant_id": str(user.restaurant_id),
            }
        )
    return _token_para

@pytest.fixture()
def outro_restaurante(db):
    """Fixture global de um segundo restaurante para testes multi-tenant."""
    r = Restaurant(trade_name="Marmitas do Zé (Restaurante B)")
    db.add(r)
    db.flush()
    db.refresh(r)
    return r

@pytest.fixture()
def outro_admin_user(db, outro_restaurante):
    """Fixture global de um admin pertencente ao segundo restaurante."""
    user = AdminUser(
        restaurant_id=outro_restaurante.id,
        name="Zé Admin",
        login="ze.admin.cardapio",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user

@pytest.fixture()
def status_criado(db):
    """Garante que existe o status inicial do pedido."""
    status = OrderStatus(code="CRIADO", name="Criado", order=1, is_final=False)
    db.add(status)
    db.flush()
    db.refresh(status)
    return status


@pytest.fixture()
def forma_pagamento_dinheiro(db):
    fp = db.query(PaymentMethod).filter_by(code="DINHEIRO").first()
    if fp is None:
        fp = PaymentMethod(code="DINHEIRO", name="Dinheiro", is_active=True)
        db.add(fp)
        db.flush()
        db.refresh(fp)
    return fp

@pytest.fixture()
def pedido_teste(db, restaurante, cliente, endereco, forma_pagamento_dinheiro, status_criado):
    """Pedido básico no status inicial, pronto pra testar transições de status."""

    pedido = Order(
        restaurant_id=restaurante.id,
        client_id=cliente.id,
        status_id=status_criado.id,
        payment_method_id=forma_pagamento_dinheiro.id,
        address_name=cliente.name,
        address_phone=cliente.phone,
        address_street=endereco.street,
        address_number=endereco.number,
        address_neighborhood=endereco.neighborhood,
        items_amount=20,
        delivery_fee=5,
        total_amount=25,
    )
    db.add(pedido)
    db.flush()
    db.refresh(pedido)
    return pedido

def _get_or_create_status(db, code, name, order, is_final):
    status = db.query(OrderStatus).filter_by(code=code).first()
    if status is None:
        status = OrderStatus(code=code, name=name, order=order, is_final=is_final)
        db.add(status)
        db.flush()
        db.refresh(status)
    return status


@pytest.fixture()
def status_criado(db):
    return _get_or_create_status(db, "CRIADO", "Criado", 1, False)