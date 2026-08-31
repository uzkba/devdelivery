from datetime import timedelta

import pytest
from jose import jwt

from app.core.seguranca import (
    ALGORITHM,
    SECRET_KEY,
    JWTError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# security.py isolado (não precisa de banco nem da API no ar)
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_password_gera_hash_diferente_da_senha_original(self):
        senha = "minhaSenha123"
        hashed = hash_password(senha)
        assert hashed != senha
        assert hashed.startswith("$2b$")

    def test_verify_password_aceita_senha_correta(self):
        senha = "minhaSenha123"
        hashed = hash_password(senha)
        assert verify_password(senha, hashed) is True

    def test_verify_password_rejeita_senha_errada(self):
        hashed = hash_password("minhaSenha123")
        assert verify_password("senhaErrada", hashed) is False


class TestJWT:
    def test_create_access_token_gera_token_decodificavel(self):
        token = create_access_token(data={"sub": "user-123", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"

    def test_token_expirado_lanca_jwt_error(self):
        token = create_access_token(
            data={"sub": "user-123"}, expires_delta=timedelta(minutes=-1)
        )
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_token_com_assinatura_invalida_lanca_jwt_error(self):
        token_forjado = jwt.encode({"sub": "invasor"}, "chave-errada", algorithm=ALGORITHM)
        with pytest.raises(JWTError):
            decode_access_token(token_forjado)


# ---------------------------------------------------------------------------
# Rotas /auth/login e /auth/me (usam a fixture `client`, que roda dentro da
# transação de teste do Postgres real e faz rollback automático no final)
# ---------------------------------------------------------------------------
class TestLogin:
    def test_login_com_credenciais_corretas_retorna_token(self, client, admin_user):
        response = client.post(
            "/auth/login/admin",
            json={"login": "maria.admin", "password": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_retornado_contem_claims_corretos(self, client, admin_user):
        response = client.post(
            "/auth/login/admin",
            json={"login": "maria.admin", "password": "senha123"},
        )
        token = response.json()["access_token"]
        payload = decode_access_token(token)

        assert payload["sub"] == str(admin_user.id)
        assert payload["role"] == "admin"
        assert payload["restaurant_id"] == str(admin_user.restaurant_id)

    def test_login_com_senha_errada_retorna_401(self, client, admin_user):
        response = client.post(
            "/auth/login/admin",
            json={"login": "maria.admin", "password": "senhaErrada"},
        )
        assert response.status_code == 401

    def test_login_com_usuario_inexistente_retorna_401(self, client):
        response = client.post(
            "/auth/login/admin",
            json={"login": "nao.existe", "password": "qualquer"},
        )
        assert response.status_code == 401

    def test_login_de_usuario_inativo_retorna_403(self, client, inactive_admin_user):
        response = client.post(
            "/auth/login/admin",
            json={"login": "joao.inativo", "password": "senha123"},
        )
        assert response.status_code == 403

    def test_login_sem_campo_password_retorna_422(self, client):
        response = client.post("/auth/login/admin", json={"login": "maria.admin"})
        assert response.status_code == 422


class TestMe:
    def test_me_com_token_valido_retorna_dados_do_usuario(self, client, admin_user):
        login_response = client.post(
            "/auth/login/admin",
            json={"login": "maria.admin", "password": "senha123"},
        )
        token = login_response.json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["login"] == "maria.admin"

    def test_me_sem_token_retorna_401(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_com_token_invalido_retorna_401(self, client):
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer token.invalido.aqui"}
        )
        assert response.status_code == 401