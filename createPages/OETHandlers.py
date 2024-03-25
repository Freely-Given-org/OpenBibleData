#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# OETHandlers.py
#
# Module handling OpenBibleData OETHandlers functions
#
# Copyright (C) 2023-2024 Robert Hunt
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

getOETTidyBBB( BBB:str, titleCase:Optional[bool]=False, allowFourChars:Optional[bool]=True ) -> str
getOETBookName( BBB:str ) -> str

findLVQuote( level:int, BBB:str, C:str, V:str, occurrenceNumber:int, originalQuote:str, state:State ) -> str (html)

livenOETWordLinks( bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, hrefTemplate:str, state:State ) -> InternalBibleEntryList


CHANGELOG:
    2023-08-22 Change some logging from critical to errors
    2023-10-25 Make use of word table index; add colourisation of OET words
    2023-12-15 Improve colorisation of OET words
    2024-03-13 Add getOETBookName(BBB) function
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
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State


LAST_MODIFIED_DATE = '2024-03-25' # by RJH
SHORT_PROGRAM_NAME = "OETHandlers"
PROGRAM_NAME = "OpenBibleData OET handler"
PROGRAM_VERSION = '0.51'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


def getOETTidyBBB( BBB:str, titleCase:Optional[bool]=False, allowFourChars:Optional[bool]=True ) -> str:
    """
    Our customised version of tidyBBB
    """
    newBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=titleCase, allowFourChars=allowFourChars )
    # OT
    if newBBB == 'JNA': return 'YNA'
    if newBBB == 'Jna': return 'Yna'
    # NT
    if newBBB == 'JHN': return 'YHN'
    if newBBB == 'Jhn': return 'Yhn'
    if newBBB == 'JOHN': return 'YHN'
    if newBBB == 'John': return 'Yhn'
    if newBBB == 'JAM': return 'YAC'
    if newBBB == 'Jam': return 'Yac'
    if newBBB == 'ACTS': return 'ACTs'
    if newBBB == '1JN': return '1YN'
    if newBBB == '2JN': return '2YN'
    if newBBB == '3JN': return '3YN'
    if newBBB == '1Jn': return '1Yn'
    if newBBB == '2Jn': return '2Yn'
    if newBBB == '3Jn': return '3Yn'
    if newBBB == '1JHN': return '1YHN'
    if newBBB == '2JHN': return '2YHN'
    if newBBB == '3JHN': return '3YHN'
    if newBBB == '1Jhn': return '1Yhn'
    if newBBB == '2Jhn': return '2Yhn'
    if newBBB == '3Jhn': return '3Yhn'
    if newBBB == 'JUDE': return 'YUD'
    if newBBB == 'Jude': return 'Yud'
    return newBBB
# end of Bibles.getOETTidyBBB


def getOETBookName( BBB:str ) -> str:
    """
    """
    return ( BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)
                .replace('Jonah','Yonah/(Jonah)')
                .replace('John','Yohan/(John)')
                .replace('James','Jacob/(James)')
                .replace('1 John',' 1 Yohan/(John)')
                .replace('2 John',' 2 Yohan/(John)')
                .replace('3 John',' 3 Yohan/(John)')
                .replace('Jude','Jacob/(Jude)')
            )
# end of OETHandlers.getOETBookName
    

