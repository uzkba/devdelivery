import uuid
from datetime import datetime, time

from app.core.tempo import FUSO_LOCAL, agora_local
from app.model.models import RestaurantHours
from app.services import estado_restaurante_service as svc

from tests.helpers_pedido import corpo_pedido, criar_avulso, item_avulso

SEXTA = 4  # 06/11/2026 e uma sexta-feira (weekday 4)


def _em(hora, minuto=0, dia=6):
    return datetime(2026, 11, dia, hora, minuto, tzinfo=FUSO_LOCAL)


def _faixa(db, restaurante, dia, abre, fecha):
    db.add(
        RestaurantHours(
            restaurant_id=restaurante.id, weekday=dia, opens_at=abre, closes_at=fecha
        )
    )
    db.flush()


def _estado(db, restaurante, agora):
    return svc.buscar_estado(db, restaurante, agora)


# ------------------------------- agora_local -------------------------------
def test_agora_local_converte_para_fuso_local():
    utc = datetime(2026, 11, 6, 15, 0, tzinfo=FUSO_LOCAL).astimezone(tz=None)
    assert agora_local(utc).hour == 15


def test_agora_local_exige_tzinfo():
    import pytest

    with pytest.raises(ValueError):
        agora_local(datetime(2026, 11, 6, 15, 0))


# --------------------------- calculo do estado ----------------------------
def test_sem_agenda_fica_aberto(db, restaurante):
    estado = _estado(db, restaurante, _em(3))
    assert estado.estado == svc.ABERTO
    assert estado.aceita_pedidos is True
    assert estado.horario_definido is False


def test_sem_agenda_com_pausa_fica_pausado(db, restaurante):
    restaurante.is_paused = True
    db.flush()
    estado = _estado(db, restaurante, _em(12))
    assert estado.estado == svc.PAUSADO
    assert estado.aceita_pedidos is False
    assert estado.motivo == svc.MOTIVO_PAUSA_MANUAL


