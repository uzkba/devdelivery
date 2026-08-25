from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.seguranca import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_password,
)
from backend.app.model.models import AdminUser
from backend.app.schemas.autenticacao_schemas import AuthenticatedUser, LoginRequest, TokenResponse
from backend.app.api.depedencias import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(AdminUser).where(AdminUser.login == payload.login))
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Login ou senha inválidos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise credenciais_invalidas

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo.",
        )

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": str(user.id),
            "login": user.login,
            "name": user.name,
            "role": user.role,
            "restaurant_id": str(user.restaurant_id),
            "type": "admin"
        },
        expires_delta=expires,
    )

    return TokenResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
    )


@router.get("/me", response_model=AuthenticatedUser)
def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    return current_user
