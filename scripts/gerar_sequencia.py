"""Gera um RASCUNHO da sequência de conteúdos de um ano, para o professor revisar.

Uso: python scripts/gerar_sequencia.py --ano 6 [--habilidades data/curriculo/lp_habilidades.json]
                                        [--saida data/sequencias/6ano.yaml] [--provedor claude|gemini] [--modelo ...]
"""

import argparse
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from profon.curriculo import carregar_habilidades
from profon.config import PROVEDORES
from profon.ia import ClienteClaude, criar_cliente
from profon.sequencia import carregar_sequencia, validar_sequencia

SISTEMA = """Você é um coordenador pedagógico experiente de Língua Portuguesa no Maranhão.
Monte a sequência anual de conteúdos de UM ano do Ensino Fundamental, cobrindo as habilidades
da BNCC desse ano, distribuída em 4 bimestres, na ordem em que um professor daria em sala.

Responda SOMENTE com YAML válido, sem comentários e sem cercas de código, no formato:
ano: <N>
conteudos:
  - {id: <N>-<slug>, bimestre: <1-4>, titulo: <nome curto como o professor fala, ex. "Crônica">,
     habilidades: [<códigos>], aulas: <aulas previstas>, aulas_minimas: <mínimo se precisar acelerar>}

Regras: use só os códigos fornecidos; bimestres em ordem crescente; cerca de 40 a 50 aulas por bimestre
no total; aulas_minimas menor que aulas só quando o conteúdo puder ser "pincelado" sem prejuízo."""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ano", type=int, required=True)
    p.add_argument("--habilidades", default="data/curriculo/lp_habilidades.json")
    p.add_argument("--saida")
    p.add_argument("--provedor", choices=sorted(PROVEDORES), default="claude")
    p.add_argument("--modelo", help="padrão: o modelo padrão do provedor")
    a = p.parse_args()
    load_dotenv()

    habs = carregar_habilidades(Path(a.habilidades))
    do_ano = [h for h in habs.values() if a.ano in h.anos]
    lista = "\n".join(f"{h.codigo}: {h.texto}" for h in do_ano)
    modelo = a.modelo or PROVEDORES[a.provedor]
    cliente = ClienteClaude(modelo, esforco="high") if a.provedor == "claude" else criar_cliente(a.provedor, modelo)
    texto = cliente.completar(
        SISTEMA, f"Ano: {a.ano}º ano.\nHabilidades da BNCC deste ano:\n{lista}"
    )
    texto = re.sub(r"^```(?:yaml)?\s*|\s*```$", "", texto.strip())

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        tmp.write(texto)
    erros = validar_sequencia(carregar_sequencia(Path(tmp.name)), habs)

    saida = Path(a.saida or f"data/sequencias/{a.ano}ano.yaml")
    cabecalho = "# RASCUNHO — revisar antes de usar\n"
    cabecalho += "".join(f"# PROBLEMA: {e}\n" for e in erros)
    saida.write_text(cabecalho + texto + "\n", encoding="utf-8")
    print(f"Rascunho salvo em {saida} ({len(erros)} problema(s) para revisar)")


if __name__ == "__main__":
    main()
