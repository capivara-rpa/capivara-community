"""Testes do cálculo de feriados nacionais brasileiros."""

from datetime import date

from core.control_room import feriados


def test_feriados_fixos():
    for dia in (
        date(2026, 1, 1),
        date(2026, 4, 21),
        date(2026, 5, 1),
        date(2026, 9, 7),
        date(2026, 10, 12),
        date(2026, 11, 2),
        date(2026, 11, 15),
        date(2026, 11, 20),
        date(2026, 12, 25),
    ):
        assert feriados.e_feriado(dia), dia


def test_feriados_moveis_2026():
    assert feriados._pascoa(2026) == date(2026, 4, 5)
    assert feriados.e_feriado(date(2026, 2, 16))  # carnaval
    assert feriados.e_feriado(date(2026, 4, 3))   # sexta-feira santa
    assert feriados.e_feriado(date(2026, 6, 4))   # corpus christi


def test_ano_comum_nao_e_feriado():
    assert not feriados.e_feriado(date(2026, 3, 10))
    assert len(feriados.feriados(2026)) == 12
