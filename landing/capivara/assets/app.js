/* Capivara 🦫 — interações da landing (vanilla JS, sem dependências). */
(function () {
  "use strict";

  var doc = document.documentElement;
  var semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  doc.classList.add("js");

  /* ------------------------------------------------------------ tema */
  var btnTema = document.getElementById("btn-tema");
  function aplicarTema(tema, salvar) {
    doc.setAttribute("data-tema", tema);
    if (salvar) {
      try { localStorage.setItem("capivara-tema", tema); } catch (e) {}
    }
  }
  btnTema.addEventListener("click", function () {
    aplicarTema(doc.getAttribute("data-tema") === "escuro" ? "claro" : "escuro", true);
  });
  // Acompanha o sistema enquanto a pessoa não escolher manualmente.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
    var salvo = null;
    try { salvo = localStorage.getItem("capivara-tema"); } catch (err) {}
    if (!salvo) aplicarTema(e.matches ? "escuro" : "claro", false);
  });

  /* ------------------------------------------------------------ navbar */
  var nav = document.querySelector(".nav");
  var btnMenu = document.getElementById("btn-menu");
  var links = document.getElementById("nav-links");

  function fecharMenu() {
    links.classList.remove("aberto");
    btnMenu.setAttribute("aria-expanded", "false");
    btnMenu.setAttribute("aria-label", "Abrir menu");
  }
  btnMenu.addEventListener("click", function () {
    var abrir = !links.classList.contains("aberto");
    links.classList.toggle("aberto", abrir);
    btnMenu.setAttribute("aria-expanded", String(abrir));
    btnMenu.setAttribute("aria-label", abrir ? "Fechar menu" : "Abrir menu");
  });
  links.addEventListener("click", function (e) { if (e.target.closest("a")) fecharMenu(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") fecharMenu(); });
  document.addEventListener("click", function (e) {
    if (!e.target.closest("#nav-links") && !e.target.closest("#btn-menu")) fecharMenu();
  });

  function aoRolar() { nav.classList.toggle("rolou", window.scrollY > 8); }
  window.addEventListener("scroll", aoRolar, { passive: true });
  aoRolar();

  /* ------------------------------------------------------------ revelar ao rolar + link ativo */
  var revelar = document.querySelectorAll(".revelar");
  if ("IntersectionObserver" in window && !semMovimento) {
    var obs = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add("visivel");
          obs.unobserve(en.target);
        }
      });
    }, { rootMargin: "0px 0px -40px 0px", threshold: 0.05 });
    revelar.forEach(function (el, i) {
      el.style.transitionDelay = (i % 3) * 70 + "ms";
      obs.observe(el);
    });

    var mapaLinks = {};
    links.querySelectorAll("a[href^='#']").forEach(function (a) { mapaLinks[a.getAttribute("href").slice(1)] = a; });
    var obsSecao = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) {
        var link = mapaLinks[en.target.id];
        if (link && en.isIntersecting) {
          links.querySelectorAll("a.ativo").forEach(function (a) { a.classList.remove("ativo"); });
          link.classList.add("ativo");
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(mapaLinks).forEach(function (id) {
      var s = document.getElementById(id);
      if (s) obsSecao.observe(s);
    });
  } else {
    revelar.forEach(function (el) { el.classList.add("visivel"); });
  }

  /* ------------------------------------------------------------ contador dos números */
  function contar(el) {
    var alvo = parseInt(el.getAttribute("data-contar"), 10);
    var inicio = null;
    var dur = 1200;
    function passo(t) {
      if (!inicio) inicio = t;
      var p = Math.min((t - inicio) / dur, 1);
      var suave = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(alvo * suave);
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }
  if ("IntersectionObserver" in window && !semMovimento) {
    var obsNum = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) {
        if (en.isIntersecting) { contar(en.target); obsNum.unobserve(en.target); }
      });
    }, { threshold: 0.6 });
    document.querySelectorAll("[data-contar]").forEach(function (el) { obsNum.observe(el); });
  }

  /* ------------------------------------------------------------ realce de sintaxe (Python) */
  var KW = "from|import|def|return|if|elif|else|for|in|while|with|as|raise|try|except|finally|class|not|and|or|is|None|True|False|lambda|pass|break|continue|yield";
  var BI = "print|len|range|str|int|float|dict|list|set|open";
  var TOKENS = new RegExp(
    "(#[^\\n]*)" +                                   // 1 comentário
    "|(\"(?:[^\"\\\\\\n]|\\\\.)*\"|'(?:[^'\\\\\\n]|\\\\.)*')" + // 2 string
    "|\\b(" + KW + ")\\b" +                          // 3 palavra-chave
    "|\\b(" + BI + ")(?=\\()" +                      // 4 builtin
    "|\\b([A-Za-z_][A-Za-z0-9_]*)(?=\\()" +          // 5 chamada de função
    "|\\b(\\d+(?:\\.\\d+)?)\\b",                     // 6 número
    "g"
  );
  function escapar(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function realcar(codigo) {
    var saida = "";
    var ultimo = 0;
    codigo.replace(TOKENS, function (m, com, str, kw, bi, fn, num, pos) {
      saida += escapar(codigo.slice(ultimo, pos));
      var cls = com ? "tk-com" : str ? "tk-str" : kw ? "tk-kw" : bi ? "tk-bi" : fn ? "tk-fn" : "tk-num";
      saida += '<span class="' + cls + '">' + escapar(m) + "</span>";
      ultimo = pos + m.length;
      return m;
    });
    return saida + escapar(codigo.slice(ultimo));
  }
  document.querySelectorAll("code.py").forEach(function (el) { el.innerHTML = realcar(el.textContent); });

  /* ------------------------------------------------------------ copiar */
  function copiarTexto(texto, botao) {
    function ok() {
      var original = botao.textContent;
      botao.textContent = "Copiado! 🦫";
      botao.classList.add("ok");
      setTimeout(function () { botao.textContent = original; botao.classList.remove("ok"); }, 1600);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(texto).then(ok, function () { copiarFallback(texto); ok(); });
    } else {
      copiarFallback(texto);
      ok();
    }
  }
  function copiarFallback(texto) {
    var area = document.createElement("textarea");
    area.value = texto;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(area);
  }
  document.querySelectorAll("[data-copiar]").forEach(function (b) {
    b.addEventListener("click", function () {
      copiarTexto(document.querySelector(b.getAttribute("data-copiar")).textContent, b);
    });
  });
  var copiarAtivo = document.querySelector("[data-copiar-ativo]");
  if (copiarAtivo) {
    copiarAtivo.addEventListener("click", function () {
      var painel = document.querySelector(".painel.ativo");
      if (painel) copiarTexto(painel.textContent, copiarAtivo);
    });
  }

  /* ------------------------------------------------------------ abas do editor (teclado acessível) */
  var abas = Array.prototype.slice.call(document.querySelectorAll(".aba"));
  function ativarAba(aba, focar) {
    abas.forEach(function (a) {
      var ativa = a === aba;
      a.classList.toggle("ativa", ativa);
      a.setAttribute("aria-selected", String(ativa));
      a.tabIndex = ativa ? 0 : -1;
      var painel = document.getElementById(a.getAttribute("aria-controls"));
      painel.hidden = !ativa;
      painel.classList.toggle("ativo", ativa);
    });
    if (focar) aba.focus();
  }
  abas.forEach(function (aba, i) {
    aba.addEventListener("click", function () { ativarAba(aba, false); });
    aba.addEventListener("keydown", function (e) {
      var alvo = null;
      if (e.key === "ArrowRight") alvo = abas[(i + 1) % abas.length];
      else if (e.key === "ArrowLeft") alvo = abas[(i - 1 + abas.length) % abas.length];
      else if (e.key === "Home") alvo = abas[0];
      else if (e.key === "End") alvo = abas[abas.length - 1];
      if (alvo) { e.preventDefault(); ativarAba(alvo, true); }
    });
  });

  /* ------------------------------------------------------------ troca de tela (screenshots) */
  var img = document.getElementById("tela-img");
  var chips = document.querySelectorAll(".telas-abas .chip");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      if (chip.classList.contains("ativo")) return;
      chips.forEach(function (c) {
        c.classList.toggle("ativo", c === chip);
        c.setAttribute("aria-selected", String(c === chip));
      });
      img.classList.add("trocando");
      var nova = new Image();
      nova.onload = function () {
        img.src = nova.src;
        img.alt = chip.getAttribute("data-alt");
        img.classList.remove("trocando");
      };
      nova.src = chip.getAttribute("data-tela");
    });
  });
  // pré-carrega as outras telas quando o navegador estiver ocioso
  (window.requestIdleCallback || setTimeout)(function () {
    chips.forEach(function (c) { new Image().src = c.getAttribute("data-tela"); });
  });

  /* ------------------------------------------------------------ easter egg: patinho na cabeça 🦆 */
  var capivara = document.getElementById("capivara");
  var cliques = 0;
  capivara.addEventListener("click", function () {
    cliques += 1;
    if (cliques >= 3) {
      capivara.classList.toggle("com-pato");
      cliques = 0;
    }
  });
})();
