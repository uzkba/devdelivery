import uuid

from app.core.websockets import manager
from app.model.models import Order
from app.services import pedido_fluxo


def montar_evento_status(pedido: Order) -> dict:
    status = pedido.status
    return {
        "tipo": "STATUS_PEDIDO",
        "pedido_id": str(pedido.id),
        "numero_pedido": pedido.order_number,
        "tipo_atendimento": pedido.service_type.value,
        "status": status.code,
        "status_rotulo": pedido_fluxo.rotulo(pedido.service_type, status.code, status.name),
        "final": status.is_final,
        "motivo": pedido.status_reason,
        "entregador": pedido.driver.name if pedido.driver else None,
        "acoes_disponiveis": pedido_fluxo.acoes_disponiveis(pedido.service_type, status.code),
    }


async def publicar(restaurant_id: uuid.UUID, client_id: uuid.UUID, evento: dict) -> None:
    await manager.broadcast_to_restaurant(restaurant_id, evento)
    await manager.broadcast_to_client(client_id, evento)


def montar_evento_pagamento(pedido: Order) -> dict:
    return {
        "tipo": "PAGAMENTO_PEDIDO",
        "pedido_id": str(pedido.id),
        "numero_pedido": pedido.order_number,
        "forma_pagamento": pedido.payment_method.code,
        "forma_pagamento_nome": pedido.payment_method.name,
        "valor_troco": float(pedido.change_amount) if pedido.change_amount is not None else None,
    }