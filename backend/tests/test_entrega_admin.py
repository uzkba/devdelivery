from decimal import Decimal

import pytest

from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    RestaurantDeliverySettings,
)

URL = "/admin/restaurante/entrega"
URL_PUBLICA = "/restaurantes/marmitas-da-vovo"


def _config(db, restaurante, **extra):
    dados = dict(restaurant_id=restaurante.id, charge_mode=DeliveryChargeMode.GRATIS)
    dados.update(extra)
    config = RestaurantDeliverySettings(**dados)
    db.add(config)
    db.flush()
    db.refresh(config)
    return config


def _bairro(db, restaurante, nome="Centro", taxa="5.00", ativo=True):
    regra = DeliveryRuleNeighborhood(
        restaurant_id=restaurante.id, neighborhood=nome, fee=Decimal(taxa), is_active=ativo
    )
    db.add(regra)
    db.flush()
    return regra


def _corpo(**extra):
    corpo = {
        "entrega_ativa": True,
        "retirada_ativa": True,
        "modo": "GRATIS",
        "valor_fixo": None,
        "frete_gratis_a_partir_de": None,
        "valor_minimo": None,
        "tempo_entrega_min": 40,
        "tempo_retirada_min": 20,
    }
    corpo.update(extra)
    return corpo


# ------------------------------- leitura -------------------------------
def test_busca_configuracao_do_restaurante(client, db, restaurante, admin_headers):
    _config(
        db,
        restaurante,
        charge_mode=DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("6.00"),
        free_delivery_from=Decimal("50.00"),
        min_order_value=Decimal("20.00"),
        delivery_time_minutes=45,
        pickup_time_minutes=15,
    )

    resp = client.get(URL, headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json() == {
        "entrega_ativa": True,
        "retirada_ativa": True,
        "modo": "FIXO",
        "valor_fixo": "6.00",
        "frete_gratis_a_partir_de": "50.00",
        "valor_minimo": "20.00",
        "tempo_entrega_min": 45,
        "tempo_retirada_min": 15,
    }


def test_busca_sem_configuracao_retorna_404(client, restaurante, admin_headers):
    resp = client.get(URL, headers=admin_headers)

    assert resp.status_code == 404


def test_somente_admin_acessa(client, db, restaurante, atendente_user, token_para):
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}
    _config(db, restaurante)

    assert client.get(URL, headers=headers).status_code == 403
    assert client.put(URL, json=_corpo(), headers=headers).status_code == 403


# ------------------------------- gravação -------------------------------
def test_salva_criando_a_configuracao_quando_nao_existe(client, db, restaurante, admin_headers):
    resp = client.put(
        URL,
        json=_corpo(modo="FIXO", valor_fixo=7.5, valor_minimo=15, frete_gratis_a_partir_de=60),
        headers=admin_headers,
    )

    assert resp.status_code == 200
    dados = resp.json()
    assert dados["modo"] == "FIXO"
    assert dados["valor_fixo"] == "7.50"
    assert dados["valor_minimo"] == "15.00"
    assert dados["frete_gratis_a_partir_de"] == "60.00"
    assert dados["tempo_entrega_min"] == 40
    assert dados["tempo_retirada_min"] == 20
    total = db.query(RestaurantDeliverySettings).filter_by(restaurant_id=restaurante.id).count()
    assert total == 1


def test_salva_atualizando_a_configuracao_existente(client, db, restaurante, admin_headers):
    config = _config(db, restaurante)

    resp = client.put(
        URL,
        json=_corpo(modo="FIXO", valor_fixo=8, entrega_ativa=False, tempo_retirada_min=10),
        headers=admin_headers,
    )

    assert resp.status_code == 200
    db.refresh(config)
    assert config.charge_mode == DeliveryChargeMode.FIXO
    assert config.fixed_fee == Decimal("8.00")
    assert config.delivery_enabled is False
    assert config.pickup_time_minutes == 10
    total = db.query(RestaurantDeliverySettings).filter_by(restaurant_id=restaurante.id).count()
    assert total == 1


@pytest.mark.parametrize("valor_fixo", [None, 0])
def test_modo_fixo_exige_valor_fixo_maior_que_zero(client, restaurante, admin_headers, valor_fixo):
    resp = client.put(URL, json=_corpo(modo="FIXO", valor_fixo=valor_fixo), headers=admin_headers)

    assert resp.status_code == 422


