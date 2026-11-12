from decimal import Decimal

from app.model.models import (
    Combo,
    ComboFoodItem,
    ComboMealBoxItem,
    DeliveryChargeMode,
    Food,
    MealBox,
    MealBoxCategory,
    MealBoxComposition,
    MealBoxKind,
    RestaurantDeliverySettings,
)


def config_entrega(db, restaurante, **extra):
    dados = {"charge_mode": DeliveryChargeMode.GRATIS}
    dados.update(extra)
    config = RestaurantDeliverySettings(restaurant_id=restaurante.id, **dados)
    db.add(config)
    db.flush()
    return config


def criar_alimento(db, restaurante, nome, composicao=None, venda=None, **extra):
    f = Food(
        restaurant_id=restaurante.id,
        name=nome,
        composition_category_id=composicao.id if composicao else None,
        sale_category_id=venda.id if venda else None,
        **extra,
    )
    db.add(f)
    db.flush()
    return f


def criar_avulso(db, restaurante, venda, nome, preco):
    return criar_alimento(
        db, restaurante, nome, venda=venda,
        is_sellable_alone=True, standalone_price=Decimal(preco),
    )


def criar_pronta(db, restaurante, composicao, nome="Pronta", preco="20.00"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome, kind=MealBoxKind.READY, price=Decimal(preco)
    )
    m.composition = [
        MealBoxComposition(food_id=a.id, fixed_quantity=q, position=i)
        for i, (a, q) in enumerate(composicao)
    ]
    db.add(m)
    db.flush()
    return m


def criar_personalizavel(db, restaurante, exigencias, nome="Monte a sua", preco="25.00"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome,
        kind=MealBoxKind.CUSTOMIZABLE, price=Decimal(preco),
    )
    m.categories = [
        MealBoxCategory(food_category_id=c.id, required_quantity=q, position=i)
        for i, (c, q) in enumerate(exigencias)
    ]
    db.add(m)
    db.flush()
    return m


def criar_combo(db, restaurante, marmitas, alimentos, nome="Combo Almoço", preco="45.00"):
    c = Combo(restaurant_id=restaurante.id, name=nome, price=Decimal(preco))
    c.meal_box_items = [
        ComboMealBoxItem(meal_box_id=m.id, quantity=q, position=i)
        for i, (m, q) in enumerate(marmitas)
    ]
    c.food_items = [
        ComboFoodItem(food_id=a.id, quantity=q, position=i) for i, (a, q) in enumerate(alimentos)
    ]
    db.add(c)
    db.flush()
    return c


def selecao(categoria, *pares):
    return {
        "categoria_id": str(categoria.id),
        "alimentos": [{"alimento_id": str(a.id), "quantidade": q} for a, q in pares],
    }


def item_avulso(alimento, quantidade=1, **extra):
    return {"tipo": "AVULSO", "alimento_id": str(alimento.id), "quantidade": quantidade, **extra}


def item_marmita(marmita, quantidade=1, **extra):
    return {"tipo": "MARMITA", "marmita_id": str(marmita.id), "quantidade": quantidade, **extra}


def item_combo(combo, marmitas=(), quantidade=1, **extra):
    return {
        "tipo": "COMBO",
        "combo_id": str(combo.id),
        "quantidade": quantidade,
        "marmitas": [{"marmita_id": str(m.id), "selecoes": list(s)} for m, s in marmitas],
        **extra,
    }


def corpo_pedido(restaurante, itens, **extra):
    corpo = {"restaurante_slug": restaurante.slug, "forma_pagamento": "PIX", "itens": itens}
    corpo.update(extra)
    return corpo