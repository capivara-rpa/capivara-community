"""Dados de exemplo (mock) para o painel do monitor.

Popula o banco com 8 robôs fictícios cobrindo **todos os status** possíveis,
cada um com o seu passo a passo — assim dá para ver o painel cheio sem
esperar um robô de verdade rodar.

Uso::

    python -m core.monitor.dados_exemplo
"""

from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from core.monitor.banco import apagar_tudo, iniciar_banco
from core.monitor.monitor import Monitor


def _relogio(inicio: datetime, intervalo: float = 4.0):
    """Cria um relógio falso que avança ``intervalo`` segundos a cada leitura.

    Serve para dar aos exemplos uma linha do tempo realista e reprodutível.
    """
    estado = {"agora": inicio}

    def proximo() -> str:
        estado["agora"] += timedelta(seconds=intervalo)
        return estado["agora"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    return proximo


def _agora_menos(**delta: float) -> datetime:
    return datetime.now() - timedelta(**delta)


# ----------------------------------------------------------------------
# Cenários (um por status, mais alguns finalizados)
# ----------------------------------------------------------------------
def _folha_pagamento() -> None:
    monitor = Monitor("robo_folha_pagamento", relogio=_relogio(_agora_menos(minutes=45), 18))
    monitor.passo("Abrindo o portal de RH")
    monitor.passo("Realizando login", detalhe="usuário: rpa_financeiro")
    monitor.sucesso("Conferindo competência 10/2026")
    monitor.passo("Baixando a planilha de colaboradores", detalhe="214 registros")
    monitor.sucesso("Validando CPFs e valores")
    monitor.passo("Emitindo holerites em lote", detalhe="214 holerites")
    monitor.sucesso("Enviando holerites por e-mail")
    monitor.finalizar("Folha de 10/2026 processada com sucesso")


def _conferencia_nfe() -> None:
    monitor = Monitor("robo_conferencia_nfe", relogio=_relogio(_agora_menos(minutes=2), 15))
    monitor.passo("Consultando notas pendentes no ERP")
    monitor.sucesso("43 notas encontradas")
    monitor.passo("Cruzando NF-e com o XML da SEFAZ")
    monitor.passo("Conferindo impostos destacados")
    monitor.passo("Atualizando status das notas no ERP", detalhe="lote 3 de 5")


def _extracao_portal() -> None:
    monitor = Monitor("robo_extracao_portal", relogio=_relogio(_agora_menos(minutes=30), 12))
    monitor.passo("Abrindo o portal do fornecedor")
    monitor.passo("Pesquisando CNPJ 12.345.678/0001-90")
    monitor.aviso("Nenhum resultado retornado na primeira busca")
    monitor.passo("Tentando novamente com a inscrição estadual")
    monitor.erro_negocio("CNPJ não encontrado na base do fornecedor")


def _download_relatorios() -> None:
    monitor = Monitor("robo_download_relatorios", relogio=_relogio(_agora_menos(hours=1, minutes=20), 20))
    monitor.passo("Acessando o painel de relatórios")
    monitor.passo("Selecionando o período 01/10 a 10/10")
    monitor.passo("Solicitando a geração dos relatórios")
    monitor.sucesso("Download iniciado")
    monitor.erro_critico("Timeout ao baixar o lote 2/4 — encerrando o robô")


def _envio_email() -> None:
    monitor = Monitor("robo_envio_email", relogio=_relogio(_agora_menos(minutes=15), 10))
    monitor.passo("Montando o corpo do e-mail")
    monitor.passo("Anexando o relatório consolidado")
    monitor.erro_sistemico("SMTP indisponível: conexão recusada em smtp.empresa.com:465")


def _conciliacao_bancaria() -> None:
    monitor = Monitor("robo_conciliacao_bancaria", relogio=_relogio(_agora_menos(hours=2), 22))
    monitor.passo("Baixando o extrato OFX do banco")
    monitor.passo("Lendo o razão do ERP")
    monitor.sucesso("1.204 lançamentos comparados")
    monitor.aviso("3 lançamentos divergentes encontrados")
    monitor.falha("Conciliação interrompida por divergência de valores")


def _backup_banco() -> None:
    monitor = Monitor("robo_backup_banco", relogio=_relogio(_agora_menos(hours=6), 15))
    monitor.passo("Conectando ao banco de produção")
    monitor.passo("Executando pg_dump", detalhe="base: erp_producao")
    monitor.sucesso("Backup compactado", detalhe="2,3 GB")
    monitor.sucesso("Enviando para o storage remoto")
    monitor.finalizar("Backup diário concluído")


def _importacao_clientes(iniciado_em: datetime) -> None:
    Monitor("robo_importacao_clientes", relogio=_relogio(iniciado_em, 1))


# ----------------------------------------------------------------------
def popular(reimprimir: bool = True) -> None:
    """Recria o banco do zero e insere os exemplos."""
    iniciar_banco()
    apagar_tudo()

    _folha_pagamento()
    _conferencia_nfe()
    _extracao_portal()
    _download_relatorios()
    _envio_email()
    _conciliacao_bancaria()
    _backup_banco()
    _importacao_clientes(_agora_menos(seconds=2))

    if reimprimir:
        logger.success("Banco do monitor populado com 8 execuções de exemplo.")


def main() -> None:
    popular()


if __name__ == "__main__":
    main()
