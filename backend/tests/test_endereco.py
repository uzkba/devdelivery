import uuid


def _login(client, login, password="senha123"):
    response = client.post("/auth/login/admin", json={"login": login, "password": password})
    return response.json()["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


ENDERECO_PAYLOAD = {
    "street": "Rua das Flores",
    "number": "123",
    "neighborhood": "Centro",
    "latitude": -23.5505,
    "longitude": -46.6333,
}


class TestCriarEnderecoStaff:
    def test_criar_endereco_sem_token_retorna_401(self, client, cliente):
        response = client.post(f"/clientes/{cliente.id}/enderecos/", json=ENDERECO_PAYLOAD)
        assert response.status_code == 401

    def test_criar_endereco_role_nao_permitida_retorna_403(self, client, cliente, entregador_user):
        token = _login(client, "pedro.entregador")
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token)
        )
        assert response.status_code == 403

    def test_criar_endereco_com_role_admin_sucesso(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token)
        )
        assert response.status_code == 201
        data = response.json()
        assert data["street"] == "Rua das Flores"
        assert data["client_id"] == str(cliente.id)

    def test_criar_endereco_com_role_atendente_sucesso(self, client, cliente, atendente_user):
        token = _login(client, "ana.atendente")
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token)
        )
        assert response.status_code == 201

    def test_criar_endereco_com_role_caixa_sucesso(self, client, cliente, caixa_user):
        token = _login(client, "carlos.caixa")
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token)
        )
        assert response.status_code == 201

    def test_criar_endereco_cliente_inexistente_retorna_404(self, client, admin_user):
        token = _login(client, "maria.admin")
        response = client.post(
            f"/clientes/{uuid.uuid4()}/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token)
        )
        assert response.status_code == 404

    def test_criar_dois_enderecos_principais_retorna_409(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        client.post(
            f"/clientes/{cliente.id}/enderecos/",
            json={**ENDERECO_PAYLOAD, "street": "Rua A", "primary_address": True},
            headers=_auth_header(token),
        )
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/",
            json={**ENDERECO_PAYLOAD, "street": "Rua B", "primary_address": True},
            headers=_auth_header(token),
        )
        assert response.status_code == 409

    def test_criar_endereco_sem_campos_obrigatorios_retorna_422(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.post(
            f"/clientes/{cliente.id}/enderecos/", json={}, headers=_auth_header(token)
        )
        assert response.status_code == 422


class TestListarEnderecosStaff:
    def test_listar_sem_token_retorna_401(self, client, cliente):
        response = client.get(f"/clientes/{cliente.id}/enderecos/")
        assert response.status_code == 401

    def test_listar_com_role_admin_retorna_200(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.get(f"/clientes/{cliente.id}/enderecos/", headers=_auth_header(token))
        assert response.status_code == 200

    def test_listar_com_role_atendente_retorna_200(self, client, cliente, atendente_user):
        token = _login(client, "ana.atendente")
        response = client.get(f"/clientes/{cliente.id}/enderecos/", headers=_auth_header(token))
        assert response.status_code == 200

    def test_listar_com_role_caixa_retorna_200(self, client, cliente, caixa_user):
        token = _login(client, "carlos.caixa")
        response = client.get(f"/clientes/{cliente.id}/enderecos/", headers=_auth_header(token))
        assert response.status_code == 200

    def test_listar_com_role_nao_permitida_retorna_403(self, client, cliente, entregador_user):
        token = _login(client, "pedro.entregador")
        response = client.get(f"/clientes/{cliente.id}/enderecos/", headers=_auth_header(token))
        assert response.status_code == 403

    def test_listar_cliente_inexistente_retorna_404(self, client, admin_user):
        token = _login(client, "maria.admin")
        response = client.get(f"/clientes/{uuid.uuid4()}/enderecos/", headers=_auth_header(token))
        assert response.status_code == 404


class TestAtualizarEnderecoStaff:
    def test_atualizar_sem_token_retorna_401(self, client, cliente, endereco):
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}", json={"neighborhood": "Novo Bairro"}
        )
        assert response.status_code == 401

    def test_atualizar_role_nao_permitida_retorna_403(self, client, cliente, endereco, entregador_user):
        token = _login(client, "pedro.entregador")
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}",
            json={"neighborhood": "Novo Bairro"},
            headers=_auth_header(token),
        )
        assert response.status_code == 403

    def test_atualizar_endereco_sucesso(self, client, cliente, endereco, admin_user):
        token = _login(client, "maria.admin")
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}",
            json={"neighborhood": "Novo Bairro"},
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        assert response.json()["neighborhood"] == "Novo Bairro"

    def test_atualizar_endereco_inexistente_retorna_404(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{uuid.uuid4()}",
            json={"neighborhood": "X"},
            headers=_auth_header(token),
        )
        assert response.status_code == 404

    def test_atualizar_endereco_de_outro_cliente_retorna_404(self, client, outro_cliente, endereco, admin_user):
        token = _login(client, "maria.admin")
        response = client.put(
            f"/clientes/{outro_cliente.id}/enderecos/{endereco.id}",
            json={"neighborhood": "X"},
            headers=_auth_header(token),
        )
        assert response.status_code == 404

    def test_atualizar_para_endereco_principal_conflitante_retorna_409(
        self, client, cliente, endereco, endereco_secundario, admin_user
    ):
        token = _login(client, "maria.admin")
        response = client.put(
            f"/clientes/{cliente.id}/enderecos/{endereco_secundario.id}",
            json={"primary_address": True},
            headers=_auth_header(token),
        )
        assert response.status_code == 409


