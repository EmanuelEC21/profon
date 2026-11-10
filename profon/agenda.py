"""Agenda derivada de cada turma e detecção de atraso.

A agenda nunca é guardada. Ela sempre sai de: datas de aula (bimestres, dias da semana e dias sem aula),
aulas canceladas e sequência de conteúdos (com os ajustes de compressão). Os conteúdos ocupam,
em ordem, as datas que sobram. Por isso, cancelar uma aula empurra a fila automaticamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from profon.config import Escola, Turma
from profon.sequencia import Conteudo


@dataclass(frozen=True)
class AulaPlanejada:
    turma_id: str
    data: date
    conteudo: Conteudo | None  # None = sequência concluída (aula livre/revisão)
    numero: int
    total: int


@dataclass(frozen=True)
class Atraso:
    turma_id: str
    bimestre: int
    aulas_necessarias: int
    aulas_disponiveis: int
    sugestoes: tuple[Conteudo, ...]


def datas_de_aula(escola: Escola, turma: Turma) -> list[date]:
    datas: list[date] = []
    for b in escola.bimestres:
        d = b.inicio
        while d <= b.fim:
            if d.weekday() in turma.dias_semana and d not in escola.dias_sem_aula:
                datas.append(d)
            d += timedelta(days=1)
    return datas


def montar_agenda(
    escola: Escola,
    turma: Turma,
    conteudos: list[Conteudo],
    canceladas: set[date],
    ajustes: dict[str, int],
) -> list[AulaPlanejada]:
    datas = [d for d in datas_de_aula(escola, turma) if d not in canceladas]
    fila = [(c, i + 1, ajustes.get(c.id, c.aulas)) for c in conteudos for i in range(ajustes.get(c.id, c.aulas))]
    agenda = []
    for k, d in enumerate(datas):
        if k < len(fila):
            c, n, total = fila[k]
            agenda.append(AulaPlanejada(turma.id, d, c, n, total))
        else:
            agenda.append(AulaPlanejada(turma.id, d, None, 0, 0))
    return agenda


def verificar_atraso(
    escola: Escola,
    turma: Turma,
    conteudos: list[Conteudo],
    canceladas: set[date],
    ajustes: dict[str, int],
    hoje: date,
) -> Atraso | None:
    bim = next((b for b in escola.bimestres if b.inicio <= hoje <= b.fim), None)
    if bim is None:
        return None
    agenda = montar_agenda(escola, turma, conteudos, canceladas, ajustes)
    dadas: dict[str, int] = {}
    for a in agenda:
        if a.data < hoje and a.conteudo is not None:
            dadas[a.conteudo.id] = dadas.get(a.conteudo.id, 0) + 1

    pendentes = [c for c in conteudos if c.bimestre <= bim.numero]
    necessarias = sum(max(ajustes.get(c.id, c.aulas) - dadas.get(c.id, 0), 0) for c in pendentes)
    disponiveis = sum(1 for a in agenda if hoje <= a.data <= bim.fim)
    if necessarias <= disponiveis:
        return None

    def ganho(c: Conteudo) -> int:
        return ajustes.get(c.id, c.aulas) - c.aulas_minimas

    sugestoes = sorted(
        (c for c in pendentes if c.bimestre == bim.numero and dadas.get(c.id, 0) == 0 and ganho(c) > 0),
        key=ganho,
        reverse=True,
    )
    return Atraso(turma.id, bim.numero, necessarias, disponiveis, tuple(sugestoes))
