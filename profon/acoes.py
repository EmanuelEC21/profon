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
            ctx.escola, t, ctx.sequencias.get(t.ano, []), ctx.estado.canceladas(t.id), ctx.estado.ajustes(), dia
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
    ajustes = ctx.estado.ajustes()
    if atraso.sugestoes:
        texto += "\nSugestões para acelerar:"
        for c in atraso.sugestoes:
            texto += f"\n• {c.titulo}: de {ajustes.get(c.id, c.aulas)} para {c.aulas_minimas} aulas"
    else:
        texto += "\nNão há conteúdos marcados como aceleráveis. Vale revisar a sequência."
    return texto


def aplicar_compressao(ctx: Contexto, conteudo_id: str) -> str:
    for conteudos in ctx.sequencias.values():
        for c in conteudos:
            if c.id == conteudo_id:
                antes = ctx.estado.ajustes().get(c.id, c.aulas)
                ctx.estado.definir_ajuste(c.id, c.aulas_minimas)
                return f"✅ {c.titulo} acelerado: de {antes} para {c.aulas_minimas} aulas."
    return "Conteúdo não encontrado."
