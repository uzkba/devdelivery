import pytest
from datetime import date, timedelta
from decimal import Decimal
 
from backend.app.model.models import Food, FoodCategory, Menu, MenuItem
 
 
# ── fixtures locais, mesmo padrão de test_alimento.py ──
 
@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
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
    )
    dados.update(overrides)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f
 
 
def criar_cardapio(db, restaurante, data=None):
    menu = Menu(restaurant_id=restaurante.id, date=data or date.today())
    db.add(menu)
    db.flush()
    db.refresh(menu)
    return menu
 
 
def criar_item_cardapio(db, menu, alimento, is_available=True, day_price=None):
    item = MenuItem(
        menu_id=menu.id,
        food_id=alimento.id,
        is_available=is_available,
        day_price=day_price,
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item
 
 
# ── testes ──────────────────────────────────────────────────────
 
def test_item_disponivel_aparece_agrupado_por_categoria(db, client, restaurante, categoria):
    alimento = criar_alimento_direto(db, categoria, name="Feijoada")
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, alimento)
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["data"] == date.today().isoformat()
    assert len(corpo["categorias"]) == 1
    assert corpo["categorias"][0]["categoria_nome"] == categoria.name
    assert corpo["categorias"][0]["itens"][0]["nome"] == "Feijoada"
    assert corpo["categorias"][0]["itens"][0]["preco"] == "10.00"
 
 
def test_item_some_quando_alimento_foi_soft_deleted(db, client, restaurante, categoria):
    # is_active=False (admin apagou o alimento) precisa esconder o item
    # mesmo que o item continue marcado como disponível no cardápio
    alimento = criar_alimento_direto(db, categoria, is_active=False)
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, alimento, is_available=True)
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    assert resp.json()["categorias"] == []
 
 
def test_item_some_quando_indisponivel_no_cardapio(db, client, restaurante, categoria):
    alimento = criar_alimento_direto(db, categoria)
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, alimento, is_available=False)
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    assert resp.json()["categorias"] == []
 
 
def test_cardapio_de_outro_dia_nao_aparece(db, client, restaurante, categoria):
    alimento = criar_alimento_direto(db, categoria)
    ontem = criar_cardapio(db, restaurante, data=date.today() - timedelta(days=1))
    criar_item_cardapio(db, ontem, alimento)
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    assert resp.json()["categorias"] == []
 
 
def test_preco_do_dia_sobrescreve_preco_base(db, client, restaurante, categoria):
    alimento = criar_alimento_direto(db, categoria, base_price=Decimal("20.00"))
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, alimento, day_price=Decimal("15.90"))
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    assert resp.json()["categorias"][0]["itens"][0]["preco"] == "15.90"
 
 
def test_categorias_respeitam_display_order(db, client, restaurante):
    cat_sobremesa = FoodCategory(restaurant_id=restaurante.id, name="Sobremesas", display_order=1)
    cat_prato = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add_all([cat_sobremesa, cat_prato])
    db.flush()
 
    menu = criar_cardapio(db, restaurante)
    criar_item_cardapio(db, menu, criar_alimento_direto(db, cat_sobremesa, name="Pudim"))
    criar_item_cardapio(db, menu, criar_alimento_direto(db, cat_prato, name="Feijoada"))
 
    resp = client.get(f"/restaurantes/{restaurante.id}/cardapio-do-dia")
 
    nomes_categorias = [c["categoria_nome"] for c in resp.json()["categorias"]]
    assert nomes_categorias == ["Pratos", "Sobremesas"]
 
