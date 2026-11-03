"""NexusDelivery - modelos do banco (ETAPA 1: transicao).

Este arquivo e o modelo final (Modelagem v3.x) MAIS o legado que o codigo atual
ainda usa. Tudo que e legado esta marcado com "LEGADO (remover na Fase N)" e
fica agrupado no fim do arquivo, exceto as colunas legadas de Food.

Remocao do legado, por fase:
  Fase 2  : Food.category_id/base_price/is_available, ModifierGroup, ModifierOption
  Fase 3  : Menu, MenuItem
  Fase 10 : OrderItemOption (OrderItem.selected_options)

Convencao do projeto: atributo em ingles, tabela/coluna em portugues
(mapped_column("nome", ...)). IDs sao UUID.

Mapa do arquivo
    1. Restaurante e horario de atendimento
    2. Clientes e enderecos
    3. Equipe (usuario_admin) e convite
    4. Catalogo: categoria, alimento, marmita, combo, disponibilidade
    5. Pedido: pedido, item, historico, auditoria
    6. Financeiro: fechamento de caixa
    7. Entrega: configuracao, taxa por bairro, taxa por distancia

Convencao de data/hora: tabelas antigas usam DateTime sem fuso; tabelas
criadas a partir da Fase 1 usam DateTime(timezone=True). A unificacao fica
para uma migration futura.
"""
import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    event,
    func,
    inspect as sa_inspect,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    """created_at/updated_at com fuso (usado nas tabelas novas)."""

    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ===========================================================================
# 1. RESTAURANTE
# ===========================================================================
class Restaurant(Base):
    __tablename__ = "restaurante"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    trade_name: Mapped[str] = mapped_column("nome_fantasia", String(150), nullable=False)
    cnpj: Mapped[str | None] = mapped_column("cnpj", String(18), unique=True)
    phone: Mapped[str | None] = mapped_column("telefone", String(20))
    # Endereco exibido ao cliente (Ajustes > Dados e horarios)
    street: Mapped[str | None] = mapped_column("rua", String(150))
    number: Mapped[str | None] = mapped_column("numero", String(20))
    neighborhood: Mapped[str | None] = mapped_column("bairro", String(100))
    city: Mapped[str | None] = mapped_column("cidade", String(100))
    # Localizacao usada no calculo de taxa por distancia
    latitude: Mapped[Decimal | None] = mapped_column("latitude", Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column("longitude", Numeric(11, 8))
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    hours: Mapped[list["RestaurantHours"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
        order_by="[RestaurantHours.weekday, RestaurantHours.opens_at]",
    )


class RestaurantHours(Base):
    """Horario de atendimento. Uma linha por faixa de funcionamento
    (pode haver mais de uma no mesmo dia, ex.: almoco e jantar).
    Dia sem nenhuma linha = fechado. dia_semana: 0 = segunda ... 6 = domingo."""

    __tablename__ = "horario_atendimento"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column("dia_semana", Integer, nullable=False)
    opens_at: Mapped[time] = mapped_column("abre_as", Time, nullable=False)
    closes_at: Mapped[time] = mapped_column("fecha_as", Time, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="hours")

    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_horario_atendimento_dia"),
        UniqueConstraint(
            "restaurante_id", "dia_semana", "abre_as", name="uq_horario_atendimento_faixa"
        ),
    )


# ===========================================================================
# 2. CLIENTES
# ===========================================================================
class Client(Base):
    __tablename__ = "cliente"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    phone: Mapped[str] = mapped_column("telefone", String(20), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())
    hashed_password: Mapped[str] = mapped_column("senha_hash", String(255), nullable=False)

    addresses: Mapped[list["CustomerAddress"]] = relationship(back_populates="client")


class CustomerAddress(Base):
    __tablename__ = "endereco_cliente"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        "cliente_id", ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False
    )
    complement: Mapped[str | None] = mapped_column("complemento", String(50))
    street: Mapped[str] = mapped_column("rua", String(150), nullable=False)
    number: Mapped[str] = mapped_column("numero", String(5), nullable=False)
    neighborhood: Mapped[str] = mapped_column("bairro", String(50), nullable=False)
    reference_point: Mapped[str | None] = mapped_column("ponto_de_referencia", String(150))
    primary_address: Mapped[bool] = mapped_column(
        "endereco_principal", Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())
    latitude: Mapped[Decimal | None] = mapped_column("latitude", Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column("longitude", Numeric(11, 8))

    client: Mapped["Client"] = relationship(back_populates="addresses")

    __table_args__ = (
        Index(
            "uq_endereco_principal_por_cliente_v2",
            "cliente_id",
            unique=True,
            postgresql_where=text("endereco_principal = true"),  # noqa: E712
        ),
    )


# ===========================================================================
# 3. EQUIPE
# ===========================================================================
class AdminUser(Base):
    __tablename__ = "usuario_admin"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id"), nullable=False
    )
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


