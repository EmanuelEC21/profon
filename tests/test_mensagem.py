from datetime import date

from profon.mensagem import compor_mensagens
from tests.conftest import SEG1, TER1


def test_sem_aulas_sem_mensagem(ctx):
    assert compor_mensagens(ctx, TER1) == []


def test_mensagem_com_questionario(ctx):
    ctx.estado.salvar_questionario("6A", "6-a#1/2", ["O que é crônica?", "Cite um cronista."])
    msgs = compor_mensagens(ctx, SEG1)
    assert len(msgs) == 1
    texto = msgs[0]
    assert texto.startswith("☀️ Bom dia! Hoje: 6º A e 9º A")
    assert "📚 6º A — Crônica (aula 1 de 2)" in texto
    assert "1. O que é crônica?" in texto and "2. Cite um cronista." in texto


def test_mensagem_sem_questionario(ctx):
    assert "questionário indisponível hoje" in compor_mensagens(ctx, SEG1)[0]


def test_mensagem_longa_divide(ctx):
    ctx.estado.salvar_questionario("6A", "6-a#1/2", ["x" * 3000])
    ctx.estado.salvar_questionario("9A", "9-c#1/3", ["y" * 3000])
    msgs = compor_mensagens(ctx, SEG1)
    assert len(msgs) == 3  # cabeçalho + uma por turma
    assert all(len(m) <= 4096 for m in msgs)


def test_sequencia_concluida_na_mensagem(ctx):
    # 6A tem 4 aulas de conteúdo; depois das datas do fixture não há mais nada.
    ctx.sequencias[6] = []
    assert "Sequência concluída" in compor_mensagens(ctx, SEG1)[0]


def test_questionario_acompanha_o_conteudo_remanejado(ctx):
    from profon.acoes import confirmar_sem_aula
    from profon.mensagem import pregerar
    from tests.conftest import SEG2
    from tests.test_questionario import QUATRO, ClienteFalso

    pregerar(ctx, ClienteFalso(QUATRO), {}, SEG1, dias=1)  # Crônica aula 1 preparada para SEG1
    confirmar_sem_aula(ctx, SEG1, "feriado")  # Crônica aula 1 vai para SEG2
    texto = compor_mensagens(ctx, SEG2)[0]
    assert "Crônica (aula 1 de 2)" in texto
    assert "1. O que é crônica?" in texto
