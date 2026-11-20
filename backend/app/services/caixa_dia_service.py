import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import periodo
from app.core.tempo import hoje_local
from app.model.models import CashClosing, CashDay
from app.schemas.caixa_schemas import CaixaDiaOut, EntregadorOut, FecharCaixaIn, FormaOut
from app.services import caixa_acerto_service as acerto_service
from app.services import caixa_apuracao_service as apuracao_service
from app.services import caixa_fechamento_service as fechamento_service

STATUS_NAO_ABERTO = "NAO_ABERTO"
STATUS_ABERTO = fechamento_service.STATUS_ABERTO
STATUS_FECHADO = fechamento_service.STATUS_FECHADO


def _erro(codigo: int, mensagem: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=mensagem)


def _buscar(
    db: Session, restaurant_id: uuid.UUID, dia: date, travar: bool = False
) -> CashDay | None:
    consulta = db.query(CashDay).filter(
        CashDay.restaurant_id == restaurant_id, CashDay.business_date == dia
    )
    if travar:
        consulta = consulta.with_for_update()
    return consulta.first()


def abrir_caixa(
    db: Session, restaurant_id: uuid.UUID, dia: date | None, usuario_id: uuid.UUID
) -> CashDay:
    hoje = hoje_local()
    alvo = dia or hoje
    if alvo > hoje:
        raise _erro(422, "Não é possível abrir o caixa de um dia futuro.")

    caixa = CashDay(restaurant_id=restaurant_id, business_date=alvo, opened_by=usuario_id)
    try:
        with db.begin_nested():
            db.add(caixa)
    except IntegrityError:
        raise _erro(409, "O caixa deste dia já foi aberto.")

    db.commit()
    db.refresh(caixa)
    return caixa


def reabrir_caixa(
    db: Session, restaurant_id: uuid.UUID, dia: date, usuario_id: uuid.UUID
) -> CashDay:
    caixa = _buscar(db, restaurant_id, dia, travar=True)
    if caixa is None:
        raise _erro(404, "Caixa não encontrado para este dia.")
    if caixa.status != STATUS_FECHADO:
        raise _erro(409, "O caixa deste dia não está fechado.")

    fechamento_id = caixa.closing_id
    caixa.status = STATUS_ABERTO
    caixa.closed_by = None
    caixa.closed_at = None
    caixa.closing_id = None
    caixa.reopened_by = usuario_id
    caixa.reopened_at = periodo.agora_em_utc()
    caixa.reopen_count = caixa.reopen_count + 1
    db.flush()

    if fechamento_id is not None:
        db.query(CashClosing).filter(CashClosing.id == fechamento_id).delete(
            synchronize_session=False
        )

    db.commit()
    db.refresh(caixa)
    return caixa


def fechar(
    db: Session, restaurant_id: uuid.UUID, payload: FecharCaixaIn, usuario_id: uuid.UUID
) -> CaixaDiaOut:
    dia = payload.data or hoje_local()

    acertos = {}
    for acerto in payload.acertos:
        if acerto.entregador_id in acertos:
            raise _erro(422, "Entregador repetido nos acertos.")
        acertos[acerto.entregador_id] = acerto.valor_repassado

    fechamento_service.fechar_caixa(
        db, restaurant_id, dia, payload.contagem, payload.observacoes, usuario_id, acertos
    )
    return resumo_do_dia(db, restaurant_id, dia)


def resumo_do_dia(db: Session, restaurant_id: uuid.UUID, dia: date | None = None) -> CaixaDiaOut:
    alvo = dia or hoje_local()
    caixa = _buscar(db, restaurant_id, alvo)
    em_aberto = fechamento_service.pedidos_em_aberto(db, restaurant_id, alvo)

    fechamento = None
    if caixa is not None and caixa.status == STATUS_FECHADO and caixa.closing_id is not None:
        fechamento = db.get(CashClosing, caixa.closing_id)

    if fechamento is not None:
        formas = [
            FormaOut(
                forma=linha.method_code,
                quantidade_pedidos=linha.order_count,
                valor_esperado=linha.expected_amount,
                valor_contado=linha.counted_amount,
                diferenca=linha.difference,
            )
            for linha in fechamento_service.formas_do_fechamento(db, fechamento.id)
        ]
        entregadores = [
            EntregadorOut(
                entregador_id=linha.driver_id,
                nome=linha.driver_name,
                quantidade_entregas=linha.delivery_count,
                valor_esperado=linha.expected_amount,
                valor_repassado=linha.handed_amount,
                diferenca=linha.difference,
            )
            for linha in fechamento_service.entregadores_do_fechamento(db, fechamento.id)
        ]
        quantidade_pedidos = fechamento.order_count
        quantidade_cancelados = fechamento.cancelled_count
        total_vendas = fechamento.total_sales
        total_dinheiro_recebido = fechamento.total_cash_paid
        total_troco = fechamento.total_change
        diferenca_total = fechamento.difference
        observacoes = fechamento.notes
    else:
        apuracao = apuracao_service.apurar_dia(db, restaurant_id, alvo)
        formas = []
        for codigo in apuracao_service.CHAVES_FORMA:
            item = apuracao.por_forma[codigo]
            if codigo == apuracao_service.FORMA_OUTROS and item.quantidade == 0:
                continue
            formas.append(
                FormaOut(forma=codigo, quantidade_pedidos=item.quantidade, valor_esperado=item.total)
            )
        entregadores = [
            EntregadorOut(
                entregador_id=entregador.driver_id,
                nome=entregador.nome,
                quantidade_entregas=entregador.quantidade_entregas,
                valor_esperado=entregador.esperado_dinheiro,
            )
            for entregador in acerto_service.apurar_entregadores(db, restaurant_id, alvo)
        ]
        quantidade_pedidos = apuracao.quantidade_pedidos
        quantidade_cancelados = apuracao.quantidade_cancelados
        total_vendas = apuracao.total_vendas
        total_dinheiro_recebido = apuracao.total_dinheiro_recebido
        total_troco = apuracao.total_troco
        diferenca_total = None
        observacoes = None

    if caixa is None:
        situacao = STATUS_NAO_ABERTO
    else:
        situacao = caixa.status

    return CaixaDiaOut(
        data=alvo,
        status=situacao,
        aberto_por=caixa.opened_by if caixa else None,
        aberto_em=caixa.opened_at if caixa else None,
        fechado_por=caixa.closed_by if caixa else None,
        fechado_em=caixa.closed_at if caixa else None,
        reaberto_por=caixa.reopened_by if caixa else None,
        reaberto_em=caixa.reopened_at if caixa else None,
        reaberturas=caixa.reopen_count if caixa else 0,
        fechamento_id=caixa.closing_id if caixa else None,
        pode_fechar=caixa is not None and caixa.status == STATUS_ABERTO and em_aberto == 0,
        pedidos_em_aberto=em_aberto,
        quantidade_pedidos=quantidade_pedidos,
        quantidade_cancelados=quantidade_cancelados,
        total_vendas=total_vendas,
        total_dinheiro_recebido=total_dinheiro_recebido,
        total_troco=total_troco,
        diferenca_total=diferenca_total,
        observacoes=observacoes,
        formas=formas,
        entregadores=entregadores,
    )