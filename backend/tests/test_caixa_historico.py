import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.model.models import CashClosing, CashClosingDriver, CashClosingMethod, OrderStatus
from app.services import caixa_historico_service

HOJE = date(2026, 11, 20)
DIA = "2026-11-10"


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(caixa_historico_service, "hoje_local", lambda agora=None: HOJE)


@pytest.fixture()
def caixa_headers(caixa_user, token_para):
    return {"Authorization": f"Bearer {token_para(caixa_user)}"}


@pytest.fixture()
def atendente_headers(atendente_user, token_para):
    return {"Authorization": f"Bearer {token_para(atendente_user)}"}


def _fechamento(
    db,
    restaurante,
    usuario,
    inicio,
    fim=None,
    diferenca_cabecalho="0.00",
    diferenca_forma="0.00",
    entregador=None,
    com_linhas=True,
):
    fechamento = CashClosing(
        restaurant_id=restaurante.id,
        start_date=inicio,
        end_date=fim or inicio,
        total_sales=Decimal("50.00"),
        expected_amount=Decimal("50.00"),
        reported_amount=Decimal("50.00") + Decimal(diferenca_cabecalho),
        difference=Decimal(diferenca_cabecalho),
        order_count=2,
        cancelled_count=1,
        closed_by=usuario.id,
    )
    db.add(fechamento)
    db.flush()
    if com_linhas:
        db.add(
            CashClosingMethod(
                closing_id=fechamento.id,
                method_code="DINHEIRO",
                order_count=2,
                expected_amount=Decimal("50.00"),
                counted_amount=Decimal("50.00") + Decimal(diferenca_forma),
                difference=Decimal(diferenca_forma),
            )
        )
    if com_linhas and entregador is not None:
        db.add(
            CashClosingDriver(
                closing_id=fechamento.id,
                driver_id=entregador.id,
                driver_name=entregador.name,
                delivery_count=1,
                expected_amount=Decimal("30.00"),
                handed_amount=Decimal("28.00"),
                difference=Decimal("-2.00"),
            )
        )
    db.flush()
    db.refresh(fechamento)
    return fechamento


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _pedido(db, criar_pedido_direto, codigo, forma, total, momento, **extra):
    return criar_pedido_direto(_status(db, codigo), forma, Decimal(total), momento, **extra)


