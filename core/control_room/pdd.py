"""Editor de fluxos e gerador de PDD da Lagoa.

Um fluxo é uma lista ordenada de passos (ação, decisão, exceção...). Os
mesmos dados alimentam o diagrama da interface e o documento de definição de
processo (PDD) em Markdown/HTML.
"""

from __future__ import annotations

import html
import json
import math
import re
from datetime import datetime
from typing import Any

TIPOS_PASSO: dict[str, dict[str, str]] = {
    "inicio": {"rotulo": "Início", "cor": "#1FA463", "icone": "●"},
    "acao": {"rotulo": "Ação", "cor": "#1F5FD1", "icone": "▶"},
    "decisao": {"rotulo": "Decisão", "cor": "#E0A400", "icone": "◆"},
    "excecao": {"rotulo": "Exceção", "cor": "#C0392B", "icone": "!"},
    "fim": {"rotulo": "Fim", "cor": "#8A8378", "icone": "■"},
}
TIPO_PADRAO = "acao"
LIMITE_PASSOS = 100
_LIMITE_NOME = 240
_LIMITE_DETALHE = 2000

_PADROES_TEXTO = (
    (re.compile(r"^(se|caso)\s+", re.I), "decisao", "sim"),
    (re.compile(r"^(senão|senao|else|caso contrário|caso contrario)\s+", re.I), "decisao", "nao"),
    (re.compile(r"^(erro|exceção|excecao|falha)\s+", re.I), "excecao", ""),
    (re.compile(r"^fim\b", re.I), "fim", ""),
    (re.compile(r"^(início|inicio)\b", re.I), "inicio", ""),
)


def _limpo(valor: Any, limite: int = _LIMITE_NOME) -> str:
    return str(valor or "").strip()[:limite]


def _numero(valor: Any, padrao: float) -> int:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = padrao
    if not math.isfinite(numero):
        numero = padrao
    return int(max(0, min(numero, 8000)))


def passos_de_texto(texto: str) -> list[dict[str, Any]]:
    """Transforma um passo por linha em passos estruturados.

    Linhas que começam com ``Se``/``Caso`` viram decisão; ``Senão`` vira o
    ramo ``não``; ``Erro``/``Falha`` viram exceção.
    """
    passos: list[dict[str, Any]] = []
    for linha in str(texto or "").splitlines():
        nome = linha.strip()
        if not nome:
            continue
        tipo, ramo = TIPO_PADRAO, ""
        for padrao, candidato, ramo_candidato in _PADROES_TEXTO:
            if padrao.match(nome):
                tipo, ramo = candidato, ramo_candidato
                break
        passos.append(
            {
                "nome": _limpo(nome),
                "tipo": tipo,
                "detalhe": "",
                "sim": "Sim" if ramo == "sim" else "",
                "nao": "Não" if ramo == "nao" else "",
            }
        )
    return passos


def normalizar_passos(passos: Any) -> list[dict[str, Any]]:
    """Valida e completa os passos (incluindo posições no diagrama)."""
    if passos is None:
        return []
    if isinstance(passos, str):
        try:
            passos = json.loads(passos or "[]")
        except (ValueError, TypeError) as erro:
            raise ValueError("Os passos não formam um JSON válido.") from erro
    if isinstance(passos, dict):
        passos = passos.get("passos", [])
    if not isinstance(passos, (list, tuple)):
        raise ValueError("Informe os passos como uma lista.")
    if len(passos) > LIMITE_PASSOS:
        raise ValueError(f"O limite é de {LIMITE_PASSOS} passos por fluxo.")

    resultado: list[dict[str, Any]] = []
    for indice, bruto in enumerate(passos):
        if isinstance(bruto, str):
            bruto = {"nome": bruto}
        if not isinstance(bruto, dict):
            raise ValueError(f"Passo {indice + 1} inválido.")
        nome = _limpo(bruto.get("nome") or bruto.get("descricao"))
        if not nome:
            raise ValueError(f"Passo {indice + 1} sem descrição.")
        tipo = str(bruto.get("tipo") or TIPO_PADRAO).strip().lower()
        if tipo not in TIPOS_PASSO:
            raise ValueError(f"Passo {indice + 1}: tipo '{tipo}' desconhecido.")
        resultado.append(
            {
                "nome": nome,
                "tipo": tipo,
                "detalhe": _limpo(bruto.get("detalhe"), _LIMITE_DETALHE),
                "sim": _limpo(bruto.get("sim")),
                "nao": _limpo(bruto.get("nao")),
                "x": _numero(bruto.get("x"), 60),
                "y": _numero(bruto.get("y"), 60 + indice * 104),
            }
        )
    return resultado


def carregar_passos(bruto: Any) -> list[dict[str, Any]]:
    """Lê passos gravados no banco sem jamais derrubar a API."""
    try:
        return normalizar_passos(bruto)
    except ValueError:
        return []


