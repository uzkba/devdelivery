import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.model.models import Order, OrderItem
from app.services.pedir_de_novo_service import MOTIVO_GENERICO, reconstruir_item
from tests.helpers_pedido import (
    config_entrega,
    corpo_pedido,
    criar_combo,
    criar_personalizavel,
    criar_pronta,
    item_avulso,
    item_combo,
    item_marmita,
    selecao,
)


@pytest.fixture()
def catalogo(
    db,
    restaurante,
    cat_composicao,
    cat_composicao_2,
    alimento_arroz,
    alimento_feijao,
    alimento_so_venda,
    alimento_bebida,
):
    config_entrega(db, restaurante)
    pronta = criar_pronta(db, restaurante, [(alimento_arroz, 1), (alimento_feijao, 1)])
    personalizavel = criar_personalizavel(
        db, restaurante, [(cat_composicao, 1), (cat_composicao_2, 1)]
    )
    combo = criar_combo(db, restaurante, [(personalizavel, 1)], [(alimento_bebida, 1)])
    return SimpleNamespace(
        cat_carnes=cat_composicao,
        cat_acomp=cat_composicao_2,
        arroz=alimento_arroz,
        feijao=alimento_feijao,
        feijoada=alimento_so_venda,
        bebida=alimento_bebida,
        pronta=pronta,
        personalizavel=personalizavel,
        combo=combo,
    )


def _escolhas(c):
    return [selecao(c.cat_carnes, (c.arroz, 1)), selecao(c.cat_acomp, (c.feijao, 1))]


def _todos_os_itens(c):
    return [
        item_avulso(c.feijoada, 2, observacao="sem pimenta"),
        item_marmita(c.pronta),
        item_marmita(c.personalizavel, selecoes=_escolhas(c)),
        item_combo(c.combo, marmitas=[(c.personalizavel, _escolhas(c))]),
    ]


def _headers(token_para_cliente, cliente):
    return {"Authorization": f"Bearer {token_para_cliente(cliente)}"}


