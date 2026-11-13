def test_pedido_novo_nao_tem_motivo_nem_entregador(client, admin_headers, pedido_teste):
    resposta = client.get(f"/pedidos/{pedido_teste.id}", headers=admin_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["motivo"] is None
    assert corpo["entregador"] is None


def test_pedido_expoe_motivo_e_nome_do_entregador(
    db, client, admin_headers, pedido_teste, entregador_user
):
    pedido_teste.status_reason = "Faltou ingrediente"
    pedido_teste.driver_id = entregador_user.id
    db.flush()
    db.refresh(pedido_teste)

    resposta = client.get(f"/pedidos/{pedido_teste.id}", headers=admin_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["motivo"] == "Faltou ingrediente"
    assert corpo["entregador"] == {"id": str(entregador_user.id), "nome": "Pedro Entregador"}


def test_cliente_ve_o_entregador_do_proprio_pedido(
    db, client, token_para_cliente, cliente, pedido_teste, entregador_user
):
    pedido_teste.driver_id = entregador_user.id
    db.flush()
    db.refresh(pedido_teste)
    headers = {"Authorization": f"Bearer {token_para_cliente(cliente)}"}

    resposta = client.get(f"/pedidos/cliente/{pedido_teste.id}", headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["entregador"]["nome"] == "Pedro Entregador"