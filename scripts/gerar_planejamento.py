"""Gera os planejamentos mensais (DOCX + PDF) de todos os anos a partir de data/planejamentos/AAAA-MM.yaml.

Uso: python scripts/gerar_planejamento.py data/planejamentos/2026-11.yaml [--raiz planejamentos]
Precisa do Microsoft Word instalado (o PDF é exportado pelo próprio Word).
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from profon.curriculo import carregar_habilidades
from profon.planejamento import montar_tarefas, validar_planejamento

AQUI = Path(__file__).parent


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("arquivo")
    p.add_argument("--raiz", default="planejamentos")
    p.add_argument("--habilidades", default="data/curriculo/lp_habilidades.json")
    a = p.parse_args()

    dados = yaml.safe_load(Path(a.arquivo).read_text(encoding="utf-8"))
    erros = validar_planejamento(dados, carregar_habilidades(Path(a.habilidades)))
    if erros:
        sys.exit("Planejamento com problemas:\n" + "\n".join(f"- {e}" for e in erros))

    tarefas = montar_tarefas(dados, Path(a.raiz).resolve())
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(tarefas, tmp, ensure_ascii=False)
    script = AQUI / "preencher_planejamento.ps1"
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), tmp.name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit(r.stderr.strip() or "Falha ao gerar no Word.")


if __name__ == "__main__":
    main()
