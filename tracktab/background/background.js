chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ELEMENT_CAPTURED') {
    chrome.action.setBadgeText({
      text: String(message.payload.count),
      tabId: sender.tab?.id
    });
    chrome.action.setBadgeBackgroundColor({
      color: '#e94560',
      tabId: sender.tab?.id
    });
  }
  return false;
});
