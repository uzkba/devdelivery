from decimal import Decimal

from backend.app.core.database import SessionLocal
from backend.app.model.models import Restaurant

LATITUDE = Decimal("-6.8990")
LONGITUDE = Decimal("-37.5218")


def main():
    db = SessionLocal()
    try:
        restaurante = db.query(Restaurant).filter(Restaurant.is_active == True).first()  # noqa: E712
        if restaurante is None:
            print("Nenhum restaurante ativo encontrado.")
            return

        restaurante.latitude = LATITUDE
        restaurante.longitude = LONGITUDE
        db.commit()
        print(f"Coordenadas atualizadas para o restaurante {restaurante.trade_name} (id={restaurante.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()