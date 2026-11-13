import pytest

from app.model.models import OrderServiceType
from app.services import pedido_fluxo as fluxo

ENTREGA = OrderServiceType.DELIVERY
RETIRADA = OrderServiceType.PICKUP


@pytest.mark.parametrize(
    "tipo, codigo, esperado",
    [
        (ENTREGA, "CRIADO", "Aguardando confirmação"),
        (ENTREGA, "PRONTO", "Pronto, aguardando o entregador"),
        (RETIRADA, "PRONTO", "Pronto para retirada"),
        (RETIRADA, "RETIRADO", "Retirado"),
        (ENTREGA, "SAIU_PARA_ENTREGA", "Saiu para entrega"),
        (ENTREGA, "RECUSADO", "Recusado"),
    ],
)
def test_rotulo_por_tipo(tipo, codigo, esperado):
    assert fluxo.rotulo(tipo, codigo, "padrao") == esperado


def test_codigo_desconhecido_usa_o_nome_padrao():
    assert fluxo.rotulo(ENTREGA, "OUTRO", "Nome padrão") == "Nome padrão"


@pytest.mark.parametrize("tipo", [ENTREGA, RETIRADA])
def test_todo_status_do_fluxo_tem_rotulo(tipo):
    for codigo in fluxo.TODOS:
        assert fluxo.rotulo(tipo, codigo, "")


@pytest.mark.parametrize(
    "tipo, atual, esperado",
    [
        (ENTREGA, "CRIADO", ["aceitar", "recusar"]),
        (ENTREGA, "PRONTO", ["enviar", "cancelar"]),
        (RETIRADA, "PRONTO", ["retirado", "cancelar"]),
        (ENTREGA, "ENTREGUE", []),
    ],
)
def test_acoes_disponiveis(tipo, atual, esperado):
    assert fluxo.acoes_disponiveis(tipo, atual) == esperado


@pytest.mark.parametrize("tipo", [ENTREGA, RETIRADA])
def test_toda_transicao_possivel_tem_acao(tipo):
    for atual in fluxo.TODOS:
        for novo in fluxo.transicoes_permitidas(tipo, atual):
            assert novo in fluxo.ACAO_POR_STATUS