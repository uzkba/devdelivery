import pytest
from datetime import date
from decimal import Decimal

from backend.app.model.models import (
    Food,
    FoodCategory,
    Menu,
    MenuItem,
    Client,
    DeliveryRule,
    ModifierGroup,
    ModifierOption,
    CustomerAddress
)
from backend.app.core.seguranca import hash_password


# ── fixtures/helpers locais ──

@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def regra_frete_basica(db, restaurante):
    """Regra de frete genérica de 0 a 10km para os testes básicos passarem na validação geográfica"""
    regra = DeliveryRule(
        restaurant_id=restaurante.id,
        min_distance_km=Decimal("0.0"),
        max_distance_km=Decimal("10.0"),
        fee=Decimal("0.00"),
        is_active=True
    )
    db.add(regra)
    db.flush()
    return regra


def criar_alimento_direto(db, categoria, **overrides):
    dados = dict(
        restaurant_id=categoria.restaurant_id,
        category_id=categoria.id,
        name="Feijoada",
        base_price=Decimal("10.00"),
        is_active=True,
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
        itens=[{"alimento_id": str(alimento.id), "quantidade": 2, "opcoes_selecionadas": []}],
    )
    dados.update(overrides)
    return dados


# ── criação de pedido ──────────────────────────────────────────────

