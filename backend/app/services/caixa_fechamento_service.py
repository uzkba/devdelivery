import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import periodo
from app.model.models import CashClosing, CashClosingMethod, CashDay, Order, OrderStatus
from app.services import caixa_apuracao_service as apuracao_service
from app.services import pedido_fluxo

STATUS_ABERTO = "ABERTO"
STATUS_FECHADO = "FECHADO"

CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")
OBSERVACAO_MIN = 3
OBSERVACAO_MAX = 500
PEDIDOS_EM_ABERTO = pedido_fluxo.ABAS["novos"] | pedido_fluxo.ABAS["em_andamento"]


def _regra(mensagem: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=mensagem)


def _conflito(mensagem: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensagem)


def _normalizar_contagem(contagem: dict[str, Decimal]) -> dict[str, Decimal]:
    normalizada = {}
    for codigo, valor in contagem.items():
        if codigo not in apuracao_service.CHAVES_FORMA:
            raise _regra(f"Forma de pagamento desconhecida: {codigo}.")
        if valor < 0:
            raise _regra(f"O valor contado de {codigo} não pode ser negativo.")
        arredondado = Decimal(valor).quantize(CENTAVO)
        if arredondado != valor:
            raise _regra(f"O valor contado de {codigo} deve ter no máximo duas casas decimais.")
        normalizada[codigo] = arredondado
    return normalizada


def _pedidos_em_aberto(db: Session, restaurant_id: uuid.UUID, dia: date) -> int:
    inicio, fim = periodo.intervalo_do_dia_em_utc(dia)
    return (
        db.query(func.count(Order.id))
        .select_from(Order)
        .join(OrderStatus, OrderStatus.id == Order.status_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.order_datetime >= inicio,
            Order.order_datetime < fim,
            OrderStatus.code.in_(PEDIDOS_EM_ABERTO),
        )
        .scalar()
    ) or 0


def fechar_caixa(
    db: Session,
    restaurant_id: uuid.UUID,
    dia: date,
    contagem: dict[str, Decimal],
    observacoes: str | None,
    usuario_id: uuid.UUID,
) -> CashClosing:
    caixa = (
        db.query(CashDay)
        .filter(CashDay.restaurant_id == restaurant_id, CashDay.business_date == dia)
        .with_for_update()
        .first()
    )
    if caixa is None:
        raise _conflito("Não há caixa aberto para este dia.")
    if caixa.status != STATUS_ABERTO:
        raise _conflito("O caixa deste dia já está fechado.")

    contada = _normalizar_contagem(contagem)

    em_aberto = _pedidos_em_aberto(db, restaurant_id, dia)
    if em_aberto:
        raise _regra(
            f"Há {em_aberto} pedido(s) em aberto neste dia. Finalize ou cancele antes de fechar o caixa."
        )

    apuracao = apuracao_service.apurar_dia(db, restaurant_id, dia)

    faltando = [
        codigo
        for codigo in apuracao_service.CHAVES_FORMA
        if apuracao.por_forma[codigo].quantidade > 0 and codigo not in contada
    ]
    if faltando:
        raise _regra(f"Informe o valor contado de: {', '.join(faltando)}.")

    formas = []
    for codigo in apuracao_service.CHAVES_FORMA:
        total_forma = apuracao.por_forma[codigo]
        contado = contada.get(codigo, ZERO)
        if codigo == apuracao_service.FORMA_OUTROS and total_forma.quantidade == 0 and contado == 0:
            continue
        formas.append(
            CashClosingMethod(
                method_code=codigo,
                order_count=total_forma.quantidade,
                expected_amount=total_forma.total,
                counted_amount=contado,
                difference=contado - total_forma.total,
            )
        )

    houve_diferenca = any(forma.difference != 0 for forma in formas)
    texto = (observacoes or "").strip()
    if len(texto) > OBSERVACAO_MAX:
        raise _regra(f"A observação deve ter no máximo {OBSERVACAO_MAX} caracteres.")
    if houve_diferenca and len(texto) < OBSERVACAO_MIN:
        raise _regra("Informe uma observação explicando a diferença encontrada.")

    por_forma = apuracao.por_forma
    total_contado = sum((forma.counted_amount for forma in formas), ZERO)

    fechamento = CashClosing(
        restaurant_id=restaurant_id,
        start_date=dia,
        end_date=dia,
        total_sales=apuracao.total_vendas,
        total_pix=por_forma["PIX"].total,
        total_cash=por_forma["DINHEIRO"].total,
        total_debit=por_forma["CARTAO_DEBITO"].total,
        total_credit=por_forma["CARTAO_CREDITO"].total,
        total_other=por_forma["OUTROS"].total,
        total_cash_paid=apuracao.total_dinheiro_recebido,
        total_change=apuracao.total_troco,
        order_count=apuracao.quantidade_pedidos,
        cancelled_count=apuracao.quantidade_cancelados,
        expected_amount=apuracao.total_vendas,
        reported_amount=total_contado,
        difference=total_contado - apuracao.total_vendas,
        closed_by=usuario_id,
        notes=texto or None,
    )

    try:
        with db.begin_nested():
            db.add(fechamento)
    except IntegrityError:
        raise _conflito("Já existe um fechamento de caixa para este dia.")

    for forma in formas:
        forma.closing_id = fechamento.id
        db.add(forma)

    caixa.status = STATUS_FECHADO
    caixa.closed_by = usuario_id
    caixa.closed_at = fechamento.closed_at
    caixa.closing_id = fechamento.id

    db.commit()
    db.refresh(fechamento)
    return fechamento


def formas_do_fechamento(db: Session, fechamento_id: uuid.UUID) -> list[CashClosingMethod]:
    linhas = (
        db.query(CashClosingMethod).filter(CashClosingMethod.closing_id == fechamento_id).all()
    )
    ordem = {codigo: posicao for posicao, codigo in enumerate(apuracao_service.CHAVES_FORMA)}
    return sorted(linhas, key=lambda linha: ordem.get(linha.method_code, len(ordem)))