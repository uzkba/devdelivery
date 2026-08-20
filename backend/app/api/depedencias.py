# backend/app/api/depedencias.py
"""
Dependencies de autenticação/autorização para proteger rotas do FastAPI.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.app.core.seguranca import JWTError, decode_access_token
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser

# tokenUrl é só documentação (Swagger); o login continua em POST /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
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
        return AuthenticatedUser(
            id=uuid.UUID(user_id),
            login=payload["login"],
            name=payload["name"],
            role=payload["role"],
            restaurant_id=uuid.UUID(payload["restaurant_id"]),
        )
    except (KeyError, ValueError):
        raise credentials_exception


def require_role(*allowed_roles: str):
    """
    Factory de dependency para restringir uma rota a determinados papéis.
    Uso: @router.post(..., dependencies=[Depends(require_role("admin"))])
    """
    def checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return current_user
    return checker