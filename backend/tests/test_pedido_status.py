import uuid
from backend.app.model.models import OrderStatus, OrderStatusHistory
import pytest
from backend.tests.conftest import _get_or_create_status


def _headers(client, login: str, password: str = "senha123") -> dict:
    response = client.post("/auth/login/admin", json={"login": login, "password": password})
    assert response.status_code == 200, f"Login falhou: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def status_em_preparacao(db):
    return _get_or_create_status(db, "EM_PREPARACAO", "Em preparação", 2, False)


@pytest.fixture()
def status_cancelado(db):
    return _get_or_create_status(db, "CANCELADO", "Cancelado", 6, True)


def test_atualizar_status_sucesso(client, db, pedido_teste, status_em_preparacao, admin_user):
    # Agora a maria.admin existe no banco de dados antes dessa linha executar!
    headers = _headers(client, "maria.admin")
    resp = client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "EM_PREPARACAO"},
        headers=headers,
    )
    assert resp.status_code == 200

    historico = db.query(OrderStatusHistory).filter_by(order_id=pedido_teste.id).all()
    assert len(historico) == 1
    assert historico[0].new_status_id == status_em_preparacao.id


def test_status_inexistente_retorna_404(client, admin_user, pedido_teste):
    headers = _headers(client, "maria.admin")
    resp = client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "NAO_EXISTE"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_pedido_inexistente_retorna_404(client, admin_user, status_em_preparacao):
    headers = _headers(client, "maria.admin")
    resp = client.patch(
        f"/pedidos/{uuid.uuid4()}/status",
        json={"novo_status": "EM_PREPARACAO"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_nao_permite_transicao_apos_status_final(client, pedido_teste, admin_user, status_cancelado, status_em_preparacao):
    headers = _headers(client, "maria.admin")

    client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "CANCELADO"},
        headers=headers,
    )

    resp = client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "EM_PREPARACAO"},
        headers=headers,
    )

    print("\nERRO DA API:", resp.json())
    assert resp.status_code == 400


def test_caixa_nao_pode_alterar_status(client, caixa_user, pedido_teste, status_em_preparacao):
    headers = _headers(client, "carlos.caixa")
    resp = client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "EM_PREPARACAO"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_isolamento_entre_restaurantes(
    client, admin_user, outro_admin_user, pedido_teste, status_em_preparacao
):
    """Pedido é do restaurante da Maria; Zé (outro restaurante) não pode alterá-lo."""
    headers_ze = _headers(client, "ze.admin.cardapio")
    resp = client.patch(
        f"/pedidos/{pedido_teste.id}/status",
        json={"novo_status": "EM_PREPARACAO"},
        headers=headers_ze,
    )
    assert resp.status_code == 404