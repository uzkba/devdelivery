import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

class Restaurant(Base):
    __tablename__ = "restaurante"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trade_name: Mapped[str] = mapped_column("nome_fantasia", String(150), nullable=False)
    cnpj: Mapped[str | None] = mapped_column("cnpj", String(18), unique=True)
    phone: Mapped[str | None] = mapped_column("telefone", String(20))
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)


class Client(Base):
    __tablename__ = "cliente"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    phone: Mapped[str] = mapped_column("telefone", String(20), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())
    hashed_password: Mapped[str] = mapped_column("senha_hash", String(255), nullable=False)
    addresses: Mapped[list["CustomerAddress"]] = relationship(back_populates="client")


class CustomerAddress(Base):
    __tablename__ = "endereco_cliente"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column("cliente_id", ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False)
    complement: Mapped[str | None] = mapped_column("complemento", String(50))
    street: Mapped[str] = mapped_column("rua", String(150), nullable=False)
    number: Mapped[str] = mapped_column("numero", String(5), nullable=False)
    neighborhood: Mapped[str] = mapped_column("bairro", String(50), nullable=False)
    reference_point: Mapped[str | None] = mapped_column("ponto_de_referencia", String(150))
    primary_address: Mapped[bool] = mapped_column("endereco_principal", Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="addresses")

    __table_args__ = (
        Index(
            "uq_endereco_principal_por_cliente_v2",
            "cliente_id",
            unique=True,
            postgresql_where=text("endereco_principal = true"),  # noqa: E712
        ),
    )


class PaymentMethod(Base):
    __tablename__ = "forma_pagamento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column("codigo", String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column("nome", String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)


