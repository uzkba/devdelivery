import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core import periodo
from app.model.models import AdminUser, Order, OrderStatus, PaymentMethod

STATUS_ENTREGUE = "ENTREGUE"
FORMA_DINHEIRO = "DINHEIRO"


@dataclass(frozen=True)
class AcertoEntregador:
    driver_id: uuid.UUID
    nome: str
    quantidade_entregas: int
    quantidade_dinheiro: int
    esperado_dinheiro: Decimal


def apurar_entregadores(db: Session, restaurant_id: uuid.UUID, dia: date) -> list[AcertoEntregador]:
    inicio, fim = periodo.intervalo_do_dia_em_utc(dia)
    eh_dinheiro = PaymentMethod.code == FORMA_DINHEIRO

    linhas = (
        db.query(
            AdminUser.id,
            AdminUser.name,
            func.count(Order.id),
            func.coalesce(func.sum(case((eh_dinheiro, 1), else_=0)), 0),
            func.coalesce(func.sum(case((eh_dinheiro, Order.total_amount), else_=0)), 0),
        )
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .join(PaymentMethod, PaymentMethod.id == Order.payment_method_id)
        .join(AdminUser, AdminUser.id == Order.driver_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code == STATUS_ENTREGUE,
        )
        .group_by(AdminUser.id, AdminUser.name)
        .order_by(func.lower(AdminUser.name), AdminUser.id)
        .all()
    )

    return [
        AcertoEntregador(
            driver_id=driver_id,
            nome=nome,
            quantidade_entregas=int(entregas),
            quantidade_dinheiro=int(em_dinheiro),
            esperado_dinheiro=Decimal(esperado),
        )
        for driver_id, nome, entregas, em_dinheiro, esperado in linhas
    ]