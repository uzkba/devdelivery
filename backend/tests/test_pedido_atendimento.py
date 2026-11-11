from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.model.models import (
    DeliveryChargeMode,
    Food,
    FoodCategory,
    Menu,
    MenuItem,
    Order,
    OrderServiceType,
    RestaurantDeliverySettings,
    PaymentMethod,
)


# ── fixtures e helpers locais ──
@pytest.fixture()
def alimento_do_dia(db, restaurante):
    categoria = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(categoria)
    db.flush()
    alimento = Food(
        restaurant_id=restaurante.id,
        category_id=categoria.id,
        name="Feijoada",
        base_price=Decimal("20.00"),
        is_active=True,
    )
    db.add(alimento)
    db.flush()
    menu = Menu(restaurant_id=restaurante.id, date=date.today())
    db.add(menu)
    db.flush()
    db.add(MenuItem(menu_id=menu.id, food_id=alimento.id, is_available=True))
    db.flush()
    return alimento


def _config(db, restaurante, **extra):
    dados = dict(
        restaurant_id=restaurante.id,
        charge_mode=DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("7.50"),
    )
    dados.update(extra)
    config = RestaurantDeliverySettings(**dados)
    db.add(config)
    db.flush()
    return config


def _payload(restaurante, alimento, **extra):
    corpo = {
        "restaurante_id": str(restaurante.id),
        "forma_pagamento": "PIX",
        "itens": [{"alimento_id": str(alimento.id), "quantidade": 1}],
    }
    corpo.update(extra)
    return corpo


def _headers(cliente, token_para_cliente):
    return {"Authorization": f"Bearer {token_para_cliente(cliente)}"}


def _pedido_direto(db, restaurante, cliente, status_criado, forma_pagamento_pix, **extra):
    dados = dict(
        restaurant_id=restaurante.id,
        client_id=cliente.id,
        status_id=status_criado.id,
        payment_method_id=forma_pagamento_pix.id,
        address_name=cliente.name,
        address_phone=cliente.phone,
        items_amount=Decimal("20.00"),
        delivery_fee=Decimal("0.00"),
        total_amount=Decimal("20.00"),
    )
    dados.update(extra)
    pedido = Order(**dados)
    db.add(pedido)
    db.flush()
    return pedido


# ── retirada ──
def test_retirada_cria_pedido_sem_endereco_e_sem_taxa(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["tipo_atendimento"] == "RETIRADA"
    assert corpo["endereco_rua"] is None
    assert corpo["endereco_numero"] is None
    assert corpo["endereco_bairro"] is None
    assert corpo["valor_itens"] == "20.00"
    assert corpo["valor_entrega"] == "0.00"
    assert corpo["valor_total"] == "20.00"

    pedido = db.query(Order).filter_by(id=corpo["id"]).one()
    assert pedido.service_type == OrderServiceType.PICKUP
    assert pedido.address_street is None
    assert pedido.address_name == cliente.name
    assert pedido.address_phone == cliente.phone


def test_retirada_ignora_endereco_enviado(
    db, client, restaurante, cliente, endereco, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)

    resp = client.post(
        "/pedidos",
        json=_payload(
            restaurante,
            alimento_do_dia,
            tipo_atendimento="RETIRADA",
            endereco_id=str(endereco.id),
        ),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 201
    assert resp.json()["endereco_rua"] is None
    assert resp.json()["valor_entrega"] == "0.00"


def test_retirada_nao_exige_bairro_cadastrado_no_modo_bairro(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante, charge_mode=DeliveryChargeMode.BAIRRO, fixed_fee=None)

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 201
    assert resp.json()["valor_entrega"] == "0.00"


def test_retirada_desativada_e_rejeitada(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante, pickup_enabled=False)

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422
    assert "retiradas" in resp.json()["detail"]


def test_retirada_respeita_o_valor_minimo(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante, min_order_value=Decimal("50.00"))

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422
    assert "mínimo" in resp.json()["detail"]


def test_retirada_respeita_a_pausa_do_restaurante(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)
    restaurante.is_paused = True
    db.flush()

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422


# ── entrega ──
def test_tipo_padrao_e_entrega(
    db, client, restaurante, cliente, endereco, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, endereco_id=str(endereco.id)),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["tipo_atendimento"] == "ENTREGA"
    assert corpo["endereco_rua"] == endereco.street
    assert corpo["valor_entrega"] == "7.50"
    assert corpo["valor_total"] == "27.50"


def test_entrega_exige_endereco(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="ENTREGA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422


def test_entrega_desativada_nao_impede_retirada(
    db, client, restaurante, cliente, endereco, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante, delivery_enabled=False)
    headers = _headers(cliente, token_para_cliente)

    entrega = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, endereco_id=str(endereco.id)),
        headers=headers,
    )
    retirada = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=headers,
    )

    assert entrega.status_code == 422
    assert retirada.status_code == 201


