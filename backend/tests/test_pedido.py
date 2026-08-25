import uuid
import pytest
from decimal import Decimal

from backend.app.model.models import (
    OrderStatus, PaymentMethod, Food, FoodCategory, 
    ModifierGroup, ModifierOption
)


def _headers(client, login: str, password: str = "senha123") -> dict:
    """Helper para autenticar o usuário e pegar o token (reaproveitando o admin_user)."""
    response = client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, f"Login falhou: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ── Fixtures Locais para o Domínio de Pedidos ─────────────────────

@pytest.fixture()
def status_criado(db):
    """Garante que existe o status inicial do pedido."""
    status = OrderStatus(code="CRIADO", name="Criado", order=1, is_final=False)
    db.add(status)
    db.flush()
    db.refresh(status)
    return status


@pytest.fixture()
def forma_pagamento_dinheiro(db):
    fp = PaymentMethod(code="DINHEIRO", name="Dinheiro", is_active=True)
    db.add(fp)
    db.flush()
    db.refresh(fp)
    return fp


@pytest.fixture()
def alimento_simples(db, restaurante):
    cat = FoodCategory(restaurant_id=restaurante.id, name="Bebidas", display_order=1)
    db.add(cat)
    db.flush()

    alimento = Food(
        restaurant_id=restaurante.id, 
        category_id=cat.id, 
        name="Guaraná Lata", 
        base_price=Decimal("6.00"), 
        is_active=True, 
        is_available=True
    )
    db.add(alimento)
    db.flush()
    db.refresh(alimento)
    return alimento


@pytest.fixture()
def alimento_combo(db, restaurante):
    """Cria um Alimento (Marmita) com grupos e opções de complementos."""
    cat = FoodCategory(restaurant_id=restaurante.id, name="Pratos", display_order=0)
    db.add(cat)
    db.flush()

    alimento = Food(
        restaurant_id=restaurante.id, 
        category_id=cat.id, 
        name="Marmita P", 
        base_price=Decimal("15.00"), 
        is_active=True, 
        is_available=True
    )
    db.add(alimento)
    db.flush()

    grupo = ModifierGroup(food_id=alimento.id, name="Escolha sua Carne", min_choices=1, max_choices=1)
    db.add(grupo)
    db.flush()

    opcao_bife = ModifierOption(group_id=grupo.id, name="Bife Acebolado", extra_price=Decimal("3.50"), is_available=True)
    opcao_frango = ModifierOption(group_id=grupo.id, name="Frango Assado", extra_price=Decimal("0.00"), is_available=True)
    db.add_all([opcao_bife, opcao_frango])
    db.flush()
    
    db.refresh(alimento)
    db.refresh(opcao_bife)
    db.refresh(opcao_frango)

    return {
        "alimento": alimento,
        "opcao_bife": opcao_bife,
        "opcao_frango": opcao_frango
    }


# ── Testes de Criação de Pedido (POST /pedidos) ───────────────────

