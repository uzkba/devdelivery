from decimal import Decimal


from app.model.models import (
    DeliveryChargeMode,
    DeliveryRuleNeighborhood,
    RestaurantDeliverySettings,
)


def _config(db, restaurante, modo, **extra):
    dados = dict(
        restaurant_id=restaurante.id,
        charge_mode=modo,
        delivery_time_minutes=40,
        pickup_time_minutes=15,
        min_order_value=Decimal("20.00"),
    )
    dados.update(extra)
    config = RestaurantDeliverySettings(**dados)
    db.add(config)
    db.flush()
    return config


def _regra_bairro(db, restaurante, bairro, taxa, ativo=True):
    db.add(
        DeliveryRuleNeighborhood(
            restaurant_id=restaurante.id,
            neighborhood=bairro,
            fee=Decimal(taxa),
            is_active=ativo,
        )
    )
    db.flush()


def _get(client, slug, esperado=200):
    resposta = client.get(f"/restaurantes/{slug}")
    assert resposta.status_code == esperado
    return resposta.json()


def test_slug_inexistente_retorna_404(client):
    _get(client, "nao-existe", esperado=404)


def test_uuid_no_lugar_do_slug_retorna_404(client, restaurante):
    _get(client, str(restaurante.id), esperado=404)


def test_restaurante_inativo_retorna_404(client, db, restaurante):
    restaurante.is_active = False
    db.flush()
    _get(client, restaurante.slug, esperado=404)


def test_slug_nao_diferencia_maiusculas(client, restaurante):
    corpo = _get(client, restaurante.slug.upper())
    assert corpo["slug"] == restaurante.slug


def test_dados_basicos_sem_configuracao_de_entrega(client, db, restaurante):
    restaurante.phone = "11999990000"
    restaurante.street = "Rua das Flores"
    restaurante.number = "10"
    restaurante.neighborhood = "Centro"
    restaurante.city = "São Paulo"
    db.flush()

    corpo = _get(client, restaurante.slug)

    assert corpo["slug"] == restaurante.slug
    assert corpo["nome"] == "Marmitas da Vovó"
    assert corpo["telefone"] == "11999990000"
    assert corpo["endereco"] == {
        "rua": "Rua das Flores",
        "numero": "10",
        "bairro": "Centro",
        "cidade": "São Paulo",
    }
    assert corpo["entrega"] is None


def test_nao_expoe_dados_internos(client, restaurante):
    corpo = _get(client, restaurante.slug)
    for campo in ("id", "cnpj", "latitude", "longitude", "is_active", "ativo"):
        assert campo not in corpo


def test_taxa_fixa(client, db, restaurante):
    _config(db, restaurante, DeliveryChargeMode.FIXO, fixed_fee=Decimal("5.00"))

    entrega = _get(client, restaurante.slug)["entrega"]

    assert entrega["entrega_ativa"] is True
    assert entrega["retirada_ativa"] is True
    assert entrega["valor_minimo"] == "20.00"
    assert entrega["tempo_entrega_min"] == 40
    assert entrega["tempo_retirada_min"] == 15
    assert entrega["taxa"] == {
        "modo": "FIXO",
        "valor_fixo": "5.00",
        "taxa_minima": None,
        "taxa_maxima": None,
    }


def test_entrega_gratis(client, db, restaurante):
    _config(db, restaurante, DeliveryChargeMode.GRATIS)

    taxa = _get(client, restaurante.slug)["entrega"]["taxa"]

    assert taxa == {"modo": "GRATIS", "valor_fixo": None, "taxa_minima": None, "taxa_maxima": None}


def test_taxa_por_bairro_devolve_faixa_das_regras_ativas(client, db, restaurante):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    _regra_bairro(db, restaurante, "Centro", "3.00")
    _regra_bairro(db, restaurante, "Jardins", "8.00")
    _regra_bairro(db, restaurante, "Bairro Desativado", "1.00", ativo=False)

    taxa = _get(client, restaurante.slug)["entrega"]["taxa"]

    assert taxa["modo"] == "BAIRRO"
    assert taxa["valor_fixo"] is None
    assert taxa["taxa_minima"] == "3.00"
    assert taxa["taxa_maxima"] == "8.00"


def test_taxa_por_bairro_sem_regras_ativas(client, db, restaurante):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)

    taxa = _get(client, restaurante.slug)["entrega"]["taxa"]

    assert taxa["taxa_minima"] is None
    assert taxa["taxa_maxima"] is None


def test_regras_de_bairro_de_outro_restaurante_nao_entram(
    client, db, restaurante, outro_restaurante
):
    _config(db, restaurante, DeliveryChargeMode.BAIRRO)
    _regra_bairro(db, restaurante, "Centro", "4.00")
    _regra_bairro(db, outro_restaurante, "Centro", "99.00")

    taxa = _get(client, restaurante.slug)["entrega"]["taxa"]

    assert taxa["taxa_minima"] == "4.00"
    assert taxa["taxa_maxima"] == "4.00"


def test_entrega_e_retirada_desativadas_sao_refletidas(client, db, restaurante):
    _config(
        db,
        restaurante,
        DeliveryChargeMode.GRATIS,
        delivery_enabled=False,
        pickup_enabled=False,
    )

    entrega = _get(client, restaurante.slug)["entrega"]

    assert entrega["entrega_ativa"] is False
    assert entrega["retirada_ativa"] is False


def test_rota_antiga_get_restaurante_foi_removida(client):
    assert client.get("/restaurante").status_code == 404