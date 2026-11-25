"""Validações e formatos brasileiros (CPF, CNPJ, CEP, telefone, datas, moeda).

Tudo em português e sem dependência externa::

    from core.rpa import validacao

    validacao.validar_cpf("529.982.247-25")       # True
    validacao.formatar_cnpj("11222333000181")     # '11.222.333/0001-81'
    validacao.adicionar_dias_uteis("2026-01-02", 5)
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from loguru import logger

from core.tratador import ErroRPA

_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_FORMATOS_DATA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y")


def limpar_digitos(valor: str | int) -> str:
    """Remove tudo que não for dígito."""
    return re.sub(r"\D", "", str(valor))


# ----------------------------------------------------------------------
# CPF / CNPJ
# ----------------------------------------------------------------------
def _digito_cpf(digitos: str, posicao: int) -> int:
    soma = sum(int(digitos[indice]) * (posicao + 1 - indice) for indice in range(posicao))
    return (soma * 10 % 11) % 10


def validar_cpf(cpf: str | int) -> bool:
    """Valida um CPF (com ou sem pontuação)."""
    digitos = limpar_digitos(cpf)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    valido = all(_digito_cpf(digitos, posicao) == int(digitos[posicao]) for posicao in (9, 10))
    logger.debug(f"CPF válido? {valido}")
    return valido


def formatar_cpf(cpf: str | int) -> str:
    """Formata um CPF como ``000.000.000-00``."""
    digitos = limpar_digitos(cpf)
    if len(digitos) != 11:
        raise ErroRPA(f"CPF precisa ter 11 dígitos: {cpf!r}")
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def gerar_cpf(formatar: bool = True) -> str:
    """Gera um CPF válido (útil para testes e massa de dados)."""
    import secrets

    while True:
        base = "".join(str(secrets.randbelow(10)) for _ in range(9))
        if len(set(base)) == 1:
            continue
        primeiro = _digito_cpf(base, 9)
        segundo = _digito_cpf(base + str(primeiro), 10)
        cpf = base + str(primeiro) + str(segundo)
        if validar_cpf(cpf):
            return formatar_cpf(cpf) if formatar else cpf


def _digito_cnpj(digitos: str, pesos: list[int]) -> int:
    soma = sum(int(digito) * peso for digito, peso in zip(digitos, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validar_cnpj(cnpj: str | int) -> bool:
    """Valida um CNPJ (com ou sem pontuação)."""
    digitos = limpar_digitos(cnpj)
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False
    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_2 = [6, *pesos_1]
    primeiro = _digito_cnpj(digitos[:12], pesos_1)
    segundo = _digito_cnpj(digitos[:12] + str(primeiro), pesos_2)
    valido = digitos[-2:] == f"{primeiro}{segundo}"
    logger.debug(f"CNPJ válido? {valido}")
    return valido


def formatar_cnpj(cnpj: str | int) -> str:
    """Formata um CNPJ como ``00.000.000/0000-00``."""
    digitos = limpar_digitos(cnpj)
    if len(digitos) != 14:
        raise ErroRPA(f"CNPJ precisa ter 14 dígitos: {cnpj!r}")
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def gerar_cnpj(formatar: bool = True) -> str:
    """Gera um CNPJ válido (útil para testes e massa de dados)."""
    import secrets

    while True:
        base = "".join(str(secrets.randbelow(10)) for _ in range(8)) + "0001"
        if len(set(base)) == 1:
            continue
        pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos_2 = [6, *pesos_1]
        primeiro = _digito_cnpj(base, pesos_1)
        segundo = _digito_cnpj(base + str(primeiro), pesos_2)
        cnpj = base + str(primeiro) + str(segundo)
        if validar_cnpj(cnpj):
            return formatar_cnpj(cnpj) if formatar else cnpj


def validar_cpf_ou_cnpj(documento: str | int) -> bool:
    """Valida automaticamente como CPF (11 dígitos) ou CNPJ (14 dígitos)."""
    digitos = limpar_digitos(documento)
    if len(digitos) == 11:
        return validar_cpf(digitos)
    if len(digitos) == 14:
        return validar_cnpj(digitos)
    return False


def formatar_documento(documento: str | int) -> str:
    """Formata como CPF ou CNPJ conforme a quantidade de dígitos."""
    digitos = limpar_digitos(documento)
    if len(digitos) == 11:
        return formatar_cpf(digitos)
    if len(digitos) == 14:
        return formatar_cnpj(digitos)
    raise ErroRPA(f"Documento precisa ter 11 (CPF) ou 14 (CNPJ) dígitos: {documento!r}")


# ----------------------------------------------------------------------
# CEP / telefone / e-mail
# ----------------------------------------------------------------------
def validar_cep(cep: str | int) -> bool:
    """Valida um CEP brasileiro (8 dígitos, diferente de 00000000)."""
    digitos = limpar_digitos(cep)
    valido = len(digitos) == 8 and digitos != "00000000"
    logger.debug(f"CEP válido? {valido}")
    return valido


def formatar_cep(cep: str | int) -> str:
    """Formata um CEP como ``00000-000``."""
    digitos = limpar_digitos(cep)
    if len(digitos) != 8:
        raise ErroRPA(f"CEP precisa ter 8 dígitos: {cep!r}")
    return f"{digitos[:5]}-{digitos[5:]}"


def validar_telefone_br(telefone: str | int) -> bool:
    """Valida telefone brasileiro com DDD (fixo com 10 ou celular com 11 dígitos)."""
    digitos = limpar_digitos(telefone)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11):
        return False
    ddd = int(digitos[:2])
    if not 11 <= ddd <= 99:
        return False
    numero = digitos[2:]
    if len(numero) == 9:
        return numero.startswith("9")
    return numero[0] in "2345"


def formatar_telefone_br(telefone: str | int) -> str:
    """Formata telefone como ``(11) 98765-4321`` ou ``(11) 3456-7890``."""
    if not validar_telefone_br(telefone):
        raise ErroRPA(f"Telefone brasileiro inválido: {telefone!r}")
    digitos = limpar_digitos(telefone)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    ddd, numero = digitos[:2], digitos[2:]
    if len(numero) == 9:
        return f"({ddd}) {numero[:5]}-{numero[5:]}"
    return f"({ddd}) {numero[:4]}-{numero[4:]}"


def validar_email(email: str) -> bool:
    """Valida o formato de um e-mail."""
    valido = bool(_EMAIL.match(str(email).strip()))
    logger.debug(f"E-mail válido? {valido}")
    return valido


# ----------------------------------------------------------------------
# Datas
# ----------------------------------------------------------------------
def _para_data(valor: str | date | datetime) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in _FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErroRPA(f"Data inválida: {valor!r}. Use, por exemplo, '31/12/2026'.")


def validar_data(data: str | date | datetime, formato: str = "%d/%m/%Y") -> bool:
    """Diz se o texto representa uma data válida no formato informado."""
    if isinstance(data, (date, datetime)):
        return True
    try:
        datetime.strptime(str(data).strip(), formato)
        return True
    except ValueError:
        return False


def converter_data(
    data: str | date | datetime,
    de: str = "%d/%m/%Y",
    para: str = "%Y-%m-%d",
) -> str:
    """Converte uma data entre formatos (ou de ``date`` para texto)."""
    if isinstance(data, datetime):
        return data.strftime(para)
    if isinstance(data, date):
        return data.strftime(para)
    try:
        convertida = datetime.strptime(str(data).strip(), de)
    except ValueError as erro:
        raise ErroRPA(f"Data {data!r} não está no formato {de!r}.") from erro
    return convertida.strftime(para)


def formatar_data_br(data: str | date | datetime) -> str:
    """Formata qualquer data aceita para ``dd/mm/aaaa``."""
    return _para_data(data).strftime("%d/%m/%Y")


def _e_dia_util(dia: date, feriados: set[date] | None) -> bool:
    return dia.weekday() < 5 and (feriados is None or dia not in feriados)


def adicionar_dias_uteis(
    data: str | date | datetime,
    dias: int,
    feriados: set[date] | None = None,
) -> date:
    """Soma (ou subtrai) dias úteis, pulando fins de semana e feriados."""
    atual = _para_data(data)
    if dias == 0:
        return atual
    passo = 1 if dias > 0 else -1
    restantes = abs(dias)
    while restantes:
        atual += timedelta(days=passo)
        if _e_dia_util(atual, feriados):
            restantes -= 1
    return atual


def dias_uteis_entre(
    inicio: str | date | datetime,
    fim: str | date | datetime,
    feriados: set[date] | None = None,
) -> int:
    """Conta dias úteis entre duas datas (início incluso, fim excluso)."""
    inicio_data, fim_data = _para_data(inicio), _para_data(fim)
    if inicio_data > fim_data:
        return -dias_uteis_entre(fim_data, inicio_data, feriados)
    total = 0
    atual = inicio_data
    while atual < fim_data:
        if _e_dia_util(atual, feriados):
            total += 1
        atual += timedelta(days=1)
    return total


def proximo_dia_util(
    data: str | date | datetime,
    feriados: set[date] | None = None,
) -> date:
    """Retorna o próximo dia útil depois da data informada."""
    atual = _para_data(data) + timedelta(days=1)
    while not _e_dia_util(atual, feriados):
        atual += timedelta(days=1)
    return atual


def idade(data_nascimento: str | date | datetime, referencia: str | date | datetime | None = None) -> int:
    """Calcula a idade em anos completos."""
    nascimento = _para_data(data_nascimento)
    hoje = _para_data(referencia) if referencia else date.today()
    if nascimento > hoje:
        raise ErroRPA("A data de nascimento não pode ser futura.")
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))


# ----------------------------------------------------------------------
# Moeda
# ----------------------------------------------------------------------
def formatar_moeda_br(valor: float | int) -> str:
    """Formata um número como moeda brasileira: ``R$ 1.234,56``."""
    try:
        numero = float(valor)
    except (TypeError, ValueError) as erro:
        raise ErroRPA(f"Valor monetário inválido: {valor!r}") from erro
    sinal = "-" if numero < 0 else ""
    texto = f"{abs(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sinal}R$ {texto}"


def converter_moeda_br(texto: str | float | int) -> float:
    """Converte ``'R$ 1.234,56'`` para ``1234.56``."""
    if isinstance(texto, (int, float)):
        return float(texto)
    limpo = str(texto).replace("R$", "").replace(" ", "").strip()
    negativo = (limpo.startswith("(") and limpo.endswith(")")) or limpo.startswith("-")
    limpo = limpo.strip("()-")
    if not limpo:
        raise ErroRPA(f"Valor monetário inválido: {texto!r}")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        numero = float(limpo)
    except ValueError as erro:
        raise ErroRPA(f"Valor monetário inválido: {texto!r}") from erro
    return -numero if negativo else numero


__all__ = [
    "limpar_digitos",
    "validar_cpf",
    "formatar_cpf",
    "gerar_cpf",
    "validar_cnpj",
    "formatar_cnpj",
    "gerar_cnpj",
    "validar_cpf_ou_cnpj",
    "formatar_documento",
    "validar_cep",
    "formatar_cep",
    "validar_telefone_br",
    "formatar_telefone_br",
    "validar_email",
    "validar_data",
    "converter_data",
    "formatar_data_br",
    "adicionar_dias_uteis",
    "dias_uteis_entre",
    "proximo_dia_util",
    "idade",
    "formatar_moeda_br",
    "converter_moeda_br",
]
