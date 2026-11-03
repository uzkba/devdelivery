"""
app/services/categoria_alimento_service.py

Regras de negócio do CRUD de categoria de alimento:
- toda operação é escopada por restaurante (restaurant_id vem do usuário
  autenticado, nunca do client)
- nome único por restaurante (case-insensitive), alinhado à
  UniqueConstraint("restaurante_id", "nome") do model
- `tipo` (composicao | venda) é definido na criação e não muda
- delete é soft-delete (ativo=False) e é BLOQUEADO (409) se ainda houver
  alimento ativo usando a categoria
"""
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.model.models import Food, FoodCategory
from app.schemas.categoria_alimento_schemas import (
    CategoriaAlimentoCreate,
    CategoriaAlimentoUpdate,
)


def _buscar_por_nome(db: Session, restaurant_id: uuid.UUID, nome: str, excluir_id: uuid.UUID | None = None):
    query = db.query(FoodCategory).filter(
        FoodCategory.restaurant_id == restaurant_id,
        func.lower(FoodCategory.name) == nome.lower(),
    )
    if excluir_id is not None:
        query = query.filter(FoodCategory.id != excluir_id)
    return query.first()


def criar_categoria(db: Session, restaurant_id: uuid.UUID, dados: CategoriaAlimentoCreate) -> FoodCategory:
    if _buscar_por_nome(db, restaurant_id, dados.nome):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe uma categoria com o nome '{dados.nome}' neste restaurante.",
        )

    categoria = FoodCategory(
        restaurant_id=restaurant_id,
        name=dados.nome,
        description=dados.descricao,
        display_order=dados.ordem_exibicao,
        type=dados.tipo,
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def listar_categorias(
    db: Session,
    restaurant_id: uuid.UUID,
    apenas_ativas: bool = False,
    tipo: Optional[str] = None,
) -> List[FoodCategory]:
    query = db.query(FoodCategory).filter(FoodCategory.restaurant_id == restaurant_id)
    if apenas_ativas:
        query = query.filter(FoodCategory.is_active.is_(True))
    if tipo:
        query = query.filter(FoodCategory.type == tipo)
    return query.order_by(FoodCategory.display_order, FoodCategory.name).all()


def buscar_categoria_por_id(db: Session, restaurant_id: uuid.UUID, categoria_id: uuid.UUID) -> FoodCategory:
    categoria = (
        db.query(FoodCategory)
        .filter(FoodCategory.id == categoria_id, FoodCategory.restaurant_id == restaurant_id)
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria {categoria_id} não encontrada.",
        )
    return categoria


def atualizar_categoria(
    db: Session, restaurant_id: uuid.UUID, categoria_id: uuid.UUID, dados: CategoriaAlimentoUpdate
) -> FoodCategory:
    categoria = buscar_categoria_por_id(db, restaurant_id, categoria_id)

    atualizacoes = dados.model_dump(exclude_unset=True)

    if atualizacoes.get("nome") is not None:
        if _buscar_por_nome(db, restaurant_id, atualizacoes["nome"], excluir_id=categoria_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe uma categoria com o nome '{atualizacoes['nome']}' neste restaurante.",
            )
        categoria.name = atualizacoes["nome"]

    if "descricao" in atualizacoes:
        categoria.description = atualizacoes["descricao"]
    if "ordem_exibicao" in atualizacoes and atualizacoes["ordem_exibicao"] is not None:
        categoria.display_order = atualizacoes["ordem_exibicao"]
    if "ativo" in atualizacoes and atualizacoes["ativo"] is not None:
        categoria.is_active = atualizacoes["ativo"]

    db.commit()
    db.refresh(categoria)
    return categoria


def _categoria_em_uso(db: Session, categoria: FoodCategory) -> bool:
    """True se existe alimento ATIVO apontando para a categoria.
    Composição: considera também o legado Food.category_id."""
    if categoria.type == "venda":
        filtro = Food.sale_category_id == categoria.id
    else:
        filtro = or_(Food.composition_category_id == categoria.id, Food.category_id == categoria.id)
    return db.query(Food.id).filter(filtro, Food.is_active.is_(True)).first() is not None


def remover_categoria(db: Session, restaurant_id: uuid.UUID, categoria_id: uuid.UUID) -> FoodCategory:
    """Soft-delete: marca ativo=False. Não apaga a linha (FKs de alimento e de
    marmita_categoria apontam para ela)."""
    categoria = buscar_categoria_por_id(db, restaurant_id, categoria_id)

    if _categoria_em_uso(db, categoria):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Categoria possui alimentos ativos. Mova ou desative-os antes.",
        )

    categoria.is_active = False
    db.commit()
    db.refresh(categoria)
    return categoria