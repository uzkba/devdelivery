from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.depedencias import require_role, get_current_client, AuthenticatedClient
from app.schemas.pagamento_schemas import (
    PaymentCardIn,
    ReceivingAccountIn,
    ReceivingAccountOut,
    PaymentResultOut,
    PixGenerateIn,
    PixGenerateOut,
)
from app.services import pagamento_service

router = APIRouter(prefix="/pagamentos", tags=["pagamentos"])

# Rotas de configuração ficam num router separado (admin-only), pra não
# misturar com as rotas que o cliente usa durante o checkout.
admin_router = APIRouter(prefix="/admin/conta-recebimento", tags=["pagamentos"])


@router.post("/pix", response_model=PixGenerateOut)
def gerar_pix(
    dados: PixGenerateIn,
    db: Session = Depends(get_db),
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    conta = pagamento_service.get_single_receiving_account(db)
    if conta is None:
        raise HTTPException(
            status_code=503,
            detail="Nenhuma conta configurada para recebimento via Pix.",
        )

    codigo = pagamento_service.generate_pix_code(conta, dados.amount)
    return PixGenerateOut(
        copy_and_paste_code=codigo,
        pix_key=conta.pix_key,
        account_holder=conta.account_holder,
        amount=dados.amount,
    )


@router.post("/cartao", response_model=PaymentResultOut)
def pagar_com_cartao(
    dados: PaymentCardIn,
    cliente: AuthenticatedClient = Depends(get_current_client),
):
    return pagamento_service.process_card_payment(dados)


@admin_router.get("", response_model=ReceivingAccountOut)
def obter_conta(
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    conta = pagamento_service.get_single_receiving_account(db)
    if conta is None:
        raise HTTPException(status_code=404, detail="Nenhuma conta de recebimento configurada.")
    return conta


@admin_router.put("", response_model=ReceivingAccountOut)
def atualizar_conta(
    dados: ReceivingAccountIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    return pagamento_service.save_single_receiving_account(db, dados)