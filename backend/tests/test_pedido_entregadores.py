import pytest

from app.core.seguranca import hash_password
from app.model.models import AdminUser


def _entregador(db, restaurante, nome, login, ativo=True):
    usuario = AdminUser(
        restaurant_id=restaurante.id,
        name=nome,
        login=login,
        password_hash=hash_password("senha123"),
        role="entregador",
        is_active=ativo,
    )
    db.add(usuario)
    db.flush()
    return usuario


def test_lista_so_entregadores_ativos_do_restaurante_em_ordem_alfabetica(
    client, db, admin_headers, restaurante, outro_restaurante, entregador_user, atendente_user
):
    ana = _entregador(db, restaurante, "Ana Entregadora", "ana.entregadora")
    _entregador(db, restaurante, "Zeca Inativo", "zeca.inativo", ativo=False)
    _entregador(db, outro_restaurante, "Rui do Outro", "rui.outro")

    resposta = client.get("/pedidos/entregadores", headers=admin_headers)

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"id": str(ana.id), "nome": "Ana Entregadora"},
        {"id": str(entregador_user.id), "nome": "Pedro Entregador"},
    ]


def test_sem_entregadores_devolve_lista_vazia(client, admin_headers, atendente_user):
    resposta = client.get("/pedidos/entregadores", headers=admin_headers)

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_so_expoe_id_e_nome(client, admin_headers, entregador_user):
    resposta = client.get("/pedidos/entregadores", headers=admin_headers)

    assert set(resposta.json()[0]) == {"id", "nome"}


@pytest.mark.parametrize(
    "papel, esperado",
    [
        ("admin_user", 200),
        ("atendente_user", 200),
        ("caixa_user", 403),
        ("entregador_user", 403),
    ],
)
def test_so_admin_e_atendente_listam(request, client, token_para, papel, esperado):
    usuario = request.getfixturevalue(papel)
    headers = {"Authorization": f"Bearer {token_para(usuario)}"}

    resposta = client.get("/pedidos/entregadores", headers=headers)

    assert resposta.status_code == esperado


def test_exige_login(client):
    assert client.get("/pedidos/entregadores").status_code in (401, 403)


def test_cada_restaurante_ve_so_os_seus(
    client, db, outro_admin_headers, restaurante, entregador_user
):
    resposta = client.get("/pedidos/entregadores", headers=outro_admin_headers)

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_id_da_lista_serve_para_enviar_o_pedido(
    client, admin_headers, novo_pedido, entregador_user
):
    pedido = novo_pedido("PRONTO")
    lista = client.get("/pedidos/entregadores", headers=admin_headers).json()

    resposta = client.post(
        f"/pedidos/{pedido.id}/enviar",
        json={"entregador_id": lista[0]["id"]},
        headers=admin_headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["entregador"]["nome"] == "Pedro Entregador"
    assert resposta.json()["status"]["codigo"] == "SAIU_PARA_ENTREGA"