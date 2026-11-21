from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.model.models import CashClosing, CashDay, OrderStatus
from app.services import caixa_fechamento_service as fechamento_service

DIA = date(2026, 11, 10)
MEIO_DIA_LOCAL = datetime(2026, 11, 10, 15, 0)
CONTAGEM_CERTA = {"DINHEIRO": Decimal("30.00"), "PIX": Decimal("20.00")}


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _abrir(db, restaurante, usuario, dia=DIA):
    caixa = CashDay(restaurant_id=restaurante.id, business_date=dia, opened_by=usuario.id)
    db.add(caixa)
    db.flush()
    db.refresh(caixa)
    return caixa


@pytest.fixture()
def caixa_com_vendas(
    db, restaurante, admin_user, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    criar_pedido_direto(_status(db, "ENTREGUE"), forma_pagamento_dinheiro, Decimal("30.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "RETIRADO"), forma_pagamento_pix, Decimal("20.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "CANCELADO"), forma_pagamento_pix, Decimal("40.00"), MEIO_DIA_LOCAL)
    return _abrir(db, restaurante, admin_user)


def _fechar(db, restaurante, usuario, contagem, observacoes=None, dia=DIA):
    return fechamento_service.fechar_caixa(db, restaurante.id, dia, contagem, observacoes, usuario.id)


def _quantidade_de_fechamentos(db, restaurante):
    return db.query(CashClosing).filter_by(restaurant_id=restaurante.id).count()


def test_fecha_sem_diferenca_e_grava_tudo(db, restaurante, admin_user, caixa_com_vendas):
    fechamento = _fechar(db, restaurante, admin_user, CONTAGEM_CERTA)

    assert fechamento.start_date == DIA
    assert fechamento.end_date == DIA
    assert fechamento.total_sales == Decimal("50.00")
    assert fechamento.total_cash == Decimal("30.00")
    assert fechamento.total_pix == Decimal("20.00")
    assert fechamento.order_count == 2
    assert fechamento.cancelled_count == 1
    assert fechamento.expected_amount == Decimal("50.00")
    assert fechamento.reported_amount == Decimal("50.00")
    assert fechamento.difference == Decimal("0.00")
    assert fechamento.closed_by == admin_user.id
    assert fechamento.notes is None

    formas = {forma.method_code: forma for forma in fechamento_service.formas_do_fechamento(db, fechamento.id)}
    assert list(formas) == ["DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO"]
    assert formas["DINHEIRO"].expected_amount == Decimal("30.00")
    assert formas["DINHEIRO"].counted_amount == Decimal("30.00")
    assert formas["DINHEIRO"].difference == Decimal("0.00")
    assert formas["CARTAO_DEBITO"].order_count == 0

    db.refresh(caixa_com_vendas)
    assert caixa_com_vendas.status == "FECHADO"
    assert caixa_com_vendas.closing_id == fechamento.id
    assert caixa_com_vendas.closed_by == admin_user.id
    assert caixa_com_vendas.closed_at is not None


def test_dia_sem_vendas_fecha_com_contagem_vazia(db, restaurante, admin_user):
    _abrir(db, restaurante, admin_user)

    fechamento = _fechar(db, restaurante, admin_user, {})

    assert fechamento.total_sales == Decimal("0.00")
    assert fechamento.order_count == 0
    assert fechamento.difference == Decimal("0.00")


def test_diferenca_com_observacao_e_gravada_por_forma(db, restaurante, admin_user, caixa_com_vendas):
    contagem = {"DINHEIRO": Decimal("25.00"), "PIX": Decimal("20.00")}

    fechamento = _fechar(db, restaurante, admin_user, contagem, "  Faltou troco do entregador  ")

    formas = {forma.method_code: forma for forma in fechamento_service.formas_do_fechamento(db, fechamento.id)}
    assert formas["DINHEIRO"].difference == Decimal("-5.00")
    assert formas["PIX"].difference == Decimal("0.00")
    assert fechamento.reported_amount == Decimal("45.00")
    assert fechamento.difference == Decimal("-5.00")
    assert fechamento.notes == "Faltou troco do entregador"


def test_diferenca_para_mais_tambem_exige_observacao(db, restaurante, admin_user, caixa_com_vendas):
    contagem = {"DINHEIRO": Decimal("30.00"), "PIX": Decimal("20.00"), "CARTAO_CREDITO": Decimal("10.00")}

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, contagem)

    assert erro.value.status_code == 422


@pytest.mark.parametrize("observacao", [None, "", "   ", "ab"])
def test_diferenca_sem_observacao_valida_e_recusada(db, restaurante, admin_user, caixa_com_vendas, observacao):
    contagem = {"DINHEIRO": Decimal("25.00"), "PIX": Decimal("20.00")}

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, contagem, observacao)

    assert erro.value.status_code == 422
    assert "observação" in erro.value.detail
    assert _quantidade_de_fechamentos(db, restaurante) == 0
    assert caixa_com_vendas.status == "ABERTO"


def test_observacao_longa_demais_e_recusada(db, restaurante, admin_user, caixa_com_vendas):
    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, "x" * 501)

    assert erro.value.status_code == 422


def test_forma_com_venda_sem_contagem_e_recusada(db, restaurante, admin_user, caixa_com_vendas):
    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, {"DINHEIRO": Decimal("30.00")})

    assert erro.value.status_code == 422
    assert "PIX" in erro.value.detail
    assert _quantidade_de_fechamentos(db, restaurante) == 0


@pytest.mark.parametrize(
    "contagem",
    [
        {"DINHEIRO": Decimal("30.00"), "PIX": Decimal("20.00"), "VALE": Decimal("1.00")},
        {"DINHEIRO": Decimal("-1.00"), "PIX": Decimal("20.00")},
        {"DINHEIRO": Decimal("30.005"), "PIX": Decimal("20.00")},
    ],
)
def test_contagem_invalida_e_recusada(db, restaurante, admin_user, caixa_com_vendas, contagem):
    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, contagem, "observação")

    assert erro.value.status_code == 422
    assert _quantidade_de_fechamentos(db, restaurante) == 0


def test_pedido_em_aberto_bloqueia_o_fechamento(
    db, restaurante, admin_user, caixa_com_vendas, criar_pedido_direto, forma_pagamento_pix
):
    criar_pedido_direto(_status(db, "CONFIRMADO"), forma_pagamento_pix, Decimal("12.00"), MEIO_DIA_LOCAL)

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA)

    assert erro.value.status_code == 422
    assert "em aberto" in erro.value.detail
    assert caixa_com_vendas.status == "ABERTO"


def test_sem_caixa_aberto_devolve_conflito(db, restaurante, admin_user):
    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, {})

    assert erro.value.status_code == 409


def test_nao_fecha_duas_vezes(db, restaurante, admin_user, caixa_com_vendas):
    _fechar(db, restaurante, admin_user, CONTAGEM_CERTA)

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA)

    assert erro.value.status_code == 409
    assert _quantidade_de_fechamentos(db, restaurante) == 1


def test_fechamento_legado_do_mesmo_dia_devolve_conflito(db, restaurante, admin_user, caixa_com_vendas):
    db.add(CashClosing(restaurant_id=restaurante.id, start_date=DIA, end_date=DIA, closed_by=admin_user.id))
    db.flush()

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA)

    assert erro.value.status_code == 409
    assert caixa_com_vendas.status == "ABERTO"
    assert caixa_com_vendas.closing_id is None