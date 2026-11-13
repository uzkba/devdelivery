import asyncio
import uuid

from app.core.websockets import ConnectionManager
from app.model.models import OrderServiceType
from app.services import notificacao_service


class FakeSocket:
    def __init__(self):
        self.recebidas = []

    async def accept(self):
        return None

    async def send_json(self, message):
        self.recebidas.append(message)


def test_evento_de_entrega_pronta(novo_pedido):
    pedido = novo_pedido("PRONTO")

    evento = notificacao_service.montar_evento_status(pedido)

    assert evento == {
        "tipo": "STATUS_PEDIDO",
        "pedido_id": str(pedido.id),
        "numero_pedido": pedido.order_number,
        "tipo_atendimento": "ENTREGA",
        "status": "PRONTO",
        "status_rotulo": "Pronto, aguardando o entregador",
        "final": False,
        "motivo": None,
        "entregador": None,
        "acoes_disponiveis": ["enviar", "cancelar"],
    }


def test_evento_de_retirada_pronta(novo_pedido):
    pedido = novo_pedido("PRONTO", service_type=OrderServiceType.PICKUP)

    evento = notificacao_service.montar_evento_status(pedido)

    assert evento["status_rotulo"] == "Pronto para retirada"
    assert evento["acoes_disponiveis"] == ["retirado", "cancelar"]


def test_evento_traz_o_nome_do_entregador(db, novo_pedido, entregador_user):
    pedido = novo_pedido("SAIU_PARA_ENTREGA")
    pedido.driver_id = entregador_user.id
    db.flush()
    db.refresh(pedido)

    evento = notificacao_service.montar_evento_status(pedido)

    assert evento["entregador"] == "Pedro Entregador"


def test_publicar_so_atinge_o_restaurante_e_o_cliente_do_pedido(monkeypatch):
    gerenciador = ConnectionManager()
    monkeypatch.setattr(notificacao_service, "manager", gerenciador)
    restaurante, outro_restaurante = uuid.uuid4(), uuid.uuid4()
    cliente, outro_cliente = uuid.uuid4(), uuid.uuid4()
    sockets = {nome: FakeSocket() for nome in ("rest", "outro_rest", "cli", "outro_cli")}
    asyncio.run(gerenciador.connect(sockets["rest"], restaurante))
    asyncio.run(gerenciador.connect(sockets["outro_rest"], outro_restaurante))
    asyncio.run(gerenciador.connect_client(sockets["cli"], cliente))
    asyncio.run(gerenciador.connect_client(sockets["outro_cli"], outro_cliente))

    asyncio.run(notificacao_service.publicar(restaurante, cliente, {"tipo": "X"}))

    assert sockets["rest"].recebidas == [{"tipo": "X"}]
    assert sockets["cli"].recebidas == [{"tipo": "X"}]
    assert sockets["outro_rest"].recebidas == []
    assert sockets["outro_cli"].recebidas == []