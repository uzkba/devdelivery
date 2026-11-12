import json
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.model.models import (
    Combo,
    ComboFoodItem,
    ComboMealBoxItem,
    Food,
    MealBox,
    MealBoxCategory,
    MealBoxComposition,
    MealBoxKind,
)
from app.schemas.pedido_v2_schemas import ItemAvulsoIn, ItemComboIn, ItemMarmitaIn
from app.services import pedido_snapshot_service as snapshot

HOJE = date(2026, 11, 11)


# --------------------------- helpers ---------------------------
def _alimento(db, restaurante, nome, composicao=None, venda=None, **extra):
    f = Food(
        restaurant_id=restaurante.id,
        name=nome,
        composition_category_id=composicao.id if composicao else None,
        sale_category_id=venda.id if venda else None,
        **extra,
    )
    db.add(f)
    db.flush()
    return f


def _avulso(db, restaurante, venda, nome, preco):
    return _alimento(
        db, restaurante, nome, venda=venda,
        is_sellable_alone=True, standalone_price=Decimal(preco),
    )


def _pronta(db, restaurante, composicao, nome="Pronta", preco="20.00"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome, kind=MealBoxKind.READY, price=Decimal(preco)
    )
    m.composition = [
        MealBoxComposition(food_id=a.id, fixed_quantity=q, position=i)
        for i, (a, q) in enumerate(composicao)
    ]
    db.add(m)
    db.flush()
    return m


def _personalizavel(db, restaurante, exigencias, nome="Monte a sua", preco="25.00"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome,
        kind=MealBoxKind.CUSTOMIZABLE, price=Decimal(preco),
    )
    m.categories = [
        MealBoxCategory(food_category_id=c.id, required_quantity=q, position=i)
        for i, (c, q) in enumerate(exigencias)
    ]
    db.add(m)
    db.flush()
    return m


def _combo(db, restaurante, marmitas, alimentos, preco="40.00"):
    c = Combo(restaurant_id=restaurante.id, name="Combo Almoço", price=Decimal(preco))
    c.meal_box_items = [
        ComboMealBoxItem(meal_box_id=m.id, quantity=q, position=i)
        for i, (m, q) in enumerate(marmitas)
    ]
    c.food_items = [
        ComboFoodItem(food_id=a.id, quantity=q, position=i) for i, (a, q) in enumerate(alimentos)
    ]
    db.add(c)
    db.flush()
    return c


def _sel(categoria, *pares):
    return {
        "categoria_id": categoria.id,
        "alimentos": [{"alimento_id": a.id, "quantidade": q} for a, q in pares],
    }


@pytest.fixture()
def frango(db, restaurante, cat_composicao):
    return _alimento(db, restaurante, "Frango", cat_composicao)


@pytest.fixture()
def bife(db, restaurante, cat_composicao):
    return _alimento(db, restaurante, "Bife", cat_composicao)


@pytest.fixture()
def arroz(db, restaurante, cat_composicao_2):
    return _alimento(db, restaurante, "Arroz", cat_composicao_2)


@pytest.fixture()
def suco(db, restaurante, cat_venda_bebida):
    return _avulso(db, restaurante, cat_venda_bebida, "Suco", "8.00")


# --------------------------- avulso ---------------------------
def test_item_avulso_monta_preco_ids_e_snapshot(db, restaurante, cat_venda):
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    item = ItemAvulsoIn(
        tipo="AVULSO", alimento_id=feijoada.id, quantidade=3, observacao="sem couve"
    )

    montado = snapshot.montar_item_pedido(db, restaurante.id, item, HOJE)

    assert montado.tipo == "AVULSO"
    assert montado.nome == "Feijoada"
    assert montado.quantidade == 3
    assert montado.preco_unitario == Decimal("32.90")
    assert montado.subtotal == Decimal("98.70")
    assert montado.observacao == "sem couve"
    assert (montado.food_id, montado.meal_box_id, montado.combo_id) == (feijoada.id, None, None)
    assert montado.snapshot == {
        "versao": 1,
        "tipo": "AVULSO",
        "alimento_id": str(feijoada.id),
        "nome": "Feijoada",
        "categoria": cat_venda.name,
        "preco_unitario": "32.90",
    }


# --------------------------- marmita ---------------------------
def test_marmita_pronta_congela_a_composicao(db, restaurante, arroz, frango):
    pronta = _pronta(db, restaurante, [(arroz, 1), (frango, 2)])

    montado = snapshot.montar_item_pedido(
        db, restaurante.id, ItemMarmitaIn(tipo="MARMITA", marmita_id=pronta.id), HOJE
    )

    assert montado.nome == "Pronta"
    assert montado.subtotal == Decimal("20.00")
    assert (montado.food_id, montado.meal_box_id, montado.combo_id) == (None, pronta.id, None)
    assert montado.snapshot == {
        "versao": 1,
        "tipo": "MARMITA",
        "preco_unitario": "20.00",
        "tamanho": None,
        "marmita_id": str(pronta.id),
        "nome": "Pronta",
        "tipo_marmita": "PRONTA",
        "composicao": [
            {"alimento_id": str(arroz.id), "nome": "Arroz", "quantidade": 1},
            {"alimento_id": str(frango.id), "nome": "Frango", "quantidade": 2},
        ],
    }


