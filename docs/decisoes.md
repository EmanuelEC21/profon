# Decisões

Registro do que foi decidido e por quê. Detalhes em `docs/design/2026-11-10-profon-design.md`.

| Decisão | Por quê | Quem decidiu |
|---|---|---|
| Canal: bot de Telegram | Grátis, oficial, manda arquivos e tem botões. Um app próprio fica para depois, reaproveitando o mesmo núcleo | Professor |
| A IA trabalha em lote, não 24 horas | Custo baixo. O envio diário não usa IA | Claude |
| Fila por turma, remanejada para a próxima aula **da turma** | As turmas têm dias diferentes | Professor |
| Remanejar só com confirmação ✅/❌ | Evita mudanças erradas | Professor |
| Atraso: acelerar antes de cortar | Cortar conteúdo prejudica os alunos | Professor |
| Mensagem às 6h (configurável) | Ele imprime na escola | Professor |
| Questionário de quadro em toda aula, de 3 a 5 perguntas | Fixação. O tamanho é escolha do Claude | Professor / Claude |
| Atividade de 10 questões uma vez por conteúdo (Fase 2) | 8 discursivas (2 fáceis, 4 médias, 2 difíceis) e 2 de múltipla escolha | Professor |
| 1º e 2º ano: discursivas simples + jogos (Fase 2) | Alfabetização | Professor |
| Revisão semanal opcional, que nunca bloqueia o envio (Fase 2) | Controle sem exigir disciplina | Professor |
| Python 3.12, SQLite e API da Claude | Simples, barato e com boas bibliotecas | Claude |
| Disciplina como parâmetro | Abre caminho para outras disciplinas | Claude |
| Aula geminada conta como um dia | Um material por bloco | Claude |
| Agenda derivada, não armazenada | Remanejamento sempre consistente | Claude |
| PDFs da BNCC e do DCTM fora do git | Arquivos grandes e públicos | Claude |
