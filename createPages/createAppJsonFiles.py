#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# createAppJsonFiles.py
#
# Module handling OpenBibleData createAppJsonFiles functions for Bibleside app
#
# Copyright (C) 2026 Robert Hunt
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
Module handling createAppJsonFiles functions
    that create JSON word files to be accessible by the Bibleside app.

createAppJsonFiles( level:int, outputFolderPath:Path, state:State ) -> bool
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
"""
from pathlib import Path
import os
from collections import defaultdict
import re
import json
import logging
from time import time
import multiprocessing, copy
from functools import cache

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27, BOOKLIST_66
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
from BibleOrgSys.OriginalLanguages import Hebrew, BibleLexicon
from bible_organisational_system import getPositiveLeadingInt
import bos_books_codes_py

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State, state, CNTR_BOOK_ID_MAP
from OETHandlers import getOETTidyBBB, getOETBookName, getHebrewWordpageFilename, getGreekWordpageFilename, livenOETWordLinks
from createSectionPages import findSectionNumber
from createOETReferencePages import HebrewWordFileName, convert_Hebrew_word_gloss_spans, tidy_Hebrew_morphology, \
                    GLOSS_TYPE_STRING_DICT,\
                GreekWordFileName, formatNTContextSpansOETGlossWords, \
                    CNTR_ROLE_NAME_DICT, CNTR_MOOD_NAME_DICT, CNTR_TENSE_NAME_DICT, CNTR_VOICE_NAME_DICT, CNTR_PERSON_NAME_DICT, \
                    CNTR_CASE_NAME_DICT, CNTR_GENDER_NAME_DICT, CNTR_NUMBER_NAME_DICT


LAST_MODIFIED_DATE = '2026-04-26' # by RJH
SHORT_PROGRAM_NAME = "createAppJsonFiles"
PROGRAM_NAME = "OpenBibleData createAppJsonFiles functions"
PROGRAM_VERSION = '0.12'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# project_folderpath = Path(__file__).parent.parent # Find folders relative to this module
# FG_folderpath = project_folderpath.parent # Path to find parallel Freely-Given.org repos
# THEOGRAPHIC_INPUT_FOLDER_PATH = FG_folderpath.joinpath( 'Bible_speaker_identification/outsideSources/TheographicBibleData/derivedFiles/' )

NARROW_NON_BREAK_SPACE = ' '


def createAppJsonFiles( level:int, outputFolderPath:Path, state:State ) -> bool:
    """
    Make pages for all the words and lemmas to link to.

    Sadly, there's almost identical code in make_table_pages() in OET convert_OET-LV_to_simple_HTML.py
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createAppJsonFiles( {level}, {outputFolderPath}, {state.BibleVersions} )" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if state.TEST_MODE_FLAG else ''}reference json word files for OET…" )

    startTime = time()
    create_Hebrew_words_json( level+1, outputFolderPath.joinpath( 'HebWrd/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Hebrew_words_json() took {(time()-startTime)/60:.1f} minutes.")
    startTime = time()
    create_Greek_words_json( level+1, outputFolderPath.joinpath( 'GrkWrd/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Greek_words_json() took {(time()-startTime)/60:.1f} minutes.")

    # bibleLexicon = BibleLexicon.BibleLexicon()
    # create_Hebrew_Strongs_pages( level+1, outputFolderPath.joinpath( 'HebStrng/' ), bibleLexicon, state )
    # del state.OETRefData['OTStrongsRefs']
    # create_Greek_Strongs_pages( level+1, outputFolderPath.joinpath( 'GrkStrng/' ), bibleLexicon, state )
    # del state.OETRefData['NTStrongsRefs']

    del state.OETRefData # No longer needed
    return True
# end of createAppJsonFiles.createAppJsonFiles



used_word_filenames = []
def create_Hebrew_words_json( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Hebrew_words_json( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Checking/Making {len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,} Hebrew json files…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    # Now make a page for each Hebrew word (including the note pages)
    numWordPagesMade = 0
    wordLinksForIndex:list[str] = [] # Used below to make an index page
    for hh, columns_string in enumerate( state.OETRefData['word_tables'][HebrewWordFileName][1:], start=1 ):
        if not columns_string: continue # a blank line (esp. at end)
        if numWordPagesMade>0 and hh % 50_000 == 0:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      {numWordPagesMade+1:,} made out of {f'{hh:,} out of ' if hh!=numWordPagesMade+1 else ''}{len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,}…" )
        # output_filename = getHebrewWordpageFilename( hh, state )
        output_filename = f'{hh}.json'
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: # NOTE: This makes the function MUCH slower
            # Check that we're not creating any duplicate filenames (that will then be overwritten)
            assert output_filename not in used_word_filenames, f"Hebrew {hh} {output_filename}"
            used_word_filenames.append( output_filename )
        ref, rowType, _morphemeRowList, _lemmaRowList, _strongs, _morphology, word, noCantillations, _morphemeGlosses, _contextualMorphemeGlosses, _wordGloss, _contextualWordGloss, _glossCapitalisation, _glossPunctuation, _glossOrder, _glossInsert, _role, _nesting, _tags = columns_string.split( '\t' )
        BBB, _CVW = ref.split( '_', 1 )
        if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST:
            continue # In some test modes, we only make the relevant json files
        hebrewWord = (noCantillations.replace( ',', '' ) # Remove morpheme breaks
                        if noCantillations else word ) # Segs and notes have nothing in the noCantillations field
        if create_Hebrew_word_json( level, hh, hebrewWord, columns_string, outputFolderPath, output_filename, state ):
            if rowType!='seg' and 'note' not in rowType:
                wordLinksForIndex.append( f'<a href="{output_filename}">{hebrewWord}</a>')
            numWordPagesMade += 1

    # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {numWordPagesMade:,}{f"/{len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,}" if numWordPagesMade < len(state.OETRefData['word_tables'][HebrewWordFileName])-1 else ''} Hebrew json word files (using {len(state.OETRefData['usedHebLemmasSet']):,} Hebrew lemmas).''' )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {numWordPagesMade:,}{f"/{len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,}" if numWordPagesMade < len(state.OETRefData['word_tables'][HebrewWordFileName])-1 else ''} Hebrew json word files.''' )

#     # Create index page for this folder
#     filepath = outputFolderPath.joinpath( 'index.htm' )
#     top = makeTop( level, None, 'wordIndex', None, state ) \
#             .replace( '__TITLE__', f"Hebrew Words Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Hebrew, words' )
#     indexText = ' '.join( wordLinksForIndex )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><span class="selectedBook">Hebrew words index</span> <a href="transIndex.htm">Transliterated Hebrew words index</a></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
# <p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics</a></p>
# <h1 id="Top">Hebrew Words Index ({len(wordLinksForIndex):,})</h1>
# <p class="note">{indexText}</p>
# {makeBottom( level, None, 'wordIndex', state )}'''
#     assert checkHtml( 'wordIndex', indexHtml )
#     assert not filepath.is_file() # Check that we're not overwriting anything
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

#     # Create transliterated index page for this folder
#     filepath = outputFolderPath.joinpath( 'transIndex.htm' )
#     top = makeTop( level, None, 'wordIndex', None, state ) \
#             .replace( '__TITLE__', f"Transliterated Hebrew Words Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Hebrew, words, transliterated' )
#     indexText = transliterate_Hebrew( indexText )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><a href="index.htm">Hebrew words index</a> <span class="selectedBook">Transliterated Hebrew words index</span></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
# <p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics</a></p>
# <h1 id="Top">Transliterated Hebrew Words Index ({len(wordLinksForIndex):,})</h1>
# <p class="note">{indexText}</p>
# {makeBottom( level, None, 'wordIndex', state )}'''
#     assert checkHtml( 'wordIndex', indexHtml )
#     assert not filepath.is_file() # Check that we're not overwriting anything
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createAppJsonFiles.create_Hebrew_words_json


def create_Hebrew_word_json( level:int, hh:int, hebrewWord:str, columns_string:str, outputFolderPath:Path, word_output_filename:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Hebrew_word_json( {level}, {hh}, {hebrewWord}, ..., {word_output_filename} ... )" )
    dPrint( 'Normal' if BibleOrgSysGlobals.alreadyMultiprocessing else 'Verbose', DEBUGGING_THIS_MODULE, f"Word {hh}: {columns_string}" )
    assert hebrewWord
    # print( f"create_Hebrew_word_json( ..., {hh}, {hebrewWord}, ..., {word_output_filename} ... )" )

    usedRoleLetters, usedMorphologies = set(), set()
    # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{word_output_filename}'" )
    ref, rowType, morphemeRowList, lemmaRowList, strongs, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tagsStr = columns_string.split( '\t' )

    BBB, CVW = ref.split( '_', 1 )
    assert not state.TEST_MODE_FLAG or state.ALL_TEST_REFERENCE_PAGES_FLAG or BBB in state.TEST_BOOK_LIST
    # if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST:
    #     return False # In some test modes, we only make the relevant json files
    C, VW = CVW.split( ':', 1 )
    V, W = VW.split( 'w', 1 ) if 'w' in VW else (VW, '') # Segs and Notes don't have word numbers
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    OSISbookCode = bos_books_codes_py.get_osis_abbreviation_py( BBB )

    jsonDict = { 'word_number':hh, 'book_abbreviation':ourTidyBbbWithNotes, 'ref':ref,
                'entry_type':rowType, 'morpheme_row_list':morphemeRowList, 'lemma_row_list':lemmaRowList,
                'actual_word':word, 'Hebrew_word_without_accents':noCantillations,
                'morpheme_glosses':morphemeGlosses, 'contextual_morpheme_glosses':contextualMorphemeGlosses,
                'word_gloss':wordGloss, 'contextual_word_gloss':contextualWordGloss,
                'gloss_caps':glossCapitalisation, 'gloss_punctuation':glossPunctuation,
                'Strongs':strongs,
                'morphology_code':morphology }

    isMultipleLemmas = ',' in lemmaRowList
    # print( f"{ref} '{rowType}' ({lemmaRowList}) got '{word}' ({noCantillations}) morphology='{morphology}'" )
    wordGloss = wordGloss.replace( '=', '_' )
    # NOTE: segs don't have glosses, plus some glosses might be missing
    gloss = contextualWordGloss if contextualWordGloss else wordGloss if wordGloss else contextualMorphemeGlosses if contextualMorphemeGlosses else morphemeGlosses
    chosenGlossType = 'cWG' if contextualWordGloss else 'wG' if wordGloss else 'cMGs' if contextualMorphemeGlosses else 'mGs'
    gloss = convert_Hebrew_word_gloss_spans( gloss.replace(',',', ').replace('</','PRoTecT').replace('/', ' / ').replace('PRoTecT', '</') ) # looks much nicer
    # NOT TRUE assert rowType in ('seg',) or gloss, f"{ref=} {rowType=} {morphemeRowList=} {lemmaRowList=} {strongs=} {morphology=} {word=} {noCantillations=} {morphemeGlosses=} {contextualMorphemeGlosses=} {wordGloss=} {contextualWordGloss=} {glossCapitalisation=} {glossPunctuation=} {glossOrder=} {glossInsert=} {role=} {nesting=} {tags=}"
    if isMultipleLemmas:
        if contextualMorphemeGlosses:
            mainGlossWord = sorted(contextualMorphemeGlosses.replace('/',',').split( ',' ), key=len)[-1]
            # print( f"{ref} {mainGlossWord=} fromA {contextualMorphemeGlosses}" )
        elif morphemeGlosses:
            mainGlossWord = sorted(morphemeGlosses.replace('/',',').split( ',' ), key=len)[-1]
            # print( f"{ref} {mainGlossWord=} fromB {morphemeGlosses}" )
        else: mainGlossWord = gloss
    else: mainGlossWord = gloss

    tidyMorphologyFields = translationFields = capsField = ''
    if rowType!='seg' and 'note' not in rowType:
        # it's a proper Hebrew (or Aramaic) word
        assert morphemeRowList.count(',') == strongs.count(',') == morphology.count(',') == word.count(',') == noCantillations.count(',')
        tidyMorphologyFields = tidy_Hebrew_morphology( rowType, morphology )
        jsonDict['tidy_morphology_html'] = tidyMorphologyFields
        if gloss:
            translationFields = f'''{GLOSS_TYPE_STRING_DICT[chosenGlossType]}=‘<b>{gloss[0].upper() if glossCapitalisation=='S' else gloss[0]}{gloss[1:]}</b>’'''
            for extraGlossType,extraGlossString in (('cWG',contextualWordGloss),('wG',wordGloss),('cMGs',contextualMorphemeGlosses),('mGs',morphemeGlosses)):
                if extraGlossType != chosenGlossType and extraGlossString:
                    extraGlossTypeString = 'possible word glosses' if extraGlossType=='wG' and '/' in extraGlossString \
                                                            else GLOSS_TYPE_STRING_DICT[extraGlossType]
                    extraGlossString = convert_Hebrew_word_gloss_spans( extraGlossString.replace(',',', ').replace('</','PRoTecT').replace('/', ' / ').replace('PRoTecT', '</') ) # looks much nicer
                    translationFields = f'''{translationFields} {extraGlossTypeString}=‘<b>{extraGlossString[0].upper() if glossCapitalisation=='S' else extraGlossString[0]}{extraGlossString[1:]}</b>’'''
            # translationFields = translationFields
        else:
            translationFields = '<small>Oops, <a href="https://GitHub.com/Clear-Bible/macula-hebrew/issues/121">no gloss available</a>!</small>'
            logging.error( f"create_Hebrew_word_json: {ref} {rowType} No gloss available for '{word}'" )
            # print( f"create_Hebrew_words_json: {ref} {rowType=} No gloss available for {word=} {role=}" )
            # print( f"  {morphemeGlosses=} {contextualMorphemeGlosses=} {wordGloss=} {contextualWordGloss=}")
            gloss = '???'
        jsonDict['translation_html'] = translationFields
        if glossCapitalisation:
            capsField = f' <small>(Caps={glossCapitalisation})</small>'

    transliterationBit = f" ({transliterate_Hebrew(noCantillations.replace(',',', '))})" if noCantillations else ''

    strongsLinks = ''
    for originalStrongsBit in strongs.split( ',' ):
        possibleStrongsNumber = originalStrongsBit
        if ' ' in possibleStrongsNumber:
            if possibleStrongsNumber[-2] == ' ' and possibleStrongsNumber[-1] in 'abcdef':
                possibleStrongsNumber = possibleStrongsNumber[:-2] # Remove suffix
            else:
                logging.critical( f"create_Hebrew_word_json {BBB} {C}:{V}w{W} {gloss=} {possibleStrongsNumber=} from {strongs=}" )
        if possibleStrongsNumber.isdigit():
            # strongsLinks = f'''{strongsLinks}{', ' if strongsLinks else ''}<a title="Goes to Strongs dictionary" href="https://BibleHub.com/hebrew/{possibleStrongsNumber}.htm">{originalStrongsBit}</a>'''
            strongsLinks = f'''{strongsLinks}{', ' if strongsLinks else ''}<a title="Goes to Strongs dictionary" href="{'../'*level}ref/HebStrng/H{possibleStrongsNumber}.htm#Top">{originalStrongsBit}</a>'''
        elif possibleStrongsNumber: # things like c, m, or b
            strongsLinks = f'''{strongsLinks}{', ' if strongsLinks else ''}{originalStrongsBit}'''
    StrongsBit = f' Strongs={strongsLinks}' if strongsLinks else ''

    # Add pointers to people, locations, etc.
    semanticExtras = ''
    if tagsStr:
        for semanticTag in tagsStr.split( ';' ):
            tagPrefix, tag = semanticTag[0], semanticTag[1:]
            # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
            if tagPrefix == 'P':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../Per/{tag}.htm#Top">{tag}</a>'''
            elif tagPrefix == 'L':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../Loc/{tag}.htm#Top">{tag}</a>'''
            elif tagPrefix == 'Y':
                year = tag
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Year={year}{' AD' if int(year)>0 else ''}'''
            elif tagPrefix == 'T':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}TimeSeries={tag}'''
            elif tagPrefix == 'E':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Event={tag}'''
            elif tagPrefix == 'G':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Group={tag}'''
            elif tagPrefix == 'F':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Referred to from <a title="Go to referent word" href="{tag}.htm#Top">Word #{tag}</a>'''
            elif tagPrefix == 'R':
                semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Refers to <a title="Go to referred word" href="{tag}.htm#Top">Word #{tag}</a>'''
            else:
                logging.critical( f"Unknown '{tagPrefix}' word tag in {n}: {columns_string}")
                unknownTag
    if semanticExtras:
        jsonDict['semantic_extras'] = semanticExtras
    
    lemmaLinksList = []
    for lemmaRowNumberStr in lemmaRowList.split( ',' ):
        # print( f"{lemmaRowNumberStr=}" )
        try: lemmaRowNumber = int(lemmaRowNumberStr)
        except ValueError: continue # could be empty string or '<<<MISSING>>>'
        lemmaHebrew = state.OETRefData['OTHebLemmaList'][lemmaRowNumber]
        lemmaTrans = state.OETRefData['OTTransLemmaList'][lemmaRowNumber]
        lemmaLinksList.append( f'<a title="View Hebrew lemma" href="../HebLem/{lemmaTrans}.htm#Top">‘{lemmaHebrew}’</a>' )
    lemmaLinksStr = ( f'''Lemmas=<b>{', '.join(lemmaLinksList)}</b>''' if isMultipleLemmas else f'Lemma=<b>{lemmaLinksList[0]}</b>' ) if lemmaLinksList else ''
    # print( f"{len(state.OETRefData['OTLemmaOETGlossesDict'])=} {noCantillations=} {state.OETRefData['OTLemmaOETGlossesDict'][noCantillations]=}")
    lemmaGlossesList = sorted( state.OETRefData['OTLemmaOETGlossesDict'][noCantillations] )
    try: lemmaGlossesList.remove( '' ) # TODO: Check how this gets in there
    except ValueError: pass
    # print( f"{len(lemmaGlossesList)=}"); halt
    wordOETGlossesList = sorted( state.OETRefData['OTFormOETGlossesDict'][(hebrewWord,morphology)] )
    # wordVLTGlossesList = sorted( state.OETRefData['OTFormVLTGlossesDict'][(hebrewWord,morphology)] )

#     # Make the navigation links for the top of the page
#     prevN = nextN = None
#     if hh > 1:
#         if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
#             for nN in range( hh-1, 0, -1 ):
#                 nWordRef = state.OETRefData['word_tables'][HebrewWordFileName][nN].split( '\t', 1 )[0]
#                 nBBB = nWordRef.split( '_', 1 )[0]
#                 if nBBB in state.TEST_BOOK_LIST:
#                     prevN = nN
#                     break
#         else: prevN = hh-1
#     if hh<len(state.OETRefData['word_tables'][HebrewWordFileName])-1:
#         if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
#             for nN in range( hh+1, len(state.OETRefData['word_tables'][HebrewWordFileName]) ):
#                 nWordRef = state.OETRefData['word_tables'][HebrewWordFileName][nN].split( '\t', 1 )[0]
#                 nBBB = nWordRef.split( '_', 1 )[0]
#                 if nBBB in state.TEST_BOOK_LIST:
#                     nextN = nN
#                     break
#         else: nextN = hh+1
#     prevLink = f'<b><a title="Previous word" href="{getHebrewWordpageFilename(prevN,state)}#Top">←</a></b> ' if prevN is not None else ''
#     nextLink = f' <b><a title="Next word" href="{getHebrewWordpageFilename(nextN,state)}#Top">→</a></b>' if nextN else ''
#     oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbbWithNotes}{NARROW_NON_BREAK_SPACE}{C}</a>'''
#     parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
#     interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}ilr/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
#     rowTypeField = '‘Ketiv’ (marginal note on original)' if rowType=='K' else 'Aramaic ‘ketiv’ (marginal note on original)' if rowType=='AK' else 'Segment punctuation' if rowType=='seg' else 'Aramaic' if rowType=='A' else rowType.title() if 'note' in rowType else rowType
#     hebrewWordTitle = rowTypeField if rowType=='seg' or 'note' in rowType else hebrewWord # f'{hebrewWord}\u202d' # unicode LRO
#     buttonBar = '' if rowType=='seg' or 'note' in rowType else f'\n<p class="btnBar"><button type="button" id="wordsButton" title="Hide/Show word lines" onclick="hide_show_words()">Hide words</button> <button type="button" id="versesButton" title="Hide/Show verse lines" onclick="hide_show_verses()">Hide verses</button> <button type="button" id="coloursButton" title="Hide/Show verse colours" onclick="hide_show_colours()">Hide verse colours</button></p>'

#     word_output_filenames = {'words':f'words/{word_output_filename}', 'verses':f'verses/{word_output_filename}','both':f'both/{word_output_filename}' }
#     wordsHtml = f'''<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Hebrew wordlink #{hh}</h1>{f"{NEWLINE}<h2>{rowTypeField}</h2>" if rowTypeField else ''}
# <p class="pgNav">{prevLink}<b>{hebrewWordTitle}</b> <a title="Go to Hebrew word index" href="index.htm">↑</a>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>{buttonBar}
# <p class="link"><a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={OSISbookCode}&c={C}&v={V}">OSHB {ourTidyBbbWithNotes} {C}:{V}</a> <b>{hebrewWord}</b>{transliterationBit}{StrongsBit} {lemmaLinksStr}
# <br> {translationFields}{capsField if state.TEST_MODE_FLAG else ''}
# <br> {tidyMorphologyFields}{f'{NEWLINE}<br>  {semanticExtras}' if semanticExtras else ''}</p>
# <p class="note"><small>Note: These json files enable you to click through to the <a href="https://hb.OpenScriptures.org">Open Scriptures Hebrew Bible</a> (OSHB) that the <em>Open English Translation</em> Old Testament is translated from.
# The OSHB is based on the <a href="https://www.Tanach.us/Tanach.xml">Westminster Leningrad Codex</a> (WLC).
# (We are still searching for a digitized facsimile of the Leningradensis manuscript that we can easily link to. See <a href="https://www.AnimatedHebrew.com/mss/index.html#leningrad">this list</a> and <a href="https://archive.org/details/Leningrad_Codex/">this archive</a> for now.)
# This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>'''
#     assert '\\' not in wordsHtml, f"{wordsHtml=}"
#     assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"

#     if rowType!='seg' and 'note' not in rowType:
#         other_count = 0
#         thisWordNumberList = state.OETRefData['OTFormUsageDict'][(hebrewWord,morphology)]
#         if len(wordOETGlossesList)>1:
#             wordGlossesStr = convert_Hebrew_word_gloss_spans( "</b>’, ‘<b>".join(wordOETGlossesList) )
#             assert '\\' not in wordGlossesStr
#         if len(thisWordNumberList) > 100: # too many to list
#             maxWordsToShow = 50
#             wordsHtml = f'{wordsHtml}\n<h2>Showing the first {maxWordsToShow} out of {len(thisWordNumberList)-1:,} uses of identical word form {hebrewWord} <small>({tidyMorphologyFields})</small> in the Hebrew originals</h2>'
#             if len(wordOETGlossesList)>1:
#                 wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyFields})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordGlossesStr}</b>’.</p>'''
#                 # if wordVLTGlossesList != wordOETGlossesList:
#                 #     wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
#             else:
#                 # assert wordOETGlossesList == [gloss], f"{wordOETGlossesList}  vs {[gloss]}"
#                 # if not gloss: print( f"NO GLOSS {ref=} {rowType=} {morphemeRowList=} {lemmaRowList=} {strongs=} {morphology=} {word=} {noCantillations=} {morphemeGlosses=} {contextualMorphemeGlosses=} {wordGloss=} {contextualWordGloss=} {glossCapitalisation=} {glossPunctuation=} {glossOrder=} {glossInsert=} {role=} {nesting=} {tags=}" )
#                 wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyFields})</small> is always and only glossed as ‘<b>{gloss}</b>’.</p>'
#                 # if VLTGlossWordsStr != gloss:
#                 #     wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> was always and only glossed as ‘<b>{VLTGlossWordsStr}</b>’)</small>.</p>'
#         else: # we can list all uses of the word
#             maxWordsToShow = 100
#             if len(thisWordNumberList) == 1:
#                 wordsHtml = f'{wordsHtml}\n<h2>Only use of identical word form ‘{hebrewWord}’ <small>({tidyMorphologyFields})</small> in the Hebrew originals</h2>'
#                 # hebLemmaWordRowsList = state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]
#                 # lemmaFormsList = sorted( state.OETRefData['OTLemmaFormsDict'][noCantillations] )
#                 # if len(hebLemmaWordRowsList) == 1:
#                 #     # print( f"{ref} '{hebrew}' ({glossWords}) {noCantillations=} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}" )
#                 #     assert len(lemmaFormsList) == 1
#                 #     assert len(morphemeGlossesList) == 1
#                 #     html = f'''{html.replace(morphemeLink, f'{morphemeLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Hebrew originals.</p>'''
#             elif len(thisWordNumberList) > 1:
#                 wordsHtml = f'{wordsHtml}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {hebrewWord} <small>({tidyMorphologyFields})</small> in the Hebrew originals</h2>'
#             if len(wordOETGlossesList)>1:
#                 wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyFields})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordGlossesStr}</b>’.</p>'''
#                 # if wordVLTGlossesList != wordOETGlossesList:
#                 #     wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
#             else:
#                 # assert wordOETGlossesList == [gloss], f"{n} {BBB} {C}:{V} {hebrewWord=} {morphology=}: {wordOETGlossesList}  vs {[gloss]}"
#                 wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyFields})</small> is always and only glossed as ‘<b>{gloss}</b>’.</p>'
#                 # if formattedVLTGlossWords != gloss:
#                 #     wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> was always and only glossed as ‘<b>{formattedVLTGlossWords}</b>’)</small>.</p>'
#         displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
#         for oN in thisWordNumberList:
#             if oN==hh: continue # don't duplicate the word we're making the page for
#             # print( f"HERE: ({len(state.OETRefData['word_tables'][wordFileName][oN].split( TAB ))}) {state.OETRefData['word_tables'][wordFileName][oN]}")
#             oWordRef, oRowType, oMorphemeRowList, oLemmaRowList, oStrongs, oMorphology, oWord, oNoCantillations, oMorphemeGlosses, oContextualMorphemeGlosses, oWordGloss, oContextualWordGloss, oGlossCapitalisation, oGlossPunctuation, oGlossOrder, oGlossInsert, oRole, oNesting, oTags = state.OETRefData['word_tables'][HebrewWordFileName][oN].split( '\t' )
#             oWordGloss = oWordGloss.replace( '=', '_' )
#             # oHebrewWord = (oNoCantillations.replace( ',', '' ) # Remove morpheme breaks
#             #                 if oNoCantillations else oWord ) # Segs and notes have nothing in the noCantillations field
#             oGloss = convert_Hebrew_word_gloss_spans( oContextualWordGloss if oContextualWordGloss else oWordGloss if oWordGloss else oContextualMorphemeGlosses if oContextualMorphemeGlosses else oMorphemeGlosses )
#             oChosenGlossType = 'cWG' if oContextualWordGloss else 'wG' if oWordGloss else 'cMGs' if oContextualMorphemeGlosses else 'mGs'
#             oTranslation = '<small>(no English gloss here)</small>' if not oGloss or oGloss=='-' \
#                                 else f'''{GLOSS_TYPE_STRING_DICT[oChosenGlossType]}=‘<b>{oGloss}</b>’'''
#             for oExtraGlossType,oExtraGlossString in (('cWG',oContextualWordGloss),('wG',oWordGloss),('cMGs',oContextualMorphemeGlosses),('mGs',oMorphemeGlosses)):
#                 if oExtraGlossType != oChosenGlossType and oExtraGlossString:
#                     oExtraGlossTypeString = 'possible word glosses' if oExtraGlossType=='wG' and '/' in oExtraGlossString \
#                                                             else GLOSS_TYPE_STRING_DICT[oExtraGlossType]
#                     oExtraGlossString = tidy_Hebrew_lemma_gloss( oExtraGlossString )
#                     oTranslation = f'''{oTranslation} {oExtraGlossTypeString}=‘<b>{oExtraGlossString}</b>’'''
#             oTranslation = oTranslation.replace(',',', ').replace('</','PRoTecT').replace('/', ' / ').replace('PRoTecT', '</') # looks much nicer
#             oBBB, oCVW = oWordRef.split( '_', 1 )
#             oC, oVW = oCVW.split( ':', 1 )
#             oV, oW = oVW.split( 'w', 1 )
#             oTidyBBB = getOETTidyBBB( oBBB )
#             oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
#             oOSISbookCode = bos_books_codes_py.get_osis_abbreviation_py( oBBB )
#             oOET_LV_verse_HTML = oOET_RV_verse_HTML = None
#             if not state.TEST_MODE_FLAG or oBBB in state.preloadedBibles['OET-RV']:
#                 oOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, oBBB, oC, oV )
#                 oOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, oBBB, oC, oV )
#             # print( f"   {oBBB} {oC}:{oV} {oOET_RV_verse_HTML=}")
#             wordsHtml = f'''{wordsHtml}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBBwithNotes} {oC}:{oV}</a>''' \
# f''' {oTranslation} <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={oOSISbookCode}&c={oC}&v={oV}">OSHB {oTidyBBBwithNotes} {oC}:{oV} word {oW}</a></p>{f'\n{oOET_LV_verse_HTML}' if oOET_LV_verse_HTML else ''}{f'\n{oOET_RV_verse_HTML}' if oOET_RV_verse_HTML else ''}''' \
#             if not state.TEST_MODE_FLAG or oBBB in state.preloadedBibles['OET-RV'] else \
#             f'''{wordsHtml}\n<p class="wordLine">{oTidyBBBwithNotes} {oC}:{oV}''' \
# f''' {oTranslation} <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={oOSISbookCode}&c={oC}&v={oV}">OSHB {oTidyBBBwithNotes} {oC}:{oV} word {oW}</a></p>{f'\n{oOET_LV_verse_HTML}' if oOET_LV_verse_HTML else ''}{f'\n{oOET_RV_verse_HTML}' if oOET_RV_verse_HTML else ''}'''
#             # other_count += 1
#             # if other_count >= 120:
#             #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
#             #     break
#             displayCounter += 1
#             if displayCounter >= maxWordsToShow: break
#         if len(lemmaGlossesList) > len(wordOETGlossesList):
#             # print( f"{n}/{len(state.OETRefData['word_tables'][HebrewWordFileName])-1} {hebrewWord=} {wordGloss=} ({len(lemmaGlossesList)}) {lemmaGlossesList=} ({len(wordOETGlossesList)}) {wordOETGlossesList=}")
#             assert lemmaGlossesList != ['']
#             # NEVER_HAPPENS_BUT_PROBABLY_SHOULD_MAYBE -- Oh, it does happen at least once for 25401 hebrewWord='וְאֵלֶּה' wordGloss='and_these' (1) lemmaGlossesList=['and=these'] (0) wordOETGlossesList=[]
#             wordsHtml = f'''{wordsHtml}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLinksStr}’ {f"""have {len(lemmaGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’""" if len(lemmaGlossesList)>1 else f"have only one gloss: ‘<b>{lemmaGlossesList[0]}</b>’"}.</p>'''
#         elif len(thisWordNumberList) == 1:
#             hebLemmaWordRowsList = state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]
#             # lemmaFormsList = state.OETRefData['OTLemmaFormsDict'][noCantillations]
#             if len(hebLemmaWordRowsList) == 1:
#                 thisSingleLemmaRowNumber = hebLemmaWordRowsList[0]
#                 if len( state.OETRefData['OTWordRowNumbersDict'][thisSingleLemmaRowNumber] ) == 1:
#                     # print( f"{ref} '{hebrew}' ({glossWords}) {lemma=} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}" )
#                     # assert len(lemmaFormsList) == 1, f"{ref} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}"
#                     # assert len(morphemeGlossesList) == 1
#                     wordsHtml = f'''{wordsHtml.replace(lemmaLinksStr, f'{lemmaLinksStr}<sup>*</sup>', 1)}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> ‘{noCantillations}’ in the Hebrew originals.</p>'''

#         extraHTMLList = []
#         if mainGlossWord not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
#             # List other words that are glossed similarly
#             try:
#                 similarWords = (mainGlossWord,) + SIMILAR_GLOSS_WORDS_DICT[mainGlossWord]
#                 # print( f"      {mainGlossWord=} {similarWords=}")
#             except KeyError: similarWords = (mainGlossWord,)
#             extraWordSet, extraLemmaSet = set(), set()
#             for similarWord in similarWords:
#                 # print( f"{similarWord=} from {similarWords=} {len(state.OETRefData['OETOTGlossWordDict'])=}")
#                 nList = state.OETRefData['OETOTGlossWordDict'][similarWord]
#                 # print( f"{similarWord=} from {similarWords=} {len(state.OETRefData['OETOTGlossWordDict'])=} {nList=}")
#                 # print( f'''    {n} {ref} {hebrewWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nlist[:8]=}{'…' if len(nList)>8 else ''}''' )
#                 if len(nList) > 1:
#                     if similarWord==mainGlossWord:
#                         # assert n in nList, f"{n=} {mainGlossWord=} ({len(nList)}) {nList=}"
#                         logging.warning( f"Not sure why {hh=} similarWord={mainGlossWord=} not in ({len(nList)})" )
#                     # elif len(nList)>400:
#                     else:
#                         # print( f"This one {n=} similarWord={mainGlossWord=} was in ({len(nList)})" )
#                         if len(nList)>400:
#                             dPrint( 'Info', DEBUGGING_THIS_MODULE, f"preprocessHebrewWordsLemmasGlosses has EXCESSIVE {len(nList):,} entries for {mainGlossWord=} from {similarWord=}")
#                     for thisN in nList:
#                         if thisN == hh: continue # That's the current word row
#                         eWordRef, eRowType, eMorphemeRowList, eLemmaRowList, eStrongs, eMorphology, eWord, eNoCantillations, eMorphemeGlosses, eContextualMorphemeGlosses, eWordGloss, eContextualWordGloss, eGlossCapitalisation, eGlossPunctuation, eGlossOrder, eGlossInsert, eRole, eNesting, eTags = state.OETRefData['word_tables'][HebrewWordFileName][thisN].split( '\t' )
#                         eHebrewWord = (eNoCantillations.replace( ',', '' ) # Remove morpheme breaks
#                                         if eNoCantillations else eWord ) # Segs and notes have nothing in the noCantillations field
#                         # eWordGloss = eWordGloss.replace( '=', '_' )
#                         # eGloss = convert_Hebrew_word_gloss_spans( eContextualWordGloss if eContextualWordGloss else eWordGloss if eWordGloss else eContextualMorphemeGlosses if eContextualMorphemeGlosses else eMorphemeGlosses )
#                         eLemmaLink = ''
#                         if eHebrewWord!=hebrewWord or eMorphology!=morphology:
#                             eBBB, eCVW = eWordRef.split( '_', 1 )
#                             eC, eVW = eCVW.split( ':', 1 )
#                             eV, eW = eVW.split( 'w', 1 )
#                             eTidyBBB = getOETTidyBBB( eBBB )
#                             eTidyBBBwithNotes = getOETTidyBBB( eBBB, addNotes=True )
#                             eOSISbookCode = bos_books_codes_py.get_osis_abbreviation_py( eBBB )

#                             eLemmaLinksList, eLemmaLinksStr = [], ''
#                             for eLemmaRowNumberStr in eLemmaRowList.split( ',' ):
#                                 # print( f"{lemmaRowNumberStr=}" )
#                                 try: eLemmaRowNumber = int(eLemmaRowNumberStr)
#                                 except ValueError: continue # could be empty string or '<<<MISSING>>>'
#                                 eLemmaHebrew = state.OETRefData['OTHebLemmaList'][eLemmaRowNumber]
#                                 state.OETRefData['usedHebLemmasSet'].add( eLemmaHebrew ) # Used in next function to make lemma pages
#                                 eLemmaTrans = state.OETRefData['OTTransLemmaList'][eLemmaRowNumber]
#                                 eLemmaLink = f'<a title="View Hebrew lemma" href="../HebLem/{eLemmaTrans}.htm#Top">‘{eLemmaHebrew}’</a>'
#                                 eLemmaLinksList.append( eLemmaLink )
#                             if eLemmaLinksList:
#                                 eLemmaLinksStr = f'''Lemmas=<b>{', '.join(eLemmaLinksList)}</b>''' if len(eLemmaLinksList)>1 else f'Lemma=<b>{eLemmaLinksList[0]}</b>'
#                                 extraLemmaSet.add( eLemmaLinksStr )

#                             eHebrewPossibleLink = f'<a title="Go to word page" href="../HebWrd/{getHebrewWordpageFilename(thisN,state)}#Top">{eHebrewWord}</a>' if not state.TEST_MODE_FLAG or state.ALL_TEST_REFERENCE_PAGES_FLAG or eBBB in state.TEST_BOOK_LIST else eHebrewWord
#                             extraWordSet.add( eHebrewPossibleLink )
#                             eWordGloss = eWordGloss.replace( '=', '_' )
#                             eGloss = convert_Hebrew_word_gloss_spans( eContextualWordGloss if eContextualWordGloss else eWordGloss if eWordGloss else eContextualMorphemeGlosses if eContextualMorphemeGlosses else eMorphemeGlosses )
#                             eChosenGlossType = 'cWG' if eContextualWordGloss else 'wG' if eWordGloss else 'cMGs' if eContextualMorphemeGlosses else 'mGs'
#                             assert '\\' not in eGloss, f"{hh=} {eGloss=}"
#                             eTranslation = '<small>(no English gloss here)</small>' if not eGloss or eGloss=='-' \
#                                                 else f'''{GLOSS_TYPE_STRING_DICT[eChosenGlossType]}=‘<b>{eGloss}</b>’'''
#                             for eExtraGlossType,eExtraGlossString in (('cWG',eContextualWordGloss),('wG',eWordGloss),('cMGs',eContextualMorphemeGlosses),('mGs',eMorphemeGlosses)):
#                                 if eExtraGlossType != eChosenGlossType and eExtraGlossString:
#                                     eExtraGlossTypeString = 'possible word glosses' if eExtraGlossType=='wG' and '/' in eExtraGlossString \
#                                                                             else GLOSS_TYPE_STRING_DICT[eExtraGlossType]
#                                     eExtraGlossString = tidy_Hebrew_lemma_gloss( eExtraGlossString )
#                                     eTranslation = f'''{eTranslation} {eExtraGlossTypeString}=‘<b>{eExtraGlossString}</b>’'''
#                             eTranslation = eTranslation.replace(',',', ').replace('</','PRoTecT').replace('/', ' / ').replace('PRoTecT', '</') # looks much nicer
#                             etidyMorphologyField = '' #= eMoodField = eTenseField = eVoiceField = ePersonField = eCaseField = eGenderField = eNumberField = ''
#                             # if eMorphology:
#                                 # eTidyMorphologyFields = tidy_Hebrew_morphology( eRowType, eMorphology )
#                                 # eTidyMorphology = eMorphology[4:] if eMorphology.startswith('····') else eMorphology
#                                 # etidyMorphologyField = f'{eTidyMorphology}'
#                                 # if eTidyMorphology != '···': usedMorphologies.add( eTidyMorphology )
#                             eOET_LV_verse_HTML = eOET_RV_verse_HTML = None
#                             if not state.TEST_MODE_FLAG or eBBB in state.preloadedBibles['OET-RV']:
#                                 eOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, eBBB, eC, eV )
#                                 eOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, eBBB, eC, eV )
#                             # print( f"     {eBBB} {eC}:{eV} {eOET_RV_verse_HTML=}")
#                             extraHTMLList.append( f'''<p class="wordLine"><a title="View OET {eTidyBBB} text" href="{'../'*level}OET/byC/{eBBB}_C{eC}.htm#C{eC}V{eV}">{eTidyBBB} {eC}:{eV}</a>''' \
# f''' <b>{eHebrewPossibleLink}</b> ({transliterate_Hebrew(eHebrewWord)}) <small>{etidyMorphologyField}</small>{f' {eLemmaLinksStr}' if eLemmaLinksStr else ''} {eTranslation}''' \
# f''' <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={eOSISbookCode}&c={eC}&v={eV}">OSHB {eTidyBBB} {eC}:{eV} word {eW}</a></p>{f'\n{eOET_LV_verse_HTML}' if eOET_LV_verse_HTML else ''}{f'\n{eOET_RV_verse_HTML}' if eOET_RV_verse_HTML else ''}'''
#                         if not state.TEST_MODE_FLAG or eBBB in state.preloadedBibles['OET-RV'] else
#                             f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eHebrewPossibleLink}’ <small>({etidyMorphologyField})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''} ‘{eTranslation}’''' \
# f''' <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={eOSISbookCode}&c={eC}&v={eV}">OSHB {eTidyBBB} {eC}:{eV} word {eW}</a></p>{f'\n{eOET_LV_verse_HTML}' if eOET_LV_verse_HTML else ''}{f'\n{eOET_RV_verse_HTML}' if eOET_RV_verse_HTML else ''}''' )
#         assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"
#         if extraHTMLList:
#             wordsHtml = f'''{wordsHtml}\n<h2 class="otherHebrew">Hebrew words ({len(extraHTMLList):,}) other than {hebrewWord} <small>({tidyMorphologyFields})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
#             if len(extraHTMLList) > 10:
#                 wordsHtml = f'''{wordsHtml}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemma{'' if len(extraLemmaSet)==1 else 's'} altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
#             wordsHtml = f'''{wordsHtml}\n{NEWLINE.join(extraHTMLList)}'''

#     wordsHtml = ( wordsHtml.replace( ' <small>(<br> ', '\n<br><small> (' )# Tidy up formatting of similar word morphologies
#                 .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>')
#                 .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>')
#                 .replace( '\\add >', '<span class="addExtra">').replace( '\\add*', '</span>')
#                 .replace( '\\sup ', '<sup>').replace( '\\sup*', '</sup>')
#                 )
#     assert '\\' not in wordsHtml, f"{wordsHtml=}"
#     assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"
#     assert '</span>C1.htm' not in wordsHtml, f"{wordsHtml=}"

#     keyHtml = ''
#     if usedRoleLetters or usedMorphologies: # Add a key at the bottom
#         for usedRoleLetter in sorted( usedRoleLetters ):
#             keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
#         for usedMorphology in sorted( usedMorphologies ):
#             try:
#                 keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
#             except KeyError:
#                 logging.warning( f"create_Hebrew_words_json: Missing {usedMorphology=}")
#         if keyHtml:
#             keyHtml = f'\n<p class="key" id="Key"><b>Key</b>:{keyHtml}</p>'

    # Now remove unnecessary empty fields (to keep the filesizes down) and then output the JSON
    for key in jsonDict.copy(): # Iterate through a copy because we'll change the original dict on the fly
        if not jsonDict[key]: del jsonDict[key]
    filepath = outputFolderPath.joinpath( word_output_filename )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as json_output_file:
        json.dump( jsonDict, json_output_file, indent=4 ) # 'indent=4' makes the file human-readable
    # vPrint( 'Normal' if BibleOrgSysGlobals.alreadyMultiprocessing else 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(wordsHtml):,} characters to {word_output_filename}" )
    return True
# end of createAppJsonFiles.create_Hebrew_word_json


def create_Greek_words_json( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Greek_words_json( {outputFolderPath}, {state.BibleVersions} )" )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Checking/Making {len(state.OETRefData['word_tables'][GreekWordFileName])-1:,} Greek json files…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    def tidyGlossOfGreekWord( engGloss:str ) -> str:
        """
        The gloss might be the OET-LV gloss,
            or the original VLT gloss.
        """
            # .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>') \
            # .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>') \
            # .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>') \
        assert '.' not in engGloss
        assert '<span class="ul">' not in engGloss # already
        assert '\\add -' not in engGloss
        assert '\\add ¿' not in engGloss
        # .replace( '\\add ¿', '<span class="unusedArticle">' )
        result = ( engGloss
            .replace( '\\add +', '<span class="addArticle">' )
            .replace( '\\add =', '<span class="addCopula">' )
            #.replace( '\\add <a title', '__PROTECT__' ) # Enable if required
            .replace( '\\add <', '<span class="addDirectObject">' )
            #.replace( '__PROTECT__', '\\add <a title' )
            .replace( '\\add >', '<span class="addExtra">' )
            .replace( '\\add &', '<span class="addOwner">' )
            .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>')
            .replace( '_', '<span class="ul">_</span>')
            )
        return result
    # end of createAppJsonFiles.tidyGlossOfGreekWord


    # Now make a page for each Greek word (including the variants not used in the translation)
    numWordPagesMade = 0
    wordLinksForIndex:list[str] = [] # Used below to make an index page
    state.OETRefData['usedGrkLemmas'], state.OETRefData['usedGrkStrongs'] = set(), set() # Used in next functions to make lemma and Strongs pages
    for gg, columns_string in enumerate( state.OETRefData['word_tables'][GreekWordFileName][1:], start=1 ):
        if gg % 40_000 == 0:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      {numWordPagesMade+1:,} made out of {f'{gg:,} out of ' if gg!=numWordPagesMade+1 else ''}{len(state.OETRefData['word_tables'][GreekWordFileName])-1:,}…" )
        if not columns_string: continue # a blank line (esp. at end)
        # print( f"Word {gg}: {columns_string}" )

        usedRoleLetters, usedMorphologies = set(), set()

        ref, greekWord, SRLemma, GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = columns_string.split( '\t' )
        if probability != 'X': continue # Only want words/variants that are actually used

        BBB, CVW = ref.split( '_', 1 )
        if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG and BBB not in state.TEST_BOOK_LIST:
            continue # In some test modes, we only make the relevant json files
        C, VW = CVW.split( ':', 1 )
        V, W = VW.split( 'w', 1 )
        # ourTidyBBB = getOETTidyBBB( BBB, addNotes=True )
        ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
        ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
        tidyBbbb = getOETTidyBBB( BBB, titleCase=True, allowFourChars=True )

        output_filename = f'{gg}.json'
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: # NOTE: this makes the function quite a bit slower
            # Check that we're not creating any duplicate filenames (that will then be overwritten)
            assert output_filename not in used_word_filenames, f"Greek {gg} {output_filename}"
            used_word_filenames.append( output_filename )

        jsonDict = { 'word_number':gg, 'book_abbreviation':tidyBbbb, 'ref':ref,
                    'Greek_word':greekWord, 'transliterated_Greek_word':transliterate_Greek(greekWord),
                    'SR_lemma':SRLemma, 'Greek_lemma':GrkLemma,
                    'OET_gloss_words':OETGlossWordsStr, 'gloss_caps':glossCaps,
                    'morphology_code':morphology }

        # formattedOETGlossWords = formatNTSpansGlossWords( OETGlossWordsStr )
        # formattedVLTGlossWords = formatNTSpansGlossWords( VLTGlossWordsStr )
        formattedContextGlossWords = formatNTContextSpansOETGlossWords( gg, state )
        mainGlossWord = None
        for someGlossWord in OETGlossWordsStr \
                                .replace('\\add ','').replace('\\add*','') \
                                .replace('\\sup ','').replace('\\sup*','') \
                                .split( ' ' ):
            # print( f"{someGlossWord=}" )
            if '˱' not in someGlossWord and '˓' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words not gloss helpers, etc.
                assert not mainGlossWord, f"There should only be ONE {BBB} {C}:{V}w{W} {mainGlossWord=} {someGlossWord=} from {gg} {columns_string=}"
                mainGlossWord = someGlossWord.split('/(')[0] # Throw away any Hebrew names #.replace('\\add_','\\add ')
        if mainGlossWord and ('\\' in mainGlossWord or '/' in mainGlossWord):
            if '\\' in mainGlossWord: print( f"{gg=} {mainGlossWord=} from {OETGlossWordsStr=}"); halt
        if extendedStrongs == 'None': extendedStrongs = None
        if roleLetter == 'None': roleLetter = None
        if morphology == 'None': morphology = None

        strongs = extendedStrongs[:-1] if extendedStrongs else None # drop the last digit
        if strongs:
            state.OETRefData['usedGrkStrongs'].add( getPositiveLeadingInt(strongs) ) # Used in next function to make Strongs pages
        jsonDict['extended_Strongs'] = extendedStrongs
        jsonDict['Strongs_number'] = strongs

        roleField = ''
        if roleLetter:
            roleName = CNTR_ROLE_NAME_DICT[roleLetter]
            if roleName=='noun' and 'U' in glossCaps:
                roleName = 'proper noun'
            roleField = f' Word role=<b>{roleName}</b>'
            usedRoleLetters.add( roleLetter )
            jsonDict['word_role'] = roleName

        nominaSacraField = 'Marked with <b>Nomina Sacra</b>' if 'N' in glossCaps else ''
        jsonDict['nomina_sacra'] = 'N' in glossCaps

        # morphologyField =
        tidyRoleMorphology = tidyMorphology = moodField = tenseField = voiceField = personField = caseField = genderField = numberField = ''
        if morphology:
            # morphologyField = f' Morphology=<b>{morphology}</b>:' # Not currently used since we give all the following information instead
            tidyMorphology = morphology[4:] if morphology.startswith('····') else morphology
            tidyRoleMorphology = f'{roleLetter}-{tidyMorphology}'
            assert len(morphology) == 7, f"Got {ref} '{greekWord}' morphology ({len(morphology)}) = '{morphology}'"
            mood,tense,voice,person,case,gender,number = morphology
            if mood!='·': moodField = f' mood=<b>{CNTR_MOOD_NAME_DICT[mood]}</b>'
            if tense!='·': tenseField = f' tense=<b>{CNTR_TENSE_NAME_DICT[tense]}</b>'
            if voice!='·': voiceField = f' voice=<b>{CNTR_VOICE_NAME_DICT[voice]}</b>'
            if person!='·': personField = f' person=<b>{CNTR_PERSON_NAME_DICT[person]}</b>'
            if case!='·': caseField = f' case=<b>{CNTR_CASE_NAME_DICT[case]}</b>'
            if gender!='·': genderField = f' gender=<b>{CNTR_GENDER_NAME_DICT[gender]}</b>'
            if number!='·': numberField = f' number=<b>{CNTR_NUMBER_NAME_DICT[number]}</b>' # or № ???
            if tidyMorphology != '···': usedMorphologies.add( tidyMorphology )
        else:
            tidyRoleMorphology = roleLetter
        jsonDict['tidy_morphology_html'] = f'{roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}'
        translation = '<small>(no English gloss here)</small>' if not OETGlossWordsStr or OETGlossWordsStr=='-' else f'''‘{tidyGlossOfGreekWord(formattedContextGlossWords)}’'''
        jsonDict['translation_html'] = translation
        # capsField = f' <small>(Caps={glossCaps})</small>' if glossCaps else ''

        # Add pointers to people, locations, etc.
        semanticExtras = nominaSacraField
        if tagsStr:
            for semanticTag in tagsStr.split( ';' ):
                tagPrefix, tag = semanticTag[0], semanticTag[1:]
                # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
                if tagPrefix == 'P':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../Per/{tag}.htm#Top">{tag}</a>'''
                elif tagPrefix == 'L':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../Loc/{tag}.htm#Top">{tag}</a>'''
                elif tagPrefix == 'Y':
                    year = tag
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Year={year}{' AD' if int(year)>0 else ''}'''
                elif tagPrefix == 'T':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}TimeSeries={tag}'''
                elif tagPrefix == 'E':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Event={tag}'''
                elif tagPrefix == 'G':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Group={tag}'''
                elif tagPrefix == 'F':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Referred to from <a title="Go to referent word" href="{tag}.htm#Top">Word #{tag}</a>'''
                elif tagPrefix == 'R':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Refers to <a title="Go to referred word" href="{tag}.htm#Top">Word #{tag}</a>'''
                else:
                    logging.critical( f"Unknown '{tagPrefix}' word tag in {gg}: {columns_string}")
                    unknownTag
        jsonDict['semantic_extras'] = semanticExtras
        state.OETRefData['usedGrkLemmas'].add( GrkLemma ) # Used in next function to make lemma pages
#         lemmaLink = f'<a title="View Greek root word" href="../GrkLem/{SRLemma}.htm#Top">{SRLemma}</a>'
#         lemmaGlossesList = sorted( state.OETRefData['NTLemmaOETGlossesDict'][SRLemma] )
#         wordOETGlossesList = sorted( state.OETRefData['NTFormOETGlossesDict'][(greekWord,roleLetter,morphology)] )
#         wordVLTGlossesList = sorted( state.OETRefData['NTFormVLTGlossesDict'][(greekWord,roleLetter,morphology)] )

#         prevN = nextN = None
#         if gg > 1:
#             if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
#                 for nN in range( gg-1, 0, -1 ):
#                     nWordRef = state.OETRefData['word_tables'][GreekWordFileName][nN].split( '\t', 1 )[0]
#                     nBBB = nWordRef.split( '_', 1 )[0]
#                     if nBBB in state.TEST_BOOK_LIST:
#                         prevN = nN
#                         break
#             else: prevN = gg-1
#         if gg<len(state.OETRefData['word_tables'][GreekWordFileName])-1:
#             if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
#                 for nN in range( gg+1, len(state.OETRefData['word_tables'][GreekWordFileName]) ):
#                     nWordRef = state.OETRefData['word_tables'][GreekWordFileName][nN].split( '\t', 1 )[0]
#                     nBBB = nWordRef.split( '_', 1 )[0]
#                     if nBBB in state.TEST_BOOK_LIST:
#                         nextN = nN
#                         break
#             else: nextN = gg+1
#         prevLink = f'<b><a title="Previous word" href="{getGreekWordpageFilename(prevN, state )}#Top">←</a></b> ' if prevN is not None else ''
#         nextLink = f' <b><a title="Next word" href="{getGreekWordpageFilename(nextN, state )}#Top">→</a></b>' if nextN else ''
#         oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbbWithNotes}{NARROW_NON_BREAK_SPACE}{C}</a>'''
#         parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
#         interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}ilr/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
# #  Strongs=<a title="Goes to Strongs dictionary" href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a> Lemma=<b>{lemmaLink}</b>
#         wordsHtml = f'''{'' if probability else '<div class="unusedWord">'}<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Koine Greek wordlink #{gg}{'' if probability else ' <small>(Unused Greek word variant)</small>'}</h1>
# <p class="pgNav">{prevLink}{f'<b>{greekWord}</b>' if greekWord else '<small>(blank)</small>'} <a title="Go to Greek word index" href="index.htm">↑</a>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
# <p class="btnBar"><button type="button" id="wordsButton" title="Hide/Show word lines" onclick="hide_show_words()">Hide words</button> <button type="button" id="versesButton" title="Hide/Show verse lines" onclick="hide_show_verses()">Hide verses</button> <button type="button" id="coloursButton" title="Hide/Show verse colours" onclick="hide_show_colours()">Hide verse colours</button></p>
# <p class="link"><a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {tidyBbbb} {C}:{V}</a>
#  {f'<b>{greekWord}</b>' if greekWord else '<small>(blank)</small>'} ({transliterate_Greek(greekWord)}) {translation}{capsField if state.TEST_MODE_FLAG else ''}
#  Strongs={f'<a title="Goes to Strongs dictionary" href="{'../'*level}ref/GrkStrng/G{strongs}.htm#Top">{extendedStrongs}</a>' if extendedStrongs else '<small>(none)</small>'} Lemma=<b>{lemmaLink}</b>
# <br> {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}{f'{NEWLINE}<br>  {semanticExtras}' if semanticExtras else ''}</p>
# <p class="note"><small>Note: With the help of a companion website, these json files enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
# If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
# From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
# This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>{'' if probability else f'{NEWLINE}</div><!--unusedWord-->'}'''
#         assert '\\' not in wordsHtml, f"{wordsHtml=}"

#         if probability: # Now list all the other places where this same Greek word is used
#             # other_count = 0
#             if len(wordOETGlossesList)>1:
#                 wordOETGlossesStr = tidyGlossOfGreekWord( "</b>’, ‘<b>".join( wordOETGlossesList ) )
#             thisWordNumberList = state.OETRefData['NTFormUsageDict'][(greekWord,roleLetter,morphology)]
#             if len(thisWordNumberList) > 100: # too many to list
#                 maxWordsToShow = 50
#                 wordsHtml = f'{wordsHtml}\n<h2>Showing the first {maxWordsToShow} out of {len(thisWordNumberList)-1:,} uses of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
#                 if len(wordOETGlossesList)>1:
#                     wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordOETGlossesStr}</b>’.</p>'''
#                     if wordVLTGlossesList != wordOETGlossesList:
#                         wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
#                 else:
#                     assert wordOETGlossesList == [OETGlossWordsStr], f"{wordOETGlossesList}  vs {[OETGlossWordsStr]}"
#                     wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{OETGlossWordsStr}</b>’.</p>'
#                     if VLTGlossWordsStr != OETGlossWordsStr:
#                         wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> was always and only glossed as ‘<b>{VLTGlossWordsStr}</b>’)</small>.</p>'
#             else: # we can list all uses of the word
#                 maxWordsToShow = 100
#                 if len(thisWordNumberList) == 1:
#                     wordsHtml = f'{wordsHtml}\n<h2>Only use of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
#                     # grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][lemma]
#                     # lemmaFormsList = sorted( state.OETRefData['NTLemmaFormsDict'][lemma] )
#                     # if len(grkLemmaWordRowsList) == 1:
#                     #     # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {grkLemmaWordRowsList=} {grkLmmaFormsList=} {lemmaGlossesList=}" )
#                     #     assert len(lemmaFormsList) == 1
#                     #     assert len(lemmaGlossesList) == 1
#                     #     html = f'''{html.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Greek originals.</p>'''
#                 else:
#                     wordsHtml = f'{wordsHtml}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
#                 if len(wordOETGlossesList)>1:
#                     wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordOETGlossesStr}</b>’.</p>'''
#                     if wordVLTGlossesList != wordOETGlossesList:
#                         wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
#                 else:
#                     assert wordOETGlossesList == [formattedOETGlossWords], f"{gg} {BBB} {C}:{V} {greekWord=} {roleLetter=} {morphology=}: {wordOETGlossesList}  vs {[formattedOETGlossWords]}"
#                     wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{tidyGlossOfGreekWord(formattedOETGlossWords)}</b>’.</p>'
#                     if formattedVLTGlossWords != formattedOETGlossWords:
#                         wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> was always and only glossed as ‘<b>{formattedVLTGlossWords}</b>’)</small>.</p>'
#             displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
#             for oN in thisWordNumberList:
#                 if oN==gg: continue # don't duplicate the word we're making the page for
#                 oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, _oVLTGlossWords, oOETGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, _oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_tables'][GreekWordFileName][oN].split( '\t' )
#                 oFormattedContextGlossWords = formatNTContextSpansOETGlossWords( oN, state )
#                 oBBB, oCVW = oWordRef.split( '_', 1 )
#                 oC, oVW = oCVW.split( ':', 1 )
#                 oV, oW = oVW.split( 'w', 1 )
#                 oTidyBBB = getOETTidyBBB( oBBB )
#                 oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
#                 oTidyBbbb = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True )
#                 oTidyBbbbWithNotes = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True, addNotes=True )
#                 # if other_count == 0:
#                 translation = '<small>(no English gloss here)</small>' if oOETGlossWords=='-' else f'''‘{tidyGlossOfGreekWord(oFormattedContextGlossWords)}’'''
#                 oOET_LV_verse_HTML = oOET_RV_verse_HTML = None
#                 if not state.TEST_MODE_FLAG or oBBB in state.preloadedBibles['OET-RV']:
#                     oOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, oBBB, oC, oV )
#                     oOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, oBBB, oC, oV )
#                 wordsHtml = f'''{wordsHtml}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBbbbWithNotes} {oC}:{oV}</a>''' \
# f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBbbbWithNotes} {oC}:{oV} word {oW}</a></p>{f'\n{oOET_LV_verse_HTML}' if oOET_LV_verse_HTML else ''}{f'\n{oOET_RV_verse_HTML}' if oOET_RV_verse_HTML else ''}''' \
#                     if not state.TEST_MODE_FLAG or oBBB in state.preloadedBibles['OET-RV'] else \
#                     f'''{wordsHtml}\n<p class="wordLine">{oTidyBbbbWithNotes} {oC}:{oV}''' \
# f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBbbbWithNotes} {oC}:{oV} word {oW}</a></p>{f'\n{oOET_LV_verse_HTML}' if oOET_LV_verse_HTML else ''}{f'\n{oOET_RV_verse_HTML}' if oOET_RV_verse_HTML else ''}'''
#                 # other_count += 1
#                 # if other_count >= 120:
#                 #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
#                 #     break
#                 displayCounter += 1
#                 if displayCounter >= maxWordsToShow: break
#             if len(lemmaGlossesList) > len(wordOETGlossesList):
#                 wordsHtml = f'''{wordsHtml}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLink}’ {f"""have {len(lemmaGlossesList):,} different glosses: ‘<b>{tidyGlossOfGreekWord("</b>’, ‘<b>".join(lemmaGlossesList))}</b>’""" if len(lemmaGlossesList)>1 else f"have only one gloss: ‘<b>{tidyGlossOfGreekWord(lemmaGlossesList[0])}</b>’"}.</p>'''
#             elif len(thisWordNumberList) == 1:
#                 grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][SRLemma]
#                 grkLemmaFormsList = state.OETRefData['NTLemmaFormsDict'][SRLemma]
#                 if len(grkLemmaWordRowsList) == 1:
#                     # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {grkLemmaWordRowsList=} {grkLemmaFormsList=} {lemmaGlossesList=}" )
#                     assert len(grkLemmaFormsList) == 1
#                     assert len(lemmaGlossesList) == 1
#                     wordsHtml = f'''{wordsHtml.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>', 1)}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> ‘{SRLemma}’ in the Greek originals.</p>'''

#             if mainGlossWord not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
#                 # List other words that are glossed similarly
#                 try:
#                     similarWords = (mainGlossWord,) + SIMILAR_GLOSS_WORDS_DICT[mainGlossWord]
#                     # print( f"      {mainGlossWord=} {similarWords=}")
#                 except KeyError: similarWords = (mainGlossWord,)
#                 extraHTMLList = []
#                 extraWordSet, extraLemmaSet = set(), set()
#                 for similarWord in similarWords:
#                     nList = state.OETRefData['OETNTGlossWordDict'][similarWord]
#                     # print( f'''    {n} {ref} {greekWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nlist[:8]=}{'…' if len(nList)>8 else ''}''' )
#                     if len(nList) > 1:
#                         if similarWord==mainGlossWord: assert gg in nList
#                         if len(nList)>400:
#                             dPrint( 'Info', DEBUGGING_THIS_MODULE, f"create_Greek_words_json has EXCESSIVE {len(nList):,} entries for '{mainGlossWord}' from {similarWord=}")
#                         for thisN in nList:
#                             if thisN == gg: continue # That's the current word row
#                             eWordRef, eGreekWord, eSRLemma, _eGrkLemma, _eVLTGlossWordsStr, _eOETGlossWordsStr, _eGlossCaps, _eProbability, _eExtendedStrongs, eRoleLetter, eMorphology, _eTagsStr = state.OETRefData['word_tables'][GreekWordFileName][thisN].split( '\t' )
#                             if eRoleLetter == 'None': eRoleLetter = None
#                             if eMorphology == 'None': eMorphology = None
#                             if eGreekWord!=greekWord or eRoleLetter!=roleLetter or eMorphology!=morphology:
#                                 eBBB, eCVW = eWordRef.split( '_', 1 )
#                                 eC, eVW = eCVW.split( ':', 1 )
#                                 eV, eW = eVW.split( 'w', 1 )
#                                 eTidyBBB = getOETTidyBBB( eBBB )
#                                 eTidyBbbb = getOETTidyBBB( eBBB, titleCase=True, allowFourChars=True )

#                                 eGreekPossibleLink = f'<a title="Go to word page" href="../GrkWrd/{getGreekWordpageFilename(thisN, state )}#Top">{eGreekWord}</a>' if not state.TEST_MODE_FLAG or state.ALL_TEST_REFERENCE_PAGES_FLAG or eBBB in state.TEST_BOOK_LIST else eGreekWord
#                                 eLemmaLink = f'<a title="View Greek root word" href="../GrkLem/{eSRLemma}.htm#Top">{eSRLemma}</a>' if eSRLemma!=SRLemma else ''
#                                 eFormattedContextGlossWords = tidyGlossOfGreekWord( formatNTContextSpansOETGlossWords( thisN, state ) )
#                                 assert '\\' not in eFormattedContextGlossWords, f"{gg=} {eFormattedContextGlossWords=}"
#                                 eTidyRoleMorphology = eTidyMorphology = '' #= eMoodField = eTenseField = eVoiceField = ePersonField = eCaseField = eGenderField = eNumberField = ''
#                                 if eMorphology:
#                                     assert len(eMorphology) == 7, f"Got {eWordRef} '{eGreekWord}' morphology ({len(eMorphology)}) = '{eMorphology}'"
#                                     eTidyMorphology = eMorphology[4:] if eMorphology.startswith('····') else eMorphology
#                                     eTidyRoleMorphology = f'{eRoleLetter}-{eTidyMorphology}'
#                                     usedRoleLetters.add( eRoleLetter )
#                                     if eTidyMorphology != '···': usedMorphologies.add( eTidyMorphology )
#                                 else:
#                                     eTidyRoleMorphology = eRoleLetter
#                                 eOET_LV_verse_HTML = eOET_RV_verse_HTML = None
#                                 if not state.TEST_MODE_FLAG or eBBB in state.preloadedBibles['OET-RV']:
#                                     eOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, eBBB, eC, eV )
#                                     eOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, eBBB, eC, eV )
#                                 extraHTMLList.append( f'''<p class="wordLine"><a title="View OET {eTidyBBB} text" href="{'../'*level}OET/byC/{eBBB}_C{eC}.htm#C{eC}V{eV}">{eTidyBBB} {eC}:{eV}</a>'''
# f''' <b>{eGreekPossibleLink}</b> ({transliterate_Greek(eGreekWord)}) <small>{eTidyRoleMorphology}</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}'''
# f''' ‘{eFormattedContextGlossWords}’'''
# f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBbbb} {eC}:{eV} word {eW}</a></p>{f'\n{eOET_LV_verse_HTML}' if eOET_LV_verse_HTML else ''}{f'\n{eOET_RV_verse_HTML}' if eOET_RV_verse_HTML else ''}'''
#                                     if not state.TEST_MODE_FLAG or eBBB in state.preloadedBibles['OET-RV'] else
#                                         f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eGreekPossibleLink}’ <small>({eTidyRoleMorphology})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}''' \
# f''' ‘{eFormattedContextGlossWords}’''' \
# f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBbbb} {eC}:{eV} word {eW}</a></p>{f'\n{eOET_LV_verse_HTML}' if eOET_LV_verse_HTML else ''}{f'\n{eOET_RV_verse_HTML}' if eOET_RV_verse_HTML else ''}''' )
#                                 extraWordSet.add( eGreekPossibleLink )
#                                 extraLemmaSet.add( eLemmaLink if eLemmaLink else lemmaLink )
#                 if extraHTMLList:
#                     wordsHtml = f'''{wordsHtml}\n<h2 class="otherGreek">Greek words ({len(extraHTMLList):,}) other than {greekWord} <small>({tidyRoleMorphology})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
#                     if len(extraHTMLList) > 10:
#                         wordsHtml = f'''{wordsHtml}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemma{'' if len(extraLemmaSet)==1 else 's'} altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
#                     wordsHtml = f'''{wordsHtml}\n{NEWLINE.join(extraHTMLList)}'''
#         assert '\\' not in wordsHtml, f"{wordsHtml=}"
#         assert '</span>C1.htm' not in wordsHtml, f"{wordsHtml=}"

#         keyHtml = ''
#         if usedRoleLetters or usedMorphologies: # Add a key at the bottom
#             for usedRoleLetter in sorted( usedRoleLetters ):
#                 keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
#             for usedMorphology in sorted( usedMorphologies ):
#                 try:
#                     keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
#                 except KeyError:
#                     logging.warning( f"create_Greek_words_json: Missing {usedMorphology=}")
#             if keyHtml:
#                 keyHtml = f'\n<p class="key" id="Key"><b>Key</b>:{keyHtml}</p>'

        # Now remove unnecessary empty fields (to keep the filesizes down) and then output the JSON
        for key in jsonDict.copy(): # Iterate through a copy because we'll change the original dict on the fly
            if not jsonDict[key]: del jsonDict[key]
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as json_output_file:
            json.dump( jsonDict, json_output_file, indent=4 ) # 'indent=4' makes the file human-readable
        # vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(wordsHtml):,} characters to {output_filename}" )
        # wordLinksForIndex.append( f'<a href="{output_filename}">{greekWord}</a>')
        numWordPagesMade += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {numWordPagesMade:,}{f"/{len(state.OETRefData['word_tables'][GreekWordFileName])-1:,}" if numWordPagesMade < len(state.OETRefData['word_tables'][GreekWordFileName])-1 else ''} Greek json files (using {len(state.OETRefData['usedGrkLemmas']):,} Greek lemmas).''' )

#     # Create index page for this folder
#     filename = 'index.htm'
#     filepath = outputFolderPath.joinpath( filename )
#     top = makeTop( level, None, 'wordIndex', None, state ) \
#             .replace( '__TITLE__', f"Greek Words Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Greek, words' )
#     indexText = ' '.join( wordLinksForIndex )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
# <p class="note"><span class="selectedBook">Greek words index</span> <a href="transIndex.htm">Transliterated Greek words index</a></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics</a></p>
# <h1 id="Top">Greek Words Index ({len(wordLinksForIndex):,})</h1>
# <p class="note">{indexText}</p>
# {makeBottom( level, None, 'wordIndex', state )}'''
#     assert checkHtml( 'wordIndex', indexHtml )
#     assert not filepath.is_file() # Check that we're not overwriting anything
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

#     # Create a transliterated index page for this folder
#     filename = 'transIndex.htm'
#     filepath = outputFolderPath.joinpath( filename )
#     top = makeTop( level, None, 'wordIndex', None, state ) \
#             .replace( '__TITLE__', f"Transliterated Greek Words Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Greek, words, transliterated' )
#     indexText = transliterate_Greek( indexText )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
# <p class="note"><a href="index.htm">Greek words index</a> <span class="selectedBook">Transliterated Greek words index</span></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics</a></p>
# <h1 id="Top">Transliterated Greek Words Index ({len(wordLinksForIndex):,})</h1>
# <p class="note">{indexText}</p>
# {makeBottom( level, None, 'wordIndex', state )}'''
#     assert checkHtml( 'wordIndex', indexHtml )
#     assert not filepath.is_file() # Check that we're not overwriting anything
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createAppJsonFiles.create_Greek_words_json


NUM_STRONGS_INDEX_ENTRIES = 60
STRONGS_NUMBER_REGEX = re.compile( '>[GH][1-9][0-9]{0,4}<' ) # It's inside a span
STRONGS_FOLDER_DICT = {'G':'GrkStrng', 'H':'HebStrng'}
def create_Hebrew_Strongs_pages( level:int, outputFolderPath:Path, bibleLexicon:BibleLexicon, state:State ) -> int:
    """
    """
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making Hebrew Strongs pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    indexList = []
    finalStrongsNumber = 8674
    # indexDistance = finalStrongsNumber // NUM_STRONGS_INDEX_ENTRIES
    # print( f"  Hebrew: {finalStrongsNumber=} {NUM_STRONGS_INDEX_ENTRIES=} {indexDistance=}" )
    indexDistance = 150 # was 144 for NUM_STRONGS_INDEX_ENTRIES=60
    numPagesMade = 0
    for strongsNumber in range( 1, finalStrongsNumber+1 ):
        strongsStr = str( strongsNumber )
        strongsLetterNumberStr = f'H{strongsStr}'
        if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
            if strongsNumber not in state.OETRefData['usedHebStrongsSet']:
                # print( f"Skipping {strongsLetterNumberString} because not in {list(state.OETRefData['usedHebStrongsSet'])[:20]}")
                continue
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Making Hebrew Strongs {strongsString} page…" )
        output_filename = f'{strongsLetterNumberStr}.htm'
        filepath = outputFolderPath.joinpath( output_filename )

        top = makeTop( level, None, 'StrongsPage', None, state ) \
                .replace( '__TITLE__', f"Strongs {strongsLetterNumberStr}{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                .replace( '__KEYWORDS__', 'Strongs, number, {strongsString}, Hebrew' )

        prevLink = f'<b><a title="Previous entry" href="H{strongsNumber-1}.htm#Top">←</a></b> ' if strongsNumber>1 else ''
        nextLink = f' <b><a title="Next entry" href="H{strongsNumber+1}.htm#Top">→</a></b>' if strongsNumber<finalStrongsNumber else ''

        middle = bibleLexicon.getStrongsEntryHTML( strongsLetterNumberStr ) # Strongs entry
        bdDrBrEntry = bibleLexicon.getBrDrBrEntryHTML( strongsLetterNumberStr ) # Brown, Driver, Briggs entry
        if bdDrBrEntry:
            middle = f'''{middle}
<h2>Brown, Driver, Briggs lexicon entry</h2>
{bdDrBrEntry}'''
            
        # Liven internal Strongs references
        def replFunction( strongsMatch:re.Match ) -> str:
            # print( f"     Matched '{strongsMatch.group(0)}' Regex from {strongsLetterNumberString}" )
            strongsLetterAndNumber = strongsMatch.group(0)[1:-1]
            return f'><a href="../{STRONGS_FOLDER_DICT[strongsLetterAndNumber[0]]}/{strongsLetterAndNumber}.htm#Top">{strongsLetterAndNumber}</a><'
        middle = STRONGS_NUMBER_REGEX.sub( replFunction, middle )

        if strongsNumber in (1,finalStrongsNumber) or strongsNumber % indexDistance == 0:
            strongsWordEntry = bibleLexicon.getStrongsEntryField( strongsLetterNumberStr, 'word' )
            assert isinstance( strongsWordEntry, tuple ) # heb,morph,pronunciation,transliteration,none
            strongsWordEntry = f'<b>{strongsWordEntry[0]}</b> ({strongsWordEntry[3]})'
            indexList.append( f'<li><a href="{strongsLetterNumberStr}.htm#Top">{strongsLetterNumberStr}: {strongsWordEntry}</a></li>' )

        numRefs = len( state.OETRefData['OTStrongsRefs'][strongsStr] )
        if numRefs > 500:
            sMod = 20
            versesHtml = [f'\n<p class="note">Displaying only every {sMod}<sup>th</sup> verse out of {numRefs:,}:</p>']
        elif numRefs > 120:
            sMod = 10
            versesHtml = [f'\n<p class="note">Displaying only every {sMod}<sup>th</sup> verse out of {numRefs}:</p>']
        else:
            sMod = None
            versesHtml = [f'''\n<p class="note">Appears in {'only one verse' if numRefs==1 else f'a total of {numRefs} verses'}:</p>''']
        for ss,sRef in enumerate( state.OETRefData['OTStrongsRefs'][strongsStr] ):
            if sMod is None or ss % sMod == 0: # The first one is always displayed
                sBBB, sCV = sRef.split( '_', 1 )
                sC, sV = sCV.split( ':', 1 )
                sOET_LV_verse_HTML = sOET_RV_verse_HTML = None
                if not state.TEST_MODE_FLAG or sBBB in state.preloadedBibles['OET-RV']:
                    sOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, sBBB, sC, sV )
                    sOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, sBBB, sC, sV )
                    versesHtml.append( f'''\n<p class="vRef">{sBBB} {sC}:{sV}</p>{f'\n{sOET_LV_verse_HTML}' if sOET_LV_verse_HTML else ''}{f'\n{sOET_RV_verse_HTML}' if sOET_RV_verse_HTML else ''}''' )

        pageHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
<p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
<p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
<p class="note"><a href="../Stats/">Bible statistics index</a></p>
<h1 id="Top">Strongs {strongsLetterNumberStr}</h1>
<p class="pgNav">{prevLink}<b>{strongsLetterNumberStr}</b> <a title="Go to Hebrew Strongs index" href="index.htm">↑</a>{nextLink}</p>
<p class="btnBar"><button type="button" id="wordsButton" title="Hide/Show verse refs" onclick="hide_show_words()">Hide verse refs</button> <button type="button" id="versesButton" title="Hide/Show verse lines" onclick="hide_show_verses()">Hide verses</button> <button type="button" id="coloursButton" title="Hide/Show verse colours" onclick="hide_show_colours()">Hide verse colours</button></p>
<p>{middle}</p>{''.join(versesHtml)}
<p>View on <a href="https://BibleHub.com/hebrew/{strongsNumber}.htm">BibleHub</a>.</p>
{makeBottom( level, None, 'StrongsPage', state )}'''
        # assert checkHtml( 'StrongsPage', pageHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( pageHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(pageHtml):,} characters to {output_filename}" )
        numPagesMade += 1
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Made {numPagesMade:,} {f'out of {finalStrongsNumber:,} ' if numPagesMade<finalStrongsNumber else ''}Hebrew Strongs pages." )

#     # Create index page for this Strongs folder
#     filename = 'index.htm'
#     filepath = outputFolderPath.joinpath( filename )
#     top = makeTop( level, None, 'StrongsIndex', None, state ) \
#             .replace( '__TITLE__', f"Strongs Hebrew Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Strongs, Hebrew, index' )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><span class="selectedBook">Hebrew Strongs numbers index</span></p>
# <p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics index</a></p>
# <h1 id="Top">Strongs Hebrew Index ({len(indexList):,})</h1>
# <ul>{'\n'.join(indexList)}</ul>
# {makeBottom( level, None, 'StrongsIndex', state )}'''
#     assert checkHtml( 'StrongsIndex', indexHtml )
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    try: del state.OETRefData['usedHebStrongsSet']
    except KeyError: pass # ignore if it never existed
# end of createAppJsonFiles.create_Hebrew_Strongs_pages function


def create_Greek_Strongs_pages( level:int, outputFolderPath:Path, bibleLexicon:BibleLexicon, state:State ) -> int:
    """
    """
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making Greek Strongs pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    indexList = []
    finalStrongsNumber = 5624
    # indexDistance = finalStrongsNumber // NUM_STRONGS_INDEX_ENTRIES
    # print( f"  Greek: {finalStrongsNumber=} {NUM_STRONGS_INDEX_ENTRIES=} {indexDistance=}" )
    indexDistance = 100 # was 94
    numPagesMade = 0
    for strongsNumber in range( 1, finalStrongsNumber+1 ):
        strongsStr = str( strongsNumber )
        strongsLetterNumberStr = f'G{strongsNumber}'
        if state.TEST_MODE_FLAG and not state.ALL_TEST_REFERENCE_PAGES_FLAG:
            if strongsNumber not in state.OETRefData['usedGrkStrongs']:
                # print( f"Skipping {strongsLetterNumberString} because not in {list(state.OETRefData['usedGrkStrongs'])[:20]}")
                continue
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Making Greek Strongs {strongsString} page…" )
        output_filename = f'{strongsLetterNumberStr}.htm'
        filepath = outputFolderPath.joinpath( output_filename )

        top = makeTop( level, None, 'StrongsPage', None, state ) \
                .replace( '__TITLE__', f"Strongs {strongsLetterNumberStr}{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                .replace( '__KEYWORDS__', 'Strongs, number, {strongsString}, Greek' )

        prevLink = f'<b><a title="Previous entry" href="G{strongsNumber-1}.htm#Top">←</a></b> ' if strongsNumber>1 else ''
        nextLink = f' <b><a title="Next entry" href="G{strongsNumber+1}.htm#Top">→</a></b>' if strongsNumber<finalStrongsNumber else ''

        middle = bibleLexicon.getStrongsEntryHTML( strongsLetterNumberStr )

        # Liven internal Strongs references
        def replFunction( strongsMatch:re.Match ) -> str:
            # print( f"     Matched '{strongsMatch.group(0)}' Regex from {strongsLetterNumberString}" )
            strongsLetterAndNumber = strongsMatch.group(0)[1:-1]
            return f'><a href="../{STRONGS_FOLDER_DICT[strongsLetterAndNumber[0]]}/{strongsLetterAndNumber}.htm#Top">{strongsLetterAndNumber}</a><'
        if middle:
            middle = STRONGS_NUMBER_REGEX.sub( replFunction, middle )

        if strongsNumber in (1,finalStrongsNumber) or strongsNumber % indexDistance == 0:
            strongsWordEntry = bibleLexicon.getStrongsEntryField( strongsLetterNumberStr, 'word' )
            if strongsWordEntry:
                assert isinstance( strongsWordEntry, tuple ) # grk,transliteration,OTHER
                strongsWordEntry = f'<b>{strongsWordEntry[0]}</b> ({strongsWordEntry[1]})'
                indexList.append( f'<li><a href="{strongsLetterNumberStr}.htm#Top">{strongsLetterNumberStr}: {strongsWordEntry}</a></li>' )

        numRefs = len( state.OETRefData['NTStrongsRefs'][strongsStr] )
        if numRefs > 500:
            sMod = 20
            versesHtml = [f'\n<p class="note">Displaying only every {sMod}<sup>th</sup> verse out of {numRefs:,}.</p>']
        elif numRefs > 120:
            sMod = 10
            versesHtml = [f'\n<p class="note">Displaying only every {sMod}<sup>th</sup> verse out of {numRefs}.</p>']
        else:
            sMod = None
            versesHtml = [f'''\n<p class="note">Appears in {'only one verse' if numRefs==1 else f'a total of {numRefs} verses'}:</p>''']
        for ss,sRef in enumerate( state.OETRefData['NTStrongsRefs'][strongsStr] ):
            if sMod is None or ss % sMod == 0: # The first one is always displayed
                sBBB, sCV = sRef.split( '_', 1 )
                sC, sV = sCV.split( ':', 1 )
                sOET_LV_verse_HTML = sOET_RV_verse_HTML = None
                if not state.TEST_MODE_FLAG or sBBB in state.preloadedBibles['OET-RV']:
                    sOET_LV_verse_HTML = get_OET_LV_verse_HTML( level, sBBB, sC, sV )
                    sOET_RV_verse_HTML = get_OET_RV_verse_HTML( level, sBBB, sC, sV )
                    versesHtml.append( f'''\n<p class="vRef">{sBBB} {sC}:{sV}</p>{f'\n{sOET_LV_verse_HTML}' if sOET_LV_verse_HTML else ''}{f'\n{sOET_RV_verse_HTML}' if sOET_RV_verse_HTML else ''}''' )

        pageHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../GrkStrng/">Greek Strongs numbers index</a></p>
<p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
<p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
<p class="note"><a href="../Stats/">Bible statistics index</a></p>
<h1 id="Top">Strongs {strongsLetterNumberStr}</h1>
<p class="pgNav">{prevLink}<b>{strongsLetterNumberStr}</b> <a title="Go to Greek Strongs index" href="index.htm">↑</a>{nextLink}</p>
<p class="btnBar"><button type="button" id="wordsButton" title="Hide/Show verse refs" onclick="hide_show_words()">Hide verse refs</button> <button type="button" id="versesButton" title="Hide/Show verse lines" onclick="hide_show_verses()">Hide verses</button> <button type="button" id="coloursButton" title="Hide/Show verse colours" onclick="hide_show_colours()">Hide verse colours</button></p>
<p>{middle}</p>{''.join(versesHtml)}
<p>View on <a href="https://BibleHub.com/greek/{strongsNumber}.htm">BibleHub</a>.</p>
{makeBottom( level, None, 'StrongsPage', state )}'''
        assert checkHtml( 'StrongsPage', pageHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( pageHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(pageHtml):,} characters to {output_filename}" )
        numPagesMade += 1
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Made {numPagesMade:,} {f'out of {finalStrongsNumber:,} ' if numPagesMade<finalStrongsNumber else ''}Greek Strongs pages." )

#     # Create index page for this Strongs folder
#     filename = 'index.htm'
#     filepath = outputFolderPath.joinpath( filename )
#     top = makeTop( level, None, 'StrongsIndex', None, state ) \
#             .replace( '__TITLE__', f"Strongs Greek Index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
#             .replace( '__KEYWORDS__', 'Bible, Strongs, Greek, index' )
#     indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
# <p class="note"><b><a href="../">Reference lists contents page</a></b></p>
# <p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
# <p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
# <p class="note"><a href="../HebStrng/">Hebrew Strongs numbers index</a></p>
# <p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
# <p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
# <p class="note"><span class="selectedBook">Greek Strongs numbers index</span></p>
# <p class="note"><a href="../Per/importantIndex.htm">Important people index</a> <a href="../Per/">All people index</a> <a href="../Loc/">Locations index</a></p>
# <p class="note"><a href="../Kingdoms/">Promised land kingdoms index</a></p>
# <p class="note"><a href="../Stats/">Bible statistics index</a></p>
# <h1 id="Top">Strongs Greek Index ({len(indexList):,})</h1>
# <ul>{'\n'.join(indexList)}</ul>
# {makeBottom( level, None, 'StrongsIndex', state )}'''
#     assert checkHtml( 'StrongsIndex', indexHtml )
#     with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
#         indexHtmlFile.write( indexHtml )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    try: del state.OETRefData['usedGrkStrongs']
    except KeyError: pass # ignore if it never existed
# end of createAppJsonFiles.create_Greek_Strongs_pages function



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createAppJsonFiles object
    pass
# end of createAppJsonFiles.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createAppJsonFiles object
    pass
# end of createAppJsonFiles.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createAppJsonFiles.py