def findLVQuote( level:int, BBB:str, C:str, V:str, occurrenceNumber:int, originalQuote:str, state:State ) -> str: # html
    """
    Given an original language (Heb/Grk) quote,
        find the OET-LV English words that match the OL words.

    Note that the original quote might have an & in it for non-consecutive quote portions.

    Note also that the SR-GNT might have ˚ nomina sacra marks in it, e.g., ˚Ἰησοῦ ˚Χριστοῦ, Υἱοῦ ˚Θεοῦ
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {BBB} {C}:{V}, {occurrenceNumber=} {originalQuote=}, … )")
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {BBB} {C}:{V}, {occurrenceNumber=} {originalQuote=}, … )")
    currentOccurrenceNumber = occurrenceNumber

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    wordFileName = 'OET-LV_NT_word_table.tsv' if NT else 'OET-LV_OT_word_table.tsv'

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
        wordTable = state.OETRefData['word_tables'][wordFileName]
        firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{C}:{V}']
        # # Go backwards through the ESFM table until we find the first word in this B/C/V
        # firstWordNumber = getLeadingInt( wordNumberStr )
        # rowStr = wordTable[firstWordNumber]
        # #  0    1          2        3           4              5              6          7            8           9     10          11
        # # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
        # assert rowStr.startswith( f'{BBB}_{C}:{V}w' )
        # # Search backwards through the word-table until we find the first word number still in the verse (includes variants)
        # while firstWordNumber > 1:
        #     firstWordNumber -= 1
        #     if not wordTable[firstWordNumber].startswith( f'{BBB}_{C}:{V}w' ):
        #         firstWordNumber += 1 # We went too far
        #         break
        # assert firstWordNumber == state.OETRefData['word_table_indexes']wordFileName[f'{BBB}_{C}:{V}'][0], f"{wordNumberStr=} {firstWordNumber=} {state.OETRefData['word_table_indexes']wordFileName[f'{BBB}_{C}:{V}']=}"

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
            # if not rowStr.startswith( f'{BBB}_{C}:{V}w' ): # gone into the next verse
            #     break
            row = rowStr.split( '\t' )

            if NT:
                #  0    1          2        3           4              5              6          7            8           9     10          11
                # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
                assert rowStr.startswith( f'{BBB}_{C}:{V}w' ), f"{BBB} {C}:{V} {rowStr=}"
                if not row[7]: # This Greek word is not in the GNT text
                    continue
                assert int(row[7]), f"{BBB} {C}:{V} {row=}"

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
            else: # OT
                #  0    1        2       3                4        5                      6           7     8                9                10                         11         12                   13                   14                15          16
                # 'Ref\tOSHBid\tRowType\tMorphemeRowList\tStrongs\tCantillationHierarchy\tMorphology\tWord\tNoCantillations\tMorphemeGlosses\tContextualMorphemeGlosses\tWordGloss\tContextualWordGloss\tGlossCapitalisation\tGlossPunctuation\tGlossOrder\tGlossInsert'
                assert rowStr.startswith( f'{BBB}_{C}:{V}' ), f"{BBB} {C}:{V} {rowStr=}" # without the 'w' because segs and notes don't have word numbers
                if row[8] == olWord: # we have a Hebrew word match
                    if currentOccurrenceNumber > 0:
                        assert olIndex == 0
                        currentOccurrenceNumber -= 1
                    if currentOccurrenceNumber == 0: # We can start matching up now
                        gloss = row[12] if row[12] else row[11] if row[11] else row[10] if row[10] else row[9]
                        if not gloss:
                            logging.critical( f"No available gloss1 for Hebrew {row}" )
                        # assert gloss, f"{BBB} {C}:{V} {row=}"
                        lvEnglishWords.append( gloss.replace(' ','_') )
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
                if NT:
                    if not row[7]: # This Greek word is not in the GNT text
                        continue
                    assert int(row[7]), f"{row=}"
                    if matchStart == -wordNumber:
                        matchStart = len(ourWords) # Convert to index of these words
                    ourWords.append( row[1] )
                else: # OT
                    if matchStart == -wordNumber:
                        matchStart = len(ourWords) # Convert to index of these words
                    gloss = row[12] if row[12] else row[11] if row[11] else row[10] if row[10] else row[9]
                    if not gloss:
                        logging.critical( f"No available gloss2 for Hebrew {row}" )
                    # assert gloss, f"{BBB} {C}:{V} {row=}"
                    ourWords.append( gloss )
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
linkedHebrewWordNumberRegex = re.compile( '/HebWrd/([1-9][0-9]{0,5}).htm' ) # /HebWrd/ is the Hebrew words folder
linkedGreekWordNumberRegex  = re.compile( '/GrkWrd/([1-9][0-9]{0,5}).htm' ) # /GrkWrd/ is the Greek words folder
def livenOETWordLinks( bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, hrefTemplate:str, state:State ) -> InternalBibleEntryList:
    """
    Livens ESFM wordlinks in the OET versions (i.e., the words with ¦ numbers suffixed to them).

    Then add the transliteration to the title="§«GreekWord»§" popup.
    """
    from createParallelVersePages import GREEK_CASE_CLASS_DICT

    assert len(bibleObject.ESFMWordTables) == 2, f"{len(bibleObject.ESFMWordTables)=}"

    # Liven the word links using the BibleOrgSys function
    revisedEntryList = bibleObject.livenESFMWordLinks( BBB, givenEntryList, linkTemplate=hrefTemplate, titleTemplate='§«GreekWord»§' )[0]
    # We get something back like:
    #   v=18
    #   v~=<a title="§καὶ§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33110.htm#Top">And</a> \add +<a title="§Σαδδουκαῖοι§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33112.htm#Top">the</a>\add*<a title="§Σαδδουκαῖοι§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33112.htm#Top">_Saddoukaios</a>_\add <a title="§Σαδδουκαῖοι§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33112.htm#Top">sect</a>\add* <a title="§ἔρχονται§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33111.htm#Top">are</a><a title="§ἔρχονται§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33111.htm#Top">_coming</a> <a title="§πρὸς§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33113.htm#Top">to</a> <a title="§αὐτόν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33114.htm#Top">him</a>, <a title="§οἵτινες§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33116.htm#Top">who</a> <a title="§λέγουσιν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33117.htm#Top">are</a><a title="§λέγουσιν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33117.htm#Top">_saying</a> <a title="§εἶναι§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33120.htm#Top">to</a>_ <a title="§μὴ§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33119.htm#Top">not</a> <a title="§εἶναι§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33120.htm#Top">_be</a> \add +<a title="§ἀνάστασιν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33118.htm#Top">a</a>\add*<a title="§ἀνάστασιν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33118.htm#Top">_resurrection</a>, <a title="§καὶ§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33121.htm#Top">and</a> <a title="§ἐπηρώτων§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33122.htm#Top">they</a><a title="§ἐπηρώτων§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33122.htm#Top">_were</a><a title="§ἐπηρώτων§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33122.htm#Top">_asking</a> <a title="§αὐτὸν§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33125.htm#Top">him</a> <a title="§λέγοντες§" href="../../ref/{'GrkWrd' if NT else 'HebWrd'}/33126.htm#Top">saying</a>,
    #   ¬v=None

    # if len(revisedEntryList) < 10:
    #     print( f"{BBB}")
    #     for revisedEntry in revisedEntryList:
    #         marker = revisedEntry.getMarker()
    #         if marker not in ('v~','p~'): continue
    #         print( f"  {marker}={revisedEntry.getOriginalText()}")

    # Now add the transliteration to the Greek HTML title popups
    # At the same time, add some colourisation
    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    wordFileName = 'OET-LV_NT_word_table.tsv' if NT else 'OET-LV_OT_word_table.tsv'

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
            originalLanguageWord = titleMatch.group(1)
            if NT:
                transliteratedWord = transliterate_Greek( originalLanguageWord )

                wordnumberMatch = linkedGreekWordNumberRegex.search( originalText, titleMatch.end()+4 ) # After the following href
                assert wordnumberMatch, f"{BBB} {originalLanguageWord=} {originalText=}"
                wordNumber = int( wordnumberMatch.group(1) )
                wordRow = state.OETRefData['word_tables'][wordFileName][wordNumber]
                # SRLemma = wordRow.split( '\t' )[2]
                _ref, _greekWord, SRLemma, _GrkLemma, _VLTGlossWordsStr, _OETGlossWordsStr, _glossCaps, _probability, extendedStrongs, roleLetter, morphology, _tagsStr = wordRow.split( '\t' )

                # Do colourisation
                if roleLetter == 'V':
                    caseClassName = 'greekVrb'
                elif extendedStrongs == '37560': # Greek 'οὐ' (ou) 'not'
                    caseClassName = 'greekNeg'
                # TODO: Need to find where collation table is imported and change 'None' to None there (and then fix this again)
                elif morphology!='None' and morphology[4] != '.': # Two words in table have morphology of 'None' Jhn 5:27 w2
                    caseClassName = f'''greek{GREEK_CASE_CLASS_DICT[morphology[4]]}'''
                else: caseClassName = None

                if caseClassName: # Add a clase to the anchor for the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    assert originalText[wordnumberMatch.end():].startswith( '#Top">' )
                    anchorEndIx = originalText.index( '>', wordnumberMatch.end()+5 ) # Allow for '#Top"'
                    assert originalText[anchorEndIx] == '>'
                    originalText = f'''{originalText[:anchorEndIx]} class="{caseClassName}"{originalText[anchorEndIx:]}'''
                    # print( f"    livenOETWordLinks now '{originalText[wordnumberMatch.end():]}'")
                    colourisationsAdded += 1
                    # # Old Code puts a new span inside the anchor containing the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    # wordStartIx = originalText.index( '>', wordnumberMatch.end()+5 ) + 1 # Allow for '#Top"' plus '>'
                    # wordEndIx = originalText.index( '<', wordStartIx + 1 )
                    # print( f"  livenOETWordLinks found {BBB} word '{originalText[wordStartIx:wordEndIx]}'")
                    # originalText = f'''{originalText[:wordStartIx]}<span class="case{morphology[4]}">{originalText[wordStartIx:wordEndIx]}</span>{originalText[wordEndIx:]}'''
                    # print( f"    livenOETWordLinks now '{originalText[wordnumberMatch.end():]}'")
                    # colourisationsAdded += 1

                newTitleGuts = f'''="{originalLanguageWord} ({transliteratedWord}){'' if SRLemma==transliteratedWord else f" from {SRLemma}"}"'''
                originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

                searchStartIndex = wordnumberMatch.end() + len(newTitleGuts) - len(originalLanguageWord) - 5 # We've added at least that many characters
                transliterationsAdded += 1
            else: # OT
                transliteratedWord = transliterate_Hebrew( originalLanguageWord )

                wordnumberMatch = linkedHebrewWordNumberRegex.search( originalText, titleMatch.end()+4 ) # After the following href
                assert wordnumberMatch, f"{BBB} {originalText=}"
                wordNumber = int( wordnumberMatch.group(1) )
                wordRow = state.OETRefData['word_tables'][wordFileName][wordNumber]

                ref, OSHBid, rowType, morphemeRowList, strongs, cantillationHierarchy, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert = wordRow.split( '\t' )

                # Do colourisation
                if morphology.startswith( 'V' ):
                    caseClassName = 'hebrewVrb'
                # elif extendedStrongs == '37560': # Greek 'οὐ' (ou) 'not'
                #     caseClassName = 'greekNeg'
                # TODO: Need to find where collation table is imported and change 'None' to None there (and then fix this again)
                # elif morphology!='None' and morphology[4] != '.': # Two words in table have morphology of 'None' Jhn 5:27 w2
                #     caseClassName = f'''greek{GREEK_CASE_CLASS_DICT[morphology[4]]}'''
                else: caseClassName = None

                if caseClassName: # Add a clase to the anchor for the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    assert originalText[wordnumberMatch.end():].startswith( '#Top">' )
                    anchorEndIx = originalText.index( '>', wordnumberMatch.end()+5 ) # Allow for '#Top"'
                    assert originalText[anchorEndIx] == '>'
                    originalText = f'''{originalText[:anchorEndIx]} class="{caseClassName}"{originalText[anchorEndIx:]}'''
                    # print( f"    livenOETWordLinks now '{originalText[wordnumberMatch.end():]}'")
                    colourisationsAdded += 1
                    # # Old Code puts a new span inside the anchor containing the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    # wordStartIx = originalText.index( '>', wordnumberMatch.end()+5 ) + 1 # Allow for '#Top"' plus '>'
                    # wordEndIx = originalText.index( '<', wordStartIx + 1 )
                    # print( f"  livenOETWordLinks found {BBB} word '{originalText[wordStartIx:wordEndIx]}'")
                    # originalText = f'''{originalText[:wordStartIx]}<span class="case{morphology[4]}">{originalText[wordStartIx:wordEndIx]}</span>{originalText[wordEndIx:]}'''
                    # print( f"    livenOETWordLinks now '{originalText[wordnumberMatch.end():]}'")
                    # colourisationsAdded += 1

                newTitleGuts = f'''="{word}"''' # ({transliteratedWord}){'' if SRLemma==transliteratedWord else f" from {SRLemma}"}"'''
                originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

                searchStartIndex = wordnumberMatch.end() + len(newTitleGuts) - len(word) - 1 # We've added at least that many characters
                transliterationsAdded += 1

        # if NT:
        if transliterationsAdded > 0 or colourisationsAdded > 0:
            # print( f"  Now '{originalText}'")
            if transliterationsAdded > 0:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Added {transliterationsAdded:,} {bibleObject.abbreviation} {BBB} transliterations to Greek titles." )
            if colourisationsAdded > 0:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Added {colourisationsAdded:,} {bibleObject.abbreviation} {BBB} colourisations to Greek words." )
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
