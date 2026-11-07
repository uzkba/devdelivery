from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.api.dependencias_publicas import get_restaurante_publico
from app.model.models import Combo, ComboFoodItem, ComboMealBoxItem
from app.services import cardapio_publico_service as svc


def _combo(db, restaurante, preco, marmitas=(), alimentos=()):
    combo = Combo(restaurant_id=restaurante.id, name="Combo", price=Decimal(preco))
    combo.meal_box_items = [
        ComboMealBoxItem(meal_box_id=m.id, quantity=q, position=i)
        for i, (m, q) in enumerate(marmitas)
    ]
    combo.food_items = [
        ComboFoodItem(food_id=a.id, quantity=q, position=i)
        for i, (a, q) in enumerate(alimentos)
    ]
    db.add(combo)
    db.flush()
    db.refresh(combo)
    return combo


# ------------------------- preco de referencia -------------------------
def test_soma_marmitas_e_avulsos_com_quantidade(db, restaurante, marmita_pronta, alimento_so_venda):
    # 2 x 20.00 + 1 x 32.90 = 72.90
    combo = _combo(
        db, restaurante, "60.00",
        marmitas=[(marmita_pronta, 2)], alimentos=[(alimento_so_venda, 1)],
    )
    assert svc.preco_referencia_combo(combo) == Decimal("72.90")


def test_so_marmitas(db, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "50.00", marmitas=[(marmita_pronta, 3)])
    assert svc.preco_referencia_combo(combo) == Decimal("60.00")


def test_economia_zero_esconde_referencia(db, restaurante, marmita_pronta, alimento_so_venda):
    combo = _combo(
        db, restaurante, "72.90",
        marmitas=[(marmita_pronta, 2)], alimentos=[(alimento_so_venda, 1)],
    )
    assert svc.preco_referencia_combo(combo) is None


def test_combo_mais_caro_que_a_soma_esconde_referencia(db, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "25.00", marmitas=[(marmita_pronta, 1)])
    assert svc.preco_referencia_combo(combo) is None


def test_item_sem_preco_avulso_esconde_referencia(db, restaurante, marmita_pronta, alimento_arroz):
    # arroz tem base_price (legado) mas nao standalone_price
    combo = _combo(
        db, restaurante, "10.00",
        marmitas=[(marmita_pronta, 1)], alimentos=[(alimento_arroz, 1)],
    )
    assert svc.preco_referencia_combo(combo) is None


# ------------------------- get_restaurante_publico -------------------------
def test_restaurante_ativo_e_devolvido(db, restaurante):
    assert get_restaurante_publico(restaurante.id, db).id == restaurante.id


def test_restaurante_inexistente_da_404(db):
    import uuid

    with pytest.raises(HTTPException) as erro:
        get_restaurante_publico(uuid.uuid4(), db)
    assert erro.value.status_code == 404


def test_restaurante_inativo_da_404(db, restaurante):
    restaurante.is_active = False
    db.flush()
    with pytest.raises(HTTPException) as erro:
        get_restaurante_publico(restaurante.id, db)
    assert erro.value.status_code == 404