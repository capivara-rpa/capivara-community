"use strict";

// ============================================================
//  Lagoa · orquestrador de robôs
// ============================================================
const INTERVALO_MS = 2000;

const estado = {
    aba: "jobs",
    filtro: "todos",
    jobInfo: {},
    maquinaInfo: {},
    itemInfo: {},
    processos: [],
    maquinas: [],
    jobs: [],
    triggers: [],
    filas: [],
    itensPorFila: {},
    filaSelecionada: null,
    assets: [],
    usuarios: [],
    papeis: [],
    permissoes: [],
    alertas: [],
    sla: {},
    sessao: null,
    auth: false,
    tokenNovo: null,
    filtroItem: "todos",
    jobAberto: null,
    visaoAgenda: "lista",
    calendario: { ano: new Date().getFullYear(), mes: new Date().getMonth() + 1, eventos: [] },
    processoVariaveis: null,
    fluxos: [],
    fluxoEditando: null,
    fluxoRascunho: [],
    pddAtual: null,
};

const el = {
    resumo: document.getElementById("resumo"),
    painelDesempenho: document.getElementById("painel-desempenho"),
    taxaAnel: document.getElementById("taxa-anel"),
    taxaValor: document.getElementById("taxa-valor"),
    taxaDetalhe: document.getElementById("taxa-detalhe"),
    grafico: document.getElementById("grafico-execucoes"),
    graficoLegenda: document.getElementById("grafico-legenda"),
    graficoTotal: document.getElementById("grafico-total"),
    btnAgendaLista: document.getElementById("btn-agenda-lista"),
    btnAgendaCalendario: document.getElementById("btn-agenda-calendario"),
    calendario: document.getElementById("calendario"),
    tabelaTriggers: document.getElementById("tabela-triggers"),
    calendarioTitulo: document.getElementById("calendario-titulo"),
    calendarioLegenda: document.getElementById("calendario-legenda"),
    calendarioGrade: document.getElementById("calendario-grade"),
    calPrev: document.getElementById("cal-prev"),
    calNext: document.getElementById("cal-next"),
    calHoje: document.getElementById("cal-hoje"),
    dialogVariaveis: document.getElementById("dialog-variaveis"),
    formVariaveis: document.getElementById("form-variaveis"),
    variaveisProcesso: document.getElementById("variaveis-processo"),
    variaveisTexto: document.getElementById("variaveis-texto"),
    variaveisErro: document.getElementById("variaveis-erro"),
    variaveisCancelar: document.getElementById("variaveis-cancelar"),
    maquinas: document.getElementById("lista-maquinas"),
    processos: document.getElementById("lista-processos"),
    jobs: document.getElementById("corpo-jobs"),
    triggers: document.getElementById("corpo-triggers"),
    filas: document.getElementById("corpo-filas"),
    itens: document.getElementById("corpo-itens"),
    detalheFila: document.getElementById("detalhe-fila"),
    detalheFilaTitulo: document.getElementById("detalhe-fila-titulo"),
    detalheFilaFechar: document.getElementById("detalhe-fila-fechar"),
    assets: document.getElementById("corpo-assets"),
    filtros: document.getElementById("filtros"),
    conexao: document.getElementById("conexao"),
    conexaoTexto: document.getElementById("conexao-texto"),
    relogio: document.getElementById("relogio"),
    atualizado: document.getElementById("atualizado"),
    qtdMaquinas: document.getElementById("qtd-maquinas"),
    qtdProcessos: document.getElementById("qtd-processos"),
    modal: document.getElementById("modal"),
    form: document.getElementById("form-job"),
    campoProcesso: document.getElementById("campo-processo"),
    campoMaquina: document.getElementById("campo-maquina"),
    campoTag: document.getElementById("campo-tag"),
    campoObs: document.getElementById("campo-obs"),
    btnNovo: document.getElementById("btn-novo"),
    btnCancelarModal: document.getElementById("btn-cancelar-modal"),
    formTrigger: document.getElementById("form-trigger"),
    btnNovoTrigger: document.getElementById("btn-novo-trigger"),
    trCancelar: document.getElementById("tr-cancelar"),
    trProcesso: document.getElementById("tr-processo"),
    trMaquina: document.getElementById("tr-maquina"),
    trTipo: document.getElementById("tr-tipo"),
    trIntervalo: document.getElementById("tr-intervalo"),
    trHora: document.getElementById("tr-hora"),
    trCron: document.getElementById("tr-cron"),
    trTag: document.getElementById("tr-tag"),
    campoHora: document.getElementById("campo-hora"),
    campoCron: document.getElementById("campo-cron"),
    trDias: document.getElementById("tr-dias"),
    trFins: document.getElementById("tr-fins"),
    trFeriados: document.getElementById("tr-feriados"),
    automacoes: document.getElementById("corpo-automacoes"),
    formPacote: document.getElementById("form-pacote"),
    pacoteArquivo: document.getElementById("au-arquivo"),
    pacoteSenha: document.getElementById("tr-senha-pacote"),
    pacoteResultado: document.getElementById("pacote-resultado"),
    formPacoteGit: document.getElementById("form-pacote-git"),
    pacoteGitUrl: document.getElementById("au-git-url"),
    pacoteGitRef: document.getElementById("au-git-ref"),
    formAsset: document.getElementById("form-asset"),
    asNome: document.getElementById("as-nome"),
    asUsuario: document.getElementById("as-usuario"),
    asValor: document.getElementById("as-valor"),
    asTipo: document.getElementById("as-tipo"),
    asDesc: document.getElementById("as-desc"),
    corpoAuditoria: document.getElementById("corpo-auditoria"),
    formFila: document.getElementById("form-fila"),
    fiNome: document.getElementById("fi-nome"),
    fiProcesso: document.getElementById("fi-processo"),
    fiDesc: document.getElementById("fi-desc"),
    formItens: document.getElementById("form-itens"),
    fiItensJson: document.getElementById("fi-itens-json"),
    fiRefCampo: document.getElementById("fi-ref-campo"),
    fiPrioridade: document.getElementById("fi-prioridade"),
    usuarios: document.getElementById("corpo-usuarios"),
    papeis: document.getElementById("corpo-papeis"),
    formUsuario: document.getElementById("form-usuario"),
    usNome: document.getElementById("us-nome"),
    usEmail: document.getElementById("us-email"),
    usSenha: document.getElementById("us-senha"),
    usPapeis: document.getElementById("us-papeis"),
    usAdmin: document.getElementById("us-admin"),
    formPapel: document.getElementById("form-papel"),
    paNome: document.getElementById("pa-nome"),
    paPermissoes: document.getElementById("pa-permissoes"),
    usuarioArea: document.getElementById("usuario-area"),
    usuarioNome: document.getElementById("usuario-nome"),
    usuarioNomeSidebar: document.getElementById("sidebar-usuario-nome"),
    usuarioIniciais: document.getElementById("sidebar-usuario-iniciais"),
    btnSair: document.getElementById("btn-sair"),
    btnSairTopo: document.getElementById("btn-sair-topo"),
    dialogLogin: document.getElementById("dialog-login"),
    formLogin: document.getElementById("form-login"),
    loginEmail: document.getElementById("login-email"),
    loginSenha: document.getElementById("login-senha"),
    loginErro: document.getElementById("login-erro"),
    listaSla: document.getElementById("lista-sla"),
    slaTotal: document.getElementById("sla-total"),
    btnExpurgar: document.getElementById("btn-expurgar"),
    linkCsv: document.getElementById("link-csv"),
    formMaquina: document.getElementById("form-maquina"),
    mqNome: document.getElementById("mq-nome"),
    mqTags: document.getElementById("mq-tags"),
    mqInfo: document.getElementById("mq-info"),
    dispositivos: document.getElementById("corpo-dispositivos"),
    tokenNovo: document.getElementById("token-novo"),
    topoTitulo: document.getElementById("topo-titulo"),
    topoSubtitulo: document.getElementById("topo-subtitulo"),
    formFilaProcessos: document.getElementById("form-fila-processos"),
    fiProcessos: document.getElementById("fi-processos"),
    filtrosItens: document.getElementById("filtros-itens"),
    dialogJob: document.getElementById("dialog-job"),
    jobTitulo: document.getElementById("job-titulo"),
    jobResumo: document.getElementById("job-resumo"),
    jobAcoes: document.getElementById("job-acoes"),
    jobTrace: document.getElementById("job-trace"),
    jobFechar: document.getElementById("job-fechar"),
    btnNovoFluxo: document.getElementById("btn-novo-fluxo"),
    formFluxo: document.getElementById("form-fluxo"),
    pdNome: document.getElementById("pd-nome"),
    pdExecucoes: document.getElementById("pd-execucoes"),
    pdProcesso: document.getElementById("pd-processo"),
    pdDescricao: document.getElementById("pd-descricao"),
    pdPassosTexto: document.getElementById("pd-passos-texto"),
    pdGerarTexto: document.getElementById("pd-gerar-texto"),
    pdPassos: document.getElementById("pd-passos"),
    pdCanvas: document.getElementById("pd-canvas"),
    pdCancelar: document.getElementById("pd-cancelar"),
    pdErro: document.getElementById("pd-erro"),
    fluxos: document.getElementById("corpo-fluxos"),
    dialogPdd: document.getElementById("dialog-pdd"),
    pddTitulo: document.getElementById("pdd-titulo"),
    pddTexto: document.getElementById("pdd-texto"),
    pddFechar: document.getElementById("pdd-fechar"),
    pddImprimir: document.getElementById("pdd-imprimir"),
    pddBaixar: document.getElementById("pdd-baixar"),
};

// ---------- utilitários ----------
function escapar(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}
function hora(iso) { return iso ? iso.slice(11, 19) : "—"; }
function haQuanto(iso) {
    if (!iso) return "";
    const seg = (Date.now() - new Date(iso.replace(" ", "T"))) / 1000;
    if (seg < 60) return `há ${Math.max(1, Math.round(seg))}s`;
    if (seg < 3600) return `há ${Math.round(seg / 60)}min`;
    return `há ${Math.round(seg / 3600)}h`;
}
function duracao(inicio, fim) {
    if (!inicio) return "—";
    const a = new Date(inicio.replace(" ", "T"));
    const b = fim ? new Date(fim.replace(" ", "T")) : new Date();
    const s = Math.max(0, (b - a) / 1000);
    if (s < 60) return `${s.toFixed(0)}s`;
    return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}
function duracaoSegundos(valor) {
    const s = Math.max(0, Number(valor) || 0);
    if (s < 60) return `${Math.round(s)}s`;
    return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}
function corJob(status) { return estado.jobInfo[status]?.cor || "#8A8378"; }
function rotuloJob(status) { return estado.jobInfo[status]?.rotulo || status; }
function corItem(status) { return estado.itemInfo[status]?.cor || "#8A8378"; }
function rotuloItem(status) { return estado.itemInfo[status]?.rotulo || status; }

async function buscarJSON(url, opcoes) {
    const resp = await fetch(url, { cache: "no-store", ...opcoes });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function enviarJSON(url, corpo) {
    return buscarJSON(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo || {}),
    });
}

