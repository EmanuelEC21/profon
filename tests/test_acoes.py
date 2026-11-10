from datetime import date, time

import pytest

from profon.acoes import aplicar_compressao, atrasos, confirmar_sem_aula, pergunta_sem_aula
from profon.config import Bimestre, Escola, Turma
from profon.estado import Estado
from profon.mensagem import Contexto, aulas_do_dia
from profon.sequencia import Conteudo

SEG1, TER1, SEG2, QUA2 = date(2027, 3, 1), date(2027, 3, 2), date(2027, 3, 8), date(2027, 3, 10)
A = Conteudo("6-a", 6, 1, "Crônica", (), 2, 2)
B = Conteudo("6-b", 6, 1, "Pontuação", (), 2, 1)
C = Conteudo("9-c", 9, 1, "Argumentação", (), 3, 3)


@pytest.fixture
def ctx():
    escola = Escola(
        professor="P", escola="E", coordenador="C", disciplina="Língua Portuguesa",
        horario_envio=time(6), modelo_ia="m", telegram_chat_id=1,
        bimestres=(Bimestre(1, SEG1, date(2027, 3, 12)),),
        dias_sem_aula={date(2027, 3, 3): "feriado"},
        turmas=(Turma("6A", 6, "6º A", "manhã", (0, 2)), Turma("9A", 9, "9º A", "tarde", (0,))),
    )
    return Contexto(escola, {6: [A, B], 9: [C]}, Estado(":memory:"))


def test_aulas_do_dia(ctx):
    assert [(a.turma_id, a.conteudo.id) for a in aulas_do_dia(ctx, SEG1)] == [("6A", "6-a"), ("9A", "9-c")]
    assert aulas_do_dia(ctx, TER1) == []


def test_sem_aula_em_dia_livre(ctx):
    assert pergunta_sem_aula(ctx, TER1) is None


def test_pergunta_lista_turmas(ctx):
    p = pergunta_sem_aula(ctx, SEG1)
    assert "6º A e 9º A" in p and "Empurro" in p


def test_confirmar_cancela_e_informa_proximo(ctx):
    msgs = confirmar_sem_aula(ctx, SEG1, "ponto facultativo")
    assert ctx.estado.canceladas("6A") == {SEG1} and ctx.estado.canceladas("9A") == {SEG1}
    assert "6º A" in msgs[0] and "08/03" in msgs[0] and "Crônica" in msgs[0]


def test_confirmar_duas_vezes_nao_empurra_de_novo(ctx):
    confirmar_sem_aula(ctx, SEG1, "x")
    antes = aulas_do_dia(ctx, SEG2)
    confirmar_sem_aula(ctx, SEG1, "x")
    assert aulas_do_dia(ctx, SEG2) == antes


def test_confirmar_so_uma_turma(ctx):
    confirmar_sem_aula(ctx, SEG1, "não terminou", turmas=["6A"])
    assert ctx.estado.canceladas("6A") == {SEG1}
    assert ctx.estado.canceladas("9A") == set()


def test_alerta_de_atraso_aparece(ctx):
    confirmar_sem_aula(ctx, SEG1, "x")
    lista = atrasos(ctx, SEG1)
    assert [(a.turma_id, a.sugestoes) for a in lista] == [("6A", (B,)), ("9A", ())]


def test_aplicar_compressao(ctx):
    texto = aplicar_compressao(ctx, "6-b")
    assert ctx.estado.ajustes() == {"6-b": 1}
    assert "Pontuação" in texto and "2" in texto and "1" in texto


def test_compressao_inexistente(ctx):
    assert "não encontrado" in aplicar_compressao(ctx, "zzz")