def test_marmita_personalizavel_congela_as_escolhas_e_multiplica_a_quantidade(
    db, restaurante, cat_composicao, cat_composicao_2, frango, arroz
):
    monte = _personalizavel(db, restaurante, [(cat_composicao, 1), (cat_composicao_2, 2)])
    item = ItemMarmitaIn(
        tipo="MARMITA",
        marmita_id=monte.id,
        quantidade=2,
        selecoes=[_sel(cat_composicao_2, (arroz, 2)), _sel(cat_composicao, (frango, 1))],
    )

    montado = snapshot.montar_item_pedido(db, restaurante.id, item, HOJE)

    assert montado.preco_unitario == Decimal("25.00")
    assert montado.subtotal == Decimal("50.00")  # preco x quantidade da linha
    assert montado.snapshot["tipo_marmita"] == "PERSONALIZAVEL"
    assert "composicao" not in montado.snapshot
    assert montado.snapshot["escolhas"] == [  # ordem das categorias da marmita
        {
            "categoria_id": str(cat_composicao.id),
            "categoria": cat_composicao.name,
            "alimento_id": str(frango.id),
            "nome": "Frango",
            "quantidade": 1,
        },
        {
            "categoria_id": str(cat_composicao_2.id),
            "categoria": cat_composicao_2.name,
            "alimento_id": str(arroz.id),
            "nome": "Arroz",
            "quantidade": 2,
        },
    ]


# --------------------------- combo ---------------------------
def _item_combo(db, restaurante, cat_composicao, frango, bife, arroz, suco, quantidade=1):
    pronta = _pronta(db, restaurante, [(arroz, 1)])
    monte = _personalizavel(db, restaurante, [(cat_composicao, 1)])
    combo = _combo(db, restaurante, [(pronta, 1), (monte, 2)], [(suco, 1)])
    item = ItemComboIn(
        tipo="COMBO",
        combo_id=combo.id,
        quantidade=quantidade,
        marmitas=[
            {"marmita_id": monte.id, "selecoes": [_sel(cat_composicao, (frango, 1))]},
            {"marmita_id": monte.id, "selecoes": [_sel(cat_composicao, (bife, 1))]},
        ],
    )
    return combo, pronta, monte, item


def test_combo_usa_o_preco_proprio_e_congela_cada_unidade_configurada(
    db, restaurante, cat_composicao, frango, bife, arroz, suco
):
    combo, pronta, monte, item = _item_combo(
        db, restaurante, cat_composicao, frango, bife, arroz, suco, quantidade=2
    )

    montado = snapshot.montar_item_pedido(db, restaurante.id, item, HOJE)

    assert montado.tipo == "COMBO"
    assert montado.preco_unitario == Decimal("40.00")  # preco do combo, nao a soma dos itens
    assert montado.subtotal == Decimal("80.00")
    assert (montado.food_id, montado.meal_box_id, montado.combo_id) == (None, None, combo.id)

    dados = montado.snapshot
    assert (dados["versao"], dados["tipo"], dados["nome"]) == (1, "COMBO", "Combo Almoço")
    assert dados["preco_unitario"] == "40.00"
    assert dados["alimentos"] == [{"alimento_id": str(suco.id), "nome": "Suco", "quantidade": 1}]

    pronta_snap, unidade_1, unidade_2 = dados["marmitas"]
    assert pronta_snap["tipo_marmita"] == "PRONTA" and pronta_snap["quantidade"] == 1
    assert pronta_snap["composicao"] == [
        {"alimento_id": str(arroz.id), "nome": "Arroz", "quantidade": 1}
    ]
    for unidade, nome in ((unidade_1, "Frango"), (unidade_2, "Bife")):
        assert unidade["marmita_id"] == str(monte.id)
        assert unidade["tipo_marmita"] == "PERSONALIZAVEL"
        assert unidade["quantidade"] == 1
        assert [e["nome"] for e in unidade["escolhas"]] == [nome]


# --------------------------- propriedades gerais ---------------------------
def test_snapshot_e_serializavel_e_nao_muda_com_edicoes_posteriores(
    db, restaurante, cat_composicao, frango, bife, arroz, suco
):
    combo, pronta, monte, item = _item_combo(
        db, restaurante, cat_composicao, frango, bife, arroz, suco
    )
    montado = snapshot.montar_item_pedido(db, restaurante.id, item, HOJE)

    antes = json.dumps(montado.snapshot, sort_keys=True)  # falha se houver Decimal/UUID cru
    assert json.loads(antes) == montado.snapshot

    frango.name = "Outro nome"
    arroz.name = "Outro arroz"
    monte.name = "Renomeada"
    monte.price = Decimal("99.00")
    combo.price = Decimal("1.00")

    assert json.dumps(montado.snapshot, sort_keys=True) == antes


def test_erro_de_validacao_interrompe_a_montagem(db, restaurante, cat_venda):
    feijoada = _avulso(db, restaurante, cat_venda, "Feijoada", "32.90")
    feijoada.sold_out_on = HOJE

    with pytest.raises(HTTPException) as erro:
        snapshot.montar_item_pedido(
            db, restaurante.id, ItemAvulsoIn(tipo="AVULSO", alimento_id=feijoada.id), HOJE
        )
    assert erro.value.status_code == 422
    assert "esgotado hoje" in erro.value.detail