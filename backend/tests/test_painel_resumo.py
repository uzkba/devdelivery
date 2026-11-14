from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.model.models import OrderStatus, OrderStatusHistory
from app.services import painel_resumo_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)


@pytest.fixture()
def status_recusado(db):
    status = db.query(OrderStatus).filter_by(code="RECUSADO").first()
    if status is None:
        status = OrderStatus(code="RECUSADO", name="Recusado", order=7, is_final=True)
        db.add(status)
        db.flush()
    return status


def _entregue_em(db, pedido, momento, status_entregue):
    db.add(
        OrderStatusHistory(
            order_id=pedido.id, new_status_id=status_entregue.id, changed_at=momento
        )
    )
    db.flush()


def test_conta_so_pedidos_faturaveis_dentro_da_janela(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro,
    status_criado, status_entregue, status_cancelado, status_recusado,
):
    pagto = forma_pagamento_dinheiro
    criar_pedido_direto(status_criado, pagto, Decimal("20.00"), datetime(2026, 11, 14, 14, 0))
    criar_pedido_direto(status_entregue, pagto, Decimal("30.00"), datetime(2026, 11, 14, 15, 0))
    criar_pedido_direto(status_cancelado, pagto, Decimal("100.00"), datetime(2026, 11, 14, 14, 0))
    criar_pedido_direto(status_recusado, pagto, Decimal("100.00"), datetime(2026, 11, 14, 14, 0))
    criar_pedido_direto(status_criado, pagto, Decimal("40.00"), datetime(2026, 11, 14, 2, 59))
    criar_pedido_direto(status_criado, pagto, Decimal("60.00"), datetime(2026, 11, 14, 19, 0))

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.pedidos == 2
    assert resumo.atual.vendas == Decimal("50.00")
    assert resumo.atual.ticket_medio == Decimal("25.00")
    assert resumo.anterior.pedidos == 0


def test_isola_por_restaurante(
    db, restaurante, outro_restaurante, criar_pedido_direto,
    forma_pagamento_dinheiro, status_criado,
):
    criar_pedido_direto(
        status_criado, forma_pagamento_dinheiro, Decimal("80.00"),
        datetime(2026, 11, 14, 14, 0), restaurant_id=outro_restaurante.id,
    )

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.pedidos == 0
    assert resumo.atual.vendas == Decimal("0.00")


def test_sem_pedidos_zera_tudo_e_nao_inventa_variacao(db, restaurante):
    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.ticket_medio == Decimal("0.00")
    assert resumo.atual.entrega_media_min is None
    assert resumo.variacao_vendas_pct is None
    assert resumo.diferenca_entrega_min is None
    assert resumo.diferenca_pedidos == 0


def test_entrega_media_usa_historico_e_so_entregas_da_janela(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, status_entregue,
):
    pagto = forma_pagamento_dinheiro
    a = criar_pedido_direto(status_entregue, pagto, Decimal("10.00"), datetime(2026, 11, 14, 14, 0))
    b = criar_pedido_direto(status_entregue, pagto, Decimal("10.00"), datetime(2026, 11, 14, 15, 0))
    c = criar_pedido_direto(status_entregue, pagto, Decimal("10.00"), datetime(2026, 11, 14, 18, 0))
    _entregue_em(db, a, datetime(2026, 11, 14, 14, 30), status_entregue)
    _entregue_em(db, b, datetime(2026, 11, 14, 15, 50), status_entregue)
    _entregue_em(db, c, datetime(2026, 11, 14, 19, 0), status_entregue)

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.entrega_media_min == 40


def test_compara_com_o_mesmo_dia_da_semana_passada_ate_a_mesma_hora(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, status_criado,
):
    pagto = forma_pagamento_dinheiro
    criar_pedido_direto(status_criado, pagto, Decimal("20.00"), datetime(2026, 11, 14, 14, 0))
    criar_pedido_direto(status_criado, pagto, Decimal("30.00"), datetime(2026, 11, 14, 15, 0))
    criar_pedido_direto(status_criado, pagto, Decimal("40.00"), datetime(2026, 11, 7, 14, 0))
    criar_pedido_direto(status_criado, pagto, Decimal("100.00"), datetime(2026, 11, 7, 19, 0))

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.rotulo_comparacao == "sábado passado"
    assert resumo.anterior.pedidos == 1
    assert resumo.anterior.vendas == Decimal("40.00")
    assert resumo.variacao_vendas_pct == Decimal("25.0")
    assert resumo.diferenca_pedidos == 1
    assert resumo.diferenca_ticket_medio == Decimal("-15.00")