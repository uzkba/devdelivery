import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.app.core.database import get_db
from backend.app.api.depedencias import get_current_user 
from backend.app.model.models import Food, FoodCategory
from backend.app.schemas.alimento_schemas import AlimentoCreate, AlimentoUpdate, AlimentoOut

router = APIRouter(prefix="/alimentos", tags=["Alimentos"])

# TODO: role check está inline aqui; se mais rotas precisarem de admin-only,
# extrair pra dependency reutilizável em dependencias.py (ver require_admin)
def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user


def _get_categoria_do_restaurante_ou_404(db, categoria_id, restaurant_id):
    categoria = (
        db.query(FoodCategory)
        .filter(FoodCategory.id == categoria_id, FoodCategory.restaurant_id == restaurant_id)
        .first()
    )
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada para este restaurante")
    return categoria


def _get_alimento_do_restaurante_ou_404(db, alimento_id, restaurant_id):
    alimento = (
        db.query(Food)
        .filter(Food.id == alimento_id, Food.restaurant_id == restaurant_id)
        .first()
    )
    if not alimento:
        raise HTTPException(status_code=404, detail="Alimento não encontrado")
    return alimento


def _to_out(alimento: Food) -> AlimentoOut:
    return AlimentoOut(
        id=alimento.id,
        nome=alimento.name,
        descricao=alimento.description,
        preco_base=alimento.base_price,
        categoria_id=alimento.category_id,
        ativo=alimento.is_active,
        disponivel=alimento.is_available,
    )


@router.post("", response_model=AlimentoOut, status_code=status.HTTP_201_CREATED)
def criar_alimento(payload: AlimentoCreate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    _get_categoria_do_restaurante_ou_404(db, payload.categoria_id, current_user.restaurant_id)
    novo = Food(
        restaurant_id=current_user.restaurant_id,
        category_id=payload.categoria_id,
        name=payload.nome,
        description=payload.descricao,
        base_price=payload.preco_base,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return _to_out(novo)


@router.get("", response_model=List[AlimentoOut])
def listar_alimentos(
    categoria_id: Optional[uuid.UUID] = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    query = db.query(Food).filter(Food.restaurant_id == current_user.restaurant_id)
    if not incluir_inativos:
        query = query.filter(Food.is_active.is_(True), Food.is_available.is_(True))
    if categoria_id is not None:
        query = query.filter(Food.category_id == categoria_id)
    return [_to_out(f) for f in query.all()]


@router.get("/{alimento_id}", response_model=AlimentoOut)
def detalhar_alimento(alimento_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return _to_out(_get_alimento_do_restaurante_ou_404(db, alimento_id, current_user.restaurant_id))


@router.put("/{alimento_id}", response_model=AlimentoOut)
def atualizar_alimento(
    alimento_id: uuid.UUID,
    payload: AlimentoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    alimento = _get_alimento_do_restaurante_ou_404(db, alimento_id, current_user.restaurant_id)
    dados = payload.model_dump(exclude_unset=True)
    if "categoria_id" in dados:
        _get_categoria_do_restaurante_ou_404(db, dados["categoria_id"], current_user.restaurant_id)
        alimento.category_id = dados["categoria_id"]
    if "nome" in dados:
        alimento.name = dados["nome"]
    if "descricao" in dados:
        alimento.description = dados["descricao"]
    if "preco_base" in dados:
        alimento.base_price = dados["preco_base"]
    db.commit()
    db.refresh(alimento)
    return _to_out(alimento)


@router.delete("/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_alimento(alimento_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    alimento = _get_alimento_do_restaurante_ou_404(db, alimento_id, current_user.restaurant_id)
    alimento.is_active = False
    db.commit()