"""Acesso à IA (Claude). Tudo que fala com a API passa por aqui."""

from __future__ import annotations

import re
import time
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


class ClienteGemini:
    """Cliente fino sobre o SDK google-genai (chave gratuita do Google AI Studio em GEMINI_API_KEY)."""

    # Erros passageiros (sobrecarga, limite por minuto, falha do servidor): tenta o modelo reserva.
    _PASSAGEIROS = {429, 500, 503}

    def __init__(
        self,
        modelo: str,
        sdk=None,
        reservas: tuple[str, ...] = ("gemini-3.5-flash",),
        intervalo: float = 13.0,  # camada gratuita: ~5 pedidos por minuto
        espera_sobrecarga: float = 30.0,
        rodadas: int = 3,
        relogio=time.monotonic,
        dormir=time.sleep,
    ):
        if sdk is None:
            from google import genai

            sdk = genai.Client()  # lê GEMINI_API_KEY (ou GOOGLE_API_KEY) do ambiente
        self.sdk = sdk
        self.modelos = [modelo, *(r for r in reservas if r != modelo)]
        self.intervalo, self.espera_sobrecarga, self.rodadas = intervalo, espera_sobrecarga, rodadas
        self._relogio, self._dormir = relogio, dormir
        self._ultimo: float | None = None

    def _respeitar_intervalo(self) -> None:
        if self._ultimo is not None:
            falta = self.intervalo - (self._relogio() - self._ultimo)
            if falta > 0:
                self._dormir(falta)
        self._ultimo = self._relogio()

    def _gerar(self, mensagem: str, config):
        """Tenta o modelo principal e as reservas; em sobrecarga, espera e faz nova rodada."""
        for rodada in range(self.rodadas):
            cota_diaria = 0
            for i, modelo in enumerate(self.modelos):
                try:
                    return self.sdk.models.generate_content(model=modelo, contents=mensagem, config=config)
                except Exception as e:
                    if "PerDay" in str(e):  # cota do dia deste modelo acabou: só a reserva pode ajudar
                        cota_diaria += 1
                        if cota_diaria == len(self.modelos):
                            raise
                        continue
                    ultima_tentativa = rodada == self.rodadas - 1 and i == len(self.modelos) - 1
                    if getattr(e, "code", None) not in self._PASSAGEIROS or ultima_tentativa:
                        raise
            self._dormir(self.espera_sobrecarga)

    def completar(self, sistema: str, mensagem: str) -> str:
        from google.genai import types

        self._respeitar_intervalo()
        config = types.GenerateContentConfig(system_instruction=sistema, max_output_tokens=16000)
        resposta = self._gerar(mensagem, config)
        texto = (resposta.text or "").strip()
        if not texto:  # bloqueado pelos filtros de segurança ou resposta vazia
            raise RecusaIA(str(getattr(resposta, "prompt_feedback", None)))
        return texto


def criar_cliente(provedor: str, modelo: str, sdk=None) -> ClienteIA:
    """Escolhe o cliente pelo provedor configurado em escola.yaml (provedor_ia)."""
    if provedor == "claude":
        return ClienteClaude(modelo, sdk=sdk)
    if provedor == "gemini":
        return ClienteGemini(modelo, sdk=sdk)
    raise ValueError(f"provedor de IA desconhecido: {provedor!r} (use claude ou gemini).")


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


# --- Material da aula: roteiro do professor + questionário, num pedido só ---------------------

SISTEMA_MATERIAL = """Você prepara aulas de Língua Portuguesa para um professor do Maranhão (Ensino Fundamental).
Para a aula informada, produza:
1. "roteiro": de 3 a 6 tópicos que o professor deve explicar NESTA aula, na ordem em que vai explicar.
   Cada tópico tem "topico" (título curto) e "explicacao" (2 a 4 frases dizendo o que explicar e como,
   com exemplos simples; quando couber, cite autores brasileiros ou maranhenses).
2. "perguntas": de 3 a 5 perguntas CURTAS para o professor copiar no quadro e os alunos responderem
   no caderno, como fixação. Linguagem adequada à idade do ano.
Considere a etapa do conteúdo: aula 1 introduz; aulas do meio aprofundam; a última fecha e pratica.
Responda SOMENTE com JSON válido: {"roteiro": [{"topico": "...", "explicacao": "..."}], "perguntas": ["..."]}"""


def _ler_material(texto: str) -> dict:
    import json

    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fim < 0:
        raise ValueError("resposta sem JSON")
    dados = json.loads(texto[inicio : fim + 1])
    roteiro = [
        {"topico": str(t.get("topico", "")).strip(), "explicacao": str(t.get("explicacao", "")).strip()}
        for t in dados.get("roteiro") or []
        if isinstance(t, dict)
    ]
    roteiro = [t for t in roteiro if t["topico"] and t["explicacao"]]
    perguntas = [_NUMERACAO.sub("", str(p)).strip() for p in dados.get("perguntas") or []]
    perguntas = [p for p in perguntas if p]
    if not 3 <= len(roteiro) <= 6 or not 3 <= len(perguntas) <= 5:
        raise ValueError(f"roteiro com {len(roteiro)} tópicos e {len(perguntas)} perguntas")
    return {"roteiro": roteiro, "perguntas": perguntas}


def gerar_material(cliente: ClienteIA, aula, ano: int, habilidades: dict) -> dict:
    """Roteiro do professor (3 a 6 tópicos) e questionário de quadro (3 a 5) para uma AulaPlanejada."""
    c = aula.conteudo
    descricoes = "\n".join(
        f"- {cod}: {habilidades[cod].texto}" if cod in habilidades else f"- {cod}" for cod in c.habilidades
    )
    mensagem = (
        f"Ano: {ano}º ano.\nConteúdo: {c.titulo} (aula {aula.numero} de {aula.total} deste conteúdo).\n"
        f"Habilidades da BNCC:\n{descricoes or '- (não informadas)'}"
    )
    erro: Exception | None = None
    for _ in range(2):
        try:
            return _ler_material(cliente.completar(SISTEMA_MATERIAL, mensagem))
        except ValueError as e:  # json.JSONDecodeError também é ValueError
            erro = e
    raise ValueError(f"A IA não devolveu o material no formato esperado para {c.titulo}: {erro}")
