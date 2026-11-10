"""Acesso à IA (Claude). Tudo que fala com a API passa por aqui."""

from __future__ import annotations

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
