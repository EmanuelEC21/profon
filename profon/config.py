"""Configuração da escola: dados administrativos, bimestres, dias sem aula e turmas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Bimestre:
    numero: int
    inicio: date
    fim: date


@dataclass(frozen=True)
class Turma:
    id: str
    ano: int
    nome: str
    turno: str
    dias_semana: tuple[int, ...]  # 0 = segunda ... 4 = sexta
    anos: tuple[int, ...] = ()  # turma multisseriada: todos os anos; `ano` é sempre o mais alto

    def __post_init__(self):
        if not self.anos:
            object.__setattr__(self, "anos", (self.ano,))


@dataclass(frozen=True)
class Escola:
    professor: str
    escola: str
    coordenador: str
    disciplina: str
    horario_envio: time
    modelo_ia: str
    telegram_chat_id: int
    bimestres: tuple[Bimestre, ...]
    dias_sem_aula: dict[date, str] = field(hash=False)
    turmas: tuple[Turma, ...]
    provedor_ia: str = "gemini"  # "gemini" (padrão, camada gratuita) ou "claude"

    def turma(self, id: str) -> Turma:
        for t in self.turmas:
            if t.id == id:
                return t
        raise KeyError(f"Turma não encontrada: {id}")


PROVEDORES = {"claude": "claude-opus-5-5", "gemini": "gemini-flash-latest"}  # provedor -> modelo padrão


def _data(valor) -> date:
    return valor if isinstance(valor, date) else date.fromisoformat(str(valor))


def _hora(valor) -> time:
    if isinstance(valor, int):  # YAML 1.1 lê 06:00 sem aspas como minutos
        return time(valor // 60, valor % 60)
    return time.fromisoformat(str(valor))


def carregar_escola(caminho: Path) -> Escola:
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))

    bimestres = tuple(
        sorted(
            (Bimestre(int(b["numero"]), _data(b["inicio"]), _data(b["fim"])) for b in dados["bimestres"]),
            key=lambda b: b.inicio,
        )
    )
    for b in bimestres:
        if b.fim < b.inicio:
            raise ValueError(f"Bimestre {b.numero} termina antes de começar.")
    for anterior, atual in zip(bimestres, bimestres[1:]):
        if atual.inicio <= anterior.fim:
            raise ValueError(f"Bimestres {anterior.numero} e {atual.numero} estão sobrepostos.")

    turmas = []
    ids = set()
    for t in dados["turmas"]:
        dias = tuple(int(d) for d in t["dias_semana"])
        if not dias or any(d < 0 or d > 4 for d in dias):
            raise ValueError(f"Turma {t['id']}: dias_semana deve ter valores de 0 (segunda) a 4 (sexta).")
        if str(t["id"]) in ids:
            raise ValueError(f"Turma duplicada: {t['id']}")
        ids.add(str(t["id"]))
        anos = tuple(sorted(int(a) for a in t["anos"])) if "anos" in t else (int(t["ano"]),)
        # Multisseriada (ex.: 1º, 2º e 3º juntos): o planejamento segue o ano mais alto.
        turmas.append(Turma(str(t["id"]), max(anos), str(t["nome"]), str(t["turno"]), dias, anos))

    provedor = str(dados.get("provedor_ia", "gemini")).lower()
    if provedor not in PROVEDORES:
        raise ValueError(f"provedor_ia deve ser um de: {', '.join(PROVEDORES)} (veio {provedor!r}).")

    return Escola(
        professor=str(dados["professor"]),
        escola=str(dados["escola"]),
        coordenador=str(dados["coordenador"]),
        disciplina=str(dados["disciplina"]),
        horario_envio=_hora(dados.get("horario_envio", "06:00")),
        modelo_ia=str(dados.get("modelo_ia") or PROVEDORES[provedor]),
        provedor_ia=provedor,
        telegram_chat_id=int(dados["telegram_chat_id"]),
        bimestres=bimestres,
        dias_sem_aula={_data(k): str(v) for k, v in (dados.get("dias_sem_aula") or {}).items()},
        turmas=tuple(turmas),
    )
