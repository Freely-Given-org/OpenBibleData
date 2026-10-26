#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""OET word-table access. References may change; native row identifiers never do.

CHANGELOG:
    2026-10-21 Exclude Hebrew paragraph-marker rows from UHB word alignment.
"""
import logging
import re
import unicodedata

from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus, VersificationMappingError
from BibleOrgSys.Internals.InternalBiblePassages import passageReferencesFromEntries


def wordTableName(BBB):
    from bos_books_codes_py import is_new_testament_nr
    return f"OET-LV_{'NT' if is_new_testament_nr(BBB) else 'OT'}_word_table.tsv"


def nativeWordRows(references, state):
    """Return ordered, deduplicated native row numbers, never a bounding range.

    Whole native verses include unused Greek variants and Hebrew separators.
    A suffix uses the ESFM links in that exact BOS text portion. Do not infer a
    subdivision of a whole verse when the edition has no stored suffix.
    """
    numbers = []
    lvBible = state.preloadedBibles['OET-LV']
    for BBB, C, V, suffix in references:
        table = wordTableName(BBB)
        first, last = state.OETRefData['word_table_indexes'][table][f'{BBB}_{C}:{V}']
        selected = range(first, last+1)
        if suffix:
            portions = lvBible.getPassageData(((BBB,C,V,suffix),))
            linked = {int(n) for portion in portions for entry in portion.entries
                      for n in re.findall(r'¦(\d+)', entry.getOriginalText() or '')}
            selected = [n for n in selected if n in linked]
            if not selected:
                raise KeyError((BBB,C,V,suffix))
        numbers.extend(selected)
    return tuple(dict.fromkeys(numbers))


def mappedWordRows(sourceSystem, references, state):
    result = state.preloadedBibles['OET-LV'].convertReferencesFromVersification(sourceSystem, references, expandGroups=True)
    if result.status != MappingStatus.EXACT:
        raise VersificationMappingError(result)
    return nativeWordRows(result.references, state)


def passageWordRows(passage, state):
    """Include every stored span BOS returned (including indivisible bridges)."""
    bible = state.preloadedBibles['OET-LV']
    references = [ref for portion in passage.portions
                  for ref in passageReferencesFromEntries(portion.reference, portion.entries, bible)]
    return nativeWordRows(references, state)


def translationNoteQuoteData(BBB, C, V, state):
    """Supply the Rust quote matcher with mapped LV text and native word rows."""
    try:
        passage = state.preloadedBibles['OET-LV'].getMappedPassage(
            state.BibleVersifications['UTN'], ((BBB,C,V),), expandGroups=True)
        rows = passageWordRows(passage, state)
    except (VersificationMappingError, KeyError) as error:
        logging.warning('Translation-note LV alignment unavailable at %s %s:%s: %s', BBB,C,V,error)
        return [], []
    return [entry.getOriginalText() or '' for portion in passage.portions for entry in portion.entries], list(rows)


def matchedHebrewWordRows(BBB, C, V, words, state):
    """Validate the UHB words against mapped native rows before attaching links.

    Differences in vocalisation and morpheme separators do not change identity.
    Different consonants/readings must not acquire a guessed word identifier.
    """
    def consonants(word):
        return ''.join(c for c in unicodedata.normalize('NFD', word)
                       if '\u05d0' <= c <= '\u05ea' or c in ('־','׀'))
    rows = mappedWordRows(state.BibleVersifications['UHB'], ((BBB,C,V),), state)
    table = state.OETRefData['word_tables'][wordTableName(BBB)]
    candidates = [(n, table[n].split('\t')) for n in rows]
    # brightenUHB removes paragraph markers from the displayed word list.
    # Keep maqaf/paseq rows: those separators still occupy positions in it.
    candidates = [(n, fields) for n, fields in candidates
                  if 'note' not in fields[1] and consonants(fields[6])
                  and not (fields[1] == 'seg' and fields[5] in ('x-pe', 'x-samekh'))]
    if [consonants(word) for word in words] != [consonants(fields[6]) for _, fields in candidates]:
        raise ValueError(f'UHB {BBB} {C}:{V}: mapped word rows differ from the displayed Hebrew')
    return [n for n, _ in candidates]
