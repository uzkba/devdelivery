"""
app/services/categoria_alimento_service.py

Regras de negócio do CRUD de categoria de alimento:
- toda operação é escopada por restaurante (restaurant_id vem do usuário
  autenticado, nunca do client)
- nome único por restaurante (case-insensitive) — bate com a
  UniqueConstraint("restaurante_id", "nome") que já existe no model
- delete é soft-delete (ativo=False): Food.category_id é FK NOT NULL sem
  ondelete, então apagar de verdade quebraria alimentos já cadastrados
  (relevante para a task #15, de outro colega)
"""
import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.model.models import FoodCategory
from backend.app.schemas.categoria_alimento_schemas import (
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
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def listar_categorias(db: Session, restaurant_id: uuid.UUID, apenas_ativas: bool = False) -> List[FoodCategory]:
    query = db.query(FoodCategory).filter(FoodCategory.restaurant_id == restaurant_id)
    if apenas_ativas:
        query = query.filter(FoodCategory.is_active.is_(True))
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


def remover_categoria(db: Session, restaurant_id: uuid.UUID, categoria_id: uuid.UUID) -> FoodCategory:
    """Soft-delete: marca ativo=False. Não apaga a linha porque Food.category_id
    é FK NOT NULL para categoria_alimento sem ondelete — um DELETE real falharia
    (ou pior, seria bloqueado) assim que houver algum alimento na categoria."""
    categoria = buscar_categoria_por_id(db, restaurant_id, categoria_id)
    categoria.is_active = False
    db.commit()
    db.refresh(categoria)
    return categoria