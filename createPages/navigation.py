#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0

"""OBD URLs and rendered links across Bible versifications.

BOS decides correspondence. This module chooses site destinations and retains
native labels, source word filenames, and edition-specific storage identities.

CHANGELOG:
    2026-10-17 Exclude books without navigation chapter counts from links and page jobs.
    2026-10-23 Preserve RV-native destinations in combined OET section pages.
    2026-10-24 Centralise OET/traditional book ordering, abbreviations and names.
    2026-10-26 Include declared titles and source Psalm headings in verse navigation.
"""
import logging
import re

import bos_books_codes_py
from openbibledata_rust import getOETTidyBBB, getOETBookName
from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus, VersificationMappingError
from settings import reorderBooksForOETVersions
from versification import _mapReference, _storedReferences, navigationVersification, parallelVersePassage


VERSE_BOOK_NAVIGATION_VIEWS = ('ParallelVerse', 'InterlinearVerse', 'VerseList',
                             'ParallelIndex', 'InterlinearIndex', 'VerseListIndex')


def verseNavigationFirstVerses(BBB, numChapters, versions, state):
    """Start at zero for scripture titles, including unnumbered Psalm d headings.

    BOS declares titles that participate in verse-number mappings. Other Psalm
    headings (e.g. Psalm 11) are stored as chapter introductions; inspect their
    mapped source entries without treating ordinary introductions as verses.
    """
    firstVerses = {}
    chapterCache = {}
    profile = state.navigationVersification
    for c in range(1, numChapters+1):
        reference = (BBB, str(c), '0')
        title = _mapReference(profile, profile, (*reference, None))
        firstVerses[c] = 0 if title.status == MappingStatus.EXACT else 1
        if BBB != 'PSA' or firstVerses[c] == 0:
            continue
        for version in versions:
            bible = state.preloadedBibles.get(version)
            if bible is None:
                continue
            try:
                portions, _label = parallelVersePassage(version, bible, reference, state, chapterCache)
            except (KeyError, VersificationMappingError):
                continue # This edition does not supply a heading at this address.
            if any('\\d ' in entries if isinstance(entries, str)
                   else any(entry.getMarker() == 'd' for entry in entries)
                   for _ref, entries, _context in portions):
                firstVerses[c] = 0
                break
    return firstVerses


def usesOETBookNames(workAbbreviation):
    """Shared study views follow the OET; individual editions follow their own style."""
    return workAbbreviation in ('OET', 'OET-RV', 'OET-LV', 'Related OET-RV',
                               *VERSE_BOOK_NAVIGATION_VIEWS)


def bookNavigationOrder(books, workAbbreviation):
    """Return a new list in OET order or traditional BOS print order."""
    return (reorderBooksForOETVersions(list(books)) if usesOETBookNames(workAbbreviation)
            else bos_books_codes_py.get_sequence_list(list(books)))


def bookAbbreviation(BBB, workAbbreviation, *, titleCase=False, addNotes=False):
    """Use traditional abbreviations outside OET, including numbered books."""
    if usesOETBookNames(workAbbreviation):
        return getOETTidyBBB(BBB, titleCase=titleCase, addNotes=addNotes)
    return bos_books_codes_py.tidy_bbb(BBB, title_case=titleCase, insert_char='\u202f')


def bookName(BBB, workAbbreviation):
    """Name for a book link's hover text, matching its containing page."""
    return (getOETBookName(BBB) if usesOETBookNames(workAbbreviation)
            else bos_books_codes_py.get_english_name_nr(BBB))


def navigationBookList(books, state, pageType):
    """Keep source order, selecting books with a defined navigation address space.

    BOS returns None for valid book identities absent from a profile (e.g. ESA
    in eng). Do not substitute a source Bible's counts: that would create pages
    with native numbering under English navigation addresses.
    """
    system = navigationVersification(state.navigationVersification)
    result = []
    for BBB in books:
        if not bos_books_codes_py.is_chapter_verse_book(BBB):
            continue
        if not system.getNumChapters(BBB):
            logging.warning(f'Skipping {pageType} pages and navigation links for {BBB}: '
                f'no chapter information in navigation versification {state.navigationVersification!r}')
            continue
        result.append(BBB)
    return result


