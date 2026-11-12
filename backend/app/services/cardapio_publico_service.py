import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import (
    Combo,
    Food,
    FoodCategory,
    MealBox,
    MealBoxKind,
    Order,
    OrderItem,
    OrderStatus,
)
from app.services import disponibilidade_service as disponibilidade

_CENTAVOS = Decimal("0.01")
GRUPOS = ("prato", "bebida")

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")
DIAS_MAIS_PEDIDOS = 30
LIMITE_MAIS_PEDIDOS = 5
STATUS_IGNORADOS = ("CANCELADO", "RECUSADO")


def preco_referencia_combo(combo: Combo) -> Decimal | None:
    total = Decimal("0")
    for item in combo.meal_box_items:
        total += item.meal_box.price * item.quantity
    for item in combo.food_items:
        if item.food.standalone_price is None:
            return None
        total += item.food.standalone_price * item.quantity

    total = total.quantize(_CENTAVOS)
    if total - combo.price <= 0:
        return None
    return total


def _visiveis(db: Session, modelo: type, objetos: list, hoje: date) -> list:
    """Dos objetos informados, os que servem hoje e nao estao esgotados."""
    servem = disponibilidade.servem_hoje(db, modelo, [o.id for o in objetos], hoje)
    return [
        o for o in objetos
        if o.id in servem and not disponibilidade.esgotado_hoje(o, hoje)
    ]


def com_componentes_disponiveis(db: Session, combos: list[Combo], hoje: date) -> list[Combo]:
    marmitas = {i.meal_box.id: i.meal_box for c in combos for i in c.meal_box_items}
    alimentos = {i.food.id: i.food for c in combos for i in c.food_items}
    for marmita in marmitas.values():
        if marmita.kind == MealBoxKind.READY:
            alimentos.update({i.food.id: i.food for i in marmita.composition})

    servem_marmitas = disponibilidade.servem_hoje(db, MealBox, marmitas.keys(), hoje)
    servem_alimentos = disponibilidade.servem_hoje(db, Food, alimentos.keys(), hoje)

    def alimento_ok(alimento: Food) -> bool:
        return (
            alimento.is_active
            and alimento.id in servem_alimentos
            and not disponibilidade.esgotado_hoje(alimento, hoje)
        )

    def marmita_ok(marmita: MealBox) -> bool:
        if not (
            marmita.is_active
            and marmita.id in servem_marmitas
            and not disponibilidade.esgotado_hoje(marmita, hoje)
        ):
            return False
        return marmita.kind != MealBoxKind.READY or all(
            alimento_ok(i.food) for i in marmita.composition
        )

    return [
        c for c in combos
        if all(marmita_ok(i.meal_box) for i in c.meal_box_items)
        and all(alimento_ok(i.food) for i in c.food_items)
    ]


