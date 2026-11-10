"""Planejamento mensal oficial (um PDF por ano escolar), no modelo do NACE.

O conteúdo do mês fica em data/planejamentos/AAAA-MM.yaml. O documento é gerado a partir do arquivo
do mesmo ano no mês anterior (herda formatação, educador e coordenação) e exportado em PDF pelo Word
(scripts/preencher_planejamento.ps1).
"""

from __future__ import annotations

import re
from pathlib import Path

from profon.curriculo import Habilidade

CAMPOS = {  # chave no YAML -> rótulo da linha na tabela do modelo
    "objetivo": "OBJETIVO GERAL",
    "conteudos": "CONTEÚDOS TRABALHADOS",
    "habilidades": "HABILIDADES",
    "metodologias": "METODOLOGIAS",
    "atividades": "ATIVIDADES",
    "avaliacao": "AVALIAÇÃO",
    "recursos": "RECURSOS DIDÁTICOS",
}
_CODIGO = re.compile(r"EF\d{2}LP\d{2}")


def validar_planejamento(dados: dict, habilidades: dict[str, Habilidade]) -> list[str]:
    erros = []
    for ano, campos in dados["anos"].items():
        ano = int(ano)
        for chave in CAMPOS:
            if not campos.get(chave):
                erros.append(f"{ano}º ano: campo {chave} vazio ou ausente.")
        for linha in campos.get("habilidades") or []:
            for codigo in _CODIGO.findall(linha):
                h = habilidades.get(codigo)
                if h is None:
                    erros.append(f"{ano}º ano: habilidade {codigo} não existe na BNCC.")
                elif ano not in h.anos:
                    erros.append(f"{ano}º ano: habilidade {codigo} não é deste ano.")
    return erros


def _modelo_do_ano(raiz: Path, ano: int, pasta_destino: str) -> Path:
    candidatos = []
    for pasta in raiz.iterdir():
        m = re.match(r"(\d+)\s", pasta.name)
        if pasta.is_dir() and m and pasta.name != pasta_destino:
            for arq in pasta.glob(f"* - {ano} ANO - LP.docx"):
                candidatos.append((int(m.group(1)), arq))
    if not candidatos:
        raise FileNotFoundError(f"Nenhum planejamento anterior do {ano} ANO para usar como modelo em {raiz}.")
    return max(candidatos)[1]


def montar_tarefas(dados: dict, raiz: Path) -> list[dict]:
    """Uma tarefa por ano: modelo de origem, arquivos de saída e o texto de cada campo."""
    raiz = Path(raiz)
    tarefas = []
    for ano, campos in sorted(dados["anos"].items(), key=lambda kv: int(kv[0])):
        ano = int(ano)
        nome = f"{dados['mes']} - {ano} ANO - LP"
        destino = raiz / dados["pasta"]
        textos = {}
        for chave, rotulo in CAMPOS.items():
            valor = campos[chave]
            textos[rotulo] = "\n".join(valor) if isinstance(valor, list) else str(valor).strip()
        tarefas.append(
            {
                "modelo": str(_modelo_do_ano(raiz, ano, dados["pasta"])),
                "docx": str(destino / f"{nome}.docx"),
                "pdf": str(destino / f"{nome}.pdf"),
                "copia_pdf": str(raiz / "Por Ano" / f"{ano} ANO" / f"{nome}.pdf"),
                "campos": textos,
            }
        )
    return tarefas
