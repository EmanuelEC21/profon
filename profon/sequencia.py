"""Sequência de conteúdos de um ano: a ordem em que os assuntos são dados e quantas aulas cada um ocupa."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from profon.curriculo import Habilidade


@dataclass(frozen=True)
class Conteudo:
    id: str
    ano: int
    bimestre: int
    titulo: str
    habilidades: tuple[str, ...]
    aulas: int
    aulas_minimas: int

    @property
    def compressivel(self) -> bool:
        return self.aulas_minimas < self.aulas


def carregar_sequencia(caminho: Path) -> list[Conteudo]:
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    ano = int(dados["ano"])
    return [
        Conteudo(
            id=str(c["id"]),
            ano=ano,
            bimestre=int(c["bimestre"]),
            titulo=str(c["titulo"]),
            habilidades=tuple(str(h) for h in c.get("habilidades", [])),
            aulas=int(c["aulas"]),
            aulas_minimas=int(c.get("aulas_minimas", c["aulas"])),
        )
        for c in dados["conteudos"]
    ]


def validar_sequencia(conteudos: list[Conteudo], habilidades: dict[str, Habilidade]) -> list[str]:
    erros: list[str] = []
    ids: set[str] = set()
    bimestre_anterior = 0
    for c in conteudos:
        nome = f"{c.id} ({c.titulo})"
        if c.id in ids:
            erros.append(f"{nome}: id repetido.")
        ids.add(c.id)
        if c.aulas < 1:
            erros.append(f"{nome}: precisa de pelo menos 1 aula.")
        if c.aulas_minimas < 1 or c.aulas_minimas > c.aulas:
            erros.append(f"{nome}: aulas_minimas deve ficar entre 1 e {c.aulas}.")
        if not 1 <= c.bimestre <= 4:
            erros.append(f"{nome}: bimestre {c.bimestre} não existe (use 1 a 4).")
        elif c.bimestre < bimestre_anterior:
            erros.append(f"{nome}: bimestre {c.bimestre} fora de ordem (vem depois do {bimestre_anterior}).")
        else:
            bimestre_anterior = c.bimestre
        for codigo in c.habilidades:
            h = habilidades.get(codigo)
            if h is None:
                erros.append(f"{nome}: habilidade {codigo} não existe na BNCC.")
            elif c.ano not in h.anos:
                erros.append(f"{nome}: habilidade {codigo} não é do {c.ano}º ano.")
    return erros
