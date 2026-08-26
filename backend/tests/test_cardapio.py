"""
tests/test_cardapio.py

Segue o padrão real de autenticação usado em test_categoria_alimento.py:
POST /auth/login com {login, password} -> {access_token, token_type},
depois Authorization: Bearer <token> nas chamadas autenticadas.

Reaproveita as fixtures já existentes no conftest.py (client, db, restaurante,
admin_user, atendente_user, caixa_user, entregador_user,
inactive_admin_with_admin_role).
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.core.seguranca import create_access_token, hash_password
from backend.app.model.models import AdminUser, AuditLog, Food, FoodCategory, Menu, MenuItem, Restaurant

RESTAURANTE_ID_PADRAO = uuid.UUID("00000000-0000-0000-0000-000000000000")


def _headers(client, login: str, password: str = "senha123") -> dict:
    response = client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, f"login falhou para {login}: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _headers_via_token_direto(user) -> dict:
    token = create_access_token(
        data={
            "sub": str(user.id),
            "login": user.login,
            "name": user.name,
            "role": user.role,
            "restaurant_id": str(user.restaurant_id),
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# fixtures locais (cardápio do dia)
# ---------------------------------------------------------------------------
@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Carnes", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def alimento(db, restaurante, categoria):
    a = Food(
        restaurant_id=restaurante.id,
        category_id=categoria.id,
        name="Frango grelhado",
        base_price=Decimal("18.90"),
    )
    db.add(a)
    db.flush()
    db.refresh(a)
    return a


@pytest.fixture()
def cardapio_hoje(db, restaurante):
    m = Menu(restaurant_id=restaurante.id, date=date.today())
    db.add(m)
    db.flush()
    db.refresh(m)
    return m


@pytest.fixture()
def item_cardapio(db, cardapio_hoje, alimento):
    item = MenuItem(menu_id=cardapio_hoje.id, food_id=alimento.id, is_available=True)
    db.add(item)
    db.flush()
    db.refresh(item)
    return item

# ---------------------------------------------------------------------------
class TestAlterarDisponibilidade:
    def _url(self, cardapio_hoje, item_cardapio) -> str:
        return f"/cardapio/{cardapio_hoje.id}/itens/{item_cardapio.id}/disponibilidade"

    def test_admin_marca_item_indisponivel(self, client, admin_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "maria.admin")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_available"] is False
        assert data["id"] == str(item_cardapio.id)

    def test_atendente_pode_alterar(self, client, atendente_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "ana.atendente")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 200

    def test_caixa_nao_pode_alterar(self, client, caixa_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "carlos.caixa")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 403

    def test_entregador_nao_pode_alterar(self, client, entregador_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "pedro.entregador")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 403

    def test_sem_token_bloqueia(self, client, item_cardapio, cardapio_hoje):
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False})
        assert response.status_code == 401

    def test_usuario_inativo_bloqueia(self, client, inactive_admin_with_admin_role, item_cardapio, cardapio_hoje):
        headers = _headers_via_token_direto(inactive_admin_with_admin_role)
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 403

    def test_item_de_outro_cardapio_retorna_404(self, client, db, admin_user, item_cardapio, restaurante):
        outro_cardapio = Menu(restaurant_id=restaurante.id, date=date.today() - timedelta(days=1))
        db.add(outro_cardapio)
        db.flush()
        db.refresh(outro_cardapio)

        headers = _headers(client, "maria.admin")
        response = client.patch(self._url(outro_cardapio, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 404

    def test_item_inexistente_retorna_404(self, client, admin_user, cardapio_hoje):
        headers = _headers(client, "maria.admin")
        response = client.patch(
            f"/cardapio/{cardapio_hoje.id}/itens/{uuid.uuid4()}/disponibilidade",
            json={"is_available": False},
            headers=headers,
        )
        assert response.status_code == 404

    def test_nao_altera_item_de_outro_restaurante(self, client, outro_admin_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "ze.admin.cardapio")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"is_available": False}, headers=headers)
        assert response.status_code == 404

    def test_payload_invalido_retorna_422(self, client, admin_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "maria.admin")
        response = client.patch(self._url(cardapio_hoje, item_cardapio), json={"disponivel": False}, headers=headers)
        assert response.status_code == 422


class TestAuditoriaDisponibilidade:
    def test_alteracao_gera_log_auditoria(self, client, db, admin_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "maria.admin")
        client.patch(
            f"/cardapio/{cardapio_hoje.id}/itens/{item_cardapio.id}/disponibilidade",
            json={"is_available": False},
            headers=headers,
        )
        log = (
            db.query(AuditLog)
            .filter(AuditLog.entity == "cardapio_item", AuditLog.entity_id == str(item_cardapio.id))
            .first()
        )
        assert log is not None
        assert log.action == "ALTERACAO_DISPONIBILIDADE"
        assert log.previous_data == {"is_available": True}
        assert log.new_data == {"is_available": False}
        assert log.user_id == admin_user.id

    def test_valor_igual_nao_duplica_log(self, client, db, admin_user, item_cardapio, cardapio_hoje):
        headers = _headers(client, "maria.admin")
        client.patch(
            f"/cardapio/{cardapio_hoje.id}/itens/{item_cardapio.id}/disponibilidade",
            json={"is_available": True},
            headers=headers,
        )
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.entity == "cardapio_item", AuditLog.entity_id == str(item_cardapio.id))
            .all()
        )
        assert len(logs) == 0


class TestCardapioDoDia:
    def test_lista_apenas_itens_disponiveis(self, db, client):
        restaurante_padrao = Restaurant(id=RESTAURANTE_ID_PADRAO, trade_name="Restaurante Placeholder")
        db.add(restaurante_padrao)
        db.flush()

        categoria = FoodCategory(restaurant_id=restaurante_padrao.id, name="Carnes", display_order=0)
        db.add(categoria)
        db.flush()

        disponivel = Food(restaurant_id=restaurante_padrao.id, category_id=categoria.id, name="Frango", base_price=Decimal("15.00"))
        indisponivel = Food(restaurant_id=restaurante_padrao.id, category_id=categoria.id, name="Peixe", base_price=Decimal("20.00"))
        db.add_all([disponivel, indisponivel])
        db.flush()

        menu = Menu(restaurant_id=restaurante_padrao.id, date=date.today())
        db.add(menu)
        db.flush()

        db.add_all(
            [
                MenuItem(menu_id=menu.id, food_id=disponivel.id, is_available=True),
                MenuItem(menu_id=menu.id, food_id=indisponivel.id, is_available=False),
            ]
        )
        db.flush()

        response = client.get("/cardapio/hoje")
        assert response.status_code == 200
        nomes = [item["nome"] for item in response.json()["itens"]]
        assert "Frango" in nomes
        assert "Peixe" not in nomes

    def test_sem_cardapio_cadastrado_retorna_404(self, client):
        response = client.get("/cardapio/hoje")
        assert response.status_code == 404


@pytest.fixture()
def alimento_basico(db, restaurante, categoria):
    a = Food(restaurant_id=restaurante.id, category_id=categoria.id, name="Refrigerante Lata", base_price=Decimal("6"))
    db.add(a)
    db.flush()
    db.refresh(a)
    return a


@pytest.fixture()
def alimento_inativo(db, restaurante, categoria):
    a = Food(restaurant_id=restaurante.id, category_id=categoria.id, name="Suco Descontinuado", base_price=Decimal("5"), is_active=False)
    db.add(a)
    db.flush()
    db.refresh(a)
    return a


class TestCriarCardapio:
    def test_criar_cardapio_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/cardapio", json={"data": str(date.today())}, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["data"] == str(date.today())

    def test_criar_cardapio_duplicado_na_mesma_data_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        data_teste = str(date.today().replace(day=1))
        client.post("/cardapio", json={"data": data_teste}, headers=headers)
        response = client.post("/cardapio", json={"data": data_teste}, headers=headers)
        assert response.status_code == 400
        assert "já existe" in response.json()["detail"].lower()

    def test_criar_cardapio_sem_autenticacao_falha(self, client):
        response = client.post("/cardapio", json={"data": str(date.today())})
        assert response.status_code == 401


class TestBuscarCardapioNovo:
    def test_buscar_cardapio_de_outro_restaurante_retorna_404(self, client, admin_user, outro_admin_user):
        headers_a = _headers(client, "maria.admin")
        headers_b = _headers(client, "ze.admin.cardapio")

        criado = client.post("/cardapio", json={"data": str(date.today())}, headers=headers_b).json()
        response = client.get(f"/cardapio/{criado['id']}", headers=headers_a)
        assert response.status_code == 404


class TestAdicionarItensNovo:
    def test_adicionar_item_simples_funciona(self, client, admin_user, alimento_basico):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_basico.id), "preco_dia": "5.50"}]},
            headers=headers,
        )
        assert response.status_code == 201
        
        item_cadastrado = response.json()["itens"][0]
        assert item_cadastrado["alimento_id"] == str(alimento_basico.id)
        assert Decimal(item_cadastrado["preco_dia"]) == Decimal("5.50")

    def test_adicionar_alimento_inativo_falha(self, client, admin_user, alimento_inativo):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_inativo.id)}]},
            headers=headers,
        )
        assert response.status_code == 400
        assert "inativo" in response.json()["detail"].lower()

    def test_adicionar_alimento_ja_existente_no_cardapio_falha(self, client, admin_user, alimento_basico):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        client.post(f"/cardapio/{cardapio['id']}/itens", json={"itens": [{"alimento_id": str(alimento_basico.id)}]}, headers=headers)
        response = client.post(f"/cardapio/{cardapio['id']}/itens", json={"itens": [{"alimento_id": str(alimento_basico.id)}]}, headers=headers)
        
        assert response.status_code == 400
        assert "já estão cadastrados" in response.json()["detail"].lower()
        
    def test_adicionar_alimento_duplicado_no_mesmo_payload_falha(self, client, admin_user, alimento_basico):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        # Envia duas vezes o mesmo alimento na mesma requisição
        response = client.post(
            f"/cardapio/{cardapio['id']}/itens", 
            json={"itens": [
                {"alimento_id": str(alimento_basico.id)},
                {"alimento_id": str(alimento_basico.id)}
            ]}, 
            headers=headers
        )
        
        assert response.status_code == 400
        assert "mais de uma vez" in response.json()["detail"].lower()