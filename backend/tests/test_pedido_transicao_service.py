import uuid

import pytest
from fastapi import HTTPException

from app.core.seguranca import hash_password
from app.model.models import AdminUser, OrderServiceType, OrderStatus, OrderStatusHistory
from app.services import pedido_service


def _pares(db, pedido):
    por_id = {s.id: s.code for s in db.query(OrderStatus).all()}
    historico = db.query(OrderStatusHistory).filter_by(order_id=pedido.id).all()
    return {(por_id[h.previous_status_id], por_id[h.new_status_id]) for h in historico}


def _transicionar(db, pedido, usuario, codigo, **extra):
    return pedido_service.transicionar_pedido(
        db, pedido.id, pedido.restaurant_id, usuario.id, codigo, **extra
    )


def _usuario(db, restaurante, login, papel, ativo=True):
    usuario = AdminUser(
        restaurant_id=restaurante.id,
        name=login,
        login=login,
        password_hash=hash_password("senha123"),
        role=papel,
        is_active=ativo,
    )
    db.add(usuario)
    db.flush()
    return usuario


def test_fluxo_completo_de_entrega(db, novo_pedido, admin_user, entregador_user):
    pedido = novo_pedido()

    _transicionar(db, pedido, admin_user, "CONFIRMADO")
    _transicionar(db, pedido, admin_user, "EM_PREPARO")
    _transicionar(db, pedido, admin_user, "PRONTO")
    _transicionar(
        db, pedido, admin_user, "SAIU_PARA_ENTREGA", entregador_id=entregador_user.id
    )
    resultado = _transicionar(db, pedido, admin_user, "ENTREGUE")

    assert resultado.status.code == "ENTREGUE"
    assert resultado.driver_id == entregador_user.id
    assert _pares(db, pedido) == {
        ("CRIADO", "CONFIRMADO"),
        ("CONFIRMADO", "EM_PREPARO"),
        ("EM_PREPARO", "PRONTO"),
        ("PRONTO", "SAIU_PARA_ENTREGA"),
        ("SAIU_PARA_ENTREGA", "ENTREGUE"),
    }


def test_fluxo_completo_de_retirada(db, novo_pedido, admin_user):
    pedido = novo_pedido(service_type=OrderServiceType.PICKUP)

    for codigo in ("CONFIRMADO", "EM_PREPARO", "PRONTO", "RETIRADO"):
        resultado = _transicionar(db, pedido, admin_user, codigo)

    assert resultado.status.code == "RETIRADO"
    assert resultado.driver_id is None
    assert len(_pares(db, pedido)) == 4


def test_registra_quem_mudou_o_status(db, novo_pedido, atendente_user):
    pedido = novo_pedido()

    _transicionar(db, pedido, atendente_user, "CONFIRMADO")

    historico = db.query(OrderStatusHistory).filter_by(order_id=pedido.id).one()
    assert historico.changed_by == atendente_user.id
    assert historico.note is None


def test_nao_pula_etapa_e_nao_grava_nada(db, novo_pedido, admin_user):
    pedido = novo_pedido()

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "PRONTO")

    assert erro.value.status_code == 422
    assert pedido.status.code == "CRIADO"
    assert _pares(db, pedido) == set()


def test_retirada_nao_pode_sair_para_entrega(db, novo_pedido, admin_user, entregador_user):
    pedido = novo_pedido("PRONTO", service_type=OrderServiceType.PICKUP)

    with pytest.raises(HTTPException) as erro:
        _transicionar(
            db, pedido, admin_user, "SAIU_PARA_ENTREGA", entregador_id=entregador_user.id
        )

    assert erro.value.status_code == 422
    assert pedido.status.code == "PRONTO"


