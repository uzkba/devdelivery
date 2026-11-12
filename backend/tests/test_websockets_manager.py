import asyncio
import uuid

from app.core.websockets import ConnectionManager


class FakeSocket:
    def __init__(self, morto=False):
        self.morto = morto
        self.recebidas = []

    async def send_json(self, message):
        if self.morto:
            raise RuntimeError("conexao fechada")
        self.recebidas.append(message)


def test_broadcast_remove_conexao_morta_sem_pular_a_proxima():
    manager = ConnectionManager()
    restaurante = uuid.uuid4()
    morta = FakeSocket(morto=True)
    viva = FakeSocket()
    manager.active_connections[restaurante] = [morta, viva]

    asyncio.run(manager.broadcast_to_restaurant(restaurante, {"tipo": "NOVO_PEDIDO"}))

    assert viva.recebidas == [{"tipo": "NOVO_PEDIDO"}]
    assert manager.active_connections[restaurante] == [viva]


def test_broadcast_remove_a_chave_quando_todas_as_conexoes_morrem():
    manager = ConnectionManager()
    restaurante = uuid.uuid4()
    manager.active_connections[restaurante] = [FakeSocket(morto=True), FakeSocket(morto=True)]

    asyncio.run(manager.broadcast_to_restaurant(restaurante, {"tipo": "X"}))

    assert restaurante not in manager.active_connections


def test_broadcast_para_restaurante_sem_conexoes_nao_falha():
    manager = ConnectionManager()

    asyncio.run(manager.broadcast_to_restaurant(uuid.uuid4(), {"tipo": "X"}))

    assert manager.active_connections == {}


def test_broadcast_nao_envia_para_outro_restaurante():
    manager = ConnectionManager()
    a, b = uuid.uuid4(), uuid.uuid4()
    socket_a, socket_b = FakeSocket(), FakeSocket()
    manager.active_connections[a] = [socket_a]
    manager.active_connections[b] = [socket_b]

    asyncio.run(manager.broadcast_to_restaurant(a, {"tipo": "X"}))

    assert socket_a.recebidas == [{"tipo": "X"}]
    assert socket_b.recebidas == []