// ---------- carga ----------
async function carregar() {
    try {
        const dados = await buscarJSON("/api/orq/painel");
        Object.assign(estado, {
            jobInfo: dados.job_info,
            maquinaInfo: dados.maquina_info,
            itemInfo: dados.item_info || {},
            processos: dados.processos,
            maquinas: dados.maquinas,
            jobs: dados.jobs,
            triggers: dados.triggers || [],
            filas: dados.filas || [],
            itensPorFila: dados.itens_por_fila || {},
            assets: dados.assets || [],
            auditoria: dados.auditoria || [],
            usuarios: dados.usuarios || [],
            papeis: dados.papeis || [],
            permissoes: dados.permissoes || [],
            alertas: dados.alertas || [],
            fluxos: dados.fluxos || [],
            sla: dados.sla || {},
            auth: !!dados.auth,
            sessao: dados.sessao || null,
        });
        marcarConexao(true);
        renderAuth();
        renderResumo(dados.resumo);
        renderDesempenho(dados.resumo);
        renderMaquinas();
        renderDispositivos();
        renderProcessos();
        renderFiltros();
        renderJobs();
        renderTriggers();
        renderAutomacoes();
        renderFilas();
        renderItens();
        renderAssets();
        renderAuditoria();
        renderUsuarios();
        renderPapeis();
        renderFluxos();
        renderSla();
        preencherProcessosSelects();
        if (estado.visaoAgenda === "calendario") {
            carregarCalendario().catch(() => { /* mantém o último render */ });
        }
        if (estado.jobAberto && el.dialogJob.open) {
            atualizarJob(estado.jobAberto).catch(() => { /* ignora */ });
        }
        el.atualizado.textContent = "última atualização " + hora(new Date().toISOString().replace("T", " "));
    } catch (erro) {
        if (String(erro.message).includes("401")) abrirLogin();
        marcarConexao(false, erro.message);
    }
}

// ---------- autenticação ----------
function abrirLogin() {
    if (el.dialogLogin && !el.dialogLogin.open) el.dialogLogin.showModal();
}

function fecharLogin() {
    if (el.dialogLogin && el.dialogLogin.open) el.dialogLogin.close();
}

function obterIniciais(nome) {
    if (!nome) return "C";
    const partes = nome.trim().split(/\s+/);
    if (partes.length === 1) {
        const p = partes[0];
        return (p[0] + (p[1] || "")).toUpperCase();
    }
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function renderAuth() {
    const logado = !!estado.sessao;
    const nome = estado.sessao?.nome || estado.sessao?.email || "Capivara";
    if (el.usuarioArea) el.usuarioArea.hidden = !logado;
    if (logado && el.usuarioNome) el.usuarioNome.textContent = nome;
    if (el.usuarioNomeSidebar) el.usuarioNomeSidebar.textContent = nome;
    if (el.usuarioIniciais) el.usuarioIniciais.textContent = obterIniciais(estado.sessao?.nome || nome);
    if (estado.auth && !logado) abrirLogin();
}

async function entrar(evento) {
    evento.preventDefault();
    el.loginErro.textContent = "";
    try {
        const dados = await enviarJSON("/api/orq/login", {
            email: el.loginEmail.value.trim(),
            senha: el.loginSenha.value,
        });
        if (!dados.ok) throw new Error(dados.erro || "credenciais inválidas");
        el.loginSenha.value = "";
        fecharLogin();
        carregar();
    } catch (erro) {
        el.loginErro.textContent = erro.message;
    }
}

async function sair() {
    try { await enviarJSON("/api/orq/logout", {}); } catch { /* ignore */ }
    estado.sessao = null;
    carregar();
}

function marcarConexao(ok, detalhe = "") {
    el.conexao.classList.toggle("ok", ok);
    el.conexao.classList.toggle("erro", !ok);
    el.conexaoTexto.textContent = ok ? "conectado" : `offline${detalhe ? " · " + detalhe : ""}`;
}

// ---------- resumo ----------
function renderResumo(r) {
    const cartoes = [
        { v: r.maquinas_online, rot: "Máquinas online", cor: "#1FA463", icone: "🖥" },
        { v: r.maquinas_offline, rot: "Máquinas offline", cor: "#8A8378", icone: "☁" },
        { v: r.pendentes, rot: "Pendentes", cor: "#E0A400", icone: "◷" },
        { v: r.em_execucao, rot: "Em execução", cor: "#1F5FD1", icone: "▶" },
        { v: r.concluidos, rot: "Concluídos", cor: "#1FA463", icone: "✓" },
        { v: r.falhas, rot: "Falhas", cor: "#C0392B", icone: "✕" },
    ];
    el.resumo.innerHTML = cartoes.map((c) => `
        <div class="cartao" style="--cor:${c.cor}">
            <span class="cartao-icone" aria-hidden="true">${c.icone}</span>
            <div class="valor" style="color:${c.cor}">${c.v ?? 0}</div>
            <div class="rotulo">${c.rot}</div>
        </div>`).join("");
}

// ---------- desempenho ----------
function renderDesempenho(r) {
    if (!el.painelDesempenho) return;
    const taxa = Math.max(0, Math.min(100, Number(r?.taxa_sucesso || 0)));
    const finalizados = Number(r?.finalizados || 0);
    const historico = Array.isArray(r?.historico) ? r.historico : [];
    const total7d = Number(r?.execucoes_7d || 0);

    if (el.taxaAnel) el.taxaAnel.style.setProperty("--pct", taxa);
    if (el.taxaValor) el.taxaValor.textContent = `${taxa.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
    if (el.taxaDetalhe) {
        el.taxaDetalhe.textContent = finalizados
            ? `${Number(r?.concluidos || 0)} concluído(s) de ${finalizados} finalizado(s).`
            : "Nenhuma execução finalizada ainda.";
    }
    if (el.graficoTotal) {
        el.graficoTotal.textContent = `${total7d} execu\u00e7\u00e3o(\u00f5es) nos \u00faltimos 7 dias`;
    }

    const statuses = [
        { chave: "concluido", rotulo: "Concluídos", cor: "#1FA463" },
        { chave: "falhou", rotulo: "Falhas", cor: "#C0392B" },
        { chave: "cancelado", rotulo: "Cancelados", cor: "#8A8378" },
        { chave: "em_execucao", rotulo: "Em execução", cor: "#1F5FD1" },
        { chave: "pendente", rotulo: "Pendentes", cor: "#E0A400" },
    ];
    if (el.graficoLegenda) {
        const totais = {};
        historico.forEach((dia) => {
            statuses.forEach((s) => { totais[s.chave] = (totais[s.chave] || 0) + Number(dia[s.chave] || 0); });
        });
        el.graficoLegenda.innerHTML = statuses.map((s) => `
            <span><i style="--cor:${s.cor}"></i>${s.rotulo} (${totais[s.chave] || 0})</span>`).join("");
    }
    if (!el.grafico) return;
    if (!historico.length) {
        el.grafico.innerHTML = `<p class="grafico-vazio">Sem execuções no período.</p>`;
        return;
    }
    const maximo = Math.max(1, ...historico.map((dia) => Number(dia.total || 0)));
    el.grafico.innerHTML = historico.map((dia) => {
        const total = Number(dia.total || 0);
        const segmentos = statuses.map((s) => {
            const quantidade = Number(dia[s.chave] || 0);
            if (!quantidade) return "";
            const altura = Math.max(2, Math.round((quantidade / maximo) * 100));
            return `<div class="grafico-seg" style="--cor:${s.cor};height:${altura}%" title="${s.rotulo}: ${quantidade}"></div>`;
        }).join("");
        return `
            <div class="grafico-dia" title="${escapar(dia.data)}: ${total} execução(ões)">
                <div class="grafico-barras">${segmentos}</div>
                <span class="grafico-rotulo">${escapar(dia.rotulo || "")}</span>
            </div>`;
    }).join("");
}

// ---------- máquinas ----------
function renderMaquinas() {
    el.qtdMaquinas.textContent = `${estado.maquinas.length} cadastradas`;
    if (!estado.maquinas.length) {
        el.maquinas.innerHTML = `<p class="vazio">Nenhuma máquina registrada. Suba um agente.</p>`;
        return;
    }
    el.maquinas.innerHTML = estado.maquinas.map((m) => {
        const atual = m.job_atual ? `<div class="maquina-atual">▶ ${escapar(m.job_atual.processo_nome)} (#${m.job_atual.id})</div>` : "";
        return `
            <div class="maquina" style="--cor:${m.cor}">
                <div class="maquina-topo">
                    <span class="maquina-nome">${escapar(m.nome)}</span>
                    <span class="badge" style="--cor:${m.cor}"><span class="ponto"></span>
                        ${escapar(estado.maquinaInfo[m.estado]?.rotulo || m.estado)}</span>
                </div>
                <div class="maquina-meta">
                    <span>${escapar(m.tags || "sem tags")}</span>
                    <span>${haQuanto(m.ultima_atividade)}</span>
                </div>
                ${atual}
            </div>`;
    }).join("");
}

// ---------- processos ----------
// ---------- dispositivos (gestão de máquinas) ----------
function renderDispositivos() {
    if (!el.dispositivos) return;
    if (!estado.maquinas.length) {
        el.dispositivos.innerHTML =
            `<tr><td colspan="6"><p class="vazio">Nenhuma máquina cadastrada. Cadastre acima ou suba um agente.</p></td></tr>`;
        return;
    }
    el.dispositivos.innerHTML = estado.maquinas.map((m) => {
        const info = estado.maquinaInfo[m.estado] || {};
        const nome = escapar(m.nome);
        const token = m.tem_token
            ? `<span class="badge" style="--cor:#1FA463"><span class="ponto"></span>emitido</span>`
            : `<span class="badge" style="--cor:#8A8378"><span class="ponto"></span>sem token</span>`;
        const acaoToken = m.tem_token
            ? `<button class="acao" data-maq="revogar" data-nome="${nome}">Revogar token</button>`
            : `<button class="acao" data-maq="token" data-nome="${nome}">Gerar token</button>`;
        return `
            <tr>
                <td>${nome}${m.info ? `<div class="obs">${escapar(m.info)}</div>` : ""}</td>
                <td><span class="badge" style="--cor:${m.cor}"><span class="ponto"></span>
                    ${escapar(info.rotulo || m.estado)}</span></td>
                <td>${m.tags ? escapar(m.tags) : "—"}</td>
                <td class="num">${m.ultima_atividade ? haQuanto(m.ultima_atividade) : "nunca"}</td>
                <td>${token}</td>
                <td>
                    <button class="acao" data-maq="editar" data-nome="${nome}">Editar</button>
                    ${acaoToken}
                    <button class="acao" data-maq="remover" data-nome="${nome}">Remover</button>
                </td>
            </tr>`;
    }).join("");
}

async function criarMaquina(evento) {
    evento.preventDefault();
    try {
        await enviarJSON("/api/orq/maquinas", {
            nome: el.mqNome.value.trim(),
            tags: el.mqTags.value.trim() || null,
            info: el.mqInfo.value.trim() || null,
            ator: "painel",
        });
        el.formMaquina.reset();
        carregar();
    } catch (erro) {
        alert("Não foi possível cadastrar a máquina: " + erro.message);
    }
}

