from datetime import datetime, timezone
from decimal import Decimal

from app.services import painel_resumo_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)


def test_conta_so_pedidos_faturaveis_dentro_da_janela(db, restaurante, pedido_em):
    pedido_em("CRIADO", datetime(2026, 11, 14, 14, 0), "20.00")
    pedido_em("ENTREGUE", datetime(2026, 11, 14, 15, 0), "30.00")
    pedido_em("CANCELADO", datetime(2026, 11, 14, 14, 0), "100.00")
    pedido_em("RECUSADO", datetime(2026, 11, 14, 14, 0), "100.00")
    pedido_em("CRIADO", datetime(2026, 11, 14, 2, 59), "40.00")
    pedido_em("CRIADO", datetime(2026, 11, 14, 19, 0), "60.00")

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.pedidos == 2
    assert resumo.atual.vendas == Decimal("50.00")
    assert resumo.atual.ticket_medio == Decimal("25.00")
    assert resumo.anterior.pedidos == 0


def test_isola_por_restaurante(db, restaurante, outro_restaurante, pedido_em):
    pedido_em(
        "CRIADO", datetime(2026, 11, 14, 14, 0), "80.00", restaurant_id=outro_restaurante.id
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
    db, restaurante, pedido_em, registrar_mudanca
):
    a = pedido_em("ENTREGUE", datetime(2026, 11, 14, 14, 0), "10.00")
    b = pedido_em("ENTREGUE", datetime(2026, 11, 14, 15, 0), "10.00")
    c = pedido_em("ENTREGUE", datetime(2026, 11, 14, 18, 0), "10.00")
    registrar_mudanca(a, "ENTREGUE", datetime(2026, 11, 14, 14, 30))
    registrar_mudanca(b, "ENTREGUE", datetime(2026, 11, 14, 15, 50))
    registrar_mudanca(c, "ENTREGUE", datetime(2026, 11, 14, 19, 0))

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.atual.entrega_media_min == 40


def test_compara_com_o_mesmo_dia_da_semana_passada_ate_a_mesma_hora(
    db, restaurante, pedido_em
):
    pedido_em("CRIADO", datetime(2026, 11, 14, 14, 0), "20.00")
    pedido_em("CRIADO", datetime(2026, 11, 14, 15, 0), "30.00")
    pedido_em("CRIADO", datetime(2026, 11, 7, 14, 0), "40.00")
    pedido_em("CRIADO", datetime(2026, 11, 7, 19, 0), "100.00")

    resumo = service.resumo_do_dia(db, restaurante.id, AGORA)

    assert resumo.rotulo_comparacao == "sábado passado"
    assert resumo.anterior.pedidos == 1
    assert resumo.anterior.vendas == Decimal("40.00")
    assert resumo.variacao_vendas_pct == Decimal("25.0")
    assert resumo.diferenca_pedidos == 1
    assert resumo.diferenca_ticket_medio == Decimal("-15.00")