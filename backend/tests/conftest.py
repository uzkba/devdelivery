import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.model.models import Base, AdminUser, Restaurant
import os
from dotenv import load_dotenv

from fastapi.testclient import TestClient

from backend.app.core.database import get_db
from backend.app.core.seguranca import hash_password
from backend.main import app

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    """
    TestClient do FastAPI, injetando a MESMA sessão (db) usada pelo teste
    no lugar do get_db real -- assim tudo que a rota grava fica dentro da
    mesma transação, e é desfeito automaticamente no rollback da fixture `db`.
    """
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
    db.flush()  # gera o id sem precisar de commit (fica dentro da transação de teste)
    db.refresh(r)
    return r


@pytest.fixture()
def admin_user(db, restaurante):
    """Usuário admin ativo, senha = 'senha123'."""
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
    """Usuário admin desativado, senha = 'senha123'."""
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