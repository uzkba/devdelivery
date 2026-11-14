from datetime import datetime, timezone
from decimal import Decimal

from app.model.models import OrderItem, OrderServiceType, OrderStatus, OrderStatusHistory
from app.services import painel_pedidos_service as service
from app.services import pedido_fluxo

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)

ORDEM = {
    codigo: posicao
    for posicao, codigo in enumerate(
        (
            "CRIADO", "CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA",
            "ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO",
        ),
        start=1,
    )
}


def _status(db, codigo):
    status = db.query(OrderStatus).filter_by(code=codigo).first()
    if status is None:
        status = OrderStatus(
            code=codigo, name=codigo, order=ORDEM[codigo], is_final=codigo in pedido_fluxo.FINAIS
        )
        db.add(status)
        db.flush()
    return status


def _pedido(db, criar_pedido_direto, pagto, codigo, criado_em, **extra):
    return criar_pedido_direto(_status(db, codigo), pagto, Decimal("20.00"), criado_em, **extra)


def _mudou_em(db, pedido, codigo, momento):
    db.add(
        OrderStatusHistory(
            order_id=pedido.id, new_status_id=_status(db, codigo).id, changed_at=momento
        )
    )
    db.flush()


def _item(db, pedido, nome, quantidade, preco):
    db.add(
        OrderItem(
            order_id=pedido.id,
            food_name=nome,
            quantity=quantidade,
            base_price=Decimal(preco),
            subtotal=Decimal(preco) * quantidade,
        )
    )
    db.flush()


def test_fila_conta_etapas_e_entregues_do_dia(
    db, restaurante, outro_restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    hoje = datetime(2026, 11, 14, 12, 0)
    for codigo in ("CRIADO", "CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA"):
        _pedido(db, criar_pedido_direto, pagto, codigo, hoje)
    _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 13, 12, 0))

    entregue = _pedido(db, criar_pedido_direto, pagto, "ENTREGUE", hoje)
    retirado = _pedido(db, criar_pedido_direto, pagto, "RETIRADO", hoje)
    no_limite = _pedido(db, criar_pedido_direto, pagto, "ENTREGUE", hoje)
    de_ontem = _pedido(db, criar_pedido_direto, pagto, "ENTREGUE", hoje)
    _mudou_em(db, entregue, "ENTREGUE", datetime(2026, 11, 14, 15, 0))
    _mudou_em(db, retirado, "RETIRADO", datetime(2026, 11, 14, 16, 0))
    _mudou_em(db, no_limite, "ENTREGUE", datetime(2026, 11, 14, 3, 0))
    _mudou_em(db, de_ontem, "ENTREGUE", datetime(2026, 11, 14, 2, 59))

    _pedido(db, criar_pedido_direto, pagto, "CANCELADO", hoje)
    _pedido(db, criar_pedido_direto, pagto, "RECUSADO", hoje)
    _pedido(
        db, criar_pedido_direto, pagto, "CRIADO", hoje, restaurant_id=outro_restaurante.id
    )

    fila = service.fila_do_dia(db, restaurante.id, AGORA)

    assert fila.novos == 2
    assert fila.preparo == 3
    assert fila.saindo == 1
    assert fila.entregues == 3


def test_espera_mais_antiga_considera_so_pedidos_novos(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 20))
    _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 0))
    _pedido(db, criar_pedido_direto, pagto, "CONFIRMADO", datetime(2026, 11, 14, 17, 0))

    assert service.fila_do_dia(db, restaurante.id, AGORA).espera_mais_antiga_min == 30


def test_fila_vazia(db, restaurante):
    fila = service.fila_do_dia(db, restaurante.id, AGORA)

    assert (fila.novos, fila.preparo, fila.saindo, fila.entregues) == (0, 0, 0, 0)
    assert fila.espera_mais_antiga_min is None


def test_cartao_de_pedido_de_entrega(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pedido = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CRIADO", datetime(2026, 11, 14, 18, 25)
    )
    _item(db, pedido, "Suco", 1, "8.00")
    _item(db, pedido, "Marmita", 2, "20.00")

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


def test_cartao_de_pedido_de_retirada(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "PRONTO", datetime(2026, 11, 14, 18, 0),
        service_type=OrderServiceType.PICKUP,
        address_street=None, address_number=None, address_neighborhood=None,
    )

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.etapa == "preparo"
    assert cartao.bairro is None
    assert cartao.status_rotulo == "Pronto para retirada"
    assert cartao.acoes_disponiveis == ["retirado", "cancelar"]
    assert cartao.itens_resumo == ""


def test_etapa_saindo(db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro):
    _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "SAIU_PARA_ENTREGA",
        datetime(2026, 11, 14, 18, 0),
    )

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.etapa == "saindo"
    assert cartao.acoes_disponiveis == ["entregue", "cancelar"]


def test_resumo_de_itens_limita_a_tres_e_conta_o_resto(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pedido = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CRIADO", datetime(2026, 11, 14, 18, 25)
    )
    for nome, preco in (("A", "50.00"), ("B", "40.00"), ("C", "30.00"), ("D", "20.00"), ("E", "10.00")):
        _item(db, pedido, nome, 1, preco)

    [cartao] = service.em_andamento(db, restaurante.id, agora=AGORA)

    assert cartao.itens_resumo == "1x A, 1x B, 1x C e mais 2"


def test_ordena_pelo_mais_antigo_e_respeita_o_limite(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    mesma_hora = datetime(2026, 11, 14, 18, 0)
    criados = [
        _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 20)),
        _pedido(db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 17, 0)),
        _pedido(db, criar_pedido_direto, pagto, "CRIADO", mesma_hora),
        _pedido(db, criar_pedido_direto, pagto, "CONFIRMADO", mesma_hora),
        _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 28)),
    ]

    padrao = service.em_andamento(db, restaurante.id, agora=AGORA)
    curto = service.em_andamento(db, restaurante.id, limite=2, agora=AGORA)

    esperados = [criados[1], criados[2], criados[3], criados[0]]
    assert [c.numero_pedido for c in padrao] == [p.order_number for p in esperados]
    assert [c.numero_pedido for c in curto] == [criados[1].order_number, criados[2].order_number]


def test_marca_atrasado_com_a_mesma_regra_dos_alertas(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    parado = _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 0))
    recente = _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 25))

    cartoes = {c.pedido_id: c for c in service.em_andamento(db, restaurante.id, agora=AGORA)}

    assert cartoes[parado.id].atrasado is True
    assert cartoes[recente.id].atrasado is False


def test_ignora_finalizados_e_outros_restaurantes(
    db, restaurante, outro_restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    antigo = datetime(2026, 11, 14, 12, 0)
    for codigo in ("ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO"):
        _pedido(db, criar_pedido_direto, pagto, codigo, antigo)
    _pedido(db, criar_pedido_direto, pagto, "CRIADO", antigo, restaurant_id=outro_restaurante.id)

    assert service.em_andamento(db, restaurante.id, agora=AGORA) == []