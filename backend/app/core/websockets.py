import uuid
from typing import Dict, List

from fastapi import WebSocket

Grupo = Dict[uuid.UUID, List[WebSocket]]


class ConnectionManager:
    def __init__(self):
        self.active_connections: Grupo = {}
        self.client_connections: Grupo = {}

    @staticmethod
    async def _conectar(grupo: Grupo, websocket: WebSocket, chave: uuid.UUID):
        await websocket.accept()
        grupo.setdefault(chave, []).append(websocket)

    @staticmethod
    def _desconectar(grupo: Grupo, websocket: WebSocket, chave: uuid.UUID):
        conexoes = grupo.get(chave)
        if conexoes is None:
            return
        if websocket in conexoes:
            conexoes.remove(websocket)
        if not conexoes:
            del grupo[chave]

    @classmethod
    async def _difundir(cls, grupo: Grupo, chave: uuid.UUID, message: dict):
        for connection in list(grupo.get(chave, [])):
            try:
                await connection.send_json(message)
            except Exception:
                cls._desconectar(grupo, connection, chave)

    async def connect(self, websocket: WebSocket, restaurant_id: uuid.UUID):
        await self._conectar(self.active_connections, websocket, restaurant_id)

    def disconnect(self, websocket: WebSocket, restaurant_id: uuid.UUID):
        self._desconectar(self.active_connections, websocket, restaurant_id)

    async def broadcast_to_restaurant(self, restaurant_id: uuid.UUID, message: dict):
        await self._difundir(self.active_connections, restaurant_id, message)

    async def connect_client(self, websocket: WebSocket, client_id: uuid.UUID):
        await self._conectar(self.client_connections, websocket, client_id)

    def disconnect_client(self, websocket: WebSocket, client_id: uuid.UUID):
        self._desconectar(self.client_connections, websocket, client_id)

    async def broadcast_to_client(self, client_id: uuid.UUID, message: dict):
        await self._difundir(self.client_connections, client_id, message)


manager = ConnectionManager()