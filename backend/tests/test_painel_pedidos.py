from datetime import datetime, timezone
from decimal import Decimal

from app.model.models import OrderServiceType
from app.services import painel_pedidos_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)


def test_fila_conta_etapas_e_entregues_do_dia(
    db, restaurante, outro_restaurante, pedido_em, registrar_mudanca
):
    hoje = datetime(2026, 11, 14, 12, 0)
    for codigo in ("CRIADO", "CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA"):
        pedido_em(codigo, hoje)
    pedido_em("CRIADO", datetime(2026, 11, 13, 12, 0))

    entregue = pedido_em("ENTREGUE", hoje)
    retirado = pedido_em("RETIRADO", hoje)
    no_limite = pedido_em("ENTREGUE", hoje)
    de_ontem = pedido_em("ENTREGUE", hoje)
    registrar_mudanca(entregue, "ENTREGUE", datetime(2026, 11, 14, 15, 0))
    registrar_mudanca(retirado, "RETIRADO", datetime(2026, 11, 14, 16, 0))
    registrar_mudanca(no_limite, "ENTREGUE", datetime(2026, 11, 14, 3, 0))
    registrar_mudanca(de_ontem, "ENTREGUE", datetime(2026, 11, 14, 2, 59))

    pedido_em("CANCELADO", hoje)
    pedido_em("RECUSADO", hoje)
    pedido_em("CRIADO", hoje, restaurant_id=outro_restaurante.id)

    fila = service.fila_do_dia(db, restaurante.id, AGORA)

    assert fila.novos == 2
    assert fila.preparo == 3
    assert fila.saindo == 1
    assert fila.entregues == 3


def test_espera_mais_antiga_considera_so_pedidos_novos(db, restaurante, pedido_em):
    pedido_em("CRIADO", datetime(2026, 11, 14, 18, 20))
    pedido_em("CRIADO", datetime(2026, 11, 14, 18, 0))
    pedido_em("CONFIRMADO", datetime(2026, 11, 14, 17, 0))

    assert service.fila_do_dia(db, restaurante.id, AGORA).espera_mais_antiga_min == 30


def test_fila_vazia(db, restaurante):
    fila = service.fila_do_dia(db, restaurante.id, AGORA)

    assert (fila.novos, fila.preparo, fila.saindo, fila.entregues) == (0, 0, 0, 0)
    assert fila.espera_mais_antiga_min is None


def test_cartao_de_pedido_de_entrega(db, restaurante, pedido_em, adicionar_item):
    pedido = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 25))
    adicionar_item(pedido, "Suco", 1, "8.00")
    adicionar_item(pedido, "Marmita", 2, "20.00")

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.pedido_id == pedido.id
    assert cartao.numero_pedido == pedido.order_number
    assert cartao.cliente_nome == "José da Silva"
    assert cartao.etapa == "novos"
    assert cartao.status == "CRIADO"
    assert cartao.status_rotulo == "Aguardando confirmação"
    assert cartao.tipo_atendimento == OrderServiceType.DELIVERY
    assert cartao.itens_resumo == "2x Marmita, 1x Suco"
    assert cartao.bairro == "Centro"
    assert cartao.minutos == 5
    assert cartao.atrasado is False
    assert cartao.valor_total == Decimal("20.00")
    assert cartao.acoes_disponiveis == ["aceitar", "recusar"]


def test_cartao_de_pedido_de_retirada(db, restaurante, pedido_em):
    pedido_em(
        "PRONTO",
        datetime(2026, 11, 14, 18, 0),
        service_type=OrderServiceType.PICKUP,
        address_street=None,
        address_number=None,
        address_neighborhood=None,
    )

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.etapa == "preparo"
    assert cartao.bairro is None
    assert cartao.status_rotulo == "Pronto para retirada"
    assert cartao.acoes_disponiveis == ["retirado", "cancelar"]
    assert cartao.itens_resumo == ""


def test_etapa_saindo(db, restaurante, pedido_em):
    pedido_em("SAIU_PARA_ENTREGA", datetime(2026, 11, 14, 18, 0))

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.etapa == "saindo"
    assert cartao.acoes_disponiveis == ["entregue", "cancelar"]


def test_resumo_de_itens_limita_a_tres_e_conta_o_resto(
    db, restaurante, pedido_em, adicionar_item
):
    pedido = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 25))
    for nome, preco in (("A", "50.00"), ("B", "40.00"), ("C", "30.00"), ("D", "20.00"), ("E", "10.00")):
        adicionar_item(pedido, nome, 1, preco)

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.itens_resumo == "1x A, 1x B, 1x C e mais 2"


def test_ordena_pelo_mais_antigo_e_respeita_o_limite(db, restaurante, pedido_em):
    mesma_hora = datetime(2026, 11, 14, 18, 0)
    criados = [
        pedido_em("CRIADO", datetime(2026, 11, 14, 18, 20)),
        pedido_em("EM_PREPARO", datetime(2026, 11, 14, 17, 0)),
        pedido_em("CRIADO", mesma_hora),
        pedido_em("CONFIRMADO", mesma_hora),
        pedido_em("CRIADO", datetime(2026, 11, 14, 18, 28)),
    ]

    padrao = service.em_andamento(db, restaurante.id, agora=AGORA)
    curto = service.em_andamento(db, restaurante.id, limite=2, agora=AGORA)

    esperados = [criados[1], criados[2], criados[3], criados[0]]
    assert [c.numero_pedido for c in padrao] == [p.order_number for p in esperados]
    assert [c.numero_pedido for c in curto] == [criados[1].order_number, criados[2].order_number]


def test_marca_atrasado_com_a_mesma_regra_dos_alertas(db, restaurante, pedido_em):
    parado = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 0))
    recente = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 25))

    cartoes = {c.pedido_id: c for c in service.em_andamento(db, restaurante.id, agora=AGORA)}

    assert cartoes[parado.id].atrasado is True
    assert cartoes[recente.id].atrasado is False


def test_ignora_finalizados_e_outros_restaurantes(
    db, restaurante, outro_restaurante, pedido_em
):
    antigo = datetime(2026, 11, 14, 12, 0)
    for codigo in ("ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO"):
        pedido_em(codigo, antigo)
    pedido_em("CRIADO", antigo, restaurant_id=outro_restaurante.id)

    assert service.em_andamento(db, restaurante.id, agora=AGORA) == []