import uuid
from decimal import Decimal

import pytest

URL = "/admin/combos"


# ── helpers ──────────────────────────────────────────────────────────

def _combo(marmitas=(), alimentos=(), **extra):
    return {
        "nome": "Combo Família",
        "preco": "49.90",
        "itens_marmita": [{"marmita_id": str(m.id), "quantidade": 1} for m in marmitas],
        "itens_alimento": [{"alimento_id": str(a.id), "quantidade": 1} for a in alimentos],
        **extra,
    }


def _criar(client, headers, payload):
    r = client.post(URL, json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _requisicoes(marmita, combo_id):
    return [
        ("POST", URL, _combo([marmita])),
        ("GET", URL, None),
        ("GET", f"{URL}/{combo_id}", None),
        ("PUT", f"{URL}/{combo_id}", _combo([marmita])),
        ("PATCH", f"{URL}/{combo_id}/ativo", {"ativo": False}),
        ("DELETE", f"{URL}/{combo_id}", None),
    ]


def _verificar_todas(client, requisicoes, headers, esperados):
    for metodo, url, corpo in requisicoes:
        r = client.request(metodo, url, json=corpo, headers=headers)
        assert r.status_code in esperados, f"{metodo} {url} -> {r.status_code}: {r.text}"


# ── autenticação e perfil ────────────────────────────────────────────

def test_sem_token_da_401_em_todas_as_rotas(client, marmita_pronta):
    _verificar_todas(client, _requisicoes(marmita_pronta, uuid.uuid4()), None, (401,))


@pytest.mark.parametrize("usuario", ["atendente_user", "caixa_user", "entregador_user"])
def test_perfil_nao_admin_da_403_em_todas_as_rotas(client, request, token_para, marmita_pronta, usuario):
    user = request.getfixturevalue(usuario)
    headers = {"Authorization": f"Bearer {token_para(user)}"}

    _verificar_todas(client, _requisicoes(marmita_pronta, uuid.uuid4()), headers, (403,))


def test_token_de_cliente_nao_acessa_rotas_admin(client, cliente, token_para_cliente, marmita_pronta):
    headers = {"Authorization": f"Bearer {token_para_cliente(cliente)}"}

    _verificar_todas(client, _requisicoes(marmita_pronta, uuid.uuid4()), headers, (401, 403))


# ── isolamento entre restaurantes ────────────────────────────────────

@pytest.fixture()
def combo_de_b(client, outro_admin_headers, marmita_b):
    return _criar(client, outro_admin_headers, _combo([marmita_b], nome="Combo do B"))


def test_admin_nao_ve_combo_de_outro_restaurante(client, admin_headers, combo_de_b):
    assert client.get(f"{URL}/{combo_de_b['id']}", headers=admin_headers).status_code == 404


def test_admin_nao_edita_nem_altera_nem_exclui_combo_de_outro_restaurante(
    client, admin_headers, outro_admin_headers, marmita_pronta, combo_de_b
):
    url = f"{URL}/{combo_de_b['id']}"

    assert client.put(url, json=_combo([marmita_pronta]), headers=admin_headers).status_code == 404
    assert client.patch(f"{url}/ativo", json={"ativo": False}, headers=admin_headers).status_code == 404
    assert client.delete(url, headers=admin_headers).status_code == 404

    r = client.get(url, headers=outro_admin_headers)
    assert r.status_code == 200
    assert r.json()["nome"] == "Combo do B"
    assert r.json()["ativo"] is True


def test_listagem_nao_traz_combo_de_outro_restaurante(client, admin_headers, marmita_pronta, combo_de_b):
    proprio = _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo do A"))

    r = client.get(URL, headers=admin_headers)

    assert r.json()["total"] == 1
    assert [i["id"] for i in r.json()["itens"]] == [proprio["id"]]


def test_criar_com_marmita_de_outro_restaurante_da_422(client, admin_headers, marmita_b):
    assert client.post(URL, json=_combo([marmita_b]), headers=admin_headers).status_code == 422


def test_criar_com_alimento_de_outro_restaurante_da_422(client, admin_headers, alimento_b):
    assert client.post(URL, json=_combo(alimentos=[alimento_b]), headers=admin_headers).status_code == 422


# ── criar ────────────────────────────────────────────────────────────

def test_criar_combo_com_marmita_e_alimento(client, admin_headers, marmita_pronta, alimento_arroz):
    payload = _combo([marmita_pronta], [alimento_arroz], descricao="Para dois", destaque=True)
    payload["itens_marmita"][0]["quantidade"] = 2
    payload["itens_alimento"][0]["quantidade"] = 3

    d = _criar(client, admin_headers, payload)

    assert d["nome"] == "Combo Família"
    assert d["descricao"] == "Para dois"
    assert Decimal(d["preco"]) == Decimal("49.90")
    assert d["ativo"] is True
    assert d["destaque"] is True
    assert d["imagem_url"] is None
    assert d["itens_marmita"] == [
        {
            "marmita_id": str(marmita_pronta.id),
            "marmita_nome": "Marmita Pronta",
            "marmita_tipo": "PRONTA",
            "quantidade": 2,
        }
    ]
    assert d["itens_alimento"] == [
        {"alimento_id": str(alimento_arroz.id), "alimento_nome": "Arroz", "quantidade": 3}
    ]


def test_criar_combo_so_com_alimentos(client, admin_headers, alimento_arroz, alimento_feijao):
    d = _criar(client, admin_headers, _combo(alimentos=[alimento_arroz, alimento_feijao]))

    assert d["itens_marmita"] == []
    assert [i["alimento_nome"] for i in d["itens_alimento"]] == ["Arroz", "Feijão"]


def test_criar_combo_so_com_marmitas(client, admin_headers, marmita_pronta, marmita_personalizavel):
    d = _criar(client, admin_headers, _combo([marmita_pronta, marmita_personalizavel]))

    assert d["itens_alimento"] == []
    assert [i["marmita_tipo"] for i in d["itens_marmita"]] == ["PRONTA", "PERSONALIZAVEL"]


def test_combo_aceita_qualquer_alimento_inclusive_avulso_puro(client, admin_headers, alimento_so_venda):
    d = _criar(client, admin_headers, _combo(alimentos=[alimento_so_venda]))

    assert d["itens_alimento"][0]["alimento_nome"] == "Feijoada"


def test_preco_do_combo_e_independente_da_soma_dos_itens(client, admin_headers, marmita_pronta, alimento_arroz):
    # marmita (20.00) + alimento (10.00) = 30.00, mas o combo custa 9.90
    d = _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz], preco="9.90"))

    assert Decimal(d["preco"]) == Decimal("9.90")