async function editarMaquina(nome) {
    const maquina = estado.maquinas.find((m) => m.nome === nome) || {};
    const tags = prompt(`Tags de "${nome}" (separadas por vírgula):`, maquina.tags || "");
    if (tags === null) return;
    const info = prompt(`Observação de "${nome}":`, maquina.info || "");
    if (info === null) return;
    try {
        await enviarJSON(`/api/orq/maquinas/${encodeURIComponent(nome)}/editar`, {
            tags, info, ator: "painel",
        });
        carregar();
    } catch (erro) {
        alert("Falha ao editar a máquina: " + erro.message);
    }
}

async function removerMaquina(nome) {
    if (!confirm(`Remover a máquina "${nome}"? Robôs que a usam perderão o vínculo.`)) return;
    try {
        await enviarJSON(`/api/orq/maquinas/${encodeURIComponent(nome)}/remover`, { ator: "painel" });
        if (estado.tokenNovo && estado.tokenNovo.nome === nome) estado.tokenNovo = null;
        carregar();
    } catch (erro) {
        alert("Falha ao remover a máquina: " + erro.message);
    }
}

async function emitirToken(nome) {
    try {
        const dados = await enviarJSON(`/api/orq/maquinas/${encodeURIComponent(nome)}/token`, {});
        estado.tokenNovo = { nome, token: dados.token };
        renderTokenNovo();
        carregar();
    } catch (erro) {
        alert("Falha ao gerar o token: " + erro.message);
    }
}

async function revogarToken(nome) {
    if (!confirm(`Revogar o token de "${nome}"? O agente perderá o acesso até gerar outro.`)) return;
    try {
        await enviarJSON(`/api/orq/maquinas/${encodeURIComponent(nome)}/token/revogar`, {});
        if (estado.tokenNovo && estado.tokenNovo.nome === nome) estado.tokenNovo = null;
        carregar();
    } catch (erro) {
        alert("Falha ao revogar o token: " + erro.message);
    }
}

function renderTokenNovo() {
    if (!el.tokenNovo) return;
    if (!estado.tokenNovo) {
        el.tokenNovo.classList.add("oculto");
        el.tokenNovo.innerHTML = "";
        return;
    }
    el.tokenNovo.classList.remove("oculto");
    el.tokenNovo.innerHTML =
        `Token de <strong>${escapar(estado.tokenNovo.nome)}</strong>` +
        ` — copie agora, não será exibido novamente:<br>` +
        `<code>${escapar(estado.tokenNovo.token)}</code>`;
}

function renderProcessos() {
    el.qtdProcessos.textContent = `${estado.processos.length} no catálogo`;
    if (!estado.processos.length) {
        el.processos.innerHTML = `<p class="vazio">Catálogo vazio.</p>`;
        return;
    }
    el.processos.innerHTML = estado.processos.map((p) => `
        <div class="processo">
            <div>
                <div class="processo-nome">${escapar(p.nome)}</div>
                <div class="processo-desc">${escapar(p.descricao || "")}</div>
            </div>
            <button class="botao-primario" onclick="abrirModal(${p.id})">Executar</button>
        </div>`).join("");
}

// ---------- jobs ----------
const ORDEM_FILTROS = ["pendente", "em_execucao", "concluido", "falhou", "cancelado"];

function renderFiltros() {
    const opcoes = [{ chave: "todos", rotulo: "Todos" }]
        .concat(ORDEM_FILTROS.map((s) => ({ chave: s, rotulo: rotuloJob(s) })));
    el.filtros.innerHTML = opcoes.map((o) => `
        <button class="chip ${estado.filtro === o.chave ? "ativo" : ""}"
                onclick="filtrar('${o.chave}')">${escapar(o.rotulo)}</button>`).join("");
}

function filtrar(chave) {
    estado.filtro = chave;
    renderFiltros();
    renderJobs();
}

function renderJobs() {
    const jobs = estado.jobs.filter((j) => estado.filtro === "todos" || j.status === estado.filtro);
    if (!jobs.length) {
        el.jobs.innerHTML = `<tr><td colspan="8"><p class="vazio">Nenhum job neste filtro.</p></td></tr>`;
        return;
    }
    el.jobs.innerHTML = jobs.map((j) => {
        const cor = corJob(j.status);
        const trace = j.execucao_id
            ? `<a class="acionar" href="/monitor/#exec=${j.execucao_id}" target="_blank">#${j.execucao_id}</a>`
            : "—";
        const cancelar = (j.status === "pendente" || j.status === "em_execucao")
            ? `<button class="acao" onclick="cancelarJob(${j.id})">Cancelar</button>`
            : "";
        const tag = j.requisito_tag ? ` <span class="tag">${escapar(j.requisito_tag)}</span>` : "";
        return `
            <tr>
                <td class="num">${j.id}</td>
                <td>
                    ${escapar(j.processo_nome || "(removido)")}${tag}
                    ${j.mensagem ? `<div class="obs">${escapar(j.mensagem)}</div>` : ""}
                </td>
                <td>${escapar(j.maquina_nome || "qualquer")}</td>
                <td><span class="badge ${j.status}" style="--cor:${cor}"><span class="ponto"></span>
                    ${escapar(rotuloJob(j.status))}</span></td>
                <td class="num">${hora(j.iniciado_em || j.criado_em)}</td>
                <td class="num">${duracao(j.iniciado_em, j.finalizado_em)}</td>
                <td>${trace}</td>
                <td class="acoes">
                    <button class="acao" onclick="abrirJob(${j.id})">Detalhes</button>
                    ${cancelar}
                </td>
            </tr>`;
    }).join("");
}

async function abrirJob(id) {
    estado.jobAberto = id;
    if (!el.dialogJob.open) el.dialogJob.showModal();
    el.jobTitulo.textContent = `Job #${id}`;
    el.jobResumo.innerHTML = `<p class="vazio">Carregando…</p>`;
    el.jobAcoes.innerHTML = "";
    el.jobTrace.innerHTML = `<p class="vazio">Carregando…</p>`;
    await atualizarJob(id);
}

async function atualizarJob(id) {
    const dados = await buscarJSON(`/api/orq/jobs/${id}`);
    const j = dados.job || {};
    const cor = corJob(j.status);
    el.jobTitulo.textContent = `Job #${j.id} · ${j.processo_nome || "(removido)"}`;
    el.jobResumo.innerHTML = `
        <div class="cartao"><span class="rotulo">Status</span>
            <span class="badge ${j.status}" style="--cor:${cor}"><span class="ponto"></span>
            ${escapar(rotuloJob(j.status))}</span></div>
        <div class="cartao"><span class="rotulo">Máquina</span>${escapar(j.maquina_nome || "qualquer")}</div>
        <div class="cartao"><span class="rotulo">Criado</span>${hora(j.criado_em)}</div>
        <div class="cartao"><span class="rotulo">Início</span>${j.iniciado_em ? hora(j.iniciado_em) : "—"}</div>
        <div class="cartao"><span class="rotulo">Fim</span>${hora(j.finalizado_em)}</div>
        <div class="cartao"><span class="rotulo">Duração</span>${duracao(j.iniciado_em, j.finalizado_em)}</div>
        ${j.mensagem ? `<div class="job-msg">${escapar(j.mensagem)}</div>` : ""}`;
    const cancelar = (j.status === "pendente" || j.status === "em_execucao")
        ? `<button class="botao-secundario" onclick="cancelarJob(${j.id})">Cancelar job</button>`
        : "";
    const monitor = j.execucao_id
        ? `<a class="botao-secundario" href="/monitor/#exec=${j.execucao_id}" target="_blank">Abrir no monitor</a>`
        : "";
    el.jobAcoes.innerHTML = `${cancelar}${monitor}`;

    if (!j.execucao_id) {
        el.jobTrace.innerHTML = `<p class="vazio">Sem trace (job ainda não executou).</p>`;
        return;
    }
    const trace = await buscarJSON(`/api/execucoes/${j.execucao_id}`);
    renderTrace(trace.passos || []);
}

function renderTrace(passos) {
    if (!passos.length) {
        el.jobTrace.innerHTML = `<p class="vazio">Nenhum passo registrado.</p>`;
        return;
    }
    el.jobTrace.innerHTML = passos.map((p) => {
        const nivel = (p.nivel || "INFO").toUpperCase();
        return `<div class="trace-linha nivel-${nivel}">
            <span class="trace-hora">${hora(p.criado_em)}</span>
            <span class="trace-texto">${escapar(p.descricao || "")}${
                p.detalhe ? `<div class="detalhe">${escapar(p.detalhe)}</div>` : ""}</span>
        </div>`;
    }).join("");
}

// ---------- abas ----------
const TITULOS = {
    jobs: ["Lagoa", "Onde a mágica das capivaras acontece"],
    dispositivos: ["Dispositivos", "Máquinas registradas · estado, tags e tokens"],
    agendamentos: ["Agendamentos", "Disparos automáticos por intervalo, horário ou cron"],
    automacoes: ["Automações", "Publique e gerencie robôs (.zip com rpa.json)"],
    bpmn: ["Fluxos & PDD", "Desenhe o processo e gere a documentação automaticamente"],
    filas: ["Filas", "Filas de trabalho (datapool) e seus itens"],
    assets: ["Credenciais", "Assets e segredos usados pelos robôs"],
    acessos: ["Acessos", "Usuários, papéis e permissões"],
    monitor: ["Monitor", "Execuções e passos em tempo real"],
};

function trocarAba(aba) {
    estado.aba = aba;
    document.querySelectorAll(".aba").forEach((b) => b.classList.toggle("ativo", b.dataset.aba === aba));
    document.querySelectorAll(".painel-aba").forEach((p) => p.classList.toggle("oculto", p.id !== `aba-${aba}`));
    el.filtros.classList.toggle("oculto", aba !== "jobs");
    if (el.painelDesempenho) el.painelDesempenho.classList.toggle("oculto", aba !== "jobs");
    if (aba === "agendamentos") aplicarVisaoAgenda();
    const lateral = document.querySelector(".painel-lateral");
    if (lateral) lateral.classList.toggle("oculto", aba === "monitor");
    if (aba === "monitor") {
        const frame = document.getElementById("frame-monitor");
        if (frame && !frame.getAttribute("src")) frame.setAttribute("src", "/monitor/?embed=1");
    }
    document.querySelectorAll(".sidebar-nav .nav-item[data-secao]").forEach((i) =>
        i.classList.toggle("ativo", i.dataset.secao === aba));
    const titulo = TITULOS[aba];
    if (titulo && el.topoTitulo) {
        el.topoTitulo.textContent = titulo[0];
        if (el.topoSubtitulo) el.topoSubtitulo.textContent = titulo[1];
    }
}

// ---------- agendamentos ----------
function aplicarVisaoAgenda() {
    const calendario = estado.visaoAgenda === "calendario";
    if (el.calendario) el.calendario.classList.toggle("oculto", !calendario);
    if (el.tabelaTriggers) el.tabelaTriggers.classList.toggle("oculto", calendario);
    if (el.btnAgendaLista) el.btnAgendaLista.classList.toggle("ativo", !calendario);
    if (el.btnAgendaCalendario) el.btnAgendaCalendario.classList.toggle("ativo", calendario);
    if (calendario) carregarCalendario().catch(() => { /* mantém o último render */ });
}

