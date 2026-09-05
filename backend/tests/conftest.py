import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import find_dotenv, load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Carrega variáveis de ambiente
load_dotenv(find_dotenv())

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DATABASE_URL = os.getenv("DATABASE_URL")

# Importações da aplicação
from backend.main import app
from backend.app.core.database import get_db
from backend.app.core.seguranca import hash_password
from backend.app.routers.autenticacao_route import create_access_token
from backend.app.model.models import (
    Base,
    AdminUser,
    Order,
    OrderStatus,
    PaymentMethod,
    Restaurant,
    AuditLog,
    Client,
    CustomerAddress,
)

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _aplicar_migrations():
    project_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _reiniciar_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def token_para_cliente(db):
    def _token_para_cliente(cliente) -> str:
        return create_access_token(data={"sub": str(cliente.id), "type": "client"})
    return _token_para_cliente


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
def restaurante(db):
    r = Restaurant(trade_name="Marmitas da Vovó", latitude=-23.5505, longitude=-46.6333)
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
        latitude=Decimal("-23.555000"),
        longitude=Decimal("-46.635000")
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
        latitude=Decimal("-23.560000"),
        longitude=Decimal("-46.640000")
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
def outro_restaurante(db):
    r = Restaurant(trade_name="Marmitas do Zé (Restaurante B)", latitude=-23.5505, longitude=-46.6333)
    db.add(r)
    db.flush()
    db.refresh(r)
    return r


@pytest.fixture()
def outro_admin_user(db, outro_restaurante):
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


def _get_or_create_payment_method(db, code, name):
    fp = db.query(PaymentMethod).filter_by(code=code).first()
    if fp is None:
        fp = PaymentMethod(code=code, name=name, is_active=True)
        db.add(fp)
        db.flush()
        db.refresh(fp)
    return fp


@pytest.fixture()
def forma_pagamento_dinheiro(db):
    return _get_or_create_payment_method(db, "DINHEIRO", "Dinheiro")


@pytest.fixture()
def forma_pagamento_pix(db):
    return _get_or_create_payment_method(db, "PIX", "Pix")


@pytest.fixture()
def forma_pagamento_debito(db):
    return _get_or_create_payment_method(db, "CARTAO_DEBITO", "Cartão de Débito")


@pytest.fixture()
def forma_pagamento_credito(db):
    return _get_or_create_payment_method(db, "CARTAO_CREDITO", "Cartão de Crédito")


@pytest.fixture()
def pedido_teste(db, restaurante, cliente, endereco, forma_pagamento_dinheiro, status_criado):
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


@pytest.fixture()
def log_do_outro_restaurante(db, outro_restaurante):
    log = AuditLog(
        restaurant_id=outro_restaurante.id,
        user_id=None,
        entity="alimento",
        entity_id=str(uuid.uuid4()),
        action="CRIACAO",
        previous_data=None,
        new_data={"nome": "Prato de outro restaurante"},
    )
    db.add(log)
    db.flush()
    db.refresh(log)
    return log


@pytest.fixture()
def algum_log_de_pedido(db, restaurante):
    log = AuditLog(
        restaurant_id=restaurante.id,
        user_id=None,
        entity="pedido",
        entity_id=str(uuid.uuid4()),
        action="CRIACAO",
        previous_data=None,
        new_data={"total_amount": "25.90"},
    )
    db.add(log)
    db.flush()
    db.refresh(log)
    return log


@pytest.fixture()
def algum_log_de_alimento(db, restaurante, admin_user):
    log = AuditLog(
        restaurant_id=restaurante.id,
        user_id=admin_user.id,
        entity="alimento",
        entity_id=str(uuid.uuid4()),
        action="CRIACAO",
        previous_data=None,
        new_data={"nome": "Feijoada"},
    )
    db.add(log)
    db.flush()
    db.refresh(log)
    return log


@pytest.fixture()
def status_entregue(db):
    return _get_or_create_status(db, "ENTREGUE", "Entregue", 5, True)


@pytest.fixture()
def status_cancelado(db):
    return _get_or_create_status(db, "CANCELADO", "Cancelado", 6, True)


@pytest.fixture()
def status_confirmado(db):
    return _get_or_create_status(db, "CONFIRMADO", "Confirmado", 2, False)


@pytest.fixture()
def criar_pedido_direto(db, restaurante, cliente, endereco):
    def _criar(status, forma_pagamento, total_amount, order_datetime, **overrides):
        dados = dict(
            restaurant_id=restaurante.id,
            client_id=cliente.id,
            status_id=status.id,
            payment_method_id=forma_pagamento.id,
            address_name=cliente.name,
            address_phone=cliente.phone,
            address_street=endereco.street,
            address_number=endereco.number,
            address_neighborhood=endereco.neighborhood,
            items_amount=total_amount,
            delivery_fee=Decimal("0"),
            total_amount=total_amount,
            order_datetime=order_datetime,
        )
        dados.update(overrides)
        pedido = Order(**dados)
        db.add(pedido)
        db.flush()
        db.refresh(pedido)
        return pedido
    return _criar