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
    2023-08-30 Add nomina sacra to word pages
    2023-10-09 Add role letter to word pages
    2023-10-13 For single-use Greek words, append a note if it's also the only use of that lemma.
    2023-10-16 Add other Greek words with similar glosses
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

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek

from html import makeTop, makeBottom
from Bibles import tidyBBB


LAST_MODIFIED_DATE = '2023-12-14' # by RJH
SHORT_PROGRAM_NAME = "createOETReferencePages"
PROGRAM_NAME = "OpenBibleData createOETReferencePages functions"
PROGRAM_VERSION = '0.47'
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
CNTR_TENSE_NAME_DICT = {'P':'present', 'I':'imperfect', 'F':'future', 'A':'aorist', 'E':'perfect', 'L':'pluperfect', 'U':'U', 'e':'per'}
CNTR_VOICE_NAME_DICT = {'A':'active', 'M':'middle', 'P':'passive', 'p':'pass', 'm':'mid', 'a':'act'}
CNTR_PERSON_NAME_DICT = {'1':'1st', '2':'2nd', '3':'3rd', 'g':'g'}
CNTR_CASE_NAME_DICT = {'N':'nominative', 'G':'genitive', 'D':'dative', 'A':'accusative', 'V':'vocative', 'g':'gen', 'n':'nom', 'a':'acc', 'd':'dat', 'v':'voc', 'U':'U'}
CNTR_GENDER_NAME_DICT = {'M':'masculine', 'F':'feminine', 'N':'neuter', 'm':'masc', 'f':'fem', 'n':'neu'}
CNTR_NUMBER_NAME_DICT = {'S':'singular', 'P':'plural', 's':'sg', 'p':'pl'}
# See https://www.publiconsulting.com/wordpress/ancientgreek/chapter/16-prepositions/ for a concise list
KNOWN_GREEK_PREFIXES = ('a','amfi','ana','anti','apo',
            'dia','eis','ek','en','epi','ex',
            'huper','hupo','kata','meta',
            'para','peri','pro','pros',
            'sun') # In the LEMMA character set

SIMILAR_GLOSS_WORDS_TABLE = [
    (('ancestor','ancestors'),('patriarch','patriarchs','elders',)),
    (('anger',),('wrath',)),
    (('barley',),('grain','wheat')),
    (('blessed',),('blessing','blessings','bless','blesses','cursed')),
    (('boat','boats'),('ship','ships')),
    (('body','bodies'),('flesh',)),
    (('child','children'),('son','sons','daughter','daughters')),
    (('clean',),('moral','permissible','pure','unclean')),
    (('cry','cries'),('weep','weeps')),
    (('daughter','daughters'),('child','children')),
    (('disbelief',),('unbelief','disbelieve')),
    (('few',),('remnant','remainder')),
    (('flesh',),('body','bodies','carnal','meat')),
    (('fleshly',),('worldly',)),
    (('fulfilment','fulfillment'),('fullness',)),
    (('fullness',),('fulfillment','fulfilment')),
    (('gift','gifts'),('reward','rewards')),
    (('glorious',),('honoured','honored','glory')),
    (('glory',),('honour','honor','glorious')),
    (('grain',),('wheat','barley')),
    (('heart','hearts'),('mind','minds')),
    (('holiness',),('purity',)),
    (('house_servant','house_servants'),('servant','servants','slave','slaves')),
    (('immediately',),('suddenly',)),
    (('Jesus',),('Joshua','Yeshua')),
    (('joined_together',),('united',)),
    (('Joshua',),('Jesus','Yeshua')),
    (('logical',),('sensible','logic','logically')),
    (('lip','lips'),('mouth','mouths')),
    (('mind','minds'),('heart','hearts')),
    (('mouth','mouths'),('lips','lip','tongue')),
    (('pagan','pagans'),('Gentile','Gentiles','Greeks')),
    (('purity',),('holiness',)),
    (('remnant',),('remainder','few')),
    (('reward','rewards'),('gift','gifts')),
    (('riches',),('wealth',)),
    (('Sabbath','Sabbaths'),('week','weeks','rest')),
    (('scroll','scrolls'),('book','books','scipture','scriptures')),
    (('seed',),('sperm',)),
    (('servant','servants'),('slave','slaves','house_servant','house_servants')),
    (('ship','ships'),('boat','boats')),
    (('slave','slaves'),('servant','house_servant','servants','house_servants')),
    (('son','sons'),('child','children')),
    (('sperm',),('seed',)),
    (('suddenly',),('immediately',)),
    (('unclean',),('immoral','prohibited','impure','clean')),
    (('united',),('joined_together',)),
    (('week','weeks'),('Sabbath','Sabbaths')),
    (('wealth',),('riches',)),
    (('weep','weeps'),('cry','cries')),
    (('wheat',),('grain','barley')),
    (('worldly',),('fleshly',)),
    (('wrath',),('anger',)),
    ]
