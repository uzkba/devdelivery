# backend/app/services/delivery_rule_service.py
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.model.models import DeliveryRule
from backend.app.schemas.regras_delivery_schemas import DeliveryRuleCreate

def criar_regra_entrega(db: Session, payload: DeliveryRuleCreate, restaurant_id: uuid.UUID) -> DeliveryRule:
    # Bloqueia regras que se sobrepõem no mesmo restaurante
    # A matemática do Overlap: (NovoMin < ExistenteMax) AND (NovoMax > ExistenteMin)
    sobreposicao = db.query(DeliveryRule).filter(
        DeliveryRule.restaurant_id == restaurant_id,
        DeliveryRule.is_active.is_(True),
        DeliveryRule.min_distance_km < payload.max_distance_km,
        DeliveryRule.max_distance_km > payload.min_distance_km
    ).first()

    if sobreposicao:
        raise HTTPException(
            status_code=400, 
            detail=f"Conflito de faixas: Já existe uma regra entre {sobreposicao.min_distance_km}km e {sobreposicao.max_distance_km}km."
        )

    nova_regra = DeliveryRule(
        restaurant_id=restaurant_id,
        min_distance_km=payload.min_distance_km,
        max_distance_km=payload.max_distance_km,
        fee=payload.fee,
        is_active=payload.is_active
    )
    
    db.add(nova_regra)
    db.commit()
    db.refresh(nova_regra)
    return nova_regra

def listar_regras(db: Session, restaurant_id: uuid.UUID):
    return db.query(DeliveryRule).filter(
        DeliveryRule.restaurant_id == restaurant_id,
        DeliveryRule.is_active.is_(True)
    ).order_by(DeliveryRule.min_distance_km.asc()).all()

def desativar_regra(db: Session, regra_id: uuid.UUID, restaurant_id: uuid.UUID):
    regra = db.query(DeliveryRule).filter_by(id=regra_id, restaurant_id=restaurant_id).first()
    if not regra:
        raise HTTPException(status_code=404, detail="Regra não encontrada.")
    
    # Soft delete: Não excluímos para manter histórico, apenas desativamos
    regra.is_active = False
    db.commit()