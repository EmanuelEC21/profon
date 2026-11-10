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
