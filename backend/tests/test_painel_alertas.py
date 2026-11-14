from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.model.models import (
    ComboMealBoxItem,
    DeliveryChargeMode,
    OrderServiceType,
    OrderStatus,
    OrderStatusHistory,
    RestaurantDeliverySettings,
)
from app.services import pedido_fluxo
from app.services import painel_alertas_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)
HOJE = date(2026, 11, 14)

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
    return criar_pedido_direto(
        _status(db, codigo), pagto, Decimal("20.00"), criado_em, **extra
    )


def _mudou_em(db, pedido, codigo, momento):
    db.add(
        OrderStatusHistory(
            order_id=pedido.id, new_status_id=_status(db, codigo).id, changed_at=momento
        )
    )
    db.flush()


def _config(db, restaurante, **extra):
    config = RestaurantDeliverySettings(
        restaurant_id=restaurante.id, charge_mode=DeliveryChargeMode.GRATIS, **extra
    )
    db.add(config)
    db.flush()
    return config


def test_criado_so_atrasa_depois_de_10_minutos(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    no_limite = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CRIADO", datetime(2026, 11, 14, 18, 20)
    )
    passou = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CRIADO", datetime(2026, 11, 14, 18, 19)
    )

    atrasos = service.atrasos_dos_pedidos(db, restaurante.id, AGORA)

    assert set(atrasos) == {passou.id}
    assert no_limite.id not in atrasos
    assert atrasos[passou.id].minutos == 11
    assert atrasos[passou.id].motivo == "PARADO"
    assert atrasos[passou.id].limite_min == 10


def test_confirmado_conta_desde_a_ultima_mudanca_de_status(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    recente = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CONFIRMADO", datetime(2026, 11, 14, 17, 0)
    )
    antigo = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CONFIRMADO", datetime(2026, 11, 14, 17, 0)
    )
    _mudou_em(db, recente, "CONFIRMADO", datetime(2026, 11, 14, 18, 25))
    _mudou_em(db, antigo, "CONFIRMADO", datetime(2026, 11, 14, 18, 10))

    atrasos = service.atrasos_dos_pedidos(db, restaurante.id, AGORA)

    assert set(atrasos) == {antigo.id}
    assert atrasos[antigo.id].minutos == 20


def test_em_preparo_usa_tempo_estimado_e_o_tipo_de_atendimento(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    _config(db, restaurante, delivery_time_minutes=40, pickup_time_minutes=15)
    pagto = forma_pagamento_dinheiro
    entrega_atrasada = _pedido(db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 17, 45))
    entrega_no_prazo = _pedido(db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 18, 0))
    retirada_atrasada = _pedido(
        db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 18, 10),
        service_type=OrderServiceType.PICKUP,
    )

    atrasos = service.atrasos_dos_pedidos(db, restaurante.id, AGORA)

    assert set(atrasos) == {entrega_atrasada.id, retirada_atrasada.id}
    assert entrega_no_prazo.id not in atrasos
    assert atrasos[entrega_atrasada.id].motivo == "TEMPO_ESTIMADO"
    assert atrasos[entrega_atrasada.id].limite_min == 40
    assert atrasos[entrega_atrasada.id].minutos == 45
    assert atrasos[retirada_atrasada.id].limite_min == 15


def test_sem_tempo_estimado_usa_limites_padrao(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    preparo_lento = _pedido(db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 17, 50))
    preparo_ok = _pedido(db, criar_pedido_direto, pagto, "EM_PREPARO", datetime(2026, 11, 14, 18, 10))
    rota_longa = _pedido(db, criar_pedido_direto, pagto, "SAIU_PARA_ENTREGA", datetime(2026, 11, 14, 17, 0))
    rota_ok = _pedido(db, criar_pedido_direto, pagto, "SAIU_PARA_ENTREGA", datetime(2026, 11, 14, 17, 0))
    _mudou_em(db, rota_longa, "SAIU_PARA_ENTREGA", datetime(2026, 11, 14, 17, 40))
    _mudou_em(db, rota_ok, "SAIU_PARA_ENTREGA", datetime(2026, 11, 14, 18, 0))

    atrasos = service.atrasos_dos_pedidos(db, restaurante.id, AGORA)

    assert set(atrasos) == {preparo_lento.id, rota_longa.id}
    assert preparo_ok.id not in atrasos
    assert rota_ok.id not in atrasos
    assert atrasos[preparo_lento.id].limite_min == 30
    assert atrasos[rota_longa.id].limite_min == 45


