"""
Testes do fluxo de pagamento (POST /pagamentos/pix, POST /pagamentos/cartao,
GET/PUT /admin/conta-recebimento).

Duas suposições que não consegui confirmar com os arquivos que vi até agora
(se alguma estiver errada, é só me mandar o arquivo certo que eu ajusto):

1. Autenticação via header "Authorization: Bearer <token>" - padrão de quase
   todo FastAPI com JWT, mas não vi o `depedencias.py`/`get_current_client`
   pra confirmar 100%.
2. O model `ReceivingAccount` (models.py) já está com todos os atributos
   Python batendo com os nomes do schema (pix_key, pix_key_type,
   account_holder, city, active) - só `account_holder` foi confirmado (era
   o bug que apareceu no PUT); os outros eu assumi que seguiram o mesmo
   padrão da tradução.
"""

import uuid
import re

import pytest

from app.model.models import ReceivingAccount


# ---------- helpers ----------

def _crc16(payload: str) -> str:
    """Reimplementação independente do CRC16 usado no backend (mesmo
    algoritmo, poly 0x1021 / init 0xFFFF), só pra validar de fora que o
    código Pix gerado bate com o que um leitor de verdade calcularia."""
    polinomio = 0x1021
    resultado = 0xFFFF
    for byte in payload.encode("utf-8"):
        resultado ^= byte << 8
        for _ in range(8):
            if resultado & 0x8000:
                resultado = ((resultado << 1) ^ polinomio) & 0xFFFF
            else:
                resultado = (resultado << 1) & 0xFFFF
    return format(resultado, "04X")


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


CARTAO_VALIDO = "4532015112830366"  # passa no Luhn
CARTAO_INVALIDO = "4532015112830367"  # mesmo número, último dígito trocado (falha no Luhn)


@pytest.fixture()
def conta_recebimento(db):
    conta = ReceivingAccount(
        pix_key="chave-pix-teste@exemplo.com",
        pix_key_type="EMAIL",
        account_holder="FULANO DE TAL",
        city="SAO PAULO",
        active=True,
    )
    db.add(conta)
    db.flush()
    db.refresh(conta)
    return conta


# ---------- POST /pagamentos/pix ----------

