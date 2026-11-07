import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_local
from app.model.models import Combo, Food, FoodCategory, MealBox, MealBoxKind
from app.services import disponibilidade_service as disponibilidade
from app.services.cardapio_publico_service import preco_referencia_combo


def _nao_encontrado(nome: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{nome} não encontrado.")


def _disponibilidade(db: Session, alvo, hoje: date, estrutural: str | None = None) -> dict:
    estado = disponibilidade.estado_hoje(db, alvo, hoje)
    if not estado.serve_hoje:
        motivo = "fora_do_dia"
    elif estado.esgotado_hoje:
        motivo = "esgotado_hoje"
    else:
        motivo = estrutural
    return {"disponivel": motivo is None, "motivo_indisponivel": motivo}


def _nutricao(calorias, proteina, carboidrato, gordura) -> dict | None:
    valores = {
        "calorias_kcal": calorias,
        "proteina_g": proteina,
        "carboidrato_g": carboidrato,
        "gordura_g": gordura,
    }
    return None if all(v is None for v in valores.values()) else valores


# ------------------------------ marmita ------------------------------
def _categorias_para_escolha(
    db: Session, restaurant_id: uuid.UUID, caixa: MealBox, hoje: date
) -> list[dict]:
    ativas = [c.food_category_id for c in caixa.categories if c.food_category.is_active]
    por_categoria: dict[uuid.UUID, list[Food]] = {cid: [] for cid in ativas}
    if ativas:
        alimentos = db.scalars(
            select(Food)
            .where(
                Food.restaurant_id == restaurant_id,
                Food.is_active.is_(True),
                Food.composition_category_id.in_(ativas),
            )
            .order_by(Food.name)
        ).all()
        servem = disponibilidade.servem_hoje(db, Food, [f.id for f in alimentos], hoje)
        for alimento in alimentos:
            if alimento.id in servem and not disponibilidade.esgotado_hoje(alimento, hoje):
                por_categoria[alimento.composition_category_id].append(alimento)

    return [
        {
            "categoria_id": c.food_category_id,
            "nome": c.food_category.name,
            "quantidade_exigida": c.required_quantity,
            "opcoes": [
                {
                    "alimento_id": f.id,
                    "nome": f.name,
                    "descricao": f.description,
                    "imagem_url": f.image_url,
                }
                for f in por_categoria.get(c.food_category_id, [])
            ],
        }
        for c in caixa.categories
    ]


def detalhar_marmita(
    db: Session, restaurant_id: uuid.UUID, marmita_id: uuid.UUID, hoje: date | None = None
) -> dict:
    hoje = hoje or hoje_local()
    caixa = db.scalar(
        select(MealBox).where(
            MealBox.id == marmita_id,
            MealBox.restaurant_id == restaurant_id,
            MealBox.is_active.is_(True),
        )
    )
    if caixa is None:
        raise _nao_encontrado("Marmita")

    pronta = caixa.kind == MealBoxKind.READY
    categorias = [] if pronta else _categorias_para_escolha(db, restaurant_id, caixa, hoje)
    sem_opcoes = any(c["quantidade_exigida"] > 0 and not c["opcoes"] for c in categorias)

    return {
        "id": caixa.id,
        "nome": caixa.name,
        "descricao": caixa.description,
        "preco": caixa.price,
        "imagem_url": caixa.image_url,
        "tipo": caixa.kind,
        "tamanho": caixa.size,
        "nutricao": (
            _nutricao(caixa.calories_kcal, caixa.protein_g, caixa.carbs_g, caixa.fat_g)
            if pronta
            else None
        ),
        "composicao": [
            {
                "alimento_id": i.food_id,
                "nome": i.food.name,
                "descricao": i.food.description,
                "quantidade": i.fixed_quantity,
            }
            for i in caixa.composition
        ]
        if pronta
        else [],
        "categorias": categorias,
        **_disponibilidade(db, caixa, hoje, "sem_opcoes" if sem_opcoes else None),
    }


# ------------------------------ combo ------------------------------
def detalhar_combo(
    db: Session, restaurant_id: uuid.UUID, combo_id: uuid.UUID, hoje: date | None = None
) -> dict:
    hoje = hoje or hoje_local()
    combo = db.scalar(
        select(Combo).where(
            Combo.id == combo_id,
            Combo.restaurant_id == restaurant_id,
            Combo.is_active.is_(True),
        )
    )
    if combo is None:
        raise _nao_encontrado("Combo")

    referencia = preco_referencia_combo(combo)
    return {
        "id": combo.id,
        "nome": combo.name,
        "descricao": combo.description,
        "preco": combo.price,
        "imagem_url": combo.image_url,
        "preco_referencia": referencia,
        "economia": referencia - combo.price if referencia is not None else None,
        "possui_marmita_personalizavel": combo.has_customizable_meal_box,
        "itens_marmita": [
            {
                "marmita_id": i.meal_box_id,
                "nome": i.meal_box.name,
                "tipo": i.meal_box.kind,
                "quantidade": i.quantity,
            }
            for i in combo.meal_box_items
        ],
        "itens_alimento": [
            {"alimento_id": i.food_id, "nome": i.food.name, "quantidade": i.quantity}
            for i in combo.food_items
        ],
        **_disponibilidade(
            db, combo, hoje, "item_indisponivel" if combo.has_inactive_items else None
        ),
    }


# ------------------------------ produto avulso ------------------------------
def detalhar_produto(
    db: Session, restaurant_id: uuid.UUID, produto_id: uuid.UUID, hoje: date | None = None
) -> dict:
    hoje = hoje or hoje_local()
    linha = db.execute(
        select(Food, FoodCategory)
        .join(FoodCategory, Food.sale_category_id == FoodCategory.id)
        .where(
            Food.id == produto_id,
            Food.restaurant_id == restaurant_id,
            Food.is_active.is_(True),
            Food.is_sellable_alone.is_(True),
            FoodCategory.restaurant_id == restaurant_id,
            FoodCategory.type == "venda",
            FoodCategory.is_active.is_(True),
        )
    ).first()
    if linha is None:
        raise _nao_encontrado("Produto")
    alimento, categoria = linha

    return {
        "id": alimento.id,
        "nome": alimento.name,
        "descricao": alimento.description,
        "preco": alimento.standalone_price,
        "imagem_url": alimento.image_url,
        "grupo": categoria.group,
        "categoria": {"id": categoria.id, "nome": categoria.name},
        "serve_pessoas": alimento.serves_people,
        "porcao": (
            {"quantidade": alimento.portion_amount, "unidade": alimento.portion_unit}
            if alimento.portion_amount is not None
            else None
        ),
        "tempo_preparo_minutos": alimento.prep_time_minutes,
        "nutricao": _nutricao(
            alimento.calories_kcal, alimento.protein_g, alimento.carbs_g, alimento.fat_g
        ),
        "componentes": [
            {"nome": c.name, "descricao": c.description} for c in alimento.components
        ],
        **_disponibilidade(db, alimento, hoje),
    }