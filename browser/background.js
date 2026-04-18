// BIL browser extension — service worker.
//
// Collects per-tab behavioral signals (time on page, scroll depth, copy count,
// word count, bookmark state) in chrome.storage.session and flushes them to the
// self-hosted BIL server when the tab closes.
//
// Servers are tried in order; first successful POST wins.
const BIL_ENDPOINTS = [
  "http://192.168.1.177:8420/bil/web",
  "http://localhost:8420/bil/web",
];

const TAB_KEY = (tabId) => `tab_${tabId}`;

// ---- storage helpers -------------------------------------------------------

async function getTabState(tabId) {
  const key = TAB_KEY(tabId);
  const store = await chrome.storage.session.get(key);
  return store[key] || null;
}

async function setTabState(tabId, state) {
  await chrome.storage.session.set({ [TAB_KEY(tabId)]: state });
}

async function clearTabState(tabId) {
  await chrome.storage.session.remove(TAB_KEY(tabId));
}

// ---- signal shaping --------------------------------------------------------

function buildPayload(state) {
  const domain = (() => {
    try { return new URL(state.url).hostname; } catch { return ""; }
  })();
  return {
    url: state.url || "",
    title: state.title || "",
    domain,
    time_on_page: Math.round((state.time_on_page || 0)),
    scroll_depth: Math.min(1, Math.max(0, state.scroll_depth || 0)),
    copy_count: state.copy_count || 0,
    bookmarked: !!state.bookmarked,
    word_count: state.word_count || 0,
  };
}

async function sendSignal(payload) {
  for (const endpoint of BIL_ENDPOINTS) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) return true;
    } catch (_err) {
      // Try next endpoint.
    }
  }
  return false;
}

// ---- content-script message channel ---------------------------------------

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!sender.tab || msg?.type !== "TAB_UPDATE") return;
  const tabId = sender.tab.id;
  (async () => {
    const prev = (await getTabState(tabId)) || {};
    const merged = {
      ...prev,
      ...msg.data,
      url: sender.tab.url,
      title: sender.tab.title,
    };
    await setTabState(tabId, merged);
    sendResponse({ ok: true });
  })();
  return true; // keep the message channel open for the async response.
});

// ---- tab lifecycle ---------------------------------------------------------

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "loading" || !changeInfo.url) return;
  // Fresh navigation — flush any existing state first, then reset.
  const prev = await getTabState(tabId);
  if (prev && prev.url) {
    const payload = buildPayload(prev);
    if (payload.time_on_page > 2) await sendSignal(payload);
  }
  await setTabState(tabId, {
    url: changeInfo.url,
    title: tab.title || "",
    time_on_page: 0,
    scroll_depth: 0,
    copy_count: 0,
    word_count: 0,
    bookmarked: false,
  });
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  const state = await getTabState(tabId);
  if (!state || !state.url) {
    await clearTabState(tabId);
    return;
  }
  const payload = buildPayload(state);
  // Don't send noise from insta-closed tabs.
  if (payload.time_on_page >= 2) await sendSignal(payload);
  await clearTabState(tabId);
});

// ---- bookmarks -------------------------------------------------------------

chrome.bookmarks.onCreated.addListener(async (_id, bookmark) => {
  if (!bookmark.url) return;
  const tabs = await chrome.tabs.query({ url: bookmark.url });
  for (const t of tabs) {
    const state = (await getTabState(t.id)) || {};
    state.bookmarked = true;
    await setTabState(t.id, state);
  }
});