def test_criar_combo_com_preco_zero_e_aceito(client, admin_headers, marmita_pronta):
    d = _criar(client, admin_headers, _combo([marmita_pronta], preco="0"))

    assert Decimal(d["preco"]) == Decimal("0")


# ── validações de payload (422) ──────────────────────────────────────

def _dup(chave, valor):
    item = {chave: valor, "quantidade": 1}
    return [item, dict(item)]


INVALIDOS = [
    pytest.param(lambda m, a: _combo(), id="sem-itens"),
    pytest.param(lambda m, a: _combo([m], preco="-1"), id="preco-negativo"),
    pytest.param(lambda m, a: _combo([m], nome="X"), id="nome-curto"),
    pytest.param(lambda m, a: _combo([m], nome="   "), id="nome-so-espacos"),
    pytest.param(lambda m, a: _combo([m], descricao="x" * 501), id="descricao-longa"),
    pytest.param(
        lambda m, a: _combo(itens_marmita=_dup("marmita_id", str(m.id))),
        id="marmita-repetida",
    ),
    pytest.param(
        lambda m, a: _combo(itens_alimento=_dup("alimento_id", str(a.id))),
        id="alimento-repetido",
    ),
    pytest.param(
        lambda m, a: _combo(itens_marmita=[{"marmita_id": str(m.id), "quantidade": 0}]),
        id="quantidade-marmita-zero",
    ),
    pytest.param(
        lambda m, a: _combo(itens_marmita=[{"marmita_id": str(m.id), "quantidade": 21}]),
        id="quantidade-marmita-acima-do-limite",
    ),
    pytest.param(
        lambda m, a: _combo(itens_alimento=[{"alimento_id": str(a.id), "quantidade": 0}]),
        id="quantidade-alimento-zero",
    ),
    pytest.param(
        lambda m, a: _combo(itens_alimento=[{"alimento_id": str(a.id), "quantidade": 21}]),
        id="quantidade-alimento-acima-do-limite",
    ),
]