def test_tipo_de_atendimento_invalido_e_rejeitado(
    db, client, restaurante, cliente, endereco, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)

    resp = client.post(
        "/pedidos",
        json=_payload(
            restaurante, alimento_do_dia, tipo_atendimento="DRIVE_THRU", endereco_id=str(endereco.id)
        ),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422


# ── leitura ──
def test_listagem_e_detalhe_mostram_o_tipo_de_atendimento(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente, admin_headers
):
    _config(db, restaurante)
    criado = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )
    assert criado.status_code == 201
    pedido_id = criado.json()["id"]

    detalhe = client.get(f"/pedidos/{pedido_id}", headers=admin_headers)
    lista = client.get("/pedidos", headers=admin_headers)
    minha_lista = client.get("/pedidos/me", headers=_headers(cliente, token_para_cliente))

    assert detalhe.status_code == 200
    assert detalhe.json()["tipo_atendimento"] == "RETIRADA"
    assert detalhe.json()["endereco_rua"] is None
    assert lista.json()["items"][0]["tipo_atendimento"] == "RETIRADA"
    assert minha_lista.json()["items"][0]["tipo_atendimento"] == "RETIRADA"


# ── banco ──
def test_banco_exige_endereco_na_entrega(
    db, restaurante, cliente, status_criado, forma_pagamento_pix
):
    with pytest.raises(IntegrityError):
        _pedido_direto(
            db,
            restaurante,
            cliente,
            status_criado,
            forma_pagamento_pix,
            service_type=OrderServiceType.DELIVERY,
        )


def test_banco_aceita_retirada_sem_endereco(
    db, restaurante, cliente, status_criado, forma_pagamento_pix
):
    pedido = _pedido_direto(
        db,
        restaurante,
        cliente,
        status_criado,
        forma_pagamento_pix,
        service_type=OrderServiceType.PICKUP,
    )

    db.refresh(pedido)

    assert pedido.service_type == OrderServiceType.PICKUP
    assert pedido.address_street is None


# ── forma de pagamento aceita ──
def test_forma_de_pagamento_aceita_e_registrada(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente, aceitar_formas
):
    _config(db, restaurante)
    aceitar_formas(restaurante, "PIX")

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 201
    assert resp.json()["forma_pagamento"]["codigo"] == "PIX"


def test_forma_de_pagamento_nao_aceita_e_rejeitada(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente, aceitar_formas
):
    _config(db, restaurante)
    aceitar_formas(restaurante, "DINHEIRO")

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422
    assert "Pix" in resp.json()["detail"]
    assert db.query(Order).filter_by(restaurant_id=restaurante.id).count() == 0


def test_forma_de_pagamento_inativa_e_rejeitada(
    db, client, restaurante, cliente, alimento_do_dia, token_para_cliente
):
    _config(db, restaurante)
    db.query(PaymentMethod).filter_by(code="PIX").update({PaymentMethod.is_active: False})
    db.flush()

    resp = client.post(
        "/pedidos",
        json=_payload(restaurante, alimento_do_dia, tipo_atendimento="RETIRADA"),
        headers=_headers(cliente, token_para_cliente),
    )

    assert resp.status_code == 422
    assert db.query(Order).filter_by(restaurant_id=restaurante.id).count() == 0