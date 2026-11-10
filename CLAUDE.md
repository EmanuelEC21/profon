# Profon: mapa do projeto

Assistente de planejamento de aulas para um professor de Língua Portuguesa (1º ao 9º ano, Maranhão).
Todo dia de manhã ele envia pelo Telegram as turmas do dia, o conteúdo e um questionário para o quadro.
Também remaneja a fila de cada turma quando uma aula não acontece.

## Regras do projeto

1. **Leia este mapa antes de mexer em qualquer coisa.** Descubra aqui onde fica o que foi pedido e abra só esses arquivos.
2. **Toda mudança que cria, move ou remove um módulo atualiza este mapa no mesmo commit.**
3. Textos para o professor ficam em português do Brasil. O fuso é `America/Fortaleza`.
4. Segredos ficam só no `.env` (veja `.env.example`), nunca no código nem no YAML.
5. TDD: teste primeiro, depois o código.

## Onde está cada coisa

| Caminho | Responsabilidade |
|---|---|
| `profon/config.py` | `Escola`, `Turma`, `Bimestre` e `carregar_escola(yaml)`: dados admin, calendário e grade |
| `profon/curriculo.py` | *(a criar, Task 2)* habilidades de LP extraídas da BNCC |
| `profon/sequencia.py` | *(a criar, Task 3)* sequência de conteúdos por ano |
| `profon/ia.py` | *(a criar, Tasks 3 e 7)* cliente da Claude e geração do questionário |
| `profon/estado.py` | *(a criar, Task 4)* SQLite: cancelamentos, ajustes e questionários |
| `profon/agenda.py` | *(a criar, Task 5)* agenda derivada por turma e detecção de atraso |
| `profon/acoes.py` | *(a criar, Task 6)* regras do bot sem Telegram: "não teve aula" e compressão |
| `profon/mensagem.py` | *(a criar, Tasks 6 e 7)* aulas do dia e texto da mensagem da manhã |
| `profon/bot.py`, `profon/__main__.py` | *(a criar, Task 8)* Telegram: comandos, botões e jobs agendados |
| `config/escola.example.yaml` | modelo de configuração (copiar para `config/escola.yaml`) |
| `docs/arquitetura.md` | como as partes conversam |
| `docs/decisoes.md` | o que foi decidido e por quê |
| `docs/design/` | documento de design aprovado |
| `docs/superpowers/plans/` | planos de implementação por fase |

## Comandos

```bash
py -3.12 -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

`BNCC.pdf` e `DCTMA.pdf` ficam na raiz, mas fora do git.
