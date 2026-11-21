from datetime import date, datetime, time

from app.core.tempo import FUSO_LOCAL
from app.model.models import CashDay, RestaurantHours
from app.services import painel_avisos_service
from app.services.painel_alertas_service import alertas_de_atencao

HOJE = date(2026, 11, 10)
ONTEM = date(2026, 11, 9)
TERCA = 1
QUARTA = 2
ABERTO_AS_10H02 = datetime(2026, 11, 10, 13, 2)
ABERTO_ONTEM = datetime(2026, 11, 9, 13, 0)


def _agora(hora, minuto=0):
    return datetime(2026, 11, 10, hora, minuto, tzinfo=FUSO_LOCAL)


def _faixa(db, restaurante, dia_semana, abre, fecha):
    db.add(
        RestaurantHours(
            restaurant_id=restaurante.id, weekday=dia_semana, opens_at=abre, closes_at=fecha
        )
    )
    db.flush()


def _caixa(db, restaurante, usuario, dia=HOJE, status="ABERTO", aberto_em=ABERTO_AS_10H02):
    caixa = CashDay(
        restaurant_id=restaurante.id,
        business_date=dia,
        opened_by=usuario.id,
        status=status,
        opened_at=aberto_em,
    )
    db.add(caixa)
    db.flush()
    return caixa


def _alertas(db, restaurante, agora):
    return [
        alerta
        for alerta in alertas_de_atencao(db, restaurante.id, agora)
        if alerta.codigo == "CAIXA_ABERTO"
    ]


def test_sem_caixa_nao_alerta(db, restaurante):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))

    assert _alertas(db, restaurante, _agora(23)) == []


def test_caixa_de_hoje_antes_do_fechamento_nao_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    assert _alertas(db, restaurante, _agora(15)) == []


def test_caixa_de_hoje_depois_do_fechamento_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    alertas = _alertas(db, restaurante, _agora(22, 30))

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.gravidade == "AVISO"
    assert alerta.destino == "caixa"
    assert alerta.quantidade == 1
    assert alerta.titulo == "1 caixa aberto"
    assert alerta.detalhe == "Aberto desde 10h02: lembre de fechar após o último pedido"


def test_exatamente_na_hora_de_fechar_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    assert len(_alertas(db, restaurante, _agora(22, 0))) == 1


def test_entre_duas_faixas_nao_alerta_e_depois_da_ultima_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(14, 0))
    _faixa(db, restaurante, TERCA, time(18, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    assert _alertas(db, restaurante, _agora(15)) == []
    assert len(_alertas(db, restaurante, _agora(22, 30))) == 1


def test_sem_horario_definido_o_caixa_de_hoje_nao_alerta(db, restaurante, admin_user):
    _caixa(db, restaurante, admin_user)

    assert _alertas(db, restaurante, _agora(23, 30)) == []


def test_dia_sem_faixa_com_horario_definido_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, QUARTA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    assert len(_alertas(db, restaurante, _agora(10))) == 1


def test_caixa_fechado_nao_alerta(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user, status="FECHADO")

    assert _alertas(db, restaurante, _agora(23)) == []


def test_caixa_de_dia_anterior_aberto_alerta_mesmo_sem_horario(db, restaurante, admin_user):
    _caixa(db, restaurante, admin_user, dia=ONTEM, aberto_em=ABERTO_ONTEM)

    alertas = _alertas(db, restaurante, _agora(8))

    assert len(alertas) == 1
    assert alertas[0].quantidade == 1
    assert alertas[0].detalhe == "Caixa de 09/11 ainda aberto: feche para conferir o dia"


def test_dois_caixas_pendentes_viram_um_alerta_agregado(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user, dia=ONTEM, aberto_em=ABERTO_ONTEM)
    _caixa(db, restaurante, admin_user)

    alertas = _alertas(db, restaurante, _agora(22, 30))

    assert len(alertas) == 1
    assert alertas[0].quantidade == 2
    assert alertas[0].titulo == "2 caixas abertos"
    assert alertas[0].detalhe == "Caixas de 09/11 e hoje ainda abertos"


def test_caixa_de_outro_restaurante_nao_alerta(
    db, restaurante, outro_restaurante, outro_admin_user
):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, outro_restaurante, outro_admin_user, dia=ONTEM, aberto_em=ABERTO_ONTEM)

    assert _alertas(db, restaurante, _agora(23)) == []


def test_sino_traz_o_alerta_e_conta_na_bolinha(db, restaurante, admin_user):
    _faixa(db, restaurante, TERCA, time(11, 0), time(22, 0))
    _caixa(db, restaurante, admin_user)

    avisos = painel_avisos_service.avisos_do_painel(db, restaurante.id, agora=_agora(22, 30))

    assert avisos.total == 1
    assert [aviso.tipo for aviso in avisos.avisos] == ["CAIXA_ABERTO"]
    assert avisos.avisos[0].destino == "caixa"
    assert avisos.avisos[0].gravidade == "AVISO"