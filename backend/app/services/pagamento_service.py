import re
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.model.models import ReceivingAccount
from app.schemas.pagamento_schemas import (
    PaymentCardIn,
    ReceivingAccountIn,
    PaymentResultOut,
)


# ---------- Conta de recebimento (chave Pix) ----------
# Single-tenant por enquanto: sempre a única conta ativa (mesmo padrão do
# GET /restaurante). Trocar a conta usada = um PUT em /admin/conta-recebimento,
# sem precisar mexer em código.

def get_single_receiving_account(db: Session) -> ReceivingAccount | None:
    return (
        db.query(ReceivingAccount)
        .filter(ReceivingAccount.active.is_(True))
        .first()
    )


def save_single_receiving_account(db: Session, data: ReceivingAccountIn) -> ReceivingAccount:
    account = get_single_receiving_account(db)
    if account is None:
        account = ReceivingAccount()
        db.add(account)

    account.pix_key = data.pix_key
    account.pix_key_type = data.pix_key_type
    account.account_holder = data.account_holder
    account.city = data.city
    account.active = True

    db.commit()
    db.refresh(account)
    return account


# ---------- Geração do código Pix "copia e cola" (padrão EMV / BR Code) ----------
# Implementação real do payload (não é só um texto fake): monta os campos TLV
# exigidos pelo Bacen e calcula o CRC16 no final, então o código gerado é um
# Pix estático válido, que qualquer app de banco consegue ler.

def _tlv(id_: str, value: str) -> str:
    length = str(len(value)).zfill(2)
    return f"{id_}{length}{value}"


def _crc16(payload: str) -> str:
    polynomial = 0x1021
    result = 0xFFFF
    for byte in payload.encode("utf-8"):
        result ^= byte << 8
        for _ in range(8):
            if result & 0x8000:
                result = ((result << 1) ^ polynomial) & 0xFFFF
            else:
                result = (result << 1) & 0xFFFF
    return format(result, "04X")


def _sanitize(text: str, max_length: int) -> str:
    text = re.sub(r"[^A-Za-z0-9 ]", "", text).strip().upper()
    return text[:max_length] or "NAO INFORMADO"


def generate_pix_code(account: ReceivingAccount, amount: Decimal, identifier: str = "***") -> str:
    merchant_account = _tlv("00", "BR.GOV.BCB.PIX") + _tlv("01", account.pix_key)
    fields = [
        _tlv("00", "01"),                               # Payload Format Indicator
        _tlv("26", merchant_account),                  # Merchant Account Info (Pix)
        _tlv("52", "0000"),                             # Merchant Category Code
        _tlv("53", "986"),                              # Moeda (BRL)
        _tlv("54", f"{amount:.2f}"),                    # Valor da transação
        _tlv("58", "BR"),                               # País
        _tlv("59", _sanitize(account.account_holder, 25)), # Titular da conta
        _tlv("60", _sanitize(account.city, 15)),        # Cidade do titular
        _tlv("62", _tlv("05", identifier[:25])),        # Dados adicionais (txid)
    ]
    payload_without_crc = "".join(fields) + "6304"
    crc = _crc16(payload_without_crc)
    return payload_without_crc + crc


# ---------- Cartão (crédito/débito) ----------
# Ainda não há integração com uma adquirente/gateway real (fica para uma task
# futura). Por ora validamos os dados do cartão de verdade (Luhn + validade) e
# aprovamos qualquer cartão que passe nessa validação, para o fluxo já
# funcionar ponta a ponta.

def _is_valid_luhn(number: str) -> bool:
    digits = [int(d) for d in number]
    total_sum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total_sum += d
    return total_sum % 10 == 0


def _is_future_expiration(expiration: str) -> bool:
    month_str, year_str = expiration.split("/")
    month = int(month_str)
    year = 2000 + int(year_str)
    if month < 1 or month > 12:
        return False
    now = datetime.utcnow()
    if year < now.year:
        return False
    if year == now.year and month < now.month:
        return False
    return True


def process_card_payment(data: PaymentCardIn) -> PaymentResultOut:
    if not _is_valid_luhn(data.number):
        return PaymentResultOut(status="RECUSADO", message="Número de cartão inválido.")
    if not _is_future_expiration(data.expiration):
        return PaymentResultOut(status="RECUSADO", message="Cartão expirado.")

    return PaymentResultOut(
        status="APROVADO",
        transaction_id=uuid.uuid4(),
        message="Pagamento aprovado.",
    )