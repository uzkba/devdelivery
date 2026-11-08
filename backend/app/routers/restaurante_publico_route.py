from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias_publicas import get_restaurante_publico
from app.core.database import get_db
from app.model.models import Restaurant
from app.schemas.restaurante_publico_schemas import RestaurantePublicoOut
from app.services import restaurante_publico_service as service

router = APIRouter(tags=["Restaurante público"])


@router.get("/restaurantes/{slug}", response_model=RestaurantePublicoOut)
def dados_publicos_do_restaurante(
    restaurante: Restaurant = Depends(get_restaurante_publico),
    db: Session = Depends(get_db),
):
    return service.montar_restaurante_publico(db, restaurante)