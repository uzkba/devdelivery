import uuid
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
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
            if not self.active_connections[restaurant_id]:
                del self.active_connections[restaurant_id]

    async def broadcast_to_restaurant(self, restaurant_id: uuid.UUID, message: dict):
        for connection in list(self.active_connections.get(restaurant_id, [])):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection, restaurant_id)


manager = ConnectionManager()