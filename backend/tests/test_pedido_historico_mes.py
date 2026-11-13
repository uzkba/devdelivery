from datetime import datetime
from types import SimpleNamespace

import pytest


def _headers(token_para_cliente, cliente):
    return {"Authorization": f"Bearer {token_para_cliente(cliente)}"}


def _em(db, novo_pedido, momento, **extra):
    pedido = novo_pedido("ENTREGUE", **extra)
    pedido.order_datetime = momento
    db.flush()
    return pedido


@pytest.fixture()
def pedidos(db, novo_pedido):
    return SimpleNamespace(
        fim_de_outubro=_em(db, novo_pedido, datetime(2026, 11, 1, 2, 59)),
        inicio_de_novembro=_em(db, novo_pedido, datetime(2026, 11, 1, 3, 0)),
        meio_de_outubro=_em(db, novo_pedido, datetime(2026, 10, 15, 12, 0)),
        fim_de_novembro=_em(db, novo_pedido, datetime(2026, 12, 1, 2, 59)),
        inicio_de_dezembro=_em(db, novo_pedido, datetime(2026, 12, 1, 3, 0)),
    )


def _listar(client, headers, **params):
    resposta = client.get("/pedidos/me", params=params, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ids(corpo):
    return [item["id"] for item in corpo["items"]]


def test_mes_usa_a_virada_do_horario_local(client, pedidos, cliente, token_para_cliente):
    headers = _headers(token_para_cliente, cliente)

    outubro = _listar(client, headers, mes="2026-10")
    novembro = _listar(client, headers, mes="2026-11")
    dezembro = _listar(client, headers, mes="2026-12")

    assert _ids(outubro) == [str(pedidos.fim_de_outubro.id), str(pedidos.meio_de_outubro.id)]
    assert _ids(novembro) == [str(pedidos.fim_de_novembro.id), str(pedidos.inicio_de_novembro.id)]
    assert _ids(dezembro) == [str(pedidos.inicio_de_dezembro.id)]
    assert outubro["total"] == 2


def test_mes_sem_pedidos_volta_vazio(client, pedidos, cliente, token_para_cliente):
    corpo = _listar(client, _headers(token_para_cliente, cliente), mes="2026-09")

    assert corpo["items"] == []
    assert corpo["total"] == 0


def test_sem_mes_lista_tudo(client, pedidos, cliente, token_para_cliente):
    assert _listar(client, _headers(token_para_cliente, cliente))["total"] == 5


def test_mes_nao_mostra_pedido_de_outro_cliente(
    db, client, novo_pedido, cliente, outro_cliente, token_para_cliente
):
    meu = _em(db, novo_pedido, datetime(2026, 10, 15, 12, 0))
    _em(db, novo_pedido, datetime(2026, 10, 16, 12, 0), client_id=outro_cliente.id)

    corpo = _listar(client, _headers(token_para_cliente, cliente), mes="2026-10")

    assert _ids(corpo) == [str(meu.id)]


@pytest.mark.parametrize(
    "mes", ["2026-13", "2026-00", "26-10", "1999-10", "2026-1", "abc", "2026-10-01"]
)
def test_mes_invalido_da_422(client, cliente, token_para_cliente, mes):
    resposta = client.get(
        "/pedidos/me", params={"mes": mes}, headers=_headers(token_para_cliente, cliente)
    )

    assert resposta.status_code == 422


def test_lista_de_meses_do_mais_novo_para_o_mais_antigo(
    client, pedidos, cliente, token_para_cliente
):
    resposta = client.get("/pedidos/me/meses", headers=_headers(token_para_cliente, cliente))

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"mes": "2026-12", "quantidade": 1},
        {"mes": "2026-11", "quantidade": 2},
        {"mes": "2026-10", "quantidade": 2},
    ]


def test_lista_de_meses_so_conta_os_proprios_pedidos(
    db, client, novo_pedido, cliente, outro_cliente, token_para_cliente
):
    _em(db, novo_pedido, datetime(2026, 10, 15, 12, 0), client_id=outro_cliente.id)

    resposta = client.get("/pedidos/me/meses", headers=_headers(token_para_cliente, cliente))

    assert resposta.json() == []


def test_meses_exigem_login_de_cliente(client, admin_headers):
    assert client.get("/pedidos/me/meses").status_code in (401, 403)
    assert client.get("/pedidos/me/meses", headers=admin_headers).status_code in (401, 403)