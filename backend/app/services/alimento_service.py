import uuid
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from backend.app.model.models import Food, FoodCategory, ModifierGroup, ModifierOption
from backend.app.schemas.alimento_schemas import AlimentoCreate, AlimentoUpdate

def _get_categoria_ou_404(db: Session, categoria_id: uuid.UUID, restaurant_id: uuid.UUID) -> FoodCategory:
    categoria = db.query(FoodCategory).filter_by(id=categoria_id, restaurant_id=restaurant_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada para este restaurante")
    return categoria

def get_alimento_por_id(db: Session, alimento_id: uuid.UUID, restaurant_id: uuid.UUID) -> Food:
    alimento = (
        db.query(Food)
        .options(joinedload(Food.modifier_groups).joinedload(ModifierGroup.options))
        .filter_by(id=alimento_id, restaurant_id=restaurant_id)
        .first()
    )
    if not alimento:
        raise HTTPException(status_code=404, detail="Alimento não encontrado")
    return alimento

def listar_alimentos(
    db: Session, restaurant_id: uuid.UUID, categoria_id: uuid.UUID = None, incluir_inativos: bool = False
):
    query = (
        db.query(Food)
        .options(joinedload(Food.modifier_groups).joinedload(ModifierGroup.options))
        .filter(Food.restaurant_id == restaurant_id)
    )
    if not incluir_inativos:
        query = query.filter(Food.is_active.is_(True), Food.is_available.is_(True))
    if categoria_id:
        query = query.filter(Food.category_id == categoria_id)
    return query.all()

def criar_alimento(db: Session, payload: AlimentoCreate, restaurant_id: uuid.UUID) -> Food:
    _get_categoria_ou_404(db, payload.categoria_id, restaurant_id)
    
    novo = Food(
        restaurant_id=restaurant_id,
        category_id=payload.categoria_id,
        name=payload.nome,
        description=payload.descricao,
        base_price=payload.preco_base,
    )
    db.add(novo)
    db.flush()

    if payload.grupos_complemento:
        for g_data in payload.grupos_complemento:
            grupo = ModifierGroup(
                food_id=novo.id,
                name=g_data.nome,
                min_choices=g_data.escolhas_minimas,
                max_choices=g_data.escolhas_maximas
            )
            db.add(grupo)
            db.flush()

            for o_data in g_data.opcoes:
                opcao = ModifierOption(
                    group_id=grupo.id,
                    name=o_data.nome,
                    extra_price=o_data.preco_adicional,
                    is_available=o_data.disponivel
                )
                db.add(opcao)

    db.commit()
    return get_alimento_por_id(db, novo.id, restaurant_id)

def atualizar_alimento(db: Session, alimento_id: uuid.UUID, payload: AlimentoUpdate, restaurant_id: uuid.UUID) -> Food:
    alimento = get_alimento_por_id(db, alimento_id, restaurant_id)
    dados = payload.model_dump(exclude_unset=True)
    
    if "categoria_id" in dados:
        _get_categoria_ou_404(db, dados["categoria_id"], restaurant_id)
        alimento.category_id = dados["categoria_id"]
    if "nome" in dados:
        alimento.name = dados["nome"]
    if "descricao" in dados:
        alimento.description = dados["descricao"]
    if "preco_base" in dados:
        alimento.base_price = dados["preco_base"]
        
    db.commit()
    return get_alimento_por_id(db, alimento.id, restaurant_id)

def desativar_alimento(db: Session, alimento_id: uuid.UUID, restaurant_id: uuid.UUID):
    alimento = get_alimento_por_id(db, alimento_id, restaurant_id)
    alimento.is_active = False
    db.commit()