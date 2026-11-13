from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.api.depedencias import AuthenticatedClient
from app.core.tempo import hoje_local
from app.model.models import (
    CustomerAddress,
    DeliveryChargeMode,
    Order,
    OrderItem,
    OrderServiceType,
)
from app.schemas.pedido_schemas import OrderCreate
from app.services import pedido_service
from tests.helpers_pedido import (
    criar_alimento as _alimento,
    criar_avulso as _avulso,
    criar_pronta as _pronta,
    criar_personalizavel as _personalizavel,
    selecao as _sel,
    item_avulso as _item_avulso,
    item_marmita as _item_marmita,
    config_entrega,
    criar_combo,
)


def _config(db, restaurante, modo=DeliveryChargeMode.GRATIS, **extra):
    return config_entrega(db, restaurante, charge_mode=modo, **extra)


def _combo(db, restaurante, marmitas, alimentos, preco="45.00"):
    return criar_combo(db, restaurante, marmitas, alimentos, preco=preco)


def _payload(restaurante, itens, endereco=None, **extra):
    dados = {
        "restaurante_slug": restaurante.slug,
        "endereco_id": endereco.id if endereco else None,
        "forma_pagamento": "PIX",
        "itens": itens,
    }
    dados.update(extra)
    return OrderCreate(**dados)


def _criar(db, payload, cliente):
    auth = AuthenticatedClient(id=cliente.id, name=cliente.name, phone=cliente.phone)
    return pedido_service.criar_pedido(db, payload, auth)


def _contagens(db):
    return db.query(Order).count(), db.query(OrderItem).count()


def _falha(codigo, trecho, chamada):
    with pytest.raises(HTTPException) as erro:
        chamada()
    assert erro.value.status_code == codigo
    assert trecho in erro.value.detail


def test_pedido_com_um_item_de_cada_tipo_e_persistido_com_snapshot(
    db, restaurante, cliente, endereco, status_criado, cat_venda, cat_composicao, cat_composicao_2
):
    _config(db, restaurante, DeliveryChargeMode.FIXO, fixed_fee=Decimal("7.50"))
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    frango = _alimento(db, restaurante, "Frango", cat_composicao)
    arroz = _alimento(db, restaurante, "Arroz", cat_composicao_2)
    pronta = _pronta(db, restaurante, [(arroz, 1)])
    monte = _personalizavel(db, restaurante, [(cat_composicao, 1)])
    combo = _combo(db, restaurante, [(pronta, 1)], [(feijoada, 1)])

    payload = _payload(
        restaurante,
        [
            _item_marmita(pronta, quantidade=2),
            _item_marmita(
                monte, selecoes=[_sel(cat_composicao, (frango, 1))], observacao="sem tempero"
            ),
            {"tipo": "COMBO", "combo_id": combo.id},
            _item_avulso(feijoada, 2),
        ],
        endereco,
        forma_pagamento="DINHEIRO",
        valor_pago_dinheiro=Decimal("200.00"),
        observacoes="tocar o interfone",
    )

    pedido = _criar(db, payload, cliente)

    assert pedido.items_amount == Decimal("175.80")
    assert pedido.delivery_fee == Decimal("7.50")
    assert pedido.total_amount == Decimal("183.30")
    assert pedido.change_amount == Decimal("16.70")
    assert pedido.notes == "tocar o interfone"
    assert pedido.client_id == cliente.id
    assert pedido.restaurant_id == restaurante.id
    assert pedido.status_id == status_criado.id
    assert pedido.service_type == OrderServiceType.DELIVERY
    assert (pedido.address_street, pedido.address_number, pedido.address_neighborhood) == (
        "Rua das Flores", "123", "Centro",
    )

    assert len(pedido.items) == 4
    por_nome = {i.food_name: i for i in pedido.items}

    item_pronta = por_nome["Pronta"]
    assert (item_pronta.meal_box_id, item_pronta.combo_id, item_pronta.food_id) == (pronta.id, None, None)
    assert (item_pronta.quantity, item_pronta.base_price, item_pronta.subtotal) == (
        2, Decimal("20.00"), Decimal("40.00"),
    )
    assert item_pronta.snapshot["tipo_marmita"] == "PRONTA"

    item_monte = por_nome["Monte a sua"]
    assert (item_monte.meal_box_id, item_monte.combo_id, item_monte.food_id) == (monte.id, None, None)
    assert item_monte.notes == "sem tempero"
    assert item_monte.snapshot["escolhas"][0]["nome"] == "Frango"

    item_combo = por_nome["Combo Almoço"]
    assert (item_combo.combo_id, item_combo.meal_box_id, item_combo.food_id) == (combo.id, None, None)
    assert item_combo.subtotal == Decimal("45.00")
    assert item_combo.snapshot["tipo"] == "COMBO"

    item_avulso = por_nome["Feijoada"]
    assert (item_avulso.food_id, item_avulso.meal_box_id, item_avulso.combo_id) == (feijoada.id, None, None)
    assert (item_avulso.quantity, item_avulso.subtotal) == (2, Decimal("65.80"))
    assert item_avulso.snapshot["tipo"] == "AVULSO"


