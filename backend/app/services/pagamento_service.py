import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.model.models import PaymentMethod, RestaurantPaymentMethod
from app.schemas.pagamento_admin_schemas import FormaPagamentoAdminOut, FormasPagamentoIn


def _formas_ativas(db: Session) -> list[PaymentMethod]:
    return (
        db.query(PaymentMethod)
        .filter(PaymentMethod.is_active.is_(True))
        .order_by(PaymentMethod.name)
        .all()
    )


def listar_aceitas(db: Session, restaurant_id: uuid.UUID) -> list[PaymentMethod]:
    return (
        db.query(PaymentMethod)
        .join(
            RestaurantPaymentMethod,
            RestaurantPaymentMethod.payment_method_id == PaymentMethod.id,
        )
        .filter(
            RestaurantPaymentMethod.restaurant_id == restaurant_id,
            PaymentMethod.is_active.is_(True),
        )
        .order_by(PaymentMethod.name)
        .all()
    )


def listar_para_admin(db: Session, restaurant_id: uuid.UUID) -> list[FormaPagamentoAdminOut]:
    aceitas_ids = {forma.id for forma in listar_aceitas(db, restaurant_id)}
    return [
        FormaPagamentoAdminOut(codigo=forma.code, nome=forma.name, aceita=forma.id in aceitas_ids)
        for forma in _formas_ativas(db)
    ]


def salvar_aceitas(
    db: Session, restaurant_id: uuid.UUID, payload: FormasPagamentoIn
) -> list[FormaPagamentoAdminOut]:
    ativas = {forma.code: forma for forma in _formas_ativas(db)}
    desconhecidas = [codigo for codigo in payload.aceitas if codigo not in ativas]
    if desconhecidas:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Forma de pagamento inválida: {', '.join(desconhecidas)}.",
        )

    desejadas = {ativas[codigo].id for codigo in payload.aceitas}
    atuais = {
        vinculo.payment_method_id: vinculo
        for vinculo in db.query(RestaurantPaymentMethod)
        .filter(RestaurantPaymentMethod.restaurant_id == restaurant_id)
        .all()
    }

    for forma_id, vinculo in atuais.items():
        if forma_id not in desejadas:
            db.delete(vinculo)
    for forma_id in desejadas - atuais.keys():
        db.add(RestaurantPaymentMethod(restaurant_id=restaurant_id, payment_method_id=forma_id))

    db.commit()
    return listar_para_admin(db, restaurant_id)


def garantir_forma_aceita(db: Session, restaurant_id: uuid.UUID, forma: PaymentMethod) -> None:
    vinculada = (
        db.query(RestaurantPaymentMethod.restaurant_id)
        .filter(
            RestaurantPaymentMethod.restaurant_id == restaurant_id,
            RestaurantPaymentMethod.payment_method_id == forma.id,
        )
        .first()
        is not None
    )
    if not (forma.is_active and vinculada):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Este restaurante não aceita pagamento em {forma.name}.",
        )


def vincular_todas_as_formas_ativas(db: Session, restaurant_id: uuid.UUID) -> list[PaymentMethod]:
    formas = _formas_ativas(db)
    db.add_all(
        [
            RestaurantPaymentMethod(restaurant_id=restaurant_id, payment_method_id=forma.id)
            for forma in formas
        ]
    )
    return formas