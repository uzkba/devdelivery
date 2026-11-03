import pytest
from decimal import Decimal

from app.model.models import Food, FoodCategory


def auth(user, token_para):
    return {"Authorization": f"Bearer {token_para(user)}"}


def _criar_categoria_direta(db, restaurante, nome, tipo="composicao"):
    c = FoodCategory(restaurant_id=restaurante.id, name=nome, display_order=0, type=tipo)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def test_criar_sem_tipo_assume_composicao(client, admin_user, token_para):
    r = client.post("/categorias", json={"nome": "Arroz"}, headers=auth(admin_user, token_para))
    assert r.status_code == 201
    assert r.json()["tipo"] == "composicao"


def test_criar_categoria_de_venda(client, admin_user, token_para):
    r = client.post("/categorias", json={"nome": "Pratos do dia", "tipo": "venda"},
                    headers=auth(admin_user, token_para))
    assert r.status_code == 201
    assert r.json()["tipo"] == "venda"


def test_criar_com_tipo_invalido_da_422(client, admin_user, token_para):
    r = client.post("/categorias", json={"nome": "X", "tipo": "outro"}, headers=auth(admin_user, token_para))
    assert r.status_code == 422


def test_listar_filtra_por_tipo(client, db, restaurante, admin_user, token_para):
    _criar_categoria_direta(db, restaurante, "Carboidrato", "composicao")
    _criar_categoria_direta(db, restaurante, "Feijoadas", "venda")

    r = client.get("/categorias?tipo=venda", headers=auth(admin_user, token_para))

    assert r.status_code == 200
    assert {c["nome"] for c in r.json()} == {"Feijoadas"}


def test_put_ignora_tipo_no_payload(client, db, restaurante, admin_user, token_para):
    cat = _criar_categoria_direta(db, restaurante, "Proteínas", "composicao")

    r = client.put(f"/categorias/{cat.id}", json={"nome": "Proteínas 2", "tipo": "venda"},
                   headers=auth(admin_user, token_para))

    assert r.status_code == 200
    assert r.json()["nome"] == "Proteínas 2"
    assert r.json()["tipo"] == "composicao"


def test_delete_categoria_vazia_desativa(client, db, restaurante, admin_user, token_para):
    cat = _criar_categoria_direta(db, restaurante, "Vazia")

    r = client.delete(f"/categorias/{cat.id}", headers=auth(admin_user, token_para))

    assert r.status_code == 200
    assert r.json()["ativo"] is False


def test_delete_categoria_composicao_com_alimento_ativo_da_409(client, db, restaurante, admin_user, token_para):
    cat = _criar_categoria_direta(db, restaurante, "Arroz", "composicao")
    db.add(Food(restaurant_id=restaurante.id, category_id=cat.id, name="Arroz branco",
                base_price=Decimal("0"), is_active=True))
    db.flush()

    r = client.delete(f"/categorias/{cat.id}", headers=auth(admin_user, token_para))

    assert r.status_code == 409


def test_delete_categoria_venda_com_alimento_avulso_ativo_da_409(client, db, restaurante, admin_user, token_para):
    cat = _criar_categoria_direta(db, restaurante, "Feijoadas", "venda")
    db.add(Food(restaurant_id=restaurante.id, category_id=None, sale_category_id=cat.id,
                is_sellable_alone=True, standalone_price=Decimal("32.90"),
                name="Feijoada", base_price=Decimal("0"), is_active=True))
    db.flush()

    r = client.delete(f"/categorias/{cat.id}", headers=auth(admin_user, token_para))

    assert r.status_code == 409


def test_delete_categoria_composicao_com_alimento_inativo_passa(client, db, restaurante, admin_user, token_para):
    cat = _criar_categoria_direta(db, restaurante, "Arroz", "composicao")
    db.add(Food(restaurant_id=restaurante.id, category_id=cat.id, name="Arroz antigo",
                base_price=Decimal("0"), is_active=False))
    db.flush()

    r = client.delete(f"/categorias/{cat.id}", headers=auth(admin_user, token_para))

    assert r.status_code == 200


def test_atendente_nao_cria_categoria(client, atendente_user, token_para):
    r = client.post("/categorias", json={"nome": "X"}, headers=auth(atendente_user, token_para))
    assert r.status_code == 403