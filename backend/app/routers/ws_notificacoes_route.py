# backend/app/api/routers/ws_notifications.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from backend.app.core.websockets import manager
from backend.app.core.seguranca import decode_access_token
import uuid

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/restaurante")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    try:
        # Reutiliza a lógica do seu OAuth2 para extrair o usuário do token
        payload = decode_access_token(token)
        restaurant_id = uuid.UUID(payload.get("restaurant_id"))
    except Exception:
        await websocket.close(code=1008) # Policy Violation
        return

    await manager.connect(websocket, restaurant_id)
    
    try:
        while True:
            # Mantém a conexão aberta esperando pings (se necessário)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id)