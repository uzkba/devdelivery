from datetime import date
from decimal import Decimal

from app.model.models import Combo


def test_esgotado_em_comeca_nulo(marmita_pronta, alimento_arroz):
    assert marmita_pronta.sold_out_on is None
    assert alimento_arroz.sold_out_on is None


def test_esgotado_em_persiste_nas_tres_tabelas(db, restaurante, marmita_pronta, alimento_arroz):
    dia = date(2026, 11, 6)
    combo = Combo(restaurant_id=restaurante.id, name="Combo", price=Decimal("30.00"))
    db.add(combo)
    db.flush()

    for obj in (marmita_pronta, alimento_arroz, combo):
        obj.sold_out_on = dia
    db.flush()

    for obj in (marmita_pronta, alimento_arroz, combo):
        db.refresh(obj)
        assert obj.sold_out_on == dia