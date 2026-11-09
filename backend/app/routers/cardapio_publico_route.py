import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias_publicas import get_restaurante_publico
from app.core.database import get_db
from app.model.models import Restaurant
from app.schemas.cardapio_publico_schemas import CardapioHomeOut
from app.schemas.detalhe_publico_schemas import (
    ComboDetalheOut,
    MarmitaDetalheOut,
    ProdutoDetalheOut,
)
from app.services import cardapio_publico_service as service
from app.services import detalhe_publico_service as detalhes

router = APIRouter(tags=["Cardápio público"])


@router.get("/restaurantes/{slug}/cardapio", response_model=CardapioHomeOut)
def cardapio_home(
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return service.montar_home(db, restaurante.id)


@router.get("/restaurantes/{slug}/marmitas/{marmita_id}", response_model=MarmitaDetalheOut)
def detalhe_marmita(
    marmita_id: uuid.UUID,
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return detalhes.detalhar_marmita(db, restaurante.id, marmita_id)


@router.get("/restaurantes/{slug}/combos/{combo_id}", response_model=ComboDetalheOut)
def detalhe_combo(
    combo_id: uuid.UUID,
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return detalhes.detalhar_combo(db, restaurante.id, combo_id)


@router.get("/restaurantes/{slug}/produtos/{produto_id}", response_model=ProdutoDetalheOut)
def detalhe_produto(
    produto_id: uuid.UUID,
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return detalhes.detalhar_produto(db, restaurante.id, produto_id)