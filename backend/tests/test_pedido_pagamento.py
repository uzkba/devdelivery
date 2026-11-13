from datetime import datetime
from decimal import Decimal

import pytest

from app.model.models import OrderPaymentHistory, PaymentMethod
from app.services import notificacao_service, pedido_service


def _patch(client, headers, pedido, corpo):
    return client.patch(f"/pedidos/{pedido.id}/pagamento", json=corpo, headers=headers)


def _historico_ate(db, pedido, usuario, de, para, momento):
    por_codigo = {f.code: f for f in db.query(PaymentMethod).all()}
    db.add(
        OrderPaymentHistory(
            order_id=pedido.id,
            previous_payment_method_id=por_codigo[de].id,
            new_payment_method_id=por_codigo[para].id,
            changed_by=usuario.id,
            changed_at=momento,
        )
    )


def test_trocar_para_pix_registra_quem_trocou(
    client, db, novo_pedido, admin_headers, admin_user, forma_pagamento_dinheiro, forma_pagamento_pix
):
    pedido = novo_pedido()

    resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "PIX"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["forma_pagamento"]["codigo"] == "PIX"
    assert corpo["valor_troco"] is None
    registro = db.query(OrderPaymentHistory).filter_by(order_id=pedido.id).one()
    assert registro.changed_by == admin_user.id
    assert registro.previous_payment_method_id == forma_pagamento_dinheiro.id
    assert registro.new_payment_method_id == forma_pagamento_pix.id


def test_atendente_tambem_pode_trocar(client, novo_pedido, atendente_user, token_para):
    pedido = novo_pedido()
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}

    resposta = _patch(client, headers, pedido, {"forma_pagamento": "PIX"})

    assert resposta.status_code == 200


def test_trocar_para_dinheiro_exige_o_valor_pago(
    client, db, novo_pedido, admin_headers, forma_pagamento_pix
):
    pedido = novo_pedido(payment_method_id=forma_pagamento_pix.id)

    sem_valor = _patch(client, admin_headers, pedido, {"forma_pagamento": "DINHEIRO"})
    valor_curto = _patch(
        client, admin_headers, pedido, {"forma_pagamento": "DINHEIRO", "valor_pago_dinheiro": 20}
    )

    assert sem_valor.status_code == 422
    assert sem_valor.json()["detail"] == "Informe o valor pago em dinheiro."
    assert valor_curto.status_code == 400
    assert db.query(OrderPaymentHistory).filter_by(order_id=pedido.id).count() == 0


def test_trocar_para_dinheiro_calcula_o_troco(
    client, db, novo_pedido, admin_headers, forma_pagamento_pix
):
    pedido = novo_pedido(payment_method_id=forma_pagamento_pix.id)

    resposta = _patch(
        client, admin_headers, pedido, {"forma_pagamento": "DINHEIRO", "valor_pago_dinheiro": 50}
    )

    assert resposta.status_code == 200
    assert resposta.json()["valor_troco"] == "25.00"
    assert resposta.json()["forma_pagamento"]["codigo"] == "DINHEIRO"
    db.refresh(pedido)
    assert pedido.cash_paid_amount == Decimal("50.00")
    assert pedido.change_amount == Decimal("25.00")


def test_sair_do_dinheiro_zera_valor_pago_e_troco(client, db, novo_pedido, admin_headers):
    pedido = novo_pedido(cash_paid_amount=Decimal("50.00"), change_amount=Decimal("25.00"))

    resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "CARTAO_DEBITO"})

    assert resposta.status_code == 200
    assert resposta.json()["valor_troco"] is None
    db.refresh(pedido)
    assert pedido.cash_paid_amount is None
    assert pedido.change_amount is None


def test_valor_pago_fora_do_dinheiro_e_recusado(client, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = _patch(
        client, admin_headers, pedido, {"forma_pagamento": "PIX", "valor_pago_dinheiro": 30}
    )

    assert resposta.status_code == 422
    assert "DINHEIRO" in resposta.json()["detail"]


def test_mesma_forma_e_recusada(client, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = _patch(
        client, admin_headers, pedido, {"forma_pagamento": "DINHEIRO", "valor_pago_dinheiro": 50}
    )

    assert resposta.status_code == 422
    assert "já usa" in resposta.json()["detail"]


def test_forma_que_o_restaurante_nao_aceita_e_recusada(
    client, db, novo_pedido, admin_headers, restaurante, aceitar_formas
):
    aceitar_formas(restaurante, "DINHEIRO", "PIX")
    pedido = novo_pedido()

    resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "CARTAO_DEBITO"})

    assert resposta.status_code == 422
    assert "não aceita" in resposta.json()["detail"]
    db.refresh(pedido)
    assert pedido.payment_method.code == "DINHEIRO"


