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

CHANGELOG:
    2023-08-22 Change some logging from critical to errors
    2023-10-25 Make use of word table index; add colourisation of OET words
"""
# from gettext import gettext as _
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import re

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek


LAST_MODIFIED_DATE = '2023-10-25' # by RJH
SHORT_PROGRAM_NAME = "OETHandlers"
PROGRAM_NAME = "OpenBibleData OET handler"
PROGRAM_VERSION = '0.25'
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
        wordTable = state.OETRefData['word_table']
        firstWordNumber,lastWordNumber = state.OETRefData['word_table_index'][f'{BBB}_{C}:{V}']
        # # Go backwards through the ESFM table until we find the first word in this B/C/V
        # firstWordNumber = getLeadingInt( wordNumberStr )
        # rowStr = wordTable[firstWordNumber]
        # #  0    1          2        3           4           5          6            7           8     9           10
        # # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
        # assert rowStr.startswith( f'{BBB}_{C}:{V}w' )
        # # Search backwards through the word-table until we find the first word number still in the verse (includes variants)
        # while firstWordNumber > 1:
        #     firstWordNumber -= 1
        #     if not wordTable[firstWordNumber].startswith( f'{BBB}_{C}:{V}w' ):
        #         firstWordNumber += 1 # We went too far
        #         break
        # assert firstWordNumber == state.OETRefData['word_table_index'][f'{BBB}_{C}:{V}'][0], f"{wordNumberStr=} {firstWordNumber=} {state.OETRefData['word_table_index'][f'{BBB}_{C}:{V}']=}"

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
        for wordNumber in range( firstWordNumber, lastWordNumber+1 ):
            # if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
            #     break

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
            assert rowStr.startswith( f'{BBB}_{C}:{V}w' )
            # if not rowStr.startswith( f'{BBB}_{C}:{V}w' ): # gone into the next verse
            #     break
            row = rowStr.split( '\t' )
            #  0    1          2        3           4           5          6            7           8     9           10
            # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
            if not row[6]: # This Greek word is not in the GNT text
                continue
            assert int(row[6]), f"{row=}"

            # NOTE: We have to replace MODIFIER LETTER APOSTROPHE with RIGHT SINGLE QUOTATION MARK to match correctly
            if row[1].replace('ʼ','’') == olWord: # we have a Greek word match
                if currentOccurrenceNumber > 0:
                    assert olIndex == 0
                    currentOccurrenceNumber -= 1
                if currentOccurrenceNumber == 0: # We can start matching up now
                    lvEnglishWords.append( row[4].replace(' ','_') )
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
                if not row[6]: # This Greek word is not in the GNT text
                    continue
                assert int(row[6]), f"{row=}"
                if matchStart == -wordNumber:
                    matchStart = len(ourWords) # Convert to index of these words
                ourWords.append( row[1] )
            lvEnglishWords.append( f"(Some words not found in SR-GNT: {' '.join( ourWords )})" )
            logging.error( f"findLVQuote unable to match {BBB}_{C}:{V} '{originalQuote}' {occurrenceNumber=} {currentOccurrenceNumber=} {inGap=}\n  {olWords=}  {olIndex=}\n  {ourWords=} {matchStart=}" )
            # if BBB not in ('MRK',) or C not in ('1',) or V not in ('5','8','14'):
            #     halt

        html = ' '.join(lvEnglishWords)
        # checkHtml( f'LV {BBB} {C}:{V}', html, segmentOnly=True )
        return html
    else:
        logging.error( f"findLVQuote: OET-LV can't find a starting word number for {BBB} {C}:{V}")
        return ''
# end of OETHandlers.findLVQuote


linkedWordTitleRegex = re.compile( '="§(.+?)§"' ) # We inserted those § markers in our titleTemplate above
linkedWordNumberRegex = re.compile( '/W/([1-9][0-9]{0,5}).htm' ) # /W/ is the words folder
def livenOETWordLinks( bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, hrefTemplate:str, state ) -> InternalBibleEntryList:
    """
    Livens ESFM wordlinks in the OET versions (i.e., the words with ¦ numbers suffixed to them).

    Then add the transliteration to the title="§«GreekWord»§" popup.
    """
    # Liven the word links using the BibleOrgSys function
    revisedEntryList = bibleObject.livenESFMWordLinks( BBB, givenEntryList, linkTemplate=hrefTemplate, titleTemplate='§«GreekWord»§' )[0]
    # We get something back like:
    #   v=18
    #   v~=<a title="§καὶ§" href="../../rf/W/33110.htm#Top">And</a> \add +<a title="§Σαδδουκαῖοι§" href="../../rf/W/33112.htm#Top">the</a>\add*<a title="§Σαδδουκαῖοι§" href="../../rf/W/33112.htm#Top">_Saddoukaios</a>_\add <a title="§Σαδδουκαῖοι§" href="../../rf/W/33112.htm#Top">sect</a>\add* <a title="§ἔρχονται§" href="../../rf/W/33111.htm#Top">are</a><a title="§ἔρχονται§" href="../../rf/W/33111.htm#Top">_coming</a> <a title="§πρὸς§" href="../../rf/W/33113.htm#Top">to</a> <a title="§αὐτόν§" href="../../rf/W/33114.htm#Top">him</a>, <a title="§οἵτινες§" href="../../rf/W/33116.htm#Top">who</a> <a title="§λέγουσιν§" href="../../rf/W/33117.htm#Top">are</a><a title="§λέγουσιν§" href="../../rf/W/33117.htm#Top">_saying</a> <a title="§εἶναι§" href="../../rf/W/33120.htm#Top">to</a>_ <a title="§μὴ§" href="../../rf/W/33119.htm#Top">not</a> <a title="§εἶναι§" href="../../rf/W/33120.htm#Top">_be</a> \add +<a title="§ἀνάστασιν§" href="../../rf/W/33118.htm#Top">a</a>\add*<a title="§ἀνάστασιν§" href="../../rf/W/33118.htm#Top">_resurrection</a>, <a title="§καὶ§" href="../../rf/W/33121.htm#Top">and</a> <a title="§ἐπηρώτων§" href="../../rf/W/33122.htm#Top">they</a><a title="§ἐπηρώτων§" href="../../rf/W/33122.htm#Top">_were</a><a title="§ἐπηρώτων§" href="../../rf/W/33122.htm#Top">_asking</a> <a title="§αὐτὸν§" href="../../rf/W/33125.htm#Top">him</a> <a title="§λέγοντες§" href="../../rf/W/33126.htm#Top">saying</a>,
    #   ¬v=None

    # if len(revisedEntryList) < 10:
    #     print( f"{BBB}")
    #     for revisedEntry in revisedEntryList:
    #         marker = revisedEntry.getMarker()
    #         if marker not in ('v~','p~'): continue
    #         print( f"  {marker}={revisedEntry.getOriginalText()}")

    # Now add the transliteration to the Greek HTML title popups
    # At the same time, add some colourisation
    updatedVerseList = InternalBibleEntryList()
    for n, entry in enumerate( revisedEntryList ):
        originalText = entry.getOriginalText()
        if originalText is None or '§' not in originalText:
            updatedVerseList.append( entry )
            continue
        # If we get here, we have at least one ESFM wordlink row number in the text
        # print( f"createOETReferencePages {n}: '{originalText}'")
        searchStartIndex = 0
        transliterationsAdded = colourisationsAdded = 0
        while True:
            titleMatch = linkedWordTitleRegex.search( originalText, searchStartIndex )
            if not titleMatch:
                break
            # print( f"createOETReferencePages {BBB} word match 1='{match.group(1)}' all='{originalText[match.start():match.end()]}'" )
            greekWord = titleMatch.group(1)
            transliteratedWord = transliterate_Greek( greekWord )

            wordnumberMatch = linkedWordNumberRegex.search( originalText, titleMatch.end()+4 ) # After the following href
            assert wordnumberMatch
            wordNumber = int( wordnumberMatch.group(1) )
            wordRow = state.OETRefData['word_table'][wordNumber]
            SRLemma = wordRow.split( '\t' )[2]
            _ref, _greekWord, SRLemma, _GrkLemma, _glossWordsStr, _glossCaps, _probability, _extendedStrongs, _roleLetter, morphology, _tagsStr = wordRow.split( '\t' )

            # Do colourisation
            if morphology[4] != '.':
                # print( f"    {originalText[wordnumberMatch.end():]=}")
                wordStartIx = originalText.index( '>', wordnumberMatch.end()+5 ) + 1 # Allow for '#Top"' plus '>'
                wordEndIx = originalText.index( '<', wordStartIx + 1 )
                # print( f"  Found {BBB} word '{originalText[wordStartIx:wordEndIx]}'")
                originalText = f'''{originalText[:wordStartIx]}<span class="case{morphology[4]}">{originalText[wordStartIx:wordEndIx]}</span>{originalText[wordEndIx:]}'''
                # print( f"    Now '{originalText[wordnumberMatch.end():]}'")
                colourisationsAdded += 1
                

            newTitleGuts = f'''="{greekWord} ({transliteratedWord}){'' if SRLemma==transliteratedWord else f" from {SRLemma}"}"'''
            originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

            searchStartIndex = wordnumberMatch.end() + len(newTitleGuts) - len(greekWord) - 5 # We've added at least that many characters
            transliterationsAdded += 1
        if transliterationsAdded > 0 or colourisationsAdded > 0:
            # print( f"  Now '{originalText}'")
            if transliterationsAdded > 0:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Added {transliterationsAdded:,} {bibleObject.abbreviation} {BBB} transliterations to Greek titles." )
            if colourisationsAdded > 0:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Added {colourisationsAdded:,} {bibleObject.abbreviation} {BBB} colourisations to Greek words." )
            # adjText, cleanText, extras = _processLineFix( self, C:str,V:str, originalMarker:str, text:str, fixErrors:List[str] )
            # newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras(), originalText )
            # Since we messed up many of the fields, set them to blank/null entries so that the old/wrong/outdated values can't be accidentally used
            newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), None, '', None, originalText )
            updatedVerseList.append( newEntry )
        else:
            logging.critical( f"ESFMBible.livenESFMWordLinks unable to find wordlink title in '{originalText}'" )
            updatedVerseList.append( entry )
            halt

    return updatedVerseList
# end of OETHandlers.livenOETWordLinks function



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
