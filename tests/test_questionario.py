import pytest

from profon.ia import gerar_questionario
from profon.mensagem import aulas_do_dia, pregerar
from tests.conftest import SEG1


class ClienteFalso:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def completar(self, sistema, mensagem):
        self.chamadas.append(mensagem)
        r = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        if isinstance(r, Exception):
            raise r
        return r


QUATRO = "1. O que é crônica?\n2. Onde se publica?\n3. Cite um cronista.\n4. Qual o tom?"


def test_questionario_3_a_5(ctx):
    aula = aulas_do_dia(ctx, SEG1)[0]
    cliente = ClienteFalso(QUATRO)
    perguntas = gerar_questionario(cliente, aula, 6, {})
    assert perguntas == ["O que é crônica?", "Onde se publica?", "Cite um cronista.", "Qual o tom?"]
    assert "Crônica" in cliente.chamadas[0] and "6º ano" in cliente.chamadas[0]


def test_questionario_resposta_ruim_tenta_de_novo(ctx):
    aula = aulas_do_dia(ctx, SEG1)[0]
    cliente = ClienteFalso("só uma", QUATRO)
    assert len(gerar_questionario(cliente, aula, 6, {})) == 4
    assert len(cliente.chamadas) == 2


def test_questionario_ruim_duas_vezes_falha(ctx):
    aula = aulas_do_dia(ctx, SEG1)[0]
    with pytest.raises(ValueError):
        gerar_questionario(ClienteFalso("só uma"), aula, 6, {})


def test_pregerar_salva_e_pula_existentes(ctx):
    cliente = ClienteFalso(QUATRO)
    falhas = pregerar(ctx, cliente, {}, SEG1, dias=1)
    assert falhas == []
    assert ctx.estado.questionario("6ano", "6-a#1/2") is not None
    n = len(cliente.chamadas)
    pregerar(ctx, cliente, {}, SEG1, dias=1)
    assert len(cliente.chamadas) == n


def test_pregerar_falha_nao_explode(ctx):
    falhas = pregerar(ctx, ClienteFalso(RuntimeError("API fora")), {}, SEG1, dias=1)
    assert len(falhas) == 2
    assert "6º A" in falhas[0]
