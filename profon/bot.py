"""Bot do Telegram: comandos, botões e jobs agendados. As regras ficam em acoes.py e mensagem.py."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from profon.acoes import aplicar_compressao, atrasos, confirmar_sem_aula, pergunta_sem_aula, texto_atraso
from profon.mensagem import Contexto, compor_mensagens, pregerar, turmas_do_dia

FUSO = ZoneInfo("America/Fortaleza")
SEM_AULAS = "Você não tem aula registrada hoje."
_NAO_TEVE_AULA = re.compile(r"n[ãa]o\s+(teve|tive|houve)\s+aula", re.IGNORECASE)
log = logging.getLogger("profon")

AJUDA = """Olá! Eu sou o Profon. Comandos:
/hoje: aulas e questionários de hoje
/amanha: aulas de amanhã
/semaula [motivo]: hoje não teve aula (empurra o conteúdo das turmas)
/naoterminou: uma turma não terminou o conteúdo de hoje
Você também pode escrever "hoje não teve aula"."""


def _hoje_padrao() -> date:
    return datetime.now(FUSO).date()


def _ctx(context) -> Contexto:
    return context.bot_data["ctx"]


def _hoje(context) -> date:
    return context.bot_data.get("hoje", _hoje_padrao)()


def _autorizado(update: Update, context) -> bool:
    return update.effective_chat is not None and update.effective_chat.id == _ctx(context).escola.telegram_chat_id


def _teclado(*linhas: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in linha] for linha in linhas])


def _botao_sem_aula(dia: date) -> InlineKeyboardMarkup:
    return _teclado([("Não teve aula hoje", f"sem:perg:{dia.isoformat()}")])


def _botoes_confirmacao(dia: date, turma: str = "", motivo: str = "") -> InlineKeyboardMarkup:
    motivo = motivo[:20].replace(":", " ")  # callback_data tem limite de 64 bytes
    return _teclado([("✅ Sim", f"sem:sim:{dia.isoformat()}:{turma}:{motivo}"), ("❌ Não", "sem:nao")])


async def _enviar_dia(enviar, context, dia: date, botao: bool) -> bool:
    msgs = compor_mensagens(_ctx(context), dia)
    for i, m in enumerate(msgs):
        ultimo = i == len(msgs) - 1
        await enviar(m, reply_markup=_botao_sem_aula(dia) if botao and ultimo else None)
    return bool(msgs)


# --- comandos ---------------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _ctx(context).escola.telegram_chat_id == 0:  # ainda não configurado: mostra o id para o YAML
        await update.message.reply_text(f"Seu chat_id é {update.effective_chat.id}. Coloque em config/escola.yaml.")
        return
    if _autorizado(update, context):
        await update.message.reply_text(AJUDA)


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        return
    dia = _hoje(context)
    if not await _enviar_dia(update.message.reply_text, context, dia, botao=True):
        await update.message.reply_text(SEM_AULAS)


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        return
    if not await _enviar_dia(update.message.reply_text, context, _hoje(context) + timedelta(days=1), botao=False):
        await update.message.reply_text("Você não tem aula registrada amanhã.")


async def _perguntar_sem_aula(update: Update, context, motivo: str) -> None:
    dia = _hoje(context)
    pergunta = pergunta_sem_aula(_ctx(context), dia)
    if pergunta is None:
        await update.message.reply_text(SEM_AULAS)
        return
    await update.message.reply_text(pergunta, reply_markup=_botoes_confirmacao(dia, motivo=motivo))


async def cmd_semaula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _autorizado(update, context):
        await _perguntar_sem_aula(update, context, " ".join(context.args or []) or "sem aula")


async def texto_livre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _autorizado(update, context) and _NAO_TEVE_AULA.search(update.message.text or ""):
        await _perguntar_sem_aula(update, context, "sem aula")


async def cmd_naoterminou(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        return
    dia = _hoje(context)
    turmas = turmas_do_dia(_ctx(context), dia)
    if not turmas:
        await update.message.reply_text(SEM_AULAS)
        return
    await update.message.reply_text(
        "Qual turma não terminou o conteúdo de hoje?",
        reply_markup=_teclado(*[[(t.nome, f"nt:{dia.isoformat()}:{t.id}")] for t in turmas]),
    )


# --- botões -----------------------------------------------------------------------------------


async def _pregerar(context, inicio: date) -> list[str]:
    falhas = await asyncio.to_thread(
        pregerar, _ctx(context), context.bot_data["cliente"], context.bot_data["habilidades"], inicio
    )
    for f in falhas:
        log.warning("pré-geração: %s", f)
    return falhas


def _pregerar_em_segundo_plano(context, inicio: date) -> None:
    """Agenda a pré-geração sem aguardar: o bot continua respondendo enquanto a IA trabalha."""
    context.application.create_task(_pregerar(context, inicio))


async def _enviar_atrasos(context, chat: int, dia: date) -> None:
    ctx = _ctx(context)
    for a in atrasos(ctx, dia):
        botoes = [[(f"Acelerar {c.titulo}", f"acel:{a.turma_id}:{c.id}")] for c in a.sugestoes]
        await context.bot.send_message(
            chat_id=chat, text=texto_atraso(ctx, a), reply_markup=_teclado(*botoes) if botoes else None
        )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        return
    q = update.callback_query
    await q.answer()
    partes = q.data.split(":")
    ctx = _ctx(context)
    chat = update.effective_chat.id

    if partes[0] == "sem" and partes[1] == "perg":
        dia = date.fromisoformat(partes[2])
        pergunta = pergunta_sem_aula(ctx, dia)
        await q.message.reply_text(pergunta or SEM_AULAS, reply_markup=_botoes_confirmacao(dia) if pergunta else None)
    elif partes[0] == "sem" and partes[1] == "nao":
        await q.edit_message_text("Tudo certo, nada foi alterado.")
    elif partes[0] == "sem" and partes[1] == "sim":
        dia = date.fromisoformat(partes[2])
        turmas = [partes[3]] if partes[3] else None
        motivo = partes[4] if len(partes) > 4 and partes[4] else "sem aula"
        await q.edit_message_text("\n\n".join(confirmar_sem_aula(ctx, dia, motivo, turmas=turmas)))
        await _enviar_atrasos(context, chat, dia)
        _pregerar_em_segundo_plano(context, dia + timedelta(days=1))
    elif partes[0] == "nt":
        dia, turma = date.fromisoformat(partes[1]), partes[2]
        nome = ctx.escola.turma(turma).nome
        await q.edit_message_text(
            f"{nome} não terminou hoje. Empurro o conteúdo do {nome} para a próxima aula dela?",
            reply_markup=_botoes_confirmacao(dia, turma=turma, motivo="não terminou"),
        )
    elif partes[0] == "acel":
        await q.edit_message_text(aplicar_compressao(ctx, partes[1], partes[2], _hoje(context)))
        _pregerar_em_segundo_plano(context, _hoje(context))  # a compressão muda as aulas seguintes


# --- jobs agendados ---------------------------------------------------------------------------


async def job_envio(context: ContextTypes.DEFAULT_TYPE) -> None:
    async def enviar(texto, reply_markup=None):
        await context.bot.send_message(chat_id=context.job.chat_id, text=texto, reply_markup=reply_markup)

    await _enviar_dia(enviar, context, _hoje(context), botao=True)


async def job_pregerar(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Domingo à noite e ao ligar o bot: prepara os 7 próximos dias e verifica atrasos."""
    dia = _hoje(context)
    falhas = await _pregerar(context, dia)
    await _enviar_atrasos(context, context.job.chat_id, dia)
    if falhas:
        texto = "⚠️ Não consegui preparar alguns questionários da semana:\n" + "\n".join(f"• {f}" for f in falhas)
        await context.bot.send_message(chat_id=context.job.chat_id, text=texto[:4096])


