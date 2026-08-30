import uuid
from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.model.models import (
    DeliveryRule, Order, OrderItem, OrderItemOption,
    Food, MenuItem, Menu, ModifierOption,
    CustomerAddress, OrderStatus,
    PaymentMethod,
    Restaurant,
)
from backend.app.schemas.pedido_schemas import OrderCreate
from backend.app.model.models import (
    Order, OrderItem, OrderItemOption,
    Food, ModifierOption, CustomerAddress, OrderStatus, OrderStatusHistory, Client
)
from backend.app.api.depedencias import AuthenticatedClient
from backend.app.services.auditoria_service import registrar_log_auditoria, ACAO_CRIACAO
from backend.app.utils.geo import calcular_distancia_km


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

    restaurante = db.query(Restaurant).filter_by(id=payload.restaurante_id).first()
    
    if not restaurante.latitude or not restaurante.longitude:
        raise HTTPException(
            status_code=500, detail="Restaurante não possui coordenadas configuradas."
        )
    if not endereco.latitude or not endereco.longitude:
        raise HTTPException(
            status_code=400, detail="Endereço de entrega não possui coordenadas válidas."
        )

    # 1. Calcular a distância em km
    distancia_km = calcular_distancia_km(
        float(restaurante.latitude), float(restaurante.longitude),
        float(endereco.latitude), float(endereco.longitude)
    )

    # 2. Buscar a regra de taxa de entrega aplicável
    regra_entrega = (
        db.query(DeliveryRule)
        .filter(
            DeliveryRule.restaurant_id == restaurante.id,
            DeliveryRule.is_active.is_(True),
            DeliveryRule.min_distance_km <= distancia_km,
            DeliveryRule.max_distance_km >= distancia_km
        )
        .first()
    )

    if not regra_entrega:
        raise HTTPException(
            status_code=422, 
            detail=f"O endereço selecionado está fora da área de entrega (Distância: {distancia_km:.1f}km)."
        )

    delivery_fee = Decimal(str(regra_entrega.fee))

    # 1. Extração em lote de IDs (Alimentos e Opções)
    alimento_ids = [item.alimento_id for item in payload.itens]
    todas_opcoes_ids = [
        opcao.opcao_complemento_id 
        for item in payload.itens 
        for opcao in item.opcoes_selecionadas
    ]

    # 2. Consultas únicas otimizadas no banco
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
    
    # Dicionário em memória para as opções
    dict_opcoes = {}
    if todas_opcoes_ids:
        opcoes_db = db.query(ModifierOption).filter(ModifierOption.id.in_(todas_opcoes_ids)).all()
        dict_opcoes = {opcao.id: opcao for opcao in opcoes_db}

    delivery_fee = Decimal("0.00")  # TODO: regra real de taxa de entrega

    # 3. Montagem do pedido
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

        # 4. Processamento iterativo estritamente em memória
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
                # Busca direto no dicionário carregado no passo 2
                opcao_db = dict_opcoes.get(opcao_data.opcao_complemento_id)
                
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

        registrar_log_auditoria(
            db,
            restaurant_id=novo_pedido.restaurant_id,
            user_id=None,
            entidade="pedido",
            entidade_id=novo_pedido.id,
            acao=ACAO_CRIACAO,
            dados_novos=novo_pedido,
        )

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


def listar_pedidos(
    db: Session,
    restaurant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Order, str]], int]:
    query = (
        db.query(Order, Client.name)
        .join(Client, Client.id == Order.client_id)
        .filter(Order.restaurant_id == restaurant_id)
    )
    total = query.count()
    resultados = (
        query.order_by(Order.order_datetime.asc(), Order.order_number.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return resultados, total


def listar_pedidos_cliente(
    db: Session,
    client_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Order, str]], int]:
    query = (
        db.query(Order, Client.name)
        .join(Client, Client.id == Order.client_id)
        .filter(Order.client_id == client_id)
    )
    total = query.count()
    resultados = (
        query.order_by(Order.order_datetime.desc(), Order.order_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return resultados, total


def buscar_pedido_do_cliente(db: Session, pedido_id: uuid.UUID, client_id: uuid.UUID) -> Order:
    pedido = db.query(Order).filter_by(id=pedido_id, client_id=client_id).first()
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

    if status_atual and status_atual.is_final:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido está em status final ('{status_atual.code}') e não pode mudar mais.",
        )

    if status_atual and status_atual.id == novo_status.id:
        raise HTTPException(status_code=400, detail="O pedido já está neste status.")

    db.add(
        OrderStatusHistory(
            order_id=pedido.id,
            previous_status_id=pedido.status_id,
            new_status_id=novo_status.id,
            changed_by=usuario_id,
        )
    )

    pedido.status_id = novo_status.id

    db.commit()
    db.refresh(pedido)
    pedido.client = db.query(Client).filter_by(id=pedido.client_id).first()
    return pedido