function mudarVisaoAgenda(visao) {
    estado.visaoAgenda = visao === "calendario" ? "calendario" : "lista";
    aplicarVisaoAgenda();
}

async function carregarCalendario() {
    const { ano, mes } = estado.calendario;
    const dados = await buscarJSON(`/api/orq/calendario?ano=${ano}&mes=${mes}`);
    estado.calendario = {
        ano: dados.ano || ano,
        mes: dados.mes || mes,
        eventos: Array.isArray(dados.eventos) ? dados.eventos : [],
    };
    renderCalendario();
}

function mudarMes(delta) {
    let { ano, mes } = estado.calendario;
    mes += delta;
    if (mes < 1) { mes = 12; ano -= 1; }
    if (mes > 12) { mes = 1; ano += 1; }
    estado.calendario.ano = ano;
    estado.calendario.mes = mes;
    carregarCalendario().catch((erro) => {
        if (el.calendarioGrade) {
            el.calendarioGrade.innerHTML = `<p class="vazio">Falha ao carregar: ${escapar(erro.message)}</p>`;
        }
    });
}

function irParaHoje() {
    const agora = new Date();
    estado.calendario.ano = agora.getFullYear();
    estado.calendario.mes = agora.getMonth() + 1;
    carregarCalendario().catch(() => { /* ignora */ });
}

function renderCalendario() {
    if (!el.calendarioGrade) return;
    const { ano, mes, eventos } = estado.calendario;
    const nomesMeses = new Date(ano, mes - 1, 1)
        .toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    const tituloMes = nomesMeses.charAt(0).toUpperCase() + nomesMeses.slice(1);
    if (el.calendarioTitulo) el.calendarioTitulo.textContent = tituloMes;

    const statusOrdem = ["concluido", "falhou", "cancelado", "em_execucao", "pendente"];
    if (el.calendarioLegenda) {
        el.calendarioLegenda.innerHTML = statusOrdem.map((status) => `
            <span><i style="--cor:${corJob(status)}"></i>${rotuloJob(status)}</span>`).join("");
    }

    const porData = {};
    eventos.forEach((evento) => {
        const chave = evento.data || (evento.iniciado_em || evento.criado_em || "").slice(0, 10);
        if (!chave) return;
        (porData[chave] ||= []).push(evento);
    });

    const primeiro = new Date(ano, mes - 1, 1);
    const deslocamento = (primeiro.getDay() + 6) % 7; // segunda-feira como primeiro dia
    const totalDias = new Date(ano, mes, 0).getDate();
    const hoje = new Date().toISOString().slice(0, 10);
    const partes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        .map((dia) => `<div class="cal-dia-semana">${dia}</div>`);

    for (let i = 0; i < deslocamento; i += 1) {
        partes.push('<div class="cal-dia fora" aria-hidden="true"></div>');
    }
    for (let dia = 1; dia <= totalDias; dia += 1) {
        const chave = `${ano}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
        const doDia = porData[chave] || [];
        const visiveis = doDia.slice(0, 3);
        const botoes = visiveis.map((evento) => {
            const cor = corJob(evento.status);
            const titulo = `#${evento.id} ${evento.processo_nome || "sem processo"} · ${rotuloJob(evento.status)} · ${hora(evento.iniciado_em || evento.criado_em)}`;
            return `<button type="button" class="cal-evento" style="--cor:${cor}"
                onclick="abrirJob(${Number(evento.id)})" title="${escapar(titulo)}">
                #${evento.id} ${escapar(evento.processo_nome || "sem processo")}</button>`;
        }).join("");
        const extra = doDia.length > visiveis.length
            ? `<span class="cal-mais">+${doDia.length - visiveis.length} mais</span>`
            : "";
        partes.push(`
            <div class="cal-dia${chave === hoje ? " hoje" : ""}">
                <span class="cal-numero">${dia}</span>
                ${botoes}${extra}
            </div>`);
    }
    const restantes = (7 - ((deslocamento + totalDias) % 7)) % 7;
    for (let i = 0; i < restantes; i += 1) {
        partes.push('<div class="cal-dia fora" aria-hidden="true"></div>');
    }
    el.calendarioGrade.innerHTML = partes.join("");
}

function descricaoDias(t) {
    const dias = (t.dias_semana ? String(t.dias_semana).split(",") : [])
        .map((n) => Number(n)).filter((n) => n >= 1 && n <= 7).sort();
    const rot = (n) => ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][n - 1];
    let texto;
    if (!dias || dias.length === 0 || dias.length === 7) texto = "todos os dias";
    else if (dias.join(",") === "1,2,3,4,5") texto = "seg a sex";
    else if (dias.join(",") === "6,7") texto = "sáb e dom";
    else texto = dias.map(rot).join(", ");
    const extras = [];
    if (!Number(t.incluir_fins ?? 1)) extras.push("sem fim de semana");
    if (!Number(t.incluir_feriados ?? 1)) extras.push("sem feriados");
    return extras.length ? `${texto} · ${extras.join(" · ")}` : texto;
}

function renderTriggers() {
    if (!estado.triggers.length) {
        el.triggers.innerHTML = `<tr><td colspan="8"><p class="vazio">Nenhum agendamento.</p></td></tr>`;
        return;
    }
    el.triggers.innerHTML = estado.triggers.map((t) => {
        const quando = t.tipo === "diario"
            ? `diário às ${escapar(t.hora || "00:00")}`
            : (t.tipo === "cron"
                ? `cron · ${escapar(t.expressao || "")}`
                : `a cada ${t.intervalo_min || 1} min`);
        const ativo = Number(t.ativo ?? 1);
        return `
            <tr>
                <td class="num">${t.id}</td>
                <td>${escapar(t.processo_nome || "(removido)")}</td>
                <td>${escapar(t.maquina_nome || "qualquer máquina")}${t.requisito_tag ? ` <span class="tag">${escapar(t.requisito_tag)}</span>` : ""}</td>
                <td>${quando}</td>
                <td class="obs">${escapar(descricaoDias(t))}</td>
                <td class="num">${hora(t.proxima_execucao)}</td>
                <td>${ativo ? `<span class="tag ativo">ativo</span>` : `<span class="tag pausado">pausado</span>`}</td>
                <td class="acoes">
                    <button class="acao" onclick="executarTrigger(${t.id})">Executar</button>
                    <button class="acao" onclick="alternarTrigger(${t.id}, ${ativo ? 0 : 1})">${ativo ? "Pausar" : "Ativar"}</button>
                    <button class="acao perigo" onclick="removerTrigger(${t.id})">Remover</button>
                </td>
            </tr>`;
    }).join("");
}

async function removerTrigger(id) {
    try {
        await enviarJSON(`/api/orq/triggers/${id}/remover`, {});
        carregar();
    } catch (erro) {
        alert("Falha ao remover agendamento: " + erro.message);
    }
}

async function alternarTrigger(id, ativo) {
    try {
        await enviarJSON(`/api/orq/triggers/${id}/ativo`, { ativo: !!ativo });
        carregar();
    } catch (erro) {
        alert("Falha ao atualizar agendamento: " + erro.message);
    }
}

async function executarTrigger(id) {
    try {
        await enviarJSON(`/api/orq/triggers/${id}/executar`, {});
        carregar();
    } catch (erro) {
        alert("Falha ao executar agendamento: " + erro.message);
    }
}

function diasSelecionados() {
    return Array.from(el.trDias.querySelectorAll("input[type=checkbox]:checked")).map((c) => Number(c.value));
}

async function criarTrigger(evento) {
    evento.preventDefault();
    const tipo = el.trTipo.value;
    const dias = diasSelecionados();
    if (!dias.length) {
        alert("Selecione ao menos um dia da semana.");
        return;
    }
    const corpo = {
        processo_id: Number(el.trProcesso.value),
        tipo,
        intervalo_min: tipo === "intervalo" ? Number(el.trIntervalo.value) : null,
        hora: tipo === "diario" ? el.trHora.value : null,
        expressao: tipo === "cron" ? el.trCron.value.trim() : null,
        maquina_id: el.trMaquina.value ? Number(el.trMaquina.value) : null,
        requisito_tag: el.trTag.value.trim() || null,
        dias_semana: dias,
        incluir_fins: el.trFins.checked,
        incluir_feriados: el.trFeriados.checked,
    };
    try {
        await enviarJSON("/api/orq/triggers", corpo);
        el.trTag.value = "";
        el.trCron.value = "";
        el.formTrigger.classList.add("oculto");
        carregar();
    } catch (erro) {
        alert("Falha ao agendar: " + erro.message);
    }
}

function atualizarTipoTrigger() {
    const tipo = el.trTipo.value;
    el.campoHora.classList.toggle("oculto", tipo !== "diario");
    el.campoCron.classList.toggle("oculto", tipo !== "cron");
    el.trIntervalo.parentElement.classList.toggle("oculto", tipo !== "intervalo");
}

// ---------- automações (pacotes de robô) ----------
function ehPacote(processo) {
    return String(processo.fluxo || "").startsWith("app.robos.");
}

function renderAutomacoes() {
    const itens = estado.processos.filter(ehPacote);
    if (!itens.length) {
        el.automacoes.innerHTML = `<tr><td colspan="7"><p class="vazio">Nenhuma automação publicada ainda. Envie um .zip ou instale de um repositório Git acima.</p></td></tr>`;
        return;
    }
    el.automacoes.innerHTML = itens.map((p) => {
        const doGit = Boolean(String(p.origem || "").trim());
        const shaCurto = String(p.commit_sha || "").slice(0, 8);
        const auto = Boolean(p.auto_atualizar);
        const origemTxt = doGit
            ? `<span class="tag git">git</span> <span class="obs">${escapar(p.origem_ref || "padrão")}</span>`
                + (shaCurto ? `<br><span class="obs" title="${escapar(p.commit_sha)}">#${shaCurto}</span>` : "")
                + `<br><button class="acao" onclick="alternarAutoAtualizar(${Number(p.id)}, ${auto ? "false" : "true"})">Auto: ${auto ? "sim" : "não"}</button>`
            : '<span class="tag pacote">pacote</span>';
        const btnAtualizar = doGit
            ? `<button class="acao" onclick="atualizarAutomacaoGit('${escapar(p.origem)}','${escapar(p.origem_ref || "")}')">Atualizar</button>`
            : "";
        const qtdVars = Object.keys(p.variaveis || {}).length;
        const btnVariaveis = `<button class="acao" onclick="abrirVariaveis(${Number(p.id)})">Variáveis${qtdVars ? ` (${qtdVars})` : ""}</button>`;
        return `
        <tr>
            <td>${escapar(p.nome)}</td>
            <td>${escapar(p.descricao || "—")}</td>
            <td class="obs">${escapar(p.fluxo || "")}</td>
            <td>${Number(p.usa_navegador) ? "sim" : "não"}</td>
            <td>${origemTxt}</td>
            <td>${btnVariaveis}</td>
            <td>${btnAtualizar}<button class="acao perigo" onclick="removerAutomacao('${escapar(p.nome)}')">Remover</button></td>
        </tr>`;
    }).join("");
}