def test_retirada_nao_exige_endereco_nem_cobra_entrega(
    db, restaurante, cliente, status_criado, cat_venda
):
    _config(db, restaurante, DeliveryChargeMode.FIXO, fixed_fee=Decimal("7.50"))
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")

    pedido = _criar(
        db,
        _payload(restaurante, [_item_avulso(feijoada)], tipo_atendimento="RETIRADA"),
        cliente,
    )

    assert pedido.service_type == OrderServiceType.PICKUP
    assert pedido.delivery_fee == Decimal("0.00")
    assert pedido.total_amount == Decimal("32.90")
    assert pedido.address_street is None


def test_frete_gratis_a_partir_do_valor(db, restaurante, cliente, endereco, status_criado, cat_venda):
    _config(
        db, restaurante, DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("7.50"), free_delivery_from=Decimal("30.00"),
    )
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")

    pedido = _criar(db, _payload(restaurante, [_item_avulso(feijoada)], endereco), cliente)

    assert pedido.delivery_fee == Decimal("0.00")
    assert pedido.total_amount == Decimal("32.90")


def test_valor_minimo_rejeita_e_nao_persiste_nada(
    db, restaurante, cliente, endereco, status_criado, cat_venda
):
    _config(db, restaurante, min_order_value=Decimal("50.00"))
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    antes = _contagens(db)

    _falha(
        422, "valor mínimo",
        lambda: _criar(db, _payload(restaurante, [_item_avulso(feijoada)], endereco), cliente),
    )
    assert _contagens(db) == antes


def test_item_invalido_cancela_o_pedido_inteiro(
    db, restaurante, cliente, endereco, status_criado, cat_venda, cat_composicao_2
):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    arroz = _alimento(db, restaurante, "Arroz", cat_composicao_2)
    pronta = _pronta(db, restaurante, [(arroz, 1)])
    pronta.sold_out_on = hoje_local()
    antes = _contagens(db)

    _falha(
        422, "esgotado hoje",
        lambda: _criar(
            db,
            _payload(restaurante, [_item_avulso(feijoada), _item_marmita(pronta)], endereco),
            cliente,
        ),
    )
    assert _contagens(db) == antes


def test_slug_inexistente_retorna_404(db, restaurante, cliente, endereco, status_criado, cat_venda):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    payload = _payload(restaurante, [_item_avulso(feijoada)], endereco, restaurante_slug="nao-existe")

    _falha(404, "não encontrado", lambda: _criar(db, payload, cliente))


def test_restaurante_pausado_nao_aceita_pedidos(
    db, restaurante, cliente, endereco, status_criado, cat_venda
):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    restaurante.is_paused = True

    _falha(
        422, "",
        lambda: _criar(db, _payload(restaurante, [_item_avulso(feijoada)], endereco), cliente),
    )


def test_forma_de_pagamento_nao_aceita_pelo_restaurante(
    db, restaurante, cliente, endereco, status_criado, cat_venda, aceitar_formas
):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    aceitar_formas(restaurante, "DINHEIRO")

    _falha(
        422, "não aceita",
        lambda: _criar(db, _payload(restaurante, [_item_avulso(feijoada)], endereco), cliente),
    )


def test_endereco_de_outro_cliente_retorna_404(
    db, restaurante, cliente, outro_cliente, status_criado, cat_venda
):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    alheio = CustomerAddress(
        client_id=outro_cliente.id, street="Rua Alheia", number="1", neighborhood="Centro"
    )
    db.add(alheio)
    db.flush()

    _falha(
        404, "Endereço",
        lambda: _criar(db, _payload(restaurante, [_item_avulso(feijoada)], alheio), cliente),
    )


def test_bairro_fora_da_area_de_entrega(db, restaurante, cliente, endereco, status_criado, cat_venda):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")

    _falha(
        422, "fora da área de entrega",
        lambda: _criar(db, _payload(restaurante, [_item_avulso(feijoada)], endereco), cliente),
    )


def test_dinheiro_exige_valor_e_cobre_o_total(
    db, restaurante, cliente, endereco, status_criado, cat_venda
):
    _config(db, restaurante)
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")

    _falha(
        422, "Informe o valor pago",
        lambda: _criar(
            db,
            _payload(restaurante, [_item_avulso(feijoada)], endereco, forma_pagamento="DINHEIRO"),
            cliente,
        ),
    )
    _falha(
        400, "menor que o total",
        lambda: _criar(
            db,
            _payload(
                restaurante, [_item_avulso(feijoada)], endereco,
                forma_pagamento="DINHEIRO", valor_pago_dinheiro=Decimal("10.00"),
            ),
            cliente,
        ),
    )