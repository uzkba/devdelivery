import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.seguranca import hash_password
from app.model.models import AdminUser, CashClosing, CashClosingDriver, CashDay, OrderStatus
from app.services import caixa_acerto_service as acerto_service
from app.services import caixa_fechamento_service as fechamento_service

DIA = date(2026, 11, 10)
MEIO_DIA_LOCAL = datetime(2026, 11, 10, 15, 0)
DIA_SEGUINTE_LOCAL = datetime(2026, 11, 11, 15, 0)
CONTAGEM_CERTA = {"DINHEIRO": Decimal("80.00"), "PIX": Decimal("20.00")}
CONTAGEM_COM_FALTA = {"DINHEIRO": Decimal("78.00"), "PIX": Decimal("20.00")}


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _pedido(db, criar_pedido_direto, codigo, forma, total, momento=MEIO_DIA_LOCAL, **extra):
    return criar_pedido_direto(_status(db, codigo), forma, Decimal(total), momento, **extra)


def _abrir(db, restaurante, usuario, dia=DIA):
    caixa = CashDay(restaurant_id=restaurante.id, business_date=dia, opened_by=usuario.id)
    db.add(caixa)
    db.flush()
    db.refresh(caixa)
    return caixa


def _contagens(db):
    return db.query(CashClosing).count(), db.query(CashClosingDriver).count()


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


@pytest.fixture()
def dia_com_dois_entregadores(
    db,
    restaurante,
    admin_user,
    entregador_user,
    lucas,
    criar_pedido_direto,
    forma_pagamento_dinheiro,
    forma_pagamento_pix,
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", driver_id=entregador_user.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "20.00", driver_id=entregador_user.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "40.00", driver_id=lucas.id)
    _pedido(db, criar_pedido_direto, "RETIRADO", forma_pagamento_dinheiro, "10.00")
    return _abrir(db, restaurante, admin_user)


def _fechar(db, restaurante, usuario, contagem, observacoes=None, acertos=None):
    return fechamento_service.fechar_caixa(
        db, restaurante.id, DIA, contagem, observacoes, usuario.id, acertos
    )


def test_agrupa_entregas_por_entregador(
    db, restaurante, entregador_user, lucas, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    pedro = entregador_user
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "30.00", driver_id=pedro.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "20.00", driver_id=pedro.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "15.00", driver_id=pedro.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "10.00", driver_id=lucas.id)
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "99.00")
    _pedido(db, criar_pedido_direto, "RETIRADO", forma_pagamento_dinheiro, "99.00")
    _pedido(db, criar_pedido_direto, "SAIU_PARA_ENTREGA", forma_pagamento_dinheiro, "99.00", driver_id=pedro.id)
    _pedido(db, criar_pedido_direto, "CANCELADO", forma_pagamento_dinheiro, "99.00", driver_id=pedro.id)
    _pedido(
        db, criar_pedido_direto, "ENTREGUE", forma_pagamento_dinheiro, "99.00", DIA_SEGUINTE_LOCAL, driver_id=pedro.id
    )

    resultado = acerto_service.apurar_entregadores(db, restaurante.id, DIA)

    assert [acerto.nome for acerto in resultado] == ["Lucas Entregador", "Pedro Entregador"]
    acerto_lucas, acerto_pedro = resultado
    assert acerto_lucas.driver_id == lucas.id
    assert acerto_lucas.quantidade_entregas == 1
    assert acerto_lucas.quantidade_dinheiro == 0
    assert acerto_lucas.esperado_dinheiro == Decimal("0")
    assert acerto_pedro.driver_id == pedro.id
    assert acerto_pedro.quantidade_entregas == 3
    assert acerto_pedro.quantidade_dinheiro == 2
    assert acerto_pedro.esperado_dinheiro == Decimal("50.00")


def test_dia_sem_entregas_devolve_lista_vazia(db, restaurante):
    assert acerto_service.apurar_entregadores(db, restaurante.id, DIA) == []


def test_ignora_entregas_de_outro_restaurante(
    db, restaurante, outro_restaurante, entregador_user, criar_pedido_direto, forma_pagamento_dinheiro
):
    _pedido(
        db,
        criar_pedido_direto,
        "ENTREGUE",
        forma_pagamento_dinheiro,
        "99.00",
        driver_id=entregador_user.id,
        restaurant_id=outro_restaurante.id,
    )

    assert acerto_service.apurar_entregadores(db, restaurante.id, DIA) == []