function abrirVariaveis(processoId) {
    const processo = estado.processos.find((p) => Number(p.id) === Number(processoId));
    if (!processo || !el.dialogVariaveis) return;
    estado.processoVariaveis = processo.id;
    if (el.variaveisProcesso) el.variaveisProcesso.textContent = processo.nome;
    if (el.variaveisTexto) {
        const variaveis = processo.variaveis || {};
        el.variaveisTexto.value = Object.entries(variaveis)
            .map(([chave, valor]) => `${chave}=${valor}`)
            .join("\n");
    }
    if (el.variaveisErro) el.variaveisErro.textContent = "";
    el.dialogVariaveis.showModal();
}

async function salvarVariaveis(evento) {
    evento.preventDefault();
    if (!estado.processoVariaveis) return;
    if (el.variaveisErro) el.variaveisErro.textContent = "";
    try {
        const dados = await enviarJSON(
            `/api/orq/processos/${estado.processoVariaveis}/variaveis`,
            { texto: el.variaveisTexto.value },
        );
        const processo = estado.processos.find((p) => Number(p.id) === Number(estado.processoVariaveis));
        if (processo) processo.variaveis = dados.variaveis || {};
        el.dialogVariaveis.close();
        carregar();
    } catch (erro) {
        if (el.variaveisErro) el.variaveisErro.textContent = erro.message;
    }
}

async function enviarPacote(evento) {
    evento.preventDefault();
    const arquivo = el.pacoteArquivo.files[0];
    if (!arquivo) return;
    const senha = (el.pacoteSenha.value || "").trim();
    const url = "/api/orq/pacotes" + (senha ? `?senha=${encodeURIComponent(senha)}` : "");
    el.pacoteResultado.classList.remove("oculto");
    el.pacoteResultado.textContent = "Enviando…";
    try {
        const resposta = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/zip" },
            body: arquivo,
        });
        const dados = await resposta.json().catch(() => ({}));
        if (!resposta.ok) throw new Error(dados.erro || `HTTP ${resposta.status}`);
        el.pacoteResultado.textContent = `Robô "${dados.nome}" instalado (v${dados.versao}).`;
        el.formPacote.reset();
        carregar();
    } catch (erro) {
        el.pacoteResultado.textContent = "Falha: " + erro.message;
    }
}

async function instalarPacoteGit(evento) {
    evento.preventDefault();
    const url = (el.pacoteGitUrl.value || "").trim();
    if (!url) return;
    const ref = (el.pacoteGitRef.value || "").trim();
    el.pacoteResultado.classList.remove("oculto");
    el.pacoteResultado.textContent = "Clonando repositório…";
    try {
        const dados = await enviarJSON("/api/orq/automacoes/git", { url, ref });
        el.pacoteResultado.textContent = `Robô "${dados.nome}" instalado do Git (v${dados.versao}).`;
        el.formPacoteGit.reset();
        carregar();
    } catch (erro) {
        el.pacoteResultado.textContent = "Falha: " + erro.message;
    }
}

async function atualizarAutomacaoGit(url, ref) {
    if (!confirm(`Atualizar o robô a partir de ${url}${ref ? " (" + ref + ")" : ""}?\nA versão atual será substituída.`)) return;
    el.pacoteResultado.classList.remove("oculto");
    el.pacoteResultado.textContent = "Atualizando do repositório…";
    try {
        const dados = await enviarJSON("/api/orq/automacoes/git/atualizar", { url, ref });
        el.pacoteResultado.textContent = `Robô "${dados.nome}" atualizado (v${dados.versao}).`;
        carregar();
    } catch (erro) {
        el.pacoteResultado.textContent = "Falha: " + erro.message;
    }
}

async function alternarAutoAtualizar(processoId, ativo) {
    try {
        await enviarJSON(`/api/orq/processos/${Number(processoId)}/auto-atualizar`, { ativo });
        carregar();
    } catch (erro) {
        alert("Falha ao alterar auto-atualização: " + erro.message);
    }
}

async function verificarAtualizacoes() {
    el.pacoteResultado.classList.remove("oculto");
    el.pacoteResultado.textContent = "Verificando repositórios…";
    try {
        const r = await enviarJSON("/api/orq/automacoes/verificar", {});
        el.pacoteResultado.textContent =
            `Verificados: ${r.verificados} · Atualizados: ${r.atualizados} · ` +
            `Sem mudança: ${r.ignorados} · Erros: ${r.erros}`;
        carregar();
    } catch (erro) {
        el.pacoteResultado.textContent = "Falha: " + erro.message;
    }
}

async function removerAutomacao(nome) {
    if (!confirm(`Remover a automação "${nome}" (arquivos + catálogo)?`)) return;
    try {
        await enviarJSON(`/api/orq/automacoes/${encodeURIComponent(nome)}/remover`, {});
        carregar();
    } catch (erro) {
        alert("Falha ao remover automação: " + erro.message);
    }
}

// ---------- assets ----------
function renderAssets() {
    if (!estado.assets.length) {
        el.assets.innerHTML = `<tr><td colspan="7"><p class="vazio">Nenhum asset.</p></td></tr>`;
        return;
    }
    el.assets.innerHTML = estado.assets.map((a) => `
        <tr>
            <td>${escapar(a.nome)}</td>
            <td>${escapar(a.usuario || "—")}</td>
            <td class="num">${escapar(a.valor ?? "")}</td>
            <td>${escapar(a.tipo || "segredo")}</td>
            <td class="num">${a.versao ?? 1}</td>
            <td>${escapar(a.descricao || "—")}</td>
            <td>
                <button class="acao" onclick="rotacionarAsset('${escapar(a.nome)}')">Rotacionar</button>
                <button class="acao" onclick="removerAsset(${a.id})">Remover</button>
            </td>
        </tr>`).join("");
}

function renderAuditoria() {
    if (!el.corpoAuditoria) return;
    if (!estado.auditoria.length) {
        el.corpoAuditoria.innerHTML = `<tr><td colspan="5"><p class="vazio">Sem eventos.</p></td></tr>`;
        return;
    }
    el.corpoAuditoria.innerHTML = estado.auditoria.slice(0, 25).map((ev) => `
        <tr>
            <td>${hora(ev.quando)}</td>
            <td>${escapar(ev.ator || "—")}</td>
            <td>${escapar(ev.acao)}</td>
            <td>${escapar(ev.recurso || "—")}</td>
            <td>${escapar(ev.resultado || "—")}</td>
        </tr>`).join("");
}

// ---------- usuários & papéis ----------
function renderUsuarios() {
    if (!el.usuarios) return;
    if (!estado.usuarios.length) {
        el.usuarios.innerHTML = `<tr><td colspan="6"><p class="vazio">Nenhum usuário.</p></td></tr>`;
        return;
    }
    el.usuarios.innerHTML = estado.usuarios.map((u) => {
        const papeis = (u.papeis || []).map((p) => `<span class="tag">${escapar(p)}</span>`).join(" ") || "—";
        const perms = (u.permissoes || []).length;
        return `
            <tr>
                <td>${escapar(u.nome || "—")}</td>
                <td>${escapar(u.email)}</td>
                <td>${papeis}</td>
                <td class="num">${perms}</td>
                <td>${u.admin ? "sim" : "não"}</td>
                <td class="acoes">
                    <button class="acao" onclick="alternarAdmin(${u.id}, ${u.admin ? 0 : 1})">
                        ${u.admin ? "Remover admin" : "Tornar admin"}</button>
                    <button class="acao" onclick="removerUsuario(${u.id})">Remover</button>
                </td>
            </tr>`;
    }).join("");
}

function renderPapeis() {
    if (!el.papeis) return;
    if (!estado.papeis.length) {
        el.papeis.innerHTML = `<tr><td colspan="2"><p class="vazio">Nenhum papel.</p></td></tr>`;
        return;
    }
    el.papeis.innerHTML = estado.papeis.map((p) => `
        <tr>
            <td>${escapar(p.nome)}</td>
            <td class="permissoes">${(p.permissoes || []).map((x) => `<span class="tag">${escapar(x)}</span>`).join(" ") || "—"}</td>
        </tr>`).join("");
}

function renderSla() {
    if (!el.listaSla) return;
    const alertas = estado.alertas || [];
    if (el.slaTotal) {
        el.slaTotal.textContent = `${alertas.length} job(s)`;
    }
    if (!alertas.length) {
        el.listaSla.innerHTML = `<p class="sla-vazio">Nenhum job acima do tempo limite.</p>`;
        return;
    }
    const rotulos = estado.sla?.rotulos || {};
    const cores = estado.sla?.cores || {};
    el.listaSla.innerHTML = alertas.map((a) => {
        const rotulo = rotulos[a.alerta] || "Atenção";
        const cor = cores[a.alerta] || "#C0392B";
        const nome = a.processo_nome || "Sem processo";
        return `
            <button type="button" class="sla-item" style="--cor:${cor}"
                    onclick="abrirJob(${Number(a.id)})"
                    title="${escapar(rotulo)} · ${escapar(nome)}">
                <span class="sla-id">#${Number(a.id)}</span>
                <span class="sla-nome">${escapar(nome)}</span>
                <span class="sla-tempo">${escapar(duracaoSegundos(a.duracao_seg))}</span>
            </button>`;
    }).join("");
}

async function criarUsuario(evento) {
    evento.preventDefault();
    const papeis = el.usPapeis.value.split(",").map((s) => s.trim()).filter(Boolean);
    const corpo = {
        nome: el.usNome.value.trim(),
        email: el.usEmail.value.trim(),
        senha: el.usSenha.value,
        papeis,
        admin: el.usAdmin.checked,
        ator: "painel",
    };
    try {
        await enviarJSON("/api/orq/usuarios", corpo);
        el.formUsuario.reset();
        carregar();
    } catch (erro) {
        alert("Falha ao criar usuário: " + erro.message);
    }
}

async function removerUsuario(id) {
    if (!confirm("Remover este usuário?")) return;
    try {
        await enviarJSON(`/api/orq/usuarios/${id}/acao`, { acao: "remover", ator: "painel" });
        carregar();
    } catch (erro) {
        alert("Falha ao remover: " + erro.message);
    }
}

async function alternarAdmin(id, admin) {
    try {
        await enviarJSON(`/api/orq/usuarios/${id}/acao`, { acao: "admin", admin: !!admin, ator: "painel" });
        carregar();
    } catch (erro) {
        alert("Falha ao alterar: " + erro.message);
    }
}

async function criarPapel(evento) {
    evento.preventDefault();
    const permissoes = el.paPermissoes.value.split(",").map((s) => s.trim()).filter(Boolean);
    try {
        await enviarJSON("/api/orq/papeis", {
            nome: el.paNome.value.trim(),
            permissoes,
            ator: "painel",
        });
        el.formPapel.reset();
        carregar();
    } catch (erro) {
        alert("Falha ao salvar papel: " + erro.message);
    }
}

async function expurgarAuditoria() {
    const dias = prompt("Expurgar eventos mais antigos que quantos dias?", "90");
    if (dias === null) return;
    try {
        await enviarJSON("/api/orq/auditoria/expurgar", { dias: Number(dias) || 90, ator: "painel" });
        carregar();
    } catch (erro) {
        alert("Falha ao expurgar: " + erro.message);
    }
}

