from datetime import datetime
from decimal import Decimal

import pytest

from app.model.models import OrderServiceType, OrderStatus

DIA = "2026-11-10"


@pytest.fixture()
def caixa_headers(caixa_user, token_para):
    return {"Authorization": f"Bearer {token_para(caixa_user)}"}


@pytest.fixture()
def atendente_headers(atendente_user, token_para):
    return {"Authorization": f"Bearer {token_para(atendente_user)}"}


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _pedido(db, criar_pedido_direto, codigo, forma, total, momento, **extra):
    return criar_pedido_direto(_status(db, codigo), forma, Decimal(total), momento, **extra)


def _vendas(client, headers, inicio=DIA, fim=DIA):
    return client.get(
        "/relatorios/vendas", params={"data_inicio": inicio, "data_fim": fim}, headers=headers
    )


def _por_chave(itens, chave):
    return {item[chave]: item for item in itens}


def test_vendas_somam_faturaveis_por_dia_forma_e_tipo(
    db, client, caixa_headers, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", datetime(2026, 11, 10, 15, 0))
    _pedido(db, criar_pedido_direto, "CRIADO", forma_pagamento_pix, "20.00", datetime(2026, 11, 10, 16, 0))
    _pedido(db, criar_pedido_direto, "CANCELADO", forma_pagamento_pix, "99.00", datetime(2026, 11, 10, 17, 0))
    _pedido(db, criar_pedido_direto, "RECUSADO", forma_pagamento_pix, "99.00", datetime(2026, 11, 10, 17, 30))
    _pedido(
        db, criar_pedido_direto, "RETIRADO", forma_pagamento_pix, "50.00", datetime(2026, 11, 12, 15, 0),
        service_type=OrderServiceType.PICKUP,
    )

    resposta = _vendas(client, caixa_headers, "2026-11-10", "2026-11-12")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["data_inicio"] == "2026-11-10"
    assert corpo["data_fim"] == "2026-11-12"
    assert corpo["quantidade_pedidos"] == 3
    assert Decimal(corpo["total_vendas"]) == Decimal("100.00")
    assert Decimal(corpo["ticket_medio"]) == Decimal("33.33")

    assert [item["data"] for item in corpo["por_dia"]] == ["2026-11-10", "2026-11-11", "2026-11-12"]
    primeiro, segundo, terceiro = corpo["por_dia"]
    assert primeiro["quantidade_pedidos"] == 2
    assert Decimal(primeiro["total_vendas"]) == Decimal("50.00")
    assert Decimal(primeiro["ticket_medio"]) == Decimal("25.00")
    assert segundo["quantidade_pedidos"] == 0
    assert Decimal(segundo["total_vendas"]) == Decimal("0")
    assert Decimal(segundo["ticket_medio"]) == Decimal("0")
    assert terceiro["quantidade_pedidos"] == 1
    assert Decimal(terceiro["total_vendas"]) == Decimal("50.00")

    formas = _por_chave(corpo["por_forma_pagamento"], "forma")
    assert formas["PIX"]["quantidade_pedidos"] == 2
    assert Decimal(formas["PIX"]["total_vendas"]) == Decimal("70.00")
    assert formas["DINHEIRO"]["quantidade_pedidos"] == 1
    assert Decimal(formas["DINHEIRO"]["total_vendas"]) == Decimal("30.00")

    tipos = _por_chave(corpo["por_tipo_atendimento"], "tipo_atendimento")
    assert tipos["ENTREGA"]["quantidade_pedidos"] == 2
    assert Decimal(tipos["ENTREGA"]["total_vendas"]) == Decimal("50.00")
    assert tipos["RETIRADA"]["quantidade_pedidos"] == 1
    assert Decimal(tipos["RETIRADA"]["total_vendas"]) == Decimal("50.00")


def test_vendas_usam_o_dia_local(db, client, caixa_headers, criar_pedido_direto, forma_pagamento_pix):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "10.00", datetime(2026, 11, 10, 3, 0))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "20.00", datetime(2026, 11, 11, 1, 30))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "100.00", datetime(2026, 11, 10, 2, 30))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "200.00", datetime(2026, 11, 11, 3, 0))

    corpo = _vendas(client, caixa_headers).json()

    assert corpo["quantidade_pedidos"] == 2
    assert Decimal(corpo["total_vendas"]) == Decimal("30.00")
    assert len(corpo["por_dia"]) == 1
    assert corpo["por_dia"][0]["data"] == DIA


def test_periodo_sem_vendas_devolve_zeros(client, caixa_headers):
    corpo = _vendas(client, caixa_headers).json()

    assert corpo["quantidade_pedidos"] == 0
    assert Decimal(corpo["total_vendas"]) == Decimal("0")
    assert Decimal(corpo["ticket_medio"]) == Decimal("0")
    assert len(corpo["por_dia"]) == 1
    assert corpo["por_forma_pagamento"] == []
    assert corpo["por_tipo_atendimento"] == []


def test_vendas_ignoram_outro_restaurante(
    db, client, caixa_headers, outro_restaurante, criar_pedido_direto, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "10.00", datetime(2026, 11, 10, 15, 0))
    _pedido(
        db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "500.00", datetime(2026, 11, 10, 15, 0),
        restaurant_id=outro_restaurante.id,
    )

    corpo = _vendas(client, caixa_headers).json()

    assert corpo["quantidade_pedidos"] == 1
    assert Decimal(corpo["total_vendas"]) == Decimal("10.00")