class UserInvite(Base):
    """Convite para atendente/caixa (RN-A02). Sem e-mail por enquanto: o admin
    copia o link de definicao de senha. So o hash do token e guardado; ao
    aceitar, cria-se o AdminUser com login = email e marca-se used_at."""

    __tablename__ = "convite_usuario"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id"), nullable=False
    )
    name: Mapped[str] = mapped_column("nome", String(150), nullable=False)
    email: Mapped[str] = mapped_column("email", String(150), nullable=False)
    role: Mapped[str] = mapped_column("papel", String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column("token_hash", String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column("expira_em", DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column("usado_em", DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(
        "criado_por", ForeignKey("usuario_admin.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("papel IN ('atendente','caixa')", name="ck_convite_usuario_papel"),
        Index("idx_convite_usuario_restaurante", "restaurante_id", "email"),
    )


# ===========================================================================
# 4. CATALOGO
# ===========================================================================
class FoodCategory(Base):
    """tipo = 'composicao': organiza alimentos usados para montar marmitas
    (carboidrato, proteina...). tipo = 'venda': organiza produtos vendidos
    avulsos (pratos, bebidas...). Sao dois tipos separados (RN-C01).

    LEGADO (remover na Fase 2): is_main_dish e a relacao foods."""

    __tablename__ = "categoria_alimento"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id"), nullable=False
    )
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False)
    display_order: Mapped[int] = mapped_column("ordem_exibicao", Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text)
    is_active: Mapped[bool] = mapped_column(
        "ativo", Boolean, default=True, server_default="true", nullable=False
    )
    type: Mapped[str] = mapped_column(
        "tipo", String(20), default="composicao", server_default="composicao", nullable=False
    )
    # LEGADO (Fase 2)
    is_main_dish: Mapped[bool] = mapped_column(
        "prato_principal", Boolean, default=False, server_default="false", nullable=False
    )

    # LEGADO (Fase 2): Food tem 3 FKs para esta tabela, entao a relacao precisa
    # dizer qual usar.
    foods: Mapped[list["Food"]] = relationship(
        back_populates="category", foreign_keys="Food.category_id"
    )

    __table_args__ = (
        UniqueConstraint("restaurante_id", "nome"),
        CheckConstraint("tipo IN ('composicao', 'venda')", name="ck_categoria_alimento_tipo"),
    )


class Food(Base):
    __tablename__ = "alimento"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id"), nullable=False
    )
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text)

    # --- modelo novo
    composition_category_id: Mapped[uuid.UUID | None] = mapped_column(
        "categoria_composicao_id", ForeignKey("categoria_alimento.id")
    )
    sale_category_id: Mapped[uuid.UUID | None] = mapped_column(
        "categoria_venda_id", ForeignKey("categoria_alimento.id")
    )
    is_sellable_alone: Mapped[bool] = mapped_column(
        "vendavel_avulso", Boolean, default=False, server_default="false", nullable=False
    )
    standalone_price: Mapped[Decimal | None] = mapped_column("preco_avulso", Numeric(10, 2))
    is_featured: Mapped[bool] = mapped_column(
        "destaque", Boolean, default=False, server_default="false", nullable=False
    )
    image_url: Mapped[str | None] = mapped_column("imagem_url", String(500))  # upload: Fase 5

    # --- LEGADO (Fase 2)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        "categoria_id", ForeignKey("categoria_alimento.id"), nullable=True
    )
    base_price: Mapped[Decimal] = mapped_column("preco_base", Numeric(10, 2), default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True, nullable=False)

    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    composition_category: Mapped["FoodCategory | None"] = relationship(
        foreign_keys=[composition_category_id]
    )
    sale_category: Mapped["FoodCategory | None"] = relationship(foreign_keys=[sale_category_id])
    # LEGADO (Fase 2)
    category: Mapped["FoodCategory | None"] = relationship(
        back_populates="foods", foreign_keys=[category_id]
    )
    modifier_groups: Mapped[list["ModifierGroup"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("preco_base >= 0", name="ck_alimento_preco_base_positivo"),  # LEGADO
        CheckConstraint(
            "NOT vendavel_avulso OR (preco_avulso IS NOT NULL AND categoria_venda_id IS NOT NULL)",
            name="ck_alimento_avulso_completo",
        ),
        CheckConstraint("preco_avulso IS NULL OR preco_avulso >= 0", name="ck_alimento_preco_avulso"),
        CheckConstraint(
            "categoria_id IS NOT NULL OR categoria_composicao_id IS NOT NULL OR categoria_venda_id IS NOT NULL",
            name="ck_alimento_tem_categoria",
        ),
        Index("idx_alimento_categoria_composicao", "categoria_composicao_id"),
        Index("idx_alimento_categoria_venda", "categoria_venda_id"),
    )


# ---------------------------------------------------------------------------
# Marmita
# ---------------------------------------------------------------------------
class MealBoxKind(str, enum.Enum):
    """Tipo da marmita. O valor e o codigo tecnico guardado no banco e
    devolvido pela API; o rotulo exibido ao cliente ("Pronta" etc.) e
    decisao de frontend."""

    CUSTOMIZABLE = "PERSONALIZAVEL"  # cliente monta por categorias
    READY = "PRONTA"  # composicao fixa definida pelo restaurante


class MealBox(TimestampMixin, Base):
    __tablename__ = "marmita"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", String(500))
    kind: Mapped[MealBoxKind] = mapped_column(
        "tipo",
        Enum(MealBoxKind, name="tipo_marmita", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    size: Mapped[str | None] = mapped_column("tamanho", String(40))  # opcional
    price: Mapped[Decimal] = mapped_column("preco", Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, server_default="true", nullable=False)
    is_featured: Mapped[bool] = mapped_column("destaque", Boolean, default=False, server_default="false", nullable=False)
    image_url: Mapped[str | None] = mapped_column("imagem_url", String(500))  # upload: Fase 5

    # Informacao nutricional opcional (cada restaurante decide se informa)
    calories_kcal: Mapped[int | None] = mapped_column("calorias_kcal", Integer)
    protein_g: Mapped[Decimal | None] = mapped_column("proteina_g", Numeric(6, 1))
    carbs_g: Mapped[Decimal | None] = mapped_column("carboidrato_g", Numeric(6, 1))
    fat_g: Mapped[Decimal | None] = mapped_column("gordura_g", Numeric(6, 1))

    categories: Mapped[list["MealBoxCategory"]] = relationship(
        back_populates="meal_box",
        cascade="all, delete-orphan",
        order_by="MealBoxCategory.position",
        lazy="selectin",
    )
    composition: Mapped[list["MealBoxComposition"]] = relationship(
        back_populates="meal_box",
        cascade="all, delete-orphan",
        order_by="MealBoxComposition.position",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_marmita_preco"),
        CheckConstraint("calorias_kcal IS NULL OR calorias_kcal >= 0", name="ck_marmita_calorias"),
        CheckConstraint(
            "(proteina_g IS NULL OR proteina_g >= 0) AND "
            "(carboidrato_g IS NULL OR carboidrato_g >= 0) AND "
            "(gordura_g IS NULL OR gordura_g >= 0)",
            name="ck_marmita_macros",
        ),
        Index("idx_marmita_restaurante_ativo", "restaurante_id", "ativo"),
    )


class MealBoxCategory(Base):
    """Marmita PERSONALIZAVEL: quantas escolhas o cliente faz em cada
    categoria de composicao (pode ser 0, nunca negativa)."""

    __tablename__ = "marmita_categoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    meal_box_id: Mapped[uuid.UUID] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="CASCADE"), nullable=False)
    food_category_id: Mapped[uuid.UUID] = mapped_column(
        "categoria_alimento_id", ForeignKey("categoria_alimento.id", ondelete="RESTRICT"), nullable=False
    )
    required_quantity: Mapped[int] = mapped_column("quantidade_exigida", Integer, nullable=False)
    position: Mapped[int] = mapped_column("posicao", Integer, default=0, nullable=False)  # ordem de cadastro

    meal_box: Mapped["MealBox"] = relationship(back_populates="categories")
    food_category: Mapped["FoodCategory"] = relationship(lazy="joined")

    @property
    def food_category_name(self) -> str:
        return self.food_category.name

    __table_args__ = (
        UniqueConstraint("marmita_id", "categoria_alimento_id", name="uq_marmita_categoria"),
        CheckConstraint("quantidade_exigida >= 0", name="ck_marmita_categoria_quantidade"),
        Index("idx_marmita_categoria_categoria", "categoria_alimento_id"),
    )


class MealBoxComposition(Base):
    """Marmita PRONTA: composicao fixa (alimento + quantidade fixa)."""

    __tablename__ = "marmita_composicao"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    meal_box_id: Mapped[uuid.UUID] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False)
    fixed_quantity: Mapped[int] = mapped_column("quantidade_fixa", Integer, nullable=False)
    position: Mapped[int] = mapped_column("posicao", Integer, default=0, nullable=False)

    meal_box: Mapped["MealBox"] = relationship(back_populates="composition")
    food: Mapped["Food"] = relationship(lazy="joined")

    @property
    def food_name(self) -> str:
        return self.food.name

    __table_args__ = (
        UniqueConstraint("marmita_id", "alimento_id", name="uq_marmita_composicao"),
        CheckConstraint("quantidade_fixa >= 1", name="ck_marmita_composicao_quantidade"),
        Index("idx_marmita_composicao_alimento", "alimento_id"),
    )


# ---------------------------------------------------------------------------
# Combo (marmitas + quaisquer alimentos; sem combo dentro de combo, o que e
# garantido pela propria estrutura: nao existe tabela combo -> combo)
# ---------------------------------------------------------------------------
class Combo(TimestampMixin, Base):
    __tablename__ = "combo"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", String(500))
    price: Mapped[Decimal] = mapped_column("preco", Numeric(10, 2), nullable=False)  # preco proprio
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, server_default="true", nullable=False)
    is_featured: Mapped[bool] = mapped_column("destaque", Boolean, default=False, server_default="false", nullable=False)
    image_url: Mapped[str | None] = mapped_column("imagem_url", String(500))

    meal_box_items: Mapped[list["ComboMealBoxItem"]] = relationship(
        back_populates="combo",
        cascade="all, delete-orphan",
        order_by="ComboMealBoxItem.position",
        lazy="selectin",
    )
    food_items: Mapped[list["ComboFoodItem"]] = relationship(
        back_populates="combo",
        cascade="all, delete-orphan",
        order_by="ComboFoodItem.position",
        lazy="selectin",
    )

    @property
    def has_customizable_meal_box(self) -> bool:
        """True se o combo tem marmita personalizavel (cliente precisa
        configurar cada unidade) - usado no aviso de complexidade do admin."""
        return any(i.meal_box.kind == MealBoxKind.CUSTOMIZABLE for i in self.meal_box_items)

    @property
    def has_inactive_items(self) -> bool:
        """True se algum componente foi desativado depois de entrar no combo.
        Na consulta do cardapio (Fase 3) um combo assim fica indisponivel."""
        return any(not i.meal_box.is_active for i in self.meal_box_items) or any(
            not i.food.is_active for i in self.food_items
        )

    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_combo_preco"),
        Index("idx_combo_restaurante_ativo", "restaurante_id", "ativo"),
    )