async function alternarFila(id, ativo) {
    try {
        await enviarJSON(`/api/orq/filas/${id}/acao`, { acao: "ativo", ativo: !!ativo, ator: "painel" });
        carregar();
    } catch (erro) {
        alert("Falha ao alterar fila: " + erro.message);
    }
}

async function removerAsset(id) {
    try {
        await enviarJSON(`/api/orq/assets/${id}/remover`, { ator: "painel" });
        carregar();
    } catch (erro) {
        alert("Falha ao remover asset: " + erro.message);
    }
}

async function rotacionarAsset(nome) {
    const novo = prompt(`Novo valor para '${nome}':`);
    if (novo === null) return;
    try {
        await enviarJSON(`/api/orq/assets/${encodeURIComponent(nome)}/rotacionar`, {
            valor: novo,
            ator: "painel",
        });
        carregar();
    } catch (erro) {
        alert("Falha ao rotacionar: " + erro.message);
    }
}

async function criarAsset(evento) {
    evento.preventDefault();
    const corpo = {
        nome: el.asNome.value.trim(),
        usuario: el.asUsuario.value.trim() || null,
        valor: el.asValor.value,
        tipo: el.asTipo.value,
        descricao: el.asDesc.value.trim() || null,
        ator: "painel",
    };
    try {
        await enviarJSON("/api/orq/assets", corpo);
        el.formAsset.reset();
        carregar();
    } catch (erro) {
        alert("Falha ao salvar asset: " + erro.message);
    }
}

// ---------- filas (datapool) ----------
function renderFilas() {
    if (!estado.filas.length) {
        el.filas.innerHTML = `<tr><td colspan="5"><p class="vazio">Nenhuma fila criada.</p></td></tr>`;
        return;
    }
    el.filas.innerHTML = estado.filas.map((f) => {
        const itens = estado.itensPorFila[f.nome] || [];
        const contagens = itens.reduce((acc, i) => {
            acc[i.status] = (acc[i.status] || 0) + 1;
            return acc;
        }, {});
        const progresso = ["novo", "em_processamento", "concluido", "falhou", "abandonado"]
            .filter((s) => contagens[s])
            .map((s) => `<span class="badge ${s}" style="--cor:${corItem(s)}"><span class="ponto"></span>
                ${escapar(rotuloItem(s))} ${contagens[s]}</span>`).join(" ") || "—";
        const executores = (f.processos || []).map((p) => `<span class="tag">${escapar(p.nome || "?")}</span>`);
        const executor = executores.length
            ? `${executores.join("")}${executores.length > 1 ? ` <span class="tag">round-robin ×${executores.length}</span>` : ""}`
            : (f.processo_id ? `#${f.processo_id}` : "(sem executor)");
        const ativa = f.ativo === undefined || f.ativo === null || Number(f.ativo) !== 0;
        return `
            <tr>
                <td class="num">${f.id}</td>
                <td>${escapar(f.nome)} ${ativa ? `<span class="tag">ativa</span>` : `<span class="tag pausada">pausada</span>`}</td>
                <td>${executor}<div class="obs">${escapar(f.descricao || "")}</div></td>
                <td class="num">${itens.length}</td>
                <td class="fila-progresso">${progresso}</td>
                <td class="acoes">
                    <button class="acao" onclick="abrirFila(${f.id})">Itens</button>
                    <button class="acao" onclick="alternarFila(${f.id}, ${ativa ? 0 : 1})">
                        ${ativa ? "Pausar" : "Ativar"}</button>
                    <button class="acao" onclick="removerFila(${f.id})">Remover</button>
                </td>
            </tr>`;
    }).join("");
}

function renderItens() {
    const fila = estado.filas.find((f) => f.id === estado.filaSelecionada);
    el.detalheFila.classList.toggle("oculto", !fila);
    if (!fila) return;
    el.detalheFilaTitulo.textContent = `Itens da fila: ${fila.nome}`;
    sincronizarProcessosFila(fila);

    const itens = estado.itensPorFila[fila.nome] || [];
    renderFiltrosItens(itens);
    const visiveis = itens.filter((i) => estado.filtroItem === "todos" || i.status === estado.filtroItem);
    if (!visiveis.length) {
        el.itens.innerHTML = `<tr><td colspan="5"><p class="vazio">Nenhum item neste filtro.</p></td></tr>`;
        return;
    }
    el.itens.innerHTML = visiveis.map((i) => {
        const prioridade = i.prioridade ?? 0;
        return `
            <tr>
                <td class="num">${i.id}</td>
                <td>${escapar(i.referencia || "—")}</td>
                <td><span class="badge ${i.status}" style="--cor:${corItem(i.status)}"><span class="ponto"></span>
                    ${escapar(rotuloItem(i.status))}</span></td>
                <td class="num">
                    <input type="number" class="item-prioridade" value="${prioridade}" style="width:70px"
                        onchange="definirPrioridadeItem(${i.id}, this.value)">
                </td>
                <td>${i.dados ? `<span class="obs">${escapar(JSON.stringify(i.dados))}</span>` : ""}${
                    i.mensagem ? `<div class="obs">${escapar(i.mensagem)}</div>` : ""}</td>
            </tr>`;
    }).join("");
}

function renderFiltrosItens(itens) {
    const contagens = itens.reduce((acc, i) => {
        acc[i.status] = (acc[i.status] || 0) + 1;
        return acc;
    }, {});
    const status = ["novo", "em_processamento", "concluido", "falhou", "abandonado"];
    const opcoes = [["todos", "Todos", itens.length]];
    status.forEach((s) => opcoes.push([s, rotuloItem(s), contagens[s] || 0]));
    el.filtrosItens.innerHTML = opcoes
        .filter(([, , n]) => n > 0 || itens.length === 0)
        .map(([chave, rotulo, n]) => `
            <button type="button" class="chip ${estado.filtroItem === chave ? "ativo" : ""}"
                onclick="estado.filtroItem='${chave}'; renderItens();">
                ${escapar(rotulo)} <b>${n}</b>
            </button>`).join("");
}

function sincronizarProcessosFila(fila) {
    const atuais = (fila.processos || []).map((p) => String(p.id));
    const opcoes = estado.processos.map((p) =>
        `<option value="${p.id}" ${atuais.includes(String(p.id)) ? "selected" : ""}>${escapar(p.nome)}</option>`);
    el.fiProcessos.innerHTML = opcoes.join("");
}

async function salvarProcessosFila(evento) {
    evento.preventDefault();
    if (!estado.filaSelecionada) return;
    const processos = Array.from(el.fiProcessos.selectedOptions).map((o) => Number(o.value));
    try {
        await enviarJSON(`/api/orq/filas/${estado.filaSelecionada}/processos`, { processos });
        carregar();
    } catch (erro) {
        alert("Falha ao salvar executores: " + erro.message);
    }
}

async function definirPrioridadeItem(itemId, valor) {
    try {
        await enviarJSON(`/api/orq/itens/${itemId}/prioridade`, { prioridade: Number(valor) || 0 });
        carregar();
    } catch (erro) {
        alert("Falha ao definir prioridade: " + erro.message);
    }
}

async function criarFila(evento) {
    evento.preventDefault();
    const corpo = {
        nome: el.fiNome.value.trim(),
        processo_id: el.fiProcesso.value ? Number(el.fiProcesso.value) : null,
        descricao: el.fiDesc.value.trim() || null,
    };
    try {
        await enviarJSON("/api/orq/filas", corpo);
        el.formFila.reset();
        el.fiProcesso.value = "";
        carregar();
    } catch (erro) {
        alert("Falha ao criar fila: " + erro.message);
    }
}

async function adicionarItens(evento) {
    evento.preventDefault();
    const texto = el.fiItensJson.value.trim();
    let itens;
    try {
        itens = JSON.parse(texto);
    } catch (e) {
        alert("JSON inválido no campo de itens.");
        return;
    }
    if (!Array.isArray(itens)) itens = [itens];
    const corpo = {
        itens,
        referencia_campo: el.fiRefCampo.value.trim() || null,
        prioridade: Number(el.fiPrioridade.value) || 0,
    };
    try {
        await enviarJSON(`/api/orq/filas/${estado.filaSelecionada}/itens`, corpo);
        el.fiItensJson.value = "";
        carregar();
    } catch (erro) {
        alert("Falha ao adicionar itens: " + erro.message);
    }
}

async function removerFila(id) {
    if (!confirm("Apagar a fila e todos os itens?")) return;
    try {
        await enviarJSON(`/api/orq/filas/${id}/remover`, {});
        estado.filaSelecionada = null;
        carregar();
    } catch (erro) {
        alert("Falha ao remover fila: " + erro.message);
    }
}

function abrirFila(id) {
    estado.filaSelecionada = estado.filaSelecionada === id ? null : id;
    carregar();
}

// ---------- fluxos e PDD ----------
const PD_TIPOS = {
    inicio: { rotulo: "Início", cor: "#1FA463", icone: "●" },
    acao: { rotulo: "Ação", cor: "#1F5FD1", icone: "▶" },
    decisao: { rotulo: "Decisão", cor: "#E0A400", icone: "◆" },
    excecao: { rotulo: "Exceção", cor: "#C0392B", icone: "!" },
    fim: { rotulo: "Fim", cor: "#8A8378", icone: "■" },
};
const PD_REGRAS_TEXTO = [
    { padrao: /^(se|caso)\s+/i, tipo: "decisao", ramo: "sim" },
    { padrao: /^(senão|senao|else|caso contrário|caso contrario)\s+/i, tipo: "decisao", ramo: "nao" },
    { padrao: /^(erro|exceção|excecao|falha)\s+/i, tipo: "excecao", ramo: "" },
    { padrao: /^fim\b/i, tipo: "fim", ramo: "" },
    { padrao: /^(início|inicio)\b/i, tipo: "inicio", ramo: "" },
];

function passosDoTexto(texto) {
    return String(texto || "").split(/\r?\n/).map((linha) => linha.trim()).filter(Boolean).map((nome) => {
        let tipo = "acao";
        let sim = "";
        let nao = "";
        for (const regra of PD_REGRAS_TEXTO) {
            if (regra.padrao.test(nome)) {
                tipo = regra.tipo;
                if (regra.ramo === "sim") sim = "Sim";
                if (regra.ramo === "nao") nao = "Não";
                break;
            }
        }
        return { nome, tipo, detalhe: "", sim, nao };
    });
}

function coletarPassos() {
    if (!el.pdPassos) return estado.fluxoRascunho.map((p) => ({ ...p }));
    return Array.from(el.pdPassos.querySelectorAll(".pd-passo")).map((linha, i) => {
        const tipo = linha.querySelector(".pd-tipo").value;
        return {
            nome: linha.querySelector(".pd-nome").value.trim(),
            tipo,
            detalhe: linha.querySelector(".pd-detalhe").value.trim(),
            sim: tipo === "decisao" ? (linha.querySelector(".pd-sim")?.value || "").trim() : "",
            nao: tipo === "decisao" ? (linha.querySelector(".pd-nao")?.value || "").trim() : "",
            x: Number(estado.fluxoRascunho[i]?.x ?? 60),
            y: Number(estado.fluxoRascunho[i]?.y ?? 60 + i * 104),
        };
    });
}

