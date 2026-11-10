# Profon: Assistente de Planejamento para Professor

**Data:** 10/11/2026 · **Status:** aprovado pelo professor em 10/11/2026

---

## 1. Por que existe

O professor ensina Língua Portuguesa, do 1º ao 9º ano do Ensino Fundamental, no Maranhão, e tem TDAH. Ele gasta muito tempo planejando, organizando horários e montando atividades, e acaba perdendo qualidade no que entrega em sala.

O Profon tira da cabeça dele a parte de **lembrar e organizar**. Todo dia de manhã ele recebe, por turma, o assunto do dia, um resumo para estudar e uma atividade pronta para imprimir. Assim a energia dele vai para o ensino.

**O que é sucesso:** o professor chega na escola, abre o Telegram, manda imprimir e dá a aula. Ele não precisa lembrar onde cada turma parou.

## 2. Objetivos, não objetivos e antiobjetivos

**Objetivos**
- Gerar o planejamento mensal de cada turma a partir do calendário escolar, da grade de horários, da BNCC e do DCTM, preenchendo o modelo oficial da escola.
- Enviar todo dia, num horário configurável (padrão 6h), o material de cada turma que tem aula naquele dia.
- Manter uma **fila de conteúdos por turma**, que pode ser remanejada quando uma aula não acontece.
- Avisar quando uma turma estiver atrasando e propor como recuperar.
- Oferecer revisão opcional do material da semana.
- Manter documentação que sirva de mapa do projeto.

**Não objetivos (por enquanto)**
- Atender vários professores, ter login ou cobrança.
- Ter app Android próprio (fica como evolução futura, reaproveitando o mesmo "cérebro").
- Cobrir o Ensino Médio (o DCTM que temos cobre a Educação Infantil e o Fundamental).
- Fazer correção de provas, diário de classe ou controle de notas.

**Antiobjetivos (o que seria fracasso, mesmo funcionando)**
- **Exigir disciplina do professor.** Se for preciso lembrar de alimentar o sistema todo dia, ele falhou. Toda interação deve ser de um toque ou de uma frase.
- **Mandar conteúdo errado com confiança.** Um lembrete desatualizado atrapalha mais do que não ter lembrete.
- **Cortar conteúdo por conveniência.** A preferência é sempre acelerar e agrupar.
- Ter material bonito, mas fraco pedagogicamente, ou desalinhado com a BNCC e o DCTM.

## 3. Restrições

- **Custo baixo:** o projeto é pago do bolso do professor. A meta é ficar abaixo de cerca de R$ 50/mês somando IA e servidor.
- **Funcionar sem o PC dele ligado:** precisa rodar num servidor na nuvem.
- **Material imprimível:** a escola tem impressora e um funcionário que imprime, então PDF chegando de manhã é suficiente.
- **Prazo:** pronto e testado para o início do ano letivo de 2027. As semanas restantes de 2026 servem de piloto.
- **Fontes:** `BNCC.pdf` (600 páginas, legível com `pypdf`) e `DCTMA.pdf`, ambos na raiz do projeto.

## 4. Abordagens consideradas

| Abordagem | Trade-off | Decisão |
|---|---|---|
| **Bot de Telegram + servidor com IA sob demanda** | Grátis, rápido de construir, tem botões e manda arquivos. Exige que o professor use o Telegram | **Escolhida pelo professor** |
| Bot de WhatsApp (API oficial da Meta) | É o app que todos usam, mas exige cadastro empresarial, modelos de mensagem aprovados e custo por conversa. As alternativas não oficiais correm risco de banimento | Descartada por enquanto |
| App Android próprio | Visual sob medida, mas é o maior esforço: app, notificações, tela de conversa e o mesmo servidor por trás | Evolução futura, se escalar |
| E-mail | Trivial, mas ruim para conversar ("hoje não teve aula") | Descartada |

**Princípio da arquitetura:** a IA **não** fica rodando 24 horas. O trabalho pesado (gerar o material) acontece em lote, uma vez por semana. O envio diário não usa IA. A conversa só aciona a IA quando o professor escreve.

## 5. Como funciona (decidido na conversa)

### 5.1 Componentes

