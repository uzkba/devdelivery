import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.model.models import OrderServiceType, OrderStatus, OrderStatusHistory

MOMENTO = datetime(2026, 11, 10, 12, 0)

ACOES = ["aceitar", "recusar", "preparo", "pronto", "enviar", "entregue", "retirado", "cancelar"]


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _headers(token_para, usuario):
    return {"Authorization": f"Bearer {token_para(usuario)}"}


def _post(client, headers, pedido, acao, corpo=None):
    return client.post(f"/pedidos/{pedido.id}/{acao}", json=corpo, headers=headers)


@pytest.fixture()
def novo_pedido(db, criar_pedido_direto, forma_pagamento_dinheiro):
    def _novo(codigo="CRIADO", **extra):
        return criar_pedido_direto(
            _status(db, codigo), forma_pagamento_dinheiro, Decimal("25.00"), MOMENTO, **extra
        )

    return _novo


def test_aceitar_confirma_e_registra_quem_aceitou(
    client, db, novo_pedido, atendente_user, token_para
):
    pedido = novo_pedido()
    assert pedido.status.code == "CRIADO"

    resposta = _post(client, _headers(token_para, atendente_user), pedido, "aceitar")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"]["codigo"] == "CONFIRMADO"
    assert corpo["status_rotulo"] == "Pedido confirmado"
    assert corpo["acoes_disponiveis"] == ["preparo", "cancelar"]
    historico = db.query(OrderStatusHistory).filter_by(order_id=pedido.id).one()
    assert historico.changed_by == atendente_user.id