SIMILAR_GLOSS_WORDS_DICT = {} # We create this dict at load time as we check the above table
for firstWords,similarWords in SIMILAR_GLOSS_WORDS_TABLE:
    assert isinstance(firstWords,tuple) and isinstance(similarWords,tuple)
    for firstWord in firstWords:
        assert isinstance( firstWord, str )
        assert firstWord not in similarWords # No duplicates
        assert firstWord not in SIMILAR_GLOSS_WORDS_DICT # No duplicates
        fwList = list( firstWords )
        fwList.remove( firstWord )
        otherFirstWords = tuple( fwList )
        expandedSimilarWords = otherFirstWords + similarWords
        SIMILAR_GLOSS_WORDS_DICT[firstWord] = otherFirstWords + similarWords
    for similarWord in similarWords:
        assert isinstance( similarWord, str )
        assert similarWords.count(similarWord) == 1 # No duplicates


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
    state.OETRefData['glossWordDict'] = defaultdict(list)
    state.OETRefData['lemmaGreekDict'] = {}
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'JHN' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma
        elif state.OETRefData['formUsageDict']: break # Must have already finished John
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'MRK' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma
        elif columns_string.startswith( 'LUK' ): break # Must have already finished Mark
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if not columns_string.startswith( 'JHN' ) and not columns_string.startswith( 'MRK' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma

    make_Greek_word_pages( level+1, outputFolderPath.joinpath( 'W/' ), state )
    make_Greek_lemma_pages( level+1, outputFolderPath.joinpath( 'G/' ), state )

    make_person_pages( level+1, outputFolderPath.joinpath( 'P/' ), state )
    make_location_pages( level+1, outputFolderPath.joinpath( 'L/' ), state )

    del state.OETRefData # No longer needed
    return True
# end of createOETReferencePages.createOETReferencePages


def formatSpansGlossWords( glossWords:str ) -> str:
    """
    Put HTML spans about the various parts of the gloss Words string
        to replace our pre, helper, and post special character markers.
    """
    return glossWords \
                .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
# end of createOETReferencePages.formatSpansGlossWords


NUM_BEFORE_AND_AFTER = 3
def formatContextSpansGlossWords( rowNum:int, state ) -> str:
    """
    Get this and previous gloss words in context.

    TODO: Need to take GlossOrder into account
    """
    fOriginalWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][rowNum].split( '\t' )
    # print( f"formatContextSpansGlossWords( {rowNum:,} ) at {fOriginalWordRef}" )
    fOriginalBCV = fOriginalWordRef.split( 'w', 1 )[0]

    glossWordsList = [f'<b>{formatSpansGlossWords(fGlossWords)}</b>']

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN -= 1
        if fN < 1: break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability is 'None': fProbability = None
        if fProbability and fGlossWords[0]!='¬':
            glossWordsList.insert( 0, formatSpansGlossWords(fGlossWords) )
            rowCount += 1

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN += 1
        if fN >= len(state.OETRefData['word_table']): break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability is 'None': fProbability = None
        if fProbability and fGlossWords[0]!='¬':
            glossWordsList.append( formatSpansGlossWords(fGlossWords) )
            rowCount += 1

    return ' '.join( glossWordsList )
# end of createOETReferencePages.formatSpansGlossWords


