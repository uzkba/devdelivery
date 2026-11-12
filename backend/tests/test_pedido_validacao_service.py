from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.model.models import (
    Combo,
    ComboFoodItem,
    ComboMealBoxItem,
    Food,
    FoodCategory,
    MealBox,
    MealBoxCategory,
    MealBoxComposition,
    MealBoxKind,
)
from app.schemas.pedido_v2_schemas import ItemAvulsoIn, ItemComboIn, ItemMarmitaIn
from app.services import disponibilidade_service as disponibilidade
from app.services import pedido_validacao_service as validacao

HOJE = date(2026, 11, 11)  # quarta-feira (weekday 2)


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


def _avulso(db, restaurante, venda, nome="Feijoada", **extra):
    return _alimento(
        db, restaurante, nome, venda=venda,
        is_sellable_alone=True, standalone_price=Decimal("30.00"), **extra,
    )


def _marmita_pronta(db, restaurante, *alimentos, nome="Pronta"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome, kind=MealBoxKind.READY, price=Decimal("20.00")
    )
    m.composition = [
        MealBoxComposition(food_id=a.id, fixed_quantity=1, position=i)
        for i, a in enumerate(alimentos)
    ]
    db.add(m)
    db.flush()
    return m


def _marmita_personalizavel(db, restaurante, exigencias, nome="Monte a sua"):
    m = MealBox(
        restaurant_id=restaurante.id, name=nome,
        kind=MealBoxKind.CUSTOMIZABLE, price=Decimal("25.00"),
    )
    m.categories = [
        MealBoxCategory(food_category_id=c.id, required_quantity=q, position=i)
        for i, (c, q) in enumerate(exigencias)
    ]
    db.add(m)
    db.flush()
    return m


def _combo(db, restaurante, marmitas=(), alimentos=()):
    c = Combo(restaurant_id=restaurante.id, name="Combo", price=Decimal("40.00"))
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


def _in_avulso(alimento):
    return ItemAvulsoIn(tipo="AVULSO", alimento_id=alimento.id)


def _in_marmita(marmita, *selecoes):
    return ItemMarmitaIn(tipo="MARMITA", marmita_id=marmita.id, selecoes=list(selecoes))


def _in_combo(combo, *marmitas):
    return ItemComboIn(
        tipo="COMBO", combo_id=combo.id,
        marmitas=[{"marmita_id": m.id, "selecoes": list(s)} for m, s in marmitas],
    )


def _rejeita(trecho, chamada):
    with pytest.raises(HTTPException) as erro:
        chamada()
    assert erro.value.status_code == 422
    assert trecho in erro.value.detail


# --------------------------- fixtures ---------------------------
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
    return _avulso(db, restaurante, cat_venda_bebida, nome="Suco")


# --------------------------- avulso ---------------------------
def test_avulso_valido(db, restaurante, cat_venda):
    feijoada = _avulso(db, restaurante, cat_venda)
    assert validacao.validar_item_avulso(db, restaurante.id, _in_avulso(feijoada), HOJE) is feijoada


def test_avulso_de_outro_restaurante_e_rejeitado(db, restaurante, outro_restaurante, cat_venda):
    feijoada = _avulso(db, restaurante, cat_venda)
    _rejeita(
        "não encontrado",
        lambda: validacao.validar_item_avulso(db, outro_restaurante.id, _in_avulso(feijoada), HOJE),
    )


def test_alimento_de_composicao_nao_e_vendido_avulso(db, restaurante, frango):
    _rejeita(
        "não está à venda",
        lambda: validacao.validar_item_avulso(db, restaurante.id, _in_avulso(frango), HOJE),
    )


def test_avulso_em_categoria_de_venda_inativa_e_rejeitado(db, restaurante):
    inativa = FoodCategory(
        restaurant_id=restaurante.id, name="Inativa", type="venda", group="prato", is_active=False
    )
    db.add(inativa)
    db.flush()
    item = _avulso(db, restaurante, inativa)
    _rejeita(
        "não está à venda",
        lambda: validacao.validar_item_avulso(db, restaurante.id, _in_avulso(item), HOJE),
    )


def test_avulso_inativo_esgotado_ou_fora_do_dia(db, restaurante, cat_venda):
    feijoada = _avulso(db, restaurante, cat_venda)
    chamada = lambda: validacao.validar_item_avulso(db, restaurante.id, _in_avulso(feijoada), HOJE)

    feijoada.sold_out_on = HOJE
    _rejeita("esgotado hoje", chamada)
    feijoada.sold_out_on = None

    feijoada.is_active = False
    _rejeita("indisponível", chamada)
    feijoada.is_active = True

    disponibilidade.definir_regra(db, feijoada, "PERSONALIZADO", [0])  # so segunda
    _rejeita("não é servido hoje", chamada)


# --------------------------- marmita pronta ---------------------------
def test_marmita_pronta_valida(db, restaurante, arroz):
    pronta = _marmita_pronta(db, restaurante, arroz)
    resultado = validacao.validar_item_marmita(db, restaurante.id, _in_marmita(pronta), HOJE)
    assert resultado.marmita is pronta
    assert resultado.escolhas == ()