def test_dentro_do_horario_fica_aberto(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    estado = _estado(db, restaurante, _em(12))
    assert estado.estado == svc.ABERTO
    assert estado.horario_definido is True
    assert estado.proxima_abertura is None


def test_abre_exatamente_na_hora_de_abertura(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    assert _estado(db, restaurante, _em(11, 0)).estado == svc.ABERTO


def test_fecha_exatamente_na_hora_de_fechamento(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    assert _estado(db, restaurante, _em(15, 0)).estado == svc.FECHADO


def test_antes_de_abrir_proxima_abertura_e_hoje(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    estado = _estado(db, restaurante, _em(9))
    assert estado.estado == svc.FECHADO
    assert estado.motivo == svc.MOTIVO_FORA_DO_HORARIO
    assert estado.aceita_pedidos is False
    assert estado.proxima_abertura == svc.ProximaAbertura(0, SEXTA, time(11))


def test_entre_duas_faixas_proxima_abertura_e_a_da_noite(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    _faixa(db, restaurante, SEXTA, time(18), time(22))
    estado = _estado(db, restaurante, _em(16))
    assert estado.estado == svc.FECHADO
    assert estado.proxima_abertura == svc.ProximaAbertura(0, SEXTA, time(18))


def test_depois_da_ultima_faixa_proxima_abertura_e_outro_dia(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    _faixa(db, restaurante, 0, time(11), time(15))  # segunda
    estado = _estado(db, restaurante, _em(16))
    assert estado.proxima_abertura == svc.ProximaAbertura(3, 0, time(11))


def test_unica_faixa_semanal_proxima_abertura_e_na_semana_seguinte(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    estado = _estado(db, restaurante, _em(16))
    assert estado.proxima_abertura == svc.ProximaAbertura(7, SEXTA, time(11))


def test_pausa_dentro_do_horario(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    db.flush()
    estado = _estado(db, restaurante, _em(12))
    assert estado.estado == svc.PAUSADO
    assert estado.aceita_pedidos is False
    assert estado.motivo == svc.MOTIVO_PAUSA_MANUAL
    assert estado.pausado_ate is None


def test_pausa_com_prazo_futuro(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    restaurante.paused_until = _em(13)
    db.flush()
    estado = _estado(db, restaurante, _em(12))
    assert estado.estado == svc.PAUSADO
    assert estado.pausado_ate == _em(13)


def test_pausa_vencida_nao_vale(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    restaurante.paused_until = _em(11, 30)
    db.flush()
    estado = _estado(db, restaurante, _em(12))
    assert estado.estado == svc.ABERTO
    assert estado.pausado_ate is None


def test_pausa_fora_do_horario_continua_fechado(db, restaurante):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    db.flush()
    estado = _estado(db, restaurante, _em(16))
    assert estado.estado == svc.FECHADO
    assert estado.motivo == svc.MOTIVO_FORA_DO_HORARIO


def test_faixas_de_outro_restaurante_nao_contam(db, restaurante, outro_restaurante):
    _faixa(db, outro_restaurante, SEXTA, time(11), time(15))
    estado = _estado(db, restaurante, _em(20))
    assert estado.estado == svc.ABERTO
    assert estado.horario_definido is False


# ----------------------- GET /restaurantes/{slug} -----------------------
def _get(client, slug):
    resposta = client.get(f"/restaurantes/{slug}")
    assert resposta.status_code == 200
    return resposta.json()


def test_endpoint_sem_agenda(client, restaurante, monkeypatch):
    monkeypatch.setattr(svc, "agora_local", lambda: _em(12))
    corpo = _get(client, restaurante.slug)
    assert corpo["estado"] == {
        "estado": "ABERTO",
        "aceita_pedidos": True,
        "horario_definido": False,
        "motivo": None,
        "pausado_ate": None,
        "proxima_abertura": None,
    }
    assert [d["dia_semana"] for d in corpo["horarios"]] == [0, 1, 2, 3, 4, 5, 6]
    assert all(d["faixas"] == [] for d in corpo["horarios"])


def test_endpoint_com_horarios_aberto(client, db, restaurante, monkeypatch):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    _faixa(db, restaurante, SEXTA, time(18), time(22))
    monkeypatch.setattr(svc, "agora_local", lambda: _em(12))
    corpo = _get(client, restaurante.slug)
    assert corpo["estado"]["estado"] == "ABERTO"
    assert corpo["estado"]["horario_definido"] is True
    assert corpo["horarios"][SEXTA]["faixas"] == [
        {"abre_as": "11:00", "fecha_as": "15:00"},
        {"abre_as": "18:00", "fecha_as": "22:00"},
    ]
    assert corpo["horarios"][0]["faixas"] == []


def test_endpoint_fechado_com_proxima_abertura(client, db, restaurante, monkeypatch):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    _faixa(db, restaurante, SEXTA, time(18), time(22))
    monkeypatch.setattr(svc, "agora_local", lambda: _em(16))
    estado = _get(client, restaurante.slug)["estado"]
    assert estado["estado"] == "FECHADO"
    assert estado["aceita_pedidos"] is False
    assert estado["motivo"] == "FORA_DO_HORARIO"
    assert estado["proxima_abertura"] == {"em_dias": 0, "dia_semana": SEXTA, "abre_as": "18:00"}


def test_endpoint_pausado(client, db, restaurante, monkeypatch):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    db.flush()
    monkeypatch.setattr(svc, "agora_local", lambda: _em(12))
    estado = _get(client, restaurante.slug)["estado"]
    assert estado["estado"] == "PAUSADO"
    assert estado["aceita_pedidos"] is False
    assert estado["motivo"] == "PAUSA_MANUAL"
    assert estado["proxima_abertura"] is None


# ------------------------- bloqueio na finalizacao -------------------------
def test_garantir_aceita_pedidos_quando_aberto(db, restaurante, monkeypatch):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(svc, "agora_local", lambda: _em(12))
    assert svc.garantir_aceita_pedidos(db, restaurante) is None


def test_garantir_bloqueia_fechado(db, restaurante, monkeypatch):
    import pytest
    from fastapi import HTTPException

    _faixa(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(svc, "agora_local", lambda: _em(16))
    with pytest.raises(HTTPException) as erro:
        svc.garantir_aceita_pedidos(db, restaurante)
    assert erro.value.status_code == 422
    assert "fechado" in erro.value.detail.lower()


def test_garantir_bloqueia_pausado(db, restaurante, monkeypatch):
    import pytest
    from fastapi import HTTPException

    _faixa(db, restaurante, SEXTA, time(11), time(15))
    restaurante.is_paused = True
    db.flush()
    monkeypatch.setattr(svc, "agora_local", lambda: _em(12))
    with pytest.raises(HTTPException) as erro:
        svc.garantir_aceita_pedidos(db, restaurante)
    assert erro.value.status_code == 422
    assert "pausou" in erro.value.detail.lower()


def test_post_pedidos_bloqueado_com_restaurante_fechado(
    client,
    db,
    restaurante,
    cliente,
    endereco,
    status_criado,
    cat_venda,
    token_para_cliente,
    monkeypatch,
):
    _faixa(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(svc, "agora_local", lambda: _em(16))
    feijoada = criar_avulso(db, restaurante, cat_venda, "Feijoada", "20.00")
    corpo = corpo_pedido(restaurante, [item_avulso(feijoada)], endereco_id=str(endereco.id))
    resposta = client.post(
        "/pedidos",
        json=corpo,
        headers={"Authorization": f"Bearer {token_para_cliente(cliente)}"},
    )
    assert resposta.status_code == 422
    assert "fechado" in resposta.json()["detail"].lower()