class TestGerarPix:
    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.post("/pagamentos/pix", json={"amount": 27})
        assert resp.status_code == 401

    def test_sem_conta_configurada_retorna_503(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/pix",
            json={"amount": 27},
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 503

    def test_valor_deve_ser_positivo(self, client, cliente, token_para_cliente, conta_recebimento):
        resp = client.post(
            "/pagamentos/pix",
            json={"amount": 0},
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 422

    def test_gera_codigo_pix_valido(self, client, cliente, token_para_cliente, conta_recebimento):
        resp = client.post(
            "/pagamentos/pix",
            json={"amount": "27.50"},
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["pix_key"] == conta_recebimento.pix_key
        assert data["account_holder"] == conta_recebimento.account_holder
        assert float(data["amount"]) == 27.50

        codigo = data["copy_and_paste_code"]
        # payload EMV básico
        assert codigo.startswith("000201")
        assert "BR.GOV.BCB.PIX" in codigo
        assert conta_recebimento.pix_key in codigo
        assert "5802BR" in codigo  # país = BR
        assert "540527.50" in codigo  # campo 54 (valor): tag 54, tamanho 05, "27.50"

        # confere o CRC16 dos últimos 4 caracteres contra o restante do payload
        payload_sem_crc, crc_informado = codigo[:-4], codigo[-4:]
        assert crc_informado == _crc16(payload_sem_crc)

    def test_titular_e_cidade_sao_sanitizados_no_codigo(self, client, cliente, token_para_cliente, db):
        conta = ReceivingAccount(
            pix_key="11999990000",
            pix_key_type="TELEFONE",
            account_holder="José D'Ávila-Souza",  # 19 caracteres com acento/apóstrofo
            city="São José dos Campos",  # > 15 caracteres, com acento
            active=True,
        )
        db.add(conta)
        db.flush()

        resp = client.post(
            "/pagamentos/pix",
            json={"amount": 10},
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 200
        codigo = resp.json()["copy_and_paste_code"]

        # mesma sanitização do backend: só A-Z0-9 e espaço, maiúsculo, cortado
        # em 25 (titular) / 15 (cidade) caracteres - reimplementada aqui pra
        # calcular o valor esperado e comparar, em vez de só checar substring
        titular_esperado = re.sub(r"[^A-Za-z0-9 ]", "", conta.account_holder).strip().upper()[:25]
        cidade_esperada = re.sub(r"[^A-Za-z0-9 ]", "", conta.city).strip().upper()[:15]

        assert f"59{len(titular_esperado):02d}{titular_esperado}" in codigo
        assert f"60{len(cidade_esperada):02d}{cidade_esperada}" in codigo
        assert "'" not in codigo


# ---------- POST /pagamentos/cartao ----------

class TestPagarComCartao:
    def _payload(self, **overrides):
        payload = {
            "method": "CARTAO_CREDITO",
            "number": CARTAO_VALIDO,
            "name": "FULANO DE TAL",
            "expiration": "12/30",
            "cvv": "123",
            "amount": 27.5,
        }
        payload.update(overrides)
        return payload

    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.post("/pagamentos/cartao", json=self._payload())
        assert resp.status_code == 401

    def test_cartao_valido_e_aprovado(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APROVADO"
        assert data["transaction_id"] is not None
        # não deve quebrar como UUID
        uuid.UUID(data["transaction_id"])

    def test_numero_invalido_no_luhn_e_recusado(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(number=CARTAO_INVALIDO),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RECUSADO"
        assert data["transaction_id"] is None

    def test_cartao_vencido_e_recusado(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(expiration="01/20"),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RECUSADO"

    def test_numero_curto_demais_e_erro_de_validacao(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(number="123456"),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 422

    def test_formato_de_validade_invalido_e_erro_de_validacao(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(expiration="2030-12"),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 422

    def test_cvv_nao_numerico_e_erro_de_validacao(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(cvv="abc"),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 422

    def test_valor_deve_ser_positivo(self, client, cliente, token_para_cliente):
        resp = client.post(
            "/pagamentos/cartao",
            json=self._payload(amount=0),
            headers=_auth(token_para_cliente(cliente)),
        )
        assert resp.status_code == 422


# ---------- GET/PUT /admin/conta-recebimento ----------

PAYLOAD_CONTA = {
    "pix_key": "nova-chave@exemplo.com",
    "pix_key_type": "EMAIL",
    "account_holder": "CICLANO DA SILVA",
    "city": "PARELHAS",
}


class TestObterConta:
    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.get("/admin/conta-recebimento")
        assert resp.status_code == 401

    def test_role_sem_permissao_retorna_403(self, client, atendente_user, token_para):
        resp = client.get("/admin/conta-recebimento", headers=_auth(token_para(atendente_user)))
        assert resp.status_code == 403

    def test_quando_nao_existe_retorna_404(self, client, admin_user, token_para):
        resp = client.get("/admin/conta-recebimento", headers=_auth(token_para(admin_user)))
        assert resp.status_code == 404

    def test_admin_com_conta_configurada_retorna_200(self, client, admin_user, token_para, conta_recebimento):
        resp = client.get("/admin/conta-recebimento", headers=_auth(token_para(admin_user)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(conta_recebimento.id)
        assert data["pix_key"] == conta_recebimento.pix_key
        assert data["account_holder"] == conta_recebimento.account_holder
        assert data["active"] is True


class TestAtualizarConta:
    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.put("/admin/conta-recebimento", json=PAYLOAD_CONTA)
        assert resp.status_code == 401

    def test_role_sem_permissao_retorna_403(self, client, atendente_user, token_para):
        resp = client.put(
            "/admin/conta-recebimento",
            json=PAYLOAD_CONTA,
            headers=_auth(token_para(atendente_user)),
        )
        assert resp.status_code == 403

    def test_payload_invalido_retorna_422(self, client, admin_user, token_para):
        payload_invalido = {**PAYLOAD_CONTA, "pix_key_type": "TIPO_QUE_NAO_EXISTE"}
        resp = client.put(
            "/admin/conta-recebimento",
            json=payload_invalido,
            headers=_auth(token_para(admin_user)),
        )
        assert resp.status_code == 422

    def test_cria_conta_quando_nao_existe(self, client, admin_user, token_para, db):
        resp = client.put(
            "/admin/conta-recebimento",
            json=PAYLOAD_CONTA,
            headers=_auth(token_para(admin_user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pix_key"] == PAYLOAD_CONTA["pix_key"]
        assert data["active"] is True

        contas = db.query(ReceivingAccount).all()
        assert len(contas) == 1
        assert contas[0].pix_key == PAYLOAD_CONTA["pix_key"]

    def test_atualiza_conta_existente_sem_duplicar(self, client, admin_user, token_para, conta_recebimento, db):
        resp = client.put(
            "/admin/conta-recebimento",
            json=PAYLOAD_CONTA,
            headers=_auth(token_para(admin_user)),
        )
        assert resp.status_code == 200
        data = resp.json()

        # mesma linha atualizada, não uma nova (single-tenant: sempre 1 conta ativa)
        assert data["id"] == str(conta_recebimento.id)
        assert data["pix_key"] == PAYLOAD_CONTA["pix_key"]
        assert data["account_holder"] == PAYLOAD_CONTA["account_holder"]

        contas = db.query(ReceivingAccount).all()
        assert len(contas) == 1