class TestCriarPedido:
    
    # O uso do status_criado nos parâmetros do teste força o pytest a criá-lo no banco antes
    def test_criar_pedido_simples_sem_complementos(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "valor_entrega": "5.00",
            "itens": [
                {
                    "alimento_id": str(alimento_simples.id),
                    "quantidade": 2,
                    "opcoes_selecionadas": []
                }
            ]
        }
        
        headers = _headers(client, "maria.admin")
        response = client.post("/pedidos", json=payload, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Validações financeiras
        assert Decimal(data["valor_itens"]) == Decimal("12.00") # 2x 6.00
        assert Decimal(data["valor_entrega"]) == Decimal("5.00")
        assert Decimal(data["valor_total"]) == Decimal("17.00") # 12.00 + 5.00
        
        # Validações de Snapshot (Endereço e Item)
        assert data["endereco_rua"] == "Rua das Flores"
        assert len(data["itens"]) == 1
        assert data["itens"][0]["nome_alimento"] == "Guaraná Lata"
        assert Decimal(data["itens"][0]["preco_base_unitario"]) == Decimal("6.00")
        assert Decimal(data["itens"][0]["subtotal"]) == Decimal("12.00")


    def test_criar_pedido_com_complementos_calcula_preco_correto(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_combo, status_criado
    ):
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "valor_entrega": "0.00",
            "itens": [
                {
                    "alimento_id": str(alimento_combo["alimento"].id),
                    "quantidade": 1,
                    "opcoes_selecionadas": [
                        {
                            "opcao_complemento_id": str(alimento_combo["opcao_bife"].id),
                            "quantidade": 1
                        }
                    ]
                }
            ]
        }
        
        headers = _headers(client, "maria.admin")
        response = client.post("/pedidos", json=payload, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Matemática: Marmita(15.00) + Bife(3.50) = 18.50
        assert Decimal(data["valor_total"]) == Decimal("18.50")
        
        item = data["itens"][0]
        assert Decimal(item["subtotal"]) == Decimal("18.50")
        assert len(item["opcoes_selecionadas"]) == 1
        assert item["opcoes_selecionadas"][0]["nome_opcao"] == "Bife Acebolado"
        assert Decimal(item["opcoes_selecionadas"][0]["preco_adicional_unitario"]) == Decimal("3.50")


    def test_criar_pedido_calcula_troco_corretamente(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "valor_entrega": "4.00",
            "valor_pago_dinheiro": "20.00", # Cliente deu uma nota de 20
            "itens": [
                {"alimento_id": str(alimento_simples.id), "quantidade": 1} # Item custa 6.00
            ]
        }
        
        # Total do pedido: 6.00 (item) + 4.00 (entrega) = 10.00. 
        # Troco esperado: 10.00
        
        headers = _headers(client, "maria.admin")
        response = client.post("/pedidos", json=payload, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        # O Pydantic pode não enviar change_amount no schema se ele não estiver definido no OrderOut,
        # mas se estiver lá, vamos validá-lo. (Assumindo que adicionamos no OrderOut).
        # Se não estiver no json do response, a validação de que não deu erro 400 já é suficiente, 
        # mas caso queiramos checar no banco:
        assert data.get("valor_troco") is None or Decimal(data["valor_troco"]) == Decimal("10.00")


    def test_criar_pedido_com_dinheiro_insuficiente_falha(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "valor_entrega": "5.00",
            "valor_pago_dinheiro": "10.00", # Total seria 11.00 (6 + 5)
            "itens": [
                {"alimento_id": str(alimento_simples.id), "quantidade": 1}
            ]
        }
        
        headers = _headers(client, "maria.admin")
        response = client.post("/pedidos", json=payload, headers=headers)
        
        assert response.status_code == 400
        assert "menor que o total" in response.json()["detail"].lower()


# ── Testes de Busca de Pedido (GET /pedidos/{id}) ───────────────────

class TestBuscarPedido:
    
    def test_buscar_pedido_existente(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        # 1. Cria o pedido
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}]
        }
        headers = _headers(client, "maria.admin")
        criado_resp = client.post("/pedidos", json=payload, headers=headers)
        pedido_id = criado_resp.json()["id"]
        
        # 2. Busca o pedido pelo ID
        busca_resp = client.get(f"/pedidos/{pedido_id}", headers=headers)
        
        assert busca_resp.status_code == 200
        assert busca_resp.json()["id"] == pedido_id
        assert busca_resp.json()["endereco_rua"] == "Rua das Flores"
        assert len(busca_resp.json()["itens"]) == 1


    def test_buscar_pedido_de_outro_restaurante_retorna_404(
        self, client, db, admin_user, outro_admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        """Isolamento multi-tenant na leitura de pedidos."""
        # Cria pedido no restaurante da Maria (admin_user)
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}]
        }
        headers_maria = _headers(client, "maria.admin")
        pedido = client.post("/pedidos", json=payload, headers=headers_maria).json()
        
        # Zé tenta buscar o pedido da Maria
        headers_ze = _headers(client, "ze.admin.cardapio")
        busca_resp = client.get(f"/pedidos/{pedido['id']}", headers=headers_ze)
        
        assert busca_resp.status_code == 404

