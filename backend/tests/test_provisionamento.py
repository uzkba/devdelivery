import pytest

from app.core.seguranca import verify_password
from app.model.models import (
    AdminUser,
    DeliveryChargeMode,
    FoodCategory,
    Restaurant,
    RestaurantDeliverySettings,
)
from app.services import provisionamento_service as svc
from app.services.provisionamento_service import ProvisionamentoError


def _provisionar(db, **sobrescritas):
    dados = dict(
        nome="Novo Restaurante",
        admin_nome="Fulano de Tal",
        admin_login="fulano.admin",
        admin_senha="senha-segura-123",
    )
    dados.update(sobrescritas)
    return svc.provisionar_restaurante(db, **dados)


def _total_restaurantes_novos(db):
    return db.query(Restaurant).filter(Restaurant.trade_name == "Novo Restaurante").count()


# --------------------------------- sucesso ---------------------------------
def test_cria_restaurante_com_slug_gerado(db):
    resultado = _provisionar(db, nome="  Sabor Caseiro  ", telefone=" 11999990000 ")
    restaurante = resultado.restaurante
    assert restaurante.trade_name == "Sabor Caseiro"
    assert restaurante.slug == "sabor-caseiro"
    assert restaurante.phone == "11999990000"
    assert restaurante.is_active is True


def test_cria_primeiro_admin_com_senha_em_hash(db):
    resultado = _provisionar(db)
    admin = resultado.admin
    assert admin.restaurant_id == resultado.restaurante.id
    assert admin.role == "admin"
    assert admin.is_active is True
    assert admin.name == "Fulano de Tal"
    assert admin.password_hash != "senha-segura-123"
    assert verify_password("senha-segura-123", admin.password_hash) is True
    assert db.query(AdminUser).filter_by(restaurant_id=resultado.restaurante.id).count() == 1


def test_cria_configuracao_de_entrega_padrao(db):
    resultado = _provisionar(db)
    config = (
        db.query(RestaurantDeliverySettings)
        .filter_by(restaurant_id=resultado.restaurante.id)
        .one()
    )
    assert config.charge_mode == DeliveryChargeMode.GRATIS
    assert config.delivery_enabled is True
    assert config.pickup_enabled is True
    assert config.delivery_time_minutes == svc.TEMPO_ENTREGA_PADRAO_MIN
    assert config.pickup_time_minutes == svc.TEMPO_RETIRADA_PADRAO_MIN
    assert config.min_order_value is None
    assert config.fixed_fee is None


def test_cria_categorias_iniciais_so_para_o_restaurante_novo(db, restaurante):
    resultado = _provisionar(db)
    categorias = (
        db.query(FoodCategory)
        .filter_by(restaurant_id=resultado.restaurante.id)
        .order_by(FoodCategory.display_order)
        .all()
    )
    assert [(c.name, c.group) for c in categorias] == [
        ("Pratos", "prato"),
        ("Sobremesas", "prato"),
        ("Bebidas", "bebida"),
    ]
    assert db.query(FoodCategory).filter_by(restaurant_id=restaurante.id).count() == 0


def test_nasce_pausado_e_nao_aceita_pedidos(client, db):
    resultado = _provisionar(db)
    assert resultado.restaurante.is_paused is True
    estado = client.get(f"/restaurantes/{resultado.restaurante.slug}").json()["estado"]
    assert estado["estado"] == "PAUSADO"
    assert estado["aceita_pedidos"] is False


def test_sem_pausa_inicial_aceita_pedidos(client, db):
    resultado = _provisionar(db, iniciar_pausado=False)
    assert resultado.restaurante.is_paused is False
    estado = client.get(f"/restaurantes/{resultado.restaurante.slug}").json()["estado"]
    assert estado["estado"] == "ABERTO"


def test_slug_informado_e_normalizado(db):
    resultado = _provisionar(db, slug="  Meu-Link  ")
    assert resultado.restaurante.slug == "meu-link"


