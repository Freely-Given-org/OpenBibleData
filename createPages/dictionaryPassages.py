#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Complete scripture selections in dictionary articles.

CHANGELOG:
    2026-10-30 Preserve Tyndale ranges/lists and add OET comparisons after paragraphs.
    2026-10-31 Lead passage controls with OET and group the RV/LV-only links.
    2026-11-02 Use one preferred OET destination without repeating the source citation.
"""
import logging
import re
from pathlib import Path
from xml.sax.saxutils import escape

import bos_books_codes_py
from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus, get_default_mapping_engine
from referencePassages import parseReferenceSelection, renderReferencePassageGroup, _selectionLinks, PASSAGE_LINK_LABELS, formatPassageLinks
from versification import _storedReferences, _referenceLabel


def parseTyndaleCitation(citation):
    citation = citation.replace('–','-').replace('Deut.31:30-','Deut.31.30-')
    match = re.fullmatch(r'([1-4]?[A-Za-z]+)\.(.+)',citation)
    if not match: raise ValueError(f'Unsupported citation {citation!r}')
    book,selection = match.groups()
    if book.endswith('Thes'): book += 's'
    BBB = 'TOB' if book=='Tb' else bos_books_codes_py.english_name_to_bos_book_code(book)
    if not BBB: raise ValueError(f'Unknown book {book!r}')
    return parseReferenceSelection(BBB,selection.replace('.',':'),'eng')


def dictionarySelectionLinks(level,references,sourceSystem,state,*,compact=False):
    links = {}
    for version,label in PASSAGE_LINK_LABELS:
        target = state.BibleVersifications['OET-RV' if version=='OET' else version]
        mapping = get_default_mapping_engine().convert_passage(sourceSystem,target,references)
        if mapping.status==MappingStatus.EXACT:
            native = _storedReferences(version,mapping.references,state)
            if linked:=_selectionLinks(level,native,version,state,label):
                if compact and linked.count('<a ')==1 and _referenceLabel(native)==_referenceLabel(references):
                    linked=re.sub(r'>([^<]+)</a>',f'>{label}</a>',linked)
                links[version] = linked
    return formatPassageLinks(links)


def livenTyndaleCitations(html,level,source,state,*,previews=False):
    """Keep controls inline and put details outside the containing paragraph.

    A range or disjoint list is mapped in full. Repeated selections share one
    preview per article, and long selections retain their complete context links.
    """
    pattern = re.compile(r'<a\b[^>]*href="\?bref=([^"]*)"[^>]*>(.*?)</a>',re.DOTALL)
    seen, pending = set(), []
    def replace(match):
        citation,label = match.groups()
        if not citation and source.endswith(':AlTaschith'): citation = 'Ps.58.1-2'
        try: references = parseTyndaleCitation(citation)
        except (ValueError,KeyError,TypeError) as error:
            logging.warning('Tyndale %s citation %r: %s',source,citation,error)
            return label
        links = dictionarySelectionLinks(level,references,'eng',state,compact=True)
        if previews and references not in seen and len(references)<=12 and links:
            seen.add(references)
            pending.append((_referenceLabel(references),references))
        # A single destination can make the existing citation clickable without
        # adding another copy of its reference. Disjoint destinations stay explicit.
        if links.count('<a ')==1:
            return re.sub(r'>[^<]*</a>$',lambda _m:f'>{label}</a>',links)
        return f'{label} <small>{links}</small>' if links else label
    def flushPreviews():
        rendered = renderReferencePassageGroup(level,pending,'eng',state,
            instancePrefix=f'tyndale{len(seen)}_',maxPreviews=len(pending))
        pending.clear()
        return rendered
    def paragraph(match):
        rendered = pattern.sub(replace,match[0])
        return rendered+flushPreviews()
    html = re.sub(r'<p\b[^>]*>.*?</p>',paragraph,html,flags=re.DOTALL)
    html = pattern.sub(replace,html)
    return html+flushPreviews()


def tyndaleEntityLinks(article,level,state):
    from referenceEntities import ENTITY_DICTIONARY_ARTICLES, loadReferenceEntities, entityLink
    keys = [key for key,name in ENTITY_DICTIONARY_ARTICLES.items() if name==article]
    if not keys: return ''
    entities = loadReferenceEntities(Path(__file__).resolve().parents[2]/'Bible_speaker_identification/outsideSources/TheographicBibleData/derivedFiles',state)
    links = [entityLink(key,level,entities) for key in keys if key in entities['records']]
    return '<p class="note">People and places: '+' · '.join(links)+'</p>' if links else ''
