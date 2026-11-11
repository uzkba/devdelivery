import re
import unicodedata

_ESPACOS = re.compile(r"\s+")


def limpar_espacos(texto: str) -> str:
    return _ESPACOS.sub(" ", texto).strip()


def chave_comparacao(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return limpar_espacos(sem_acento).casefold()