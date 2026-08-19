# backend/app/schemas/auth.py
"""
Schemas Pydantic usados na autenticação.
"""
import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(..., description="Login (usuário) do AdminUser")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos até expirar


class AuthenticatedUser(BaseModel):
    """Payload decodificado do token, exposto via dependency."""
    id: uuid.UUID
    login: str
    name: str
    role: str
    restaurant_id: uuid.UUID