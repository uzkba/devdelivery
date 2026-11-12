from datetime import date, datetime
from decimal import Decimal

from app.model.models import OrderStatus
from app.services.relatorio_service import get_relatorio_pedidos


def _status(db, codigo):
    return db.query(OrderStatus).filter_by(code=codigo).one()


def test_recusado_e_cancelado_ficam_fora_do_valor_faturavel(
    db, restaurante, forma_pagamento_dinheiro, criar_pedido_direto
):
    momento = datetime(2026, 11, 10, 12, 0)
    for codigo, total in (("ENTREGUE", "30.00"), ("RECUSADO", "50.00"), ("CANCELADO", "70.00")):
        criar_pedido_direto(
            _status(db, codigo), forma_pagamento_dinheiro, Decimal(total), momento
        )

    resultado = get_relatorio_pedidos(db, restaurante.id, date(2026, 11, 10), date(2026, 11, 10))

    assert resultado["quantidade_pedidos"] == 3
    assert resultado["valor_total"] == Decimal("30.00")
    assert resultado["ticket_medio"] == Decimal("30.00")
    assert len(resultado["por_status"]) == 3