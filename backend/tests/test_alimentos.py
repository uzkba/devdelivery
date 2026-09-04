import uuid
import pytest
from decimal import Decimal

from app.model.models import Restaurant, AdminUser, Food, FoodCategory
from app.core.seguranca import hash_password


@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def categoria_b(db, outro_restaurante):
    c = FoodCategory(restaurant_id=outro_restaurante.id, name="Bebidas", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def criar_alimento_direto(db, categoria, **overrides):
    dados = dict(
        restaurant_id=categoria.restaurant_id,
        category_id=categoria.id,
        name="Item",
        description=None,
        base_price=Decimal("10.00"),
        is_active=True,
        is_available=True,
    )
    dados.update(overrides)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


def auth(user, token_para):
    return {"Authorization": f"Bearer {token_para(user)}"}


# ── POST /alimentos ──────────────────────────────────────────────

def test_criar_alimento_sucesso(client, categoria, admin_user, token_para):
    payload = {
        "nome": "Marmita Fitness",
        "descricao": "Frango grelhado com legumes",
        "preco_base": "24.90",
        "categoria_id": str(categoria.id),
    }
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Marmita Fitness"
    assert data["disponivel"] is True
    assert data["grupos_complemento"] == []


def test_criar_alimento_com_grupos_complemento_sucesso(client, categoria, admin_user, token_para):
    """
    NOVO TESTE: Garante que a estrutura de árvore (Food -> ModifierGroup -> ModifierOption)
    é criada corretamente através do payload aninhado.
    """
    payload = {
        "nome": "Combo Marmita P",
        "descricao": "Monte sua marmita",
        "preco_base": "15.00",
        "categoria_id": str(categoria.id),
        "grupos_complemento": [
            {
                "nome": "Escolha sua Carne",
                "escolhas_minimas": 1,
                "escolhas_maximas": 1,
                "opcoes": [
                    {"nome": "Bife Acebolado", "preco_adicional": "0.00", "disponivel": True},
                    {"nome": "Filé a Parmegiana", "preco_adicional": "4.50", "disponivel": True}
                ]
            }
        ]
    }
    
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 201
    data = resp.json()
    
    assert data["nome"] == "Combo Marmita P"
    assert len(data["grupos_complemento"]) == 1
    
    grupo = data["grupos_complemento"][0]
    assert grupo["nome"] == "Escolha sua Carne"
    assert grupo["escolhas_minimas"] == 1
    assert grupo["escolhas_maximas"] == 1
    assert len(grupo["opcoes"]) == 2
    
    opcoes_nomes = [op["nome"] for op in grupo["opcoes"]]
    assert "Bife Acebolado" in opcoes_nomes
    assert "Filé a Parmegiana" in opcoes_nomes


def test_criar_alimento_role_nao_admin_e_bloqueado(client, categoria, atendente_user, token_para):
    payload = {
        "nome": "Item",
        "descricao": None,
        "preco_base": "10.00",
        "categoria_id": str(categoria.id),
    }
    resp = client.post("/alimentos", json=payload, headers=auth(atendente_user, token_para))

    assert resp.status_code == 403


def test_criar_alimento_com_categoria_de_outro_restaurante_da_404(
    client, categoria_b, admin_user, token_para
):
    payload = {
        "nome": "Suco",
        "descricao": None,
        "preco_base": "10.00",
        "categoria_id": str(categoria_b.id),
    }
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 404


@pytest.mark.parametrize("preco", ["-0.01", "-10"])
def test_criar_alimento_preco_negativo_e_rejeitado(client, categoria, admin_user, token_para, preco):
    payload = {"nome": "Inválido", "descricao": None, "preco_base": preco, "categoria_id": str(categoria.id)}
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 422


def test_criar_alimento_preco_zero_e_aceito(client, categoria, admin_user, token_para):
    payload = {"nome": "Cortesia", "descricao": None, "preco_base": "0", "categoria_id": str(categoria.id)}
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 201


def test_criar_alimento_sem_autenticacao_e_rejeitado(client, categoria):
    payload = {"nome": "Item", "descricao": None, "preco_base": "10.00", "categoria_id": str(categoria.id)}
    resp = client.post("/alimentos", json=payload)

    assert resp.status_code == 401


# ── GET /alimentos ───────────────────────────────────────────────

def test_listar_esconde_inativos_por_padrao(client, db, categoria, admin_user, token_para):
    ativo = criar_alimento_direto(db, categoria, name="Ativo")
    inativo = criar_alimento_direto(db, categoria, name="Inativo", is_active=False)

    resp = client.get("/alimentos", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(ativo.id) in ids
    assert str(inativo.id) not in ids


def test_listar_esconde_indisponiveis_por_padrao(client, db, categoria, admin_user, token_para):
    disponivel = criar_alimento_direto(db, categoria, name="Em estoque")
    indisponivel = criar_alimento_direto(db, categoria, name="Sem estoque", is_available=False)

    resp = client.get("/alimentos", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(disponivel.id) in ids
    assert str(indisponivel.id) not in ids


def test_listar_incluir_inativos_true_traz_tudo(client, db, categoria, admin_user, token_para):
    ativo = criar_alimento_direto(db, categoria, name="Ativo")
    inativo = criar_alimento_direto(db, categoria, name="Inativo", is_active=False, is_available=False)

    resp = client.get("/alimentos?incluir_inativos=true", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(ativo.id) in ids
    assert str(inativo.id) in ids


def test_listar_filtra_por_categoria(client, db, categoria, restaurante, admin_user, token_para):
    outra = FoodCategory(restaurant_id=restaurante.id, name="Sobremesas", display_order=1)
    db.add(outra)
    db.flush()
    db.refresh(outra)

    da_categoria = criar_alimento_direto(db, categoria, name="Prato")
    de_outra = criar_alimento_direto(db, outra, name="Doce")

    resp = client.get(f"/alimentos?categoria_id={categoria.id}", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(da_categoria.id) in ids
    assert str(de_outra.id) not in ids


def test_listar_nao_traz_alimento_de_outro_restaurante(
    client, db, categoria, categoria_b, admin_user, token_para
):
    da_a = criar_alimento_direto(db, categoria, name="Do A")
    da_b = criar_alimento_direto(db, categoria_b, name="Do B")

    resp = client.get("/alimentos", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(da_a.id) in ids
    assert str(da_b.id) not in ids


# ── GET /alimentos/:id ───────────────────────────────────────────

def test_detalhar_alimento_de_outro_restaurante_da_404(client, db, categoria_b, admin_user, token_para):
    alimento_de_b = criar_alimento_direto(db, categoria_b, name="Não é seu")

    resp = client.get(f"/alimentos/{alimento_de_b.id}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404


def test_detalhar_alimento_inexistente_da_404(client, admin_user, token_para):
    resp = client.get(f"/alimentos/{uuid.uuid4()}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404


# ── PUT /alimentos/:id ────────────────────────────────────────────

def test_atualizar_alimento_sucesso(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Nome Antigo")

    resp = client.put(
        f"/alimentos/{alimento.id}",
        json={"nome": "Nome Novo", "preco_base": "15.50"},
        headers=auth(admin_user, token_para),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nome"] == "Nome Novo"
    assert Decimal(data["preco_base"]) == Decimal("15.50")


def test_atualizar_ignora_campo_disponivel_no_payload(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Item", is_available=True)

    resp = client.put(
        f"/alimentos/{alimento.id}",
        json={"nome": "Item Editado", "disponivel": False},
        headers=auth(admin_user, token_para),
    )

    assert resp.status_code == 200
    assert resp.json()["disponivel"] is True


def test_atualizar_categoria_de_outro_restaurante_da_404(
    client, db, categoria, categoria_b, admin_user, token_para
):
    alimento = criar_alimento_direto(db, categoria, name="Item")

    resp = client.put(
        f"/alimentos/{alimento.id}",
        json={"categoria_id": str(categoria_b.id)},
        headers=auth(admin_user, token_para),
    )

    assert resp.status_code == 404


# ── DELETE /alimentos/:id ─────────────────────────────────────────

def test_deletar_alimento_e_soft_delete(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Item", is_active=True)

    resp = client.delete(f"/alimentos/{alimento.id}", headers=auth(admin_user, token_para))
    assert resp.status_code == 204

    db.refresh(alimento)
    assert alimento.is_active is False
    assert db.get(Food, alimento.id) is not None


def test_deletar_alimento_de_outro_restaurante_da_404(client, db, categoria_b, admin_user, token_para):
    alimento_de_b = criar_alimento_direto(db, categoria_b, name="Não é seu")

    resp = client.delete(f"/alimentos/{alimento_de_b.id}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404