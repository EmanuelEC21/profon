# Profon: assistente de planejamento de aulas com IA

Bot do Telegram que organiza a rotina de um professor de Língua Portuguesa (1º ao 9º ano, rede pública do Maranhão).
Toda manhã ele envia as turmas do dia, o conteúdo de cada aula e um questionário pronto para o quadro.
Quando uma aula não acontece, ele reorganiza sozinho a fila de conteúdos daquela turma.

**Stack:** Python 3.12 · python-telegram-bot · API Claude (Anthropic) e Gemini (Google) · SQLite · pypdf · fpdf2 · pytest

## O que ele faz

- **Mensagem da manhã:** turmas do dia, conteúdo e questionário, além de uma folha A4 em PDF com o roteiro do professor.
- **Base curricular real:** `scripts/extrair_bncc.py` lê o PDF da BNCC e extrai as **391 habilidades de Língua Portuguesa** que orientam o conteúdo gerado.
- **IA com dois provedores:** Claude ou Gemini, escolhidos por configuração. O código respeita o limite de requisições, usa um modelo reserva quando o principal está sobrecarregado e recebe as respostas em JSON estruturado, já validado.
- **Agenda derivada, não armazenada:** a agenda de cada turma é recalculada a partir das datas letivas, das aulas canceladas e da sequência de conteúdos. Cancelar uma aula empurra a fila automaticamente.
- **Conversa pelo Telegram:** comandos e botões para avisar que "não teve aula" e aprovar ajustes.

## Arquitetura

```
  Documentos ──► Ingestão (BNCC → habilidades; sequência por ano revisada pelo professor)
                     │
                     ▼
               config/escola.yaml + data/ + profon.db (SQLite)
                     │
     ┌───────────────┼──────────────────┐
     ▼               ▼                  ▼
 Pré-geração      Envio diário       Conversa
 (domingo, IA)    (sem IA)           (Telegram)
     └───────────────┴──────────────────┘
                     ▼
              Bot do Telegram ◄──► Professor
```

O envio da manhã **não depende da IA**: o material é gerado antes, em lote. Se a IA falhar, a mensagem sai mesmo assim.
Detalhes em [docs/arquitetura.md](docs/arquitetura.md) e decisões em [docs/decisoes.md](docs/decisoes.md).

## Como rodar

```powershell
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
copy .env.example .env                              # preencha TELEGRAM_TOKEN e a chave da IA
copy config\escola.example.yaml config\escola.yaml  # turmas, horários e bimestres
.venv\Scripts\python -m profon
```

## Testes

Desenvolvido com TDD: são **126 testes** com pytest.

```powershell
.venv\Scripts\python -m pytest
```

## Autor

**Emanuel Carllos**: professor de Língua Portuguesa e estudante de Ciência da Computação.
Projeto feito com desenvolvimento assistido por IA (Claude Code).
