def test_listar_logs_auditoria_filtrado_por_entidade(
    db, client, restaurante, admin_user, token_para, algum_log_de_pedido, algum_log_de_alimento
):
    token = token_para(admin_user)
    resposta = client.get(
        "/logs-auditoria?entidade=alimento",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 200
    assert all(log["entidade"] == "alimento" for log in resposta.json())


def test_listar_logs_auditoria_nega_acesso_papel_nao_admin(client, restaurante, token_para, atendente_user):
    token = token_para(atendente_user)
    resposta = client.get(
        "/logs-auditoria", headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 403


def test_listar_logs_auditoria_nao_vaza_de_outro_restaurante(
    db, client, restaurante, outro_restaurante, admin_user, token_para,
    log_do_outro_restaurante,
):
    token = token_para(admin_user)
    resposta = client.get(
        "/logs-auditoria", headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 200
    ids_retornados = {log["id"] for log in resposta.json()}
    assert str(log_do_outro_restaurante.id) not in ids_retornados