# Guia do professor

## O que o Profon faz por você

- **Todo dia de manhã (segunda a sexta, às 6h)** chega no Telegram uma mensagem com as turmas do dia, o conteúdo de cada uma (com o código da BNCC) e um questionário de 3 a 5 perguntas para passar no quadro.
- **Quando uma aula não acontece**, você avisa e ele empurra o conteúdo de cada turma para a próxima aula **daquela turma**.
- **Se uma turma começar a atrasar**, ele avisa e sugere quais conteúdos dá para acelerar. Você aprova com um toque.
- **No domingo à noite**, ele prepara os questionários da semana. Se algo falhar, ele avisa.

## Configuração (uma vez só)

1. **Crie o bot:** no Telegram, procure **@BotFather**, mande `/newbot`, escolha um nome (ex.: "Profon do Prof. Fulano") e um usuário terminado em `bot`. Ele te devolve um **token**.
2. Copie `.env.example` para `.env` e preencha:
   - `TELEGRAM_TOKEN=` com o token do BotFather;
   - a chave da IA que você escolher (veja "Qual IA usar" abaixo): `ANTHROPIC_API_KEY=` para a Claude ou `GEMINI_API_KEY=` para o Gemini.
3. Copie `config/escola.example.yaml` para `config/escola.yaml` e preencha os seus dados, as datas dos bimestres, os feriados e as suas turmas (e em que dias da semana você dá aula em cada uma).
4. Rode `python -m profon`, abra o seu bot no Telegram e mande `/start`. Ele responde com o seu **chat_id**. Coloque esse número em `telegram_chat_id` no `escola.yaml` e rode de novo.
5. Para cada ano em que você dá aula, gere o rascunho da sequência e **revise**:
   `python scripts/gerar_sequencia.py --ano 6`.
   Abra `data/sequencias/6ano.yaml` e ajuste a ordem, os títulos e as aulas. `aulas_minimas` é o mínimo de aulas se for preciso acelerar. Igual a `aulas` quer dizer que não dá para acelerar aquele conteúdo.

## Qual IA usar

Em `config/escola.yaml`, a linha `provedor_ia` escolhe a IA:

- **`claude`** (padrão): melhor qualidade, mas é paga por uso. A chave é criada em console.anthropic.com.
- **`gemini`**: tem uma **camada gratuita**. A chave é criada em aistudio.google.com, no botão "Get API key".
  - **Atenção:** a assinatura do app Gemini (Google AI Pro, plano para educação) **não inclui a API**. A chave do AI Studio é separada, e a camada gratuita tem limite diário de pedidos. O Profon faz poucos pedidos por semana, então costuma caber.
  - Na camada gratuita, o Google pode usar o conteúdo dos pedidos para melhorar os produtos dele. O Profon só manda conteúdo pedagógico (títulos e habilidades da BNCC), nunca dados de alunos.

Para gerar a sequência com o Gemini: `python scripts/gerar_sequencia.py --ano 6 --provedor gemini`.

## No dia a dia

| Situação | O que fazer |
|---|---|
| Ver as aulas de hoje | `/hoje` |
| Ver as aulas de amanhã | `/amanha` |
| Hoje não teve aula (feriado, ponto facultativo, paralisação) | Toque em **"Não teve aula hoje"** na mensagem da manhã, mande `/semaula`, ou escreva "hoje não teve aula". Depois confirme com ✅ |
| Uma turma não terminou o conteúdo | `/naoterminou`, escolha a turma e confirme ✅ |
| Aviso de atraso | Toque em **"Acelerar …"** no conteúdo que você aceita reduzir, ou ignore |

Nada muda sem o seu ✅.

## Cuidados

- **Mexer na sequência (`data/sequencias/*.yaml`) no meio do ano** muda a agenda desde o começo do ano, porque o Profon recalcula a fila a partir das datas. Se precisar trocar algo, mude **apenas conteúdos que ainda não foram dados**, e sem mudar a ordem nem as aulas dos que já foram.
- **Acelerar** vale só para a turma do aviso e nunca apaga aulas já dadas. Se o conteúdo já começou, ele só corta as aulas que ainda faltam.
- Ao ligar o bot, ele prepara os questionários da semana e verifica atrasos. No domingo à noite faz isso de novo.
