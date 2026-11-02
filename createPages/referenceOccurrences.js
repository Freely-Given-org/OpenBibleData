// SPDX-License-Identifier: CC0-1.0
// 2026-10-31 Filter the complete static occurrence list; render at most 100 rows.
"use strict";
(async () => {
  const browser = document.getElementById("occurrenceBrowser");
  if (!browser) return;
  const count = document.getElementById("occurrenceCount");
  try {
    const response = await fetch(browser.dataset.source);
    if (!response.ok) throw new Error("Occurrence data unavailable");
    const records = await response.json();
    const book = document.getElementById("occurrenceBook");
    const form = document.getElementById("occurrenceForm");
    const gloss = document.getElementById("occurrenceGloss");
    const search = document.getElementById("occurrenceSearch");
    const list = document.getElementById("occurrenceRows");
    const navigation = document.getElementById("occurrencePages");
    const query = new URLSearchParams(location.search);
    let offset = Number(browser.dataset.offset);
    for (const [field, control] of [["form", form], ["gloss", gloss]]) {
      const values = [...new Set(records.map(row => row[field]))].sort();
      for (const value of values) {
        const option = document.createElement("option");
        option.value = JSON.stringify(value);
        option.textContent = value || "(no gloss)";
        control.append(option);
      }
      if (query.has(field)) {
        control.value = JSON.stringify(query.get(field));
        offset = 0;
      }
    }
    function render() {
      const term = search.value.trim().toLocaleLowerCase();
      const selectedForm = form.value ? JSON.parse(form.value) : null;
      const selectedGloss = gloss.value ? JSON.parse(gloss.value) : null;
      const selected = records.filter(row => (!book.value || row.book === book.value)
        && (selectedForm === null || row.form === selectedForm)
        && (selectedGloss === null || row.gloss === selectedGloss)
        && (!term || `${row.ref} ${row.form} ${row.gloss}`.toLocaleLowerCase().includes(term)));
      offset = Math.min(offset, Math.max(0, Math.floor((selected.length - 1) / 100) * 100));
      // HTML is generated locally with escaped source text and verified URLs.
      list.innerHTML = selected.slice(offset, offset + 100).map(row => row.html).join("");
      list.start = offset + 1;
      count.textContent = selected.length
        ? `${offset + 1}–${Math.min(offset + 100, selected.length)} of ${selected.length} matching occurrences`
        : "No matching occurrences.";
      navigation.replaceChildren();
      for (const [label, nextOffset, disabled] of [["Previous", offset - 100, offset === 0],
        ["Next", offset + 100, offset + 100 >= selected.length]]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.disabled = disabled;
        button.addEventListener("click", () => { offset = nextOffset; render(); });
        navigation.append(button, document.createTextNode(" "));
      }
    }
    for (const control of [book, form, gloss, search]) {
      control.addEventListener(control === search ? "input" : "change", () => { offset = 0; render(); });
    }
    document.getElementById("occurrenceFilters").hidden = false;
    render();
  } catch (error) {
    count.append(document.createTextNode(" Filters are unavailable; use the page links below."));
  }
})();
