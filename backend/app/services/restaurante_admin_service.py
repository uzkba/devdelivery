import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.slug import motivo_slug_invalido
from app.model.models import Restaurant, RestaurantHours
from app.schemas.restaurante_admin_schemas import (
    HorariosIn,
    PausaIn,
    RestauranteAdminOut,
    RestauranteAtualizarIn,
    SlugDisponivelOut,
)
from app.schemas.restaurante_publico_schemas import EnderecoPublicoOut, EstadoOperacaoOut
from app.services import estado_restaurante_service as estado_service
from app.services import slug_service
from app.services.restaurante_publico_service import montar_estado, montar_horarios

_CAMPOS_ENDERECO = {
    "rua": "street",
    "numero": "number",
    "bairro": "neighborhood",
    "cidade": "city",
}


def buscar_restaurante(db: Session, restaurant_id: uuid.UUID) -> Restaurant:
    restaurante = db.get(Restaurant, restaurant_id)
    if restaurante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurante não encontrado.")
    return restaurante


def montar_admin(
    db: Session, restaurante: Restaurant, agora: datetime | None = None
) -> RestauranteAdminOut:
    momento = agora if agora is not None else estado_service.agora_local()
    faixas = estado_service.buscar_faixas(db, restaurante.id)
    estado = estado_service.calcular_estado(restaurante, faixas, momento)
    return RestauranteAdminOut(
        slug=restaurante.slug,
        nome=restaurante.trade_name,
        cnpj=restaurante.cnpj,
        telefone=restaurante.phone,
        endereco=EnderecoPublicoOut(
            rua=restaurante.street,
            numero=restaurante.number,
            bairro=restaurante.neighborhood,
            cidade=restaurante.city,
        ),
        estado=montar_estado(estado),
        horarios=montar_horarios(faixas),
    )


def buscar_dados(db: Session, restaurant_id: uuid.UUID) -> RestauranteAdminOut:
    return montar_admin(db, buscar_restaurante(db, restaurant_id))


def atualizar_dados(
    db: Session, restaurant_id: uuid.UUID, dados: RestauranteAtualizarIn
) -> RestauranteAdminOut:
    restaurante = buscar_restaurante(db, restaurant_id)
    campos = dados.model_fields_set

    if "slug" in campos and dados.slug != restaurante.slug:
        restaurante.slug = slug_service.garantir_slug_valido_e_livre(
            db, dados.slug, excluir_restaurante_id=restaurante.id
        )
    if "nome" in campos:
        restaurante.trade_name = dados.nome
    if "telefone" in campos:
        restaurante.phone = dados.telefone
    if dados.endereco is not None:
        for campo in dados.endereco.model_fields_set:
            setattr(restaurante, _CAMPOS_ENDERECO[campo], getattr(dados.endereco, campo))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este link já está em uso por outro restaurante.")
    db.refresh(restaurante)
    return montar_admin(db, restaurante)


def verificar_slug(db: Session, restaurant_id: uuid.UUID, slug: str) -> SlugDisponivelOut:
    restaurante = buscar_restaurante(db, restaurant_id)
    candidato = slug.strip().lower()
    motivo = motivo_slug_invalido(candidato)
    if motivo is None and not slug_service.slug_disponivel(db, candidato, restaurante.id):
        motivo = "Este link já está em uso por outro restaurante."
    return SlugDisponivelOut(slug=candidato, disponivel=motivo is None, motivo=motivo)


def substituir_horarios(
    db: Session, restaurant_id: uuid.UUID, dados: HorariosIn
) -> RestauranteAdminOut:
    restaurante = buscar_restaurante(db, restaurant_id)

    db.query(RestaurantHours).filter(RestaurantHours.restaurant_id == restaurante.id).delete(
        synchronize_session=False
    )
    for dia in dados.dias:
        for faixa in dia.faixas:
            db.add(
                RestaurantHours(
                    restaurant_id=restaurante.id,
                    weekday=dia.dia_semana,
                    opens_at=faixa.abre_as,
                    closes_at=faixa.fecha_as,
                )
            )
    db.commit()
    db.refresh(restaurante)
    return montar_admin(db, restaurante)


def _fim_padrao_da_pausa(db: Session, restaurante: Restaurant, agora: datetime) -> datetime:
    for faixa in estado_service.buscar_faixas(db, restaurante.id):
        if faixa.weekday == agora.weekday() and faixa.opens_at <= agora.time() < faixa.closes_at:
            return agora.replace(
                hour=faixa.closes_at.hour,
                minute=faixa.closes_at.minute,
                second=0,
                microsecond=0,
            )
    return (agora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def alterar_pausa(db: Session, restaurant_id: uuid.UUID, dados: PausaIn) -> EstadoOperacaoOut:
    restaurante = buscar_restaurante(db, restaurant_id)
    agora = estado_service.agora_local()

    if dados.pausado:
        restaurante.is_paused = True
        restaurante.paused_until = (
            agora + timedelta(minutes=dados.minutos)
            if dados.minutos is not None
            else _fim_padrao_da_pausa(db, restaurante, agora)
        )
    else:
        restaurante.is_paused = False
        restaurante.paused_until = None

    db.commit()
    db.refresh(restaurante)
    faixas = estado_service.buscar_faixas(db, restaurante.id)
    return montar_estado(estado_service.calcular_estado(restaurante, faixas, agora))