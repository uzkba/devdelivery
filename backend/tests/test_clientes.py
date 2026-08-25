from backend.app.core.seguranca import create_access_token
from backend.app.model.models import Client
from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError


def cliente_payload(phone="11999990001"):
    return {"name": "João Silva", "phone": phone}


def token_para(user) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "login": user.login,
            "name": user.name,
            "role": user.role,
            "restaurant_id": str(user.restaurant_id),
        }
    )


def auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {token_para(user)}"}


def test_criar_cliente_com_sucesso(client, db, admin_user):
    response = client.post(
        "/clientes/", json=cliente_payload(), headers=auth_headers(admin_user)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == "11999990001"
    assert data["is_active"] is True

    criado = db.query(Client).filter(Client.phone == "11999990001").first()
    assert criado is not None


def test_criar_cliente_telefone_duplicado(client, admin_user):
    client.post("/clientes/", json=cliente_payload(), headers=auth_headers(admin_user))
    response = client.post(
        "/clientes/", json=cliente_payload(), headers=auth_headers(admin_user)
    )
    assert response.status_code in (400, 409)


def test_criar_cliente_nome_vazio(client, admin_user):
    payload = cliente_payload()
    payload["name"] = ""
    response = client.post("/clientes/", json=payload, headers=auth_headers(admin_user))
    assert response.status_code == 422


def test_criar_cliente_campo_faltando(client, admin_user):
    payload = cliente_payload()
    del payload["name"]
    response = client.post("/clientes/", json=payload, headers=auth_headers(admin_user))
    assert response.status_code == 422


def test_criar_cliente_sem_token_bloqueia(client):
    response = client.post("/clientes/", json=cliente_payload())
    assert response.status_code == 401

def test_criar_cliente_usuario_inativo_bloqueia(client, inactive_admin_user):
    response = client.post(
        "/clientes/", json=cliente_payload(), headers=auth_headers(inactive_admin_user)
    )
    assert response.status_code == 403