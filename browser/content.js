/**
 * Bill — Content Script v2
 * Tracks scroll, copy, and GitHub-specific repo data.
 * Sends messages to background — never contacts BIL directly.
 */

// ── Scroll tracking ───────────────────────────────────────────────────────────
let sentScrollBottom = false;

window.addEventListener("scroll", () => {
  if (sentScrollBottom) return;
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const scrollHeight = document.documentElement.scrollHeight;
  const clientHeight = document.documentElement.clientHeight;
  if (scrollTop + clientHeight >= scrollHeight - 100) {
    sentScrollBottom = true;
    chrome.runtime.sendMessage({ type: "scroll_bottom" });
  }
}, { passive: true });

// ── Copy tracking ─────────────────────────────────────────────────────────────
let sentCopied = false;

document.addEventListener("copy", () => {
  if (sentCopied) return;
  sentCopied = true;
  chrome.runtime.sendMessage({ type: "copied" });

  const text = window.getSelection()?.toString() || "";
  if (text.trim()) {
    chrome.runtime.sendMessage({
      type: "clipboard_text",
      data: { text: text.trim() }
    });
  }
});

// ── GitHub repo extraction ────────────────────────────────────────────────────
function getGitHubRepoData() {
  if (!location.hostname.includes("github.com")) return null;

  const parts = location.pathname.split("/").filter(Boolean);
  if (parts.length < 2) return null;

  const repo = `${parts[0]}/${parts[1]}`;

  // Stars
  const starsEl = document.querySelector('[href$="/stargazers"] .Counter')
    || document.querySelector('#repo-stars-counter-star')
    || document.querySelector('[aria-label*="star"]');
  const stars = starsEl?.textContent?.trim() || "0";

  // Forks
  const forksEl = document.querySelector('[href$="/forks"] .Counter')
    || document.querySelector('#repo-network-counter');
  const forks = forksEl?.textContent?.trim() || "0";

  // Language
  const langEl = document.querySelector('[data-testid="repo-language-color"] + span')
    || document.querySelector('.d-inline .color-fg-default');
  const language = langEl?.textContent?.trim() || "";

  // Topics
  const topicEls = document.querySelectorAll('[data-octo-click="topic_click"]');
  const topics = Array.from(topicEls).map(el => el.textContent.trim()).slice(0, 10);

  // Description
  const descEl = document.querySelector('p.f4.my-3')
    || document.querySelector('[data-testid="repository-description"]');
  const description = descEl?.textContent?.trim() || "";

  // README presence (proxy for quality)
  const hasReadme = !!document.querySelector('#readme');

  // Are we viewing a specific file?
  const viewingFile = parts.length > 3 && parts[2] === "blob";
  const filePath = viewingFile ? parts.slice(3).join("/") : null;

  // Is the user on issues, PRs, actions, etc.?
  const section = parts[2] || "root";

  return {
    repo,
    stars,
    forks,
    language,
    topics,
    description: description.slice(0, 200),
    has_readme: hasReadme,
    section,            // "root" | "issues" | "pulls" | "blob" | etc.
    file_path: filePath,
  };
}

// Send GitHub data when page is ready
if (location.hostname.includes("github.com")) {
  // Wait for dynamic content to settle
  setTimeout(() => {
    const data = getGitHubRepoData();
    if (data) {
      chrome.runtime.sendMessage({ type: "github_data", data });
    }
  }, 1500);

  // Also re-send if the page updates (GitHub is a SPA)
  const observer = new MutationObserver(() => {
    const data = getGitHubRepoData();
    if (data) {
      chrome.runtime.sendMessage({ type: "github_data", data });
    }
  });
  // Watch for major DOM changes only
  observer.observe(document.querySelector("title") || document.head, {
    childList: true, subtree: false
  });
}

// ── Page text length (proxy for content density) ──────────────────────────────
function getTextLength() {
  const body = document.body?.innerText || "";
  return Math.min(body.length, 50000);
}

function getTextPreview() {
  const body = document.body?.innerText || "";
  return body.replace(/\s+/g, " ").trim().slice(0, 4000);
}

// Send text length once on load
window.addEventListener("load", () => {
  chrome.runtime.sendMessage({
    type: "page_meta",
    data: {
      text_length: getTextLength(),
      text_preview: getTextPreview(),
      title: document.title,
    }
  });
}, { once: true });

// SearXNG result re-ranking. This runs after results load and never blocks the page.
function collectSearxngResults() {
  const nodes = Array.from(document.querySelectorAll("#urls .result, article.result, .result"))
    .filter(node => node.querySelector("a[href]"));

  return nodes.slice(0, 20).map((node, index) => {
    const link = node.querySelector("h3 a[href], a[href]");
    const snippet = node.querySelector(".content, p");
    const engine = node.querySelector(".engines, .engine");
    return {
      _index: index,
      url: link?.href || "",
      title: link?.textContent?.trim() || "",
      content: snippet?.textContent?.trim() || "",
      engine: engine?.textContent?.trim() || "searxng",
      score: Math.max(1, 20 - index),
    };
  }).filter(result => result.url && result.title);
}

function applySearxngRanking(rankedResults) {
  const nodes = Array.from(document.querySelectorAll("#urls .result, article.result, .result"))
    .filter(node => node.querySelector("a[href]"));
  if (!nodes.length || !rankedResults?.length) return;

  const parent = nodes[0].parentElement;
  if (!parent) return;

  const byUrl = new Map();
  nodes.forEach(node => {
    const link = node.querySelector("h3 a[href], a[href]");
    if (link?.href) byUrl.set(link.href, node);
  });

  rankedResults.forEach((result, index) => {
    const node = byUrl.get(result.url);
    if (!node) return;
    node.dataset.bilRanked = "true";
    let badge = node.querySelector(".bil-rank-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "bil-rank-badge";
      badge.style.cssText = "display:inline-block;margin-left:8px;padding:2px 6px;border-radius:6px;background:#f59e0b22;color:#b45309;font-size:11px;font-weight:600;";
      const title = node.querySelector("h3") || node;
      title.appendChild(badge);
    }
    badge.textContent = `BIL ${index + 1} · ${result.final_score ?? result.bil_score ?? ""}`;
    parent.appendChild(node);
  });
}

function maybeRankSearxng() {
  const looksLikeSearxng = location.pathname.includes("search")
    || document.querySelector('input[name="q"]')
    || document.querySelector("#urls");
  if (!looksLikeSearxng) return;

  const results = collectSearxngResults();
  if (!results.length) return;
  chrome.runtime.sendMessage({ type: "rank_search_results", results });
}

document.addEventListener("click", (event) => {
  const link = event.target?.closest?.("a[href]");
  if (!link) return;

  const resultNode = link.closest("#urls .result, article.result, .result");
  if (!resultNode) return;

  const results = Array.from(document.querySelectorAll("#urls .result, article.result, .result"))
    .filter(node => node.querySelector("a[href]"));
  const position = results.indexOf(resultNode) + 1;
  if (position <= 0) return;

  const query = document.querySelector('input[name="q"]')?.value
    || new URLSearchParams(location.search).get("q")
    || "";

  chrome.runtime.sendMessage({
    type: "search_result_click",
    data: {
      query,
      position,
      url: link.href,
      title: link.textContent?.trim() || "",
    }
  });
}, true);

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "ranked_search_results" && message.data?.results) {
    applySearxngRanking(message.data.results);
  }
});

window.addEventListener("load", () => {
  setTimeout(maybeRankSearxng, 800);
}, { once: true });
