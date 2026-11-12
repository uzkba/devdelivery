import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import Combo, Food, FoodCategory, MealBox, MealBoxKind
from app.schemas.pedido_schemas import (
    ItemAvulsoIn,
    ItemComboIn,
    ItemMarmitaIn,
    SelecaoCategoriaIn,
)
from app.services import disponibilidade_service as disponibilidade


@dataclass(frozen=True)
class EscolhaValidada:
    categoria: FoodCategory
    alimento: Food
    quantidade: int


@dataclass(frozen=True)
class MarmitaValidada:
    marmita: MealBox
    escolhas: tuple[EscolhaValidada, ...]  # vazio para marmita PRONTA


@dataclass(frozen=True)
class ComboValidado:
    combo: Combo
    marmitas: tuple[MarmitaValidada, ...]  # uma por unidade de marmita personalizavel


def _erro(mensagem: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, mensagem)


# ---------------------------------------------------------------------------
# Disponibilidade
# ---------------------------------------------------------------------------
def _garantir_disponivel(db: Session, alvo: MealBox | Combo, rotulo: str, hoje: date) -> None:
    if not alvo.is_active:
        raise _erro(f"{rotulo}: indisponível.")
    estado = disponibilidade.estado_hoje(db, alvo, hoje)
    if not estado.serve_hoje:
        raise _erro(f"{rotulo}: não é servido hoje.")
    if estado.esgotado_hoje:
        raise _erro(f"{rotulo}: esgotado hoje.")


def _garantir_alimentos_disponiveis(
    db: Session, alimentos: Sequence[Food], hoje: date, contexto: str | None = None
) -> None:
    if not alimentos:
        return
    servem = disponibilidade.servem_hoje(db, Food, [a.id for a in alimentos], hoje)
    for alimento in alimentos:
        rotulo = f"'{alimento.name}'" + (f" ({contexto})" if contexto else "")
        if not alimento.is_active:
            raise _erro(f"{rotulo}: indisponível.")
        if alimento.id not in servem:
            raise _erro(f"{rotulo}: não é servido hoje.")
        if disponibilidade.esgotado_hoje(alimento, hoje):
            raise _erro(f"{rotulo}: esgotado hoje.")


def _garantir_marmita_pedivel(
    db: Session, marmita: MealBox, hoje: date, contexto: str | None = None
) -> None:
    rotulo = f"Marmita '{marmita.name}'" + (f" ({contexto})" if contexto else "")
    _garantir_disponivel(db, marmita, rotulo, hoje)
    if marmita.kind == MealBoxKind.READY:
        _garantir_alimentos_disponiveis(
            db, [i.food for i in marmita.composition], hoje, f"marmita '{marmita.name}'"
        )


# ---------------------------------------------------------------------------
# Buscas (sempre filtradas pelo restaurante)
# ---------------------------------------------------------------------------
def _buscar_marmita(db: Session, restaurante_id: uuid.UUID, marmita_id: uuid.UUID) -> MealBox:
    marmita = db.scalar(
        select(MealBox).where(MealBox.id == marmita_id, MealBox.restaurant_id == restaurante_id)
    )
    if marmita is None:
        raise _erro("Marmita não encontrada neste restaurante.")
    return marmita


def _buscar_combo(db: Session, restaurante_id: uuid.UUID, combo_id: uuid.UUID) -> Combo:
    combo = db.scalar(
        select(Combo).where(Combo.id == combo_id, Combo.restaurant_id == restaurante_id)
    )
    if combo is None:
        raise _erro("Combo não encontrado neste restaurante.")
    return combo


def _buscar_alimentos(
    db: Session, restaurante_id: uuid.UUID, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Food]:
    ids = set(ids)
    if not ids:
        return {}
    encontrados = {
        a.id: a
        for a in db.scalars(
            select(Food).where(Food.id.in_(ids), Food.restaurant_id == restaurante_id)
        )
    }
    if len(encontrados) != len(ids):
        raise _erro("Alimento não encontrado neste restaurante.")
    return encontrados


