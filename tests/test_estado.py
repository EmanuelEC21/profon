from datetime import date

from profon.estado import Estado

D = date(2027, 3, 1)


def test_cancelar_idempotente():
    e = Estado(":memory:")
    assert e.cancelar("6A", D, "feriado") is True
    assert e.cancelar("6A", D, "feriado") is False
    assert e.canceladas("6A") == {D}
    assert e.canceladas("9A") == set()


def test_desfazer():
    e = Estado(":memory:")
    e.cancelar("6A", D, "x")
    e.desfazer_cancelamento("6A", D)
    assert e.canceladas("6A") == set()


def test_ajustes():
    e = Estado(":memory:")
    e.definir_ajuste("6A", "6-cronica", 4)
    e.definir_ajuste("6A", "6-cronica", 3)
    assert e.ajustes("6A") == {"6-cronica": 3}
    assert e.ajustes("6B") == {}


def test_questionario_roundtrip():
    e = Estado(":memory:")
    assert e.questionario("6A", "6-cronica#1/6") is None
    e.salvar_questionario("6A", "6-cronica#1/6", ["O que é crônica?", "Cite um autor."])
    assert e.questionario("6A", "6-cronica#1/6") == ["O que é crônica?", "Cite um autor."]


def test_persiste_em_arquivo(tmp_path):
    arq = tmp_path / "p.db"
    e = Estado(arq)
    e.cancelar("6A", D, "x")
    e.fechar()
    assert Estado(arq).canceladas("6A") == {D}
