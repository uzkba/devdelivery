from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias_publicas import get_restaurante_publico
from app.core.database import get_db
from app.model.models import Restaurant
from app.schemas.cardapio_publico_schemas import CardapioHomeOut
from app.services import cardapio_publico_service as service

router = APIRouter(tags=["Cardápio público"])


@router.get("/restaurantes/{restaurante_id}/cardapio", response_model=CardapioHomeOut)
def cardapio_home(
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return service.montar_home(db, restaurante.id)