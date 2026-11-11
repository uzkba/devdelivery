from decimal import Decimal

import pytest

from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    RestaurantDeliverySettings,
)

URL = "/admin/restaurante/entrega/bairros"
URL_PUBLICA = "/restaurantes/marmitas-da-vovo"


def _config(db, restaurante, modo=DeliveryChargeMode.GRATIS):
    config = RestaurantDeliverySettings(restaurant_id=restaurante.id, charge_mode=modo)
    db.add(config)
    db.flush()
    return config


def _bairro(db, restaurante, nome="Centro", taxa="5.00", ativo=True):
    regra = DeliveryRuleNeighborhood(
        restaurant_id=restaurante.id, neighborhood=nome, fee=Decimal(taxa), is_active=ativo
    )
    db.add(regra)
    db.flush()
    db.refresh(regra)
    return regra


def _corpo(**extra):
    corpo = {"bairro": "Centro", "taxa": 5, "ativo": True}
    corpo.update(extra)
    return corpo


# ------------------------------- listagem -------------------------------
def test_lista_vazia(client, restaurante, admin_headers):
    resp = client.get(URL, headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json() == []


def test_lista_ordenada_por_nome_e_so_do_restaurante(
    client, db, restaurante, outro_restaurante, admin_headers
):
    _bairro(db, restaurante, "Zona Sul", "9.00")
    _bairro(db, restaurante, "Centro", "5.00", ativo=False)
    _bairro(db, restaurante, "Bairro Novo", "7.50")
    _bairro(db, outro_restaurante, "Do Outro", "3.00")

    resp = client.get(URL, headers=admin_headers)

    assert resp.status_code == 200
    assert [(b["bairro"], b["taxa"], b["ativo"]) for b in resp.json()] == [
        ("Bairro Novo", "7.50", True),
        ("Centro", "5.00", False),
        ("Zona Sul", "9.00", True),
    ]
    assert all("id" in b for b in resp.json())


def test_somente_admin_acessa(client, db, restaurante, atendente_user, token_para):
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}
    bairro = _bairro(db, restaurante)

    assert client.get(URL, headers=headers).status_code == 403
    assert client.post(URL, json=_corpo(), headers=headers).status_code == 403
    assert client.put(f"{URL}/{bairro.id}", json=_corpo(), headers=headers).status_code == 403
    assert client.delete(f"{URL}/{bairro.id}", headers=headers).status_code == 403


# ------------------------------- criação -------------------------------
def test_cria_bairro_limpando_espacos(client, db, restaurante, admin_headers):
    resp = client.post(
        URL, json=_corpo(bairro="  Vila   Nova  ", taxa=6.5), headers=admin_headers
    )

    assert resp.status_code == 201
    dados = resp.json()
    assert dados["bairro"] == "Vila Nova"
    assert dados["taxa"] == "6.50"
    assert dados["ativo"] is True
    regra = db.query(DeliveryRuleNeighborhood).filter_by(restaurant_id=restaurante.id).one()
    assert str(regra.id) == dados["id"]


def test_ativo_e_verdadeiro_por_padrao(client, restaurante, admin_headers):
    resp = client.post(URL, json={"bairro": "Centro", "taxa": 4}, headers=admin_headers)

    assert resp.status_code == 201
    assert resp.json()["ativo"] is True


def test_aceita_taxa_zero(client, restaurante, admin_headers):
    resp = client.post(URL, json=_corpo(taxa=0), headers=admin_headers)

    assert resp.status_code == 201
    assert resp.json()["taxa"] == "0.00"


@pytest.mark.parametrize(
    "existente, novo",
    [
        ("Centro", "centro"),
        ("São José", "sao jose"),
        ("Centro", "  CENTRO  "),
        ("Vila Nova", "Vila   Nova"),
    ],
)
def test_rejeita_nome_duplicado_sem_diferenciar_acento_caixa_e_espacos(
    client, db, restaurante, admin_headers, existente, novo
):
    _bairro(db, restaurante, existente)

    resp = client.post(URL, json=_corpo(bairro=novo), headers=admin_headers)

    assert resp.status_code == 409


def test_nome_duplicado_conta_mesmo_com_bairro_inativo(client, db, restaurante, admin_headers):
    _bairro(db, restaurante, "Centro", ativo=False)

    resp = client.post(URL, json=_corpo(bairro="Centro"), headers=admin_headers)

    assert resp.status_code == 409


def test_mesmo_nome_em_outro_restaurante_e_permitido(
    client, db, restaurante, outro_restaurante, admin_headers
):
    _bairro(db, outro_restaurante, "Centro")

    resp = client.post(URL, json=_corpo(bairro="Centro"), headers=admin_headers)

    assert resp.status_code == 201


@pytest.mark.parametrize(
    "extra",
    [
        {"bairro": ""},
        {"bairro": "   "},
        {"bairro": "x" * 121},
        {"taxa": -1},
        {"taxa": 1.234},
    ],
)
def test_rejeita_valores_invalidos(client, restaurante, admin_headers, extra):
    resp = client.post(URL, json=_corpo(**extra), headers=admin_headers)

    assert resp.status_code == 422


