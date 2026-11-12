import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from app.model.models import Food, MealBox, MealBoxKind
from app.schemas.pedido_schemas import (
    ItemAvulsoIn,
    ItemComboIn,
    ItemMarmitaIn,
    ItemPedidoIn,
)
from app.services import pedido_validacao_service as validacao
from app.services.pedido_validacao_service import (
    ComboValidado,
    EscolhaValidada,
    MarmitaValidada,
)

SNAPSHOT_VERSAO = 1
_CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class ItemMontado:
    tipo: str  # "MARMITA" | "COMBO" | "AVULSO"
    nome: str  # nome comercial -> OrderItem.food_name
    quantidade: int
    preco_unitario: Decimal  # -> OrderItem.base_price
    subtotal: Decimal
    observacao: str | None
    food_id: uuid.UUID | None
    meal_box_id: uuid.UUID | None
    combo_id: uuid.UUID | None
    snapshot: dict  # -> OrderItem.snapshot (JSONB)


def _dinheiro(valor) -> str:
    return str(Decimal(valor).quantize(_CENTAVOS))


# ---------------------------------------------------------------------------
# Blocos do snapshot
# ---------------------------------------------------------------------------
def _composicao(marmita: MealBox) -> list[dict]:
    return [
        {"alimento_id": str(i.food_id), "nome": i.food.name, "quantidade": i.fixed_quantity}
        for i in marmita.composition
    ]


def _escolhas(escolhas: Sequence[EscolhaValidada]) -> list[dict]:
    return [
        {
            "categoria_id": str(e.categoria.id),
            "categoria": e.categoria.name,
            "alimento_id": str(e.alimento.id),
            "nome": e.alimento.name,
            "quantidade": e.quantidade,
        }
        for e in escolhas
    ]


def _detalhe_marmita(marmita: MealBox, escolhas: Sequence[EscolhaValidada]) -> dict:
    detalhe = {
        "marmita_id": str(marmita.id),
        "nome": marmita.name,
        "tipo_marmita": marmita.kind.value,
    }
    if marmita.kind == MealBoxKind.READY:
        detalhe["composicao"] = _composicao(marmita)
    else:
        detalhe["escolhas"] = _escolhas(escolhas)
    return detalhe


# ---------------------------------------------------------------------------
# Snapshot por tipo
# ---------------------------------------------------------------------------
def snapshot_avulso(alimento: Food) -> dict:
    categoria = alimento.sale_category
    return {
        "versao": SNAPSHOT_VERSAO,
        "tipo": "AVULSO",
        "alimento_id": str(alimento.id),
        "nome": alimento.name,
        "categoria": categoria.name if categoria else None,
        "preco_unitario": _dinheiro(alimento.standalone_price),
    }


def snapshot_marmita(validada: MarmitaValidada) -> dict:
    marmita = validada.marmita
    return {
        "versao": SNAPSHOT_VERSAO,
        "tipo": "MARMITA",
        "preco_unitario": _dinheiro(marmita.price),
        "tamanho": marmita.size,
        **_detalhe_marmita(marmita, validada.escolhas),
    }


def snapshot_combo(validado: ComboValidado) -> dict:
    combo = validado.combo

    # configuracoes das marmitas personalizaveis, na ordem em que o validador as devolveu
    configuradas: dict[uuid.UUID, deque[MarmitaValidada]] = defaultdict(deque)
    for unidade in validado.marmitas:
        configuradas[unidade.marmita.id].append(unidade)

    marmitas: list[dict] = []
    for item in combo.meal_box_items:
        marmita = item.meal_box
        if marmita.kind == MealBoxKind.READY:
            marmitas.append({**_detalhe_marmita(marmita, ()), "quantidade": item.quantity})
        else:
            for _ in range(item.quantity):  # uma entrada por unidade configurada
                unidade = configuradas[marmita.id].popleft()
                marmitas.append({**_detalhe_marmita(marmita, unidade.escolhas), "quantidade": 1})

    return {
        "versao": SNAPSHOT_VERSAO,
        "tipo": "COMBO",
        "combo_id": str(combo.id),
        "nome": combo.name,
        "preco_unitario": _dinheiro(combo.price),
        "marmitas": marmitas,
        "alimentos": [
            {"alimento_id": str(i.food_id), "nome": i.food.name, "quantidade": i.quantity}
            for i in combo.food_items
        ],
    }


# ---------------------------------------------------------------------------
# Item montado
# ---------------------------------------------------------------------------
def _montar(
    tipo: str,
    nome: str,
    item: ItemPedidoIn,
    preco: Decimal,
    snapshot: dict,
    *,
    food_id: uuid.UUID | None = None,
    meal_box_id: uuid.UUID | None = None,
    combo_id: uuid.UUID | None = None,
) -> ItemMontado:
    preco = Decimal(preco).quantize(_CENTAVOS)
    return ItemMontado(
        tipo=tipo,
        nome=nome,
        quantidade=item.quantidade,
        preco_unitario=preco,
        subtotal=(preco * item.quantidade).quantize(_CENTAVOS),
        observacao=item.observacao,
        food_id=food_id,
        meal_box_id=meal_box_id,
        combo_id=combo_id,
        snapshot=snapshot,
    )


def montar_item_pedido(
    db: Session, restaurante_id: uuid.UUID, item: ItemPedidoIn, hoje: date | None = None
) -> ItemMontado:
    if isinstance(item, ItemAvulsoIn):
        alimento = validacao.validar_item_avulso(db, restaurante_id, item, hoje)
        return _montar(
            "AVULSO", alimento.name, item, alimento.standalone_price,
            snapshot_avulso(alimento), food_id=alimento.id,
        )

    if isinstance(item, ItemMarmitaIn):
        validada = validacao.validar_item_marmita(db, restaurante_id, item, hoje)
        marmita = validada.marmita
        return _montar(
            "MARMITA", marmita.name, item, marmita.price,
            snapshot_marmita(validada), meal_box_id=marmita.id,
        )

    if isinstance(item, ItemComboIn):
        validado = validacao.validar_item_combo(db, restaurante_id, item, hoje)
        combo = validado.combo
        return _montar(
            "COMBO", combo.name, item, combo.price,
            snapshot_combo(validado), combo_id=combo.id,
        )

    raise TypeError(f"Tipo de item de pedido não suportado: {type(item).__name__}")