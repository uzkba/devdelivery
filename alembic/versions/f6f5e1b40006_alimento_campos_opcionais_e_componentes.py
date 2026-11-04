"""alimento: campos opcionais (serve, porção, preparo, nutrição) e tabela alimento_componente

Revision ID: f6f5e1b40006
Revises: f5e4d0a30005
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6f5e1b40006"
down_revision = "f5e4d0a30005"
branch_labels = None
depends_on = None

_COLUNAS = [
    ("serve_pessoas", sa.Integer()),
    ("porcao_quantidade", sa.Numeric(8, 2)),
    ("porcao_unidade", sa.String(length=2)),
    ("tempo_preparo_minutos", sa.Integer()),
    ("calorias_kcal", sa.Integer()),
    ("proteina_g", sa.Numeric(6, 1)),
    ("carboidrato_g", sa.Numeric(6, 1)),
    ("gordura_g", sa.Numeric(6, 1)),
]

_CHECKS = [
    ("ck_alimento_serve_pessoas", "serve_pessoas IS NULL OR serve_pessoas BETWEEN 1 AND 50"),
    ("ck_alimento_porcao_quantidade", "porcao_quantidade IS NULL OR porcao_quantidade > 0"),
    ("ck_alimento_porcao_unidade", "porcao_unidade IS NULL OR porcao_unidade IN ('g', 'kg', 'ml', 'l')"),
    ("ck_alimento_porcao_completa", "(porcao_quantidade IS NULL) = (porcao_unidade IS NULL)"),
    (
        "ck_alimento_tempo_preparo",
        "tempo_preparo_minutos IS NULL OR tempo_preparo_minutos BETWEEN 1 AND 480",
    ),
    ("ck_alimento_calorias", "calorias_kcal IS NULL OR calorias_kcal >= 0"),
    (
        "ck_alimento_macros",
        "(proteina_g IS NULL OR proteina_g >= 0) AND "
        "(carboidrato_g IS NULL OR carboidrato_g >= 0) AND "
        "(gordura_g IS NULL OR gordura_g >= 0)",
    ),
]


def upgrade() -> None:
    for nome, tipo in _COLUNAS:
        op.add_column("alimento", sa.Column(nome, tipo, nullable=True))
    for nome, expressao in _CHECKS:
        op.create_check_constraint(nome, "alimento", expressao)

    op.create_table(
        "alimento_componente",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alimento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=300), nullable=True),
        sa.Column("posicao", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["alimento_id"], ["alimento.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_alimento_componente_alimento", "alimento_componente", ["alimento_id", "posicao"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_alimento_componente_alimento", table_name="alimento_componente")
    op.drop_table("alimento_componente")

    for nome, _ in reversed(_CHECKS):
        op.drop_constraint(nome, "alimento", type_="check")
    for nome, _ in reversed(_COLUNAS):
        op.drop_column("alimento", nome)