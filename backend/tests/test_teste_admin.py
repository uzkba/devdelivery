# backend/tests/test_teste_admin.py
from backend.app.core.seguranca import create_access_token


def _gerar_token(user):
    """Monta um token com os mesmos claims que o /auth/login gera."""
    return create_access_token(
        data={
            "sub": str(user.id),
            "login": user.login,
            "name": user.name,
            "role": user.role,
            "restaurant_id": str(user.restaurant_id),
        }
    )


class TestTesteAdmin:
    def test_sem_token_retorna_401(self, client):
        response = client.get("/teste-admin")
        assert response.status_code == 401

    def test_token_invalido_retorna_401(self, client):
        response = client.get(
            "/teste-admin",
            headers={"Authorization": "Bearer token-invalido-qualquer"},
        )
        assert response.status_code == 401

    def test_role_sem_permissao_retorna_403(self, client, inactive_admin_user):
        # reaproveitando esse fixture só pela role="atendente";
        # is_active não importa aqui, pois /teste-admin não consulta o banco
        token = _gerar_token(inactive_admin_user)
        response = client.get(
            "/teste-admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_role_admin_retorna_200(self, client, admin_user):
        token = _gerar_token(admin_user)
        response = client.get(
            "/teste-admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "Maria Admin" in response.json()["mensagem"]