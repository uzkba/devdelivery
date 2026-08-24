import uuid
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.model.models import (
    Order, OrderItem, OrderItemOption, 
    Food, ModifierOption, CustomerAddress, OrderStatus
)
from backend.app.schemas.pedido_schemas import OrderCreate
from backend.app.model.models import (
    Order, OrderItem, OrderItemOption,
    Food, ModifierOption, CustomerAddress, OrderStatus, OrderStatusHistory
)

def criar_pedido(db: Session, payload: OrderCreate, restaurant_id: uuid.UUID) -> Order:
    status_inicial = db.query(OrderStatus).order_by(OrderStatus.order.asc()).first()
    if not status_inicial:
        raise HTTPException(status_code=500, detail="Nenhum status de pedido configurado no banco.")

    endereco = db.query(CustomerAddress).filter_by(
        id=payload.endereco_id, client_id=payload.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado para este cliente.")

    novo_pedido = Order(
        restaurant_id=restaurant_id,
        client_id=payload.cliente_id,
        status_id=status_inicial.id,
        payment_method_id=payload.forma_pagamento_id,
        
        address_name="Endereço de Entrega",
        address_phone="",
        address_street=endereco.street,
        address_number=endereco.number,
        address_neighborhood=endereco.neighborhood,
        address_complement=endereco.complement,
        
        notes=payload.observacoes,
        delivery_fee=payload.valor_entrega,
        items_amount=Decimal("0.00"), 
        total_amount=Decimal("0.00"),
        cash_paid_amount=payload.valor_pago_dinheiro,
    )
    
    db.add(novo_pedido)
    db.flush()

    valor_total_itens = Decimal("0.00")

    for item_data in payload.itens:
        alimento = db.query(Food).filter_by(id=item_data.alimento_id, restaurant_id=restaurant_id).first()
        if not alimento or not alimento.is_active or not alimento.is_available:
            raise HTTPException(status_code=400, detail=f"Alimento {item_data.alimento_id} inválido ou indisponível.")

        novo_item = OrderItem(
            order_id=novo_pedido.id,
            food_id=alimento.id,
            food_name=alimento.name,
            quantity=item_data.quantidade,
            base_price=alimento.base_price,
            subtotal=Decimal("0.00"),
            notes=item_data.observacoes
        )
        db.add(novo_item)
        db.flush()

        subtotal_item = alimento.base_price

        for opcao_data in item_data.opcoes_selecionadas:
            opcao_db = db.query(ModifierOption).filter_by(id=opcao_data.opcao_complemento_id).first()
            if not opcao_db or not opcao_db.is_available:
                raise HTTPException(status_code=400, detail=f"Opção {opcao_data.opcao_complemento_id} indisponível.")
  
            nova_opcao = OrderItemOption(
                order_item_id=novo_item.id,
                modifier_option_id=opcao_db.id,
                option_name=opcao_db.name,
                extra_price=opcao_db.extra_price,
                quantity=opcao_data.quantidade
            )
            db.add(nova_opcao)
          
            subtotal_item += (opcao_db.extra_price * opcao_data.quantidade)
        
        novo_item.subtotal = subtotal_item * item_data.quantidade
        valor_total_itens += novo_item.subtotal

    novo_pedido.items_amount = valor_total_itens
    novo_pedido.total_amount = valor_total_itens + novo_pedido.delivery_fee

    if novo_pedido.cash_paid_amount:
        if novo_pedido.cash_paid_amount < novo_pedido.total_amount:
            raise HTTPException(status_code=400, detail="Valor pago em dinheiro é menor que o total do pedido.")
        novo_pedido.change_amount = novo_pedido.cash_paid_amount - novo_pedido.total_amount

    db.commit()
    db.refresh(novo_pedido)
    return novo_pedido

def buscar_pedido_por_id(db: Session, pedido_id: uuid.UUID, restaurant_id: uuid.UUID) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, restaurant_id=restaurant_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido

def atualizar_status_pedido(
    db: Session,
    pedido_id: uuid.UUID,
    novo_status_codigo: str,
    restaurant_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, restaurant_id=restaurant_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    novo_status = db.query(OrderStatus).filter_by(code=novo_status_codigo).first()
    if not novo_status:
        raise HTTPException(status_code=404, detail=f"Status '{novo_status_codigo}' não existe.")

    status_atual = db.query(OrderStatus).filter_by(id=pedido.status_id).first()

    # RN18 — status final (ENTREGUE/CANCELADO) não pode mais transicionar
    if status_atual and status_atual.is_final:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido está em status final ('{status_atual.code}') e não pode mudar mais.",
        )

    # RN16 — pedido já vinculado a um fechamento de caixa é imutável
    if pedido.cash_closing_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Pedido já vinculado a um fechamento de caixa; status não pode ser alterado.",
        )

    if status_atual and status_atual.id == novo_status.id:
        raise HTTPException(status_code=400, detail="O pedido já está neste status.")

    # RN17 — registra a transição no histórico
    db.add(
        OrderStatusHistory(
            order_id=pedido.id,
            previous_status_id=pedido.status_id,
            new_status_id=novo_status.id,
            changed_by=usuario_id,
        )
    )

    pedido.status_id = novo_status.id

    db.commit()          # tudo (update + insert do histórico) na mesma transação
    db.refresh(pedido)
    return pedido