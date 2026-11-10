# Profon Fase 1 — Núcleo: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** um bot de Telegram que, todo dia no horário configurado, envia ao professor as turmas do dia, o conteúdo de cada uma e um questionário de quadro, remaneja a fila de cada turma quando uma aula não acontece e avisa quando uma turma está atrasando.

**Architecture:** a agenda de cada turma é **derivada**, nunca armazenada: a sequência de conteúdos é distribuída pelas datas de aula que sobram depois de tirar os dias sem aula e as aulas canceladas. Por isso, cancelar uma aula empurra a fila automaticamente. A IA (Claude) só gera os questionários, em lote, no domingo à noite. O envio da manhã apenas lê o que já está pronto. O SQLite guarda só os eventos (cancelamentos, ajustes de compressão e questionários).

**Tech Stack:** Python 3.12, `python-telegram-bot[job-queue]` ≥ 21, `anthropic`, `pypdf`, `pyyaml`, `pytest`, SQLite (`sqlite3` da stdlib).

**Spec:** `docs/design/2026-11-10-profon-design.md`

**Fora desta fase:** PDFs de resumo e de atividade, jogos, ilustrações, DCTM, revisão semanal (Fase 2), planejamento oficial e deploy (Fase 3).

## Global Constraints

- Fuso horário fixo: `America/Fortaleza` (Maranhão, UTC−3, sem horário de verão). Toda data "de hoje" usa esse fuso.
- Horário de envio padrão: `06:00`, configurável em `config/escola.yaml`.
- O bot **só responde** ao `telegram_chat_id` configurado. Mensagens de outros chats são ignoradas, sem resposta.
- Segredos (`TELEGRAM_TOKEN`, `ANTHROPIC_API_KEY`) vêm de variáveis de ambiente (arquivo `.env` fora do git), nunca do código ou do YAML.
- A disciplina é um parâmetro (`disciplina: "Língua Portuguesa"` no YAML), e não algo fixo no código.
- Questionário de quadro: **de 3 a 5 perguntas curtas**.
- Remanejar exige confirmação: o bot pergunta *"Empurro o conteúdo de … para a próxima aula de cada turma?"* com ✅/❌ e só cancela no ✅.
- Atraso: o bot propõe **acelerar** (conteúdos com `aulas_minimas < aulas`) e nunca corta conteúdo sozinho. Toda compressão precisa da aprovação do professor.
- O modelo da IA vem da configuração (`modelo_ia`, padrão `claude-sonnet-5-5`). Ao implementar chamadas à API, carregue a skill `claude-api`.
- Toda task que cria, move ou remove um módulo atualiza o mapa em `CLAUDE.md` no mesmo commit.
- Textos voltados ao professor ficam em português do Brasil.

## Review Focus

1. **"Não teve aula" num dia em que o professor não tem aula:** responde *"Você não tem aula registrada hoje."* e não muda nada. (teste em Task 6)
2. **Cancelar o mesmo dia duas vezes:** é idempotente, sem empurrar a fila duas vezes. (teste em Task 4)
3. **A sequência de uma turma acaba antes do ano letivo:** as aulas excedentes aparecem como *"Sequência concluída — aula livre/revisão"*, sem erro. (teste em Task 5)
4. **A API da Claude falha na pré-geração ou não há questionário salvo:** a mensagem da manhã sai mesmo assim, com *"(questionário indisponível hoje)"*. O envio nunca é bloqueado. (teste em Task 7)
5. **Mensagem do dia com mais de 4096 caracteres (limite do Telegram):** é dividida em uma mensagem por turma. (teste em Task 7)

---

## Estrutura de arquivos

