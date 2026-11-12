import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.model.models import (
    Combo,
    ComboFoodItem,
    ComboMealBoxItem,
    FoodComponent,
    MealBoxCategory,
    MealBoxComposition,
)
from app.services import detalhe_publico_service as svc
from app.services import disponibilidade_service as disponibilidade

HOJE = date(2026, 11, 6)
QUINTA = 3


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


def _get(client, slug, caminho, esperado=200):
    resposta = client.get(f"/restaurantes/{slug}/{caminho}")
    assert resposta.status_code == esperado
    return resposta.json()


def _pronta_com(db, marmita, itens):
    marmita.composition = [
        MealBoxComposition(food_id=a.id, fixed_quantity=q, position=i)
        for i, (a, q) in enumerate(itens)
    ]
    db.flush()
    db.refresh(marmita)
    return marmita


def _personalizavel_com(db, marmita, categorias):
    marmita.categories = [
        MealBoxCategory(food_category_id=c.id, required_quantity=q, position=i)
        for i, (c, q) in enumerate(categorias)
    ]
    db.flush()
    db.refresh(marmita)
    return marmita


def _combo(db, restaurante, preco, marmitas=(), alimentos=()):
    combo = Combo(restaurant_id=restaurante.id, name="Combo", price=Decimal(preco))
    combo.meal_box_items = [
        ComboMealBoxItem(meal_box_id=m.id, quantity=q, position=i)
        for i, (m, q) in enumerate(marmitas)
    ]
    combo.food_items = [
        ComboFoodItem(food_id=a.id, quantity=q, position=i)
        for i, (a, q) in enumerate(alimentos)
    ]
    db.add(combo)
    db.flush()
    db.refresh(combo)
    return combo


# =============================== marmita pronta ===============================
def test_marmita_pronta_traz_composicao_e_nao_tem_categorias(
    db, client, restaurante, marmita_pronta, alimento_arroz, alimento_feijao
):
    _pronta_com(db, marmita_pronta, [(alimento_arroz, 1), (alimento_feijao, 2)])
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_pronta.id}")
    assert corpo["tipo"] == "PRONTA"
    assert [(i["nome"], i["quantidade"]) for i in corpo["composicao"]] == [
        ("Arroz", 1),
        ("Feijão", 2),
    ]
    assert corpo["categorias"] == []
    assert corpo["nutricao"] is None
    assert corpo["disponivel"] is True
    assert corpo["motivo_indisponivel"] is None


def test_marmita_pronta_com_nutricao_parcial(db, client, restaurante, marmita_pronta):
    marmita_pronta.calories_kcal = 650
    marmita_pronta.protein_g = Decimal("30.0")
    db.flush()
    nutricao = _get(client, restaurante.slug, f"marmitas/{marmita_pronta.id}")["nutricao"]
    assert nutricao["calorias_kcal"] == 650
    assert Decimal(nutricao["proteina_g"]) == Decimal("30.0")
    assert nutricao["carboidrato_g"] is None
    assert nutricao["gordura_g"] is None


def test_marmita_esgotada_hoje_responde_200_indisponivel(db, client, restaurante, marmita_pronta):
    marmita_pronta.sold_out_on = HOJE
    db.flush()
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_pronta.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "esgotado_hoje"


def test_marmita_fora_do_dia_responde_200_indisponivel(db, client, restaurante, marmita_pronta):
    disponibilidade.definir_regra(db, marmita_pronta, "PERSONALIZADO", [QUINTA])
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_pronta.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "fora_do_dia"


def test_marmita_inativa_da_404(client, restaurante, marmita_inativa):
    _get(client, restaurante.slug, f"marmitas/{marmita_inativa.id}", 404)


def test_marmita_inexistente_da_404(client, restaurante):
    _get(client, restaurante.slug, f"marmitas/{uuid.uuid4()}", 404)


def test_marmita_de_outro_restaurante_da_404(client, restaurante, marmita_b):
    _get(client, restaurante.slug, f"marmitas/{marmita_b.id}", 404)


def test_restaurante_inativo_da_404_no_detalhe(db, client, restaurante, marmita_pronta):
    restaurante.is_active = False
    db.flush()
    _get(client, restaurante.slug, f"marmitas/{marmita_pronta.id}", 404)