def make_Greek_word_pages( level:int, outputFolderPath:Path, state ) -> None:
    """
    """
    from createSitePages import TEST_MODE, ALL_TEST_REFERENCE_PAGES
    fnPrint( DEBUGGING_THIS_MODULE, f"make_Greek_word_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Checking {len(state.OETRefData['word_table'])-1:,} word pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    # Now make a page for each Greek word (including the variants not used in the translation)
    numWordPagesMade = 0
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        # print( n, columns_string )
        output_filename = f'{n}.htm'
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        if columns_string: # not a blank line (esp. at end)
            ref, greekWord, SRLemma, _GrkLemma, glossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = columns_string.split( '\t' )
            formattedGlossWords = formatSpansGlossWords( glossWordsStr )
            formattedContextGlossWords = formatContextSpansGlossWords( n, state )
            mainGlossWord = None
            for someGlossWord in glossWordsStr.split( ' '):
                if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                    assert not mainGlossWord
                    mainGlossWord = someGlossWord
            if extendedStrongs == 'None': extendedStrongs = None
            if roleLetter == 'None': roleLetter = None
            if morphology == 'None': morphology = None

            BBB, CVW = ref.split( '_', 1 )
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and BBB not in state.preloadedBibles['OET-RV']:
                continue # In some test modes, we only make the relevant word pages
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

            nominaSacraField = 'Marked with <b>Nomina Sacra</b>' if 'N' in glossCaps else ''

            probabilityField = f'<small>(P={probability}%)</small> ' if probability else ''

            # morphologyField = 
            tidyRoleMorphology = tidyMorphology = moodField = tenseField = voiceField = personField = caseField = genderField = numberField = ''
            if morphology:
                # morphologyField = f' Morphology=<b>{morphology}</b>:' # Not currently used since we give all the following information instead
                tidyMorphology = morphology[4:] if morphology.startswith('....') else morphology
                tidyRoleMorphology = f'{roleLetter}-{tidyMorphology}'
                assert len(morphology) == 7, f"Got {ref} '{greekWord}' morphology ({len(morphology)}) = '{morphology}'"
                mood,tense,voice,person,case,gender,number = morphology
                if mood!='.': moodField = f' mood=<b>{CNTR_MOOD_NAME_DICT[mood]}</b>'
                if tense!='.': tenseField = f' tense=<b>{CNTR_TENSE_NAME_DICT[tense]}</b>'
                if voice!='.': voiceField = f' voice=<b>{CNTR_VOICE_NAME_DICT[voice]}</b>'
                if person!='.': personField = f' person=<b>{CNTR_PERSON_NAME_DICT[person]}</b>'
                if case!='.': caseField = f' case=<b>{CNTR_CASE_NAME_DICT[case]}</b>'
                if gender!='.': genderField = f' gender=<b>{CNTR_GENDER_NAME_DICT[gender]}</b>'
                if number!='.': numberField = f' number=<b>{CNTR_NUMBER_NAME_DICT[number]}</b>' # or № ???
            else:
                tidyRoleMorphology = roleLetter
            translation = '<small>(no English gloss here)</small>' if glossWordsStr=='-' else f'''‘{formattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
            capsField = f' <small>(Caps={glossCaps})</small>' if glossCaps else ''

            # Add pointers to people, locations, etc.
            semanticExtras = nominaSacraField
            if tagsStr:
                for semanticTag in tagsStr.split( ';' ):
                    tagPrefix, tag = semanticTag[0], semanticTag[1:]
                    # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
                    if tagPrefix == 'P':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../P/{tag}.htm#Top">{tag}</a>'''
                    elif tagPrefix == 'L':
                        semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../L/{tag}.htm#Top">{tag}</a>'''
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
            lemmaLink = f'<a title="View Greek root word" href="../G/{SRLemma}.htm#Top">{SRLemma}</a>'
            lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][SRLemma] )
            wordGlossesList = sorted( state.OETRefData['formGlossesDict'][(greekWord,roleLetter,morphology)] )

            prevN = nextN = None
            if n > 1:
                if TEST_MODE and not ALL_TEST_REFERENCE_PAGES: 
                    for nN in range( n-1, 0, -1 ):
                        nWordRef = state.OETRefData['word_table'][nN].split( '\t', 1 )[0]
                        nBBB = nWordRef.split( '_', 1 )[0]
                        if nBBB in state.preloadedBibles['OET-RV']:
                            prevN = nN
                            break
                else: prevN = n-1
            if n<len(state.OETRefData['word_table']):
                if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                    for nN in range( n+1, len(state.OETRefData['word_table']) ):
                        nWordRef = state.OETRefData['word_table'][nN].split( '\t', 1 )[0]
                        nBBB = nWordRef.split( '_', 1 )[0]
                        if nBBB in state.preloadedBibles['OET-RV']:
                            nextN = nN
                            break
                else: nextN = n+1
            prevLink = f'<b><a title="Previous word" href="{prevN}.htm#Top">←</a></b> ' if prevN else ''
            nextLink = f' <b><a title="Next word" href="{nextN}.htm#Top">→</a></b>' if nextN else ''
            oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbb}{NARROW_NON_BREAK_SPACE}{C}</a>'''
            parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}pa/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
            interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
            html = f'''{'' if probability else '<div class="unusedWord">'}<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Wordlink #{n}{'' if probability else ' <small>(Unused Greek word variant)</small>'}</h1>
