// BIL browser extension — content script.
//
// Tracks per-page engagement signals and ships them to the background service
// worker, which batches them per-tab and POSTs on tab close.
(() => {
  const start = Date.now();
  let maxScrollDepth = 0;
  let copyCount = 0;

  // Re-sampled on every flush so SPAs that inject content over time (Twitter,
  // GitHub, infinite-scroll feeds) get an accurate count instead of the empty
  // shell that loaded at document_idle.
  const estimateWordCount = () => {
    const txt = (document.body && document.body.innerText) || "";
    if (!txt) return 0;
    return txt.trim().split(/\s+/).filter(Boolean).length;
  };

  let wordCount = estimateWordCount();

  // Cap on the text snippet shipped to BIL so YAKE has something to work on
  // without bloating the payload. The body text on most articles is well under
  // this; long pages get truncated. Goes only to your self-hosted server.
  const TEXT_SNIPPET_CHARS = 5000;
  const sampleText = () => {
    const txt = (document.body && document.body.innerText) || "";
    return txt.slice(0, TEXT_SNIPPET_CHARS);
  };

  const updateScroll = () => {
    const height = Math.max(
      document.body.scrollHeight || 0,
      document.documentElement.scrollHeight || 0
    );
    const viewport = window.innerHeight || 0;
    const scrolled = (window.scrollY || window.pageYOffset || 0) + viewport;
    if (height <= 0) return;
    const depth = Math.min(1, scrolled / height);
    if (depth > maxScrollDepth) maxScrollDepth = depth;
  };

  window.addEventListener("scroll", updateScroll, { passive: true });
  updateScroll();

  document.addEventListener("copy", () => {
    copyCount += 1;
  });

  const snapshot = () => {
    const fresh = estimateWordCount();
    if (fresh > wordCount) wordCount = fresh;
    return {
      time_on_page: (Date.now() - start) / 1000,
      scroll_depth: maxScrollDepth,
      copy_count: copyCount,
      word_count: wordCount,
      text: sampleText(),
    };
  };

  const send = () => {
    try {
      chrome.runtime.sendMessage({ type: "TAB_UPDATE", data: snapshot() });
    } catch (_err) {
      // Extension context invalidated (reload) — ignore.
    }
  };

  // Periodic flush so long-lived tabs still report progress.
  const flushInterval = setInterval(send, 30_000);

  window.addEventListener("beforeunload", () => {
    clearInterval(flushInterval);
    send();
  });

  window.addEventListener("pagehide", send);
  // Initial beacon so the background worker knows the page exists.
  send();
})();