# =========================== marmita personalizavel ===========================
def test_personalizavel_traz_categorias_com_opcoes(
    db, client, restaurante, marmita_personalizavel,
    cat_composicao, cat_composicao_2, alimento_arroz, alimento_feijao,
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1), (cat_composicao_2, 2)])
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")
    assert corpo["tipo"] == "PERSONALIZAVEL"
    assert corpo["composicao"] == []
    assert [
        (c["nome"], c["quantidade_exigida"], [o["nome"] for o in c["opcoes"]])
        for c in corpo["categorias"]
    ] == [("Carnes", 1, ["Arroz"]), ("Acompanhamentos", 2, ["Feijão"])]
    assert corpo["disponivel"] is True


def test_personalizavel_nunca_mostra_nutricao(
    db, client, restaurante, marmita_personalizavel, cat_composicao, alimento_arroz
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1)])
    marmita_personalizavel.calories_kcal = 700
    db.flush()
    assert _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")["nutricao"] is None


def test_opcao_inativa_ou_esgotada_some_da_categoria(
    db, client, restaurante, marmita_personalizavel, cat_composicao,
    alimento_arroz, alimento_inativo, _alimento_extra,
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1)])
    _alimento_extra.sold_out_on = HOJE
    db.flush()
    categoria = _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")["categorias"][0]
    assert [o["nome"] for o in categoria["opcoes"]] == ["Arroz"]


def test_categoria_sem_opcao_visivel_derruba_a_marmita(
    db, client, restaurante, marmita_personalizavel,
    cat_composicao, cat_composicao_2, alimento_arroz, alimento_feijao,
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1), (cat_composicao_2, 2)])
    alimento_feijao.sold_out_on = HOJE
    db.flush()
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "sem_opcoes"
    assert [o["nome"] for o in corpo["categorias"][0]["opcoes"]] == ["Arroz"]
    assert corpo["categorias"][1]["opcoes"] == []


def test_opcao_fora_do_dia_some_da_categoria(
    db, client, restaurante, marmita_personalizavel, cat_composicao, alimento_arroz
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1)])
    disponibilidade.definir_regra(db, alimento_arroz, "PERSONALIZADO", [QUINTA])
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")
    assert corpo["categorias"][0]["opcoes"] == []
    assert corpo["motivo_indisponivel"] == "sem_opcoes"


def test_categoria_com_exigencia_zero_sem_opcoes_nao_derruba(
    db, client, restaurante, marmita_personalizavel,
    cat_composicao, cat_composicao_2, alimento_arroz,
):
    _personalizavel_com(db, marmita_personalizavel, [(cat_composicao, 1), (cat_composicao_2, 0)])
    corpo = _get(client, restaurante.slug, f"marmitas/{marmita_personalizavel.id}")
    assert corpo["categorias"][1]["opcoes"] == []
    assert corpo["disponivel"] is True


@pytest.fixture()
def _alimento_extra(db, restaurante, cat_composicao):
    from app.model.models import Food

    f = Food(
        restaurant_id=restaurante.id,
        name="Alimento Extra",
        composition_category_id=cat_composicao.id,
    )
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


# ================================== combo ==================================
def test_combo_traz_itens_referencia_e_economia(
    db, client, restaurante, marmita_pronta, alimento_so_venda
):
    combo = _combo(
        db, restaurante, "60.00",
        marmitas=[(marmita_pronta, 2)], alimentos=[(alimento_so_venda, 1)],
    )
    corpo = _get(client, restaurante.slug, f"combos/{combo.id}")
    assert Decimal(corpo["preco"]) == Decimal("60.00")
    assert Decimal(corpo["preco_referencia"]) == Decimal("72.90")
    assert Decimal(corpo["economia"]) == Decimal("12.90")
    assert corpo["possui_marmita_personalizavel"] is False
    assert [(i["nome"], i["tipo"], i["quantidade"]) for i in corpo["itens_marmita"]] == [
        ("Marmita Pronta", "PRONTA", 2)
    ]
    assert [(i["nome"], i["quantidade"]) for i in corpo["itens_alimento"]] == [("Feijoada", 1)]
    assert corpo["disponivel"] is True


def test_combo_sem_economia_nao_tem_referencia_nem_economia(db, client, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "40.00", marmitas=[(marmita_pronta, 2)])
    corpo = _get(client, restaurante.slug, f"combos/{combo.id}")
    assert corpo["preco_referencia"] is None
    assert corpo["economia"] is None


def test_combo_avisa_marmita_personalizavel(db, client, restaurante, marmita_personalizavel):
    combo = _combo(db, restaurante, "50.00", marmitas=[(marmita_personalizavel, 1)])
    corpo = _get(client, restaurante.slug, f"combos/{combo.id}")
    assert corpo["possui_marmita_personalizavel"] is True
    assert corpo["itens_marmita"][0]["tipo"] == "PERSONALIZAVEL"


