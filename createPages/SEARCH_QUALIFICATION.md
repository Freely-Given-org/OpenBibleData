<!-- SPDX-License-Identifier: CC0-1.0 -->

# Native Bible search: implementation and qualification

Updated: 2 November 2026.

The generator now builds its own search data while the source Bibles are still loaded. `Search.htm` uses repository-owned JavaScript and a worker, with no Pagefind package, post-build indexing command, search service, or replacement search-library dependency. The production site has not been rebuilt as part of this work.

## Implemented behaviour

- Passage lookup recognises BOS and OET book names, abbreviations, numbered books, single-chapter books, verse suffixes, bridges, ranges, and semicolon-separated selections across books. `Jn 3:16` and `Jn3.16` mean John, not Third John. Native numbering is the default; shared study-page numbering uses exact mappings only.
- Text searches support all words, any word, consecutive-word phrases, exclusions, exact whole words, and optional accent/pointing matching. Punctuation separates word tokens. The Hebrew word joiner preserves a word's identity. Common words remain indexed.
- Versions, books, collections, source languages, passage ranges, fields, and book order are selectable. A normal visit starts with OET-RV; both OET versions can be selected together. Search links from Bible pages carry the version and offer the current book without silently restricting the query to it.
- Bible text, transliteration, modernised spelling, supplementary translation, headings, introductions, and notes are separate fields. Conditions never combine different source records or fields into one match.
- Original-word searches support source lemmas, word forms, Strong's identifiers, and exact source morphology codes. Morphology restrictions apply to the same annotation. Availability is stated in the results; an English translation is not assumed to have original-word alignment.
- Results identify their version, field, native reference, and verified destinations. They support highlighting, nearby verse expansion, exact mapped-passage grouping, counts by book, copying displayed references, pagination, shareable URLs, and browser history.
- A submitted search moves focus and scrolls to its results when ready, including empty results and query failures. Reduced-motion preferences are respected. An older request finishing does not interrupt a newly edited query.
- Worker cancellation, download failures, empty searches, limited builds, malformed source references, unavailable annotations, and missing passages have explicit outcomes. Results use text nodes rather than inserting source HTML into the page.

Study mode currently searches the supplied notes and Bible-associated fields. Broader topic/entity/dictionary discovery, guided grammatical filters, prefix/spelling suggestions, and proximity/adjacent-verse matching remain Step 11 follow-ups. The advanced morphology box deliberately requests a source code rather than claiming a universal grammatical vocabulary.

## Coverage and identity

The former indexing instruction selected the rendered `OET` and `par` page families. That exposed many duplicate displays and mixed Bible text with page furniture, derived displays, and notes. The replacement exports each native source passage once per version and indexes its fields separately.

Native Bible records come from loaded BOS entries or selected-verse dictionaries. The parallel-page generator separately exports its transformed text, Tyndale introductions/study/theme notes, SIL and unfoldingWord notes, BibleMapper notes, and OBD editorial comments. It captures source content before adding repeated resource labels. Workers write separate intermediate files; the parent verifies and merges them.

Selected-verse editions can use an actual parallel-page anchor when they lack chapter pages. Bridges retain their source label and are not duplicated into artificial verses. Missing mappings do not manufacture parallel links. Reused interlinear pages are not advertised by a fresh index unless they are present in the current staging output: the retained pages lack a source fingerprint proving compatibility.

Every emitted destination is checked against actual files and anchors. The build report lists indexed and unpublished passage counts and malformed source references. For example, a malformed ULT source verse label containing `\\add` is reported and omitted; the exporter does not guess its intended verse number. A failed index or invalid staged generation stops publication.

An isolated preview reads existing source resources and checks the existing published pages. It does not regenerate those pages, and it cannot recreate the parallel generator's intermediate exports by itself. Consequently, its counts qualify the native Bible corpus; the generator-owned derived/study exports are covered separately by focused tests and must also be exercised in the deployment build.

