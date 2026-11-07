from datetime import date

import pytest

from app.model.models import AvailabilityException
from app.services import disponibilidade_service as svc

SEXTA = date(2026, 11, 6)  # weekday 4
SABADO = date(2026, 11, 7)
ONTEM = date(2026, 11, 5)

RECURSOS = [
    ("/admin/marmitas", "marmita_pronta", "meal_box_id"),
    ("/admin/combos", "combo_teste", "combo_id"),
    ("/alimentos", "alimento_arroz", "food_id"),
]


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: SEXTA)


@pytest.fixture(params=RECURSOS, ids=["marmita", "combo", "alimento"])
def recurso(request):
    prefixo, nome_fixture, atributo = request.param
    alvo = request.getfixturevalue(nome_fixture)
    return {"alvo": alvo, "atributo": atributo, "base": f"{prefixo}/{alvo.id}"}


@pytest.fixture()
def atendente_headers(atendente_user, token_para):
    return {"Authorization": f"Bearer {token_para(atendente_user)}"}


def test_leitura_padrao(client, admin_headers, recurso):
    r = client.get(f"{recurso['base']}/disponibilidade", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {
        "modo": "TODOS_OS_DIAS",
        "dias": [],
        "excecoes": [],
        "serve_hoje": True,
        "esgotado_hoje": False,
    }


def test_salva_regra_personalizada_e_substitui_os_dias(client, admin_headers, recurso):
    url = f"{recurso['base']}/disponibilidade"

    r = client.put(url, json={"modo": "PERSONALIZADO", "dias": [4, 0]}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["dias"] == [0, 4]
    assert r.json()["serve_hoje"] is True  # hoje e sexta (4)

    # repete dias que ja existem: nao pode violar a unicidade
    r = client.put(url, json={"modo": "PERSONALIZADO", "dias": [0, 1, 4]}, headers=admin_headers)
    assert r.json()["dias"] == [0, 1, 4]

    r = client.put(url, json={"modo": "PERSONALIZADO", "dias": [0]}, headers=admin_headers)
    assert r.json()["dias"] == [0]
    assert r.json()["serve_hoje"] is False


def test_todos_os_dias_limpa_os_dias(client, admin_headers, recurso):
    url = f"{recurso['base']}/disponibilidade"
    client.put(url, json={"modo": "PERSONALIZADO", "dias": [0]}, headers=admin_headers)

    r = client.put(url, json={"modo": "TODOS_OS_DIAS", "dias": []}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["modo"] == "TODOS_OS_DIAS"
    assert r.json()["dias"] == []
    assert r.json()["serve_hoje"] is True


@pytest.mark.parametrize(
    "corpo",
    [
        {"modo": "PERSONALIZADO", "dias": []},
        {"modo": "PERSONALIZADO", "dias": [7]},
        {"modo": "PERSONALIZADO", "dias": [1, 1]},
        {"modo": "TODOS_OS_DIAS", "dias": [1]},
        {"modo": "QUINZENAL", "dias": []},
    ],
)
def test_regra_invalida_da_422(client, admin_headers, recurso, corpo):
    r = client.put(f"{recurso['base']}/disponibilidade", json=corpo, headers=admin_headers)
    assert r.status_code == 422


def test_excecao_cria_atualiza_e_remove(client, admin_headers, recurso):
    url = f"{recurso['base']}/disponibilidade/excecoes/{SABADO.isoformat()}"

    r = client.put(url, json={"disponivel": True}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["excecoes"] == [{"data": "2026-11-07", "disponivel": True}]

    # segunda chamada atualiza, nao duplica
    r = client.put(url, json={"disponivel": False}, headers=admin_headers)
    assert r.json()["excecoes"] == [{"data": "2026-11-07", "disponivel": False}]

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.delete(url, headers=admin_headers).status_code == 404

    leitura = client.get(f"{recurso['base']}/disponibilidade", headers=admin_headers)
    assert leitura.json()["excecoes"] == []


def test_excecao_no_passado_da_422(client, admin_headers, recurso):
    url = f"{recurso['base']}/disponibilidade/excecoes/{ONTEM.isoformat()}"
    r = client.put(url, json={"disponivel": True}, headers=admin_headers)
    assert r.status_code == 422


def test_excecao_de_hoje_muda_serve_hoje(client, admin_headers, recurso):
    base = recurso["base"]
    r = client.put(
        f"{base}/disponibilidade", json={"modo": "PERSONALIZADO", "dias": [0]}, headers=admin_headers
    )
    assert r.json()["serve_hoje"] is False

    r = client.put(
        f"{base}/disponibilidade/excecoes/{SEXTA.isoformat()}",
        json={"disponivel": True},
        headers=admin_headers,
    )
    assert r.json()["serve_hoje"] is True


def test_leitura_nao_lista_excecoes_passadas(client, db, admin_headers, recurso):
    db.add(
        AvailabilityException(
            **{recurso["atributo"]: recurso["alvo"].id},
            exception_date=ONTEM,
            is_available=False,
        )
    )
    db.flush()
    r = client.get(f"{recurso['base']}/disponibilidade", headers=admin_headers)
    assert r.json()["excecoes"] == []


def test_esgotar_e_liberar(client, admin_headers, recurso):
    url = f"{recurso['base']}/esgotado"

    r = client.patch(url, json={"esgotado": True}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["esgotado_hoje"] is True
    assert r.json()["serve_hoje"] is True  # esgotado nao e o mesmo que nao servir hoje
    assert recurso["alvo"].sold_out_on == SEXTA

    r = client.patch(url, json={"esgotado": False}, headers=admin_headers)
    assert r.json()["esgotado_hoje"] is False
    assert recurso["alvo"].sold_out_on is None


def test_atendente_esgota_mas_nao_edita_regra(client, atendente_headers, recurso):
    base = recurso["base"]
    r = client.patch(f"{base}/esgotado", json={"esgotado": True}, headers=atendente_headers)
    assert r.status_code == 200

    corpo_regra = {"modo": "TODOS_OS_DIAS", "dias": []}
    assert client.get(f"{base}/disponibilidade", headers=atendente_headers).status_code == 403
    assert client.put(f"{base}/disponibilidade", json=corpo_regra, headers=atendente_headers).status_code == 403
    excecao = f"{base}/disponibilidade/excecoes/{SABADO.isoformat()}"
    assert client.put(excecao, json={"disponivel": True}, headers=atendente_headers).status_code == 403
    assert client.delete(excecao, headers=atendente_headers).status_code == 403


def test_outro_restaurante_recebe_404(client, outro_admin_headers, recurso):
    base = recurso["base"]
    excecao = f"{base}/disponibilidade/excecoes/{SABADO.isoformat()}"

    assert client.get(f"{base}/disponibilidade", headers=outro_admin_headers).status_code == 404
    assert client.put(
        f"{base}/disponibilidade", json={"modo": "TODOS_OS_DIAS", "dias": []}, headers=outro_admin_headers
    ).status_code == 404
    assert client.put(excecao, json={"disponivel": True}, headers=outro_admin_headers).status_code == 404
    assert client.delete(excecao, headers=outro_admin_headers).status_code == 404
    assert client.patch(f"{base}/esgotado", json={"esgotado": True}, headers=outro_admin_headers).status_code == 404