def test_combo_com_item_inativo_responde_200_indisponivel(db, client, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "30.00", marmitas=[(marmita_pronta, 1)])
    marmita_pronta.is_active = False
    db.flush()
    corpo = _get(client, restaurante.slug, f"combos/{combo.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "item_indisponivel"


def test_combo_esgotado_hoje_responde_200_indisponivel(db, client, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "30.00", marmitas=[(marmita_pronta, 1)])
    combo.sold_out_on = HOJE
    db.flush()
    corpo = _get(client, restaurante.slug, f"combos/{combo.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "esgotado_hoje"


def test_combo_inativo_da_404(db, client, restaurante, marmita_pronta):
    combo = _combo(db, restaurante, "30.00", marmitas=[(marmita_pronta, 1)])
    combo.is_active = False
    db.flush()
    _get(client, restaurante.slug, f"combos/{combo.id}", 404)


def test_combo_de_outro_restaurante_da_404(client, outro_restaurante, combo_teste):
    _get(client, outro_restaurante.slug, f"combos/{combo_teste.id}", 404)


# =============================== produto avulso ===============================
def test_produto_traz_todos_os_campos_informados(db, client, restaurante, alimento_so_venda):
    alimento_so_venda.serves_people = 4
    alimento_so_venda.portion_amount = Decimal("800")
    alimento_so_venda.portion_unit = "g"
    alimento_so_venda.prep_time_minutes = 45
    alimento_so_venda.calories_kcal = 900
    alimento_so_venda.components = [
        FoodComponent(name="Arroz", position=0),
        FoodComponent(name="Farofa", description="crocante", position=1),
    ]
    db.flush()
    db.refresh(alimento_so_venda)

    corpo = _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}")
    assert corpo["nome"] == "Feijoada"
    assert Decimal(corpo["preco"]) == Decimal("32.90")
    assert corpo["grupo"] == "prato"
    assert corpo["categoria"]["nome"] == "Pratos do dia"
    assert corpo["serve_pessoas"] == 4
    assert Decimal(corpo["porcao"]["quantidade"]) == Decimal("800")
    assert corpo["porcao"]["unidade"] == "g"
    assert corpo["tempo_preparo_minutos"] == 45
    assert corpo["nutricao"]["calorias_kcal"] == 900
    assert corpo["nutricao"]["proteina_g"] is None
    assert [(c["nome"], c["descricao"]) for c in corpo["componentes"]] == [
        ("Arroz", None),
        ("Farofa", "crocante"),
    ]
    assert corpo["disponivel"] is True


def test_produto_sem_campos_opcionais(client, restaurante, alimento_so_venda):
    corpo = _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}")
    assert corpo["serve_pessoas"] is None
    assert corpo["porcao"] is None
    assert corpo["tempo_preparo_minutos"] is None
    assert corpo["nutricao"] is None
    assert corpo["componentes"] == []


def test_bebida_vem_no_grupo_bebida(client, restaurante, alimento_bebida):
    corpo = _get(client, restaurante.slug, f"produtos/{alimento_bebida.id}")
    assert corpo["grupo"] == "bebida"
    assert corpo["categoria"]["nome"] == "Bebidas"


def test_produto_esgotado_hoje_responde_200_indisponivel(db, client, restaurante, alimento_so_venda):
    alimento_so_venda.sold_out_on = HOJE
    db.flush()
    corpo = _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "esgotado_hoje"


def test_produto_fora_do_dia_responde_200_indisponivel(db, client, restaurante, alimento_so_venda):
    disponibilidade.definir_regra(db, alimento_so_venda, "PERSONALIZADO", [QUINTA])
    corpo = _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}")
    assert corpo["disponivel"] is False
    assert corpo["motivo_indisponivel"] == "fora_do_dia"


def test_alimento_de_composicao_nao_e_produto(client, restaurante, alimento_arroz):
    _get(client, restaurante.slug, f"produtos/{alimento_arroz.id}", 404)


def test_produto_inativo_da_404(db, client, restaurante, alimento_so_venda):
    alimento_so_venda.is_active = False
    db.flush()
    _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}", 404)


def test_produto_de_categoria_inativa_da_404(db, client, restaurante, alimento_so_venda, cat_venda):
    cat_venda.is_active = False
    db.flush()
    _get(client, restaurante.slug, f"produtos/{alimento_so_venda.id}", 404)


def test_produto_de_outro_restaurante_da_404(client, outro_restaurante, alimento_so_venda):
    _get(client, outro_restaurante.slug, f"produtos/{alimento_so_venda.id}", 404)