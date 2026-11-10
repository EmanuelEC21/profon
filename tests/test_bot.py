import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from profon import bot
from tests.conftest import SEG1, TER1


def _update(chat_id=1, data=None, texto="/x"):
    msg = SimpleNamespace(reply_text=AsyncMock(), text=texto)
    q = None
    if data is not None:
        q = SimpleNamespace(data=data, answer=AsyncMock(), edit_message_text=AsyncMock(), message=msg)
    return SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=q)


def _context(ctx, hoje, args=()):
    dados = {"ctx": ctx, "cliente": None, "habilidades": {}, "hoje": lambda: hoje, "pregerar": False}
    return SimpleNamespace(bot_data=dados, args=list(args), bot=SimpleNamespace(send_message=AsyncMock()))


def _rodar(coro):
    return asyncio.run(coro)


def test_chat_estranho_ignorado(ctx):
    up = _update(chat_id=999)
    _rodar(bot.cmd_hoje(up, _context(ctx, SEG1)))
    up.message.reply_text.assert_not_called()


def test_hoje_envia_mensagem(ctx):
    up = _update()
    _rodar(bot.cmd_hoje(up, _context(ctx, SEG1)))
    texto = up.message.reply_text.call_args_list[0].args[0]
    assert texto.startswith("☀️ Bom dia!")


def test_semaula_sem_aulas_responde_aviso(ctx):
    up = _update()
    _rodar(bot.cmd_semaula(up, _context(ctx, TER1)))
    assert up.message.reply_text.call_args.args[0] == "Você não tem aula registrada hoje."


def test_semaula_pergunta_com_botoes(ctx):
    up = _update()
    _rodar(bot.cmd_semaula(up, _context(ctx, SEG1, args=["feriado"])))
    chamada = up.message.reply_text.call_args
    assert "Empurro" in chamada.args[0]
    botoes = [b.callback_data for linha in chamada.kwargs["reply_markup"].inline_keyboard for b in linha]
    assert botoes == [f"sem:sim:{SEG1.isoformat()}::feriado", "sem:nao"]


def test_texto_livre_nao_teve_aula(ctx):
    up = _update(texto="hoje não teve aula, choveu muito")
    _rodar(bot.texto_livre(up, _context(ctx, SEG1)))
    assert "Empurro" in up.message.reply_text.call_args.args[0]


def test_callback_sim_cancela(ctx):
    up = _update(data=f"sem:sim:{SEG1.isoformat()}::feriado")
    c = _context(ctx, SEG1)
    _rodar(bot.callback(up, c))
    assert ctx.estado.canceladas("6A") == {SEG1}
    assert "remanejado" in up.callback_query.edit_message_text.call_args.args[0]
    # 6A ficou atrasada: chega um alerta com botão de acelerar
    alertas = [ch for ch in c.bot.send_message.call_args_list if "atrasando" in ch.kwargs["text"]]
    assert alertas


def test_callback_so_uma_turma(ctx):
    up = _update(data=f"sem:sim:{SEG1.isoformat()}:6A:não terminou")
    _rodar(bot.callback(up, _context(ctx, SEG1)))
    assert ctx.estado.canceladas("6A") == {SEG1}
    assert ctx.estado.canceladas("9A") == set()


def test_callback_nao_mantem(ctx):
    up = _update(data="sem:nao")
    _rodar(bot.callback(up, _context(ctx, SEG1)))
    assert ctx.estado.canceladas("6A") == set()


def test_callback_acelerar(ctx):
    up = _update(data="acel:6-b")
    _rodar(bot.callback(up, _context(ctx, SEG1)))
    assert ctx.estado.ajustes() == {"6-b": 1}


def test_envio_diario(ctx):
    c = _context(ctx, SEG1)
    c.job = SimpleNamespace(chat_id=1)
    _rodar(bot.job_envio(c))
    assert c.bot.send_message.call_args_list[0].kwargs["text"].startswith("☀️")


def test_envio_diario_sem_aula_nao_envia(ctx):
    c = _context(ctx, TER1)
    c.job = SimpleNamespace(chat_id=1)
    _rodar(bot.job_envio(c))
    c.bot.send_message.assert_not_called()


def test_criar_app_agenda_jobs(ctx):
    app = bot.criar_app(ctx, None, {}, "123456:TESTE")
    assert {j.name for j in app.job_queue.jobs()} == {"envio", "pregerar"}


def test_main_carrega_contexto(tmp_path):
    from pathlib import Path

    from profon.__main__ import carregar_contexto

    raiz = Path(__file__).parent.parent
    ctx, habs, avisos = carregar_contexto(raiz / "config/escola.example.yaml", raiz / "data", tmp_path / "t.db")
    assert 6 in ctx.sequencias and "EF67LP28" in habs
    # o exemplo só tem a sequência do 6º ano: as outras turmas geram aviso, o 6º não
    assert any("1º A" in a for a in avisos)
    assert not any("6ano" in a or "6º A" in a for a in avisos)