## Build and publication

Run the normal build from `createPages/` with `uv run createSitePages.py`. It follows the existing test/private/public settings. This work does not turn off test mode or initiate a production build.

The relevant settings are `CREATE_SEARCH_INDEX_FLAG`, `SEARCH_CACHE_MIB` (64), and `SEARCH_FETCH_CONCURRENCY` (6). Disabling indexing produces an explanatory search page. The ordinary build creates search data before releasing the loaded resources.

To create a separate review build against existing pages:

```bash
cd createPages
uv run buildSearchIndex.py --site ../htmlPages --output /tmp/obd-search-review --versions OET-RV OET-LV UHB SR-GNT
```

The output directory must be new and outside the published site. `--books MRK` makes a smaller trial; `--all-versions` selects available configured Bible sources. The utility disables writing Bible pickles and never rewrites the published pages. Serve the preview over HTTP; browser workers and module scripts are not intended to run from `file:` URLs.

Format 3 uses version/book partitions, 32 hashed term buckets, compact passage/document catalogues, and blocks of 128 display records. Positional postings implement phrases. Display text is fetched only for the current result page; the browser derives highlight offsets from that preserved text using the same tested token rules as the builder. Gzip payloads use `.bin` names and explicit browser decompression, avoiding reliance on server-specific compression headers. A modern browser with `DecompressionStream` is required; no-JavaScript navigation remains available.

Input fingerprints include exported content, destinations/mappings, metadata, and extraction/indexing code. Unchanged compatible artifacts are verified before reuse. Deleted sources do not enter the new manifest. Files and the entire client bundle have content-addressed names. `Search.htm` pins its immutable manifest and client; it does not depend on the mutable discovery pointer.

Publication validates the complete staged generation, installs only its referenced assets, repairs corrupt copies atomically, then replaces the discovery manifest and search page with same-filesystem renames. Interrupted-publication tests verify that an old page can still use its pinned files. Older generations and legacy Pagefind files are retained for rollback and cached clients. There is no automatic asset pruning in this initial release; retain them for at least 30 days after production cutover and until the observation period is accepted.

This protects search assets; the surrounding site's existing delete-and-move deployment is still not atomic. A complete previous site deployment remains necessary for a production rollback, including passage pages.

## Verification evidence

The pre-change baseline passed 560 Python tests and 311 Rust tests. The final repository suite passed 574 Python tests and 312 Rust tests; the 14 focused search tests also passed after adding the missing-language regression. The focused search tests exercise actual BOS entries and run the browser engine with Python-produced artifacts using Node's built-in test runner. Node is a test tool, not a site-build requirement. The generated page also passed the site's normal HTML and stylesheet checks with the full site layout.

Acceptance examples include whole-word versus prefix behaviour, repeated-word phrases, note-only terms, exclusions, no cross-version/field false matches, Greek accents, Hebrew pointing/joiners, emoji/UTF-16 offsets, single-chapter references, suffixes and bridges, multiple books, renumbered Malachi passages, parallel-only selected verses, original-word morphology association, deterministic output, cache invalidation, corrupt artifacts, cancelled/failed requests, restricted publication, interruption, and rollback.

An initial complete-book trial exported 106,966 passages and 217,921 searchable fields across OET-RV, OET-LV, UHB, and SR-GNT (231 partitions). Source export and indexing took 335.5 seconds with a 1,643.7 MiB peak process RSS. Re-indexing that exported corpus with the final compact catalogue/token rules took 56.1 seconds and produced 72.7 MB of artifacts. The latter is an indexing-only measurement, not the time for a fresh source build.

The completed all-version qualification exported 1,184,521 passages and 1,874,470 searchable fields from 65 configured Bible sources, in 3,361 version/book partitions. Fresh source loading, destination checking, and indexing took 1,152.6 seconds (19.2 minutes), peaked at 2,222.8 MiB process RSS, and produced 444.1 MB of search artifacts. Every referenced immutable artifact and the final client bundle passed validation. This is a separate preview against existing published destinations, not a production website rebuild or a measurement of incremental time inside the ordinary build.

