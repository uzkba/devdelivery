"""
tests/test_tamanho_marmita.py

Segue o mesmo padrão de test_categoria_alimento.py: POST /auth/login para
obter o token, depois Authorization: Bearer <token>. Fixtures locais
(outro_restaurante/outro_admin_user) duplicadas do test_categoria_alimento.py
por enquanto — mover para conftest.py se quiserem centralizar depois.
"""
import uuid

import pytest

from backend.app.core.seguranca import hash_password
from backend.app.model.models import AdminUser, FoodCategory, Restaurant


@pytest.fixture()
def outro_restaurante(db):
    r = Restaurant(trade_name="Marmitas do Zé")
    db.add(r)
    db.flush()
    db.refresh(r)
    return r


@pytest.fixture()
def outro_admin_user(db, outro_restaurante):
    user = AdminUser(
        restaurant_id=outro_restaurante.id,
        name="Zé Admin",
        login="ze.admin.tamanho",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture()
def categoria_prato_principal(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Marmita", is_main_dish=True)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def categoria_adicional(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Proteína", is_main_dish=False)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def _headers(client, login: str, password: str = "senha123") -> dict:
    response = client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, f"login falhou para {login}: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _payload(nome="Grande", ordem_exibicao=0):
    return {"nome": nome, "ordem_exibicao": ordem_exibicao}


class TestCriarTamanho:
    def test_criar_tamanho_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/tamanhos-marmita", json=_payload(), headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Grande"
        assert data["ativo"] is True

    def test_criar_tamanho_com_nome_duplicado_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/tamanhos-marmita", json=_payload(nome="Pequena"), headers=headers)
        response = client.post("/tamanhos-marmita", json=_payload(nome="Pequena"), headers=headers)
        assert response.status_code == 400

    def test_nome_duplicado_case_insensitive_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/tamanhos-marmita", json=_payload(nome="Média"), headers=headers)
        response = client.post("/tamanhos-marmita", json=_payload(nome="média"), headers=headers)
        assert response.status_code == 400

    def test_mesmo_nome_em_restaurantes_diferentes_e_permitido(
        self, client, admin_user, outro_admin_user
    ):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin.tamanho")

        r1 = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers_a)
        r2 = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers_b)
        assert r1.status_code == 201
        assert r2.status_code == 201

    def test_criar_tamanho_sem_autenticacao_falha(self, client):
        response = client.post("/tamanhos-marmita", json=_payload())
        assert response.status_code == 401


class TestListarTamanhos:
    def test_listar_tamanhos_retorna_criados(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/tamanhos-marmita", json=_payload(nome="Pequena"), headers=headers)
        client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers)

        response = client.get("/tamanhos-marmita", headers=headers)
        assert response.status_code == 200
        nomes = [t["nome"] for t in response.json()]
        assert "Pequena" in nomes
        assert "Grande" in nomes

    def test_listar_apenas_ativos_oculta_removidos(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criado = client.post("/tamanhos-marmita", json=_payload(nome="Média"), headers=headers).json()
        client.delete(f"/tamanhos-marmita/{criado['id']}", headers=headers)

        response = client.get("/tamanhos-marmita?apenas_ativos=true", headers=headers)
        nomes = [t["nome"] for t in response.json()]
        assert "Média" not in nomes

        response_todos = client.get("/tamanhos-marmita", headers=headers)
        nomes_todos = [t["nome"] for t in response_todos.json()]
        assert "Média" in nomes_todos

    def test_nao_ve_tamanhos_de_outro_restaurante(self, client, admin_user, outro_admin_user):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin.tamanho")

        client.post("/tamanhos-marmita", json=_payload(nome="Tamanho Do Outro"), headers=headers_b)
        response = client.get("/tamanhos-marmita", headers=headers_a)
        nomes = [t["nome"] for t in response.json()]
        assert "Tamanho Do Outro" not in nomes


class TestAtualizarTamanho:
    def test_atualizar_nome_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criado = client.post("/tamanhos-marmita", json=_payload(nome="P"), headers=headers).json()

        response = client.put(f"/tamanhos-marmita/{criado['id']}", json={"nome": "Pequena"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["nome"] == "Pequena"

    def test_atualizar_para_nome_ja_existente_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/tamanhos-marmita", json=_payload(nome="Pequena"), headers=headers)
        criado = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers).json()

        response = client.put(f"/tamanhos-marmita/{criado['id']}", json={"nome": "Pequena"}, headers=headers)
        assert response.status_code == 400


class TestRemoverTamanho:
    def test_remover_marca_como_inativo(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criado = client.post("/tamanhos-marmita", json=_payload(nome="Extra Grande"), headers=headers).json()

        response = client.delete(f"/tamanhos-marmita/{criado['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["ativo"] is False

    def test_remover_inexistente_retorna_404(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.delete(f"/tamanhos-marmita/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404


class TestLimites:
    def test_definir_limite_com_sucesso(self, client, admin_user, categoria_adicional):
        headers = _headers(client, "maria.admin")
        tamanho = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers).json()

        response = client.post(
            f"/tamanhos-marmita/{tamanho['id']}/limites",
            json={"categoria_id": str(categoria_adicional.id), "quantidade_maxima": 2},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["categoria_id"] == str(categoria_adicional.id)
        assert data["quantidade_maxima"] == 2

    def test_definir_limite_e_upsert(self, client, admin_user, categoria_adicional):
        headers = _headers(client, "maria.admin")
        tamanho = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers).json()

        client.post(
            f"/tamanhos-marmita/{tamanho['id']}/limites",
            json={"categoria_id": str(categoria_adicional.id), "quantidade_maxima": 2},
            headers=headers,
        )
        response = client.post(
            f"/tamanhos-marmita/{tamanho['id']}/limites",
            json={"categoria_id": str(categoria_adicional.id), "quantidade_maxima": 3},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["quantidade_maxima"] == 3

        listagem = client.get(f"/tamanhos-marmita/{tamanho['id']}/limites", headers=headers)
        assert len(listagem.json()) == 1
        assert listagem.json()[0]["quantidade_maxima"] == 3

    def test_definir_limite_para_categoria_prato_principal_falha(
        self, client, admin_user, categoria_prato_principal
    ):
        headers = _headers(client, "maria.admin")
        tamanho = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers).json()

        response = client.post(
            f"/tamanhos-marmita/{tamanho['id']}/limites",
            json={"categoria_id": str(categoria_prato_principal.id), "quantidade_maxima": 1},
            headers=headers,
        )
        assert response.status_code == 400

    def test_definir_limite_categoria_de_outro_restaurante_retorna_404(
        self, client, admin_user, outro_admin_user, db, outro_restaurante
    ):
        categoria_de_outro = FoodCategory(
            restaurant_id=outro_restaurante.id, name="Sobremesa", is_main_dish=False
        )
        db.add(categoria_de_outro)
        db.flush()
        db.refresh(categoria_de_outro)

        headers = _headers(client, "maria.admin")
        tamanho = client.post("/tamanhos-marmita", json=_payload(nome="Grande"), headers=headers).json()

        response = client.post(
            f"/tamanhos-marmita/{tamanho['id']}/limites",
            json={"categoria_id": str(categoria_de_outro.id), "quantidade_maxima": 1},
            headers=headers,
        )
        assert response.status_code == 404