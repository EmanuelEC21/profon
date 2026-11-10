from profon.acoes import aplicar_compressao, atrasos, confirmar_sem_aula, pergunta_sem_aula
from profon.mensagem import aulas_do_dia
from tests.conftest import SEG1, SEG2, TER1, B


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
    texto = aplicar_compressao(ctx, "6A", "6-b", SEG1)
    assert ctx.estado.ajustes("6A") == {"6-b": 1}
    assert "Pontuação" in texto and "2" in texto and "1" in texto


def test_compressao_inexistente(ctx):
    assert "não encontrado" in aplicar_compressao(ctx, "6A", "zzz", SEG1)


def test_compressao_nao_apaga_aulas_ja_dadas(ctx):
    from profon.mensagem import agenda_da_turma
    from profon.sequencia import Conteudo
    from tests.conftest import QUA2

    ctx.sequencias[6] = [Conteudo("6-x", 6, 1, "X", (), 3, 1)]
    aplicar_compressao(ctx, "6A", "6-x", QUA2)  # X 1 e 2 já foram dadas (SEG1, SEG2)
    assert ctx.estado.ajustes("6A") == {"6-x": 2}
    ag = agenda_da_turma(ctx, ctx.escola.turma("6A"))
    assert [(a.numero, a.total) for a in ag[:2]] == [(1, 2), (2, 2)]


def test_compressao_de_conteudo_concluido_recusa(ctx):
    from tests.conftest import QUA2

    assert "já" in aplicar_compressao(ctx, "6A", "6-a", QUA2)  # Crônica já terminou
    assert ctx.estado.ajustes("6A") == {}
