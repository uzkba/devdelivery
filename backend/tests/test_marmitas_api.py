import uuid
from decimal import Decimal

import pytest

URL = "/admin/marmitas"
URL_COMBOS = "/admin/combos"


# ── helpers ──────────────────────────────────────────────────────────

def _pronta(*alimentos, **extra):
    return {
        "nome": "Marmita Fit",
        "tipo": "PRONTA",
        "preco": "24.90",
        "composicao": [{"alimento_id": str(a.id), "quantidade_fixa": 1} for a in alimentos],
        **extra,
    }


def _personalizavel(*categorias, quantidade=2, **extra):
    return {
        "nome": "Monte a sua",
        "tipo": "PERSONALIZAVEL",
        "preco": "22.00",
        "categorias": [
            {"categoria_alimento_id": str(c.id), "quantidade_exigida": quantidade} for c in categorias
        ],
        **extra,
    }


def _criar(client, headers, payload):
    r = client.post(URL, json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _requisicoes(alimento, marmita_id):
    return [
        ("POST", URL, _pronta(alimento)),
        ("GET", URL, None),
        ("GET", f"{URL}/{marmita_id}", None),
        ("PUT", f"{URL}/{marmita_id}", _pronta(alimento)),
        ("PATCH", f"{URL}/{marmita_id}/ativo", {"ativo": False}),
        ("DELETE", f"{URL}/{marmita_id}", None),
    ]


def _verificar_todas(client, requisicoes, headers, esperados):
    for metodo, url, corpo in requisicoes:
        r = client.request(metodo, url, json=corpo, headers=headers)
        assert r.status_code in esperados, f"{metodo} {url} -> {r.status_code}: {r.text}"


# ── autenticação e perfil ────────────────────────────────────────────

def test_sem_token_da_401_em_todas_as_rotas(client, alimento_arroz):
    _verificar_todas(client, _requisicoes(alimento_arroz, uuid.uuid4()), None, (401,))


@pytest.mark.parametrize("usuario", ["atendente_user", "caixa_user", "entregador_user"])
def test_perfil_nao_admin_da_403_em_todas_as_rotas(client, request, token_para, alimento_arroz, usuario):
    user = request.getfixturevalue(usuario)
    headers = {"Authorization": f"Bearer {token_para(user)}"}

    _verificar_todas(client, _requisicoes(alimento_arroz, uuid.uuid4()), headers, (403,))


def test_token_de_cliente_nao_acessa_rotas_admin(client, cliente, token_para_cliente, alimento_arroz):
    headers = {"Authorization": f"Bearer {token_para_cliente(cliente)}"}

    _verificar_todas(client, _requisicoes(alimento_arroz, uuid.uuid4()), headers, (401, 403))


# ── isolamento entre restaurantes ────────────────────────────────────

@pytest.fixture()
def marmita_de_b(client, outro_admin_headers, alimento_b):
    return _criar(client, outro_admin_headers, _pronta(alimento_b, nome="Marmita do B"))


def test_admin_nao_ve_marmita_de_outro_restaurante(client, admin_headers, marmita_de_b):
    r = client.get(f"{URL}/{marmita_de_b['id']}", headers=admin_headers)

    assert r.status_code == 404


def test_admin_nao_edita_nem_altera_nem_exclui_marmita_de_outro_restaurante(
    client, admin_headers, outro_admin_headers, alimento_arroz, marmita_de_b
):
    url = f"{URL}/{marmita_de_b['id']}"

    assert client.put(url, json=_pronta(alimento_arroz), headers=admin_headers).status_code == 404
    assert client.patch(f"{url}/ativo", json={"ativo": False}, headers=admin_headers).status_code == 404
    assert client.delete(url, headers=admin_headers).status_code == 404

    # continua intacta para o dono
    r = client.get(url, headers=outro_admin_headers)
    assert r.status_code == 200
    assert r.json()["nome"] == "Marmita do B"
    assert r.json()["ativo"] is True


def test_listagem_nao_traz_marmita_de_outro_restaurante(client, admin_headers, alimento_arroz, marmita_de_b):
    propria = _criar(client, admin_headers, _pronta(alimento_arroz, nome="Marmita do A"))

    r = client.get(URL, headers=admin_headers)

    assert r.json()["total"] == 1
    assert [i["id"] for i in r.json()["itens"]] == [propria["id"]]


def test_criar_pronta_com_alimento_de_outro_restaurante_da_422(client, admin_headers, alimento_b):
    r = client.post(URL, json=_pronta(alimento_b), headers=admin_headers)

    assert r.status_code == 422


def test_criar_personalizavel_com_categoria_de_outro_restaurante_da_422(client, admin_headers, cat_composicao_b):
    r = client.post(URL, json=_personalizavel(cat_composicao_b), headers=admin_headers)

    assert r.status_code == 422


# ── criar ────────────────────────────────────────────────────────────

def test_criar_pronta_sucesso(client, admin_headers, alimento_arroz):
    d = _criar(
        client,
        admin_headers,
        _pronta(alimento_arroz, descricao="Arroz com frango", tamanho="M", destaque=True),
    )

    assert d["nome"] == "Marmita Fit"
    assert d["tipo"] == "PRONTA"
    assert d["tamanho"] == "M"
    assert Decimal(d["preco"]) == Decimal("24.90")
    assert d["ativo"] is True
    assert d["destaque"] is True
    assert d["imagem_url"] is None
    assert d["categorias"] == []
    assert d["composicao"] == [
        {"alimento_id": str(alimento_arroz.id), "alimento_nome": "Arroz", "quantidade_fixa": 1}
    ]


def test_criar_pronta_sem_tamanho_e_sem_descricao(client, admin_headers, alimento_arroz):
    d = _criar(client, admin_headers, _pronta(alimento_arroz))

    assert d["tamanho"] is None
    assert d["descricao"] is None
    assert d["destaque"] is False


def test_criar_personalizavel_aceita_categoria_com_quantidade_zero(
    client, admin_headers, cat_composicao, cat_composicao_2
):
    payload = _personalizavel(cat_composicao)
    payload["categorias"].append({"categoria_alimento_id": str(cat_composicao_2.id), "quantidade_exigida": 0})

    d = _criar(client, admin_headers, payload)

    assert d["tipo"] == "PERSONALIZAVEL"
    assert d["composicao"] == []
    assert [(c["categoria_nome"], c["quantidade_exigida"]) for c in d["categorias"]] == [
        ("Carnes", 2),
        ("Acompanhamentos", 0),
    ]


def test_criar_com_preco_zero_e_aceito(client, admin_headers, alimento_arroz):
    d = _criar(client, admin_headers, _pronta(alimento_arroz, preco="0"))

    assert Decimal(d["preco"]) == Decimal("0")


# ── validações de payload (422) ──────────────────────────────────────

def _dup(chave, valor, extra):
    item = {chave: valor, **extra}
    return [item, dict(item)]


INVALIDOS = [
    pytest.param(lambda a, c: _pronta(a, preco="-0.01"), id="preco-negativo"),
    pytest.param(lambda a, c: _pronta(a, nome="X"), id="nome-curto"),
    pytest.param(lambda a, c: _pronta(a, nome="   "), id="nome-so-espacos"),
    pytest.param(lambda a, c: _pronta(a, tipo="OUTRO"), id="tipo-invalido"),
    pytest.param(lambda a, c: _pronta(a, descricao="x" * 501), id="descricao-longa"),
    pytest.param(lambda a, c: _pronta(a, tamanho="x" * 41), id="tamanho-longo"),
    pytest.param(lambda a, c: _pronta(a, calorias_kcal=-1), id="calorias-negativas"),
    pytest.param(lambda a, c: _pronta(a, proteina_g="-1"), id="proteina-negativa"),
    pytest.param(lambda a, c: _pronta(a, carboidrato_g="-0.5"), id="carboidrato-negativo"),
    pytest.param(lambda a, c: _pronta(a, gordura_g="-2"), id="gordura-negativa"),
    # pronta
    pytest.param(lambda a, c: _pronta(), id="pronta-sem-composicao"),
    pytest.param(
        lambda a, c: _pronta(a, categorias=[{"categoria_alimento_id": str(c.id), "quantidade_exigida": 1}]),
        id="pronta-com-categorias",
    ),
    pytest.param(
        lambda a, c: _pronta(a, composicao=[{"alimento_id": str(a.id), "quantidade_fixa": 0}]),
        id="quantidade-fixa-zero",
    ),
    pytest.param(
        lambda a, c: _pronta(a, composicao=_dup("alimento_id", str(a.id), {"quantidade_fixa": 1})),
        id="alimento-repetido",
    ),
    # personalizavel
    pytest.param(lambda a, c: _personalizavel(), id="personalizavel-sem-categorias"),
    pytest.param(
        lambda a, c: _personalizavel(c, composicao=[{"alimento_id": str(a.id), "quantidade_fixa": 1}]),
        id="personalizavel-com-composicao",
    ),
    pytest.param(
        lambda a, c: _personalizavel(
            c, categorias=_dup("categoria_alimento_id", str(c.id), {"quantidade_exigida": 1})
        ),
        id="categoria-repetida",
    ),
    pytest.param(lambda a, c: _personalizavel(c, quantidade=0), id="todas-quantidades-zero"),
    pytest.param(lambda a, c: _personalizavel(c, quantidade=-1), id="quantidade-exigida-negativa"),
    pytest.param(lambda a, c: _personalizavel(c, quantidade=51), id="quantidade-exigida-acima-do-limite"),
]


@pytest.mark.parametrize("montar", INVALIDOS)
def test_payload_invalido_da_422(client, admin_headers, alimento_arroz, cat_composicao, montar):
    r = client.post(URL, json=montar(alimento_arroz, cat_composicao), headers=admin_headers)

    assert r.status_code == 422, r.text


# ── validações de referência (422 vindo do service) ──────────────────

@pytest.mark.parametrize("fixture_alimento", ["alimento_inativo", "alimento_so_venda", "alimento_b"])
def test_pronta_com_alimento_invalido_da_422(client, request, admin_headers, fixture_alimento):
    alimento = request.getfixturevalue(fixture_alimento)

    r = client.post(URL, json=_pronta(alimento), headers=admin_headers)

    assert r.status_code == 422, r.text


@pytest.mark.parametrize("fixture_categoria", ["cat_venda", "cat_composicao_inativa", "cat_composicao_b"])
def test_personalizavel_com_categoria_invalida_da_422(client, request, admin_headers, fixture_categoria):
    categoria = request.getfixturevalue(fixture_categoria)

    r = client.post(URL, json=_personalizavel(categoria), headers=admin_headers)

    assert r.status_code == 422, r.text


def test_referencias_inexistentes_da_422(client, admin_headers, alimento_arroz):
    fantasma = type("F", (), {"id": uuid.uuid4()})()

    assert client.post(URL, json=_pronta(fantasma), headers=admin_headers).status_code == 422
    assert client.post(URL, json=_personalizavel(fantasma), headers=admin_headers).status_code == 422


# ── informação nutricional (opcional) ────────────────────────────────

def test_criar_sem_informacao_nutricional_devolve_nulos(client, admin_headers, alimento_arroz):
    d = _criar(client, admin_headers, _pronta(alimento_arroz))

    assert d["calorias_kcal"] is None
    assert d["proteina_g"] is None
    assert d["carboidrato_g"] is None
    assert d["gordura_g"] is None


def test_criar_com_informacao_nutricional(client, admin_headers, alimento_arroz):
    d = _criar(
        client,
        admin_headers,
        _pronta(alimento_arroz, calorias_kcal=520, proteina_g="30.5", carboidrato_g="55", gordura_g="12.2"),
    )

    assert d["calorias_kcal"] == 520
    assert Decimal(d["proteina_g"]) == Decimal("30.5")
    assert Decimal(d["carboidrato_g"]) == Decimal("55")
    assert Decimal(d["gordura_g"]) == Decimal("12.2")


def test_informacao_nutricional_parcial_e_aceita(client, admin_headers, alimento_arroz):
    d = _criar(client, admin_headers, _pronta(alimento_arroz, calorias_kcal=450))

    assert d["calorias_kcal"] == 450
    assert d["proteina_g"] is None


# ── buscar ───────────────────────────────────────────────────────────

def test_buscar_marmita_por_id(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.get(f"{URL}/{criada['id']}", headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == criada


def test_buscar_inexistente_da_404(client, admin_headers):
    assert client.get(f"{URL}/{uuid.uuid4()}", headers=admin_headers).status_code == 404


def test_buscar_com_id_malformado_da_422(client, admin_headers):
    assert client.get(f"{URL}/nao-e-uuid", headers=admin_headers).status_code == 422


# ── listar ───────────────────────────────────────────────────────────

def test_listar_vazio(client, admin_headers):
    r = client.get(URL, headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == {"itens": [], "total": 0}


def test_listar_ordena_ativas_primeiro_e_depois_por_nome(client, admin_headers, alimento_arroz):
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Zebra Fit"))
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Alfa Fit", ativo=False))
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Beta Fit"))

    r = client.get(URL, headers=admin_headers)

    assert [i["nome"] for i in r.json()["itens"]] == ["Beta Fit", "Zebra Fit", "Alfa Fit"]


def test_listar_resumo_nao_traz_composicao(client, admin_headers, alimento_arroz):
    _criar(client, admin_headers, _pronta(alimento_arroz))

    item = client.get(URL, headers=admin_headers).json()["itens"][0]

    assert "composicao" not in item
    assert "categorias" not in item


def test_listar_filtra_por_tipo(client, admin_headers, alimento_arroz, cat_composicao):
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Pronta A"))
    _criar(client, admin_headers, _personalizavel(cat_composicao, nome="Monte A"))

    prontas = client.get(f"{URL}?tipo=PRONTA", headers=admin_headers).json()
    personalizaveis = client.get(f"{URL}?tipo=PERSONALIZAVEL", headers=admin_headers).json()

    assert [i["nome"] for i in prontas["itens"]] == ["Pronta A"]
    assert [i["nome"] for i in personalizaveis["itens"]] == ["Monte A"]


def test_listar_filtra_por_ativo(client, admin_headers, alimento_arroz):
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Marmita Ativa"))
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Marmita Inativa", ativo=False))

    ativas = client.get(f"{URL}?ativo=true", headers=admin_headers).json()
    inativas = client.get(f"{URL}?ativo=false", headers=admin_headers).json()

    assert [i["nome"] for i in ativas["itens"]] == ["Marmita Ativa"]
    assert [i["nome"] for i in inativas["itens"]] == ["Marmita Inativa"]


def test_listar_busca_por_nome_sem_diferenciar_maiusculas(client, admin_headers, alimento_arroz):
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Marmita Fit"))
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Feijoada Completa"))

    r = client.get(f"{URL}?busca=FIT", headers=admin_headers)

    assert [i["nome"] for i in r.json()["itens"]] == ["Marmita Fit"]
    assert r.json()["total"] == 1


def test_listar_paginacao_mantem_total(client, admin_headers, alimento_arroz):
    for letra in "ABC":
        _criar(client, admin_headers, _pronta(alimento_arroz, nome=f"Marmita {letra}"))

    pagina1 = client.get(f"{URL}?limite=2", headers=admin_headers).json()
    pagina2 = client.get(f"{URL}?limite=2&deslocamento=2", headers=admin_headers).json()

    assert pagina1["total"] == 3 and len(pagina1["itens"]) == 2
    assert pagina2["total"] == 3 and len(pagina2["itens"]) == 1


@pytest.mark.parametrize("query", ["limite=0", "limite=101", "deslocamento=-1"])
def test_listar_paginacao_invalida_da_422(client, admin_headers, query):
    assert client.get(f"{URL}?{query}", headers=admin_headers).status_code == 422


# ── atualizar ────────────────────────────────────────────────────────

def test_atualizar_substitui_campos_e_composicao(client, admin_headers, alimento_arroz, alimento_feijao):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))
    novo = _pronta(alimento_feijao, nome="Marmita Nova", preco="30.00", tamanho="G")
    novo["composicao"][0]["quantidade_fixa"] = 2

    r = client.put(f"{URL}/{criada['id']}", json=novo, headers=admin_headers)

    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == criada["id"]
    assert d["nome"] == "Marmita Nova"
    assert Decimal(d["preco"]) == Decimal("30.00")
    assert d["tamanho"] == "G"
    assert [(c["alimento_nome"], c["quantidade_fixa"]) for c in d["composicao"]] == [("Feijão", 2)]


def test_atualizar_com_a_mesma_composicao_nao_viola_unicidade(client, admin_headers, alimento_arroz):
    """Regressão: o service limpa e recria os filhos; INSERT antes de DELETE quebraria a UNIQUE."""
    payload = _pronta(alimento_arroz)
    criada = _criar(client, admin_headers, payload)

    r = client.put(f"{URL}/{criada['id']}", json=payload, headers=admin_headers)

    assert r.status_code == 200, r.text
    assert len(r.json()["composicao"]) == 1


def test_atualizar_com_as_mesmas_categorias_nao_viola_unicidade(client, admin_headers, cat_composicao):
    payload = _personalizavel(cat_composicao)
    criada = _criar(client, admin_headers, payload)

    r = client.put(f"{URL}/{criada['id']}", json=payload, headers=admin_headers)

    assert r.status_code == 200, r.text
    assert len(r.json()["categorias"]) == 1


def test_atualizar_trocando_o_tipo_substitui_os_filhos(client, admin_headers, alimento_arroz, cat_composicao):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.put(f"{URL}/{criada['id']}", json=_personalizavel(cat_composicao), headers=admin_headers)

    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tipo"] == "PERSONALIZAVEL"
    assert d["composicao"] == []
    assert len(d["categorias"]) == 1


def test_atualizar_e_substituicao_completa_limpa_nutricao_omitida(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz, calorias_kcal=500))

    r = client.put(f"{URL}/{criada['id']}", json=_pronta(alimento_arroz), headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["calorias_kcal"] is None


def test_atualizar_invalido_da_422_e_nao_altera(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.put(f"{URL}/{criada['id']}", json=_pronta(alimento_arroz, preco="-1"), headers=admin_headers)

    assert r.status_code == 422
    atual = client.get(f"{URL}/{criada['id']}", headers=admin_headers).json()
    assert Decimal(atual["preco"]) == Decimal("24.90")


def test_atualizar_com_referencia_invalida_da_422_e_nao_altera(client, admin_headers, alimento_arroz, alimento_b):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.put(f"{URL}/{criada['id']}", json=_pronta(alimento_b, nome="Outra"), headers=admin_headers)

    assert r.status_code == 422
    atual = client.get(f"{URL}/{criada['id']}", headers=admin_headers).json()
    assert atual["nome"] == "Marmita Fit"
    assert atual["composicao"][0]["alimento_nome"] == "Arroz"


def test_atualizar_inexistente_da_404(client, admin_headers, alimento_arroz):
    r = client.put(f"{URL}/{uuid.uuid4()}", json=_pronta(alimento_arroz), headers=admin_headers)

    assert r.status_code == 404


# ── ativar / desativar ───────────────────────────────────────────────

def test_desativar_e_reativar(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))
    url = f"{URL}/{criada['id']}/ativo"

    r1 = client.patch(url, json={"ativo": False}, headers=admin_headers)
    r2 = client.patch(url, json={"ativo": True}, headers=admin_headers)

    assert r1.status_code == 200 and r1.json()["ativo"] is False
    assert r2.status_code == 200 and r2.json()["ativo"] is True


def test_ativo_ausente_no_patch_da_422(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.patch(f"{URL}/{criada['id']}/ativo", json={}, headers=admin_headers)

    assert r.status_code == 422


def test_patch_ativo_inexistente_da_404(client, admin_headers):
    r = client.patch(f"{URL}/{uuid.uuid4()}/ativo", json={"ativo": False}, headers=admin_headers)

    assert r.status_code == 404


# ── excluir ──────────────────────────────────────────────────────────

def test_excluir_marmita(client, admin_headers, alimento_arroz):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    r = client.delete(f"{URL}/{criada['id']}", headers=admin_headers)

    assert r.status_code == 204
    assert client.get(f"{URL}/{criada['id']}", headers=admin_headers).status_code == 404


def test_excluir_marmita_leva_os_filhos_junto_e_preserva_o_alimento(
    client, admin_headers, alimento_arroz
):
    criada = _criar(client, admin_headers, _pronta(alimento_arroz))

    assert client.delete(f"{URL}/{criada['id']}", headers=admin_headers).status_code == 204

    # o alimento continua existindo e pode compor outra marmita
    _criar(client, admin_headers, _pronta(alimento_arroz, nome="Outra Marmita"))


def test_excluir_inexistente_da_404(client, admin_headers):
    assert client.delete(f"{URL}/{uuid.uuid4()}", headers=admin_headers).status_code == 404


def test_excluir_marmita_usada_em_combo_da_409(client, admin_headers, alimento_arroz):
    # tudo criado via API (cada POST faz commit), para o rollback do 409 nao levar o setup junto
    marmita = _criar(client, admin_headers, _pronta(alimento_arroz))
    combo = client.post(
        URL_COMBOS,
        json={
            "nome": "Combo Teste",
            "preco": "30.00",
            "itens_marmita": [{"marmita_id": marmita["id"], "quantidade": 1}],
        },
        headers=admin_headers,
    )
    assert combo.status_code == 201, combo.text

    r = client.delete(f"{URL}/{marmita['id']}", headers=admin_headers)

    assert r.status_code == 409
    assert client.get(f"{URL}/{marmita['id']}", headers=admin_headers).status_code == 200
