from decimal import Decimal

from app.model.models import Combo

_CENTAVOS = Decimal("0.01")


def preco_referencia_combo(combo: Combo) -> Decimal | None:
    total = Decimal("0")
    for item in combo.meal_box_items:
        total += item.meal_box.price * item.quantity
    for item in combo.food_items:
        if item.food.standalone_price is None:
            return None
        total += item.food.standalone_price * item.quantity

    total = total.quantize(_CENTAVOS)
    if total - combo.price <= 0:
        return None
    return total