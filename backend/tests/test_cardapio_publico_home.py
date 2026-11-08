import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.model.models import Combo, ComboMealBoxItem
from app.services import cardapio_publico_service as svc
from app.services import disponibilidade_service as disponibilidade

HOJE = date(2026, 11, 6)  # sexta-feira (weekday 4)
ONTEM = date(2026, 11, 5)
QUINTA = 3


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


def _get(client, slug):
    resposta = client.get(f"/restaurantes/{slug}/cardapio")
    assert resposta.status_code == 200
    return resposta.json()


def _ids(lista):
    return {i["id"] for i in lista}


def _combo_com(db, restaurante, marmita, preco="30.00", quantidade=2):
    combo = Combo(restaurant_id=restaurante.id, name="Combo da casa", price=Decimal(preco))
    combo.meal_box_items = [
        ComboMealBoxItem(meal_box_id=marmita.id, quantity=quantidade, position=0)
    ]
    db.add(combo)
    db.flush()
    db.refresh(combo)
    return combo


# ------------------------------ geral ------------------------------
def test_restaurante_sem_itens_devolve_listas_vazias(client, restaurante):
        assert _get(client, restaurante.slug) == {
        "destaques": [],
        "mais_pedidos": [],
        "marmitas": [],
        "combos": [],
        "secoes": [],
    }


def test_restaurante_inexistente_da_404(client):
    assert client.get("/restaurantes/nao-existe/cardapio").status_code == 404


def test_restaurante_inativo_da_404(db, client, restaurante):
    restaurante.is_active = False
    db.flush()
    assert client.get(f"/restaurantes/{restaurante.slug}/cardapio").status_code == 404


# ------------------------------ marmitas ------------------------------
def test_marmita_ativa_aparece_com_seus_campos(client, restaurante, marmita_pronta):
    marmitas = _get(client, restaurante.slug)["marmitas"]
    assert len(marmitas) == 1
    assert marmitas[0]["id"] == str(marmita_pronta.id)
    assert marmitas[0]["tipo"] == "PRONTA"
    assert Decimal(marmitas[0]["preco"]) == Decimal("20.00")


def test_marmita_inativa_nao_aparece(client, restaurante, marmita_inativa):
    assert _get(client, restaurante.slug)["marmitas"] == []


def test_marmita_fora_do_dia_nao_aparece(db, client, restaurante, marmita_pronta):
    disponibilidade.definir_regra(db, marmita_pronta, "PERSONALIZADO", [QUINTA])
    assert _get(client, restaurante.slug)["marmitas"] == []


def test_excecao_de_hoje_traz_a_marmita_de_volta(db, client, restaurante, marmita_pronta):
    disponibilidade.definir_regra(db, marmita_pronta, "PERSONALIZADO", [QUINTA])
    disponibilidade.definir_excecao(db, marmita_pronta, HOJE, True, hoje=HOJE)
    assert _ids(_get(client, restaurante.slug)["marmitas"]) == {str(marmita_pronta.id)}


def test_marmita_esgotada_hoje_nao_aparece(db, client, restaurante, marmita_pronta):
    marmita_pronta.sold_out_on = HOJE
    db.flush()
    assert _get(client, restaurante.slug)["marmitas"] == []


def test_esgotado_de_ontem_ja_voltou(db, client, restaurante, marmita_pronta):
    marmita_pronta.sold_out_on = ONTEM
    db.flush()
    assert _ids(_get(client, restaurante.slug)["marmitas"]) == {str(marmita_pronta.id)}


# ------------------------------ combos ------------------------------
def test_combo_aparece_com_preco_de_referencia(db, client, restaurante, marmita_pronta):
    combo = _combo_com(db, restaurante, marmita_pronta, preco="30.00", quantidade=2)
    combos = _get(client, restaurante.slug)["combos"]
    assert _ids(combos) == {str(combo.id)}
    assert Decimal(combos[0]["preco_referencia"]) == Decimal("40.00")  # 2 x 20.00


def test_combo_sem_economia_aparece_sem_preco_de_referencia(db, client, restaurante, marmita_pronta):
    _combo_com(db, restaurante, marmita_pronta, preco="40.00", quantidade=2)
    combos = _get(client, restaurante.slug)["combos"]
    assert len(combos) == 1
    assert combos[0]["preco_referencia"] is None


def test_combo_com_item_inativo_nao_aparece(db, client, restaurante, marmita_pronta):
    _combo_com(db, restaurante, marmita_pronta)
    marmita_pronta.is_active = False
    db.flush()
    assert _get(client, restaurante.slug)["combos"] == []


def test_combo_esgotado_hoje_nao_aparece(db, client, restaurante, marmita_pronta):
    combo = _combo_com(db, restaurante, marmita_pronta)
    combo.sold_out_on = HOJE
    db.flush()
    assert _get(client, restaurante.slug)["combos"] == []


def test_combo_inativo_nao_aparece(db, client, restaurante, marmita_pronta):
    combo = _combo_com(db, restaurante, marmita_pronta)
    combo.is_active = False
    db.flush()
    assert _get(client, restaurante.slug)["combos"] == []


# ------------------------------ secoes ------------------------------
def test_secoes_separam_prato_e_bebida(client, restaurante, alimento_so_venda, alimento_bebida):
    secoes = _get(client, restaurante.slug)["secoes"]
    assert [s["grupo"] for s in secoes] == ["prato", "bebida"]
    prato, bebida = secoes
    assert [c["nome"] for c in prato["categorias"]] == ["Pratos do dia"]
    item = prato["categorias"][0]["itens"][0]
    assert item["id"] == str(alimento_so_venda.id)
    assert Decimal(item["preco"]) == Decimal("32.90")
    assert [c["nome"] for c in bebida["categorias"]] == ["Bebidas"]
    assert bebida["categorias"][0]["itens"][0]["nome"] == "Suco de laranja"


def test_secao_vazia_e_omitida(client, restaurante, alimento_so_venda):
    secoes = _get(client, restaurante.slug)["secoes"]
    assert [s["grupo"] for s in secoes] == ["prato"]


def test_categoria_inativa_e_omitida(db, client, restaurante, alimento_so_venda, cat_venda):
    cat_venda.is_active = False
    db.flush()
    assert _get(client, restaurante.slug)["secoes"] == []


def test_alimento_de_composicao_nao_vira_produto(client, restaurante, alimento_arroz):
    assert _get(client, restaurante.slug)["secoes"] == []


def test_avulso_inativo_nao_aparece(db, client, restaurante, alimento_so_venda):
    alimento_so_venda.is_active = False
    db.flush()
    assert _get(client, restaurante.slug)["secoes"] == []


def test_avulso_esgotado_hoje_nao_aparece(db, client, restaurante, alimento_so_venda):
    alimento_so_venda.sold_out_on = HOJE
    db.flush()
    assert _get(client, restaurante.slug)["secoes"] == []


def test_avulso_fora_do_dia_nao_aparece(db, client, restaurante, alimento_so_venda):
    disponibilidade.definir_regra(db, alimento_so_venda, "PERSONALIZADO", [QUINTA])
    assert _get(client, restaurante.slug)["secoes"] == []


# ------------------------------ isolamento ------------------------------
def test_cada_restaurante_ve_so_o_proprio_cardapio(
    client, restaurante, outro_restaurante, marmita_pronta, marmita_b
):
    do_a = _ids(_get(client, restaurante.slug)["marmitas"])
    do_b = _ids(_get(client, outro_restaurante.slug)["marmitas"])
    assert do_a == {str(marmita_pronta.id)}
    assert do_b == {str(marmita_b.id)}