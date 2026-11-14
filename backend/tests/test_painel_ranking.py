from datetime import datetime, timezone
from decimal import Decimal

from app.model.models import OrderItem
from app.services import painel_ranking_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)
DENTRO = datetime(2026, 11, 14, 14, 0)


def _item(db, pedido, nome, quantidade, **ids):
    db.add(
        OrderItem(
            order_id=pedido.id,
            food_name=nome,
            quantity=quantidade,
            base_price=Decimal("10.00"),
            subtotal=Decimal("10.00") * quantidade,
            **ids,
        )
    )
    db.flush()


def _pedido(criar_pedido_direto, status, pagto, momento=DENTRO, **extra):
    return criar_pedido_direto(status, pagto, Decimal("10.00"), momento, **extra)


def test_ordena_por_quantidade_e_soma_entre_pedidos(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, status_criado,
    marmita_pronta, combo_teste, alimento_so_venda,
):
    p1 = _pedido(criar_pedido_direto, status_criado, forma_pagamento_dinheiro)
    p2 = _pedido(criar_pedido_direto, status_criado, forma_pagamento_dinheiro)
    _item(db, p1, "Marmita Pronta", 3, meal_box_id=marmita_pronta.id)
    _item(db, p2, "Marmita Pronta", 2, meal_box_id=marmita_pronta.id)
    _item(db, p1, "Feijoada", 4, food_id=alimento_so_venda.id)
    _item(db, p2, "Combo Teste", 2, combo_id=combo_teste.id)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA)

    assert [(r.tipo, r.nome, r.quantidade) for r in ranking] == [
        ("MARMITA", "Marmita Pronta", 5),
        ("AVULSO", "Feijoada", 4),
        ("COMBO", "Combo Teste", 2),
    ]
    assert ranking[0].item_id == marmita_pronta.id
    assert ranking[1].item_id == alimento_so_venda.id
    assert ranking[2].item_id == combo_teste.id


def test_respeita_o_limite(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, status_criado,
    marmita_pronta, combo_teste, alimento_so_venda,
):
    pedido = _pedido(criar_pedido_direto, status_criado, forma_pagamento_dinheiro)
    _item(db, pedido, "Marmita Pronta", 3, meal_box_id=marmita_pronta.id)
    _item(db, pedido, "Feijoada", 2, food_id=alimento_so_venda.id)
    _item(db, pedido, "Combo Teste", 1, combo_id=combo_teste.id)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, limite=2, agora=AGORA)

    assert [r.nome for r in ranking] == ["Marmita Pronta", "Feijoada"]


def test_ignora_cancelados_outros_dias_e_outros_restaurantes(
    db, restaurante, outro_restaurante, criar_pedido_direto, forma_pagamento_dinheiro,
    status_criado, status_cancelado, marmita_pronta, alimento_so_venda,
):
    pagto = forma_pagamento_dinheiro
    valido = _pedido(criar_pedido_direto, status_criado, pagto)
    cancelado = _pedido(criar_pedido_direto, status_cancelado, pagto)
    ontem = _pedido(criar_pedido_direto, status_criado, pagto, datetime(2026, 11, 13, 14, 0))
    outro = _pedido(
        criar_pedido_direto, status_criado, pagto, restaurant_id=outro_restaurante.id
    )
    _item(db, valido, "Marmita Pronta", 1, meal_box_id=marmita_pronta.id)
    _item(db, cancelado, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)
    _item(db, ontem, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)
    _item(db, outro, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA)

    assert [(r.nome, r.quantidade) for r in ranking] == [("Marmita Pronta", 1)]


def test_itens_sem_vinculo_agrupam_pelo_nome_do_pedido(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, status_criado,
):
    pedido = _pedido(criar_pedido_direto, status_criado, forma_pagamento_dinheiro)
    _item(db, pedido, "Pudim", 2)
    _item(db, pedido, "Pudim", 1)
    _item(db, pedido, "Mousse", 1)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA)

    assert [(r.tipo, r.item_id, r.nome, r.quantidade) for r in ranking] == [
        ("AVULSO", None, "Pudim", 3),
        ("AVULSO", None, "Mousse", 1),
    ]


def test_sem_vendas_devolve_lista_vazia(db, restaurante):
    assert service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA) == []