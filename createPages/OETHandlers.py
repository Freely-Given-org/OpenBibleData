#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# OETHandlers.py
#
# Module handling OpenBibleData OETHandlers functions
#
# Copyright (C) 2023-2025 Robert Hunt
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

getOETTidyBBB( BBB:str, titleCase:bool|None=False, allowFourChars:bool|None=True ) -> str
getOETBookName( BBB:str ) -> str
getHebrewWordpageFilename( rowNum:int, state:State ) -> str
getGreekWordpageFilename( rowNum:int, state:State ) -> str
livenOETWordLinks( level, bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, state:State ) -> InternalBibleEntryList
findLVQuote( level:int, BBB:str, C:str, V:str, occurrenceNumber:int, originalQuote:str, state:State ) -> str (html)
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2023-08-22 Change some logging from critical to errors
    2023-10-25 Make use of word table index; add colourisation of OET words
    2023-12-15 Improve colorisation of OET words
    2024-03-13 Add getOETBookName(BBB) function
    2024-05-01 Added morphology in popups in livenOETWordLinks()
    2024-11-14 NFC normalise Hebrew title fields
    2025-01-15 Handle NT morphology fields with middle dot instead of period
    2025-09-18 Add insertChar parameter to getOETTidyBBB
"""
import logging
import re
import unicodedata

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry

sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State


LAST_MODIFIED_DATE = '2025-09-29' # by RJH
SHORT_PROGRAM_NAME = "OETHandlers"
PROGRAM_NAME = "OpenBibleData OET handler"
PROGRAM_VERSION = '0.67'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

WJ = '\u2060' # word joiner (makes Hebrew displays on console ugly and hard to read)
NARROW_NON_BREAK_SPACE = ' '


def getOETTidyBBB( BBB:str, titleCase:bool|None=False, allowFourChars:bool|None=True, insertChar:str|None=NARROW_NON_BREAK_SPACE, addNotes:bool|None=False ) -> str:
    """
    Our customised version of tidyBBB
    """
    newBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=titleCase, allowFourChars=allowFourChars, insertChar=insertChar )

    if insertChar is None: insertChar = ''
    # OT
    if newBBB == 'JNA': return '<span title="Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)">YNA</span> (JNA)' if addNotes else 'YNA'
    if newBBB == 'Jna': return '<span title="Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)">Yna</span> (Jna)' if addNotes else 'Yna'
    # NT
    if newBBB == 'JHN': return '<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (JHN)' if addNotes else 'YHN'
    if newBBB == 'Jhn': return '<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yhn</span> (Jhn)' if addNotes else 'Yhn'
    if newBBB == 'JOHN': return '<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (JHN)' if addNotes else 'YHN'
    if newBBB == 'John': return '<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yhn</span> (Jhn)' if addNotes else 'Yhn'
    if newBBB == 'JAM': return 'YAC (JAM)' if addNotes else 'YAC'
    if newBBB == 'Jam': return 'Yac (Jam)' if addNotes else 'Yac'
    if newBBB == 'ACTS': return 'ACTs'
    if newBBB == f'1{insertChar}JN': return f'1{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YN</span> (1{insertChar}JN)' if addNotes else f'1{insertChar}YN'
    if newBBB == f'2{insertChar}JN': return f'2{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YN</span> (2{insertChar}JN)' if addNotes else f'2{insertChar}YN'
    if newBBB == f'3{insertChar}JN': return f'3{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YN</span> (3{insertChar}JN)' if addNotes else f'3{insertChar}YN'
    if newBBB == f'1{insertChar}Jn': return f'1{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yn</span> (1{insertChar}Jn)' if addNotes else f'1{insertChar}Yn'
    if newBBB == f'2{insertChar}Jn': return f'2{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yn</span> (2{insertChar}Jn)' if addNotes else f'2{insertChar}Yn'
    if newBBB == f'3{insertChar}Jn': return f'3{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yn</span> (3{insertChar}Jn)' if addNotes else f'3{insertChar}Yn'
    if newBBB == f'1{insertChar}JHN': return f'1{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (1{insertChar}JHN)' if addNotes else f'1{insertChar}YHN'
    if newBBB == f'2{insertChar}JHN': return f'2{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (2{insertChar}JHN)' if addNotes else f'2{insertChar}YHN'
    if newBBB == f'3{insertChar}JHN': return f'3{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (3{insertChar}JHN)' if addNotes else f'3{insertChar}YHN'
    if newBBB == f'1{insertChar}Jhn': return f'1{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yhn</span> (1{insertChar}Yohan or 1{insertChar}Jhn)' if addNotes else f'1{insertChar}Yhn'
    if newBBB == f'2{insertChar}Jhn': return f'2{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yhn</span> (2{insertChar}Yohan or 2{insertChar}Jhn)' if addNotes else f'2{insertChar}Yhn'
    if newBBB == f'3{insertChar}Jhn': return f'3{insertChar}<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">Yhn</span> (3{insertChar}Yohan or 3{insertChar}Jhn)' if addNotes else f'3{insertChar}Yhn'
    if newBBB == 'JUDE': return '<span title="Yudas (which is closer to the Greek Ἰούδας/Youdas)">YUD</span> (JUD)' if addNotes else 'YUD'
    if newBBB == 'Jude': return '<span title="Yudas (which is closer to the Greek Ἰούδας/Youdas)">Yud</span> (Jud)' if addNotes else 'Yud'
    return newBBB
# end of Bibles.getOETTidyBBB


def getOETBookName( BBB:str ) -> str:
    """
    Handle our different spelling of well-known book names.
    """
    return ( BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)
                .replace('Joshua','Yehoshua/(Joshua)')
                .replace('‘Judges’','Heroes/(‘Judges’)')
                .replace('1 Samuel',' 1 Shemuel/(Samuel)')
                .replace('2 Samuel',' 2 Shemuel/(Samuel)')
                .replace('Job','Iyyov/(Job)')
                .replace('Psalms','Songs/(Psalms)')
                .replace('Isaiah','Yeshayah/(Isaiah)')
                .replace('Jeremiah','Yermeyah/(Jeremiah)')
                .replace('Ezekiel','Yehezkel/(Ezekiel)')
                .replace('Joel','Yoel/(Joel)')
                .replace('Amos','Amots/(Amos)')
                .replace('Obadiah','Ovadyah/(Obadiah)')
                .replace('Jonah','Yonah/(Jonah)')
                .replace('Micah','Mikah/(Micah)')
                .replace('Habakkuk','Havakkuk/(Habakkuk)')
                .replace('Zephaniah','Tsefanyah/(Zephaniah)')
                .replace('Zechariah','Zekaryah/(Zechariah)')
                .replace('Malachi','Malaki/(Malachi)')
                .replace('John','Yohan/(John)')
                .replace('James','Yacob/Jacob/(James)')
                .replace('1 John',' 1 Yohan/(John)')
                .replace('2 John',' 2 Yohan/(John)')
                .replace('3 John',' 3 Yohan/(John)')
                .replace('Jude','Yudas/(Jude)')
            )
# end of OETHandlers.getOETBookName


# Assumes spaces and final periods already removed and converted to uppercase
#    TODO: How much of this should be in BibleOrgSys ???
OET_BBB_DICT = {
                '1SAMUEL':'SA1', '2SAMUEL':'SA2',
                '1KINGS':'KI1', '2KINGS':'KI2', # However LXX calls 1&2 Samuel, 1&2 Kings
                '3KINGS':'KI1', '4KINGS':'KI2',
                '1CHRONICLES':'CH1', '2CHRONICLES':'CH2',
                'YOB':'JOB', 'SONGOFSOLOMON':'SNG',
                'YONAH':'JNA','YNA':'JNA', 'YOEL':'JOL',
                'YOCHANAN':'JHN','YHN':'JHN',
                '1CORINTHIANS':'CO1', '2CORINTHIANS':'CO2',
                '1TIMOTHY':'TI1', '2TIMOTHY':'TI2',
                '1THESSALONIANS':'TH1', '2THESSALONIANS':'TH2',
                'YAC':'JAM',
                '1PETER':'PE1', '2PETER':'PE2',
                '1YHN':'JN1', '2YHN':'JN2', '3YHN':'JN3',
                'YUD':'JDE',
                '2PS':'PS2',
                }
def getBBBFromOETBookName( originalBooknameText:str, where:str ) -> str|None:
    """
    Can return None.

    TODO: How much of this should be in BibleOrgSys ???
    """
    # Too many errors from having this function first, e.g., gives 'NAH' from 'Yonah'
    # resultBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( originalBooknameText )
    # if resultBBB and resultBBB not in ('SAM','CHR','NAH): return resultBBB
    # else: dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText() can't get valid BBB from {originalBooknameText=}" )
                                                                        
    booknameText = ( originalBooknameText
                        .replace( ' ', '' ).replace( NARROW_NON_BREAK_SPACE, '' )
                        #.rstrip( '.' ) # Remove any final period TODO: Should BibleOrgSys do that?
                        .replace( '.', '' ) # Actually, we'll get rid of any period, to handle unexpected xrefs like '2.kings' (e.g., from KJB)
                    ).upper()
    
    try: return OET_BBB_DICT[booknameText]
    except KeyError: pass

    resultBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( booknameText
                    # .replace( 'Yob', 'JOB' ).replace( 'Yochanan', 'JHN' ).replace( 'Yoel', 'JOL' ).replace( 'Yonah', 'JNA' )
                    .replace( 'Yhn', 'JHN' ).replace( 'Yud', 'JDE' )
                    # .replace( '1Yhn', 'JN1' ).replace( '2Yhn', 'JN2' ).replace( '3Yhn', 'JN3' )
                )
    if resultBBB not in BibleOrgSysGlobals.loadedBibleBooksCodes:
        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"getBBBFromOETBookName( {where} ) can't get valid BBB from {booknameText=}: {resultBBB=} from {originalBooknameText=}" )
    return resultBBB
# end of OETHandlers.getOETBookName


def getHebrewWordpageFilename( wordTableRowNum:int, state:State ) -> str:
    """
    Take a unique reference like JN2_1:3w4 and make it into a filename
            like KI2c1v3w4.htm
        although notes and segment punctuation are treated differently
            like KI2c1v3n123456.htm
    """
    ref, rowType, morphemeRowNumberOrList, _rest = state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'][wordTableRowNum].split( '\t', 3 )
    ref = ref.replace('_','c',1).replace(':','v',1) # Don't want underlines coz they're used for many other things, and colon might not be legal in filesystem

    if 'w' not in ref:
        letter = 's' if rowType=='seg' else 'n' if 'note' in rowType else None
        assert letter
        assert morphemeRowNumberOrList.isdigit()
        ref = f'{ref}{letter}{morphemeRowNumberOrList}'

    return f'{ref}.htm'
# end of createOETReferencePages.getHebrewWordpageFilename


def getGreekWordpageFilename( rowNum:int, state:State ) -> str:
    """
    Take a unique reference like JN2_1:3w4 and make it into a filename
            like JN2c1v3w4.htm
        although notes and segment punctuation are treated differently
            like JN2n1v3n123456.htm
    """
    nWordRef = state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'][rowNum].split( '\t', 1 )[0]
    result = f"{nWordRef.replace('_','c',1).replace(':','v',1)}.htm" # Don't want underlines coz they're used for many other things, and colon might not be legal in filesystem
    return result
# end of createOETReferencePages.getGreekWordpageFilename


linkedWordTitleRegex = re.compile( '="§(.+?)§"' ) # We inserted those § markers in our titleTemplate above
linkedHrefWordNumberRegex = re.compile( '="►([1-9][0-9]{0,5})◄"' )
# linkedHebrewWordNumberRegex = re.compile( '/HebWrd/([1-9][0-9]{0,5}).htm' ) # /HebWrd/ is the Hebrew words folder
# linkedGreekWordNumberRegex  = re.compile( '/GrkWrd/([1-9][0-9]{0,5}).htm' ) # /GrkWrd/ is the Greek words folder
def livenOETWordLinks( level:int, bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, state:State ) -> InternalBibleEntryList:
    """
    Livens ESFM wordlinks in the OET versions (i.e., the words with ¦ numbers suffixed to them).

    Then add the transliteration to the title="§«OrigWord»§" popup.

    NOTE: Now that we no longer use word numbers as word filenames, we have to do an extra step of post-processing
    """
    from createParallelVersePages import GREEK_CASE_CLASS_DICT

    assert 1 <= level <= 3, f"{level=}"
    assert len(bibleObject.ESFMWordTables) == 2, f"{len(bibleObject.ESFMWordTables)=}"
    for entry in givenEntryList:
        if entry.getOriginalText():
            assert '\\nd \\nd ' not in entry.getOriginalText(), f"Double nd in {bibleObject.abbreviation} {BBB} {entry=}"

    # Liven the word links using the BibleOrgSys function
    #   We use unusual word pairs in both templates (we don't actually use titleTemplate as a template)
    #       so that we can easily find them again in the returned InternalBibleEntryList
    revisedEntryList = bibleObject.livenESFMWordLinks( BBB, givenEntryList, linkTemplate='►{n}◄', titleTemplate='§«OrigWord»§' )[0]
    for revisedEntry in givenEntryList:
        if revisedEntry.getOriginalText():
            assert '\\nd \\nd ' not in revisedEntry.getOriginalText()
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

    updatedVerseList = InternalBibleEntryList()
    for n, entry in enumerate( revisedEntryList ):
        originalText = entry.getOriginalText()
        if originalText is None or '§' not in originalText:
            updatedVerseList.append( entry )
            continue
        # If we get here, we have at least one ESFM wordlink row number in the text
        # print( f"livenOETWordLinks {level=} {BBB} {n}: {originalText=}")
        searchStartIndex = 0
        transliterationsAdded = colourisationsAdded = 0
        while True:
            # Get out all the information we need
            titleMatch = linkedWordTitleRegex.search( originalText, searchStartIndex )
            if not titleMatch:
                break
            # print( f"livenOETWordLinks {BBB} word match 1='{titleMatch.group(1)}' all='{titleMatch.group(0)}'" )
            hrefMatch = linkedHrefWordNumberRegex.search( originalText, titleMatch.end() )
            if not hrefMatch:
                halt # What went wrong here
            # print( f"{titleMatch.start()=} {hrefMatch.start()=} {hrefMatch.start()-titleMatch.end()=} {hrefMatch.group(1)=} from {hrefMatch.group(0)=}" )
            assert hrefMatch.start() - titleMatch.end() == 5 # Should be immediately after href
            placeholderOriginalLanguageWord = titleMatch.group(1)
            wordNumberStr = hrefMatch.group(1)
            wordNumber = int( wordNumberStr )

            if NT:
                # Put in the correct word link
                originalText = f'''{originalText[:hrefMatch.start()]}="{'../'*level}ref/GrkWrd/{getGreekWordpageFilename(wordNumber,state)}#Top"{originalText[hrefMatch.end():]}'''
                # print( f"NT {originalText=}" )

                # transliteratedWord = transliterate_Greek( placeholderOriginalLanguageWord )

                # wordnumberMatch = linkedGreekWordNumberRegex.search( originalText, titleMatch.end()+4 ) # After the following href
                # assert wordnumberMatch, f"{BBB} {placeholderOriginalLanguageWord=} {originalText=}"
                # wordNumber = int( wordnumberMatch.group(1) )
                wordRow = state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'][wordNumber]
                # SRLemma = wordRow.split( '\t' )[2]
                _ref, greekWord, SRLemma, _GrkLemma, _VLTGlossWordsStr, _OETGlossWordsStr, _glossCaps, _probability, extendedStrongs, roleLetter, morphology, _tagsStr = wordRow.split( '\t' )
                transliteratedWord = transliterate_Greek( greekWord )

                # Do colourisation
                if roleLetter == 'V':
                    caseClassName = 'grkVrb'
                elif extendedStrongs == '37560': # Greek 'οὐ' (ou) 'not'
                    caseClassName = 'grkNeg'
                # TODO: Need to find where collation table is imported and change 'None' to None there (and then fix this again)
                elif morphology!='None' and morphology[4] != '·': # (Middle dot) Two words in table have morphology of 'None' Jhn 5:27 w2
                    caseClassName = f'''grk{GREEK_CASE_CLASS_DICT[morphology[4]]}'''
                else: caseClassName = None

                if caseClassName: # Add a clase to the anchor for the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    # assert originalText[wordnumberMatch.end():].startswith( '#Top">' )
                    anchorEndIx = originalText.index( '>', hrefMatch.end()+5 ) # Allow for '#Top"'
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

                newTitleGuts = f'''="{greekWord} ({transliteratedWord}, {morphology.removeprefix('····')}){'' if SRLemma==transliteratedWord else f" from {SRLemma}"}"'''
                originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

                searchStartIndex = hrefMatch.end()
                transliterationsAdded += 1
            else: # OT
                # Put in the correct word link
                originalText = f'''{originalText[:hrefMatch.start()]}="{'../'*level}ref/HebWrd/{getHebrewWordpageFilename(wordNumber,state)}#Top"{originalText[hrefMatch.end():]}'''
                # print( f"OT {originalText=}" )

                # transliteratedWord = transliterate_Hebrew( placeholderOriginalLanguageWord )

                # wordnumberMatch = linkedHebrewWordNumberRegex.search( originalText, titleMatch.end()+4 ) # After the following href
                # assert wordnumberMatch, f"{BBB} {originalText=}"
                # wordNumber = int( wordnumberMatch.group(1) )
                wordRow = state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'][wordNumber]

                ref, rowType, morphemeRowList, lemmaRowList, strongs, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tags = wordRow.split( '\t' )
                transliteratedWord = ','.join( [transliterate_Hebrew(part) for part in noCantillations.split(',')] ) # Need to split at commas for correct transliteration
                transliteratedWordForTitle = transliteratedWord.replace( 'ə', '~~SCHWA~~' ) # Protect it so not adjusted in the title field

                # Do colourisation
                # NOTE: We have almost identical code in brightenUHB() in createParallelVersePages.py
                caseClassName = None
                for subMorph in morphology.split( ',' ):
                    if subMorph.startswith( 'V' ):
                        caseClassName = 'hebVrb'
                        break
                for subStrong in strongs.split( ',' ):
                    try: subStrongInt = getLeadingInt( subStrong ) # Ignores suffixes like a,b,c
                    except ValueError: continue
                    if subStrongInt in (369, 3808): # Hebrew 'אַיִן' 'ayin' 'no', or 'לֹא' (lo) 'not'
                        caseClassName = 'hebNeg'
                        break
                    if subStrongInt in (430,410,433): # Hebrew 'אֱלֹהִים' 'ʼelohīm', 'אֵל' 'El'
                        caseClassName = 'hebEl'
                        break
                    if subStrongInt in (3068,3050): # Hebrew 'יְהוָה' 'Yahweh', 'יָהּ' 'Yah'
                        caseClassName = 'hebYhwh'
                        break
                # TODO: Need to find where collation table is imported and change 'None' to None there (and then fix this again)
                # elif morphology!='None' and morphology[4] != '.': # Two words in table have morphology of 'None' Jhn 5:27 w2
                #     caseClassName = f'''heb{HEBREW_CASE_CLASS_DICT[morphology[4]]}'''

                if caseClassName: # Add a clase to the anchor for the English word
                    # print( f"    livenOETWordLinks {originalText[wordnumberMatch.end():]=}")
                    # assert originalText[wordnumberMatch.end():].startswith( '#Top">' )
                    anchorEndIx = originalText.index( '>', hrefMatch.end()+5 ) # Allow for '#Top"'
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

                # print( f"livenOETWordLinks ({len(noCantillations)}) {noCantillations=} NFC={unicodedata.is_normalized('NFC',noCantillations)} NFKC={unicodedata.is_normalized('NFKC',noCantillations)} NFD={unicodedata.is_normalized('NFD',noCantillations)} NFKD={unicodedata.is_normalized('NFKD',noCantillations)}")
                # noCantillations = unicodedata.normalize( 'NFC', noCantillations )
                # print( f"                  ({len(noCantillations)}) {noCantillations=} NFC={unicodedata.is_normalized('NFC',noCantillations)} NFKC={unicodedata.is_normalized('NFKC',noCantillations)} NFD={unicodedata.is_normalized('NFD',noCantillations)} NFKD={unicodedata.is_normalized('NFKD',noCantillations)}")
                newTitleGuts = f'''="{unicodedata.normalize('NFC',noCantillations)} ({transliteratedWordForTitle}, {morphology})"''' # ({transliteratedWord}){'' if SRLemma==transliteratedWord else f" from {SRLemma}"}"'''
                originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

                searchStartIndex = hrefMatch.end()
                transliterationsAdded += 1

        if transliterationsAdded > 0 or colourisationsAdded > 0:
            # print( f"  Now '{originalText}'")
            if transliterationsAdded > 0:
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Added {transliterationsAdded:,} {bibleObject.abbreviation} {BBB} transliterations to Greek titles." )
            if colourisationsAdded > 0:
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Added {colourisationsAdded:,} {bibleObject.abbreviation} {BBB} colourisations to Greek words." )
            # adjText, cleanText, extras = _processLineFix( self, C:str,V:str, originalMarker:str, text:str, fixErrors:list[str] )
            # newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras(), originalText )
            # Since we messed up many of the fields, set them to blank/null entries so that the old/wrong/outdated values can't be accidentally used
            newEntry = InternalBibleEntry( entry.getMarker(), entry.getOriginalMarker(), '', '', None, originalText )
            updatedVerseList.append( newEntry )
        else:
            logging.critical( f"ESFMBible.livenESFMWordLinks unable to find wordlink title in '{originalText}'" )
            updatedVerseList.append( entry )
            halt

    for updatedEntry in updatedVerseList:
        if updatedEntry.getOriginalText():
            assert '\\nd \\nd ' not in updatedEntry.getOriginalText()
    return updatedVerseList
# end of OETHandlers.livenOETWordLinks function


def findLVQuote( level:int, BBB:str, C:str, V:str, occurrenceNumber:int, originalQuote:str, state:State ) -> str: # html
    """
    Given an original language (Heb/Grk) quote,
        find the OET-LV English words that match the OL words.

    Note that the original quote might have an & in it for non-consecutive quote portions.

    Note also that the SR-GNT might have ˚ nomina sacra marks in it, e.g., ˚Ἰησοῦ ˚Χριστοῦ, Υἱοῦ ˚Θεοῦ
    """
    from html import checkHtml

    # DEBUGGING_THIS_MODULE = 99
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {BBB} {C}:{V}, {occurrenceNumber=} {originalQuote=}, … )")
    ref = f'{BBB}_{C}:{V}'
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level=}, {ref}, {occurrenceNumber=} {originalQuote=}, … )")
    currentOccurrenceNumber = occurrenceNumber

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    wordFileName = 'OET-LV_NT_word_table.tsv' if NT else 'OET-LV_OT_word_table.tsv'

    try:
        lvVerseEntryList, _lvContextList = state.preloadedBibles['OET-LV'].getContextVerseData( (BBB, C, V) )
    except (KeyError, TypeError): # TypeError is if None is returned
        logger = logging.error if BBB in state.booksToLoad['OET-LV'] else logging.warning
        logger( f"findLVQuote: OET-LV has no text for {ref}")
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
        firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][ref]
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
                                    .replace( '(', '' ).replace( ')', '' )
        adjustedOriginalQuote = adjustedOriginalQuote.removesuffix( ' & ') # Rev 15:4 after final ? is removed above
        if not NT: adjustedOriginalQuote = ( adjustedOriginalQuote.replace( WJ, ',' ) # We use commas to separate Hebrew morphemes instead of word joiners
                                            .replace( '־', ' ' ) # And we separate words by maqqaf
                                            .replace( '׀', '' ).replace( '  ', ' ' ) )
        adjustedOriginalQuote = adjustedOriginalQuote.replace( '   ', ' ' ).replace( '  ', ' ' ).strip() # Cleans up and copes with uW having multiple spaces
        #     import unicodedata
        #     for char in adjustedOriginalQuote:
        #         if char not in ' &’' and 'GREEK' not in unicodedata.name(char):
        #             print( f"findLVQuote: uW UTN has unexpected char {BBB} {C}:{V} '{char}' ({unicodedata.name(char)}) from '{adjustedOriginalQuote}' from '{originalQuote}'" )
        #             halt
        olWords = adjustedOriginalQuote.split( ' ' )
        assert '' not in olWords, f"findLVQuote: uW UTN has unexpected empty string {ref} {olWords=} from '{adjustedOriginalQuote}' from '{originalQuote}'"
        olIndex = wordNumberOffset = 0
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
                    logging.critical( f"findLVQuote: uW UTN has ampersand at beginning {ref} '{originalQuote}'" )
                elif olIndex == len(olWords):
                    logging.critical( f"findLVQuote: uW UTN has ampersand at end {ref} '{originalQuote}'" )
                    break # finished
                inGap = True
                continue # Pass over whatever this SR row was (i.e., sort of match the ampersand)

            rowStr = wordTable[wordNumber+wordNumberOffset]
            # if not rowStr.startswith( f'{BBB}_{C}:{V}w' ): # gone into the next verse
            #     break
            row = rowStr.split( '\t' )
            if not NT:
                while row[1]=='seg' or 'note' in row[1]: #('־','׃'): # maqqaf
                    # print( f"<<< {wordNumber+wordNumberOffset}: {row[0]} Skip Hebrew {row[1]} >>>" )
                    wordNumberOffset += 1
                    if wordNumber+wordNumberOffset > lastWordNumber:
                        break
                    rowStr = wordTable[wordNumber+wordNumberOffset]
                    row = rowStr.split( '\t' )
            if wordNumber+wordNumberOffset > lastWordNumber:
                break
            assert rowStr.startswith( f'{ref}w' ), f"{ref} {rowStr=}"

            if NT:
                #  0    1          2        3           4              5              6          7            8           9     10          11
                # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
                # assert rowStr.startswith( f'{ref}w' ), f"{ref} {rowStr=}"
                if not row[7]: # This Greek word is not in the GNT text
                    continue
                assert int(row[7]), f"{ref} {row=}"

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
                #  0    1        2             3        4           5     6                7                8                          9          10                   11                   12                13          14           15    16       17
                # 'Ref\tRowType\tLemmaRowList\tStrongs\tMorphology\tWord\tNoCantillations\tMorphemeGlosses\tContextualMorphemeGlosses\tWordGloss\tContextualWordGloss\tGlossCapitalisation\tGlossPunctuation\tGlossOrder\tGlossInsert\tRole\tNesting\tTags'
                # assert rowStr.startswith( ref ), f"{ref} {rowStr=}" # without the 'w' because segs and notes don't have word numbers
                # print( f"{ref} {wordNumber=}+{wordNumberOffset}={wordNumber+wordNumberOffset}/{lastWordNumber} {row[6]=} vs {olWord=} {olIndex=}")
                if row[6] == olWord: # we have a Hebrew word match
                    # print( "  Matched" )
                    if currentOccurrenceNumber > 0:
                        assert olIndex == 0
                        currentOccurrenceNumber -= 1
                    if currentOccurrenceNumber == 0: # We can start matching up now
                        gloss = row[10] if row[10] else row[9] if row[9] else row[8] if row[8] else row[7]
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
                    # print( "  Didn't match!" )
                    olIndex = 0 # We started a match and then failed -- back to the beginning
                    matchStart = None

        if olIndex < len(olWords): # We didn't match them all
            ourWords = []
            for wordNumber in range( firstWordNumber, firstWordNumber+999 ):
                if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                    break
                rowStr = wordTable[wordNumber]
                if not rowStr.startswith( f'{ref}' ): # gone into the next verse
                    break
                row = rowStr.split( '\t' )
                if NT:
                    if not row[7]: # probability: This Greek word is not in the GNT text
                        continue
                    assert int(row[7]), f"{row=}"
                    if matchStart == -wordNumber:
                        matchStart = len(ourWords) # Convert to index of these words
                    ourWords.append( row[1] )
                else: # OT
                    if matchStart == -wordNumber:
                        matchStart = len(ourWords) # Convert to index of these words
                    gloss = row[10] if row[10] else row[9] if row[9] else row[8] if row[8] else row[7]
                    if not gloss:
                        logging.error( f"No available gloss2 for Hebrew {row}" )
                    # assert gloss, f"{BBB} {C}:{V} {row=}"
                    ourWords.append( gloss )
            lvEnglishWords.append( f'''(Some words not found in {'<a href="#SR-GNT">SR-GNT</a>' if NT else '<a href="#UHB">UHB</a>'}: {' '.join( ourWords )})''' )
            logging.warning( f"findLVQuote unable to match {ref} '{originalQuote}' {occurrenceNumber=} {currentOccurrenceNumber=} {inGap=}\n  {olWords=}  {olIndex=}\n  {ourWords=} {matchStart=}" )
            # if BBB not in ('MRK',) or C not in ('1',) or V not in ('5','8','14'):
            # halt

        assembledHtml = ' '.join(lvEnglishWords)
        # assert checkHtml( f'LV {BBB} {C}:{V}', html, segmentOnly=True )
        if not NT:
            assembledHtml = ( assembledHtml
                                # Not totally sure where/why some of these have an underline after the ESFM marker where a space is expected
                                .replace( '\\untr_', '<span class="untr">').replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>')
                                .replace( '\\nd_', '<span class="nd">').replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>')
                            )
        assert checkHtml( 'LVQuote', assembledHtml, segmentOnly=True )
        return assembledHtml
    else:
        logging.error( f"findLVQuote: OET-LV can't find a starting word number for {ref}")
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
