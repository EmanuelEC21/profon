import io

from pypdf import PdfReader

from profon.folha import gerar_folha, nome_arquivo
from tests.conftest import SEG1, TER1

MATERIAL = {
    "roteiro": [
        {"topico": "O que é crônica", "explicacao": "Texto curto do cotidiano, publicado em jornal."},
        {"topico": "Autores maranhenses", "explicacao": "Comente Josué Montello e a São Luís das crônicas."},
        {"topico": "Tom e linguagem", "explicacao": "Linguagem leve, humor ou reflexão — “quase uma conversa”."},
    ],
    "perguntas": ["O que é uma crônica?", "Onde ela é publicada?", "Cite um cronista maranhense."],
}


def _texto(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_sem_aulas_sem_folha(ctx):
    assert gerar_folha(ctx, TER1) is None


def test_folha_tem_turmas_roteiro_e_perguntas(ctx):
    ctx.estado.salvar_material("6ano", "6-a#1/2", MATERIAL)
    pdf = gerar_folha(ctx, SEG1)
    assert pdf[:4] == b"%PDF"
    texto = _texto(pdf)
    for trecho in ["6º A", "9º A", "Crônica", "aula 1 de 2", "Roteiro do professor", "O que é crônica",
                   "Josué Montello", "Para o quadro", "1. O que é uma crônica?", "Argumentação"]:
        assert trecho in texto, trecho


def test_folha_avisa_quando_material_falta(ctx):
    texto = _texto(gerar_folha(ctx, SEG1))
    assert "indisponíveis" in texto


def test_folha_sequencia_concluida(ctx):
    ctx.sequencias["6ano"] = []
    assert "Sequência concluída" in _texto(gerar_folha(ctx, SEG1))


def test_folha_muitas_turmas_quebra_pagina(ctx):
    longo = dict(MATERIAL, roteiro=[{"topico": f"Tópico {i}", "explicacao": "explicação " * 60} for i in range(6)])
    ctx.estado.salvar_material("6ano", "6-a#1/2", longo)
    ctx.estado.salvar_material("9ano", "9-c#1/3", longo)
    assert len(PdfReader(io.BytesIO(gerar_folha(ctx, SEG1))).pages) >= 2


def test_nome_arquivo():
    assert nome_arquivo(SEG1) == "aulas-2027-03-01.pdf"


def test_turmas_com_a_mesma_aula_aparecem_juntas(ctx):
    from dataclasses import replace

    t6b = replace(ctx.escola.turma("6A"), id="6B", nome="6º B")
    ctx.escola = replace(ctx.escola, turmas=ctx.escola.turmas + (t6b,))
    ctx.estado.salvar_material("6ano", "6-a#1/2", MATERIAL)
    texto = _texto(gerar_folha(ctx, SEG1))
    assert texto.count("Roteiro do professor") == 1
    assert "6º A" in texto and "6º B" in texto
