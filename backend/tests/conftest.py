from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.model.models import Base, AdminUser, Restaurant
import os
from dotenv import load_dotenv

from fastapi.testclient import TestClient

from backend.app.core.database import get_db
from backend.app.core.seguranca import hash_password
from backend.main import app
from backend.app.model.models import Client, CustomerAddress

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _aplicar_migrations():
    """Roda `alembic upgrade head` uma vez, no início da sessão de testes,
    antes de qualquer fixture que use o banco. Evita depender de cada
    dev lembrar de rodar isso manualmente (foi exatamente o que causou
    os erros de "coluna não existe" na task de categoria de alimento)."""
    project_root = Path(__file__).resolve().parents[2]  # conftest.py -> tests/ -> backend/ -> raiz
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
    c = Client(name="José da Silva", phone="11999990000")
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def outro_cliente(db):
    c = Client(name="Ana Souza", phone="11988880000")
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