class TestDeletarEnderecoStaff:
    def test_deletar_sem_token_retorna_401(self, client, cliente, endereco):
        response = client.delete(f"/clientes/{cliente.id}/enderecos/{endereco.id}")
        assert response.status_code == 401

    def test_deletar_role_nao_permitida_retorna_403(self, client, cliente, endereco, entregador_user):
        token = _login(client, "pedro.entregador")
        response = client.delete(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}", headers=_auth_header(token)
        )
        assert response.status_code == 403

    def test_deletar_endereco_sucesso(self, client, cliente, endereco, admin_user):
        token = _login(client, "maria.admin")
        response = client.delete(
            f"/clientes/{cliente.id}/enderecos/{endereco.id}", headers=_auth_header(token)
        )
        assert response.status_code == 204

    def test_deletar_endereco_inexistente_retorna_404(self, client, cliente, admin_user):
        token = _login(client, "maria.admin")
        response = client.delete(
            f"/clientes/{cliente.id}/enderecos/{uuid.uuid4()}", headers=_auth_header(token)
        )
        assert response.status_code == 404


class TestListarMeusEnderecos:
    def test_listar_sem_token_retorna_401(self, client):
        response = client.get("/clientes/me/enderecos/")
        assert response.status_code == 401

    def test_listar_retorna_apenas_os_proprios_enderecos(
        self, client, cliente, endereco, endereco_secundario, outro_cliente, token_para_cliente
    ):
        token = token_para_cliente(cliente)
        response = client.get("/clientes/me/enderecos/", headers=_auth_header(token))
        assert response.status_code == 200
        ids = {e["id"] for e in response.json()}
        assert ids == {str(endereco.id), str(endereco_secundario.id)}


class TestCriarMeuEndereco:
    def test_criar_sem_token_retorna_401(self, client):
        response = client.post("/clientes/me/enderecos/", json=ENDERECO_PAYLOAD)
        assert response.status_code == 401

    def test_criar_sucesso(self, client, cliente, token_para_cliente):
        token = token_para_cliente(cliente)
        response = client.post("/clientes/me/enderecos/", json=ENDERECO_PAYLOAD, headers=_auth_header(token))
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == str(cliente.id)


class TestAtualizarMeuEndereco:
    def test_atualizar_sem_token_retorna_401(self, client, endereco):
        response = client.put(f"/clientes/me/enderecos/{endereco.id}", json={"neighborhood": "X"})
        assert response.status_code == 401

    def test_atualizar_endereco_proprio_sucesso(self, client, cliente, endereco, token_para_cliente):
        token = token_para_cliente(cliente)
        response = client.put(
            f"/clientes/me/enderecos/{endereco.id}",
            json={"neighborhood": "Novo Bairro"},
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        assert response.json()["neighborhood"] == "Novo Bairro"

    def test_atualizar_endereco_de_outro_cliente_retorna_404(
        self, client, endereco, outro_cliente, token_para_cliente
    ):
        token = token_para_cliente(outro_cliente)
        response = client.put(
            f"/clientes/me/enderecos/{endereco.id}",
            json={"neighborhood": "X"},
            headers=_auth_header(token),
        )
        assert response.status_code == 404

    def test_atualizar_endereco_inexistente_retorna_404(self, client, cliente, token_para_cliente):
        token = token_para_cliente(cliente)
        response = client.put(
            f"/clientes/me/enderecos/{uuid.uuid4()}",
            json={"neighborhood": "X"},
            headers=_auth_header(token),
        )
        assert response.status_code == 404


class TestDeletarMeuEndereco:
    def test_deletar_sem_token_retorna_401(self, client, endereco):
        response = client.delete(f"/clientes/me/enderecos/{endereco.id}")
        assert response.status_code == 401

    def test_deletar_endereco_proprio_sucesso(self, client, cliente, endereco, token_para_cliente):
        token = token_para_cliente(cliente)
        response = client.delete(f"/clientes/me/enderecos/{endereco.id}", headers=_auth_header(token))
        assert response.status_code == 204

    def test_deletar_endereco_de_outro_cliente_retorna_404(
        self, client, endereco, outro_cliente, token_para_cliente
    ):
        token = token_para_cliente(outro_cliente)
        response = client.delete(f"/clientes/me/enderecos/{endereco.id}", headers=_auth_header(token))
        assert response.status_code == 404


class TestDefinirMeuEnderecoPadrao:
    def test_definir_padrao_sem_token_retorna_401(self, client, endereco_secundario):
        response = client.patch(f"/clientes/me/enderecos/{endereco_secundario.id}/padrao")
        assert response.status_code == 401

    def test_definir_padrao_promove_e_despromove_atomicamente(
        self, client, cliente, endereco, endereco_secundario, token_para_cliente
    ):
        token = token_para_cliente(cliente)
        response = client.patch(
            f"/clientes/me/enderecos/{endereco_secundario.id}/padrao", headers=_auth_header(token)
        )
        assert response.status_code == 200
        assert response.json()["primary_address"] is True

        listagem = client.get("/clientes/me/enderecos/", headers=_auth_header(token))
        principais = [e for e in listagem.json() if e["primary_address"]]
        assert len(principais) == 1
        assert principais[0]["id"] == str(endereco_secundario.id)

    def test_definir_padrao_endereco_de_outro_cliente_retorna_404(
        self, client, endereco, outro_cliente, token_para_cliente
    ):
        token = token_para_cliente(outro_cliente)
        response = client.patch(f"/clientes/me/enderecos/{endereco.id}/padrao", headers=_auth_header(token))
        assert response.status_code == 404