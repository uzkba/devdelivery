import pytest
from fastapi import HTTPException

from app.core.slug import SLUG_MAX, motivo_slug_invalido, normalizar_slug
from app.services import slug_service


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("Marmitas da Vovó", "marmitas-da-vovo"),
        ("  Zé & Cia!!  ", "ze-cia"),
        ("Sabor   Caseiro", "sabor-caseiro"),
        ("---", ""),
        ("", ""),
    ],
)
def test_normalizar_slug(texto, esperado):
    assert normalizar_slug(texto) == esperado


def test_normalizar_slug_respeita_tamanho_maximo():
    slug = normalizar_slug("a" * 30 + " " + "b" * 50)
    assert len(slug) <= SLUG_MAX
    assert not slug.endswith("-")


@pytest.mark.parametrize("slug", ["sabor-caseiro", "abc", "a1b2", "restaurante-2"])
def test_slug_valido(slug):
    assert motivo_slug_invalido(slug) is None


@pytest.mark.parametrize(
    "slug",
    ["", "ab", "Sabor", "a--b", "-abc", "abc-", "a_b", "a b", "x" * 61, "admin"],
)
def test_slug_invalido(slug):
    assert motivo_slug_invalido(slug) is not None


def test_slug_disponivel(db, restaurante):
    assert slug_service.slug_disponivel(db, "outro-nome") is True
    assert slug_service.slug_disponivel(db, restaurante.slug) is False


def test_slug_disponivel_ignora_o_proprio_restaurante(db, restaurante):
    assert (
        slug_service.slug_disponivel(db, restaurante.slug, excluir_restaurante_id=restaurante.id)
        is True
    )


def test_gerar_slug_unico_sem_colisao(db):
    assert slug_service.gerar_slug_unico(db, "Sabor Caseiro") == "sabor-caseiro"


def test_gerar_slug_unico_com_colisao(db, restaurante):
    assert slug_service.gerar_slug_unico(db, "Marmitas da Vovó") == "marmitas-da-vovo-2"


def test_gerar_slug_unico_nome_curto_ou_reservado(db):
    assert slug_service.gerar_slug_unico(db, "ab") == "restaurante"
    assert slug_service.gerar_slug_unico(db, "Admin") == "admin-restaurante"


def test_garantir_slug_rejeita_formato_invalido(db):
    with pytest.raises(HTTPException) as erro:
        slug_service.garantir_slug_valido_e_livre(db, "Ab")
    assert erro.value.status_code == 422


def test_garantir_slug_rejeita_slug_ocupado(db, restaurante, outro_restaurante):
    with pytest.raises(HTTPException) as erro:
        slug_service.garantir_slug_valido_e_livre(
            db, restaurante.slug, excluir_restaurante_id=outro_restaurante.id
        )
    assert erro.value.status_code == 409


def test_garantir_slug_aceita_slug_livre_e_o_proprio(db, restaurante):
    assert slug_service.garantir_slug_valido_e_livre(db, "novo-link") == "novo-link"
    assert (
        slug_service.garantir_slug_valido_e_livre(
            db, restaurante.slug, excluir_restaurante_id=restaurante.id
        )
        == restaurante.slug
    )