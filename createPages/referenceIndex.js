// SPDX-License-Identifier: CC0-1.0
// 2026-10-31 Search static indexes and keep the displayed list bounded.
// 2026-11-01 Accept ordinary-letter transliterations and browse grouped word occurrences.
"use strict";
(() => {
  // NFKD also expands superscript/subscript vowels. These remaining letters do
  // not decompose; readers can type their ordinary keyboard equivalents.
  const letters = { "ⱪ": "k", "ⱱ": "v", "ɽ": "r", "ə": "e", "ʦ": "ts", "æ": "ae", "œ": "oe" };
  const normalise = text => text.normalize("NFKD").toLowerCase().replace(/\p{M}/gu, "")
    .replace(/[ⱪⱱɽəʦæœ]/gu, letter => letters[letter])
    .replace(/['’ʼˊʹʾʿ\u2060\u200b]/gu, "").replace(/ς/gu, "σ");
  const node = (tag, text) => { const result = document.createElement(tag); if (text !== undefined) result.textContent = text; return result; };
  const referenceLabel = ref => ref.replace("_", " ").replace("w", ", word ");
  const quantity = (count, noun) => `${count.toLocaleString()} ${noun}${count === 1 ? "" : "s"}`;
  const pageSize = 25;

  async function initialiseWords(browser) {
    const response = await fetch(browser.dataset.source);
    if (!response.ok) throw new Error("Word index data unavailable");
    const groups = await response.json();
    const transliterated = browser.dataset.transliterated === "true";
    const label = group => group.word === group.transliteration ? group.word || "(blank)" : transliterated
      ? `${group.transliteration || "(blank)"} (${group.word})`
      : `${group.word || "(blank)"} (${group.transliteration})`;
    const books = new Set();
    groups.forEach((group, id) => {
      group.id = String(id);
      group.search = normalise(`${group.word} ${group.transliteration}`);
      group.occurrences.forEach(row => {
        row.book = row.ref.slice(0, 3); books.add(row.book);
        row.search = normalise(`${referenceLabel(row.ref)} ${row.ref} ${row.gloss}`);
      });
    });
    groups.sort((a, b) => normalise(label(a)).localeCompare(normalise(label(b))));
    const controls = browser.querySelector(".referenceIndexControls");
    const search = controls.querySelector("input");
    const book = controls.querySelector("select");
    for (const code of [...books].sort()) { const option = node("option", code); option.value = code; book.append(option); }
    const count = browser.querySelector(".referenceIndexCount");
    const entries = browser.querySelector(".wordIndexEntries");
    const url = new URL(location.href);
    search.value = url.searchParams.get("q") || "";
    book.value = url.searchParams.get("book") || "";
    const pageNumber = value => Math.max(0, Number.parseInt(value, 10) || 0);
    let offset = pageNumber(url.searchParams.get("page")) * pageSize;
    let opened = url.searchParams.get("word"), occurrenceOffset = pageNumber(url.searchParams.get("occurrencePage")) * pageSize;
    let selected = [], timer;
    function save() {
      for (const [key, value] of Object.entries({q: search.value, book: book.value, page: offset / pageSize || "",
        word: opened ?? "", occurrencePage: occurrenceOffset / pageSize || ""})) {
        if (value !== "") url.searchParams.set(key, value); else url.searchParams.delete(key);
      }
      history.replaceState(null, "", url);
    }
    function paging(container, start, total, move, noun) {
      const previous = node("button", `Previous ${noun}`), next = node("button", `Next ${noun}`);
      previous.type = next.type = "button";
      previous.disabled = start === 0; next.disabled = start + pageSize >= total;
      previous.addEventListener("click", () => move(Math.max(0, start - pageSize)));
      next.addEventListener("click", () => move(start + pageSize));
      container.replaceChildren(previous, node("span", ` ${total ? start + 1 : 0}–${Math.min(start + pageSize, total)} of ${total.toLocaleString()} ${noun} `), next);
    }
    function render() {
      offset = Math.min(offset, Math.max(0, Math.ceil(selected.length / pageSize) - 1) * pageSize);
      const total = selected.reduce((sum, group) => sum + group.matches.length, 0);
      count.textContent = selected.length ? `${quantity(selected.length, "matching spelling")}; ${quantity(total, "occurrence")}. Expand a spelling to browse.` : "No matching words.";
      const move = start => { offset = start; opened = null; occurrenceOffset = 0; save(); render(); browser.scrollIntoView({block: "start"}); };
      for (const container of browser.querySelectorAll(":scope > .wordIndexPages")) paging(container, offset, selected.length, move, "spellings");
      entries.replaceChildren();
      for (const group of selected.slice(offset, offset + pageSize)) {
        const details = node("details"), summary = node("summary");
        const glosses = [...new Set(group.matches.map(row => row.gloss).filter(Boolean))].slice(0, 3).join(" / ");
        summary.textContent = `${label(group)} — ${group.language} — ${glosses || "(no gloss)"} — ${quantity(group.matches.length, "occurrence")}`;
        summary.title = `${label(group)}: ${glosses}. Expand to see verse locations and individual word details.`;
        details.append(summary); entries.append(details);
        const before = node("div"), rows = node("ol"), after = node("div");
        before.className = after.className = "wordIndexPages";
        let start = group.id === opened ? occurrenceOffset : 0, populated = false;
        function renderOccurrences(newStart) {
          start = Math.min(newStart, Math.max(0, Math.ceil(group.matches.length / pageSize) - 1) * pageSize);
          rows.start = start + 1; rows.replaceChildren();
          for (const row of group.matches.slice(start, start + pageSize)) {
            const item = node("li"), link = node("a", `${referenceLabel(row.ref)} — ${row.gloss || "(no gloss)"}${row.status ? ` (${row.status})` : ""}`);
            link.href = row.href; link.title = `${label(group)} — ${link.textContent}`;
            item.append(link); rows.append(item);
          }
          const moveOccurrences = newStart => { opened = group.id; occurrenceOffset = newStart; renderOccurrences(newStart); save(); summary.scrollIntoView({block: "nearest"}); };
          paging(before, start, group.matches.length, moveOccurrences, "occurrences");
          paging(after, start, group.matches.length, moveOccurrences, "occurrences");
        }
        details.addEventListener("toggle", () => {
          if (!details.isConnected) return; // A pending search may have replaced this result.
          if (details.open) {
            if (!populated) { details.append(before, rows, after); renderOccurrences(start); populated = true; }
            opened = group.id; occurrenceOffset = start; save();
          } else if (opened === group.id) { opened = null; occurrenceOffset = 0; save(); }
        });
        if (group.id === opened) details.open = true;
      }
    }
    function find(reset = true) {
      if (reset) { offset = 0; opened = null; occurrenceOffset = 0; }
      const words = normalise(search.value).trim().split(/\s+/).filter(Boolean);
      selected = [];
      for (const group of groups) {
        const remaining = words.filter(word => !group.search.includes(word));
        const matches = group.occurrences.filter(row => (!book.value || row.book === book.value) && remaining.every(word => row.search.includes(word)));
        if (matches.length) selected.push({...group, matches});
      }
      // Exact spelling matches precede incidental substrings in other words/glosses.
      const query = normalise(search.value).trim();
      const exact = group => normalise(group.word) === query || normalise(group.transliteration) === query;
      selected.sort((a, b) => Number(exact(b)) - Number(exact(a)));
      render(); save();
    }
    search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(find, 150); });
    book.addEventListener("change", () => { clearTimeout(timer); find(); });
    controls.querySelector('[data-action="clear"]').addEventListener("click", () => { clearTimeout(timer); search.value = ""; book.value = ""; find(); search.focus(); });
    controls.hidden = false;
    find(false);
  }
  async function initialise(browser) {
    if (browser.dataset.ready) return;
    browser.dataset.ready = "true";
    const entries = browser.querySelector(".referenceIndexEntries");
    const tag = browser.dataset.itemTag;
    const records = browser.dataset.source ? await (async () => {
      const response = await fetch(browser.dataset.source);
      if (!response.ok) throw new Error("Index data unavailable");
      return (await response.json()).map(row => ({ text: normalise(row.text), html: row.html }));
    })() : [...entries.querySelectorAll(tag)].map(node => {
      const link = tag === "a" ? node : node.querySelector("a");
      let destination = link?.getAttribute("href") || "";
      try { destination = decodeURIComponent(destination); } catch (_) { /* Keep readable source. */ }
      return { text: normalise(`${node.textContent} ${destination}`), html: node.outerHTML };
    });
    const controls = browser.querySelector(".referenceIndexControls");
    const search = controls.querySelector("input");
    const count = controls.querySelector(".referenceIndexCount");
    const previous = controls.querySelector('[data-action="previous"]');
    const next = controls.querySelector('[data-action="next"]');
    const clear = controls.querySelector('[data-action="clear"]');
    let selected = records, offset = 0, timer;
    function render() {
      const items = selected.slice(offset, offset + 200).map(row => row.html).join(tag === "a" ? " · " : "\n");
      entries.innerHTML = tag === "li" ? `<ul>${items}</ul>` : `<p>${items}</p>`;
      count.textContent = selected.length
        ? `${offset + 1}–${Math.min(offset + 200, selected.length)} of ${selected.length.toLocaleString()} matching entries`
        : "No matching entries.";
      previous.disabled = offset === 0;
      next.disabled = offset + 200 >= selected.length;
    }
    function find() {
      const words = normalise(search.value).trim().split(/\s+/).filter(Boolean);
      selected = words.length ? records.filter(row => words.every(word => row.text.includes(word))) : records;
      offset = 0;
      render();
    }
    search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(find, 120); });
    clear.addEventListener("click", () => { clearTimeout(timer); search.value = ""; find(); search.focus(); });
    previous.addEventListener("click", () => { offset = Math.max(0, offset - 200); render(); });
    next.addEventListener("click", () => { offset += 200; render(); });
    controls.hidden = false;
    render();
  }
  for (const browser of document.querySelectorAll(".referenceIndex")) {
    initialise(browser).catch(() => {
      const notice = document.createElement("p");
      notice.textContent = "Search is unavailable. Use the complete HTML list below.";
      browser.append(notice);
    });
  }
  for (const browser of document.querySelectorAll(".wordIndex")) {
    initialiseWords(browser).catch(() => {
      browser.querySelector(".referenceIndexCount").textContent = "Search is unavailable. Use the complete HTML list below.";
    });
  }
})();