def test_marmita_pronta_nao_aceita_escolhas(db, restaurante, arroz, cat_composicao_2):
    pronta = _marmita_pronta(db, restaurante, arroz)
    item = _in_marmita(pronta, _sel(cat_composicao_2, (arroz, 1)))
    _rejeita("não aceita escolhas", lambda: validacao.validar_item_marmita(db, restaurante.id, item, HOJE))


def test_marmita_pronta_com_alimento_da_composicao_esgotado_ou_inativo(db, restaurante, arroz):
    pronta = _marmita_pronta(db, restaurante, arroz)
    chamada = lambda: validacao.validar_item_marmita(db, restaurante.id, _in_marmita(pronta), HOJE)

    arroz.sold_out_on = HOJE
    _rejeita("esgotado hoje", chamada)
    arroz.sold_out_on = None

    arroz.is_active = False
    _rejeita("indisponível", chamada)


def test_marmita_inativa_esgotada_ou_de_outro_restaurante(db, restaurante, outro_restaurante, arroz):
    pronta = _marmita_pronta(db, restaurante, arroz)
    chamada = lambda: validacao.validar_item_marmita(db, restaurante.id, _in_marmita(pronta), HOJE)

    pronta.sold_out_on = HOJE
    _rejeita("esgotado hoje", chamada)
    pronta.sold_out_on = None

    pronta.is_active = False
    _rejeita("indisponível", chamada)
    pronta.is_active = True

    _rejeita(
        "não encontrada",
        lambda: validacao.validar_item_marmita(db, outro_restaurante.id, _in_marmita(pronta), HOJE),
    )


# --------------------------- marmita personalizavel ---------------------------
def test_personalizavel_valida_e_agrupa_na_ordem_das_categorias(
    db, restaurante, cat_composicao, cat_composicao_2, frango, arroz
):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 2), (cat_composicao_2, 1)])
    item = _in_marmita(
        monte,
        _sel(cat_composicao_2, (arroz, 1)),  # enviado fora de ordem
        _sel(cat_composicao, (frango, 2)),  # repete o mesmo alimento via quantidade
    )
    resultado = validacao.validar_item_marmita(db, restaurante.id, item, HOJE)

    assert [(e.categoria.id, e.alimento.name, e.quantidade) for e in resultado.escolhas] == [
        (cat_composicao.id, "Frango", 2),
        (cat_composicao_2.id, "Arroz", 1),
    ]


def test_personalizavel_com_soma_errada(db, restaurante, cat_composicao, frango, bife):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 2)])
    chamada = lambda sel: validacao.validar_item_marmita(db, restaurante.id, _in_marmita(monte, sel), HOJE)

    _rejeita("Escolha exatamente 2", lambda: chamada(_sel(cat_composicao, (frango, 1))))
    _rejeita("Escolha exatamente 2", lambda: chamada(_sel(cat_composicao, (frango, 2), (bife, 1))))


def test_personalizavel_sem_selecao_de_categoria_obrigatoria(db, restaurante, cat_composicao):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1)])
    _rejeita(
        "Escolha exatamente 1",
        lambda: validacao.validar_item_marmita(db, restaurante.id, _in_marmita(monte), HOJE),
    )


def test_personalizavel_com_categoria_que_nao_faz_parte(
    db, restaurante, cat_composicao, cat_composicao_2, frango, arroz
):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1)])
    item = _in_marmita(monte, _sel(cat_composicao, (frango, 1)), _sel(cat_composicao_2, (arroz, 1)))
    _rejeita("não faz parte", lambda: validacao.validar_item_marmita(db, restaurante.id, item, HOJE))


def test_personalizavel_com_alimento_de_outra_categoria(
    db, restaurante, cat_composicao, cat_composicao_2, arroz
):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1), (cat_composicao_2, 0)])
    item = _in_marmita(monte, _sel(cat_composicao, (arroz, 1)))  # arroz e de cat_composicao_2
    _rejeita("não pertence", lambda: validacao.validar_item_marmita(db, restaurante.id, item, HOJE))


def test_categoria_com_quantidade_zero_nao_recebe_escolhas(
    db, restaurante, cat_composicao, cat_composicao_2, frango, arroz
):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1), (cat_composicao_2, 0)])

    ok = validacao.validar_item_marmita(
        db, restaurante.id, _in_marmita(monte, _sel(cat_composicao, (frango, 1))), HOJE
    )
    assert len(ok.escolhas) == 1

    item = _in_marmita(monte, _sel(cat_composicao, (frango, 1)), _sel(cat_composicao_2, (arroz, 1)))
    _rejeita("não recebe escolhas", lambda: validacao.validar_item_marmita(db, restaurante.id, item, HOJE))


def test_personalizavel_com_alimento_esgotado_ou_de_outro_restaurante(
    db, restaurante, cat_composicao, frango, alimento_b
):
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1)])

    frango.sold_out_on = HOJE
    _rejeita(
        "esgotado hoje",
        lambda: validacao.validar_item_marmita(
            db, restaurante.id, _in_marmita(monte, _sel(cat_composicao, (frango, 1))), HOJE
        ),
    )

    _rejeita(
        "não encontrado",
        lambda: validacao.validar_item_marmita(
            db, restaurante.id, _in_marmita(monte, _sel(cat_composicao, (alimento_b, 1))), HOJE
        ),
    )


