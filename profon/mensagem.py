"""O que acontece em cada dia: as aulas do dia e o texto da mensagem da manhã."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from profon.agenda import AulaPlanejada, montar_agenda
from profon.config import Escola, Turma
from profon.estado import Estado
from profon.sequencia import Conteudo


@dataclass
class Contexto:
    escola: Escola
    sequencias: dict[int, list[Conteudo]]  # chave: ano
    estado: Estado


def agenda_da_turma(ctx: Contexto, turma: Turma) -> list[AulaPlanejada]:
    return montar_agenda(
        ctx.escola, turma, ctx.sequencias.get(turma.ano, []), ctx.estado.canceladas(turma.id), ctx.estado.ajustes()
    )


def turmas_do_dia(ctx: Contexto, dia: date) -> list[Turma]:
    return [t for t in ctx.escola.turmas if any(a.data == dia for a in agenda_da_turma(ctx, t))]


def aulas_do_dia(ctx: Contexto, dia: date) -> list[AulaPlanejada]:
    aulas = []
    for t in ctx.escola.turmas:
        aulas.extend(a for a in agenda_da_turma(ctx, t) if a.data == dia)
    return aulas
