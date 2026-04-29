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

// Send text length once on load
window.addEventListener("load", () => {
  chrome.runtime.sendMessage({
    type: "page_meta",
    data: {
      text_length: getTextLength(),
      title: document.title,
    }
  });
}, { once: true });
