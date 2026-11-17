from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.model.models import CashDay

DIA = date(2026, 11, 10)


def _abrir(db, restaurante, usuario, dia=DIA, **extra):
    caixa = CashDay(restaurant_id=restaurante.id, business_date=dia, opened_by=usuario.id, **extra)
    db.add(caixa)
    db.flush()
    db.refresh(caixa)
    return caixa


def test_caixa_nasce_aberto_e_sem_reaberturas(db, restaurante, admin_user):
    caixa = _abrir(db, restaurante, admin_user)

    assert caixa.status == "ABERTO"
    assert caixa.reopen_count == 0
    assert caixa.opened_at is not None
    assert caixa.closed_by is None
    assert caixa.closed_at is None
    assert caixa.closing_id is None


def test_um_caixa_por_restaurante_e_dia(db, restaurante, admin_user, caixa_user):
    _abrir(db, restaurante, admin_user)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            _abrir(db, restaurante, caixa_user)


def test_mesmo_dia_em_outro_restaurante_e_permitido(db, restaurante, outro_restaurante, admin_user, outro_admin_user):
    primeiro = _abrir(db, restaurante, admin_user)
    segundo = _abrir(db, outro_restaurante, outro_admin_user)

    assert primeiro.id != segundo.id


def test_dias_diferentes_no_mesmo_restaurante(db, restaurante, admin_user):
    _abrir(db, restaurante, admin_user, date(2026, 11, 10))
    _abrir(db, restaurante, admin_user, date(2026, 11, 11))

    assert db.query(CashDay).filter_by(restaurant_id=restaurante.id).count() == 2


def test_status_invalido_e_rejeitado(db, restaurante, admin_user):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            _abrir(db, restaurante, admin_user, status="PAUSADO")


def test_reaberturas_negativas_sao_rejeitadas(db, restaurante, admin_user):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            _abrir(db, restaurante, admin_user, reopen_count=-1)