def test_entrega_nao_pode_ser_retirada(db, novo_pedido, admin_user):
    pedido = novo_pedido("PRONTO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "RETIRADO")

    assert erro.value.status_code == 422


@pytest.mark.parametrize("final", ["ENTREGUE", "CANCELADO", "RECUSADO"])
def test_status_final_nao_muda_mais(db, novo_pedido, admin_user, final):
    pedido = novo_pedido(final)

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CANCELADO", motivo="Tentativa depois do fim")

    assert erro.value.status_code == 422
    assert "finalizado" in erro.value.detail or "já está" in erro.value.detail


def test_mesmo_status_e_recusado(db, novo_pedido, admin_user):
    pedido = novo_pedido("CONFIRMADO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CONFIRMADO")

    assert erro.value.status_code == 422
    assert "já está" in erro.value.detail


def test_recusar_guarda_o_motivo_no_pedido_e_no_historico(db, novo_pedido, admin_user):
    pedido = novo_pedido()

    resultado = _transicionar(db, pedido, admin_user, "RECUSADO", motivo="  Sem estoque hoje  ")

    assert resultado.status.code == "RECUSADO"
    assert resultado.status_reason == "Sem estoque hoje"
    historico = db.query(OrderStatusHistory).filter_by(order_id=pedido.id).one()
    assert historico.note == "Sem estoque hoje"


def test_cancelar_guarda_o_motivo(db, novo_pedido, admin_user):
    pedido = novo_pedido("EM_PREPARO")

    resultado = _transicionar(db, pedido, admin_user, "CANCELADO", motivo="Cliente desistiu")

    assert resultado.status.code == "CANCELADO"
    assert resultado.status_reason == "Cliente desistiu"


@pytest.mark.parametrize("motivo", [None, "", "   ", "ab", "x" * 301])
def test_recusar_e_cancelar_exigem_motivo_valido(db, novo_pedido, admin_user, motivo):
    pedido = novo_pedido("CONFIRMADO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CANCELADO", motivo=motivo)

    assert erro.value.status_code == 422
    assert "motivo" in erro.value.detail.lower()
    assert pedido.status.code == "CONFIRMADO"
    assert pedido.status_reason is None


def test_criado_nao_cancela_so_recusa(db, novo_pedido, admin_user):
    pedido = novo_pedido()

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CANCELADO", motivo="Mudei de ideia")

    assert erro.value.status_code == 422


def test_motivo_fora_de_recusa_ou_cancelamento_e_recusado(db, novo_pedido, admin_user):
    pedido = novo_pedido()

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CONFIRMADO", motivo="Algum texto")

    assert erro.value.status_code == 422
    assert pedido.status.code == "CRIADO"


def test_enviar_exige_entregador(db, novo_pedido, admin_user):
    pedido = novo_pedido("PRONTO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "SAIU_PARA_ENTREGA")

    assert erro.value.status_code == 422
    assert "entregador" in erro.value.detail.lower()
    assert pedido.status.code == "PRONTO"


def test_entregador_de_outro_restaurante_e_recusado(
    db, novo_pedido, admin_user, outro_restaurante
):
    de_fora = _usuario(db, outro_restaurante, "ze.entregador", "entregador")
    pedido = novo_pedido("PRONTO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "SAIU_PARA_ENTREGA", entregador_id=de_fora.id)

    assert erro.value.status_code == 422
    assert "não encontrado" in erro.value.detail
    assert pedido.driver_id is None


def test_usuario_que_nao_e_entregador_e_recusado(db, novo_pedido, admin_user, atendente_user):
    pedido = novo_pedido("PRONTO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(
            db, pedido, admin_user, "SAIU_PARA_ENTREGA", entregador_id=atendente_user.id
        )

    assert erro.value.status_code == 422
    assert "não encontrado" in erro.value.detail


def test_entregador_inativo_e_recusado(db, novo_pedido, admin_user, restaurante):
    inativo = _usuario(db, restaurante, "inativo.entregador", "entregador", ativo=False)
    pedido = novo_pedido("PRONTO")

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "SAIU_PARA_ENTREGA", entregador_id=inativo.id)

    assert erro.value.status_code == 422
    assert "inativo" in erro.value.detail


def test_entregador_so_vale_ao_enviar(db, novo_pedido, admin_user, entregador_user):
    pedido = novo_pedido()

    with pytest.raises(HTTPException) as erro:
        _transicionar(db, pedido, admin_user, "CONFIRMADO", entregador_id=entregador_user.id)

    assert erro.value.status_code == 422
    assert pedido.status.code == "CRIADO"


def test_pedido_de_outro_restaurante_da_404(db, novo_pedido, outro_admin_user, outro_restaurante):
    pedido = novo_pedido()

    with pytest.raises(HTTPException) as erro:
        pedido_service.transicionar_pedido(
            db, pedido.id, outro_restaurante.id, outro_admin_user.id, "CONFIRMADO"
        )

    assert erro.value.status_code == 404
    assert pedido.status.code == "CRIADO"


def test_pedido_inexistente_da_404(db, restaurante, admin_user):
    with pytest.raises(HTTPException) as erro:
        pedido_service.transicionar_pedido(
            db, uuid.uuid4(), restaurante.id, admin_user.id, "CONFIRMADO"
        )

    assert erro.value.status_code == 404