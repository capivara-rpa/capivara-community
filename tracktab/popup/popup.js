const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');
const btnClear = document.getElementById('btnClear');
const btnExportJson = document.getElementById('btnExportJson');
const btnExportTxt = document.getElementById('btnExportTxt');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const counterSection = document.getElementById('counterSection');
const counterValue = document.getElementById('counterValue');
const elementsList = document.getElementById('elementsList');
const elementsUl = document.getElementById('elementsUl');
const exportSection = document.getElementById('exportSection');

let isRecording = false;

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function executeInContent(code) {
  const tab = await getActiveTab();
  if (!tab) return null;
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.__tracktabResult,
    });
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: 'MAIN',
      func: (cmd) => { window.__tracktabCommand = cmd; },
      args: [code],
    });
    await new Promise(r => setTimeout(r, 50));
    const res = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const r = window.__tracktabResult;
        window.__tracktabResult = undefined;
        return r;
      },
    });
    return res?.[0]?.result ?? null;
  } catch (e) {
    console.error('TrackTab execute error:', e);
    return null;
  }
}

async function sendMessageToContent(message) {
  const tab = await getActiveTab();
  if (!tab) return null;
  try {
    return await chrome.tabs.sendMessage(tab.id, message);
  } catch {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content/content.js'],
      });
      await new Promise(r => setTimeout(r, 100));
      return await chrome.tabs.sendMessage(tab.id, message);
    } catch {
      return null;
    }
  }
}

function updateUI(recording, elements = []) {
  isRecording = recording;

  if (recording) {
    btnStart.disabled = true;
    btnStop.disabled = false;
    statusDot.classList.add('recording');
    statusText.textContent = 'Gravando... clique nos elementos';
    counterSection.style.display = 'flex';
    elementsList.style.display = 'block';
    exportSection.style.display = 'none';
  } else {
    btnStart.disabled = false;
    btnStop.disabled = true;
    statusDot.classList.remove('recording');
    statusText.textContent = elements.length > 0
      ? `${elements.length} elemento(s) capturado(s)`
      : 'Pronto para gravar';
    counterSection.style.display = elements.length > 0 ? 'flex' : 'none';
    elementsList.style.display = elements.length > 0 ? 'block' : 'none';
    exportSection.style.display = elements.length > 0 ? 'flex' : 'none';
  }

  counterValue.textContent = elements.length;
  renderElements(elements);
}

function renderElements(elements) {
  elementsUl.innerHTML = '';
  elements.forEach((el) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="element-tag">${el.tag}</span>
      <span class="element-name" title="${el.name}">${el.name}</span>
    `;
    elementsUl.appendChild(li);
  });
}

btnStart.addEventListener('click', async () => {
  let response = await sendMessageToContent({ type: 'START_RECORDING' });
  if (response?.success) {
    await chrome.storage.session.set({ isRecording: true });
    updateUI(true, []);
  } else {
    statusText.textContent = 'Erro ao iniciar. Recarregue a página.';
  }
});

btnStop.addEventListener('click', async () => {
  const response = await sendMessageToContent({ type: 'STOP_RECORDING' });
  await chrome.storage.session.set({ isRecording: false });
  const elements = response?.elements || [];
  updateUI(false, elements);
});

btnClear.addEventListener('click', async () => {
  await sendMessageToContent({ type: 'CLEAR_ELEMENTS' });
  updateUI(false, []);
});

btnExportJson.addEventListener('click', async () => {
  const response = await sendMessageToContent({ type: 'GET_ELEMENTS' });
  const elements = response?.elements || [];
  if (elements.length === 0) return;

  const tab = await getActiveTab();
  const exportData = {
    page: tab?.url || '',
    title: tab?.title || '',
    timestamp: new Date().toISOString(),
    elements: elements.map(el => ({
      name: el.name,
      tag: el.tag,
      text: el.text,
      fullXpath: el.fullXpath,
      relativeXpath: el.relativeXpath,
      customPath: el.customPath
    }))
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tracktab-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
});

btnExportTxt.addEventListener('click', async () => {
  const response = await sendMessageToContent({ type: 'GET_ELEMENTS' });
  const elements = response?.elements || [];
  if (elements.length === 0) return;

  const tab = await getActiveTab();
  const header = `TrackTab Export\nPage: ${tab?.url || ''}\nTitle: ${tab?.title || ''}\nDate: ${new Date().toISOString()}\n${'='.repeat(100)}\n`;
  const colHeaders = `${'Elemento'.padEnd(30)}| ${'Full XPath'.padEnd(40)}| ${'Relative XPath'.padEnd(35)}| Custom Path`;
  const separator = `${'-'.repeat(30)}| ${'-'.repeat(40)}| ${'-'.repeat(35)}| ${'-'.repeat(40)}`;

  const rows = elements.map(el =>
    `${el.name.padEnd(30)}| ${el.fullXpath.padEnd(40)}| ${el.relativeXpath.padEnd(35)}| ${el.customPath}`
  );

  const content = [header, colHeaders, separator, ...rows].join('\n');
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tracktab-${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
});

chrome.storage.session.get('isRecording', async (data) => {
  if (data.isRecording) {
    const response = await sendMessageToContent({ type: 'GET_STATUS' });
    if (response?.isRecording) {
      const elementsResponse = await sendMessageToContent({ type: 'GET_ELEMENTS' });
      const elements = elementsResponse?.elements || [];
      updateUI(true, elements);
    } else {
      await chrome.storage.session.set({ isRecording: false });
      updateUI(false, []);
    }
  }
});
