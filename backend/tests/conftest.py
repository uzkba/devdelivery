import os
import pytest

from datetime import datetime
from pathlib import Path
from decimal import Decimal

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Carrega variáveis de ambiente
load_dotenv(BACKEND_ROOT / ".env.test")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DATABASE_URL = os.getenv("DATABASE_URL")

# Importações da aplicação
from main import app
from app.core.database import get_db
from app.core.seguranca import hash_password
from app.routers.autenticacao_route import create_access_token
from app.model.models import (
    AdminUser,
    Order,
    OrderStatus,
    PaymentMethod,
    Restaurant,
    Client,
    CustomerAddress,
    Food,
    FoodCategory,
    MealBox,
    MealBoxKind,
    Combo,
    PaymentMethod,
    RestaurantPaymentMethod,
)

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

FORMAS_PAGAMENTO_PADRAO = [
    ("DINHEIRO", "Dinheiro"),
    ("PIX", "Pix"),
    ("CARTAO_CREDITO", "Cartão de Crédito"),
    ("CARTAO_DEBITO", "Cartão de Débito"),
]


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
    r = Restaurant(
        trade_name="Marmitas da Vovó",
        slug="marmitas-da-vovo",
    )
    db.add(r)
    db.flush()
    for codigo, nome in FORMAS_PAGAMENTO_PADRAO:
        forma = _get_or_create_payment_method(db, codigo, nome)
        db.add(RestaurantPaymentMethod(restaurant_id=r.id, payment_method_id=forma.id))
    db.flush()
    db.refresh(r)
    return r


@pytest.fixture()
def aceitar_formas(db):
    
    def _aceitar(restaurante, *codigos):
        desejadas = {
            db.query(PaymentMethod).filter_by(code=codigo).one().id for codigo in codigos
        }
        atuais = {
            vinculo.payment_method_id: vinculo
            for vinculo in db.query(RestaurantPaymentMethod)
            .filter(RestaurantPaymentMethod.restaurant_id == restaurante.id)
            .all()
        }
        for forma_id, vinculo in atuais.items():
            if forma_id not in desejadas:
                db.delete(vinculo)
        for forma_id in desejadas - atuais.keys():
            db.add(
                RestaurantPaymentMethod(
                    restaurant_id=restaurante.id, payment_method_id=forma_id
                )
            )
        db.flush()

    return _aceitar


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
def outro_restaurante(db):
    r = Restaurant(
        trade_name="Marmitas do Zé (Restaurante B)",
        slug="marmitas-do-ze",
    )
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


@pytest.fixture()
def novo_pedido(db, criar_pedido_direto, forma_pagamento_dinheiro):
    def _novo(codigo="CRIADO", **extra):
        status = db.query(OrderStatus).filter_by(code=codigo).one()
        return criar_pedido_direto(
            status,
            forma_pagamento_dinheiro,
            Decimal("25.00"),
            datetime(2026, 11, 10, 12, 0),
            **extra,
        )

    return _novo


@pytest.fixture()
def admin_headers(admin_user, token_para):
    return {"Authorization": f"Bearer {token_para(admin_user)}"}
    
    
@pytest.fixture()
def outro_admin_headers(outro_admin_user, token_para):
    return {"Authorization": f"Bearer {token_para(outro_admin_user)}"}
    
    
# ---------------------------------------------------------------------------
# Categorias
# ---------------------------------------------------------------------------
def _nova_categoria(db, restaurante, nome, tipo="composicao", **extra):
    c = FoodCategory(restaurant_id=restaurante.id, name=nome, display_order=0, type=tipo, **extra)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c
    
    
@pytest.fixture()
def cat_composicao(db, restaurante):
    return _nova_categoria(db, restaurante, "Carnes")
    
    
@pytest.fixture()
def cat_composicao_2(db, restaurante):
    return _nova_categoria(db, restaurante, "Acompanhamentos")
    
    
