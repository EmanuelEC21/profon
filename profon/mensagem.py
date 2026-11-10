"""O que acontece em cada dia: as aulas do dia e o texto da mensagem da manhã."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from profon.agenda import AulaPlanejada, montar_agenda
from profon.config import Escola, Turma
from profon.estado import Estado
from profon.sequencia import Conteudo


@dataclass
class Contexto:
    escola: Escola
    sequencias: dict[str, list[Conteudo]]  # chave: nome da sequência (Turma.sequencia)
    estado: Estado


def agenda_da_turma(ctx: Contexto, turma: Turma) -> list[AulaPlanejada]:
    return montar_agenda(
        ctx.escola, turma, ctx.sequencias.get(turma.sequencia, []), ctx.estado.canceladas(turma.id), ctx.estado.ajustes(turma.id)
    )


def turmas_do_dia(ctx: Contexto, dia: date) -> list[Turma]:
    return [t for t in ctx.escola.turmas if any(a.data == dia for a in agenda_da_turma(ctx, t))]


def aulas_do_dia(ctx: Contexto, dia: date) -> list[AulaPlanejada]:
    aulas = []
    for t in sorted(ctx.escola.turmas, key=lambda t: t.horario):  # sem horário: mantém a ordem do YAML
        aulas.extend(a for a in agenda_da_turma(ctx, t) if a.data == dia)
    return aulas


# --- Pré-geração e mensagem da manhã ---------------------------------------------------------

LIMITE_TELEGRAM = 4096


def _dono(ctx: Contexto, aula: AulaPlanejada) -> str:
    """Questionários são guardados por sequência: turmas que seguem a mesma sequência compartilham."""
    return ctx.escola.turma(aula.turma_id).sequencia


def chave_aula(aula: AulaPlanejada) -> str:
    """Identifica a aula pelo conteúdo, não pela data (ex.: "6-cronica#2/6")."""
    return f"{aula.conteudo.id}#{aula.numero}/{aula.total}"


def motivo_falha(e: Exception) -> str:
    """Traduz o erro da IA para uma frase curta, sem detalhes técnicos."""
    texto, codigo = str(e), getattr(e, "code", None)
    if "PerDay" in texto:
        return "cota diária do Gemini esgotada"
    if codigo == 429:
        return "limite de pedidos por minuto"
    if codigo in (500, 503):
        return "Gemini sobrecarregado"
    if type(e).__name__ == "RecusaIA":
        return "a IA recusou o pedido"
    if isinstance(e, ValueError):
        return "a IA respondeu fora do formato"
    return texto.splitlines()[0][:80] if texto else type(e).__name__


def pregerar(ctx: Contexto, cliente, habilidades: dict, inicio: date, dias: int = 7) -> list[str]:
    """Gera e salva os questionários do período. Nunca levanta exceção: devolve as falhas em texto."""
    from profon.ia import gerar_material

    falhas: list[str] = []
    for i in range(dias):
        dia = inicio + timedelta(days=i)
        for aula in aulas_do_dia(ctx, dia):
            existente = ctx.estado.material(_dono(ctx, aula), chave_aula(aula)) if aula.conteudo else None
            if aula.conteudo is None or (existente and existente["roteiro"]):
                continue  # sem conteúdo, ou material completo já pronto (o antigo, sem roteiro, é refeito)
            turma = ctx.escola.turma(aula.turma_id)
            try:
                material = gerar_material(cliente, aula, turma.ano, habilidades)
                ctx.estado.salvar_material(_dono(ctx, aula), chave_aula(aula), material)
            except Exception as e:  # a pré-geração nunca pode derrubar o bot
                falhas.append(f"{turma.nome} {dia:%d/%m} ({aula.conteudo.titulo}): {motivo_falha(e)}")
    return falhas


def _bloco(ctx: Contexto, aula: AulaPlanejada) -> str:
    turma = ctx.escola.turma(aula.turma_id)
    nome = f"{turma.horario} · {turma.nome}" if turma.horario else turma.nome
    if aula.conteudo is None:
        return f"📚 {nome} — Sequência concluída (aula livre/revisão)"
    c = aula.conteudo
    codigos = f" · {', '.join(c.habilidades)}" if c.habilidades else ""
    linhas = [f"📚 {nome} — {c.titulo} (aula {aula.numero} de {aula.total}){codigos}", "✏️ Para o quadro:"]
    material = ctx.estado.material(_dono(ctx, aula), chave_aula(aula))
    perguntas = material["perguntas"] if material else None
    if perguntas:
        linhas += [f"{i}. {p}" for i, p in enumerate(perguntas, 1)]
    else:
        linhas.append("(questionário indisponível hoje)")
    return "\n".join(linhas)


def compor_mensagens(ctx: Contexto, dia: date) -> list[str]:
    aulas = aulas_do_dia(ctx, dia)
    if not aulas:
        return []
    from profon.acoes import juntar_nomes

    cabecalho = f"☀️ Bom dia! Hoje: {juntar_nomes([ctx.escola.turma(a.turma_id).nome for a in aulas])}"
    blocos = [_bloco(ctx, a) for a in aulas]
    inteira = "\n\n".join([cabecalho, *blocos])
    if len(inteira) <= LIMITE_TELEGRAM:
        return [inteira]
    return [cabecalho, *(b[:LIMITE_TELEGRAM] for b in blocos)]
