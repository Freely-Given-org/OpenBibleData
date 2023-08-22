#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createOETReferencePages.py
#
# Module handling OpenBibleData createOETReferencePages functions
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
Module handling createOETReferencePages functions.

CHANGELOG:
    2023-07-30 Show first 40 word & lemma entries even if there's over 100 (didn't use to display any of them)
    2023-08-15 Remove '....' off front of displayed morphology field (if it's there)
                and put ‘typographic quotes’ around glosses
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
from collections import defaultdict
import re
import json
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek

from html import makeTop, makeBottom
from Bibles import tidyBBB


LAST_MODIFIED_DATE = '2023-08-16' # by RJH
SHORT_PROGRAM_NAME = "createOETReferencePages"
PROGRAM_NAME = "OpenBibleData createOETReferencePages functions"
PROGRAM_VERSION = '0.33'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


project_folderpath = Path(__file__).parent.parent # Find folders relative to this module
FG_folderpath = project_folderpath.parent # Path to find parallel Freely-Given.org repos
THEOGRAPHIC_INPUT_FOLDER_PATH = FG_folderpath.joinpath( 'Bible_speaker_identification/outsideSources/TheographicBibleData/derivedFiles/' )


CNTR_BOOK_ID_MAP = {
    'MAT':40, 'MRK':41, 'LUK':42, 'JHN':43, 'ACT':44,
    'ROM':45, 'CO1':46, 'CO2':47, 'GAL':48, 'EPH':49, 'PHP':50, 'COL':51, 'TH1':52, 'TH2':53, 'TI1':54, 'TI2':55, 'TIT':56, 'PHM':57,
    'HEB':58, 'JAM':58, 'PE1':60, 'PE2':61, 'JN1':62, 'JN2':63, 'JN3':64, 'JDE':65, 'REV':66}
CNTR_ROLE_NAME_DICT = {'N':'noun', 'S':'substantive adjective', 'A':'adjective', 'E':'determiner/case-marker', 'R':'pronoun',
                  'V':'verb', 'I':'interjection', 'P':'preposition', 'D':'adverb', 'C':'conjunction', 'T':'particle'}
CNTR_MOOD_NAME_DICT = {'I':'indicative', 'M':'imperative', 'S':'subjunctive',
            'O':'optative', 'N':'infinitive', 'P':'participle', 'e':'e'}
CNTR_TENSE_NAME_DICT = {'P':'present', 'I':'imperfect', 'F':'future', 'A':'aorist', 'E':'perfect', 'L':'pluperfect', 'U':'U', 'e':'e'}
CNTR_VOICE_NAME_DICT = {'A':'active', 'M':'middle', 'P':'passive', 'p':'p', 'm':'m', 'a':'a'}
CNTR_PERSON_NAME_DICT = {'1':'1st', '2':'2nd', '3':'3rd', 'g':'g'}
CNTR_CASE_NAME_DICT = {'N':'nominative', 'G':'genitive', 'D':'dative', 'A':'accusative', 'V':'vocative', 'g':'g', 'n':'n', 'a':'a', 'd':'d', 'v':'v', 'U':'U'}
CNTR_GENDER_NAME_DICT = {'M':'masculine', 'F':'feminine', 'N':'neuter', 'm':'m', 'f':'f', 'n':'n'}
CNTR_NUMBER_NAME_DICT = {'S':'singular', 'P':'plural', 's':'s', 'p':'p'}
def createOETReferencePages( level:int, outputFolderPath:Path, state ) -> bool:
    """
    Make pages for all the words and lemmas to link to.

    Sadly, there's almost identical code in make_table_pages() in OET convert_OET-LV_to_simple_HTML.py
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETReferencePages( {level}, {outputFolderPath}, {state.BibleVersions} )" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}reference pages for OET…" )

    # First make a list of each place the same Greek word (and matching morphology) is used
    # NOTE: The word table has Matthew at the beginning (whereas the OET places John and Mark at the beginning) so we do them first
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Finding all uses of {len(state.OETRefData['word_table'])-1:,} words…" )
    state.OETRefData['formUsageDict'], state.OETRefData['lemmaDict'] = defaultdict(list), defaultdict(list)
    state.OETRefData['lemmaFormsDict'] = defaultdict(set)
    state.OETRefData['formGlossesDict'], state.OETRefData['lemmaGlossesDict'] = defaultdict(set), defaultdict(set)
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'JHN' ):
            _ref, greek, lemma, glossWords, _glossCaps,probability, _extendedStrongs, _roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            formattedGlossWords = glossWords \
                                    .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                    .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                    .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
            if probability:
                formMorph2Tuple = (greek, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph2Tuple].append( n )
                state.OETRefData['lemmaDict'][lemma].append( n )
                state.OETRefData['lemmaFormsDict'][lemma].add( formMorph2Tuple )
                state.OETRefData['formGlossesDict'][formMorph2Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][lemma].add( formattedGlossWords )
        elif state.OETRefData['formUsageDict']: break # Must have already finished John
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'MRK' ):
            _ref, greek, lemma, glossWords, _glossCaps,probability, _extendedStrongs, _roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            formattedGlossWords = glossWords \
                                    .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                    .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                    .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
            if probability:
                formMorph2Tuple = (greek, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph2Tuple].append( n )
                state.OETRefData['lemmaDict'][lemma].append( n )
                state.OETRefData['lemmaFormsDict'][lemma].add( formMorph2Tuple )
                state.OETRefData['formGlossesDict'][formMorph2Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][lemma].add( formattedGlossWords )
        elif columns_string.startswith( 'LUK' ): break # Must have already finished Mark
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if not columns_string.startswith( 'JHN' ) and not columns_string.startswith( 'MRK' ):
            _ref, greek, lemma, glossWords, _glossCaps,probability, _extendedStrongs, _roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            formattedGlossWords = glossWords \
                                    .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                    .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                    .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
            if probability:
                formMorph2Tuple = (greek, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph2Tuple].append( n )
                state.OETRefData['lemmaDict'][lemma].append( n )
                state.OETRefData['lemmaFormsDict'][lemma].add( formMorph2Tuple )
                state.OETRefData['formGlossesDict'][formMorph2Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][lemma].add( formattedGlossWords )

    make_word_pages( level+1, outputFolderPath.joinpath( 'W/' ), state )
    make_Greek_lemma_pages( level+1, outputFolderPath.joinpath( 'G/' ), state )

    make_person_pages( level+1, outputFolderPath.joinpath( 'P/' ), state )
    make_location_pages( level+1, outputFolderPath.joinpath( 'L/' ), state )

    del state.OETRefData # No longer needed
    return True
# end of createOETReferencePages.createOETReferencePages


def make_word_pages( level:int, outputFolderPath:Path, state ) -> None:
    """
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"make_word_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making {len(state.OETRefData['word_table'])-1:,} word pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    # Now make a page for each Greek word (including the variants not used in the translation)
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        # print( n, columns_string )
        output_filename = f'{n}.htm'
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        if columns_string: # not a blank line (esp. at end)
            ref, greek, lemma, glossWords, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = columns_string.split( '\t' )
            formattedGlossWords = glossWords \
                                    .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                    .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                    .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
            if extendedStrongs == 'None': extendedStrongs = None
            if roleLetter == 'None': roleLetter = None
            if morphology == 'None': morphology = None

            BBB, CVW = ref.split( '_', 1 )
            C, VW = CVW.split( ':', 1 )
            V, W = VW.split( 'w', 1 )
            ourTidyBBB = tidyBBB( BBB )
            ourTidyBbb = tidyBBB( BBB, titleCase=True )

            strongs = extendedStrongs[:-1] if extendedStrongs else None # drop the last digit

            roleField = ''
            if roleLetter:
                roleName = CNTR_ROLE_NAME_DICT[roleLetter]
                if roleName=='noun' and 'U' in glossCaps:
                    roleName = 'proper noun'
                roleField = f' Word role=<b>{roleName}</b>'

            probabilityField = f'<small>(P={probability}%)</small> ' if probability else ''

            # morphologyField = 
            tidyMorphology = moodField = tenseField = voiceField = personField = caseField = genderField = numberField = ''
            if morphology:
                # morphologyField = f' Morphology=<b>{morphology}</b>:' # Not currently used since we give all the following information instead
                tidyMorphology = morphology[4:] if morphology.startswith('....') else morphology
                assert len(morphology) == 7, f"Got {ref} '{greek}' morphology ({len(morphology)}) = '{morphology}'"
                mood,tense,voice,person,case,gender,number = morphology
                if mood!='.': moodField = f' mood=<b>{CNTR_MOOD_NAME_DICT[mood]}</b>'
                if tense!='.': tenseField = f' tense=<b>{CNTR_TENSE_NAME_DICT[tense]}</b>'
                if voice!='.': voiceField = f' voice=<b>{CNTR_VOICE_NAME_DICT[voice]}</b>'
                if person!='.': personField = f' person=<b>{CNTR_PERSON_NAME_DICT[person]}</b>'
                if case!='.': caseField = f' case=<b>{CNTR_CASE_NAME_DICT[case]}</b>'
                if gender!='.': genderField = f' gender=<b>{CNTR_GENDER_NAME_DICT[gender]}</b>'
                if number!='.': numberField = f' number=<b>{CNTR_NUMBER_NAME_DICT[number]}</b>' # or № ???
            translation = '<small>(no English gloss here)</small>' if glossWords=='-' else f'''English gloss=‘<b>{formattedGlossWords.replace('_','<span class="ul">_</span>')}</b>’'''
            capsField = f' <small>(Caps={glossCaps})</small>' if glossCaps else ''

            # Add pointers to people, locations, etc.
            semanticExtras = ''
            if tagsStr:
                for semanticTag in tagsStr.split( ';' ):
                    tagPrefix, tag = semanticTag[0], semanticTag[1:]
                    # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
                    if tagPrefix == 'P':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../P/{tag}.htm#Top">{tag}</a>'''
                    elif tagPrefix == 'L':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../L/{tag}.htm#Top">{tag}</a>'''
                    elif tagPrefix == 'Y':
                        year = tag
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Year={year}{' AD' if int(year)>0 else ''}'''
                    elif tagPrefix == 'T':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}TimeSeries={tag}'''
                    elif tagPrefix == 'E':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Event={tag}'''
                    elif tagPrefix == 'G':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Group={tag}'''
                    elif tagPrefix == 'F':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Referred to from <a title="Go to referent word" href="{tag}.htm#Top">Word #{tag}</a>'''
                    elif tagPrefix == 'R':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Refers to <a title="Go to referred word" href="{tag}.htm#Top">Word #{tag}</a>'''
                    else:
                        logging.critical( f"Unknown '{tagPrefix}' word tag in {n}: {columns_string}")
                        unknownTag
            lemmaLink = f'<a title="View Greek root word" href="../G/{lemma}.htm#Top">{lemma}</a>'
            lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][lemma] )
            wordGlossesList = sorted( state.OETRefData['formGlossesDict'][(greek,morphology)] )

            prevLink = f'<b><a title="Previous word" href="{n-1}.htm#Top">←</a></b> ' if n>1 else ''
            nextLink = f' <b><a title="Next word" href="{n+1}.htm#Top">→</a></b>' if n<len(state.OETRefData['word_table']) else ''
            oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbb}{NARROW_NON_BREAK_SPACE}{C}</a>'''
            parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}pa/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
            interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
            html = f'''{'' if probability else '<div class="unusedWord">'}<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Wordlink #{n}{'' if probability else ' <small>(Unused Greek word variant)</small>'}</h1>