@pytest.mark.parametrize("montar", INVALIDOS)
def test_payload_invalido_da_422(client, admin_headers, marmita_pronta, alimento_arroz, montar):
    r = client.post(URL, json=montar(marmita_pronta, alimento_arroz), headers=admin_headers)

    assert r.status_code == 422, r.text


# ── validações de referência (422 vindo do service) ──────────────────

@pytest.mark.parametrize("fixture_marmita", ["marmita_inativa", "marmita_b"])
def test_combo_com_marmita_invalida_da_422(client, request, admin_headers, fixture_marmita):
    marmita = request.getfixturevalue(fixture_marmita)

    r = client.post(URL, json=_combo([marmita]), headers=admin_headers)

    assert r.status_code == 422, r.text


@pytest.mark.parametrize("fixture_alimento", ["alimento_inativo", "alimento_b"])
def test_combo_com_alimento_invalido_da_422(client, request, admin_headers, fixture_alimento):
    alimento = request.getfixturevalue(fixture_alimento)

    r = client.post(URL, json=_combo(alimentos=[alimento]), headers=admin_headers)

    assert r.status_code == 422, r.text


def test_referencias_inexistentes_da_422(client, admin_headers):
    fantasma = type("F", (), {"id": uuid.uuid4()})()

    assert client.post(URL, json=_combo([fantasma]), headers=admin_headers).status_code == 422
    assert client.post(URL, json=_combo(alimentos=[fantasma]), headers=admin_headers).status_code == 422


# ── avisos para o admin ──────────────────────────────────────────────

def test_aviso_de_marmita_personalizavel(client, admin_headers, marmita_pronta, marmita_personalizavel):
    simples = _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo Simples"))
    complexo = _criar(client, admin_headers, _combo([marmita_personalizavel], nome="Combo Complexo"))

    assert simples["possui_marmita_personalizavel"] is False
    assert complexo["possui_marmita_personalizavel"] is True


def test_aviso_de_item_inativo_apos_entrar_no_combo(client, db, admin_headers, marmita_pronta, alimento_arroz):
    criado = _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz]))
    assert criado["possui_item_inativo"] is False

    alimento_arroz.is_active = False
    db.flush()

    r = client.get(f"{URL}/{criado['id']}", headers=admin_headers)
    assert r.json()["possui_item_inativo"] is True


