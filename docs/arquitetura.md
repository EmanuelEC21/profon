# Arquitetura

```
  Documentos ──► Ingestão (BNCC → habilidades; sequência por ano revisada pelo professor)
                     │
                     ▼
               config/escola.yaml + data/ + profon.db (SQLite)
                     │
     ┌───────────────┼──────────────────┐
     ▼               ▼                  ▼
 Pré-geração      Envio diário       Conversa
 (domingo 20h,    (horário config.,  (comandos e botões
  usa IA)          sem IA)            no Telegram)
     └───────────────┴──────────────────┘
                     ▼
              Bot do Telegram ◄──► Professor
```

## Ideia central: a agenda é derivada, não armazenada

A agenda de uma turma **não fica salva**. Ela é recalculada sempre a partir de:

1. as **datas de aula**: os dias dentro dos bimestres que caem nos `dias_semana` da turma, tirando os `dias_sem_aula`;
2. as **aulas canceladas** (registradas no SQLite quando o professor diz "não teve aula");
3. a **sequência de conteúdos** do ano, com o número de aulas de cada um, já com os ajustes de compressão aprovados.

Os conteúdos são distribuídos, em ordem, pelas datas que sobraram. Por isso, cancelar uma aula empurra a fila sozinho, e cancelar duas vezes o mesmo dia não empurra de novo.

## Onde a IA entra

- **Uma vez por ano:** o rascunho da sequência de conteúdos de cada ano (`scripts/gerar_sequencia.py`), revisado pelo professor.
- **Toda semana:** os questionários de quadro dos próximos 7 dias, gerados em lote no domingo.
- O envio da manhã **não chama a IA**. Se faltar um questionário, a mensagem sai assim mesmo.
