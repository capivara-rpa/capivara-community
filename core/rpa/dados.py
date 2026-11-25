"""Operações com dados (pandas) com cara de low-code.

Tudo loga no terminal e devolve resultados fáceis de usar::

    from core.rpa.dados import ler_csv, escrever_excel, mostrar_df

    df = ler_csv("data/input/clientes.csv")
    mostrar_df(df)
    escrever_excel(df, "data/output/clientes.xlsx")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from rich.console import Console
from rich.table import Table

from core.tratador import ErroRPA

_console = Console()


# ----------------------------------------------------------------------
# Leitura
# ----------------------------------------------------------------------
def ler_csv(caminho: str | Path, separador: str = ",", codificacao: str = "utf-8", **kwargs) -> pd.DataFrame:
    """Lê um arquivo CSV e retorna um DataFrame."""
    caminho = Path(caminho)
    df = pd.read_csv(caminho, sep=separador, encoding=codificacao, **kwargs)
    logger.success(f"CSV lido: {caminho.name} ({len(df)} linhas)")
    return df


def ler_excel(caminho: str | Path, aba: str | int = 0, cabecalho: int = 0, **kwargs) -> pd.DataFrame:
    """Lê uma aba de um arquivo Excel (.xlsx) e retorna um DataFrame."""
    caminho = Path(caminho)
    df = pd.read_excel(caminho, sheet_name=aba, header=cabecalho, **kwargs)
    logger.success(f"Planilha lida: {caminho.name} / aba '{aba}' ({len(df)} linhas)")
    return df


def ler_json(caminho: str | Path, orientacao: str = "records", **kwargs) -> pd.DataFrame:
    """Lê um arquivo JSON e retorna um DataFrame."""
    caminho = Path(caminho)
    df = pd.read_json(caminho, orient=orientacao, **kwargs)
    logger.success(f"JSON lido: {caminho.name} ({len(df)} linhas)")
    return df


def listar_abas_excel(caminho: str | Path) -> list[str]:
    """Lista os nomes das abas de uma planilha Excel."""
    caminho = Path(caminho)
    abas = pd.ExcelFile(caminho).sheet_names
    logger.info(f"Abas encontradas em {caminho.name}: {abas}")
    return abas


# ----------------------------------------------------------------------
# Escrita
# ----------------------------------------------------------------------
def escrever_csv(df: pd.DataFrame, caminho: str | Path, separador: str = ";", codificacao: str = "utf-8-sig", **kwargs) -> Path:
    """Salva um DataFrame como CSV. O separador padrão é ``;`` (Excel BR)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, sep=separador, encoding=codificacao, index=False, **kwargs)
    logger.success(f"CSV salvo: {caminho} ({len(df)} linhas)")
    return caminho


def escrever_excel(df: pd.DataFrame, caminho: str | Path, aba: str = "Dados", **kwargs) -> Path:
    """Salva um DataFrame em uma aba de um arquivo Excel."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(caminho, sheet_name=aba, index=False, **kwargs)
    logger.success(f"Planilha salva: {caminho} / aba '{aba}' ({len(df)} linhas)")
    return caminho


def escrever_planilha(abas: dict[str, pd.DataFrame], caminho: str | Path) -> Path:
    """Salva várias abas em um único arquivo Excel.

    Exemplo: ``escrever_planilha({"Clientes": df1, "Resumo": df2}, caminho)``
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho, engine="openpyxl") as escritor:
        for nome_aba, df in abas.items():
            df.to_excel(escritor, sheet_name=nome_aba[:31], index=False)
    logger.success(f"Planilha com {len(abas)} abas salva: {caminho}")
    return caminho