```
                ┌───────────────────────────────┐
  Documentos ──►│  Ingestão (1x por ano/bimestre)│  calendário, grade, BNCC, DCTM,
                └──────────────┬────────────────┘  modelo de planejamento, dados admin
                               ▼
                     ┌───────────────────┐
                     │  Banco (SQLite)    │  turmas, aulas, fila por turma,
                     └───┬─────┬─────┬───┘  habilidades, materiais gerados
                         │     │     │
       ┌─────────────────┘     │     └──────────────────┐
       ▼                       ▼                        ▼
┌──────────────┐      ┌────────────────┐      ┌──────────────────┐
│ Gerador (IA) │      │ Agendador      │      │ Conversa (IA)    │
│ semanal      │      │ diário, sem IA │      │ sob demanda      │
└──────┬───────┘      └───────┬────────┘      └────────┬─────────┘
       └──────────────────────┼────────────────────────┘
                              ▼
                       Bot do Telegram ◄──► Professor
```

### 5.2 Fila por turma (regra central)

- Cada turma tem uma sequência ordenada de conteúdos, distribuída pelas aulas reais do calendário.
- **Aula que não aconteceu** (feriado, ponto facultativo, paralisação): o professor avisa ("hoje não teve aula"), o bot pergunta *"Empurro o conteúdo de 5º, 6º e 9º para a próxima aula de cada turma?"* e espera ✅/❌. Na confirmação, **cada turma** passa o conteúdo para a **sua** próxima aula, não para um dia fixo.
- Uma aula também pode ser marcada como não dada de forma parcial ("a turma do 6º não terminou").
- Dias sem aula que já estão no calendário oficial já entram na distribuição desde o início.

### 5.3 Turma atrasada

- Quando a fila de uma turma passa do que cabe até o fim do bimestre, o bot avisa assim que detecta, sem esperar a véspera do fim.
- O bot **propõe acelerar**: conteúdos que podem ser "pincelados" (por exemplo, a classificação silábica no 1º ano) são agrupados e têm o tempo reduzido, juntando atividades.
- Cortar conteúdo é o último recurso, e só para conteúdo pouco aplicável. O professor sempre aprova.

### 5.4 Mensagem da manhã (horário configurável, padrão 6h)

```
☀️ Bom dia! Hoje: 5º, 6º e 9º ano

📚 6º ANO — Crônica  (EF67LP28 · DCTM)
✏️ Para o quadro:
   1. O que é uma crônica?
   2. Onde as crônicas costumam ser publicadas?
   3. ...
📄 resumo-cronica-6ano.pdf
📝 atividade-cronica-6ano.pdf   (só na aula de atividade)
[ Não teve aula hoje ]
...
```

### 5.5 Material de cada aula

1. **Resumo para o professor:** os principais aspectos do conteúdo, autores brasileiros **e maranhenses**, pontos-chave e as fontes consultadas. Serve de revisão rápida, porque o professor já estuda pelas próprias gramáticas.
2. **Questionário de quadro, em toda aula:** poucas perguntas curtas para o professor escrever no quadro e os alunos copiarem e responderem, para fixação. Vem no corpo da mensagem, sem PDF.
3. **Atividade principal, uma vez por conteúdo** (não em toda aula), em PDF, no padrão de **10 questões**:
   - 8 discursivas: 2 fáceis, 4 médias e 2 difíceis;
   - 2 de múltipla escolha, médias;
   - gabarito separado, só para o professor.
4. **Do 6º ano para baixo:** visual mais chamativo, com ilustrações.
5. **1º e 2º ano:** o padrão de 10 questões **não se aplica**. A atividade mistura algumas questões discursivas simples com jogos de palavras (caça-palavras, cruzadinhas e afins, gerados por programa sem custo de IA). O formato segue as orientações da BNCC e do DCTM para essa etapa, combinadas com a preferência do professor.
5. A IA pode pesquisar na internet documentos e atividades parecidas para embasar o material, sempre citando as fontes.
6. As "atividades sugeridas" do DCTM entram como ponto de partida.

### 5.6 Revisão opcional (semanal)

- No domingo à noite o gerador prepara a semana seguinte, e o bot manda: *"Material da semana pronto. Quer revisar?"* [Ver] [Está bom].
- Na revisão, o professor pode pedir ajustes em linguagem natural ("deixa a questão 7 mais fácil", "troca o texto do 9º ano").
- **Se ele não responder, o material sai normalmente de manhã.** A revisão é opcional e nunca bloqueia o envio.