def _versionProfile(version, state):
    declared = state.BibleVersifications.get(version)
    bible = getattr(state, 'preloadedBibles', {}).get(version)
    return declared or (bible.getVersificationSystemName() if bible and not isinstance(bible, dict) else None)


def mappedReferences(reference, sourceVersion, targetVersion, state):
    BBB, C, V = map(str, reference[:3])
    match = re.fullmatch(r'(\d+)([a-z]*)', V)
    if not match or int(C) < 1:
        return ()
    verse, suffix = match.groups()
    # Reverse the explicit import layout before handing a reference to BOS.
    for book, layouts in getattr(state, 'BibleSourceBookLayouts', {}).get(sourceVersion, {}).items():
        for first, last, storedBook, offset in layouts:
            if BBB == storedBook and first <= int(C)-offset <= last:
                BBB, C = book, str(int(C)-offset)
                break
    source, target = _versionProfile(sourceVersion, state), _versionProfile(targetVersion, state)
    if not source or not target:
        return ()
    ref = (BBB,C,verse,suffix or None)
    if source == target:
        refs = (ref,)
    else:
        result = _mapReference(source, target, ref)
        if result.status != MappingStatus.EXACT:
            return ()
        refs = result.references
    return _storedReferences(targetVersion, refs, state)


def referenceHref(level, reference, version='OET', view='byC'):
    BBB,C,V,*suffix = reference
    V = str(V) + ((suffix[0] or '') if suffix else '')
    prefix = '../' * level
    if view in ('par','ilr','lst'):
        # English page addresses have no suffix; a mapped suffix belongs to
        # that whole verse page.
        return f'{prefix}{view}/{BBB}/C{C}V{re.match(r"\d+", V)[0]}.htm#Top'
    if view == 'byDoc':
        return f'{prefix}{version}/byDoc/{BBB}.htm#C{C}V{V}'
    return f'{prefix}{version}/byC/{BBB}_C{C}.htm#C{C}V{V}'


def scriptureLink(level, reference, sourceVersion, targetVersion, view, label, state, title='View passage'):
    refs = mappedReferences(reference, sourceVersion, targetVersion, state)
    if not refs:
        return label
    links = []
    for ref in refs:
        text = label if len(refs) == 1 else f'{label} ({ref[0]} {ref[1]}:{ref[2]}{ref[3] or ""})'
        links.append(f'<a title="{title}" data-vref="mapped" href="{referenceHref(level, ref, targetVersion, view)}">{text}</a>')
    return ' / '.join(dict.fromkeys(links))


_ANCHOR = re.compile(r'<a\b([^>]*?)href="([^"]+)"([^>]*)>(.*?)</a>', re.DOTALL)
_VERSE_PAGE = re.compile(r'(?:[./]*(par|ilr|lst)/([A-Z0-9]{3})/|([./]*)(?:([A-Z0-9]{3})/)?)C(\d+)V(\d+[a-z]*).htm(?:#[^\"]*)?$')
_VERSION_PAGE = re.compile(r'([./]*)([A-Za-z0-9][^/]*)/by(C|Doc|Sec)/([A-Z0-9]{3})(?:_C(\d+)|_S(\d+))?\.htm(?:#(.*))?$')
_LOCAL_PAGE = re.compile(r'(?:\.\./by(?:C|Doc|Sec)/)?([A-Z0-9]{3})(?:_C(\d+)|_S(\d+))?\.htm(?:#(.*))?$')


def _pageReference(BBB, C, section, anchor, sourceVersion, state):
    if anchor and (match := re.fullmatch(r'C(\d+)(?:V(\d+[a-z]*))?', anchor)):
        return BBB, match[1], match[2] or '1'
    if section:
        sections = getattr(state, 'sectionsListsForSections', {}).get(sourceVersion, {}).get(BBB, ())
        for record in sections:
            if str(record[0]) == section:
                return BBB, str(record[1]), str(record[2])
        return None
    if C:
        verse = anchor[1:] if anchor and re.fullmatch(r'V\d+[a-z]*', anchor) else '1'
        return BBB,C,verse
    return None # A book/index link has no verse position to map.