def test_slug_gerado_evita_colisao(db, restaurante):
    resultado = _provisionar(db, nome="Marmitas da Vovó")
    assert resultado.restaurante.slug == "marmitas-da-vovo-2"


def test_dois_restaurantes_com_o_mesmo_nome_ficam_com_links_diferentes(db):
    primeiro = _provisionar(db, admin_login="admin.um")
    segundo = _provisionar(db, admin_login="admin.dois")
    assert primeiro.restaurante.slug == "novo-restaurante"
    assert segundo.restaurante.slug == "novo-restaurante-2"


def test_restaurante_novo_aparece_na_rota_publica(client, db):
    resultado = _provisionar(db)
    resposta = client.get(f"/restaurantes/{resultado.restaurante.slug}")
    assert resposta.status_code == 200
    assert resposta.json()["entrega"]["taxa"]["modo"] == "GRATIS"


# ------------------------------- conflitos -------------------------------
def test_slug_informado_ocupado_e_recusado(db, restaurante):
    with pytest.raises(ProvisionamentoError, match="em uso"):
        _provisionar(db, slug=restaurante.slug)
    assert _total_restaurantes_novos(db) == 0


@pytest.mark.parametrize("slug", ["ab", "a--b", "tem espaco", "admin"])
def test_slug_informado_invalido_ou_reservado_e_recusado(db, slug):
    with pytest.raises(ProvisionamentoError):
        _provisionar(db, slug=slug)
    assert _total_restaurantes_novos(db) == 0


def test_login_ja_existente_e_recusado(db, admin_user):
    with pytest.raises(ProvisionamentoError, match="login"):
        _provisionar(db, admin_login=admin_user.login)
    assert _total_restaurantes_novos(db) == 0


def test_login_existente_com_outras_maiusculas_e_recusado(db, admin_user):
    with pytest.raises(ProvisionamentoError, match="login"):
        _provisionar(db, admin_login=admin_user.login.upper())
    assert _total_restaurantes_novos(db) == 0


def test_cnpj_ja_existente_e_recusado(db, restaurante):
    restaurante.cnpj = "12.345.678/0001-90"
    db.flush()
    with pytest.raises(ProvisionamentoError, match="CNPJ"):
        _provisionar(db, cnpj="12.345.678/0001-90")
    assert _total_restaurantes_novos(db) == 0


# ------------------------------- validacoes -------------------------------
@pytest.mark.parametrize(
    "sobrescritas",
    [
        {"nome": " a "},
        {"nome": "x" * 151},
        {"admin_nome": ""},
        {"admin_login": "ab"},
        {"admin_login": "com espaco"},
        {"admin_login": "x" * 61},
        {"admin_senha": "curta"},
        {"admin_senha": "x" * 73},
        {"telefone": "1" * 21},
        {"cnpj": "1" * 19},
    ],
)
def test_entrada_invalida_e_recusada_sem_gravar_nada(db, sobrescritas):
    with pytest.raises(ProvisionamentoError):
        _provisionar(db, **sobrescritas)
    assert _total_restaurantes_novos(db) == 0
    assert db.query(AdminUser).filter_by(login="fulano.admin").count() == 0


# ------------------------------- atomicidade -------------------------------
def test_falha_no_meio_nao_deixa_nada_gravado(db, monkeypatch):
    def _falhar(*args, **kwargs):
        raise RuntimeError("falha simulada nas categorias iniciais")

    monkeypatch.setattr(svc, "criar_categorias_iniciais", _falhar)

    with pytest.raises(RuntimeError):
        _provisionar(db, nome="Falha No Meio", admin_login="falha.admin")

    assert db.query(Restaurant).filter_by(slug="falha-no-meio").count() == 0
    assert db.query(AdminUser).filter_by(login="falha.admin").count() == 0
    assert db.query(RestaurantDeliverySettings).count() == 0