# ---------------------------------------------------------------------------
# Marmita personalizavel: composicao e soma por categoria
# ---------------------------------------------------------------------------
def _validar_configuracao(
    db: Session,
    restaurante_id: uuid.UUID,
    marmita: MealBox,
    selecoes: Sequence[SelecaoCategoriaIn],
    hoje: date,
) -> tuple[EscolhaValidada, ...]:
    categorias_da_marmita = {c.food_category_id for c in marmita.categories}
    for selecao in selecoes:
        if selecao.categoria_id not in categorias_da_marmita:
            raise _erro(f"Há uma categoria que não faz parte da marmita '{marmita.name}'.")

    por_categoria = {s.categoria_id: s for s in selecoes}
    alimentos = _buscar_alimentos(
        db, restaurante_id, [a.alimento_id for s in selecoes for a in s.alimentos]
    )

    escolhas: list[EscolhaValidada] = []
    for categoria_marmita in marmita.categories:  # ordem de cadastro
        selecao = por_categoria.get(categoria_marmita.food_category_id)
        itens = selecao.alimentos if selecao else []
        total = sum(i.quantidade for i in itens)
        exigida = categoria_marmita.required_quantity
        nome = categoria_marmita.food_category_name

        if total != exigida:
            if exigida == 0:
                raise _erro(f"A categoria '{nome}' não recebe escolhas nesta marmita.")
            raise _erro(f"Escolha exatamente {exigida} em '{nome}' (recebido: {total}).")

        for item in itens:
            alimento = alimentos[item.alimento_id]
            if alimento.composition_category_id != categoria_marmita.food_category_id:
                raise _erro(f"'{alimento.name}' não pertence à categoria '{nome}'.")
            escolhas.append(
                EscolhaValidada(categoria_marmita.food_category, alimento, item.quantidade)
            )

    _garantir_alimentos_disponiveis(db, [e.alimento for e in escolhas], hoje)
    return tuple(escolhas)


# ---------------------------------------------------------------------------
# Itens do pedido
# ---------------------------------------------------------------------------
def validar_item_avulso(
    db: Session, restaurante_id: uuid.UUID, item: ItemAvulsoIn, hoje: date | None = None
) -> Food:
    hoje = hoje or hoje_local()
    alimento = db.scalar(
        select(Food).where(Food.id == item.alimento_id, Food.restaurant_id == restaurante_id)
    )
    if alimento is None:
        raise _erro("Produto não encontrado neste restaurante.")

    categoria = alimento.sale_category
    if (
        not alimento.is_sellable_alone
        or alimento.standalone_price is None
        or categoria is None
        or categoria.type != "venda"
        or not categoria.is_active
    ):
        raise _erro(f"'{alimento.name}' não está à venda.")

    _garantir_alimentos_disponiveis(db, [alimento], hoje)
    return alimento


def validar_item_marmita(
    db: Session, restaurante_id: uuid.UUID, item: ItemMarmitaIn, hoje: date | None = None
) -> MarmitaValidada:
    hoje = hoje or hoje_local()
    marmita = _buscar_marmita(db, restaurante_id, item.marmita_id)
    _garantir_marmita_pedivel(db, marmita, hoje)

    if marmita.kind == MealBoxKind.READY:
        if item.selecoes:
            raise _erro(f"A marmita '{marmita.name}' é pronta e não aceita escolhas.")
        return MarmitaValidada(marmita, ())

    escolhas = _validar_configuracao(db, restaurante_id, marmita, item.selecoes, hoje)
    return MarmitaValidada(marmita, escolhas)


def validar_item_combo(
    db: Session, restaurante_id: uuid.UUID, item: ItemComboIn, hoje: date | None = None
) -> ComboValidado:
    hoje = hoje or hoje_local()
    combo = _buscar_combo(db, restaurante_id, item.combo_id)

    if combo.has_inactive_items:
        raise _erro(f"Combo '{combo.name}': indisponível no momento (item desativado).")
    _garantir_disponivel(db, combo, f"Combo '{combo.name}'", hoje)

    contexto = f"combo '{combo.name}'"
    for item_marmita in combo.meal_box_items:
        _garantir_marmita_pedivel(db, item_marmita.meal_box, hoje, contexto)
    _garantir_alimentos_disponiveis(db, [i.food for i in combo.food_items], hoje, contexto)

    # uma configuracao por UNIDADE de marmita personalizavel do combo
    esperadas = {
        i.meal_box_id: i.quantity
        for i in combo.meal_box_items
        if i.meal_box.kind == MealBoxKind.CUSTOMIZABLE
    }
    recebidas = Counter(m.marmita_id for m in item.marmitas)
    for marmita_id in recebidas:
        if marmita_id not in esperadas:
            raise _erro(
                "Configuração enviada para marmita que não é personalizável "
                f"ou não faz parte do combo '{combo.name}'."
            )

    validadas: list[MarmitaValidada] = []
    for item_marmita in combo.meal_box_items:
        if item_marmita.meal_box_id not in esperadas:
            continue
        marmita = item_marmita.meal_box
        if recebidas.get(marmita.id, 0) != item_marmita.quantity:
            raise _erro(
                f"Configure {item_marmita.quantity} unidade(s) da marmita '{marmita.name}' "
                f"(recebido: {recebidas.get(marmita.id, 0)})."
            )
        for entrada in item.marmitas:
            if entrada.marmita_id == marmita.id:
                escolhas = _validar_configuracao(
                    db, restaurante_id, marmita, entrada.selecoes, hoje
                )
                validadas.append(MarmitaValidada(marmita, escolhas))

    return ComboValidado(combo, tuple(validadas))
