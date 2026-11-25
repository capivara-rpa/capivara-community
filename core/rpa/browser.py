"""Motor de automação web (Selenium) com "cara" de ferramenta low-code.

Todas as ações registram logs coloridos automaticamente, para que o
desenvolvedor saiba exatamente o que o robô está fazendo a cada momento.

Exemplo de uso::

    navegador = Navegador()
    navegador.iniciar()
    navegador.abrir_url("https://exemplo.com.br")
    navegador.escrever_texto("#usuario", "fulano")
    navegador.clicar_elemento("//button[@type='submit']")
    navegador.capturar_tela("tela_apos_login")
    navegador.finalizar()
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from core.tratador import ErroCriticoRPA, ErroRPA
from settings.parametros import HEADLESS, PASTA_OUTPUT, TEMPO_ESPERA_PADRAO, TEMPO_TIMEOUT


class Navegador:
    """Abstração sobre o Selenium com ações descritivas em português."""

    def __init__(
        self,
        headless: bool | None = None,
        download_dir: str | Path | None = None,
        tempo_espera: int | None = None,
        tempo_timeout: int | None = None,
    ) -> None:
        self.headless = HEADLESS if headless is None else headless
        self.download_dir = Path(download_dir or PASTA_OUTPUT)
        self.tempo_espera = tempo_espera or TEMPO_ESPERA_PADRAO
        self.tempo_timeout = tempo_timeout or TEMPO_TIMEOUT
        self._driver: webdriver.Chrome | None = None

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------
    def iniciar(self, url: str | None = None) -> None:
        """Abre o navegador Chrome e, opcionalmente, uma URL.

        Se ``HEADLESS`` for True (ambiente prod), roda sem janela.
        """
        opcoes = Options()

        if self.headless:
            opcoes.add_argument("--headless=new")
            opcoes.add_argument("--window-size=1366,768")
        else:
            opcoes.add_argument("--start-maximized")

        opcoes.add_argument("--no-sandbox")
        opcoes.add_argument("--disable-gpu")
        opcoes.add_argument("--disable-dev-shm-usage")
        opcoes.add_argument("--lang=pt-BR")
        opcoes.add_argument("--disable-blink-features=AutomationControlled")

        opcoes.add_experimental_option(
            "prefs",
            {
                # Salvar downloads direto na pasta do robô
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
            },
        )

        try:
            self._driver = webdriver.Chrome(options=opcoes)
        except Exception as erro:  # noqa: BLE001
            raise ErroCriticoRPA(
                "Não foi possível abrir o Chrome. Verifique se ele está instalado "
                f"(ou se o versionamento está correto). Detalhe: {erro}"
            ) from erro

        self._driver.implicitly_wait(self.tempo_espera)
        logger.success(f"Navegador iniciado (modo {'headless' if self.headless else 'janela'})")

        if url:
            self.abrir_url(url)

    def finalizar(self) -> None:
        """Fecha o navegador de forma segura."""
        if self._driver is not None:
            try:
                self._driver.quit()
                logger.success("Navegador finalizado.")
            except Exception:  # noqa: BLE001
                self._driver = None
            finally:
                self._driver = None

    # ------------------------------------------------------------------
    # Suporte (context manager)
    # ------------------------------------------------------------------
    def __enter__(self) -> Navegador:
        self.iniciar()
        return self

    def __exit__(self, *exc_info) -> None:
        self.finalizar()

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------
    @property
    def driver(self) -> webdriver.Chrome:
        if self._driver is None:
            raise ErroCriticoRPA("Navegador não iniciado. Execute navegador.iniciar() antes.")
        return self._driver

    def _checar_iniciado(self) -> None:
        self.driver  # noqa: B018  (a property já valida)

    @staticmethod
    def _converter_seletor(seletor) -> tuple[str, str]:
        """Transforma uma string amigável em uma tupla (By, valor).

        Regras:
        - ``//...`` ou ``(...)`` ou ``*[...]``  -> XPATH
        - ``@id``                                -> ID
        - qualquer outra coisa                   -> CSS
        """
        if isinstance(seletor, tuple):
            return seletor

        seletor = str(seletor).strip()
        if not seletor:
            raise ErroRPA("Seletor vazio não é permitido.")

        if seletor.startswith(("//", "((", "*")):
            return (By.XPATH, seletor)
        if seletor.startswith("@"):
            return (By.ID, seletor[1:])
        return (By.CSS_SELECTOR, seletor)

    def _localizar(self, seletor, tempo_max: int | None = None):
        """Aguarda e retorna o elemento (ou None se não encontrado)."""
        self._checar_iniciado()
        tempo = tempo_max if tempo_max is not None else self.tempo_timeout
        by, valor = self._converter_seletor(seletor)
        try:
            return WebDriverWait(self.driver, tempo).until(
                EC.presence_of_element_located((by, valor))
            )
        except Exception:  # noqa: BLE001
            return None

    def _localizar_ou_erro(self, seletor, acao: str):
        elemento = self._localizar(seletor)
        if elemento is None:
            raise ErroRPA(f"Elemento não encontrado para '{acao}': {seletor}")
        return elemento

    def _esperar_carregamento(self) -> None:
        try:
            WebDriverWait(self.driver, self.tempo_timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:  # noqa: BLE001
            logger.warning("Tempo de carregamento da página excedido; seguindo adiante.")

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def abrir_url(self, url: str) -> None:
        """Navega até uma URL."""
        self._checar_iniciado()
        logger.info(f"Navegando para: {url}")
        self.driver.get(url)
        self._esperar_carregamento()
        logger.success(f"Página aberta: {url}")

    # Alias amigável
    abrir_site = abrir_url

    def voltar_pagina(self) -> None:
        """Volta para a página anterior."""
        self._checar_iniciado()
        self.driver.back()
        self._esperar_carregamento()
        logger.info("Voltou para a página anterior.")

    def recarregar_pagina(self) -> None:
        """Recarrega a página atual."""
        self._checar_iniciado()
        self.driver.refresh()
        self._esperar_carregamento()
        logger.info("Página recarregada.")

    def obter_url_atual(self) -> str:
        """Retorna a URL atual da página."""
        url = self.driver.current_url
        logger.info(f"URL atual: {url}")
        return url

    def obter_titulo(self) -> str:
        """Retorna o título da página atual."""
        titulo = self.driver.title
        logger.info(f"Título da página: {titulo}")
        return titulo

    def aguardar_url_contem(
        self, fragmento: str, tempo_max: int | None = None
    ) -> bool:
        """Aguarda a URL atual conter um fragmento de texto.

        Exemplo: ``navegador.aguardar_url_contem("/search")``
        """
        tempo = tempo_max if tempo_max is not None else self.tempo_timeout
        try:
            WebDriverWait(self.driver, tempo).until(
                EC.url_contains(fragmento)
            )
            logger.success(f"URL passou a conter: {fragmento}")
            return True
        except Exception:  # noqa: BLE001
            logger.warning(f"URL não passou a conter '{fragmento}' em {tempo}s.")
            return False

    # ------------------------------------------------------------------
    # Aguardar / checagens
    # ------------------------------------------------------------------
    def aguardar_elemento(self, seletor, tempo_max: int | None = None, descricao: str | None = None):
        """Aguarda um elemento aparecer na tela. Retorna o elemento ou None."""
        nome = descricao or str(seletor)
        logger.info(f"Aguardando elemento: {nome}")
        elemento = self._localizar(seletor, tempo_max)
        if elemento is None:
            logger.warning(f"Elemento não encontrado: {nome}")
            return None
        logger.success(f"Elemento presente: {nome}")
        return elemento

    def elemento_existe(self, seletor) -> bool:
        """Verifica rapidamente se o elemento existe na página."""
        encontrado = self._localizar(seletor, tempo_max=1) is not None
        logger.debug(f"Elemento existe? {encontrado} <- {seletor}")
        return encontrado

    def elemento_visivel(self, seletor) -> bool:
        """Verifica se o elemento existe e está visível."""
        by, valor = self._converter_seletor(seletor)
        try:
            visivel = EC.visibility_of_element_located((by, valor))(self.driver)
        except Exception:  # noqa: BLE001
            visivel = False
        logger.debug(f"Elemento visível? {visivel} <- {seletor}")
        return bool(visivel)

    def aguardar_tempo(self, segundos: float = 1.0) -> None:
        """Pausa o robô por alguns segundos (pequena espera fixa)."""
        logger.debug(f"Aguardando {segundos}s...")
        time.sleep(segundos)

    # ------------------------------------------------------------------
    # Interação com elementos
    # ------------------------------------------------------------------
    def clicar_elemento(self, seletor, descricao: str | None = None) -> None:
        """Clica em um elemento."""
        nome = descricao or str(seletor)
        elemento = self._localizar_ou_erro(seletor, f"clicar em '{nome}'")
        self.rolar_ate_elemento(seletor, logar=False)
        elemento.click()
        logger.success(f"Clique realizado em: {nome}")

    def clicar_por_texto(self, texto: str, tag: str = "*") -> None:
        """Clica no elemento que contém o texto informado."""
        seletor = f"//{tag}[contains(text(), '{texto}') or contains(@value, '{texto}')]"
        self.clicar_elemento(seletor, descricao=f"texto '{texto}'")

    def escrever_texto(
        self,
        seletor,
        texto: str,
        limpar: bool = True,
        enter: bool = False,
        descricao: str | None = None,
    ) -> None:
        """Escreve um texto em um campo, limpando antes (opcional)."""
        nome = descricao or str(seletor)
        elemento = self._localizar_ou_erro(seletor, f"escrever no campo '{nome}'")
        if limpar:
            elemento.clear()
        elemento.send_keys(str(texto))
        if enter:
            elemento.send_keys(Keys.RETURN)
        trecho = str(texto)[:40] + ("..." if len(str(texto)) > 40 else "")
        logger.success(f"Texto escrito em '{nome}': {trecho}")

    def ler_texto(self, seletor) -> str:
        """Lê o texto visível de um elemento."""
        elemento = self._localizar_ou_erro(seletor, "ler texto")
        texto = elemento.text
        logger.info(f"Texto lido: {texto[:60]}")
        return texto

    def pegar_valor_campo(self, seletor) -> str:
        """Obtém o valor (atributo ``value``) de um campo."""
        elemento = self._localizar_ou_erro(seletor, "obter valor do campo")
        valor = elemento.get_attribute("value") or ""
        logger.info(f"Valor do campo: {valor[:60]}")
        return valor

    def pegar_atributo(self, seletor, atributo: str) -> str:
        """Retorna o valor de um atributo do elemento."""
        elemento = self._localizar_ou_erro(seletor, f"obter atributo '{atributo}'")
        valor = elemento.get_attribute(atributo) or ""
        logger.info(f"Atributo '{atributo}': {valor[:60]}")
        return valor

    def pressionar_tecla(self, tecla: str) -> None:
        """Pressiona uma tecla (ex.: 'enter', 'tab', 'escape', 'f5'...)."""
        tecla = tecla.upper()
        if not hasattr(Keys, tecla):
            raise ErroRPA(f"Tecla inválida: {tecla}")
        self.driver.switch_to.active_element.send_keys(getattr(Keys, tecla))
        logger.info(f"Tecla pressionada: {tecla.lower()}")

    def pressionar_enter(self) -> None:
        self.pressionar_tecla("enter")

    def pressionar_tab(self) -> None:
        self.pressionar_tecla("tab")

    def pressionar_escape(self) -> None:
        self.pressionar_tecla("escape")

    def pressionar_combinacao(self, *teclas: str) -> None:
        """Pressiona uma combinação de teclas (ex.: ctrl, c).

        Exemplo: ``navegador.pressionar_combinacao("CONTROL", "A")``
        """
        lista = []
        for tecla in teclas:
            tecla = tecla.upper()
            if not hasattr(Keys, tecla):
                raise ErroRPA(f"Tecla inválida: {tecla}")
            lista.append(getattr(Keys, tecla))
        self.driver.switch_to.active_element.send_keys(*lista)
        logger.info(f"Combinação pressionada: {' + '.join(t.lower() for t in teclas)}")

    def selecionar_opcao(self, seletor, valor: str | None = None, texto: str | None = None, indice: int | None = None) -> None:
        """Seleciona uma opção em um campo ``<select>``.

        Informe apenas um dos parâmetros: ``valor``, ``texto`` ou ``indice``.
        """
        elemento = self._localizar_ou_erro(seletor, "selecionar opção")
        select = Select(elemento)
        if valor is not None:
            select.select_by_value(str(valor))
        elif texto is not None:
            select.select_by_visible_text(str(texto))
        elif indice is not None:
            select.select_by_index(int(indice))
        else:
            raise ErroRPA("Informe 'valor', 'texto' ou 'indice' para selecionar a opção.")
        logger.success(f"Opção selecionada no campo {seletor}: {valor or texto or indice}")

    def marcar_checkbox(self, seletor, marcar: bool = True) -> None:
        """Marca ou desmarca um checkbox (conforme o estado atual)."""
        elemento = self._localizar_ou_erro(seletor, "marcar checkbox")
        marcado = elemento.is_selected()
        if marcado != marcar:
            elemento.click()
        estado = "marcado" if marcar else "desmarcado"
        logger.success(f"Checkbox {estado}: {seletor}")

    def fazer_upload(self, seletor, caminho: str | Path) -> None:
        """Envia um arquivo para um campo de upload (input[type=file])."""
        caminho = Path(caminho)
        if not caminho.exists():
            raise ErroRPA(f"Arquivo não encontrado para upload: {caminho}")
        elemento = self._localizar_ou_erro(seletor, "fazer upload")
        elemento.send_keys(str(caminho.resolve()))
        logger.success(f"Upload enviado: {caminho.name}")

    def arrastar_e_soltar(self, origem, destino) -> None:
        """Arrasta um elemento até outro (drag and drop)."""
        el_origem = self._localizar_ou_erro(origem, "arrastar (origem)")
        el_destino = self._localizar_ou_erro(destino, "soltar (destino)")
        ActionChains(self.driver).drag_and_drop(el_origem, el_destino).perform()
        logger.success("Arrastar e soltar concluído.")

    # ------------------------------------------------------------------
    # Rolagem
    # ------------------------------------------------------------------
    def rolar_pagina(self, para: str = "baixo", quantidade: int = 600) -> None:
        """Rola a página (para='baixo' | 'cima' | 'topo' | 'fim')."""
        para = para.lower()
        if para == "topo":
            self.driver.execute_script("window.scrollTo(0, 0)")
        elif para == "fim":
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        else:
            sentido = 1 if para == "baixo" else -1
            self.driver.execute_script(f"window.scrollBy(0, {quantidade * sentido})")
        logger.info(f"Página rolada: {para}")

    def rolar_ate_elemento(self, seletor, logar: bool = True) -> None:
        """Rola a página até que o elemento fique visível."""
        elemento = self._localizar(seletor)
        if elemento is None:
            return
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", elemento)
        if logar:
            logger.info(f"Página rolada até o elemento: {seletor}")

    # ------------------------------------------------------------------
    # Captura de tela
    # ------------------------------------------------------------------
    def capturar_tela(self, nome: str = "captura") -> Path:
        """Salva uma captura de tela em ``data/output``."""
        self._checar_iniciado()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        caminho = PASTA_OUTPUT / f"{stamp}_{nome}.png"
        self.driver.save_screenshot(str(caminho))
        logger.success(f"Captura de tela salva: {caminho}")
        return caminho

    # ------------------------------------------------------------------
    # Frames / janelas
    # ------------------------------------------------------------------
    def entrar_iframe(self, seletor) -> None:
        """Entra em um iframe para interagir com o conteúdo dele."""
        elemento = self._localizar_ou_erro(seletor, "entrar em iframe")
        self.driver.switch_to.frame(elemento)
        logger.success(f"Entrou no iframe: {seletor}")

    def sair_iframe(self, voltar_ao_principal: bool = True) -> None:
        """Sai do iframe (volta ao conteúdo principal da página)."""
        if voltar_ao_principal:
            self.driver.switch_to.default_content()
        else:
            self.driver.switch_to.parent_frame()
        logger.info("Saiu do iframe.")

    def lista_titulos_janelas(self) -> list[str]:
        """Retorna os títulos de todas as janelas/abas abertas."""
        titulos = [self.driver.switch_to.window(j).title for j in self.driver.window_handles]
        self.driver.switch_to.window(self.driver.window_handles[0])
        logger.debug(f"Janelas abertas: {titulos}")
        return titulos

    def mudar_janela_por_titulo(self, titulo: str) -> None:
        """Troca para a janela/aba que contenha parte do título."""
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if titulo.lower() in self.driver.title.lower():
                logger.success(f"Janela ativada: {self.driver.title}")
                return
        raise ErroRPA(f"Nenhuma janela com título contendo '{titulo}' foi encontrada.")

    def mudar_para_ultima_janela(self) -> None:
        """Troca para a janela/aba mais recente."""
        self.driver.switch_to.window(self.driver.window_handles[-1])
        logger.info("Trocado para a última janela/aba.")

    def fechar_janela_por_titulo(self, titulo: str) -> None:
        """Fecha a janela/aba que contenha parte do título."""
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if titulo.lower() in self.driver.title.lower():
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                logger.success(f"Janela fechada: {titulo}")
                return
        raise ErroRPA(f"Nenhuma janela com título contendo '{titulo}' foi encontrada.")

    # ------------------------------------------------------------------
    # Leitura da página / elementos extras
    # ------------------------------------------------------------------
    def obter_texto_pagina(self) -> str:
        """Retorna todo o texto visível da página."""
        texto = self.driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"Texto da página obtido ({len(texto)} caracteres).")
        return texto

    def obter_html(self) -> str:
        """Retorna o HTML completo da página atual."""
        html = self.driver.page_source
        logger.info(f"HTML da página obtido ({len(html)} caracteres).")
        return html

    def contar_elementos(self, seletor) -> int:
        """Conta quantos elementos casam com o seletor."""
        by, valor = self._converter_seletor(seletor)
        total = len(self.driver.find_elements(by, valor))
        logger.info(f"{total} elemento(s) encontrados para {seletor}")
        return total

    def aguardar_pagina_carregar(self) -> None:
        """Aguarda a página terminar de carregar (document.readyState)."""
        self._esperar_carregamento()
        logger.success("Página carregada.")

    def aguardar_texto_na_pagina(self, texto: str, tempo_max: int | None = None) -> bool:
        """Aguarda um texto aparecer em qualquer lugar da página."""
        tempo = tempo_max if tempo_max is not None else self.tempo_timeout
        try:
            WebDriverWait(self.driver, tempo).until(
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), texto)
            )
            logger.success(f"Texto encontrado na página: {texto[:40]}")
            return True
        except Exception:  # noqa: BLE001
            logger.warning(f"Texto não apareceu na página em {tempo}s: {texto[:40]}")
            return False

    def aguardar_elemento_sumir(self, seletor, tempo_max: int | None = None) -> bool:
        """Aguarda um elemento desaparecer da página."""
        tempo = tempo_max if tempo_max is not None else self.tempo_timeout
        by, valor = self._converter_seletor(seletor)
        try:
            WebDriverWait(self.driver, tempo).until(
                EC.invisibility_of_element_located((by, valor))
            )
            logger.success(f"Elemento sumiu: {seletor}")
            return True
        except Exception:  # noqa: BLE001
            logger.warning(f"Elemento continuou visível após {tempo}s: {seletor}")
            return False

    def clicar_se_existir(self, seletor) -> bool:
        """Clica no elemento apenas se ele existir; devolve se clicou."""
        if not self.elemento_existe(seletor):
            logger.warning(f"Elemento não existe (clique ignorado): {seletor}")
            return False
        self.clicar_elemento(seletor)
        return True

    def limpar_campo(self, seletor) -> None:
        """Limpa o conteúdo de um campo de texto."""
        elemento = self._localizar_ou_erro(seletor, "limpar campo")
        elemento.clear()
        logger.success(f"Campo limpo: {seletor}")

    def focar_elemento(self, seletor) -> None:
        """Coloca o foco em um elemento."""
        elemento = self._localizar_ou_erro(seletor, "focar elemento")
        self.driver.execute_script("arguments[0].focus();", elemento)
        logger.info(f"Foco colocado em: {seletor}")

    def executar_js(self, script: str, *argumentos) -> Any:
        """Executa JavaScript na página e devolve o resultado."""
        resultado = self.driver.execute_script(script, *argumentos)
        logger.info("JavaScript executado.")
        return resultado

    def obter_opcoes_select(self, seletor) -> list[str]:
        """Lista os textos das opções de um ``<select>``."""
        elemento = self._localizar_ou_erro(seletor, "listar opções do select")
        opcoes = [opcao.text for opcao in Select(elemento).options]
        logger.info(f"Opções do select {seletor}: {opcoes}")
        return opcoes

    def obter_valor_select(self, seletor) -> str:
        """Retorna o valor selecionado em um ``<select>``."""
        elemento = self._localizar_ou_erro(seletor, "obter valor do select")
        valor = Select(elemento).first_selected_option.get_attribute("value") or ""
        logger.info(f"Valor selecionado em {seletor}: {valor}")
        return valor

    def ler_tabela(self, seletor) -> list[list[str]]:
        """Lê uma tabela HTML e devolve uma lista de linhas (listas de células)."""
        tabela = self._localizar_ou_erro(seletor, "ler tabela")
        linhas: list[list[str]] = []
        for linha in tabela.find_elements(By.CSS_SELECTOR, "tr"):
            celulas = [celula.text.strip() for celula in linha.find_elements(By.CSS_SELECTOR, "th,td")]
            if celulas:
                linhas.append(celulas)
        logger.success(f"Tabela lida: {len(linhas)} linha(s).")
        return linhas

    def capturar_elemento(self, seletor, nome: str = "elemento") -> Path:
        """Salva uma captura de tela apenas do elemento."""
        elemento = self._localizar_ou_erro(seletor, "capturar elemento")
        stamp = time.strftime("%Y%m%d_%H%M%S")
        caminho = PASTA_OUTPUT / f"{stamp}_{nome}.png"
        elemento.screenshot(str(caminho))
        logger.success(f"Captura do elemento salva: {caminho}")
        return caminho

    # ------------------------------------------------------------------
    # Cookies / abas / alertas
    # ------------------------------------------------------------------
    def obter_cookies(self) -> list[dict[str, Any]]:
        """Retorna os cookies da sessão atual."""
        cookies = self.driver.get_cookies()
        logger.info(f"{len(cookies)} cookie(s) obtidos.")
        return cookies

    def adicionar_cookie(
        self,
        nome: str,
        valor: str,
        dominio: str | None = None,
        caminho: str = "/",
    ) -> None:
        """Adiciona um cookie à sessão atual."""
        cookie: dict[str, Any] = {"name": nome, "value": valor, "path": caminho}
        if dominio:
            cookie["domain"] = dominio
        self.driver.add_cookie(cookie)
        logger.success(f"Cookie adicionado: {nome}")

    def salvar_cookies(self, caminho: str | Path) -> Path:
        """Salva os cookies atuais em um arquivo JSON."""
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(self.driver.get_cookies(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.success(f"Cookies salvos em: {caminho}")
        return caminho

    def carregar_cookies(self, caminho: str | Path) -> int:
        """Carrega cookies de um arquivo JSON e devolve quantos foram adicionados."""
        caminho = Path(caminho)
        if not caminho.is_file():
            raise ErroRPA(f"Arquivo de cookies não encontrado: {caminho}")
        cookies = json.loads(caminho.read_text(encoding="utf-8"))
        total = 0
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
                total += 1
            except Exception:  # noqa: BLE001
                logger.warning(f"Cookie ignorado: {cookie.get('name')}")
        logger.success(f"{total} cookie(s) carregados de {caminho.name}")
        return total

    def abrir_nova_aba(self, url: str | None = None) -> None:
        """Abre uma nova aba e, opcionalmente, navega para uma URL."""
        self.driver.switch_to.new_window("tab")
        if url:
            self.driver.get(url)
            self._esperar_carregamento()
        logger.success(f"Nova aba aberta{' em ' + url if url else ''}.")

    def fechar_aba_atual(self) -> None:
        """Fecha a aba atual e volta para a última aba restante."""
        self.driver.close()
        abas = self.driver.window_handles
        if abas:
            self.driver.switch_to.window(abas[-1])
            logger.success("Aba atual fechada.")
        else:
            logger.warning("Última aba fechada; o navegador ficou sem janelas.")

    def mudar_para_aba(self, indice: int = -1) -> None:
        """Troca para a aba pelo índice (0 = primeira, -1 = última)."""
        abas = self.driver.window_handles
        if not abas:
            raise ErroRPA("Não há abas abertas.")
        self.driver.switch_to.window(abas[indice])
        logger.info(f"Trocado para a aba {indice}.")

    def _alerta(self):
        try:
            return WebDriverWait(self.driver, self.tempo_espera).until(EC.alert_is_present())
        except Exception as erro:  # noqa: BLE001
            raise ErroRPA("Nenhum alerta/diálogo presente na página.") from erro

    def aceitar_alerta(self) -> str:
        """Aceita um alerta/diálogo e devolve o texto dele."""
        alerta = self._alerta()
        texto = alerta.text
        alerta.accept()
        logger.success(f"Alerta aceito: {texto[:60]}")
        return texto

    def recusar_alerta(self) -> str:
        """Recusa (cancela) um alerta/diálogo e devolve o texto dele."""
        alerta = self._alerta()
        texto = alerta.text
        alerta.dismiss()
        logger.info(f"Alerta recusado: {texto[:60]}")
        return texto

    def obter_texto_alerta(self) -> str:
        """Retorna o texto de um alerta/diálogo sem fechá-lo."""
        texto = self._alerta().text
        logger.info(f"Texto do alerta: {texto[:60]}")
        return texto

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------
    def encontrar_ultimo_download(self, pasta: str | Path | None = None) -> Path | None:
        """Retorna o arquivo mais recente baixado na pasta de downloads."""
        pasta = Path(pasta or self.download_dir)
        arquivos = sorted(pasta.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        arquivo = next((a for a in arquivos if a.is_file()), None)
        if arquivo:
            logger.info(f"Último download: {arquivo.name}")
        return arquivo

    def aguardar_download(
        self, nome_parcial: str = "", pasta: str | Path | None = None, tempo_max: int | None = None
    ) -> Path | None:
        """Aguarda um download terminar e retorna o caminho do arquivo.

        O download é considerado pronto quando o nome do arquivo não muda
        por alguns segundos (downloads do Chrome usam a extensão ``.crdownload``).
        """
        pasta = Path(pasta or self.download_dir)
        tempo = tempo_max or self.tempo_timeout
        inicio = time.time()
        anterior: Path | None = None
        arquivo: Path | None = None

        while time.time() - inicio < tempo:
            candidatos = [p for p in pasta.glob("*") if p.is_file() and not p.name.endswith(".crdownload")]
            candidatos = [p for p in candidatos if nome_parcial.lower() in p.name.lower()] if nome_parcial else candidatos
            if candidatos:
                arquivo = max(candidatos, key=lambda p: p.stat().st_mtime)
                if anterior == arquivo:  # tamanho estável há 1s -> download concluído
                    logger.success(f"Download concluído: {arquivo.name}")
                    return arquivo
                anterior = arquivo
            time.sleep(1)

        logger.warning(f"Download não finalizado em {tempo}s.")
        return arquivo