"""Robô de exemplo — ponto de partida para publicar na Lagoa.

1. Renomeie a pasta e ajuste o ``rpa.json`` (principalmente ``nome`` e ``descricao``).
2. Escreva a automação dentro da função ``rodar`` (ou mude o nome dela no rpa.json).
3. Empacote:  python -m core.control_room.pacote empacotar TEMPLATE/
4. Suba o .zip na aba **Automações** da Lagoa.
"""


def rodar(navegador=None, agente=None, item=None):
    """Função que o agente executa para este robô.

    Receba **apenas** os parâmetros que for usar:

    - ``navegador``: Chrome já aberto (só chega quando ``usa_navegador`` = true).
    - ``agente``: acesso a segredos/credenciais e ao cancelamento do job.
    - ``item``: o item da fila em processamento (quando o robô consome fila).

    Devolva ``True`` para sucesso; lance ``ErroRPA`` (ou devolva ``False``) para
    marcar o job como falha.
    """
    # --- navegador (opcional) -------------------------------------------------
    if navegador is not None:
        navegador.abrir_url("https://example.com")
        titulo = navegador.obter_titulo()
        print(f"Página aberta: {titulo}")

    # --- item de fila (opcional) ---------------------------------------------
    if item is not None:
        print(f"Processando item #{item.get('id')}: {item.get('dados')}")

    # --- agente: segredos e cancelamento (opcional) --------------------------
    if agente is not None:
        if agente.cancelado():
            print("Job cancelado — encerrando.")
            return False
        # senha = agente.asset("portal_senha")
        # cred = agente.credencial("portal")   # {"usuario": ..., "senha": ...}

    print("Olá! Meu robô rodou com sucesso.")
    return True


if __name__ == "__main__":
    rodar()
