# Profon: mapa do projeto

Assistente de planejamento de aulas para um professor de Língua Portuguesa (1º ao 9º ano, Maranhão).
Todo dia de manhã ele envia pelo Telegram as turmas do dia, o conteúdo e um questionário para o quadro.
Também remaneja a fila de cada turma quando uma aula não acontece.

## Regras do projeto

1. **Leia este mapa antes de mexer em qualquer coisa.** Descubra aqui onde fica o que foi pedido e abra só esses arquivos.
2. **Toda mudança que cria, move ou remove um módulo atualiza este mapa no mesmo commit.**
3. Textos para o professor ficam em português do Brasil. O fuso é `America/Fortaleza`.
4. Segredos ficam só no `.env` (veja `.env.example`), nunca no código nem no YAML. **O `.env.example` é só um modelo com valores vazios.** Antes de commitar, confira o que entrou (`git diff --cached`). Nunca use `git add -A` às cegas.
5. TDD: teste primeiro, depois o código.

## Onde está cada coisa

| Caminho | Responsabilidade |
|---|---|
| `profon/config.py` | `Escola`, `Turma`, `Bimestre` e `carregar_escola(yaml)`: dados admin, calendário e grade. Turma multisseriada tem `anos` e `ano` = o mais alto |
| `profon/curriculo.py` | `Habilidade`, `anos_do_codigo`, `extrair_habilidades`, `carregar_habilidades`: habilidades de LP da BNCC |
| `scripts/extrair_bncc.py` | gera `data/curriculo/lp_habilidades.json` a partir do `BNCC.pdf` (391 habilidades) |
| `data/curriculo/lp_habilidades.json` | habilidades extraídas (gerado, versionado) |
| `profon/sequencia.py` | `Conteudo`, `carregar_sequencia`, `validar_sequencia`: sequência de conteúdos por ano |
| `data/sequencias/<N>ano.yaml` | sequência de cada ano (o `6ano.yaml` é exemplo) |
| `scripts/gerar_sequencia.py` | rascunho da sequência de um ano via IA, para o professor revisar |
| `profon/ia.py` | `ClienteIA` (protocolo), `ClienteClaude` (SDK, fallback de recusa), `ClienteGemini` (google-genai), `criar_cliente(provedor, modelo)`, `RecusaIA`, `gerar_questionario` (3 a 5 perguntas) |
| `profon/estado.py` | `Estado` (SQLite): cancelamentos, ajustes de compressão e questionários. Só eventos |
| `profon/agenda.py` | `datas_de_aula`, `montar_agenda` → `AulaPlanejada`, `verificar_atraso` → `Atraso`: agenda derivada e atraso |
| `profon/acoes.py` | `pergunta_sem_aula`, `confirmar_sem_aula`, `atrasos`, `texto_atraso`, `aplicar_compressao`: regras do bot sem Telegram |
| `profon/mensagem.py` | `Contexto`, `aulas_do_dia`, `chave_aula`, `pregerar` (lote semanal) e `compor_mensagens` (texto da manhã, divide acima de 4096) |
| `profon/bot.py` | Telegram: `/start /hoje /amanha /semaula /naoterminou`, texto livre "não teve aula", botões (`sem:*`, `nt:*`, `acel:*`), jobs (envio seg a sex no horário configurado; pré-geração domingo 20h); `criar_app` |
| `profon/__main__.py` | `python -m profon`: `carregar_contexto` (YAML, sequências, BNCC, banco) e polling |
| `docs/guia-do-professor.md` | guia de uso para o professor |
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