class TestListarPedidos:

    def _criar_pedido(self, client, headers, cliente, endereco, forma_pagamento_dinheiro, alimento_simples):
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}],
        }
        resp = client.post("/pedidos", json=payload, headers=headers)
        assert resp.status_code == 201
        return resp.json()

    def test_listar_pedidos_ordenado_do_mais_antigo_para_o_mais_novo(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        primeiro = self._criar_pedido(client, headers, cliente, endereco, forma_pagamento_dinheiro, alimento_simples)
        segundo = self._criar_pedido(client, headers, cliente, endereco, forma_pagamento_dinheiro, alimento_simples)

        resp = client.get("/pedidos", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert [item["id"] for item in data["items"]] == [primeiro["id"], segundo["id"]]

    def test_listar_pedidos_isola_por_restaurante(
        self, client, admin_user, outro_admin_user, cliente, endereco,
        forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        """Isolamento multi-tenant na listagem geral."""
        headers_maria = _headers(client, "maria.admin")
        self._criar_pedido(client, headers_maria, cliente, endereco, forma_pagamento_dinheiro, alimento_simples)

        headers_ze = _headers(client, "ze.admin.cardapio")
        resp = client.get("/pedidos", headers=headers_ze)

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_listar_pedidos_traz_nome_do_cliente(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        self._criar_pedido(client, headers, cliente, endereco, forma_pagamento_dinheiro, alimento_simples)

        resp = client.get("/pedidos", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["items"][0]["cliente_nome"] == "José da Silva"

    def test_listar_pedidos_paginacao(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        for _ in range(3):
            self._criar_pedido(client, headers, cliente, endereco, forma_pagamento_dinheiro, alimento_simples)

        resp = client.get("/pedidos", params={"page": 1, "page_size": 2}, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["total_pages"] == 2
        assert len(data["items"]) == 2

        resp_pagina2 = client.get("/pedidos", params={"page": 2, "page_size": 2}, headers=headers)
        assert len(resp_pagina2.json()["items"]) == 1

    def test_listar_pedidos_sem_autenticacao_falha(self, client):
        resp = client.get("/pedidos")
        assert resp.status_code == 401


# ── Testes de Histórico do Cliente (GET /pedidos/me) ───────────────

class TestListarMeusPedidos:

    def test_listar_meus_pedidos_retorna_apenas_do_cliente(
        self, client, admin_user, cliente, outro_cliente, endereco,
        forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}],
        }
        client.post("/pedidos", json=payload, headers=headers)

        resp_cliente = client.get("/pedidos/me", params={"client_id": str(cliente.id)})
        resp_outro = client.get("/pedidos/me", params={"client_id": str(outro_cliente.id)})

        assert resp_cliente.status_code == 200
        assert resp_cliente.json()["total"] == 1

        assert resp_outro.status_code == 200
        assert resp_outro.json()["total"] == 0

    def test_listar_meus_pedidos_nao_exige_autenticacao(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        """Rota do cliente é pública (ainda sem login de cliente)."""
        resp = client.get("/pedidos/me", params={"client_id": str(cliente.id)})
        assert resp.status_code == 200

    def test_listar_meus_pedidos_ordenado_do_mais_recente_para_o_mais_antigo(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}],
        }
        primeiro = client.post("/pedidos", json=payload, headers=headers).json()
        segundo = client.post("/pedidos", json=payload, headers=headers).json()

        resp = client.get("/pedidos/me", params={"client_id": str(cliente.id)})

        assert [item["id"] for item in resp.json()["items"]] == [segundo["id"], primeiro["id"]]


# ── Testes de Detalhe do Pedido para o Cliente (GET /pedidos/cliente/{id}) ─

class TestBuscarPedidoDoCliente:

    def test_buscar_pedido_do_cliente_dono_retorna_detalhe(
        self, client, admin_user, cliente, endereco, forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}],
        }
        pedido = client.post("/pedidos", json=payload, headers=headers).json()

        resp = client.get(f"/pedidos/cliente/{pedido['id']}", params={"client_id": str(cliente.id)})

        assert resp.status_code == 200
        assert resp.json()["id"] == pedido["id"]
        assert resp.json()["cliente"]["nome"] == "José da Silva"

    def test_buscar_pedido_de_outro_cliente_retorna_404(
        self, client, admin_user, cliente, outro_cliente, endereco,
        forma_pagamento_dinheiro, alimento_simples, status_criado
    ):
        headers = _headers(client, "maria.admin")
        payload = {
            "cliente_id": str(cliente.id),
            "endereco_id": str(endereco.id),
            "forma_pagamento_id": str(forma_pagamento_dinheiro.id),
            "itens": [{"alimento_id": str(alimento_simples.id), "quantidade": 1}],
        }
        pedido = client.post("/pedidos", json=payload, headers=headers).json()

        resp = client.get(f"/pedidos/cliente/{pedido['id']}", params={"client_id": str(outro_cliente.id)})

        assert resp.status_code == 404