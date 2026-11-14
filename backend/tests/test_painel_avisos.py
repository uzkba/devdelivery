from datetime import date, datetime, timezone

from app.model.models import OrderServiceType
from app.services import painel_avisos_service as service

AGORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)
HOJE = date(2026, 11, 14)


def test_cada_pedido_novo_vira_um_aviso(db, restaurante, pedido_em):
    pedido = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 25))

    resultado = service.avisos_do_painel(db, restaurante.id, agora=AGORA)

    assert resultado.total == 1
    [aviso] = resultado.avisos
    assert aviso.tipo == "PEDIDO_NOVO"
    assert aviso.gravidade == "AVISO"
    assert aviso.titulo == f"Pedido #{pedido.order_number} aguardando aceite"
    assert aviso.detalhe == "José da Silva · Entrega"
    assert aviso.destino == "pedidos"
    assert aviso.quantidade == 1
    assert aviso.pedido_id == pedido.id
    assert aviso.numero_pedido == pedido.order_number
    assert aviso.minutos == 5


def test_pedido_de_retirada_mostra_o_tipo_no_detalhe(db, restaurante, pedido_em):
    pedido_em("CRIADO", datetime(2026, 11, 14, 18, 28), service_type=OrderServiceType.PICKUP)

    [aviso] = service.avisos_do_painel(db, restaurante.id, agora=AGORA).avisos

    assert aviso.detalhe == "José da Silva · Retirada"


def test_ordem_critico_depois_novos_depois_demais_alertas(
    db, restaurante, pedido_em, marmita_pronta
):
    antigo = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 15))
    recente = pedido_em("CRIADO", datetime(2026, 11, 14, 18, 25))
    marmita_pronta.sold_out_on = HOJE
    db.flush()

    resultado = service.avisos_do_painel(db, restaurante.id, agora=AGORA)

    assert resultado.total == 4
    assert [a.tipo for a in resultado.avisos] == [
        "PEDIDO_ATRASADO", "PEDIDO_NOVO", "PEDIDO_NOVO", "ITENS_INDISPONIVEIS",
    ]
    critico, primeiro, segundo, itens = resultado.avisos
    assert critico.gravidade == "CRITICO"
    assert critico.pedido_id is None
    assert primeiro.numero_pedido == antigo.order_number
    assert primeiro.gravidade == "CRITICO"
    assert primeiro.minutos == 15
    assert segundo.numero_pedido == recente.order_number
    assert segundo.gravidade == "AVISO"
    assert itens.gravidade == "AVISO"
    assert itens.destino == "cardapio"


def test_limite_corta_so_os_pedidos_novos_e_o_total_continua_real(
    db, restaurante, pedido_em
):
    criados = [
        pedido_em("CRIADO", datetime(2026, 11, 14, 18, minuto)) for minuto in (26, 27, 28)
    ]

    resultado = service.avisos_do_painel(db, restaurante.id, limite=2, agora=AGORA)

    assert resultado.total == 3
    assert [a.numero_pedido for a in resultado.avisos] == [
        criados[0].order_number, criados[1].order_number,
    ]


def test_pedido_atrasado_que_nao_e_novo_gera_so_o_alerta(db, restaurante, pedido_em):
    pedido_em("CONFIRMADO", datetime(2026, 11, 14, 18, 0))

    resultado = service.avisos_do_painel(db, restaurante.id, agora=AGORA)

    assert resultado.total == 1
    assert [a.tipo for a in resultado.avisos] == ["PEDIDO_ATRASADO"]


def test_ignora_finalizados_e_outros_restaurantes(
    db, restaurante, outro_restaurante, pedido_em
):
    recente = datetime(2026, 11, 14, 18, 28)
    pedido_em("ENTREGUE", recente)
    pedido_em("CANCELADO", recente)
    pedido_em("CRIADO", recente, restaurant_id=outro_restaurante.id)

    resultado = service.avisos_do_painel(db, restaurante.id, agora=AGORA)

    assert resultado.total == 0
    assert resultado.avisos == []


def test_sem_nada_o_sino_fica_vazio(db, restaurante):
    resultado = service.avisos_do_painel(db, restaurante.id, agora=AGORA)

    assert resultado.total == 0
    assert resultado.avisos == []


def test_admin_e_atendente_acessam_o_sino(
    client, admin_headers, atendente_user, token_para, pedido_em, utc_ha_minutos
):
    pedido_em("CRIADO", utc_ha_minutos(2))
    headers_atendente = {"Authorization": f"Bearer {token_para(atendente_user)}"}

    for headers in (admin_headers, headers_atendente):
        resposta = client.get("/painel/avisos", headers=headers)
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert set(corpo) == {"total", "avisos"}
        assert corpo["total"] == 1
        [aviso] = corpo["avisos"]
        assert aviso["tipo"] == "PEDIDO_NOVO"
        assert aviso["minutos"] >= 0


def test_caixa_e_entregador_nao_acessam_o_sino(
    client, caixa_user, entregador_user, token_para
):
    for usuario in (caixa_user, entregador_user):
        headers = {"Authorization": f"Bearer {token_para(usuario)}"}
        assert client.get("/painel/avisos", headers=headers).status_code == 403


def test_exige_autenticacao(client):
    assert client.get("/painel/avisos").status_code in (401, 403)


def test_limite_e_validado(client, admin_headers):
    assert client.get("/painel/avisos?limite=0", headers=admin_headers).status_code == 422
    assert client.get("/painel/avisos?limite=51", headers=admin_headers).status_code == 422