def test_valor_fixo_e_descartado_fora_do_modo_fixo(client, restaurante, admin_headers):
    resp = client.put(URL, json=_corpo(modo="GRATIS", valor_fixo=5), headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["valor_fixo"] is None


def test_zero_em_minimo_e_frete_gratis_significa_sem_limite(client, restaurante, admin_headers):
    resp = client.put(
        URL,
        json=_corpo(modo="FIXO", valor_fixo=5, valor_minimo=0, frete_gratis_a_partir_de=0),
        headers=admin_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["valor_minimo"] is None
    assert resp.json()["frete_gratis_a_partir_de"] is None


def test_exige_entrega_ou_retirada_ativa(client, restaurante, admin_headers):
    resp = client.put(
        URL, json=_corpo(entrega_ativa=False, retirada_ativa=False), headers=admin_headers
    )

    assert resp.status_code == 422


def test_retirada_sozinha_e_valida(client, restaurante, admin_headers):
    resp = client.put(URL, json=_corpo(entrega_ativa=False), headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["entrega_ativa"] is False
    assert resp.json()["retirada_ativa"] is True


def test_modo_bairro_exige_bairro_ativo(client, db, restaurante, admin_headers):
    corpo = _corpo(modo="BAIRRO")

    resp = client.put(URL, json=corpo, headers=admin_headers)
    assert resp.status_code == 422
    assert "bairro" in resp.json()["detail"]

    _bairro(db, restaurante, "Inativo", ativo=False)
    resp = client.put(URL, json=corpo, headers=admin_headers)
    assert resp.status_code == 422

    _bairro(db, restaurante, "Centro")
    resp = client.put(URL, json=corpo, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["modo"] == "BAIRRO"


@pytest.mark.parametrize(
    "extra",
    [
        {"tempo_entrega_min": 0},
        {"tempo_retirada_min": 481},
        {"valor_minimo": -1},
        {"frete_gratis_a_partir_de": -1},
        {"modo": "FIXO", "valor_fixo": 1.234},
        {"modo": "DISTANCIA"},
    ],
)
def test_rejeita_valores_invalidos(client, restaurante, admin_headers, extra):
    resp = client.put(URL, json=_corpo(**extra), headers=admin_headers)

    assert resp.status_code == 422


def test_configuracao_e_isolada_por_restaurante(
    client, db, restaurante, outro_restaurante, admin_headers, outro_admin_headers
):
    resp = client.put(URL, json=_corpo(modo="FIXO", valor_fixo=9), headers=outro_admin_headers)
    assert resp.status_code == 200

    assert client.get(URL, headers=admin_headers).status_code == 404
    assert client.get(URL, headers=outro_admin_headers).json()["valor_fixo"] == "9.00"


# ------------------------------- API publica -------------------------------
def test_publico_expoe_frete_gratis_no_modo_fixo(client, db, restaurante):
    _config(
        db,
        restaurante,
        charge_mode=DeliveryChargeMode.FIXO,
        fixed_fee=Decimal("6.00"),
        free_delivery_from=Decimal("50.00"),
    )

    taxa = client.get(URL_PUBLICA).json()["entrega"]["taxa"]

    assert taxa["modo"] == "FIXO"
    assert taxa["valor_fixo"] == "6.00"
    assert taxa["frete_gratis_a_partir_de"] == "50.00"


def test_publico_expoe_frete_gratis_no_modo_bairro(client, db, restaurante):
    _config(
        db,
        restaurante,
        charge_mode=DeliveryChargeMode.BAIRRO,
        free_delivery_from=Decimal("80.00"),
    )
    _bairro(db, restaurante, "Centro", "4.00")
    _bairro(db, restaurante, "Distrito", "9.00")

    taxa = client.get(URL_PUBLICA).json()["entrega"]["taxa"]

    assert taxa["taxa_minima"] == "4.00"
    assert taxa["taxa_maxima"] == "9.00"
    assert taxa["frete_gratis_a_partir_de"] == "80.00"


def test_publico_oculta_frete_gratis_no_modo_gratis(client, db, restaurante):
    _config(db, restaurante, free_delivery_from=Decimal("50.00"))

    taxa = client.get(URL_PUBLICA).json()["entrega"]["taxa"]

    assert taxa["modo"] == "GRATIS"
    assert taxa["frete_gratis_a_partir_de"] is None