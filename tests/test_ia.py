from types import SimpleNamespace

import pytest

from profon.ia import ClienteClaude, RecusaIA


class _Mensagens:
    def __init__(self, resposta):
        self.resposta = resposta
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.resposta


def _sdk(resposta):
    msgs = _Mensagens(resposta)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def test_completar_junta_texto_e_usa_modelo():
    resp = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="olá")],
    )
    sdk, msgs = _sdk(resp)
    assert ClienteClaude("claude-opus-5-5", sdk=sdk).completar("sis", "msg") == "olá"
    assert msgs.kwargs["model"] == "claude-opus-5-5"
    assert msgs.kwargs["system"] == "sis"
    assert msgs.kwargs["fallbacks"] == "default"


def test_recusa_vira_excecao():
    resp = SimpleNamespace(stop_reason="refusal", content=[], stop_details=None)
    sdk, _ = _sdk(resp)
    with pytest.raises(RecusaIA):
        ClienteClaude("claude-opus-5-5", sdk=sdk).completar("s", "m")


# --- Gemini e escolha de provedor --------------------------------------------------------------

from profon.ia import ClienteGemini, criar_cliente


class _ModelosGemini:
    def __init__(self, texto):
        self.texto = texto
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text=self.texto)


def test_gemini_completar_usa_instrucao_de_sistema():
    modelos = _ModelosGemini("  olá  ")
    cli = ClienteGemini("gemini-flash-latest", sdk=SimpleNamespace(models=modelos))
    assert cli.completar("sis", "msg") == "olá"
    assert modelos.kwargs["model"] == "gemini-flash-latest"
    assert modelos.kwargs["contents"] == "msg"
    assert modelos.kwargs["config"].system_instruction == "sis"


def test_gemini_resposta_bloqueada_vira_recusa():
    cli = ClienteGemini("gemini-flash-latest", sdk=SimpleNamespace(models=_ModelosGemini(None)))
    with pytest.raises(RecusaIA):
        cli.completar("s", "m")


def test_criar_cliente_por_provedor():
    sdk = SimpleNamespace(models=None, beta=None)
    assert isinstance(criar_cliente("gemini", "gemini-flash-latest", sdk=sdk), ClienteGemini)
    assert isinstance(criar_cliente("claude", "claude-opus-5-5", sdk=sdk), ClienteClaude)
    with pytest.raises(ValueError, match="provedor"):
        criar_cliente("chatgpt", "x", sdk=sdk)
