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


class _ErroGemini(Exception):
    def __init__(self, code):
        self.code = code


class _ModelosComFalha:
    def __init__(self, falham: dict):
        self.falham = falham  # modelo -> código de erro
        self.tentados = []

    def generate_content(self, **kwargs):
        self.tentados.append(kwargs["model"])
        if kwargs["model"] in self.falham:
            raise _ErroGemini(self.falham[kwargs["model"]])
        return SimpleNamespace(text="ok")


def test_gemini_usa_reserva_quando_sobrecarregado():
    modelos = _ModelosComFalha({"gemini-3.8-flash": 503})
    cli = ClienteGemini("gemini-3.8-flash", sdk=SimpleNamespace(models=modelos), reservas=("gemini-3.5-flash",))
    assert cli.completar("s", "m") == "ok"
    assert modelos.tentados == ["gemini-3.8-flash", "gemini-3.5-flash"]


def test_gemini_erro_de_pedido_nao_tenta_reserva():
    modelos = _ModelosComFalha({"gemini-3.8-flash": 400})
    cli = ClienteGemini("gemini-3.8-flash", sdk=SimpleNamespace(models=modelos), reservas=("gemini-3.5-flash",))
    with pytest.raises(_ErroGemini):
        cli.completar("s", "m")
    assert modelos.tentados == ["gemini-3.8-flash"]


class _Relogio:
    def __init__(self):
        self.agora = 0.0
        self.esperas = []

    def __call__(self):
        return self.agora

    def dormir(self, s):
        self.esperas.append(s)
        self.agora += s


def test_gemini_respeita_intervalo_entre_pedidos():
    rel = _Relogio()
    cli = ClienteGemini("m", sdk=SimpleNamespace(models=_ModelosGemini("ok")), reservas=(),
                        intervalo=12.0, relogio=rel, dormir=rel.dormir)
    cli.completar("s", "m")
    cli.completar("s", "m")
    assert rel.esperas == [12.0]


def test_gemini_sobrecarregado_espera_e_tenta_de_novo():
    rel = _Relogio()

    class Modelos:
        n = 0

        def generate_content(self, **kw):
            Modelos.n += 1
            if Modelos.n <= 2:  # principal e reserva falham na 1ª rodada
                raise _ErroGemini(503)
            return SimpleNamespace(text="ok")

    cli = ClienteGemini("a", sdk=SimpleNamespace(models=Modelos()), reservas=("b",),
                        intervalo=0, espera_sobrecarga=30.0, relogio=rel, dormir=rel.dormir)
    assert cli.completar("s", "m") == "ok"
    assert 30.0 in rel.esperas