def test_cliente_cria_pedido_com_sucesso(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("15.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    if resp.status_code != 201:
        print(f"\n[ERRO PAYLOAD] A API disse: {resp.json()}\n")

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["cliente_id"] == str(cliente.id)
    assert corpo["valor_itens"] == "30.00"  # 15.00 * 2
    assert corpo["valor_entrega"] == "0.00"
    assert corpo["valor_total"] == "30.00"
    assert len(corpo["itens"]) == 1


def test_pedido_usa_preco_do_dia_quando_setado(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("20.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento, day_price=Decimal("12.50"))

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, itens=[{"alimento_id": str(alimento.id), "quantidade": 1, "opcoes_selecionadas": []}]),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    if resp.status_code != 201:
        print(f"\n[ERRO PAYLOAD] A API disse: {resp.json()}\n")

    assert resp.status_code == 201
    assert resp.json()["valor_itens"] == "12.50"


def test_pedido_rejeita_item_fora_do_cardapio_de_hoje(db, client, restaurante, cliente, endereco, categoria, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)

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
    endereco_alheio = CustomerAddress(
        client_id=outro_cliente.id, street="Rua de Outro", number="1", neighborhood="Bairro",
        latitude=Decimal("-23.555000"), longitude=Decimal("-46.635000")
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
    assert resp.status_code == 401


# ── forma de pagamento / troco ──────────────────────────────────────

def test_dinheiro_sem_valor_pago_retorna_422(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, forma_pagamento="DINHEIRO"),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 422


def test_dinheiro_com_valor_menor_que_total_retorna_400(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("10.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(
            restaurante, endereco, alimento,
            forma_pagamento="DINHEIRO", valor_pago_dinheiro=5.00,
            itens=[{"alimento_id": str(alimento.id), "quantidade": 1, "opcoes_selecionadas": []}],
        ),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resp.status_code == 400


def test_dinheiro_calcula_troco_corretamente(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("10.00"))
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(
            restaurante, endereco, alimento,
            forma_pagamento="DINHEIRO", valor_pago_dinheiro=20.00,
            itens=[{"alimento_id": str(alimento.id), "quantidade": 1, "opcoes_selecionadas": []}],
        ),
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )

    if resp.status_code != 201:
        print(f"\n[ERRO PAYLOAD] A API disse: {resp.json()}\n")

    assert resp.status_code == 201
    assert resp.json()["valor_troco"] == "10.00"


def test_pix_com_valor_pago_retorna_422(db, client, restaurante, cliente, endereco, categoria, regra_frete_basica, token_para_cliente):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio_hoje(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    resp = client.post(
        "/pedidos",
        json=payload_pedido(restaurante, endereco, alimento, forma_pagamento="PIX", valor_pago_dinheiro=10.00),
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

    resp = client.post("/clientes/login/cliente", json={"phone": cli.phone, "password": "senha1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_cliente_senha_errada_retorna_401(db, client):
    cli = Client(name="Login Teste 2", phone="11966665555", hashed_password=hash_password("senha1234"))
    db.add(cli)
    db.flush()
    db.refresh(cli)

    resp = client.post("/clientes/login/cliente", json={"phone": cli.phone, "password": "senha_errada"})
    assert resp.status_code == 401


# ── checkout detalhado ──────────────────────────────────────────────

@pytest.fixture
def cenario_checkout(db, restaurante, categoria, endereco, status_criado, forma_pagamento_dinheiro):
    """
    Prepara o ecossistema necessário para um pedido:
    Coordenadas, Regra de Entrega, Cardápio de Hoje e Complementos.
    """
    restaurante.latitude = Decimal("-23.550520")
    restaurante.longitude = Decimal("-46.633308")

    endereco.latitude = Decimal("-23.555000")
    endereco.longitude = Decimal("-46.635000")

    regra_frete = DeliveryRule(
        restaurant_id=restaurante.id,
        min_distance_km=Decimal("0.0"),
        max_distance_km=Decimal("5.0"),
        fee=Decimal("7.50"),
        is_active=True
    )
    db.add(regra_frete)

    hamburguer = Food(
        restaurant_id=restaurante.id,
        category_id=categoria.id,
        name="Hamburguer Artesanal",
        base_price=Decimal("25.00"),
        is_active=True
    )
    db.add(hamburguer)
    db.flush()

    # 3.5 Criar o GRUPO vinculado ao Alimento
    grupo_adicionais = ModifierGroup(
        name="Adicionais",
        food_id=hamburguer.id,
        min_choices=0,
        max_choices=3,
    )
    db.add(grupo_adicionais)
    db.flush()

    # 4. Criar Opção/Complemento
    bacon = ModifierOption(
        group_id=grupo_adicionais.id,
        name="Adicional de Bacon",
        extra_price=Decimal("5.00")
    )
    db.add(bacon)
    db.flush()

    cardapio_hoje = Menu(
        restaurant_id=restaurante.id,
        date=date.today(),
    )
    db.add(cardapio_hoje)
    db.flush()

    item_hoje = MenuItem(
        menu_id=cardapio_hoje.id,
        food_id=hamburguer.id,
        day_price=Decimal("22.00"),
        is_available=True
    )
    db.add(item_hoje)
    db.commit()

    return {
        "alimento": hamburguer,
        "opcao": bacon,
        "regra_frete": regra_frete
    }


def test_criar_pedido_com_sucesso(client, db, cenario_checkout, restaurante, cliente, endereco, token_para_cliente):
    token = token_para_cliente(cliente)
    headers = {"Authorization": f"Bearer {token}"}

    alimento = cenario_checkout["alimento"]
    opcao = cenario_checkout["opcao"]

    payload = {
        "restaurante_id": str(restaurante.id),
        "endereco_id": str(endereco.id),
        "forma_pagamento": "DINHEIRO",
        "valor_pago_dinheiro": 70.00,
        "itens": [
            {
                "alimento_id": str(alimento.id),
                "quantidade": 2,
                "opcoes_selecionadas": [
                    {
                        "opcao_complemento_id": str(opcao.id),
                        "quantidade": 2
                    }
                ]
            }
        ]
    }

    response = client.post("/pedidos", json=payload, headers=headers)

    if response.status_code != 201:
        print(f"\n[ERRO PAYLOAD] A API disse: {response.json()}\n")

    assert response.status_code == 201
    dados = response.json()

    assert dados["status_id"] is not None
    assert dados["cliente_id"] == str(cliente.id)
    assert dados["valor_itens"] == "54.00"
    assert dados["valor_entrega"] == "7.50"
    assert dados["valor_total"] == "61.50"
    assert dados["valor_troco"] == "8.50"


def test_deve_rejeitar_pedido_fora_da_area_de_entrega(client, db, cenario_checkout, restaurante, cliente, endereco, token_para_cliente):
    token = token_para_cliente(cliente)
    headers = {"Authorization": f"Bearer {token}"}
    alimento = cenario_checkout["alimento"]

    endereco.latitude = Decimal("-24.000000")
    endereco.longitude = Decimal("-47.000000")
    db.commit()

    payload = {
        "restaurante_id": str(restaurante.id),
        "endereco_id": str(endereco.id),
        "forma_pagamento": "PIX",
        "itens": [
            {
                "alimento_id": str(alimento.id),
                "quantidade": 1,
                "opcoes_selecionadas": []
            }
        ]
    }

    response = client.post("/pedidos", json=payload, headers=headers)

    assert response.status_code == 422
    assert "fora da área de entrega" in response.json()["detail"]


def test_deve_rejeitar_item_nao_disponivel_no_cardapio_do_dia(client, db, categoria, cenario_checkout, restaurante, cliente, endereco, token_para_cliente):
    token = token_para_cliente(cliente)
    headers = {"Authorization": f"Bearer {token}"}

    pizza = Food(
        restaurant_id=restaurante.id,
        category_id=categoria.id,
        name="Pizza",
        base_price=Decimal("50.00"),
        is_active=True
    )
    db.add(pizza)
    db.commit()

    payload = {
        "restaurante_id": str(restaurante.id),
        "endereco_id": str(endereco.id),
        "forma_pagamento": "PIX",
        "itens": [
            {
                "alimento_id": str(pizza.id),
                "quantidade": 1,
                "opcoes_selecionadas": []
            }
        ]
    }

    response = client.post("/pedidos", json=payload, headers=headers)

    assert response.status_code == 422
    assert "Itens indisponíveis no cardápio de hoje" in response.json()["detail"]