def test_forma_inativa_e_recusada(client, db, novo_pedido, admin_headers, forma_pagamento_debito):
    forma_pagamento_debito.is_active = False
    db.flush()
    pedido = novo_pedido()

    resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "CARTAO_DEBITO"})

    assert resposta.status_code == 422


@pytest.mark.parametrize("final", ["ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO"])
def test_status_final_trava_a_troca(client, db, novo_pedido, admin_headers, final):
    pedido = novo_pedido(final)

    resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "PIX"})

    assert resposta.status_code == 422
    assert "finalizado" in resposta.json()["detail"]
    assert db.query(OrderPaymentHistory).filter_by(order_id=pedido.id).count() == 0


@pytest.mark.parametrize("corpo", [{}, {"forma_pagamento": "BOLETO"}, {"forma_pagamento": "PIX", "extra": 1}])
def test_corpo_invalido_da_422(client, novo_pedido, admin_headers, corpo):
    pedido = novo_pedido()

    assert _patch(client, admin_headers, pedido, corpo).status_code == 422


@pytest.mark.parametrize("papel", ["caixa_user", "entregador_user"])
def test_caixa_e_entregador_nao_trocam(request, client, db, novo_pedido, token_para, papel):
    usuario = request.getfixturevalue(papel)
    pedido = novo_pedido()
    headers = {"Authorization": f"Bearer {token_para(usuario)}"}

    resposta = _patch(client, headers, pedido, {"forma_pagamento": "PIX"})

    assert resposta.status_code == 403
    db.refresh(pedido)
    assert pedido.payment_method.code == "DINHEIRO"


def test_isolamento_entre_restaurantes(client, novo_pedido, outro_admin_headers):
    pedido = novo_pedido()

    assert _patch(client, outro_admin_headers, pedido, {"forma_pagamento": "PIX"}).status_code == 404
    historico = client.get(f"/pedidos/{pedido.id}/pagamento/historico", headers=outro_admin_headers)
    assert historico.status_code == 404


def test_cliente_ve_a_forma_nova(client, novo_pedido, admin_headers, cliente, token_para_cliente):
    pedido = novo_pedido()
    _patch(client, admin_headers, pedido, {"forma_pagamento": "PIX"})
    headers = {"Authorization": f"Bearer {token_para_cliente(cliente)}"}

    resposta = client.get(f"/pedidos/cliente/{pedido.id}", headers=headers)

    assert resposta.json()["forma_pagamento"]["codigo"] == "PIX"


def test_cliente_recebe_o_aviso_da_troca(
    client, novo_pedido, admin_headers, cliente, token_para_cliente, forma_pagamento_pix
):
    pedido = novo_pedido()

    with client.websocket_connect(f"/ws/cliente?token={token_para_cliente(cliente)}") as ws:
        resposta = _patch(client, admin_headers, pedido, {"forma_pagamento": "PIX"})
        evento = ws.receive_json()

    assert resposta.status_code == 200
    assert evento == {
        "tipo": "PAGAMENTO_PEDIDO",
        "pedido_id": str(pedido.id),
        "numero_pedido": pedido.order_number,
        "forma_pagamento": "PIX",
        "forma_pagamento_nome": forma_pagamento_pix.name,
        "valor_troco": None,
    }


def test_evento_de_pagamento_traz_o_troco(db, novo_pedido, forma_pagamento_dinheiro):
    pedido = novo_pedido(cash_paid_amount=Decimal("50.00"), change_amount=Decimal("25.00"))

    evento = notificacao_service.montar_evento_pagamento(pedido)

    assert evento["forma_pagamento"] == "DINHEIRO"
    assert evento["valor_troco"] == 25.0


def test_historico_lista_quem_trocou_com_os_nomes(client, novo_pedido, admin_headers):
    pedido = novo_pedido()
    _patch(client, admin_headers, pedido, {"forma_pagamento": "PIX"})

    resposta = client.get(f"/pedidos/{pedido.id}/pagamento/historico", headers=admin_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["forma_anterior"]["codigo"] == "DINHEIRO"
    assert corpo[0]["forma_nova"]["codigo"] == "PIX"
    assert corpo[0]["alterado_por"] == "Maria Admin"


def test_historico_vem_do_mais_novo_para_o_mais_antigo(db, novo_pedido, admin_user, restaurante):
    pedido = novo_pedido()
    _historico_ate(db, pedido, admin_user, "DINHEIRO", "PIX", datetime(2026, 11, 10, 12, 5))
    _historico_ate(db, pedido, admin_user, "PIX", "CARTAO_DEBITO", datetime(2026, 11, 10, 12, 10))
    db.flush()

    registros = pedido_service.listar_historico_pagamento(db, pedido.id, restaurante.id)

    assert [(a.code, n.code) for _, a, n, _ in registros] == [
        ("PIX", "CARTAO_DEBITO"),
        ("DINHEIRO", "PIX"),
    ]