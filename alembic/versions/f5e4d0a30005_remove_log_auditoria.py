"""remove log_auditoria (auditoria abandonada por ora)

Revision ID: f5e4d0a30005
Revises: f4d3e9f20004
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f5e4d0a30005"
down_revision = "f4d3e9f20004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drop_table leva junto os índices idx_log_auditoria_entidade e idx_log_auditoria_restaurante_periodo
    op.drop_table("log_auditoria")


def downgrade() -> None:
    op.create_table(
        "log_auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entidade", sa.String(length=50), nullable=False),
        sa.Column("entidade_id", sa.String(length=50), nullable=False),
        sa.Column("acao", sa.String(length=30), nullable=False),
        sa.Column("dados_anteriores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dados_novos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["restaurante_id"], ["restaurante.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario_admin.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_log_auditoria_entidade", "log_auditoria", ["entidade", "entidade_id"], unique=False)
    op.create_index(
        "idx_log_auditoria_restaurante_periodo", "log_auditoria", ["restaurante_id", "criado_em"], unique=False
    )