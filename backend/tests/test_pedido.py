import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.seguranca import hash_password
from app.core.tempo import hoje_local
from app.model.models import (
    Client,
    CustomerAddress,
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    Order,
    OrderItem,
)
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


def _pedidos_do_restaurante(db, restaurante):
    return db.query(Order).filter_by(restaurant_id=restaurante.id).count()


def test_um_pedido_de_cada_tipo_e_criado_validado_e_persistido_com_snapshot(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante, charge_mode=DeliveryChargeMode.FIXO, fixed_fee=Decimal("7.50"))
    c = cardapio

    resp = postar(
        corpo_pedido(
            restaurante,
            [
                item_marmita(c.pronta, quantidade=2),
                item_marmita(
                    c.monte,
                    selecoes=[selecao(c.carnes, (c.frango, 1))],
                    observacao="sem tempero",
                ),
                item_combo(c.combo),
                item_avulso(c.feijoada, 2),
            ],
            endereco_id=str(endereco.id),
            forma_pagamento="DINHEIRO",
            valor_pago_dinheiro="200.00",
            observacoes="tocar o interfone",
        )
    )

    assert resp.status_code == 201, resp.json()
    corpo = resp.json()
    assert corpo["valor_itens"] == "175.80"
    assert corpo["valor_entrega"] == "7.50"
    assert corpo["valor_total"] == "183.30"
    assert corpo["valor_troco"] == "16.70"
    assert corpo["observacoes"] == "tocar o interfone"

    por_nome = {i["nome"]: i for i in corpo["itens"]}
    assert set(por_nome) == {"Pronta", "Monte a sua", "Combo Almoço", "Feijoada"}

    pronta = por_nome["Pronta"]
    assert (pronta["marmita_id"], pronta["combo_id"], pronta["alimento_id"]) == (
        str(c.pronta.id), None, None,
    )
    assert (pronta["quantidade"], pronta["preco_unitario"], pronta["subtotal"]) == (
        2, "20.00", "40.00",
    )
    assert pronta["snapshot"]["composicao"][0]["nome"] == "Arroz"

    monte = por_nome["Monte a sua"]
    assert monte["observacao"] == "sem tempero"
    assert monte["snapshot"]["escolhas"][0]["nome"] == "Frango"

    combo = por_nome["Combo Almoço"]
    assert (combo["combo_id"], combo["marmita_id"], combo["alimento_id"]) == (
        str(c.combo.id), None, None,
    )
    assert combo["snapshot"]["alimentos"][0]["nome"] == "Feijoada"

    avulso = por_nome["Feijoada"]
    assert avulso["alimento_id"] == str(c.feijoada.id)
    assert avulso["subtotal"] == "65.80"

    assert db.query(OrderItem).filter_by(order_id=uuid.UUID(corpo["id"])).count() == 4


def test_detalhe_para_a_equipe_traz_o_snapshot(
    db, client, restaurante, endereco, cardapio, postar, admin_headers
):
    config_entrega(db, restaurante)

    criado = postar(
        corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id))
    )
    detalhe = client.get(f"/pedidos/{criado.json()['id']}", headers=admin_headers)

    assert detalhe.status_code == 200
    assert detalhe.json()["itens"][0]["snapshot"]["tipo"] == "AVULSO"


def test_pedido_sem_token_retorna_401(client, restaurante, endereco, cardapio):
    corpo = corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id))
    assert client.post("/pedidos", json=corpo).status_code == 401


def test_pedido_com_token_de_admin_retorna_401(
    client, restaurante, endereco, cardapio, admin_headers
):
    corpo = corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id))
    assert client.post("/pedidos", json=corpo, headers=admin_headers).status_code == 401


def test_slug_inexistente_retorna_404(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            restaurante_slug="nao-existe", endereco_id=str(endereco.id),
        )
    )

    assert resp.status_code == 404


def test_restaurante_id_no_payload_e_rejeitado(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            endereco_id=str(endereco.id), restaurante_id=str(restaurante.id),
        )
    )

    assert resp.status_code == 422


def test_preco_enviado_pelo_cliente_e_rejeitado(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada, preco="1.00")],
            endereco_id=str(endereco.id),
        )
    )

    assert resp.status_code == 422


def test_observacao_do_item_acima_de_140_caracteres_e_rejeitada(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada, observacao="a" * 141)],
            endereco_id=str(endereco.id),
        )
    )

    assert resp.status_code == 422


