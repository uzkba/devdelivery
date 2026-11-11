import pytest

from app.model.models import PaymentMethod, RestaurantPaymentMethod

URL = "/admin/restaurante/pagamentos"
URL_PUBLICA = "/restaurantes/marmitas-da-vovo"
TODOS = ["CARTAO_CREDITO", "CARTAO_DEBITO", "DINHEIRO", "PIX"]


def _codigos(resposta):
    return [forma["codigo"] for forma in resposta.json()]


def _aceitas(db, restaurante):
    linhas = (
        db.query(PaymentMethod.code)
        .join(
            RestaurantPaymentMethod,
            RestaurantPaymentMethod.payment_method_id == PaymentMethod.id,
        )
        .filter(RestaurantPaymentMethod.restaurant_id == restaurante.id)
        .all()
    )
    return sorted(codigo for (codigo,) in linhas)


# ------------------------------- leitura -------------------------------
def test_lista_todas_as_formas_ativas_marcando_as_aceitas(
    client, restaurante, admin_headers, aceitar_formas
):
    aceitar_formas(restaurante, "PIX", "DINHEIRO")

    resp = client.get(URL, headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json() == [
        {"codigo": "CARTAO_CREDITO", "nome": "Cartão de Crédito", "aceita": False},
        {"codigo": "CARTAO_DEBITO", "nome": "Cartão de Débito", "aceita": False},
        {"codigo": "DINHEIRO", "nome": "Dinheiro", "aceita": True},
        {"codigo": "PIX", "nome": "Pix", "aceita": True},
    ]


def test_restaurante_de_teste_aceita_todas_por_padrao(client, restaurante, admin_headers):
    resp = client.get(URL, headers=admin_headers)

    assert _codigos(resp) == TODOS
    assert all(forma["aceita"] for forma in resp.json())


def test_forma_inativa_nao_aparece_nem_pode_ser_aceita(client, db, restaurante, admin_headers):
    db.query(PaymentMethod).filter_by(code="CARTAO_DEBITO").update(
        {PaymentMethod.is_active: False}
    )
    db.flush()

    listagem = client.get(URL, headers=admin_headers)
    tentativa = client.put(
        URL, json={"aceitas": ["PIX", "CARTAO_DEBITO"]}, headers=admin_headers
    )

    assert "CARTAO_DEBITO" not in _codigos(listagem)
    assert tentativa.status_code == 422


def test_somente_admin_acessa(client, restaurante, atendente_user, token_para):
    headers = {"Authorization": f"Bearer {token_para(atendente_user)}"}

    assert client.get(URL, headers=headers).status_code == 403
    assert client.put(URL, json={"aceitas": ["PIX"]}, headers=headers).status_code == 403


# ------------------------------- gravação -------------------------------
def test_substitui_a_lista_de_formas_aceitas(client, db, restaurante, admin_headers):
    resp = client.put(URL, json={"aceitas": ["PIX", "DINHEIRO"]}, headers=admin_headers)

    assert resp.status_code == 200
    assert {f["codigo"]: f["aceita"] for f in resp.json()} == {
        "CARTAO_CREDITO": False,
        "CARTAO_DEBITO": False,
        "DINHEIRO": True,
        "PIX": True,
    }
    assert _aceitas(db, restaurante) == ["DINHEIRO", "PIX"]


def test_pode_voltar_a_aceitar_uma_forma_removida(client, db, restaurante, admin_headers):
    client.put(URL, json={"aceitas": ["PIX"]}, headers=admin_headers)

    resp = client.put(URL, json={"aceitas": ["PIX", "CARTAO_CREDITO"]}, headers=admin_headers)

    assert resp.status_code == 200
    assert _aceitas(db, restaurante) == ["CARTAO_CREDITO", "PIX"]


def test_normaliza_maiusculas_e_espacos_nos_codigos(client, db, restaurante, admin_headers):
    resp = client.put(URL, json={"aceitas": ["pix", " dinheiro "]}, headers=admin_headers)

    assert resp.status_code == 200
    assert _aceitas(db, restaurante) == ["DINHEIRO", "PIX"]


def test_exige_ao_menos_uma_forma(client, db, restaurante, admin_headers):
    resp = client.put(URL, json={"aceitas": []}, headers=admin_headers)

    assert resp.status_code == 422
    assert _aceitas(db, restaurante) == TODOS


@pytest.mark.parametrize(
    "aceitas",
    [
        ["PIX", "PIX"],
        ["PIX", "pix"],
        ["PIX", ""],
        ["PIX", "VALE_REFEICAO"],
    ],
)
def test_rejeita_codigos_repetidos_vazios_ou_desconhecidos(
    client, db, restaurante, admin_headers, aceitas
):
    resp = client.put(URL, json={"aceitas": aceitas}, headers=admin_headers)

    assert resp.status_code == 422
    assert _aceitas(db, restaurante) == TODOS


def test_aceitas_sao_isoladas_por_restaurante(
    client, db, restaurante, outro_restaurante, outro_admin_headers
):
    resp = client.put(URL, json={"aceitas": ["PIX"]}, headers=outro_admin_headers)

    assert resp.status_code == 200
    assert _aceitas(db, outro_restaurante) == ["PIX"]
    assert _aceitas(db, restaurante) == TODOS


# ------------------------------- API publica -------------------------------
def test_publico_lista_as_formas_aceitas(client, restaurante, admin_headers):
    client.put(URL, json={"aceitas": ["PIX", "CARTAO_DEBITO"]}, headers=admin_headers)

    resp = client.get(URL_PUBLICA)

    assert resp.status_code == 200
    assert resp.json()["formas_pagamento"] == [
        {"codigo": "CARTAO_DEBITO", "nome": "Cartão de Débito"},
        {"codigo": "PIX", "nome": "Pix"},
    ]


def test_publico_oculta_forma_inativa(client, db, restaurante):
    db.query(PaymentMethod).filter_by(code="DINHEIRO").update({PaymentMethod.is_active: False})
    db.flush()

    codigos = [forma["codigo"] for forma in client.get(URL_PUBLICA).json()["formas_pagamento"]]

    assert "DINHEIRO" not in codigos
    assert "PIX" in codigos