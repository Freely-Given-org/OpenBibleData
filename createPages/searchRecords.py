#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Export native Bible records once, independent of their rendered page families.

CHANGELOG:
    2026-11-01 Preserve native verse labels and separate text, headings and notes.
"""
from collections import OrderedDict, defaultdict, Counter
from functools import lru_cache
from pathlib import Path
import logging
import re
from urllib.parse import unquote, urlsplit
import sqlite3
import tempfile
from types import SimpleNamespace

from searchText import FragmentParser, cleanText, plainHtml, usfmText

FORMAT_VERSION = 3


class PublishedPages:
    """Bounded destination checks; retained pages are opt-in per resource family."""
    def __init__(self, root, retained=None):
        self.root = Path(root).resolve()
        self.retained = Path(retained).resolve() if retained else None
        # A bounded disk-backed cache prevents reparsing a large parallel page
        # once for every version while keeping the parent's resident set small.
        self.cacheDirectory = tempfile.TemporaryDirectory(prefix='obd-search-anchors-')
        self.cache = sqlite3.connect(str(Path(self.cacheDirectory.name) / 'anchors.sqlite'))
        self.cache.execute('CREATE TABLE pages (path TEXT PRIMARY KEY, anchors TEXT NOT NULL)')
        self.coverage = defaultdict(Counter)
        self.issues = []

    @lru_cache(maxsize=32)
    def anchors(self, path, retained=True):
        source = self.root / path
        if not source.is_file() and retained and self.retained and path.split('/')[0] in ('ref', 'ilr', 'dct', 'UBS', 'tpc', 'rel'):
            source = self.retained / path
        if not source.is_file():
            return frozenset()
        row = self.cache.execute('SELECT anchors FROM pages WHERE path=?', (str(source),)).fetchone()
        if row:
            return frozenset(row[0].split('\n'))
        parser = FragmentParser()
        # Do not retain all the page's text just to check its anchors.
        parser.handle_data = lambda value: None
        with source.open(encoding='utf-8') as stream:
            for line in stream:
                parser.feed(line)
                parser.parts.clear()
        self.cache.execute('INSERT INTO pages VALUES (?,?)', (str(source),'\n'.join(sorted(parser.ids))))
        return frozenset(parser.ids)

    def close(self):
        self.cache.close()
        self.cacheDirectory.cleanup()
        self.anchors.cache_clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def available(self, href, *, retained=True):
        url = urlsplit(href)
        if url.scheme or url.netloc or url.path.startswith('/') or '..' in Path(unquote(url.path)).parts:
            raise ValueError(f'Unsafe search destination: {href}')
        anchors = self.anchors(unquote(url.path),retained)
        return bool(anchors) and (not url.fragment or unquote(url.fragment) in anchors)


def nativePassages(bible, book):
    """Read stored entries, avoiding CV-index aliases for bridges and suffixes."""
    chapter, verse, entries = '-1', '0', []
    for entry in bible.books[book]._processedLines:
        marker, text = entry.getMarker(), entry.getCleanText()
        if marker in ('c', 'v', 'v='):
            if entries:
                yield (book, chapter, verse), entries
            entries = []
            if marker == 'c':
                chapter, verse = text, '0'
            else:
                verse = text
        if not marker.startswith('¬'):
            entries.append(entry)
    if entries:
        yield (book, chapter, verse), entries


def entryFields(entries, version=None, reference=None):
    fields = {}
    for entry in entries:
        marker, text = entry.getMarker(), entry.getCleanText()
        if marker in ('v~', 'p~', 'd'):
            field = 'body'
        elif marker in ('s', 's1', 's2', 's3', 's4', 'ms1', 'ms2', 'r', 'sr'):
            field = 'heading'
        elif marker.startswith(('ip', 'iq', 'is', 'imt')):
            field = 'introduction'
        else:
            continue
        if text:
            if version:
                from openbibledata_rust import convertVerseEntryListToHtml, do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations
                adjusted = re.sub(r'¦\d+', '', entry.getAdjustedText())
                rendered = convertVerseEntryListToHtml(2, version, reference, 'dictVerse', [],
                    [SimpleNamespace(marker='v~',full_text=adjusted,clean_text=text)],
                    basicOnly=True,colouriseWordClasses=False)
                if version in ('OET-RV', 'OET-LV'):
                    customise = do_OET_RV_HTMLcustomisations if version=='OET-RV' else do_OET_LV_HTMLcustomisations
                    rendered = customise(f'Search {version} {reference}',rendered)
                text = plainHtml(rendered)
            fields.setdefault(field, []).append(cleanText(text))
        for extra in entry.getExtras() or ():
            if extra.getType() in ('fn', 'en', 'xr'):
                note = usfmText('\\f ' + extra.getFullText() + '\\f*').get('note', '')
                if note:
                    fields.setdefault('note', []).append(note)
    return {name: ' '.join(parts) for name, parts in fields.items() if any(parts)}


def nativePoints(reference):
    book, chapter, label = reference
    points = []
    for part in label.split(','):
        match = re.fullmatch(r'(\d+)([a-z]*)(?:-(\d+)([a-z]*))?', part)
        if not match:
            raise ValueError(f'Unsupported native search reference {reference}')
        first, suffix, last, lastSuffix = match.groups()
        if last and (suffix or lastSuffix):
            # Keep partial bridges intact; never claim an invented mapping.
            return ()
        points.extend((book, chapter, str(number), suffix or None)
                      for number in range(int(first), int(last or first) + 1))
    return tuple(points)


def recordLinks(version, reference, state, pages):
    book, chapter, verse = reference
    match = re.match(r'\d+[a-z]*', verse)
    if not match:
        raise ValueError(f'Invalid native search reference: {version} {reference!r}')
    first = match[0]
    suffix = 'Intro' if chapter == '-1' else f'C{chapter}'
    anchor = 'Top' if first == '0' else f'C{chapter}V{first}'
    candidates = {'context': f'{version}/byC/{book}_{suffix}.htm#{anchor}'}
    mapped, status = (), 'unavailable'
    points = nativePoints(reference) if int(chapter) > 0 else ()
    if points:
        from BibleOrgSys.Reference.BibleVersificationMappings import get_default_mapping_engine, MappingStatus
        physical = list(points)
        for original, layouts in getattr(state, 'BibleSourceBookLayouts', {}).get(version, {}).items():
            for start, end, stored, offset in layouts:
                physical = [(original, str(int(c)-offset), v, s)
                            if b == stored and start <= int(c)-offset <= end else (b,c,v,s)
                            for b,c,v,s in physical]
        source = state.BibleVersifications.get(version)
        if source:
            result = get_default_mapping_engine().convert_passage(source, state.navigationVersification, physical)
            status = result.status.value
            if result.status == MappingStatus.EXACT:
                mapped = result.references
                b, c, v, s = mapped[0]
                # Shared pages do not have arbitrary suffixed filenames.
                if not s:
                    candidates['parallel'] = f'par/{b}/C{c}V{v}.htm#{version}'
                    candidates['interlinear'] = f'ilr/{b}/C{c}V{v}.htm#Top'
    # Reused interlinear pages have no source fingerprint. Do not advertise them
    # as context for freshly indexed words merely because an old anchor exists.
    links = {kind: href for kind, href in candidates.items() if pages.available(href,retained=False)}
    if 'context' not in links and 'parallel' in links:
        links['context'] = links['parallel']
    return links, mapped, status


def exportBook(version, book, bible, state, pages):
    """Yield records only for text with an actual published reading destination."""
    annotations = {}
    if isinstance(bible, dict):
        passages = ((tuple(map(str, ref)), usfmText(value)) for ref, value in bible.items() if ref[0] == book)
    else:
        def sourcePassages():
            from searchLexical import entryAnnotations, oetAnnotations
            for ref, entries in nativePassages(bible, book):
                words = entryAnnotations(entries)
                if words:
                    annotations.setdefault(ref, []).extend(words)
                yield ref, entryFields(entries, version, ref)
        passages = sourcePassages()
    combined = OrderedDict()
    for reference, fields in passages:
        if not fields:
            continue
        old = combined.setdefault(reference, {})
        for field, text in fields.items():
            old[field] = ' '.join(filter(None, (old.get(field), text)))
    for reference, fields in combined.items():
        pages.coverage[version,book]['sourcePassages']+=1
        if not re.fullmatch(r'-?\d+',reference[1]) or not re.fullmatch(r'\d+[a-z]*(?:-\d+[a-z]*)?(?:,\d+[a-z]*(?:-\d+[a-z]*)?)*',reference[2]):
            reason='The source has a malformed chapter/verse label; no passage number was guessed.'
            logging.warning('Search omitted %s %s: %s',version,reference,reason)
            pages.coverage[version,book]['malformedReferences']+=1
            pages.issues.append(dict(version=version,reference=list(reference),reason=reason))
            continue
        links, mapped, status = recordLinks(version, reference, state, pages)
        if not links:
            pages.coverage[version,book]['unpublishedPassages']+=1
            logging.info('Search omitted %s %s: no published destination', version, reference)
            continue
        pages.coverage[version,book]['indexedPassages']+=1
        if fields.get('body'):
            from bible_transliterations import transliterate_Greek, transliterate_Hebrew
            if any('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in fields['body']):
                fields['transliteration'] = transliterate_Greek(fields['body'])
            elif any('\u0590' <= c <= '\u05ff' for c in fields['body']):
                fields['transliteration'] = transliterate_Hebrew(fields['body'])
        words = annotations.get(reference, [])
        if version == 'OET-LV' and int(reference[1]) > 0:
            from searchLexical import oetAnnotations
            words = oetAnnotations(reference, state) or words
        yield dict(key=f'{version}:{":".join(reference)}', version=version, ref=list(reference),annotations=words,
                   language=(state.BibleLanguages.get(version) or 'und').lower(), fields=fields,
                   links=links, mapped=[list(ref) for ref in mapped], mapping=status)
