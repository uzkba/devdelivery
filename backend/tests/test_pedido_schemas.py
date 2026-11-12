import uuid

import pytest
from pydantic import ValidationError

from app.model.models import OrderServiceType
from app.schemas.pedido_schemas import (
    ItemAvulsoIn,
    ItemComboIn,
    ItemMarmitaIn,
    OrderCreate,
)


def _id() -> str:
    return str(uuid.uuid4())


def _avulso(**extra):
    return {"tipo": "AVULSO", "alimento_id": _id(), "quantidade": 2, **extra}


def _base(**extra):
    dados = {
        "restaurante_slug": "marmitas-da-vovo",
        "endereco_id": _id(),
        "forma_pagamento": "PIX",
        "itens": [_avulso()],
    }
    dados.update(extra)
    return dados


def test_aceita_um_item_de_cada_tipo():
    categoria = _id()
    pedido = OrderCreate(
        **_base(
            itens=[
                {"tipo": "MARMITA", "marmita_id": _id()},
                {
                    "tipo": "MARMITA",
                    "marmita_id": _id(),
                    "selecoes": [
                        {
                            "categoria_id": categoria,
                            "alimentos": [{"alimento_id": _id(), "quantidade": 2}],
                        }
                    ],
                },
                {
                    "tipo": "COMBO",
                    "combo_id": _id(),
                    "marmitas": [{"marmita_id": _id(), "selecoes": []}],
                },
                _avulso(),
            ]
        )
    )
    tipos = [type(i) for i in pedido.itens]
    assert tipos == [ItemMarmitaIn, ItemMarmitaIn, ItemComboIn, ItemAvulsoIn]


def test_retirada_nao_exige_endereco():
    pedido = OrderCreate(**_base(tipo_atendimento="RETIRADA", endereco_id=None))
    assert pedido.tipo_atendimento == OrderServiceType.PICKUP


def test_entrega_exige_endereco():
    with pytest.raises(ValidationError):
        OrderCreate(**_base(endereco_id=None))


def test_slug_invalido_e_rejeitado():
    for slug in ["AB", "Marmitas Da Vovo", "-abc", "abc-", "a" * 61]:
        with pytest.raises(ValidationError):
            OrderCreate(**_base(restaurante_slug=slug))


def test_restaurante_id_antigo_e_rejeitado():
    dados = _base()
    dados["restaurante_id"] = _id()
    with pytest.raises(ValidationError):
        OrderCreate(**dados)


def test_preco_enviado_pelo_cliente_e_rejeitado():
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[_avulso(preco="1.00")]))


def test_tipo_de_item_desconhecido_ou_ausente():
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[{"tipo": "BEBIDA", "alimento_id": _id()}]))
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[{"alimento_id": _id()}]))


def test_pedido_sem_itens_e_rejeitado():
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[]))


def test_quantidade_deve_ser_positiva():
    for qtd in (0, -1):
        with pytest.raises(ValidationError):
            OrderCreate(**_base(itens=[_avulso(quantidade=qtd)]))


def test_observacao_aceita_140_e_rejeita_141():
    pedido = OrderCreate(**_base(itens=[_avulso(observacao="a" * 140)]))
    assert len(pedido.itens[0].observacao) == 140
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[_avulso(observacao="a" * 141)]))


def test_observacao_e_aparada_e_vazia_vira_none():
    pedido = OrderCreate(**_base(itens=[_avulso(observacao="  sem cebola  ")]))
    assert pedido.itens[0].observacao == "sem cebola"
    pedido = OrderCreate(**_base(itens=[_avulso(observacao="   ")]))
    assert pedido.itens[0].observacao is None


def test_categoria_repetida_nas_selecoes_e_rejeitada():
    categoria = _id()
    selecoes = [
        {"categoria_id": categoria, "alimentos": []},
        {"categoria_id": categoria, "alimentos": []},
    ]
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[{"tipo": "MARMITA", "marmita_id": _id(), "selecoes": selecoes}]))


def test_alimento_repetido_na_mesma_categoria_e_rejeitado():
    alimento = _id()
    selecoes = [
        {
            "categoria_id": _id(),
            "alimentos": [
                {"alimento_id": alimento, "quantidade": 1},
                {"alimento_id": alimento, "quantidade": 1},
            ],
        }
    ]
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[{"tipo": "MARMITA", "marmita_id": _id(), "selecoes": selecoes}]))


def test_categoria_repetida_dentro_de_marmita_do_combo_e_rejeitada():
    categoria = _id()
    marmita = {
        "marmita_id": _id(),
        "selecoes": [
            {"categoria_id": categoria, "alimentos": []},
            {"categoria_id": categoria, "alimentos": []},
        ],
    }
    with pytest.raises(ValidationError):
        OrderCreate(**_base(itens=[{"tipo": "COMBO", "combo_id": _id(), "marmitas": [marmita]}]))