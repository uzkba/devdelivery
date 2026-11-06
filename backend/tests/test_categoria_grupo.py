from decimal import Decimal

import pytest

from app.model.models import Food, FoodCategory, FoodComponent
from app.services.categoria_alimento_service import criar_categorias_iniciais


@pytest.fixture()
def cat_bebida(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Sucos", display_order=0, type="venda", group="bebida")
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def _item_avulso(db, categoria, nome, **extra):
    f = Food(
        restaurant_id=categoria.restaurant_id,
        name=nome,
        base_price=Decimal("0"),
        sale_category_id=categoria.id,
        is_sellable_alone=True,
        standalone_price=Decimal("10.00"),
        **extra,
    )
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


def _payload_bebida(cat, **extra):
    return {
        "nome": "Suco de laranja",
        "vendavel_avulso": True,
        "preco_avulso": "8.00",
        "categoria_venda_id": str(cat.id),
        **extra,
    }


# ── criar categoria ─────────────────────────────────────────────

def test_venda_sem_grupo_vira_prato(client, admin_headers):
    r = client.post("/categorias", json={"nome": "Doces", "tipo": "venda"}, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["grupo"] == "prato"


def test_venda_com_grupo_bebida(client, admin_headers):
    r = client.post("/categorias", json={"nome": "Refris", "tipo": "venda", "grupo": "bebida"}, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["grupo"] == "bebida"


def test_composicao_nasce_sem_grupo(client, admin_headers):
    r = client.post("/categorias", json={"nome": "Massas", "tipo": "composicao"}, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["grupo"] is None


def test_grupo_invalido_da_422(client, admin_headers):
    r = client.post("/categorias", json={"nome": "X", "tipo": "venda", "grupo": "sobremesa"}, headers=admin_headers)
    assert r.status_code == 422


def test_grupo_em_categoria_de_composicao_da_422(client, admin_headers):
    r = client.post("/categorias", json={"nome": "X", "tipo": "composicao", "grupo": "prato"}, headers=admin_headers)
    assert r.status_code == 422


# ── trocar grupo ────────────────────────────────────────────────

def test_trocar_grupo_move_itens_e_informa_quantidade(client, db, admin_headers, cat_venda):
    _item_avulso(db, cat_venda, "Feijoada")
    _item_avulso(db, cat_venda, "Strogonoff")

    r = client.put(f"/categorias/{cat_venda.id}", json={"grupo": "bebida"}, headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["grupo"] == "bebida"
    assert r.json()["itens_movidos"] == 2


def test_trocar_para_bebida_limpa_campos_de_prato(client, db, admin_headers, cat_venda):
    item = _item_avulso(
        db, cat_venda, "Feijoada",
        serves_people=4, calories_kcal=500, components=[FoodComponent(name="Arroz", position=0)],
    )

    client.put(f"/categorias/{cat_venda.id}", json={"grupo": "bebida"}, headers=admin_headers)

    db.refresh(item)
    assert item.serves_people is None
    assert item.calories_kcal is None
    assert item.components == []


def test_trocar_para_o_mesmo_grupo_nao_move_nada(client, db, admin_headers, cat_venda):
    _item_avulso(db, cat_venda, "Feijoada")

    r = client.put(f"/categorias/{cat_venda.id}", json={"grupo": "prato"}, headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["itens_movidos"] == 0


def test_grupo_em_categoria_de_composicao_no_put_da_422(client, admin_headers, cat_composicao):
    r = client.put(f"/categorias/{cat_composicao.id}", json={"grupo": "bebida"}, headers=admin_headers)
    assert r.status_code == 422


def test_grupo_null_no_put_da_422(client, admin_headers, cat_venda):
    r = client.put(f"/categorias/{cat_venda.id}", json={"grupo": None}, headers=admin_headers)
    assert r.status_code == 422


# ── bebida com campo de prato ───────────────────────────────────

def test_bebida_com_porcao_e_aceita(client, admin_headers, cat_bebida):
    r = client.post(
        "/alimentos",
        json=_payload_bebida(cat_bebida, porcao_quantidade="300", porcao_unidade="ml"),
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert r.json()["porcao_unidade"] == "ml"


@pytest.mark.parametrize(
    "extra",
    [
        {"serve_pessoas": 2},
        {"tempo_preparo_minutos": 10},
        {"calorias_kcal": 100},
        {"proteina_g": "1.0"},
        {"carboidrato_g": "1.0"},
        {"gordura_g": "1.0"},
        {"componentes": [{"nome": "Gelo"}]},
    ],
)
def test_bebida_com_campo_de_prato_da_422(client, admin_headers, cat_bebida, extra):
    r = client.post("/alimentos", json=_payload_bebida(cat_bebida, **extra), headers=admin_headers)
    assert r.status_code == 422


def test_mover_item_com_campo_de_prato_para_bebida_exige_limpar(client, admin_headers, cat_venda, cat_bebida):
    criado = client.post(
        "/alimentos",
        json={"nome": "Feijoada", "vendavel_avulso": True, "preco_avulso": "30", "serve_pessoas": 4,
              "categoria_venda_id": str(cat_venda.id)},
        headers=admin_headers,
    )
    assert criado.status_code == 201
    alvo = f"/alimentos/{criado.json()['id']}"

    recusado = client.put(alvo, json={"categoria_venda_id": str(cat_bebida.id)}, headers=admin_headers)
    assert recusado.status_code == 422

    aceito = client.put(
        alvo, json={"categoria_venda_id": str(cat_bebida.id), "serve_pessoas": None}, headers=admin_headers
    )
    assert aceito.status_code == 200
    assert aceito.json()["serve_pessoas"] is None


# ── filtro por grupo ────────────────────────────────────────────

def test_listar_filtra_por_grupo(client, db, admin_headers, cat_venda, cat_bebida):
    _item_avulso(db, cat_venda, "Feijoada")
    _item_avulso(db, cat_bebida, "Suco")

    pratos = client.get("/alimentos?grupo=prato", headers=admin_headers)
    bebidas = client.get("/alimentos?grupo=bebida", headers=admin_headers)

    assert {i["nome"] for i in pratos.json()} == {"Feijoada"}
    assert {i["nome"] for i in bebidas.json()} == {"Suco"}


def test_listar_grupo_invalido_da_422(client, admin_headers):
    assert client.get("/alimentos?grupo=sobremesa", headers=admin_headers).status_code == 422


# ── categorias iniciais ─────────────────────────────────────────

def test_categorias_iniciais_sao_criadas(db, restaurante):
    criadas = criar_categorias_iniciais(db, restaurante.id)

    assert {(c.name, c.type, c.group) for c in criadas} == {
        ("Pratos", "venda", "prato"),
        ("Sobremesas", "venda", "prato"),
        ("Bebidas", "venda", "bebida"),
    }


def test_categorias_iniciais_sao_idempotentes(db, restaurante):
    criar_categorias_iniciais(db, restaurante.id)

    assert criar_categorias_iniciais(db, restaurante.id) == []
    assert db.query(FoodCategory).filter_by(restaurant_id=restaurante.id).count() == 3


def test_categorias_iniciais_respeitam_nome_existente(db, restaurante):
    db.add(FoodCategory(restaurant_id=restaurante.id, name="Bebidas", type="venda", group="bebida"))
    db.flush()

    criadas = criar_categorias_iniciais(db, restaurante.id)

    assert {c.name for c in criadas} == {"Pratos", "Sobremesas"}


def test_categorias_iniciais_nao_vazam_para_outro_restaurante(db, restaurante, outro_restaurante):
    criar_categorias_iniciais(db, restaurante.id)

    assert db.query(FoodCategory).filter_by(restaurant_id=outro_restaurante.id).count() == 0