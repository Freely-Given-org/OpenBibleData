#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Summarise how the OET-RV translates each OET-LV source word.

The OET-RV ESFM files link English words back to OET-LV word-table rows,
e.g., `the¦10 father¦10 of¦10`. Collect those words per row number so that
the Greek and Hebrew word and lemma pages can say how the OET-RV renders them,
next to the OET-LV gloss summaries. The alignment is still incomplete, so the
summary always says how many occurrences (and what percentage) are linked.

CHANGELOG:
    2026-11-24 Created to show OET-RV renderings on word and lemma reference pages,
                always saying how many (and what percentage) of the occurrences are linked.
    2026-11-25 Show up to 50 renderings (was 20) before summarising the rest as ‘and N others’.
"""
from collections import Counter, defaultdict
from pathlib import Path
import logging
import re


WORD_TABLE_REGEX = re.compile(r'^\\rem WORDTABLE (\S+)', re.MULTILINE)
NOTE_REGEX = re.compile(r'\\(f|x) .*?\\\1\*', re.DOTALL) # Footnotes and cross-references
ALTERNATIVE_REGEX = re.compile(r'\\\+?add !.*?\\\+?add\*', re.DOTALL) # e.g., `\add !(Simon¦5595,\add*` alternative names
SUP_REGEX = re.compile(r'\\\+?sup\*? ?')
MARKER_REGEX = re.compile(r'\\\+?[a-z]+[0-9]*\*?')
LINKED_WORD_REGEX = re.compile(r'([^\s¦—–]+)¦([1-9][0-9]*)') # Like the Rust livening, only link the part after any dash
LEADING_CHARS = '“‘"([{—–-≈*@#%&<>^≡→?⇔!$+=¬/'
TRAILING_CHARS = '”"),.;:?!]}—–'


def tidyRVWord( word:str ) -> str:
    """Remove punctuation and OET formatting characters from around one linked RV word."""
    word = word.lstrip( LEADING_CHARS ).rstrip( TRAILING_CHARS )
    if word.endswith( '’' ) and not word.endswith( 's’' ): word = word[:-1] # Keep plural possessives like ‘Zebedaios’’
    return word.strip( '‘' )


def extractRVRenderings( esfmText:str ) -> dict[int,str]:
    """Return {LV word-table row number: OET-RV words linked to it} for one ESFM book.

    Words for the same row are joined with a space when adjacent,
        or with ‘…’ when unlinked or differently-linked words come between them.
    Alternative-name additions like `\\add !(Simon¦5595)\\add*` are ignored.
    """
    text = NOTE_REGEX.sub( ' ', esfmText )
    text = ALTERNATIVE_REGEX.sub( ' ', text )
    text = SUP_REGEX.sub( '', text )
    text = MARKER_REGEX.sub( ' ', text )
    words, lastEnds = defaultdict(list), {}
    for match in LINKED_WORD_REGEX.finditer( text ):
        rowNumber = int( match[2] )
        word = tidyRVWord( match[1] )
        if not word: continue
        if rowNumber in lastEnds:
            between = text[lastEnds[rowNumber]:match.start()]
            words[rowNumber].append( '…' if re.search( r'\w', between ) else '' )
        words[rowNumber].append( word )
        lastEnds[rowNumber] = match.end()
    return {rowNumber: ' '.join( word for word in wordList if word )
                for rowNumber, wordList in words.items()}


def loadRVRenderings( folderPath:str|Path ) -> dict[str,dict[int,str]]:
    """Return {word-table filename: {row number: OET-RV rendering}} for every OET-RV ESFM book."""
    renderings = defaultdict(dict)
    for filepath in sorted( Path( folderPath ).glob( 'OET-RV_*.ESFM' ) ):
        esfmText = filepath.read_text( encoding='utf-8' )
        match = WORD_TABLE_REGEX.search( esfmText )
        if not match:
            if '¦' in esfmText: logging.warning( f"loadRVRenderings: {filepath.name} has word links but no WORDTABLE line" )
            continue
        bookRenderings = extractRVRenderings( esfmText )
        if clashes := bookRenderings.keys() & renderings[match[1]].keys():
            logging.warning( f"loadRVRenderings: {filepath.name} reuses {len(clashes):,} {match[1]} row numbers, e.g., {min(clashes)}" )
        renderings[match[1]].update( bookRenderings )
    return dict(renderings)


def rvRenderingsSummaryHtml( rowNumbers:list[int], renderings:dict[int,str], subject:str='it', maxShown:int=50 ) -> str:
    """Return a summary paragraph saying how the OET-RV translates the given LV word rows.

    `subject` is the HTML for the word form or lemma, e.g., ‘the word form ‘X’’ or ‘it’.
    Renderings differing only by capitalisation (e.g., at sentence starts) are counted together,
        and shown in their most common lower-case form if they have one.
    """
    total = len( rowNumbers )
    forms = defaultdict(Counter)
    for rowNumber in rowNumbers:
        if rendering := renderings.get( rowNumber ):
            forms[rendering.lower()][rendering] += 1
    linked = sum( sum(counter.values()) for counter in forms.values() )
    if not linked:
        return f'<p class="summary">In the <em>OET-RV</em>, {"the only occurrence" if total==1 else f"none of the {total:,} occurrences"} of {subject} {"isn’t" if total==1 else "are"} linked to its source word yet.</p>'
    ranked = sorted( forms.values(), key=lambda counter: (-sum(counter.values()), min(counter)) )
    def displayForm( counter:Counter ) -> str:
        return max( counter, key=lambda form: (form[:1].islower(), counter[form]) ) # Prefer lower-case over sentence-initial capitals
    renderingStrs = [f'‘<b>{displayForm(counter)}</b>’({sum(counter.values()):,})' for counter in ranked[:maxShown]]
    if len(ranked) > maxShown:
        renderingStrs.append( f'and {len(ranked)-maxShown:,} others' )
    linkedStr = f' <small>({linkedCountStr(linked,total)})</small>'
    if len(ranked) == 1:
        return f'<p class="summary">In the <em>OET-RV</em>, {subject} is {"always " if linked==total and total>1 else ""}translated as ‘<b>{displayForm(ranked[0])}</b>’{linkedStr}.</p>'
    return f'<p class="summary">In the <em>OET-RV</em>, {subject} is translated in {len(ranked):,} different ways{linkedStr}: {", ".join(renderingStrs)}.</p>'


def linkedCountStr( linked:int, total:int ) -> str:
    """Say how many of the occurrences are linked, e.g., ‘19 of 22 occurrences linked so far: 86%’.

    The percentage is rounded down, so it never shows 100% while any occurrence is still unlinked.
    """
    if linked == total:
        return 'its only occurrence is linked' if total==1 else f'all {total:,} occurrences linked'
    return f'{linked:,} of {total:,} occurrences linked so far: {max(1, linked*100//total)}%'
