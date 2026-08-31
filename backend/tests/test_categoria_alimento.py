"""
tests/test_categoria_alimento.py

Segue o padrão real de autenticação usado em test_autenticacao.py:
POST /auth/login com {login, password} -> {access_token, token_type},
depois Authorization: Bearer <token> nas chamadas autenticadas.

Reaproveita as fixtures já existentes no conftest.py (client, db,
restaurante, admin_user). Para os testes de isolamento entre restaurantes,
defini localmente `outro_restaurante` e `outro_admin_user` — se preferir,
dá pra mover essas duas fixtures para o conftest.py compartilhado depois.
"""
import uuid

import pytest

from app.core.seguranca import hash_password
from app.model.models import AdminUser, Restaurant


# ---------------------------------------------------------------------------
# fixtures locais (segundo restaurante, para testar isolamento multi-tenant)
# ---------------------------------------------------------------------------
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
        login="ze.admin",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _headers(client, login: str, password: str = "senha123") -> dict:
    response = client.post("/auth/login/admin", json={"login": login, "password": password})
    assert response.status_code == 200, f"login falhou para {login}: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _payload(nome="Bebidas", descricao="Sucos, refrigerantes e água", ordem_exibicao=0):
    return {"nome": nome, "descricao": descricao, "ordem_exibicao": ordem_exibicao}


# ---------------------------------------------------------------------------
class TestCriarCategoria:
    def test_criar_categoria_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/categorias", json=_payload(), headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Bebidas"
        assert data["descricao"] == "Sucos, refrigerantes e água"
        assert data["ativo"] is True
        assert "id" in data

    def test_criar_categoria_sem_nome_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/categorias", json={"descricao": "sem nome"}, headers=headers)
        assert response.status_code == 422

    def test_criar_categoria_com_nome_vazio_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/categorias", json=_payload(nome="   "), headers=headers)
        assert response.status_code == 422

    def test_criar_categoria_com_nome_duplicado_no_mesmo_restaurante_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/categorias", json=_payload(nome="Sobremesas"), headers=headers)
        response = client.post("/categorias", json=_payload(nome="Sobremesas"), headers=headers)
        assert response.status_code == 400
        assert "já existe" in response.json()["detail"].lower()

    def test_nome_duplicado_case_insensitive_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/categorias", json=_payload(nome="Pratos Principais"), headers=headers)
        response = client.post("/categorias", json=_payload(nome="pratos principais"), headers=headers)
        assert response.status_code == 400

    def test_mesmo_nome_em_restaurantes_diferentes_e_permitido(self, client, admin_user, outro_admin_user):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin")

        r1 = client.post("/categorias", json=_payload(nome="Bebidas"), headers=headers_a)
        r2 = client.post("/categorias", json=_payload(nome="Bebidas"), headers=headers_b)
        assert r1.status_code == 201
        assert r2.status_code == 201

    def test_criar_categoria_sem_autenticacao_falha(self, client):
        response = client.post("/categorias", json=_payload())
        assert response.status_code == 401

    def test_criar_categoria_role_sem_permissao_falha(self, client, db, restaurante):
        atendente = AdminUser(
            restaurant_id=restaurante.id,
            name="Ana Atendente",
            login="ana.atendente.cat",
            password_hash=hash_password("senha123"),
            role="atendente",
            is_active=True,
        )
        db.add(atendente)
        db.flush()

        headers = _headers(client, "ana.atendente.cat")
        response = client.post("/categorias", json=_payload(), headers=headers)
        assert response.status_code == 403


class TestListarCategorias:
    def test_listar_categorias_retorna_criadas(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/categorias", json=_payload(nome="Entradas"), headers=headers)
        client.post("/categorias", json=_payload(nome="Sobremesas"), headers=headers)

        response = client.get("/categorias", headers=headers)
        assert response.status_code == 200
        nomes = [c["nome"] for c in response.json()]
        assert "Entradas" in nomes
        assert "Sobremesas" in nomes

    def test_listar_apenas_ativas_oculta_removidas(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(nome="Bebidas Quentes"), headers=headers).json()
        client.delete(f"/categorias/{criada['id']}", headers=headers)

        response = client.get("/categorias?apenas_ativas=true", headers=headers)
        nomes = [c["nome"] for c in response.json()]
        assert "Bebidas Quentes" not in nomes

        response_todas = client.get("/categorias", headers=headers)
        nomes_todas = [c["nome"] for c in response_todas.json()]
        assert "Bebidas Quentes" in nomes_todas

    def test_nao_ve_categorias_de_outro_restaurante(self, client, admin_user, outro_admin_user):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin")

        client.post("/categorias", json=_payload(nome="Categoria Do Outro"), headers=headers_b)
        response = client.get("/categorias", headers=headers_a)
        nomes = [c["nome"] for c in response.json()]
        assert "Categoria Do Outro" not in nomes


class TestBuscarCategoriaPorId:
    def test_buscar_categoria_existente(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(), headers=headers).json()

        response = client.get(f"/categorias/{criada['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == criada["id"]

    def test_buscar_categoria_inexistente_retorna_404(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.get(f"/categorias/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    def test_buscar_categoria_de_outro_restaurante_retorna_404(self, client, admin_user, outro_admin_user):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin")

        criada = client.post("/categorias", json=_payload(), headers=headers_b).json()
        response = client.get(f"/categorias/{criada['id']}", headers=headers_a)
        assert response.status_code == 404


class TestAtualizarCategoria:
    def test_atualizar_nome_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(nome="Lanches"), headers=headers).json()

        response = client.put(
            f"/categorias/{criada['id']}", json={"nome": "Lanches Rápidos"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["nome"] == "Lanches Rápidos"

    def test_atualizar_ordem_exibicao(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(), headers=headers).json()

        response = client.put(f"/categorias/{criada['id']}", json={"ordem_exibicao": 5}, headers=headers)
        assert response.status_code == 200
        assert response.json()["ordem_exibicao"] == 5

    def test_atualizar_para_nome_ja_existente_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        client.post("/categorias", json=_payload(nome="Massas"), headers=headers)
        criada = client.post("/categorias", json=_payload(nome="Pizzas"), headers=headers).json()

        response = client.put(f"/categorias/{criada['id']}", json={"nome": "Massas"}, headers=headers)
        assert response.status_code == 400

    def test_atualizar_nome_vazio_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(), headers=headers).json()

        response = client.put(f"/categorias/{criada['id']}", json={"nome": "  "}, headers=headers)
        assert response.status_code == 422


class TestRemoverCategoria:
    def test_remover_categoria_marca_como_inativa(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        criada = client.post("/categorias", json=_payload(nome="Grelhados"), headers=headers).json()

        response = client.delete(f"/categorias/{criada['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["ativo"] is False

        busca = client.get(f"/categorias/{criada['id']}", headers=headers)
        assert busca.status_code == 200
        assert busca.json()["ativo"] is False

    def test_remover_categoria_inexistente_retorna_404(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.delete(f"/categorias/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404