def escrever_json(df: pd.DataFrame, caminho: str | Path, orientacao: str = "records") -> Path:
    """Salva um DataFrame como JSON."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(caminho, orient=orientacao, force_ascii=False, indent=2)
    logger.success(f"JSON salvo: {caminho}")
    return caminho


# ----------------------------------------------------------------------
# Exploração / visualização
# ----------------------------------------------------------------------
def mostrar_df(df: pd.DataFrame, colunas: list[str] | None = None, n_linhas: int = 10, titulo: str = "DataFrame") -> None:
    """Exibe um DataFrame como uma tabela colorida no terminal."""
    colunas_escolhidas = list(df.columns) if colunas is None else colunas

    tabela = Table(title=titulo, header_style="bold cyan", show_lines=False)
    for coluna in colunas_escolhidas:
        tabela.add_column(str(coluna), no_wrap=False)

    for _, linha in df[colunas_escolhidas].head(n_linhas).iterrows():
        tabela.add_row(*(str(valor) if valor is not None else "" for valor in linha))

    _console.print(tabela)


def resumo_df(df: pd.DataFrame, n_primeiras: int = 10) -> None:
    """Mostra resumo do DataFrame: dimensões, tipos e primeiras linhas."""
    logger.info(f"Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas")

    tabela = Table(title="Tipos das colunas", header_style="bold magenta")
    tabela.add_column("Coluna")
    tabela.add_column("Tipo")
    for coluna in df.columns:
        tabela.add_row(str(coluna), str(df[coluna].dtype))
    _console.print(tabela)

    mostrar_df(df, n_linhas=n_primeiras, titulo="Primeiras linhas")


def listar_colunas(df: pd.DataFrame) -> list[str]:
    """Retorna a lista de colunas do DataFrame."""
    colunas = list(df.columns)
    logger.info(f"Colunas ({len(colunas)}): {colunas}")
    return colunas


def contar_linhas(df: pd.DataFrame) -> int:
    """Retorna a quantidade de linhas do DataFrame."""
    total = len(df)
    logger.info(f"Total de linhas: {total}")
    return total


# ----------------------------------------------------------------------
# Manipulação
# ----------------------------------------------------------------------
def filtrar_linhas(df: pd.DataFrame, condicao: str) -> pd.DataFrame:
    """Filtra linhas usando uma condição em texto (estilo pandas ``query``).

    Exemplo: ``filtrar_linhas(df, "estado == 'SP' and valor_compra > 1000")``
    """
    filtrado = df.query(condicao)
    logger.success(f"Filtro aplicado: {len(filtrado)} de {len(df)} linhas")
    return filtrado


def unir_tabelas(df_esquerda: pd.DataFrame, df_direita: pd.DataFrame, chave: str, como: str = "left") -> pd.DataFrame:
    """Une dois DataFrames por uma chave (join)."""
    unido = pd.merge(df_esquerda, df_direita, on=chave, how=como)
    logger.success(f"União concluída: {len(unido)} linhas (tipo '{como}')")
    return unido


def agrupar_somar(df: pd.DataFrame, por: str, colunas: list[str]) -> pd.DataFrame:
    """Agrupa por uma coluna e soma outras (útil para resumos).

    Exemplo: ``agrupar_somar(df, "estado", ["valor_compra"])``
    """
    agrupado = df.groupby(por, as_index=False)[colunas].sum()
    logger.success(f"Agrupamento por '{por}' concluído: {len(agrupado)} grupos")
    return agrupado


def converter_para_texto(df: pd.DataFrame, separador: str = ";") -> str:
    """Converte o DataFrame para texto (uma linha por registro)."""
    texto = df.to_csv(sep=separador, index=False).rstrip("\n")
    logger.info(f"DataFrame convertido para texto ({len(df)} registros).")
    return texto


# ----------------------------------------------------------------------
# Transformações rápidas
# ----------------------------------------------------------------------
def renomear_colunas(df: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    """Renomeia colunas a partir de ``{nome_atual: nome_novo}``."""
    resultado = df.rename(columns=mapa)
    logger.success(f"Colunas renomeadas: {mapa}")
    return resultado


def remover_duplicados(df: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    """Remove linhas duplicadas (opcionalmente considerando só algumas colunas)."""
    resultado = df.drop_duplicates(subset=colunas, keep="first")
    logger.success(f"Duplicados removidos: {len(df) - len(resultado)} linha(s).")
    return resultado


def preencher_vazios(
    df: pd.DataFrame,
    valor: Any = "",
    metodo: str = "valor",
    colunas: list[str] | None = None,
) -> pd.DataFrame:
    """Preenche valores vazios por valor fixo, ``frente`` (ffill) ou ``tras`` (bfill)."""
    resultado = df.copy()
    alvo = colunas or list(resultado.columns)
    if metodo == "valor":
        resultado[alvo] = resultado[alvo].fillna(valor)
    elif metodo in {"frente", "ffill"}:
        resultado[alvo] = resultado[alvo].ffill()
    elif metodo in {"tras", "bfill"}:
        resultado[alvo] = resultado[alvo].bfill()
    else:
        raise ErroRPA("Método inválido. Use 'valor', 'frente' ou 'tras'.")
    logger.success(f"Valores vazios preenchidos ({metodo}) em {len(alvo)} coluna(s).")
    return resultado


def substituir_valores(
    df: pd.DataFrame,
    substituicoes: dict[Any, Any],
    colunas: list[str] | None = None,
) -> pd.DataFrame:
    """Substitui valores em todo o DataFrame ou em colunas específicas."""
    resultado = df.copy()
    if colunas:
        resultado[colunas] = resultado[colunas].replace(substituicoes)
    else:
        resultado = resultado.replace(substituicoes)
    logger.success(f"Substituições aplicadas: {substituicoes}")
    return resultado


def ordenar_df(df: pd.DataFrame, por: str | list[str], crescente: bool = True) -> pd.DataFrame:
    """Ordena o DataFrame por uma ou mais colunas."""
    resultado = df.sort_values(by=por, ascending=crescente)
    logger.success(f"DataFrame ordenado por {por!r}.")
    return resultado


def selecionar_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Seleciona (e ordena) um subconjunto de colunas."""
    faltantes = [coluna for coluna in colunas if coluna not in df.columns]
    if faltantes:
        raise ErroRPA(f"Colunas não encontradas: {faltantes}")
    return df[colunas]