class OrderStatus(Base):
    __tablename__ = "status_pedido"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column("codigo", String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column("nome", String(50), nullable=False)
    order: Mapped[int] = mapped_column("ordem", Integer, nullable=False)
    is_paid: Mapped[bool] = mapped_column("pago", Boolean, default=False, nullable=False)
    is_final: Mapped[bool] = mapped_column("is_final", Boolean, default=False, nullable=False)


class AdminUser(Base):
    __tablename__ = "usuario_admin"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    login: Mapped[str] = mapped_column("login", String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("senha_hash", String(255), nullable=False)
    role: Mapped[str] = mapped_column("papel", String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "papel IN ('admin','atendente','caixa','entregador')",
            name="ck_usuario_admin_papel",
        ),
    )


class FoodCategory(Base):
    __tablename__ = "categoria_alimento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False)
    display_order: Mapped[int] = mapped_column("ordem_exibicao", Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, server_default="true", nullable=False)
    is_main_dish: Mapped[bool] = mapped_column("prato_principal", Boolean, default=False, server_default="false", nullable=False)

    foods: Mapped[list["Food"]] = relationship(back_populates="category")

    __table_args__ = (UniqueConstraint("restaurante_id", "nome"),)


class Food(Base):
    __tablename__ = "alimento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column("categoria_id", ForeignKey("categoria_alimento.id"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text)
    base_price: Mapped[Decimal] = mapped_column("preco_base", Numeric(10, 2), default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    category: Mapped["FoodCategory"] = relationship(back_populates="foods")
    
    modifier_groups: Mapped[list["ModifierGroup"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("preco_base >= 0", name="ck_alimento_preco_base_positivo"),
    )
class ModifierGroup(Base):
    __tablename__ = "grupo_complemento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    food_id: Mapped[uuid.UUID] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False)
    min_choices: Mapped[int] = mapped_column("escolhas_minimas", Integer, default=0, nullable=False)
    max_choices: Mapped[int] = mapped_column("escolhas_maximas", Integer, nullable=False)
    display_order: Mapped[int] = mapped_column("ordem_exibicao", Integer, default=0)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True)
    
    food: Mapped["Food"] = relationship(back_populates="modifier_groups")
    options: Mapped[list["ModifierOption"]] = relationship(back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("escolhas_maximas >= escolhas_minimas", name="ck_grupo_complemento_limites"),
    )


class ModifierOption(Base):
    __tablename__ = "opcao_complemento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column("grupo_id", ForeignKey("grupo_complemento.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False) 
    extra_price: Mapped[Decimal] = mapped_column("preco_adicional", Numeric(10, 2), default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True)

    group: Mapped["ModifierGroup"] = relationship(back_populates="options")

class Menu(Base):
    __tablename__ = "cardapio"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    date: Mapped[date] = mapped_column("data", Date, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column("criado_por", ForeignKey("usuario_admin.id"))
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    items: Mapped[list["MenuItem"]] = relationship(back_populates="menu", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("restaurante_id", "data"),)

class MenuItem(Base):
    __tablename__ = "cardapio_item"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column("cardapio_id", ForeignKey("cardapio.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID] = mapped_column("alimento_id", ForeignKey("alimento.id"), nullable=False)
    
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True, nullable=False)
    day_price: Mapped[Decimal | None] = mapped_column("preco_dia", Numeric(10, 2))

    menu: Mapped["Menu"] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("cardapio_id", "alimento_id", name="uq_cardapio_item_alimento"),
        CheckConstraint("preco_dia IS NULL OR preco_dia >= 0", name="ck_cardapio_item_preco_dia"),
        Index("idx_cardapio_item_disponivel", "cardapio_id", "disponivel"),
    )


class CashClosing(Base):
    __tablename__ = "fechamento_caixa"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    start_date: Mapped[date] = mapped_column("data_inicio", Date, nullable=False)
    end_date: Mapped[date] = mapped_column("data_fim", Date, nullable=False)
    total_sales: Mapped[Decimal] = mapped_column("total_vendas", Numeric(10, 2), default=0, nullable=False)
    total_pix: Mapped[Decimal] = mapped_column("total_pix", Numeric(10, 2), default=0, nullable=False)
    total_cash: Mapped[Decimal] = mapped_column("total_dinheiro", Numeric(10, 2), default=0, nullable=False)
    total_debit: Mapped[Decimal] = mapped_column("total_debito", Numeric(10, 2), default=0, nullable=False)
    total_credit: Mapped[Decimal] = mapped_column("total_credito", Numeric(10, 2), default=0, nullable=False)
    total_other: Mapped[Decimal] = mapped_column("total_outros", Numeric(10, 2), default=0, nullable=False)
    total_cash_paid: Mapped[Decimal] = mapped_column("total_dinheiro_recebido", Numeric(10, 2), default=0, nullable=False)
    total_change: Mapped[Decimal] = mapped_column("total_troco", Numeric(10, 2), default=0, nullable=False)
    order_count: Mapped[int] = mapped_column("quantidade_pedidos", Integer, default=0, nullable=False)
    cancelled_count: Mapped[int] = mapped_column("quantidade_cancelados", Integer, default=0, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column("valor_esperado", Numeric(10, 2), default=0, nullable=False)
    reported_amount: Mapped[Decimal] = mapped_column("valor_informado", Numeric(10, 2), default=0, nullable=False)
    difference: Mapped[Decimal] = mapped_column("diferenca", Numeric(10, 2), default=0, nullable=False)
    closed_by: Mapped[uuid.UUID] = mapped_column("fechado_por", ForeignKey("usuario_admin.id"), nullable=False)
    closed_at: Mapped[datetime] = mapped_column("fechado_em", DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column("observacoes", Text)

    __table_args__ = (
    CheckConstraint("data_fim >= data_inicio", name="ck_fechamento_periodo_valido"),
    UniqueConstraint("restaurante_id", "data_inicio", "data_fim", name="uq_fechamento_restaurante_periodo"),
)

class Order(Base):
    __tablename__ = "pedido"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_number: Mapped[int] = mapped_column("numero_pedido", Integer, Identity(), unique=True, nullable=False)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column("cliente_id", ForeignKey("cliente.id"), nullable=False)
    status_id: Mapped[uuid.UUID] = mapped_column("status_id", ForeignKey("status_pedido.id"), nullable=False)
    payment_method_id: Mapped[uuid.UUID] = mapped_column("forma_pagamento_id", ForeignKey("forma_pagamento.id"), nullable=False)
    order_datetime: Mapped[datetime] = mapped_column("data_hora", DateTime, server_default=func.now())

    address_name: Mapped[str] = mapped_column("endereco_nome", String(150), nullable=False)
    address_phone: Mapped[str] = mapped_column("endereco_telefone", String(20), nullable=False)
    address_street: Mapped[str] = mapped_column("endereco_rua", String(150), nullable=False)
    address_number: Mapped[str] = mapped_column("endereco_numero", String(20), nullable=False)
    address_neighborhood: Mapped[str] = mapped_column("endereco_bairro", String(100), nullable=False)
    address_complement: Mapped[str | None] = mapped_column("endereco_complemento", String(150))

    notes: Mapped[str | None] = mapped_column("observacoes", Text)
    items_amount: Mapped[Decimal] = mapped_column("valor_itens", Numeric(10, 2), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column("valor_entrega", Numeric(10, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column("valor_total", Numeric(10, 2), nullable=False)
    cash_paid_amount: Mapped[Decimal | None] = mapped_column("valor_pago_dinheiro", Numeric(10, 2))
    change_amount: Mapped[Decimal | None] = mapped_column("valor_troco", Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    client: Mapped["Client"] = relationship(lazy="joined")


    __table_args__ = (
        CheckConstraint("valor_itens >= 0", name="ck_pedido_valor_itens"),
        CheckConstraint("valor_entrega >= 0", name="ck_pedido_valor_entrega"),
        CheckConstraint("valor_total >= 0", name="ck_pedido_valor_total"),
        CheckConstraint("valor_pago_dinheiro IS NULL OR valor_pago_dinheiro >= 0", name="ck_pedido_valor_pago_dinheiro"),
        CheckConstraint("valor_troco IS NULL OR valor_troco >= 0", name="ck_pedido_valor_troco"),
        Index("idx_pedido_data_hora", "data_hora"),
        Index("idx_pedido_cliente", "cliente_id"),
        Index("idx_pedido_status", "status_id"),
        Index("idx_pedido_forma_pagamento", "forma_pagamento_id"),
        Index("idx_pedido_restaurante_data_status", "restaurante_id", "data_hora", "status_id"),
    )


class OrderItem(Base):
    __tablename__ = "pedido_item"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column("pedido_id", ForeignKey("pedido.id", ondelete="CASCADE"), nullable=False)
    
    food_id: Mapped[uuid.UUID | None] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="SET NULL"), nullable=True)
    food_name: Mapped[str] = mapped_column("nome_alimento", String(120), nullable=False) 
    quantity: Mapped[int] = mapped_column("quantidade", Integer, nullable=False)
    
    base_price: Mapped[Decimal] = mapped_column("preco_base_unitario", Numeric(10, 2), nullable=False) 
    subtotal: Mapped[Decimal] = mapped_column("subtotal", Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column("observacoes", Text)
    order: Mapped["Order"] = relationship(back_populates="items")
    
    selected_options: Mapped[list["OrderItemOption"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_pedido_item_quantidade"),
        CheckConstraint("preco_base_unitario >= 0", name="ck_pedido_item_preco_unitario"),
        CheckConstraint("subtotal >= 0", name="ck_pedido_item_subtotal"),
    )


class OrderItemOption(Base):
    __tablename__ = "pedido_item_opcao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_item_id: Mapped[uuid.UUID] = mapped_column("pedido_item_id", ForeignKey("pedido_item.id", ondelete="CASCADE"), nullable=False)
    modifier_option_id: Mapped[uuid.UUID | None] = mapped_column("opcao_complemento_id", ForeignKey("opcao_complemento.id", ondelete="SET NULL"), nullable=True)

    option_name: Mapped[str] = mapped_column("nome_opcao", String(60), nullable=False)
    extra_price: Mapped[Decimal] = mapped_column("preco_adicional_unitario", Numeric(10, 2), default=0, nullable=False)
    quantity: Mapped[int] = mapped_column("quantidade", Integer, default=1, nullable=False) 

    order_item: Mapped["OrderItem"] = relationship(back_populates="selected_options")

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_pedido_item_opcao_quantidade"),
        CheckConstraint("preco_adicional_unitario >= 0", name="ck_pedido_item_opcao_preco"),
    )


class OrderStatusHistory(Base):
    __tablename__ = "historico_status_pedido"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column("pedido_id", ForeignKey("pedido.id", ondelete="CASCADE"), nullable=False)
    previous_status_id: Mapped[uuid.UUID | None] = mapped_column("status_anterior_id", ForeignKey("status_pedido.id"))
    new_status_id: Mapped[uuid.UUID] = mapped_column("status_novo_id", ForeignKey("status_pedido.id"), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column("usuario_id", ForeignKey("usuario_admin.id"))
    changed_at: Mapped[datetime] = mapped_column("alterado_em", DateTime, server_default=func.now())
    note: Mapped[str | None] = mapped_column("observacao", Text)

    order: Mapped["Order"] = relationship(back_populates="status_history")

    __table_args__ = (Index("idx_historico_status_pedido", "pedido_id", "alterado_em"),)


class AuditLog(Base):
    __tablename__ = "log_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column("usuario_id", ForeignKey("usuario_admin.id"))
    entity: Mapped[str] = mapped_column("entidade", String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column("entidade_id", String(50), nullable=False)
    action: Mapped[str] = mapped_column("acao", String(30), nullable=False)
    previous_data: Mapped[dict | None] = mapped_column("dados_anteriores", JSONB)
    new_data: Mapped[dict | None] = mapped_column("dados_novos", JSONB)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_log_auditoria_entidade", "entidade", "entidade_id"),
        Index("idx_log_auditoria_restaurante_periodo", "restaurante_id", "criado_em"),
    )

class DeliveryRule(Base):
    __tablename__ = "delivery_rules"
    id = Column(uuid.UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(uuid.UUID, ForeignKey("restaurants.id"), nullable=False)
    min_distance_km = Column(Numeric(5, 2), nullable=False) # Ex: 0.00
    max_distance_km = Column(Numeric(5, 2), nullable=False) # Ex: 3.00
    fee = Column(Numeric(10, 2), nullable=False)            # Ex: 5.00
    is_active = Column(Boolean, default=True)