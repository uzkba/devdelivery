import uuid
from datetime import datetime, timedelta, timezone

from app.model.models import Order, OrderStatus


def _status(db, code, name, order=1, is_final=False):
    status = db.query(OrderStatus).filter_by(code=code).first()
    if status is None:
        status = OrderStatus(code=code, name=name, order=order, is_final=is_final)
        db.add(status)
        db.flush()
        db.refresh(status)
    return status


def _criar_pedido(db, restaurante, cliente, status, forma_pagamento, endereco, total_amount, order_datetime=None):
    pedido = Order(
        restaurant_id=restaurante.id,
        client_id=cliente.id,
        status_id=status.id,
        payment_method_id=forma_pagamento.id,
        address_name=cliente.name,
        address_phone=cliente.phone,
        address_street=endereco.street,
        address_number=endereco.number,
        address_neighborhood=endereco.neighborhood,
        items_amount=total_amount,
        delivery_fee=0,
        total_amount=total_amount,
    )
    if order_datetime is not None:
        pedido.order_datetime = order_datetime
    db.add(pedido)
    db.flush()
    db.refresh(pedido)
    return pedido


def test_relatorio_geral_exclui_cancelado(
    client, db, restaurante, admin_user, cliente, endereco, forma_pagamento_dinheiro, token_para
):
    status_concluido = _status(db, "CONCLUIDO", "Concluído", order=5, is_final=True)
    status_cancelado = _status(db, "CANCELADO", "Cancelado", order=6, is_final=True)

    _criar_pedido(db, restaurante, cliente, status_concluido, forma_pagamento_dinheiro, endereco, total_amount=50)
    _criar_pedido(db, restaurante, cliente, status_cancelado, forma_pagamento_dinheiro, endereco, total_amount=1000)
    db.commit()

    hoje = datetime.now(timezone.utc).date()
    resp = client.get(
        "/relatorios/pedidos",
        params={"data_inicio": (hoje - timedelta(days=1)).isoformat(), "data_fim": hoje.isoformat()},
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantidade_pedidos"] == 2        
    assert float(body["valor_total"]) == 50          
    assert float(body["ticket_medio"]) == 50


def test_relatorio_por_cliente_isola_pedidos(
    client, db, restaurante, admin_user, cliente, outro_cliente, endereco, endereco_secundario, forma_pagamento_dinheiro, token_para
):
    status_concluido = _status(db, "CONCLUIDO", "Concluído", order=5, is_final=True)

    _criar_pedido(db, restaurante, cliente, status_concluido, forma_pagamento_dinheiro, endereco, total_amount=30)
    _criar_pedido(db, restaurante, outro_cliente, status_concluido, forma_pagamento_dinheiro, endereco_secundario, total_amount=999)
    db.commit()

    hoje = datetime.now(timezone.utc).date()
    resp = client.get(
        "/relatorios/pedidos",
        params={
            "data_inicio": (hoje - timedelta(days=1)).isoformat(),
            "data_fim": hoje.isoformat(),
            "cliente_id": str(cliente.id),
        },
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantidade_pedidos"] == 1
    assert float(body["valor_total"]) == 30


def test_relatorio_periodo_sem_pedidos(client, db, restaurante, admin_user, token_para):
    resp = client.get(
        "/relatorios/pedidos",
        params={"data_inicio": "2020-01-01", "data_fim": "2020-01-02"},
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantidade_pedidos"] == 0
    assert float(body["valor_total"]) == 0
    assert float(body["ticket_medio"]) == 0
    assert body["por_status"] == []


def test_relatorio_data_fim_menor_que_data_inicio_retorna_422(client, admin_user, token_para):
    resp = client.get(
        "/relatorios/pedidos",
        params={"data_inicio": "2026-01-10", "data_fim": "2026-01-01"},
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 422


def test_relatorio_cliente_sem_pedidos_no_restaurante_retorna_404(
    client, db, restaurante, outro_restaurante, admin_user, cliente, endereco,
    forma_pagamento_dinheiro, token_para
):
    status_concluido = _status(db, "CONCLUIDO", "Concluído", order=5, is_final=True)
    _criar_pedido(db, outro_restaurante, cliente, status_concluido, forma_pagamento_dinheiro, endereco, total_amount=40)
    db.commit()

    hoje = datetime.now(timezone.utc).date()
    resp = client.get(
        "/relatorios/pedidos",
        params={
            "data_inicio": (hoje - timedelta(days=1)).isoformat(),
            "data_fim": hoje.isoformat(),
            "cliente_id": str(cliente.id),
        },
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 404


def test_relatorio_cliente_id_totalmente_inexistente_retorna_404(client, admin_user, token_para):
    resp = client.get(
        "/relatorios/pedidos",
        params={
            "data_inicio": "2020-01-01",
            "data_fim": "2020-01-02",
            "cliente_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token_para(admin_user)}"},
    )
    assert resp.status_code == 404