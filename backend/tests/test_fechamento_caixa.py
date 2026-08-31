from datetime import datetime, date
from decimal import Decimal

from app.model.models import CashClosing


# ── helpers de payload ──────────────────────────────────────────────

def payload_fechamento(restaurante, data_inicio, data_fim, reported_amount="0.00", **overrides):
    dados = dict(
        restaurante_id=str(restaurante.id),
        data_inicio=str(data_inicio),
        data_fim=str(data_fim),
        reported_amount=reported_amount,
    )
    dados.update(overrides)
    return dados


# ── geração de fechamento ────────────────────────────────────────────

def test_gerar_fechamento_consolida_pedidos_do_periodo(
    db, client, restaurante, caixa_user, token_para,
    criar_pedido_direto, status_entregue, status_confirmado,
    forma_pagamento_dinheiro, forma_pagamento_pix, forma_pagamento_credito,
):
    dia = date(2026, 8, 20)

    # pedido em dinheiro, entregue, dentro do período
    criar_pedido_direto(
        status_entregue, forma_pagamento_dinheiro, Decimal("30.00"),
        datetime(2026, 8, 20, 12, 0),
        cash_paid_amount=Decimal("50.00"), change_amount=Decimal("20.00"),
    )
    # pedido em pix, entregue, dentro do período
    criar_pedido_direto(
        status_entregue, forma_pagamento_pix, Decimal("45.00"),
        datetime(2026, 8, 20, 19, 30),
    )
    # pedido em cartão de crédito, entregue, dentro do período
    criar_pedido_direto(
        status_entregue, forma_pagamento_credito, Decimal("25.00"),
        datetime(2026, 8, 20, 20, 0),
    )
    # pedido ainda não entregue (CONFIRMADO) — não deve entrar no fechamento
    criar_pedido_direto(
        status_confirmado, forma_pagamento_pix, Decimal("99.00"),
        datetime(2026, 8, 20, 21, 0),
    )
    # pedido entregue, mas fora do período (dia seguinte) — não deve entrar
    criar_pedido_direto(
        status_entregue, forma_pagamento_dinheiro, Decimal("15.00"),
        datetime(2026, 8, 21, 8, 0),
    )

    resp = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia, reported_amount="30.00"),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["quantidade_pedidos"] == 3
    assert corpo["total_vendas"] == "100.00"  # 30 + 45 + 25
    assert corpo["totais_por_forma_pagamento"]["DINHEIRO"] == "30.00"
    assert corpo["totais_por_forma_pagamento"]["PIX"] == "45.00"
    assert corpo["totais_por_forma_pagamento"]["CARTAO_CREDITO"] == "25.00"
    assert corpo["totais_por_forma_pagamento"]["CARTAO_DEBITO"] == "0.00"
    assert corpo["total_dinheiro_recebido"] == "50.00"
    assert corpo["total_troco"] == "20.00"
    assert corpo["valor_esperado"] == "30.00"  # só dinheiro
    assert corpo["valor_informado"] == "30.00"
    assert corpo["diferenca"] == "0.00"


def test_gerar_fechamento_pedido_cancelado_nao_entra_no_total_mas_conta_cancelados(
    db, client, restaurante, caixa_user, token_para,
    criar_pedido_direto, status_entregue, status_cancelado, forma_pagamento_pix,
):
    dia = date(2026, 8, 22)
    criar_pedido_direto(status_entregue, forma_pagamento_pix, Decimal("40.00"), datetime(2026, 8, 22, 12, 0))
    criar_pedido_direto(status_cancelado, forma_pagamento_pix, Decimal("40.00"), datetime(2026, 8, 22, 13, 0))

    resp = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["quantidade_pedidos"] == 1
    assert corpo["quantidade_cancelados"] == 1
    assert corpo["total_vendas"] == "40.00"


def test_gerar_fechamento_com_admin_tambem_permitido(
    db, client, restaurante, admin_user, token_para, criar_pedido_direto,
    status_entregue, forma_pagamento_pix,
):
    dia = date(2026, 8, 23)
    criar_pedido_direto(status_entregue, forma_pagamento_pix, Decimal("10.00"), datetime(2026, 8, 23, 12, 0))

    resp = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 201


