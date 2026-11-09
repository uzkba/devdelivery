from datetime import date, datetime
from decimal import Decimal

import pytest

from app.model.models import MealBox, MealBoxKind, OrderItem
from app.services import cardapio_publico_service as svc

HOJE = date(2026, 11, 6)
NA_JANELA = datetime(2026, 10, 10, 12, 0)
FORA_DA_JANELA = datetime(2026, 10, 1, 12, 0)
RECENTE = datetime(2026, 11, 5, 12, 0)


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


def _home(client, slug):
    resposta = client.get(f"/restaurantes/{slug}/cardapio")
    assert resposta.status_code == 200
    return resposta.json()


def _ids(lista):
    return [i["id"] for i in lista]


@pytest.fixture()
def pedir(db, criar_pedido_direto, status_criado, forma_pagamento_dinheiro):
    def _pedir(quando=RECENTE, status=None, restaurant_id=None, **ids):
        overrides = {"restaurant_id": restaurant_id} if restaurant_id else {}
        pedido = criar_pedido_direto(
            status or status_criado, forma_pagamento_dinheiro, Decimal("10.00"), quando, **overrides
        )
        db.add(
            OrderItem(
                order_id=pedido.id,
                food_name="Item",
                quantity=1,
                base_price=Decimal("10.00"),
                subtotal=Decimal("10.00"),
                **ids,
            )
        )
        db.flush()
        return pedido

    return _pedir


# ------------------------------ destaques ------------------------------
def test_sem_destaque_a_lista_vem_vazia(client, restaurante, marmita_pronta):
    assert _home(client, restaurante.slug)["destaques"] == []


def test_destaques_trazem_os_tres_tipos_nessa_ordem(
    db, client, restaurante, marmita_pronta, combo_teste, alimento_so_venda
):
    marmita_pronta.is_featured = True
    combo_teste.is_featured = True
    alimento_so_venda.is_featured = True
    db.flush()

    destaques = _home(client, restaurante.slug)["destaques"]
    assert [(d["tipo"], d["id"]) for d in destaques] == [
        ("marmita", str(marmita_pronta.id)),
        ("combo", str(combo_teste.id)),
        ("produto", str(alimento_so_venda.id)),
    ]
    assert Decimal(destaques[2]["preco"]) == Decimal("32.90")


def test_destaque_esgotado_hoje_nao_aparece(db, client, restaurante, marmita_pronta):
    marmita_pronta.is_featured = True
    marmita_pronta.sold_out_on = HOJE
    db.flush()
    assert _home(client, restaurante.slug)["destaques"] == []


# ------------------------------ mais pedidos ------------------------------
def test_mais_pedidos_ordena_por_quantidade_de_itens(
    client, restaurante, pedir, marmita_pronta, alimento_so_venda, alimento_bebida
):
    for _ in range(3):
        pedir(food_id=alimento_so_venda.id)
    for _ in range(2):
        pedir(meal_box_id=marmita_pronta.id)
    pedir(food_id=alimento_bebida.id)

    mais = _home(client, restaurante.slug)["mais_pedidos"]
    assert [(m["tipo"], m["id"]) for m in mais] == [
        ("produto", str(alimento_so_venda.id)),
        ("marmita", str(marmita_pronta.id)),
        ("produto", str(alimento_bebida.id)),
    ]


def test_pedido_cancelado_nao_conta(
    client, restaurante, pedir, status_cancelado, alimento_so_venda, alimento_bebida
):
    pedir(food_id=alimento_so_venda.id)
    for _ in range(2):
        pedir(status=status_cancelado, food_id=alimento_bebida.id)

    assert _ids(_home(client, restaurante.slug)["mais_pedidos"]) == [str(alimento_so_venda.id)]


def test_so_conta_os_ultimos_30_dias(client, restaurante, pedir, alimento_so_venda, alimento_bebida):
    for _ in range(3):
        pedir(quando=FORA_DA_JANELA, food_id=alimento_so_venda.id)
    pedir(quando=NA_JANELA, food_id=alimento_bebida.id)

    assert _ids(_home(client, restaurante.slug)["mais_pedidos"]) == [str(alimento_bebida.id)]


def test_item_esgotado_hoje_sai_de_mais_pedidos(db, client, restaurante, pedir, alimento_so_venda):
    pedir(food_id=alimento_so_venda.id)
    alimento_so_venda.sold_out_on = HOJE
    db.flush()
    assert _home(client, restaurante.slug)["mais_pedidos"] == []


def test_alimento_de_composicao_pedido_no_legado_nao_aparece(client, restaurante, pedir, alimento_arroz):
    pedir(food_id=alimento_arroz.id)
    assert _home(client, restaurante.slug)["mais_pedidos"] == []


def test_mais_pedidos_tem_no_maximo_cinco(db, client, restaurante, pedir):
    for i in range(7):
        caixa = MealBox(
            restaurant_id=restaurante.id,
            name=f"Marmita {i}",
            kind=MealBoxKind.READY,
            price=Decimal("20.00"),
        )
        db.add(caixa)
        db.flush()
        pedir(meal_box_id=caixa.id)

    assert len(_home(client, restaurante.slug)["mais_pedidos"]) == 5


def test_pedidos_de_outro_restaurante_nao_contam(
    client, restaurante, outro_restaurante, pedir, marmita_pronta, marmita_b
):
    pedir(restaurant_id=outro_restaurante.id, meal_box_id=marmita_b.id)

    assert _ids(_home(client, outro_restaurante.slug)["mais_pedidos"]) == [str(marmita_b.id)]
    assert _home(client, restaurante.slug)["mais_pedidos"] == []