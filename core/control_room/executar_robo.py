"""Runner de um robô dentro do seu próprio ``.venv``.

O agente chama este módulo via subprocess quando o robô tem um
``requirements.txt`` próprio::

    python -m core.control_room.executar_robo <config.json> <resultado.json>

O ``config.json`` traz o fluxo (``pacote.modulo:funcao``), o nome do robô, se
usa navegador e os dados de acesso à Lagoa (URL, token, máquina, job,
item). O runner executa o fluxo e grava ``{"sucesso": bool, "mensagem": str}``
no ``resultado.json``.

Os logs saem no stdout/stderr e são repassados pelo agente para o trace.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))


def _montar_agente(cfg: dict):
    """Cria um agente "proxy" para ``asset``/``credencial``/``cancelado``."""
    from core.control_room.agente import Agente

    agente = Agente(
        control_room=cfg.get("control_room") or "",
        maquina=cfg.get("maquina") or "desconhecida",
        token=cfg.get("token"),
    )
    agente._job_atual = {"id": cfg.get("job_id")} if cfg.get("job_id") else None
    agente._item_atual = cfg.get("item")
    return agente


def executar(cfg: dict) -> dict:
    """Roda o fluxo descrito em ``cfg`` e devolve ``{"sucesso", "mensagem"}``."""
    from core.control_room.agente import resolver_fluxo
    from core.robo import Robo

    resultado = {"sucesso": False, "mensagem": ""}
    try:
        funcao = resolver_fluxo(cfg["fluxo"])
        agente = _montar_agente(cfg)
        robo = Robo(nome=cfg["nome"])
        try:
            if cfg.get("usa_navegador"):
                robo.iniciar()
            ok = robo.executar_fluxo(cfg["nome"], funcao, agente=agente, item=cfg.get("item"))
        finally:
            robo.finalizar()
        resultado["sucesso"] = bool(ok)
        resultado["mensagem"] = "Executado com sucesso" if ok else "Fluxo retornou falha"
    except Exception as erro:  # noqa: BLE001
        resultado["mensagem"] = f"Erro no robô: {erro}"
    return resultado


def main() -> int:
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    destino = Path(sys.argv[2])
    resultado = executar(cfg)
    destino.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return 0 if resultado["sucesso"] else 1


if __name__ == "__main__":
    sys.exit(main())
