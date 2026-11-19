#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""
Load the extra UBS open-licensed resources (from our OET-adapted copies) that go along with the UBS dictionaries:
    - the flora, fauna, and realia handbooks (see ubsHandbooks.py)
    - the Hebrew Old Testament Text Project (HOTTP) text-critical notes (see ubsHOTTP.py)
    - the MARBLE index, which links each WLC Hebrew word to its UBS Hebrew dictionary sense
        (and to HOTTP notes, handbook articles, images, and map coordinates)
    - the UBS parallel passages database (OT/OT, gospel, and OT-quoted-in-NT parallels)

These are loaded (once, in the parent process) along with TOSN, and saved in the TOSN pickle.

CHANGELOG:
    2026-11-19 First version
"""
from collections import defaultdict
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
import unicodedata
from xml.etree import ElementTree

import bos_books_codes_py

from ubsHandbooks import loadHandbooks
from ubsHOTTP import loadHOTTP, loadHOTTPFactors


HANDBOOKS_SUBFOLDER = 'flora-fauna-realia/XML/'
HOTTP_SUBFOLDER = 'HOTTP/'
MARBLE_SUBFOLDER = 'index/WLC/JSON/'
PARALLELS_SUBFOLDER = 'parallel passages/'
PARALLELS_FILENAME = 'ParallelPassages.xml'


def sourceFilepaths(ubsFolder) -> list[Path]:
    """
    The source files read by loadUBSExtraResources (so that the TOSN pickle can be rebuilt when they change).
    """
    ubsFolder = Path(ubsFolder)
    return sorted((ubsFolder/HANDBOOKS_SUBFOLDER).glob('*_en.xml')) \
            + sorted((ubsFolder/HOTTP_SUBFOLDER).glob('*.XML')) + sorted((ubsFolder/HOTTP_SUBFOLDER).glob('*-EN.HTML')) \
            + sorted((ubsFolder/MARBLE_SUBFOLDER).glob('*.json')) \
            + [ubsFolder/PARALLELS_SUBFOLDER/PARALLELS_FILENAME]
# end of sourceFilepaths


HOLAM_WAW_RE = re.compile('\u05B9([\u05BC\u05C1\u05C2]*)\u05D5(?![\u05B0-\u05BC])')


def normaliseHebrewLemma(lemma:str) -> str:
    """
    The MARBLE index writes holam-waw as holam then waw (e.g., 'יֹום')
        whereas the UBS Hebrew dictionary has waw then holam ('יוֹם').
    (Any dagesh or shin/sin dot stays on the preceding letter,
        and a waw followed by its own vowel or dagesh, e.g., in 'מִצְוָה', isn't changed.)
    """
    decomposed = unicodedata.normalize('NFD', lemma)
    return unicodedata.normalize('NFC', HOLAM_WAW_RE.sub(lambda match: f'{match.group(1)}\u05D5\u05B9', decomposed))
# end of normaliseHebrewLemma


@dataclass
class MARBLEWord:
    """
    The MARBLE links for one WLC word segment.
    """
    word:int # MACULA word number in the verse (1-based; NB: MACULA numbers both the ketiv and the qere, but the OET only numbers the ketiv)
    segment:int # Segment (morpheme) number in the word (1-based)
    senses:list[tuple[str,str]] # (UBS Hebrew dictionary MainId, LEXID) for each resolved LexicalLink
    unresolvedSenses:list[str] # LexicalLinks that couldn't be resolved
    thematic:list[str] # e.g., 'Realia:1.5.2.1', 'Flora:5.1.2'
    textual:list[str] # HOTTP entry IDs (zero-padded like the HOTTP.XML Ids, e.g., '01474')
    images:list[str] # e.g., 'WEB-0029_animals_ark'
    maps:list[str] # 'latitude,longitude'


def loadMARBLEIndex(folderpath, hebrewDictionary:list[dict]) -> dict[tuple[str,str,str],list[MARBLEWord]]:
    """
    Load the MARBLE WLC index (one JSON file per OT book).

    The IDs are like 'o010010010012' = book 01, chapter 001, verse 001, word 001, segment 2,
    and the lexical links are like 'SDBH:רוּחַ:000003:Air' where the sense code is the
        zero-based base form (3 digits) and meaning (3 digits) of that lemma in the UBS Hebrew dictionary.

    Returns a dict with original-numbered (BBB,C,V) keys and lists of MARBLEWord values.
    """
    # NB: Some meanings are stored out of order, so we use the base form and meaning digits of the LEXIDs
    #   (e.g., '000396001003000' = MainId 000396, base form 001, meaning 003), not their positions in the lists
    lexIDsByLemma:dict[str,dict[str,tuple[str,str]]] = defaultdict(dict)
    for entry in hebrewDictionary:
        for baseForm in entry['BaseForms']:
            for meaning in baseForm.get('LEXMeanings') or ():
                lexID = meaning['LEXID']
                code = f'{int(lexID[6:9])-1:03}{int(lexID[9:12])-1:03}' # Zero-based in the MARBLE links
                lexIDsByLemma[unicodedata.normalize('NFC',entry['Lemma'])][code] = (entry['MainId'], lexID)
    index:dict[tuple[str,str,str],list[MARBLEWord]] = defaultdict(list)
    numUnresolved = numLinks = 0
    for filepath in sorted(Path(folderpath).glob('*.json')):
        with open(filepath, 'rt', encoding='utf-8-sig') as jsonFile:
            for item in json.load(jsonFile):
                senses, unresolved = [], []
                for link in item.get('LexicalLinks') or ():
                    numLinks += 1
                    parts = link.split(':', 3)
                    if len(parts) == 4 and parts[0] == 'SDBH':
                        lemma, code = parts[1], parts[2]
                        resolved = lexIDsByLemma.get(unicodedata.normalize('NFC',lemma), {}).get(code) \
                                    or lexIDsByLemma.get(normaliseHebrewLemma(lemma), {}).get(code)
                        if resolved:
                            senses.append(resolved); continue
                    unresolved.append(link); numUnresolved += 1
                for wordID in item['ID'].split(): # A few IDs are multi-word phrases, e.g., 'o220080110042 o220080110051'
                    match = re.fullmatch(r'o(\d\d)(\d{3})(\d{3})(\d{3})(\d)', wordID)
                    BBB = bos_books_codes_py.get_bos_book_code_from_reference_number(int(match.group(1))) if match else None
                    if not BBB:
                        logging.warning(f"loadMARBLEIndex: unexpected ID {wordID!r} in {filepath.name}"); continue
                    index[(BBB, str(int(match.group(2))), str(int(match.group(3))))].append(
                        MARBLEWord(int(match.group(4)), int(match.group(5)), senses, unresolved,
                                    list(item.get('ThematicLinks') or ()),
                                    [f"{int(textual[5:]):05}" for textual in item.get('TextualLinks') or () if re.fullmatch(r'HOTTP\d+', textual)],
                                    list(item.get('ImageLinks') or ()), list(item.get('MapLinks') or ())))
    if numUnresolved:
        logging.info(f"loadMARBLEIndex: couldn't resolve {numUnresolved:,} of {numLinks:,} lexical links to UBS Hebrew dictionary senses")
    return dict(index)
# end of loadMARBLEIndex


@dataclass
class ParallelVerse:
    BBB:str
    reference:str # As given, e.g., 'MRK 10:7-8' (original numbering)
    verses:list[tuple[str,str,str]] # The original-numbered (BBB,C,V) verses covered
    language:str # 'HEB' or 'GRK' (NB: HEB codes count LXX words when the passage is quoted in the NT)
    matchCodes:str # One digit per word (0/1/2 = no/partial/full match, +3 or +6 for presentation line breaks)


def parseParallelReference(reference:str) -> tuple[str,list[tuple[str,str,str]]]|None:
    """
    Parse a reference like 'GEN 1:27', 'MRK 10:7-8', 'ACT 2:17,19', or 'LUK 3:23-25,27' (USFM book codes).
    """
    match = re.fullmatch(r'([1-4A-Z]{3}) (\d+):([\d,-]+)', reference.strip())
    if not match: return None
    BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code(match.group(1))
    if not BBB: return None
    C, verses = match.group(2), []
    for part in match.group(3).split(','):
        start, _dash, end = part.partition('-')
        if not start.isdigit() or (end and not end.isdigit()): return None
        verses.extend((BBB, C, str(V)) for V in range(int(start), int(end or start)+1))
    return BBB, verses
# end of parseParallelReference


def loadParallelPassages(folderpath) -> tuple[list[list[ParallelVerse]],dict[tuple[str,str,str],list[int]]]:
    """
    Load the UBS parallel passages database.

    Returns a list of passage groups and an index from original-numbered (BBB,C,V) to group numbers.
    """
    groups:list[list[ParallelVerse]] = []
    verseIndex:dict[tuple[str,str,str],list[int]] = defaultdict(list)
    for passage in ElementTree.parse(Path(folderpath, PARALLELS_FILENAME)).getroot().iterfind('Passage'):
        group = []
        for verseElement in passage.iterfind('Verse'):
            reference = (verseElement.text or '').strip()
            parsed = parseParallelReference(reference)
            if parsed is None:
                logging.warning(f"loadParallelPassages: can't parse reference {reference!r}"); continue
            language = 'HEB' if verseElement.get('HEB') is not None else 'GRK'
            group.append(ParallelVerse(parsed[0], reference, parsed[1], language, verseElement.get(language) or ''))
        if len(group) < 2: continue
        groupNumber = len(groups)
        groups.append(group)
        for parallelVerse in group:
            for verseRef in parallelVerse.verses:
                if groupNumber not in verseIndex[verseRef]: verseIndex[verseRef].append(groupNumber)
    return groups, dict(verseIndex)
# end of loadParallelPassages


def isQuotationGroup(group:list[ParallelVerse]) -> bool:
    """ An OT passage quoted in the NT (the group has both HEB and GRK entries) """
    return len({parallelVerse.language for parallelVerse in group}) > 1


def loadUBSExtraResources(ubsFolder, state) -> None:
    """
    Load the extra UBS resources into state (the UBS Hebrew dictionary must already be loaded).
    """
    ubsFolder = Path(ubsFolder)
    state.UBS_HANDBOOKS = loadHandbooks(ubsFolder/HANDBOOKS_SUBFOLDER)
    state.UBS_HOTTP_ENTRIES, state.UBS_HOTTP_VERSE_INDEX = loadHOTTP(ubsFolder/HOTTP_SUBFOLDER)
    state.UBS_HOTTP_FACTORS = loadHOTTPFactors(ubsFolder/HOTTP_SUBFOLDER)
    hebrewDictionary = getattr(state, 'UBS_HEB_DATA', None)
    if hebrewDictionary is None: # Dict.py's loaders put the dictionaries into the global settings.state
        from settings import state as globalState
        hebrewDictionary = globalState.UBS_HEB_DATA
    state.UBS_MARBLE_INDEX = loadMARBLEIndex(ubsFolder/MARBLE_SUBFOLDER, hebrewDictionary)
    state.UBS_PARALLEL_GROUPS, state.UBS_PARALLEL_VERSE_INDEX = loadParallelPassages(ubsFolder/PARALLELS_SUBFOLDER)
# end of loadUBSExtraResources

UBS_EXTRA_STATE_ATTRIBUTES = ('UBS_HANDBOOKS', 'UBS_HOTTP_ENTRIES', 'UBS_HOTTP_VERSE_INDEX', 'UBS_HOTTP_FACTORS',
                                'UBS_MARBLE_INDEX', 'UBS_PARALLEL_GROUPS', 'UBS_PARALLEL_VERSE_INDEX') # In pickle order
