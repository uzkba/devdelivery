from datetime import datetime, timezone

from app.services import painel_ranking_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)
DENTRO = datetime(2026, 11, 14, 14, 0)


def test_ordena_por_quantidade_e_soma_entre_pedidos(
    db, restaurante, pedido_em, adicionar_item, marmita_pronta, combo_teste, alimento_so_venda
):
    p1 = pedido_em("CRIADO", DENTRO)
    p2 = pedido_em("CRIADO", DENTRO)
    adicionar_item(p1, "Marmita Pronta", 3, meal_box_id=marmita_pronta.id)
    adicionar_item(p2, "Marmita Pronta", 2, meal_box_id=marmita_pronta.id)
    adicionar_item(p1, "Feijoada", 4, food_id=alimento_so_venda.id)
    adicionar_item(p2, "Combo Teste", 2, combo_id=combo_teste.id)

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
    db, restaurante, pedido_em, adicionar_item, marmita_pronta, combo_teste, alimento_so_venda
):
    pedido = pedido_em("CRIADO", DENTRO)
    adicionar_item(pedido, "Marmita Pronta", 3, meal_box_id=marmita_pronta.id)
    adicionar_item(pedido, "Feijoada", 2, food_id=alimento_so_venda.id)
    adicionar_item(pedido, "Combo Teste", 1, combo_id=combo_teste.id)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, limite=2, agora=AGORA)

    assert [r.nome for r in ranking] == ["Marmita Pronta", "Feijoada"]


def test_ignora_cancelados_outros_dias_e_outros_restaurantes(
    db, restaurante, outro_restaurante, pedido_em, adicionar_item, marmita_pronta
):
    valido = pedido_em("CRIADO", DENTRO)
    cancelado = pedido_em("CANCELADO", DENTRO)
    ontem = pedido_em("CRIADO", datetime(2026, 11, 13, 14, 0))
    outro = pedido_em("CRIADO", DENTRO, restaurant_id=outro_restaurante.id)
    adicionar_item(valido, "Marmita Pronta", 1, meal_box_id=marmita_pronta.id)
    adicionar_item(cancelado, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)
    adicionar_item(ontem, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)
    adicionar_item(outro, "Marmita Pronta", 50, meal_box_id=marmita_pronta.id)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA)

    assert [(r.nome, r.quantidade) for r in ranking] == [("Marmita Pronta", 1)]


def test_itens_sem_vinculo_agrupam_pelo_nome_do_pedido(
    db, restaurante, pedido_em, adicionar_item
):
    pedido = pedido_em("CRIADO", DENTRO)
    adicionar_item(pedido, "Pudim", 2)
    adicionar_item(pedido, "Pudim", 1)
    adicionar_item(pedido, "Mousse", 1)

    ranking = service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA)

    assert [(r.tipo, r.item_id, r.nome, r.quantidade) for r in ranking] == [
        ("AVULSO", None, "Pudim", 3),
        ("AVULSO", None, "Mousse", 1),
    ]


def test_sem_vendas_devolve_lista_vazia(db, restaurante):
    assert service.mais_vendidos_hoje(db, restaurante.id, agora=AGORA) == []