def _pedir(client, headers, restaurante, itens):
    resposta = client.post(
        "/pedidos",
        json=corpo_pedido(restaurante, itens, tipo_atendimento="RETIRADA"),
        headers=headers,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _repetir(client, headers, pedido):
    return client.get(f"/pedidos/cliente/{pedido['id']}/repetir", headers=headers)


def test_repete_os_quatro_tipos_e_o_resultado_vira_um_pedido_igual(
    client, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(client, headers, restaurante, _todos_os_itens(catalogo))

    resposta = _repetir(client, headers, pedido)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["restaurante_slug"] == restaurante.slug
    assert corpo["tipo_atendimento"] == "RETIRADA"
    assert corpo["indisponiveis"] == []
    assert sorted(i["item"]["tipo"] for i in corpo["itens"]) == [
        "AVULSO", "COMBO", "MARMITA", "MARMITA",
    ]
    assert not any(i["preco_mudou"] for i in corpo["itens"])
    assert Decimal(corpo["valor_itens"]) == Decimal(pedido["valor_itens"])

    segundo = _pedir(client, headers, restaurante, [i["item"] for i in corpo["itens"]])

    assert segundo["id"] != pedido["id"]
    assert Decimal(segundo["valor_itens"]) == Decimal(pedido["valor_itens"])


def test_mantem_quantidade_e_observacao(client, catalogo, restaurante, cliente, token_para_cliente):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(
        client, headers, restaurante, [item_avulso(catalogo.feijoada, 2, observacao="sem pimenta")]
    )

    corpo = _repetir(client, headers, pedido).json()

    item = corpo["itens"][0]
    assert item["quantidade"] == 2
    assert item["item"]["observacao"] == "sem pimenta"
    assert item["item"]["alimento_id"] == str(catalogo.feijoada.id)


def test_preco_novo_vem_do_cadastro_e_o_pedido_antigo_nao_muda(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(client, headers, restaurante, [item_avulso(catalogo.feijoada, 2)])
    catalogo.feijoada.standalone_price = Decimal("35.00")
    db.flush()

    corpo = _repetir(client, headers, pedido).json()

    item = corpo["itens"][0]
    assert Decimal(item["preco_unitario"]) == Decimal("35.00")
    assert Decimal(item["preco_anterior"]) == Decimal("32.90")
    assert item["preco_mudou"] is True
    assert Decimal(item["subtotal"]) == Decimal("70.00")
    assert Decimal(corpo["valor_itens"]) == Decimal("70.00")
    antigo = client.get(f"/pedidos/cliente/{pedido['id']}", headers=headers).json()
    assert Decimal(antigo["itens"][0]["preco_unitario"]) == Decimal("32.90")


def test_item_indisponivel_nao_derruba_os_outros(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(
        client, headers, restaurante, [item_avulso(catalogo.feijoada), item_marmita(catalogo.pronta)]
    )
    catalogo.feijoada.is_active = False
    db.flush()

    corpo = _repetir(client, headers, pedido).json()

    assert [i["item"]["tipo"] for i in corpo["itens"]] == ["MARMITA"]
    assert len(corpo["indisponiveis"]) == 1
    assert corpo["indisponiveis"][0]["nome"] == "Feijoada"
    assert "indisponível" in corpo["indisponiveis"][0]["motivo"]


def test_alimento_escolhido_na_personalizavel_ficou_indisponivel(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(
        client,
        headers,
        restaurante,
        [item_marmita(catalogo.personalizavel, selecoes=_escolhas(catalogo))],
    )
    catalogo.arroz.is_active = False
    db.flush()

    corpo = _repetir(client, headers, pedido).json()

    assert corpo["itens"] == []
    assert Decimal(corpo["valor_itens"]) == Decimal("0.00")
    assert len(corpo["indisponiveis"]) == 1
    assert "Arroz" in corpo["indisponiveis"][0]["motivo"]


def test_combo_com_componente_desativado_fica_indisponivel(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(
        client,
        headers,
        restaurante,
        [item_combo(catalogo.combo, marmitas=[(catalogo.personalizavel, _escolhas(catalogo))])],
    )
    catalogo.bebida.is_active = False
    db.flush()

    corpo = _repetir(client, headers, pedido).json()

    assert corpo["itens"] == []
    assert corpo["indisponiveis"][0]["nome"] == "Combo Almoço"
    assert "indisponível" in corpo["indisponiveis"][0]["motivo"]


def test_item_sem_referencia_ao_cardapio_usa_o_motivo_generico(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(client, headers, restaurante, [item_avulso(catalogo.feijoada)])
    db.get(Order, uuid.UUID(pedido["id"])).items[0].food_id = None
    db.flush()

    corpo = _repetir(client, headers, pedido).json()

    assert corpo["itens"] == []
    assert corpo["indisponiveis"] == [{"nome": "Feijoada", "motivo": MOTIVO_GENERICO}]


def test_repetir_nao_cria_pedido(db, client, catalogo, restaurante, cliente, token_para_cliente):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(client, headers, restaurante, _todos_os_itens(catalogo))
    antes = db.query(Order).count()

    _repetir(client, headers, pedido)

    assert db.query(Order).count() == antes


def test_pedido_de_outro_cliente_da_404(
    client, catalogo, restaurante, cliente, outro_cliente, token_para_cliente
):
    pedido = _pedir(
        client,
        _headers(token_para_cliente, cliente),
        restaurante,
        [item_avulso(catalogo.feijoada)],
    )

    resposta = _repetir(client, _headers(token_para_cliente, outro_cliente), pedido)

    assert resposta.status_code == 404


def test_pedido_inexistente_da_404(client, cliente, token_para_cliente):
    resposta = client.get(
        f"/pedidos/cliente/{uuid.uuid4()}/repetir", headers=_headers(token_para_cliente, cliente)
    )

    assert resposta.status_code == 404


def test_exige_login_de_cliente(client, admin_headers):
    caminho = f"/pedidos/cliente/{uuid.uuid4()}/repetir"

    assert client.get(caminho).status_code in (401, 403)
    assert client.get(caminho, headers=admin_headers).status_code in (401, 403)


def test_restaurante_inativo_da_404(
    client, db, catalogo, restaurante, cliente, token_para_cliente
):
    headers = _headers(token_para_cliente, cliente)
    pedido = _pedir(client, headers, restaurante, [item_avulso(catalogo.feijoada)])
    restaurante.is_active = False
    db.flush()

    assert _repetir(client, headers, pedido).status_code == 404


def test_reconstruir_avulso_com_e_sem_observacao():
    alimento = uuid.uuid4()

    com = reconstruir_item(OrderItem(food_id=alimento, quantity=2, notes="sem sal"))
    sem = reconstruir_item(OrderItem(food_id=alimento, quantity=1))

    assert com == {
        "quantidade": 2, "observacao": "sem sal", "tipo": "AVULSO", "alimento_id": str(alimento),
    }
    assert "observacao" not in sem


def test_reconstruir_marmita_agrupa_as_escolhas_por_categoria():
    marmita, cat_1, cat_2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    a1, a2, a3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    snapshot = {
        "escolhas": [
            {"categoria_id": str(cat_1), "alimento_id": str(a1), "quantidade": 1},
            {"categoria_id": str(cat_1), "alimento_id": str(a2), "quantidade": 2},
            {"categoria_id": str(cat_2), "alimento_id": str(a3), "quantidade": 1},
        ]
    }

    dados = reconstruir_item(OrderItem(meal_box_id=marmita, quantity=1, snapshot=snapshot))

    assert dados["tipo"] == "MARMITA"
    assert dados["marmita_id"] == str(marmita)
    assert dados["selecoes"] == [
        {
            "categoria_id": str(cat_1),
            "alimentos": [
                {"alimento_id": str(a1), "quantidade": 1},
                {"alimento_id": str(a2), "quantidade": 2},
            ],
        },
        {"categoria_id": str(cat_2), "alimentos": [{"alimento_id": str(a3), "quantidade": 1}]},
    ]


def test_reconstruir_marmita_pronta_nao_tem_selecoes():
    snapshot = {"composicao": [{"alimento_id": str(uuid.uuid4()), "nome": "Arroz", "quantidade": 1}]}

    dados = reconstruir_item(OrderItem(meal_box_id=uuid.uuid4(), quantity=1, snapshot=snapshot))

    assert dados["selecoes"] == []


def test_reconstruir_combo_leva_so_as_marmitas_personalizadas():
    combo, pronta, personalizavel = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    categoria, alimento = uuid.uuid4(), uuid.uuid4()
    escolha = {"categoria_id": str(categoria), "alimento_id": str(alimento), "quantidade": 1}
    snapshot = {
        "marmitas": [
            {"marmita_id": str(pronta), "composicao": [], "quantidade": 1},
            {"marmita_id": str(personalizavel), "escolhas": [escolha], "quantidade": 1},
            {"marmita_id": str(personalizavel), "escolhas": [escolha], "quantidade": 1},
        ]
    }

    dados = reconstruir_item(OrderItem(combo_id=combo, quantity=1, snapshot=snapshot))

    assert dados["tipo"] == "COMBO"
    assert dados["combo_id"] == str(combo)
    assert [m["marmita_id"] for m in dados["marmitas"]] == [str(personalizavel)] * 2
    assert dados["marmitas"][0]["selecoes"] == [
        {
            "categoria_id": str(categoria),
            "alimentos": [{"alimento_id": str(alimento), "quantidade": 1}],
        }
    ]


def test_reconstruir_item_sem_referencia_levanta_erro():
    with pytest.raises(ValueError):
        reconstruir_item(OrderItem(quantity=1))