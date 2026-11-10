"""Inicia o Profon: python -m profon

Lê .env (TELEGRAM_TOKEN e ANTHROPIC_API_KEY ou GEMINI_API_KEY), config/escola.yaml, data/sequencias/*.yaml,
data/curriculo/lp_habilidades.json e profon.db.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from profon.config import carregar_escola
from profon.curriculo import Habilidade, carregar_habilidades
from profon.estado import Estado
from profon.mensagem import Contexto
from profon.sequencia import carregar_sequencia, validar_sequencia


def carregar_contexto(config: Path, dados: Path, banco: Path) -> tuple[Contexto, dict[str, Habilidade], list[str]]:
    escola = carregar_escola(config)
    habilidades = carregar_habilidades(dados / "curriculo" / "lp_habilidades.json")
    sequencias, avisos = {}, []
    for arq in sorted((dados / "sequencias").glob("*.yaml")):
        conteudos = carregar_sequencia(arq)
        sequencias[arq.stem] = conteudos  # nome do arquivo = Turma.sequencia
        avisos += [f"{arq.name}: {e}" for e in validar_sequencia(conteudos, habilidades)]
    for t in escola.turmas:
        if t.sequencia not in sequencias:
            avisos.append(f"Turma {t.nome}: não há data/sequencias/{t.sequencia}.yaml.")
    return Contexto(escola, sequencias, Estado(banco)), habilidades, avisos


def main() -> None:
    from dotenv import load_dotenv

    from profon.bot import criar_app
    from profon.ia import criar_cliente

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        sys.exit("Falta TELEGRAM_TOKEN no arquivo .env (veja docs/guia-do-professor.md).")
    ctx, habilidades, avisos = carregar_contexto(Path("config/escola.yaml"), Path("data"), Path("profon.db"))
    for a in avisos:
        logging.warning(a)
    cliente = criar_cliente(ctx.escola.provedor_ia, ctx.escola.modelo_ia)
    logging.info("IA: %s (%s)", ctx.escola.provedor_ia, ctx.escola.modelo_ia)
    app = criar_app(ctx, cliente, habilidades, token)
    logging.info("Profon no ar. Envio diário às %s.", ctx.escola.horario_envio.strftime("%H:%M"))
    app.run_polling()


if __name__ == "__main__":
    main()
