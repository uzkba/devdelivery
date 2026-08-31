import pytest
from decimal import Decimal
from fastapi import HTTPException

# Adapte os imports conforme a estrutura real das suas pastas
from backend.app.schemas.regras_delivery_schemas import DeliveryRuleCreate
from backend.app.services.regras_delivery_service import criar_regra_entrega
from backend.app.model.models import DeliveryRule

def test_criar_regra_entrega_com_sucesso(db, restaurante):
    # Setup: Payload de criação
    payload = DeliveryRuleCreate(
        min_distance_km=Decimal("0.0"),
        max_distance_km=Decimal("3.0"),
        fee=Decimal("5.00"),
        is_active=True
    )

    # Execução (usando o restaurante real da fixture)
    nova_regra = criar_regra_entrega(db, payload, restaurante.id)

    # Assertions (Validações)
    assert nova_regra.id is not None
    assert nova_regra.restaurant_id == restaurante.id
    assert nova_regra.fee == Decimal("5.00")
    assert nova_regra.is_active is True

def test_deve_bloquear_regras_com_sobreposicao(db, restaurante):
    # Regra 1: 0 a 5km
    payload_1 = DeliveryRuleCreate(
        min_distance_km=Decimal("0.0"),
        max_distance_km=Decimal("5.0"),
        fee=Decimal("5.00")
    )
    # Usando o restaurante real da fixture
    criar_regra_entrega(db, payload_1, restaurante.id)

    # Regra 2: 4 a 10km (Sobrepõe do 4 ao 5)
    payload_2 = DeliveryRuleCreate(
        min_distance_km=Decimal("4.0"),
        max_distance_km=Decimal("10.0"),
        fee=Decimal("10.00")
    )

    # Deve disparar um erro HTTP 400
    with pytest.raises(HTTPException) as exc_info:
        criar_regra_entrega(db, payload_2, restaurante.id)
        
    assert exc_info.value.status_code == 400
    assert "Conflito de faixas" in exc_info.value.detail

def test_schema_deve_bloquear_distancia_minima_maior_que_maxima():
    # Isso testa a validação do Pydantic antes mesmo de chegar no banco
    with pytest.raises(ValueError):
        DeliveryRuleCreate(
            min_distance_km=Decimal("10.0"),
            max_distance_km=Decimal("5.0"), # Erro proposital: max < min
            fee=Decimal("15.00")
        )