def test_pronto_de_retirada_nunca_alerta_mas_o_de_entrega_sim(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    entrega = _pedido(db, criar_pedido_direto, pagto, "PRONTO", datetime(2026, 11, 14, 18, 19))
    retirada = _pedido(
        db, criar_pedido_direto, pagto, "PRONTO", datetime(2026, 11, 14, 18, 0),
        service_type=OrderServiceType.PICKUP,
    )

    atrasos = service.atrasos_dos_pedidos(db, restaurante.id, AGORA)

    assert set(atrasos) == {entrega.id}
    assert retirada.id not in atrasos


def test_ignora_finalizados_e_outros_restaurantes(
    db, restaurante, outro_restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pagto = forma_pagamento_dinheiro
    antigo = datetime(2026, 11, 14, 12, 0)
    for codigo in ("ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO"):
        _pedido(db, criar_pedido_direto, pagto, codigo, antigo)
    _pedido(
        db, criar_pedido_direto, pagto, "CRIADO", antigo, restaurant_id=outro_restaurante.id
    )

    assert service.atrasos_dos_pedidos(db, restaurante.id, AGORA) == {}


def test_itens_indisponiveis_juntam_esgotados_e_combo_com_componente_inativo(
    db, restaurante, outro_restaurante, marmita_pronta, marmita_inativa, marmita_b,
    alimento_so_venda, alimento_bebida, combo_teste,
):
    marmita_pronta.sold_out_on = HOJE
    alimento_so_venda.sold_out_on = HOJE
    alimento_bebida.sold_out_on = date(2026, 11, 13)
    marmita_b.sold_out_on = HOJE
    combo_teste.meal_box_items.append(ComboMealBoxItem(meal_box_id=marmita_inativa.id, quantity=1))
    db.flush()
    db.refresh(combo_teste)

    itens = service.itens_indisponiveis_hoje(db, restaurante.id, AGORA)

    assert [(i.tipo, i.nome, i.motivo) for i in itens] == [
        ("COMBO", "Combo Teste", "COMPONENTE_INATIVO"),
        ("AVULSO", "Feijoada", "ESGOTADO_HOJE"),
        ("MARMITA", "Marmita Pronta", "ESGOTADO_HOJE"),
    ]


def test_combo_esgotado_e_com_componente_inativo_conta_uma_vez(
    db, restaurante, marmita_inativa, combo_teste
):
    combo_teste.sold_out_on = HOJE
    combo_teste.meal_box_items.append(ComboMealBoxItem(meal_box_id=marmita_inativa.id, quantity=1))
    db.flush()
    db.refresh(combo_teste)

    itens = service.itens_indisponiveis_hoje(db, restaurante.id, AGORA)

    assert [(i.nome, i.motivo) for i in itens] == [("Combo Teste", "ESGOTADO_HOJE")]


def test_item_inativo_nao_aparece_como_indisponivel(db, restaurante, marmita_inativa):
    marmita_inativa.sold_out_on = HOJE
    db.flush()

    assert service.itens_indisponiveis_hoje(db, restaurante.id, AGORA) == []


def test_alertas_ordenam_pedidos_antes_dos_itens_e_montam_os_textos(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro, marmita_pronta
):
    pagto = forma_pagamento_dinheiro
    mais_antigo = _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 0))
    mais_novo = _pedido(db, criar_pedido_direto, pagto, "CRIADO", datetime(2026, 11, 14, 18, 15))
    marmita_pronta.sold_out_on = HOJE
    db.flush()

    alertas = service.alertas_de_atencao(db, restaurante.id, AGORA)

    assert [a.codigo for a in alertas] == ["PEDIDO_ATRASADO", "ITENS_INDISPONIVEIS"]
    pedidos, itens = alertas
    assert (pedidos.gravidade, pedidos.destino, pedidos.quantidade) == ("CRITICO", "pedidos", 2)
    assert pedidos.titulo == "2 pedidos atrasados"
    assert pedidos.detalhe == (
        f"#{mais_antigo.order_number} e #{mais_novo.order_number} passaram do tempo esperado"
    )
    assert (itens.gravidade, itens.destino, itens.quantidade) == ("AVISO", "cardapio", 1)
    assert itens.titulo == "1 item indisponível hoje"
    assert itens.detalhe == "Marmita Pronta"


def test_alerta_de_um_pedido_detalha_o_tempo(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro
):
    pedido = _pedido(
        db, criar_pedido_direto, forma_pagamento_dinheiro, "CRIADO", datetime(2026, 11, 14, 18, 15)
    )

    [alerta] = service.alertas_de_atencao(db, restaurante.id, AGORA)

    assert alerta.titulo == "1 pedido atrasado"
    assert alerta.detalhe == f"#{pedido.order_number} está parado há 15 min"


def test_lista_longa_de_itens_resume_o_restante(
    db, restaurante, marmita_pronta, marmita_personalizavel, alimento_so_venda, alimento_bebida
):
    for item in (marmita_pronta, marmita_personalizavel, alimento_so_venda, alimento_bebida):
        item.sold_out_on = HOJE
    db.flush()

    [alerta] = service.alertas_de_atencao(db, restaurante.id, AGORA)

    assert alerta.quantidade == 4
    assert alerta.titulo == "4 itens indisponíveis hoje"
    assert alerta.detalhe == "Feijoada, Marmita Personalizável e mais 2"


def test_sem_nada_para_alertar_devolve_lista_vazia(db, restaurante):
    assert service.alertas_de_atencao(db, restaurante.id, AGORA) == []