def test_fecha_caixa_com_dois_entregadores_e_uma_diferenca(
    db, restaurante, admin_user, entregador_user, lucas, dia_com_dois_entregadores
):
    acertos = {entregador_user.id: Decimal("30.00"), lucas.id: Decimal("38.00")}

    fechamento = _fechar(
        db, restaurante, admin_user, CONTAGEM_COM_FALTA, "Lucas repassou 2 reais a menos", acertos
    )

    assert fechamento.total_sales == Decimal("100.00")
    assert fechamento.expected_amount == Decimal("100.00")
    assert fechamento.reported_amount == Decimal("98.00")
    assert fechamento.difference == Decimal("-2.00")
    assert fechamento.notes == "Lucas repassou 2 reais a menos"

    formas = {forma.method_code: forma for forma in fechamento_service.formas_do_fechamento(db, fechamento.id)}
    assert formas["DINHEIRO"].expected_amount == Decimal("80.00")
    assert formas["DINHEIRO"].counted_amount == Decimal("78.00")
    assert formas["DINHEIRO"].difference == Decimal("-2.00")
    assert formas["PIX"].difference == Decimal("0.00")

    linhas = fechamento_service.entregadores_do_fechamento(db, fechamento.id)
    assert [linha.driver_name for linha in linhas] == ["Lucas Entregador", "Pedro Entregador"]
    linha_lucas, linha_pedro = linhas
    assert linha_lucas.driver_id == lucas.id
    assert linha_lucas.delivery_count == 1
    assert linha_lucas.expected_amount == Decimal("40.00")
    assert linha_lucas.handed_amount == Decimal("38.00")
    assert linha_lucas.difference == Decimal("-2.00")
    assert linha_pedro.driver_id == entregador_user.id
    assert linha_pedro.delivery_count == 2
    assert linha_pedro.expected_amount == Decimal("30.00")
    assert linha_pedro.handed_amount == Decimal("30.00")
    assert linha_pedro.difference == Decimal("0.00")

    db.refresh(dia_com_dois_entregadores)
    assert dia_com_dois_entregadores.status == "FECHADO"
    assert dia_com_dois_entregadores.closing_id == fechamento.id


def test_acerto_sem_diferenca_nao_exige_observacao(
    db, restaurante, admin_user, entregador_user, lucas, dia_com_dois_entregadores
):
    acertos = {entregador_user.id: Decimal("30.00"), lucas.id: Decimal("40.00")}

    fechamento = _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, None, acertos)

    assert fechamento.difference == Decimal("0.00")
    assert all(
        linha.difference == Decimal("0.00")
        for linha in fechamento_service.entregadores_do_fechamento(db, fechamento.id)
    )


def test_diferenca_so_no_acerto_exige_observacao(
    db, restaurante, admin_user, entregador_user, lucas, dia_com_dois_entregadores
):
    acertos = {entregador_user.id: Decimal("30.00"), lucas.id: Decimal("38.00")}

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, None, acertos)

    assert erro.value.status_code == 422
    assert "observação" in erro.value.detail
    assert _contagens(db) == (0, 0)
    assert dia_com_dois_entregadores.status == "ABERTO"

    fechamento = _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, "Lucas ficou com 2 reais", acertos)

    assert fechamento.difference == Decimal("0.00")
    diferencas = [
        linha.difference for linha in fechamento_service.entregadores_do_fechamento(db, fechamento.id)
    ]
    assert diferencas == [Decimal("-2.00"), Decimal("0.00")]


def test_entregador_com_dinheiro_exige_repasse_informado(
    db, restaurante, admin_user, entregador_user, dia_com_dois_entregadores
):
    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, None, {entregador_user.id: Decimal("30.00")})

    assert erro.value.status_code == 422
    assert "Lucas" in erro.value.detail
    assert _contagens(db) == (0, 0)


def test_entregador_so_com_pix_nao_precisa_de_acerto(
    db, restaurante, admin_user, entregador_user, criar_pedido_direto, forma_pagamento_pix
):
    _pedido(db, criar_pedido_direto, "ENTREGUE", forma_pagamento_pix, "25.00", driver_id=entregador_user.id)
    _abrir(db, restaurante, admin_user)

    fechamento = _fechar(db, restaurante, admin_user, {"PIX": Decimal("25.00")})

    linhas = fechamento_service.entregadores_do_fechamento(db, fechamento.id)
    assert len(linhas) == 1
    assert linhas[0].driver_id == entregador_user.id
    assert linhas[0].delivery_count == 1
    assert linhas[0].expected_amount == Decimal("0.00")
    assert linhas[0].handed_amount == Decimal("0.00")
    assert linhas[0].difference == Decimal("0.00")


def test_dia_sem_entregas_fecha_sem_linhas_de_entregador(db, restaurante, admin_user):
    _abrir(db, restaurante, admin_user)

    fechamento = _fechar(db, restaurante, admin_user, {})

    assert fechamento_service.entregadores_do_fechamento(db, fechamento.id) == []


def test_acerto_de_entregador_sem_entregas_no_dia_e_recusado(
    db, restaurante, admin_user, entregador_user, lucas, dia_com_dois_entregadores
):
    acertos = {
        entregador_user.id: Decimal("30.00"),
        lucas.id: Decimal("40.00"),
        uuid.uuid4(): Decimal("5.00"),
    }

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, "observação", acertos)

    assert erro.value.status_code == 422
    assert _contagens(db) == (0, 0)


@pytest.mark.parametrize("valor", [Decimal("-1.00"), Decimal("30.005")])
def test_repasse_invalido_e_recusado(
    db, restaurante, admin_user, entregador_user, lucas, dia_com_dois_entregadores, valor
):
    acertos = {entregador_user.id: valor, lucas.id: Decimal("40.00")}

    with pytest.raises(HTTPException) as erro:
        _fechar(db, restaurante, admin_user, CONTAGEM_CERTA, "observação", acertos)

    assert erro.value.status_code == 422
    assert _contagens(db) == (0, 0)