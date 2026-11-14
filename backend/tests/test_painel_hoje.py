from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.core.tempo import hoje_local
from app.model.models import OrderItem, RestaurantHours
from app.services import painel_hoje_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)


def _utc_naive(minutos_atras=0):
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutos_atras)


def _faixa(db, restaurante, abre, fecha):
    db.add(
        RestaurantHours(
            restaurant_id=restaurante.id, weekday=5, opens_at=abre, closes_at=fecha
        )
    )
    db.flush()


def test_monta_o_painel_completo_com_dados_consistentes(
    db, restaurante, criar_pedido_direto, forma_pagamento_dinheiro,
    status_criado, status_entregue, marmita_pronta,
):
    pagto = forma_pagamento_dinheiro
    parado = criar_pedido_direto(status_criado, pagto, Decimal("30.00"), datetime(2026, 11, 14, 18, 0))
    entregue = criar_pedido_direto(status_entregue, pagto, Decimal("50.00"), datetime(2026, 11, 14, 16, 0))
    db.add(
        OrderItem(
            order_id=entregue.id,
            meal_box_id=marmita_pronta.id,
            food_name="Marmita Pronta",
            quantity=2,
            base_price=Decimal("25.00"),
            subtotal=Decimal("50.00"),
        )
    )
    marmita_pronta.sold_out_on = date(2026, 11, 14)
    db.flush()

    painel = service.montar_hoje(db, restaurante.id, AGORA)

    assert painel.data == date(2026, 11, 14)
    assert painel.restaurante.nome == "Marmitas da Vovó"
    assert painel.restaurante.estado.estado == "ABERTO"
    assert painel.fila.novos == 1
    assert painel.fila.espera_mais_antiga_min == 30
    assert [c.numero_pedido for c in painel.em_andamento] == [parado.order_number]
    assert painel.em_andamento[0].atrasado is True
    assert [a.codigo for a in painel.atencao] == ["PEDIDO_ATRASADO", "ITENS_INDISPONIVEIS"]
    assert painel.resumo.atual.pedidos == 2
    assert painel.resumo.atual.vendas == Decimal("80.00")
    assert [(m.nome, m.quantidade) for m in painel.mais_vendidos] == [("Marmita Pronta", 2)]


def test_fecha_as_traz_o_fim_da_faixa_atual(db, restaurante):
    _faixa(db, restaurante, time(10, 0), time(22, 0))

    painel = service.montar_hoje(db, restaurante.id, AGORA)

    assert painel.restaurante.estado.estado == "ABERTO"
    assert painel.restaurante.fecha_as == "22:00"


def test_fecha_as_e_nulo_fora_do_horario(db, restaurante):
    _faixa(db, restaurante, time(10, 0), time(14, 0))

    painel = service.montar_hoje(db, restaurante.id, AGORA)

    assert painel.restaurante.estado.estado == "FECHADO"
    assert painel.restaurante.fecha_as is None


def test_exige_perfil_admin(client, atendente_user, token_para):
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}

    assert client.get("/painel/hoje", headers=headers).status_code == 403


def test_exige_autenticacao(client):
    assert client.get("/painel/hoje").status_code in (401, 403)


def test_painel_vazio_tem_formato_completo(client, admin_headers):
    resposta = client.get("/painel/hoje", headers=admin_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {
        "data", "restaurante", "fila", "em_andamento", "atencao", "resumo", "mais_vendidos",
    }
    assert corpo["restaurante"]["nome"] == "Marmitas da Vovó"
    assert corpo["restaurante"]["estado"]["aceita_pedidos"] is True
    assert corpo["restaurante"]["fecha_as"] is None
    assert corpo["fila"] == {
        "novos": 0, "preparo": 0, "saindo": 0, "entregues": 0, "espera_mais_antiga_min": None,
    }
    assert corpo["em_andamento"] == []
    assert corpo["atencao"] == []
    assert corpo["mais_vendidos"] == []
    assert corpo["resumo"]["atual"]["pedidos"] == 0
    assert corpo["resumo"]["variacao_vendas_pct"] is None
    assert corpo["resumo"]["diferenca_entrega_min"] is None
    assert isinstance(corpo["resumo"]["rotulo_comparacao"], str)


def test_mostra_pedido_aberto_e_alerta_de_item_esgotado(
    client, admin_headers, db, criar_pedido_direto, forma_pagamento_dinheiro,
    status_criado, marmita_pronta,
):
    pedido = criar_pedido_direto(
        status_criado, forma_pagamento_dinheiro, Decimal("30.00"), _utc_naive(2)
    )
    marmita_pronta.sold_out_on = hoje_local()
    db.flush()

    corpo = client.get("/painel/hoje", headers=admin_headers).json()

    assert corpo["fila"]["novos"] == 1
    [cartao] = corpo["em_andamento"]
    assert cartao["pedido_id"] == str(pedido.id)
    assert cartao["numero_pedido"] == pedido.order_number
    assert cartao["etapa"] == "novos"
    assert cartao["tipo_atendimento"] == "ENTREGA"
    assert cartao["acoes_disponiveis"] == ["aceitar", "recusar"]
    assert cartao["atrasado"] is False
    assert [a["codigo"] for a in corpo["atencao"]] == ["ITENS_INDISPONIVEIS"]


def test_nao_mostra_pedidos_de_outro_restaurante(
    client, admin_headers, criar_pedido_direto, forma_pagamento_dinheiro,
    status_criado, outro_restaurante,
):
    criar_pedido_direto(
        status_criado, forma_pagamento_dinheiro, Decimal("30.00"), _utc_naive(2),
        restaurant_id=outro_restaurante.id,
    )

    corpo = client.get("/painel/hoje", headers=admin_headers).json()

    assert corpo["fila"]["novos"] == 0
    assert corpo["em_andamento"] == []


def test_reflete_a_pausa_do_restaurante(client, admin_headers, db, restaurante):
    restaurante.is_paused = True
    db.flush()

    estado = client.get("/painel/hoje", headers=admin_headers).json()["restaurante"]["estado"]

    assert estado["estado"] == "PAUSADO"
    assert estado["aceita_pedidos"] is False