# ------------------------------- atualização -------------------------------
def test_atualiza_bairro(client, db, restaurante, admin_headers):
    bairro = _bairro(db, restaurante, "Centro", "5.00")

    resp = client.put(
        f"{URL}/{bairro.id}",
        json=_corpo(bairro="Centro Histórico", taxa=8, ativo=False),
        headers=admin_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["bairro"] == "Centro Histórico"
    assert resp.json()["taxa"] == "8.00"
    assert resp.json()["ativo"] is False
    db.refresh(bairro)
    assert bairro.neighborhood == "Centro Histórico"
    assert bairro.is_active is False


def test_atualiza_mantendo_o_proprio_nome_com_outra_grafia(client, db, restaurante, admin_headers):
    bairro = _bairro(db, restaurante, "Centro")

    resp = client.put(
        f"{URL}/{bairro.id}", json=_corpo(bairro="CENTRO", taxa=6), headers=admin_headers
    )

    assert resp.status_code == 200
    assert resp.json()["bairro"] == "CENTRO"


def test_atualiza_rejeita_nome_de_outro_bairro(client, db, restaurante, admin_headers):
    _bairro(db, restaurante, "Centro")
    outro = _bairro(db, restaurante, "Zona Sul")

    resp = client.put(f"{URL}/{outro.id}", json=_corpo(bairro="centro"), headers=admin_headers)

    assert resp.status_code == 409


def test_atualiza_bairro_inexistente_ou_de_outro_restaurante(
    client, db, restaurante, outro_restaurante, admin_headers
):
    alheio = _bairro(db, outro_restaurante, "Do Outro")

    resp = client.put(f"{URL}/{alheio.id}", json=_corpo(), headers=admin_headers)

    assert resp.status_code == 404
    db.refresh(alheio)
    assert alheio.neighborhood == "Do Outro"


# --------------------------- último bairro ativo ---------------------------
def test_nao_desativa_ultimo_bairro_ativo_no_modo_bairro(client, db, restaurante, admin_headers):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    unico = _bairro(db, restaurante, "Centro")
    _bairro(db, restaurante, "Inativo", ativo=False)

    resp = client.put(f"{URL}/{unico.id}", json=_corpo(ativo=False), headers=admin_headers)

    assert resp.status_code == 422
    db.refresh(unico)
    assert unico.is_active is True


def test_desativa_bairro_quando_sobra_outro_ativo(client, db, restaurante, admin_headers):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    primeiro = _bairro(db, restaurante, "Centro")
    _bairro(db, restaurante, "Zona Sul")

    resp = client.put(f"{URL}/{primeiro.id}", json=_corpo(ativo=False), headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["ativo"] is False


@pytest.mark.parametrize("modo", [DeliveryChargeMode.GRATIS, DeliveryChargeMode.FIXO])
def test_desativa_ultimo_bairro_fora_do_modo_bairro(client, db, restaurante, admin_headers, modo):
    _config(db, restaurante, modo)
    unico = _bairro(db, restaurante, "Centro")

    resp = client.put(f"{URL}/{unico.id}", json=_corpo(ativo=False), headers=admin_headers)

    assert resp.status_code == 200


def test_desativa_ultimo_bairro_sem_configuracao_de_entrega(client, db, restaurante, admin_headers):
    unico = _bairro(db, restaurante, "Centro")

    resp = client.put(f"{URL}/{unico.id}", json=_corpo(ativo=False), headers=admin_headers)

    assert resp.status_code == 200


# ------------------------------- remoção -------------------------------
def test_remove_bairro(client, db, restaurante, admin_headers):
    bairro = _bairro(db, restaurante)

    resp = client.delete(f"{URL}/{bairro.id}", headers=admin_headers)

    assert resp.status_code == 204
    assert db.query(DeliveryRuleNeighborhood).filter_by(id=bairro.id).first() is None


def test_nao_remove_ultimo_bairro_ativo_no_modo_bairro(client, db, restaurante, admin_headers):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    unico = _bairro(db, restaurante, "Centro")

    resp = client.delete(f"{URL}/{unico.id}", headers=admin_headers)

    assert resp.status_code == 422
    assert db.query(DeliveryRuleNeighborhood).filter_by(id=unico.id).first() is not None


def test_remove_bairro_inativo_mesmo_sendo_o_unico_ativo_preservado(
    client, db, restaurante, admin_headers
):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    _bairro(db, restaurante, "Centro")
    inativo = _bairro(db, restaurante, "Antigo", ativo=False)

    resp = client.delete(f"{URL}/{inativo.id}", headers=admin_headers)

    assert resp.status_code == 204


def test_remove_bairro_inexistente_ou_de_outro_restaurante(
    client, db, restaurante, outro_restaurante, admin_headers
):
    alheio = _bairro(db, outro_restaurante, "Do Outro")

    resp = client.delete(f"{URL}/{alheio.id}", headers=admin_headers)

    assert resp.status_code == 404
    assert db.query(DeliveryRuleNeighborhood).filter_by(id=alheio.id).first() is not None


# ------------------------------- API publica -------------------------------
def test_publico_reflete_os_bairros_ativos(client, db, restaurante, admin_headers):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    client.post(URL, json=_corpo(bairro="Centro", taxa=4), headers=admin_headers)
    client.post(URL, json=_corpo(bairro="Distrito", taxa=9), headers=admin_headers)
    client.post(URL, json=_corpo(bairro="Desativado", taxa=1, ativo=False), headers=admin_headers)

    taxa = client.get(URL_PUBLICA).json()["entrega"]["taxa"]

    assert taxa["taxa_minima"] == "4.00"
    assert taxa["taxa_maxima"] == "9.00"