// SPDX-License-Identifier: CC0-1.0
// CHANGELOG: 2026-11-01 Preserve selected verses and modes, and complete chapter/verse controls.
// 2026-11-01 Use direct chapter/verse links and remove redundant selector labels.
// 2026-11-01 Restore selector context and the original long-chapter verse spacing.
// 2026-11-01 Separate verse choices with em spaces, matching the chapter choices.
// 2026-11-01 Do not create verse choices for book introductions.
// 2026-11-03 Generate chapter/verse bars in Python; leave their links and selection to HTML/CSS.
"use strict";
(() => {
  const header = document.getElementById("bibleNavigation");
  if (!header) return;
  const mode = header.dataset.mode;
  const shared = ["par", "lst", "ilr"].includes(mode);
  const routes = (link, wanted) => link?.getAttribute(`data-nav-${wanted.toLowerCase()}`);
  const verseNodes = [...document.querySelectorAll('[id]')].flatMap(node => {
    const match = /^(?:a)?C(\d+)V(\d+[a-z]*)$/.exec(node.id);
    return match ? [{node, chapter: match[1], verse: match[2]}] : [];
  });
  function selectedNode() {
    const hash = decodeURIComponent(location.hash.slice(1));
    let node = document.getElementById(hash);
    if (!/^(?:a)?(?:C\d|V\d)/.test(hash)) node = null;
    return node || verseNodes.find(row => row.chapter === header.dataset.chapter && row.verse === header.dataset.verse)?.node;
  }
  function parallelHref() {
    if (mode === "par" && /\/C\d+V\d+\.htm$/.test(location.pathname)) return location.href;
    const current = selectedNode();
    if (current) {
      const candidates = [current, current.nextElementSibling, current.closest('.verseText')];
      for (const node of candidates) {
        const link = node?.matches('a[href*="/par/"]') ? node : node?.querySelector('a[href*="/par/"]');
        if (link) return link.href;
      }
    }
    if (shared) {
      const link = document.querySelector('a[data-bible-mode="par"]');
      if (link && /\/C\d+V\d+\.htm$/.test(new URL(link.href).pathname)) return link.href;
    }
    return null;
  }
  function selectedVersion() {
    const hash = decodeURIComponent(location.hash.slice(1));
    return shared && [...header.querySelectorAll('[data-bible-version]')].some(link => link.dataset.bibleVersion === hash)
      ? hash : header.dataset.version;
  }
  const fetches = new Map();
  function refreshStudyLinks() {
    const href = parallelHref();
    if (!href || !/\/C\d+V[1-9]\d*\.htm/.test(href)) return;
    for (const link of header.querySelectorAll('[data-bible-mode]')) {
      const wanted = link.dataset.bibleMode;
      if (["par", "lst", "ilr"].includes(wanted)
          && (wanted !== "ilr" || /\/C\d+V\d+\.htm/.test(link.href))) {
        link.href = href.replace("/par/", `/${wanted}/`).replace(/#.*$/, "#Top");
      }
    }
  }
  async function mappedRoutes(version) {
    const href = parallelHref();
    if (!href) return null;
    const url = new URL(href, location.href); url.hash = "";
    let page;
    if (url.pathname === location.pathname) page = document;
    else {
      if (!fetches.has(url.href)) fetches.set(url.href, fetch(url).then(response => {
        if (!response.ok) throw new Error("Reference navigation unavailable");
        return response.text();
      }).then(text => new DOMParser().parseFromString(text, "text/html")));
      page = await fetches.get(url.href);
    }
    const link = [...page.querySelectorAll('[data-bible-version]')].find(link => link.dataset.bibleVersion === version);
    return link ? {link, url} : null;
  }
  async function refreshDestinations() {
    const startingURL = location.href;
    refreshStudyLinks();
    try {
      const mapped = await mappedRoutes(selectedVersion());
      if (!mapped || location.href !== startingURL) return;
      if (!shared && mode !== "rel") {
        const targets = [...mapped.link.ownerDocument.querySelectorAll('[data-bible-version]')];
        for (const link of header.querySelectorAll('[data-bible-version]')) {
          const target = targets.find(item => item.dataset.bibleVersion === link.dataset.bibleVersion);
          const href = routes(target, mode) || routes(target, "byC");
          if (href) link.href = new URL(href, mapped.url).href;
        }
      }
      for (const link of header.querySelectorAll('[data-bible-mode]')) {
        const href = routes(mapped.link, link.dataset.bibleMode);
        if (href) link.href = new URL(href, mapped.url).href;
      }
    } catch (_) { /* Keep the valid, statically generated fallback links. */ }
  }
  window.addEventListener("hashchange", refreshDestinations);
  if (location.hash && location.hash !== "#Top") refreshDestinations();
  let opening = false;
  header.addEventListener("click", async event => {
    const link = event.target.closest("a[data-bible-version], a[data-bible-mode]");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (link.dataset.bibleVersion && (shared || mode === "rel")) return;
    if (link.getAttribute("href").startsWith("#")) return;
    if (link.dataset.bibleMode === "rel") return;
    const wanted = link.dataset.bibleMode || (shared || mode === "rel" ? "byC" : mode);
    if (!["byC", "bySec", "byDoc", "rel"].includes(wanted)) {
      // Existing mapped verse links provide the common study-view address.
      const href = parallelHref();
      if (href && ["par", "lst", "ilr"].includes(wanted) && /\/C\d+V[1-9]\d*\.htm/.test(href)) {
        // Interlinear availability is narrower; use its generated mode link.
        if (wanted !== "ilr" || /\/C\d+V\d+\.htm/.test(link.href)) link.href = href.replace("/par/", `/${wanted}/`).replace(/#.*$/, "#Top");
      }
      return;
    }
    if (!parallelHref()) return;
    event.preventDefault();
    if (opening) return;
    opening = true;
    const fallback = link.href;
    const notice = document.createElement("span"); notice.setAttribute("role", "status"); notice.textContent = " Opening passage…"; header.append(notice);
    try {
      const destination = await mappedRoutes(link.dataset.bibleVersion || selectedVersion());
      const href = destination && (routes(destination.link, wanted) || routes(destination.link, "byC"));
      location.assign(href ? new URL(href, destination.url).href : fallback);
    } catch (_) { location.assign(fallback); }
    finally { notice.remove(); opening = false; }
  });

})();