def test_lista_apenas_fechamentos_do_restaurante_autenticado(
    db, client, restaurante, outro_restaurante, caixa_user, outro_admin_user, caixa_headers
):
    proprio = _fechamento(db, restaurante, caixa_user, date(2026, 11, 10))
    _fechamento(db, outro_restaurante, outro_admin_user, date(2026, 11, 10))

    resposta = client.get("/caixa/historico", headers=caixa_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert corpo["items"][0]["id"] == str(proprio.id)
    assert corpo["items"][0]["fechado_por_nome"] == "Carlos Caixa"


def test_ordena_do_mais_recente_e_pagina(db, client, restaurante, caixa_user, caixa_headers):
    for dia in (10, 11, 12):
        _fechamento(db, restaurante, caixa_user, date(2026, 11, dia))

    primeira = client.get("/caixa/historico", params={"page": 1, "page_size": 2}, headers=caixa_headers).json()
    segunda = client.get("/caixa/historico", params={"page": 2, "page_size": 2}, headers=caixa_headers).json()

    assert primeira["total"] == 3
    assert primeira["total_pages"] == 2
    assert [item["data_inicio"] for item in primeira["items"]] == ["2026-11-12", "2026-11-11"]
    assert [item["data_inicio"] for item in segunda["items"]] == ["2026-11-10"]


def test_filtra_por_periodo(db, client, restaurante, caixa_user, caixa_headers):
    _fechamento(db, restaurante, caixa_user, date(2026, 11, 10))
    escolhido = _fechamento(db, restaurante, caixa_user, date(2026, 11, 11))
    _fechamento(db, restaurante, caixa_user, date(2026, 11, 12))

    resposta = client.get(
        "/caixa/historico",
        params={"data_inicio": "2026-11-11", "data_fim": "2026-11-11"},
        headers=caixa_headers,
    )

    assert [item["id"] for item in resposta.json()["items"]] == [str(escolhido.id)]


def test_periodo_invertido_devolve_422(client, caixa_headers):
    resposta = client.get(
        "/caixa/historico",
        params={"data_inicio": "2026-11-12", "data_fim": "2026-11-10"},
        headers=caixa_headers,
    )

    assert resposta.status_code == 422


def test_filtra_por_diferenca_olhando_tambem_as_linhas(db, client, restaurante, caixa_user, caixa_headers):
    com_diferenca = _fechamento(db, restaurante, caixa_user, date(2026, 11, 10), diferenca_forma="-2.00")
    sem_diferenca = _fechamento(db, restaurante, caixa_user, date(2026, 11, 11))

    so_com = client.get("/caixa/historico", params={"com_diferenca": "true"}, headers=caixa_headers).json()
    so_sem = client.get("/caixa/historico", params={"com_diferenca": "false"}, headers=caixa_headers).json()
    todos = client.get("/caixa/historico", headers=caixa_headers).json()

    assert [item["id"] for item in so_com["items"]] == [str(com_diferenca.id)]
    assert so_com["items"][0]["tem_diferenca"] is True
    assert Decimal(so_com["items"][0]["diferenca"]) == Decimal("0")
    assert [item["id"] for item in so_sem["items"]] == [str(sem_diferenca.id)]
    assert so_sem["items"][0]["tem_diferenca"] is False
    assert todos["total"] == 2


def test_detalhe_traz_formas_e_entregadores(db, client, restaurante, caixa_user, entregador_user, caixa_headers):
    fechamento = _fechamento(
        db,
        restaurante,
        caixa_user,
        date(2026, 11, 10),
        diferenca_cabecalho="-2.00",
        diferenca_forma="-2.00",
        entregador=entregador_user,
    )

    resposta = client.get(f"/caixa/historico/{fechamento.id}", headers=caixa_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(fechamento.id)
    assert corpo["fechado_por_nome"] == "Carlos Caixa"
    assert corpo["tem_diferenca"] is True
    assert Decimal(corpo["diferenca"]) == Decimal("-2.00")
    assert corpo["formas"][0]["forma"] == "DINHEIRO"
    assert Decimal(corpo["formas"][0]["valor_contado"]) == Decimal("48.00")
    assert Decimal(corpo["formas"][0]["diferenca"]) == Decimal("-2.00")
    assert corpo["entregadores"][0]["nome"] == "Pedro Entregador"
    assert Decimal(corpo["entregadores"][0]["valor_repassado"]) == Decimal("28.00")


def test_detalhe_de_fechamento_antigo_vem_sem_linhas(db, client, restaurante, caixa_user, caixa_headers):
    fechamento = _fechamento(db, restaurante, caixa_user, date(2026, 11, 10), com_linhas=False)

    corpo = client.get(f"/caixa/historico/{fechamento.id}", headers=caixa_headers).json()

    assert corpo["formas"] == []
    assert corpo["entregadores"] == []


def test_detalhe_de_outro_restaurante_devolve_404(
    db, client, outro_restaurante, outro_admin_user, caixa_headers
):
    alheio = _fechamento(db, outro_restaurante, outro_admin_user, date(2026, 11, 11))

    resposta = client.get(f"/caixa/historico/{alheio.id}", headers=caixa_headers)

    assert resposta.status_code == 404


@pytest.mark.parametrize(
    "url",
    ["/caixa/historico", "/caixa/movimentos", f"/caixa/historico/{uuid.uuid4()}"],
)
def test_atendente_nao_acessa_historico_nem_movimentos(client, atendente_headers, url):
    assert client.get(url, headers=atendente_headers).status_code == 403


@pytest.fixture()
def dia_com_movimentos(
    db,
    outro_restaurante,
    entregador_user,
    criar_pedido_direto,
    forma_pagamento_dinheiro,
    forma_pagamento_pix,
):
    entregue = _pedido(
        db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00",
        datetime(2026, 11, 10, 15, 0), driver_id=entregador_user.id,
    )
    retirado = _pedido(
        db, criar_pedido_direto, "RETIRADO", forma_pagamento_pix, "20.00", datetime(2026, 11, 10, 16, 0)
    )
    cancelado = _pedido(
        db, criar_pedido_direto, "CANCELADO", forma_pagamento_pix, "40.00", datetime(2026, 11, 10, 17, 0)
    )
    _pedido(db, criar_pedido_direto, "CONFIRMADO", forma_pagamento_pix, "99.00", datetime(2026, 11, 10, 18, 0))
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "99.00", datetime(2026, 11, 11, 15, 0))
    _pedido(
        db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "99.00",
        datetime(2026, 11, 10, 15, 0), restaurant_id=outro_restaurante.id,
    )
    return entregue, retirado, cancelado


def test_movimentos_do_dia_trazem_so_entregues_retirados_e_cancelados(
    client, caixa_headers, dia_com_movimentos
):
    entregue, retirado, cancelado = dia_com_movimentos

    resposta = client.get("/caixa/movimentos", params={"data": DIA}, headers=caixa_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["data"] == DIA
    assert corpo["total"] == 3
    assert [item["status"] for item in corpo["items"]] == ["CANCELADO", "RETIRADO", "ENTREGUE"]
    assert [item["conta_no_caixa"] for item in corpo["items"]] == [False, True, True]
    assert [item["pedido_id"] for item in corpo["items"]] == [
        str(cancelado.id), str(retirado.id), str(entregue.id)
    ]

    item = corpo["items"][2]
    assert item["numero_pedido"] == entregue.order_number
    assert item["forma_pagamento"] == "DINHEIRO"
    assert item["tipo_atendimento"] == "ENTREGA"
    assert Decimal(item["total"]) == Decimal("30.00")
    assert item["entregador_id"] is not None
    assert item["entregador_nome"] == "Pedro Entregador"
    assert corpo["items"][1]["entregador_nome"] is None


def test_movimentos_paginam(client, caixa_headers, dia_com_movimentos):
    primeira = client.get(
        "/caixa/movimentos", params={"data": DIA, "page": 1, "page_size": 2}, headers=caixa_headers
    ).json()
    segunda = client.get(
        "/caixa/movimentos", params={"data": DIA, "page": 2, "page_size": 2}, headers=caixa_headers
    ).json()

    assert primeira["total"] == 3
    assert primeira["total_pages"] == 2
    assert len(primeira["items"]) == 2
    assert [item["status"] for item in segunda["items"]] == ["ENTREGUE"]


def test_movimentos_sem_data_usam_hoje(db, client, caixa_headers, criar_pedido_direto, forma_pagamento_pix):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "15.00", datetime(2026, 11, 20, 15, 0))

    corpo = client.get("/caixa/movimentos", headers=caixa_headers).json()

    assert corpo["data"] == str(HOJE)
    assert corpo["total"] == 1