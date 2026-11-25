"""Feriados nacionais brasileiros (para os agendamentos da Lagoa).

Calcula os feriados **nacionais** de um ano sem dependências externas:

- fixos: Confraternização (01/01), Tiradentes (21/04), Dia do Trabalho (01/05),
  Independência (07/09), Nossa Senhora Aparecida (12/10), Finados (02/11),
  Proclamação da República (15/11), Consciência Negra (20/11), Natal (25/12);
- móveis (derivados da Páscoa): Carnaval (48 dias antes), Sexta-feira Santa
  (2 dias antes) e Corpus Christi (60 dias depois).

Uso::

    from core.control_room import feriados

    feriados.e_feriado(date(2026, 1, 1))     # True
    feriados.feriados(2026)                   # {date(...), ...}
"""

from __future__ import annotations

from datetime import date, timedelta

# Feriados de data fixa (mês, dia)
_FIXOS = (
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (11, 20),
    (12, 25),
)

_CACHE: dict[int, set[date]] = {}


def _pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    linha = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * linha) // 451
    mes = (h + linha - 7 * m + 114) // 31
    dia = ((h + linha - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados(ano: int) -> set[date]:
    """Conjunto de feriados nacionais (fixos + móveis) de ``ano``."""
    if ano in _CACHE:
        return _CACHE[ano]
    dias = {date(ano, mes, dia) for mes, dia in _FIXOS}
    pascoa = _pascoa(ano)
    dias.add(pascoa - timedelta(days=48))  # terça de carnaval
    dias.add(pascoa - timedelta(days=2))   # sexta-feira santa
    dias.add(pascoa + timedelta(days=60))  # corpus christi
    _CACHE[ano] = dias
    return dias


def e_feriado(dia: date) -> bool:
    """Diz se ``dia`` é feriado nacional."""
    return dia in feriados(dia.year)


def e_fim_de_semana(dia: date) -> bool:
    """Diz se ``dia`` cai em sábado ou domingo."""
    return dia.isoweekday() >= 6


__all__ = ["feriados", "e_feriado", "e_fim_de_semana"]
