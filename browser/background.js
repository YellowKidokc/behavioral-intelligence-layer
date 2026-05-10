/**
 * Bill — Background Service Worker v2
 * Tracks tab timing, bookmarks, GitHub repo data, and sends signals to BIL.
 */

const BIL_URL = "http://localhost:8420/bil/web";
const BIL_GITHUB_URL = "http://localhost:8420/bil/github";
const NAS_GITHUB_URL = "http://192.168.1.177:8420/github";

// Tab state map
const tabState = {};
const pendingSearchClicks = {};

// ── Tab activation ────────────────────────────────────────────────────────────
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const now = Date.now();

  // Close out previous active tab
  for (const [tabId, state] of Object.entries(tabState)) {
    if (state.active && parseInt(tabId) !== activeInfo.tabId) {
      state.active = false;
      state.totalTime += now - state.lastActive;
    }
  }

  // Start tracking new tab
  if (!tabState[activeInfo.tabId]) {
    try {
      const tab = await chrome.tabs.get(activeInfo.tabId);
      tabState[activeInfo.tabId] = freshState(tab.url, tab.title, true, now);
    } catch (e) {}
  } else {
    tabState[activeInfo.tabId].active = true;
    tabState[activeInfo.tabId].lastActive = now;
  }
});

// ── Tab navigation ────────────────────────────────────────────────────────────
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url && tabState[tabId]) {
    sendSignal(tabId);
    tabState[tabId] = freshState(changeInfo.url, tab.title, tabState[tabId]?.active, Date.now());
  }
});

// ── Tab closed ────────────────────────────────────────────────────────────────
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabState[tabId]) {
    if (tabState[tabId].active) {
      tabState[tabId].totalTime += Date.now() - tabState[tabId].lastActive;
    }
    sendSignal(tabId);
    delete tabState[tabId];
  }
});

// ── Bookmarks ─────────────────────────────────────────────────────────────────
chrome.bookmarks.onCreated.addListener(async (id, bookmark) => {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.url === bookmark.url && tabState[tab.id]) {
      tabState[tab.id].bookmarked = true;
    }
  }
});

// ── Messages from content script ──────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type === "rank_search_results") {
    rankSearchResults(message.results || []).then((data) => {
      chrome.tabs.sendMessage(sender.tab.id, {
        type: "ranked_search_results",
        data
      });
    });
    return true;
  }

  if (!sender.tab) return;
  const tabId = sender.tab.id;
  if (!tabState[tabId]) return;

  switch (message.type) {
    case "scroll_bottom":
      tabState[tabId].scrolledBottom = true;
      break;

    case "copied":
      tabState[tabId].copied = true;
      break;

    case "clipboard_text":
      tabState[tabId].copied = true;
      sendClipboardSignal(message.data || {}, sender.tab);
      break;

    case "search_result_click":
      pendingSearchClicks[message.data?.url] = {
        query: message.data?.query || "",
        position: message.data?.position ?? null,
        title: message.data?.title || "",
        source: sender.tab.url || "",
        clicked_at: Date.now(),
      };
      sendSkippedSearchSignals(message.data || {});
      break;

    case "github_data":
      // Merge GitHub-specific data into tab state
      if (message.data) {
        tabState[tabId].github = message.data;
      }
      break;

    case "page_meta":
      if (message.data) {
        tabState[tabId].text_length = message.data.text_length || 0;
        tabState[tabId].text_preview = message.data.text_preview || "";
      }
      break;
  }
});

async function rankSearchResults(results) {
  try {
    const response = await fetch("http://localhost:8420/bil/rank", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results })
    });
    return await response.json();
  } catch (e) {
    return { error: "rank_failed", results };
  }
}

// ── Signal sending ────────────────────────────────────────────────────────────
async function sendSignal(tabId) {
  const state = tabState[tabId];
  if (!state?.url) return;

  // Skip internal pages
  if (/^(chrome|edge|about|chrome-extension):/.test(state.url)) return;

  const timeOnPage = Math.round(state.totalTime / 1000);
  if (timeOnPage < 2) return;

  // Base web signal — always send
  const payload = {
    url: state.url,
    title: state.title || "",
    time_on_page: timeOnPage,
    scrolledBottom: state.scrolledBottom,
    copied: state.copied,
    bookmarked: state.bookmarked,
    text_length: state.text_length || 0,
    text_preview: state.text_preview || "",
  };

  const searchClick = pendingSearchClicks[state.url];
  if (searchClick) {
    payload.search_query = searchClick.query;
    payload.search_result_position = searchClick.position;
    payload.search_result_title = searchClick.title;
    payload.search_source = searchClick.source;
    delete pendingSearchClicks[state.url];
  }

  try {
    await fetch(BIL_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) {}

  // GitHub-specific signal — send separately if we have repo data
  if (state.github?.repo) {
    const ghPayload = {
      ...state.github,
      time_on_page: timeOnPage,
      copied_code: state.copied,
      bookmarked: state.bookmarked,
      scrolled_bottom: state.scrolledBottom,
      url: state.url,
      ts: new Date().toISOString(),
    };

    try {
      await fetch(BIL_GITHUB_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ghPayload)
      });
    } catch (e) {}

    // Also send to NAS PIL API
    try {
      await fetch(NAS_GITHUB_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ghPayload)
      });
    } catch (e) {}
  }
}

async function sendClipboardSignal(data, tab) {
  const text = (data.text || "").trim();
  if (!text) return;

  try {
    await fetch("http://localhost:8420/bil/clipboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text.slice(0, 5000),
        app: new URL(tab.url).hostname || "browser",
        used: false,
        url: tab.url,
        title: tab.title || ""
      })
    });
  } catch (e) {}
}

async function sendSkippedSearchSignals(data) {
  const skipped = data.skipped_results || [];
  for (const result of skipped.slice(0, 10)) {
    try {
      await fetch(BIL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: result.url,
          title: result.title,
          time_on_page: 0,
          scrolledBottom: false,
          copied: false,
          bookmarked: false,
          text_length: result.content?.length || 0,
          text_preview: result.content || result.title || "",
          search_query: data.query || "",
          search_result_position: result.position,
          search_source: "searxng_skipped",
        })
      });
    } catch (e) {}
  }
}

// ── Helper ────────────────────────────────────────────────────────────────────
function freshState(url, title, active, now) {
  return {
    url: url || "",
    title: title || "",
    active: !!active,
    lastActive: now,
    totalTime: 0,
    scrolledBottom: false,
    copied: false,
    bookmarked: false,
    text_length: 0,
    text_preview: "",
    github: null,
  };
}
