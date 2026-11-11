import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.seguranca import hash_password
from app.core.slug import motivo_slug_invalido
from app.model.models import (
    AdminUser,
    DeliveryChargeMode,
    FoodCategory,
    Restaurant,
    RestaurantDeliverySettings,
    PaymentMethod,
)
from app.services import pagamento_service, slug_service
from app.services.categoria_alimento_service import criar_categorias_iniciais

TEMPO_ENTREGA_PADRAO_MIN = 40
TEMPO_RETIRADA_PADRAO_MIN = 20
SENHA_MIN_CARACTERES = 8
SENHA_MAX_BYTES = 72

_PADRAO_LOGIN = re.compile(r"^[A-Za-z0-9._@+-]{3,60}$")


class ProvisionamentoError(ValueError):
    """Dado invalido ou ja em uso. A mensagem e apresentavel ao operador."""


@dataclass(frozen=True)
class ProvisionamentoResultado:
    restaurante: Restaurant
    admin: AdminUser
    configuracao_entrega: RestaurantDeliverySettings
    categorias: list[FoodCategory]
    formas_pagamento: list[PaymentMethod]


def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _validar_entrada(
    nome: str,
    admin_nome: str,
    admin_login: str,
    admin_senha: str,
    telefone: str | None,
    cnpj: str | None,
) -> None:
    if not 2 <= len(nome) <= 150:
        raise ProvisionamentoError("O nome do restaurante deve ter entre 2 e 150 caracteres.")
    if not 2 <= len(admin_nome) <= 150:
        raise ProvisionamentoError("O nome do admin deve ter entre 2 e 150 caracteres.")
    if not _PADRAO_LOGIN.match(admin_login):
        raise ProvisionamentoError(
            "O login do admin deve ter de 3 a 60 caracteres, usando apenas letras, "
            "números e . _ @ + -"
        )
    if len(admin_senha) < SENHA_MIN_CARACTERES:
        raise ProvisionamentoError(
            f"A senha deve ter ao menos {SENHA_MIN_CARACTERES} caracteres."
        )
    if len(admin_senha.encode("utf-8")) > SENHA_MAX_BYTES:
        raise ProvisionamentoError(f"A senha deve ter no máximo {SENHA_MAX_BYTES} bytes.")
    if telefone is not None and len(telefone) > 20:
        raise ProvisionamentoError("O telefone deve ter no máximo 20 caracteres.")
    if cnpj is not None and len(cnpj) > 18:
        raise ProvisionamentoError("O CNPJ deve ter no máximo 18 caracteres.")


def _resolver_slug(db: Session, nome: str, slug: str | None) -> str:
    if slug is None or not slug.strip():
        return slug_service.gerar_slug_unico(db, nome)
    candidato = slug.strip().lower()
    motivo = motivo_slug_invalido(candidato)
    if motivo is not None:
        raise ProvisionamentoError(motivo)
    if not slug_service.slug_disponivel(db, candidato):
        raise ProvisionamentoError("Este link já está em uso por outro restaurante.")
    return candidato


def _garantir_login_livre(db: Session, login: str) -> None:
    existe = (
        db.query(AdminUser.id).filter(func.lower(AdminUser.login) == login.lower()).first()
    )
    if existe is not None:
        raise ProvisionamentoError(f"O login '{login}' já está em uso.")


def _garantir_cnpj_livre(db: Session, cnpj: str | None) -> None:
    if cnpj is None:
        return
    if db.query(Restaurant.id).filter(Restaurant.cnpj == cnpj).first() is not None:
        raise ProvisionamentoError("Já existe um restaurante com este CNPJ.")


def provisionar_restaurante(
    db: Session,
    *,
    nome: str,
    admin_nome: str,
    admin_login: str,
    admin_senha: str,
    slug: str | None = None,
    telefone: str | None = None,
    cnpj: str | None = None,
    iniciar_pausado: bool = True,
) -> ProvisionamentoResultado:
    nome = nome.strip()
    admin_nome = admin_nome.strip()
    admin_login = admin_login.strip()
    telefone = _texto_opcional(telefone)
    cnpj = _texto_opcional(cnpj)

    _validar_entrada(nome, admin_nome, admin_login, admin_senha, telefone, cnpj)
    slug_final = _resolver_slug(db, nome, slug)
    _garantir_login_livre(db, admin_login)
    _garantir_cnpj_livre(db, cnpj)

    try:
        restaurante = Restaurant(
            trade_name=nome,
            slug=slug_final,
            phone=telefone,
            cnpj=cnpj,
            is_active=True,
            is_paused=iniciar_pausado,
        )
        db.add(restaurante)
        db.flush()

        admin = AdminUser(
            restaurant_id=restaurante.id,
            name=admin_nome,
            login=admin_login,
            password_hash=hash_password(admin_senha),
            role="admin",
            is_active=True,
        )
        configuracao = RestaurantDeliverySettings(
            restaurant_id=restaurante.id,
            delivery_enabled=True,
            pickup_enabled=True,
            delivery_time_minutes=TEMPO_ENTREGA_PADRAO_MIN,
            pickup_time_minutes=TEMPO_RETIRADA_PADRAO_MIN,
            charge_mode=DeliveryChargeMode.GRATIS,
        )
        db.add_all([admin, configuracao])
        db.flush()

        categorias = criar_categorias_iniciais(db, restaurante.id)

        formas_pagamento = pagamento_service.vincular_todas_as_formas_ativas(db, restaurante.id)
        if not formas_pagamento:
            raise ProvisionamentoError(
                "Não há forma de pagamento ativa cadastrada. Aplique as migrations e tente novamente."
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise ProvisionamentoError(
            "Algum dado já está em uso (link, login ou CNPJ). Tente novamente."
        )
    except Exception:
        db.rollback()
        raise

    db.refresh(restaurante)
    db.refresh(admin)
    db.refresh(configuracao)
    return ProvisionamentoResultado(restaurante, admin, configuracao, categorias, formas_pagamento)