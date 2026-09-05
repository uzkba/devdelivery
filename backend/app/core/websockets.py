# backend/app/core/websockets.py
import uuid
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Estrutura: { restaurant_id: [websocket1, websocket2, ...] }
        # Uma lista para suportar múltiplos atendentes logados no mesmo restaurante
        self.active_connections: Dict[uuid.UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, restaurant_id: uuid.UUID):
        await websocket.accept()
        if restaurant_id not in self.active_connections:
            self.active_connections[restaurant_id] = []
        self.active_connections[restaurant_id].append(websocket)

    def disconnect(self, websocket: WebSocket, restaurant_id: uuid.UUID):
        if restaurant_id in self.active_connections:
            if websocket in self.active_connections[restaurant_id]:
                self.active_connections[restaurant_id].remove(websocket)
            # Limpa a memória se não houver mais ninguém logado naquele restaurante
            if not self.active_connections[restaurant_id]:
                del self.active_connections[restaurant_id]

    async def broadcast_to_restaurant(self, restaurant_id: uuid.UUID, message: dict):
        """Envia o payload apenas para os atendentes do restaurante específico"""
        if restaurant_id in self.active_connections:
            for connection in self.active_connections[restaurant_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Remove conexões mortas (se o cliente fechou a aba abruptamente)
                    self.disconnect(connection, restaurant_id)

manager = ConnectionManager()