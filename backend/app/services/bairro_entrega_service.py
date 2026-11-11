import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.texto import chave_comparacao
from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    RestaurantDeliverySettings,
)
from app.schemas.bairro_entrega_schemas import BairroIn


def listar_bairros(db: Session, restaurant_id: uuid.UUID) -> list[DeliveryRuleNeighborhood]:
    return (
        db.query(DeliveryRuleNeighborhood)
        .filter(DeliveryRuleNeighborhood.restaurant_id == restaurant_id)
        .order_by(DeliveryRuleNeighborhood.neighborhood)
        .all()
    )


def _buscar(db: Session, restaurant_id: uuid.UUID, bairro_id: uuid.UUID) -> DeliveryRuleNeighborhood:
    bairro = (
        db.query(DeliveryRuleNeighborhood)
        .filter(
            DeliveryRuleNeighborhood.id == bairro_id,
            DeliveryRuleNeighborhood.restaurant_id == restaurant_id,
        )
        .first()
    )
    if bairro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bairro não encontrado.")
    return bairro


def _garantir_nome_livre(
    db: Session, restaurant_id: uuid.UUID, nome: str, ignorar_id: uuid.UUID | None = None
) -> None:
    chave = chave_comparacao(nome)
    for existente in listar_bairros(db, restaurant_id):
        if existente.id != ignorar_id and chave_comparacao(existente.neighborhood) == chave:
            raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um bairro com este nome.")


def _modo_bairro_ligado(db: Session, restaurant_id: uuid.UUID) -> bool:
    modo = (
        db.query(RestaurantDeliverySettings.charge_mode)
        .filter(RestaurantDeliverySettings.restaurant_id == restaurant_id)
        .scalar()
    )
    return modo == DeliveryChargeMode.BAIRRO


def _garantir_que_sobra_bairro_ativo(
    db: Session, restaurant_id: uuid.UUID, bairro: DeliveryRuleNeighborhood
) -> None:
    if not bairro.is_active or not _modo_bairro_ligado(db, restaurant_id):
        return
    outros_ativos = (
        db.query(func.count(DeliveryRuleNeighborhood.id))
        .filter(
            DeliveryRuleNeighborhood.restaurant_id == restaurant_id,
            DeliveryRuleNeighborhood.is_active.is_(True),
            DeliveryRuleNeighborhood.id != bairro.id,
        )
        .scalar()
    )
    if outros_ativos == 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Este é o último bairro ativo e a cobrança por bairro está ligada. "
            "Troque o modo de cobrança antes de desativá-lo ou apagá-lo.",
        )


def criar_bairro(
    db: Session, restaurant_id: uuid.UUID, payload: BairroIn
) -> DeliveryRuleNeighborhood:
    _garantir_nome_livre(db, restaurant_id, payload.bairro)
    bairro = DeliveryRuleNeighborhood(
        restaurant_id=restaurant_id,
        neighborhood=payload.bairro,
        fee=payload.taxa,
        is_active=payload.ativo,
    )
    db.add(bairro)
    db.commit()
    db.refresh(bairro)
    return bairro


def atualizar_bairro(
    db: Session, restaurant_id: uuid.UUID, bairro_id: uuid.UUID, payload: BairroIn
) -> DeliveryRuleNeighborhood:
    bairro = _buscar(db, restaurant_id, bairro_id)
    _garantir_nome_livre(db, restaurant_id, payload.bairro, ignorar_id=bairro.id)
    if not payload.ativo:
        _garantir_que_sobra_bairro_ativo(db, restaurant_id, bairro)

    bairro.neighborhood = payload.bairro
    bairro.fee = payload.taxa
    bairro.is_active = payload.ativo
    db.commit()
    db.refresh(bairro)
    return bairro


def remover_bairro(db: Session, restaurant_id: uuid.UUID, bairro_id: uuid.UUID) -> None:
    bairro = _buscar(db, restaurant_id, bairro_id)
    _garantir_que_sobra_bairro_ativo(db, restaurant_id, bairro)
    db.delete(bairro)
    db.commit()