```
CLAUDE.md                     mapa do projeto (ler primeiro)
pyproject.toml
.env.example                  TELEGRAM_TOKEN, ANTHROPIC_API_KEY
config/escola.example.yaml    modelo de configuração (dados admin, bimestres, dias sem aula, turmas)
data/curriculo/lp_habilidades.json   gerado pela Task 2
data/sequencias/<N>ano.yaml   sequência de conteúdos por ano (rascunho da IA, revisado pelo professor)
profon/
  config.py        Escola, Turma, Bimestre, carregar_escola
  curriculo.py     Habilidade, extração da BNCC
  sequencia.py     Conteudo, carregar/validar sequência
  agenda.py        datas de aula, agenda derivada, atraso
  estado.py        SQLite: cancelamentos, ajustes, questionários
  ia.py            cliente Claude fino + gerar_questionario
  mensagem.py      aulas do dia + texto da mensagem
  acoes.py         regras do bot sem Telegram (testáveis)
  bot.py           handlers e jobs do Telegram
  __main__.py      python -m profon
scripts/
  extrair_bncc.py      gera data/curriculo/lp_habilidades.json
  gerar_sequencia.py   rascunho de data/sequencias/<N>ano.yaml via IA
tests/
docs/arquitetura.md, docs/guia-do-professor.md, docs/decisoes.md
```

---

### Task 1: Esqueleto do projeto, configuração e mapa

**Files:**
- Create: `pyproject.toml`, `.gitignore` (`.env`, `*.db`, `.venv/`, `__pycache__/`), `.env.example`, `CLAUDE.md`, `docs/arquitetura.md`, `docs/decisoes.md`, `config/escola.example.yaml`, `profon/__init__.py`, `profon/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Bimestre(numero: int, inicio: date, fim: date)`
  - `@dataclass(frozen=True) Turma(id: str, ano: int, nome: str, turno: str, dias_semana: tuple[int, ...])`, com `dias_semana` em 0=segunda … 4=sexta. Aula geminada conta como um dia.
  - `@dataclass(frozen=True) Escola(professor: str, escola: str, coordenador: str, disciplina: str, horario_envio: time, modelo_ia: str, telegram_chat_id: int, bimestres: tuple[Bimestre, ...], dias_sem_aula: dict[date, str], turmas: tuple[Turma, ...])`, com o método `turma(id: str) -> Turma`
  - `carregar_escola(caminho: Path) -> Escola`, que levanta `ValueError` com mensagem em português para bimestres sobrepostos, `dias_semana` fora de 0–4 ou ids de turma duplicados.

- [ ] **Step 1:** `git init`, criar venv com `py -3.12 -m venv .venv` e instalar as dependências do `pyproject.toml` (com extra `dev` = pytest).
- [ ] **Step 2: Write the failing test.** `tests/test_config.py`:
  - `test_carrega_exemplo`: `carregar_escola(Path("config/escola.example.yaml"))` retorna 4 bimestres, `horario_envio == time(6, 0)` e `disciplina == "Língua Portuguesa"`.
  - `test_bimestres_sobrepostos_falha`: um YAML temporário com o bimestre 2 começando antes do fim do 1 levanta `ValueError` com `"sobrep"` na mensagem.
  - `test_turma_por_id`: `escola.turma("6A").ano == 6`.
- [ ] **Step 3:** rodar `pytest tests/test_config.py -v` e conferir que FALHA.
- [ ] **Step 4:** escrever `config/escola.example.yaml` (ano de 2027 fictício, com 4 bimestres, alguns feriados e as turmas `1A`, `5A`, `6A`, `9A`) e implementar `profon/config.py`.
- [ ] **Step 5:** rodar `pytest tests/test_config.py -v` e conferir que PASSA.
- [ ] **Step 6:** escrever o `CLAUDE.md`, com o que é o Profon, a regra "leia este mapa antes de mexer", a tabela módulo → responsabilidade (já com os módulos futuros marcados como *a criar*) e como rodar os testes. Escrever também `docs/arquitetura.md` (o diagrama do spec 5.1 e a ideia de "agenda derivada") e `docs/decisoes.md` (as decisões do spec, seções 4, 6 e 10).
- [ ] **Step 7:** commit `feat: esqueleto do projeto, configuração da escola e mapa`.

### Task 2: Habilidades de LP extraídas da BNCC

**Files:**
- Create: `profon/curriculo.py`, `scripts/extrair_bncc.py`, `data/curriculo/lp_habilidades.json` (gerado)
- Test: `tests/test_curriculo.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Habilidade(codigo: str, texto: str, anos: tuple[int, ...])`
  - `anos_do_codigo(codigo: str) -> tuple[int, ...]`
  - `extrair_habilidades(texto_pdf: str) -> list[Habilidade]`
  - `carregar_habilidades(caminho: Path) -> dict[str, Habilidade]` (chave = código)

