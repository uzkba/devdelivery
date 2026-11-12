import uuid
import pytest
from decimal import Decimal

from app.model.models import Food, FoodCategory


@pytest.fixture()
def categoria(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


@pytest.fixture()
def categoria_b(db, outro_restaurante):
    c = FoodCategory(restaurant_id=outro_restaurante.id, name="Bebidas", display_order=0)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def criar_alimento_direto(db, categoria, **overrides):
    dados = dict(
        restaurant_id=categoria.restaurant_id,
        composition_category_id=categoria.id,
        name="Item",
        description=None,
        is_active=True,
    )
    dados.update(overrides)
    f = Food(**dados)
    db.add(f)
    db.flush()
    db.refresh(f)
    return f


def auth(user, token_para):
    return {"Authorization": f"Bearer {token_para(user)}"}


def test_criar_alimento_sucesso(client, categoria, admin_user, token_para):
    payload = {
        "nome": "Marmita Fitness",
        "descricao": "Frango grelhado com legumes",
        "categoria_id": str(categoria.id),
    }
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Marmita Fitness"
    assert data["categoria_id"] == str(categoria.id)
    assert "preco_base" not in data
    assert "disponivel" not in data
    assert "grupos_complemento" not in data


def test_criar_alimento_role_nao_admin_e_bloqueado(client, categoria, atendente_user, token_para):
    payload = {"nome": "Item", "descricao": None, "categoria_id": str(categoria.id)}
    resp = client.post("/alimentos", json=payload, headers=auth(atendente_user, token_para))

    assert resp.status_code == 403


def test_criar_alimento_com_categoria_de_outro_restaurante_da_404(
    client, categoria_b, admin_user, token_para
):
    payload = {"nome": "Suco", "descricao": None, "categoria_id": str(categoria_b.id)}
    resp = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert resp.status_code == 404


def test_criar_alimento_sem_autenticacao_e_rejeitado(client, categoria):
    payload = {"nome": "Item", "descricao": None, "categoria_id": str(categoria.id)}
    resp = client.post("/alimentos", json=payload)

    assert resp.status_code == 401


def test_listar_esconde_inativos_por_padrao(client, db, categoria, admin_user, token_para):
    ativo = criar_alimento_direto(db, categoria, name="Ativo")
    inativo = criar_alimento_direto(db, categoria, name="Inativo", is_active=False)

    resp = client.get("/alimentos", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(ativo.id) in ids
    assert str(inativo.id) not in ids


def test_listar_incluir_inativos_true_traz_tudo(client, db, categoria, admin_user, token_para):
    ativo = criar_alimento_direto(db, categoria, name="Ativo")
    inativo = criar_alimento_direto(db, categoria, name="Inativo", is_active=False)

    resp = client.get("/alimentos?incluir_inativos=true", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(ativo.id) in ids
    assert str(inativo.id) in ids


def test_listar_filtra_por_categoria(client, db, categoria, restaurante, admin_user, token_para):
    outra = FoodCategory(restaurant_id=restaurante.id, name="Sobremesas", display_order=1)
    db.add(outra)
    db.flush()
    db.refresh(outra)

    da_categoria = criar_alimento_direto(db, categoria, name="Prato")
    de_outra = criar_alimento_direto(db, outra, name="Doce")

    resp = client.get(f"/alimentos?categoria_id={categoria.id}", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(da_categoria.id) in ids
    assert str(de_outra.id) not in ids


def test_listar_nao_traz_alimento_de_outro_restaurante(
    client, db, categoria, categoria_b, admin_user, token_para
):
    da_a = criar_alimento_direto(db, categoria, name="Do A")
    da_b = criar_alimento_direto(db, categoria_b, name="Do B")

    resp = client.get("/alimentos", headers=auth(admin_user, token_para))

    ids = {i["id"] for i in resp.json()}
    assert str(da_a.id) in ids
    assert str(da_b.id) not in ids


def test_detalhar_alimento_de_outro_restaurante_da_404(client, db, categoria_b, admin_user, token_para):
    alimento_de_b = criar_alimento_direto(db, categoria_b, name="Não é seu")

    resp = client.get(f"/alimentos/{alimento_de_b.id}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404


def test_detalhar_alimento_inexistente_da_404(client, admin_user, token_para):
    resp = client.get(f"/alimentos/{uuid.uuid4()}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404


def test_atualizar_alimento_sucesso(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Nome Antigo")

    resp = client.put(
        f"/alimentos/{alimento.id}",
        json={"nome": "Nome Novo", "descricao": "Descrição nova"},
        headers=auth(admin_user, token_para),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nome"] == "Nome Novo"
    assert data["descricao"] == "Descrição nova"


def test_atualizar_categoria_de_outro_restaurante_da_404(
    client, db, categoria, categoria_b, admin_user, token_para
):
    alimento = criar_alimento_direto(db, categoria, name="Item")

    resp = client.put(
        f"/alimentos/{alimento.id}",
        json={"categoria_id": str(categoria_b.id)},
        headers=auth(admin_user, token_para),
    )

    assert resp.status_code == 404


def test_atualizar_nome_null_preserva_o_nome(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Nome Original")

    r = client.put(f"/alimentos/{alimento.id}", json={"nome": None}, headers=auth(admin_user, token_para))

    assert r.status_code == 200
    assert r.json()["nome"] == "Nome Original"


def test_atualizar_nome_null_junto_com_outro_campo_aplica_so_o_outro(
    client, db, categoria, admin_user, token_para
):
    alimento = criar_alimento_direto(db, categoria, name="Nome Original")

    r = client.put(
        f"/alimentos/{alimento.id}",
        json={"nome": None, "descricao": "Outra descrição"},
        headers=auth(admin_user, token_para),
    )

    assert r.status_code == 200
    d = r.json()
    assert d["nome"] == "Nome Original"
    assert d["descricao"] == "Outra descrição"


def test_atualizar_vendavel_avulso_null_preserva_o_estado(
    client, categoria, categoria_venda, admin_user, token_para
):
    h = auth(admin_user, token_para)
    criado = client.post(
        "/alimentos", json=_payload_avulso(categoria_venda, categoria_id=str(categoria.id)), headers=h
    )
    assert criado.status_code == 201

    r = client.put(f"/alimentos/{criado.json()['id']}", json={"vendavel_avulso": None}, headers=h)

    assert r.status_code == 200
    d = r.json()
    assert d["vendavel_avulso"] is True
    assert Decimal(d["preco_avulso"]) == Decimal("32.90")
    assert d["categoria_venda_id"] == str(categoria_venda.id)


def test_deletar_alimento_e_soft_delete(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Item", is_active=True)

    resp = client.delete(f"/alimentos/{alimento.id}", headers=auth(admin_user, token_para))
    assert resp.status_code == 204

    db.refresh(alimento)
    assert alimento.is_active is False
    assert db.get(Food, alimento.id) is not None


def test_deletar_alimento_de_outro_restaurante_da_404(client, db, categoria_b, admin_user, token_para):
    alimento_de_b = criar_alimento_direto(db, categoria_b, name="Não é seu")

    resp = client.delete(f"/alimentos/{alimento_de_b.id}", headers=auth(admin_user, token_para))

    assert resp.status_code == 404


# ── Produto avulso (Fase 2) ──────────────────────────────────────

@pytest.fixture()
def categoria_venda(db, restaurante):
    c = FoodCategory(restaurant_id=restaurante.id, name="Pratos do dia", display_order=0, type="venda")
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def _payload_avulso(categoria_venda, **extra):
    return {
        "nome": "Feijoada",
        "vendavel_avulso": True,
        "preco_avulso": "32.90",
        "categoria_venda_id": str(categoria_venda.id),
        **extra,
    }


def test_criar_avulso_puro_sem_categoria_de_composicao(client, categoria_venda, admin_user, token_para):
    r = client.post("/alimentos", json=_payload_avulso(categoria_venda), headers=auth(admin_user, token_para))

    assert r.status_code == 201
    d = r.json()
    assert d["vendavel_avulso"] is True
    assert d["categoria_id"] is None
    assert d["categoria_venda_id"] == str(categoria_venda.id)
    assert Decimal(d["preco_avulso"]) == Decimal("32.90")
    assert d["destaque"] is False


def test_criar_alimento_dupla_natureza(client, categoria, categoria_venda, admin_user, token_para):
    payload = _payload_avulso(categoria_venda, nome="Farofa", categoria_id=str(categoria.id), destaque=True)

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 201
    d = r.json()
    assert d["categoria_id"] == str(categoria.id)
    assert d["categoria_venda_id"] == str(categoria_venda.id)
    assert d["destaque"] is True


def test_avulso_sem_preco_da_422(client, categoria_venda, admin_user, token_para):
    payload = _payload_avulso(categoria_venda)
    del payload["preco_avulso"]

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_avulso_sem_categoria_de_venda_da_422(client, categoria, admin_user, token_para):
    payload = {"nome": "X", "vendavel_avulso": True, "preco_avulso": "10", "categoria_id": str(categoria.id)}

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_preco_avulso_com_vendavel_false_da_422(client, categoria, admin_user, token_para):
    payload = {"nome": "X", "categoria_id": str(categoria.id), "preco_avulso": "10"}

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_sem_nenhuma_categoria_da_422(client, admin_user, token_para):
    r = client.post("/alimentos", json={"nome": "Solto"}, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_categoria_venda_com_tipo_composicao_da_422(client, categoria, admin_user, token_para):
    payload = {"nome": "X", "vendavel_avulso": True, "preco_avulso": "10", "categoria_venda_id": str(categoria.id)}

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_categoria_composicao_com_tipo_venda_da_422(client, categoria_venda, admin_user, token_para):
    payload = {"nome": "X", "categoria_id": str(categoria_venda.id)}

    r = client.post("/alimentos", json=payload, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_categoria_venda_de_outro_restaurante_da_404(client, db, outro_restaurante, admin_user, token_para):
    cat_b = FoodCategory(restaurant_id=outro_restaurante.id, name="Venda B", display_order=0, type="venda")
    db.add(cat_b)
    db.flush()

    r = client.post("/alimentos", json=_payload_avulso(cat_b), headers=auth(admin_user, token_para))

    assert r.status_code == 404


def test_atualizar_desligar_avulso_limpa_preco_e_categoria_de_venda(
    client, categoria, categoria_venda, admin_user, token_para
):
    h = auth(admin_user, token_para)
    criado = client.post("/alimentos", json=_payload_avulso(categoria_venda, categoria_id=str(categoria.id)), headers=h)
    assert criado.status_code == 201

    r = client.put(f"/alimentos/{criado.json()['id']}", json={"vendavel_avulso": False}, headers=h)

    assert r.status_code == 200
    d = r.json()
    assert d["vendavel_avulso"] is False
    assert d["preco_avulso"] is None
    assert d["categoria_venda_id"] is None
    assert d["categoria_id"] == str(categoria.id)


def test_atualizar_desligar_avulso_puro_da_422(client, categoria_venda, admin_user, token_para):
    """Avulso puro não tem categoria de composição: desligar deixaria sem nenhuma categoria."""
    h = auth(admin_user, token_para)
    criado = client.post("/alimentos", json=_payload_avulso(categoria_venda), headers=h)

    r = client.put(f"/alimentos/{criado.json()['id']}", json={"vendavel_avulso": False}, headers=h)

    assert r.status_code == 422


def test_atualizar_tornar_avulso_mantem_categoria_legada(client, db, categoria, categoria_venda, admin_user, token_para):
    h = auth(admin_user, token_para)
    alimento = criar_alimento_direto(db, categoria, name="Arroz")

    r = client.put(
        f"/alimentos/{alimento.id}",
        json={"vendavel_avulso": True, "preco_avulso": "8.00", "categoria_venda_id": str(categoria_venda.id)},
        headers=h,
    )

    assert r.status_code == 200
    d = r.json()
    assert d["categoria_id"] == str(categoria.id)
    assert d["categoria_venda_id"] == str(categoria_venda.id)
    assert Decimal(d["preco_avulso"]) == Decimal("8.00")


def test_atualizar_preco_avulso_em_alimento_nao_avulso_da_422(client, db, categoria, admin_user, token_para):
    alimento = criar_alimento_direto(db, categoria, name="Arroz")

    r = client.put(f"/alimentos/{alimento.id}", json={"preco_avulso": "8.00"}, headers=auth(admin_user, token_para))

    assert r.status_code == 422


def test_listar_filtra_vendavel_avulso(client, categoria, categoria_venda, admin_user, token_para):
    h = auth(admin_user, token_para)
    client.post("/alimentos", json=_payload_avulso(categoria_venda), headers=h)
    client.post("/alimentos", json={"nome": "Arroz", "categoria_id": str(categoria.id)}, headers=h)

    r = client.get("/alimentos?vendavel_avulso=true", headers=h)

    assert {i["nome"] for i in r.json()} == {"Feijoada"}


def test_listar_filtra_por_categoria_de_venda(client, db, restaurante, categoria_venda, admin_user, token_para):
    h = auth(admin_user, token_para)
    outra = FoodCategory(restaurant_id=restaurante.id, name="Bebidas", display_order=1, type="venda")
    db.add(outra)
    db.flush()
    client.post("/alimentos", json=_payload_avulso(categoria_venda), headers=h)
    client.post("/alimentos", json=_payload_avulso(outra, nome="Suco", preco_avulso="7.00"), headers=h)

    r = client.get(f"/alimentos?categoria_venda_id={outra.id}", headers=h)

    assert {i["nome"] for i in r.json()} == {"Suco"}


# ===========================================================================
# Campos opcionais do produto avulso + componentes ("O que vem")
# ===========================================================================
URL_ALIMENTOS = "/alimentos"  # ajuste ao prefixo usado no resto do arquivo

CAMPOS_OPCIONAIS = [
    "serve_pessoas", "porcao_quantidade", "porcao_unidade", "tempo_preparo_minutos",
    "calorias_kcal", "proteina_g", "carboidrato_g", "gordura_g",
]
INICIAIS_NUMERICOS = {
    "serve_pessoas": 4,
    "tempo_preparo_minutos": 30,
    "calorias_kcal": 500,
    "proteina_g": "20.5",
    "carboidrato_g": "50.0",
    "gordura_g": "10.5",
}


def _num(valor):
    return Decimal(str(valor))


def _corpo_avulso(cat_venda, **extra):
    corpo = {
        "nome": "Feijoada completa",
        "vendavel_avulso": True,
        "preco_avulso": "39.90",
        "categoria_venda_id": str(cat_venda.id),
    }
    corpo.update(extra)
    return corpo


def _post(client, user, token_para, corpo):
    return client.post(URL_ALIMENTOS, json=corpo, headers=auth(user, token_para))


def _put(client, user, token_para, alimento_id, corpo):
    return client.put(f"{URL_ALIMENTOS}/{alimento_id}", json=corpo, headers=auth(user, token_para))


def _get(client, user, token_para, alimento_id):
    return client.get(f"{URL_ALIMENTOS}/{alimento_id}", headers=auth(user, token_para))


def _criar_ok(client, user, token_para, cat_venda, **extra):
    r = _post(client, user, token_para, _corpo_avulso(cat_venda, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def _criar_completo(client, user, token_para, cat_venda):
    return _criar_ok(
        client, user, token_para, cat_venda,
        porcao_quantidade="350", porcao_unidade="g",
        componentes=[{"nome": "Feijão preto"}, {"nome": "Arroz"}],
        **INICIAIS_NUMERICOS,
    )


# ── criar ────────────────────────────────────────────────────────────────────
def test_criar_com_todos_os_campos_opcionais(client, admin_user, token_para, cat_venda):
    d = _criar_ok(
        client, admin_user, token_para, cat_venda,
        descricao="Feijoada com arroz, couve e farofa",
        serve_pessoas=4,
        porcao_quantidade="1.5", porcao_unidade="kg",
        tempo_preparo_minutos=45,
        calorias_kcal=820, proteina_g="42.5", carboidrato_g="60.0", gordura_g="35.5",
        componentes=[{"nome": "Feijão preto", "descricao": "Com carnes secas"}, {"nome": "Arroz"}],
    )
    assert d["descricao"] == "Feijoada com arroz, couve e farofa"
    assert d["serve_pessoas"] == 4
    assert _num(d["porcao_quantidade"]) == Decimal("1.5")
    assert d["porcao_unidade"] == "kg"
    assert d["tempo_preparo_minutos"] == 45
    assert d["calorias_kcal"] == 820
    assert _num(d["proteina_g"]) == Decimal("42.5")
    assert _num(d["carboidrato_g"]) == Decimal("60.0")
    assert _num(d["gordura_g"]) == Decimal("35.5")
    assert d["componentes"] == [
        {"nome": "Feijão preto", "descricao": "Com carnes secas"},
        {"nome": "Arroz", "descricao": None},
    ]
    # persistiu: a releitura devolve exatamente o mesmo
    g = _get(client, admin_user, token_para, d["id"])
    assert g.status_code == 200
    assert g.json() == d


def test_criar_sem_campos_opcionais_retorna_nulos_e_componentes_vazio(
    client, admin_user, token_para, cat_venda
):
    d = _criar_ok(client, admin_user, token_para, cat_venda)
    for campo in CAMPOS_OPCIONAIS:
        assert d[campo] is None, campo
    assert d["componentes"] == []
    assert d["descricao"] is None


# ── serve_pessoas ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor", [0, 51, -1])
def test_serve_pessoas_fora_do_intervalo(client, admin_user, token_para, cat_venda, valor):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, serve_pessoas=valor))
    assert r.status_code == 422


@pytest.mark.parametrize("valor", [1, 50])
def test_serve_pessoas_nos_limites(client, admin_user, token_para, cat_venda, valor):
    d = _criar_ok(client, admin_user, token_para, cat_venda, serve_pessoas=valor)
    assert d["serve_pessoas"] == valor


# ── porção ───────────────────────────────────────────────────────────────────
def test_porcao_so_com_quantidade_422(client, admin_user, token_para, cat_venda):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, porcao_quantidade="200"))
    assert r.status_code == 422


def test_porcao_so_com_unidade_422(client, admin_user, token_para, cat_venda):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, porcao_unidade="g"))
    assert r.status_code == 422


@pytest.mark.parametrize("unidade", ["mg", "G", "litro", ""])
def test_porcao_unidade_invalida(client, admin_user, token_para, cat_venda, unidade):
    r = _post(
        client, admin_user, token_para,
        _corpo_avulso(cat_venda, porcao_quantidade="200", porcao_unidade=unidade),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("unidade", ["g", "kg", "ml", "l"])
def test_porcao_unidades_validas(client, admin_user, token_para, cat_venda, unidade):
    d = _criar_ok(
        client, admin_user, token_para, cat_venda, porcao_quantidade="200", porcao_unidade=unidade
    )
    assert d["porcao_unidade"] == unidade
    assert _num(d["porcao_quantidade"]) == Decimal("200")


@pytest.mark.parametrize("quantidade", [0, -1, "-0.5"])
def test_porcao_quantidade_deve_ser_positiva(client, admin_user, token_para, cat_venda, quantidade):
    r = _post(
        client, admin_user, token_para,
        _corpo_avulso(cat_venda, porcao_quantidade=quantidade, porcao_unidade="g"),
    )
    assert r.status_code == 422


# ── tempo de preparo ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor", [0, 481, -5])
def test_tempo_preparo_fora_do_limite(client, admin_user, token_para, cat_venda, valor):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, tempo_preparo_minutos=valor))
    assert r.status_code == 422


@pytest.mark.parametrize("valor", [1, 480])
def test_tempo_preparo_nos_limites(client, admin_user, token_para, cat_venda, valor):
    d = _criar_ok(client, admin_user, token_para, cat_venda, tempo_preparo_minutos=valor)
    assert d["tempo_preparo_minutos"] == valor


# ── nutrição ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "campo,valor",
    [
        ("calorias_kcal", -1),
        ("calorias_kcal", 10001),
        ("proteina_g", "-0.1"),
        ("carboidrato_g", "-1"),
        ("gordura_g", "-2.5"),
    ],
)
def test_nutricao_invalida_422(client, admin_user, token_para, cat_venda, campo, valor):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, **{campo: valor}))
    assert r.status_code == 422


def test_nutricao_parcial_e_valida(client, admin_user, token_para, cat_venda):
    d = _criar_ok(client, admin_user, token_para, cat_venda, calorias_kcal=300, proteina_g="12.5")
    assert d["calorias_kcal"] == 300
    assert _num(d["proteina_g"]) == Decimal("12.5")
    assert d["carboidrato_g"] is None
    assert d["gordura_g"] is None


def test_nutricao_toda_nula_explicita(client, admin_user, token_para, cat_venda):
    d = _criar_ok(
        client, admin_user, token_para, cat_venda,
        calorias_kcal=None, proteina_g=None, carboidrato_g=None, gordura_g=None,
    )
    assert d["calorias_kcal"] is None
    assert d["proteina_g"] is None
    assert d["carboidrato_g"] is None
    assert d["gordura_g"] is None


# ── descricao (limite de 300) ────────────────────────────────────────────────
def test_descricao_no_limite_de_300_e_aceita(client, admin_user, token_para, cat_venda):
    d = _criar_ok(client, admin_user, token_para, cat_venda, descricao="x" * 300)
    assert len(d["descricao"]) == 300


def test_descricao_acima_de_300_422_no_post_e_no_put(client, admin_user, token_para, cat_venda):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, descricao="x" * 301))
    assert r.status_code == 422
    criado = _criar_ok(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"descricao": "x" * 301})
    assert r.status_code == 422


# ── componentes: criar ───────────────────────────────────────────────────────
def test_componentes_criar_preserva_ordem(client, admin_user, token_para, cat_venda):
    nomes = ["Zebra", "Abacate", "Manga"]
    d = _criar_ok(
        client, admin_user, token_para, cat_venda, componentes=[{"nome": n} for n in nomes]
    )
    assert [c["nome"] for c in d["componentes"]] == nomes
    g = _get(client, admin_user, token_para, d["id"]).json()
    assert [c["nome"] for c in g["componentes"]] == nomes


def test_componentes_maximo_de_10(client, admin_user, token_para, cat_venda):
    dez = [{"nome": f"Item {i:02d}"} for i in range(10)]
    d = _criar_ok(client, admin_user, token_para, cat_venda, componentes=dez)
    assert len(d["componentes"]) == 10
    r = _post(
        client, admin_user, token_para,
        _corpo_avulso(cat_venda, componentes=dez + [{"nome": "Item 11"}]),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("nome", ["a", "", "   "])
def test_componente_nome_curto_422(client, admin_user, token_para, cat_venda, nome):
    r = _post(client, admin_user, token_para, _corpo_avulso(cat_venda, componentes=[{"nome": nome}]))
    assert r.status_code == 422


def test_componente_nome_acima_de_120_422(client, admin_user, token_para, cat_venda):
    r = _post(
        client, admin_user, token_para,
        _corpo_avulso(cat_venda, componentes=[{"nome": "x" * 121}]),
    )
    assert r.status_code == 422


def test_componente_descricao_acima_de_300_422(client, admin_user, token_para, cat_venda):
    r = _post(
        client, admin_user, token_para,
        _corpo_avulso(cat_venda, componentes=[{"nome": "Arroz", "descricao": "x" * 301}]),
    )
    assert r.status_code == 422


def test_componente_descricao_vazia_vira_nulo(client, admin_user, token_para, cat_venda):
    d = _criar_ok(
        client, admin_user, token_para, cat_venda,
        componentes=[{"nome": "Arroz", "descricao": "   "}],
    )
    assert d["componentes"] == [{"nome": "Arroz", "descricao": None}]


# ── componentes: PUT ─────────────────────────────────────────────────────────
def test_put_substitui_componentes_por_inteiro(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(
        client, admin_user, token_para, cat_venda,
        componentes=[{"nome": "Um"}, {"nome": "Dois"}, {"nome": "Três"}],
    )
    r = _put(
        client, admin_user, token_para, criado["id"],
        {"componentes": [{"nome": "Novo", "descricao": "só este"}]},
    )
    assert r.status_code == 200, r.text
    esperado = [{"nome": "Novo", "descricao": "só este"}]
    assert r.json()["componentes"] == esperado
    assert _get(client, admin_user, token_para, criado["id"]).json()["componentes"] == esperado


def test_put_sem_componentes_preserva_a_lista(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(
        client, admin_user, token_para, cat_venda,
        componentes=[{"nome": "Um"}, {"nome": "Dois"}],
    )
    r = _put(client, admin_user, token_para, criado["id"], {"destaque": True})
    assert r.status_code == 200, r.text
    assert [c["nome"] for c in r.json()["componentes"]] == ["Um", "Dois"]


def test_put_lista_vazia_limpa_componentes(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(
        client, admin_user, token_para, cat_venda, componentes=[{"nome": "Um"}, {"nome": "Dois"}]
    )
    r = _put(client, admin_user, token_para, criado["id"], {"componentes": []})
    assert r.status_code == 200, r.text
    assert r.json()["componentes"] == []
    assert _get(client, admin_user, token_para, criado["id"]).json()["componentes"] == []


def test_put_componentes_null_422_e_preserva(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(client, admin_user, token_para, cat_venda, componentes=[{"nome": "Um"}])
    r = _put(client, admin_user, token_para, criado["id"], {"componentes": None})
    assert r.status_code == 422
    assert len(_get(client, admin_user, token_para, criado["id"]).json()["componentes"]) == 1


def test_put_com_mais_de_10_componentes_422_e_preserva(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(client, admin_user, token_para, cat_venda, componentes=[{"nome": "Um"}])
    onze = [{"nome": f"Item {i:02d}"} for i in range(11)]
    r = _put(client, admin_user, token_para, criado["id"], {"componentes": onze})
    assert r.status_code == 422
    assert [c["nome"] for c in _get(client, admin_user, token_para, criado["id"]).json()["componentes"]] == ["Um"]


def test_put_preserva_a_ordem_enviada(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(
        client, admin_user, token_para, cat_venda, componentes=[{"nome": "A1"}, {"nome": "B2"}]
    )
    nova = ["Zeta", "Alfa", "Mu"]
    r = _put(
        client, admin_user, token_para, criado["id"],
        {"componentes": [{"nome": n} for n in nova]},
    )
    assert [c["nome"] for c in r.json()["componentes"]] == nova


# ── PUT: campos novos, estado final e null ───────────────────────────────────
def test_put_muda_so_um_campo_novo_mantem_regras_de_avulso(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(client, admin_user, token_para, cat_venda, serve_pessoas=2, tempo_preparo_minutos=20)
    r = _put(client, admin_user, token_para, criado["id"], {"calorias_kcal": 300})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["calorias_kcal"] == 300
    assert d["serve_pessoas"] == 2
    assert d["tempo_preparo_minutos"] == 20
    assert d["vendavel_avulso"] is True
    assert _num(d["preco_avulso"]) == Decimal("39.90")
    assert d["categoria_venda_id"] == str(cat_venda.id)


def test_put_desligar_avulso_com_campo_novo_continua_422(client, admin_user, token_para, cat_venda):
    # só tem categoria de venda: desligar o avulso deixa o alimento sem categoria
    criado = _criar_ok(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"vendavel_avulso": False, "serve_pessoas": 3})
    assert r.status_code == 422
    assert _get(client, admin_user, token_para, criado["id"]).json()["serve_pessoas"] is None


@pytest.mark.parametrize("campo", list(INICIAIS_NUMERICOS))
def test_put_null_limpa_o_campo_e_preserva_os_demais(client, admin_user, token_para, cat_venda, campo):
    criado = _criar_completo(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {campo: None})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d[campo] is None
    for outro, inicial in INICIAIS_NUMERICOS.items():
        if outro != campo:
            assert _num(d[outro]) == _num(inicial), outro
    assert len(d["componentes"]) == 2


def test_put_null_nos_dois_campos_da_porcao_limpa(client, admin_user, token_para, cat_venda):
    criado = _criar_completo(client, admin_user, token_para, cat_venda)
    r = _put(
        client, admin_user, token_para, criado["id"],
        {"porcao_quantidade": None, "porcao_unidade": None},
    )
    assert r.status_code == 200, r.text
    assert r.json()["porcao_quantidade"] is None
    assert r.json()["porcao_unidade"] is None


def test_put_null_so_na_quantidade_da_porcao_422(client, admin_user, token_para, cat_venda):
    criado = _criar_completo(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"porcao_quantidade": None})
    assert r.status_code == 422
    g = _get(client, admin_user, token_para, criado["id"]).json()
    assert _num(g["porcao_quantidade"]) == Decimal("350")
    assert g["porcao_unidade"] == "g"


def test_put_so_quantidade_sem_porcao_previa_422(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"porcao_quantidade": "100"})
    assert r.status_code == 422


def test_put_so_unidade_sem_porcao_previa_422(client, admin_user, token_para, cat_venda):
    criado = _criar_ok(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"porcao_unidade": "kg"})
    assert r.status_code == 422


def test_put_muda_so_a_unidade_com_porcao_existente(client, admin_user, token_para, cat_venda):
    criado = _criar_completo(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"porcao_unidade": "kg"})
    assert r.status_code == 200, r.text
    assert r.json()["porcao_unidade"] == "kg"
    assert _num(r.json()["porcao_quantidade"]) == Decimal("350")


def test_put_quantidade_da_porcao_zero_422(client, admin_user, token_para, cat_venda):
    criado = _criar_completo(client, admin_user, token_para, cat_venda)
    r = _put(client, admin_user, token_para, criado["id"], {"porcao_quantidade": 0})
    assert r.status_code == 422


# ── saída: detalhe e listagem ────────────────────────────────────────────────
def test_listagem_expoe_campos_novos_e_componentes(client, admin_user, token_para, cat_venda):
    com = _criar_completo(client, admin_user, token_para, cat_venda)
    sem = _criar_ok(client, admin_user, token_para, cat_venda, nome="Sem extras")
    r = client.get(URL_ALIMENTOS, headers=auth(admin_user, token_para))
    assert r.status_code == 200
    por_id = {a["id"]: a for a in r.json()}
    assert [c["nome"] for c in por_id[com["id"]]["componentes"]] == ["Feijão preto", "Arroz"]
    assert por_id[com["id"]]["serve_pessoas"] == 4
    assert por_id[sem["id"]]["componentes"] == []
    for campo in CAMPOS_OPCIONAIS:
        assert por_id[sem["id"]][campo] is None, campo


# ── isolamento entre restaurantes ────────────────────────────────────────────
def test_isolamento_entre_restaurantes_com_campos_novos(
    client, admin_user, outro_admin_user, token_para, cat_venda, cat_composicao_b
):
    do_a = _criar_ok(
        client, admin_user, token_para, cat_venda, serve_pessoas=2, componentes=[{"nome": "Arroz"}]
    )
    rb = _post(
        client, outro_admin_user, token_para,
        {"nome": "Arroz do B", "categoria_id": str(cat_composicao_b.id), "componentes": [{"nome": "Item B"}]},
    )
    assert rb.status_code == 201, rb.text
    do_b = rb.json()

    # B não enxerga nem altera o alimento de A (404)
    assert _get(client, outro_admin_user, token_para, do_a["id"]).status_code == 404
    r = _put(client, outro_admin_user, token_para, do_a["id"], {"serve_pessoas": 9, "componentes": []})
    assert r.status_code == 404

    # A segue intacto
    a = _get(client, admin_user, token_para, do_a["id"]).json()
    assert a["serve_pessoas"] == 2
    assert [c["nome"] for c in a["componentes"]] == ["Arroz"]

    # e vice-versa
    assert _get(client, admin_user, token_para, do_b["id"]).status_code == 404

    # listagens separadas
    ids_a = {x["id"] for x in client.get(URL_ALIMENTOS, headers=auth(admin_user, token_para)).json()}
    assert do_a["id"] in ids_a
    assert do_b["id"] not in ids_a