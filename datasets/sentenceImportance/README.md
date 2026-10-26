# Open Bible Data (OBD)
# Sentence Importance Dataset

## Introduction

This is a TSV file with at least one entry for every Bible ‘verse’ giving rough indications of
1/ the **‘importance’** of each verse,
2/ whether or not it **contains textual issues**,
3/ the **‘clarity’ (or ‘understandability’)** of the original Hebrew or Greek text, and
4/ the speaker(s) at that point (or the narrator).

Since ‘verses’ are totally artificial units
(sometimes being only part of a sentence, yet other times containing two or more sentences)
this dataset also has the ability to roughly specify the first or second half of the verse
(in the original language that is), especially if multiple sentences are involved.

NOTE: Don't use this datafile yet -- it's **STILL IN DEVELOPMENT and VERY PRELIMINARY**

## Importance

For example, Gen 1:1 ‘In the beginning God created the heavens and the earth.’
and John 14:6 ‘Jesus answered, “I am the way and the truth and the life. No one comes to the Father except through Me.’
would surely seem more important to everyone than something like 2 Tim 4:13
‘When you come, bring the cloak that I left with Carpus at Troas, and my scrolls, especially the parchments.’
or Col 4:14 ‘Luke, the beloved physician, and Demas send you greetings.’?

On the other hand, we don’t want to be trying to discriminate between a saying
that one Christian denomination gives little importance to or considers to no longer apply,
when another considers it important. So we don't want to try to be too fine-grained.

Hence the importance values are:

- 0=T=Trivial (like a forgotten cloak, or greetings from some person we know longer know)
- 1=M=Medium/Normal (the great majority of sentences in the Bible)
- 2=I=Important (specific statements that are commonly considered to be more important, and hence often memorised)
- 3=V=Vital (specific statements that are commonly found in doctrinal statements)

## Textual issues

Secondly, another field indicates potential textual (known by experts as ‘textual criticism’) issues.
For example if this ‘verse’/‘sentence’ (or some part of it) doesn’t occur in all the ancient manuscripts.
It may have been deleted by some, added by some, or (intentionally or accidentally) amended by some.

Hence the textual issue values are:

- 0=No issue (so most translations are working from the same Hebrew/Greek text here)
- 1=Minor spelling or word order issues (with pretty-much no effect on meaning)
- 2=Minor word changes (some words vary in manuscripts of different origins)
- 3=Major differences (any translations might be expected to have a footnote her to explain textual differences in the source)

## Clarity / Understandability

In addition, a third field indicates where commentators are unsure what was actually meant.
For example, in the above quote from 2 Timothy 4:13, we’re not sure if Paul meant _blank parchments_ (i.e., like a writing pad)
or _parchments that he wanted to read_ (i.e., like library books).
But other passages are much more obscure than that.

Hence the clarity values are:

- 0=O=Obscure (we can only really guess at what was meant, and hence we might expect translations to differ widely)
- 1=U=Unclear (we’re unsure exactly what was meant, like the parchment example above)
- 2=C=Clear (it seems clear enough what the author or speaker meant, as far as we know)

## TSV format

The first line of the tab-separated data file contains the six column headers:

**FGRef**: Freely-Given verse reference (see below)

**Importance**: T, M, I, or V (representing numerical values 0, 1, 2, or 3)

**TextualIssue**: 0, 1, 2, or 3

**Clarity**: O, U, or C (representing numerical values 0, 1, or 2)

**Speakers**: `@` by default, which represents the narrator (i.e., the writer of the text
who has no particular speaker). Otherwise this is a comma-separated list of the
speaker(s) in that verse, e.g. `Yeshua`, `@,Yahweh`, `@,Mosheh`, or `@,David,Natan`.
This column is (still-preliminary) automatically derived from the OET-RV text,
with explicit OET-LV evidence as described below:
`\wj` marks the words of Yeshua (Jesus); USFM `\sp` speaker markers (as used in
Song of Songs, e.g. 'The bride', 'The groom', and Jeremiah) identify the current
speaker for the following verses; and speech-attribution patterns like
'Mosheh said, …' or '…, responded David' are used to spot other named speakers.

