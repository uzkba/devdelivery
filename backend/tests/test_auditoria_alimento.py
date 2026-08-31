import uuid
from app.model.models import Food, FoodCategory, AuditLog


def _criar_categoria(db, restaurante):
    categoria = FoodCategory(restaurant_id=restaurante.id, name="Pratos principais")
    db.add(categoria)
    db.flush()
    db.refresh(categoria)
    return categoria


def test_criar_alimento_gera_log_auditoria(db, client, restaurante, admin_user, token_para):
    categoria = _criar_categoria(db, restaurante)
    token = token_para(admin_user)

    payload = {
        "categoria_id": str(categoria.id),
        "nome": "Feijoada",
        "descricao": "Feijoada completa",
        "preco_base": "25.90",
    }
    resposta = client.post(
        "/alimentos", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 201

    log = (
        db.query(AuditLog)
        .filter_by(entity="alimento", action="CRIACAO")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log is not None
    assert log.user_id == admin_user.id
    assert log.restaurant_id == restaurante.id
    assert log.previous_data is None
    assert log.new_data["name"] == "Feijoada"


def test_atualizar_alimento_gera_log_com_diff(db, client, restaurante, admin_user, token_para):
    categoria = _criar_categoria(db, restaurante)
    alimento = Food(
        restaurant_id=restaurante.id,
        category_id=categoria.id,
        name="Feijoada",
        base_price="25.90",
    )
    db.add(alimento)
    db.flush()
    db.refresh(alimento)

    token = token_para(admin_user)
    resposta = client.put(
        f"/alimentos/{alimento.id}",
        json={"preco_base": "29.90"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 200

    log = (
        db.query(AuditLog)
        .filter_by(entity="alimento", entity_id=str(alimento.id), action="EDICAO")
        .first()
    )
    assert log is not None
    assert log.previous_data["base_price"] == "25.90"
    assert log.new_data["base_price"] == "29.90"


def test_atualizar_alimento_sem_mudancas_nao_gera_log(db, client, restaurante, admin_user, token_para):
    categoria = _criar_categoria(db, restaurante)
    alimento = Food(
        restaurant_id=restaurante.id, category_id=categoria.id, name="Feijoada", base_price="25.90"
    )
    db.add(alimento)
    db.flush()
    db.refresh(alimento)

    token = token_para(admin_user)
    resposta = client.put(
        f"/alimentos/{alimento.id}", json={}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 200

    total_logs = db.query(AuditLog).filter_by(entity="alimento", entity_id=str(alimento.id)).count()
    assert total_logs == 0


def test_desativar_alimento_gera_log_exclusao(db, client, restaurante, admin_user, token_para):
    categoria = _criar_categoria(db, restaurante)
    alimento = Food(
        restaurant_id=restaurante.id, category_id=categoria.id, name="Feijoada", base_price="25.90"
    )
    db.add(alimento)
    db.flush()
    db.refresh(alimento)

    token = token_para(admin_user)
    resposta = client.delete(
        f"/alimentos/{alimento.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 204

    log = db.query(AuditLog).filter_by(entity="alimento", action="EXCLUSAO").first()
    assert log is not None
    assert log.previous_data["is_active"] is True
    assert log.new_data["is_active"] is False


def test_desativar_alimento_ja_inativo_retorna_400_sem_log_duplicado(
    db, client, restaurante, admin_user, token_para
):
    categoria = _criar_categoria(db, restaurante)
    alimento = Food(
        restaurant_id=restaurante.id, category_id=categoria.id, name="Feijoada",
        base_price="25.90", is_active=False,
    )
    db.add(alimento)
    db.flush()
    db.refresh(alimento)

    token = token_para(admin_user)
    resposta = client.delete(
        f"/alimentos/{alimento.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 400

    total_logs = db.query(AuditLog).filter_by(entity="alimento", action="EXCLUSAO").count()
    assert total_logs == 0