from datetime import datetime, time

import pytest

from app.core.tempo import FUSO_LOCAL
from app.model.models import RestaurantHours
from app.services import estado_restaurante_service as estado_svc

SEXTA = 4  # 06/11/2026 e uma sexta-feira


def _em(hora, minuto=0, dia=6):
    return datetime(2026, 11, dia, hora, minuto, tzinfo=FUSO_LOCAL)


def _faixa_db(db, restaurante, dia, abre, fecha):
    db.add(
        RestaurantHours(
            restaurant_id=restaurante.id, weekday=dia, opens_at=abre, closes_at=fecha
        )
    )
    db.flush()


def _dia(dia, *faixas):
    return {
        "dia_semana": dia,
        "faixas": [{"abre_as": abre, "fecha_as": fecha} for abre, fecha in faixas],
    }


def _horarios(client, headers, *dias):
    return client.put("/admin/restaurante/horarios", json={"dias": list(dias)}, headers=headers)


# ------------------------------ autenticacao ------------------------------
def test_rotas_exigem_autenticacao(client):
    assert client.get("/admin/restaurante").status_code in (401, 403)
    assert client.patch("/admin/restaurante", json={}).status_code in (401, 403)
    assert client.put("/admin/restaurante/horarios", json={"dias": []}).status_code in (401, 403)
    assert client.patch("/admin/restaurante/pausa", json={"pausado": False}).status_code in (
        401,
        403,
    )


def test_atendente_nao_acessa(client, atendente_user, token_para):
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}
    assert client.get("/admin/restaurante", headers=headers).status_code == 403
    assert client.patch("/admin/restaurante", json={}, headers=headers).status_code == 403
    assert (
        client.patch("/admin/restaurante/pausa", json={"pausado": True}, headers=headers).status_code
        == 403
    )


# ---------------------------------- GET ----------------------------------
def test_get_devolve_dados_do_proprio_restaurante(client, admin_headers, restaurante):
    corpo = client.get("/admin/restaurante", headers=admin_headers).json()
    assert corpo["slug"] == restaurante.slug
    assert corpo["nome"] == "Marmitas da Vovó"
    assert corpo["cnpj"] is None
    assert corpo["estado"]["estado"] in ("ABERTO", "PAUSADO", "FECHADO")
    assert [d["dia_semana"] for d in corpo["horarios"]] == [0, 1, 2, 3, 4, 5, 6]


def test_get_nao_vaza_dados_de_outro_restaurante(client, outro_admin_headers, outro_restaurante):
    corpo = client.get("/admin/restaurante", headers=outro_admin_headers).json()
    assert corpo["slug"] == outro_restaurante.slug