@pytest.mark.parametrize("rota", ["vendas", "itens-campeoes", "horarios-de-pico"])
def test_periodo_invertido_ou_longo_demais_devolve_422(client, caixa_headers, rota):
    invertido = client.get(
        f"/relatorios/{rota}",
        params={"data_inicio": "2026-11-12", "data_fim": "2026-11-10"},
        headers=caixa_headers,
    )
    longo = client.get(
        f"/relatorios/{rota}",
        params={"data_inicio": "2025-01-01", "data_fim": "2026-01-02"},
        headers=caixa_headers,
    )

    assert invertido.status_code == 422
    assert longo.status_code == 422


@pytest.mark.parametrize("rota", ["vendas", "itens-campeoes", "horarios-de-pico"])
def test_atendente_nao_acessa_os_relatorios_de_vendas(client, atendente_headers, rota):
    resposta = client.get(
        f"/relatorios/{rota}",
        params={"data_inicio": DIA, "data_fim": DIA},
        headers=atendente_headers,
    )

    assert resposta.status_code == 403


def test_sem_token_devolve_401(client):
    resposta = client.get("/relatorios/vendas", params={"data_inicio": DIA, "data_fim": DIA})

    assert resposta.status_code == 401


def test_admin_tambem_acessa(client, admin_headers):
    assert _vendas(client, admin_headers).status_code == 200


@pytest.fixture()
def dia_com_itens(
    db, criar_pedido_direto, adicionar_item, forma_pagamento_pix, marmita_pronta, alimento_so_venda
):
    entregue = _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "50.00", datetime(2026, 11, 10, 15, 0))
    adicionar_item(entregue, "Feijoada", 3, food_id=alimento_so_venda.id)
    adicionar_item(entregue, "Marmita Pronta", 2, meal_box_id=marmita_pronta.id)

    criado = _pedido(db, criar_pedido_direto, "CRIADO", forma_pagamento_pix, "30.00", datetime(2026, 11, 10, 16, 0))
    adicionar_item(criado, "Feijoada", 2, food_id=alimento_so_venda.id)
    adicionar_item(criado, "Item antigo", 1)

    cancelado = _pedido(db, criar_pedido_direto, "CANCELADO", forma_pagamento_pix, "99.00", datetime(2026, 11, 10, 17, 0))
    adicionar_item(cancelado, "Feijoada", 10, food_id=alimento_so_venda.id)

    outro_dia = _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "99.00", datetime(2026, 11, 11, 15, 0))
    adicionar_item(outro_dia, "Feijoada", 10, food_id=alimento_so_venda.id)


def test_itens_campeoes_ordenam_por_quantidade_e_ignoram_nao_faturaveis(
    client, caixa_headers, dia_com_itens, alimento_so_venda, marmita_pronta
):
    resposta = client.get(
        "/relatorios/itens-campeoes", params={"data_inicio": DIA, "data_fim": DIA}, headers=caixa_headers
    )

    assert resposta.status_code == 200
    itens = resposta.json()["items"]
    assert [item["posicao"] for item in itens] == [1, 2, 3]
    assert [item["nome"] for item in itens] == ["Feijoada", "Marmita Pronta", "Item antigo"]
    assert [item["quantidade"] for item in itens] == [5, 2, 1]
    assert [item["tipo"] for item in itens] == ["AVULSO", "MARMITA", "AVULSO"]
    assert itens[0]["item_id"] == str(alimento_so_venda.id)
    assert itens[1]["item_id"] == str(marmita_pronta.id)
    assert itens[2]["item_id"] is None


def test_itens_campeoes_respeitam_o_limite(client, caixa_headers, dia_com_itens):
    resposta = client.get(
        "/relatorios/itens-campeoes",
        params={"data_inicio": DIA, "data_fim": DIA, "limite": 2},
        headers=caixa_headers,
    )

    assert [item["nome"] for item in resposta.json()["items"]] == ["Feijoada", "Marmita Pronta"]


def test_itens_campeoes_com_limite_invalido_devolve_422(client, caixa_headers):
    resposta = client.get(
        "/relatorios/itens-campeoes",
        params={"data_inicio": DIA, "data_fim": DIA, "limite": 0},
        headers=caixa_headers,
    )

    assert resposta.status_code == 422


def test_horarios_de_pico_agrupam_por_hora_local(
    db, client, caixa_headers, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", datetime(2026, 11, 10, 15, 0))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "20.00", datetime(2026, 11, 10, 15, 40))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "10.00", datetime(2026, 11, 10, 22, 30))
    _pedido(db, criar_pedido_direto, "RETIRADO", forma_pagamento_pix, "15.00", datetime(2026, 11, 11, 1, 30))
    _pedido(db, criar_pedido_direto, "CANCELADO", forma_pagamento_pix, "99.00", datetime(2026, 11, 10, 15, 10))

    resposta = client.get(
        "/relatorios/horarios-de-pico", params={"data_inicio": DIA, "data_fim": DIA}, headers=caixa_headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [item["hora"] for item in corpo["horas"]] == list(range(24))
    horas = _por_chave(corpo["horas"], "hora")
    assert horas[12]["quantidade_pedidos"] == 2
    assert Decimal(horas[12]["total_vendas"]) == Decimal("50.00")
    assert horas[19]["quantidade_pedidos"] == 1
    assert Decimal(horas[19]["total_vendas"]) == Decimal("10.00")
    assert horas[22]["quantidade_pedidos"] == 1
    assert Decimal(horas[22]["total_vendas"]) == Decimal("15.00")
    assert horas[3]["quantidade_pedidos"] == 0
    assert [item["hora"] for item in corpo["picos"]] == [12, 19, 22]


def test_horarios_de_pico_sem_pedidos_nao_tem_picos(client, caixa_headers):
    corpo = client.get(
        "/relatorios/horarios-de-pico", params={"data_inicio": DIA, "data_fim": DIA}, headers=caixa_headers
    ).json()

    assert len(corpo["horas"]) == 24
    assert corpo["picos"] == []