# --------------------------- combo ---------------------------
def _combo_completo(db, restaurante, cat_composicao, arroz, suco):
    pronta = _marmita_pronta(db, restaurante, arroz)
    monte = _marmita_personalizavel(db, restaurante, [(cat_composicao, 1)])
    combo = _combo(db, restaurante, marmitas=[(pronta, 1), (monte, 2)], alimentos=[(suco, 1)])
    return combo, pronta, monte


def test_combo_valido_devolve_uma_marmita_por_unidade_configurada(
    db, restaurante, cat_composicao, frango, bife, arroz, suco
):
    combo, _, monte = _combo_completo(db, restaurante, cat_composicao, arroz, suco)
    item = _in_combo(
        combo,
        (monte, [_sel(cat_composicao, (frango, 1))]),
        (monte, [_sel(cat_composicao, (bife, 1))]),
    )
    resultado = validacao.validar_item_combo(db, restaurante.id, item, HOJE)

    assert resultado.combo is combo
    assert [m.marmita.id for m in resultado.marmitas] == [monte.id, monte.id]
    assert [m.escolhas[0].alimento.name for m in resultado.marmitas] == ["Frango", "Bife"]


def test_combo_sem_marmita_personalizavel_nao_precisa_de_configuracao(db, restaurante, arroz, suco):
    pronta = _marmita_pronta(db, restaurante, arroz)
    combo = _combo(db, restaurante, marmitas=[(pronta, 1)], alimentos=[(suco, 1)])
    resultado = validacao.validar_item_combo(db, restaurante.id, _in_combo(combo), HOJE)
    assert resultado.marmitas == ()


def test_combo_com_configuracoes_faltando(db, restaurante, cat_composicao, frango, arroz, suco):
    combo, _, monte = _combo_completo(db, restaurante, cat_composicao, arroz, suco)
    item = _in_combo(combo, (monte, [_sel(cat_composicao, (frango, 1))]))  # 1 de 2
    _rejeita("Configure 2 unidade(s)", lambda: validacao.validar_item_combo(db, restaurante.id, item, HOJE))


def test_combo_com_configuracao_para_marmita_pronta(
    db, restaurante, cat_composicao, frango, bife, arroz, suco
):
    combo, pronta, monte = _combo_completo(db, restaurante, cat_composicao, arroz, suco)
    item = _in_combo(
        combo,
        (monte, [_sel(cat_composicao, (frango, 1))]),
        (monte, [_sel(cat_composicao, (bife, 1))]),
        (pronta, []),
    )
    _rejeita(
        "não é personalizável",
        lambda: validacao.validar_item_combo(db, restaurante.id, item, HOJE),
    )


def test_combo_com_selecao_invalida_em_uma_das_unidades(
    db, restaurante, cat_composicao, frango, arroz, suco
):
    combo, _, monte = _combo_completo(db, restaurante, cat_composicao, arroz, suco)
    item = _in_combo(
        combo,
        (monte, [_sel(cat_composicao, (frango, 1))]),
        (monte, [_sel(cat_composicao, (frango, 3))]),
    )
    _rejeita("Escolha exatamente 1", lambda: validacao.validar_item_combo(db, restaurante.id, item, HOJE))


def test_combo_com_componente_inativo_esgotado_ou_fora_do_dia(db, restaurante, arroz, suco):
    pronta = _marmita_pronta(db, restaurante, arroz)
    combo = _combo(db, restaurante, marmitas=[(pronta, 1)], alimentos=[(suco, 1)])
    chamada = lambda: validacao.validar_item_combo(db, restaurante.id, _in_combo(combo), HOJE)

    suco.sold_out_on = HOJE
    _rejeita("esgotado hoje", chamada)
    suco.sold_out_on = None

    arroz.sold_out_on = HOJE  # alimento dentro da marmita pronta do combo
    _rejeita("esgotado hoje", chamada)
    arroz.sold_out_on = None

    disponibilidade.definir_regra(db, pronta, "PERSONALIZADO", [0])
    _rejeita("não é servido hoje", chamada)


def test_combo_com_item_desativado_esgotado_ou_de_outro_restaurante(
    db, restaurante, outro_restaurante, arroz, suco
):
    pronta = _marmita_pronta(db, restaurante, arroz)
    combo = _combo(db, restaurante, marmitas=[(pronta, 1)], alimentos=[(suco, 1)])
    chamada = lambda: validacao.validar_item_combo(db, restaurante.id, _in_combo(combo), HOJE)

    combo.sold_out_on = HOJE
    _rejeita("esgotado hoje", chamada)
    combo.sold_out_on = None

    pronta.is_active = False
    _rejeita("indisponível no momento", chamada)
    pronta.is_active = True

    _rejeita(
        "não encontrado",
        lambda: validacao.validar_item_combo(db, outro_restaurante.id, _in_combo(combo), HOJE),
    )
