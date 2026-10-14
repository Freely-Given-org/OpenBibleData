#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Pair English OET-RV passages with complete BOS-mapped OET-LV passages.

Split the source entries before rendering, rather than cutting translated HTML
at matching numbers. The renderer remains responsible for balanced markup and
word links. Import it only when rendering, so the mapping can be tested offline.
"""
import logging
import re

from BibleOrgSys.Internals.InternalBiblePassages import passageReferencesFromEntries
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingError
from versification import combinedPassageLabel


def oetRVChunks(bible, BBB, chapter=None):
    """Yield (starting reference, entries, context) at RV chapter/section breaks.

    CV-index boundaries keep headings and paragraph starts with their verse.
    A chapter's title stays with its first numbered section. Book headers and
    introductions are editorial chunks, not scripture verse zero.
    """
    entries, _context = bible.getContextVerseData((BBB,))
    records = [(cv, ix) for cv, ix in bible[BBB]._CVIndex.items()
               if chapter is None or cv[0] == str(chapter)]
    if not records:
        raise KeyError((BBB, chapter))
    records.sort(key=lambda item: item[1].getEntryIndex())
    start = records[0][1].getEntryIndex()
    end = records[-1][1].getNextEntryIndex()
    boundaries = [(start, (BBB, *records[0][0]), records[0][1].getContextList())]
    lastC, haveVerse = records[0][0][0], False
    for (C,V), index in records:
        ix, nextIx = index.getEntryIndex(), index.getNextEntryIndex()
        markers = {entry.getMarker() for entry in entries[ix:nextIx]}
        newChunk = C != lastC or ('intro' in markers and C == '-1') \
            or (haveVerse and bool(markers & {'s1','ms1'}))
        if ix > boundaries[-1][0] and newChunk:
            boundaries.append((ix, (BBB,C,V), index.getContextList()))
            haveVerse = False
        haveVerse |= 'v' in markers
        lastC = C
    for n, (ix, reference, context) in enumerate(boundaries):
        nextIx = boundaries[n+1][0] if n+1 < len(boundaries) else end
        yield reference, entries[ix:nextIx], context


def _editorialLV(bible, reference, sourceEntries):
    """Match headers/introduction by role, never by RV pseudo-verse line numbers."""
    BBB = reference[0]
    if BBB not in bible and BBB not in bible.availableBBBs:
        return []
    try:
        entries, context = bible.getContextVerseData((BBB,'-1'))
    except (KeyError, TypeError):
        return []
    sourceMarkers = {e.getMarker() for e in sourceEntries}
    introIx = next((n for n,e in enumerate(entries) if e.getMarker() == 'intro'), len(entries))
    haveIntro = any(m.startswith('i') and m not in ('id','ide') for m in sourceMarkers)
    if not haveIntro:
        entries = entries[:introIx]
    elif not sourceMarkers & {'headers','mt1','mt2','id'}:
        entries = entries[introIx:]
    return [((BBB,'-1','0'), entries, context)] if entries else []


def mappedOETLVPortions(bible, reference, sourceEntries, state, chapterCache):
    """Fetch complete native portions, including any indivisible mapping group."""
    return _mappedOETLVPassage(bible, reference, sourceEntries, state, chapterCache)[0]


def _mappedOETLVPassage(bible, reference, sourceEntries, state, chapterCache):
    """Keep BOS coverage metadata available to the OBD renderer."""
    if reference[1] == '-1':
        return _editorialLV(bible, reference, sourceEntries), ''
    references = passageReferencesFromEntries(reference, sourceEntries, state.navigationVersification)
    if not references: # editorial heading without scripture
        return [], ''
    passage = bible.getMappedPassage(state.navigationVersification, references,
        chapterCache=chapterCache, combineAdjacent=True, expandGroups=True)
    return passage.portions, combinedPassageLabel(passage)


def _namespaceIds(html, prefix):
    """Isolate LV addresses and per-render notes from English navigation anchors."""
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    html = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m[1]}"', html)
    return re.sub(r'href="#([^"]+)"',
                  lambda m: f'href="#{prefix}{m[1]}"' if m[1] in ids else m[0], html)


def renderOETLVPassage(level, bible, reference, sourceEntries, segmentType, state,
                       chapterCache, chunkNumber=0):
    """Return (LV HTML, first native reference) for an RV passage.

    Non-exact mappings and absent text are explicit. Never reuse RV numbers or
    display an incomplete mapped group as though it were the complete passage.
    """
    from openbibledata_rust import convertVerseEntryListToHtml
    from html import do_OET_LV_HTMLcustomisations

    try:
        portions, combinedLabel = _mappedOETLVPassage(bible, reference, sourceEntries, state, chapterCache)
    except VersificationMappingError as error:
        logging.warning('OET %s %s LV alignment unavailable: %s', segmentType, reference, error)
        return f'<p class="error">OET-LV passage alignment unavailable ({error.result.status.value}).</p>', None
    except KeyError as error:
        logging.warning('OET %s %s missing mapped LV passage: %s', segmentType, reference, error)
        return '<p class="error">OET-LV passage is not available in this edition.</p>', None
    bits = [f'<p class="rem">{combinedLabel}</p>'] if combinedLabel else []
    for partNumber, (nativeRef, entries, context) in enumerate(portions):
        html = convertVerseEntryListToHtml(level, 'OET-LV', nativeRef, segmentType,
            context, entries, basicOnly=False, state=state, livenWordLinks=True, colouriseWordClasses=False,
            navigationVersion='OET')
        html = do_OET_LV_HTMLcustomisations(f'{segmentType}={nativeRef}', html)
        if nativeRef[1] != '-1' and (nativeRef[:2] != reference[:2] or partNumber):
            html = f'<p class="rem">Literal Version {nativeRef[0]} {nativeRef[1]}:{nativeRef[2]}</p>\n{html}'
        bits.append(_namespaceIds(html, f'LV{chunkNumber}_{partNumber}_'))
    return '\n'.join(bits), portions[0][0] if portions else None


def renderOETSideBySideChunks(level, rvBible, lvBible, BBB, segmentType, state, chapter=None):
    """Render book/chapter rows from RV entries, returning HTML and an LV link."""
    from openbibledata_rust import convertVerseEntryListToHtml
    from html import do_OET_RV_HTMLcustomisations

    rows, firstNative, cache = [], None, {}
    for number, (reference, entries, context) in enumerate(oetRVChunks(rvBible, BBB, chapter)):
        rvHtml = convertVerseEntryListToHtml(level, 'OET-RV', reference, segmentType,
            context, entries, basicOnly=False, state=state, livenWordLinks=True, colouriseWordClasses=False)
        rvHtml = do_OET_RV_HTMLcustomisations(f'{segmentType}={reference}', rvHtml)
        # Notes restart on each converter call; retain RV CV ids for navigation.
        rvHtml = re.sub(r'(id="|href="#)((?:fn|footnotes|crossRefs|xr)[^"]*)"',
                        lambda m: f'{m[1]}RV{number}_{m[2]}"', rvHtml)
        lvHtml, nativeRef = renderOETLVPassage(level, lvBible, reference, entries,
                                             segmentType, state, cache, number)
        if firstNative is None and nativeRef is not None and nativeRef[1] != '-1':
            firstNative = nativeRef
        rows.append(f'<div class="chunkRV">{rvHtml}</div><!--chunkRV-->\n'
                    f'<div class="chunkLV">{lvHtml}</div><!--chunkLV-->\n')
    return ''.join(rows), firstNative


def oetLVSourceLink(level, BBB, nativeRef):
    """A native book anchor also works for passages crossing LV chapters."""
    book, chapter, verse = nativeRef if nativeRef else (BBB,'-1','0')
    anchor = f'C{chapter}V{verse}' if chapter != '-1' else 'Top'
    return f'{"../"*level}OET-LV/byDoc/{book}.htm#{anchor}'
