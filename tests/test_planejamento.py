from pathlib import Path

from profon.curriculo import Habilidade
from profon.planejamento import montar_tarefas, validar_planejamento

HABS = {"EF06LP01": Habilidade("EF06LP01", "x", (6,)), "EF01LP02": Habilidade("EF01LP02", "y", (1,))}


def _dados(hab="EF06LP01 — Reconhecer..."):
    campos = dict(objetivo="o", conteudos="c", habilidades=[hab], metodologias="m",
                  atividades="a", avaliacao="av", recursos="r")
    return {"mes": "NOV", "pasta": "9 Novembro", "anos": {6: campos}}


def test_valida_codigo_e_ano():
    assert validar_planejamento(_dados(), HABS) == []
    assert any("EF01LP02" in e for e in validar_planejamento(_dados("EF01LP02 — x"), HABS))
    assert any("EF99LP99" in e for e in validar_planejamento(_dados("EF99LP99 — x"), HABS))


def test_valida_campo_faltando():
    d = _dados()
    del d["anos"][6]["recursos"]
    assert any("recursos" in e for e in validar_planejamento(d, HABS))


def test_tarefa_usa_mes_anterior_mais_recente_como_modelo(tmp_path):
    for pasta in ["7 Setembro", "8 Outubro"]:
        (tmp_path / pasta).mkdir()
    (tmp_path / "7 Setembro" / "SET - 6 ANO - LP.docx").write_text("x")
    (tmp_path / "8 Outubro" / "OUT - 6 ANO - LP.docx").write_text("x")
    [t] = montar_tarefas(_dados(), tmp_path)
    assert Path(t["modelo"]).name == "OUT - 6 ANO - LP.docx"
    assert Path(t["docx"]) == tmp_path / "9 Novembro" / "NOV - 6 ANO - LP.docx"
    assert Path(t["pdf"]).name == "NOV - 6 ANO - LP.pdf"
    assert Path(t["copia_pdf"]) == tmp_path / "Por Ano" / "6 ANO" / "NOV - 6 ANO - LP.pdf"
    assert t["campos"]["HABILIDADES"] == "EF06LP01 — Reconhecer..."
    assert t["campos"]["OBJETIVO GERAL"] == "o"


def test_tarefa_sem_modelo_do_ano_falha(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError, match="6 ANO"):
        montar_tarefas(_dados(), tmp_path)