### 5.7 Planejamento mensal e documento oficial

- O professor envia o modelo de planejamento da escola. O Profon preenche os campos pedagógicos e os administrativos (nome, turno, coordenador etc.) com dados guardados uma única vez.
- O planejamento é reaproveitado de um ano para o outro, com uma validação contra mudanças da BNCC ou do DCTM.

### 5.8 Documentação (exigência do professor)

- `CLAUDE.md` na raiz: o mapa curto, com o que é cada parte, onde fica e as regras do projeto. **É lido antes de qualquer mudança.**
- `docs/arquitetura.md`, `docs/decisoes.md`, `docs/guia-do-professor.md`, `docs/instalacao.md`.
- Regra: toda mudança que cria, move ou remove uma parte atualiza o mapa no mesmo passo.

## 6. Escolhas técnicas (decisões do Claude, podem ser corrigidas)

- **Python**, pelo ecossistema de bot e de geração de PDF.
- **API da Claude** para o planejamento, os resumos, as atividades e a conversa. Modelo a escolher por custo e qualidade na fase de plano.
- **SQLite** como banco, num arquivo único.
- **Biblioteca de bot do Telegram** (por exemplo, `python-telegram-bot`) com botões inline.
- **PDF** gerado a partir de HTML ou de templates. Caça-palavras e cruzadinha por algoritmo próprio.
- **Ilustrações:** banco de imagens livres ou serviço de geração de imagem barato, a decidir no plano conforme o custo.
- **Hospedagem:** um serviço barato e sempre ligado na nuvem, com agendamento.
- **Ingestão do DCTM:** extrair do PDF a tabela de Língua Portuguesa (páginas 89 a 184, organizadas por ano, com práticas de linguagem, objetos de conhecimento, habilidades e atividades sugeridas) para o banco, uma única vez, com revisão.

## 7. Custos estimados (a confirmar no plano)

- IA: dezenas de reais por mês, gerando em lote uma vez por semana.
- Servidor: de R$ 0 a R$ 30 por mês.
- Telegram: grátis.

## 8. Fica a critério de quem constrói

- A estrutura exata do banco e das pastas.
- O layout visual dos PDFs, seguindo a regra de mais visual do 6º ano para baixo.
- Como o bot interpreta frases livres. Os comandos e botões cobrem o essencial.
- A estratégia de backup do banco.

## 9. Perguntas feitas ao professor (respondidas na seção 10)

1. **Frequência da atividade de 10 questões:** ela vem em toda aula, ou uma por conteúdo/sequência, com as outras aulas trazendo só o roteiro (explicação, leitura, discussão)?
2. **1º e 2º ano:** o padrão de 10 questões (8 discursivas) se aplica a crianças em alfabetização, ou para elas a atividade é só de jogos e tarefas curtas?

**Decisões do Claude na revisão (podem ser corrigidas):**
- Aulas geminadas (duas seguidas na mesma turma) contam como um bloco, com um material só.
- A grade de horários e as turmas de 2027 entram como dados na ingestão. O design não depende delas.
- Cada material traz o código das habilidades trabalhadas, para facilitar o preenchimento do planejamento e do diário.

## 10. Respostas do professor

1. **Frequência:** a atividade pesada vem uma vez por conteúdo. **Toda aula** traz um questionário curto para o quadro, para fixação (ver 5.5).
2. **1º e 2º ano:** algumas questões discursivas simples e jogos de palavras, seguindo a BNCC. É a preferência dele para Língua Portuguesa.

**Decisões do Claude após as respostas (podem ser corrigidas):**
- O questionário de quadro tem de 3 a 5 perguntas curtas, que dá para copiar em poucos minutos.
- A disciplina fica como um **parâmetro** no sistema, e não fixa no código. O professor quer adaptar para outras disciplinas no futuro, e isso deixa o caminho aberto sem custo agora. Outras disciplinas continuam fora do escopo.
- O `BNCC.pdf` não está corrompido de verdade: uma das ferramentas falhou ao ler, mas outra extraiu as 600 páginas e 391 códigos de habilidade de LP. A seção 3 fica corrigida assim.
