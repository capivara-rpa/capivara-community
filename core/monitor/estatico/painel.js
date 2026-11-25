"use strict";

// ============================================================
//  Capivara · Monitor · painel em tempo real
// ============================================================
const INTERVALO_MS = 2000;

const estado = {
    selecionada: null,
    filtro: "todas",
    statusInfo: {},
    execucoes: [],
};

const el = {
    resumo: document.getElementById("resumo"),
    lista: document.getElementById("lista-execucoes"),
    filtros: document.getElementById("filtros"),
    trace: document.getElementById("trace"),
    traceTitulo: document.getElementById("trace-titulo"),
    traceSub: document.getElementById("trace-sub"),
    conexao: document.getElementById("conexao"),
    conexaoTexto: document.getElementById("conexao-texto"),
    relogio: document.getElementById("relogio"),
    atualizado: document.getElementById("atualizado"),
    btnTema: document.getElementById("btn-tema"),
    temaIcone: document.getElementById("tema-icone"),
    temaTexto: document.getElementById("tema-texto"),
};

// ---------- tema claro/escuro ----------
function aplicarTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
    try { localStorage.setItem("rpa-tema", tema); } catch { /* ignora */ }
    if (el.temaIcone) el.temaIcone.textContent = tema === "dark" ? "☾" : "☀";
    if (el.temaTexto) el.temaTexto.textContent = tema === "dark" ? "Modo claro" : "Modo escuro";
}

function alternarTema() {
    const atual = document.documentElement.getAttribute("data-theme");
    aplicarTema(atual === "dark" ? "light" : "dark");
}

function temaInicial() {
    let tema = "light";
    try { tema = localStorage.getItem("rpa-tema") || tema; } catch { /* ignora */ }
    aplicarTema(tema || "light");
}

if (el.btnTema) el.btnTema.addEventListener("click", alternarTema);
temaInicial();

// Quando embutido na Lagoa (iframe), esconde a sidebar própria.
if (new URLSearchParams(location.search).has("embed")) {
    document.body.classList.add("embed");
}

