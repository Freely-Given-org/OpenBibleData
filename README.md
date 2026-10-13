# Open Bible Data (OBD)

Code and datasets for the OpenBibleData project

This consists of three main components:

1. Some public domain or open-licenced Bible source files copied from other sites
2. Our own _sentenceImportance_ database (giving an importance value for each ‘verse’/‘sentence’)
3. Python code to generate a static website from the various Bible file sets

The copied Bibles are not committed yet (because we're unsure about ‘redistribution’ rights/licensing even for open-licensed resources)

The preliminary static website can currently be viewed (in an iFrame) at
[OpenEnglishTranslation.Bible](https://OpenEnglishTranslation.Bible/) at the <em>Reader</em> link
or directly at [Freely-Given.org/OBD](https://Freely-Given.org/OBD/).

Currently the static website is approx 300 GB with around 1.3 million separate pages
and includes almost forty Bible translations along with multiple Hebrew and Greek originals,
and then parallel and interlinear verse pages with two sets of notes for translators,
related/parallel section pages, topic pages, and reference pages including two Bible dictionaries.

## Versification alignment

Parallel-page URLs, chapter counts, and verse navigation use BOS `eng` numbering,
independently of which translations have been loaded. `State.BibleVersifications`
in `createPages/settings.py` declares the numbering of each imported source.
OET-RV uses `eng`, OET-LV uses `org`; UHB and all selected-verse TSVs use English
addresses. The declarations are applied both to newly loaded Bibles and to old
pickles, so changing a declaration does not require rebuilding Bible caches.
`None` leaves a source's declaration to BOS metadata. Wycliffe's Zefania import
contains only GEN, EXO, LEV, NUM, DEU, MAT, MRK, LUK, and JHN and is configured
as `vul`. The source owner confirmed that its Mark 9:1 begins the transfiguration
(“after six days”), corresponding to English Mark 9:2. English Mark 9:1 instead
maps to Wycliffe Mark 8:39.

`createPages/versification.py` adapts English navigation, excerpt dictionaries,
and explicit edition layouts to BOS's mapping and `Bible.getPassageData` APIs.
Each portion is fetched and rendered under its native address,
including its word links and source-chapter link. Changed addresses are labelled.
Psalm titles are handled on the existing `V0` pages, separately from verse 1;
there is no title-marker-based verse offset. Stored verse bridges are displayed
once per group, and explicit suffixes must exist in the text. Whole verses stored
as separate suffixed entries include all those entries. Editorial introductions
are kept separate from numbered scripture/title mapping.

The OET side-by-side book, chapter, and section pages use
`createPages/oetPassages.py` to choose display chunks and call
`Bible.getMappedPassage(sourceSystem, references, combineAdjacent=True)` for the
LV text. Generic entry-to-reference extraction, complete-group retrieval, bridge
and suffix handling, and adjacent-portion assembly now live in BOS's
`InternalBiblePassages` module. OBD retains OET chunking, editorial pairing, HTML
rendering, and navigation. Deploy the updated BOS alongside these OBD changes,
and rebuild/install the OBD Rust extension in `createPages/Rust` in the server's
build environment (for example, `maturin develop --release` in its activated
virtual environment). The renderer now calls back into OBD's navigation layer,
and the translation-note quote matcher receives mapped native word rows.
Book and chapter rows are split at RV entry/index boundaries rather
than by cutting LV HTML at matching verse numbers. This handles, for example,
English Genesis 31:55 in LV 32:1 and English Malachi 4 in LV 3:19–24. Intermediate
Psalm titles are included when BOS declares a separate title address; other
titles remain with verse 1. Disjoint mapped portions are fetched separately,
without including unrelated intervening verses. Stored bridges are rendered
once and complete merge groups are submitted together to BOS.

RV anchors and page navigation retain English numbering. LV numbers retain
their native numbering, with a reference label when a passage changes chapters.
LV verse links lead to English parallel pages when BOS can resolve the reverse
mapping; unresolved links are left as plain numbers. The LV column heading links
to the native passage in its standalone book page. LV anchors and notes have
separate IDs so they cannot take over an English navigation target. Book headers
and introductions are paired by their role, not their internal line numbers.

Simple verse lists, interlinear pages, topic passages, and RV quotations on
word/lemma/Strong's pages also use BOS passage mapping and retrieval. Interlinear
word rows and translation-note quote matches follow the selected native
portions, including disjoint portions, instead of scanning a contiguous range
of word IDs. `createPages/oetWords.py` keeps this OET word-table handling in OBD.
UHB word links use BOS correspondence and verify the Hebrew consonants before
attaching a native word ID; differing readings remain unlinked.

`createPages/navigation.py` translates scripture links in rendered text, page
controls, version switching, introductions, and reference pages. BOS supplies
the correspondence; OBD chooses the destination URLs. Native LV labels, ESFM
word numbers, and word-page filenames remain unchanged. Links within standalone
editions retain that edition's numbering, while combined OET, parallel, simple,
and interlinear destinations use English numbering. Section switches use the
corresponding chapter/verse, since section numbers differ between editions.

App word JSON retains its existing native `ref` and `word_number`, and adds
`versification`, `navigation_versification`, `navigation_mapping_status`, and
`navigation_references`. For example, native `MAL_3:19w1` has English navigation
reference `MAL_4:1`. Consumers must check the mapping status; an empty navigation
list is retained when no correspondence is available.

The two Brenton imports need explicit book-storage adapters after conversion:
BOS `lxx` uses `EZN` for combined Ezra/Nehemiah, while the Greek import uses `EZR`
and the English import separates `EZR` and `NEH`. These are configured in
`State.BibleSourceBookLayouts`; book aliases are never guessed from names.
The source editions can be inspected at [Greek Brenton](https://ebible.org/grcbrent/)
and [English Brenton](https://ebible.org/eng-Brenton/).

BOS's current mapping data are draft and have explicit gaps. Ambiguous, partial,
unsupported, and invalid scripture mappings produce an alignment-unavailable
message and a build warning, with no unchanged-reference fallback. For example,
the historical `Luther` system is currently count-only; Vulgate Tobit, Judith,
and Sirach lack supported textual bridges. Some individual mappings are also
quarantined by BOS. A declared profile is a statement about source numbering,
not a guarantee that all of an edition's passages can be mapped. A mapped book or
verse missing from an imported subset is reported separately. Books without an
English navigation definition are omitted from the parallel index.

Focused offline checks (from this directory, using an environment with the
updated BOS and its native dependencies):

```sh
../BibleOrgSys/.venv/bin/python -m unittest discover -s createPages -p test_versification.py
../BibleOrgSys/.venv/bin/python -m unittest discover -s createPages -p test_oet_passages.py
../BibleOrgSys/.venv/bin/python -m unittest discover -s createPages -p test_navigation_mapping.py
```

These tests use small USFM/ESFM fixtures and actual page-building functions.
They cover titles, chapter boundaries, LXX reordering, book identities, grouped
and suffixed verses, cache declarations, missing data, source links, native word
IDs, topic passages, and unavailable mappings. The navigation tests also exercise
the Rust renderer and note matcher when the updated extension is installed;
those integration cases are skipped if it is absent. Related-passage pages
currently use OET-RV alone and need no LV text pairing. The full
`createSitePages.py` build still requires the server's external datasets.

## Future Plans

The site doesn't yet contain any Strongs-indexed lexicons,
and so links to BibleHub.com for that.

Search functionality is provided by [Pagefind](https://Pagefind.app/).

Hopefully if BibleOrgSys is able to start using more Rust functions in the future,
then the memory use should reduce and the site build time should be greatly increased.
(Currently taking 65 minutes and using most of the 64GB RAM.)