@pytest.fixture()
def cat_composicao_inativa(db, restaurante):
    return _nova_categoria(db, restaurante, "Categoria Inativa", is_active=False)
    
    
@pytest.fixture()
def cat_venda(db, restaurante):
    return _nova_categoria(db, restaurante, "Pratos do dia", tipo="venda")
    
    
@pytest.fixture()
def cat_composicao_b(db, outro_restaurante):
    return _nova_categoria(db, outro_restaurante, "Carnes do B")
    
    
# ---------------------------------------------------------------------------
# Alimentos
# ---------------------------------------------------------------------------
def _novo_alimento(db, restaurante, nome, categoria=None, **extra):
    dados = dict(
        restaurant_id=restaurante.id,
        name=nome,
        is_active=True,
    )
    if categoria is not None:
        dados.update(composition_category_id=categoria.id)
    dados.update(extra)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f
    
    
@pytest.fixture()
def alimento_arroz(db, restaurante, cat_composicao):
    return _novo_alimento(db, restaurante, "Arroz", cat_composicao)
    
    
@pytest.fixture()
def alimento_feijao(db, restaurante, cat_composicao_2):
    return _novo_alimento(db, restaurante, "Feijão", cat_composicao_2)
    
    
@pytest.fixture()
def alimento_inativo(db, restaurante, cat_composicao):
    return _novo_alimento(db, restaurante, "Alimento Inativo", cat_composicao, is_active=False)
    
    
@pytest.fixture()
def alimento_so_venda(db, restaurante, cat_venda):
    """Avulso puro: so categoria de venda, sem categoria de composicao."""
    return _novo_alimento(
        db,
        restaurante,
        "Feijoada",
        categoria=None,
        sale_category_id=cat_venda.id,
        is_sellable_alone=True,
        standalone_price=Decimal("32.90"),
    )
    
    
@pytest.fixture()
def alimento_b(db, outro_restaurante, cat_composicao_b):
    return _novo_alimento(db, outro_restaurante, "Alimento do B", cat_composicao_b)
    
    
# ---------------------------------------------------------------------------
# Marmitas criadas direto no banco (usadas como insumo dos testes de combo)
# ---------------------------------------------------------------------------
def _nova_marmita(db, restaurante, nome, tipo, **extra):
    m = MealBox(restaurant_id=restaurante.id, name=nome, kind=tipo, price=Decimal("20.00"), **extra)
    db.add(m)
    db.flush()
    db.refresh(m)
    return m
    
    
@pytest.fixture()
def marmita_pronta(db, restaurante):
    return _nova_marmita(db, restaurante, "Marmita Pronta", MealBoxKind.READY)
    
    
@pytest.fixture()
def marmita_personalizavel(db, restaurante):
    return _nova_marmita(db, restaurante, "Marmita Personalizável", MealBoxKind.CUSTOMIZABLE)
    
    
@pytest.fixture()
def marmita_inativa(db, restaurante):
    return _nova_marmita(db, restaurante, "Marmita Inativa", MealBoxKind.READY, is_active=False)
    
    
@pytest.fixture()
def marmita_b(db, outro_restaurante):
    return _nova_marmita(db, outro_restaurante, "Marmita do B", MealBoxKind.READY)


@pytest.fixture()
def combo_teste(db, restaurante):
    combo = Combo(restaurant_id=restaurante.id, name="Combo Teste", price=Decimal("30.00"))
    db.add(combo)
    db.flush()
    db.refresh(combo)
    return combo


@pytest.fixture()
def cat_venda_bebida(db, restaurante):
    return _nova_categoria(db, restaurante, "Bebidas", tipo="venda", group="bebida")


@pytest.fixture()
def alimento_bebida(db, restaurante, cat_venda_bebida):
    return _novo_alimento(
        db,
        restaurante,
        "Suco de laranja",
        categoria=None,
        sale_category_id=cat_venda_bebida.id,
        is_sellable_alone=True,
        standalone_price=Decimal("8.00"),
    )