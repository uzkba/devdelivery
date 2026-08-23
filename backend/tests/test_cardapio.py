"""
tests/test_cardapio.py

Segue o padrão real de autenticação usado em test_categoria_alimento.py:
POST /auth/login com {login, password} -> {access_token, token_type},
depois Authorization: Bearer <token> nas chamadas autenticadas.

Reaproveita as fixtures já existentes no conftest.py (client, db, restaurante,
admin_user, atendente_user, caixa_user, entregador_user,
inactive_admin_with_admin_role). Como ainda não existem fixtures de
Menu/MenuItem/Food/FoodCategory no conftest.py compartilhado, defini-as
localmente aqui (mesmo padrão de `outro_restaurante`/`outro_admin_user` em
test_categoria_alimento.py) — se preferirem, dá pra mover pro conftest.py
depois.

Nota sobre `GET /cardapio/hoje`: essa rota ainda usa um restaurante
"placeholder" fixo (RESTAURANTE_ID_PADRAO, ver TODO em cardapio_route.py),
já que não existe contexto de restaurante para rotas públicas ainda. Os
testes dessa rota criam o restaurante explicitamente com esse UUID fixo.
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
    """Gera o header de Authorization direto com create_access_token, sem passar
    por /auth/login. Necessário para simular um usuário que ficou inativo DEPOIS
    de ter um token válido emitido — /auth/login já bloqueia o login de usuário
    inativo antes de gerar token, então não dá pra testar esse caso via login
    (mesmo padrão usado em test_admin.py)."""
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
# fixtures locais (cardápio do dia com 1 item disponível + segundo
# restaurante, para testar isolamento multi-tenant)
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
        login="ze.admin.cardapio",
        password_hash=hash_password("senha123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


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
        """Isolamento multi-tenant: usuário de outro restaurante não pode
        alterar um item que pertence ao cardápio de outro restaurante."""
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
        # item já está disponível=True; enviar True de novo não deve gerar log
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
    """Testa GET /cardapio/hoje (rota pública). Como a rota ainda depende do
    RESTAURANTE_ID_PADRAO fixo (ver TODO em cardapio_route.py), o restaurante
    é criado explicitamente com esse UUID — isso deve ser revisitado quando
    o contexto de restaurante for definido de verdade (ver roadmap)."""

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

        # --- novo (task #16 — Gestão do Cardápio do Dia) --------------------------

@pytest.fixture()
def categoria_marmita(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Marmita", is_main_dish=True)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def alimento_marmita(db, restaurante, categoria_marmita):
    a = Food(restaurant_id=restaurante.id, category_id=categoria_marmita.id, name="Marmita Tradicional", base_price=Decimal("0"))
    db.add(a)
    db.flush()
    db.refresh(a)
    return a


@pytest.fixture()
def alimento_refrigerante(db, restaurante, categoria):
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


def _criar_tamanho(client, headers, nome="Grande"):
    response = client.post("/tamanhos-marmita", json={"nome": nome, "ordem_exibicao": 0}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


class TestCriarCardapio:
    def test_criar_cardapio_com_sucesso(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        response = client.post("/cardapio", json={"data": str(date.today())}, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["data"] == str(date.today())

    def test_criar_cardapio_duplicado_na_mesma_data_falha(self, client, admin_user):
        headers = _headers(client, "maria.admin")
        # já existe um cardápio de hoje criado pela fixture cardapio_hoje em
        # outros testes desta classe — usa uma data futura pra não colidir
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
    def test_adicionar_prato_principal_com_tamanho_funciona(self, client, admin_user, alimento_marmita):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()
        tamanho = _criar_tamanho(client, headers, "Grande")

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_marmita.id), "tamanho_id": tamanho["id"], "preco_dia": "25.00"}]},
            headers=headers,
        )
        assert response.status_code == 201
        itens = response.json()["itens"]
        assert itens[0]["tamanho_id"] == tamanho["id"]

    def test_adicionar_adicional_sem_tamanho_funciona(self, client, admin_user, alimento_refrigerante):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_refrigerante.id)}]},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["itens"][0]["tamanho_id"] is None

    def test_adicionar_prato_principal_sem_tamanho_falha(self, client, admin_user, alimento_marmita):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_marmita.id)}]},
            headers=headers,
        )
        assert response.status_code == 400
        assert "exige um tamanho" in response.json()["detail"].lower()

    def test_adicionar_adicional_com_tamanho_falha(self, client, admin_user, alimento_refrigerante):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()
        tamanho = _criar_tamanho(client, headers, "Grande")

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_refrigerante.id), "tamanho_id": tamanho["id"]}]},
            headers=headers,
        )
        assert response.status_code == 400
        assert "não deve ter tamanho" in response.json()["detail"].lower()

    def test_adicionar_alimento_inativo_falha(self, client, admin_user, alimento_inativo):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        response = client.post(
            f"/cardapio/{cardapio['id']}/itens",
            json={"itens": [{"alimento_id": str(alimento_inativo.id)}]},
            headers=headers,
        )
        assert response.status_code == 400

    def test_adicionar_alimento_ja_existente_no_cardapio_falha(self, client, admin_user, alimento_refrigerante):
        headers = _headers(client, "maria.admin")
        cardapio = client.post("/cardapio", json={"data": str(date.today())}, headers=headers).json()

        client.post(f"/cardapio/{cardapio['id']}/itens", json={"itens": [{"alimento_id": str(alimento_refrigerante.id)}]}, headers=headers)
        response = client.post(f"/cardapio/{cardapio['id']}/itens", json={"itens": [{"alimento_id": str(alimento_refrigerante.id)}]}, headers=headers)
        assert response.status_code == 400