from datetime import date
from decimal import Decimal

import pytest

from app.model.models import (
    AvailabilityException,
    AvailabilityRule,
    AvailabilityRuleDay,
    Combo,
    Food,
    MealBox,
)
from app.services import disponibilidade_service as svc

SEGUNDA = date(2026, 11, 9)  # weekday 0
SEXTA = date(2026, 11, 6)  # weekday 4
SABADO = date(2026, 11, 7)  # weekday 5

ATRIBUTO = {MealBox: "meal_box_id", Combo: "combo_id", Food: "food_id"}


@pytest.fixture()
def combo_teste(db, restaurante):
    combo = Combo(restaurant_id=restaurante.id, name="Combo Teste", price=Decimal("30.00"))
    db.add(combo)
    db.flush()
    db.refresh(combo)
    return combo


@pytest.fixture(params=["marmita_pronta", "alimento_arroz", "combo_teste"])
def alvo(request):
    return request.getfixturevalue(request.param)


def _regra(db, alvo, modo, dias=()):
    regra = AvailabilityRule(**{ATRIBUTO[type(alvo)]: alvo.id}, mode=modo)
    regra.days = [AvailabilityRuleDay(weekday=d) for d in dias]
    db.add(regra)
    db.flush()
    return regra


def _excecao(db, alvo, dia, disponivel):
    excecao = AvailabilityException(
        **{ATRIBUTO[type(alvo)]: alvo.id}, exception_date=dia, is_available=disponivel
    )
    db.add(excecao)
    db.flush()
    return excecao


def test_datas_de_referencia_batem_com_o_dia_da_semana():
    assert (SEGUNDA.weekday(), SEXTA.weekday(), SABADO.weekday()) == (0, 4, 5)


# ---------------------------- regra semanal ----------------------------
def test_sem_regra_serve_todos_os_dias(db, alvo):
    assert svc.serve_hoje(db, alvo, SABADO) is True


def test_regra_todos_os_dias_serve(db, alvo):
    _regra(db, alvo, "TODOS_OS_DIAS")
    assert svc.serve_hoje(db, alvo, SABADO) is True


def test_personalizado_serve_so_nos_dias_da_regra(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[0, 4])
    assert svc.serve_hoje(db, alvo, SEGUNDA) is True
    assert svc.serve_hoje(db, alvo, SEXTA) is True
    assert svc.serve_hoje(db, alvo, SABADO) is False


def test_personalizado_sem_dias_nunca_serve(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[])
    assert svc.serve_hoje(db, alvo, SEXTA) is False


# ---------------------------- excecao por data ----------------------------
def test_excecao_indisponivel_sobrepoe_regra_que_serviria(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[4])
    _excecao(db, alvo, SEXTA, disponivel=False)
    assert svc.serve_hoje(db, alvo, SEXTA) is False


def test_excecao_disponivel_sobrepoe_regra_que_nao_serviria(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[0])
    _excecao(db, alvo, SABADO, disponivel=True)
    assert svc.serve_hoje(db, alvo, SABADO) is True


def test_excecao_de_outra_data_nao_afeta_hoje(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[4])
    _excecao(db, alvo, SABADO, disponivel=True)
    assert svc.serve_hoje(db, alvo, SEXTA) is True
    assert svc.serve_hoje(db, alvo, SEGUNDA) is False


# ---------------------------- esgotado hoje ----------------------------
def test_esgotado_hoje_so_vale_na_propria_data(alvo):
    assert svc.esgotado_hoje(alvo, SEXTA) is False  # nunca esgotado

    alvo.sold_out_on = SEXTA
    assert svc.esgotado_hoje(alvo, SEXTA) is True
    # virada do dia: no dia seguinte volta sozinho, sem nenhuma escrita
    assert svc.esgotado_hoje(alvo, SABADO) is False


def test_esgotado_independe_da_regra_semanal(db, alvo):
    alvo.sold_out_on = SEXTA
    estado = svc.estado_hoje(db, alvo, SEXTA)
    assert estado == svc.EstadoDisponibilidade(serve_hoje=True, esgotado_hoje=True)


def test_estado_hoje_combina_regra_e_esgotado(db, alvo):
    _regra(db, alvo, "PERSONALIZADO", dias=[0])
    estado = svc.estado_hoje(db, alvo, SABADO)
    assert estado == svc.EstadoDisponibilidade(serve_hoje=False, esgotado_hoje=False)


def test_sem_data_informada_usa_hoje_local(db, alvo, monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: SABADO)
    _regra(db, alvo, "PERSONALIZADO", dias=[0])
    assert svc.serve_hoje(db, alvo) is False
    alvo.sold_out_on = SABADO
    assert svc.esgotado_hoje(alvo) is True


# ---------------------------- em lote ----------------------------
def test_em_lote_cada_item_segue_a_propria_regra(db, marmita_pronta, marmita_personalizavel, marmita_inativa):
    _regra(db, marmita_pronta, "PERSONALIZADO", dias=[0])  # so segunda
    _excecao(db, marmita_personalizavel, SABADO, disponivel=False)

    ids = [marmita_pronta.id, marmita_personalizavel.id, marmita_inativa.id]
    
    assert svc.servem_hoje(db, MealBox, ids, SABADO) == {marmita_inativa.id}
    assert svc.servem_hoje(db, MealBox, ids, SEGUNDA) == set(ids)


def test_em_lote_sem_ids_devolve_vazio(db):
    assert svc.servem_hoje(db, MealBox, [], SEXTA) == set()