function nosDoDiagrama() {
    const passos = estado.fluxoRascunho || [];
    const primeiro = passos[0] || { x: 60 };
    const ultimo = passos[passos.length - 1] || { x: 60, y: 10 };
    return [
        { nome: "Início", tipo: "inicio", x: primeiro.x ?? 60, y: 12 },
        ...passos.map((p, i) => ({ ...p, indice: i })),
        { nome: "Fim", tipo: "fim", x: ultimo.x ?? 60, y: (ultimo.y ?? 10) + 104 },
    ];
}

function desenharLinhas() {
    const svg = el.pdCanvas?.querySelector("svg.pd-linhas");
    if (!svg) return;
    const nos = nosDoDiagrama();
    let tracos = `<defs><marker id="pd-seta" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-secondary)"></path></marker></defs>`;
    for (let i = 0; i < nos.length - 1; i += 1) {
       const atual = nos[i];
        const proximo = nos[i + 1];
        const x1 = (atual.x ?? 60) + 95;
        const y1 = (atual.y ?? 60) + 58;
        const x2 = (proximo.x ?? 60) + 95;
        const y2 = proximo.y ?? 60;
        const meio = (y1 + y2) / 2;
        tracos += `<path d="M ${x1} ${y1} C ${x1} ${meio}, ${x2} ${meio}, ${x2} ${y2}" marker-end="url(#pd-seta)"></path>`;
        if (atual.tipo === "decisao") {
            tracos += `<text x="${x1 + 9}" y="${meio - 4}">sim</text>`;
            if (atual.nao) {
                tracos += `<text class="pd-ramo-nao" x="${x1 - 34}" y="${meio - 4}">não: ${escapar(String(atual.nao).slice(0, 18))}</text>`;
            }
        }
    }
    svg.innerHTML = tracos;
}

function renderCanvas() {
    if (!el.pdCanvas) return;
    const nos = nosDoDiagrama();
    const altura = Math.max(300, ...nos.map((n) => (n.y ?? 0) + 96));
    const largura = Math.max(560, ...nos.map((n) => (n.x ?? 0) + 240));
    el.pdCanvas.style.height = `${altura}px`;
    el.pdCanvas.innerHTML = `<svg class="pd-linhas" width="${largura}" height="${altura}"></svg>` +
        nos.map((n) => {
            const info = PD_TIPOS[n.tipo] || PD_TIPOS.acao;
            const arrastavel = Number.isInteger(n.indice) ? ` data-pd-indice="${n.indice}"` : "";
            const ramo = n.tipo === "decisao" && n.nao ? `<small>não: ${escapar(n.nao)}</small>` : "";
            return `<div class="pd-no tipo-${n.tipo}"${arrastavel}
                style="left:${n.x}px;top:${n.y}px;--cor:${info.cor}">
                <span class="pd-no-icone">${info.icone}</span>
                <span class="pd-no-corpo"><strong>${escapar(n.nome)}</strong>
                <small>${info.rotulo}</small>${ramo}</span></div>`;
        }).join("");
    desenharLinhas();
}

function renderPassosEditaveis(passos) {
    estado.fluxoRascunho = (passos || []).map((p, i) => ({
        nome: p.nome || "Nova etapa",
        tipo: PD_TIPOS[p.tipo] ? p.tipo : "acao",
        detalhe: p.detalhe || "",
        sim: p.sim || "",
        nao: p.nao || "",
        x: Number.isFinite(Number(p.x)) ? Number(p.x) : 60,
        y: Number.isFinite(Number(p.y)) ? Number(p.y) : 60 + i * 104,
    }));
    if (!el.pdPassos) return;
    el.pdPassos.innerHTML = estado.fluxoRascunho.map((p, i) => `
        <div class="pd-passo" data-i="${i}">
            <select class="pd-tipo" aria-label="Tipo do passo">
                ${Object.entries(PD_TIPOS).map(([valor, info]) =>
                    `<option value="${valor}"${valor === p.tipo ? " selected" : ""}>${info.rotulo}</option>`).join("")}
            </select>
            <input class="pd-nome" value="${escapar(p.nome)}" placeholder="descrição do passo">
            <input class="pd-detalhe" value="${escapar(p.detalhe)}" placeholder="detalhe (opcional)">
            ${p.tipo === "decisao" ? `
            <input class="pd-sim" value="${escapar(p.sim)}" placeholder="sim →">
            <input class="pd-nao" value="${escapar(p.nao)}" placeholder="não →">` : ""}
            <button type="button" class="acao" data-pd-acao="subir" title="Subir"${i === 0 ? " disabled" : ""}>↑</button>
            <button type="button" class="acao" data-pd-acao="descer" title="Descer"${i === estado.fluxoRascunho.length - 1 ? " disabled" : ""}>↓</button>
            <button type="button" class="acao perigo" data-pd-acao="remover" title="Remover">×</button>
        </div>`).join("");
    renderCanvas();
}

function iniciarArraste(evento) {
    const no = evento.target.closest(".pd-no[data-pd-indice]");
    if (!no || !el.pdCanvas) return;
    const indice = Number(no.dataset.pdIndice);
    const passo = estado.fluxoRascunho[indice];
    if (!passo) return;
    evento.preventDefault();
    const caixa = el.pdCanvas.getBoundingClientRect();
    const deslocamentoX = evento.clientX - caixa.left - parseFloat(no.style.left || "0");
    const deslocamentoY = evento.clientY - caixa.top - parseFloat(no.style.top || "0");
    no.setPointerCapture(evento.pointerId);
    const mover = (e) => {
        passo.x = Math.max(4, Math.round(e.clientX - caixa.left - deslocamentoX));
        passo.y = Math.max(4, Math.round(e.clientY - caixa.top - deslocamentoY));
        no.style.left = `${passo.x}px`;
        no.style.top = `${passo.y}px`;
        desenharLinhas();
    };
    const parar = () => {
        no.removeEventListener("pointermove", mover);
        no.removeEventListener("pointerup", parar);
    };
    no.addEventListener("pointermove", mover);
    no.addEventListener("pointerup", parar);
}

function novoFluxo() {
    estado.fluxoEditando = "novo";
    el.formFluxo.classList.remove("oculto");
    el.pdNome.value = "";
    el.pdExecucoes.value = "1";
    el.pdProcesso.value = "";
    el.pdDescricao.value = "";
    el.pdPassosTexto.value = "";
    el.pdErro.textContent = "";
    renderPassosEditaveis([{ nome: "Abrir o sistema", tipo: "acao", detalhe: "" }]);
    el.pdNome.focus();
}

function editarFluxo(id) {
    const fluxo = estado.fluxos.find((f) => String(f.id) === String(id));
    if (!fluxo) return;
    estado.fluxoEditando = fluxo.id;
    el.formFluxo.classList.remove("oculto");
    el.pdNome.value = fluxo.nome || "";
    el.pdExecucoes.value = fluxo.execucoes_por_dia || 1;
    el.pdProcesso.value = fluxo.processo_id ? String(fluxo.processo_id) : "";
    el.pdDescricao.value = fluxo.descricao || "";
    el.pdPassosTexto.value = "";
    el.pdErro.textContent = "";
    renderPassosEditaveis(fluxo.passos || []);
}

function cancelarFluxo() {
    estado.fluxoEditando = null;
    estado.fluxoRascunho = [];
    el.formFluxo.classList.add("oculto");
    el.pdErro.textContent = "";
}

async function salvarFluxo(evento) {
    evento.preventDefault();
    const passos = coletarPassos().filter((p) => p.nome);
    if (!passos.length) {
        el.pdErro.textContent = "Descreva ao menos um passo do processo.";
        return;
    }
    const corpo = {
        nome: el.pdNome.value.trim(),
        execucoes_por_dia: Number(el.pdExecucoes.value),
        descricao: el.pdDescricao.value.trim(),
        processo_id: el.pdProcesso.value ? Number(el.pdProcesso.value) : null,
        passos,
    };
    const editando = estado.fluxoEditando !== "novo" ? estado.fluxoEditando : null;
    try {
        await enviarJSON(editando ? `/api/orq/fluxos/${editando}` : "/api/orq/fluxos", corpo);
        cancelarFluxo();
        carregar();
    } catch (erro) {
        el.pdErro.textContent = "Falha ao salvar: " + erro.message;
    }
}

function renderFluxos() {
    if (!el.fluxos) return;
    el.fluxos.innerHTML = estado.fluxos.map((f) => `
        <tr>
            <td><strong>${escapar(f.nome)}</strong></td>
            <td>${Number(f.execucoes_por_dia) || 1}</td>
            <td>${Number(f.qtd_passos) || 0}</td>
            <td>v${Number(f.versao) || 1}</td>
            <td>${haQuanto(f.atualizado_em || f.criado_em)}</td>
            <td><div class="acoes">
                <button type="button" class="acao" data-fluxo-acao="editar" data-id="${f.id}">Editar</button>
                <button type="button" class="acao" data-fluxo-acao="pdd" data-id="${f.id}">Ver PDD</button>
                <button type="button" class="acao perigo" data-fluxo-acao="remover" data-id="${f.id}">Remover</button>
            </div></td>
        </tr>`).join("") || `<tr><td colspan="6" class="vazio">Nenhum fluxo cadastrado. Clique em “+ Novo fluxo”.</td></tr>`;
}

async function abrirPdd(id) {
    try {
        const dados = await buscarJSON(`/api/orq/fluxos/${id}`);
        estado.pddAtual = dados.fluxo.id;
        el.pddTitulo.textContent = `PDD · ${dados.fluxo.nome} (v${dados.fluxo.versao})`;
        el.pddTexto.textContent = dados.markdown || "";
        el.dialogPdd.showModal();
    } catch (erro) {
        alert("Não foi possível abrir o PDD: " + erro.message);
    }
}

async function removerFluxo(id) {
    if (!window.confirm("Remover este fluxo e seu PDD?")) return;
    try {
        await enviarJSON(`/api/orq/fluxos/${id}/remover`, {});
        if (String(estado.fluxoEditando) === String(id)) cancelarFluxo();
        carregar();
    } catch (erro) {
        alert("Falha ao remover: " + erro.message);
    }
}

// ---------- modal ----------
function preencherProcessosSelects() {
    const opcoes = estado.processos.map((p) => `<option value="${p.id}">${escapar(p.nome)}</option>`).join("");

    // Preserva a seleção do modal entre os refreshes automáticos (senão o
    // <select> voltaria sempre para o primeiro processo do catálogo).
    const selecionado = el.campoProcesso.value;
    el.campoProcesso.innerHTML = opcoes;
    if (selecionado && estado.processos.some((p) => String(p.id) === String(selecionado))) {
        el.campoProcesso.value = selecionado;
    }

    if (!el.trProcesso.dataset.pronto) {
        el.trProcesso.innerHTML = opcoes;
        el.trProcesso.dataset.pronto = "1";
    }
    if (!el.fiProcesso.dataset.pronto) {
        el.fiProcesso.innerHTML = `<option value="">sem executor</option>` + opcoes;
        el.fiProcesso.dataset.pronto = "1";
    }
    if (el.pdProcesso) {
        const vinculado = el.pdProcesso.value;
        el.pdProcesso.innerHTML = `<option value="">Nenhuma</option>` + opcoes;
        if (vinculado && estado.processos.some((p) => String(p.id) === String(vinculado))) {
            el.pdProcesso.value = vinculado;
        }
    }

    if (el.trMaquina) {
        const maquinaSel = el.trMaquina.value;
        el.trMaquina.innerHTML = `<option value="">Qualquer máquina</option>` + estado.maquinas
            .map((m) => `<option value="${m.id}">${escapar(m.nome)}</option>`).join("");
        if (maquinaSel && estado.maquinas.some((m) => String(m.id) === String(maquinaSel))) {
            el.trMaquina.value = maquinaSel;
        }
    }
}

