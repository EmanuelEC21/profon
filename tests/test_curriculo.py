import pytest

from profon.curriculo import anos_do_codigo, extrair_habilidades


@pytest.mark.parametrize(
    "codigo,anos",
    [
        ("EF03LP01", (3,)),
        ("EF12LP01", (1, 2)),
        ("EF15LP01", (1, 2, 3, 4, 5)),
        ("EF35LP01", (3, 4, 5)),
        ("EF67LP28", (6, 7)),
        ("EF69LP01", (6, 7, 8, 9)),
        ("EF89LP01", (8, 9)),
    ],
)
def test_anos_do_codigo(codigo, anos):
    assert anos_do_codigo(codigo) == anos


def test_codigo_desconhecido_falha():
    with pytest.raises(ValueError):
        anos_do_codigo("EF99LP01")


def test_extrai_e_deduplica():
    texto = (
        "(EF15LP01) Identificar a função\nsocial de textos.\n"
        "(EF15LP01) Identificar a função social de textos.\n"
        "(EF01LP02) Escrever palavras."
    )
    habs = extrair_habilidades(texto)
    assert [h.codigo for h in habs] == ["EF15LP01", "EF01LP02"]
    assert habs[0].texto == "Identificar a função social de textos."
    assert habs[0].anos == (1, 2, 3, 4, 5)
    assert habs[1].texto == "Escrever palavras."
