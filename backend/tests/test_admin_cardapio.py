import pytest
from datetime import date
from uuid import uuid4
from decimal import Decimal

from app.model.models import Food, FoodCategory, Menu, MenuItem

# ==============================================================================
# FIXTURES LOCAIS PARA OS TESTES DE CARDÁPIO
# ==============================================================================

@pytest.fixture()
def categoria_teste(db, restaurante):
    categoria = FoodCategory(
        restaurant_id=restaurante.id,
        name="Pratos Principais",
        display_order=1,
        is_active=True
    )
    db.add(categoria)
    db.flush()
    return categoria

@pytest.fixture()
def alimento_teste(db, restaurante, categoria_teste):
    alimento = Food(
        restaurant_id=restaurante.id,
        category_id=categoria_teste.id,
        name="Lasanha à Bolonhesa",
        description="Lasanha caseira",
        base_price=Decimal("35.00"),
        is_active=True,
        is_available=True
    )
    db.add(alimento)
    db.flush()
    return alimento

@pytest.fixture()
def menu_hoje(db, restaurante, admin_user):
    menu = Menu(
        restaurant_id=restaurante.id,
        date=date.today(),
        created_by=admin_user.id
    )
    db.add(menu)
    db.flush()
    return menu

@pytest.fixture()
def item_cardapio_teste(db, menu_hoje, alimento_teste):
    item = MenuItem(
        menu_id=menu_hoje.id,
        food_id=alimento_teste.id,
        is_available=True,
        day_price=None
    )
    db.add(item)
    db.flush()
    return item

# ==============================================================================
# TESTES DA ROTA POST (GERAR CARDÁPIO)
# ==============================================================================

def test_gerar_cardapio_sucesso(client, admin_user, token_para, alimento_teste):
    """Deve gerar o cardápio com sucesso puxando os alimentos ativos."""
    token = token_para(admin_user)
    payload = {"data": str(date.today())}

    response = client.post(
        "/admin/cardapio/gerar",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    dados = response.json()
    assert "menu_id" in dados
    assert dados["message"] == "Cardápio gerado com sucesso com todos os itens ativos!"

def test_gerar_cardapio_sem_alimentos(client, admin_user, token_para):
    """Deve retornar erro 400 se o restaurante não tiver nenhum alimento ativo."""
    # Note que não injetamos a fixture `alimento_teste` aqui, então o banco está vazio
    token = token_para(admin_user)
    payload = {"data": str(date.today())}

    response = client.post(
        "/admin/cardapio/gerar",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Nenhum alimento ativo no catálogo."

def test_gerar_cardapio_duplicado(client, admin_user, token_para, alimento_teste, menu_hoje):
    """Deve bloquear a criação se já existir um cardápio para a data."""
    # A fixture `menu_hoje` já criou um cardápio no banco para hoje
    token = token_para(admin_user)
    payload = {"data": str(date.today())}

    response = client.post(
        "/admin/cardapio/gerar",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe um cardápio criado para esta data."

# ==============================================================================
# TESTES DA ROTA PATCH (EDITAR ITEM DO CARDÁPIO)
# ==============================================================================

def test_atualizar_item_cardapio_sucesso(client, admin_user, token_para, item_cardapio_teste, db):
    """Deve atualizar a disponibilidade e o preço promocional do item."""
    token = token_para(admin_user)
    
    payload = {
        "is_available": False,
        "day_price": "29.90"
    }

    response = client.patch(
        f"/admin/cardapio/item/{item_cardapio_teste.id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Esgotado"

    # Confere no banco se realmente alterou
    db.refresh(item_cardapio_teste)
    assert item_cardapio_teste.is_available is False
    assert item_cardapio_teste.day_price == Decimal("29.90")

def test_atualizar_item_inexistente(client, admin_user, token_para):
    """Deve retornar 404 ao tentar atualizar um UUID que não existe."""
    token = token_para(admin_user)
    id_falso = str(uuid4())
    
    response = client.patch(
        f"/admin/cardapio/item/{id_falso}",
        json={"is_available": False},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item do cardápio não encontrado."

def test_atualizar_item_outro_restaurante(client, outro_admin_user, token_para, item_cardapio_teste):
    """Garante que um admin do restaurante B não consegue editar um item do restaurante A."""
    # O `item_cardapio_teste` pertence ao restaurante A. 
    # O `outro_admin_user` pertence ao restaurante B.
    token = token_para(outro_admin_user)
    
    response = client.patch(
        f"/admin/cardapio/item/{item_cardapio_teste.id}",
        json={"is_available": False},
        headers={"Authorization": f"Bearer {token}"}
    )

    # A query faz um JOIN com Menu para checar o restaurant_id. 
    # Como não vai bater, ele não encontra e devolve 404, protegendo os dados.
    assert response.status_code == 404
    assert response.json()["detail"] == "Item do cardápio não encontrado."