from datetime import date

from profon.mensagem import compor_mensagens
from tests.conftest import SEG1, TER1


def test_sem_aulas_sem_mensagem(ctx):
    assert compor_mensagens(ctx, TER1) == []


def test_mensagem_com_questionario(ctx):
    ctx.estado.salvar_questionario("6ano", "6-a#1/2", ["O que é crônica?", "Cite um cronista."])
    msgs = compor_mensagens(ctx, SEG1)
    assert len(msgs) == 1
    texto = msgs[0]
    assert texto.startswith("☀️ Bom dia! Hoje: 6º A e 9º A")
    assert "📚 6º A — Crônica (aula 1 de 2)" in texto
    assert "1. O que é crônica?" in texto and "2. Cite um cronista." in texto


def test_mensagem_sem_questionario(ctx):
    assert "questionário indisponível hoje" in compor_mensagens(ctx, SEG1)[0]


def test_mensagem_longa_divide(ctx):
    ctx.estado.salvar_questionario("6ano", "6-a#1/2", ["x" * 3000])
    ctx.estado.salvar_questionario("9ano", "9-c#1/3", ["y" * 3000])
    msgs = compor_mensagens(ctx, SEG1)
    assert len(msgs) == 3  # cabeçalho + uma por turma
    assert all(len(m) <= 4096 for m in msgs)


def test_sequencia_concluida_na_mensagem(ctx):
    # 6A tem 4 aulas de conteúdo; depois das datas do fixture não há mais nada.
    ctx.sequencias["6ano"] = []
    assert "Sequência concluída" in compor_mensagens(ctx, SEG1)[0]


def test_questionario_acompanha_o_conteudo_remanejado(ctx):
    from profon.acoes import confirmar_sem_aula
    from profon.mensagem import pregerar
    from tests.conftest import SEG2
    from tests.test_questionario import MATERIAL_JSON as QUATRO, ClienteFalso

    pregerar(ctx, ClienteFalso(QUATRO), {}, SEG1, dias=1)  # Crônica aula 1 preparada para SEG1
    confirmar_sem_aula(ctx, SEG1, "feriado")  # Crônica aula 1 vai para SEG2
    texto = compor_mensagens(ctx, SEG2)[0]
    assert "Crônica (aula 1 de 2)" in texto
    assert "1. O que é reportagem?" in texto


def test_turma_usa_sua_propria_sequencia(ctx):
    from dataclasses import replace

    from profon.mensagem import aulas_do_dia
    from profon.sequencia import Conteudo

    t6 = ctx.escola.turma("6A")
    t6b = replace(t6, id="6P", nome="6º prod.", sequencia="6ano-producao")
    ctx.escola = replace(ctx.escola, turmas=ctx.escola.turmas + (t6b,))
    ctx.sequencias["6ano-producao"] = [Conteudo("6p-x", 6, 1, "Produção de crônica", (), 2, 2)]
    titulos = {a.turma_id: a.conteudo.titulo for a in aulas_do_dia(ctx, SEG1)}
    assert titulos["6A"] == "Crônica" and titulos["6P"] == "Produção de crônica"


def test_horario_aparece_e_ordena(ctx):
    from dataclasses import replace

    turmas = tuple(replace(t, horario={"6A": "10:00", "9A": "07:30"}[t.id]) for t in ctx.escola.turmas)
    ctx.escola = replace(ctx.escola, turmas=turmas)
    texto = compor_mensagens(ctx, SEG1)[0]
    assert texto.index("07:30 · 9º A") < texto.index("10:00 · 6º A")


def test_turmas_da_mesma_sequencia_compartilham_questionario(ctx):
    from dataclasses import replace

    from profon.mensagem import pregerar
    from tests.test_questionario import MATERIAL_JSON as QUATRO, ClienteFalso

    t6b = replace(ctx.escola.turma("6A"), id="6B", nome="6º B")
    ctx.escola = replace(ctx.escola, turmas=ctx.escola.turmas + (t6b,))
    cliente = ClienteFalso(QUATRO)
    pregerar(ctx, cliente, {}, SEG1, dias=1)
    assert len(cliente.chamadas) == 2  # 6A e 6B (mesma sequência) = 1 pedido; 9A = 1 pedido
    assert "1. O que é reportagem?" in compor_mensagens(ctx, SEG1)[0].split("6º B")[1]