<p class="pNav">{prevLink}<b>{greekWord}</b>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
<p class="link"><a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {ourTidyBBB} {C}:{V}</a>
 {probabilityField if TEST_MODE else ''}<b>{greekWord}</b> ({transliterate_Greek(greekWord)}) {translation}{capsField if TEST_MODE else ''}
 Strongs=<a title="Goes to Strongs dictionary" href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a> <small>Lemma={lemmaLink}</small><br>
 {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}{f'<br>  {semanticExtras}' if semanticExtras else ''}</p>
<p class="note"><small>Note: With the help of a companion website, these word pages enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>{'' if probability else f'{NEWLINE}</div><!--unusedWord-->'}'''

            if probability: # Now list all the other places where this same Greek word is used
                # other_count = 0
                thisWordNumberList = state.OETRefData['formUsageDict'][(greekWord,roleLetter,morphology)]
                if len(thisWordNumberList) > 100: # too many to list
                    maxWordsToShow = 50
                    html = f'{html}\n<h2>Showing the first {maxWordsToShow} out of ({len(thisWordNumberList)-1:,}) uses of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                    if len(wordGlossesList)>1:
                        html = f'''{html}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [glossWordsStr], f"{wordGlossesList}  vs {[glossWordsStr]}"
                        html = f'{html}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{glossWordsStr}</b>’.</p>'
                else: # we can list all uses of the word
                    maxWordsToShow = 100
                    if len(thisWordNumberList) == 1:
                        html = f'{html}\n<h2>Only use of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                        # lemmaRowsList = state.OETRefData['lemmaDict'][lemma]
                        # lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][lemma] )
                        # if len(lemmaRowsList) == 1:
                        #     # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {lemmaRowsList=} {lemmaFormsList=} {lemmaGlossesList=}" )
                        #     assert len(lemmaFormsList) == 1
                        #     assert len(lemmaGlossesList) == 1
                        #     html = f'''{html.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Greek originals.</p>'''
                    else:
                        html = f'{html}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                    if len(wordGlossesList)>1:
                        html = f'''{html}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [formattedGlossWords], f"{n} {BBB} {C}:{V} {greekWord=} {roleLetter=} {morphology=}: {wordGlossesList}  vs {[formattedGlossWords]}"
                        html = f'{html}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{formattedGlossWords}</b>’.</p>'
                displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
                for oN in thisWordNumberList:
                    if oN==n: continue # don't duplicate the word we're making the page for
                    oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, _oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                    oFormattedContextGlossWords = formatContextSpansGlossWords( oN, state )
                    oBBB, oCVW = oWordRef.split( '_', 1 )
                    oC, oVW = oCVW.split( ':', 1 )
                    oV, oW = oVW.split( 'w', 1 )
                    oTidyBBB = tidyBBB( oBBB )
                    # if other_count == 0:
                    translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''‘{oFormattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
                    html = f'''{html}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBB} {oC}:{oV}</a>''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>''' \
                        if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else \
                        f'''{html}\n<p class="wordLine">{oTidyBBB} {oC}:{oV}''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
                    # other_count += 1
                    # if other_count >= 120:
                    #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                    #     break
                    displayCounter += 1
                    if displayCounter >= maxWordsToShow: break
                if len(lemmaGlossesList) > len(wordGlossesList):
                    html = f'''{html}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLink}’ have {len(lemmaGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>'''
                elif len(thisWordNumberList) == 1:
                    lemmaRowsList = state.OETRefData['lemmaDict'][SRLemma]
                    lemmaFormsList = state.OETRefData['lemmaFormsDict'][SRLemma]
                    if len(lemmaRowsList) == 1:
                        # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {lemmaRowsList=} {lemmaFormsList=} {lemmaGlossesList=}" )
                        assert len(lemmaFormsList) == 1
                        assert len(lemmaGlossesList) == 1
                        html = f'''{html.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>', 1)}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> ‘{SRLemma}’ in the Greek originals.</p>'''

                if mainGlossWord not in ( # Ignore the most common words
                    'God','Jesus','Lord', 'Joshua',
                    'the','¬the','that','this','which','¬which','these',
                    'and','for','but','if','as','therefore','in_order_that','because',
                    'is','also',
                    'to','in','with','from','by','on','into',
                    'not','all','saying','said','having',
                    'what','who',
                    'you', 'he','we','they','I','she','you_all',
                           'him','us','them','me','her',
                    'your','his','our','their','my',):
                    # List other words that are glossed similarly
                    try:
                        similarWords = (mainGlossWord,) + SIMILAR_GLOSS_WORDS_DICT[mainGlossWord]
                        # print( f"      {mainGlossWord=} {similarWords=}")
                    except KeyError: similarWords = (mainGlossWord,)
                    extraHTMLList = []
                    extraWordSet, extraLemmaSet = set(), set()
                    for similarWord in similarWords:
                        nList = state.OETRefData['glossWordDict'][similarWord]
                        # print( f'''    {n} {ref} {greekWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nList[:8]=}{'…' if len(nList)>8 else ''}''' )
                        if len(nList) > 1:
                            if similarWord==mainGlossWord: assert n in nList
                            if len(nList)>400: print( f"EXCESSIVE {len(nList):,} entries for '{mainGlossWord}'")
                            for thisN in nList:
                                if thisN == n: continue # That's the current word row
                                eWordRef, eGreekWord, eSRLemma, _eGrkLemma, eGlossWordsStr, _eGlossCaps, _eProbability, _eExtendedStrongs, eRoleLetter, eMorphology, _eTagsStr = state.OETRefData['word_table'][thisN].split( '\t' )
                                if eRoleLetter == 'None': eRoleLetter = None
                                if eMorphology == 'None': eMorphology = None
                                if eGreekWord!=greekWord or eRoleLetter!=roleLetter or eMorphology!=morphology:
                                    eBBB, eCVW = eWordRef.split( '_', 1 )
                                    eC, eVW = eCVW.split( ':', 1 )
                                    eV, eW = eVW.split( 'w', 1 )
                                    eTidyBBB = tidyBBB( eBBB )

                                    eGreekPossibleLink = f'<a title="Go to word page" href="{thisN}.htm#Top">{eGreekWord}</a>' if ALL_TEST_REFERENCE_PAGES or eBBB in state.preloadedBibles['OET-RV'] else eGreekWord
                                    eLemmaLink = f'<a title="View Greek root word" href="../G/{eSRLemma}.htm#Top">{eSRLemma}</a>' if eSRLemma!=SRLemma else ''
                                    eFormattedContextGlossWords = formatContextSpansGlossWords( thisN, state )
                                    eTidyRoleMorphology = eTidyMorphology = '' #= eMoodField = eTenseField = eVoiceField = ePersonField = eCaseField = eGenderField = eNumberField = ''
                                    if eMorphology:
                                        assert len(eMorphology) == 7, f"Got {eWordRef} '{eGreekWord}' morphology ({len(eMorphology)}) = '{eMorphology}'"
                                        eTidyMorphology = eMorphology[4:] if eMorphology.startswith('....') else eMorphology
                                        eTidyRoleMorphology = f'{eRoleLetter}-{eTidyMorphology}'
                                    else:
                                        eTidyRoleMorphology = eRoleLetter
                                    extraHTMLList.append( f'''<p class="wordLine"><a title="View OET {eTidyBBB} text" href="{'../'*level}OET/byC/{eBBB}_C{eC}.htm#C{eC}V{eV}">{eTidyBBB} {eC}:{eV}</a>'''
f''' ‘{eGreekPossibleLink}’ <small>({eTidyRoleMorphology})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}'''
f''' ‘{eFormattedContextGlossWords}’'''
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBBB} {eC}:{eV} word {eW}</a></p>'''
                                        if not TEST_MODE or eBBB in state.preloadedBibles['OET-RV'] else
                                            f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eGreekPossibleLink}’ <small>({eTidyRoleMorphology})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}''' \
