"""Habilidades de Língua Portuguesa da BNCC (Ensino Fundamental)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_CODIGO = re.compile(r"\((EF\d{2}LP\d{2})\)")

_FAIXAS = {
    "12": (1, 2),
    "15": (1, 2, 3, 4, 5),
    "35": (3, 4, 5),
    "67": (6, 7),
    "69": (6, 7, 8, 9),
    "89": (8, 9),
}


@dataclass(frozen=True)
class Habilidade:
    codigo: str
    texto: str
    anos: tuple[int, ...]


def anos_do_codigo(codigo: str) -> tuple[int, ...]:
    faixa = codigo[2:4]
    if faixa in _FAIXAS:
        return _FAIXAS[faixa]
    if faixa[0] == "0" and faixa[1] in "123456789":
        return (int(faixa[1]),)
    raise ValueError(f"Código de habilidade com faixa de anos desconhecida: {codigo}")


def extrair_habilidades(texto_pdf: str) -> list[Habilidade]:
    """Extrai habilidades do texto da BNCC.

    O texto de cada habilidade começa logo depois do código e termina na primeira linha
    que fecha com ponto final ou quando aparece o próximo código. As linhas que vêm depois
    pertencem a outras colunas do quadro (objetos de conhecimento) e são descartadas.
    """
    vistos: dict[str, Habilidade] = {}
    marcas = list(_CODIGO.finditer(texto_pdf))
    for i, m in enumerate(marcas):
        codigo = m.group(1)
        if codigo in vistos:
            continue
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto_pdf)
        partes: list[str] = []
        for linha in texto_pdf[m.end():fim].splitlines():
            linha = linha.strip()
            if not linha:
                continue
            partes.append(linha)
            if linha.endswith("."):
                break
        texto = re.sub(r"\s+", " ", " ".join(partes)).strip()
        texto = re.sub(r"(\w)- (\w)", r"\1-\2", texto)  # hífen de quebra de linha: "gráfico- visuais"
        vistos[codigo] = Habilidade(codigo, texto, anos_do_codigo(codigo))
    return list(vistos.values())


def salvar_habilidades(habilidades: list[Habilidade], caminho: Path) -> None:
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(
        json.dumps([asdict(h) for h in habilidades], ensure_ascii=False, indent=1), encoding="utf-8"
    )


def carregar_habilidades(caminho: Path) -> dict[str, Habilidade]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return {d["codigo"]: Habilidade(d["codigo"], d["texto"], tuple(d["anos"])) for d in dados}
