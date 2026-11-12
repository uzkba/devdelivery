import pytest

from app.model.models import OrderServiceType, OrderStatus
from app.services import pedido_fluxo as fluxo

ENTREGA = OrderServiceType.DELIVERY
RETIRADA = OrderServiceType.PICKUP


@pytest.mark.parametrize(
    "tipo, atual, esperado",
    [
        (ENTREGA, "CRIADO", ["CONFIRMADO", "RECUSADO"]),
        (ENTREGA, "CONFIRMADO", ["EM_PREPARO", "CANCELADO"]),
        (ENTREGA, "EM_PREPARO", ["PRONTO", "CANCELADO"]),
        (ENTREGA, "PRONTO", ["SAIU_PARA_ENTREGA", "CANCELADO"]),
        (ENTREGA, "SAIU_PARA_ENTREGA", ["ENTREGUE", "CANCELADO"]),
        (RETIRADA, "CRIADO", ["CONFIRMADO", "RECUSADO"]),
        (RETIRADA, "PRONTO", ["RETIRADO", "CANCELADO"]),
    ],
)
def test_transicoes_permitidas(tipo, atual, esperado):
    assert fluxo.transicoes_permitidas(tipo, atual) == esperado


@pytest.mark.parametrize("final", sorted(fluxo.FINAIS))
@pytest.mark.parametrize("tipo", [ENTREGA, RETIRADA])
def test_status_final_nao_tem_saida(tipo, final):
    assert fluxo.transicoes_permitidas(tipo, final) == []


def test_retirada_nunca_passa_por_saiu_para_entrega():
    for atual in fluxo.FLUXO_RETIRADA:
        assert "SAIU_PARA_ENTREGA" not in fluxo.transicoes_permitidas(RETIRADA, atual)
        assert "ENTREGUE" not in fluxo.transicoes_permitidas(RETIRADA, atual)


def test_entrega_nunca_vai_para_retirado():
    for atual in fluxo.FLUXO_ENTREGA:
        assert "RETIRADO" not in fluxo.transicoes_permitidas(ENTREGA, atual)


def test_nao_pula_etapa_nem_volta():
    assert not fluxo.pode_transitar(ENTREGA, "CONFIRMADO", "PRONTO")
    assert not fluxo.pode_transitar(ENTREGA, "EM_PREPARO", "CONFIRMADO")
    assert not fluxo.pode_transitar(ENTREGA, "CRIADO", "CANCELADO")
    assert not fluxo.pode_transitar(ENTREGA, "CONFIRMADO", "RECUSADO")


def test_codigo_desconhecido_nao_transita():
    assert fluxo.transicoes_permitidas(ENTREGA, "INEXISTENTE") == []
    assert not fluxo.pode_transitar(ENTREGA, "CRIADO", "INEXISTENTE")


def test_status_do_fluxo_existem_no_banco(db):
    por_codigo = {s.code: s for s in db.query(OrderStatus).all()}
    assert fluxo.TODOS <= por_codigo.keys()
    assert fluxo.FINAIS <= {c for c, s in por_codigo.items() if s.is_final}
    assert not {c for c in fluxo.TODOS - fluxo.FINAIS if por_codigo[c].is_final}


def test_ordem_dos_status_segue_o_fluxo(db):
    por_codigo = {s.code: s.order for s in db.query(OrderStatus).all()}
    for sequencia in (fluxo.FLUXO_ENTREGA, fluxo.FLUXO_RETIRADA):
        ordens = [por_codigo[c] for c in sequencia]
        assert ordens == sorted(ordens)
    assert por_codigo["CRIADO"] == min(por_codigo.values())


def test_retirado_conta_como_pago_igual_ao_entregue(db):
    por_codigo = {s.code: s for s in db.query(OrderStatus).all()}
    assert por_codigo["RETIRADO"].is_paid == por_codigo["ENTREGUE"].is_paid