O ano sai do próprio código: `EF0N` → (N,); `EF12` → (1, 2); `EF15` → (1..5); `EF35` → (3, 4, 5); `EF67` → (6, 7); `EF69` → (6..9); `EF89` → (8, 9).

- [ ] **Step 1: Write the failing test.**
  - `test_anos_do_codigo`: parametrizado com os 7 padrões acima, por exemplo `anos_do_codigo("EF69LP01") == (6, 7, 8, 9)`.
  - `test_extrai_e_deduplica`: um texto com `"(EF15LP01) Identificar a função\nsocial de textos.\n(EF15LP01) Identificar a função social de textos.\n(EF01LP02) Escrever palavras."` gera 2 habilidades, e a primeira tem `texto == "Identificar a função social de textos."` (quebras de linha viram espaço e o texto termina no próximo código).
  - `test_codigo_desconhecido_falha`: `anos_do_codigo("EF99LP01")` levanta `ValueError`.
- [ ] **Step 2:** rodar o teste e conferir que FALHA.
- [ ] **Step 3:** implementar `profon/curriculo.py`. Regex `\((EF\d{2}LP\d{2})\)`. O texto vai até o próximo código ou até um cabeçalho de quadro. Prevalece a primeira ocorrência de cada código.
- [ ] **Step 4:** rodar o teste e conferir que PASSA.
- [ ] **Step 5:** `scripts/extrair_bncc.py BNCC.pdf data/curriculo/lp_habilidades.json`. Ler com `pypdf.PdfReader(strict=False)` (o poppler falha nesse arquivo). Verificação: rodar e conferir que imprime pelo menos `380` habilidades únicas (a BNCC tem 391 códigos LP do EF) e que `EF67LP28` está presente.
- [ ] **Step 6:** atualizar o `CLAUDE.md` e fazer o commit `feat: extração das habilidades de LP da BNCC`.

### Task 3: Sequência de conteúdos por ano

**Files:**
- Create: `profon/sequencia.py`, `profon/ia.py` (só `ClienteIA`), `scripts/gerar_sequencia.py`, `data/sequencias/6ano.yaml` (exemplo revisado à mão para os testes)
- Test: `tests/test_sequencia.py`

**Interfaces:**
- Consumes: `Habilidade`, `carregar_habilidades` (Task 2).
- Produces:
  - `@dataclass(frozen=True) Conteudo(id: str, ano: int, bimestre: int, titulo: str, habilidades: tuple[str, ...], aulas: int, aulas_minimas: int)`, onde `compressivel` é uma property que vale `aulas_minimas < aulas`.
  - `carregar_sequencia(caminho: Path) -> list[Conteudo]`, que mantém a ordem do arquivo.
  - `validar_sequencia(conteudos: list[Conteudo], habilidades: dict[str, Habilidade]) -> list[str]`, que lista problemas em português: código inexistente, habilidade de outro ano, `aulas_minimas > aulas`, `aulas < 1`, bimestre fora de 1–4 ou bimestres fora de ordem.
  - `class ClienteIA(Protocol): def completar(self, sistema: str, mensagem: str) -> str`, mais `ClienteClaude(modelo: str)` implementando com `anthropic`.

Formato YAML:
```yaml
ano: 6
conteudos:
  - id: 6-cronica
    bimestre: 1
    titulo: Crônica
    habilidades: [EF67LP28]
    aulas: 6
    aulas_minimas: 4
```

- [ ] **Step 1: Write the failing test.** `test_carrega_em_ordem`, `test_valida_codigo_inexistente` (`"EF67LP99"` gera um erro que contém `"EF67LP99"`), `test_valida_ano_errado` (`EF01LP02` numa sequência do 6º ano gera erro), `test_compressivel` (6/4 é `True` e 3/3 é `False`).
- [ ] **Step 2:** rodar e conferir que FALHA. **Step 3:** implementar. **Step 4:** rodar e conferir que PASSA.
- [ ] **Step 5:** `scripts/gerar_sequencia.py --ano N --habilidades data/curriculo/lp_habilidades.json --saida data/sequencias/Nano.yaml`. O script pede à IA uma sequência para os 4 bimestres cobrindo as habilidades do ano, com títulos de conteúdo do jeito que o professor fala ("Crônica", "Classificação silábica") e uma estimativa de aulas e de aulas mínimas, roda `validar_sequencia` e grava o rascunho com o cabeçalho `# RASCUNHO — revisar antes de usar`. Verificação manual: rodar para `--ano 6` e abrir o arquivo.
- [ ] **Step 6:** atualizar o `CLAUDE.md` e fazer o commit `feat: sequência de conteúdos por ano`.

