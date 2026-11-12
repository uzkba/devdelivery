import uuid

import sqlalchemy as sa
from alembic import op

revision = "f2c4a8e30017"
down_revision = "f1b3c8d90016"
branch_labels = None
depends_on = None

ORDEM_NOVA = {
    "CRIADO": 1,
    "CONFIRMADO": 2,
    "EM_PREPARO": 3,
    "PRONTO": 4,
    "SAIU_PARA_ENTREGA": 5,
    "ENTREGUE": 6,
    "RETIRADO": 7,
    "CANCELADO": 8,
    "RECUSADO": 9,
}

ORDEM_ANTIGA = {
    "CRIADO": 1,
    "CONFIRMADO": 2,
    "EM_PREPARO": 3,
    "SAIU_PARA_ENTREGA": 4,
    "ENTREGUE": 5,
    "CANCELADO": 6,
}

NOVOS = ("PRONTO", "RETIRADO", "RECUSADO")


def upgrade():
    bind = op.get_bind()
    pago_entregue = bool(
        bind.execute(sa.text("SELECT pago FROM status_pedido WHERE codigo = 'ENTREGUE'")).scalar()
    )
    existentes = {linha[0] for linha in bind.execute(sa.text("SELECT codigo FROM status_pedido"))}
    novos = {
        "PRONTO": ("Pronto", False, False),
        "RETIRADO": ("Retirado", pago_entregue, True),
        "RECUSADO": ("Recusado", False, True),
    }
    for codigo in NOVOS:
        if codigo in existentes:
            continue
        nome, pago, final = novos[codigo]
        bind.execute(
            sa.text(
                "INSERT INTO status_pedido (id, codigo, nome, ordem, pago, is_final) "
                "VALUES (CAST(:id AS uuid), :codigo, :nome, :ordem, :pago, :final)"
            ),
            {
                "id": str(uuid.uuid4()),
                "codigo": codigo,
                "nome": nome,
                "ordem": ORDEM_NOVA[codigo],
                "pago": pago,
                "final": final,
            },
        )
    for codigo, ordem in ORDEM_NOVA.items():
        bind.execute(
            sa.text("UPDATE status_pedido SET ordem = :ordem WHERE codigo = :codigo"),
            {"ordem": ordem, "codigo": codigo},
        )


def downgrade():
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM status_pedido WHERE codigo IN ('PRONTO', 'RETIRADO', 'RECUSADO')"))
    for codigo, ordem in ORDEM_ANTIGA.items():
        bind.execute(
            sa.text("UPDATE status_pedido SET ordem = :ordem WHERE codigo = :codigo"),
            {"ordem": ordem, "codigo": codigo},
        )