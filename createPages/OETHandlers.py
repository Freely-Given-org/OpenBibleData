#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# OETHandlers.py
#
# Module handling OpenBibleData OETHandlers functions
#
# Copyright (C) 2023 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module handling OETHandlers functions.

BibleOrgSys uses a three-character book code to identify books.
    These referenceAbbreviations are nearly always represented as BBB in the program code
            (although formally named referenceAbbreviation
                and possibly still represented as that in some of the older code),
        and in a sense, this is the centre of the BibleOrgSys.
    The referenceAbbreviation/BBB always starts with a letter, and letters are always UPPERCASE
        so 2 Corinthians is 'CO2' not '2Co' or anything.
        This was because early versions of HTML ID fields used to need
                to start with a letter (not a digit),
            (and most identifiers in computer languages still require that).
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import re

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

import sys
sys.path.append( '../../BibleTransliterations/Python/' )

# from html import checkHtml


LAST_MODIFIED_DATE = '2023-05-05' # by RJH
SHORT_PROGRAM_NAME = "OETHandlers"
PROGRAM_NAME = "OpenBibleData OET handler"
PROGRAM_VERSION = '0.21'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


def findLVQuote( level:int, BBB:str, C:str, V:str, occurrenceNumber:int, originalQuote:str, state ) -> str: # html
    """
    Given an original language (Heb/Grk) quote,
        find the OET-LV English words that match the OL words.

    Note that the original quote might have an & in it for non-consecutive quote portions.

    Note also that the SR-GNT might have ˚ nomina sacra marks in it, e.g., ˚Ἰησοῦ ˚Χριστοῦ, Υἱοῦ ˚Θεοῦ
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {BBB} {C}:{V}, {occurrenceNumber=} {originalQuote=}, … )")
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {BBB} {C}:{V}, {occurrenceNumber=} {originalQuote=}, … )")
    currentOccurrenceNumber = occurrenceNumber

    try:
        lvVerseEntryList, _lvContextList = state.preloadedBibles['OET-LV'].getContextVerseData( (BBB, C, V) )
    except (KeyError, TypeError): # TypeError is if None is returned
        logger = logging.critical if BBB in state.booksToLoad['OET-LV'] else logging.warning
        logger( f"findLVQuote: OET-LV has no text for {BBB} {C}:{V}")
        return ''

    # Find a ESFM word number that belongs with this B/C/V
    wordNumberStr = None
    for lvVerseEntry in lvVerseEntryList:
        text = lvVerseEntry.getFullText()
        if not text or '¦' not in text: continue # no interest to us here
        # print( f"findLVQuote found {BBB} {C}:{V} {lvVerseEntry=}" )
        ixMarker = text.index( '¦' )
        if not wordNumberStr: # We only need to find one word number (preferably the first one) here
            wordNumberStr = ''
            for increment in range( 1, 7 ): # (maximum of six word-number digits)
                if text[ixMarker+increment].isdigit():
                    wordNumberStr = f'{wordNumberStr}{text[ixMarker+increment]}' # Append the next digit
                else: break
        if wordNumberStr: # we only need one
            break

    if wordNumberStr: # Now we have a word number from the correct verse
        # Go backwards through the ESFM table until we find the first word in this B/C/V
        firstWordNumber = getLeadingInt( wordNumberStr )
        wordTable = state.OETRefData['word_table']
        rowStr = wordTable[firstWordNumber]
        #  0    1      2      3           4          5            6           7     8           9
        # 'Ref\tGreek\tLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
        assert rowStr.startswith( f'{BBB}_{C}:{V}w' )
        # Search backwards through the word-table until we find the first word number still in the verse (includes variants)
        while firstWordNumber > 1:
            firstWordNumber -= 1
            if not wordTable[firstWordNumber].startswith( f'{BBB}_{C}:{V}w' ):
                firstWordNumber += 1 # We went too far
                break

        # Ok, now we can trying to match the given Greek words
        #   Note: We don't try to match punctuation, only the clean words
        adjustedOriginalQuote = originalQuote.strip() \
                                    .replace( ',', '' ).replace( '.', '' ).replace( '?', '' ).replace( '!', '' ) \
                                    .replace( ';', '' ).replace( ':', '' ).replace( '—', '' ) \
                                    .replace( '(', '' ).replace( ')', '' ) \
                                    .replace( '   ', ' ' ).replace( '  ', ' ' ) # This last one copes with uW having multiple spaces
        adjustedOriginalQuote = adjustedOriginalQuote.removesuffix( ' & ') # Rev 15:4 after final ? is removed above
        # if DEBUGGING_THIS_MODULE:
        #     import unicodedata
        #     for char in adjustedOriginalQuote:
        #         if char not in ' &’' and 'GREEK' not in unicodedata.name(char):
        #             print( f"findLVQuote: uW TN has unexpected char {BBB} {C}:{V} '{char}' ({unicodedata.name(char)}) from '{adjustedOriginalQuote}' from '{originalQuote}'" )
        #             halt
        olWords = adjustedOriginalQuote.split( ' ' )
        assert '' not in olWords, f"findLVQuote: uW TN has unexpected empty string {BBB} {C}:{V} {olWords=} from '{adjustedOriginalQuote}' from '{originalQuote}'"
        olIndex = 0
        lvEnglishWords = []
        inGap = False
        matchStart = None # Just for curiosity / debugging
        for wordNumber in range( firstWordNumber, firstWordNumber+999 ):
            if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                break

            olWord = olWords[olIndex]
            if olWord == '&':
                lvEnglishWords.append( '&' )
                olIndex += 1
                if olIndex == 0:
                    logging.critical( f"findLVQuote: uW TN has ampersand at beginning {BBB} {C}:{V} '{originalQuote}'" )
                elif olIndex == len(olWords):
                    logging.critical( f"findLVQuote: uW TN has ampersand at end {BBB} {C}:{V} '{originalQuote}'" )
                    break # finished
                inGap = True
                continue # Pass over whatever this SR row was (i.e., sort of match the ampersand)

            rowStr = wordTable[wordNumber]
            if not rowStr.startswith( f'{BBB}_{C}:{V}w' ): # gone into the next verse
                break
            row = rowStr.split( '\t' )
            #  0    1      2      3           4          5            6           7     8           9
            # 'Ref\tGreek\tLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
            if not row[5]: # This Greek word is not in the GNT text
                continue
            assert int(row[5]), f"{row=}"

            # NOTE: We have to replace MODIFIER LETTER APOSTROPHE with RIGHT SINGLE QUOTATION MARK to match correctly
            if row[1].replace('ʼ','’') == olWord: # we have a Greek word match
                if currentOccurrenceNumber > 0:
                    assert olIndex == 0
                    currentOccurrenceNumber -= 1
                if currentOccurrenceNumber == 0: # We can start matching up now
                    lvEnglishWords.append( row[3].replace(' ','_') )
                    inGap = False
                    if olIndex == 0:
                        matchStart = -wordNumber # negative so don't get double match below
                    olIndex += 1
                    if olIndex >= len(olWords): # finished
                        break
            # We had a mismatch
            elif olIndex>0 and not inGap: # No problem at all if either we haven't started yet, or else we're in a gap (&)
                olIndex = 0 # We started a match and then failed -- back to the beginning
                matchStart = None

        if olIndex < len(olWords): # We didn't match them all
            ourWords = []
            for wordNumber in range( firstWordNumber, firstWordNumber+999 ):
                if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                    break
                rowStr = wordTable[wordNumber]
                if not rowStr.startswith( f'{BBB}_{C}:{V}w' ): # gone into the next verse
                    break
                row = rowStr.split( '\t' )
                if not row[5]: # This Greek word is not in the GNT text
                    continue
                assert int(row[5]), f"{row=}"
                if matchStart == -wordNumber:
                    matchStart = len(ourWords) # Convert to index of these words
                ourWords.append( row[1] )
            lvEnglishWords.append( f"(Some words not found in SR-GNT: {' '.join( ourWords )})" )
            logging.critical( f"findLVQuote unable to match {BBB}_{C}:{V} '{originalQuote}' {occurrenceNumber=} {currentOccurrenceNumber=} {inGap=}\n  {olWords=}  {olIndex=}\n  {ourWords=} {matchStart=}" )
            # if BBB not in ('MRK',) or C not in ('1',) or V not in ('5','8','14'):
            #     halt

        html = ' '.join(lvEnglishWords)
        # checkHtml( f'LV {BBB} {C}:{V}', html, segmentOnly=True )
        return html
    else:
        logging.critical( f"findLVQuote: OET-LV can't find a starting word number for {BBB} {C}:{V}")
        return ''
# end of OETHandlers.findLVQuote


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the OETHandlers object
    findLVQuote( ['OET','OET-RV','OET-LV', 'ULT','UST'] )
# end of OETHandlers.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the OETHandlers object
    findLVQuote( ['OET','OET-RV','OET-LV', 'ULT','UST'] )
# end of OETHandlers.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of OETHandlers.py
