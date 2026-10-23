#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Map English parallel-page addresses to the addresses actually stored in a Bible.

Keep this module independent of the site renderer so it can be tested with small
USFM fixtures. BOS owns the mapping data and all decisions about correspondence.

CHANGELOG:
    2026-10-17 Keep combined-passage explanations in version-label tooltips,
               and target version labels explicitly when adding native references.
"""
from functools import lru_cache
import re
from xml.sax.saxutils import escape

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


def _referenceLabel(references):
    """Compact adjacent addresses without hiding gaps or chapter boundaries."""
    spans = []
    for BBB,C,V,S in references:
        if spans and not S and not spans[-1][4] and (BBB,C) == spans[-1][:2] and int(V) == int(spans[-1][3])+1:
            spans[-1] = (*spans[-1][:3], V, S)
        else:
            spans.append((BBB,C,V,V,S))
    return '; '.join(f'{b} {c}:{first}{s or ""}' + (f'–{last}' if last != first else '')
                     for b,c,first,last,s in spans)


def combinedPassageLabel(passage):
    """Explain extra coverage while keeping native text and word ids untouched."""
    mapping = passage.mapping
    if not mapping.is_expanded:
        return ''
    sourceName = 'English' if mapping.source_system == 'eng' else mapping.source_system
    return (f'<small class="versificationRef">Combined passage: {sourceName} '
            f'{_referenceLabel(mapping.source_references)} '
            f'(native {_referenceLabel(passage.native_references or mapping.references)}; '
            'verse text cannot be split).</small> ')


def parallelVersePassage(version, bible, reference, state, chapterCache):
    """Retrieve complete BOS passages and return their display coverage label."""
    BBB,C,V = reference
    source = state.navigationVersification
    editorial = C == '-1' or (V == '0' and any(d.code == 'UNDECLARED_TITLE'
        for d in _mapReference(source, source, (BBB,C,V,None)).diagnostics))
    layouts = getattr(state, 'BibleSourceBookLayouts', {}).get(version, {})
    if editorial or isinstance(bible, dict):
        references = parallelVerseReferences(version, bible, reference, state)
        return getVersePortions(bible, references, chapterCache), ''
    mapping = None
    if layouts:
        mapping = bible.convertReferencesFromVersification(source, (reference,), expandGroups=True)
        if mapping.status != MappingStatus.EXACT:
            raise VersificationMappingError(mapping)
    if mapping is not None and any(ref[0] in layouts for ref in mapping.references):
        # This importer splits a profile's book into different physical books.
        # Mapping still belongs to BOS; only the storage addresses change here.
        from BibleOrgSys.Internals.InternalBiblePassages import MappedBiblePassage, passageReferencesFromEntries
        references = _storedReferences(version, mapping.references, state)
        portions = getVersePortions(bible, references, chapterCache)
        native = tuple(dict.fromkeys(ref for part in portions for ref in
            passageReferencesFromEntries(part.reference, part.entries, bible)))
        passage = MappedBiblePassage(mapping, portions, native)
        if any(ref not in references and not (ref[3] and (*ref[:3],None) in references) for ref in native):
            # The physical edition contains a larger stored bridge. Its native
            # extent is known, but do not claim an English extent from aliases.
            return portions, (f'<small class="versificationRef">Combined native passage: '
                f'{_referenceLabel(native)} (requested English {_referenceLabel(mapping.source_references)}; '
                'verse text cannot be split).</small>')
    else:
        passage = bible.getMappedPassage(source, (reference,), chapterCache=chapterCache, expandGroups=True)
    return passage.portions, combinedPassageLabel(passage)


def versePortionHtml(html, version, nativeRef, pageRef, portionNumber, combinedLabel=''):
    """Annotate version labels and isolate ids/callers in additional portions."""
    # Native footnote return addresses need a real anchor on this English page.
    BBB, C, V = nativeRef
    html = html.replace(f'href="#C{C}V{V}"', f'href="#{version}"')
    if portionNumber:
        ids = re.findall(r'\bid="([^"]+)"', html)
        for original in dict.fromkeys(ids):
            replacement = f'{original}_part{portionNumber+1}'
            html = html.replace(f'id="{original}"', f'id="{replacement}"')
            html = html.replace(f'href="#{original}"', f'href="#{replacement}"')
    if combinedLabel or (tuple(nativeRef) != tuple(pageRef) and nativeRef[1] != '-1'):
        # OET's version label includes a nested <small>(<a>OET-RV</a>)</small>.
        # A bare </a></span> search can match a scripture word link instead.
        heading = re.search(r'<span\b[^>]*\bclass="wrkName[^"]*"[^>]*>.*?</span>', html, re.DOTALL)
        if heading:
            label = heading.group()
            if combinedLabel:
                explanation = escape(re.sub(r'<[^>]+>', '', combinedLabel).strip(), {'"': '&quot;'})
                # Links have their own titles, which override a parent tooltip.
                label, count = re.subn(r' title="([^"]*)"',
                    lambda match: f' title="{match[1]} {explanation}"', label)
                if not count:
                    label = label.replace('<span ', f'<span title="{explanation}" ', 1)
            else:
                BBB, C, V = nativeRef
                label += f' <small class="versificationRef">({BBB} {C}:{V})</small>'
            html = html[:heading.start()] + label + html[heading.end():]
    return html
