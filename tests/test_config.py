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


def test_provedor_padrao_gemini():
    escola = carregar_escola(EXEMPLO)
    assert (escola.provedor_ia, escola.modelo_ia) == ("gemini", "gemini-flash-latest")


def test_sem_provedor_no_yaml_usa_gemini(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(_yaml_minimo("  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}"), encoding="utf-8")
    assert carregar_escola(arq).provedor_ia == "gemini"


def test_gemini_tem_modelo_padrao_proprio(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo("  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}") + "provedor_ia: gemini\n",
        encoding="utf-8",
    )
    escola = carregar_escola(arq)
    assert (escola.provedor_ia, escola.modelo_ia) == ("gemini", "gemini-flash-latest")


def test_provedor_invalido_falha(tmp_path):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo("  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}") + "provedor_ia: chatgpt\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="provedor_ia"):
        carregar_escola(arq)


def _turma_yaml(tmp_path, linha_turma, extra=""):
    arq = tmp_path / "e.yaml"
    arq.write_text(
        _yaml_minimo("  - {numero: 1, inicio: 2027-02-01, fim: 2027-04-30}", linha_turma) + extra,
        encoding="utf-8",
    )
    return carregar_escola(arq)


def test_tres_anos_juntos_usa_o_do_meio(tmp_path):
    t = _turma_yaml(tmp_path, "  - {id: M1, anos: [1, 2, 3], nome: M, turno: manhã, dias_semana: [0]}").turma("M1")
    assert (t.ano, t.anos) == (2, (1, 2, 3))


def test_dois_anos_juntos_nivela_por_cima(tmp_path):
    t = _turma_yaml(tmp_path, "  - {id: M2, anos: [8, 9], nome: M, turno: manhã, dias_semana: [4]}").turma("M2")
    assert t.ano == 9


def test_ano_explicito_vence_a_regra(tmp_path):
    t = _turma_yaml(tmp_path, "  - {id: M3, anos: [1, 2, 3], ano: 3, nome: M, turno: manhã, dias_semana: [0]}").turma("M3")
    assert t.ano == 3


def test_turma_seriada_tem_um_ano():
    t = carregar_escola(EXEMPLO).turma("6A")
    assert (t.ano, t.anos) == (6, (6,))


def test_sequencia_e_horario_da_turma(tmp_path):
    e = _turma_yaml(
        tmp_path,
        "  - {id: S1, anos: [8, 9], nome: M, turno: manhã, dias_semana: [4], horario: '07:30', sequencia: 9ano-producao}",
    )
    t = e.turma("S1")
    assert (t.sequencia, t.horario) == ("9ano-producao", "07:30")


def test_sequencia_padrao_pelo_ano():
    assert carregar_escola(EXEMPLO).turma("6A").sequencia == "6ano"


def test_inicio_de_uso(tmp_path):
    from datetime import date

    e = _turma_yaml(tmp_path, "", "inicio: 2027-03-01\n")
    assert e.inicio == date(2027, 3, 1)
    assert carregar_escola(EXEMPLO).inicio is None