class ComboMealBoxItem(Base):
    __tablename__ = "combo_item_marmita"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    combo_id: Mapped[uuid.UUID] = mapped_column("combo_id", ForeignKey("combo.id", ondelete="CASCADE"), nullable=False)
    meal_box_id: Mapped[uuid.UUID] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column("quantidade", Integer, nullable=False)
    position: Mapped[int] = mapped_column("posicao", Integer, default=0, nullable=False)

    combo: Mapped["Combo"] = relationship(back_populates="meal_box_items")
    meal_box: Mapped["MealBox"] = relationship(lazy="joined")

    @property
    def meal_box_name(self) -> str:
        return self.meal_box.name

    @property
    def meal_box_kind(self) -> MealBoxKind:
        return self.meal_box.kind

    __table_args__ = (
        UniqueConstraint("combo_id", "marmita_id", name="uq_combo_item_marmita"),
        CheckConstraint("quantidade >= 1", name="ck_combo_item_marmita_quantidade"),
        Index("idx_combo_item_marmita_marmita", "marmita_id"),
    )


class ComboFoodItem(Base):
    """Qualquer alimento (prato, bebida, acompanhamento, sobremesa): o
    criterio de composicao do combo e do restaurante, nao do sistema."""

    __tablename__ = "combo_item_alimento"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    combo_id: Mapped[uuid.UUID] = mapped_column("combo_id", ForeignKey("combo.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column("quantidade", Integer, nullable=False)
    position: Mapped[int] = mapped_column("posicao", Integer, default=0, nullable=False)

    combo: Mapped["Combo"] = relationship(back_populates="food_items")
    food: Mapped["Food"] = relationship(lazy="joined")

    @property
    def food_name(self) -> str:
        return self.food.name

    __table_args__ = (
        UniqueConstraint("combo_id", "alimento_id", name="uq_combo_item_alimento"),
        CheckConstraint("quantidade >= 1", name="ck_combo_item_alimento_quantidade"),
        Index("idx_combo_item_alimento_alimento", "alimento_id"),
    )


# ---------------------------------------------------------------------------
# Disponibilidade (distinta de ativo/inativo)
#
# Cada regra/excecao pertence a EXATAMENTE UM alvo: marmita, combo ou alimento
# (tres FKs opcionais + CHECK, em vez de FK polimorfica sem integridade).
#   - Sem regra para o alvo      => disponivel todos os dias.
#   - Regra TODOS_OS_DIAS        => idem (preserva a escolha do admin).
#   - Regra PERSONALIZADO        => disponivel so nos dias de *_regra_dia.
#   - Excecao (data, disponivel) => sobrepoe a regra semanal naquela data.
# dia_semana: 0 = segunda ... 6 = domingo (mesmo valor de date.weekday()).
# ---------------------------------------------------------------------------
class AvailabilityRule(TimestampMixin, Base):
    __tablename__ = "disponibilidade_regra"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    meal_box_id: Mapped[uuid.UUID | None] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="CASCADE"))
    combo_id: Mapped[uuid.UUID | None] = mapped_column("combo_id", ForeignKey("combo.id", ondelete="CASCADE"))
    food_id: Mapped[uuid.UUID | None] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column("modo", String(20), default="TODOS_OS_DIAS", server_default="TODOS_OS_DIAS", nullable=False)

    days: Mapped[list["AvailabilityRuleDay"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="AvailabilityRuleDay.weekday",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("num_nonnulls(marmita_id, combo_id, alimento_id) = 1", name="ck_disponibilidade_regra_alvo"),
        CheckConstraint("modo IN ('TODOS_OS_DIAS', 'PERSONALIZADO')", name="ck_disponibilidade_regra_modo"),
        UniqueConstraint("marmita_id", name="uq_disponibilidade_regra_marmita"),
        UniqueConstraint("combo_id", name="uq_disponibilidade_regra_combo"),
        UniqueConstraint("alimento_id", name="uq_disponibilidade_regra_alimento"),
    )


class AvailabilityRuleDay(Base):
    __tablename__ = "disponibilidade_regra_dia"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column("regra_id", ForeignKey("disponibilidade_regra.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column("dia_semana", Integer, nullable=False)

    rule: Mapped["AvailabilityRule"] = relationship(back_populates="days")

    __table_args__ = (
        UniqueConstraint("regra_id", "dia_semana", name="uq_disponibilidade_regra_dia"),
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_disponibilidade_regra_dia_semana"),
    )


class AvailabilityException(Base):
    __tablename__ = "excecao_disponibilidade"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    meal_box_id: Mapped[uuid.UUID | None] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="CASCADE"))
    combo_id: Mapped[uuid.UUID | None] = mapped_column("combo_id", ForeignKey("combo.id", ondelete="CASCADE"))
    food_id: Mapped[uuid.UUID | None] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="CASCADE"))
    exception_date: Mapped[date] = mapped_column("data", Date, nullable=False)
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("num_nonnulls(marmita_id, combo_id, alimento_id) = 1", name="ck_excecao_disponibilidade_alvo"),
        # um registro por alvo e data (NULLs nao colidem entre si no PostgreSQL)
        UniqueConstraint("marmita_id", "data", name="uq_excecao_disponibilidade_marmita"),
        UniqueConstraint("combo_id", "data", name="uq_excecao_disponibilidade_combo"),
        UniqueConstraint("alimento_id", "data", name="uq_excecao_disponibilidade_alimento"),
    )


