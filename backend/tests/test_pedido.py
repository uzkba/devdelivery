import pytest
from datetime import date
from decimal import Decimal

from backend.app.model.models import Food, FoodCategory, Menu, MenuItem, Client
from backend.app.core.seguranca import hash_password


# ── fixtures/helpers locais, mesmo padrão de test_cardapio_do_dia.py ──

@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def criar_alimento_direto(db, categoria, **overrides):
    dados = dict(
        restaurant_id=categoria.restaurant_id,
        category_id=categoria.id,
        name="Feijoada",
        base_price=Decimal("10.00"),
        is_active=True,
        is_available=True,
    )
    dados.update(overrides)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


def criar_cardapio_hoje(db, restaurante):
    menu = Menu(restaurant_id=restaurante.id, date=date.today())
    db.add(menu)
    db.flush()
    db.refresh(menu)
    return menu


def criar_item_cardapio(db, menu, alimento, is_available=True, day_price=None):
    item = MenuItem(menu_id=menu.id, food_id=alimento.id, is_available=is_available, day_price=day_price)
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def payload_pedido(restaurante, endereco, alimento, **overrides):
    dados = dict(
        restaurante_id=str(restaurante.id),
        endereco_id=str(endereco.id),
        forma_pagamento="PIX",
        itens=[{"alimento_id": str(alimento.id), "quantidade": 2}],
    )
    dados.update(overrides)
    return dados


# ── criação de pedido ──────────────────────────────────────────────

def test_cliente_cria_pedido_com_sucesso(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("15.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["cliente_id"] == str(cliente.id)
    assert corpo["valor_itens"] == "30.00"  # 15.00 * 2
    assert corpo["valor_entrega"] == "0.00"
    assert corpo["valor_total"] == "30.00"
    assert len(corpo["itens"]) == 1


def test_pedido_usa_preco_do_dia_quando_setado(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("20.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento, day_price=Decimal("12.50"))

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, itens=[{"alimento_id": str(alimento.id), "quantidade": 1}]),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    assert resp.status_code == 201
    assert resp.json()["valor_itens"] == "12.50"


def test_pedido_rejeita_item_fora_do_cardapio_de_hoje(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    # sem criar_cardapio_hoje/criar_item_cardapio — item existe no catálogo mas não está no cardápio de hoje

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    assert resp.status_code == 422


def test_pedido_rejeita_item_indisponivel_hoje(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento, is_available=False)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    assert resp.status_code == 422


def test_pedido_rejeita_endereco_de_outro_cliente(db, client, restaurante, cliente, outro_cliente, categoria, token_para_cliente):
    # endereço pertence a outro_cliente, mas quem autentica é cliente — não pode usar
    from backend.app.model.models import CustomerAddress
    endereco_alheio = CustomerAddress(
        client_id=outro_cliente.id, street="Rua de Outro", number="1", neighborhood="Bairro"
    )
    db.add(endereco_alheio)
    db.flush()
    db.refresh(endereco_alheio)

    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco_alheio, alimento),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    assert resp.status_code == 404


def test_pedido_sem_token_retorna_401(client, restaurante, endereco, categoria, db):
    alimento = criar_alimento_direto(db, categoria)
    resp = client.post("/pedidos", json=payload_pedido(restaurante, endereco, alimento))
    assert resp.status_code == 401


def test_pedido_com_token_de_admin_retorna_401(db, client, restaurante, cliente, endereco, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria)
    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento),
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 401  # token não tem "type": "client"


# ── forma de pagamento / troco ──────────────────────────────────────

def test_dinheiro_sem_valor_pago_retorna_422(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, forma_pagamento="DINHEIRO"),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 422


def test_dinheiro_com_valor_menor_que_total_retorna_400(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("10.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(
            restaurante, endereco, alimento,
            forma_pagamento="DINHEIRO", valor_pago_dinheiro="5.00",
            itens=[{"alimento_id": str(alimento.id), "quantidade": 1}],
        ),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 400


def test_dinheiro_calcula_troco_corretamente(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("10.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(
            restaurante, endereco, alimento,
            forma_pagamento="DINHEIRO", valor_pago_dinheiro="20.00",
            itens=[{"alimento_id": str(alimento.id), "quantidade": 1}],
        ),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 201
    assert resp.json()["valor_troco"] == "10.00"


def test_pix_com_valor_pago_retorna_422(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, forma_pagamento="PIX", valor_pago_dinheiro="10.00"),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 422


# ── cadastro e login de cliente ─────────────────────────────────────

def test_registrar_cliente_sucesso(client):
    resp = client.post("/clientes/registrar", json={
        "name": "Novo Cliente", "phone": "11955554444", "password": "senha1234",
    })
    assert resp.status_code == 201
    assert resp.json()["phone"] == "11955554444"


def test_registrar_cliente_telefone_duplicado_retorna_409(client, cliente):
    resp = client.post("/clientes/registrar", json={
        "name": "Outro Nome", "phone": cliente.phone, "password": "senha1234",
    })
    assert resp.status_code == 409


def test_login_cliente_sucesso(db, client):
    cli = Client(name="Login Teste", phone="11977776666", hashed_password=hash_password("senha1234"))
    db.add(cli)
    db.flush()
    db.refresh(cli)

    resp = client.post("/clientes/login", json={"phone": cli.phone, "password": "senha1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_cliente_senha_errada_retorna_401(db, client):
    cli = Client(name="Login Teste 2", phone="11966665555", hashed_password=hash_password("senha1234"))
    db.add(cli)
    db.flush()
    db.refresh(cli)

    resp = client.post("/clientes/login", json={"phone": cli.phone, "password": "senha_errada"})
    assert resp.status_code == 401