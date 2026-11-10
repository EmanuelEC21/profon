from datetime import date, time

import pytest

from profon.agenda import datas_de_aula, montar_agenda, verificar_atraso
from profon.config import Bimestre, Escola, Turma
from profon.sequencia import Conteudo

SEG1, QUA1, SEG2, QUA2 = date(2027, 3, 1), date(2027, 3, 3), date(2027, 3, 8), date(2027, 3, 10)
A = Conteudo("A", 6, 1, "Crônica", (), 2, 2)
B = Conteudo("B", 6, 1, "Pontuação", (), 2, 1)
TURMA = Turma("6A", 6, "6º A", "manhã", (0, 2))


@pytest.fixture
def escola():
    return Escola(
        professor="P", escola="E", coordenador="C", disciplina="Língua Portuguesa",
        horario_envio=time(6), modelo_ia="m", telegram_chat_id=1,
        bimestres=(Bimestre(1, SEG1, date(2027, 3, 12)),),
        dias_sem_aula={QUA1: "feriado"},
        turmas=(TURMA,),
    )


def test_datas_excluem_feriado(escola):
    assert datas_de_aula(escola, TURMA) == [SEG1, SEG2, QUA2]


def test_agenda_distribui_em_ordem(escola):
    ag = montar_agenda(escola, TURMA, [A, B], set(), {})
    assert [(a.data, a.conteudo.id, a.numero, a.total) for a in ag] == [
        (SEG1, "A", 1, 2), (SEG2, "A", 2, 2), (QUA2, "B", 1, 2),
    ]


def test_cancelar_empurra_fila(escola):
    ag = montar_agenda(escola, TURMA, [A, B], {SEG1}, {})
    assert [(a.data, a.conteudo.id) for a in ag] == [(SEG2, "A"), (QUA2, "A")]


def test_sequencia_concluida(escola):
    ag = montar_agenda(escola, TURMA, [A], set(), {})
    assert ag[2].data == QUA2 and ag[2].conteudo is None


def test_ajuste_reduz_aulas(escola):
    ag = montar_agenda(escola, TURMA, [A, B], set(), {"B": 1})
    assert [a.total for a in ag if a.conteudo and a.conteudo.id == "B"] == [1]


def test_atraso_sugere_compressivel(escola):
    atraso = verificar_atraso(escola, TURMA, [A, B], {SEG1}, {}, hoje=SEG1)
    assert atraso is not None
    assert (atraso.aulas_necessarias, atraso.aulas_disponiveis) == (4, 2)
    assert atraso.sugestoes == (B,)


def test_ajuste_resolve_atraso(escola):
    assert verificar_atraso(escola, TURMA, [A, B], {SEG1}, {"A": 1, "B": 1}, hoje=SEG1) is None


def test_sem_atraso_fora_do_bimestre(escola):
    assert verificar_atraso(escola, TURMA, [A, B], {SEG1}, {}, hoje=date(2027, 5, 1)) is None


def test_aulas_dadas_nao_contam_como_necessarias(escola):
    # Em QUA2, A já foi dada (SEG1, SEG2) e só falta B (2 aulas) para 1 data: atraso de 1, sugere B.
    atraso = verificar_atraso(escola, TURMA, [A, B], set(), {}, hoje=QUA2)
    assert (atraso.aulas_necessarias, atraso.aulas_disponiveis) == (2, 1)