# --------------------------------- PATCH ---------------------------------
def test_patch_atualiza_nome_e_telefone(client, admin_headers):
    resposta = client.patch(
        "/admin/restaurante",
        json={"nome": "  Sabor Caseiro  ", "telefone": "11999990000"},
        headers=admin_headers,
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Sabor Caseiro"
    assert corpo["telefone"] == "11999990000"


def test_patch_telefone_vazio_limpa(client, db, admin_headers, restaurante):
    restaurante.phone = "11999990000"
    db.flush()
    corpo = client.patch("/admin/restaurante", json={"telefone": "  "}, headers=admin_headers).json()
    assert corpo["telefone"] is None


def test_patch_endereco_parcial_preserva_os_outros_campos(client, db, admin_headers, restaurante):
    restaurante.street = "Rua das Flores"
    restaurante.city = "São Paulo"
    db.flush()
    corpo = client.patch(
        "/admin/restaurante",
        json={"endereco": {"numero": "10", "bairro": "Centro"}},
        headers=admin_headers,
    ).json()
    assert corpo["endereco"] == {
        "rua": "Rua das Flores",
        "numero": "10",
        "bairro": "Centro",
        "cidade": "São Paulo",
    }


def test_patch_corpo_vazio_nao_muda_nada(client, admin_headers, restaurante):
    resposta = client.patch("/admin/restaurante", json={}, headers=admin_headers)
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Marmitas da Vovó"
    assert resposta.json()["slug"] == restaurante.slug


def test_patch_nome_nulo_ou_curto_e_rejeitado(client, admin_headers):
    assert client.patch("/admin/restaurante", json={"nome": None}, headers=admin_headers).status_code == 422
    assert client.patch("/admin/restaurante", json={"nome": " a "}, headers=admin_headers).status_code == 422


def test_patch_slug_novo_troca_o_link_publico(client, admin_headers, restaurante):
    antigo = restaurante.slug
    resposta = client.patch("/admin/restaurante", json={"slug": "Sabor-Caseiro"}, headers=admin_headers)
    assert resposta.status_code == 200
    assert resposta.json()["slug"] == "sabor-caseiro"
    assert client.get("/restaurantes/sabor-caseiro").status_code == 200
    assert client.get(f"/restaurantes/{antigo}").status_code == 404


def test_patch_mesmo_slug_e_aceito(client, admin_headers, restaurante):
    resposta = client.patch("/admin/restaurante", json={"slug": restaurante.slug}, headers=admin_headers)
    assert resposta.status_code == 200


def test_patch_slug_ocupado_da_409_e_nao_altera_outros_campos(
    client, admin_headers, outro_restaurante
):
    resposta = client.patch(
        "/admin/restaurante",
        json={"slug": outro_restaurante.slug, "nome": "Nome Que Nao Deve Gravar"},
        headers=admin_headers,
    )
    assert resposta.status_code == 409
    assert client.get("/admin/restaurante", headers=admin_headers).json()["nome"] == "Marmitas da Vovó"


@pytest.mark.parametrize("slug", ["ab", "a--b", "tem espaco", "admin", "x" * 61])
def test_patch_slug_invalido_ou_reservado(client, admin_headers, slug):
    resposta = client.patch("/admin/restaurante", json={"slug": slug}, headers=admin_headers)
    assert resposta.status_code == 422


# ----------------------------- slug-disponivel -----------------------------
def _checar(client, headers, slug):
    resposta = client.get("/admin/restaurante/slug-disponivel", params={"slug": slug}, headers=headers)
    assert resposta.status_code == 200
    return resposta.json()


def test_slug_livre_esta_disponivel(client, admin_headers):
    assert _checar(client, admin_headers, "Novo-Link") == {
        "slug": "novo-link",
        "disponivel": True,
        "motivo": None,
    }


def test_slug_proprio_esta_disponivel(client, admin_headers, restaurante):
    assert _checar(client, admin_headers, restaurante.slug)["disponivel"] is True


def test_slug_de_outro_restaurante_nao_esta_disponivel(client, admin_headers, outro_restaurante):
    corpo = _checar(client, admin_headers, outro_restaurante.slug)
    assert corpo["disponivel"] is False
    assert "em uso" in corpo["motivo"]


def test_slug_invalido_nao_esta_disponivel(client, admin_headers):
    corpo = _checar(client, admin_headers, "admin")
    assert corpo["disponivel"] is False
    assert corpo["motivo"]


# ------------------------------ PUT /horarios ------------------------------
def test_put_horarios_grava_e_devolve_a_grade(client, admin_headers):
    resposta = _horarios(
        client,
        admin_headers,
        _dia(SEXTA, ("18:00", "22:00"), ("11:00", "15:00")),
        _dia(0, ("11:00", "15:00")),
    )
    assert resposta.status_code == 200
    horarios = resposta.json()["horarios"]
    assert horarios[SEXTA]["faixas"] == [
        {"abre_as": "11:00", "fecha_as": "15:00"},
        {"abre_as": "18:00", "fecha_as": "22:00"},
    ]
    assert horarios[0]["faixas"] == [{"abre_as": "11:00", "fecha_as": "15:00"}]
    assert horarios[1]["faixas"] == []


def test_put_horarios_substitui_a_grade_anterior(client, db, admin_headers, restaurante):
    _faixa_db(db, restaurante, 2, time(9), time(12))
    _horarios(client, admin_headers, _dia(SEXTA, ("11:00", "15:00")))
    horarios = client.get("/admin/restaurante", headers=admin_headers).json()["horarios"]
    assert horarios[2]["faixas"] == []
    assert horarios[SEXTA]["faixas"] == [{"abre_as": "11:00", "fecha_as": "15:00"}]


def test_put_horarios_aparece_na_rota_publica(client, admin_headers, restaurante):
    _horarios(client, admin_headers, _dia(SEXTA, ("11:00", "15:00")))
    corpo = client.get(f"/restaurantes/{restaurante.slug}").json()
    assert corpo["estado"]["horario_definido"] is True
    assert corpo["horarios"][SEXTA]["faixas"] == [{"abre_as": "11:00", "fecha_as": "15:00"}]


def test_put_horarios_nao_mexe_em_outro_restaurante(
    client, db, admin_headers, outro_restaurante
):
    _faixa_db(db, outro_restaurante, SEXTA, time(11), time(15))
    _horarios(client, admin_headers, _dia(0, ("08:00", "10:00")))
    restantes = (
        db.query(RestaurantHours).filter(RestaurantHours.restaurant_id == outro_restaurante.id).count()
    )
    assert restantes == 1


def test_put_horarios_faixas_encostadas_sao_aceitas(client, admin_headers):
    resposta = _horarios(client, admin_headers, _dia(SEXTA, ("11:00", "15:00"), ("15:00", "18:00")))
    assert resposta.status_code == 200


@pytest.mark.parametrize(
    "dias",
    [
        [_dia(SEXTA, ("15:00", "11:00"))],
        [_dia(SEXTA, ("11:00", "11:00"))],
        [_dia(SEXTA, ("22:00", "02:00"))],
        [_dia(SEXTA, ("11:00", "15:00"), ("14:00", "18:00"))],
        [_dia(SEXTA, ("11:00", "15:00")), _dia(SEXTA, ("18:00", "22:00"))],
        [_dia(7, ("11:00", "15:00"))],
        [_dia(SEXTA, ("11:00:30", "15:00"))],
        [_dia(SEXTA, ("8:00", "9:00"), ("10:00", "11:00"), ("12:00", "13:00"), ("14:00", "15:00"), ("16:00", "17:00"))],  # mais de 4 faixas
        [],
        [_dia(SEXTA)],
    ],
)
def test_put_horarios_invalido_da_422(client, admin_headers, dias):
    assert _horarios(client, admin_headers, *dias).status_code == 422


def test_put_horarios_invalido_nao_apaga_a_grade_atual(client, db, admin_headers, restaurante):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    _horarios(client, admin_headers, _dia(SEXTA, ("15:00", "11:00")))
    horarios = client.get("/admin/restaurante", headers=admin_headers).json()["horarios"]
    assert horarios[SEXTA]["faixas"] == [{"abre_as": "11:00", "fecha_as": "15:00"}]


# ------------------------------ PATCH /pausa ------------------------------
def _pausa(client, headers, **corpo):
    return client.patch("/admin/restaurante/pausa", json=corpo, headers=headers)


def test_pausar_sem_prazo_vai_ate_o_fim_da_faixa_atual(
    client, db, admin_headers, restaurante, monkeypatch
):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    resposta = _pausa(client, admin_headers, pausado=True)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "PAUSADO"
    assert corpo["aceita_pedidos"] is False
    assert datetime.fromisoformat(corpo["pausado_ate"]) == _em(15)


def test_pausar_sem_prazo_e_sem_agenda_vai_ate_a_meia_noite(
    client, admin_headers, monkeypatch
):
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    corpo = _pausa(client, admin_headers, pausado=True).json()
    assert corpo["estado"] == "PAUSADO"
    assert datetime.fromisoformat(corpo["pausado_ate"]) == _em(0, dia=7)


def test_pausar_com_minutos(client, db, admin_headers, restaurante, monkeypatch):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    corpo = _pausa(client, admin_headers, pausado=True, minutos=30).json()
    assert corpo["estado"] == "PAUSADO"
    assert datetime.fromisoformat(corpo["pausado_ate"]) == _em(12, 30)


def test_pausa_aparece_na_rota_publica(client, db, admin_headers, restaurante, monkeypatch):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    _pausa(client, admin_headers, pausado=True)
    estado = client.get(f"/restaurantes/{restaurante.slug}").json()["estado"]
    assert estado["estado"] == "PAUSADO"
    assert estado["motivo"] == "PAUSA_MANUAL"


def test_retomar_limpa_a_pausa(client, db, admin_headers, restaurante, monkeypatch):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    _pausa(client, admin_headers, pausado=True, minutos=60)
    corpo = _pausa(client, admin_headers, pausado=False).json()
    assert corpo["estado"] == "ABERTO"
    assert corpo["aceita_pedidos"] is True
    assert corpo["pausado_ate"] is None


def test_retomar_fora_do_horario_continua_fechado(
    client, db, admin_headers, restaurante, monkeypatch
):
    _faixa_db(db, restaurante, SEXTA, time(11), time(15))
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(16))
    corpo = _pausa(client, admin_headers, pausado=False).json()
    assert corpo["estado"] == "FECHADO"


@pytest.mark.parametrize(
    "corpo",
    [
        {"pausado": False, "minutos": 30},
        {"pausado": True, "minutos": 0},
        {"pausado": True, "minutos": 10081},
        {"minutos": 30},
    ],
)
def test_pausa_invalida_da_422(client, admin_headers, corpo):
    assert _pausa(client, admin_headers, **corpo).status_code == 422


def test_pausa_nao_afeta_outro_restaurante(
    client, admin_headers, outro_admin_headers, monkeypatch
):
    monkeypatch.setattr(estado_svc, "agora_local", lambda: _em(12))
    _pausa(client, admin_headers, pausado=True, minutos=30)
    estado = client.get("/admin/restaurante", headers=outro_admin_headers).json()["estado"]
    assert estado["estado"] == "ABERTO"