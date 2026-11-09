import re
import unicodedata

SLUG_MIN = 3
SLUG_MAX = 60

_PADRAO = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SLUGS_RESERVADOS = frozenset(
    {
        "admin",
        "api",
        "app",
        "assets",
        "cadastro",
        "cardapio",
        "carrinho",
        "cliente",
        "clientes",
        "conta",
        "docs",
        "health",
        "login",
        "logout",
        "nexus",
        "nexusdelivery",
        "openapi",
        "pedido",
        "pedidos",
        "redoc",
        "registrar",
        "restaurante",
        "restaurantes",
        "revisao",
        "static",
        "suporte",
        "www",
        "ws",
    }
)


def normalizar_slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    com_hifens = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower())
    return com_hifens.strip("-")[:SLUG_MAX].strip("-")


def motivo_slug_invalido(slug: str) -> str | None:
    if len(slug) < SLUG_MIN or len(slug) > SLUG_MAX:
        return f"O link deve ter entre {SLUG_MIN} e {SLUG_MAX} caracteres."
    if not _PADRAO.match(slug):
        return "O link deve usar apenas letras minúsculas, números e hifens, sem hifen no começo, no fim ou repetido."
    if slug in SLUGS_RESERVADOS:
        return "Este link é reservado. Escolha outro."
    return None