def test_item_esgotado_hoje_rejeita_o_pedido_inteiro(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)
    cardapio.pronta.sold_out_on = hoje_local()

    resp = postar(
        corpo_pedido(
            restaurante,
            [item_avulso(cardapio.feijoada), item_marmita(cardapio.pronta)],
            endereco_id=str(endereco.id),
        )
    )

    assert resp.status_code == 422
    assert "esgotado hoje" in resp.json()["detail"]
    assert _pedidos_do_restaurante(db, restaurante) == 0


def test_marmita_personalizavel_com_soma_errada_retorna_422(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante,
            [item_marmita(cardapio.monte, selecoes=[selecao(cardapio.carnes, (cardapio.frango, 2))])],
            endereco_id=str(endereco.id),
        )
    )

    assert resp.status_code == 422
    assert "Escolha exatamente 1" in resp.json()["detail"]
    assert _pedidos_do_restaurante(db, restaurante) == 0


def test_endereco_de_outro_cliente_retorna_404(db, restaurante, outro_cliente, cardapio, postar):
    config_entrega(db, restaurante)
    alheio = CustomerAddress(
        client_id=outro_cliente.id, street="Rua de Outro", number="1", neighborhood="Bairro"
    )
    db.add(alheio)
    db.flush()

    resp = postar(
        corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(alheio.id))
    )

    assert resp.status_code == 404


def test_dinheiro_sem_valor_pago_retorna_422(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            endereco_id=str(endereco.id), forma_pagamento="DINHEIRO",
        )
    )

    assert resp.status_code == 422


def test_dinheiro_com_valor_menor_que_total_retorna_400(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            endereco_id=str(endereco.id), forma_pagamento="DINHEIRO", valor_pago_dinheiro=20,
        )
    )

    assert resp.status_code == 400


def test_dinheiro_calcula_troco(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            endereco_id=str(endereco.id), forma_pagamento="DINHEIRO", valor_pago_dinheiro=50,
        )
    )

    assert resp.status_code == 201
    assert resp.json()["valor_troco"] == "17.10"


def test_pix_com_valor_pago_retorna_422(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante)

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada)],
            endereco_id=str(endereco.id), forma_pagamento="PIX", valor_pago_dinheiro=10,
        )
    )

    assert resp.status_code == 422


def test_taxa_por_bairro_ignora_acento_caixa_e_espacos(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(db, restaurante, charge_mode=DeliveryChargeMode.BAIRRO)
    db.add(
        DeliveryRuleNeighborhood(
            restaurant_id=restaurante.id, neighborhood="São José", fee=Decimal("7.50"), is_active=True
        )
    )
    endereco.neighborhood = "  sao   JOSE "
    db.flush()

    resp = postar(
        corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id))
    )

    assert resp.status_code == 201
    assert resp.json()["valor_entrega"] == "7.50"


def test_bairro_fora_da_area_de_entrega_retorna_422(db, restaurante, endereco, cardapio, postar):
    config_entrega(db, restaurante, charge_mode=DeliveryChargeMode.BAIRRO)
    db.add(
        DeliveryRuleNeighborhood(
            restaurant_id=restaurante.id, neighborhood="Centro", fee=Decimal("7.50"), is_active=True
        )
    )
    endereco.neighborhood = "Bairro Distante"
    db.flush()

    resp = postar(
        corpo_pedido(restaurante, [item_avulso(cardapio.feijoada)], endereco_id=str(endereco.id))
    )

    assert resp.status_code == 422
    assert "fora da área de entrega" in resp.json()["detail"]


def test_frete_gratis_quando_os_itens_atingem_o_valor(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(
        db, restaurante, charge_mode=DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("7.50"), free_delivery_from=Decimal("65.80"),
    )

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada, 2)], endereco_id=str(endereco.id)
        )
    )

    assert resp.status_code == 201
    assert resp.json()["valor_entrega"] == "0.00"
    assert resp.json()["valor_total"] == "65.80"


def test_frete_cobrado_quando_os_itens_ficam_abaixo_do_valor(
    db, restaurante, endereco, cardapio, postar
):
    config_entrega(
        db, restaurante, charge_mode=DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("7.50"), free_delivery_from=Decimal("65.81"),
    )

    resp = postar(
        corpo_pedido(
            restaurante, [item_avulso(cardapio.feijoada, 2)], endereco_id=str(endereco.id)
        )
    )

    assert resp.status_code == 201
    assert resp.json()["valor_entrega"] == "7.50"
    assert resp.json()["valor_total"] == "73.30"


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