function abrirModal(processoId = null) {
    preencherProcessosSelects();
    el.campoMaquina.innerHTML = `<option value="">Qualquer máquina disponível</option>` +
        estado.maquinas.map((m) => `<option value="${m.id}">${escapar(m.nome)}</option>`).join("");
    if (processoId != null) el.campoProcesso.value = String(processoId);
    el.campoTag.value = "";
    el.campoObs.value = "";
    el.modal.showModal();
}

async function dispararJob(evento) {
    evento.preventDefault();
    const corpo = {
        processo_id: Number(el.campoProcesso.value),
        maquina_id: el.campoMaquina.value ? Number(el.campoMaquina.value) : null,
        requisito_tag: el.campoTag.value.trim() || null,
        mensagem: el.campoObs.value.trim() || null,
    };
    try {
        await enviarJSON("/api/orq/jobs", corpo);
        el.modal.close();
        carregar();
    } catch (erro) {
        alert("Não foi possível disparar o job: " + erro.message);
    }
}

async function cancelarJob(id) {
    try {
        await enviarJSON(`/api/orq/jobs/${id}/cancelar`, {});
        carregar();
    } catch (erro) {
        alert("Falha ao cancelar: " + erro.message);
    }
}

el.btnNovo.addEventListener("click", () => abrirModal());
el.btnCancelarModal.addEventListener("click", () => el.modal.close());
el.form.addEventListener("submit", dispararJob);
el.formTrigger.addEventListener("submit", criarTrigger);
el.btnNovoTrigger.addEventListener("click", () => {
    el.formTrigger.classList.remove("oculto");
    el.trProcesso.focus();
});
el.trCancelar.addEventListener("click", () => el.formTrigger.classList.add("oculto"));
el.trTipo.addEventListener("change", atualizarTipoTrigger);
el.formPacote.addEventListener("submit", enviarPacote);
el.formPacoteGit.addEventListener("submit", instalarPacoteGit);
el.formAsset.addEventListener("submit", criarAsset);
el.formFila.addEventListener("submit", criarFila);
el.formFilaProcessos.addEventListener("submit", salvarProcessosFila);
el.formItens.addEventListener("submit", adicionarItens);
el.formUsuario.addEventListener("submit", criarUsuario);
el.formPapel.addEventListener("submit", criarPapel);
el.formMaquina.addEventListener("submit", criarMaquina);
if (el.dispositivos) {
    el.dispositivos.addEventListener("click", (ev) => {
        const botao = ev.target.closest("button[data-maq]");
        if (!botao) return;
        const acoes = { token: emitirToken, revogar: revogarToken, editar: editarMaquina, remover: removerMaquina };
        const acao = acoes[botao.dataset.maq];
        if (acao) acao(botao.dataset.nome);
    });
}
document.querySelectorAll(".sidebar-nav .nav-link[data-secao]").forEach((b) =>
    b.addEventListener("click", () => trocarAba(b.dataset.secao)));
window.addEventListener("hashchange", () => {
    const aba = (location.hash || "").replace("#", "");
    if (TITULOS[aba]) trocarAba(aba);
});
const abaInicial = (location.hash || "").replace("#", "");
trocarAba(TITULOS[abaInicial] ? abaInicial : "jobs");
el.formLogin.addEventListener("submit", entrar);
if (el.btnSair) el.btnSair.addEventListener("click", sair);
if (el.btnSairTopo) el.btnSairTopo.addEventListener("click", sair);
el.btnExpurgar.addEventListener("click", expurgarAuditoria);
if (el.jobFechar) el.jobFechar.addEventListener("click", () => {
    estado.jobAberto = null;
    el.dialogJob.close();
});
el.detalheFilaFechar.addEventListener("click", () => {
    estado.filaSelecionada = null;
    carregar();
});
document.querySelectorAll(".aba").forEach((b) =>
    b.addEventListener("click", () => trocarAba(b.dataset.aba)));
if (el.btnAgendaLista) el.btnAgendaLista.addEventListener("click", () => mudarVisaoAgenda("lista"));
if (el.btnAgendaCalendario) el.btnAgendaCalendario.addEventListener("click", () => mudarVisaoAgenda("calendario"));
if (el.calPrev) el.calPrev.addEventListener("click", () => mudarMes(-1));
if (el.calNext) el.calNext.addEventListener("click", () => mudarMes(1));
if (el.calHoje) el.calHoje.addEventListener("click", irParaHoje);
if (el.formVariaveis) el.formVariaveis.addEventListener("submit", salvarVariaveis);
if (el.variaveisCancelar) el.variaveisCancelar.addEventListener("click", () => el.dialogVariaveis.close());
if (el.btnNovoFluxo) el.btnNovoFluxo.addEventListener("click", novoFluxo);
if (el.formFluxo) el.formFluxo.addEventListener("submit", salvarFluxo);
if (el.pdCancelar) el.pdCancelar.addEventListener("click", cancelarFluxo);
if (el.pdGerarTexto) {
    el.pdGerarTexto.addEventListener("click", () => {
        const passos = passosDoTexto(el.pdPassosTexto.value);
        if (!passos.length) {
            el.pdErro.textContent = "Escreva uma etapa por linha antes de gerar.";
            return;
        }
        el.pdErro.textContent = "";
        renderPassosEditaveis(passos);
    });
}
document.querySelectorAll("button[data-pd-tipo]").forEach((botao) =>
    botao.addEventListener("click", () => {
        const passos = coletarPassos();
        const tipo = botao.dataset.pdTipo;
        passos.push({ nome: "Nova etapa", tipo, detalhe: "", sim: tipo === "decisao" ? "Sim" : "", nao: tipo === "decisao" ? "Não" : "" });
        renderPassosEditaveis(passos);
    }));
if (el.pdPassos) {
    el.pdPassos.addEventListener("click", (ev) => {
        const botao = ev.target.closest("button[data-pd-acao]");
        if (!botao) return;
        const i = Number(botao.closest(".pd-passo").dataset.i);
        const passos = coletarPassos();
        if (botao.dataset.pdAcao === "remover") passos.splice(i, 1);
        if (botao.dataset.pdAcao === "subir" && i > 0) [passos[i - 1], passos[i]] = [passos[i], passos[i - 1]];
        if (botao.dataset.pdAcao === "descer" && i < passos.length - 1) [passos[i + 1], passos[i]] = [passos[i], passos[i + 1]];
        renderPassosEditaveis(passos);
    });
    el.pdPassos.addEventListener("change", (ev) => {
        if (!ev.target.matches(".pd-tipo")) return;
        const i = Number(ev.target.closest(".pd-passo").dataset.i);
        const passos = coletarPassos();
        if (passos[i].tipo === "decisao") {
            passos[i].sim = passos[i].sim || "Sim";
            passos[i].nao = passos[i].nao || "Não";
        }
        renderPassosEditaveis(passos);
    });
    el.pdPassos.addEventListener("input", (ev) => {
        if (!ev.target.matches(".pd-nome, .pd-detalhe, .pd-sim, .pd-nao")) return;
        const i = Number(ev.target.closest(".pd-passo").dataset.i);
        const campo = ev.target.classList[0].replace("pd-", "");
        const valor = ev.target.value;
        if (estado.fluxoRascunho[i]) estado.fluxoRascunho[i][campo] = valor;
        renderCanvas();
    });
}
if (el.pdCanvas) el.pdCanvas.addEventListener("pointerdown", iniciarArraste);
if (el.fluxos) {
    el.fluxos.addEventListener("click", (ev) => {
        const botao = ev.target.closest("button[data-fluxo-acao]");
        if (!botao) return;
        const acoes = { editar: editarFluxo, pdd: abrirPdd, remover: removerFluxo };
        const acao = acoes[botao.dataset.fluxoAcao];
        if (acao) acao(botao.dataset.id);
    });
}
if (el.pddFechar) el.pddFechar.addEventListener("click", () => el.dialogPdd.close());
if (el.pddImprimir) el.pddImprimir.addEventListener("click", () => {
    if (estado.pddAtual) window.open(`/api/orq/fluxos/${estado.pddAtual}/pdd?formato=html`, "_blank");
});
if (el.pddBaixar) el.pddBaixar.addEventListener("click", () => {
    if (!estado.pddAtual) return;
    const link = document.createElement("a");
    link.href = `/api/orq/fluxos/${estado.pddAtual}/pdd?formato=md`;
    link.download = `PDD-${estado.pddAtual}.md`;
    link.click();
});
atualizarTipoTrigger();

// ---------- tema claro/escuro ----------
const btnTema = document.getElementById("btn-tema");
const temaIcone = document.getElementById("tema-icone");
const temaTexto = document.getElementById("tema-texto");

function aplicarTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
    try { localStorage.setItem("rpa-tema", tema); } catch { /* ignora */ }
    if (temaIcone) temaIcone.textContent = tema === "dark" ? "☾" : "☀";
    if (temaTexto) temaTexto.textContent = tema === "dark" ? "Modo claro" : "Modo escuro";
}

function alternarTema() {
    const atual = document.documentElement.getAttribute("data-theme");
    aplicarTema(atual === "dark" ? "light" : "dark");
}

function temaInicial() {
    let tema = "light";
    const url = new URLSearchParams(location.search).get("tema"); // ?tema=dark · uso em testes/links
    try { tema = url || localStorage.getItem("rpa-tema") || tema; } catch { tema = url || tema; }
    if (tema !== "dark" && tema !== "light") tema = "light";
    aplicarTema(tema);
}

if (btnTema) btnTema.addEventListener("click", alternarTema);
temaInicial();

// ---------- relógio + loop ----------
function tique() { el.relogio.textContent = new Date().toLocaleTimeString("pt-BR"); }
setInterval(tique, 1000);
tique();

// Push em tempo real (SSE): recarrega assim que algo muda. O polling abaixo
// continua como rede de segurança (mantém o painel vivo se o SSE cair).
function iniciarEventos() {
    if (!("EventSource" in window)) return;
    if (new URLSearchParams(location.search).has("sem-sse")) return; // uso em testes
    const fonte = new EventSource("/api/orq/eventos");
    let rev = null;
    fonte.onmessage = (ev) => {
        let dados;
        try { dados = JSON.parse(ev.data); } catch { return; }
        if (dados.rev && dados.rev !== rev) { rev = dados.rev; carregar(); }
    };
    fonte.onerror = () => { /* o polling cobre eventuais quedas */ };
}

carregar();
iniciarEventos();
setInterval(() => { if (!document.hidden) carregar(); }, INTERVALO_MS);