### Task 4: Estado em SQLite

**Files:**
- Create: `profon/estado.py`
- Test: `tests/test_estado.py`

**Interfaces:**
- Produces a `class Estado`, com:
  - `__init__(self, caminho: Path | str)`, que cria as tabelas se não existirem (`":memory:"` nos testes);
  - `cancelar(turma_id: str, data: date, motivo: str) -> bool` (False se já estava cancelada);
  - `canceladas(turma_id: str) -> set[date]`;
  - `desfazer_cancelamento(turma_id: str, data: date) -> None`;
  - `definir_ajuste(conteudo_id: str, aulas: int) -> None` e `ajustes() -> dict[str, int]`;
  - `salvar_questionario(turma_id: str, data: date, perguntas: list[str]) -> None` e `questionario(turma_id: str, data: date) -> list[str] | None`.

- [ ] **Step 1: Write the failing test.** `test_cancelar_idempotente` (o segundo `cancelar` retorna `False` e `canceladas` tem 1 item), `test_desfazer`, `test_ajustes`, `test_questionario_roundtrip` e `test_persiste_em_arquivo` (fechar, reabrir em `tmp_path` e os dados continuam lá).
- [ ] **Step 2:** FALHA. **Step 3:** implementar (tabelas `cancelamentos(turma_id, data, motivo, PK(turma_id, data))`, `ajustes(conteudo_id PK, aulas)` e `questionarios(turma_id, data, perguntas_json, PK)`). **Step 4:** PASSA.
- [ ] **Step 5:** commit `feat: estado persistente em SQLite`.

### Task 5: Agenda derivada e detecção de atraso

**Files:**
- Create: `profon/agenda.py`
- Test: `tests/test_agenda.py`

**Interfaces:**
- Consumes: `Escola`, `Turma`, `Bimestre` (Task 1) e `Conteudo` (Task 3).
- Produces:
  - `datas_de_aula(escola: Escola, turma: Turma) -> list[date]`: todas as datas dentro dos bimestres que caem num dia de `turma.dias_semana` e não estão em `escola.dias_sem_aula`, em ordem.
  - `@dataclass(frozen=True) AulaPlanejada(turma_id: str, data: date, conteudo: Conteudo | None, numero: int, total: int)`, onde `conteudo=None` significa sequência concluída.
  - `montar_agenda(escola, turma, conteudos: list[Conteudo], canceladas: set[date], ajustes: dict[str, int]) -> list[AulaPlanejada]`: tira as `canceladas` das datas e expande cada conteúdo em `ajustes.get(id, aulas)` aulas, na ordem. As datas que sobram recebem `conteudo=None`.
  - `@dataclass(frozen=True) Atraso(turma_id: str, bimestre: int, aulas_necessarias: int, aulas_disponiveis: int, sugestoes: tuple[Conteudo, ...])`
  - `verificar_atraso(escola, turma, conteudos, canceladas, ajustes, hoje: date) -> Atraso | None`: no bimestre de `hoje`, compara as aulas que faltam para os conteúdos daquele bimestre que ainda não terminaram com as datas restantes até `bimestre.fim`. Se faltar espaço, `sugestoes` traz os conteúdos compressíveis ainda não iniciados daquele bimestre, os maiores ganhos primeiro (`aulas - aulas_minimas`).

- [ ] **Step 1: Write the failing test.** Fixture: um bimestre de 2 semanas, turma com aula na seg e na qua, um feriado na qua da 1ª semana, conteúdos A (2 aulas) e B (2 aulas, mínimo 1).
  - `test_datas_excluem_feriado`: 3 datas.
  - `test_cancelar_empurra_fila`: cancelar a 1ª segunda-feira faz A ocupar as 2 datas seguintes e B sair do bimestre.
  - `test_sequencia_concluida`: com só o conteúdo A, a 3ª data tem `conteudo is None`.
  - `test_atraso_sugere_compressivel`: depois do cancelamento, `verificar_atraso` retorna `aulas_necessarias == 4`, `aulas_disponiveis == 2` e `sugestoes == (B,)`.
  - `test_ajuste_resolve_atraso`: com `ajustes={"A": 1, "B": 1}`, retorna `None`.
