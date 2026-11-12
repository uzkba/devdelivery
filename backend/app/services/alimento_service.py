import uuid
from typing import Literal, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.model.models import Food, FoodCategory, FoodComponent
from app.schemas.alimento_schemas import (
    AlimentoCreate,
    AlimentoUpdate,
    ComponenteIn,
    UnidadePorcao,
    validar_porcao,
    validar_regras_avulso,
)


def _get_categoria_ou_404(
    db: Session, categoria_id: uuid.UUID, restaurant_id: uuid.UUID, tipo: Optional[str] = None
) -> FoodCategory:
    categoria = db.query(FoodCategory).filter_by(id=categoria_id, restaurant_id=restaurant_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada para este restaurante")
    if tipo and categoria.type != tipo:
        raise HTTPException(status_code=422, detail=f"A categoria informada deve ser do tipo '{tipo}'.")
    return categoria


_CAMPOS_OPCIONAIS = {
    "serve_pessoas": "serves_people",
    "porcao_quantidade": "portion_amount",
    "porcao_unidade": "portion_unit",
    "tempo_preparo_minutos": "prep_time_minutes",
    "calorias_kcal": "calories_kcal",
    "proteina_g": "protein_g",
    "carboidrato_g": "carbs_g",
    "gordura_g": "fat_g",
}

_CAMPOS_SO_DE_PRATO = (
    "serve_pessoas",
    "tempo_preparo_minutos",
    "calorias_kcal",
    "proteina_g",
    "carboidrato_g",
    "gordura_g",
)


def validar_campos_de_bebida(grupo: Optional[str], valores: dict, componentes) -> None:
    if grupo != "bebida":
        return
    preenchidos = [c for c in _CAMPOS_SO_DE_PRATO if valores.get(c) is not None]
    if componentes:
        preenchidos.append("componentes")
    if preenchidos:
        raise ValueError("Item do grupo bebida não aceita: " + ", ".join(preenchidos) + ".")


def _montar_componentes(itens: list[ComponenteIn]) -> list[FoodComponent]:
    return [
        FoodComponent(name=item.nome, description=item.descricao, position=posicao)
        for posicao, item in enumerate(itens)
    ]


def get_alimento_por_id(db: Session, alimento_id: uuid.UUID, restaurant_id: uuid.UUID) -> Food:
    alimento = db.query(Food).filter_by(id=alimento_id, restaurant_id=restaurant_id).first()
    if not alimento:
        raise HTTPException(status_code=404, detail="Alimento não encontrado")
    return alimento


def listar_alimentos(
    db: Session,
    restaurant_id: uuid.UUID,
    categoria_id: Optional[uuid.UUID] = None,
    incluir_inativos: bool = False,
    vendavel_avulso: Optional[bool] = None,
    categoria_venda_id: Optional[uuid.UUID] = None,
    grupo: Optional[Literal["prato", "bebida"]] = None,
):
    query = db.query(Food).filter(Food.restaurant_id == restaurant_id)
    if not incluir_inativos:
        query = query.filter(Food.is_active.is_(True))
    if categoria_id:
        query = query.filter(Food.composition_category_id == categoria_id)
    if vendavel_avulso is not None:
        query = query.filter(Food.is_sellable_alone.is_(vendavel_avulso))
    if categoria_venda_id:
        query = query.filter(Food.sale_category_id == categoria_venda_id)
    if grupo:
        query = query.join(FoodCategory, Food.sale_category_id == FoodCategory.id).filter(
            FoodCategory.group == grupo
        )
    return query.all()


def criar_alimento(db: Session, payload: AlimentoCreate, restaurant_id: uuid.UUID) -> Food:
    if payload.categoria_id:
        _get_categoria_ou_404(db, payload.categoria_id, restaurant_id, tipo="composicao")
    grupo_venda = None
    if payload.categoria_venda_id:
        grupo_venda = _get_categoria_ou_404(db, payload.categoria_venda_id, restaurant_id, tipo="venda").group

    try:
        validar_campos_de_bebida(
            grupo_venda,
            {c: getattr(payload, c) for c in _CAMPOS_SO_DE_PRATO},
            payload.componentes,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    novo = Food(
        restaurant_id=restaurant_id,
        name=payload.nome,
        description=payload.descricao,
        composition_category_id=payload.categoria_id,
        sale_category_id=payload.categoria_venda_id,
        is_sellable_alone=payload.vendavel_avulso,
        standalone_price=payload.preco_avulso,
        is_featured=payload.destaque,
        serves_people=payload.serve_pessoas,
        portion_amount=payload.porcao_quantidade,
        portion_unit=payload.porcao_unidade.value if payload.porcao_unidade else None,
        prep_time_minutes=payload.tempo_preparo_minutos,
        calories_kcal=payload.calorias_kcal,
        protein_g=payload.proteina_g,
        carbs_g=payload.carboidrato_g,
        fat_g=payload.gordura_g,
        components=_montar_componentes(payload.componentes),
    )
    db.add(novo)
    db.commit()
    return get_alimento_por_id(db, novo.id, restaurant_id)


def atualizar_alimento(
    db: Session, alimento_id: uuid.UUID, payload: AlimentoUpdate, restaurant_id: uuid.UUID,
) -> Food:
    alimento = get_alimento_por_id(db, alimento_id, restaurant_id)
    dados = payload.model_dump(exclude_unset=True)

    for campo in ("nome", "vendavel_avulso", "destaque"):
        if dados.get(campo) is None:
            dados.pop(campo, None)

    if not dados:
        return alimento

    if dados.get("categoria_id"):
        _get_categoria_ou_404(db, dados["categoria_id"], restaurant_id, tipo="composicao")
    if dados.get("categoria_venda_id"):
        _get_categoria_ou_404(db, dados["categoria_venda_id"], restaurant_id, tipo="venda")

    if dados.get("vendavel_avulso") is False:
        dados.setdefault("preco_avulso", None)
        dados.setdefault("categoria_venda_id", None)

    try:
        validar_regras_avulso(
            dados.get("vendavel_avulso", alimento.is_sellable_alone),
            dados.get("preco_avulso", alimento.standalone_price),
            dados.get("categoria_venda_id", alimento.sale_category_id),
            dados.get("categoria_id", alimento.composition_category_id),
        )
        validar_porcao(
            dados.get("porcao_quantidade", alimento.portion_amount),
            dados.get("porcao_unidade", alimento.portion_unit),
        )
        id_venda_final = dados.get("categoria_venda_id", alimento.sale_category_id)
        grupo_final = (
            _get_categoria_ou_404(db, id_venda_final, restaurant_id, tipo="venda").group
            if id_venda_final
            else None
        )
        validar_campos_de_bebida(
            grupo_final,
            {
                c: dados[c] if c in dados else getattr(alimento, _CAMPOS_OPCIONAIS[c])
                for c in _CAMPOS_SO_DE_PRATO
            },
            payload.componentes if "componentes" in dados else alimento.components,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if "categoria_id" in dados:
        alimento.composition_category_id = dados["categoria_id"]
    if "categoria_venda_id" in dados:
        alimento.sale_category_id = dados["categoria_venda_id"]
    if "vendavel_avulso" in dados:
        alimento.is_sellable_alone = dados["vendavel_avulso"]
    if "preco_avulso" in dados:
        alimento.standalone_price = dados["preco_avulso"]
    if "destaque" in dados and dados["destaque"] is not None:
        alimento.is_featured = dados["destaque"]
    if "nome" in dados:
        alimento.name = dados["nome"]
    if "descricao" in dados:
        alimento.description = dados["descricao"]

    for campo, atributo in _CAMPOS_OPCIONAIS.items():
        if campo in dados:
            valor = dados[campo]
            if isinstance(valor, UnidadePorcao):
                valor = valor.value
            setattr(alimento, atributo, valor)

    if "componentes" in dados:
        alimento.components.clear()
        db.flush()
        alimento.components.extend(_montar_componentes(payload.componentes))

    db.commit()
    return get_alimento_por_id(db, alimento.id, restaurant_id)


def desativar_alimento(db: Session, alimento_id: uuid.UUID, restaurant_id: uuid.UUID):
    alimento = get_alimento_por_id(db, alimento_id, restaurant_id)

    if not alimento.is_active:
        raise HTTPException(status_code=400, detail="Alimento já está inativo.")

    alimento.is_active = False

    db.commit()