def test_gerar_fechamento_atendente_sem_permissao_retorna_403(
    db, client, restaurante, atendente_user, token_para,
):
    dia = date(2026, 8, 24)
    resp = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(atendente_user)}"},
    )
    assert resp.status_code == 403


def test_gerar_fechamento_sem_token_retorna_401(client, restaurante):
    dia = date(2026, 8, 24)
    resp = client.post("/fechamento-caixa", json=payload_fechamento(restaurante, dia, dia))
    assert resp.status_code == 401


# ── duplicidade ───────────────────────────────────────────────────────

def test_gerar_fechamento_duplicado_mesmo_periodo_retorna_409(
    db, client, restaurante, caixa_user, token_para, criar_pedido_direto,
    status_entregue, forma_pagamento_pix,
):
    dia = date(2026, 8, 25)
    criar_pedido_direto(status_entregue, forma_pagamento_pix, Decimal("10.00"), datetime(2026, 8, 25, 12, 0))

    primeiro = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert primeiro.status_code == 201

    segundo = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert segundo.status_code == 409


def test_gerar_fechamento_periodos_diferentes_nao_conflitam(
    db, client, restaurante, caixa_user, token_para, criar_pedido_direto,
    status_entregue, forma_pagamento_pix,
):
    """Fechamento diário de um dia e um fechamento semanal que cobre o mesmo dia devem coexistir
    (regra de duplicidade é só start_date+end_date exatamente iguais)."""
    criar_pedido_direto(status_entregue, forma_pagamento_pix, Decimal("10.00"), datetime(2026, 8, 18, 12, 0))

    diario = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, date(2026, 8, 18), date(2026, 8, 18)),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert diario.status_code == 201

    semanal = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, date(2026, 8, 17), date(2026, 8, 23)),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert semanal.status_code == 201


# ── período sem pedidos ──────────────────────────────────────────────

def test_gerar_fechamento_periodo_sem_pedidos_retorna_zerado(
    db, client, restaurante, caixa_user, token_para,
):
    dia = date(2026, 8, 26)
    resp = client.post(
        "/fechamento-caixa",
        json=payload_fechamento(restaurante, dia, dia),
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["quantidade_pedidos"] == 0
    assert corpo["quantidade_cancelados"] == 0
    assert corpo["total_vendas"] == "0.00"
    assert corpo["valor_esperado"] == "0.00"
    assert all(v == "0.00" for v in corpo["totais_por_forma_pagamento"].values())


# ── consulta ─────────────────────────────────────────────────────────

def test_listar_fechamentos_retorna_apenas_do_restaurante_autenticado(
    db, client, restaurante, outro_restaurante, caixa_user, outro_admin_user, token_para,
):
    fechamento_do_restaurante = CashClosing(
        restaurant_id=restaurante.id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 10),
        closed_by=caixa_user.id,
    )
    fechamento_do_outro = CashClosing(
        restaurant_id=outro_restaurante.id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 10),
        closed_by=outro_admin_user.id,
    )
    db.add_all([fechamento_do_restaurante, fechamento_do_outro])
    db.flush()

    resp = client.get(
        "/fechamento-caixa",
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    assert corpo["items"][0]["restaurante_id"] == str(restaurante.id)


def test_buscar_fechamento_por_id_de_outro_restaurante_retorna_404(
    db, client, outro_restaurante, outro_admin_user, caixa_user, token_para,
):
    fechamento_alheio = CashClosing(
        restaurant_id=outro_restaurante.id, start_date=date(2026, 8, 11), end_date=date(2026, 8, 11),
        closed_by=outro_admin_user.id,
    )
    db.add(fechamento_alheio)
    db.flush()
    db.refresh(fechamento_alheio)

    resp = client.get(
        f"/fechamento-caixa/{fechamento_alheio.id}",
        headers={"Authorization": f"Bearer {token_para(caixa_user)}"},
    )
    assert resp.status_code == 404