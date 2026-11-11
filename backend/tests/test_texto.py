import pytest

from app.core.texto import chave_comparacao, limpar_espacos


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("São José", "sao jose"),
        ("  CENTRO ", "centro"),
        ("Vila   Nova", "vila nova"),
        ("Água Branca", "agua branca"),
    ],
)
def test_chave_comparacao_ignora_acento_caixa_e_espacos(entrada, esperado):
    assert chave_comparacao(entrada) == esperado


def test_limpar_espacos_colapsa_e_apara():
    assert limpar_espacos("  Vila \t  Nova \n") == "Vila Nova"