def serializar_passos(passos: Any) -> str:
    return json.dumps(normalizar_passos(passos), ensure_ascii=False)


def _rotulo(texto: Any) -> str:
    return _limpo(texto, 120).replace("\\", " ").replace('"', "'").replace("[", "(").replace("]", ")")


def gerar_mermaid(fluxo: dict[str, Any]) -> str:
    """Diagrama Mermaid do fluxo (início → passos → fim)."""
    passos = carregar_passos(fluxo.get("passos"))
    linhas = ["flowchart TD", '  START([Início])']
    anterior = "START"
    for indice, passo in enumerate(passos, start=1):
        no = f"P{indice}"
        rotulo = _rotulo(passo["nome"])
        if passo["tipo"] == "decisao":
            linhas.append(f'  {no}{{{rotulo}}}')
        elif passo["tipo"] == "excecao":
            linhas.append(f'  {no}["⚠ {rotulo}"]')
        else:
            linhas.append(f'  {no}["{rotulo}"]')
        if passo["tipo"] == "decisao":
            linhas.append(f"  {anterior} --> {no}")
            if passo.get("nao"):
                desvio = f"D{indice}"
                linhas.append(f'  {desvio}["{_rotulo(passo["nao"])}"]')
                linhas.append(f"  {no} -->|não| {desvio}")
                linhas.append(f"  {desvio} --> {no}")
        else:
            linhas.append(f"  {anterior} --> {no}")
        anterior = no
    linhas.append("  END([Fim])")
    linhas.append(f"  {anterior} --> END")
    return "\n".join(linhas)


def gerar_markdown(fluxo: dict[str, Any]) -> str:
    """PDD completo em Markdown, pronto para download/versionamento."""
    passos = carregar_passos(fluxo.get("passos"))
    nome = _limpo(fluxo.get("nome"), 200) or "Processo sem nome"
    versao = fluxo.get("versao") or 1
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    execucoes = fluxo.get("execucoes_por_dia") or 1
    tipo = fluxo.get("tipo") or "Não informado"
    pessoas = fluxo.get("pessoas") or 0
    tempo = fluxo.get("tempo") or "Não informado"

    linhas = [
        f"# PDD — {nome}",
        "",
        f"> Documento de Definição de Processo · versão {versao} · gerado em {agora} pela Lagoa",
        "",
        "## 1. Identificação",
        "",
        "| Campo | Valor |",
        "| --- | --- |",
        f"| Processo | {nome} |",
        f"| Tipo do processo | {tipo} |",
        f"| Execuções por dia | {execucoes} |",
        f"| Pessoas hoje | {pessoas} |",
        f"| Tempo por execução | {tempo} |",
        f"| Versão | {versao} |",
        "",
        "## 2. Objetivo e visão geral",
        "",
        _limpo(fluxo.get("descricao"), 4000) or "_Objetivo não informado._",
        "",
        "## 3. Fluxo do processo",
        "",
        "```mermaid",
        gerar_mermaid(fluxo),
        "```",
        "",
        "## 4. Passo a passo",
        "",
    ]
    if not passos:
        linhas.append("_Nenhum passo cadastrado._")
    for indice, passo in enumerate(passos, start=1):
        tipo = TIPOS_PASSO[passo["tipo"]]["rotulo"]
        linhas.append(f"{indice}. **{tipo} — {passo['nome']}**")
        if passo["detalhe"]:
            linhas.append(f"   - Detalhe: {passo['detalhe']}")
        if passo["tipo"] == "decisao":
            linhas.append(f"   - Sim: {passo['sim'] or '—'}")
            linhas.append(f"   - Não: {passo['nao'] or '—'}")
    excecoes = [p for p in passos if p["tipo"] == "excecao"]
    linhas += ["", "## 5. Exceções e tratamentos", ""]
    if excecoes:
        for passo in excecoes:
            linhas.append(f"- {passo['nome']}{': ' + passo['detalhe'] if passo['detalhe'] else ''}")
    else:
        linhas.append("_Nenhuma exceção registrada._")
    linhas += [
        "",
        "## 6. Controles e critérios de aceite",
        "",
        f"- Volume previsto: {execucoes} execução(ões) por dia.",
        f"- Esforço atual: {pessoas} pessoa(s), {tempo} por execução.",
        "- Cada execução é registrada no Monitor da Lagoa com status e trace de passos.",
        "- Falhas de negócio e falhas sistêmicas são classificadas no painel de execuções.",
        "- Toda alteração neste documento é registrada na auditoria da Lagoa.",
        "",
    ]
    return "\n".join(linhas)


