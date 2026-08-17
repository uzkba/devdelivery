import uuid

from sqlalchemy import Uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from sqlalchemy import ForeignKey

class Restaurant(Base):
    __tablename__ = "restaurante"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trade_name: Mapped[str] = mapped_column("nome fantasia", String(150), nullable=False)
    cnpj: Mapped[str | None] = mapped_column("cnpj", String(18), unique=True)
    phone: Mapped[str | None] = mapped_column("telefone", String(20))
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("ariado_em", DateTime, server_default=func.now())

class Client(Base):
    __tablename__ = "cliente"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    phone: Mapped[str] = mapped_column("telefone", String(20), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

class customerAddress(Base):
    __tablename__ = "endereco_cliente"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False)
    complement: Mapped[str | None] = mapped_column("complemento", String(50))
    street: Mapped[str] = mapped_column("rua", String(150), nullable=False)
    number: Mapped[str] = mapped_column("numero", String(5), nullable=False)
    neighborhood: Mapped[str] = mapped_column("bairro", String(50), nullable=False)
    reference_point: Mapped[str | None] = mapped_column("ponto_de_referencia", String(150))
    primary_address: Mapped[bool] = mapped_column("endereco_principal", Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column("ariado_em", DateTime, server_default=func.now())
