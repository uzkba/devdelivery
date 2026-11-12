import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.websockets import manager


def _recusada(client, caminho):
    with pytest.raises(WebSocketDisconnect) as erro:
        with client.websocket_connect(caminho):
            pass
    assert erro.value.code == 1008


@pytest.mark.parametrize("papel", ["admin_user", "atendente_user"])
def test_admin_e_atendente_conectam_no_restaurante(request, client, restaurante, token_para, papel):
    usuario = request.getfixturevalue(papel)

    with client.websocket_connect(f"/ws/restaurante?token={token_para(usuario)}"):
        assert len(manager.active_connections[restaurante.id]) == 1

    assert restaurante.id not in manager.active_connections


@pytest.mark.parametrize(
    "papel", ["caixa_user", "entregador_user", "inactive_admin_user", "inactive_admin_with_admin_role"]
)
def test_quem_nao_opera_a_fila_ou_esta_inativo_e_recusado(request, client, token_para, papel):
    usuario = request.getfixturevalue(papel)

    _recusada(client, f"/ws/restaurante?token={token_para(usuario)}")


def test_token_invalido_ou_ausente_e_recusado(client):
    _recusada(client, "/ws/restaurante?token=lixo")
    _recusada(client, "/ws/restaurante")
    _recusada(client, "/ws/cliente?token=lixo")


def test_token_de_cliente_nao_entra_no_canal_do_restaurante(client, cliente, token_para_cliente):
    _recusada(client, f"/ws/restaurante?token={token_para_cliente(cliente)}")


def test_token_de_admin_nao_entra_no_canal_do_cliente(client, admin_user, token_para):
    _recusada(client, f"/ws/cliente?token={token_para(admin_user)}")


def test_cliente_conecta_e_desconecta(client, cliente, token_para_cliente):
    with client.websocket_connect(f"/ws/cliente?token={token_para_cliente(cliente)}"):
        assert len(manager.client_connections[cliente.id]) == 1

    assert cliente.id not in manager.client_connections


def test_cliente_recebe_o_status_novo(
    client, novo_pedido, admin_headers, cliente, token_para_cliente
):
    pedido = novo_pedido()

    with client.websocket_connect(f"/ws/cliente?token={token_para_cliente(cliente)}") as ws:
        resposta = client.post(f"/pedidos/{pedido.id}/aceitar", headers=admin_headers)
        evento = ws.receive_json()

    assert resposta.status_code == 200
    assert evento["tipo"] == "STATUS_PEDIDO"
    assert evento["pedido_id"] == str(pedido.id)
    assert evento["status"] == "CONFIRMADO"
    assert evento["status_rotulo"] == "Pedido confirmado"
    assert evento["final"] is False
    assert evento["motivo"] is None


def test_cliente_recebe_o_motivo_da_recusa(
    client, novo_pedido, admin_headers, cliente, token_para_cliente
):
    pedido = novo_pedido()

    with client.websocket_connect(f"/ws/cliente?token={token_para_cliente(cliente)}") as ws:
        client.post(
            f"/pedidos/{pedido.id}/recusar", json={"motivo": "Fechamos mais cedo"}, headers=admin_headers
        )
        evento = ws.receive_json()

    assert evento["status"] == "RECUSADO"
    assert evento["final"] is True
    assert evento["motivo"] == "Fechamos mais cedo"


def test_restaurante_tambem_recebe_o_status_com_as_acoes(
    client, novo_pedido, admin_headers, admin_user, token_para
):
    pedido = novo_pedido()

    with client.websocket_connect(f"/ws/restaurante?token={token_para(admin_user)}") as ws:
        client.post(f"/pedidos/{pedido.id}/aceitar", headers=admin_headers)
        evento = ws.receive_json()

    assert evento["tipo"] == "STATUS_PEDIDO"
    assert evento["acoes_disponiveis"] == ["preparo", "cancelar"]


def test_transicao_invalida_nao_dispara_evento(
    client, novo_pedido, admin_headers, cliente, token_para_cliente
):
    pedido = novo_pedido()
    invalida = novo_pedido()

    with client.websocket_connect(f"/ws/cliente?token={token_para_cliente(cliente)}") as ws:
        recusada = client.post(f"/pedidos/{invalida.id}/pronto", headers=admin_headers)
        valida = client.post(f"/pedidos/{pedido.id}/aceitar", headers=admin_headers)
        evento = ws.receive_json()

    assert recusada.status_code == 422
    assert valida.status_code == 200
    assert evento["pedido_id"] == str(pedido.id)