from datetime import date, time

import pytest

from profon.config import Bimestre, Escola, Turma
from profon.estado import Estado
from profon.mensagem import Contexto
from profon.sequencia import Conteudo

SEG1, TER1, SEG2, QUA2 = date(2027, 3, 1), date(2027, 3, 2), date(2027, 3, 8), date(2027, 3, 10)
A = Conteudo("6-a", 6, 1, "Crônica", (), 2, 2)
B = Conteudo("6-b", 6, 1, "Pontuação", (), 2, 1)
C = Conteudo("9-c", 9, 1, "Argumentação", (), 3, 3)


@pytest.fixture
def ctx():
    escola = Escola(
        professor="P", escola="E", coordenador="C", disciplina="Língua Portuguesa",
        horario_envio=time(6), modelo_ia="m", telegram_chat_id=1,
        bimestres=(Bimestre(1, SEG1, date(2027, 3, 12)),),
        dias_sem_aula={date(2027, 3, 3): "feriado"},
        turmas=(Turma("6A", 6, "6º A", "manhã", (0, 2)), Turma("9A", 9, "9º A", "tarde", (0,))),
    )
    return Contexto(escola, {"6ano": [A, B], "9ano": [C]}, Estado(":memory:"))