def mapHtmlLinks(html, sourceVersion, level, state, *, segmentType='', reference=(), navigationVersion=None,
                 versionBar=False):
    """Translate scripture destinations, leaving word IDs and external URLs alone.

    navigationVersion is the version of the containing page (OET for combined
    rows). It can differ from the native version of the rendered text. An
    unavailable mapping removes the link, retaining its readable contents.
    """
    if sourceVersion not in getattr(state, 'BibleVersifications', {}):
        return html # Standalone renderer callers without site declarations.
    pageVersion = navigationVersion or ('OET' if segmentType in (
        'parallelVerse','interlinearVerse','simpleVerse','topicalPassage','relatedPassage') else sourceVersion)
    def replace(match):
        before, href, after, label = match.groups()
        if 'data-vref="mapped"' in before + after:
            return match[0]
        if '://' in href or href.startswith(('mailto:','//')):
            return match[0]
        target, ref, view = None, None, 'byC'
        canonical = False
        if m := _VERSION_PAGE.fullmatch(href):
            _, target, _, BBB, C, section, anchor = m.groups()
            if target not in state.BibleVersifications:
                return match[0]
            if not versionBar and sourceVersion == 'OET-RV' and target == 'OET' and m[3] == 'Sec':
                # Combined OET sections use the RV section files and native RV
                # anchors. Their addresses are not the OET/eng chapter system.
                return f'<a{before}data-vref="mapped" href="{href}"{after}>{label}</a>'
            ref = _pageReference(BBB,C,section,anchor,sourceVersion,state)
            view = 'byDoc' if m[3] == 'Doc' else 'byC'
            # Section IDs are edition-specific, even with identical numbering.
            # Version switching uses the retained verse in a chapter page.
            canonical = versionBar and (m[3] == 'Sec' or (bool(anchor) and not C and m[3] == 'C'))
        elif not versionBar and (m := _VERSE_PAGE.fullmatch(href)):
            folder, BBB, _, otherBBB, C, V = m.groups()
            if not folder and segmentType not in ('parallelVerse','interlinearVerse','simpleVerse'):
                return match[0]
            view = folder or {'parallelVerse':'par','interlinearVerse':'ilr','simpleVerse':'lst'}[segmentType]
            BBB = BBB or otherBBB or reference[0]
            target, ref = 'OET', (BBB,C,V)
        elif not versionBar and (m := _LOCAL_PAGE.fullmatch(href)):
            BBB,C,section,anchor = m.groups()
            target, ref = pageVersion, _pageReference(BBB,C,section,anchor,sourceVersion,state)
            view = 'byDoc' if segmentType == 'book' and not C and not section else 'byC'
            canonical = segmentType in ('topicalPassage','dictVerse') or (
                bool(C) and segmentType == 'section' and not href.startswith('../byC/'))
        elif not versionBar and pageVersion != sourceVersion and (m := re.fullmatch(r'#C(\d+)(?:V(\d+[a-z]*))?', href)):
            if f'id="{href[1:]}"' in html:
                return match[0] # Local footnote return; the LV renderer namespaces it.
            target, ref = pageVersion, (reference[0], m[1], m[2] or '1')
        if ref is None or target is None:
            return match[0]
        refs = mappedReferences(ref, sourceVersion, target, state)
        if not refs:
            return label
        # Preserve links within a native edition, and stable same-system page
        # anchors. Only links crossing numbering systems need new destinations.
        if (not canonical and _versionProfile(sourceVersion, state) == _versionProfile(target, state)
                and not getattr(state, 'BibleSourceBookLayouts', {}).get(sourceVersion)
                and not getattr(state, 'BibleSourceBookLayouts', {}).get(target)):
            return f'<a{before}data-vref="mapped" href="{href}"{after}>{label}</a>'
        return ' / '.join(dict.fromkeys(
            f'<a{before}data-vref="mapped" href="{referenceHref(level, r, target, view)}"{after}>{label}</a>' for r in refs))
    return _ANCHOR.sub(replace, html)


def wordReferenceMetadata(reference, state):
    """Export both coordinate systems without changing a native word reference."""
    BBB, cvw = reference.split('_', 1)
    C, vw = cvw.split(':', 1)
    V = vw.split('w', 1)[0]
    result = _mapReference(state.BibleVersifications['OET-LV'], state.navigationVersification,
                           (BBB,C,V,None))
    return {'versification': state.BibleVersifications['OET-LV'],
            'navigation_versification': state.navigationVersification,
            'navigation_mapping_status': result.status.value,
            'navigation_references': [f'{b}_{c}:{v}{s or ""}' for b,c,v,s in result.references]}
