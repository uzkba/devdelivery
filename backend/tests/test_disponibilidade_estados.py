from datetime import date

import pytest

from app.services import disponibilidade_service as svc

HOJE = date(2026, 11, 6)  # sexta-feira (weekday 4)
QUINTA, SEXTA = 3, 4


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


@pytest.fixture(params=["marmita", "combo", "alimento"])
def recurso(request, marmita_pronta, combo_teste, alimento_arroz):
    """(alvo, url_base, extrator_da_lista) para cada um dos tres recursos."""
    if request.param == "marmita":
        return marmita_pronta, "/admin/marmitas", lambda corpo: corpo["itens"]
    if request.param == "combo":
        return combo_teste, "/admin/combos", lambda corpo: corpo["itens"]
    return alimento_arroz, "/alimentos", lambda corpo: corpo


def _estado_na_lista(client, headers, recurso):
    alvo, base, extrair = recurso
    resposta = client.get(base, headers=headers)
    assert resposta.status_code == 200
    linha = next(i for i in extrair(resposta.json()) if i["id"] == str(alvo.id))
    return linha["serve_hoje"], linha["esgotado_hoje"]


def _estado_no_detalhe(client, headers, recurso):
    alvo, base, _ = recurso
    resposta = client.get(f"{base}/{alvo.id}", headers=headers)
    assert resposta.status_code == 200
    corpo = resposta.json()
    return corpo["serve_hoje"], corpo["esgotado_hoje"]


def _ambos(client, headers, recurso):
    return (
        _estado_na_lista(client, headers, recurso),
        _estado_no_detalhe(client, headers, recurso),
    )


def test_sem_regra_serve_e_nao_esta_esgotado(client, admin_headers, recurso):
    lista, detalhe = _ambos(client, admin_headers, recurso)
    assert lista == detalhe == (True, False)


def test_regra_personalizada_sem_hoje_nao_serve(db, client, admin_headers, recurso):
    svc.definir_regra(db, recurso[0], svc.MODO_PERSONALIZADO, [QUINTA])
    lista, detalhe = _ambos(client, admin_headers, recurso)
    assert lista == detalhe == (False, False)


def test_regra_personalizada_com_hoje_serve(db, client, admin_headers, recurso):
    svc.definir_regra(db, recurso[0], svc.MODO_PERSONALIZADO, [SEXTA])
    lista, detalhe = _ambos(client, admin_headers, recurso)
    assert lista == detalhe == (True, False)


def test_excecao_de_hoje_vence_a_regra_semanal(db, client, admin_headers, recurso):
    svc.definir_regra(db, recurso[0], svc.MODO_PERSONALIZADO, [QUINTA])
    svc.definir_excecao(db, recurso[0], HOJE, True)
    lista, detalhe = _ambos(client, admin_headers, recurso)
    assert lista == detalhe == (True, False)


def test_esgotado_hoje_aparece_e_nao_altera_serve_hoje(db, client, admin_headers, recurso):
    svc.definir_esgotado(db, recurso[0], True)
    lista, detalhe = _ambos(client, admin_headers, recurso)
    assert lista == detalhe == (True, True)


def test_listagem_calcula_estado_de_cada_item(
    db, client, admin_headers, marmita_pronta, marmita_personalizavel
):
    svc.definir_regra(db, marmita_pronta, svc.MODO_PERSONALIZADO, [QUINTA])
    svc.definir_esgotado(db, marmita_personalizavel, True)

    resposta = client.get("/admin/marmitas", headers=admin_headers)
    assert resposta.status_code == 200
    por_id = {i["id"]: i for i in resposta.json()["itens"]}

    pronta = por_id[str(marmita_pronta.id)]
    assert (pronta["serve_hoje"], pronta["esgotado_hoje"]) == (False, False)
    personalizavel = por_id[str(marmita_personalizavel.id)]
    assert (personalizavel["serve_hoje"], personalizavel["esgotado_hoje"]) == (True, True)


@pytest.mark.parametrize("base", ["/admin/marmitas", "/admin/combos"])
def test_patch_ativo_devolve_estados(
    db, client, admin_headers, base, marmita_pronta, combo_teste
):
    alvo = marmita_pronta if base == "/admin/marmitas" else combo_teste
    svc.definir_esgotado(db, alvo, True)

    resposta = client.patch(f"{base}/{alvo.id}/ativo", json={"ativo": False}, headers=admin_headers)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ativo"] is False
    assert corpo["serve_hoje"] is True
    assert corpo["esgotado_hoje"] is True