def test_aviso_de_marmita_inativa_apos_entrar_no_combo(client, db, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    marmita_pronta.is_active = False
    db.flush()

    r = client.get(f"{URL}/{criado['id']}", headers=admin_headers)
    assert r.json()["possui_item_inativo"] is True


# ── buscar ───────────────────────────────────────────────────────────

def test_buscar_combo_por_id(client, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    r = client.get(f"{URL}/{criado['id']}", headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == criado


def test_buscar_inexistente_da_404(client, admin_headers):
    assert client.get(f"{URL}/{uuid.uuid4()}", headers=admin_headers).status_code == 404


def test_buscar_com_id_malformado_da_422(client, admin_headers):
    assert client.get(f"{URL}/nao-e-uuid", headers=admin_headers).status_code == 422


# ── listar ───────────────────────────────────────────────────────────

def test_listar_vazio(client, admin_headers):
    r = client.get(URL, headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == {"itens": [], "total": 0}


def test_listar_ordena_ativos_primeiro_e_depois_por_nome(client, admin_headers, marmita_pronta):
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Zebra Combo"))
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Alfa Combo", ativo=False))
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Beta Combo"))

    r = client.get(URL, headers=admin_headers)

    assert [i["nome"] for i in r.json()["itens"]] == ["Beta Combo", "Zebra Combo", "Alfa Combo"]


def test_listar_resumo_nao_traz_itens_mas_traz_avisos(client, admin_headers, marmita_pronta):
    _criar(client, admin_headers, _combo([marmita_pronta]))

    item = client.get(URL, headers=admin_headers).json()["itens"][0]

    assert "itens_marmita" not in item
    assert "itens_alimento" not in item
    assert item["possui_marmita_personalizavel"] is False
    assert item["possui_item_inativo"] is False


def test_listar_filtra_por_ativo(client, admin_headers, marmita_pronta):
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo Ativo"))
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo Inativo", ativo=False))

    ativos = client.get(f"{URL}?ativo=true", headers=admin_headers).json()
    inativos = client.get(f"{URL}?ativo=false", headers=admin_headers).json()

    assert [i["nome"] for i in ativos["itens"]] == ["Combo Ativo"]
    assert [i["nome"] for i in inativos["itens"]] == ["Combo Inativo"]


def test_listar_busca_por_nome_sem_diferenciar_maiusculas(client, admin_headers, marmita_pronta):
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo Família"))
    _criar(client, admin_headers, _combo([marmita_pronta], nome="Combo Casal"))

    r = client.get(f"{URL}?busca=casal", headers=admin_headers)

    assert [i["nome"] for i in r.json()["itens"]] == ["Combo Casal"]
    assert r.json()["total"] == 1


def test_listar_paginacao_mantem_total(client, admin_headers, marmita_pronta):
    for letra in "ABC":
        _criar(client, admin_headers, _combo([marmita_pronta], nome=f"Combo {letra}"))

    pagina1 = client.get(f"{URL}?limite=2", headers=admin_headers).json()
    pagina2 = client.get(f"{URL}?limite=2&deslocamento=2", headers=admin_headers).json()

    assert pagina1["total"] == 3 and len(pagina1["itens"]) == 2
    assert pagina2["total"] == 3 and len(pagina2["itens"]) == 1


@pytest.mark.parametrize("query", ["limite=0", "limite=101", "deslocamento=-1"])
def test_listar_paginacao_invalida_da_422(client, admin_headers, query):
    assert client.get(f"{URL}?{query}", headers=admin_headers).status_code == 422


# ── atualizar ────────────────────────────────────────────────────────

def test_atualizar_substitui_campos_e_itens(
    client, admin_headers, marmita_pronta, marmita_personalizavel, alimento_arroz, alimento_feijao
):
    criado = _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz]))
    novo = _combo([marmita_personalizavel], [alimento_feijao], nome="Combo Novo", preco="39.90")
    novo["itens_alimento"][0]["quantidade"] = 2

    r = client.put(f"{URL}/{criado['id']}", json=novo, headers=admin_headers)

    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == criado["id"]
    assert d["nome"] == "Combo Novo"
    assert Decimal(d["preco"]) == Decimal("39.90")
    assert [i["marmita_nome"] for i in d["itens_marmita"]] == ["Marmita Personalizável"]
    assert [(i["alimento_nome"], i["quantidade"]) for i in d["itens_alimento"]] == [("Feijão", 2)]


def test_atualizar_removendo_todos_os_itens_de_um_tipo(client, admin_headers, marmita_pronta, alimento_arroz):
    criado = _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz]))

    r = client.put(f"{URL}/{criado['id']}", json=_combo([marmita_pronta]), headers=admin_headers)

    assert r.status_code == 200, r.text
    assert r.json()["itens_alimento"] == []
    assert len(r.json()["itens_marmita"]) == 1


