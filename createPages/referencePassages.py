#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Small, source-numbered OET passage controls for reference material.

CHANGELOG:
    2026-10-30 Share mapped links and bounded, independently anchored previews.
    2026-10-30 Route Psalm headings and jumps outside an excerpt to chapter context.
    2026-10-31 Retain verse suffixes when resolving excerpt context anchors.
    2026-10-31 Put combined OET links first, with RV/LV-only alternatives in parentheses.
    2026-11-02 Use RV-only/LV-only labels and keep the alternatives beside the OET link.
    2026-11-02 Put indented previews before one section-first OET jump per selection.
"""
import logging
import re
from functools import lru_cache
from xml.sax.saxutils import escape

from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, VersificationMappingError, get_default_mapping_engine,
)
from navigation import referenceHref
from oetPassages import _namespaceIds
from versification import _referenceLabel, _storedReferences, combinedPassageLabel, navigationVersification

PASSAGE_LINK_LABELS = (('OET','OET'),('OET-RV','OET-RV'),('OET-LV','OET-LV'))


def formatPassageLinks(links):
    """One reading destination, using an individual edition only as a fallback."""
    return next((links[version] for version,_ in PASSAGE_LINK_LABELS
                 if '<a ' in links.get(version,'')), '')


def parseReferenceSelection(BBB, selection, sourceSystem):
    """Expand same-book chapters, ranges and comma/semicolon lists without losing gaps.

    The source numbering system is required. Individual suffixes are retained;
    suffix ranges need an explicit inventory and are deliberately not guessed.
    """
    engine = get_default_mapping_engine()
    references = []
    chapter = None
    for item in re.split(r'[,;]',selection.replace('–','-').replace('—','-')):
        item = item.strip()
        if not item: raise ValueError(f'Empty citation component in {BBB} {selection}')
        endpoints = item.split('-')
        if len(endpoints) > 2: raise ValueError(f'Unsupported citation {BBB} {selection}')
        if ':' not in item and chapter is None:
            first,last = int(endpoints[0]),int(endpoints[-1])
            counts = navigationVersification(sourceSystem)
            start,end = (BBB,str(first),'1',None),(BBB,str(last),str(counts.getNumVerses(BBB,str(last))),None)
        else:
            def point(value):
                nonlocal chapter
                match = re.fullmatch(r'(?:(\d+):)?(\d+)([a-z]*)',value.strip())
                if not match or (not match[1] and chapter is None):
                    raise ValueError(f'Unsupported citation {BBB} {selection}')
                if match[1]: chapter = match[1]
                return BBB,chapter,match[2],match[3] or None
            start = point(endpoints[0])
            end = point(endpoints[-1]) if len(endpoints)>1 else start
        result = (engine.convert(sourceSystem,sourceSystem,(start,)) if start == end
                  else engine.convert_range(sourceSystem,sourceSystem,start,end))
        if result.status != MappingStatus.EXACT: raise VersificationMappingError(result)
        references.extend(result.references)
    return tuple(dict.fromkeys(references))


def _available(reference, version, state):
    """Do not create destinations for books omitted from a reduced build."""
    books = state.booksToLoad.get(version,state.booksToLoad.get('OET',()))
    if 'ALL' not in books and reference[0] not in books: return False
    bible = getattr(state,'preloadedBibles',{}).get('OET-RV' if version == 'OET' else version)
    if bible is None: return False
    return reference[0] in bible or reference[0] in getattr(bible,'availableBBBs',())


@lru_cache(maxsize=8192)
def _nativeContextReference(bible, reference):
    """Find the starting label of a stored bridge, not a missing interior anchor."""
    if len(reference)==3 and (verse:=re.fullmatch(r'(\d+)([a-z]+)',str(reference[2]))):
        reference = (*reference[:2],verse[1],verse[2])
    try: native = bible.getPassageData((reference,))[0].reference
    except KeyError: return None
    return (*native[:2],re.match(r'\d+[a-z]*',native[2])[0])


def passageContextHref(level, reference, version, state, *, preferSections=True):
    """Resolve a native verse to an existing section, falling back to its chapter."""
    if not _available(reference,version,state): return None
    # Combined OET pages are rendered in RV chunks, with RV anchors.
    key = 'OET-RV' if version=='OET' else version
    bible = state.preloadedBibles[key]
    heading = str(reference[2])=='0'
    native = ((*reference[:2],'1') if heading else
              _nativeContextReference(bible,tuple(reference)) if hasattr(bible,'getPassageData') else reference)
    if native is None: return None
    book,chapter,verse = map(str,native[:3])
    if len(native)>3: verse += native[3] or ''
    anchor = 'Top' if heading else f'C{chapter}V{verse}'
    sections = getattr(state,'sectionsListsForSections',{}).get(key,{}).get(book,())
    if preferSections and sections:
        from openbibledata_rust import findSectionNumber
        number = findSectionNumber(key,book,chapter,verse,state)
        if number is not None:
            section = sections[number]
            if (str(section[1]),str(section[2]))==(chapter,verse): anchor = 'Top'
            return f'{"../"*level}{version}/bySec/{section[-1]}#{anchor}'
    return referenceHref(level,native,version).split('#')[0]+'#'+anchor


def referenceCitationLink(level, reference, sourceSystem, version, label, state):
    targetVersion = 'OET-RV' if version=='OET' else version
    mapping = get_default_mapping_engine().convert_passage(sourceSystem,state.BibleVersifications[targetVersion],(reference,))
    if mapping.status != MappingStatus.EXACT: return escape(label)
    destinations = dict.fromkeys(href for ref in _storedReferences(targetVersion,mapping.references,state)
                                if (href:=passageContextHref(level,ref,version,state)))
    return ' / '.join(f'<a href="{href}" data-vref="mapped">{escape(label)}</a>' for href in destinations) or escape(label)


def _externaliseExcerptJumps(html,level,BBB,version,state):
    """Local excerpt IDs are already namespaced; remaining verse jumps leave it."""
    def replace(match):
        before,C,V,after,body=match.groups()
        href=passageContextHref(level,(BBB,C,V),version,state)
        if 'data-vref=' not in before+after: after += ' data-vref="mapped"'
        return f'<a{before}href="{href}"{after}>{body}</a>' if href else body
    return re.sub(r'<a\b([^>]*?)href="#C(\d+)V(\d+[a-z]*)"([^>]*)>(.*?)</a>',replace,html,flags=re.DOTALL)


def _selectionLinks(level, references, version, state, label, *, destinationLabel=False):
    """One context link per consecutive span; keep disjoint selections visible."""
    spans = []
    for ref in references:
        if spans and not ref[3] and not spans[-1][-1][3] and ref[:2] == spans[-1][-1][:2] \
                and int(ref[2]) == int(spans[-1][-1][2])+1:
            spans[-1].append(ref)
        else: spans.append([ref])
    return ' · '.join(f'<a href="{href}" data-vref="mapped">'
                      f'{escape(label)} {escape(_referenceLabel(span))}'
                      + ((' section.' if '/bySec/' in href else ' chapter.') if destinationLabel else '')+'</a>'
                      for span in spans if all(_available(ref,version,state) for ref in span)
                      and (href:=passageContextHref(level,span[0],version,state)))


def referenceSelectionLinks(level, references, sourceSystem, state, *, destinationLabel=False):
    """Map the full selection and label the preferred destination in its own numbering."""
    for version,label in PASSAGE_LINK_LABELS:
        target = state.BibleVersifications['OET-RV' if version=='OET' else version]
        mapping = get_default_mapping_engine().convert_passage(sourceSystem,target,references)
        if mapping.status == MappingStatus.EXACT:
            native = _storedReferences(version,mapping.references,state)
            if links := _selectionLinks(level,native,version,state,label,destinationLabel=destinationLabel):
                return links
    return ''


def _referencePassageParts(level, references, sourceSystem, state, *, instanceId,
                           label=None, preview=True, maxPreviewVerses=12, wordPaths=()):
    """Render complete mapped selections; expansions never manufacture RV word alignment.

    instanceId must be unique on the containing page. Long selections keep all
    context links but omit inline text. No JavaScript is needed for disclosure.
    """
    from openbibledata_rust import convertVerseEntryListToHtml
    from html import do_OET_LV_HTMLcustomisations, do_OET_RV_HTMLcustomisations

    references = tuple(references)
    if not references: return '', ''
    if not re.fullmatch(r'[A-Za-z][\w-]*',instanceId): raise ValueError(instanceId)
    label = label or _referenceLabel(references)
    engine = get_default_mapping_engine()
    controls, excerpts = {}, []
    for version,linkLabel in PASSAGE_LINK_LABELS:
        targetSystem = state.BibleVersifications['OET-RV' if version=='OET' else version]
        mapping = engine.convert_passage(sourceSystem,targetSystem,references)
        if mapping.status != MappingStatus.EXACT:
            logging.warning('Reference %s (%s), %s → %s: %s',instanceId,label,sourceSystem,version,mapping.status.value)
            controls[version] = f'{linkLabel} unavailable'
            continue
        native = _storedReferences(version,mapping.references,state)
        links = _selectionLinks(level,native,version,state,linkLabel,destinationLabel=True)
        if not links:
            controls[version] = f'{linkLabel} unavailable in this build'
            continue
        controls[version] = links
        if version == 'OET' or not preview or len(mapping.references)>maxPreviewVerses: continue
        bible = state.preloadedBibles[version]
        try:
            if native != mapping.references:
                # Explicit storage aliases (e.g. split additions) are not verse mappings.
                portions, combined = bible.getPassageData(native), ''
            else:
                passage = bible.getMappedPassage(sourceSystem,references,expandGroups=True)
                portions, combined = passage.portions,combinedPassageLabel(passage)
        except (KeyError,VersificationMappingError) as error:
            logging.warning('Reference %s (%s): missing %s preview: %s',instanceId,label,version,error)
            excerpts.append(f'<p class="note">{version} text unavailable for this selection.</p>')
            continue
        if combined: excerpts.append(f'<p class="note">{combined}</p>')
        for index,(nativeRef,entries,context) in enumerate(portions):
            text = convertVerseEntryListToHtml(level,version,nativeRef,'dictVerse',context,entries,
                basicOnly=True,state=state,livenWordLinks=True)
            customise = do_OET_LV_HTMLcustomisations if version == 'OET-LV' else do_OET_RV_HTMLcustomisations
            text = customise(f'Reference={instanceId}:{nativeRef}',text)
            for wordPath in dict.fromkeys(wordPaths):
                pattern = r'<a\b[^>]*\bhref="[^"<>]*/'+re.escape(wordPath)+r'#Top"[^>]*>.*?</a>'
                text = re.sub(pattern,lambda m:f'<b>{m[0]}</b>',text,flags=re.DOTALL)
            text = _namespaceIds(text,f'{instanceId}_{version.removeprefix("OET-")}{index}_')
            text = _externaliseExcerptJumps(text,level,nativeRef[0],version,state)
            # A stored bridge is labelled 20–21, but chapter pages anchor its
            # individual verse numbers, not the literal "20-21" label.
            contextRef = (*nativeRef[:2],re.match(r'\d+[a-z]*',nativeRef[2])[0])
            contextHref = passageContextHref(level,contextRef,version,state)
            headingLabel = f'{version} {escape(" ".join((nativeRef[0], ":".join(nativeRef[1:]))))}'
            heading = f'<a href="{contextHref}" data-vref="mapped">{headingLabel}</a>' if contextHref else headingLabel
            excerpts.append(f'<div><p class="note"><b>{heading}</b></p>{text}</div>')
    previewHtml = (f'<details><summary>Show passage in OET: {escape(label)}</summary>{"".join(excerpts)}</details>'
                   if excerpts else '')
    links = formatPassageLinks(controls)
    jumpHtml = (f'<p class="referenceJump">Jump to {links}</p>' if links else
                f'<p class="referenceJump">{escape(label)} — OET passage unavailable in this build.</p>')
    return previewHtml, jumpHtml


def renderReferencePassage(level, references, sourceSystem, state, **options):
    """An indented preview followed by a single preferred reading destination."""
    parts = _referencePassageParts(level,references,sourceSystem,state,**options)
    return '<div class="referencePassage">'+''.join(parts)+'</div>' if any(parts) else ''


def renderReferencePassageGroup(level, selections, sourceSystem, state, *, instancePrefix, maxPreviews=3):
    """Keep all disclosures together above the jump links belonging to one entry."""
    previews, jumps = [], []
    for number,(label,references) in enumerate(selections):
        if references:
            preview,jump = _referencePassageParts(level,references,sourceSystem,state,
                instanceId=f'{instancePrefix}{number}',label=label,preview=number<maxPreviews)
            previews.append(preview)
            jumps.append(jump)
        else:
            jumps.append(f'<p class="referenceJump">{escape(label)} (reference unavailable)</p>')
    return '<div class="referencePassage">'+''.join(previews+jumps)+'</div>' if jumps else ''