# ===========================================================================
# 5. PEDIDO
# ===========================================================================
class PaymentMethod(Base):
    __tablename__ = "forma_pagamento"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column("codigo", String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column("nome", String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)


class OrderStatus(Base):
    __tablename__ = "status_pedido"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column("codigo", String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column("nome", String(50), nullable=False)
    order: Mapped[int] = mapped_column("ordem", Integer, nullable=False)
    is_paid: Mapped[bool] = mapped_column("pago", Boolean, default=False, nullable=False)
    is_final: Mapped[bool] = mapped_column("is_final", Boolean, default=False, nullable=False)


class Order(Base):
    __tablename__ = "pedido"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    order_number: Mapped[int] = mapped_column("numero_pedido", Integer, Identity(), unique=True, nullable=False)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column("cliente_id", ForeignKey("cliente.id"), nullable=False)
    status_id: Mapped[uuid.UUID] = mapped_column("status_id", ForeignKey("status_pedido.id"), nullable=False)
    # unica coluna mutavel apos a criacao (RN-P11), ate o status final; trocas vao para log_auditoria
    payment_method_id: Mapped[uuid.UUID] = mapped_column("forma_pagamento_id", ForeignKey("forma_pagamento.id"), nullable=False)
    order_datetime: Mapped[datetime] = mapped_column("data_hora", DateTime, server_default=func.now())

    # Snapshot do endereco no momento do pedido (nao e FK)
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
    status: Mapped["OrderStatus"] = relationship(lazy="joined")
    payment_method: Mapped["PaymentMethod"] = relationship(lazy="joined")

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
    """Item do pedido. Aponta para UM item do catalogo (alimento, marmita ou
    combo) e guarda um snapshot: nome, preco e configuracao no momento da
    compra, sem alteracao retroativa. Configuracao de marmita personalizavel e
    componentes do combo ficam em snapshot_json (nao ha tabela de opcoes).

    As FKs usam SET NULL (alimento, legado) e RESTRICT (marmita, combo): item
    de catalogo ja vendido deve ser desativado, nao excluido."""

    __tablename__ = "pedido_item"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column("pedido_id", ForeignKey("pedido.id", ondelete="CASCADE"), nullable=False)

    food_id: Mapped[uuid.UUID | None] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="SET NULL"), nullable=True)
    meal_box_id: Mapped[uuid.UUID | None] = mapped_column("marmita_id", ForeignKey("marmita.id", ondelete="RESTRICT"), nullable=True)
    combo_id: Mapped[uuid.UUID | None] = mapped_column("combo_id", ForeignKey("combo.id", ondelete="RESTRICT"), nullable=True)

    # nome comercial do item vendido (alimento, marmita ou combo)
    food_name: Mapped[str] = mapped_column("nome_alimento", String(120), nullable=False)
    quantity: Mapped[int] = mapped_column("quantidade", Integer, nullable=False)
    base_price: Mapped[Decimal] = mapped_column("preco_base_unitario", Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column("subtotal", Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column("observacoes", Text)
    snapshot: Mapped[dict | None] = mapped_column("snapshot_json", JSONB)

    order: Mapped["Order"] = relationship(back_populates="items")
    # LEGADO (Fase 10): substituido por snapshot_json
    selected_options: Mapped[list["OrderItemOption"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_pedido_item_quantidade"),
        CheckConstraint("preco_base_unitario >= 0", name="ck_pedido_item_preco_unitario"),
        CheckConstraint("subtotal >= 0", name="ck_pedido_item_subtotal"),
        CheckConstraint(
            "num_nonnulls(alimento_id, marmita_id, combo_id) <= 1",
            name="ck_pedido_item_um_item",
        ),
        # "Mais pedidos" = contagem por item num periodo
        Index("idx_pedido_item_alimento", "alimento_id"),
        Index("idx_pedido_item_marmita", "marmita_id"),
        Index("idx_pedido_item_combo", "combo_id"),
    )


class OrderStatusHistory(Base):
    __tablename__ = "historico_status_pedido"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
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


# ===========================================================================
# 6. FINANCEIRO (somente fechamento de caixa: nao ha gastos/saldo no admin)
# ===========================================================================
class CashClosing(Base):
    __tablename__ = "fechamento_caixa"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
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


# ===========================================================================
# 7. ENTREGA (cada restaurante escolhe a propria forma de cobranca)
# ===========================================================================
class DeliveryChargeMode(str, enum.Enum):
    GRATIS = "GRATIS"
    FIXO = "FIXO"
    BAIRRO = "BAIRRO"
    DISTANCIA = "DISTANCIA"


class RestaurantDeliverySettings(Base):
    __tablename__ = "configuracao_entrega"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", UUID(as_uuid=True), ForeignKey("restaurante.id"), unique=True, nullable=False
    )
    delivery_enabled: Mapped[bool] = mapped_column("entrega_ativa", Boolean, default=True, nullable=False)
    pickup_enabled: Mapped[bool] = mapped_column("retirada_ativa", Boolean, default=True, nullable=False)
    min_order_value: Mapped[Decimal | None] = mapped_column("valor_minimo", Numeric(10, 2))
    delivery_time_minutes: Mapped[int | None] = mapped_column("tempo_entrega_min", Integer)
    pickup_time_minutes: Mapped[int | None] = mapped_column("tempo_retirada_min", Integer)
    charge_mode: Mapped[DeliveryChargeMode] = mapped_column(
        "modo_cobranca", Enum(DeliveryChargeMode, name="modo_cobranca_entrega"), nullable=False
    )
    fixed_fee: Mapped[Decimal | None] = mapped_column("taxa_fixa", Numeric(10, 2))  # so com charge_mode == FIXO
    created_at: Mapped[datetime | None] = mapped_column("criado_em", DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        "atualizado_em", DateTime, server_default=func.now(), onupdate=func.now()
    )


class DeliveryRuleNeighborhood(Base):
    """Taxa por bairro (charge_mode == BAIRRO)."""

    __tablename__ = "regra_entrega_bairro"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", UUID(as_uuid=True), ForeignKey("restaurante.id"), nullable=False, index=True
    )
    neighborhood: Mapped[str] = mapped_column("bairro", String(120), nullable=False)
    fee: Mapped[Decimal] = mapped_column("taxa", Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)


class DeliveryRule(Base):
    """Faixa de distancia em km (charge_mode == DISTANCIA)."""

    __tablename__ = "regra_entrega_distancia"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        "restaurante_id", ForeignKey("restaurante.id"), nullable=False, index=True
    )
    min_distance_km: Mapped[Decimal] = mapped_column("distancia_min_km", Numeric(5, 2), nullable=False)
    max_distance_km: Mapped[Decimal] = mapped_column("distancia_max_km", Numeric(5, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column("taxa", Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True, nullable=False)


# ===========================================================================
# LEGADO - ainda usado pelo codigo atual. NAO criar codigo novo em cima disto.
# ===========================================================================


class ModifierGroup(Base):
    """LEGADO (remover na Fase 2)."""

    __tablename__ = "grupo_complemento"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    food_id: Mapped[uuid.UUID] = mapped_column("alimento_id", ForeignKey("alimento.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False)
    min_choices: Mapped[int] = mapped_column("escolhas_minimas", Integer, default=0, nullable=False)
    max_choices: Mapped[int] = mapped_column("escolhas_maximas", Integer, nullable=False)
    display_order: Mapped[int] = mapped_column("ordem_exibicao", Integer, default=0)
    is_active: Mapped[bool] = mapped_column("ativo", Boolean, default=True)

    food: Mapped["Food"] = relationship(back_populates="modifier_groups")
    options: Mapped[list["ModifierOption"]] = relationship(back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("escolhas_maximas >= escolhas_minimas", name="ck_grupo_complemento_limites"),)


class ModifierOption(Base):
    """LEGADO (remover na Fase 2)."""

    __tablename__ = "opcao_complemento"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column("grupo_id", ForeignKey("grupo_complemento.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(60), nullable=False)
    extra_price: Mapped[Decimal] = mapped_column("preco_adicional", Numeric(10, 2), default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column("disponivel", Boolean, default=True)

    group: Mapped["ModifierGroup"] = relationship(back_populates="options")


class Menu(Base):
    """LEGADO (remover na Fase 3)."""

    __tablename__ = "cardapio"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column("restaurante_id", ForeignKey("restaurante.id"), nullable=False)
    date: Mapped[date] = mapped_column("data", Date, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column("criado_por", ForeignKey("usuario_admin.id"))
    created_at: Mapped[datetime] = mapped_column("criado_em", DateTime, server_default=func.now())

    items: Mapped[list["MenuItem"]] = relationship(back_populates="menu", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("restaurante_id", "data"),)


class MenuItem(Base):
    """LEGADO (remover na Fase 3)."""

    __tablename__ = "cardapio_item"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
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


class OrderItemOption(Base):
    """LEGADO (remover na Fase 10)."""

    __tablename__ = "pedido_item_opcao"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
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


# ---------------------------------------------------------------------------
# Compatibilidade de transicao (remover na Fase 2, junto com Food.category_id)
#
# O cadastro atual de alimento so conhece category_id. Alimento legado e sempre
# de composicao, entao category_id e copiado para composition_category_id.
# Alimentos "do modelo novo" (com categoria de venda definida) nao sao tocados.
# ---------------------------------------------------------------------------
@event.listens_for(Food, "before_insert")
def _food_mirror_composition_on_insert(mapper, connection, target):
    if target.composition_category_id is None and target.sale_category_id is None:
        target.composition_category_id = target.category_id


@event.listens_for(Food, "before_update")
def _food_mirror_composition_on_update(mapper, connection, target):
    if target.sale_category_id is None and sa_inspect(target).attrs.category_id.history.has_changes():
        target.composition_category_id = target.category_id