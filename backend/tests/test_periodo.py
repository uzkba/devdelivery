from datetime import datetime, timedelta

import pytest

from app.core.periodo import intervalo_do_mes_em_utc, mes_local


def test_mes_comeca_a_meia_noite_local():
    inicio, fim = intervalo_do_mes_em_utc("2026-11")

    assert inicio == datetime(2026, 11, 1, 3, 0)
    assert fim == datetime(2026, 12, 1, 3, 0)


def test_dezembro_vira_o_ano():
    inicio, fim = intervalo_do_mes_em_utc("2026-12")

    assert inicio == datetime(2026, 12, 1, 3, 0)
    assert fim == datetime(2027, 1, 1, 3, 0)


@pytest.mark.parametrize(
    "momento, esperado",
    [
        (datetime(2026, 11, 1, 2, 59, 59), "2026-10"),
        (datetime(2026, 11, 1, 3, 0), "2026-11"),
        (datetime(2027, 1, 1, 2, 59, 59), "2026-12"),
        (datetime(2027, 1, 1, 3, 0), "2027-01"),
    ],
)
def test_mes_local(momento, esperado):
    assert mes_local(momento) == esperado


def test_intervalo_e_mes_local_concordam():
    inicio, fim = intervalo_do_mes_em_utc("2026-11")

    assert mes_local(inicio) == "2026-11"
    assert mes_local(fim - timedelta(seconds=1)) == "2026-11"
    assert mes_local(fim) == "2026-12"