Psalm `\d` headings remain narrator even when they name an author. An explicit
attribution such as “a song by David”, “David's song”, or “a prayer of David's”
sets the default voice of the Psalm's body to `David`. This survives stanza and
section headings but resets at the next Psalm. Other named authors and Korah's
descendants are handled in the same way. Explicit `\sp` speakers override this
default; other detected speakers are retained alongside the author. A name
merely mentioned in a heading is not by itself evidence of authorship.

The OET-LV Psalm text corroborates the attribution or supplies one when absent
from the RV heading. RV attributions take precedence, and both readings are
saved in `speaker_evidence` in the build report for review. For example, the
current RV Psalm 132 heading explicitly credits David, whereas the LV's short
heading does not; this discrepancy is retained, not silently resolved.

Proverbs has reviewed section boundaries at 1:1, 10:1, 22:17, 24:23, 25:1,
30:1, and 31:1. The reader checks the source's attribution before applying the
new default: Shelomoh (Solomon), the wise, Agur, or Lemuel's mother. Attribution
lines themselves remain narrator. Collectors such as Hizkiyah's (Hezekiah's)
men are not treated as authors. The separate anonymous poem at 31:10 resets
the default to narrator rather than extending the mother's speech into it.

Speaker changes within one verse are preserved. When two explicit text runs
have different speakers, the generator may create `a`/`b` rows for the first
and second portions. Examples are `PSA_25:1a` (narrator heading) and
`PSA_25:1b` (David's prayer), or `PRO_10:1a` (narrator attribution) and
`PRO_10:1b` (Shelomoh's proverb). These are editorial portions, not necessarily
equal lengths. Hebrew Psalm headings with separate numbered verses (Psalm 9,
for example) need no extra split. An embedded Psalm heading is split only when
the LV's explicit English-numbering boundary note and shared RV/LV word numbers
confirm its location inside the first verse. Existing curated halves are never
redefined automatically, and BOS split/merge groups are kept whole. Such cases,
or verses with more than two speaker turns, retain a combined list. Consecutive
duplicates are removed; a return to an earlier speaker is retained (for example,
Song of Songs 1:4 has bride, young women, bride). Splits and declined splits are
recorded in the build report. Whole-verse ratings apply to both new portions.

The OET-LV NT word table can supplement a whole verse still marked only `@`:
it must identify a speech verb with an explicit first/third-person subject,
a pronoun-referent tag (`R...`), and a linked person tag (`P...`). Its native
`OET-LV` reference is mapped to `org` before adding the named speaker(s).
Person tags on ordinary names, second-person addresses, and unlinked pronouns
are insufficient. This fallback never replaces RV speakers or editorial halves.
The OT word table does not provide equivalent consistent pronoun evidence, so
mere OT person tags are not used to guess speakers. These rules are conservative
and do not yet identify every unmarked quotation or resolve all pronouns.

**Comment**: speaker-portion boundaries, or mapping coverage where an annotation is shared across an indivisible
split or merged passage. The source profile, native references, and original
output references are given explicitly. Empty means no such coverage note.

Each line (including the final one) is ended with a single newline character.

There are AT LEAST 41,899 data lines, representing each verse of the Old Testament,
the New Testament, and then the Deutercanon books.
However, any single verse line can be divided into two where necessary (see below),
so the number of lines is likely to increase over time (until the data become stabilised).

## Reference keys

Freely-Given.org uses our own reference system:

1. The bookcode is always an UPPERCASE three-character code starting with a letter,
e.g., GEN, KI1, EZE, JNA, NAM, MAT, JAM, PE2, JN3, JDE, JDT, TOB, etc.
See https://Freely-Given.org/Software/BibleOrganisationalSystem/BOSBooksCodes.html
and https://GitHub.com/Freely-Given-org/BibleBooksCodes.
(In our documentation and software, we always represent this three-character bookcode as BBB.)
2. A verse reference is **BBB_C:V**, e.g., EZE_17:5.
3. Verse references **may be split into two parts**:
roughly representing the first half and second half of verse,
e.g., (on two separate lines) EZE_17:5**a** and EZE_17:5**b**.
Note: these might be ‘logical’ halves,
e.g., there might be two sentences in a verse
(even if the second sentence is 3x the length of the first one).
Of course, splitting references like this increases the number of lines in the file.

## Versification scheme

**Every output FGRef uses BibleOrgSys's `org` profile: original Hebrew/Greek
versification.** This is a declared numbering convention, not an inference from
the language of a source. It is distinct from the legacy BOS count-only system
`Original`, the composite mapping pivot `BOSReference`, and the OET source profiles.

Hebrew Psalm titles are numbered verses in this table. An English `\d` heading
can correspond to one or two original verses: English Psalm 51:10 becomes
`PSA_51:12`, and its heading corresponds to `PSA_51:1–2`. Other examples are
English Deuteronomy 29:29 → `DEU_29:28`, English Micah 5:2 → `MIC_5:1`,
and English 2 Corinthians 13:14 → `CO2_13:13`.

Consumers must convert their own references into `org` before looking up rows.
Matching book codes and numerical chapter/verse labels does not establish that
two sources refer to the same text.

The OBD site now does this in `createPages/Bibles.py::getVerseMetaInfoHtml`.
The loader checks this table's `output_versification` in the adjacent build
report. Both parallel-verse and verse-list builders pass their configured
`state.navigationVersification`, including when preloading for worker processes.
All mapped rows are displayed separately, with original references when the
numbering changes and a coverage label when BOS expands an indivisible group.
Editorial halves are looked up only after converting the whole verse.

Book/chapter introductions have no metadata, but declared Psalm titles do.
Unsupported or ambiguous correspondences show an explicit unavailable notice
and log the source reference; they never reuse the same numbers as a fallback.
Books outside the dataset's 89-book scope also show an unavailable notice.
Missing mapped rows within a covered book, invalid references and unknown source
profiles are errors. Native OET-LV callers must pass `OET-LV`, since its Philippians
1:16–17 order differs from `org`.

### Source conventions used by the generator

`initalise.py` explicitly maps each source through the current BibleOrgSys
mapping engine before combining annotations. Source text is never renumbered.

| Source | Declared source profile | Notes |
| --- | --- | --- |
| Curated importance, clarity and textual-issue lists in the script | `eng` | Lists are maintained using conventional English references, including their ranges and editorial halves. |
| Cross-testament quotation OT references | `eng` | Two existing rows use original Psalm numbering: John 19:24 → Psalm 22:19, and 1 Peter 5:7 → Psalm 55:23. `QUOTE_PROFILES` declares these as `org`; the shared quotation source file is unchanged. Only OT quotations currently affect importance. |
| UHB USFM | `eng` | Its stored verse labels are English; alternate Hebrew numbers occur in `\va`. Being Hebrew text does not make its stored labels `org`. |
| OSHB notes in OET-LV OT ESFM | `OET-LV` | This profile uses original OT numbering. |
| NET USX in `copiedBibles/English/NET/` | `eng` for OT and Acts; `org` for the other NT books | Verified against this source's boundary text: Acts retains 19:40–41; 2 Corinthians combines the greetings in 13:12 and has the blessing in 13:13; 3 John ends at 1:15; Revelation 12 ends at 18; Philippians 1:16 is the loving preachers. NET's note at 2 Corinthians 13:12 explains its NA/UBS numbering. |
| CNTR collation `VerseId` | `VLT` | The local collation has original NT divisions but keeps the older Philippians 1:16–17 order, matching BOS's reviewed `VLT` profile. Selfish preaching is at native 1:16 and maps to original 1:17. Acts 19:40 and 2 Corinthians 13:12 are combined; 3 John 1:15 and Revelation 12:18 are separate. |
| OET-RV speaker annotations | `OET-RV` | Uses the edition's explicit profile, including its NT exceptions. The reviewed profile covers the 66-book canon. |
| OET-LV Psalm headings and NT tagged speech verbs | `OET-LV` | Psalm text corroborates titles and shared title/body verses. The NT word table supplements otherwise unnamed speakers using linked subject evidence; its verse references are mapped before use. |

These declarations describe the local editions checked on 2026-10-26. A new
edition or changed verse boundaries require reviewing its profile, not just
comparing verse counts. The quotation overrides address the two identified
mixed-numbering rows; they are not a claim that every quotation's content has
been independently reviewed.

### Splits, merges, halves and missing material

BOS supplies the complete corresponding passage, including groups that cross
chapter boundaries. For example, English Numbers 26:1 covers original
Numbers 25:19 **and** 26:1; English Acts 19:40–41 covers original Acts 19:40.
The generator applies an annotation to that whole indivisible group and records
the coverage in `Comment`. Where evidence overlaps, the strongest importance
(`V > I > M > T`), strongest textual issue, and least clarity (`O > U > C`) win.
Speaker sequences are joined in source order, removing consecutive duplicates.

Our `a`/`b` labels are approximate editorial halves, **not** declared BOS verse
segments. Their parent verse must map exactly one-to-one before the label can
be retained. A half that crosses a split/merged boundary stops generation for
editorial review. Whole-verse footnote and CNTR scores apply to both halves;
the generator does not invent half-verse alignment by halving the collation's
word-row count.

Invalid, ambiguous and unsupported mappings stop generation with the source and
reference identified. The sole mapping-absence exception is a BOS-reviewed
`NO_REFERENCE_COUNTERPART` result (currently English Nehemiah 7:68): it is
reported and omitted, never attached to the next original verse. An OET-RV
unnumbered heading without a declared title coordinate is listed separately in
the build report; it is not assigned to a numbered verse. A mapped NET/UHB
verse-zero title with no stored text supplies no footnote score. Unexpected
missing numbered source verses or required source books are errors.

The local NET USX deliberately omits 16 NT verse numbers. `NET_OMISSION_NOTES`
identifies each missing verse and the location of NET's explanatory
textual-criticism note. The generator verifies that note in the actual input
before assigning the omitted verse a textual-issue score of 2. These are
documented textual omissions, not missing versification relationships. The
omissions and their evidence locations are recorded in the report and comments.

That USX also prints Jonah's `1:17 (2:1)` label as paragraph text instead of a
verse element. The generator restores the explicit 1:17 marker in a temporary
import copy, so BOS can map it to original `JNA_2:1`. It checks the exact printed
label and alternate-number marker, records the repair, and never modifies the
source USX. This repair does not invent a correspondence outside BOS.

The output retains the starter inventory's 89-book scope. The current sources
provide no reviewed annotations for its other books beyond the 66-book canon,
so those rows keep defaults. The starter's Greek Esther counts predate the BOS
`org` profile: regeneration removes `ESG_8:40`, `ESG_8:41`, `ESG_10:14`, and adds
`ESG_4:6`, `ESG_9:5`, `ESG_9:30`. This reconciles its selected books to the current
profile while retaining **41,899 whole-verse addresses**, before editorial splits.
The immutable starter file is preserved for provenance.

### Regenerating and testing

From the repository's `createPages/` directory:

```sh
uv run ../datasets/sentenceImportance/test_initialise.py -v
uv run ../datasets/sentenceImportance/initalise.py --single
```

Paths are resolved from the script's location. Regeneration reads
`sentenceImportance.tsv.init`, **not** the previous generated TSV, along with
the source files listed above and `datasets/crossTestamentQuotes/crossTestamentQuotes.tsv`.
No site build or cached Bible pickle is involved. Manual changes to generated
rows should instead be expressed in the source annotation lists before rebuilding.

The generator builds and validates all rows before replacing the TSV. The first
existing database is preserved as `sentenceImportance.tsv.bak-before-regeneration`;
repeat runs do not overwrite that backup. Mapping, input or validation failures
leave the existing TSV untouched. The staged TSV is installed by an atomic file
replacement.

`sentenceImportance.build.json` records the output profile, BOS reference/data/
policy versions, input file hashes, output hash, counts, seed reconciliation and
omitted source annotations. Both outputs are deterministic for unchanged inputs
and mapping data. Read the report and `Comment` coverage when auditing a build.
The new tests cover Psalm titles, chapter shifts, NT ordering, grouped passages,
editorial halves, quotation conventions, mapped footnotes, repeatability and
preserving the previous output on validation failure.
