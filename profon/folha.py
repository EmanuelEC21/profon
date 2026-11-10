"""Folha A4 do dia, em PDF, para imprimir: por turma, o roteiro do professor e o questionário do quadro.

Gerada em Python com fpdf2, sem Word e sem IA. O texto vem do material já salvo no banco.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

from profon.mensagem import Contexto, _dono, aulas_do_dia, chave_aula

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

# Fontes com acentos e travessão: Arial no Windows; DejaVu ou Liberation no Linux (servidor caseiro).
_FONTES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]
_TROCAS = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-", "…": "..."}


def nome_arquivo(dia: date) -> str:
    return f"aulas-{dia.isoformat()}.pdf"


class _Folha(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=15)
        self.fonte, self.unicode = "Helvetica", False
        for regular, negrito in _FONTES:
            if Path(regular).exists() and Path(negrito).exists():
                self.add_font("Texto", "", regular)
                self.add_font("Texto", "B", negrito)
                self.fonte, self.unicode = "Texto", True
                break

    def t(self, texto: str) -> str:
        """Sem fonte Unicode, troca os símbolos que a fonte padrão (latin-1) não tem."""
        if self.unicode:
            return texto
        for de, para in _TROCAS.items():
            texto = texto.replace(de, para)
        return texto.encode("latin-1", "replace").decode("latin-1")

    def escrever(self, texto: str, tamanho: float = 10.5, negrito: bool = False, altura: float = 5.2) -> None:
        self.set_font(self.fonte, "B" if negrito else "", tamanho)
        self.multi_cell(0, altura, self.t(texto), new_x="LMARGIN", new_y="NEXT")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self.fonte, "", 8)
        self.set_text_color(120)
        self.cell(0, 5, self.t(f"Profon · página {self.page_no()}"), align="R")
        self.set_text_color(0)


def gerar_folha(ctx: Contexto, dia: date) -> bytes | None:
    """PDF do dia, ou None quando não há aula."""
    aulas = aulas_do_dia(ctx, dia)
    if not aulas:
        return None
    pdf = _Folha()
    pdf.add_page()
    pdf.escrever(f"Aulas de {DIAS[dia.weekday()]}, {dia:%d/%m/%Y}", tamanho=16, negrito=True, altura=8)
    pdf.escrever(f"{ctx.escola.disciplina} · {ctx.escola.escola}", tamanho=9, altura=5)
    pdf.ln(2)

    # Turmas com a mesma aula (mesma sequência e mesmo ponto) saem juntas, sem repetir o material.
    grupos: dict[tuple, list] = {}
    for aula in aulas:
        chave = (_dono(ctx, aula), chave_aula(aula)) if aula.conteudo else ("", aula.turma_id)
        grupos.setdefault(chave, []).append(aula)

    for grupo in grupos.values():
        aula = grupo[0]
        if pdf.get_y() > 240:  # não começa uma turma no pé da página
            pdf.add_page()
        pdf.set_draw_color(160)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(2)
        for a in grupo:
            turma = ctx.escola.turma(a.turma_id)
            nome = f"{turma.horario} · {turma.nome}" if turma.horario else turma.nome
            pdf.escrever(nome, tamanho=12.5, negrito=True, altura=6.5)

        if aula.conteudo is None:
            pdf.escrever("Sequência concluída: aula livre ou de revisão.")
            pdf.ln(3)
            continue
        c = aula.conteudo
        codigos = f" · {', '.join(c.habilidades)}" if c.habilidades else ""
        pdf.escrever(f"{c.titulo} — aula {aula.numero} de {aula.total}{codigos}", tamanho=11, negrito=True)
        pdf.ln(1.5)

        material = ctx.estado.material(_dono(ctx, aula), chave_aula(aula))
        if not material:
            pdf.escrever("Roteiro e questionário indisponíveis (o bot tenta de novo às 5h15).")
            pdf.ln(3)
            continue
        if material.get("roteiro"):
            pdf.escrever("Roteiro do professor", negrito=True)
            for i, item in enumerate(material["roteiro"], 1):
                pdf.escrever(f"{i}. {item['topico']}", negrito=True)
                pdf.set_x(20)
                pdf.set_font(pdf.fonte, "", 10)
                pdf.multi_cell(0, 5, pdf.t(item["explicacao"]), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        else:
            pdf.escrever("Roteiro indisponível para esta aula (o bot completa às 5h15).")
        pdf.escrever("Para o quadro", negrito=True)
        for i, pergunta in enumerate(material["perguntas"], 1):
            pdf.escrever(f"{i}. {pergunta}")
        pdf.ln(3)
    return bytes(pdf.output())
