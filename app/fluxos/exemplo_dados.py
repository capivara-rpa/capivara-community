"""Fluxo de exemplo: tratamento de dados com pandas.

Mostra as funções low-code do módulo ``core.rpa.dados``:
ler CSV, visualizar, filtrar, gerar resumos e exportar Excel.
"""

from core.rpa.dados import (
    escrever_planilha,
    escrever_csv,
    filtrar_linhas,
    ler_csv,
    mostrar_df,
    resumo_df,
)
from settings.parametros import PASTA_INPUT, PASTA_OUTPUT

ARQUIVO_ENTRADA = PASTA_INPUT / "clientes_exemplo.csv"
ARQUIVO_SAIDA = PASTA_OUTPUT / "relatorio_clientes.xlsx"
ARQUIVO_SAIDA_CSV = PASTA_OUTPUT / "clientes_sp.csv"


def tratar_planilha(navegador=None) -> bool:
    """Lê uma planilha, filtra por estado e gera relatórios."""
    # 1. Ler o CSV de exemplo
    dados = ler_csv(ARQUIVO_ENTRADA)

    # 2. Visualizar os dados carregados
    mostrar_df(dados, titulo="Clientes (original)")
    resumo_df(dados)

    # 3. Filtrar somente clientes de São Paulo
    dados_sp = filtrar_linhas(dados, "estado == 'SP'")
    mostrar_df(dados_sp, n_linhas=20, titulo="Somente São Paulo")

    # 4. Resumo agrupado por cidade
    resumo_por_cidade = (
        dados_sp.groupby("cidade")
        .agg(quantidade=("id", "count"), total_compra=("valor_compra", "sum"))
        .reset_index()
    )
    mostrar_df(resumo_por_cidade, n_linhas=20, titulo="Resumo por cidade")

    # 5. Exportar: planilha com várias abas + CSV
    escrever_planilha(
        {"Todos": dados, "Somente_SP": dados_sp, "Resumo_SP": resumo_por_cidade},
        ARQUIVO_SAIDA,
    )
    escrever_csv(dados_sp, ARQUIVO_SAIDA_CSV)

    return True