def gerar_html(fluxo: dict[str, Any]) -> str:
    """Versão HTML do PDD, formatada para impressão/PDF pelo navegador."""
    passos = carregar_passos(fluxo.get("passos"))
    nome = html.escape(_limpo(fluxo.get("nome"), 200) or "Processo sem nome")
    versao = html.escape(str(fluxo.get("versao") or 1))
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    descricao = html.escape(_limpo(fluxo.get("descricao"), 4000) or "Objetivo não informado.")
    execucoes = html.escape(str(fluxo.get("execucoes_por_dia") or 1))
    tipo = html.escape(_limpo(fluxo.get("tipo"), 120) or "Não informado")
    pessoas = html.escape(str(fluxo.get("pessoas") or 0))
    tempo = html.escape(_limpo(fluxo.get("tempo"), 100) or "Não informado")

    etapas = []
    for passo in passos:
        tipo = TIPOS_PASSO[passo["tipo"]]
        detalhe = f"<div class='detalhe'>{html.escape(passo['detalhe'])}</div>" if passo["detalhe"] else ""
        ramos = ""
        if passo["tipo"] == "decisao":
            ramos = (
                "<div class='ramos'>"
                f"<span>Sim: {html.escape(passo['sim'] or '—')}</span>"
                f"<span>Não: {html.escape(passo['nao'] or '—')}</span>"
                "</div>"
            )
        etapas.append(
            f"<li><span class='selo' style='--cor:{tipo['cor']}'>{tipo['icone']} {tipo['rotulo']}</span>"
            f" <strong>{html.escape(passo['nome'])}</strong>{detalhe}{ramos}</li>"
        )
    excecoes = [p for p in passos if p["tipo"] == "excecao"]
    bloco_excecoes = "".join(f"<li>{html.escape(p['nome'])}</li>" for p in excecoes) or "<li>Nenhuma exceção registrada.</li>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>PDD — {nome}</title>
<style>
@page {{ size: A4; margin: 18mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0 auto; max-width: 780px; padding: 28px 32px; color: #14231c;
  font: 14px/1.6 Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #fff; }}
h1 {{ color: #0E1411; font-size: 26px; margin: 0 0 6px; }}
h2 {{ color: #006b3f; font-size: 16px; margin: 26px 0 10px; border-bottom: 1px solid #e3e9e4; padding-bottom: 5px; }}
.meta {{ color: #6c766f; font-size: 12px; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
td, th {{ border: 1px solid #dce5df; padding: 7px 10px; text-align: left; }}
th {{ background: #f3f8f5; width: 35%; }}
pre {{ background: #0E1411; color: #d8f4e3; border-radius: 8px; padding: 14px; overflow-x: auto; font-size: 11px; }}
ol {{ padding-left: 22px; }}
li {{ margin: 0 0 10px; }}
.selo {{ display: inline-block; color: var(--cor); font-size: 11px; font-weight: 700; margin-right: 6px; }}
.detalhe {{ color: #4d5b53; font-size: 12.5px; }}
.ramos {{ display: flex; gap: 14px; font-size: 12px; color: #4d5b53; }}
.acoes {{ position: fixed; top: 14px; right: 14px; }}
.acoes button {{ border: 0; border-radius: 7px; padding: 8px 14px; background: #006b3f; color: #fff; cursor: pointer; }}
footer {{ margin-top: 34px; color: #6c766f; font-size: 11px; }}
@media print {{ .acoes {{ display: none; }} body {{ padding: 0; }} }}
</style>
</head>
<body>
<div class="acoes"><button type="button" onclick="window.print()">Imprimir / salvar PDF</button></div>
<h1>PDD — {nome}</h1>
<p class="meta">Documento de Definição de Processo · versão {versao} · gerado em {agora} pela Lagoa</p>
<h2>1. Identificação</h2>
<table><tr><th>Processo</th><td>{nome}</td></tr>
<tr><th>Tipo do processo</th><td>{tipo}</td></tr>
<tr><th>Execuções por dia</th><td>{execucoes}</td></tr>
<tr><th>Pessoas hoje</th><td>{pessoas}</td></tr>
<tr><th>Tempo por execução</th><td>{tempo}</td></tr>
<tr><th>Versão</th><td>{versao}</td></tr></table>
<h2>2. Objetivo e visão geral</h2>
<p>{descricao}</p>
<h2>3. Fluxo do processo</h2>
<pre>{html.escape(gerar_mermaid(fluxo))}</pre>
<h2>4. Passo a passo</h2>
<ol>{''.join(etapas) or '<li>Nenhum passo cadastrado.</li>'}</ol>
<h2>5. Exceções e tratamentos</h2>
<ul>{bloco_excecoes}</ul>
<h2>6. Controles e critérios de aceite</h2>
<ul>
<li>Volume previsto: {execucoes} execução(ões) por dia.</li>
<li>Esforço atual: {pessoas} pessoa(s), {tempo} por execução.</li>
<li>Cada execução é registrada no Monitor da Lagoa com status e trace de passos.</li>
<li>Falhas de negócio e sistêmicas são classificadas no painel de execuções.</li>
<li>Toda alteração neste documento é registrada na auditoria da Lagoa.</li>
</ul>
<footer>Capivara · Lagoa — documento gerado automaticamente a partir do editor de fluxos.</footer>
</body>
</html>"""
