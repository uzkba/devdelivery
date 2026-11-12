import uuid
from contextlib import contextmanager

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import get_db
from app.core.seguranca import decode_access_token
from app.core.websockets import manager
from app.model.models import AdminUser, Client

router = APIRouter(tags=["WebSockets"])

PAPEIS_DA_FILA = ("admin", "atendente")
POLICY_VIOLATION = 1008


@contextmanager
def _sessao(websocket: WebSocket):
    fabrica = websocket.app.dependency_overrides.get(get_db, get_db)
    gerador = fabrica()
    db = next(gerador)
    try:
        yield db
    finally:
        gerador.close()


def _payload(token: str) -> dict | None:
    try:
        return decode_access_token(token)
    except Exception:
        return None


def _uuid(valor) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (ValueError, TypeError):
        return None


def _restaurante_do_usuario(db, token: str) -> uuid.UUID | None:
    payload = _payload(token)
    if not payload or payload.get("type") == "client":
        return None
    usuario_id = _uuid(payload.get("sub"))
    if usuario_id is None:
        return None
    usuario = db.query(AdminUser).filter_by(id=usuario_id).first()
    if not usuario or not usuario.is_active or usuario.role not in PAPEIS_DA_FILA:
        return None
    return usuario.restaurant_id


def _id_do_cliente(db, token: str) -> uuid.UUID | None:
    payload = _payload(token)
    if not payload or payload.get("type") != "client":
        return None
    cliente_id = _uuid(payload.get("sub"))
    if cliente_id is None:
        return None
    cliente = db.query(Client).filter_by(id=cliente_id).first()
    if not cliente or not getattr(cliente, "is_active", True):
        return None
    return cliente.id


async def _manter_aberta(websocket: WebSocket) -> None:
    while True:
        await websocket.receive_text()


@router.websocket("/ws/restaurante")
async def websocket_restaurante(websocket: WebSocket, token: str = Query(...)):
    with _sessao(websocket) as db:
        restaurant_id = _restaurante_do_usuario(db, token)
    if restaurant_id is None:
        await websocket.close(code=POLICY_VIOLATION)
        return

    await manager.connect(websocket, restaurant_id)
    try:
        await _manter_aberta(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, restaurant_id)


@router.websocket("/ws/cliente")
async def websocket_cliente(websocket: WebSocket, token: str = Query(...)):
    with _sessao(websocket) as db:
        client_id = _id_do_cliente(db, token)
    if client_id is None:
        await websocket.close(code=POLICY_VIOLATION)
        return

    await manager.connect_client(websocket, client_id)
    try:
        await _manter_aberta(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_client(websocket, client_id)