import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.seguranca import JWTError, decode_access_token
from app.model.models import AdminUser, Client
from app.schemas.autenticacao_schemas import AuthenticatedUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = db.get(AdminUser, uid)
    
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo."
        )

    return AuthenticatedUser(
        id=user.id,
        login=user.login,
        name=user.name,
        role=user.role,
        restaurant_id=user.restaurant_id,
    )


def require_role(*allowed_roles: str):
    def checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return current_user
    return checker

@dataclass
class AuthenticatedClient:
    id: uuid.UUID
    name: str
    phone: str


def get_current_client(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedClient:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "client":
        raise credentials_exception

    client_id = payload.get("sub")
    if client_id is None:
        raise credentials_exception
    try:
        cid = uuid.UUID(client_id)
    except ValueError:
        raise credentials_exception

    client = db.get(Client, cid)
    if client is None:
        raise credentials_exception
    if not client.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente inativo.")

    return AuthenticatedClient(id=client.id, name=client.name, phone=client.phone)