Of 1,187,521 source passages examined, 2,995 lacked a verified destination in that existing output (including 2,800 ClVg passages), and five had malformed source references. The malformed labels are ULT CH1 7 `\\add`, and Moff PRO 1 `ii`, SNG 4 `I`, SNG 8 `for`, and AMO 3 `The`. These omissions are reported rather than assigned guessed destinations or verse numbers. Review them against newly generated pages during production staging.

Desktop Chromium checks used a 10 Mbit/s, 100 ms-latency connection simulation:

| Query/scope | Time to results | Result |
| --- | ---: | --- |
| `Jesus`, OET-RV, cold | 2.56 s | 635 source-field matches; approximately 513 KB of query assets |
| Same query, repeated | 55–59 ms | No further asset requests |
| `Jn 3:16`, both OET versions | 167 ms | Two native passages |
| `λόγος`, SR-GNT | 1.53 s | 65 source-field matches |
| `בראשית`, UHB | 1.10 s | Five source-field matches |
| `G3056`, OET-LV original-word mode | 2.52 s | 317 annotated passages |

The existing local Pagefind search returned 7,342 page matches for `Jesus`, taking 1.64 seconds cold and 81 ms warm, with approximately 887 KB downloaded cold. Its scope and result unit differ from the OET-RV native-verse search, so those timings are not a like-for-like speed comparison. The replacement's principal benefits are source identity, controlled scope, Bible-specific navigation, and build integration.

An additional unthrottled local Chromium check used the complete 65-version manifest. `Jesus` across all versions returned 31,234 field matches in 2.05 seconds, requesting 14.5 MB across 4,234 query assets after the default OET query. `the` across all versions returned 776,704 field matches in 3.83 seconds, requesting 38.4 MB across 6,312 assets. Sampled worker JavaScript heap use peaked at 83.5 MiB and 373.5 MiB respectively. These are sequential desktop measurements with some cached assets, not cold-network timings. The configured 64 MiB cache allowance does not cap total worker memory: current matches, decoding, and grouping also consume memory.

With the complete manifest and the 10 Mbit/s, 100 ms network simulation, the default OET-RV `Jesus` search took 2.51 seconds cold and 29 ms repeated. Expanding it to all 65 versions took 74.75 seconds, downloaded 14.5 MB in 4,234 requests, and reached a sampled worker heap of 74 MiB. Scope therefore matters substantially; the interface advises narrowing versions or books and reports progress while searching. The provisional desktop budget for an explicitly requested all-version search is 120 seconds and 512 MiB sampled worker heap under this network profile. This is separate from the default-search target and is not a phone guarantee. A throttled all-version `the` run was interrupted before completion, so its cold-network latency remains unqualified.

The desktop and 390-pixel phone layouts had no horizontal overflow or JavaScript errors in the tested flows. Checks covered highlights, context expansion, pagination, shared references, Back navigation, reset, passage lookup without workers, download failures, and the absence of Pagefind requests. With the full site layout, submitting with Enter scrolled the phone-sized view to the results region, leaving about 16 pixels above it and setting keyboard focus there. A failed new query cleared previous counts and pagination. These are desktop-browser measurements and phone-sized layout checks, not a physical-phone p95 benchmark.

## Release gates

Before production cutover, run a normal staging build with the intended production corpus, inspect its coverage/build report (including generator-owned study/derived fields), verify representative links against that output, and retain the previous complete deployment. Finish the cold-network all-version common-word measurement and physical-phone measurements; the desktop checks do not establish a phone p95. Complete the production observation period before removing the old deployment assets.

The implementation removes Pagefind from newly generated pages and active build instructions. It deliberately leaves the existing production output and rollback assets alone.
