# backend/scripts/criar_cardapio_hoje.py
from datetime import date

from backend.app.core.database import SessionLocal
from backend.app.model.models import Menu, MenuItem, Restaurant

ITENS = [
    {"alimento_id": "04865528-4a20-4281-9e83-e154383ff53d", "preco_dia": 8.00, "disponivel": True},
    {"alimento_id": "0826b84e-80c7-40ea-b448-31379a558454", "preco_dia": 9.50, "disponivel": True},
    {"alimento_id": "8adfd920-1b1a-4597-8066-becbfd23517d", "preco_dia": 11.00, "disponivel": True},
    {"alimento_id": "e2f4ecd5-e4f3-4a48-a49c-84e03be9a2a4", "preco_dia": 18.00, "disponivel": True},
    {"alimento_id": "a8a31523-0b47-4088-a082-d79162e9c763", "preco_dia": 7.00, "disponivel": True},
    {"alimento_id": "73fa9a0d-5551-42c8-ba0b-c30c1c9e837a", "preco_dia": 14.00, "disponivel": True},
    {"alimento_id": "ada2d11b-e4e3-4ceb-b0d7-0e6a511eaec2", "preco_dia": 12.00, "disponivel": True},
    {"alimento_id": "15dc1639-07f1-43bf-9a5a-9df83d91ab89", "preco_dia": 8.00, "disponivel": True},
    {"alimento_id": "c07a0dc5-20f2-4d53-bf84-2dee8674c11c", "preco_dia": 38.00, "disponivel": True},
    {"alimento_id": "0394b6cb-62c0-48b4-a7df-e8ec18eeffe1", "preco_dia": 22.00, "disponivel": True},
    {"alimento_id": "c347e86a-e763-4686-b949-6862c1e54e53", "preco_dia": 34.00, "disponivel": True},
    {"alimento_id": "6dabd098-00e5-44f0-872e-dcdca031578f", "preco_dia": 36.00, "disponivel": True},
    {"alimento_id": "5fffd18a-1a52-44d1-8240-db96d1b47389", "preco_dia": 16.00, "disponivel": True},
    {"alimento_id": "be5c387f-8105-46c1-96f3-ef71014c56d0", "preco_dia": 8.00, "disponivel": True},
    {"alimento_id": "bb8d0f63-f185-45b1-bf17-0fbb07cd005e", "preco_dia": 12.00, "disponivel": True},
    {"alimento_id": "2974d05a-7cd5-4c46-b26c-f9b2fe35a601", "preco_dia": 10.00, "disponivel": True},
    {"alimento_id": "85559acc-3cb6-42b2-b381-e86a58420b2f", "preco_dia": 24.00, "disponivel": True},
    {"alimento_id": "80d25593-a481-40eb-851f-2922c76a7813", "preco_dia": 12.00, "disponivel": True},
    {"alimento_id": "544ddb67-c6cb-4685-b5b8-499fa26f72ce", "preco_dia": 22.00, "disponivel": True},
    {"alimento_id": "c6cd7743-ce68-457e-8c27-a97abcc2e287", "preco_dia": 26.00, "disponivel": True},
    {"alimento_id": "ea45bead-610a-4af5-b9fa-6938ec975063", "preco_dia": 9.00, "disponivel": True},
    {"alimento_id": "fa3e3e34-f544-4d1f-8ea3-1ad7bdeadd12", "preco_dia": 6.00, "disponivel": True},
    {"alimento_id": "3ba92348-f983-4a96-8744-dad1dcdb9ee9", "preco_dia": 4.00, "disponivel": True},
    {"alimento_id": "d67ec598-08c9-49e5-a934-90783b9d7907", "preco_dia": 10.00, "disponivel": True},
]


def main():
    db = SessionLocal()
    try:
        restaurante = db.query(Restaurant).filter(Restaurant.is_active == True).first()  # noqa: E712
        if restaurante is None:
            print("Nenhum restaurante ativo encontrado — nada foi criado.")
            return

        hoje = date.today()
        cardapio = (
            db.query(Menu)
            .filter(Menu.restaurant_id == restaurante.id, Menu.date == hoje)
            .first()
        )

        if cardapio is None:
            cardapio = Menu(restaurant_id=restaurante.id, date=hoje)
            db.add(cardapio)
            db.flush()  # garante o id antes de inserir os itens
            print(f"Cardápio criado para {hoje} (id={cardapio.id})")
        else:
            print(f"Cardápio de {hoje} já existia (id={cardapio.id}) — itens serão atualizados")

        for item in ITENS:
            existente = (
                db.query(MenuItem)
                .filter(MenuItem.menu_id == cardapio.id, MenuItem.food_id == item["alimento_id"])
                .first()
            )
            if existente:
                existente.day_price = item["preco_dia"]
                existente.is_available = item["disponivel"]
            else:
                db.add(
                    MenuItem(
                        menu_id=cardapio.id,
                        food_id=item["alimento_id"],
                        day_price=item["preco_dia"],
                        is_available=item["disponivel"],
                    )
                )

        db.commit()
        print(f"{len(ITENS)} itens processados com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()