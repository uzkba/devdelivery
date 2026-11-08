from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.model.models import Restaurant


def get_restaurante_publico(slug: str, db: Session = Depends(get_db)) -> Restaurant:
    restaurante = db.query(Restaurant).filter(Restaurant.slug == slug.lower()).first()
    if restaurante is None or not restaurante.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurante não encontrado.")
    return restaurante