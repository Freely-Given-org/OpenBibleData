#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Map English parallel-page addresses to the addresses actually stored in a Bible.

Keep this module independent of the site renderer so it can be tested with small
USFM fixtures. BOS owns the mapping data and all decisions about correspondence.
"""
from functools import lru_cache
import re

from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBiblePassages import MissingPassageBookError as MissingMappedBookError
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, VersificationMappingError, get_default_mapping_engine,
)
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem


def configureBibleVersification(bible, versionAbbreviation, state):
    """Apply site declarations to fresh AND cached Bibles before they are used.

    None leaves the decision to BOS metadata. Never infer a system from language,
    observed counts, or the Bible's abbreviation. Settings changes also apply to
    old pickles without forcing an expensive reload of the Bible text.
    """
    name = state.BibleVersifications[versionAbbreviation]
    if name is not None:
        bible.setVersificationSystem(name)
    else:
        bible.clearVersificationSystem()
    return bible


@lru_cache(maxsize=8)
def navigationVersification(name='eng'):
    return BibleVersificationSystem(name)


@lru_cache(maxsize=8)
def _navigationBible(name):
    return Bible(versification=name)


@lru_cache(maxsize=32768)
def _mapReference(sourceSystem, targetSystem, reference):
    # Most versions share a numbering profile. Cache per profile, not per Bible;
    # bound the cache so a full-site build cannot retain millions of results.
    return get_default_mapping_engine().convert(sourceSystem, targetSystem, (reference,))


def parallelVerseReferences(versionAbbreviation, bible, reference, state):
    """Return every exact native reference, in BOS order, or raise its typed error.

    Introductions are editorial material, not scripture verse zero. A declared
    Psalm title is mapped normally. Other chapter introductions are retrieved
    only when the mapped first verse really starts a native chapter. Book
    introductions retain their book identity. Empty tuple means no corresponding
    chapter introduction, not a failed scripture mapping.
    """
    BBB, C, V = map(str, reference)
    if C == '-1':
        return ((BBB, C, V, None),)
    source = state.navigationVersification
    target = (state.BibleVersifications[versionAbbreviation]
              if isinstance(bible, dict) else bible.getVersificationSystemName())
    target = target or 'undeclared'
    ref = (BBB, C, V, None)
    if V == '0':
        title = _mapReference(source, source, ref)
        # Only an undeclared zero denotes editorial material. Do not hide a
        # real title's ambiguous/unsupported mapping behind an intro fallback.
        if any(d.code == 'UNDECLARED_TITLE' for d in title.diagnostics):
            first = _mapReference(source, target, (BBB, C, '1', None))
            if first.status == MappingStatus.EXACT and len(first.references) == 1:
                book, chapter, verse, suffix = first.references[0]
                if verse == '1' and suffix is None:
                    return _storedReferences(versionAbbreviation, ((book, chapter, '0', None),), state)
            return ()
    result = (_navigationBible(source).convertToVersification(bible, BBB, C, V, detailed=True)
              if target == 'undeclared' and not isinstance(bible, dict)
              else _mapReference(source, target, ref))
    if result.status != MappingStatus.EXACT:
        raise VersificationMappingError(result)
    return _storedReferences(versionAbbreviation, result.references, state)


def _storedReferences(version, references, state):
    """Apply explicitly declared storage identities (not inferred book aliases)."""
    layouts = getattr(state, 'BibleSourceBookLayouts', {}).get(version, {})
    stored = []
    for BBB, C, V, suffix in references:
        for first, last, book, offset in layouts.get(BBB, ()):
            if first <= int(C) <= last:
                BBB, C = book, str(int(C) + offset)
                break
        stored.append((BBB,C,V,suffix))
    return tuple(stored)


def getVersePortions(bible, references, chapterCache):
    """Adapt selected-excerpt dictionaries and editorial pages to BOS retrieval.

    Native scripture retrieval, bridges, suffixes, and complete-group fetching
    belong to BOS. Edition-specific book layouts have already been applied by
    parallelVerseReferences before this adapter is called.
    """
    references = tuple(references)
    if isinstance(bible, dict):
        return [((BBB,C,V + (suffix or '')), bible[(BBB,C,V + (suffix or ''))], None)
                for BBB,C,V,suffix in references]
    if references and references[0][1] == '-1':
        assert len(references) == 1 # A standalone book-introduction page.
        BBB,C,V,suffix = references[0]
        native = (BBB,C,V + (suffix or ''))
        if BBB not in bible and BBB not in bible.availableBBBs:
            raise MissingMappedBookError(native)
        data = bible.getContextVerseData((BBB,C))
        if data is None:
            raise MissingMappedBookError(native)
        entries, context = data
        return [(native, entries, context)]
    return bible.getPassageData(references, chapterCache=chapterCache)


def versePortionHtml(html, version, nativeRef, pageRef, portionNumber):
    """Label changed addresses and isolate ids/callers in additional portions."""
    # Native footnote return addresses need a real anchor on this English page.
    BBB, C, V = nativeRef
    html = html.replace(f'href="#C{C}V{V}"', f'href="#{version}"')
    if portionNumber:
        ids = re.findall(r'\bid="([^"]+)"', html)
        for original in dict.fromkeys(ids):
            replacement = f'{original}_part{portionNumber+1}'
            html = html.replace(f'id="{original}"', f'id="{replacement}"')
            html = html.replace(f'href="#{original}"', f'href="#{replacement}"')
    if tuple(nativeRef) != tuple(pageRef) and nativeRef[1] != '-1':
        BBB, C, V = nativeRef
        label = f'<small class="versificationRef">({BBB} {C}:{V})</small>'
        # Immediately after the version label, before the verse's own markup.
        html = html.replace('</a></span>', f'</a></span> {label}', 1)
    return html