f''' ‘{eFormattedContextGlossWords}’''' \
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBBB} {eC}:{eV} word {eW}</a></p>''' )
                                    extraWordSet.add( eGreekPossibleLink )
                                    extraLemmaSet.add( eLemmaLink if eLemmaLink else lemmaLink )
                    if extraHTMLList:
                        html = f'''{html}\n<h2 class="otherGreek">Greek words ({len(extraHTMLList):,}) other than {greekWord} <small>({tidyRoleMorphology})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
                        if len(extraHTMLList) > 10:
                            html = f'''{html}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemmas altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
                        html = f'''{html}\n{NEWLINE.join(extraHTMLList)}'''

            # Now put it all together
            top = makeTop( level, None, 'word', None, state ) \
                            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek word ‘{greekWord}’" ) \
                            .replace( '__KEYWORDS__', 'Bible, word' ) \
                            .replace( 'pa/"', f'pa/{BBB}/C{C}V{V}.htm#Top"' )
            html = f'''{top}{html}
{makeBottom( level, 'word', state )}'''
            with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
                html_output_file.write( html )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(html):,} characters to {output_filename}" )
            numWordPagesMade += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Created {numWordPagesMade:,} word pages." )
# end of createOETReferencePages.make_Greek_word_pages


def make_Greek_lemma_pages( level:int, outputFolderPath:Path, state ) -> None:
    """
    These end up in OBD/rf/G/abc.htm

    TODO: Add related lemma info (not just prefixed ones, but adding synonyms, etc.)
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
        grkLemma = state.OETRefData['lemmaGreekDict'][lemma]
        lemmaRowsList = state.OETRefData['lemmaDict'][lemma]
        lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][lemma] )
        lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][lemma] )
        def getFirstWordNumber(grk:str,roleLetter:str,morph:str): return state.OETRefData['formUsageDict'][(grk,roleLetter,morph)][0]

        output_filename = f'{lemma}.htm'

        prevLink = f'<b><a title="Previous lemma" href="{lemmaList[ll-1]}.htm#Top">←</a></b> ' if ll>0 else ''
        nextLink = f' <b><a title="Next lemma" href="{lemmaList[ll+1]}.htm#Top">→</a></b>' if ll<len(lemmaList)-1 else ''
        html = f'''<h1 id="Top">Greek root word <small>(lemma)</small> ‘{grkLemma}’ ({lemma})</h1>
