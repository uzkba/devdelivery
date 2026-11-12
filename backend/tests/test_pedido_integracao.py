from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.tempo import hoje_local
from app.routers import pedido_route
from app.services import disponibilidade_service as disponibilidade
from app.services import pedido_service
from tests.helpers_pedido import (
    config_entrega,
    corpo_pedido,
    criar_alimento,
    criar_avulso,
    criar_combo,
    criar_personalizavel,
    criar_pronta,
    item_avulso,
    item_combo,
    item_marmita,
    selecao,
)


@pytest.fixture()
def cardapio(db, restaurante, cat_venda, cat_composicao, cat_composicao_2):
    feijoada = criar_avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    frango = criar_alimento(db, restaurante, "Frango", cat_composicao)
    arroz = criar_alimento(db, restaurante, "Arroz", cat_composicao_2)
    pronta = criar_pronta(db, restaurante, [(arroz, 1)])
    monte = criar_personalizavel(db, restaurante, [(cat_composicao, 1)])
    combo = criar_combo(db, restaurante, [(pronta, 1)], [(feijoada, 1)])
    return SimpleNamespace(
        feijoada=feijoada, frango=frango, arroz=arroz,
        pronta=pronta, monte=monte, combo=combo, carnes=cat_composicao,
    )


@pytest.fixture()
def postar(client, cliente, token_para_cliente):
    def _postar(corpo):
        return client.post(
            "/pedidos",
            json=corpo,
            headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
        )

    return _postar


def test_pedido_nao_muda_quando_o_cadastro_muda_depois(
    db, client, restaurante, endereco, cardapio, postar, admin_headers
):
    config_entrega(db, restaurante)
    c = cardapio
    criado = postar(
        corpo_pedido(
            restaurante,
            [item_marmita(c.pronta), item_combo(c.combo), item_avulso(c.feijoada)],
            endereco_id=str(endereco.id),
        )
    )
    assert criado.status_code == 201, criado.json()
    pedido_id = criado.json()["id"]
    antes = client.get(f"/pedidos/{pedido_id}", headers=admin_headers).json()

    c.pronta.name = "Renomeada"
    c.pronta.price = Decimal("99.00")
    c.combo.name = "Combo renomeado"
    c.combo.price = Decimal("1.00")
    c.feijoada.name = "Outro nome"
    c.feijoada.standalone_price = Decimal("1.00")
    c.arroz.name = "Outro arroz"
    db.flush()
    db.expire_all()

    depois = client.get(f"/pedidos/{pedido_id}", headers=admin_headers).json()

    assert depois == antes


def test_disponibilidade_usa_o_dia_local_do_servico(
    db, restaurante, endereco, cardapio, postar, monkeypatch
):
    config_entrega(db, restaurante)
    outro_dia = hoje_local() + timedelta(days=1)
    disponibilidade.definir_regra(db, cardapio.feijoada, "PERSONALIZADO", [outro_dia.weekday()])
    corpo = corpo_pedido(
        restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id)
    )

    recusado = postar(corpo)
    assert recusado.status_code == 422
    assert "não é servido hoje" in recusado.json()["detail"]

    monkeypatch.setattr(pedido_service, "hoje_local", lambda: outro_dia)

    aceito = postar(corpo)
    assert aceito.status_code == 201, aceito.json()


def test_pedido_alimenta_o_mais_pedidos_de_cada_tipo(
    db, client, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante)
    c = cardapio
    criado = postar(
        corpo_pedido(
            restaurante,
            [item_marmita(c.pronta), item_combo(c.combo), item_avulso(c.feijoada)],
            endereco_id=str(endereco.id),
        )
    )
    assert criado.status_code == 201, criado.json()

    home = client.get(f"/restaurantes/{restaurante.slug}/cardapio")

    assert home.status_code == 200
    populares = {(i["tipo"], i["id"]) for i in home.json()["mais_pedidos"]}
    assert populares == {
        ("marmita", str(c.pronta.id)),
        ("combo", str(c.combo.id)),
        ("produto", str(c.feijoada.id)),
    }


def test_combo_com_marmitas_personalizaveis_exige_uma_configuracao_por_unidade(
    db, restaurante, endereco, cardapio, postar, cat_composicao
):
    config_entrega(db, restaurante)
    c = cardapio
    bife = criar_alimento(db, restaurante, "Bife", cat_composicao)
    combo = criar_combo(db, restaurante, [(c.monte, 2)], [])

    completo = postar(
        corpo_pedido(
            restaurante,
            [
                item_combo(
                    combo,
                    marmitas=[
                        (c.monte, [selecao(c.carnes, (c.frango, 1))]),
                        (c.monte, [selecao(c.carnes, (bife, 1))]),
                    ],
                    quantidade=2,
                )
            ],
            endereco_id=str(endereco.id),
        )
    )

    assert completo.status_code == 201, completo.json()
    item = completo.json()["itens"][0]
    assert item["subtotal"] == "90.00"
    unidades = item["snapshot"]["marmitas"]
    assert [u["escolhas"][0]["nome"] for u in unidades] == ["Frango", "Bife"]

    incompleto = postar(
        corpo_pedido(
            restaurante,
            [item_combo(combo, marmitas=[(c.monte, [selecao(c.carnes, (c.frango, 1))])])],
            endereco_id=str(endereco.id),
        )
    )

    assert incompleto.status_code == 422
    assert "Configure 2 unidade(s)" in incompleto.json()["detail"]


def test_novo_pedido_notifica_o_restaurante(
    db, restaurante, cardapio, postar, monkeypatch
):
    config_entrega(db, restaurante)
    eventos = []

    async def capturar(restaurant_id, mensagem):
        eventos.append((restaurant_id, mensagem))

    monkeypatch.setattr(pedido_route.manager, "broadcast_to_restaurant", capturar)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)], tipo_atendimento="RETIRADA"
        )
    )

    assert resp.status_code == 201, resp.json()
    assert eventos == [
        (
            restaurante.id,
            {
                "tipo": "NOVO_PEDIDO",
                "pedido_id": resp.json()["id"],
                "numero_pedido": resp.json()["numero_pedido"],
                "tipo_atendimento": "RETIRADA",
                "valor_total": 32.9,
            },
        )
    ]