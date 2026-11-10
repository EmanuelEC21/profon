"""Acesso à IA (Claude). Tudo que fala com a API passa por aqui."""

from __future__ import annotations

import re
from typing import Protocol


class RecusaIA(Exception):
    """A IA recusou o pedido (stop_reason == "refusal")."""


class ClienteIA(Protocol):
    def completar(self, sistema: str, mensagem: str) -> str: ...


class ClienteClaude:
    """Cliente fino sobre o SDK da Anthropic, com fallback de recusa do lado do servidor."""

    def __init__(self, modelo: str, sdk=None, esforco: str = "medium"):
        if sdk is None:
            import anthropic

            sdk = anthropic.Anthropic()  # credenciais: ANTHROPIC_API_KEY do .env
        self.sdk = sdk
        self.modelo = modelo
        self.esforco = esforco

    def completar(self, sistema: str, mensagem: str) -> str:
        resposta = self.sdk.beta.messages.create(
            model=self.modelo,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": self.esforco},
            system=sistema,
            messages=[{"role": "user", "content": mensagem}],
        )
        if resposta.stop_reason == "refusal":
            raise RecusaIA(str(getattr(resposta, "stop_details", None)))
        return "".join(b.text for b in resposta.content if b.type == "text").strip()


# --- Questionário de quadro -------------------------------------------------------------------

SISTEMA_QUESTIONARIO = """Você ajuda um professor de Língua Portuguesa do Maranhão.
Escreva de 3 a 5 perguntas CURTAS para ele copiar no quadro, para os alunos copiarem e responderem
no caderno, como fixação da aula. Linguagem adequada à idade do ano informado.
Responda só com as perguntas, uma por linha, numeradas (1., 2., ...), sem introdução nem respostas."""

_NUMERACAO = re.compile(r"^\s*(?:\d+[.)-]|[-•*])\s*")


def _perguntas(texto: str) -> list[str]:
    return [_NUMERACAO.sub("", l).strip() for l in texto.splitlines() if _NUMERACAO.sub("", l).strip()]


def gerar_questionario(cliente: ClienteIA, aula, ano: int, habilidades: dict) -> list[str]:
    """Gera de 3 a 5 perguntas de quadro para uma AulaPlanejada. Tenta duas vezes antes de desistir."""
    c = aula.conteudo
    descricoes = "\n".join(
        f"- {cod}: {habilidades[cod].texto}" if cod in habilidades else f"- {cod}" for cod in c.habilidades
    )
    mensagem = (
        f"Ano: {ano}º ano.\nConteúdo: {c.titulo} (aula {aula.numero} de {aula.total} deste conteúdo).\n"
        f"Habilidades da BNCC:\n{descricoes or '- (não informadas)'}\n"
        "Foque no que é esperado nesta etapa do conteúdo (início, meio ou fechamento)."
    )
    for _ in range(2):
        perguntas = _perguntas(cliente.completar(SISTEMA_QUESTIONARIO, mensagem))
        if 3 <= len(perguntas) <= 5:
            return perguntas
    raise ValueError(f"A IA não devolveu de 3 a 5 perguntas para {c.titulo}.")