- [ ] **Step 2:** FALHA. **Step 3:** implementar. **Step 4:** PASSA.
- [ ] **Step 5:** commit `feat: agenda derivada por turma e alerta de atraso`.

### Task 6: Regras do bot (sem Telegram)

**Files:**
- Create: `profon/mensagem.py` (só `aulas_do_dia`), `profon/acoes.py`
- Test: `tests/test_acoes.py`

**Interfaces:**
- Consumes: `montar_agenda`, `verificar_atraso`, `AulaPlanejada`, `Atraso` (Task 5) e `Estado` (Task 4).
- Produces:
  - `@dataclass Contexto(escola: Escola, sequencias: dict[int, list[Conteudo]], estado: Estado)`, onde a chave das sequências é o ano.
  - `aulas_do_dia(ctx: Contexto, dia: date) -> list[AulaPlanejada]`, em ordem de turma.
  - `turmas_do_dia(ctx, dia) -> list[Turma]`.
  - `pergunta_sem_aula(ctx, dia) -> str | None`: devolve `None` quando não há turmas no dia. Caso contrário, devolve *"Hoje não teve aula com 5º A, 6º A e 9º A? Empurro o conteúdo de cada turma para a próxima aula dela?"*.
  - `confirmar_sem_aula(ctx, dia, motivo: str, turmas: list[str] | None = None) -> list[str]`: cancela as turmas indicadas, ou todas as do dia quando `None` (cobre o caso do spec 5.2 "a turma do 6º não terminou") (de forma idempotente) e devolve as mensagens de resposta. A primeira é a confirmação com o novo conteúdo da próxima aula de cada turma. Em seguida vem uma mensagem por `Atraso` detectado, listando as sugestões *"acelerar Crônica de 6 para 4 aulas"*.
  - `aplicar_compressao(ctx, conteudo_id: str) -> str`: define o ajuste para `aulas_minimas` e confirma.

- [ ] **Step 1: Write the failing test.** `test_sem_aula_em_dia_livre` retorna `None`, e a resposta do bot (Task 8) usa *"Você não tem aula registrada hoje."*. `test_confirmar_cancela_e_informa_proximo`, `test_confirmar_duas_vezes_nao_empurra_de_novo` (as agendas ficam idênticas depois da segunda chamada), `test_confirmar_so_uma_turma` (`turmas=["6A"]` cancela só o 6A), `test_alerta_de_atraso_aparece` e `test_aplicar_compressao`.
- [ ] **Step 2:** FALHA. **Step 3:** implementar. **Step 4:** PASSA.
- [ ] **Step 5:** commit `feat: regras de aula cancelada, atraso e compressão`.

### Task 7: Questionário de quadro e mensagem da manhã

**Files:**
- Modify: `profon/ia.py` (add `gerar_questionario`), `profon/mensagem.py` (add `compor_mensagens`, `pregerar`)
- Test: `tests/test_questionario.py`, `tests/test_mensagem.py`

**Interfaces:**
- Consumes: `ClienteIA` (Task 3), `Contexto`, `aulas_do_dia` (Task 6) e `Habilidade` (Task 2).
- Produces:
  - `gerar_questionario(cliente: ClienteIA, aula: AulaPlanejada, ano: int, habilidades: dict[str, Habilidade]) -> list[str]`: o prompt pede de 3 a 5 perguntas curtas para copiar no quadro, adequadas ao ano, focadas na aula `numero/total` do conteúdo, com uma pergunta por linha. Se a resposta não tiver entre 3 e 5 itens, tenta mais uma vez e depois levanta `ValueError`.
  - `pregerar(ctx: Contexto, cliente: ClienteIA, habilidades, inicio: date, dias: int = 7) -> list[str]`: gera e salva os questionários das aulas com conteúdo no período, pulando as que já existem. Devolve a lista de falhas em português e **não** levanta exceção.
  - `compor_mensagens(ctx: Contexto, dia: date) -> list[str]`: a primeira mensagem é o cabeçalho *"☀️ Bom dia! Hoje: 5º A, 6º A e 9º A"* seguido de um bloco por turma (`📚 6º A — Crônica (aula 2 de 6) · EF67LP28` + `✏️ Para o quadro:` + perguntas numeradas, ou *"(questionário indisponível hoje)"*). Se o texto total passar de 4096 caracteres, vira uma mensagem por turma. Sem aulas no dia, devolve `[]`.

