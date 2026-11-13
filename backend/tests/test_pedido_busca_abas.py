from types import SimpleNamespace

import pytest

from app.services import pedido_fluxo as fluxo

CODIGOS = [
    "CRIADO", "CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA",
    "ENTREGUE", "RETIRADO", "CANCELADO", "RECUSADO",
]


def _listar(client, headers, **params):
    resposta = client.get("/pedidos", params=params, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _codigos(corpo):
    return [item["status"]["codigo"] for item in corpo["items"]]


def _ids(corpo):
    return {item["id"] for item in corpo["items"]}


@pytest.fixture()
def um_de_cada_status(novo_pedido):
    return {codigo: novo_pedido(codigo) for codigo in CODIGOS}


@pytest.fixture()
def de_dois_clientes(novo_pedido, outro_cliente):
    return SimpleNamespace(
        jose=novo_pedido("CRIADO"),
        ana_nova=novo_pedido("CRIADO", client_id=outro_cliente.id),
        ana_entregue=novo_pedido("ENTREGUE", client_id=outro_cliente.id),
    )


def test_toda_etapa_do_fluxo_cai_em_exatamente_uma_aba():
    for codigo in fluxo.TODOS:
        assert sum(codigo in codigos for codigos in fluxo.ABAS.values()) == 1


def test_sem_filtros_lista_tudo_do_mais_antigo_e_traz_as_contagens(
    client, admin_headers, um_de_cada_status
):
    corpo = _listar(client, admin_headers)

    assert corpo["total"] == 9
    assert _codigos(corpo) == CODIGOS
    assert corpo["abas"] == {"novos": 1, "em_andamento": 4, "finalizados": 4}


@pytest.mark.parametrize(
    "aba, esperados",
    [
        ("novos", ["CRIADO"]),
        ("em_andamento", ["CONFIRMADO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA"]),
        ("finalizados", ["RECUSADO", "CANCELADO", "RETIRADO", "ENTREGUE"]),
    ],
)
def test_aba_filtra_pelas_etapas(client, admin_headers, um_de_cada_status, aba, esperados):
    corpo = _listar(client, admin_headers, aba=aba)

    assert _codigos(corpo) == esperados
    assert corpo["total"] == len(esperados)


def test_contagens_ignoram_a_aba_escolhida(client, admin_headers, um_de_cada_status):
    corpo = _listar(client, admin_headers, aba="novos")

    assert corpo["abas"] == {"novos": 1, "em_andamento": 4, "finalizados": 4}


def test_contagens_respeitam_a_busca(client, admin_headers, de_dois_clientes):
    corpo = _listar(client, admin_headers, q="ana", aba="novos")

    assert _ids(corpo) == {str(de_dois_clientes.ana_nova.id)}
    assert corpo["abas"] == {"novos": 1, "em_andamento": 0, "finalizados": 1}


@pytest.mark.parametrize("termo", ["ana", "ANA", "souza", "a sou"])
def test_busca_por_nome_ignora_caixa_e_acha_trecho(client, admin_headers, de_dois_clientes, termo):
    corpo = _listar(client, admin_headers, q=termo)

    assert _ids(corpo) == {
        str(de_dois_clientes.ana_nova.id),
        str(de_dois_clientes.ana_entregue.id),
    }


def test_busca_por_numero_do_pedido(client, admin_headers, de_dois_clientes):
    numero = de_dois_clientes.jose.order_number

    simples = _listar(client, admin_headers, q=str(numero))
    com_cerquilha = _listar(client, admin_headers, q=f"#{numero}")

    assert _ids(simples) == {str(de_dois_clientes.jose.id)}
    assert _ids(com_cerquilha) == {str(de_dois_clientes.jose.id)}


@pytest.mark.parametrize("termo", ["%", "_", "\\", "a%a"])
def test_curingas_sao_tratados_como_texto(client, admin_headers, de_dois_clientes, termo):
    assert _listar(client, admin_headers, q=termo)["total"] == 0


@pytest.mark.parametrize("termo", ["99999999999999999999", "²", "٣"])
def test_numero_absurdo_ou_digito_estranho_nao_quebra(
    client, admin_headers, de_dois_clientes, termo
):
    assert _listar(client, admin_headers, q=termo)["total"] == 0


@pytest.mark.parametrize("termo", ["", "   "])
def test_busca_em_branco_nao_filtra(client, admin_headers, de_dois_clientes, termo):
    assert _listar(client, admin_headers, q=termo)["total"] == 3


def test_paginacao_mantem_total_e_contagens_do_filtro(client, admin_headers, um_de_cada_status):
    corpo = _listar(client, admin_headers, aba="em_andamento", page=2, page_size=3)

    assert corpo["total"] == 4
    assert corpo["total_pages"] == 2
    assert _codigos(corpo) == ["SAIU_PARA_ENTREGA"]
    assert corpo["abas"] == {"novos": 1, "em_andamento": 4, "finalizados": 4}


def test_isolamento_entre_restaurantes(
    client, admin_headers, outro_admin_headers, novo_pedido, outro_restaurante
):
    novo_pedido("CRIADO", restaurant_id=outro_restaurante.id)

    meu = _listar(client, admin_headers)
    do_outro = _listar(client, outro_admin_headers)

    assert meu["total"] == 0
    assert meu["abas"] == {"novos": 0, "em_andamento": 0, "finalizados": 0}
    assert do_outro["total"] == 1
    assert do_outro["abas"]["novos"] == 1


@pytest.mark.parametrize("params", [{"aba": "todos"}, {"q": "x" * 101}, {"page": 0}])
def test_parametros_invalidos_dao_422(client, admin_headers, params):
    assert client.get("/pedidos", params=params, headers=admin_headers).status_code == 422