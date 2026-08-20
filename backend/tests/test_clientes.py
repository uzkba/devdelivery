# backend/tests/test_clientes.py
from backend.app.model.models import Client


def cliente_payload(phone="11999990001"):
    return {"name": "João Silva", "phone": phone}


def test_criar_cliente_com_sucesso(client, db):
    response = client.post("/clientes/", json=cliente_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == "11999990001"
    assert data["is_active"] is True
    assert "id" in data

    # confirma que realmente foi pro banco (dentro da transação de teste)
    criado = db.query(Client).filter(Client.phone == "11999990001").first()
    assert criado is not None
    assert criado.name == "João Silva"


def test_criar_cliente_telefone_duplicado(client):
    client.post("/clientes/", json=cliente_payload())
    response = client.post("/clientes/", json=cliente_payload())  # mesmo telefone
    assert response.status_code in (400, 409)


def test_criar_cliente_nome_vazio(client):
    payload = cliente_payload()
    payload["name"] = ""
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 422


def test_criar_cliente_campo_faltando(client):
    payload = cliente_payload()
    del payload["name"]
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 422


def test_criar_cliente_sem_admin_bloqueia():
    """
    Placeholder: fake_admin_dependency sempre libera, então não dá pra
    testar bloqueio real ainda. Quando o middleware de admin verdadeiro
    for integrado, reescreva usando as fixtures `admin_user`/token real
    para checar 401/403 sem token.
    """
    pass