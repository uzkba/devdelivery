from datetime import datetime

from app.model.models import OrderStatus, OrderStatusHistory
from app.services import pedido_service


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def _headers_cliente(token_para_cliente, cliente):
    return {"Authorization": f"Bearer {token_para_cliente(cliente)}"}


def _historico(db, pedido, usuario, de, para, momento):
    db.add(
        OrderStatusHistory(
            order_id=pedido.id,
            previous_status_id=_status(db, de).id,
            new_status_id=_status(db, para).id,
            changed_by=usuario.id,
            changed_at=momento,
        )
    )


def test_avisos_vem_do_mais_novo_para_o_mais_antigo(db, novo_pedido, cliente, admin_user):
    pedido = novo_pedido()
    _historico(db, pedido, admin_user, "CRIADO", "CONFIRMADO", datetime(2026, 11, 10, 12, 5))
    _historico(db, pedido, admin_user, "CONFIRMADO", "EM_PREPARO", datetime(2026, 11, 10, 12, 10))
    db.flush()

    avisos = pedido_service.listar_avisos_cliente(db, cliente.id)

    assert [novo.code for _, _, novo in avisos] == ["EM_PREPARO", "CONFIRMADO"]


def test_limite_corta_os_mais_antigos(db, novo_pedido, cliente, admin_user):
    pedido = novo_pedido()
    _historico(db, pedido, admin_user, "CRIADO", "CONFIRMADO", datetime(2026, 11, 10, 12, 5))
    _historico(db, pedido, admin_user, "CONFIRMADO", "EM_PREPARO", datetime(2026, 11, 10, 12, 10))
    db.flush()

    avisos = pedido_service.listar_avisos_cliente(db, cliente.id, limite=1)

    assert [novo.code for _, _, novo in avisos] == ["EM_PREPARO"]


def test_cliente_ve_so_os_avisos_dos_proprios_pedidos(
    client, novo_pedido, admin_headers, cliente, outro_cliente, token_para_cliente
):
    meu = novo_pedido()
    alheio = novo_pedido(client_id=outro_cliente.id)
    client.post(f"/pedidos/{meu.id}/aceitar", headers=admin_headers)
    client.post(
        f"/pedidos/{meu.id}/cancelar", json={"motivo": "Fogão quebrou"}, headers=admin_headers
    )
    client.post(f"/pedidos/{alheio.id}/aceitar", headers=admin_headers)

    resposta = client.get("/pedidos/me/avisos", headers=_headers_cliente(token_para_cliente, cliente))

    assert resposta.status_code == 200
    avisos = resposta.json()
    assert {a["status"] for a in avisos} == {"CONFIRMADO", "CANCELADO"}
    assert {a["pedido_id"] for a in avisos} == {str(meu.id)}
    cancelado = next(a for a in avisos if a["status"] == "CANCELADO")
    assert cancelado["motivo"] == "Fogão quebrou"
    assert cancelado["rotulo"] == "Cancelado"
    assert cancelado["numero_pedido"] == meu.order_number


def test_cliente_sem_avisos_recebe_lista_vazia(client, cliente, token_para_cliente):
    resposta = client.get("/pedidos/me/avisos", headers=_headers_cliente(token_para_cliente, cliente))

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_avisos_exigem_login_de_cliente(client, admin_headers):
    assert client.get("/pedidos/me/avisos").status_code in (401, 403)
    assert client.get("/pedidos/me/avisos", headers=admin_headers).status_code in (401, 403)


def test_limite_invalido_da_422(client, cliente, token_para_cliente):
    resposta = client.get(
        "/pedidos/me/avisos?limite=0", headers=_headers_cliente(token_para_cliente, cliente)
    )

    assert resposta.status_code == 422