async def job_completar(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Todo dia cedo (depois que a cota gratuita do Gemini renova): preenche questionários que faltaram."""
    await _pregerar(context, _hoje(context))


def criar_app(ctx: Contexto, cliente, habilidades: dict, token: str) -> Application:
    app = Application.builder().token(token).build()
    app.bot_data.update({"ctx": ctx, "cliente": cliente, "habilidades": habilidades})
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("semaula", cmd_semaula))
    app.add_handler(CommandHandler("naoterminou", cmd_naoterminou))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_livre))

    chat = ctx.escola.telegram_chat_id
    hora = ctx.escola.horario_envio.replace(tzinfo=FUSO)
    # Dias no PTB: 0 = domingo ... 6 = sábado
    app.job_queue.run_daily(job_envio, time=hora, days=(1, 2, 3, 4, 5), chat_id=chat, name="envio")
    app.job_queue.run_daily(job_pregerar, time=time(20, 0, tzinfo=FUSO), days=(0,), chat_id=chat, name="pregerar")
    app.job_queue.run_once(job_pregerar, when=10, chat_id=chat, name="pregerar-inicial")  # recupera ao ligar
    app.job_queue.run_daily(job_completar, time=time(5, 15, tzinfo=FUSO), chat_id=chat, name="completar")
    return app