def test_pedido_novo_oferece_aceitar_e_recusar(client, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = client.get(f"/pedidos/{pedido.id}", headers=admin_headers)

    assert resposta.json()["acoes_disponiveis"] == ["aceitar", "recusar"]
    assert resposta.json()["status_rotulo"] == "Aguardando confirmação"


def test_fluxo_completo_de_entrega_pela_api(client, novo_pedido, admin_headers, entregador_user):
    pedido = novo_pedido()

    for acao in ("aceitar", "preparo"):
        assert _post(client, admin_headers, pedido, acao).status_code == 200
    pronto = _post(client, admin_headers, pedido, "pronto")
    enviado = _post(
        client, admin_headers, pedido, "enviar", {"entregador_id": str(entregador_user.id)}
    )
    final = _post(client, admin_headers, pedido, "entregue")

    assert pronto.json()["status_rotulo"] == "Pronto, aguardando o entregador"
    assert pronto.json()["acoes_disponiveis"] == ["enviar", "cancelar"]
    assert enviado.status_code == 200
    assert enviado.json()["entregador"]["nome"] == "Pedro Entregador"
    assert enviado.json()["acoes_disponiveis"] == ["entregue", "cancelar"]
    assert final.json()["status"]["codigo"] == "ENTREGUE"
    assert final.json()["status"]["final"] is True
    assert final.json()["acoes_disponiveis"] == []


def test_fluxo_completo_de_retirada_pela_api(client, novo_pedido, admin_headers):
    pedido = novo_pedido(service_type=OrderServiceType.PICKUP)

    for acao in ("aceitar", "preparo"):
        assert _post(client, admin_headers, pedido, acao).status_code == 200
    pronto = _post(client, admin_headers, pedido, "pronto")
    final = _post(client, admin_headers, pedido, "retirado")

    assert pronto.json()["status_rotulo"] == "Pronto para retirada"
    assert pronto.json()["acoes_disponiveis"] == ["retirado", "cancelar"]
    assert final.json()["status"]["codigo"] == "RETIRADO"
    assert final.json()["entregador"] is None


def test_recusar_guarda_o_motivo(client, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = _post(client, admin_headers, pedido, "recusar", {"motivo": "Sem estoque hoje"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"]["codigo"] == "RECUSADO"
    assert corpo["motivo"] == "Sem estoque hoje"
    assert corpo["acoes_disponiveis"] == []


def test_cancelar_guarda_o_motivo(client, novo_pedido, admin_headers):
    pedido = novo_pedido("EM_PREPARO")

    resposta = _post(client, admin_headers, pedido, "cancelar", {"motivo": "Cliente desistiu"})

    assert resposta.status_code == 200
    assert resposta.json()["status"]["codigo"] == "CANCELADO"
    assert resposta.json()["motivo"] == "Cliente desistiu"


@pytest.mark.parametrize("acao", ["recusar", "cancelar"])
def test_motivo_e_obrigatorio(client, novo_pedido, admin_headers, acao):
    pedido = novo_pedido("CRIADO" if acao == "recusar" else "CONFIRMADO")

    sem_corpo = _post(client, admin_headers, pedido, acao, {})
    em_branco = _post(client, admin_headers, pedido, acao, {"motivo": "   "})

    assert sem_corpo.status_code == 422
    assert em_branco.status_code == 422
    assert "motivo" in em_branco.json()["detail"].lower()


def test_transicao_invalida_da_422_e_nao_muda_nada(client, db, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = _post(client, admin_headers, pedido, "pronto")

    assert resposta.status_code == 422
    db.refresh(pedido)
    assert pedido.status.code == "CRIADO"
    assert db.query(OrderStatusHistory).filter_by(order_id=pedido.id).count() == 0


def test_enviar_exige_o_entregador_no_corpo(client, novo_pedido, admin_headers):
    pedido = novo_pedido("PRONTO")

    assert _post(client, admin_headers, pedido, "enviar").status_code == 422
    assert _post(client, admin_headers, pedido, "enviar", {}).status_code == 422


def test_enviar_com_usuario_que_nao_e_entregador_da_422(
    client, novo_pedido, admin_headers, atendente_user
):
    pedido = novo_pedido("PRONTO")

    resposta = _post(
        client, admin_headers, pedido, "enviar", {"entregador_id": str(atendente_user.id)}
    )

    assert resposta.status_code == 422
    assert "não encontrado" in resposta.json()["detail"]


def test_retirada_nao_pode_ser_enviada(client, novo_pedido, admin_headers, entregador_user):
    pedido = novo_pedido("PRONTO", service_type=OrderServiceType.PICKUP)

    resposta = _post(
        client, admin_headers, pedido, "enviar", {"entregador_id": str(entregador_user.id)}
    )

    assert resposta.status_code == 422


def test_status_final_nao_aceita_mais_acoes(client, novo_pedido, admin_headers):
    pedido = novo_pedido("ENTREGUE")

    resposta = _post(client, admin_headers, pedido, "cancelar", {"motivo": "Tarde demais"})

    assert resposta.status_code == 422


@pytest.mark.parametrize("acao", ACOES)
@pytest.mark.parametrize("papel", ["caixa_user", "entregador_user"])
def test_caixa_e_entregador_nao_operam_a_fila(
    request, client, db, novo_pedido, token_para, acao, papel
):
    usuario = request.getfixturevalue(papel)
    pedido = novo_pedido()
    corpos = {
        "recusar": {"motivo": "Teste de permissão"},
        "cancelar": {"motivo": "Teste de permissão"},
        "enviar": {"entregador_id": str(uuid.uuid4())},
    }

    resposta = _post(client, _headers(token_para, usuario), pedido, acao, corpos.get(acao))

    assert resposta.status_code == 403
    db.refresh(pedido)
    assert pedido.status.code == "CRIADO"


def test_isolamento_entre_restaurantes(client, novo_pedido, outro_admin_headers):
    pedido = novo_pedido()

    resposta = _post(client, outro_admin_headers, pedido, "aceitar")

    assert resposta.status_code == 404


def test_pedido_inexistente_da_404(client, admin_headers):
    resposta = client.post(f"/pedidos/{uuid.uuid4()}/aceitar", headers=admin_headers)

    assert resposta.status_code == 404


def test_patch_antigo_de_status_nao_existe_mais(client, novo_pedido, admin_headers):
    pedido = novo_pedido()

    resposta = client.patch(
        f"/pedidos/{pedido.id}/status", json={"novo_status": "CONFIRMADO"}, headers=admin_headers
    )

    assert resposta.status_code == 404


def test_listagem_traz_rotulo_e_acoes(client, novo_pedido, admin_headers):
    novo_pedido("CONFIRMADO")

    resposta = client.get("/pedidos", headers=admin_headers)

    assert resposta.status_code == 200
    item = resposta.json()["items"][0]
    assert item["status_rotulo"] == "Pedido confirmado"
    assert item["acoes_disponiveis"] == ["preparo", "cancelar"]


def test_cliente_ve_o_rotulo_e_o_motivo_da_recusa(
    client, novo_pedido, admin_headers, cliente, token_para_cliente
):
    pedido = novo_pedido()
    _post(client, admin_headers, pedido, "recusar", {"motivo": "Fechamos mais cedo"})
    headers = {"Authorization": f"Bearer {token_para_cliente(cliente)}"}

    resposta = client.get(f"/pedidos/cliente/{pedido.id}", headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status_rotulo"] == "Recusado"
    assert corpo["motivo"] == "Fechamos mais cedo"