<p class="pNav">{prevLink}<b>{greek}</b>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
<p class="link"><a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?{CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {ourTidyBBB} {C}:{V}</a>
 {probabilityField if TEST_MODE else ''}<b>{greek}</b> ({transliterate_Greek(greek)}) {translation}{capsField if TEST_MODE else ''}
 Strongs=<a title="Goes to Strongs dictionary" href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a> <small>Lemma={lemmaLink}</small><br>
 {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}{f'<br>  {semanticExtras}' if semanticExtras else ''}</p>
<p class="note"><small>Note: With the help of a companion website, these word pages enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>{'' if probability else f'{NEWLINE}</div><!--unusedWord-->'}'''

            if probability: # Now list all the other places where this same Greek word is used
                # other_count = 0
                thisWordNumberList = state.OETRefData['formUsageDict'][(greek,morphology)]
                if len(thisWordNumberList) > 100: # too many to list
                    maxWordsToShow = 40
                    html = f'{html}\n<h2>Showing the first {maxWordsToShow} out of ({len(thisWordNumberList)-1:,}) uses of word form {greek} <small>({tidyMorphology})</small> in the NT</h2>'
                    if len(wordGlossesList)>1:
                        html = f'''{html}\n<p class="summary">The word form ‘{greek}’ <small>({tidyMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [glossWords], f"{wordGlossesList}  vs {[glossWords]}"
                        html = f'{html}\n<p class="summary">The word form ‘{greek}’ <small>({tidyMorphology})</small> is always and only glossed as ‘<b>{glossWords}</b>’.</p>'
                else: # we can list all uses of the word
                    maxWordsToShow = 100
                    if len(thisWordNumberList) == 1:
                        html = f'{html}\n<h2>Only use of word form {greek} <small>({tidyMorphology})</small> in the NT</h2>'
                    else:
                        html = f'{html}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of word form {greek} <small>({tidyMorphology})</small> in the NT</h2>'
                    if len(wordGlossesList)>1:
                        html = f'''{html}\n<p class="summary">The word form ‘{greek}’ <small>({tidyMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [formattedGlossWords], f"{n} {BBB} {C}:{V} {greek=} {morphology=}: {wordGlossesList}  vs {[formattedGlossWords]}"
                        html = f'{html}\n<p class="summary">The word form ‘{greek}’ <small>({tidyMorphology})</small> is always and only glossed as ‘<b>{formattedGlossWords}</b>’.</p>'
                displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
                for oN in thisWordNumberList:
                    if oN==n: continue # don't duplicate the word we're making the page for
                    oWordRef, _oGreek, _oLemma, oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, _oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                    oFormattedGlossWords = oGlossWords \
                                            .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                            .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                            .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
                    oBBB, oCVW = oWordRef.split( '_', 1 )
                    oC, oVW = oCVW.split( ':', 1 )
                    oV, oW = oVW.split( 'w', 1 )
                    oTidyBBB = tidyBBB( oBBB )
                    # if other_count == 0:
                    translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''English gloss=‘<b>{oFormattedGlossWords.replace('_','<span class="ul">_</span>')}</b>’'''
                    html = f'''{html}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">OET {oTidyBBB} {oC}:{oV}</a> {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?{CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>''' \
if oBBB in state.preloadedBibles['OET-RV'] else f'''{html}\n<p class="wordLine">OET {oTidyBBB} {oC}:{oV} {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?{CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
                    # other_count += 1
                    # if other_count >= 120:
                    #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                    #     break
                    displayCounter += 1
                    if displayCounter >= maxWordsToShow: break
                if len(lemmaGlossesList) > len(wordGlossesList):
                    html = f'''{html}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLink}’ have {len(lemmaGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>'''

            # Now put it all together
            html = makeTop( level, None, 'word', None, state ) \
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}NT Word ‘{greek}’" ) \
                                    .replace( '__KEYWORDS__', 'Bible, word' ) \
                                    .replace( 'pa/"', f'pa/{BBB}/C{C}V{V}.htm#Top"' ) \
                                + html + makeBottom( level, 'word', state )
            with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
                html_output_file.write( html )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
# end of createOETReferencePages.make_word_pages


def make_Greek_lemma_pages( level:int, outputFolderPath:Path, state ) -> None:
    """
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"make_Greek_lemma_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making {len(state.OETRefData['lemmaDict']):,} lemma pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    lemmaList = sorted( [lemma for lemma in state.OETRefData['lemmaDict']] )

    # Now make a page for each Greek lemma (including the variants not used in the translation)
    for ll, lemma in enumerate( lemmaList ):
        # print( ll, lemma )
        lemmaRowsList = state.OETRefData['lemmaDict'][lemma]
        lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][lemma] )
        lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][lemma] )
        def getFirstWordNumber(grk,morph): return state.OETRefData['formUsageDict'][(grk,morph)][0]

        output_filename = f'{lemma}.htm'

        prevLink = f'<b><a title="Previous lemma" href="{lemmaList[ll-1]}.htm#Top">←</a></b> ' if ll>0 else ''
        nextLink = f' <b><a title="Next lemma" href="{lemmaList[ll+1]}.htm#Top">→</a></b>' if ll<len(lemmaList)-1 else ''
        html = f'''<h1 id="Top">Greek root word (lemma) ‘{lemma}’</h1>
<p class="pNav">{prevLink}<b>{lemma}</b>{nextLink}</p>
<p class="summary">This root form (lemma) is used in {len(lemmaFormsList):,} different forms in the NT: {', '.join([f'<a title="View Greek word form" href="../W/{getFirstWordNumber(grk,morph)}.htm#Top">{grk}</a> <small>({morph[4:] if morph.startswith("....") else morph})</small>' for grk,morph in lemmaFormsList])}.</p>
<p class="summary">It is glossed in {len(lemmaGlossesList):,}{'' if len(lemmaGlossesList)==1 else ' different'} way{'' if len(lemmaGlossesList)==1 else 's'}: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>
'''

        if len(lemmaRowsList) > 100: # too many to list
            maxWordsToShow = 40
            html = f'{html}\n<h2>Showing the first {maxWordsToShow} out of ({len(lemmaRowsList)-1:,}) uses of Greek root word (lemma) ‘{lemma}’ in the NT</h2>'
        else: # we can list all uses of the word
            maxWordsToShow = 100
            html = f'''{html}\n<h2>Have {len(lemmaRowsList):,} {'use' if len(lemmaRowsList)==1 else 'uses'} of Greek root word (lemma) ‘{lemma}’ in the NT</h2>'''
        for displayCounter,oN in enumerate( lemmaRowsList, start=1 ):
            oWordRef, oGreek, oLemma, oGlossWords, oGlossCaps,oProbability, oExtendedStrongs, oRoleLetter, oMorphology, oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
            oFormattedGlossWords = oGlossWords \
                                    .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                                    .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                                    .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
            oBBB, oCVW = oWordRef.split( '_', 1 )
            oC, oVW = oCVW.split( ':', 1 )
            oV, oW = oVW.split( 'w', 1 )
            oTidyBBB = tidyBBB( oBBB )
            oTidyMorphology = oMorphology[4:] if oMorphology.startswith('....') else oMorphology
            # if other_count == 0:
            translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''English gloss=‘<b>{oFormattedGlossWords.replace('_','<span class="ul">_</span>')}</b>’'''
            html = f'''{html}\n<p class="lemmaLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">OET {oTidyBBB} {oC}:{oV}</a> Greek word=<b><a title="Go to word page" href="../W/{oN}.htm#Top">{oGreek}</a></b> ({transliterate_Greek(oGreek)}) <small>Morphology={oTidyMorphology}</small> {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?{CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
            # other_count += 1
            # if other_count >= 120:
            #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
            #     break
            if displayCounter >= maxWordsToShow: break

        # Now put it all together
        html = makeTop( level, None, 'lemma', None, state ) \
                                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek lemma ‘{lemma}’" ) \
                                .replace( '__KEYWORDS__', 'Bible, word' ) \
                            + html + makeBottom( level, 'lemma', state )
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
# end of createOETReferencePages.make_Greek_lemma_pages


def make_person_pages( level:int, outputFolderPath:Path, state ) -> int:
    """
    Make pages for all the words to link to.

    There's almost identical code in createOETReferencePages() in OpenBibleData createOETReferencePages.py (sadly)
    """
    from createSitePages import TEST_MODE
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making person pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    with open( THEOGRAPHIC_INPUT_FOLDER_PATH.joinpath( 'normalised_People.json' ), 'rb' ) as people_file:
        peopleDict = json.load( people_file )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded {len(peopleDict):,} person entries." )

    # Firstly, make a list of all the keys
    peopleKeys = []
    for personKey in peopleDict:
        if personKey == '__HEADERS__': continue
        if personKey == '__COLUMN_HEADERS__': continue
        peopleKeys.append( personKey )

    # Now make a page for each person
    for n,(personKey,entry) in enumerate( peopleDict.items() ):
        if personKey == '__HEADERS__': continue
        if personKey == '__COLUMN_HEADERS__': continue

        previousLink = f'''<a title="Previous person" href="{peopleKeys[n-3][1:]}.htm#Top">←</a>''' if n>3 else ''
        nextLink = f'''<a title="Next person" href="{peopleKeys[n-1][1:]}.htm#Top">→</a>''' if n<len(peopleDict)-1 else ''

        personName = entry['displayTitle']
        bornStr = f"Born: {entry['birthYear']}" if entry['birthYear'] else ''
        diedStr = f"Died: {entry['deathYear']}" if entry['deathYear'] else ''

        bodyHtml = f'''<h1>{personName.replace( "'", '’' )}</h1>
<p class="personName">{livenMD(level, entry['dictText'])}</p>
<p class="personGender">{entry['gender']}{f' {bornStr}' if bornStr else ''}{f' {diedStr}' if diedStr else ''}</p>'''

        # Now put it all together
        output_filename = f"{personKey[1:]}.htm#Top"
        html = f'''{makeTop( level, None, 'person', None, state )
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{personName}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'person', state )}'''
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
# end of createOETReferencePages.make_person_pages function


def make_location_pages( level:int, outputFolderPath:Path, state ) -> int:
    """
    Make pages for all the words to link to.

    There's almost identical code in createOETReferencePages() in OpenBibleData createOETReferencePages.py (sadly)
    """
    from createSitePages import TEST_MODE
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making location pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    with open( THEOGRAPHIC_INPUT_FOLDER_PATH.joinpath( 'normalised_Places.json' ), 'rb' ) as locations_file:
        locationsDict = json.load( locations_file )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded {len(locationsDict):,} location entries." )

    # Firstly, make a list of all the keys
    placeKeys = []
    for placeKey in locationsDict:
        if placeKey == '__HEADERS__': continue
        if placeKey == '__COLUMN_HEADERS__': continue
        placeKeys.append( placeKey )

    # Now make a page for each location
    for n,(placeKey,entry) in enumerate( locationsDict.items() ):
        if placeKey == '__HEADERS__': continue
        if placeKey == '__COLUMN_HEADERS__': continue

        previousLink = f'''<a title="Previous location" href="{placeKeys[n-3][1:]}.htm#Top">←</a>''' if n>3 else ''
        nextLink = f'''<a title="Next location" href="{placeKeys[n-1][1:]}.htm#Top">→</a>''' if n<len(locationsDict)-1 else ''

        placeName = entry['displayTitle']
        commentStr = f" {entry['comment']}" if entry['comment'] else ''

        bodyHtml = f'''<h1>{placeName.replace( "'", '’' )}</h1>
<p class="locationName">{livenMD(level, entry['dictText'])}</p>
<p class="locationType">{entry['featureType']}{f"/{entry['featureSubType']}" if entry['featureSubType'] else ''}{f' {commentStr}' if commentStr else ''}</p>
<p class="locationVersions">KJB=‘{entry['kjvName']}’ ESV=‘{entry['esvName']}’</p>'''

        # Now put it all together
        output_filename = f"{placeKey[1:]}.htm#Top"
        html = f'''{makeTop( level, None, 'location', None, state )
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{placeName}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'location', state )}'''
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
# end of createOETReferencePages.make_location_pages function


mdLinkRegex = re.compile( '\\[(.+?)\\]\\((.+?)\\)' )
def livenMD( level:int, mdText:str ) -> str:
    """
    Take markdown style links like '[Gen. 35:16](/gen#Gen.35.16)'
        from person and location pages
        and convert them to HTML links.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenMD( {level}, {mdText[:140]}… )" )

    # Firstly, try to improve the overall formatting
    mdText = mdText.replace( '\n\n', '</p><p class="markdown">' ).replace( '\n', '<br>' )
    mdText = mdText.replace( "'", '’' ) # Improve apostrophes

    # Now liven links
    count = 0
    searchStartIndex = 0
    while True: # Look for links that we could maybe liven
        match = mdLinkRegex.search( mdText, searchStartIndex )
        if not match:
            break
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {match=} {match.groups()=}" )
        readableRef, mdLinkTarget = match.group(1), match.group(2)
        mdLinkTarget = mdLinkTarget.split( '#', 1 )[1]
        if mdLinkTarget.count( '.' ) == 2: # Then it's almost certainly an OSIS B/C/V ref
            OSISBkCode, C, V = mdLinkTarget.split( '.' )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISBkCode )
            ourLinkTarget = f"{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}V{V}"
        else:
            assert mdLinkTarget.count( '.' ) == 1 # Then it's almost certainly an OSIS B/C ref
            OSISBkCode, C = mdLinkTarget.split( '.' )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISBkCode )
            ourLinkTarget = f'{BBB}.htm#C{C}'
        ourLink = f'<a title="View OET reference" href="{ourLinkTarget}">{readableRef}</a>'
        mdText = f'''{mdText[:match.start()]}{ourLink}{mdText[match.end():]}'''
        searchStartIndex = match.end() + 10 # We've added at least that many characters
        count += 1
    return mdText
# end of createOETReferencePages.livenMD function


linkedWordTitleRegex = re.compile( '="§(.+?)§"' ) # We inserted those § markers in our titleTemplate above
linkedWordNumberRegex = re.compile( '/W/([1-9][0-9]{0,5}).htm' ) # /W/ is the words folder
def livenOETWordLinks( bibleObject:ESFMBible, BBB:str, givenEntryList:InternalBibleEntryList, hrefTemplate:str, state ) -> InternalBibleEntryList:
    """
    Livens ESFM wordlinks in the OET versions (i.e., the words with ¦ numbers suffixed to them).

    Then add the transliteration to the title="§«Greek»§" popup.
    """
    # Liven the word links using the BOS function
    revisedEntryList, _wordList = bibleObject.livenESFMWordLinks( BBB, givenEntryList, hrefTemplate, '§«Greek»§' )

    # Now add the transliteration to the Greek HTML title popups
    updatedVerseList = InternalBibleEntryList()
    for n, entry in enumerate( revisedEntryList ):
        originalText = entry.getOriginalText()
        if originalText is None or '§' not in originalText:
            updatedVerseList.append( entry )
            continue
        # If we get here, we have at least one ESFM wordlink row number in the text
        # print( f"createOETReferencePages {n}: '{originalText}'")
        searchStartIndex = 0
        count = 0
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
            lemma = wordRow.split('\t')[2]

            newTitleGuts = f'''="{greekWord} ({transliteratedWord}){'' if lemma==transliteratedWord else f" from {lemma}"}"'''
            originalText = f'''{originalText[:titleMatch.start()]}{newTitleGuts}{originalText[titleMatch.end():]}'''

            searchStartIndex = wordnumberMatch.end() + len(newTitleGuts) - len(greekWord) - 5 # We've added at least that many characters
            count += 1
        if count > 0:
            # print( f"  Now '{originalText}'")
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Added {count:,} {bibleObject.abbreviation} {BBB} transliterations to Greek titles." )
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
# end of createOETReferencePages.livenMD function

def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETReferencePages object
    pass
# end of createOETReferencePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETReferencePages object
    pass
# end of createOETReferencePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createOETReferencePages.py
