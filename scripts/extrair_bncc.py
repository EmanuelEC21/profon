"""Gera data/curriculo/lp_habilidades.json a partir do PDF da BNCC.

Uso: python scripts/extrair_bncc.py BNCC.pdf data/curriculo/lp_habilidades.json
"""

import sys
from pathlib import Path

from pypdf import PdfReader

from profon.curriculo import extrair_habilidades, salvar_habilidades


def main(pdf: str, saida: str) -> None:
    leitor = PdfReader(pdf, strict=False)  # o poppler falha nesse arquivo; o pypdf lê
    texto = "\n".join((p.extract_text() or "") for p in leitor.pages)
    habilidades = extrair_habilidades(texto)
    salvar_habilidades(habilidades, Path(saida))
    print(f"{len(habilidades)} habilidades únicas salvas em {saida}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
