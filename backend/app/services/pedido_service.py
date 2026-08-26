import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.model.models import (
    Order, OrderItem, OrderItemOption,
    Food, MenuItem, Menu, ModifierOption,
    CustomerAddress, OrderStatus,
    PaymentMethod,
)
from backend.app.schemas.pedido_schemas import OrderCreate
from backend.app.api.depedencias import AuthenticatedClient

def criar_pedido(db: Session, payload: OrderCreate, current_client: AuthenticatedClient) -> Order:
    status_inicial = db.query(OrderStatus).order_by(OrderStatus.order.asc()).first()
    if not status_inicial:
        raise HTTPException(status_code=500, detail="Nenhum status de pedido configurado no banco.")

    endereco = (
        db.query(CustomerAddress)
        .filter_by(id=payload.endereco_id, client_id=current_client.id)
        .first()
    )
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado para este cliente.")

    forma_pagamento = db.query(PaymentMethod).filter_by(code=payload.forma_pagamento).first()
    
    if not forma_pagamento:
        raise HTTPException(status_code=422, detail="Forma de pagamento inválida.")

    if payload.forma_pagamento == "DINHEIRO" and payload.valor_pago_dinheiro is None:
        raise HTTPException(status_code=422, detail="Informe o valor pago em dinheiro.")
    if payload.forma_pagamento != "DINHEIRO" and payload.valor_pago_dinheiro is not None:
        raise HTTPException(
            status_code=422, detail="valor_pago_dinheiro só é válido para pagamento em DINHEIRO."
        )

    alimento_ids = [item.alimento_id for item in payload.itens]
    itens_cardapio_hoje = (
        db.query(MenuItem)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .filter(
            Menu.restaurant_id == payload.restaurante_id,
            Menu.date == date.today(),
            MenuItem.is_available.is_(True),
            MenuItem.food_id.in_(alimento_ids),
        )
        .all()
    )
    cardapio_por_alimento = {mi.food_id: mi for mi in itens_cardapio_hoje}

    faltando = [str(i) for i in alimento_ids if i not in cardapio_por_alimento]
    if faltando:
        raise HTTPException(
            status_code=422,
            detail=f"Itens indisponíveis no cardápio de hoje: {', '.join(faltando)}",
        )

    alimentos_por_id = {f.id: f for f in db.query(Food).filter(Food.id.in_(alimento_ids)).all()}
    delivery_fee = Decimal("0.00")  # TODO: regra real de taxa de entrega ainda não definida

    novo_pedido = Order(
        restaurant_id=payload.restaurante_id,
        client_id=current_client.id,
        status_id=status_inicial.id,
        payment_method_id=forma_pagamento.id,
        address_name=current_client.name,
        address_phone=current_client.phone,
        address_street=endereco.street,
        address_number=endereco.number,
        address_neighborhood=endereco.neighborhood,
        address_complement=endereco.complement,
        notes=payload.observacoes,
        delivery_fee=delivery_fee,
        items_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        cash_paid_amount=payload.valor_pago_dinheiro,
    )

    try:
        db.add(novo_pedido)
        db.flush()

        valor_total_itens = Decimal("0.00")

        for item_data in payload.itens:
            menu_item = cardapio_por_alimento[item_data.alimento_id]
            alimento = alimentos_por_id[item_data.alimento_id]
            preco_unitario = (
                menu_item.day_price if menu_item.day_price is not None else alimento.base_price
            )

            novo_item = OrderItem(
                order_id=novo_pedido.id,
                food_id=alimento.id,
                food_name=alimento.name,
                quantity=item_data.quantidade,
                base_price=preco_unitario,
                subtotal=Decimal("0.00"),
                notes=item_data.observacoes,
            )
            db.add(novo_item)
            db.flush()

            subtotal_item = preco_unitario

            for opcao_data in item_data.opcoes_selecionadas:
                opcao_db = db.query(ModifierOption).filter_by(id=opcao_data.opcao_complemento_id).first()
                if not opcao_db or not opcao_db.is_available:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Opção {opcao_data.opcao_complemento_id} indisponível.",
                    )
                nova_opcao = OrderItemOption(
                    order_item_id=novo_item.id,
                    modifier_option_id=opcao_db.id,
                    option_name=opcao_db.name,
                    extra_price=opcao_db.extra_price,
                    quantity=opcao_data.quantidade,
                )
                db.add(nova_opcao)
                subtotal_item += opcao_db.extra_price * opcao_data.quantidade

            novo_item.subtotal = subtotal_item * item_data.quantidade
            valor_total_itens += novo_item.subtotal

        novo_pedido.items_amount = valor_total_itens
        novo_pedido.total_amount = valor_total_itens + novo_pedido.delivery_fee

        if novo_pedido.cash_paid_amount is not None:
            if novo_pedido.cash_paid_amount < novo_pedido.total_amount:
                raise HTTPException(
                    status_code=400, detail="Valor pago em dinheiro é menor que o total do pedido."
                )
            novo_pedido.change_amount = novo_pedido.cash_paid_amount - novo_pedido.total_amount

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar o pedido.")

    db.refresh(novo_pedido)
    return novo_pedido

def buscar_pedido_por_id(db: Session, pedido_id: uuid.UUID, restaurant_id: uuid.UUID) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, restaurant_id=restaurant_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return pedido