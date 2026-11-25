#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""
Load the UBS Preliminary and Interim Report of the Hebrew Old Testament Text Project (HOTTP)
    (from our OET-adapted copy) and index its text-critical notes by verse.

Each <HOTTP_Entry Id="00010"> has References (UBS word codes like '00100201900010'),
    an English Remark and Suggestion, and Alternatives, each with a Hebrew Source,
    an A–D Rating (only on the preferred reading), the Versions that follow it,
    numbered Factors (explained in HOTTP-FACTORS-EN.HTML), and an English Literal rendering.

CHANGELOG:
    2026-11-19 First version
    2026-11-26 Show the source's USFM-style \\heb…\\heb* and \\grk…\\grk* markers as Hebrew and Greek spans (not as raw text),
                including in the version renderings and factors; look up factor titles like '12 (for/pour …)' by their number;
                show the backslash between alternative Hebrew readings, e.g., '[קֵן \\ קֵין]', as a slash.
"""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import logging
import re
from xml.etree import ElementTree
from xml.sax.saxutils import escape, unescape # (Our html.py shadows the standard html module)

from versification import _mapReference

import bos_books_codes_py


HOTTP_FILENAME = 'HOTTP.XML'

FACTORS_FILENAME = 'HOTTP-FACTORS-EN.HTML'
RATING_DESCRIPTIONS = { # From HOTTP-RATINGS-EN.HTML (the 'Second Phase' is the earliest attested form of the text)
    'A': 'This form of the text has a very high probability of representing the earliest attested text.',
    'B': 'This form of the text probably represents the earliest attested text, but there is some doubt.',
    'C': 'This form of the text possibly represents the earliest attested text, but there is considerable doubt.',
    'D': 'There is a possibility that this form of the text represents the earliest attested text, but this is highly uncertain.',
    }
VERSION_NAMES = { # The HOTTP 'base translations' (from HOTTP-RATINGS-EN.HTML)
    'RSV': 'Revised Standard Version (English)',
    'NEB': 'New English Bible (English)',
    'BJ': 'Bible de Jérusalem (French)',
    'LUT': 'Luther Bible (German)',
    'TOB': 'Traduction œcuménique de la Bible (French)',
    }


def loadHOTTPFactors(folderpath) -> dict[str,str]:
    """
    Load the numbered factor titles from HOTTP-FACTORS-EN.HTML,
        e.g., {'1': 'Narrow basis for a variant form of the text', …, '15': 'Inexplicable texts'}.
    """
    text = Path(folderpath, FACTORS_FILENAME).read_text(encoding='utf-8')
    text = re.sub(r'(?s)<style.*?</style>', '', text)
    text = re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', text), {'&quot;':'"', '&nbsp;':' ', '&#39;':"'"}))
    factors = {match.group(2):match.group(1).strip()
                for match in re.finditer(r'\d+\. ([^.=]{3,120}?) = Factor (\d+)', text)}
    if len(factors) != 15:
        logging.warning(f"loadHOTTPFactors: expected 15 factors but found {len(factors)} in {folderpath}")
    return factors
# end of loadHOTTPFactors


@dataclass
class HOTTPVersion:
    abbreviation:str # e.g., 'RSV', 'NEB', 'LUT', 'BJ', 'TOB'
    content:str # The rendering in that version (often not English)


@dataclass
class HOTTPAlternative:
    source:str # The Hebrew text (or '[-]' for omission)
    rating:str # 'A'–'D' for the committee's preferred reading, else ''
    versions:list[HOTTPVersion]
    factors:list[str] # Factor numbers, e.g., ['4','6']
    literal:str # English literal rendering


@dataclass
class HOTTPEntry:
    entryID:str # e.g., '00010'
    references:list[str] # UBS word reference codes
    remark:str # English (may contain escaped <span class="hebrew"> markup)
    suggestion:str
    alternatives:list[HOTTPAlternative]

    @property
    def number(self) -> int:
        """ The number used in MARBLE TextualLinks, e.g., 'HOTTP1474' """
        return int(self.entryID)
# end of HOTTPEntry class


def ubsBookCode(bookNumber:int) -> str|None:
    """
    Convert a UBS book number to a BOS book code.

    UBS numbers the canonical books 1–66 (like BOS reference numbers),
        then the deuterocanonical books with one less than their USFM numbers
        (because USFM skips 40), e.g., 069 = USFM 70 = ESG (Greek Esther), 077 = USFM 78 = 1 Maccabees.
    """
    if bookNumber <= 66:
        return bos_books_codes_py.get_bos_book_code_from_reference_number(bookNumber)
    return _USFM_NUMBER_BOOK_CODES.get(str(bookNumber+1))

_USFM_NUMBER_BOOK_CODES:dict[str,str] = {}
for _abbreviation, _number, _BBB in bos_books_codes_py.get_all_usfm_books_code_number_triples():
    _USFM_NUMBER_BOOK_CODES.setdefault(_number, _BBB) # First one, e.g., ESG (not ESA or ESC) for 70


def parseUBSWordReference(code:str) -> tuple[str,str,str,int]|None:
    """
    Convert a UBS reference code like '00100201900010' (book 001, chapter 002, verse 019, word position 00010)
        to (BBB, C, V, wordPosition). Returns None if the book number is unknown.

    The code can have a single letter prefix, e.g., 'H' (Hebrew), 'G' (Greek), or 'V' (as in some handbook references).
    """
    match = re.fullmatch(r'[A-Z]?(\d{3})(\d{3})(\d{3})(\d{5})', code.strip())
    if not match: return None
    BBB = ubsBookCode(int(match.group(1)))
    if not BBB: return None
    return BBB, str(int(match.group(2))), str(int(match.group(3))), int(match.group(4))
# end of parseUBSWordReference


def textOf(element:ElementTree.Element|None) -> str:
    return (''.join(element.itertext()).strip()) if element is not None else ''


def loadHOTTP(folderpath) -> tuple[dict[str,HOTTPEntry],dict[tuple[str,str,str],list[str]]]:
    """
    Load the HOTTP entries.

    Returns a dict of entries (keyed by entry ID, e.g., '00010')
        and an index from original-numbered (BBB, C, V) to the IDs of entries that start in that verse.
    """
    filepath = Path(folderpath, HOTTP_FILENAME)
    entries:dict[str,HOTTPEntry] = {}
    verseIndex:dict[tuple[str,str,str],list[str]] = defaultdict(list)
    for entryElement in ElementTree.parse(filepath).getroot().iterfind('HOTTP_Entry'):
        entryID = entryElement.get('Id','').strip()
        references = [textOf(reference) for reference in entryElement.iterfind('References/Reference') if textOf(reference)]
        alternatives = [HOTTPAlternative(textOf(alternative.find('Source')), textOf(alternative.find('Rating')),
                                        [HOTTPVersion(textOf(version.find('Text')), textOf(version.find('Content')))
                                            for version in alternative.iterfind('Versions/Version')],
                                        [textOf(factor) for factor in alternative.iterfind('Factors/Factor') if textOf(factor)],
                                        textOf(alternative.find('Literal')))
                        for alternative in entryElement.iterfind('Alternatives/Alternative')]
        entry = HOTTPEntry(entryID, references, textOf(entryElement.find('Remark')), textOf(entryElement.find('Suggestion')), alternatives)
        if not entryID or entryID in entries:
            logging.warning(f"loadHOTTP: missing or duplicate entry ID {entryID!r} in {filepath}"); continue
        entries[entryID] = entry
        verses = [] # The verse(s) this entry is about (usually one)
        for reference in references:
            parsed = parseUBSWordReference(reference)
            if parsed is None:
                logging.warning(f"loadHOTTP: can't parse reference {reference!r} in entry {entryID}"); continue
            if parsed[:3] not in verses: verses.append(parsed[:3])
        for verseRef in verses:
            verseIndex[verseRef].append(entryID)
    return entries, dict(verseIndex)
# end of loadHOTTP


HOTTP_LANGUAGE_MARKER_RE = re.compile(r'\\(heb|grk) (.*?)\\\1\*', re.DOTALL) # e.g., '\heb עוד\heb*'
HOTTP_LANGUAGE_CLASSES = {'heb':'hebrew', 'grk':'greek'}


def _hottpText(text:str) -> str:
    """
    Escape HOTTP text, but keep the source's <span class="hebrew">…</span> markup,
        and convert its USFM-style \\heb…\\heb* and \\grk…\\grk* markers to the same spans.
    """
    html = escape(text)
    html = re.sub(r'&lt;span class="hebrew"&gt;(.*?)&lt;/span&gt;', r'<span class="hebrew">\1</span>', html)
    return HOTTP_LANGUAGE_MARKER_RE.sub(lambda match: f'<span class="{HOTTP_LANGUAGE_CLASSES[match.group(1)]}">{match.group(2)}</span>', html)
# end of _hottpText


def _factorTitle(factor:str, factors:dict[str,str]) -> str:
    """
    Return the title for a factor like '14' or '12 (for/pour \\heb אל־תתעבר\\heb*)' (looked up by its number).
    """
    number = match.group(0) if (match:=re.match(r'\d+', factor)) else factor
    return factors.get(number, f'Factor {number}')
# end of _factorTitle


def formatHOTTPEntry(entry:HOTTPEntry, factors:dict[str,str]) -> str:
    """
    Format one HOTTP entry as HTML: the alternatives (with the rated reading first), then the suggestion and remark.
    """
    alternativesHtml = []
    for alternative in sorted(entry.alternatives, key=lambda alt: alt.rating[:1].upper() not in RATING_DESCRIPTIONS): # Rated reading first
        rating = alternative.rating[:1].upper()
        ratingHtml = f''' <span class="HOTTPrating" title="{escape(RATING_DESCRIPTIONS[rating], {'"':'&quot;'})}">{escape(alternative.rating)}</span>''' if rating in RATING_DESCRIPTIONS else ''
        literalHtml = f' ‘{_hottpText(alternative.literal)}’' if alternative.literal else ''
        versionsHtml = '; '.join(f'''<span class="HOTTPversion" title="{escape(VERSION_NAMES.get(version.abbreviation, version.abbreviation), {'"':'&quot;'})}">{escape(version.abbreviation)}</span> {_hottpText(version.content)}'''
                                    for version in alternative.versions)
        factorsHtml = ', '.join(f'''<span class="HOTTPfactor" title="{escape(_factorTitle(factor, factors), {'"':'&quot;'})}">{_hottpText(factor)}</span>'''
                                    for factor in alternative.factors)
        alternativesHtml.append( f'''<li><span class="hebrew">{escape(alternative.source).replace(' \\ ', ' / ')}</span>{literalHtml}{ratingHtml}'''
                                 f'''{f' <small>({versionsHtml})</small>' if versionsHtml else ''}{f' <small>Factors: {factorsHtml}</small>' if factorsHtml else ''}</li>''' )
    html = f'''<ul>{''.join(alternativesHtml)}</ul>''' # (Styled by div.HOTTPnote ul)
    if entry.suggestion and not entry.suggestion.startswith('See '):
        html = f'''{html}<p class="HOTTP"><b>Suggested translation</b>: {_hottpText(entry.suggestion)}</p>'''
    if entry.remark:
        html = f'''{html}<p class="HOTTP"><b>Remark</b>: {_hottpText(entry.remark)}</p>'''
    return html
# end of formatHOTTPEntry


def formatHOTTPNotes(level:int, BBB:str, C:str, V:str, state) -> str:
    """
    Return the formatted HOTTP notes for a verse (in state.navigationVersification numbering), or '' if none.
    """
    verseIndex = getattr(state, 'UBS_HOTTP_VERSE_INDEX', None)
    if not verseIndex or not C.isdigit() or not V.isdigit(): return ''
    result = _mapReference(state.navigationVersification, 'org', (BBB,C,V,None))
    entryIDs = []
    for reference in getattr(result, 'references', None) or (): # Nothing if the verse doesn't map
        for entryID in verseIndex.get(tuple(reference[:3]), ()):
            if entryID not in entryIDs: entryIDs.append(entryID)
    if not entryIDs: return ''
    factors = getattr(state, 'UBS_HOTTP_FACTORS', {})
    return '\n'.join(f'''<div class="HOTTPnote">{formatHOTTPEntry(state.UBS_HOTTP_ENTRIES[entryID], factors)}</div>'''
                        for entryID in entryIDs)
# end of formatHOTTPNotes
