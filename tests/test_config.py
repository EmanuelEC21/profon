from datetime import time
from pathlib import Path

import pytest

from profon.config import carregar_escola

EXEMPLO = Path(__file__).parent.parent / "config" / "escola.example.yaml"


def test_carrega_exemplo():
    escola = carregar_escola(EXEMPLO)
    assert len(escola.bimestres) == 4
    assert escola.horario_envio == time(6, 0)
    assert escola.disciplina == "Língua Portuguesa"


def test_turma_por_id():
    escola = carregar_escola(EXEMPLO)
    assert escola.turma("6A").ano == 6


def _yaml_minimo(bimestres: str, turmas: str = "") -> str:
    return f"""
professor: P
escola: E
coordenador: C
disciplina: Língua Portuguesa
telegram_chat_id: 1
bimestres:
{bimestres}
turmas:
{turmas or '  - {id: 6A, ano: 6, nome: 6º A, turno: manhã, dias_semana: [0]}'}
"""


def test_bimestres_sobrepostos_falha(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo(
            "  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}\n"
            "  - {numero: 2, inicio: 2027-04-15, fim: 2027-06-30}"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sobrep"):
        carregar_escola(arq)


def test_dia_semana_invalido_falha(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo(
            "  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}",
            "  - {id: 6A, ano: 6, nome: 6º A, turno: manhã, dias_semana: [5]}",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dias_semana"):
        carregar_escola(arq)


def test_turma_duplicada_falha(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo(
            "  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}",
            "  - {id: 6A, ano: 6, nome: 6º A, turno: manhã, dias_semana: [0]}\n"
            "  - {id: 6A, ano: 6, nome: 6º A, turno: manhã, dias_semana: [1]}",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicad"):
        carregar_escola(arq)
