"""Regras do bot, sem Telegram: "não teve aula", remanejamento, atraso e compressão."""

from __future__ import annotations

from datetime import date

from profon.agenda import Atraso, verificar_atraso
from profon.mensagem import Contexto, agenda_da_turma, turmas_do_dia


def juntar_nomes(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def pergunta_sem_aula(ctx: Contexto, dia: date) -> str | None:
    turmas = turmas_do_dia(ctx, dia)
    if not turmas:
        return None
    nomes = juntar_nomes([t.nome for t in turmas])
    return f"Hoje não teve aula com {nomes}? Empurro o conteúdo de cada turma para a próxima aula dela?"


def confirmar_sem_aula(ctx: Contexto, dia: date, motivo: str, turmas: list[str] | None = None) -> list[str]:
    alvo = [t for t in turmas_do_dia(ctx, dia) if turmas is None or t.id in turmas]
    if not alvo:
        return ["Você não tem aula registrada hoje."]
    linhas = ["✅ Conteúdo remanejado. Próxima aula de cada turma:"]
    for t in alvo:
        ctx.estado.cancelar(t.id, dia, motivo)
        proxima = next((a for a in agenda_da_turma(ctx, t) if a.data > dia), None)
        if proxima is None:
            linhas.append(f"• {t.nome}: não há mais aulas no calendário.")
        elif proxima.conteudo is None:
            linhas.append(f"• {t.nome} — {proxima.data:%d/%m}: sequência concluída (aula livre/revisão).")
        else:
            linhas.append(
                f"• {t.nome} — {proxima.data:%d/%m}: {proxima.conteudo.titulo} "
                f"(aula {proxima.numero} de {proxima.total})"
            )
    return ["\n".join(linhas)]


def atrasos(ctx: Contexto, dia: date) -> list[Atraso]:
    lista = []
    for t in ctx.escola.turmas:
        a = verificar_atraso(
            ctx.escola, t, ctx.sequencias.get(t.sequencia, []), ctx.estado.canceladas(t.id), ctx.estado.ajustes(t.id), dia
        )
        if a is not None:
            lista.append(a)
    return lista


def texto_atraso(ctx: Contexto, atraso: Atraso) -> str:
    nome = ctx.escola.turma(atraso.turma_id).nome
    texto = (
        f"⚠️ {nome} está atrasando no {atraso.bimestre}º bimestre: faltam {atraso.aulas_necessarias} aulas "
        f"de conteúdo e restam {atraso.aulas_disponiveis} aulas até o fim do bimestre."
    )
    ajustes = ctx.estado.ajustes(atraso.turma_id)
    if atraso.sugestoes:
        texto += "\nSugestões para acelerar:"
        for c in atraso.sugestoes:
            texto += f"\n• {c.titulo}: de {ajustes.get(c.id, c.aulas)} para {c.aulas_minimas} aulas"
    else:
        texto += "\nNão há conteúdos marcados como aceleráveis. Vale revisar a sequência."
    return texto


def aplicar_compressao(ctx: Contexto, turma_id: str, conteudo_id: str, hoje: date) -> str:
    """Reduz as aulas de um conteúdo numa turma, sem nunca ficar abaixo das aulas já dadas.

    Como a agenda é recalculada desde o início do ano, reduzir abaixo do que já foi dado
    reescreveria o passado e faria a turma pular aulas.
    """
    turma = ctx.escola.turma(turma_id)
    c = next((x for x in ctx.sequencias.get(turma.sequencia, []) if x.id == conteudo_id), None)
    if c is None:
        return "Conteúdo não encontrado."
    atual = ctx.estado.ajustes(turma_id).get(c.id, c.aulas)
    dadas = sum(1 for a in agenda_da_turma(ctx, turma) if a.data < hoje and a.conteudo and a.conteudo.id == c.id)
    if dadas >= atual:
        return f"{c.titulo} já foi dado por completo no {turma.nome}; não há o que acelerar."
    novo = max(c.aulas_minimas, dadas)
    if novo >= atual:
        return f"{c.titulo} no {turma.nome} já está no mínimo de aulas ({atual})."
    ctx.estado.definir_ajuste(turma_id, c.id, novo)
    return f"✅ {c.titulo} acelerado no {turma.nome}: de {atual} para {novo} aulas."
