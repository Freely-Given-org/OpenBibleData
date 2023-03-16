#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createWordPages.py
#
# Module handling OpenBibleData createWordPages functions
#
# Copyright (C) 2023 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
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
Module handling createWordPages functions.
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os

# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import load_transliteration_table, transliterate_Greek

from usfm import convertUSFMMarkerListToHtml
from html import do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, removeDuplicateCVids, checkHtml


LAST_MODIFIED_DATE = '2023-03-14' # by RJH
SHORT_PROGRAM_NAME = "createWordPages"
PROGRAM_NAME = "OpenBibleData createWordPages functions"
PROGRAM_VERSION = '0.04'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
# NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '


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
def createOETGreekWordsPages( outputFolderPath:Path, state ) -> bool:
    """
    Make pages for all the words to link to.

    Sadly, there's almost identical code in make_table_pages() in OET convert_OET-LV_to_simple_HTML.py
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETGreekWordsPages( {outputFolderPath}, {state.BibleVersions} )" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there
    load_transliteration_table( 'Greek' )

    lvBible = state.preloadedBibles['OET-LV']
    # print( lvBible.ESFMWordTables.keys() )
    assert len(lvBible.ESFMWordTables) == 1
    word_table = list(lvBible.ESFMWordTables.values())[0]
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}word pages for OET-LV…" )
    columnHeaders = word_table[0]
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Word table column headers = '{columnHeaders}'" )
    assert columnHeaders == 'Ref\tGreek\tGlossWords\tProbability\tStrongsExt\tRole\tMorphology' # If not, probably need to fix some stuff
    for n, columns_string in enumerate( word_table[1:], start=1 ):
        # print( n, columns_string )
        output_filename = f'{n}.htm'
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        if columns_string: # not a blank line (esp. at end)
            ref, greek, glossWords, probability, extendedStrongs, roleLetter, morphology = columns_string.split( '\t' )
            if extendedStrongs == 'None': extendedStrongs = None
            if roleLetter == 'None': roleLetter = None
            if morphology == 'None': morphology = None

            BBB, CV = ref.split( '_', 1 )
            C, V = CV.split( ':', 1 )
            tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )

            strongs = extendedStrongs[:-1] if extendedStrongs else None # drop the last digit

            roleField = ''
            if roleLetter: roleField = f' Word role=<b>{CNTR_ROLE_NAME_DICT[roleLetter]}</b>'

            morphologyField = moodField = tenseField = voiceField = personField = caseField = genderField = numberField = ''
            if morphology:
                morphologyField = f' Morphology=<b>{morphology}</b>:' # Not currently used since we give all the following information instead
                assert len(morphology) == 7, f"Got {ref} '{greek}' morphology ({len(morphology)}) = '{morphology}'"
                mood,tense,voice,person,case,gender,number = morphology
                if mood!='.': moodField = f' mood=<b>{CNTR_MOOD_NAME_DICT[mood]}</b>'
                if tense!='.': tenseField = f' tense=<b>{CNTR_TENSE_NAME_DICT[tense]}</b>'
                if voice!='.': voiceField = f' voice=<b>{CNTR_VOICE_NAME_DICT[voice]}</b>'
                if person!='.': personField = f' person=<b>{CNTR_PERSON_NAME_DICT[person]}</b>'
                if case!='.': caseField = f' case=<b>{CNTR_CASE_NAME_DICT[case]}</b>'
                if gender!='.': genderField = f' gender=<b>{CNTR_GENDER_NAME_DICT[gender]}</b>'
                if number!='.': numberField = f' number=<b>{CNTR_NUMBER_NAME_DICT[number]}</b>' # or № ???
            translation = '<small>(no English gloss)</small>' if glossWords=='-' else f'''English gloss=‘<b>{glossWords.replace('_','<span class="ul">_</span>')}</b>’'''

            prevLink = f'<b><a href="{n-1}.htm#Top">←</a></b> ' if n>1 else ''
            nextLink = f' <b><a href="{n+1}.htm#Top">→</a></b>' if n<len(word_table) else ''
            oetLink = f'<b><a href="../versions/OET/byChapter/{BBB}_C{C}.html#C{C}">↑OET {tidyBBB} Chapter {C}</a></b>'
            html = f'''<h1 id="Top">OET-LV Wordlink #{n}</h1>
<p>{prevLink}{oetLink}{nextLink}</p>
<p><span title="Goes to Statistical Restoration Greek page"><a href="https://GreekCNTR.org/collation/?{CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {tidyBBB} {C}:{V}</a></span>
 <b>{greek}</b> ({transliterate_Greek(greek)}) {translation}
 Strongs=<span title="Goes to Strongs dictionary"><a href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a></span><br>
 {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}</p>
<p><small>Note: With the help of a companion website, these word pages enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>'''
            html = makeTop( 1, 'word', None, state ) \
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET-LV NT Word {greek}" ) \
                                    .replace( '__KEYWORDS__', 'Bible, word' ) \
                                    .replace( 'parallel/"', f'parallel/{BBB}/C{C}V{V}.html"' ) \
                                + html + makeBottom( 1, 'word', state )
            with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
                html_output_file.write( html )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
    return True
# end of createWordPages.createOETGreekWordsPages




def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createWordPages object
    pass
# end of createWordPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createWordPages object
    pass
# end of createWordPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createWordPages.py