def dividir_df(df: pd.DataFrame, tamanho: int) -> list[pd.DataFrame]:
    """Divide o DataFrame em partes com ``tamanho`` linhas cada."""
    if tamanho < 1:
        raise ErroRPA("O tamanho da parte precisa ser maior que zero.")
    partes = [df.iloc[inicio : inicio + tamanho] for inicio in range(0, len(df), tamanho)]
    logger.success(f"DataFrame dividido em {len(partes)} parte(s) de até {tamanho} linhas.")
    return partes


def amostrar_df(
    df: pd.DataFrame,
    quantidade: int = 5,
    aleatorio: bool = True,
    semente: int | None = None,
) -> pd.DataFrame:
    """Retorna uma amostra (aleatória ou as primeiras N linhas)."""
    if quantidade < 1:
        raise ErroRPA("A quantidade precisa ser maior que zero.")
    if aleatorio:
        return df.sample(n=min(quantidade, len(df)), random_state=semente)
    return df.head(quantidade)


def resumo_estatistico(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo estatístico das colunas (equivalente a ``df.describe``)."""
    return df.describe(include="all").transpose()


def dataframe_para_markdown(df: pd.DataFrame, index: bool = False) -> str:
    """Converte o DataFrame em uma tabela Markdown (sem depender de tabulate)."""
    colunas = [str(coluna) for coluna in df.columns]
    if index:
        colunas = [str(df.index.name or "")] + colunas
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join("---" for _ in colunas) + " |",
    ]
    for indice, linha in df.iterrows():
        valores = [str(valor).replace("|", "\\|") for valor in linha]
        if index:
            valores = [str(indice)] + valores
        linhas.append("| " + " | ".join(valores) + " |")
    return "\n".join(linhas)


def tratar_datas(
    df: pd.DataFrame,
    colunas: list[str],
    formato: str | None = None,
) -> pd.DataFrame:
    """Converte colunas para data (valores inválidos viram ``NaT``)."""
    resultado = df.copy()
    for coluna in colunas:
        if coluna not in resultado.columns:
            raise ErroRPA(f"Coluna não encontrada: {coluna}")
        resultado[coluna] = pd.to_datetime(resultado[coluna], format=formato, errors="coerce")
    logger.success(f"Datas tratadas em {len(colunas)} coluna(s).")
    return resultado


def calcular_percentual(
    df: pd.DataFrame,
    coluna: str,
    novo_nome: str = "percentual",
) -> pd.DataFrame:
    """Adiciona uma coluna com o percentual de cada linha sobre o total."""
    if coluna not in df.columns:
        raise ErroRPA(f"Coluna não encontrada: {coluna}")
    total = df[coluna].sum()
    if total == 0:
        raise ErroRPA("O total da coluna é zero; não é possível calcular percentual.")
    resultado = df.copy()
    resultado[novo_nome] = (resultado[coluna] / total * 100).round(2)
    logger.success(f"Percentual calculado sobre '{coluna}' em '{novo_nome}'.")
    return resultado


def pivotar(
    df: pd.DataFrame,
    indice: str | list[str],
    colunas: str | list[str],
    valores: str | list[str],
    funcao: str = "sum",
) -> pd.DataFrame:
    """Cria uma tabela dinâmica (pivot)."""
    resultado = df.pivot_table(
        index=indice, columns=colunas, values=valores, aggfunc=funcao
    )
    logger.success("Tabela dinâmica criada.")
    return resultado


def derreter(
    df: pd.DataFrame,
    ids: list[str] | None = None,
    variaveis: list[str] | None = None,
) -> pd.DataFrame:
    """Transforma colunas em linhas (melt), no estilo "wide" -> "long"."""
    resultado = df.melt(id_vars=ids, value_vars=variaveis)
    logger.success(f"DataFrame derretido: {len(resultado)} linha(s).")
    return resultado