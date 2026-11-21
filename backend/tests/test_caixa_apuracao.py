from datetime import date, datetime
from decimal import Decimal

from app.model.models import OrderStatus
from app.services import caixa_apuracao_service as apuracao_service

DIA = date(2026, 11, 10)
MEIO_DIA_LOCAL = datetime(2026, 11, 10, 15, 0)


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def test_dia_sem_pedidos_devolve_zeros_e_todas_as_formas(db, restaurante):
    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.dia == DIA
    assert resultado.quantidade_pedidos == 0
    assert resultado.quantidade_cancelados == 0
    assert resultado.total_vendas == Decimal("0")
    assert resultado.total_dinheiro_recebido == Decimal("0")
    assert resultado.total_troco == Decimal("0")
    assert set(resultado.por_forma) == {"DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO", "OUTROS"}
    assert all(item.quantidade == 0 and item.total == Decimal("0") for item in resultado.por_forma.values())


def test_conta_so_entregues_e_retirados(db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix):
    criar_pedido_direto(_status(db, "ENTREGUE"), forma_pagamento_dinheiro, Decimal("30.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "RETIRADO"), forma_pagamento_pix, Decimal("20.00"), MEIO_DIA_LOCAL)
    for codigo in ("CRIADO", "CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA"):
        criar_pedido_direto(_status(db, codigo), forma_pagamento_dinheiro, Decimal("99.00"), MEIO_DIA_LOCAL)

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.quantidade_pedidos == 2
    assert resultado.total_vendas == Decimal("50.00")


def test_cancelados_ficam_fora_do_total_e_recusados_nao_contam(db, restaurante, criar_pedido_direto, forma_pagamento_pix):
    criar_pedido_direto(_status(db, "ENTREGUE"), forma_pagamento_pix, Decimal("25.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "CANCELADO"), forma_pagamento_pix, Decimal("40.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "CANCELADO"), forma_pagamento_pix, Decimal("15.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "RECUSADO"), forma_pagamento_pix, Decimal("60.00"), MEIO_DIA_LOCAL)

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.quantidade_pedidos == 1
    assert resultado.quantidade_cancelados == 2
    assert resultado.total_vendas == Decimal("25.00")


def test_separa_totais_por_forma_de_pagamento(
    db,
    restaurante,
    criar_pedido_direto,
    forma_pagamento_dinheiro,
    forma_pagamento_pix,
    forma_pagamento_debito,
    forma_pagamento_credito,
):
    entregue = _status(db, "ENTREGUE")
    criar_pedido_direto(entregue, forma_pagamento_dinheiro, Decimal("30.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(entregue, forma_pagamento_dinheiro, Decimal("10.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("20.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(entregue, forma_pagamento_debito, Decimal("15.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(_status(db, "RETIRADO"), forma_pagamento_credito, Decimal("5.00"), MEIO_DIA_LOCAL)

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)
    por_forma = resultado.por_forma

    assert (por_forma["DINHEIRO"].quantidade, por_forma["DINHEIRO"].total) == (2, Decimal("40.00"))
    assert (por_forma["PIX"].quantidade, por_forma["PIX"].total) == (1, Decimal("20.00"))
    assert (por_forma["CARTAO_DEBITO"].quantidade, por_forma["CARTAO_DEBITO"].total) == (1, Decimal("15.00"))
    assert (por_forma["CARTAO_CREDITO"].quantidade, por_forma["CARTAO_CREDITO"].total) == (1, Decimal("5.00"))
    assert por_forma["OUTROS"].quantidade == 0
    assert resultado.total_vendas == Decimal("80.00")


def test_dinheiro_recebido_e_troco_so_valem_para_forma_dinheiro(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, forma_pagamento_pix
):
    entregue = _status(db, "ENTREGUE")
    criar_pedido_direto(
        entregue,
        forma_pagamento_dinheiro,
        Decimal("30.00"),
        MEIO_DIA_LOCAL,
        cash_paid_amount=Decimal("50.00"),
        change_amount=Decimal("20.00"),
    )
    criar_pedido_direto(
        entregue,
        forma_pagamento_pix,
        Decimal("40.00"),
        MEIO_DIA_LOCAL,
        cash_paid_amount=Decimal("100.00"),
        change_amount=Decimal("60.00"),
    )

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.total_dinheiro_recebido == Decimal("50.00")
    assert resultado.total_troco == Decimal("20.00")


def test_dia_e_o_dia_local_e_nao_o_dia_utc(db, restaurante, criar_pedido_direto, forma_pagamento_pix):
    entregue = _status(db, "ENTREGUE")
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("10.00"), datetime(2026, 11, 10, 3, 0))
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("20.00"), datetime(2026, 11, 11, 1, 30))
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("100.00"), datetime(2026, 11, 10, 2, 30))
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("200.00"), datetime(2026, 11, 11, 3, 0))

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.quantidade_pedidos == 2
    assert resultado.total_vendas == Decimal("30.00")


def test_ignora_pedidos_de_outro_restaurante(db, restaurante, outro_restaurante, criar_pedido_direto, forma_pagamento_pix):
    entregue = _status(db, "ENTREGUE")
    criar_pedido_direto(entregue, forma_pagamento_pix, Decimal("10.00"), MEIO_DIA_LOCAL)
    criar_pedido_direto(
        entregue, forma_pagamento_pix, Decimal("500.00"), MEIO_DIA_LOCAL, restaurant_id=outro_restaurante.id
    )

    resultado = apuracao_service.apurar_dia(db, restaurante.id, DIA)

    assert resultado.quantidade_pedidos == 1
    assert resultado.total_vendas == Decimal("10.00")