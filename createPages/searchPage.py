#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Accessible static shell for OBD's native Bible search.

CHANGELOG:
    2026-11-01 Add passage, Bible text and study-material search controls.
    2026-11-02 Add a focusable destination for automatic result scrolling.
    2026-11-02 Explain how to narrow the scope for faster searches.
"""
from xml.sax.saxutils import escape


def searchBody(manifest):
    return f'''<h1 id="Top">Search the Bible</h1>
<p>Find a passage or words in particular Bible versions. Results identify the text and version that matched.</p>
<div id="bibleSearch" data-manifest="search/{escape(manifest)}">
<form id="searchForm">
<div class="searchControls">
<label>Search mode <select name="mode"><option value="text">Bible text</option><option value="reference">Go to passage</option><option value="study">Study material</option><option value="original">Original words</option></select></label>
<label class="searchQuery">Words or reference <input name="query" type="search" placeholder="Words, a phrase, or John 3:16" autocomplete="off" list="searchBookSuggestions" required><datalist id="searchBookSuggestions"></datalist></label>
<button type="submit">Search</button>
</div>
<div id="referenceSuggestion"></div>
<div id="originalControls" class="searchControls" hidden>
<label>Find an original <select name="lookup"><option value="lemma">Lemma</option><option value="form">Word form</option><option value="strong">Strong’s number</option></select></label>
<label>Morphology code <input name="morphology" placeholder="Optional exact source code"></label>
<p>Search one original word or identifier. Grammar filters apply to the same annotated word. Coverage and codes depend on the selected source.</p>
</div>
<div class="searchControls">
<label>Versions <select name="versions" multiple size="5" aria-describedby="versionHelp"></select></label>
<p id="versionHelp">Choose one or more versions. <button type="button" id="bothOET">Both OET versions</button> <button type="button" id="allVersions">All versions</button><br>Choose fewer versions or a book for faster searches.</p>
<label>Book <select name="book"><option value="">All available books</option></select></label>
<label>Collection <select name="group"><option value="">All collections</option><option value="OT">Old Testament</option><option value="NT">New Testament</option><option value="DC">Additional books</option></select></label>
</div>
<details><summary>Matching and more options</summary><div class="searchControls">
<label>Match <select name="match"><option value="all">All words in one verse or field</option><option value="any">Any word</option><option value="phrase">Exact phrase</option></select></label>
<label>Exclude words <input name="exclude" type="text"></label>
<label>Passage range <input name="range" type="text" placeholder="John 3:1-21"></label>
<label>Reference numbering <select name="numbering"><option value="native">Each version’s own numbering</option><option value="shared">Shared study-page numbering (exact mappings)</option></select></label>
<label>Text field <select name="field"><option value="">All fields for this mode</option><option value="body">Bible text only</option><option value="transliteration">Transliteration</option><option value="modernised">Modernised spelling</option><option value="translation">Supplementary translation</option><option value="note">Notes</option><option value="heading">Headings</option><option value="introduction">Introductions</option></select></label>
<label>Language <select name="language"><option value="">All languages</option></select></label>
<label>Book order <select name="order"><option value="oet">OET order</option><option value="traditional">Traditional order</option></select></label>
<label><input name="accents" type="checkbox"> Match accents and Hebrew pointing exactly</label>
<label><input name="groupMatches" type="checkbox"> Group sources with the same complete, exact passage mapping</label>
</div><p>Words are matched in full, ignoring case. Exact phrases match consecutive words; punctuation separates words. Each match stays within one version and text field.</p></details>
<p><button type="reset">Reset filters</button> <button type="button" id="copyReferences">Copy displayed references</button></p>
</form>
<div id="searchResultsArea" role="region" aria-label="Search results" tabindex="-1">
<p id="searchScope"></p><p id="searchOrigin"></p><p id="searchStatus" role="status" aria-live="polite">Loading available Bibles…</p>
<details><summary>Source matches by book</summary><div id="searchCounts"></div></details>
<ol id="searchResults" class="searchResults"></ol>
<nav class="searchControls" aria-label="Search result pages"><button id="searchPrevious" type="button" disabled>Previous</button><span id="searchPageNumber"></span><button id="searchNext" type="button" disabled>Next</button></nav>
</div>
</div>
<noscript><p>Text search needs JavaScript. You can still <a href="OET/byC/">browse Bible books and chapters</a>.</p></noscript>'''
