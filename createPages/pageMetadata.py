#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Plain-text search metadata for Bible passage and word pages.

CHANGELOG:
    2026-11-05 Identify sections and individual source-word occurrences by passage.
    2026-11-05 Describe lexical resources and share escaping with their standalone indexes.
    2026-11-05 Distinguish book text, chapter text, introductory material and reading indexes.
    2026-11-05 Identify verse comparisons, introductions and available interlinear material.
    2026-11-05 Resolve preferred public URLs for copies while preserving offline navigation.
"""
from functools import cache
import re
from textwrap import shorten
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape

from searchReferences import searchBookName
from searchText import plainHtml, usfmText


def escapedMetadata(metadata, testMode):
    """Return one HTML title value and one double-quoted attribute value."""
    title, description = metadata
    assert title.strip() and description.strip(), metadata
    title = ' '.join(title.split()) + (' TEST' if testMode else '')
    return escape(title), escape(shorten(description, width=240, placeholder='…'), {'"': '&quot;'})


def publicCanonicalUrl(state, path):
    base = getattr(state, 'PUBLIC_BASE_URL', None)
    if not base or getattr(state, 'TEST_MODE_FLAG', False):
        return None
    url = urlsplit(base)
    if url.scheme not in ('http', 'https') or not url.netloc or url.query or url.fragment:
        raise ValueError(f'Expected an absolute site URL in PUBLIC_BASE_URL, got {base!r}')
    return f'{base.rstrip("/")}/{quote(path, safe="/")}'


def lemmaMetadata(language, spelling, transliteration, gloss):
    term = f'{spelling} ({transliteration})'
    title = f'{term} — {language} lemma'
    description = f'Explore the forms and recorded uses of the {language} lemma {term}.'
    if gloss:
        description += f' English glosses include “{gloss}”.'
        if len(gloss) <= 48:
            title = f'{term} — {gloss} | {language} lemma'
    return title, description


def hebrewTableLanguages(table, rows):
    """A lemma or word form can have both Hebrew and Aramaic occurrences."""
    languages = set()
    for row in rows:
        rowType = table[row].split('\t', 2)[1]
        languages.add('Aramaic' if rowType.startswith('A') else 'Hebrew')
        if len(languages) == 2:
            return 'Hebrew and Aramaic'
    return next(iter(languages), 'Hebrew')


def strongsMetadata(code, word, definition):
    title = f'Strong’s {code}'
    if not word:
        if definition == 'Not Used':
            return f'{title} — unused number', f'The lexicon lists {title} as unused.'
        return title, plainHtml(definition) or f'Look up {title} in the biblical lexicon.'
    transliteration = word[3] if code.startswith('H') else word[1]
    term = f'{word[0]} ({transliteration})' if transliteration else word[0]
    # Prefer an explicitly marked gloss. Other entries contain free-form definitions.
    shortGloss = re.search(r'<def>(.*?)</def>', definition, re.DOTALL)
    gloss = plainHtml(shortGloss[1]) if shortGloss else ''
    description = plainHtml(definition)
    description = f'{term} ({code}) — {description}' if description else f'Read the lexical entry for {term}, {title}.'
    title += f' — {term}'
    if gloss and len(gloss) <= 48:
        title += f' — {gloss}'
    return title, description


def lexicalIndexMetadata(collection, kind, count, *, transliterated=False):
    order = 'transliterations' if transliterated else 'original spellings'
    title = f'{collection} {kind} index — {order}'
    unit = 'lemma' if kind == 'lemma' else 'spelling'
    description = f'Browse {count:,} {unit}{"s" if count != 1 else ""} by {order} in the {collection} {kind} index.'
    return title, description


@cache
def metadataBookName(book, version):
    traditional = (searchBookName(book, None) or book).strip()
    if version is None:
        return traditional
    editionName = (searchBookName(book, version) or traditional).strip()
    if editionName == traditional:
        return traditional
    primary = editionName.split('/')[0].strip()
    return primary if primary == traditional else f'{primary} ({traditional})'


def bookReadingMetadata(version, book, state):
    name = metadataBookName(book, version)
    return f'{name} — whole document | {version}', f'Read {name} on one page in {state.BibleNames[version]}.'


def chapterReadingMetadata(version, book, chapter, state):
    name = metadataBookName(book, version)
    if chapter is None:  # Front matter and other unchaptered documents.
        return f'{name} — chapter view | {version}', f'Read {name} from {state.BibleNames[version]} in the chapter view.'
    passage = f'{name} introduction' if chapter == -1 else f'{name} {chapter}'
    return f'{passage} | {version}', f'Read {passage} in {state.BibleNames[version]}.'


def readingIndexMetadata(version, view, state, book=None):
    edition = state.BibleNames[version]
    if book is None:
        return f'{version} — books by {view}', f'Choose a book in {edition} to read it by {view}.'
    name = metadataBookName(book, version)
    return f'{name} — {view} index | {version}', f'Choose a {view} of {name} to read in {edition}.'


def studyIndexMetadata(view, book=None):
    label = view if view.startswith('OET') else view.lower()
    if book is None:
        return f'{view} — Bible book index', f'Choose a Bible book to browse its {label} pages.'
    name = metadataBookName(book, None)
    return f'{name} — {label} index', f'Choose a passage in {name} for the {label} view.'


def verseStudyMetadata(view, book, chapter, verse, *, chapterNotes=False, interlinearLanguage=None):
    name = metadataBookName(book, None)
    if chapter == -1:
        return f'{name} introduction — {view}', f'Browse introductory material for {name} in the {view.lower()} view.'
    if chapterNotes:
        return f'{name} {chapter} introduction — {view}', f'Read the chapter introduction and available study notes for {name} {chapter}.'
    passage = f'{name} {chapter}:{verse}'
    if view == 'Parallel translations':
        return f'{passage} — compare Bible translations', f'Compare translations of {passage} and explore the study material available for this verse.'
    if view == 'Simple verse list':
        return f'{passage} — simple verse list', f'Read the available translations of {passage} together in a compact list.'
    assert view == 'OET interlinear', view
    if interlinearLanguage:
        return f'{passage} — {interlinearLanguage} interlinear | OET', f'Study {passage} in source-word order and OET English order, with word-level details.'
    return f'{passage} — OET interlinear', f'View the OET interlinear page for {passage}. Word-level alignment is unavailable for this passage.'


def sectionMetadata(version, book, startC, startV, endC, endV, heading, *, related=False, paired=False):
    name = metadataBookName(book, version)
    start = f'{startC}:{startV}'
    if startC == '-1':
        unit = 'line' if startV == endV else 'lines'
        start = f'introduction, {unit} {startV}'
    if startC != endC:
        start += f'–{endC}:{endV}'
    elif startV != endV:
        start += f'–{endV}'
    reference = f'{name} {start}'
    heading = plainHtml(heading)
    heading = usfmText(heading).get('body', '') if '\\' in heading or '¦' in heading else heading
    subject = f'{reference} — {heading}' if heading else reference
    if related:
        return f'{subject} | {version} related passages', f'Explore related passages and cross-references for {subject} in {version}.'
    edition = 'the Open English Translation’s Readers’ and Literal Versions side by side' if paired else version
    return f'{subject} | {version}', f'Read {subject} in {edition}.'


def wordMetadata(language, book, chapter, verse, position, form, glossHtml, *, variant=False):
    reference = f'{metadataBookName(book, None)} {chapter}:{verse}, word {position}'
    title = f'{form} — {reference} ({language})'
    description = f'{language} {"variant reading" if variant else "word"} {form} at {reference}.'
    gloss = plainHtml(glossHtml).replace('_', ' ').replace('=', ' ').strip()
    if gloss and gloss != '???':
        description += f' The English gloss is “{gloss}”.'
    return title, description