def test_atualizar_com_os_mesmos_itens_nao_viola_unicidade(
    client, admin_headers, marmita_pronta, alimento_arroz
):
    """Regressão: o service limpa e recria os filhos; INSERT antes de DELETE quebraria a UNIQUE."""
    payload = _combo([marmita_pronta], [alimento_arroz])
    criado = _criar(client, admin_headers, payload)

    r = client.put(f"{URL}/{criado['id']}", json=payload, headers=admin_headers)

    assert r.status_code == 200, r.text
    assert len(r.json()["itens_marmita"]) == 1
    assert len(r.json()["itens_alimento"]) == 1


def test_atualizar_invalido_da_422_e_nao_altera(client, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    r = client.put(f"{URL}/{criado['id']}", json=_combo([marmita_pronta], preco="-1"), headers=admin_headers)

    assert r.status_code == 422
    atual = client.get(f"{URL}/{criado['id']}", headers=admin_headers).json()
    assert Decimal(atual["preco"]) == Decimal("49.90")


def test_atualizar_com_referencia_invalida_da_422_e_nao_altera(client, admin_headers, marmita_pronta, marmita_b):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    r = client.put(f"{URL}/{criado['id']}", json=_combo([marmita_b], nome="Outro"), headers=admin_headers)

    assert r.status_code == 422
    atual = client.get(f"{URL}/{criado['id']}", headers=admin_headers).json()
    assert atual["nome"] == "Combo Família"
    assert atual["itens_marmita"][0]["marmita_nome"] == "Marmita Pronta"


def test_atualizar_inexistente_da_404(client, admin_headers, marmita_pronta):
    r = client.put(f"{URL}/{uuid.uuid4()}", json=_combo([marmita_pronta]), headers=admin_headers)

    assert r.status_code == 404


# ── ativar / desativar ───────────────────────────────────────────────

def test_desativar_e_reativar(client, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))
    url = f"{URL}/{criado['id']}/ativo"

    r1 = client.patch(url, json={"ativo": False}, headers=admin_headers)
    r2 = client.patch(url, json={"ativo": True}, headers=admin_headers)

    assert r1.status_code == 200 and r1.json()["ativo"] is False
    assert r2.status_code == 200 and r2.json()["ativo"] is True


def test_ativo_ausente_no_patch_da_422(client, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    assert client.patch(f"{URL}/{criado['id']}/ativo", json={}, headers=admin_headers).status_code == 422


def test_patch_ativo_inexistente_da_404(client, admin_headers):
    r = client.patch(f"{URL}/{uuid.uuid4()}/ativo", json={"ativo": False}, headers=admin_headers)

    assert r.status_code == 404


# ── excluir ──────────────────────────────────────────────────────────

def test_excluir_combo(client, admin_headers, marmita_pronta):
    criado = _criar(client, admin_headers, _combo([marmita_pronta]))

    r = client.delete(f"{URL}/{criado['id']}", headers=admin_headers)

    assert r.status_code == 204
    assert client.get(f"{URL}/{criado['id']}", headers=admin_headers).status_code == 404


def test_excluir_combo_preserva_marmita_e_alimento(client, admin_headers, marmita_pronta, alimento_arroz):
    criado = _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz]))

    assert client.delete(f"{URL}/{criado['id']}", headers=admin_headers).status_code == 204

    # ambos continuam existindo e podem compor outro combo
    _criar(client, admin_headers, _combo([marmita_pronta], [alimento_arroz], nome="Combo Novo"))


def test_excluir_inexistente_da_404(client, admin_headers):
    assert client.delete(f"{URL}/{uuid.uuid4()}", headers=admin_headers).status_code == 404
