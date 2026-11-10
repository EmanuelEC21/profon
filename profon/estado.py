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
    turma_id TEXT NOT NULL, conteudo_id TEXT NOT NULL, aulas INTEGER NOT NULL,
    PRIMARY KEY (turma_id, conteudo_id));
CREATE TABLE IF NOT EXISTS questionarios (
    turma_id TEXT NOT NULL, chave TEXT NOT NULL, perguntas_json TEXT NOT NULL,
    PRIMARY KEY (turma_id, chave));
CREATE TABLE IF NOT EXISTS materiais (
    dono TEXT NOT NULL, chave TEXT NOT NULL, material_json TEXT NOT NULL,
    PRIMARY KEY (dono, chave));
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

    def definir_ajuste(self, turma_id: str, conteudo_id: str, aulas: int) -> None:
        """Compressão vale só para a turma informada (outras turmas do mesmo ano não mudam)."""
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO ajustes VALUES (?, ?, ?)", (turma_id, conteudo_id, aulas))

    def ajustes(self, turma_id: str) -> dict[str, int]:
        return dict(self._db.execute("SELECT conteudo_id, aulas FROM ajustes WHERE turma_id = ?", (turma_id,)))

    def salvar_questionario(self, turma_id: str, chave: str, perguntas: list[str]) -> None:
        """`chave` identifica a aula do conteúdo (veja mensagem.chave_aula), não a data: assim o
        questionário acompanha o conteúdo quando ele é remanejado."""
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO questionarios VALUES (?, ?, ?)",
                (turma_id, chave, json.dumps(perguntas, ensure_ascii=False)),
            )

    def salvar_material(self, dono: str, chave: str, material: dict) -> None:
        """Material da aula: {"roteiro": [{"topico", "explicacao"}], "perguntas": [...]}.
        `dono` é a sequência (turmas da mesma sequência compartilham); `chave` é mensagem.chave_aula."""
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO materiais VALUES (?, ?, ?)",
                (dono, chave, json.dumps(material, ensure_ascii=False)),
            )

    def material(self, dono: str, chave: str) -> dict | None:
        linha = self._db.execute(
            "SELECT material_json FROM materiais WHERE dono = ? AND chave = ?", (dono, chave)
        ).fetchone()
        if linha:
            return json.loads(linha[0])
        antigo = self.questionario(dono, chave)  # questionários gerados antes do roteiro existir
        return {"roteiro": [], "perguntas": antigo} if antigo else None

    def questionario(self, turma_id: str, chave: str) -> list[str] | None:
        linha = self._db.execute(
            "SELECT perguntas_json FROM questionarios WHERE turma_id = ? AND chave = ?", (turma_id, chave)
        ).fetchone()
        return json.loads(linha[0]) if linha else None
