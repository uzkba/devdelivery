from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.model.models import Restaurant
from app.schemas.restaurante_schemas import RestaurantOut


router = APIRouter(prefix="/restaurante", tags=["Restaurante"])


@router.get("", response_model=RestaurantOut)
def buscar_restaurante(
    db: Session = Depends(get_db),
):
    restaurante = (
        db.query(Restaurant)
        .filter(Restaurant.is_active == True)
        .first()
    )

    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum restaurante ativo encontrado.",
        )

    return restaurante