// ---------- utilitários ----------
function escapar(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function hora(iso) {
    if (!iso) return "—";
    return iso.slice(11, 19);
}

function duracao(segundos) {
    if (segundos == null || segundos < 0) return "—";
    if (segundos < 60) return `${segundos.toFixed(1)}s`;
    const m = Math.floor(segundos / 60);
    const s = Math.round(segundos % 60);
    return `${m}m ${s}s`;
}

function segundosEntre(inicio, fim) {
    if (!inicio) return null;
    const a = new Date(inicio.replace(" ", "T"));
    const b = fim ? new Date(fim.replace(" ", "T")) : new Date();
    return (b - a) / 1000;
}

function haQuanto(iso) {
    if (!iso) return "";
    const seg = (Date.now() - new Date(iso.replace(" ", "T"))) / 1000;
    if (seg < 60) return `há ${Math.max(1, Math.round(seg))}s`;
    if (seg < 3600) return `há ${Math.round(seg / 60)}min`;
    return `há ${Math.round(seg / 3600)}h`;
}

function corDoStatus(status) {
    return estado.statusInfo[status]?.cor || "#8A8378";
}

function rotuloDoStatus(status) {
    return estado.statusInfo[status]?.rotulo || status;
}

// ---------- dados ----------
async function buscarJSON(url) {
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function carregarPainel() {
    try {
        const dados = await buscarJSON("/api/painel");
        estado.statusInfo = dados.status_info;
        estado.execucoes = dados.execucoes;
        marcarConexao(true);
        renderResumo(dados.resumo);
        renderFiltros(dados.resumo);
        renderLista();
        el.atualizado.textContent = "última atualização " + hora(new Date().toISOString().replace("T", " "));

        if (estado.selecionada && !estado.execucoes.some((e) => e.id === estado.selecionada)) {
            estado.selecionada = null;
        }
        if (estado.selecionada) await carregarTrace(estado.selecionada, true);
    } catch (erro) {
        marcarConexao(false, erro.message);
    }
}

async function carregarTrace(id, silencioso = false) {
    try {
        const dados = await buscarJSON(`/api/execucoes/${id}`);
        renderTrace(dados.execucao, dados.passos);
    } catch (erro) {
        if (!silencioso) {
            el.trace.innerHTML = `<p class="vazio">Não foi possível carregar o trace (${escapar(erro.message)}).</p>`;
        }
    }
}

function marcarConexao(ok, detalhe = "") {
    el.conexao.classList.toggle("ok", ok);
    el.conexao.classList.toggle("erro", !ok);
    el.conexaoTexto.textContent = ok ? "conectado" : `desconectado${detalhe ? " · " + detalhe : ""}`;
}

// ---------- resumo ----------
const ORDEM_CARTOES = [
    "iniciado", "processando", "finalizado",
    "falha", "erro_negocio", "erro_sistemico", "erro_critico",
];

function renderResumo(resumo) {
    const cartoes = ORDEM_CARTOES.map((status) => {
        const info = estado.statusInfo[status] || {};
        const total = resumo[status] ?? 0;
        return `
            <div class="cartao ativo" style="--cor:${info.cor || "#8A8378"}"
                 onclick="filtrarPor('${status}')" title="Filtrar por ${escapar(info.rotulo)}">
                <div class="valor" style="color:${info.cor || "inherit"}">${total}</div>
                <div class="rotulo">${escapar(info.rotulo || status)}</div>
            </div>`;
    }).join("");

    el.resumo.innerHTML = `
        <div class="cartao" style="--cor:#3B82F6">
            <div class="valor">${resumo.total ?? 0}</div>
            <div class="rotulo">Total de execuções</div>
        </div>` + cartoes;
}

// ---------- filtros ----------
function renderFiltros(resumo) {
    const opcoes = [{ chave: "todas", rotulo: "Todas", cor: "#3B82F6" }];
    for (const status of ORDEM_CARTOES) {
        if ((resumo[status] ?? 0) === 0) continue;
        opcoes.push({ chave: status, rotulo: rotuloDoStatus(status), cor: corDoStatus(status) });
    }

    el.filtros.innerHTML = opcoes.map((o) => `
        <button class="chip ${estado.filtro === o.chave ? "ativo" : ""}"
                onclick="filtrarPor('${o.chave}')">${escapar(o.rotulo)}</button>`).join("");
}

function filtrarPor(chave) {
    if (estado.filtro === chave) chave = "todas";
    estado.filtro = chave;
    renderFiltros(contarStatusAtual());
    renderLista();
}

function contarStatusAtual() {
    const contagem = { total: estado.execucoes.length };
    for (const exec of estado.execucoes) {
        contagem[exec.status] = (contagem[exec.status] || 0) + 1;
    }
    return contagem;
}

// ---------- lista ----------
function renderLista() {
    const lista = estado.execucoes.filter(
        (exec) => estado.filtro === "todas" || exec.status === estado.filtro
    );

    if (lista.length === 0) {
        el.lista.innerHTML = `<p class="vazio">Nenhuma execução neste filtro.</p>`;
        return;
    }

    el.lista.innerHTML = lista.map((exec) => {
        const cor = corDoStatus(exec.status);
        const dur = duracao(segundosEntre(exec.inicio, exec.fim));
        const selecionada = exec.id === estado.selecionada ? "selecionado" : "";
        return `
            <article class="robo ${selecionada}" style="--cor:${cor}" onclick="selecionar(${exec.id})">
                <div class="robo-topo">
                    <span class="robo-nome" title="${escapar(exec.robo)}">${escapar(exec.robo)}</span>
                    <span class="badge ${exec.status}" style="--cor:${cor}">
                        <span class="ponto"></span>${escapar(rotuloDoStatus(exec.status))}
                    </span>
                </div>
                <div class="robo-passo" title="${escapar(exec.mensagem || exec.ultimo_passo || "")}">
                    ${escapar(exec.mensagem || exec.ultimo_passo || "sem passos registrados")}
                </div>
                <div class="robo-meta">
                    <span>início <b>${hora(exec.inicio)}</b></span>
                    <span>${exec.fim ? "duração" : "em execução"} <b>${dur}</b></span>
                    <span><b>${exec.total_passos}</b> passos</span>
                    <span>${haQuanto(exec.atualizado_em)}</span>
                </div>
            </article>`;
    }).join("");
}

function selecionar(id) {
    estado.selecionada = id;
    history.replaceState(null, "", "#exec=" + id);
    renderLista();
    el.trace.innerHTML = `<p class="vazio">Carregando trace…</p>`;
    carregarTrace(id, true);
}

// ---------- trace ----------
function renderTrace(execucao, passos) {
    estado.selecionada = execucao.id;
    const cor = corDoStatus(execucao.status);
    el.traceTitulo.textContent = execucao.robo;
    el.traceSub.textContent = `${passos.length} passos · execução #${execucao.id}`;

    const durTotal = segundosEntre(execucao.inicio, execucao.fim);

    const cabecalho = `
        <div class="trace-cabecalho">
            <span class="badge ${execucao.status}" style="--cor:${cor}">
                <span class="ponto"></span>${escapar(rotuloDoStatus(execucao.status))}
            </span>
            ${execucao.mensagem ? `<span class="nome">${escapar(execucao.mensagem)}</span>` : ""}
        </div>
        <div class="trace-dados">
            <span>início <b>${hora(execucao.inicio)}</b></span>
            <span>fim <b>${hora(execucao.fim)}</b></span>
            <span>${execucao.fim ? "duração" : "em execução"} <b>${duracao(durTotal)}</b></span>
        </div>`;

    if (passos.length === 0) {
        el.trace.innerHTML = cabecalho + `<p class="vazio">Nenhum passo registrado ainda.</p>`;
        return;
    }

    // duração de cada passo = delta até o próximo (ou até agora)
    const duracoes = passos.map((p, i) => {
        const proximo = passos[i + 1]?.criado_em || execucao.fim || null;
        return Math.max(0, segundosEntre(p.criado_em, proximo) ?? 0);
    });
    const maior = Math.max(...duracoes, 0.001);

    const NIVEIS = {
        DEBUG: "#8A8378", INFO: "#3B82F6", SUCCESS: "#1FA463",
        WARNING: "#E0A400", ERROR: "#C0392B", CRITICAL: "#A93226",
    };

    const linhas = passos.map((p, i) => {
        const corPasso = corDoStatus(p.status) || NIVEIS[p.nivel] || "#8A8378";
        const corNivel = NIVEIS[p.nivel] || "#8A8378";
        const largura = Math.round((duracoes[i] / maior) * 100);
        return `
            <div class="linha" style="--cor:${corPasso}">
                <span class="marcador"></span>
                <span class="hora">${hora(p.criado_em)}</span>
                <div class="texto">
                    <div class="desc">${escapar(p.descricao)}</div>
                    ${p.detalhe ? `<div class="detalhe">${escapar(p.detalhe)}</div>` : ""}
                </div>
                <span class="nivel" style="--cor:${corNivel}">${escapar(p.nivel)}</span>
                <div class="barra"><i style="width:${largura}%;background:${corPasso}"></i></div>
            </div>`;
    }).join("");

    el.trace.innerHTML = cabecalho + `<div class="timeline">${linhas}</div>`;
    renderLista();
}

// ---------- relógio ----------
function tique() {
    const agora = new Date();
    el.relogio.textContent = agora.toLocaleTimeString("pt-BR");
}
setInterval(tique, 1000);
tique();

// ---------- loop ----------
const _alvo = location.hash.match(/exec=(\d+)/);
if (_alvo) estado.selecionada = Number(_alvo[1]);
window.addEventListener("hashchange", () => {
    const achado = location.hash.match(/exec=(\d+)/);
    if (achado) selecionar(Number(achado[1]));
});

// ---------- push em tempo real (SSE) ----------
function iniciarEventos() {
    if (!("EventSource" in window)) return;
    if (new URLSearchParams(location.search).has("sem-sse")) return; // uso em testes
    const fonte = new EventSource("/api/eventos");
    let rev = null;
    fonte.onmessage = (ev) => {
        let dados;
        try { dados = JSON.parse(ev.data); } catch { return; }
        if (dados.rev && dados.rev !== rev) { rev = dados.rev; carregarPainel(); }
    };
    fonte.onerror = () => { /* o polling cobre eventuais quedas */ };
}

carregarPainel();
iniciarEventos();
setInterval(() => {
    if (!document.hidden) carregarPainel();
}, INTERVALO_MS);
