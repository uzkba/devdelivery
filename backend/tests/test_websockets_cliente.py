import asyncio
import uuid

from app.core.websockets import ConnectionManager


class FakeSocket:
    def __init__(self, morto=False):
        self.morto = morto
        self.aceito = False
        self.recebidas = []

    async def accept(self):
        self.aceito = True

    async def send_json(self, message):
        if self.morto:
            raise RuntimeError("conexao fechada")
        self.recebidas.append(message)


def test_conectar_cliente_aceita_e_registra():
    manager = ConnectionManager()
    cliente = uuid.uuid4()
    socket = FakeSocket()

    asyncio.run(manager.connect_client(socket, cliente))

    assert socket.aceito is True
    assert manager.client_connections[cliente] == [socket]
    assert manager.active_connections == {}


def test_broadcast_so_atinge_o_cliente_certo():
    manager = ConnectionManager()
    a, b = uuid.uuid4(), uuid.uuid4()
    socket_a, socket_b = FakeSocket(), FakeSocket()
    asyncio.run(manager.connect_client(socket_a, a))
    asyncio.run(manager.connect_client(socket_b, b))

    asyncio.run(manager.broadcast_to_client(a, {"tipo": "STATUS_PEDIDO"}))

    assert socket_a.recebidas == [{"tipo": "STATUS_PEDIDO"}]
    assert socket_b.recebidas == []


def test_cliente_com_duas_abas_recebe_nas_duas():
    manager = ConnectionManager()
    cliente = uuid.uuid4()
    aba_1, aba_2 = FakeSocket(), FakeSocket()
    asyncio.run(manager.connect_client(aba_1, cliente))
    asyncio.run(manager.connect_client(aba_2, cliente))

    asyncio.run(manager.broadcast_to_client(cliente, {"tipo": "X"}))

    assert aba_1.recebidas == [{"tipo": "X"}]
    assert aba_2.recebidas == [{"tipo": "X"}]


def test_mesmo_uuid_de_restaurante_e_cliente_nao_se_misturam():
    manager = ConnectionManager()
    mesmo_id = uuid.uuid4()
    do_restaurante, do_cliente = FakeSocket(), FakeSocket()
    asyncio.run(manager.connect(do_restaurante, mesmo_id))
    asyncio.run(manager.connect_client(do_cliente, mesmo_id))

    asyncio.run(manager.broadcast_to_client(mesmo_id, {"tipo": "C"}))
    asyncio.run(manager.broadcast_to_restaurant(mesmo_id, {"tipo": "R"}))

    assert do_cliente.recebidas == [{"tipo": "C"}]
    assert do_restaurante.recebidas == [{"tipo": "R"}]


def test_conexao_morta_do_cliente_e_removida_sem_pular_a_proxima():
    manager = ConnectionManager()
    cliente = uuid.uuid4()
    morta, viva = FakeSocket(morto=True), FakeSocket()
    asyncio.run(manager.connect_client(morta, cliente))
    asyncio.run(manager.connect_client(viva, cliente))

    asyncio.run(manager.broadcast_to_client(cliente, {"tipo": "X"}))

    assert viva.recebidas == [{"tipo": "X"}]
    assert manager.client_connections[cliente] == [viva]


def test_desconectar_cliente_limpa_a_chave():
    manager = ConnectionManager()
    cliente = uuid.uuid4()
    socket = FakeSocket()
    asyncio.run(manager.connect_client(socket, cliente))

    manager.disconnect_client(socket, cliente)
    manager.disconnect_client(socket, cliente)

    assert cliente not in manager.client_connections


def test_broadcast_para_cliente_sem_conexao_nao_falha():
    manager = ConnectionManager()

    asyncio.run(manager.broadcast_to_client(uuid.uuid4(), {"tipo": "X"}))

    assert manager.client_connections == {}