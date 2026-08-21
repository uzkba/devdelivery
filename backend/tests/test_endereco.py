import uuid


def _login(client, login, password="senha123"):
    response = client.post("/auth/login", json={"login": login, "password": password})
    return response.json()["access_token"]


class TestCriarEndereco:
    def test_criar_endereco_sucesso(self, client, cliente):
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/",
            json={"street": "Rua das Flores", "number": "123", "neighborhood": "Centro"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["street"] == "Rua das Flores"
        assert data["client_id"] == str(cliente.id)

    def test_criar_endereco_cliente_inexistente_retorna_404(self, client):
        response = client.post(
            f"/clientes/{uuid.uuid4()}/enderecos/",
            json={"street": "Rua X", "number": "1", "neighborhood": "Bairro"},
        )
        assert response.status_code == 404

    def test_criar_dois_enderecos_principais_retorna_409(self, client, cliente):
        client.post(
            f"/clientes/{cliente.id}/enderecos/",
            json={"street": "Rua A", "number": "1", "neighborhood": "B1", "primary_address": True},
        )
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/",
            json={"street": "Rua B", "number": "2", "neighborhood": "B2", "primary_address": True},
        )
        assert response.status_code == 409

    def test_criar_endereco_sem_campos_obrigatorios_retorna_422(self, client, cliente):
        response = client.post(f"/clientes/{cliente.id}/enderecos/", json={})
        assert response.status_code == 422


class TestListarEnderecos:
    def test_listar_sem_token_retorna_401(self, client, cliente):
        response = client.get(f"/clientes/{cliente.id}/enderecos/")
        assert response.status_code == 401

    def test_listar_com_role_admin_retorna_200(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.get(
            f"/clientes/{cliente.id}/enderecos/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_listar_com_role_atendente_retorna_200(self, client, cliente, atendente_user):
        token = _login(client, "ana.atendente")
        response = client.get(
            f"/clientes/{cliente.id}/enderecos/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_listar_com_role_caixa_retorna_200(self, client, cliente, caixa_user):
        token = _login(client, "carlos.caixa")
        response = client.get(
            f"/clientes/{cliente.id}/enderecos/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_listar_com_role_nao_permitida_retorna_403(self, client, cliente, entregador_user):
        token = _login(client, "pedro.entregador")
        response = client.get(
            f"/clientes/{cliente.id}/enderecos/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_listar_cliente_inexistente_retorna_404(self, client, admin_user):
        token = _login(client, "maria.admin")
        response = client.get(
            f"/clientes/{uuid.uuid4()}/enderecos/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestAtualizarEndereco:
    def test_atualizar_endereco_sucesso(self, client, cliente, endereco):
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}",
            json={"neighborhood": "Novo Bairro"},
        )
        assert response.status_code == 200
        assert response.json()["neighborhood"] == "Novo Bairro"

    def test_atualizar_endereco_inexistente_retorna_404(self, client, cliente):
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{uuid.uuid4()}",
            json={"neighborhood": "X"},
        )
        assert response.status_code == 404

    def test_atualizar_endereco_de_outro_cliente_retorna_404(self, client, outro_cliente, endereco):
        response = client.put(
            f"/clientes/{outro_cliente.id}/enderecos/{endereco.id}",
            json={"neighborhood": "X"},
        )
        assert response.status_code == 404

    def test_atualizar_para_endereco_principal_conflitante_retorna_409(
        self, client, cliente, endereco, endereco_secundario
    ):
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco_secundario.id}",
            json={"primary_address": True},
        )
        assert response.status_code == 409


class TestDeletarEndereco:
    def test_deletar_endereco_sucesso(self, client, cliente, endereco):
        response = client.delete(f"/clientes/{cliente.id}/enderecos/{endereco.id}")
        assert response.status_code == 204

    def test_deletar_endereco_inexistente_retorna_404(self, client, cliente):
        response = client.delete(f"/clientes/{cliente.id}/enderecos/{uuid.uuid4()}")
        assert response.status_code == 404