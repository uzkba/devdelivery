"""
app/services/tamanho_marmita_service.py

Regras de negócio de Tamanho de Marmita e dos limites de quantidade
por categoria:
- nome de tamanho único por restaurante (mesmo padrão de categoria_alimento)
- delete é soft-delete (mantém histórico em cardapio_item que já referencia
  o tamanho)
- limite de quantidade é upsert (definir de novo sobrescreve o valor
  anterior) e não pode ser definido para a categoria marcada como
  prato_principal (não faz sentido limitar "quantas marmitas" dentro da
  própria marmita)
"""
import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.model.models import FoodCategory, MarmitaSize, SizeCategoryLimit
from backend.app.schemas.tamanho_marmita_schemas import (
    LimiteCategoriaTamanhoSet,
    TamanhoMarmitaCreate,
    TamanhoMarmitaUpdate,
)


def _buscar_por_nome(db: Session, restaurant_id: uuid.UUID, nome: str, excluir_id: uuid.UUID | None = None):
    query = db.query(MarmitaSize).filter(
        MarmitaSize.restaurant_id == restaurant_id,
        func.lower(MarmitaSize.name) == nome.lower(),
    )
    if excluir_id is not None:
        query = query.filter(MarmitaSize.id != excluir_id)
    return query.first()


def criar_tamanho(db: Session, restaurant_id: uuid.UUID, dados: TamanhoMarmitaCreate) -> MarmitaSize:
    if _buscar_por_nome(db, restaurant_id, dados.nome):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe um tamanho de marmita com o nome '{dados.nome}' neste restaurante.",
        )
    tamanho = MarmitaSize(restaurant_id=restaurant_id, name=dados.nome, display_order=dados.ordem_exibicao)
    db.add(tamanho)
    db.commit()
    db.refresh(tamanho)
    return tamanho


def listar_tamanhos(db: Session, restaurant_id: uuid.UUID, apenas_ativos: bool = False) -> List[MarmitaSize]:
    query = db.query(MarmitaSize).filter(MarmitaSize.restaurant_id == restaurant_id)
    if apenas_ativos:
        query = query.filter(MarmitaSize.is_active.is_(True))
    return query.order_by(MarmitaSize.display_order, MarmitaSize.name).all()


def buscar_tamanho_por_id(db: Session, restaurant_id: uuid.UUID, tamanho_id: uuid.UUID) -> MarmitaSize:
    tamanho = (
        db.query(MarmitaSize)
        .filter(MarmitaSize.id == tamanho_id, MarmitaSize.restaurant_id == restaurant_id)
        .first()
    )
    if not tamanho:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tamanho de marmita {tamanho_id} não encontrado.",
        )
    return tamanho


def atualizar_tamanho(
    db: Session, restaurant_id: uuid.UUID, tamanho_id: uuid.UUID, dados: TamanhoMarmitaUpdate
) -> MarmitaSize:
    tamanho = buscar_tamanho_por_id(db, restaurant_id, tamanho_id)
    atualizacoes = dados.model_dump(exclude_unset=True)

    if atualizacoes.get("nome") is not None:
        if _buscar_por_nome(db, restaurant_id, atualizacoes["nome"], excluir_id=tamanho_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um tamanho de marmita com o nome '{atualizacoes['nome']}' neste restaurante.",
            )
        tamanho.name = atualizacoes["nome"]

    if "ordem_exibicao" in atualizacoes and atualizacoes["ordem_exibicao"] is not None:
        tamanho.display_order = atualizacoes["ordem_exibicao"]
    if "ativo" in atualizacoes and atualizacoes["ativo"] is not None:
        tamanho.is_active = atualizacoes["ativo"]

    db.commit()
    db.refresh(tamanho)
    return tamanho


def remover_tamanho(db: Session, restaurant_id: uuid.UUID, tamanho_id: uuid.UUID) -> MarmitaSize:
    """Soft-delete: mantém histórico em cardapio_item que já referencia este tamanho."""
    tamanho = buscar_tamanho_por_id(db, restaurant_id, tamanho_id)
    tamanho.is_active = False
    db.commit()
    db.refresh(tamanho)
    return tamanho


def definir_limite(
    db: Session, restaurant_id: uuid.UUID, tamanho_id: uuid.UUID, dados: LimiteCategoriaTamanhoSet
) -> SizeCategoryLimit:
    """Cria ou atualiza (upsert) o limite de quantidade de uma categoria para um tamanho."""
    tamanho = buscar_tamanho_por_id(db, restaurant_id, tamanho_id)

    categoria = (
        db.query(FoodCategory)
        .filter(FoodCategory.id == dados.categoria_id, FoodCategory.restaurant_id == restaurant_id)
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria {dados.categoria_id} não encontrada neste restaurante.",
        )
    if categoria.is_main_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível definir limite de quantidade para a categoria do prato principal.",
        )

    limite = (
        db.query(SizeCategoryLimit)
        .filter(SizeCategoryLimit.size_id == tamanho.id, SizeCategoryLimit.category_id == categoria.id)
        .first()
    )
    if limite:
        limite.max_quantity = dados.quantidade_maxima
    else:
        limite = SizeCategoryLimit(
            size_id=tamanho.id, category_id=categoria.id, max_quantity=dados.quantidade_maxima
        )
        db.add(limite)

    db.commit()
    db.refresh(limite)
    return limite


def listar_limites(db: Session, restaurant_id: uuid.UUID, tamanho_id: uuid.UUID) -> List[SizeCategoryLimit]:
    tamanho = buscar_tamanho_por_id(db, restaurant_id, tamanho_id)
    return tamanho.limits