(() => {
  let isRecording = false;
  let capturedElements = [];
  let overlay = null;
  let highlightBox = null;
  let listenersAttached = false;

  const ELEMENT_DESCRIPTIONS = {
    'a': 'Link',
    'button': 'Botão',
    'input': 'Input',
    'select': 'Select',
    'textarea': 'Textarea',
    'img': 'Imagem',
    'h1': 'Título H1',
    'h2': 'Título H2',
    'h3': 'Título H3',
    'h4': 'Título H4',
    'h5': 'Título H5',
    'h6': 'Título H6',
    'label': 'Label',
    'li': 'Item de Lista',
    'tr': 'Linha de Tabela',
    'td': 'Célula de Tabela',
    'th': 'Cabeçalho de Tabela',
    'div': 'Div',
    'span': 'Span',
    'p': 'Parágrafo',
    'nav': 'Navegação',
    'header': 'Cabeçalho',
    'footer': 'Rodapé',
    'section': 'Seção',
    'article': 'Artigo',
    'aside': 'Barra Lateral',
    'main': 'Conteúdo Principal',
    'form': 'Formulário',
    'table': 'Tabela',
    'ul': 'Lista',
    'ol': 'Lista Ordenada',
    'iframe': 'iFrame',
    'video': 'Vídeo',
    'audio': 'Áudio',
    'svg': 'SVG',
    'canvas': 'Canvas',
  };

  function getElementName(el) {
    const tag = el.tagName.toLowerCase();
    const description = ELEMENT_DESCRIPTIONS[tag] || tag;

    const text = (el.textContent || '').trim().substring(0, 50);
    const id = el.id || '';
    const ariaLabel = el.getAttribute('aria-label') || '';
    const placeholder = el.getAttribute('placeholder') || '';
    const name = el.getAttribute('name') || '';
    const type = el.getAttribute('type') || '';
    const alt = el.getAttribute('alt') || '';
    const title = el.getAttribute('title') || '';

    let label = '';
    if (text) label = text;
    else if (ariaLabel) label = ariaLabel;
    else if (placeholder) label = placeholder;
    else if (alt) label = alt;
    else if (title) label = title;
    else if (name) label = name;
    else if (id) label = id;

    if (tag === 'input' && type) {
      label = label ? `${label} (${type})` : type;
    }

    return label ? `${description} "${label}"` : description;
  }

  function escapeXPathString(str) {
    if (!str.includes('"')) return `"${str}"`;
    if (!str.includes("'")) return `'${str}'`;
    return `concat(${str.split('"').map((p, i) =>
      i === 0 ? `"${p}"` : `,'"',"${p}"`
    ).join('')})`;
  }

  function isUniqueXPath(xpath) {
    try {
      const result = document.evaluate(xpath, document, null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      return result.snapshotLength === 1;
    } catch {
      return false;
    }
  }

  function getFullXpath(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      if (current === document.documentElement) {
        parts.unshift('/html');
        break;
      }
      if (current === document.body) {
        parts.unshift('/body');
        current = document.documentElement;
        continue;
      }

      const tag = current.tagName.toLowerCase();
      const parent = current.parentElement;
      if (!parent) {
        parts.unshift(`/${tag}`);
        break;
      }

      const siblings = [...parent.children].filter(c => c.tagName === current.tagName);
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        parts.unshift(`${tag}[${index}]`);
      } else {
        parts.unshift(tag);
      }
      current = parent;
    }
    return '/' + parts.join('/');
  }

  function relativeAnchor(nd) {
    if (nd.id) {
      const xpath = `//*[@id=${escapeXPathString(nd.id)}]`;
      if (isUniqueXPath(xpath)) return xpath;
    }
    const cls = buildSelector(nd);
    if (cls && !cls.includes("'")) {
      const xpath = `//${nd.tagName.toLowerCase()}[contains(@class,'${cls}')]`;
      if (isUniqueXPath(xpath)) return xpath;
    }
    return '';
  }

  function getShortRelative(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';

    const chain = [el];
    let cur = el.parentElement;
    while (cur && cur.nodeType === Node.ELEMENT_NODE && cur !== document.body) {
      chain.push(cur);
      cur = cur.parentElement;
    }

    for (let i = 0; i < chain.length; i++) {
      const root = relativeAnchor(chain[i]);
      if (!root) continue;
      let xpath = root;
      for (let j = i - 1; j >= 0; j--) {
        xpath += '/' + customStep(chain[j]);
      }
      if (isUniqueXPath(xpath)) return xpath;
    }
    return '';
  }

  function getRelativeXpath(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';

    if (el.id) {
      const xpath = `//*[@id=${escapeXPathString(el.id)}]`;
      if (isUniqueXPath(xpath)) return xpath;
    }

    for (const attr of ['data-testid', 'data-test-id', 'data-cy', 'aria-label', 'name', 'role']) {
      const val = el.getAttribute(attr);
      if (val) {
        const xpath = `//*[${attr}=${escapeXPathString(val)}]`;
        if (isUniqueXPath(xpath)) return xpath;
      }
    }

    const text = (el.textContent || '').trim();
    if (text && el.children.length === 0 && text.length < 80) {
      const xpath = `//*[text()=${escapeXPathString(text)}]`;
      if (isUniqueXPath(xpath)) return xpath;
    }

    const short = getShortRelative(el);
    if (short) return short;

    return getCustomPath(el);
  }

  function customStep(nd) {
    const tag = nd.tagName.toLowerCase();
    const parent = nd.parentElement;
    const sibs = parent ? [...parent.children].filter(c => c.tagName === nd.tagName) : [nd];
    if (sibs.length > 1) {
      return `${tag}[${sibs.indexOf(nd) + 1}]`;
    }
    const cls = buildSelector(nd);
    if (cls && !cls.includes("'")) {
      return `${tag}[contains(@class,'${cls}')]`;
    }
    return tag;
  }

  function getCustomPath(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';

    if (el.id) {
      const xpath = `//*[@id=${escapeXPathString(el.id)}]`;
      if (isUniqueXPath(xpath)) return xpath;
    }

    const chain = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      chain.unshift(current);
      if (current === document.documentElement) break;
      current = current.parentElement;
    }

    let root = -1;
    for (let i = 1; i < chain.length; i++) {
      const nd = chain[i];
      if (nd.id) {
        const xpath = `//*[@id=${escapeXPathString(nd.id)}]`;
        if (isUniqueXPath(xpath)) { root = i; break; }
      }
    }

    let xpath;
    if (root === -1) {
      xpath = '//html';
      root = 0;
    } else {
      xpath = `//*[@id=${escapeXPathString(chain[root].id)}]`;
    }

    for (let i = root + 1; i < chain.length; i++) {
      xpath += '/' + customStep(chain[i]);
    }

    if (isUniqueXPath(xpath)) return xpath;

    return getFullXpath(el);
  }

  function buildSelector(el) {
    const classes = [...el.classList].filter(c => !c.startsWith('css-') && !c.startsWith('sc-'));
    return classes.join('.');
  }

  function getElementData(el) {
    const tag = el.tagName.toLowerCase();
    return {
      name: getElementName(el),
      tag: tag,
      text: (el.textContent || '').trim().substring(0, 200),
      fullXpath: getFullXpath(el),
      relativeXpath: getRelativeXpath(el),
      customPath: getCustomPath(el)
    };
  }

  function createOverlay() {
    if (overlay) return;

    const host = document.createElement('div');
    host.id = 'tracktab-overlay-root';
    host.style.cssText = 'position: fixed; top: 0; left: 0; z-index: 2147483647; pointer-events: none;';
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: 'open' });

    const style = document.createElement('style');
    style.textContent = `
      .tracktab-banner {
        position: fixed;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #e94560, #c23152);
        color: white;
        padding: 10px 24px;
        border-radius: 24px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(233, 69, 96, 0.4);
        z-index: 2147483647;
        display: flex;
        align-items: center;
        gap: 8px;
        pointer-events: none;
        animation: tracktab-slide-in 0.3s ease-out;
      }
      .tracktab-dot {
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: tracktab-blink 1.5s infinite;
      }
      @keyframes tracktab-slide-in {
        from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
      }
      @keyframes tracktab-blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
      }
    `;
    shadow.appendChild(style);

    const banner = document.createElement('div');
    banner.className = 'tracktab-banner';
    banner.innerHTML = '<span class="tracktab-dot"></span> TrackTab - Modo Gravador';
    shadow.appendChild(banner);

    highlightBox = document.createElement('div');
    highlightBox.style.cssText = `
      position: absolute;
      border: 2px solid #e94560;
      background: rgba(233, 69, 96, 0.1);
      border-radius: 4px;
      pointer-events: none;
      display: none;
      z-index: 2147483646;
      transition: all 0.1s ease;
    `;
    shadow.appendChild(highlightBox);

    overlay = host;
  }

  function removeOverlay() {
    if (overlay) {
      overlay.remove();
      overlay = null;
      highlightBox = null;
    }
  }

  function highlightElement(el) {
    if (!highlightBox) return;
    const rect = el.getBoundingClientRect();
    highlightBox.style.display = 'block';
    highlightBox.style.left = `${rect.left}px`;
    highlightBox.style.top = `${rect.top}px`;
    highlightBox.style.width = `${rect.width}px`;
    highlightBox.style.height = `${rect.height}px`;
  }

  function clearHighlight() {
    if (highlightBox) {
      highlightBox.style.display = 'none';
    }
  }

  function handleClick(e) {
    if (!isRecording) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();

    const el = e.target;
    if (!el || el === document.documentElement || el === document.body) return;

    const data = getElementData(el);
    const alreadyCaptured = capturedElements.some(
      existing => existing.fullXpath === data.fullXpath && existing.customPath === data.customPath
    );

    if (!alreadyCaptured) {
      capturedElements.push(data);
      chrome.runtime.sendMessage({
        type: 'ELEMENT_CAPTURED',
        payload: { count: capturedElements.length }
      });
    }

    showCaptureFeedback(el);
  }

  function handleMouseOver(e) {
    if (!isRecording) return;
    highlightElement(e.target);
  }

  function handleMouseOut(e) {
    if (!isRecording) return;
    clearHighlight();
  }

  function showCaptureFeedback(el) {
    const host = document.createElement('div');
    host.style.cssText = 'position: fixed; z-index: 2147483647; pointer-events: none;';
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = `
      .tracktab-feedback {
        position: fixed;
        background: #2ecc71;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        animation: tracktab-fade 1.5s forwards;
        white-space: nowrap;
      }
      @keyframes tracktab-fade {
        0% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-20px); }
      }
    `;
    shadow.appendChild(style);

    const feedback = document.createElement('div');
    feedback.className = 'tracktab-feedback';
    feedback.textContent = 'Capturado!';
    shadow.appendChild(feedback);

    const rect = el.getBoundingClientRect();
    feedback.style.left = `${rect.left}px`;
    feedback.style.top = `${rect.top - 10}px`;

    setTimeout(() => host.remove(), 1500);
  }

  function handleKeyDown(e) {
    if (e.key === 'Escape' && isRecording) {
      stopRecording();
    }
  }

  function startRecording() {
    if (isRecording) return;
    isRecording = true;
    createOverlay();
    if (!listenersAttached) {
      document.addEventListener('click', handleClick, true);
      document.addEventListener('mouseover', handleMouseOver, true);
      document.addEventListener('mouseout', handleMouseOut, true);
      document.addEventListener('keydown', handleKeyDown, true);
      listenersAttached = true;
    }
    chrome.storage.session.set({ isRecording: true });
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    removeOverlay();
    if (listenersAttached) {
      document.removeEventListener('click', handleClick, true);
      document.removeEventListener('mouseover', handleMouseOver, true);
      document.removeEventListener('mouseout', handleMouseOut, true);
      document.removeEventListener('keydown', handleKeyDown, true);
      listenersAttached = false;
    }
    chrome.storage.session.set({ isRecording: false });
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case 'START_RECORDING':
        startRecording();
        sendResponse({ success: true, isRecording });
        break;

      case 'STOP_RECORDING':
        stopRecording();
        sendResponse({ elements: [...capturedElements] });
        break;

      case 'GET_STATUS':
        sendResponse({ isRecording, count: capturedElements.length });
        break;

      case 'GET_ELEMENTS':
        sendResponse({ elements: [...capturedElements] });
        break;

      case 'CLEAR_ELEMENTS':
        capturedElements = [];
        sendResponse({ success: true });
        break;
    }
    return true;
  });

  chrome.storage.session.get('isRecording', (data) => {
    if (data.isRecording && !isRecording) {
      startRecording();
    }
  });
})();
