"""Estado persistente (SQLite). Guarda só eventos: aulas canceladas, ajustes de compressão e questionários.

A agenda em si não é guardada. Ela é recalculada a partir disto (veja agenda.py).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS cancelamentos (
    turma_id TEXT NOT NULL, data TEXT NOT NULL, motivo TEXT NOT NULL,
    PRIMARY KEY (turma_id, data));
CREATE TABLE IF NOT EXISTS ajustes (
    conteudo_id TEXT PRIMARY KEY, aulas INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS questionarios (
    turma_id TEXT NOT NULL, chave TEXT NOT NULL, perguntas_json TEXT NOT NULL,
    PRIMARY KEY (turma_id, chave));
"""


class Estado:
    def __init__(self, caminho: Path | str):
        self._db = sqlite3.connect(str(caminho), check_same_thread=False)
        self._db.executescript(_ESQUEMA)

    def fechar(self) -> None:
        self._db.close()

    def cancelar(self, turma_id: str, data: date, motivo: str) -> bool:
        with self._db:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO cancelamentos VALUES (?, ?, ?)", (turma_id, data.isoformat(), motivo)
            )
        return cur.rowcount == 1

    def canceladas(self, turma_id: str) -> set[date]:
        linhas = self._db.execute("SELECT data FROM cancelamentos WHERE turma_id = ?", (turma_id,))
        return {date.fromisoformat(d) for (d,) in linhas}

    def desfazer_cancelamento(self, turma_id: str, data: date) -> None:
        with self._db:
            self._db.execute("DELETE FROM cancelamentos WHERE turma_id = ? AND data = ?", (turma_id, data.isoformat()))

    def definir_ajuste(self, conteudo_id: str, aulas: int) -> None:
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO ajustes VALUES (?, ?)", (conteudo_id, aulas))

    def ajustes(self) -> dict[str, int]:
        return dict(self._db.execute("SELECT conteudo_id, aulas FROM ajustes"))

    def salvar_questionario(self, turma_id: str, chave: str, perguntas: list[str]) -> None:
        """`chave` identifica a aula do conteúdo (veja mensagem.chave_aula), não a data: assim o
        questionário acompanha o conteúdo quando ele é remanejado."""
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO questionarios VALUES (?, ?, ?)",
                (turma_id, chave, json.dumps(perguntas, ensure_ascii=False)),
            )

    def questionario(self, turma_id: str, chave: str) -> list[str] | None:
        linha = self._db.execute(
            "SELECT perguntas_json FROM questionarios WHERE turma_id = ? AND chave = ?", (turma_id, chave)
        ).fetchone()
        return json.loads(linha[0]) if linha else None