- [ ] **Step 1: Write the failing test.** Com um `ClienteFalso` que devolve um texto fixo: `test_questionario_3_a_5`, `test_questionario_resposta_ruim_tenta_de_novo` (o falso responde 1 linha e depois 4 linhas, então são 2 chamadas e 4 itens), `test_pregerar_falha_nao_explode` (o falso levanta exceção e o resultado tem 1 falha), `test_mensagem_sem_questionario` (contém `"questionário indisponível hoje"`), `test_mensagem_longa_divide` (perguntas gigantes geram 1 mensagem por turma, todas com ≤ 4096) e `test_sequencia_concluida_na_mensagem` (contém `"Sequência concluída"`).
- [ ] **Step 2:** FALHA. **Step 3:** implementar. **Step 4:** PASSA.
- [ ] **Step 5:** commit `feat: questionário de quadro e mensagem da manhã`.

### Task 8: Bot do Telegram e execução

**Files:**
- Create: `profon/bot.py`, `profon/__main__.py`, `docs/guia-do-professor.md`
- Test: `tests/test_bot.py`

**Interfaces:**
- Consumes: tudo de `acoes.py` e `mensagem.py`.
- Produces: `criar_app(ctx: Contexto, cliente: ClienteIA, habilidades, token: str) -> telegram.ext.Application`, com:
  - `/start`: apresentação e lista de comandos;
  - `/hoje`: envia `compor_mensagens(hoje)`;
  - `/amanha`: o mesmo para amanhã;
  - `/naoterminou`: mostra um botão por turma do dia e, ao escolher, pergunta ✅/❌ e chama `confirmar_sem_aula(..., turmas=[id])`;
  - `/semaula [motivo]`, o botão **"Não teve aula hoje"** anexado à mensagem da manhã ou um texto livre que contenha "não teve aula": chama `pergunta_sem_aula` e mostra os botões ✅ Sim / ❌ Não. O ✅ chama `confirmar_sem_aula` e envia as respostas, e as mensagens de atraso trazem um botão "Acelerar <título>" por sugestão, que chama `aplicar_compressao`;
  - job diário no `escola.horario_envio` (fuso `America/Fortaleza`), de segunda a sexta, que envia `compor_mensagens(hoje)` quando há aulas;
  - job no domingo às 20:00, que roda `pregerar` para os 7 dias seguintes e avisa o professor só se houver falhas;
  - filtro de chat: só `escola.telegram_chat_id`.
- `python -m profon` lê o `.env`, `config/escola.yaml`, `data/sequencias/*.yaml`, `data/curriculo/lp_habilidades.json` e `profon.db`, e inicia o polling.

- [ ] **Step 1: Write the failing test.** Testar as funções de handler com objetos falsos de `Update`/`Context` (sem rede): `test_chat_estranho_ignorado` (nenhuma resposta), `test_semaula_sem_aulas_responde_aviso` (*"Você não tem aula registrada hoje."*) e `test_callback_sim_cancela` (o estado registra o cancelamento).
- [ ] **Step 2:** FALHA. **Step 3:** implementar `bot.py` e `__main__.py`. **Step 4:** PASSA, e a suíte inteira com `pytest -v` também PASSA.
- [ ] **Step 5: Verificação manual com o professor.** Ele cria o bot no @BotFather, coloca o token no `.env` e manda `/start`. Rodar `python -m profon` e conferir que `/hoje` responde, que `/semaula` mostra os botões e que o ✅ remaneja.
- [ ] **Step 6:** escrever `docs/guia-do-professor.md` em linguagem simples (como criar o bot, os comandos e o que fazer quando não tiver aula), atualizar o `CLAUDE.md` com todos os módulos e fazer o commit `feat: bot do Telegram com envio diário e remanejamento`.
