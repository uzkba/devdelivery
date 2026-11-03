"""Remove o pagamento legado (conta_recebimento)

Revision ID: f3c2d8e10003
Revises: f2b1a7c90002
Create Date: 2026-11-01

O pagamento real (Pix com QR/copia-e-cola) foi revertido: no sistema o
pagamento e apenas informativo (forma_pagamento no pedido). A tabela
conta_recebimento, o model ReceivingAccount e os arquivos pagamento_* nao sao
mais usados.

Reversivel: o downgrade recria a tabela (vazia).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f3c2d8e10003"
down_revision = "f2b1a7c90002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("conta_recebimento")


def downgrade() -> None:
    op.create_table(
        "conta_recebimento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chave_pix", sa.String(140), nullable=False),
        sa.Column("tipo_chave_pix", sa.String(20), nullable=False),
        sa.Column("titular", sa.String(150), nullable=False),
        sa.Column("cidade", sa.String(60), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False),
        sa.Column("criado_em", sa.DateTime, nullable=False),
    )
