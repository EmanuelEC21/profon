from pathlib import Path

import pytest

from profon.curriculo import Habilidade
from profon.sequencia import Conteudo, carregar_sequencia, validar_sequencia

HABS = {
    "EF67LP28": Habilidade("EF67LP28", "Ler crônicas...", (6, 7)),
    "EF01LP02": Habilidade("EF01LP02", "Escrever palavras.", (1,)),
}


def _c(id="6-cronica", ano=6, bimestre=1, habs=("EF67LP28",), aulas=6, minimas=4):
    return Conteudo(id, ano, bimestre, "Crônica", habs, aulas, minimas)


def test_carrega_em_ordem(tmp_path):
    arq = tmp_path / "6ano.yaml"
    arq.write_text(
        "ano: 6\nconteudos:\n"
        "  - {id: b, bimestre: 1, titulo: B, habilidades: [EF67LP28], aulas: 2, aulas_minimas: 1}\n"
        "  - {id: a, bimestre: 1, titulo: A, habilidades: [EF67LP28], aulas: 3, aulas_minimas: 3}\n",
        encoding="utf-8",
    )
    cs = carregar_sequencia(arq)
    assert [c.id for c in cs] == ["b", "a"]
    assert cs[0].ano == 6 and cs[0].habilidades == ("EF67LP28",)


def test_exemplo_do_repositorio_e_valido():
    from profon.curriculo import carregar_habilidades

    raiz = Path(__file__).parent.parent
    habs = carregar_habilidades(raiz / "data/curriculo/lp_habilidades.json")
    assert validar_sequencia(carregar_sequencia(raiz / "data/sequencias/6ano.yaml"), habs) == []


def test_valida_codigo_inexistente():
    erros = validar_sequencia([_c(habs=("EF67LP99",))], HABS)
    assert any("EF67LP99" in e for e in erros)


def test_valida_ano_errado():
    erros = validar_sequencia([_c(habs=("EF01LP02",))], HABS)
    assert any("EF01LP02" in e for e in erros)


@pytest.mark.parametrize(
    "conteudo",
    [_c(aulas=3, minimas=4), _c(aulas=0, minimas=0), _c(bimestre=5)],
)
def test_valida_numeros(conteudo):
    assert validar_sequencia([conteudo], HABS) != []


def test_valida_bimestres_fora_de_ordem():
    erros = validar_sequencia([_c(id="x", bimestre=2), _c(id="y", bimestre=1)], HABS)
    assert any("ordem" in e for e in erros)


def test_compressivel():
    assert _c(aulas=6, minimas=4).compressivel is True
    assert _c(aulas=3, minimas=3).compressivel is False
