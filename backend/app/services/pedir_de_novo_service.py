import uuid
from decimal import Decimal

from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.api.dependencias_publicas import get_restaurante_publico
from app.core.tempo import hoje_local
from app.model.models import OrderItem, Restaurant
from app.schemas.pedido_schemas import ItemPedidoIn
from app.services import pedido_service
from app.services.pedido_snapshot_service import montar_item_pedido

_ENTRADA = TypeAdapter(ItemPedidoIn)
MOTIVO_GENERICO = "Não foi possível repetir este item."


def _selecoes(escolhas: list[dict]) -> list[dict]:
    por_categoria: dict[str, list[dict]] = {}
    for escolha in escolhas:
        por_categoria.setdefault(escolha["categoria_id"], []).append(
            {"alimento_id": escolha["alimento_id"], "quantidade": escolha["quantidade"]}
        )
    return [
        {"categoria_id": categoria_id, "alimentos": alimentos}
        for categoria_id, alimentos in por_categoria.items()
    ]


def reconstruir_item(item: OrderItem) -> dict:
    snapshot = item.snapshot or {}
    dados: dict = {"quantidade": item.quantity}
    if item.notes:
        dados["observacao"] = item.notes

    if item.combo_id is not None:
        dados.update(
            tipo="COMBO",
            combo_id=str(item.combo_id),
            marmitas=[
                {"marmita_id": m["marmita_id"], "selecoes": _selecoes(m["escolhas"])}
                for m in snapshot.get("marmitas", [])
                if "escolhas" in m
            ],
        )
    elif item.meal_box_id is not None:
        dados.update(
            tipo="MARMITA",
            marmita_id=str(item.meal_box_id),
            selecoes=_selecoes(snapshot.get("escolhas", [])),
        )
    elif item.food_id is not None:
        dados.update(tipo="AVULSO", alimento_id=str(item.food_id))
    else:
        raise ValueError("Item sem referência ao cardápio.")
    return dados


def montar_repeticao(db: Session, pedido_id: uuid.UUID, client_id: uuid.UUID) -> dict:
    pedido = pedido_service.buscar_pedido_do_cliente(db, pedido_id, client_id)
    dono = db.get(Restaurant, pedido.restaurant_id)
    restaurante = get_restaurante_publico(dono.slug, db)

    hoje = hoje_local()
    itens: list[dict] = []
    indisponiveis: list[dict] = []

    for original in pedido.items:
        try:
            entrada = _ENTRADA.validate_python(reconstruir_item(original))
            montado = montar_item_pedido(db, restaurante.id, entrada, hoje)
        except HTTPException as erro:
            indisponiveis.append({"nome": original.food_name, "motivo": str(erro.detail)})
        except (ValueError, KeyError, TypeError):
            indisponiveis.append({"nome": original.food_name, "motivo": MOTIVO_GENERICO})
        else:
            itens.append(
                {
                    "item": entrada,
                    "nome": montado.nome,
                    "quantidade": montado.quantidade,
                    "preco_unitario": montado.preco_unitario,
                    "preco_anterior": original.base_price,
                    "preco_mudou": montado.preco_unitario != original.base_price,
                    "subtotal": montado.subtotal,
                }
            )

    return {
        "restaurante_slug": restaurante.slug,
        "tipo_atendimento": pedido.service_type,
        "itens": itens,
        "indisponiveis": indisponiveis,
        "valor_itens": sum((i["subtotal"] for i in itens), Decimal("0.00")),
    }