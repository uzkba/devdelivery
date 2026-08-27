import pytest
from datetime import date
from decimal import Decimal

from backend.app.model.models import AuditLog, Food, FoodCategory, Menu, MenuItem


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
        name="Item",
        description=None,
        base_price=Decimal("10.00"),
        is_active=True,
    )
    dados.update(overrides)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


def criar_cardapio(db, restaurante):
    menu = Menu(restaurant_id=restaurante.id, date=date.today())
    db.add(menu)
    db.flush()
    db.refresh(menu)
    return menu


def criar_item_cardapio(db, menu, alimento, is_available=True, day_price=None):
    item = MenuItem(
        menu_id=menu.id, food_id=alimento.id, is_available=is_available, day_price=day_price,
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def test_criar_pedido_gera_log_auditoria(
    db, client, restaurante, categoria, cliente, endereco, token_para_cliente,
    forma_pagamento_dinheiro,
):
    alimento = criar_alimento_direto(db, categoria, name="Feijoada", base_price=Decimal("15.00"))
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, alimento)

    token = token_para_cliente(cliente)
    payload = {
        "restaurante_id": str(restaurante.id),
        "endereco_id": str(endereco.id),
        "forma_pagamento": "DINHEIRO",
        "valor_pago_dinheiro": "30.00",
        "itens": [{"alimento_id": str(alimento.id), "quantidade": 2, "opcoes_selecionadas": []}],
    }
    resposta = client.post(
        "/pedidos", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 201

    log = db.query(AuditLog).filter_by(entity="pedido", action="CRIACAO").first()
    assert log is not None
    assert log.user_id is None
    assert log.restaurant_id == restaurante.id
    assert log.new_data["total_amount"] == resposta.json()["valor_total"]