<p class="pNav">{prevLink}<b>{lemma}</b>{nextLink}</p>
<p class="summary">This root form (lemma) ‘{grkLemma}’ is used in {len(lemmaFormsList):,} different forms in the Greek originals: {', '.join([f'<a title="View Greek word form" href="../W/{getFirstWordNumber(grk,roleLetter,morph)}.htm#Top">{grk}</a> <small>({roleLetter}-{morph[4:] if morph.startswith("....") else morph})</small>' for grk,roleLetter,morph in lemmaFormsList])}.</p>
<p class="summary">It is glossed in {len(lemmaGlossesList):,}{'' if len(lemmaGlossesList)==1 else ' different'} way{'' if len(lemmaGlossesList)==1 else 's'}: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>
'''

        def makeLemmaHTML( thisLemmaStr:str, thisLemmaRowsList ) -> str:
            """
            The guts of making the lemma page
                put into a function so that we can also re-use it for related words
            """
            oRoleSet = set()
            for oN in thisLemmaRowsList:
                _oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, _oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                oRoleSet.add( oRoleLetter )
            # oRoleLetter remains set to the last value added to the set (which is the only value if len(oRoleSet)==1)

            if len(thisLemmaRowsList) > 100: # too many to list
                maxWordsToShow = 50
                lemmaHTML = f"<h2>Showing the first {maxWordsToShow} out of ({len(thisLemmaRowsList)-1:,}) uses of Greek root word <small>(lemma)</small> ‘{thisLemmaStr}’ {f'<small>({CNTR_ROLE_NAME_DICT[oRoleLetter]})</small> ' if len(oRoleSet)==1 else ''}in the Greek originals</h2>"
            else: # we can list all uses of the word
                maxWordsToShow = 100
                lemmaHTML = f"<h2>Have {len(thisLemmaRowsList):,} {'use' if len(thisLemmaRowsList)==1 else 'uses'} of Greek root word <small>(lemma)</small> ‘{thisLemmaStr}’ {f'<small>({CNTR_ROLE_NAME_DICT[oRoleLetter]})</small> ' if len(oRoleSet)==1 else ''}in the Greek originals</h2>"
            for displayCounter,oN in enumerate( thisLemmaRowsList, start=1 ):
                oWordRef, oGreekWord, _oSRLemma, _oGrkLemma, oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                oFormattedContextGlossWords = formatContextSpansGlossWords( oN, state )
                oBBB, oCVW = oWordRef.split( '_', 1 )
                oC, oVW = oCVW.split( ':', 1 )
                oV, oW = oVW.split( 'w', 1 )
                oTidyBBB = tidyBBB( oBBB )
                oTidyMorphology = oMorphology[4:] if oMorphology.startswith('....') else oMorphology
                # if other_count == 0:
                oOETLink = f'''<a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBB} {oC}:{oV}</a>''' \
                                if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] \
                                    else f'{oTidyBBB} {oC}:{oV}'
                oGreekWordLink = f'<a title="Go to word page" href="../W/{oN}.htm#Top">{oGreekWord}</a>' if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else oGreekWord
                translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''‘{oFormattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
                lemmaHTML = f'''{lemmaHTML}\n<p class="lemmaLine">{oOETLink} Greek word=<b>{oGreekWordLink}</b> ({transliterate_Greek(oGreekWord)})''' \
                    f"{f' {CNTR_ROLE_NAME_DICT[oRoleLetter].title()}' if len(oRoleSet)>1 else ''} <small>Morphology={oTidyMorphology}</small>" \
                    f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
                # other_count += 1
                # if other_count >= 120:
                #     lemmaHTML = f'{lemmaHTML}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                #     break
                if displayCounter >= maxWordsToShow: break
            return lemmaHTML
        html = f"{html}\n{makeLemmaHTML(lemma, lemmaRowsList)}"

        # Consider related lemmas, e.g., with or without prefix
        this_extended_lemma_list = [lemma]
        for mm, this_second_lemma in enumerate( lemmaList ):
            if this_second_lemma and len(this_second_lemma)>1 and this_second_lemma not in this_extended_lemma_list:
                prefix = None
                if this_second_lemma.endswith( lemma ):
                    prefix = this_second_lemma[:len(this_second_lemma)-len(lemma)]
                elif lemma.endswith( this_second_lemma ):
                    prefix = lemma[:len(lemma)-len(this_second_lemma)]
                if prefix and len(prefix) < 6:
                    if prefix in KNOWN_GREEK_PREFIXES:
                        # print(f"make_Greek_lemma_pages also got lemma '{this_second_lemma}' with prefix '{prefix}' (cf. '{lemma}')")
                        lemmaRowsList = state.OETRefData['lemmaDict'][this_second_lemma]
                        lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][this_second_lemma] )
                        lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][this_second_lemma] )
                        this_second_lemma_link = f'<a title="Go to lemma page" href="{this_second_lemma}.htm#Top">{this_second_lemma}</a>'
                        if len(this_extended_lemma_list) == 1:
                            html = f"{html}\n<h1>Other possible related lemmas</h1>"
                        html = f'''{html}
<h2>Greek root word <small>(lemma)</small> ‘{this_second_lemma}’ <small>with prefix=‘{prefix}’</small></h2>
{makeLemmaHTML(this_second_lemma_link, lemmaRowsList)}'''
                        this_extended_lemma_list.append( this_second_lemma )
                    # else:
                    #     print(f"make_Greek_lemma_pages ignored potential lemma '{this_second_lemma}' with unrecognised prefix '{prefix}' (cf. '{lemma}')")
        # if len(this_extended_lemma_list) > 1:
        #     print( f"Got {this_extended_lemma_list=}" )

        # Now put it all together
        top = makeTop( level, None, 'lemma', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek lemma ‘{lemma}’" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' )
        html = f'''{top}{html}
{makeBottom( level, 'lemma', state )}'''
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
        output_filename = f"{personKey[1:]}.htm"
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
        output_filename = f"{placeKey[1:]}.htm"
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
