"""NexusDelivery - Fase 1: testes de schema (nao precisam de banco)."""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.combo_schemas import ComboIn
from app.schemas.marmita_schemas import MarmitaIn

A, B, C = (str(uuid.uuid4()) for _ in range(3))


def marmita(**over):
    base = {
        "nome": "Marmita M",
        "tipo": "PERSONALIZAVEL",
        "preco": "20.00",
        "categorias": [{"categoria_alimento_id": A, "quantidade_exigida": 1}],
    }
    base.update(over)
    return base


def pronta(**over):
    base = {
        "nome": "Fit",
        "tipo": "PRONTA",
        "preco": "25",
        "composicao": [{"alimento_id": A, "quantidade_fixa": 1}],
    }
    base.update(over)
    return base


def test_id_que_nao_e_uuid_e_rejeitado():
    with pytest.raises(ValidationError):
        MarmitaIn(**marmita(categorias=[{"categoria_alimento_id": "1", "quantidade_exigida": 1}]))


def test_marmita_personalizavel_valida():
    assert MarmitaIn(**marmita()).tipo.value == "PERSONALIZAVEL"


def test_marmita_pronta_valida_com_nutricao_opcional():
    m = MarmitaIn(**pronta(calorias_kcal=450, proteina_g="38.5"))
    assert m.calorias_kcal == 450 and m.carboidrato_g is None


@pytest.mark.parametrize(
    "payload",
    [
        marmita(composicao=[{"alimento_id": A, "quantidade_fixa": 1}]),  # mistura
        marmita(categorias=[]),  # sem categorias
        marmita(categorias=[{"categoria_alimento_id": A, "quantidade_exigida": 0}]),  # tudo zero
        marmita(categorias=[{"categoria_alimento_id": A, "quantidade_exigida": 1}] * 2),  # repetida
        pronta(categorias=[{"categoria_alimento_id": A, "quantidade_exigida": 1}]),  # mistura
        pronta(composicao=[]),
        pronta(composicao=[{"alimento_id": A, "quantidade_fixa": 1}] * 2),
        pronta(composicao=[{"alimento_id": A, "quantidade_fixa": 0}]),
        marmita(preco="-1"),
        marmita(nome=" "),
        marmita(calorias_kcal=-5),
    ],
)
def test_marmita_invalida(payload):
    with pytest.raises(ValidationError):
        MarmitaIn(**payload)


def test_categoria_com_quantidade_zero_e_permitida_se_houver_outra_positiva():
    m = MarmitaIn(
        **marmita(
            categorias=[
                {"categoria_alimento_id": A, "quantidade_exigida": 0},
                {"categoria_alimento_id": B, "quantidade_exigida": 2},
            ]
        )
    )
    assert len(m.categorias) == 2


def combo(**over):
    base = {
        "nome": "Combo",
        "preco": "30",
        "itens_marmita": [{"marmita_id": A, "quantidade": 2}],
        "itens_alimento": [{"alimento_id": C, "quantidade": 1}],
    }
    base.update(over)
    return base


def test_combo_valido_so_com_alimentos():
    assert ComboIn(**combo(itens_marmita=[]))


@pytest.mark.parametrize(
    "payload",
    [
        combo(itens_marmita=[], itens_alimento=[]),
        combo(itens_marmita=[{"marmita_id": A, "quantidade": 1}] * 2),
        combo(itens_alimento=[{"alimento_id": C, "quantidade": 1}] * 2),
        combo(itens_marmita=[{"marmita_id": A, "quantidade": 0}]),
        combo(preco="-0.01"),
    ],
)
def test_combo_invalido(payload):
    with pytest.raises(ValidationError):
        ComboIn(**payload)