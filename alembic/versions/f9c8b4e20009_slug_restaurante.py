"""slug do restaurante

Revision ID: f9c8b4e20009
Revises: f8b7a3d10008
"""
import re
import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "f9c8b4e20009"
down_revision = "f8b7a3d10008"
branch_labels = None
depends_on = None

# Copia propositalmente independente do codigo da aplicacao: a migration nao pode
# mudar de comportamento se app/core/slug.py mudar no futuro.
_RESERVADOS = {
    "admin", "api", "app", "assets", "cadastro", "cardapio", "carrinho", "cliente",
    "clientes", "conta", "docs", "health", "login", "logout", "nexus", "nexusdelivery",
    "openapi", "pedido", "pedidos", "redoc", "registrar", "restaurante", "restaurantes",
    "revisao", "static", "suporte", "www", "ws",
}


def _slugify(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    com_hifens = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower())
    return com_hifens.strip("-")[:60].strip("-")


def upgrade() -> None:
    op.add_column("restaurante", sa.Column("slug", sa.String(length=60), nullable=True))

    conexao = op.get_bind()
    linhas = conexao.execute(
        sa.text("SELECT id, nome_fantasia FROM restaurante ORDER BY criado_em, id")
    ).fetchall()

    usados: set[str] = set()
    for restaurante_id, nome in linhas:
        base = _slugify(nome or "")
        if len(base) < 3:
            base = "restaurante"
        elif base in _RESERVADOS:
            base = f"{base}-restaurante"

        candidato = base
        contador = 2
        while candidato in usados:
            sufixo = f"-{contador}"
            candidato = f"{base[: 60 - len(sufixo)].rstrip('-')}{sufixo}"
            contador += 1
        usados.add(candidato)

        conexao.execute(
            sa.text("UPDATE restaurante SET slug = :slug WHERE id = :id"),
            {"slug": candidato, "id": restaurante_id},
        )

    op.alter_column("restaurante", "slug", existing_type=sa.String(length=60), nullable=False)
    op.create_unique_constraint("uq_restaurante_slug", "restaurante", ["slug"])
    op.create_check_constraint(
        "ck_restaurante_slug",
        "restaurante",
        "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND char_length(slug) BETWEEN 3 AND 60",
    )


def downgrade() -> None:
    op.drop_constraint("ck_restaurante_slug", "restaurante", type_="check")
    op.drop_constraint("uq_restaurante_slug", "restaurante", type_="unique")
    op.drop_column("restaurante", "slug")