def _marmitas(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    caixas = db.scalars(
        select(MealBox)
        .where(MealBox.restaurant_id == restaurant_id, MealBox.is_active.is_(True))
        .order_by(MealBox.name)
    ).all()
    return [
        {
            "id": m.id,
            "nome": m.name,
            "descricao": m.description,
            "tipo": m.kind,
            "tamanho": m.size,
            "preco": m.price,
            "imagem_url": m.image_url,
            "destaque": m.is_featured,
        }
        for m in _visiveis(db, MealBox, list(caixas), hoje)
    ]


def _combos(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    combos = db.scalars(
        select(Combo)
        .where(Combo.restaurant_id == restaurant_id, Combo.is_active.is_(True))
        .order_by(Combo.name)
    ).all()
    # componente inativo, esgotado ou fora do dia derruba o combo (igual ao pedido)
    combos = com_componentes_disponiveis(db, list(combos), hoje)
    return [
        {
            "id": c.id,
            "nome": c.name,
            "descricao": c.description,
            "preco": c.price,
            "preco_referencia": preco_referencia_combo(c),
            "imagem_url": c.image_url,
            "destaque": c.is_featured,
        }
        for c in _visiveis(db, Combo, combos, hoje)
    ]


def _produto(alimento: Food) -> dict:
    return {
        "id": alimento.id,
        "nome": alimento.name,
        "descricao": alimento.description,
        "preco": alimento.standalone_price,
        "imagem_url": alimento.image_url,
        "destaque": alimento.is_featured,
    }


def _secoes(db: Session, restaurant_id: uuid.UUID, hoje: date) -> list[dict]:
    # join com ON explicito: Food tem 3 FKs para FoodCategory
    linhas = db.execute(
        select(Food, FoodCategory)
        .join(FoodCategory, Food.sale_category_id == FoodCategory.id)
        .where(
            Food.restaurant_id == restaurant_id,
            Food.is_active.is_(True),
            Food.is_sellable_alone.is_(True),
            FoodCategory.restaurant_id == restaurant_id,
            FoodCategory.type == "venda",
            FoodCategory.is_active.is_(True),
        )
        .order_by(FoodCategory.display_order, FoodCategory.name, Food.name)
    ).all()
    visiveis = {f.id for f in _visiveis(db, Food, [f for f, _ in linhas], hoje)}

    por_grupo: dict[str, dict[uuid.UUID, dict]] = {g: {} for g in GRUPOS}
    for alimento, categoria in linhas:
        if alimento.id not in visiveis or categoria.group not in por_grupo:
            continue
        secao = por_grupo[categoria.group].setdefault(
            categoria.id, {"id": categoria.id, "nome": categoria.name, "itens": []}
        )
        secao["itens"].append(_produto(alimento))

    # categoria e secao vazias nem chegam a ser criadas
    return [
        {"grupo": grupo, "categorias": list(categorias.values())}
        for grupo, categorias in por_grupo.items()
        if categorias
    ]


# ------------------------- destaques e mais pedidos -------------------------
def _itens_vitrine(marmitas: list[dict], combos: list[dict], produtos: list[dict]) -> list[tuple[str, dict]]:
    pares = (("marmita", marmitas), ("combo", combos), ("produto", produtos))
    return [(tipo, item) for tipo, itens in pares for item in itens]


def _card(tipo: str, item: dict) -> dict:
    return {
        "tipo": tipo,
        "id": item["id"],
        "nome": item["nome"],
        "preco": item["preco"],
        "imagem_url": item["imagem_url"],
    }


def _destaques(itens: list[tuple[str, dict]]) -> list[dict]:
    return [_card(tipo, item) for tipo, item in itens if item["destaque"]]


def _inicio_da_janela(hoje: date) -> datetime:
    """Meia-noite local de (hoje - 30 dias), em UTC sem fuso, como order_datetime."""
    inicio_local = datetime.combine(
        hoje - timedelta(days=DIAS_MAIS_PEDIDOS), time.min, tzinfo=FUSO_LOCAL
    )
    return inicio_local.astimezone(timezone.utc).replace(tzinfo=None)


def _contagem_ultimos_dias(
    db: Session, restaurant_id: uuid.UUID, hoje: date
) -> dict[tuple[str, uuid.UUID], int]:
    """Linhas de pedido_item por item nos ultimos 30 dias, sem pedidos cancelados."""
    linhas = db.execute(
        select(OrderItem.food_id, OrderItem.meal_box_id, OrderItem.combo_id, func.count())
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .join(OrderStatus, Order.status_id == OrderStatus.id)
        .where(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= _inicio_da_janela(hoje),
            OrderStatus.code.not_in(STATUS_IGNORADOS),
        )
        .group_by(OrderItem.food_id, OrderItem.meal_box_id, OrderItem.combo_id)
    ).all()

    contagem: dict[tuple[str, uuid.UUID], int] = {}
    for food_id, meal_box_id, combo_id, total in linhas:
        if food_id is not None:
            chave = ("produto", food_id)
        elif meal_box_id is not None:
            chave = ("marmita", meal_box_id)
        elif combo_id is not None:
            chave = ("combo", combo_id)
        else:
            continue
        contagem[chave] = contagem.get(chave, 0) + total
    return contagem


def _mais_pedidos(
    itens: list[tuple[str, dict]], contagem: dict[tuple[str, uuid.UUID], int]
) -> list[dict]:
    """Os mais pedidos entre os itens VISIVEIS da Home (desempate por nome)."""
    ranking = sorted(
        (
            (contagem[(tipo, item["id"])], tipo, item)
            for tipo, item in itens
            if (tipo, item["id"]) in contagem
        ),
        key=lambda r: (-r[0], r[2]["nome"]),
    )
    return [_card(tipo, item) for _, tipo, item in ranking[:LIMITE_MAIS_PEDIDOS]]


def montar_home(db: Session, restaurant_id: uuid.UUID, hoje: date | None = None) -> dict:
    hoje = hoje or hoje_local()
    marmitas = _marmitas(db, restaurant_id, hoje)
    combos = _combos(db, restaurant_id, hoje)
    secoes = _secoes(db, restaurant_id, hoje)

    produtos = [i for s in secoes for c in s["categorias"] for i in c["itens"]]
    itens = _itens_vitrine(marmitas, combos, produtos)
    contagem = _contagem_ultimos_dias(db, restaurant_id, hoje)

    return {
        "destaques": _destaques(itens),
        "mais_pedidos": _mais_pedidos(itens, contagem),
        "marmitas": marmitas,
        "combos": combos,
        "secoes": secoes,
    }