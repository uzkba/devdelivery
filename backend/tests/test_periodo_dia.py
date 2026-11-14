from datetime import date, datetime, timezone

import pytest

from app.core import periodo


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_intervalo_do_dia_em_utc_usa_fuso_de_sao_paulo():
    inicio, fim = periodo.intervalo_do_dia_em_utc(date(2026, 11, 14))
    assert inicio == datetime(2026, 11, 14, 3, 0)
    assert fim == datetime(2026, 11, 15, 3, 0)


def test_janelas_comparaveis_cortam_na_mesma_hora_local():
    atual, anterior = periodo.janelas_comparaveis(_utc(2026, 11, 14, 18, 30))
    assert atual.dia == date(2026, 11, 14)
    assert atual.inicio == datetime(2026, 11, 14, 3, 0)
    assert atual.fim == datetime(2026, 11, 14, 18, 30)
    assert anterior.dia == date(2026, 11, 7)
    assert anterior.inicio == datetime(2026, 11, 7, 3, 0)
    assert anterior.fim == datetime(2026, 11, 7, 18, 30)


def test_dia_local_vira_na_meia_noite_de_sao_paulo():
    antes, _ = periodo.janelas_comparaveis(_utc(2026, 11, 15, 2, 30))
    depois, _ = periodo.janelas_comparaveis(_utc(2026, 11, 15, 3, 30))
    assert antes.dia == date(2026, 11, 14)
    assert depois.dia == date(2026, 11, 15)
    assert depois.inicio == datetime(2026, 11, 15, 3, 0)


def test_janelas_comparaveis_exigem_fuso():
    with pytest.raises(ValueError):
        periodo.janelas_comparaveis(datetime(2026, 11, 14, 12, 0))


def test_rotulo_semana_passada_concorda_com_o_genero():
    assert periodo.rotulo_semana_passada(date(2026, 11, 9)) == "segunda passada"
    assert periodo.rotulo_semana_passada(date(2026, 11, 12)) == "quinta passada"
    assert periodo.rotulo_semana_passada(date(2026, 11, 14)) == "sábado passado"
    assert periodo.rotulo_semana_passada(date(2026, 11, 15)) == "domingo passado"