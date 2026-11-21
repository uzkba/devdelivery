import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.seguranca import hash_password
from app.model.models import AdminUser, CashClosing, CashClosingMethod, OrderStatus
from app.services import caixa_dia_service

HOJE = date(2026, 11, 20)
DIA = "2026-11-10"
MEIO_DIA_LOCAL = datetime(2026, 11, 10, 15, 0)


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(caixa_dia_service, "hoje_local", lambda agora=None: HOJE)


@pytest.fixture()
def caixa_headers(caixa_user, token_para):
    return {"Authorization": f"Bearer {token_para(caixa_user)}"}


@pytest.fixture()
def atendente_headers(atendente_user, token_para):
    return {"Authorization": f"Bearer {token_para(atendente_user)}"}


@pytest.fixture()
def lucas(db, restaurante):
    user = AdminUser(
        restaurant_id=restaurante.id,
        name="Lucas Entregador",
        login="lucas.entregador",
        password_hash=hash_password("senha123"),
        role="entregador",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _pedido(db, criar_pedido_direto, codigo, forma, total, **extra):
    return criar_pedido_direto(_status(db, codigo), forma, Decimal(total), MEIO_DIA_LOCAL, **extra)


def _abrir(client, headers, data=DIA):
    resposta = client.post("/caixa/abrir", json={"data": data}, headers=headers)
    assert resposta.status_code == 201
    return resposta.json()


def _dia(client, headers, data=DIA):
    resposta = client.get("/caixa/dia", params={"data": data}, headers=headers)
    assert resposta.status_code == 200
    return resposta.json()


def _por_chave(itens, chave):
    return {item[chave]: item for item in itens}


def _corpo_fechamento(pedro, lucas_user, dinheiro="78.00", repasse_lucas="38.00", observacoes="Lucas repassou 2 reais a menos"):
    return {
        "data": DIA,
        "contagem": {"DINHEIRO": dinheiro, "PIX": "20.00"},
        "acertos": [
            {"entregador_id": str(pedro.id), "valor_repassado": "30.00"},
            {"entregador_id": str(lucas_user.id), "valor_repassado": repasse_lucas},
        ],
        "observacoes": observacoes,
    }


@pytest.fixture()
def dia_de_vendas(
    db, entregador_user, lucas, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", driver_id=entregador_user.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "20.00", driver_id=entregador_user.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "40.00", driver_id=lucas.id)
    _pedido(db, criar_pedido_direto, "RETIRADO", forma_pagamento_dinheiro, "10.00")


def test_abre_o_caixa_do_dia(client, caixa_headers, caixa_user):
    resposta = client.post("/caixa/abrir", json={"data": DIA}, headers=caixa_headers)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["data"] == DIA
    assert corpo["status"] == "ABERTO"
    assert corpo["aberto_por"] == str(caixa_user.id)
    assert corpo["aberto_em"] is not None
    assert corpo["fechado_em"] is None
    assert corpo["reaberturas"] == 0
    assert corpo["pode_fechar"] is True


def test_abre_o_caixa_de_hoje_quando_nao_informa_a_data(client, admin_headers):
    resposta = client.post("/caixa/abrir", headers=admin_headers)

    assert resposta.status_code == 201
    assert resposta.json()["data"] == str(HOJE)


def test_nao_abre_o_mesmo_dia_duas_vezes(client, admin_headers, caixa_headers):
    _abrir(client, admin_headers)

    resposta = client.post("/caixa/abrir", json={"data": DIA}, headers=caixa_headers)

    assert resposta.status_code == 409


def test_nao_abre_dia_futuro(client, admin_headers):
    resposta = client.post("/caixa/abrir", json={"data": "2026-11-21"}, headers=admin_headers)

    assert resposta.status_code == 422


ROTAS = [
    ("post", "/caixa/abrir", {}),
    ("get", "/caixa/dia", None),
    ("post", "/caixa/fechar", {"contagem": {}}),
    ("post", "/caixa/reabrir", {"data": DIA}),
]


@pytest.mark.parametrize("metodo,url,corpo", ROTAS)
def test_atendente_nao_acessa_o_caixa(client, atendente_headers, metodo, url, corpo):
    argumentos = {"json": corpo} if corpo is not None else {}

    resposta = getattr(client, metodo)(url, headers=atendente_headers, **argumentos)

    assert resposta.status_code == 403


def test_sem_token_devolve_401(client):
    assert client.get("/caixa/dia").status_code == 401


def test_so_o_admin_reabre_o_caixa(client, admin_headers, caixa_headers):
    _abrir(client, admin_headers)
    client.post("/caixa/fechar", json={"data": DIA, "contagem": {}}, headers=admin_headers)

    resposta = client.post("/caixa/reabrir", json={"data": DIA}, headers=caixa_headers)

    assert resposta.status_code == 403


def test_dia_sem_caixa_aberto(client, caixa_headers):
    corpo = _dia(client, caixa_headers)

    assert corpo["status"] == "NAO_ABERTO"
    assert corpo["pode_fechar"] is False
    assert corpo["aberto_por"] is None
    assert Decimal(corpo["total_vendas"]) == Decimal("0")


def test_resumo_do_caixa_aberto_mostra_a_apuracao_ao_vivo(
    db, client, caixa_headers, entregador_user, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", driver_id=entregador_user.id)
    _pedido(db, criar_pedido_direto, "CONFIRMADO", forma_pagamento_pix, "12.00")
    _abrir(client, caixa_headers)

    corpo = _dia(client, caixa_headers)

    assert corpo["status"] == "ABERTO"
    assert corpo["pedidos_em_aberto"] == 1
    assert corpo["pode_fechar"] is False
    assert Decimal(corpo["total_vendas"]) == Decimal("30.00")
    formas = _por_chave(corpo["formas"], "forma")
    assert set(formas) == {"DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO"}
    assert Decimal(formas["DINHEIRO"]["valor_esperado"]) == Decimal("30.00")
    assert formas["DINHEIRO"]["valor_contado"] is None
    assert len(corpo["entregadores"]) == 1
    assert corpo["entregadores"][0]["nome"] == "Pedro Entregador"
    assert corpo["entregadores"][0]["valor_repassado"] is None


def test_fecha_o_caixa_de_um_dia_com_dois_entregadores_e_uma_diferenca(
    client, caixa_headers, caixa_user, entregador_user, lucas, dia_de_vendas
):
    _abrir(client, caixa_headers)

    resposta = client.post(
        "/caixa/fechar", json=_corpo_fechamento(entregador_user, lucas), headers=caixa_headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "FECHADO"
    assert corpo["fechado_por"] == str(caixa_user.id)
    assert corpo["fechado_em"] is not None
    assert corpo["fechamento_id"] is not None
    assert corpo["pode_fechar"] is False
    assert corpo["quantidade_pedidos"] == 4
    assert Decimal(corpo["total_vendas"]) == Decimal("100.00")
    assert Decimal(corpo["diferenca_total"]) == Decimal("-2.00")
    assert corpo["observacoes"] == "Lucas repassou 2 reais a menos"

    formas = _por_chave(corpo["formas"], "forma")
    assert Decimal(formas["DINHEIRO"]["valor_esperado"]) == Decimal("80.00")
    assert Decimal(formas["DINHEIRO"]["valor_contado"]) == Decimal("78.00")
    assert Decimal(formas["DINHEIRO"]["diferenca"]) == Decimal("-2.00")
    assert Decimal(formas["PIX"]["diferenca"]) == Decimal("0")

    assert [item["nome"] for item in corpo["entregadores"]] == ["Lucas Entregador", "Pedro Entregador"]
    entregadores = _por_chave(corpo["entregadores"], "nome")
    assert Decimal(entregadores["Lucas Entregador"]["valor_esperado"]) == Decimal("40.00")
    assert Decimal(entregadores["Lucas Entregador"]["valor_repassado"]) == Decimal("38.00")
    assert Decimal(entregadores["Lucas Entregador"]["diferenca"]) == Decimal("-2.00")
    assert entregadores["Pedro Entregador"]["quantidade_entregas"] == 2
    assert Decimal(entregadores["Pedro Entregador"]["diferenca"]) == Decimal("0")

    assert _dia(client, caixa_headers) == corpo


def test_fechar_com_diferenca_sem_observacao_devolve_422_e_mantem_aberto(
    client, caixa_headers, entregador_user, lucas, dia_de_vendas
):
    _abrir(client, caixa_headers)

    resposta = client.post(
        "/caixa/fechar",
        json=_corpo_fechamento(entregador_user, lucas, observacoes=None),
        headers=caixa_headers,
    )

    assert resposta.status_code == 422
    assert _dia(client, caixa_headers)["status"] == "ABERTO"


def test_fechar_sem_abrir_devolve_409(client, caixa_headers):
    resposta = client.post("/caixa/fechar", json={"data": DIA, "contagem": {}}, headers=caixa_headers)

    assert resposta.status_code == 409


def test_fechar_com_acerto_repetido_devolve_422(client, caixa_headers, entregador_user, lucas, dia_de_vendas):
    _abrir(client, caixa_headers)
    corpo = _corpo_fechamento(entregador_user, lucas)
    corpo["acertos"].append({"entregador_id": str(lucas.id), "valor_repassado": "1.00"})

    resposta = client.post("/caixa/fechar", json=corpo, headers=caixa_headers)

    assert resposta.status_code == 422


def test_reabre_o_caixa_fechado_e_permite_fechar_de_novo(db, client, admin_headers, admin_user):
    _abrir(client, admin_headers)
    fechado = client.post("/caixa/fechar", json={"data": DIA, "contagem": {}}, headers=admin_headers)
    assert fechado.status_code == 200
    fechamento_id = uuid.UUID(fechado.json()["fechamento_id"])
    assert db.query(CashClosingMethod).filter_by(closing_id=fechamento_id).count() > 0

    resposta = client.post("/caixa/reabrir", json={"data": DIA}, headers=admin_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ABERTO"
    assert corpo["reaberturas"] == 1
    assert corpo["reaberto_por"] == str(admin_user.id)
    assert corpo["reaberto_em"] is not None
    assert corpo["fechamento_id"] is None
    assert corpo["fechado_em"] is None
    assert db.query(CashClosing).filter_by(id=fechamento_id).count() == 0
    assert db.query(CashClosingMethod).filter_by(closing_id=fechamento_id).count() == 0

    novamente = client.post("/caixa/fechar", json={"data": DIA, "contagem": {}}, headers=admin_headers)

    assert novamente.status_code == 200
    assert novamente.json()["status"] == "FECHADO"
    assert novamente.json()["reaberturas"] == 1


def test_reabrir_caixa_aberto_devolve_409(client, admin_headers):
    _abrir(client, admin_headers)

    resposta = client.post("/caixa/reabrir", json={"data": DIA}, headers=admin_headers)

    assert resposta.status_code == 409


def test_reabrir_dia_sem_caixa_devolve_404(client, admin_headers):
    resposta = client.post("/caixa/reabrir", json={"data": DIA}, headers=admin_headers)

    assert resposta.status_code == 404


def test_caixa_de_um_restaurante_nao_aparece_no_outro(client, admin_headers, outro_admin_headers):
    _abrir(client, admin_headers)

    corpo = _dia(client, outro_admin_headers)

    assert corpo["status"] == "NAO_ABERTO"