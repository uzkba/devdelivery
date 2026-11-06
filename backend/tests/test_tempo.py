from datetime import date, datetime, timezone

import pytest

from app.core.tempo import hoje_local


def test_virada_do_dia_usa_o_fuso_local():
    # 01:30 UTC de 07/11 ainda e 22:30 de 06/11 em Sao Paulo
    assert hoje_local(datetime(2026, 11, 7, 1, 30, tzinfo=timezone.utc)) == date(2026, 11, 6)
    # 03:00 UTC de 07/11 ja e 00:00 de 07/11 local
    assert hoje_local(datetime(2026, 11, 7, 3, 0, tzinfo=timezone.utc)) == date(2026, 11, 7)


def test_rejeita_datetime_sem_fuso():
    with pytest.raises(ValueError):
        hoje_local(datetime(2026, 11, 7, 1, 30))