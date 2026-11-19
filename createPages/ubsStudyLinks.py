#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""
Link verse pages to the UBS handbook articles that cite them,
    and to their parallel passages (and OT quotations in the NT) from the UBS parallel passages database.

The UBS data uses original (Hebrew/Greek) numbering, so the indexes are mapped to state.navigationVersification.
prepareUBSStudyAssociations() should be called in the parent process before the page-creation processes are forked.

CHANGELOG:
    2026-11-19 First version
"""
from collections import defaultdict
import logging
from urllib.parse import quote
from xml.sax.saxutils import escape

from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus
import bos_books_codes_py

from navigation import referenceHref
from openbibledata_rust import getOETTidyBBB
from ubsHandbooks import HANDBOOKS
from ubsHOTTP import parseUBSWordReference
from ubsResources import isQuotationGroup
from versification import _mapReference


MAX_HANDBOOK_LINKS = 12 # Per verse


def _navigationRefs(originalRefs, state) -> list[tuple[str,str,str]]:
    """
    Map original-numbered (BBB,C,V) references to the navigation versification.
    """
    navigationRefs = []
    for BBB, C, V in originalRefs:
        result = _mapReference('org', state.navigationVersification, (BBB,C,V,None))
        if result.status != MappingStatus.EXACT: continue
        for reference in result.references:
            if tuple(reference[:3]) not in navigationRefs: navigationRefs.append(tuple(reference[:3]))
    return navigationRefs
# end of _navigationRefs


def _handbookCodeVerses(code:str) -> list[tuple[str,str,str]]:
    """
    Convert a UBS scripture code (or range of codes like '00301101301000-00301101901000') to original-numbered verses.
    """
    start, _dash, end = code.partition('-')
    startRef, endRef = parseUBSWordReference(start), parseUBSWordReference(end) if end else None
    if startRef is None or startRef[2] == '0': return [] # Unknown book or chapter-level reference
    if endRef and endRef[:2] == startRef[:2] and int(endRef[2]) >= int(startRef[2]):
        return [(startRef[0], startRef[1], str(V)) for V in range(int(startRef[2]), int(endRef[2])+1)]
    return [startRef[:3]]
# end of _handbookCodeVerses


def prepareUBSStudyAssociations(state) -> dict:
    """
    Build (once) the verse indexes for the UBS handbooks and parallel passages.
    """
    if hasattr(state, 'ubsStudyAssociations'): return state.ubsStudyAssociations
    handbookPassages = defaultdict(set) # Navigation (BBB,C,V) -> {(handbook, key)}
    for handbook, entries in getattr(state, 'UBS_HANDBOOKS', {}).items():
        for key, entry in entries.items():
            originalVerses = []
            for code in entry.referenceCodes():
                for verse in _handbookCodeVerses(code):
                    if verse not in originalVerses: originalVerses.append(verse)
            for reference in _navigationRefs(originalVerses, state):
                handbookPassages[reference].add( (handbook, key) )
    parallelPassages = defaultdict(list) # Navigation (BBB,C,V) -> [group number]
    for groupNumber, group in enumerate(getattr(state, 'UBS_PARALLEL_GROUPS', ())):
        for parallelVerse in group:
            for reference in _navigationRefs(parallelVerse.verses, state):
                if groupNumber not in parallelPassages[reference]: parallelPassages[reference].append(groupNumber)
    state.ubsStudyAssociations = dict(handbookPassages=dict(handbookPassages), parallelPassages=dict(parallelPassages))
    logging.info(f"prepareUBSStudyAssociations: {len(handbookPassages):,} verses cited in handbooks, {len(parallelPassages):,} verses with parallels")
    return state.ubsStudyAssociations
# end of prepareUBSStudyAssociations


def _verseLink(level:int, reference:tuple[str,str,str], label:str, state) -> str:
    if state.TEST_MODE_FLAG and reference[0] not in state.TEST_BOOK_LIST: return escape(label) # No page to link to
    return f'''<a title="View parallel verses" data-vref="mapped" href="{referenceHref(level, (*reference, None), view='par')}">{escape(label)}</a>'''


def _parallelVerseLabelAndRef(parallelVerse, state) -> tuple[str,tuple[str,str,str]|None]:
    """
    Return a label like 'Mrk 10:7–8' (in navigation numbering) and the first navigation reference.
    """
    references = _navigationRefs(parallelVerse.verses, state)
    if not references: return parallelVerse.reference, None
    first, last = references[0], references[-1]
    tidyBBB = getOETTidyBBB(first[0])
    if first == last: return f'{tidyBBB} {first[1]}:{first[2]}', first
    if first[1] == last[1]: return f'{tidyBBB} {first[1]}:{first[2]}–{last[2]}', first
    return f'{tidyBBB} {first[1]}:{first[2]}–{last[1]}:{last[2]}', first
# end of _parallelVerseLabelAndRef


def _parallelAndQuotationLinks(level:int, navigationRefs, state) -> tuple[list[str],list[str]]:
    """
    Return links to the UBS parallel passages, and to the OT quotations in the NT (or vice versa), of the given verses.
    """
    graph = prepareUBSStudyAssociations(state)
    parallelLinks, quotationLinks = [], []
    if not navigationRefs: return parallelLinks, quotationLinks
    currentIsOT = bos_books_codes_py.is_old_testament_nr(navigationRefs[0][0])
    for groupNumber in dict.fromkeys(groupNumber for reference in navigationRefs for groupNumber in graph['parallelPassages'].get(reference, ())):
        group = state.UBS_PARALLEL_GROUPS[groupNumber]
        for parallelVerse in group:
            label, firstRef = _parallelVerseLabelAndRef(parallelVerse, state)
            if firstRef is None or firstRef in navigationRefs: continue # Don't link to these verses themselves
            link = _verseLink(level, firstRef, label, state)
            # In an OT-quoted-in-NT group, verses in the same testament as ours are parallels, and the others are the quotation(s)
            if isQuotationGroup(group) and bos_books_codes_py.is_old_testament_nr(firstRef[0]) != currentIsOT:
                if link not in quotationLinks: quotationLinks.append(link)
            elif link not in parallelLinks and link not in quotationLinks: parallelLinks.append(link)
    return parallelLinks, quotationLinks
# end of _parallelAndQuotationLinks


def _quotationLabel(BBB:str) -> str:
    return 'Quoted in the New Testament' if bos_books_codes_py.is_old_testament_nr(BBB) else 'Quotes from the Old Testament'


def ubsSectionParallelsHtml(level:int, BBB:str, startC:str, startV:str, endC:str, endV:str, state) -> str:
    """
    Return a block (or '') listing the UBS parallel passages and OT quotations for a section of a book.

    The section is in OET-RV numbering, which we treat as the navigation numbering here.
    """
    if not (startC.isdigit() and startV.isdigit() and endC.isdigit() and endV.isdigit()): return ''
    graph = prepareUBSStudyAssociations(state)
    start, end = (int(startC), int(startV)), (int(endC), int(endV))
    sectionRefs = sorted((reference for reference in graph['parallelPassages']
                            if reference[0] == BBB and reference[1].isdigit() and reference[2].isdigit()
                                and start <= (int(reference[1]), int(reference[2])) <= end),
                         key=lambda reference: (int(reference[1]), int(reference[2])))
    if not sectionRefs: return ''
    parallelLinks, quotationLinks = _parallelAndQuotationLinks(level, sectionRefs, state)
    html = ''
    if parallelLinks: html += f'<p>Parallel passages: {" · ".join(parallelLinks)}</p>'
    if quotationLinks: html += f'<p>{_quotationLabel(BBB)}: {" · ".join(quotationLinks)}</p>'
    return f'<div><h2>UBS parallel passages database</h2>\n{html}\n</div><!--end of UBS parallels-->' if html else ''
# end of ubsSectionParallelsHtml


def ubsPassageResources(level:int, navigationRefs, state) -> str:
    """
    Return HTML paragraphs (or '') linking the given navigation-numbered verses
        to UBS handbook articles and parallel passages.
    """
    graph = prepareUBSStudyAssociations(state)
    html = ''
    navigationRefs = [tuple(reference[:3]) for reference in navigationRefs]
    handbookArticles = sorted(set().union(*(graph['handbookPassages'].get(reference, ()) for reference in navigationRefs)))
    if handbookArticles:
        links = []
        for handbook, key in handbookArticles[:MAX_HANDBOOK_LINKS]:
            entry = state.UBS_HANDBOOKS[handbook][key]
            filename = 'index.htm' if key == '0' else f'{key}.htm'
            links.append( f'''<a title="Go to UBS {escape(HANDBOOKS[handbook][1])} article" href="{'../'*level}UBS/{handbook}/{quote(filename)}#Top">{escape(entry.title)}</a> <small>({handbook.lower()})</small>''' )
        more = f' (and {len(handbookArticles)-MAX_HANDBOOK_LINKS} more)' if len(handbookArticles) > MAX_HANDBOOK_LINKS else ''
        html += f'<p class="note">UBS handbooks: {" · ".join(links)}{more}</p>'
    parallelLinks, quotationLinks = _parallelAndQuotationLinks(level, navigationRefs, state)
    if parallelLinks:
        html += f'<p class="note">UBS parallel passages: {" · ".join(parallelLinks)}</p>'
    if quotationLinks and navigationRefs:
        html += f'<p class="note">{_quotationLabel(navigationRefs[0][0])} (UBS): {" · ".join(quotationLinks)}</p>'
    return html
# end of ubsPassageResources
