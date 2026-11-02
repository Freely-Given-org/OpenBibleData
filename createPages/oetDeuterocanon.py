#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Reference pages for the independent OET-LV DC lexical draft word table.

CHANGELOG:
    2026-10-29 Preserve DC Greek forms, gloss status and source attribution.
    2026-10-30 Accept the generic source-word column and show Latin LAO provenance.
    2026-10-31 Group words by verse with native LV context, mapped previews and exact lemma links.
    2026-10-31 Connect the DC index to the other lexical resource indexes.
    2026-10-31 Explain conservative draft grammatical colours and their limitations.
    2026-11-01 Search additional-book Greek and Latin words by gloss, transliteration and reference.
    2026-11-02 Place indented prologue previews before their reading links.
"""
from collections import defaultdict
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from xml.sax.saxutils import escape

from html import makeTop, makeBottom, checkHtml
from navigation import bookNavigationOrder
from referencePassages import passageContextHref,renderReferencePassage
from oetPassages import _namespaceIds
from lexicalLinks import prepareLexicalAssociations,lemmaFilename,ubsEntryLink
from referenceIndexes import referenceIndexLinks,dcWordIndexRecords,groupWordIndex,wordIndex
from bible_transliterations import transliterate_Greek
from grammaticalColours import GREEK_CASE_CLASS_KEY_DICT


DC_WORD_TABLE = 'OET-LV_DC_word_table.tsv'
DC_COLUMN_HEADERS = 'Ref\tSourceWord\tLemma\tMorphology\tLexiconGloss\tOETGlossWords\tGlossStatus\tGlossSource\tCandidates\tSourceRef\tSourceFile\tBefore\tAfter'
DC_DRAFT_NOTE = ('<p class="note">These additional books are draft glosses in source-language word order. '
    'Grammar and context require review; unresolved words appear in ⟦brackets⟧. '
    'Draft grammatical colours appear only where the available form analyses agree; '
    'they do not establish grammar in context. '
    'Word links identify LV source words; they do not establish word alignment to the Readers’ Version.</p>')
LAO_DRAFT_NOTE = ('<p class="note">Laodiceans uses Latin source text and provisional OET occurrence glosses, '
    'with explicit OET name equivalents. These AI-assisted drafts require human editorial review. '
    'No Greek lexical or morphological analysis is claimed for these words. '
    'Latin morphology is not yet available, so these words have no grammatical colours.</p>')
LAO_SOURCE_NOTE = ('<p class="note">Latin source: J. B. Lightfoot, '
    '<a href="https://www.gutenberg.org/ebooks/50857">St. Paul’s Epistles to the Colossians and Philemon</a> '
    '(1875), pp. 353–355, public domain, digitised by Project Gutenberg. '
    'The Greek reconstruction is not used. OET verses 16–17 split Lightfoot’s verse 16; '
    'verse 13 preserves his bracketed supplement. Glosses are OET editorial drafts.</p>')
DC_SOURCE_NOTE = ('<p class="note">Greek sources: Brenton’s Septuagint from '
    '<a href="https://ebible.org/">eBible.org</a> (public domain), and H. B. Swete, volume III (1905), '
    'digitised by Harvard College Library and Digital Divide Data, from '
    '<a href="https://github.com/OpenGreekAndLatin/First1KGreek">Open Greek and Latin / First1KGreek</a> '
    '(<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>). '
    'Glosses and forms: <a href="https://www.STEPBible.org/">STEPBible, Tyndale House Cambridge</a>, '
    'and <a href="https://github.com/openscriptures/GreekResources">Open Scriptures Septuagint Project</a> '
    '(<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>). '
    'Changes include lexical lookup, book assembly, OET editorial overrides and ESFM conversion. '
    'Source transcription and OCR errors remain subject to review.</p>')


def dcGrammaticalColourKey(text):
    """Describe just the draft colours present, with one shared colour control."""
    classes = {name for value in re.findall(r'\bclass="([^"]+)"', text) for name in value.split()}
    keys = [key for name,key in GREEK_CASE_CLASS_KEY_DICT.items() if name in classes]
    if not keys:
        return ''
    button = ('' if 'id="coloursButton"' in text else
        '<button type="button" id="coloursButton" title="Hide grammatical colours" '
        'aria-label="Show or hide grammatical colours" onclick="hide_show_colours()">C</button> ')
    return ('<p class="key"><b>Draft grammatical colours</b>: '+button+', '.join(keys)+'. '
        'Colours indicate agreement between available Greek form analyses; grammar in this passage '
        'has not been reviewed. Uncertain words remain uncoloured.</p>')


def dcLemmaLinks(level, state):
    """Exact Greek spellings only; ambiguous matches remain plain source text.

    The resources describe the matching lemma, without assigning their NT
    morphology or Strong's identifiers to the independent DC word occurrence.
    """
    graph = prepareLexicalAssociations(state)
    lemmas = defaultdict(set)
    for language,lemma in graph['availableLemmas']:
        if language == 'Grk':
            label = graph['lemmaLabels'].get((language,lemma),lemma)
            lemmas[unicodedata.normalize('NFC',label)].add(lemma)
    links = {}
    spellings = set(lemmas) | {spelling for language,spelling in graph['ubsByLemma'] if language == 'Grk'}
    for spelling in spellings:
        parts = []
        matches = lemmas.get(spelling,())
        if len(matches) == 1:
            filename = lemmaFilename('Grk',next(iter(matches)))
            parts.append(f'<a href="{"../"*level}ref/GrkLem/{quote(filename)}#Top">OET lemma</a>')
        matches = graph['ubsByLemma'].get(('Grk',spelling),())
        if len(matches) == 1: parts.append(ubsEntryLink(level,next(iter(matches)),graph,label='UBS lemma'))
        if parts: links[spelling] = ' · '.join(parts)
    return links


def dcContextHref(level, reference, state):
    """Chapter zero is native prologue text outside the verse-mapping system."""
    BBB,C,V,suffix = reference
    if C != '0': return passageContextHref(level,reference,'OET-LV',state)
    bible = state.preloadedBibles['OET-LV']
    if not bible.getNumVerses(BBB,'0'):
        # Sirach's source-table prologue groups are stored as unnumbered \ip
        # paragraphs, not as chapter zero or canonical verse numbers.
        try: bible.getContextVerseData((BBB,'-1'))
        except KeyError: return None
        return f'{"../"*level}OET-LV/byC/{BBB}_Intro.htm#Top'
    try: bible.getContextVerseData((BBB,C,V+(suffix or '')))
    except KeyError: return None
    return f'{"../"*level}OET-LV/byC/{BBB}_C0.htm#C0V{V}{suffix or ""}'


def dcVersePreview(level, reference, state):
    BBB,C,V,suffix = reference
    verse = V+(suffix or '')
    if C != '0':
        return renderReferencePassage(level,(reference,),state.BibleVersifications['OET-LV'],state,
            instanceId=f'dc-{BBB}-{C}-{verse}',label=f'{BBB} {C}:{verse}')
    from openbibledata_rust import convertVerseEntryListToHtml
    from html import do_OET_LV_HTMLcustomisations
    href = dcContextHref(level,reference,state)
    if not href: return '<p>LV prologue text unavailable in this build.</p>'
    isIntro = '_Intro.htm' in href
    label = f'OET-LV {BBB} prologue'+(' (complete)' if isIntro else f', verse {verse}')
    jump = f'<p class="referenceJump">Jump to <a href="{href}" data-vref="mapped">{label}.</a></p>'
    if isIntro and verse != '1': return f'<div class="referencePassage">{jump}</div>'
    native = (BBB,'-1') if isIntro else (BBB,C,verse)
    entries,context = state.preloadedBibles['OET-LV'].getContextVerseData(native)
    if isIntro:
        # The public excerpt starts at the actual introduction, not ESFM source
        # metadata or the book-title block that precedes it.
        from bible_organisational_system import InternalBibleEntryList
        introStart = next((index for index,entry in enumerate(entries)
                           if entry.getMarker().startswith(('is','im','ip','io'))),0)
        entries = InternalBibleEntryList(entries[introStart:])
    text = convertVerseEntryListToHtml(level,'OET-LV',native,'dictVerse',context,entries,
        basicOnly=not isIntro,state=state,livenWordLinks=True)
    text = _namespaceIds(do_OET_LV_HTMLcustomisations(f'DC prologue {native}',text),f'dc-{BBB}-0-{verse}_')
    return (f'<div class="referencePassage"><details><summary>Show passage in OET-LV: {BBB} prologue</summary>'
            f'{text}</details>{jump}</div>')


def createDCWordPages(level: int, folder: Path, state) -> None:
    """Group word details by native chapter; anchors retain the table row numbers.

    These pages use the DC table directly, without claiming NT morphology,
    Strong’s numbers or RV word alignment that the draft does not supply.
    """
    table = state.OETRefData['word_tables'].get(DC_WORD_TABLE)
    if table is None:
        return
    assert table[0] == DC_COLUMN_HEADERS, f'Unexpected columns in {DC_WORD_TABLE}: {table[0]!r}'
    loadedBooks = state.preloadedBibles['OET-LV'].books
    selectedBooks = state.booksToLoad['OET-LV']
    chapters = defaultdict(lambda:defaultdict(list))
    lemmaLinks = dcLemmaLinks(level,state)
    contextLinks = {}
    for number, row in enumerate(table[1:], 1):
        fields = row.split('\t')
        assert len(fields) == 13, f'{DC_WORD_TABLE} row {number}: expected 13 columns, got {len(fields)}'
        match = re.fullmatch(r'([A-Z0-9]{3})_(\d+):(\d+[a-z]?)w(\d+)', fields[0])
        assert match, f'{DC_WORD_TABLE} row {number}: invalid reference {fields[0]!r}'
        BBB, C, V, word = match.groups()
        BBB = state.OET_SOURCE_BOOK_ALIASES.get(BBB, BBB)
        if BBB not in loadedBooks or ('ALL' not in selectedBooks and BBB not in selectedBooks):
            continue
        verse = re.fullmatch(r'(\d+)([a-z]?)',V)
        reference = (BBB,C,verse[1],verse[2] or None)
        if reference not in contextLinks:
            contextLinks[reference] = dcContextHref(level,reference,state)
        href = contextLinks[reference]
        wordLabel = f'{V} word {word}'
        detail = [f'<a href="{href}">{wordLabel}</a>' if href else wordLabel,
                  *(escape(value) for value in fields[1:8]),escape(fields[9]),escape(fields[10])]
        if BBB != 'LAO' and (links:=lemmaLinks.get(unicodedata.normalize('NFC',fields[2]))):
            detail[2] += f'<br><small>{links}</small>'
        cells = ''.join(f'<td>{value}</td>' for value in detail)
        chapters[BBB, C][V].append(f'<tr id="W{number}">{cells}</tr>')
    if not chapters:
        return
    folder.mkdir(parents=True, exist_ok=True)
    indexLinks = []
    for BBB in bookNavigationOrder(dict.fromkeys(BBB for BBB, C in chapters), 'OET-LV'):
        for book, C in sorted(chapters, key=lambda key: int(key[1])):
            if book != BBB:
                continue
            language = 'Latin' if BBB == 'LAO' else 'Greek'
            title = f'OET-LV {BBB} {"prologue" if C=="0" else C} {language} word details'
            filename = f'{BBB}_C{C}.htm'
            indexLinks.append(f'<a href="{filename}#Top">{BBB} {C}</a>')
            top = makeTop(level, None, 'word', None, state).replace('__TITLE__', title).replace('__KEYWORDS__', f'Bible, {language}, deuterocanon, words')
            headings = ''.join(f'<th>{label}</th>' for label in ('Verse / word', f'{language} form', 'Lemma', 'Morphology',
                'Lexicon gloss', 'OET gloss', 'Gloss status', 'Gloss source', 'Source reference', 'Source file'))
            verseGroups = []
            for V,rows in sorted(chapters[BBB,C].items(),key=lambda item:(int(re.match(r'\d+',item[0])[0]),item[0])):
                number = re.fullmatch(r'(\d+)([a-z]?)',V)
                passage = dcVersePreview(level,(BBB,C,number[1],number[2] or None),state)
                verseLabel = f'Source prologue group {V}' if C=='0' else f'Verse {V}'
                verseGroups.append(f'<section><h2 id="V{V}">{verseLabel}</h2>{passage}'
                    f'<div class="dcWordTable"><table><tr>{headings}</tr>'+''.join(rows)+'</table></div></section>')
            chapterHref = (dcContextHref(level,(BBB,C,next(iter(chapters[BBB,C])),None),state) if C=='0'
                           else f'{"../"*level}OET-LV/byC/{filename}#Top')
            chapterLink = f'<a href="{chapterHref}">Read OET-LV {BBB} {"prologue" if C=="0" else C}</a>' if chapterHref else ''
            content = (f'{top}<h1 id="Top">{title}</h1>\n'
                f'<p><a href="index.htm#Top">DC word index</a> '
                f'{chapterLink}</p>\n'
                f'{LAO_DRAFT_NOTE if BBB == "LAO" else DC_DRAFT_NOTE}\n'
                + '\n'.join(verseGroups) + f'\n{LAO_SOURCE_NOTE if BBB == "LAO" else DC_SOURCE_NOTE}\n'
                + makeBottom(level, None, 'word'))
            assert checkHtml(title, content)
            (folder / filename).write_text(content, encoding='utf-8')
    title = 'OET-LV additional-book word details (Greek and Latin)'
    groups=groupWordIndex(dcWordIndexRecords(state),transliterate_Greek)
    for transliterated in (False,True):
        other='index.htm' if transliterated else 'transIndex.htm'
        otherLabel='Original spelling order' if transliterated else 'Transliterated order'
        index = (makeTop(level, None, 'wordIndex', None, state).replace('__TITLE__', title)
            .replace('__KEYWORDS__', 'Bible, Greek, Latin, deuterocanon, words')
            + f'<h1 id="Top">{title}</h1>\n'+referenceIndexLinks(level,state,includeCore=True)+f'{DC_DRAFT_NOTE}\n{LAO_DRAFT_NOTE}\n'
            + f'<p><a href="{other}#Top">{otherLabel}</a></p>'
            + wordIndex(level,groups,folder,transliterated=transliterated)
            + '<details><summary>Browse word details by chapter</summary><p>'+' '.join(indexLinks)+'</p></details>'
            + f'\n{DC_SOURCE_NOTE}\n{LAO_SOURCE_NOTE}\n' + makeBottom(level, None, 'wordIndex'))
        assert checkHtml(title, index)
        (folder / ('transIndex.htm' if transliterated else 'index.htm')).write_text(index, encoding='utf-8')
