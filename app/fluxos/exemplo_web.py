"""Fluxo de exemplo: busca no Google usando o navegador.

Mostra as funções low-code mais comuns do módulo ``core.rpa.browser``:
abrir URL, aguardar elemento, escrever texto, capturar tela etc.
"""

from loguru import logger

from settings.parametros import SITE_DEMO

# Seletores do site (extraídos em constantes para facilitar a manutenção)
CAMPO_BUSCA = "//textarea[@name='q']"


def buscar_no_google(navegador) -> bool:
    """Executa uma busca no Google e captura a tela dos resultados."""
    # 1. Abrir o site
    navegador.abrir_url(SITE_DEMO)

    # 2. Aguardar o campo de busca aparecer
    navegador.aguardar_elemento(CAMPO_BUSCA, descricao="Campo de busca do Google")

    # 3. Digitar o termo e pressionar Enter
    navegador.escrever_texto(CAMPO_BUSCA, "RPA com Python", enter=True)

    # 4. Aguardar a URL dos resultados (mais robusto que um seletor específico)
    navegador.aguardar_url_contem("/search")

    # 5. Registrar a URL de resultados
    logger.info(f"URL de resultados: {navegador.obter_url_atual()}")

    # 6. Capturar a tela como prova de execução
    navegador.capturar_tela("resultado_busca_google")

    # 7. Voltar para a página inicial
    navegador.abrir_url(SITE_DEMO)

    return True