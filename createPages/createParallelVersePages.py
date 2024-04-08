#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData createParallelVersePages functions
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
Module handling createParallelVersePages functions.

CHANGELOG:
    2023-10-23 Move SR-GNT up so it's under OET-LV
    2023-10-25 Add word numbers to SR-GNT words
    2023-12-15 Improve SR-GNT colorisation and add colourisation for other GNTs that differ
    2023-12-16 Fix bad links to version that don't have their own pages
    2024-01-08 Place UHB up higher on parallel pages
    2024-02-01 Add hide fields button
    2024-02-05 Add hide colours button
    2024-02-18 Add hide transliterations button
    2024-02-19 Add verse selection bar
"""
from gettext import gettext as _
from typing import Tuple, List
from pathlib import Path
import os
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.OriginalLanguages.Greek as Greek

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State, TEST_MODE, reorderBooksForOETVersions
from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTyndaleBookIntro, formatUnfoldingWordTranslationNotes, formatTyndaleNotes
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP, OSHB_ADJECTIVE_DICT, OSHB_PARTICLE_DICT, OSHB_NOUN_DICT, OSHB_PREPOSITION_DICT, OSHB_PRONOUN_DICT, OSHB_SUFFIX_DICT
from OETHandlers import getOETTidyBBB, getOETBookName, livenOETWordLinks


LAST_MODIFIED_DATE = '2024-04-07' # by RJH
SHORT_PROGRAM_NAME = "createParallelVersePages"
PROGRAM_NAME = "OpenBibleData createParallelVersePages functions"
PROGRAM_VERSION = '0.92'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createParallelVersePages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelVersePages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateParallelVersePages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Prepare the book links
    BBBNextLinks = []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            ourTidyBBB = getOETTidyBBB( BBB )
            BBBNextLinks.append( f'''<a title="{getOETBookName(BBB)}" href="../{BBB}/">{ourTidyBBB}</a>''' )

    # Now create the actual parallel pages
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            createParallelVersePagesForBook( level, folder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallelVerse', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Parallel View" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel' )
    indexHtml = f'''{top}<h1 id="Top">Parallel verse pages</h1>
<p class="note">Each page only contains a single verse with minimal formatting, but displays it in a large number of different versions to enable analysis of different translation decisions. Study notes, theme notes, and translation notes will also be displayed, although not every verse has these.</p>
<p class="note">Generally the older versions are nearer the bottom, and so reading from the bottom to the top can show how many English vocabulary and punctuation decisions propagated from one version to another.</p>
<h2>Index of books</h2>
{makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'parallelIndex', state)}
<p class="note"><small>Note: We would like to display more English Bible versions on these parallel pages to assist Bible translation research, but copyright restrictions from the commercial Bible industry and refusals from publishers greatly limit this. (See the <a href="https://SellingJesus.org/graphics">Selling Jesus</a> website for more information on this problem.)</small></p>
{makeBottom( level, 'parallelVerse', state )}'''
    checkHtml( 'parallelIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createParallelVersePages.createParallelVersePages

class MissingBookError( Exception ): pass
class UntranslatedVerseError( Exception ): pass

def createParallelVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state:State ) -> bool:
    """
    Create a page for every Bible verse
        displaying the verse for every available version.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1
    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )


    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # Move SR-GNT and UHB up after OET-RV and OET-LV
    parallelVersions = state.BibleVersions[:]
    parallelVersions.remove('SR-GNT'); parallelVersions.insert( 3, 'SR-GNT' )
    parallelVersions.remove('UHB'); parallelVersions.insert( 4, 'UHB' )

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    adjBBBLinksHtml = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'parallelVerse', state) \
            .replace( f'''<a title="{getOETBookName(BBB)}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )

    numChapters = None
    for versionAbbreviation in parallelVersions: # Our adjusted order
        if versionAbbreviation == 'OET': continue # that's only a "pseudo-version"!
        referenceBible = state.preloadedBibles[versionAbbreviation]
        if BBB not in referenceBible: continue # don't want to force loading the book
        # referenceBible.loadBookIfNecessary( BBB )
        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        if numChapters: break
    else:
        logging.critical( f"createParallelVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does
    introLinks = [ '<a title="Go to parallel intro page" href="Intro.htm#Top">Intro</a>' ]
    cLinksPar = f'''<p class="chLst">{ourTidyBbb} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
        if BBB=='PSA' else \
            f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>'''

    vLinksList = []
    detailsLink = f''' <a title="Show details about these works" href="{'../'*(BBBLevel)}allDetails.htm#Top">©</a>'''
    hideFieldsButton = ' <button type="button" id="__ID__FieldsButton" title="Hide historical translations" onclick="hide_show_fields()">↕</button>'
    hideTransliterationsButton = ' <button type="button" id="__ID__TransliterationsButton" title="Hide transliterations, etc." onclick="hide_show_transliterations()">ⱦ</button>'
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( -1, numChapters+1 ):
            C = str( c )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating {'TEST ' if TEST_MODE else ''}parallel pages for {BBB} {C}…" )
            introLink = f'''<a title="Go to book intro" href="Intro.htm#__ID__">B</a> {f'<a title="Go to chapter intro" href="C{c}V0.htm#__ID__">I</a> ' if c!=-1 else ''}'''
            leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a> ' if c>1 else ''
            rightCLink = f' <a title="Go to first chapter" href="C1V1.htm#__ID__">►</a>' if c==-1 \
                    else f' <a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters \
                    else ''
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createParallelVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            # There's an EM_SPACE and an EN_SPACE (for the join) in the following line
            for v in range( 0, numVerses+1 ):
                V = str( v )
                vLinksPar = f'''<p class="vsLst">{ourTidyBbb} {C} {' '.join( [f'<a title="Go to parallel verse page" href="C{C}V{vv}.htm#Top">V{vv}</a>'
                                for vv in range(1,numVerses+1,5 if numVerses>100 else 4 if numVerses>80 else 3 if numVerses>60 else 2 if numVerses>40 else 1) if vv!=v] )}</p>'''
                doneHideablesDiv = False
                greekWords = {}; greekVersionKeysHtmlSet = set()

                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Go to previous verse" href="C{C}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                # NOTE below: C1V0 may not exist in the version but usually there's uW TNs for 1:0
                rightVLink = f' <a title="Go to first chapter intro" href="C1V0.htm#__ID__">→</a>' if c==-1 \
                        else f' <a title="Go to next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses \
                        else ''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introductions <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}{hideFieldsButton}{hideTransliterationsButton}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{introLink}{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}{hideFieldsButton}{hideTransliterationsButton}</p>'
                parallelHtml = ''
                for versionAbbreviation in parallelVersions: # our adjusted order
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    createParallelVersePagesForBook {BBB} {C}:{V} processing {versionAbbreviation}…" )
                    assert not parallelHtml.endswith( '\n' )

                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have OET-RV and OET-LV
                    if versionAbbreviation in ('UHB','JPS') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB):
                        continue # Skip non-OT books for Hebrew
                    if versionAbbreviation in ('BRN','BrLXX') \
                    and BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip NT books for Brenton (it has deuterocanon/apocrypha)
                    if versionAbbreviation in ('TCNT','TNT', 'SR-GNT','UGNT','SBL-GNT','TC-GNT') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip non-NT books for Koine Greek NT
                    if versionAbbreviation in ('TOSN','TTN','UTN'):
                        continue # We handle the notes separately at the end

                    if not doneHideablesDiv and versionAbbreviation not in ('OET-RV','OET-LV','SR-GNT','UHB','ULT','UST'):
                        assert not parallelHtml.endswith( '\n' )
                        parallelHtml = f'{parallelHtml}\n<div class="hideables">\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">'
                        doneHideablesDiv = True

                    thisBible = state.preloadedBibles[versionAbbreviation]
                    # thisBible.loadBookIfNecessary( BBB )
                    textHtml = None
                    if versionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
                        try:
                            verseText = thisBible[(BBB,C,V)] \
                                .removeprefix( '\\p ' ).replace( '\\p ', '\n' ) \
                                .removeprefix( '\\p ' ).replace( '\\q1 ', '\n' ) \
                                .replace( '\n\n', '\n' )
                            # if versionAbbreviation=='CSB' and BBB=='RUT' and 'ORD' in verseText: print( f"{versionAbbreviation} {BBB} {C}:{V} {verseText=}" )
                            vHtml = verseText \
                                .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
                                .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
                                .replace( '\\add ', '<span class="add">' ).replace( '\\add*', '</span>' ) \
                                .replace( '\\nd LORD\\nd*', '\\nd L<span style="font-size:.75em;">ORD</span>\\nd*' ) \
                                    .replace( '\\nd ', '<span class="nd">' ).replace( '\\nd*', '</span>' ) \
                                .replace( '\\wj ', '<span class="wj">' ).replace( '\\wj*', '</span>' ) \
                                .replace( '\n', '<br>' )
                            # if versionAbbreviation=='CSB' and BBB=='RUT' and C=='2' and 'ORD' in verseText: print( f"{versionAbbreviation} {BBB} {C}:{V} {vHtml=}" ); halt
                            assert '\\' not in vHtml, f"{versionAbbreviation} {BBB} {C}:{V} {vHtml=}"
                            vHtml =  f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="Go to {state.BibleNames[versionAbbreviation]} copyright info" href="{'../'*BBBLevel}allDetails.htm#{versionAbbreviation}">{versionAbbreviation}</a></span> {vHtml}</p>'''
                        except KeyError:
                            vHtml = None # We display nothing at all for these versions that only have a few selected verses
                    else: # should be a Bible object
                        try:
                            if BBB not in thisBible: raise MissingBookError # Requested book is not in this Bible
                            # NOTE: For the book intro, we fetch the whole lot in one go (not line by line)
                            verseEntryList, contextList = thisBible.getContextVerseData( (BBB, C) if c==-1 else (BBB, C, V) )
                            if 'GNT' in versionAbbreviation:
                                plainGreekText = getPlainText( verseEntryList )
                                if versionAbbreviation == 'SBL-GNT': plainGreekText = plainGreekText.replace('1','').replace('2','') # 1 Cor 12:10
                                greekWords[versionAbbreviation] = plainGreekText
                                greekWords[f'{versionAbbreviation}_NoPunct'] = removeGreekPunctuation(  greekWords[versionAbbreviation] )
                                greekClass = Greek.Greek( greekWords[f'{versionAbbreviation}_NoPunct'] )
                                try:
                                    greekWords[f'{versionAbbreviation}_NoAccents'] = greekClass.removeAccents()
                                except Exception as exc:
                                    print( f"\n{BBB} {C}:{V} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}" )
                                    raise exc
                                # print( f"\n{BBB} {C}:{V} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}\n{greekWords[f'{versionAbbreviation}_NoAccents']=}" )
                            if isinstance( thisBible, ESFMBible.ESFMBible ):
                                verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*BBBLevel}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
                            textHtml = convertUSFMMarkerListToHtml( BBBLevel, versionAbbreviation, (BBB,C,V), 'verse', contextList, verseEntryList, basicOnly=(c!=-1), state=state )
                            assert '¦' not in textHtml, f"{BBB} {C}:{V} {versionAbbreviation} {textHtml=}"
                            assert not textHtml.endswith( '\n' )
                            if textHtml == '◘': raise UntranslatedVerseError

                            if 'OET' not in versionAbbreviation:
                                # Hardwire added words in non-OET versions to italics
                                for _safetyCheck in range( 30 ): # 20 was too few (because this might include an intro paragraph)
                                    ix = textHtml.find( '<span class="add">' )
                                    if ix == -1: break
                                    textHtml = textHtml.replace( '<span class="add">', '<i>', 1 )
                                    textHtml = f"{textHtml[:ix]}{textHtml[ix:].replace('</span>','</i>',1)}"
                                else: need_to_increase_range_value

                            if versionAbbreviation == 'OET-RV':
                                textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                            elif versionAbbreviation == 'OET-LV':
                                # assert '<span class="ul">_</span>HNcbsa' not in textHtml, f'''Here1 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                                textHtml = do_OET_LV_HTMLcustomisations( textHtml )
                                # assert textHtml.count('<span class="ul">_</span>HNcbsa') < 2, f'''Here2 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                            elif versionAbbreviation == 'WEB': # assuming WEB comes BEFORE WMB
                                textHtmlWEB = textHtml # Save it
                            elif versionAbbreviation == 'WMB': # assuming WEB comes BEFORE WMB
                                if textHtml == textHtmlWEB:
                                    # print( f"Skipping parallel for WMB {BBB} {C}:{V} because same as WEB" )
                                    continue
                                # else:
                                #     print( f"Using parallel for WMB {BBB} {C}:{V} because different from WEB:" )
                                #     print( f"  {textHtmlWEB=}" )
                                #     print( f"     {textHtml=}" )
                            elif versionAbbreviation == 'LSV':
                                textHtml = do_LSV_HTMLcustomisations( textHtml )
                            elif versionAbbreviation == 'T4T':
                                textHtml = do_T4T_HTMLcustomisations( textHtml )
                            elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB'):
                                modernisedTextHtml = moderniseEnglishWords( textHtml )
                                if versionAbbreviation in ('WYC','TNT','CB','GNV','BB'): # all from 1500's
                                    modernisedTextHtml = modernisedTextHtml.replace( 'J', 'Y' ).replace( 'Ie', 'Ye' ).replace( 'Io', 'Yo' )
                                if modernisedTextHtml != textHtml: # only show it if it changed
                                    textHtml = f'{textHtml}<span class="{versionAbbreviation}_mod"><br>  ({modernisedTextHtml})</span>'
                            elif versionAbbreviation == 'LUT':
                                if (adjustedTextHtml:=translateGerman(textHtml)) != textHtml: # only show it if it changed
                                    textHtml = f'{textHtml}<span class="LUT_trans"><br>  ({adjustedTextHtml})</span>'
                            elif versionAbbreviation == 'CLV':
                                if (adjustedTextHtml:=adjustLatin(textHtml)) != textHtml: # only show it if it changed
                                    textHtml = f'{textHtml}<span class="CLV_trans"><br>  ({adjustedTextHtml})</span>'
                            elif versionAbbreviation == 'SR-GNT':
                                if C!='-1' and V!='0' and textHtml:
                                    # print( f"{BBB} {C}:{V} SR-GNT {verseEntryList=} {textHtml=} {transcription=}" )
                                    if '<' in textHtml or '>' in textHtml or '=' in textHtml or '"' in textHtml:
                                        if '<br>' not in textHtml: # Some verses have a sentence break
                                            halt # Have some unexpected fields in SR-GNT textHtml
                                    textHtml, grammaticalKeysHtmlList = brightenSRGNT( BBB, C, V, textHtml, verseEntryList, state )
                                transcription = transliterate_Greek(textHtml) # Colourisation and nomina sacra gets carried through
                                if 'Ah' in transcription or ' ah' in transcription or transcription.startswith('ah') \
                                or 'Eh' in transcription or ' eh' in transcription or transcription.startswith('eh') \
                                or 'Oh' in transcription or ' oh' in transcription or transcription.startswith('oh') \
                                or 'Uh' in transcription or ' uh' in transcription or transcription.startswith('uh'):
                                    raise ValueError( f"Bad Greek transcription for {versionAbbreviation} {BBB} {C}:{V} {transcription=} from '{textHtml}'" )
                                # Add an extra link to the CNTR collation page
                                collationHref = f'https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}'
                                try:
                                    # NOTE: We close the previous paragraph, but leave the key paragraph open
                                    keysHtml = f'''</p><p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the OET-RV to the LV is done by some temporary software, hence the OET-RV alignments are incomplete (and may occasionally be wrong).</small>'''
                                except UnboundLocalError: # grammaticalKeysHtmlList
                                    keysHtml = ''
                                textHtml = f'''{textHtml} <a title="Go to the GreekCNTR collation page" href="{collationHref}">‡</a><span class="SR-GNT_trans">
<br>   ({transcription})</span>
{keysHtml}'''
                            elif versionAbbreviation in ('UGNT','SBL-GNT','TC-GNT','BrLXX'):
                                transcription = transliterate_Greek(textHtml)
                                if 'Ah' in transcription or ' ah' in transcription or transcription.startswith('ah') \
                                or 'Eh' in transcription or ' eh' in transcription or transcription.startswith('eh') \
                                or 'Oh' in transcription or ' oh' in transcription or transcription.startswith('oh') \
                                or 'Uh' in transcription or ' uh' in transcription or transcription.startswith('uh'):
                                    raise ValueError( f"Bad Greek transcription for {versionAbbreviation} {BBB} {C}:{V} {transcription=} from '{textHtml}'" )
                                if transcription:
                                    textHtml = f'{textHtml}<span class="{versionAbbreviation}_trans"><br>  ({transcription})</span>'
                            elif versionAbbreviation == 'UHB':
                                # print( f"{versionAbbreviation} {BBB} {C}:{V} {textHtml=}")
                                if C!='-1' and V!='0' and textHtml:
                                    textHtml, grammaticalKeysHtmlList = brightenUHB( BBB, C, V, textHtml, verseEntryList, state )
                                transcription = transliterate_Hebrew(textHtml)
                                collationHref = f'https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation(BBB)}&c={C}&v={V}'
                                try:
                                    keysHtml = f'''</p><p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the OET-RV to the LV is done by some temporary software, hence the OET-RV alignments are incomplete (and may occasionally be wrong).</small>'''
                                except UnboundLocalError: # grammaticalKeysHtmlList
                                    keysHtml = ''
                                textHtml = f'''{textHtml} <a title="Go to the OSHB verse page" href="{collationHref}">‡</a><span class="UHB_trans">
<br>   ({transcription})</span>
{keysHtml}'''
                            if textHtml:
                                # assert textHtml.count('<span class="ul">_</span>HNcbsa') < 2, f'''Here3 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                                if versionAbbreviation in ('UGNT','SBL-GNT','TC-GNT') \
                                and 'SR-GNT' in greekWords and greekWords[versionAbbreviation]!=greekWords['SR-GNT']:
                                    # Here we colour the workname to show critical GNT texts that differ in someway from the SR-GNT
                                    # print( f"\n{versionAbbreviation}\n{versionAbbreviation}='{greekWords[versionAbbreviation]}'\nSR-GNT='{greekWords['SR-GNT']}'" )
                                    if greekWords[f'{versionAbbreviation}_NoPunct'] == greekWords['SR-GNT_NoPunct']:
                                        spanClassName = 'wrkNameDiffPunct'
                                    elif greekWords[f'{versionAbbreviation}_NoAccents'] == greekWords['SR-GNT_NoAccents']:
                                        spanClassName = 'wrkNameDiffAccents'
                                    else: spanClassName = 'wrkNameDiffText'
                                    greekVersionKeysHtmlSet.add( spanClassName )
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="{spanClassName}"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                elif versionAbbreviation=='OET-RV':
                                    # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case)
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} chapter (side-by-side versions)" href="{'../'*BBBLevel}OET/byC/{BBB}_C{C}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_C{C}.htm#Top">OET-RV</a>)</small></span> {textHtml}</p>'''                                    
                                elif versionAbbreviation=='WYC': # Just add a bit about it being translated from the Latin (not the Greek)
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter (translated from the Latin)'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                else: # for all the others
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                            else: # no textHtml -- can include verses that are not in the OET-LV
                                if c==-1 or v==0: # For these edge cases, we don't want the version abbreviation appearing
                                    vHtml = ''
                            if versionAbbreviation=='TC-GNT': # the final one that we display, so show the key to the colours
                                greekVersionKeysHtmlList = []
                                if 'wrkNameDiffPunct' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffPunct">yellow</span>:punctuation differs' )
                                if 'wrkNameDiffAccents' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffAccents">orange</span>:accents differ' )
                                if 'wrkNameDiffText' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffText">red</span>:words differ' )
                                if greekVersionKeysHtmlList:
                                    vHtml = f'''{vHtml}<p class="key"><b>Key for above GNTs</b>: {', '.join(greekVersionKeysHtmlList)} (from our <b>SR-GNT</b> base).</p>'''

                        except MissingBookError:
                            assert not textHtml, f"{versionAbbreviation} {BBB} {C}:{V} {verseEntryList=} {textHtml=}"
                            assert BBB not in thisBible
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except UntranslatedVerseError:
                            assert textHtml == '◘'
                            assert versionAbbreviation == 'OET-RV'
                            assert BBB in thisBible
                            if BBB in thisBible:
                                # print( f"No verse inB {versionAbbreviation} {BBB} in {thisBible}"); halt
                                warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                            else:
                                warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except KeyError:
                            assert not textHtml, f"{versionAbbreviation} {BBB} {C}:{V} {verseEntryList=} {textHtml=}"
                            if c==-1 or v==0:
                                vHtml = ''
                            elif BBB in thisBible:
                                # print( f"No verse inKT {versionAbbreviation} {BBB} in {thisBible}"); halt
                                warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                                versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{versionNameLink}">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )
                            else:
                                warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )

                    if vHtml:
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                        checkHtml( f'{versionAbbreviation} {BBB} {C}:{V}', vHtml, segmentOnly=True )
                        assert not parallelHtml.endswith( '\n' )
                        assert not vHtml.endswith( '\n' )
                        parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{vHtml}"

                # Close the hideable div
                assert doneHideablesDiv # Fails if no Bible versions were included that go in the hideable div
                parallelHtml = f'{parallelHtml}\n</div><!--end of hideables-->'

                if c == -1: # Handle Tyndale book intro summaries and book intros
                    tbisHtml = formatTyndaleBookIntro( 'TBIS', BBBLevel, BBB, 'parallelVerse', state )
                    if tbisHtml:
                        tbisHtml = f'''<div id="TBIS" class="parallelTBI"><a title="Go to TSN copyright page" href="{'../'*BBBLevel}TSN/details.htm#Top">TBIS</a> <b>Tyndale Book Intro Summary</b>: {tbisHtml}</div><!--end of TBI-->'''
                        parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{tbisHtml}"
                    tbiHtml = formatTyndaleBookIntro( 'TBI', BBBLevel, BBB, 'parallelVerse', state )
                    if tbiHtml:
                        tbiHtml = f'''<div id="TBI" class="parallelTBI"><a title="Go to TSN copyright page" href="{'../'*BBBLevel}TSN/details.htm#Top">TBI</a> <b>Tyndale Book Intro</b>: {tbiHtml}</div><!--end of TBI-->'''
                        parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{tbiHtml}"

                # Handle Tyndale open study notes and theme notes
                tsnHtml = formatTyndaleNotes( 'TOSN', BBBLevel, BBB, C, V, 'parallelVerse', state )
                if tsnHtml:
                    tsnHtml = f'''<div id="TSN" class="parallelTSN"><a title="Go to TSN copyright page" href="{'../'*BBBLevel}TSN/details.htm#Top">TSN</a> <b>Tyndale Study Notes</b>: {tsnHtml}</div><!--end of TSN-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n{tsnHtml}'
                ttnHtml = formatTyndaleNotes( 'TTN', BBBLevel, BBB, C, V, 'parallelVerse', state )
                if ttnHtml:
                    ttnHtml = f'''<div id="TTN" class="parallelTTN"><a title="Go to TSN copyright page" href="{'../'*BBBLevel}TSN/details.htm#Top">TTN</a> <b>Tyndale Theme Notes</b>: {ttnHtml}</div><!--end of TTN-->'''
                    parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{ttnHtml}"
                # Handle uW translation notes
                utnHtml = formatUnfoldingWordTranslationNotes( BBBLevel, BBB, C, V, 'parallelVerse', state )
                if utnHtml:
                    utnHtml = f'''<div id="UTN" class="parallelUTN"><a title="Go to UTN copyright page" href="{'../'*BBBLevel}UTN/details.htm#Top">UTN</a> <b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n{utnHtml}'

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'parallelVerse', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {C}:{V} Parallel View" ) \
                        .replace( '__KEYWORDS__', f'Bible, parallel, {ourTidyBBB}' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*BBBLevel}ilr/"''', f'''href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top"''')
                parallelHtml = f'''{top}<!--parallel verse page-->
{adjBBBLinksHtml}
{cLinksPar}
{vLinksPar}
<h1>Parallel {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>
<p class="rem">Note: This view shows ‘verses’ which are not natural language units and hence sometimes only part of a sentence will be visible. This view is only designed for doing comparisons of different translations. Click on the version abbreviation to see the verse in more of its context.</p>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{parallelHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, 'parallelVerse', state )}'''
                checkHtml( f'Parallel {BBB} {C}:{V}', parallelHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( parallelHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(parallelHtml):,} characters written to {filepath}" )
                vLinksList.append( f'<a title="Go to parallel verse page" href="{filename}#Top">{C}:{V}</a>' )
                if c == -1: # then we're doing the book intro
                    break # no need to loop -- we handle the entire intro in one go
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename1 = 'index.htm'
    filepath1 = BBBFolder.joinpath( filename1 )
    top = makeTop( BBBLevel, None, 'parallelVerse', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Parallel View" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel songs index</h1>' if BBB=='PSA' else ''}{cLinksPar}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel verses index</h1>' if BBB!='PSA' else ''}{f'{NEWLINE}<p class="vsLst">{" ".join( vLinksList )}</p>' if BBB!='PSA' else ''}
{makeBottom( BBBLevel, 'parallelVerse', state )}'''
    checkHtml( 'parallelIndex', indexHtml )
    with open( filepath1, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath1}" )

    # Write a second copy of the index page up a level
    newBBBVLinks = []
    for vLink in vLinksList:
        newBBBVLinks.append( vLink.replace('href="', f'href="{BBB}/') )
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, None, 'parallelVerse', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Parallel View" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel songs index</h1>' if BBB=='PSA' else ''}{cLinksPar}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel verses index</h1>' if BBB!='PSA' else ''}{f'{NEWLINE}<p class="vsLst">{" ".join( newBBBVLinks )}</p>' if BBB!='PSA' else ''}
{makeBottom( level, 'parallelVerse', state )}'''
    checkHtml( 'parallelIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook() finished processing {len(vLinksList):,} {BBB} verses." )
    return True
# end of createParallelVersePages.createParallelVersePagesForBook


def getPlainText( givenVerseEntryList ) -> str:
    """
    Takes a verseEntryList and converts it to a string of plain text words.

    Used to compare critical Greek versions.
    """
    plainTextStringBits = []
    for entry in givenVerseEntryList:
        # print( entry )
        marker, cleanText = entry.getMarker(), entry.getCleanText()
        # print( f"{marker=} {cleanText=}")
        if marker in ('v~','p~'):
            plainTextStringBits.append( cleanText )

    return ' '.join( plainTextStringBits )
# end of createParallelVersePages.getPlainText


def removeGreekPunctuation( greekText:str ) -> str:
    """
    Converts to lowercase and removes punctuation used in any Greek version.

    Used to compare critical Greek versions.
    """
    return ( greekText.lower()
                .replace(',','').replace('.','').replace('!','') # English punctuation marks
                .replace('?','').replace(';','') # English and Greek question marks
                .replace(';','').replace('·','').replace('·','').replace(':','') # English and Greek semicolons and colon
                .replace('(','').replace(')','').replace('[','').replace(']','') # Parentheses and square brackets
                .replace('“','').replace('”','').replace('‘','').replace('’','') # Double and single typographic quotation marks
                .replace('⸀','').replace('⸂','').replace('⸃','').replace('⸁','').replace('⸄','').replace('⸅','').replace('⟦','').replace('⟧','')
                .replace('ʼ','')
                .replace('˚','') # Used by SR-GNT to mark Nomina Sacra
                .replace('—',' ').replace('–',' ').replace('…',' ') # Em and en dashes and ellipsis are converted to spaces
                .replace('   ',' ').replace('  ',' ') # Clean up spaces
            .strip() )
# end of createParallelVersePages.removeGreekPunctuation


GREEK_CASE_CLASS_DICT = { 'N':'Nom','n':'Nom', 'G':'Gen','g':'Gen', 'A':'Acc','a':'Acc', 'D':'Dat','d':'Dat', 'V':'Voc','v':'Voc', }
GREEK_CASE_CLASS_KEY_DICT = { 'grkVrb':'<span class="grkVrb">yellow</span>:verbs',
                              'grkNom':'<span class="grkNom">light-green</span>:nominative/subject',
                              'grkAcc':'<span class="grkAcc">orange</span>:accusative/object',
                              'grkGen':'<span class="grkGen">pink</span>:genitive/possessor',
                              'grkDat':'<span class="grkDat">cyan</span>:dative/indirect object',
                              'grkVoc':'<span class="grkVoc">magenta</span>:vocative',
                              'grkNeg':'<span class="grkNeg">red</span>:negative'}
def brightenSRGNT( BBB:str, C:str, V:str, brightenTextHtml:str, verseEntryList, state:State ) -> Tuple[str,List[str]]:
    """
    Take the SR-GNT text (which includes punctuation and might also include <br> characters)
        and mark the role participants
    """
    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"brightenSRGNT( {BBB} {C}:{V} {brightenTextHtml}, {verseEntryList}, … )…" )

    wordFileName = 'OET-LV_NT_word_table.tsv'

    punctuatedGrkWords = brightenTextHtml.replace( '<br>', ' ').replace( '  ', ' ').split( ' ' )
    strippedGrkWords = [punctuatedGrkWord.lstrip( '“‘˚(' ).rstrip( '.,?!:”’·;)–…' ) for punctuatedGrkWord in punctuatedGrkWords]

    # Match Greek words to word numbers
    firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{C}:{V}']
    currentWordNumber = firstWordNumber
    grkWordNumbers = []
    for strippedGrkWord in strippedGrkWords:
        # print( f"  {BBB} {C}:{V} {strippedGrkWord=} {currentWordNumber=} from ({firstWordNumber},{lastWordNumber})" )
        ref, greekWord, SRLemma, _GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
        while not probability and currentWordNumber < lastWordNumber:
            currentWordNumber += 1
            ref, greekWord, SRLemma, _GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
        assert probability
        if not greekWord.startswith('κρ') and not greekWord.startswith('μακρ') and not greekWord.startswith('γενν'): # Seems there were some spelling changes
            # and greekWord not in ('κράββατον','κράββατόν'):
            if greekWord.lower() != strippedGrkWord.lower():
                logging.critical( f"Unable to find word number for {BBB} {C}:{V} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {len(grkWordNumbers)=}" )
                break # We failed to match -- it's not critical so we'll just stop here (meaning we won't have all the word numbers for this verse)
            # assert greekWord.lower() == strippedGrkWord.lower(), f"{BBB} {C}:{V} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {grkWordNumbers=}"
        grkWordNumbers.append( currentWordNumber )    
        assert currentWordNumber <= lastWordNumber
        currentWordNumber += 1
    if len(grkWordNumbers) != len(punctuatedGrkWords):
        logging.critical( f"brighten SR-GNT was unable to find word numbers for all words for {BBB} {C}:{V} (got {len(grkWordNumbers)} out of {len(punctuatedGrkWords)})" )

    # TODO: Not totally sure that we need these extras from https://github.com/Center-for-New-Testament-Restoration/SR files
    #           now that we have the word numbers for the Greek words
    allExtras = None
    for verseEntry in verseEntryList:
        # print( f"    vE {verseEntry=}" )
        marker, extras = verseEntry.getMarker(), verseEntry.getExtras()
        if extras: # Extras contain the info we need, like: ww @ 4 = 'Ἀρχὴ|lemma="ἀρχή" x-koine="αρχη" x-strong="G07460" x-morph="Gr,N,....NFS"'
            # print( f"      ME {marker=} {extras=}" )
            if allExtras is None:
                allExtras = list( extras )
            else: allExtras += list( extras )

    classKeySet = set()
    if allExtras:
        # Find each word in brightenTextHtml, find the word info in allExtras, and then update brightenTextHtml with more classes
        searchStartIndex = wordNumberIndex = extraIndexOffset = 0
        for _safetyCount1 in range( len(punctuatedGrkWords)+1 ):
            rawGrkWord = punctuatedGrkWords[wordNumberIndex]
            ix = brightenTextHtml.index( rawGrkWord, searchStartIndex )
            # print( f"  aE {wordNumberIndex=} {rawGrkWord=} {searchStartIndex=} {ix=} {extraIndexOffset=}")
            assert ix != -1
            simpleGrkWord = rawGrkWord.lstrip( '“‘˚(' )
            ix += len(rawGrkWord) - len(simpleGrkWord) # Adjust for removal of any leading punctuation
            simpleGrkWord = simpleGrkWord.rstrip( '.,?!:”’·;)–…' )
            assert simpleGrkWord.isalpha(), f"{simpleGrkWord=}"
            attribDict = {}
            for _safetyCount2 in range( 4 ):
                extraEntry = allExtras[wordNumberIndex+extraIndexOffset]
                # print( f"     {brightenTextHtml[ix:ix+20]=}… {extraEntry=}")
                extraType, extraText = extraEntry.getType(), extraEntry.getText()
                # print( f"       TyTxClTx {extraType=} {extraText=} {extraEntry.getCleanText()=}")
                if extraType != 'ww': extraIndexOffset += 1; continue # it could be a footnote or something
                if extraText.startswith( f'{simpleGrkWord}|' ):
                    extraText = extraText[len(simpleGrkWord)+1:] # Remove the word that we've just confirmed, left with something like 'lemma="ἁμαρτία" x-koine="αμαρτιασ" x-strong="G02660" x-morph="Gr,N,....AFP"'
                    for chunk in extraText.split( ' ' ):
                        fieldName, fieldValue = chunk.split( '=', 1 )
                        fieldValue = fieldValue.strip( '"' )
                        if fieldName.startswith( 'x-' ): fieldName = fieldName[2:]
                        if fieldName == 'morph':
                            assert fieldValue.startswith( 'Gr,' )
                            attribDict['role'] = fieldValue[3]
                            assert fieldValue[4] == ',', f"{BBB} {C}:{V} {fieldValue=} {extraType=} {extraEntry.getText()=}" # SR-GNT Mrk 1:1 has 'Gr,N,....NFS'
                            fieldValue = fieldValue[5:] # Get only the morph bit
                            assert len(fieldValue) == 7
                        elif fieldName == 'strong':
                            assert fieldValue[0] == 'G', f"{fieldValue=}"
                            fieldValue = fieldValue[1:] # Get only the numerical bit
                        # print( f"     {simpleGrkWord} {fieldName}='{fieldValue}'" )
                        attribDict[fieldName] = fieldValue
                    break
                print( f"Oops!!! {simpleGrkWord=} {extraText=}"); halt
            else: need_to_increase_count2_for_brightenSRGNT
            # print( f"    {attribDict=}" )
            try:
                wordLink = f'../../ref/GrkWrd/{grkWordNumbers[_safetyCount1]}.htm#Top' # We'd prefer to link to our own word pages
            except IndexError:
                wordLink = f'''https://BibleHub.com/greek/{attribDict['strong'][:-1]}.htm''' # default to BibleHub by Strongs number if we don't know the word number
            if attribDict['role'] == 'V':
                caseClassName = 'grkVrb'
            elif attribDict['strong'] == '37560': # Greek 'οὐ' (ou) 'not'
                caseClassName = 'grkNeg'
            elif attribDict['morph'][4] != '.':
                try:
                    caseClassName = f'''grk{GREEK_CASE_CLASS_DICT[attribDict['morph'][4]]}'''
                except KeyError:
                    print( f"{BBB} {C}:{V} {currentWordNumber=} {rawGrkWord=} {simpleGrkWord=} {attribDict=}" )
                    raise KeyError
            else: caseClassName = None
            if caseClassName: classKeySet.add( caseClassName )
            caseClassHtml = '' if not caseClassName else f'''class="{caseClassName}" ''' # Has a trailing space
            brightenTextHtml = f'''{brightenTextHtml[:ix-1]}<b>˚<a title="{attribDict['role']}-{attribDict['morph']}" {caseClassHtml}href="{wordLink}">{simpleGrkWord}</a></b>{brightenTextHtml[ix+len(simpleGrkWord):]}''' \
                        if '˚' in rawGrkWord else \
                        f'''{brightenTextHtml[:ix]}<a title="{attribDict['role']}-{attribDict['morph']}" {caseClassHtml}href="{wordLink}">{simpleGrkWord}</a>{brightenTextHtml[ix+len(simpleGrkWord):]}'''
            wordNumberIndex += 1
            if wordNumberIndex >= len(punctuatedGrkWords):
                break
            searchStartIndex = ix + len(simpleGrkWord)
        else: need_to_increase_count1_for_brightenSRGNT

    # Get the colour keys into the correct order
    classKeyList = []
    for classKey,classKeyHtml in GREEK_CASE_CLASS_KEY_DICT.items():
        if classKey in classKeySet:
            classKeyList.append( classKeyHtml )
    assert classKeyList

    return brightenTextHtml, classKeyList
# end of createParallelVersePages.brightenSRGNT


# HEBREW_CASE_CLASS_DICT = { 'N':'Nom','n':'Nom', 'G':'Gen','g':'Gen', 'A':'Acc','a':'Acc', 'D':'Dat','d':'Dat', 'V':'Voc','v':'Voc', }
HEBREW_CASE_CLASS_KEY_DICT = { 'hebVrb':'<span class="hebVrb">yellow</span>:verbs',
                            #   'hebNom':'<span class="hebNom">light-green</span>:nominative/subject',
                            #   'hebAcc':'<span class="hebAcc">orange</span>:accusative/object',
                            #   'hebGen':'<span class="hebGen">pink</span>:genitive/possessor',
                            #   'hebDat':'<span class="hebDat">cyan</span>:dative/indirect object',
                            #   'hebVoc':'<span class="hebVoc">magenta</span>:vocative',
                              'hebNeg':'<span class="hebNeg">red</span>:negative'}
def brightenUHB( BBB:str, C:str, V:str, brightenUHBTextHtml:str, verseEntryList, state:State ) -> Tuple[str,List[str]]:
    """
    Take the UHB text (which includes punctuation and might also include <br> characters)
        and mark the role participants

    From https://git.door43.org/unfoldingWord/hbo_uhb:
        The UHB differs from the OSHB in a few respects (though more may be coming):

        Metadata—The UHB text includes various metadata to mark the text which create links to other content that our software uses.
            For example, we add links to our unfoldingWord® Translation Words articles where appropriate.
        Joined words (for example: inseparable prepositions, the definite article, conjunctive waw) are separated
                using a unicode WORD JOINER (U+2060) character instead of the / character that the OSHB uses.
        The UHB is encoded in USFM 3.0 instead of the OSIS that the OSHB uses.
        The UHB uses the versification scheme of the ULT instead of that of the OSHB (which is based on the WLC scheme common for Hebrew Bibles).
            The goal of this change is to simplify the translation and reference process for Gateway Language teams and supplemental resources
                (such as our translation helps suite).
            This may make some resources that are keyed to the WLC more difficult to use with the Hebrew text
                but it will likely simplify the use of many other resources that use an ASV/KJV style of versification.
        For each Ketiv/Qere occurrence, we have selected one of the forms for the main body of the text and have footnoted the other.
        In some instances, the UHB selects alternate readings (either in the text or in the footnotes) from the OSHB,
                usually on the basis of manuscripts other than the Leningrad Codex.
            These references include: Gen 13:10; Ruth 3:12, 3:15, 4:4; 2 Sam 2:9, 5:8, 22:8, 23:8; 1 Ki 12:12; 1 Chr 9:4;
                                        Isa 53:11; Jer 2:21, 6:6, 8:6, 8:10 [x2], 15:10, 18:16; Nah 2:1.

    Sadly it doesn't document the morphology field which contains a wide range of formats,
        e.g., "He,D", "He,Np", "He,Ncmsc", "He,Vqp3ms", and with colons: "He,R:R", "He,C:Ncmsa", "He,Ncmpc:Sp1cs"
        It seems that the colon is often correlated to a colon in strongs, e.g., "b:H1471a"
            but there are also word entries without a colon in strongs, yet one in the morphology!!!
    """
    dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nbrightenUHB( {BBB} {C}:{V} {brightenUHBTextHtml}, {verseEntryList}, … )…" )

    wordFileName = 'OET-LV_OT_word_table.tsv'

    # NOTE: UHB wrongly has the ca fields before the \p field so they go onto the end of the previous lines
    # /w בָּ⁠הָֽר|lemma="הַר" strong="b:H2022" x-morph="He,Rd:Ncmsa"/w*׃
    # /ca 32/ca*
    # /p
    # /v 55
    # /va 32:1/va*
    # /w וַ⁠יַּשְׁכֵּ֨ם|lemma="שָׁכַם" strong="c:H7925" x-morph="He,C:Vhw3ms"/w*
    # gives
    # וַ⁠יִּזְבַּ֨ח יַעֲקֹ֥ב זֶ֨בַח֙ בָּ⁠הָ֔ר וַ⁠יִּקְרָ֥א לְ⁠אֶחָ֖י⁠ו לֶ⁠אֱכָל־לָ֑חֶם וַ⁠יֹּ֣אכְלוּ לֶ֔חֶם וַ⁠יָּלִ֖ינוּ בָּ⁠הָֽר׃ <span class="ca">32</span>
    # so we'll just ignore it

    adjustedBrightenUHBTextHtml, vaText, caText = brightenUHBTextHtml, None, None
    vC, vV = C, V
    if '<span class="ca">' in adjustedBrightenUHBTextHtml: # First one is at Gen 31:54
        ixStartSpan = adjustedBrightenUHBTextHtml.index( '<span class="ca">' )
        ixEndSpan = adjustedBrightenUHBTextHtml.index( '</span>', ixStartSpan+17 )
        caText = adjustedBrightenUHBTextHtml[ixStartSpan+17:ixEndSpan]
        # print( f"{caText=}")
        assert ':' not in caText
        adjustedBrightenUHBTextHtml = f'{adjustedBrightenUHBTextHtml[:ixStartSpan]}{adjustedBrightenUHBTextHtml[ixEndSpan+7:]}' # Remove this non-Hebrew bit before we divide it into words
        # vC, vV = caText, '1'
    assert 'class="ca"' not in adjustedBrightenUHBTextHtml
    while '<span class="va">' in adjustedBrightenUHBTextHtml: # First one is at Gen 31:55
        ixStartSpan =  adjustedBrightenUHBTextHtml.index( '<span class="va">')
        ixEndSpan = adjustedBrightenUHBTextHtml.index( '</span> ', ixStartSpan+16 )
        vaText = adjustedBrightenUHBTextHtml[ixStartSpan+17:ixEndSpan]
        adjustedBrightenUHBTextHtml = f'{adjustedBrightenUHBTextHtml[:ixStartSpan]}{adjustedBrightenUHBTextHtml[ixEndSpan+8:]}' # Remove this non-Hebrew bit before we divide it into words
        vC, vV = vaText.split(':') if ':' in vaText else (C, vaText)
    assert 'class="va"' not in adjustedBrightenUHBTextHtml
    punctuatedHebWords = ( adjustedBrightenUHBTextHtml.replace( '<br>', ' ')
                          .replace( '־', ' ־ ') # We surrounded maqaf by spaces so it's processed like a word
                          .replace( '׀', ' ׀ ' ) # Same for HEBREW PUNCTUATION PASEQ U+05C0
                          .replace( ' פ ', ' ') # Remove stand-alone pe, first one at Gen 35:22
                          .replace( ' ס ', ' ') # Remove stand-alone samekh, first one at Deu 2:8
                          .replace( '  ', ' ')
                          .split( ' ' )
                          )
    WJ = '\u2060' # word joiner (makes Hebrew displays on console ugly and hard to read)
    strippedHebWords = []
    for punctuatedHebWord in punctuatedHebWords:
        if punctuatedHebWord.endswith( '׃׆ס' ):
            punctuatedHebWord = punctuatedHebWord[:-3] # Remove 'sof pasuq' and 'reverse nun' and 'samekh' Hebrew characters
        if punctuatedHebWord.endswith( '׃פ' ) or punctuatedHebWord.endswith( '׃ס' ): # We don't want to remove these from the end of normal words
            punctuatedHebWord = punctuatedHebWord[:-2] # Remove 'sof pasuq' and 'pe' or 'samekh' Hebrew characters
        strippedHebWords.append( punctuatedHebWord.lstrip( '“‘˚(' ).rstrip( '.,?!:”’·;)–…׃') ) # Last rstrip one is 'sof pasuq' and 'pe' & 'samekh' Hebrew characters
    print( f"  brightenUHB strippedHebWords={str(strippedHebWords).replace(WJ,'')}" )

    # Match Hebrew words to word numbers -- we use the original numbering which is marked as variant in UHB
    try: firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{vC}:{vV}']
    except KeyError as e:
        logging.critical( f"brightenUHB() nothing for {e}" )
        return brightenUHBTextHtml, []
    
    currentWordNumber = firstWordNumber
    hebWordNumbers = []
    for strippedHebWord in strippedHebWords:
        print( f"  {BBB} {C}:{V} strippedHebWord='{strippedHebWord.replace(WJ,'')}' {currentWordNumber=} from ({firstWordNumber},{lastWordNumber})" )
        ref, rowType, lemmaRowList, strongs, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tags = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
        hebWordNumbers.append( currentWordNumber )
        # TODO: probably d field in PSA is a problem
        if BBB!='PSA' and not f'{BBB}_{C}' in ('NUM_26','SA1_20','KI1_22','CH1_12','JOB_41'): # Num 26:1/25:19 and SA1 20:42 is a very complicated versification issue (chapter break in middle of alternative verse)
            assert currentWordNumber <= lastWordNumber, f"{currentWordNumber=} {firstWordNumber=} {lastWordNumber=}"
        currentWordNumber += 1
    if len(hebWordNumbers) != len(strippedHebWords):
        logging.critical( f"brighten UHB was unable to find word numbers for all words for {BBB} {C}:{V} (got {len(hebWordNumbers)} out of {len(strippedHebWords)})" )

    # TODO: Not totally sure that we need these extras from https://github.com/Center-for-New-Testament-Restoration/SR files
    #           now that we have the word numbers for the Hebrew words
    allExtras = None
    for verseEntry in verseEntryList:
        print( f"    vE {verseEntry=}" )
        marker, extras = verseEntry.getMarker(), verseEntry.getExtras()
        if extras: # Extras contain the info we need, like: ww @ 4 = 'Ἀρχὴ|lemma="ἀρχή" x-koine="αρχη" x-strong="G07460" x-morph="Gr,N,....NFS"'
            print( f"      ME {marker=} {extras=}" )
            if allExtras is None:
                allExtras = list( extras )
            else: allExtras += list( extras )

    classKeySet = set()
    if allExtras:
        # Find each word in brightenTextHtml, find the word info in allExtras, and then update brightenTextHtml with more classes
        searchStartIndex = verseWordNumberIndex = extraIndexOffset = 0
        for _safetyCount1 in range( len(strippedHebWords)+1 ):
            rawHebWord = strippedHebWords[verseWordNumberIndex]
            print( f"Start of loop1 {verseWordNumberIndex=} {rawHebWord=}" )
            attribDict = {}
            if rawHebWord in '־׀': # maqaf and paseq
                attribDict['lang'] = 'He'
                attribDict['morph'] = ['maqaf' if rawHebWord=='־' else 'paseq']
                verseWordNumberIndex += 1
                if verseWordNumberIndex >= len(strippedHebWords):
                    break
                searchStartIndex = ix + len(simpleHebWord)
                extraIndexOffset -= 1 # Stops the extras from advancing
                continue # nothing more to do in this loop
            ix = brightenUHBTextHtml.index( rawHebWord, searchStartIndex )
            print( f"  aE {verseWordNumberIndex=} {rawHebWord=} {searchStartIndex=} {ix=} {extraIndexOffset=}")
            assert ix != -1
            simpleHebWord = rawHebWord.lstrip( '“‘˚(' ) # TODO: Why do we need to do this again? Seems redundant
            print( f"{simpleHebWord=}" )
            ix += len(rawHebWord) - len(simpleHebWord) # Adjust for removal of any leading punctuation
            simpleHebWord = simpleHebWord.rstrip( '.,?!:”’·;)–…׃' ) # Last ones are 'sof pasuq' and was 'pe' & samekh Hebrew characters
            # if '\u2060' not in simpleHebWord: # word joiner '⁠' -- this fails for words like 'בְּ\u2060רֵאשִׁ֖ית' which has a word-joiner in it
            #     assert simpleHebWord.isalpha(), f"{simpleHebWord=}" # This doesn't seem to work for Hebrew, e.g., word 'בָּרָ֣א' fails
            assert ',' not in simpleHebWord and ':' not in simpleHebWord and '.' not in simpleHebWord and '¦' not in simpleHebWord # Do this instead
            if '־' in simpleHebWord: halt # maqaf
            for _safetyCount2 in range( 4 ): # we use this instead of while True to use extraIndexOffset to step past any possible footnotes, etc.
                print( f"     {_safetyCount2} {verseWordNumberIndex=} {extraIndexOffset=} sum={verseWordNumberIndex+extraIndexOffset} {len(allExtras)=}")
                try: extraEntry = allExtras[verseWordNumberIndex+extraIndexOffset]
                except IndexError: break # not sure why wordNumberIndex is too high (even with extraIndexOffset=0) and this happens -- first one at Gen 3:15
                print( f"     {brightenUHBTextHtml[ix:ix+20]=}… {extraEntry=}")
                extraType, extraText = extraEntry.getType(), extraEntry.getText()
                print( f"       TyTxClTx {extraType=} {extraText=} {extraEntry.getCleanText()=}")
                if extraType != 'ww': extraIndexOffset += 1; continue # it could be a footnote or something
                if extraText.startswith( f'{simpleHebWord}|' ):
                    extraText = extraText[len(simpleHebWord)+1:] # Remove the word that we've just confirmed, left with something like 'lemma="ἁμαρτία" x-koine="αμαρτιασ" x-strong="G02660" x-morph="Gr,N,....AFP"'
                    for extraTextChunk in ( extraText
                                        #    .replace( 'תּוּבַל קַיִן', 'תּוּבַל_קַיִן' ) # Need special handling for Tubal-Cain (Gen 4:22 onwards) with a space in the lemma
                                        #    .replace( 'בְּאֵר שֶׁבַע', 'בְּאֵ_שֶׁבַע' ) # Need special handling for Be'er Sheba (Gen 21:14 onwards) with a space in the lemma
                                        #    .replace( 'קִרְיַת אַרְבַּע', 'קִרְיַת_אַרְבַּע' ) # Need special handling for Kiriath Arba (Gen 23:2 onwards) with a space in the lemma
                                        #    .replace( 'בְּאֵר לַחַי רֹאִי', 'בְּאֵר_לַחַי_רֹאִי' ) # Need special handling for Be’er-Lahai-Roi (Gen 24:62 onwards) with a space in the lemma
                                        #    .replace( 'בֵּית לֶחֶם', 'בֵּית_לֶחֶם' ) # Need special handling for Beth Lechem / Bethlehem (Gen 35:19 onwards) with a space in the lemma
                                        #    .replace( 'בַּעַל חָנָן', 'בַּעַל_חָנָן' ) # Need special handling for Ba'al Hanan (Gen 36:38 onwards) with a space in the lemma
                                            .split( '" ' ) ): # Use the double quote so we don't need every special case with a space in the UHB 'lemma' field
                        print( f"    {extraTextChunk=}")
                        fieldName, fieldValue = extraTextChunk.split( '=', 1 )
                        fieldValue = fieldValue.strip( '"' )
                        if fieldName.startswith( 'x-' ): fieldName = fieldName[2:]
                        if fieldName == 'strong':
                            # assert 'H' in fieldValue, f"{fieldValue=}" # Can be something like 'b:H7225' or "l"
                            assert fieldValue.count( 'H' ) <= 1, f"{fieldValue=}" # Can be something like 'b:H7225' or "l"
                            # Seems that the ':' is a morpheme separator
                            strongs = []
                            for subFieldValue in fieldValue.split( ':' ):
                                print( f"      strong {subFieldValue=}" )
                                if subFieldValue[0] == 'H':
                                    subFieldValue = subFieldValue[1:]
                                    # assert subFieldValue.isdigit() # Fails on '7760a'
                                assert 1 <= len(subFieldValue) <= 5
                                strongs.append( subFieldValue )
                            fieldValue = strongs
                        elif fieldName == 'morph':
                            print( f"      morph field {fieldValue=}")
                            if ':' in attribDict['strong']: # 'strong' in attribDict and 
                                assert fieldValue.count(':') == attribDict['strong'].count( ':' )
                            assert fieldValue.startswith( 'He,' ) or fieldValue.startswith( 'Ar,' ), f"{fieldValue=}"
                            attribDict['lang'] = fieldValue[:2]
                            fieldValue = fieldValue[3:] # Remove unneeded? language prefix
                            # Seems that the ':' is a morpheme separator in the UHB
                            morphs = []
                            for subFieldValue in fieldValue.split( ':' ):
                                print( f"        morph {subFieldValue=}" )
                                assert 1 <= len(subFieldValue) <= 6
                                morphs.append( subFieldValue )
                            fieldValue = morphs
                        print( f"     {simpleHebWord} {fieldName}='{fieldValue}'" )
                        attribDict[fieldName] = fieldValue
                    break
                print( f"Oops!!! No match for {simpleHebWord=} {extraText=}")
                # TODO: Why do we have to disable the next two lines for NEH 7:68
            #     halt
            # else: need_to_increase_count2_for_brightenUHB
            print( f"    {attribDict=}" )
            try:
                wordLink = f'../../ref/HebWrd/{hebWordNumbers[_safetyCount1]}.htm#Top' # We'd prefer to link to our own word pages
            except IndexError:
                wordLink = f'''https://BibleHub.com/greek/{attribDict['strong'][:-1]}.htm''' # default to BibleHub by Strongs number if we don't know the word number
            caseClassName = None
            try:
                for subMorph in attribDict['morph']:
                    if subMorph[0] == 'V':
                        caseClassName = 'hebVrb'
                        break
            except KeyError:
                print( f"Error: no morph available for {simpleHebWord=} from {simpleHebWord=}" )
            try:
                for subStrong in attribDict['strong']:
                    print( f"{subStrong=}" )
                    try: subStrongInt = getLeadingInt( subStrong ) # Ignores suffixes like a,b,c
                    except ValueError: continue
                    if subStrongInt in (369, 3808): # Hebrew 'אַיִן' 'ayin' 'no', or 'לֹא' (lo) 'not'
                        caseClassName = 'hebNeg'
                        break
            except KeyError:
                print( f"Error: no strongs available for {simpleHebWord=} from {simpleHebWord=}" )
            # elif attribDict['morph'][4] != '.':
            #     try:
            #         caseClassName = f'''heb{HEBREW_CASE_CLASS_DICT[attribDict['morph'][4]]}'''
            #     except KeyError:
            #         print( f"{BBB} {C}:{V} {currentWordNumber=} {rawHebWord=} {simpleHebWord=} {attribDict=}" )
            #         raise KeyError
            if caseClassName: classKeySet.add( caseClassName )
            caseClassHtml = '' if not caseClassName else f'''class="{caseClassName}" ''' # Has a trailing space
            adjusted_morphology_fields = []
            for some_morph in attribDict['morph']:
                if len(some_morph) <= 2: # We expand these short ones
                    if some_morph[0]=='A': adjusted_morphology_fields.append( OSHB_ADJECTIVE_DICT[some_morph] ); continue
                    if some_morph[0]=='C': adjusted_morphology_fields.append( 'conjunction' ); continue
                    if some_morph[0]=='D': adjusted_morphology_fields.append( 'adverb' ); continue
                    if some_morph[0]=='N': adjusted_morphology_fields.append( OSHB_NOUN_DICT[some_morph] ); continue
                    if some_morph[0]=='P': adjusted_morphology_fields.append( OSHB_PRONOUN_DICT[some_morph] ); continue
                    if some_morph[0]=='R': adjusted_morphology_fields.append( OSHB_PREPOSITION_DICT[some_morph] ); continue
                    if some_morph[0]=='S': adjusted_morphology_fields.append( OSHB_SUFFIX_DICT[some_morph] ); continue
                    if some_morph[0]=='T': adjusted_morphology_fields.append( OSHB_PARTICLE_DICT[some_morph] ); continue
                    raise ValueError( "Some unexpected short Hebrew morphology '{some_morph}'")
                adjusted_morphology_fields.append( some_morph ) 
            titleHtml = f'''title="{'Aramic ' if attribDict['lang']=='Ar' else ''}{', '.join(adjusted_morphology_fields)}" ''' if 'morph' in attribDict else ''
            brightenUHBTextHtml = f'''{brightenUHBTextHtml[:ix]}<a {titleHtml}{caseClassHtml}href="{wordLink}">{simpleHebWord}</a>{brightenUHBTextHtml[ix+len(simpleHebWord):]}'''
            verseWordNumberIndex += 1
            if verseWordNumberIndex >= len(strippedHebWords):
                break
            searchStartIndex = ix + len(simpleHebWord)
        else: need_to_increase_count1_for_brightenUHB

    # Get the colour keys into the correct order
    classKeyList = []
    for classKey,classKeyHtml in HEBREW_CASE_CLASS_KEY_DICT.items():
        if classKey in classKeySet:
            classKeyList.append( classKeyHtml )
    # assert classKeyList # TODO: re-enable once the above is working better

    return brightenUHBTextHtml, classKeyList
# end of createParallelVersePages.brightenUHB


ENGLISH_WORD_MAP = ( # Place longer words first,
                     #     use space before to prevent accidental partial-word matches
                     #     since we're only doing string matches (but they're case sensitive)
    # Pairs of words (two words to two words)
    ((' a boot',),' a boat'),
    ((' afarre off',' afarre of',' a farre of'),' afar off'),
    ((' a none ',),' anon '),
    (('at euen ','at even ',),'at evening '),(('when euen ','when even '),'when evening '),(('when the euen ','when the even '),'when the evening '),
    (('carest for',),'care for/about'),
    (('fro God',),'from God'),
    (('get bred',),'get bread'),
    (('Hooli Goost',),'Holy Ghost'),
    (('loves have',),'loaves have'),
    (('nynthe our',),'ninth hour'),
    ((' righte hade',' right honde'),' right hand'),
    (('sche felde ',),'she fell '),
    (('swete breed','swete bred'),'sweet bread'),
    (('to bye ',),'to buy '),
    (('the see ',),'the sea '),
    (('we han ',),'we have '),
    (('with greet',),'with great'),

    # Two words into one word
    (('a fore honde','afore hand','aforehande'),'aforehand'),
    ((' all wayes ',),' always '),
    ((' any thyng',' eny thinge',' any thing'),' anything'),
    ((' can not ',),' cannot '),
    (('even tyde',),'eventide/evening'),
    (('fare wel ',),'farewell '),
    (('Hos anna ',),'Hosanna '),
    ((' in deede ',' in dede '),' indeed '),
    ((' for o ',),' into '),
    ((' for euer',),' forever'),
    ((' her selfe',' her self',' hir selfe',' hir self'),' herself'),
    ((' hym silf',' hym selfe',' him selfe',' him sylfe'),' himself'),
    ((' it selfe',' it self',' it silfe',' it silf',),' itself'),
    ((' lyke wyse',),' likewise'),
    (('money chaungeris','money chaungers'),'moneychangers'),
    (('sea syde','sea side'),'seaside'),
    (('strayght waye','streight waye'),'straightway'),
    (('taske maisters',),'taskmasters'),
    (('them selues',),'themselves'),
    (('thy selfe','thi silf','yi self'),'thyself/yourself'),
    ((' to gedder',' to geder',' to gidir'),' together'),
    (('with outen',),'without'),
    (('youre selues',),'yourselves'),

    # One word into two
    ((' assoone ',' assone '),' as soon '),
    (('gendride',),'begat/gave_birth_to'), # middle-English
    (('riythond','riythalf'),'right hand'),
    (('shalbe ',),'shall be '),(('shalbe.',),'shall be.'),
    ((' wilbe ',),' will be '),

    # Change single words (esp. middle English)
    ((' reuth ',),' pity/sorrow '),

    # Single words
    ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' abyde ',),' abide '), ((' aboute',),' about'), ((' abrode',' abroade'),' abroad'), ((' abstayne ',),' abstain '),
        ((' accorde ',' acorde '),' accord '), (('knoulechide',),'acknowledged'),
        ((' affliccion',),' affliction'), ((' afrayed',' afrayde',' afraide'),' afraid'), ((' afterwarde',' aftirward'),' afterward'),((' aftir ',' afer ',' eft '),' after '),(('Aftir',),'After'),
        ((' agaynste',' agaynst',' ageynste',' ayens'),' against'), ((' ayen,',),' again,'),((' agayne',' againe'),' again'),(('Againe',),'Again'),
        ((' aliaunt',),' alien/foreigner'), ((' aliue',' alyue',' alyve'),' alive'),
            (('Alle ',),'All '),((' alle ',' al '),' all '),((' alle,',' al,'),' all,'),
            ((' aloone',),' alone'),
            ((' alredy',),' already'),
            ((' altare',' aulter',' auter'),' altar'),
            ((' allwayes',' alwayes',' alwaies',' allwaie'),' always'),
        (('amased',),'amazed'), ((' amede',),' amend'), ((' amonge',' amoge'),' among'),
        (('Andrewe',),'Andrew'),
            ((' aungel',),' angel'), ((' angwische',),' anguish'),
            (('anoyntiden','anointide','annoynted','anoynted'),'anointed'),(('Annoynted',),'Anointed'),((' annoynt',' anoynte',' anoynt'),' anoint'),
                ((' anoon ',' anone ',' anon '),' anon/immediately '), (('Anothir',),'Another'),((' anothir',),' another'),
            (('answerden','answerede','answerde','answeride','aunswered'),'answered'),((' aunswere ',' answere '),' answer '),((' aunswere:',' answere:'),' answer:'),
            ((' ony ',' eny '),' any '), (('enythinge',),'anything'),
        (('apostlis',),'apostles'),
            (('appearaunce',),'appearance'),(('appearynge','apperynge','apperinge','appearyng'),'appearing'),((' appered',' apperide'),' appeared'),((' appeare ',),' appear '), (('appoynte','apoynte'),'appoint'),
        (('archaungel',),'archangel'), ((' aryse',),' arise'),(('Aryse ',),'Arise '), (('Arke ',),'ark '),((' arcke ',' arke '),' ark '), ((' arte ',),' art '),
        (('ascencioun',),'ascension'),
            ((' asshes',),' ashes'),
             ((' askeden',' axiden',' axide',' axed'),' asked'), ((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            (('astonnied','astonied','astonnyed','astonyed'),'astonished'), (('astromyenes',),'astronomers'),
        ((' eeten,',' eten,'),' ate,'), ((' athyrst',),' athirst'), ((' attayne ',' attaine '),' attain '),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
        ((' auoyded',),' avoided'),
        ((' awaye',' awei'),' away'),
    ((' backe ',),' back '), (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            (('basskettes','baskettes'),'baskets'), (('bastardes',),'bastards'),
            ((' batels',),' battles'),
        ((' bee ',),' be '),
            ((' bearinge',' bearynge',' beringe',' berynge'),' bearing'),((' beare ',' bere '),' bear '), (('beastes','beestes','beestis'),'beasts'),((' beesti',),' beast'),
            ((' beed ',' bedde '),' bed '),
            ((' bene ',' ben '),' been '),
            ((' bifore',' bifor'),' before'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), ((' bigat ',' begate '),' begat '), ((' beggere',' begger'),' beggar'), ((' beggide',),' begged'), (('bigynnyng','beginnynge','beginnyng','begynnynge','begynnyng','begynninge'),'beginning'), (('bigetun ','begotte '),'begotten '),
            (('behelde','biheeld'),'beheld'), ((' behinde',' bihynde',' behynde'),' behind'), ((' biholdinge',),' beholding'),(('Biholde','Beholde'),'Behold'),((' biholdist ',' biholde ', ' beholde '),' behold '),((' beholde,',),' behold,'), ((' bihoueth',),' behoves'),
            ((' beynge ',' beyng '),' being '),
            (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), (('Bileue ','Beleeue ','Beleue ','Beleve '),'Believe '),((' beleue',' beleeue',' beleve',' bileue'),' believe'), ((' belonge ',),' belong '), ((' beloued',' beloven'),' beloved'),
            ((' berith',),' beareth'),
            (('beseeching','besechyng'),'beseeching/imploring'),(('biseche ','beseech '),'beseech/implore '),(('biseche,','beseech,'),'beseech/implore,'), ((' besydes',),' besides'),((' bisidis',),' beside'),
            (('Bethanie ','Bethania ','Bethanye ','Betanye '),'Bethany '), (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '), (('bitraiede','betraied'),'betrayed'),(('bitraye ','betraye ','betraie '),'betray '), ((' betere ',),' better '), ((' bitwixe',' betweene',' betwene'),' between'),
            ((' beyonde',' biyende',' biyondis'),' beyond'),
        ((' byd ',),' bid '), ((' byde ',),' bide/stay '),
            ((' bynde',),' bind'),
            ((' briddis',),' birds'), ((' birthe',),' birth'),
        (('Blessid ',),'Blessed '),(('blesside','blissid'),'blessed'), (('blessynge',),'blessing'),
            (('blynde','blynd','blinde'),'blind'),
            (('bloude','bloud'),'blood'),
        ((' bootys',),' boats'),
            ((' boddy ',' bodi '),' body '),
            ((' booke ',' boke '),' book '),
            ((' boond ',),' bond '),
            ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'),
            ((' bosome ',' bosum '),' bosom '),
            ((' bothe ',),' both '), (('bottomlesse',),'bottomless'),
            ((' boundun ',' bounde '),' bound '),
        ((' braunches',),' branches'),((' braunch',' braunche'),' branch'),
            (('britheren',),'brethren/brothers'),(('brithre.',),'brethren/brothers.'),(('brethren:','brethre:'),'brethren/brothers:'),
            (('brycke','bricke','bryck'),'brick'), ((' bryde',),' bride'), (('bryngeth',),'bringeth/brings'),(('bryngyng',),'bringing'), (('Brynge ','Bryng '),'Bring '),((' brynge ',' bryng ',' bringe '),' bring '),
            ((' brouyten ',),' brought '),
        (('buyldynges','buildynges','bildyngis'),'buildings'),(('buyldinge',),'building'),
            ((' buriall',),' burial'),((' buryinge',' biriyng'),' burying'), ((' brent',),' burnt'),((' burne ',),' burn '),
            ((' bysy ',),' busy '),((' busines',' busynesse',' busynes'),' business'),(('businesss',),'business'), ((' byers',' biggeris'),' buyers'),
            ((' bie ',),' buy '),
        (('Bi ',),'By '),((' bi ',),' by '),
    (('Cæsar','Cesar'),'Caesar'),
            ((' clepiden',' clepide',' clepid'),' called'),(('calleth','clepith'),'calleth/calls'),((' callyng',),' calling'),((' cal ',),' call '),
            ((' cam ',' camen '),' came '),((' cam,',' camen,'),' came,'),
            ((' kunne ',),' can '), ((' candlestickes',' candelstyckes',' candlestyckes',' candilstikis'),' candlesticks'),
            (('Captaine','Captayne'),'Captain'), (('captiues',),'captives'),(('captyue',),'captive'),
            (('carnall ',),'carnal '), (('carpeter',),'carpenter'), ((' carieth',' caried'),' carried'),((' cary ',),' carry '),
            ((' castynge',' castyng',' castinge'),' casting/throwing'),((' castiden ',' kesten '),' cast/throw '),((' caste ',' keste '),' cast/threw '), (('casteles','castels'),'castles'),
            ((' cattell',' catel'),' cattle'),
        ((' ceesside',' ceessid'),' ceased'),
            (('centurien',),'centurion'),
            ((' certayne',' certein',' certaine'),' certain'),
        (('cheynes','chaines'),'chains'),(('chamber','chaumber','chambre'),'chamber/room'), (('chaunced','chaunsed'),'chanced'), (('chaungeris',),'changers'), (('charite',),'charity'), (('chastisynge',),'chastising'),(('chastisith','chasteneth'),'chastens/disciplines'),
            ((' cheife ',' chefe '),' chief '), (('chyldren',),'children'),(('childre ',),'children '), (('chylde,','childe,'),'child,'), (('chymney',),'chimney'),
            ((' chese ',),' choose '), (('chosun',),'chosen'),
            (('chirchis',),'churches'),(('chirche',),'church'),(('Churche ',),'Church '),(('Churche,',),'Church,'),
            (('Christes',),'Christ’s'),(('Christe','Crist'),'Christ'),
        ((' citees',),' cities'),((' cyte ',' citie ',' citee '),' city '),((' citie,',' citee,',' cite,'),' city,'),((' citie.',' citee.',' cite.'),' city.'),
        ((' claye ',' cley '),' clay '),((' clei,',' cley,',' claye,'),' clay,'),
            (('climbeth','clymmeth','clymeth','climeth'),'climbeth/climbs'),
            ((' clothis',),' clothes'), ((' cloudis',' cloudes'),' clouds'), ((' clouen',),' cloven'),
        ((' coostis',' coastes'),' coasts'), ((' cootis',' coottes',' coates',' cotes'),' coats'),
            ((' coold ',),' cold '), ((' coolte ',),' colt '),
            ((' cometh',' commeth'),' cometh/comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming'),' coming'),
                ((' conforted',' coforted',' coumfortid'),' comforted'),((' coumfortour',),' comforter'),
                (('commaundementes','commandementes','commandements'),'commandments'),(('commaundement','comaundement','commandement'),'commandment'),(('comaundide','comaundid','commaunded','comaunded'),'commanded'), ((' commaunde ',' commaund '),' command '), ((' comyn',),' common'),
                (('companye',),'company'), (('comprehendiden',),'comprehended'),
            (('conseyue ',),'conceive '),
                (('confessioun',),'confession'),
                (('congregacions','cogregacios'),'congregations'),(('congregacion',),'congregation'),
                (('consyderest','considerest'),'consider'), (('consolacion',),'consolation'),
                (('contynued',),'continued'),(('contynuynge',),'continuing'),
                (('conueniently','coueniently'),'conveniently'),
            (('Corinthyans',),'Corinthians'), ((' corne ',),' corn '),
            ((' coulde',' coude'),' could'), ((' councill',' councell',' counsell'),' council'), ((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre'),' country'),
            ((' couenaunt',' couenaut',' couenant'),' covenant'), ((' couered',),' covered'),
        ((' crieden',' criede',' cryed'),' cried'), (('crepell',),'crippled'),
            ((' crokid',),' crooked'), ((' crosse ',' cros '),' cross '),((' crosse,',),' cross,'), (('crownes','crounes'),'crowns'),(('coroun ','croune ','crowne ',),'crown '),
            ((' crye ',' crie '),' cry '),((' crye,',' crie,'),' cry,'),
        ((' kunnyng',),' cunning/knowledge'),
            ((' cuppe',),' cup'),
    ((' dayly',' daylie'),' daily'),
            ((' daunger ',),' danger '),
            (('derknessis','darkenesse','darknesse','darcknes','darkenes'),'darkness'),((' darknes.',),' darkness.'),
            (('douytris','doughters'),'daughters'),
            (('Daiud',),'David'),
            ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),((' daye:',' daie:',' dai:'),' day:'),
        ((' dekenes',),' deacons'), ((' deed',),' dead'), (('Deare ',),'Dear '),((' deare ',' dere '),' dear '), ((' deeth',' deth',' derth'),' death'),
            (('disseyve','disceaue','deceave','deceiue'),'deceive'),
            ((' degre ',),' degree '),
            ((' delyte',),' delight'), (('delyuerauce','deliueraunce','deliuerance'),'deliverance'),((' deliuered',' delyuered'),' delivered'),((' delyuer ',' deliuer '),' deliver '),
            ((' denne ',' deen '),' den '), ((' denyede',' denyed'),' denied'),
            ((' departide',' departid'),' departed'),(('Departe ',),'Depart '),((' departe ',),' depart '),
            (('descendinge',),'descending'),(('descende ',),'descend '),
                ((' deseert ',' deserte '),' desert '),
                ((' desirith',' desyreth',' desireth'),' desires'), ((' desyred',),' desired'),
                ((' despysed',' dispiside'),' despised'),((' despyse ',' dispise '),' despise '),
                ((' distriede',),' destroyed'),((' distrie ',' destroye ',' distroye '),' destroy '),
            ((' deuelis',' devylles',' devvyls',' deuils',' deuyls',' deuels'),' devils'),((' devyll',' deuell',' deuyll'),' devil'),
        ((' dyd ',' dide '),' did '),((' dide,',),' did,'),
            ((' dyeth ',' dieth '),' dieth/dies '), ((' dieden ',' dyed '),' died '),((' diede,',),' died,'),
            ((' discerne:',),' discern:'), (('disciplis',),'disciples'), (('disdayned',),'disdained'),(('disdaine ',),'disdain '),
                ((' dyvers',' diuers'),' diverse/various'), (('devided','deuided','deuyded'),'divided'), (('devorsement','deuorcemet','diuorcement'),'divorcement'),
        ((' doe ',),' do '),((' doe?',),' do?'),
            (('doctryne',),'doctrine'),
            ((' doist ',),' doest '),
            ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),((' doon;',),' done;'),
            ((' doores',' dores'),' doors'),((' doore',' dore'),' door'),
            ((' doute,',),' doubt,'),
            ((' doue',),' dove'),
            ((' downe',' doune',' doun'),' down'),
        (('dredden','dredde'),'dreaded'), ((' dryncke',' drynke', ' drinke'),' drink'), ((' driueth',' driveth'),' drives'), ((' driue',' dryue'),' drive'),
            ((' drave',' droue'),' drove'), ((' drie ',),' dry '),((' dryed',),' dried'),
        ((' duste ',),' dust '), ((' duetie ',),' duty '),
        (('dwelliden','dwellide','dwellyde'),'dwelled/dwelt'),(('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
    ((' ech ',),' each '),
            ((' eerli',' erly'),' early'), ((' eares ',' eeris ',' eris '),' ears '), ((' erthe',' erth',' `erthe'),' earth'),
            (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'), ((' easyer',),' easier'), ((' eest ',),' east '),
            ((' etynge',' eatyng'),' eating'),((' eate ',' ete '),' eat '),((' eate,',' ete,'),' eat,'),((' eate.',' ete.'),' eat.'),((' eate:',' ete:'),' eat:'),((' eate;',' ete;'),' eat;'),
        (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
        (('Egipte',),'Egypt'),
        ((' eldere ',),' elder '), (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'),
            ((' els ',),' else '),((' els,',),' else,'),
        (('Emperours',),'Emperors'),((' emperours',),' emperors'),(('Emperoure',),'Emperor'),((' emperoure',),' emperor'), ((' emptie,',),' empty,'),
        ((' ende ',),' end '),((' ende,',),' end,'), (('ynough','inough'),'enough'), ((' entred',' entriden',' entride',' entrid'),' entered'),((' entereth',' entreth'),' entereth/enters'),((' entre ',),' enter '),
        (('Hester',),'Esther'),
        (('euangelisynge',),'evangelising'),
            (('Euen ',),'Even '),((' euen ',),' even '), ((' euenyng',' euening'),' evening'),((' euentid ',),' eventide/evening '), (('euen ',),'even '), # At beginning of sentence
            (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' eueremore',' euermore'),' evermore'), (('Euery',),'Every'),((' euery',),' every'), ((' euer ',),' ever '),
        ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll',' evell'),' evil'),
        (('excedyngly','exceadingly','exceedyngly'),'exceedingly'), ((' excepte ',),' except '), ((' exercyse ',),' exercise '),
        ((' iyen,',),' eyes,'),((' iyen.',),' eyes.'),((' iyen;',),' eyes;'),
    ((' failinge',),' failing'), ((' fayle ',),' fail '), ((' faynte ',' faynt '),' faint '), ((' feith',' fayth'),' faith'),
            ((' falle ',),' fall '),
            ((' farre ',),' far '),((' farre.',' fer.'),' far.'),
            ((' fastynge',' fastyng',' fastinge'),' fasting'),
            ((' fadris',),' fathers'),((' fadir',),' father'), ((' fauoure',),' favour'),
        ((' feare ',),' fear '), ((' feete',' fete'),' feet'), ((' fel ',),' fell '), ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),((' feawe.',' fewe.'),' few.'),
        ((' fielde',' feeld',' felde'),' field'), ((' feendis',),' fiends'),
            ((' figges',' fygges'),' figs'),((' fygge ',' fyge ',' figge ',' fige ',),' fig '), ((' fiytyng',),' fighting'),(('Fyght',),'Fight'),((' fyght',' fighte'),' fight'),
            (('fylthynesse','filthynes'),'filthiness'),
            ((' fynde ',' finde '),' find '),((' fynnyssher',' fynissher',' finissher'),' finisher'),
            ((' fier ',' fyre '),' fire '),((' fier,',' fyre,'),' fire,'),((' fyre:',),' fire:'),((' fier;',),' fire;'), ((' fyrste',' firste',' fyrst'),' first'),
            (('fischis','fysshes','fyshes'),'fishes'),(('fisscheris','fisshers','fysshers'),'fishers'),
            ((' fyue',' fyve',' fiue'),' five'),
        ((' flye ',' fleen ',' fle '),' flee '), ((' fleischli ',),' fleshly '),((' flesshe',' fleshe',' fleische',' fleisch'),' flesh'),
            ((' flyght ',),' flight '),
            (('flockis',),'flocks'),
                (('floude,',),'flood,'),
                (('flowith ','floweth '),'floweth/flows '),
        ((' foale ',),' foal '),
            ((' foold ',),' fold '), ((' folkis',),' folks/people'), ((' folowed',' folewiden',' suede'),' followed'), ((' folowe',' folow',' suen'),' follow'), (('Folowe','Folow'),'Follow'), ((' foli ',),' folly '),
            (('foolishnesse','folishnes'),'foolishness'), ((' foote ',' fote '),' foot '),
            (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '),
                ((' fourme,',' forme,'),' form,'),
                ((' fornicacion',),' fornication'),
                ((' forsooke',' forsoke',),' forsook'),((' foorth',' forthe'),' forth'),
                ((' fourtie',' fourtye',' fourti'),' forty'),
            ((' founden ',' founde ',' foond ',' foud '),' found '), ((' fowre',' foure',' fower'),' four'),
            ((' foules ',),' fowls/birds '),((' foule ',),' fowl/bird(s) '),
        ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'),
            ((' freend',' frende'),' friend'), (('Fro ',),'From '),((' fro ',),' from '), ((' fruyt ',' frute ',' fruite '),' fruit '),
        ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
    (('Gayus',),'Gaius'), (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'), ((' galoun',),' gallon'),
            ((' garmentes',' garmetes'),' garments'),((' garmente ',),' garment '), (('garnisshed','garnysshed'),'garnished'),
            ((' yate',),' gate'), (('gadirid','gaderid','gaddered','gadered','gaddred'),'gathered'),((' gadere ',' gaddre ',' gadre ',' geder '),' gather '),
            ((' yaf ',' gaue '),' gave '),
        (('generacioun','generacion'),'generation'),((' gentyls',),' gentiles'),
        ((' goost',),' ghost'),
        ((' yyueth',' geueth'),' giveth/gives'), ((' geven',' giuen',' geuen',' youun',' youe',' yyuen'),' given'), (('Geue ','Giue '),'Give '),((' geve ',' geue ',' giue ',' yyue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'),((' yyue?',' geue?',' geve?'),' give?'),
        ((' girdil',' gerdyll',' gerdell'),' girdle'),
        ((' gladde ',),' glad '), ((' glorie',),' glory'),
        (('Goo ','Goe '),'Go '),(('Goo,','Goe,'),'Go,'),((' goe ',' goo '),' go '),((' goe.',' goo.'),' go.'),
            ((' goeth ',' goith '),' goeth/goes '), ((' goinge ',' goyng '),' going '),
            ((' golde ',),' gold '),((' golde.',),' gold.'),
            ((' goon ',),' gone '),
            (('Gospell',),'Gospel'),((' gospell',),' gospel'),
        (('Graunte ','Graunt '),'Grant '),((' graunte ',' graunt ',' graut '),' grant '), ((' graue.',),' grave.'),
            (('gretter',),'greater'),(('greate ','grete ','greet ','grett ','gret '),'great '),(('grett.','greate.','greet.'),'great.'),
            (('greeueth ',),'grieveth/grieves '),(('greeuous','grieuous'),'grievous'),
            (('growne ',),'grown '),
            (('grounde',),'ground'), (('grutchyng',),'groutching/grudging'),
        ((' ghest',' geest',' gest'),' guest'),
    ((' hadden ',' hadde '),' had '),((' hadde;',),' had;'), ((' heeris',),' hairs'),
            ((' handes',' hondes',' hoondis',' hondis'),' hands'),((' hande ',' honde ',' hoond ',' hond '),' hand '),
            ((' happe ',),' happen '), ((' happili',' haply'),' happily'),
            ((' hardnesse ',' hardnes '),' hardness '), ((' haruest',' heruest'),' harvest'),
            ((' hath ',),' hath/has '),
            (('Haue ',),'Have '),((' haue ',' han '),' have '), ((' havinge',' hauinge',' hauing',' hauynge',' havynge',' hauyng'),' having'),
        ((' hee ',),' he '),
            ((' heades',' heddes',' heedis'),' heads'), ((' helide',' heelid'),' healed'), ((' helthe ',),' health '), ((' hearde',' herden',' herde',' herd'),' heard'),((' herynge',' hearyng',' heryng',' hearinge',' heringe',' hering'),' hearing'),((' heareth',' herith'),' hears'),((' heare',' heere'),' hear'),
                (('Heythen',),'Heathen'),((' hethene',),' heathen'),
                ((' heyre ',' heire '),' heir '),
                ((' hertis',' hertes',' heartes'),' hearts'),((' herte ',' hert '),' heart '), ((' heate',' heete'),' heat'), ((' heauens',' heuenes'),' heavens'), ((' heauen',' heuene',' heven'),' heaven'),
            (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), (('Hebrewe ','Hebrue ','Ebreu '),'Hebrew '),((' hebrue ',),' hebrew '),
            ((' hede ',' heede '),' heed '),
            ((' helde ',),' held '), ((' helle ',),' hell '), ((' helpe ',),' help '),
            ((' hir ',' hyr '),' her '),((' hir,',),' her,'),((' hir.',),' her.'),((' hir;',),' her;'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), (('Erodians',),'Herodians'),(('Herodes',),"Herod's"),(('Herode ','Eroude '),'Herod '), (('Eroude,',),'Herod,'),
        ((' hidde ',),' hid '),
            ((' hiyeste',' hiyest'),' highest'),((' hye ',' hie ',' hiy '),' high '),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',' hi:'),' him:'),((' hym?',),' him?'), (('himselfe',),'himself'),
            ((' hiryd',' hyred'),' hired'), ((' hise ',' hys '),' his '),
            ((' hyther',' hidder',' hidir'),' hither'),
        ((' holde ',),' hold '), ((' holynesse',' holynes'),' holiness'),((' holines ',),' holiness '),((' hooli ',' holie '),' holy '),((' hooli.',' holie.'),' holy.'),
            (('honeste','honestye','honestie'),'honesty'), ((' hony',),' honey'), ((' onoure',' onour'),' honour'),(('honoure,',),'honour,'),
            (('Hosyanna','Osanna'),'Hosanna'),
            ((' houres',),' hours'),((' houre ',),' hour '), ((' housse ',' hous '),' house '),((' housse',),' house'),((' hous,',),' house,'), (('houssholde','housholde'),'household'),
            ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
        ((' hundrid',),' hundred'), ((' hungren',),' hungering'),((' hungride',' hungred',' hugred'),' hungered'),((' hungur',' honger'),' hunger'), ((' hurte ',),' hurt '), (('husbande','hosebonde'),'husband'),
        ((' hypocrisie',' ypocrisye'),' hypocrisy'),
    (('Y ',),'I '),((' Y ',),' I '),((' Y;',),' I;'),
        ((' Yd',),' Id'), ((' idel ',),' idle '), ((' ydols',),' idols'),
        (('Yf ',),'If '),((' yff ',' yf '),' if '), ((' ymage ',),' image '), (('Ys ',),'Is '),((' ys ',),' is '), ((' yssue',),' issue'),
        (('Yt ',),'It '),((' yt ',),' it '),
        (('encreased',),'increased'), (('indignacioun',),'indignation'), ((' inheret ',' inherite '),' inherit '), (('interpretacion',),'interpretation'),(('interprete ',),'interpret '),
        (('immediatelye','immediatly'),'immediately'),
    ((' ioperdy',),' jeopardy'),
        (('Iorney',),'Journey'),(('iourney',),'journey'),
            ((' ioyous',),' joyous'),((' ioye ',' ioy '),' joy '),
        (('iudgement','iudgment'),'judgement'),((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'), ((' iust ',),' just '),
    ((' keperis',),' keepers'),((' keepeth',' kepith',' kepeth'),' keepeth/keeps'),((' keepe',' kepe'),' keep'),
            ((' keyes',' keies'),' keys'),((' kaye ',' keye '),' key '),
        ((' killiden',' kylled',' kyllid'),' killed'),
            ((' kyndes',' kindes'),' kinds'),((' kynde',),' kind'), (('kingdome','kyngdoom','kyngdome','kyngdom'),'kingdom'), ((' kynges',' kyngis',' kinges'),' kings'),((' kynge ',' kyng '),' king '),((' kynge,',' kyng,'),' king,'),((' kynge.',' kyng.'),' king.'), ((' kynysman',' kynsman'),' kinsman'),((' kynnysmen',),' kinsmen'), ((' kynne',),' kin'),((' kyn,',),' kin,'),
            ((' kiste ',' kyssed '),' kissed '),
        (('knewest','knewen','knewe'),'knew'),
        (('knowith ','knoweth ',),'knoweth/knows '),(('knowyng',),'knowing'), (('knowne','knowun','knowen'),'known'), (('Knowe',),'Know'),((' knowe',' woot'),' know'),
    ((' labor',),' labour'), ((' lomb ',' lambe ',' labe '),' lamb '),(('Lambe',),'Lamb'), ((' lastynge',),' lasting'),
            ((' lande ',' londe ',' lond ',' lode '),' land '),((' lande,',' londe,',' lond,'),' land,'),((' loond.',' lande.',' londe.',' lond.'),' land.'),((' lande;',' londe;',' lond;'),' land;'),
            ((' laste ',),' last '),
            ((' laye ',),' lay '), ((' layed',' layde',' leiden', ' leyd',' layd'),' laid'),
            ((' leeueful',' leueful',' laufull',' lawfull'),' lawful'), (('Lawe.',),'Law.'),((' lawe ',),' law '),((' lawe,',),' law,'),((' lawe.',),' law.'),
        (('ledith','ledeth'),'leadeth/leads'), (('learnyng','learninge','lernynge'),'learning'),((' learne ',' lerne '),' learn '),(('Learne ','Lerne '),'Learn '), ((' leest',),' least'), ((' leeues',' leaues',' leves'),' leaves'), ((' leeue ',' leaue ',' leue ',' leve '),' leave '), ((' leauen',' leuen',' leven'),' leaven'),
            ((' ledde ',' leden '),' led '),
            ((' leften',' leeft',' lefte'),' left'),
            (('Leuite',),'Levite'),
        (('lyberte','libertie'),'liberty'),
            ((' lyffe',' lyfe',' lijf'),' life'),
            ((' leityngis',' lyghtnynges',' lightnynges'),' lightnings'), (('Liyt ',),'Light '),((' lyght',' liyt'),' light'),
            (('Lykewyse',),'Likewise'),(('lykewyse','likewyse'),'likewise'), ((' lyke',' lijk',' lijc'),' like'),
            ((' lynage ',),' lineage '),
            ((' litil',' lytell',' lytle',' litle'),' little'),
            ((' liueth',' lyueth'),' liveth/lives'),((' liues',),' lives'),((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),((' liue ',' lyue '),' live '),((' liue,',' lyue,'),' live,'),
        ((' looues',' loaues'),' loaves'),
            ((' loynes',),' loins'),
            ((' longe ',),' long '),((' longe,',),' long,'),
            ((' lokide',' loked'),' looked'),(('lokynge',),'looking'),(('Lokyng ',),'Looking '),(('Loke ',),'Look '),((' looke ',' loke '),' look '), ((' loosyng',' loosinge'),' loosing'),
            ((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),
            (('Loth',),'Lot'),
            ((' loude ',),' loud '),
            ((' louede',' loued',' louyde'),' loved'),((' loveth',' loueth'),' loveth/loves'),((' lovest',' louest'),' lovest/love'),((' louen ',' loue '),' love '),((' loue.',),' love.'),
    ((' maad',),' made'),
            ((' maydens',),' maidens'),((' mayden ',),' maiden '), ((' maydes',),' maids'),((' mayde,',),' maid,'), ((' maymed',),' maimed'),
            ((' makynge',),' making'),((' makere ',),' maker '),
            ((' mannus',),' man\'s'),((' ma ',),' man '), ((' mankynde',),' mankind'),((' mankinde,',),' mankind,'), ((' manere',' maner'),' manner'), ((' manye ',),' many '),
            ((' mariage',),' marriage'), ((' maried',),' married'), (('marueyled','marueiled','merveled','marueled','merveyled','marveled'),'marvelled'), (('Maryes',),"Mary's/Maria's"),(('Marye','Marie'),'Mary/Maria'),
            (('Maister','Maistir'),'Master'),((' maister',),' master'),
            ((' mayest',' mayste',' mayst',' maiest'),' mayest/may'),((' maye ',' maie '),' may '),((' maye.',),' may.'),(('Maye ',),'May '),
        ((' mesure',),' measure'),
            ((' `metis ',' metis '),' meats '),((' meate ',),' meat '),
            ((' meeke ',' meke '),' meek '),((' meeke:',' meke:'),' meek:'), ((' metinge',' metyng'),' meeting'),((' meete ',' mete '),' meet '),((' meete,',' mete,'),' meet,'),((' meete:',' mete:'),' meet:'), (('meekenes','mekenes','meknes'),'meekness'),
            ((' mendynge',' mendyng',' mendinge'),' mending'),
            ((' mercyfull ',' mercifull '),' merciful '),((' mercyfull:',' mercifull:'),' merciful:'),
            (('messauger',),'messenger'),
        ((' myddil',),' middle'),
            ((' myghty',' mightie',' miyti'),' mighty'),((' myyte',' myght'),' might'),
            ((' mylke ',' milke '),' milk '), (('mylstone','milstone'),'millstone'),
            ((' myndes',' mindes'),' minds'),((' mynde',),' mind'), ((' myne ',' myn '),' mine '), (('ministred','mynistred','mynystriden'),'ministered'),((' mynyster',' mynister'),' minister'),
            ((' myracles',),' miracles'),
        ((' mony',),' money'), ((' monethe',' moneth'),' month'),
            ((' moone ',' mone '),' moon '), 
            (('Mardochee','Mardocheus'),'Mordecai'),
                (('Moreouer','Morouer'),'Moreover/What\'s_more'),(('morouer',),'moreover/what\'s_more'), ((' moare ',' mowe '),' more '),
                ((' morninge',' mornynge',' mornyng',' morewtid',' morewe'),' morning'),
                ((' morowe',' morow'),' morrow'),
            (('Moises','Moyses'),'Moses'),
            ((' moder ',' modir '),' mother '),
            ((' mountaynes',' moutaynes',' mountaines'),' mountains'),((' mountayne',' mountaine'),' mountain'), ((' moute ',),' mount '), ((' mornen ',' mourne ',' morne '),' mourn '),((' mornen,',' mourne,',' morne,'),' mourn,'),((' mornen:',' mourne:',' morne:'),' mourn:'),
            ((' mouyng',),' moving'),((' moued',),' moved'),((' moue ',),' move '),
        ((' myche',' moche',' moch',' muche'),' much'), (('murthurers',),'murderers'),(('murthurer',),'murderer'),
    (('Naomy','Naemi'),'Naomi'), ((' naciouns',' nacions'),' nations'), ((' natiue',),' native'),
        ((' neere ',' neare '),' near '),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),
            ((' nedeful',),' needful'),((' nedes',),' needs'),((' neede ',' neade ',' nede '),' need '),
            ((' neiyboris',' neghboures',' neghbours',' neyghbours'),' neighbours'),((' neiybore',),' neighbour'), (('Nether ',),'Neither '),((' nether',' nethir'),' neither'),(('(nether',),'(neither'),
            ((' nettes',' nettis'),' nets'),
            (('Neverthelesse ','Neuertheles ',),'Nevertheless '),(('Neuertheles,',),'Nevertheless,'), ((' neuere',' neuer'),' never'),
            ((' newe ',),' new '),
            ((' nexte',),' next'),
        ((' neer ',' nyer ',' nier '),' nigher/nearer '),((' nyy ',' nye '),' nigh/near '),((' nyy.',' nye.'),' nigh/near.'), ((' nyyti',' nyyt',' nyght',' nighte'),' night'), ((' nyenth',' nynthe',' nynth'),' ninth'),
        ((' ner ',' ne '),' nor '), (('northwarde',),'northward'),
            (('nothinge','nothyng'),'nothing'),
            ((' nouyt ',),' nought/nothing '),
        (('Nowe ',),'Now '),((' nowe ',),' now '),
        (('numbred',),'numbered'),(('noumbre','nombre','nomber'),'number'),
    ((' othe ',' ooth '),' oath '),
        ((' obteyne ',' obteine '),' obtain '),
        ((' of;',),' off;'), ((' offende ',),' offend '),((' offende,',),' offend,'), ((' offerynge',),' offering'), ((' offred',),' offered'),
        ((' oyle ',),' oil '),((' oyle,',),' oil,'), ((' oynement',' oyntment'),' ointment'),
        ((' eeld ',' eld ',' olde '),' old '),((' eeld,',' olde,'),' old,'),
            (('Oliuete','olivete'),'Olivet'),(('Olyues','Oliues'),'Olives'),((' olyues',),' olives'), (('Oliue',),'Olive'),((' olyue ',' olyve ',' oliue '),' olive '),
        ((' oon ',),' one '),((' oon.',),' one.'), ((' onely ',' `oon '),' only '),
        ((' openyde',' openyd'),' opened'), ((' opynyouns',),' opinions'), ((' oppressith',),' oppresses'),
        ((' ordayned',' ordeined',' ordeynede',' ordeyned'),' ordained'),((' ordayne ',),' ordain '),
        (('Othere','Othir','Wother'),'Other'),((' othere',' othir'),' other'),
        ((' oure ',),' our '),
            ((' outwarde',),' outward'), ((' oute.',),' out.'),
        ((' ouer ',),' over '), (('ouercommeth','ouercometh'),'overcometh/overcomes'), ((' ouercome',),' overcome'),
        ((' awne ',' owne '),' own '),
    ((' paynes',),' pains'),
            ((' parablis',),' parables'), ((' partynge',),' parting'), ((' parts',' parties'),' parts/region'),
            (('Passeouer','Passouer'),'Passover'),((' passiden',' passide'),' passed'),((' passynge',),' passing'),((' passe ',),' pass '),((' passe?',),' pass?'),((' passe:',),' pass:'),
            ((' pacience',),' patience'),
            (('Pavl',),'Paul'),
            ((' paye ',),' pay '),
        ((' pees',),' peace'),
            (('penaunce',),'penance'), ((' penie ',' peny '),' penny '),((' penie,',' peny,'),' penny,'),
            (('puplis',),'peoples'),((' puple',' pople'),' people'),
            (('perceiued','perceaved','perceaued'),'perceived'),(('Perceave','Perceiue'),'Perceive'),((' witen',),' perceive'),
                ((' perfaicte ',),' perfect '), ((' perfourme ',),' perform '),
                ((' perel ',),' peril '),((' perel.',),' peril.'), ((' perische',' perisshe',' perishe'),' perish'),
                (('persecucioun','persecucion'),'persecution'),
                (('perteyneth',),'pertaineth/pertains'),(('perteyninge','parteyning','pertayninge'),'pertaining'),(('pertayne ',),'pertain '),
            (('Petir',),'Peter'),
        (('Fariseis','Farisees','Pharises','pharisees','pharises'),'Pharisees'), (('Philippe',),'Philip'),
        ((' peaces',' peeces',' peces'),' pieces'), ((' pearced',),' pierced'),
            ((' pylgrym',),' pilgrim'),
            ((' pyned',),' pined'),
            ((' pytte',' pytt',' pyt'),' pit'), ((' reuthe',),' pity'),
        (('playnely','playnly','plainely'),'plainly'), ((' playne ',' plaine '),' plain '),
            ((' plese ',),' please '), ((' pleside',' plesid'),' pleased'), ((' plente ',),' plenty '),
            ((' plucke ',),' pluck '),
        ((' poole ',),' pool '), ((' poore ',' povre ',' pore '),' poor '),
            (('possessyoun',),'possession'),(('possesse ',),'possess '),
            ((' pottere',),' potter'),
            ((' powdir',),' powder'),
        (('praysed',),'praised'), (('preyeden','preiede','praied'),'prayed'),(('preier',),'prayer'),(('preyng',),'praying'),((' preye ',' praye '),' pray '),((' praye:',),' pray:'),((' praye.',),' pray.'),
            (('prechiden','prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ','preache '),'preach '), (('preuent',),'prevent'),
            (('preestis','prestis','prestes','priestes'),'priests'),(('Priestes','Prestes'),'Priests'),(('prieste','preste','prest',),'priest'), (('princis','prynces'),'princes'),
                (('prisouneris','presoners'),'prisoners'), (('pryuatly',),'privately'),
            (('proffet',),'profit'), (('promysed','bihiyten'),'promised'), (('Prophetes',),'Prophets'),(('profetis','prophetes'),'prophets'), (('Prophete',),'Prophet'),((' prophete ',),' prophet '),((' prophete,',),' prophet,'),((' prophete.',),' prophet.'),((' prophete?',' profete?'),' prophet?'),
                ((' preued',),' proved'),((' proue ',),' prove '), (('prouerbe',),'proverb'), (('prouynces','prouinces'),'provinces'),
        (('publysshed',),'published'),
            ((' pourses',),' purses'), (('Sue ',),'Pursue '),
            ((' putteth ',),' putteth/puts '),
    (('quenchid','queched'),'quenched'),
        (('quike',),'quick/alive'),
    (('Rabi',),'Rabbi'), ((' raysed',),' raised'),((' reise',' reyse',' rayse'),' raise'),
        ((' redi ',),' ready '), ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'),
            ((' resseyueth',' receaveth',' receaueth',' receiueth'),' receives'),((' resseyueden',' resseyuede',' receaved',' receaued',' receiued'),' received'),((' resseyue',' receave',' receaue',' receiue'),' receive'), (('recompence',),'recompense'), ((' recorde ',),' record '), (('recouering',),'recovering'),
            ((' redde ',' reed '),' red '),
            (('refrayne ',),'refrain '),
            (('regardest',),'regard'),
            ((' raygne ',),' reign '),
            (('remayned',),'remained'),(('remaynynge','remayninge','remayning'),'remaining'),
                (('remembraunce',),'remembrance'),
                (('remyssion','remissioun'),'remission'),
                ((' remooue ',),' remove '),
            (('repentaunce',),'repentance'), ((' reptils',),' reptiles'),
            ((' reste ',),' rest '), (('ressurreccioun','resurreccion'),'resurrection'),
            ((' returne ',),' return '),
            ((' rewarde ',),' reward '),((' rewarde.',),' reward.'),
        ((' riche ',),' rich '),
            ((' ryght ',' riyt '),' right '), (('riytwisnesse ','rightewesnes ','righteousnes '),'righteousness '),(('riytwisnesse,','rightewesnes,','righteousnes,'),'righteousness,'),(('riytwisnesse:','rightewesnes:','righteousnes:'),'righteousness:'),((' ryghteous',),' righteous'),
            ((' risith',),' riseth/rises'), ((' ryse ',),' rise '),
        ((' rodde ',),' rod/staff '),((' rodde:',),' rod/staff:'),
            ((' roofe',' rofe'),' roof'), ((' roume',' rowme'),' room'), ((' rootis',),' roots'),((' roote',' rote'),' root'),
            ((' roos ',),' rose '),
        (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
    (('Sabbathes',),'Sabbaths'),((' sabatys',),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabat',' saboth'),' sabbath'),
            (('sackecloth',),'sackcloth'), ((' sacrifise',),' sacrifice'),
            (('Saduceis','Saduces','Sadduces'),'Sadducees'),
            ((' saaf',),' safe'),
            ((' seyden',' seiden',' seide',' seid',' sayde',' sayd',' saide', ' seien'),' said'),
            ((' saltid',),' salted'),
            ((' sate ',),' sat '), (('Sathanas','Sathan'),'Satan'), ((' satisfie ',),' satisfy '),
            ((' saued',),' saved'),((' saue ',),' save '),((' sauyng',' sauinge',' sauing',' savinge'),' saving'), ((' sauery',),' savoury'),
            ((' sawe ',' sai ',' sayn ',' siy '),' saw '),
            ((' seist',),' sayest'),((' sayege',' sayinge',' saynge'),' saying'), ((' seith ',' sayth '),' saith/says '), ((' seie ',' seye ',' saye '),' say '),((' seie,',' saye,'),' say,'),((' seie:',' saye:'),' say:'),
        (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
        (('seesyde ' ,'seeside ',),'seaside '), ((' seete ',' seet ',' seate '),' seat '),
            ((' secounde ',' seconde '),' second '),
            ((' seynge',' seinge',' seyng'),' seeing'),((' seiy ',' se '),' see '),((' se.',),' see.'), ((' seede ',' sede '),' seed '), ((' seken ',' seeke ',' seke '),' seek '), ((' semeth',),' seemeth/seems'),((' semen ',' seeme ',' seme '),' seem '), ((' seyn ',' seene ',' sene '),' seen '),((' seyn,',' seene,',' sene,'),' seen,'),
            ((' silfe ',' silf ',' selfe '),' self '),((' selfe,',),' self,'),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'), ((' silleris',),' sellers'), ((' selues',),' selves'),
            ((' sendeth',' sendith'),' sendeth/sends'),((' sende ',),' send '), ((' senten ',' sente '),' sent '),
            ((' sermoun',),' sermon'), ((' serue ',),' serve '), (('seruauntis','seruauntes','servauntes','seruants','servantes'),'servants'),((' seruaunt',' servaunt',' seruant',' seruaut',' servaut'),' servant'),
            ((' sette ',),' set '),
            (('seuenthe ','seuenth '),'seventh '),((' seuene ',' seuen ',' seue '),' seven '),
        ((' schal ',' shal ',),' shall '),
            (('Sche ',),'She '),((' sche ',' shee '),' she '), (('sheddinge',),'shedding'), (('sheepefolde','sheepfolde','shepefolde'),'sheepfold'), ((' scheep ',' sheepe ',' shepe '),' sheep '),((' scheep,',' sheepe,',' shepe,'),' sheep,'), (('scheepherdis',),'shepherds'),(('scheepherde','shepeherde','shepherde','sheephearde','shephearde','shepheard'),'shepherd'),
            (('schyneth','shyneth'),'shineth/shines'),(('schynynge',),'shining'), ((' shippes',),' ships'),((' shyppe',' shyp',' shippe',' schip'),' ship'),
            ((' shue',),' shoe'),((' schoo.',),' shoe.'), ((' shoore',),' shore'), (('shouldest','schulen','schuldist'),'should'),((' schulden ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '), (('shoute ','showte '),'shout '), (('shewyng','shewinge','shewing'),'showing'),(('schewide','schewid','shewed'),'showed'),((' schewe ',' shewe '),' show '),
        (('sijknessis',),'sicknesses'),((' syknesse',' sicknesse',' sickenes'),' sickness'),((' sicke',' sijk'),' sick'),
            ((' syde ',),' side '),((' syde.',),' side.'),((' syde:',),' side:'),
            ((' syght ',' sighte ',' siyt '),' sight '),((' sighte,',),' sight,'), ((' signes',),' signs'),((' signe ',),' sign '),
            ((' siluer',),' silver'),
            (('Symount','Symon'),'Simon'), ((' simulacion',),' simulation'),
            ((' sence ',' sithen '),' since '), ((' synners',),' sinners'),((' synner',),' sinner'), ((' synfull',' synful'),' sinful'),((' sinnes',' synnes'),' sins'),((' synnede',' synned'),' sinned'),((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),
            ((' sistris',' systers'),' sisters'),((' sistir',),' sister'),
            ((' sittynge',' syttyng'),' sitting'),((' sitten ',' sitte ',' syt '),' sit '), ((' liggynge',),' situated'),
            ((' sixte ',' sixt '),' sixth '), ((' sixe ',),' six '),
        ((' skynne ',' skyn ',' skinne '),' skin '),
        ((' slayn',' slaine'),' slain/killed'),((' sleye ',' slaye ',' sle '),' slay/kill '), (('sclaundrid',),'slandered/disgraced'),
            ((' slepith',),' sleeps'),((' slepte ',),' slept '),(('Sleepe ','Slepe '),'Sleep '),((' sleepe',' slepe'),' sleep'),
            ((' slyme ',),' slime/mud '),
        ((' smale ',),' small '),
        (('Sodome ','zodom '),'Sodom '),
            ((' soiourne',),' sojourn'),
            ((' solde ',),' sold '), ((' solitarie',),' solitary'),
            ((' summe ',),' some '), (('somwhat','sumwhat'),'somewhat'),
            ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,',),'Son,'),
            ((' sorewis',' sorowes'),' sorrows'),((' sorewe ',),' sorrow '),((' sorowe,',),' sorrow,'), ((' sory ',),' sorry '),
            ((' souyten',),' sought'), ((' sounde',),' sound'), (('southwarde',),'southward'), (('souereynes',),'sovereigns'),
        ((' spette ',' spate '),' spat '),
            (('speakynge','spekynge','speakinge','spekinge','speakyng'),'speaking'),((' spekith',' speaketh'),' speaks'),((' speake',),' speak'),
            ((' spyed',),' spied'), ((' spirites',' spiritis',' spretes'),' spirits'),(('Spiryt',),'Spirit'),((' spirite',' sprete'),' spirit'), (('spotil','spetil','spettle'),'spittle'),
            ((' spak ',),' spoke '),
            ((' sprede ',' spred '),' spread '),
        ((' staffe ',),' staff '), (('stondinge','standyng','stodinge'),'standing'),((' stondith',),' standeth/stands'),((' stande ',' stonde '),' stand '),((' stonde.',),' stand.'), ((' starre',),' star'),
            (('Steppe ',),'Step '),
            ((' styll',),' still'),
            ((' stockis',),' stocks'), ((' stoonys',),' stones'),((' stoone',' stoon'),' stone'), ((' stoode',' stonden',' stoden',' stode'),' stood'), ((' stoupe',' stowpe'),' stoop'),
            (('strayght',),'straight'), (('straunger',),'stranger'),(('straunge ',),'strange '),
                ((' strewiden ',' strawed ',' strowed '),' strewed '),
                ((' strijf',' stryfe'),' strife'),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'),(('stryve','stryue','striue'),'strive'),
            (('stumbleth','stombleth','stomblith'),'stumbles'),
        (('subiection','subieccion'),'subjection'),((' suget',),' subject'), (('substaunce',),'substance'), ((' subtill ',' subtil '),' subtle '),
            ((' soch ',' suche ',' siche ',' sich '),' such '), ((' soucke ',' sucke '),' suck '),
            (('suffrith',),'suffereth/suffers'),((' suffride',' suffred'),' suffered'),(('Suffre ',),'Suffer '),((' suffre ',),' suffer '), (('suffysed','suffised'),'sufficed'),
            (('Sommer',),'Summer'),((' sommer ',' somer '),' summer '),
            ((' sunne ',),' sun '),
            (('superscripcion',),'superscription'), ((' soper ',),' supper '), (('supplicacion',),'supplication'),
            (('Shushan','Susan'),'Susa'), # What about Susanna in NT?
        (('swete ',),'sweet '),
        (('synagoge',),'synagogue'),
    (('tabernaclis',),'tabernacles/tents'),
            ((' takun',),' taken'), ((' takynge',),' taking'),(('Takyng',),'Taking'),
            ((' talke.',),' talk.'),
            ((' taried',),' tarried/waited'),(('Tarye ','Tary '),'Tarry/Wait '),
            (('taskemasters:',),'taskmasters:'), ((' taist ',),' taste '),
            ((' tauyte',),' taught'),
        (('techyng','teching'),'teaching'),((' teachest',' teache',' techist',' teche'),' teach'),
            (('temptacioun','temptacion','teptacion','tentation'),'temptation'), (('temptiden','temptid'),'tempted'), ((' tempte ',' tepte '),' tempt '),
            ((' tenauntes',),' tenants'), ((' tendre',' teder'),' tender'), ((' tentes',),' tents'), ((' tenthe',),' tenth'),
            (('testifie ','testifye ','testyfye '),'testify '), (('testimoniall',),'testimonial'),
        (('thankes','thakes'),'thanks'),(('thanke ',),'thank '), (('Thilke ',),'That '),((' thilke ',),' that '),
            ((' theyr ',),' their '),
                ((' hem ',),' them '),((' hem,',' the,'),' them,'),((' hem.',' the.'),' them.'), (('themselues',),'themselves'), (('Thanne ',),'Then '),((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),
                ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
                ((' therfore',' therfor'),' therefore'),(('Therfor ',),'Therefore '), (('Thei ',),'They '),((' thei ',),' they '),
            ((' thieues',' theeues',' theves',' theues'),' thieves'),((' thiefe',' theefe',' theef',' thefe'),' thief'), ((' thyne ',' thine '),' thine/your '), ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'),
                ((' thridde',' thyrde',' thirde'),' third'), ((' thristen',),' thirsting'),((' thyrst ',' thurst ',' thirste '),' thirst '),((' thirste,',),' thirst,'),
            (('thwong',),'thong'), ((' thou ',),' thou/you '), ((' thouy ',),' though '), ((' thouyte ',),' thought '), (('thousynde','thousande'),'thousand'),
            ((' thre ',),' three '), ((' trone ',),' throne '), (('thorowout',),'throughout'), (('thorow ','thorou '),'through '),(('thorow,',),'through,'), (('throwen',),'thrown'),
            (('thundringes','thundrings','thondringes','thundris'),'thunderings'),(('thundryng',),'thundering'),(('thounder','thonder'),'thunder'),
        ((' tydynges',' tidynges',' tydinges',' tydings'),' tidings/news'),(('Tydinges',),'Tidings'), ((' tyde',),' tide'),
            ((' tyed ',),' tied '), ((' tiel ',),' tile '),
            ((' tyll ',),' till '),
            ((' tyme',),' time'),
        (('togidir','togidere','togidre','togedder'),'together'),
            ((' tokene ',),' token '),
            ((' tungis',' tunges',' toges'),' tongues'),((' tonge ',),' tongue '),((' tonge,',),' tongue,'),
            ((' tokun ',' toke ',' tooke '),' took '),
            ((' townes',' tounes'),' towns'),((' towne ',' toune '),' town '),
        (('ttasfigured',),'transfigured'), ((' trauelid',),' travelled'),
            (('treasurie','tresorie'),'treasury'), ((' tre,',),' tree,'),
            (('trybe ',),'tribe '), (('tribulacioun',),'tribulation'), ((' tryed',),' tried'),
            (('Treuli','Sotheli'),'Truly'),(('truely','treuli','sotheli'),'truly'), (('sothfast',),'truthful'), ((' trewthe',' trueth',' treuthe',' verite'),' truth'),
        ((' turneden',' turnede'),' turned'),(('Turne ',),'Turn '),((' tourne ',' turne '),' turn '),
        (('twolue','twelue'),'twelve'), (('twentie ','twenti ','twentye '),'twenty '),
            ((' twyse',' twise'),' twice'), ((' twei ',' tweyne ',' tweyn ',' twey ', ' twaine '),' two '),
    (('vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'), (('vnbeleuing','vnbeleuynge'),'unbelieving'),
        (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'),
            ((' vnderstande',' vnderstand'),' understand'),(('Vnderstonde',),'Understood'),(('vnderstonde','vnderstoode','vnderstode','vndirstood'),'understood'), ((' vnder',),' under'), ((' vndon.',),' undone.'),
            (('vnfeithful',),'unfaithful'),
            (('vnleauened','vnleuened'),'unleavened'), ((' vnloose',),' unloose'),
            ((' vnsauerie',' unsauery',' unsavery'),' unsavoury'),
            ((' vntieden',),' untied'), (('Untyll ','Vntill '),'Until '),(('vntill','vntyll'),'until'), (('Vnto ',),'Unto '),((' vnto',),' unto'), ((' vntiynge',),' untying'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon ',' upo ',' apon '),' upon '),(('Vpon ',),'Upon '),
        ((' vs',),' us'),
            ((' vn',),' un'), # Special case for all remaining un- words
            ((' vp',),' up'), # Special case for all remaining up- words
    ((' valey',),' valley'), (('vanisshed','vanysshed'),'vanished'), (('vanyte ','vanitie '),'vanity '),
        (('Ueryly','Verely','Veryly'),'Verily/Truly'),((' verely',' veryly'),' verily/truly'), ((' vessell',),' vessel'),
        (('vyneyarde','vynyarde','vynyerd','vineyarde'),'vineyard'), ((' vertu',),' virtue'), ((' visite ',' vyset '),' visit '),
        ((' voyce',' vois'),' voice'), ((' voyde',' voide'),' void'),
    (('walkynge','walkinge'),'walking'),((' walkid',),' walked'),((' walke ',),' walk '),((' walke,',),' walk,'),
             ((' warres',),' wars'),((' warre ',),' war '),
             ((' waisschide',' wasshed',' wesshed'),' washed'),((' waisschun',),' washing'),((' wesshe ',' washe '),' wash '),((' wassche;',),' wash;'),
             ((' watred',),' watered'),((' watris',),' waters'),((' watir',' watre'),' water'),
                ((' wayes',' weies'),' ways'),((' waye ',' weie ',' weye '),' way '),((' waye,',' weie,',' weye,'),' way,'),((' waye.',' weie.',' weye.'),' way.'),((' waye:',' weie:',' weye:'),' way:'),
        ((' wee ',),' we '),
            ((' weryed',' weried'),' wearied'),((' weery',' wery'),' weary'),
            ((' wepe ',),' weep '),
            ((' welde ',),' weld '), ((' wel ',),' well '),
            ((' wenten ',' wente ',' wete ',' yeden ',' yede '),' went '),
            ((' wepte',),' wept'),
            ((' weren ',),' were '), (('westwarde',),'westward'),
        (('Whatsoeuer',),'Whatsoever'),(('whatsoeuer',),'whatsoever'),
            (('Whanne ',),'When '),((' whanne ',' whan '),' when '), ((' whethir',),' whether'),
            (('Whiche ',),'Which '),((' whiche ',),' which '), ((' whill ',' whyll ',' whyle '),' while '), (('whyte ','whijt '),'white '),
            ((' whoale',),' whole'), ((' whome',),' whom'), (('Whosoeuer',),'Whosoever'),(('whosoeuer',),'whosoever'),
            ((' whi ',),' why '),
        (('wickednesse',),'wickedness'), ((' wickid',),' wicked'),
            ((' wyde ',),' wide '), (('widewis','wyddowes','widowes'),'widows'),(('widewe ','wyddowe ','widdowe ','widowe '),'widow '), (('wyldernesse','wildirnesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf'),' wife'),
            ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),((' wylt ',' wilt '),' wilt/will '),
            ((' winne ',' wynne '),' win '), ((' wyndis',' wyndes',' windes'),' winds'),((' wynde ',' wynd ',' winde '),' wind '), ((' wengis',' wynges'),' wings'), (('Wynter',),'Winter'),((' wyntir.',' wynter.'),' winter.'),
            ((' wipte',' wyped'),' wiped'),
            (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'), ((' wyse ',),' wise '),
            ((' withynne',),' within'),((' wi ',' wt '),' with '), (('widdred','wythred','wythered','wyddred'),'withered'),
                (('withouten ',),'without '), (('witnessyng',),'witnessing'),((' wytnesse ',' witnesse ',' witnes '),' witness '),
            ((' wyues',' wiues'),' wives'),
        (('Woo ','Wo '),'Woe '),((' wo ',),' woe '),
            ((' womman',),' woman'), ((' wombe',),' womb'), ((' wymmen',' wemen'),' women'),
            (('wondriden','wondride'),'wondered'),
            ((' wordis',),' words'),((' worde',),' word'), ((' workes',' werkis'),' works'),((' worche ',' worke ',' werke ',' werk '),' work '),((' worke,',' werk,'),' work,'),((' worche.',),' work.'), ((' worlde',),' world'), ((' worme ',),' worm '), (('worschipide','worshypped'),'worshipped'), ((' worthie',' worthi'),' worthy'),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),
        ((' writyng',),' writing'),((' wryte ',),' write '), (('wrytten','wrytte','writun'),'written'), ((' wroote ',' wroot '),' wrote '), (('wrought','wrouyt'),'wrought/done'),
    (('Iaakob','Iacob'),'Yacob'), (('Iames','James'),'Yames/Yacob'), (('Iauan',),'Yavan'),
        (('Ye ',),'Ye/You_all '),((' ye ',' yee '),' ye/you_all '), ((' thi ',' thy '),' thy/your '), ((' youre ',),' your(pl) '),
            ((' yhe,',),' yea/yes,'), ((' yeres',),' years'),((' yeare',' yeere',' yeer',' yere'),' year'),
            (('Hierusalem','Ierusalem','Ierusale','Jerusalem'),'Yerusalem'),
            (('Iesus',),'Yesus/Yeshua'),(('Iesu ',),'Yesu '),(('Iesu.',),'Yesu.'),
            ((' yit ',),' yet '),
            (('Iewry ',),'Yewry '), (('Iewes ','Jewis '),'Yews '),
        (('Ioanna','Joone'),'Yoanna'), (('Iohn','Ihon','Joon'),'Yohn'),
            (('Iordane ','Iordan ','Iorden ','Iorda ','Jordan '),'Yordan '),(('Iordane,','Iordan,','Iorden,','Iorda,','Jordan,'),'Yordan,'),
            (('Ioseph',),'Yoseph'), (('Ioses','Joses'),'Yoses'),
        (('Iudas','Ivdas','Judas'),'Yudas'), (('Iuda','Juda'),'Yudah'), (('Iudea','Judee'',Judaea'),'Yudea'), (('Iude',),'Yude'), (('Iury','Iurie'),'Yury/Yudea'), (('Iewry',),'Yewry'),
    (('Zebedeus ','zebede ','Zebede '),'Zebedee '), (('Zebedeus,','zebede,','Zebede,'),'Zebedee,'),

    # Roman numerals
    (('.iii.',),'3'), (('.vii.',),'7'), (('xii.',),'12'), ((' xl ',),' 40 '),

    # Symbols
    ((' & ',),' and '),
    )
oldWords, newWords = [], []
for wordMapEntry in ENGLISH_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    someOldWords,newWord = wordMapEntry
    assert isinstance( someOldWords, tuple ), f"{someOldWords=}"
    assert isinstance( newWord, str )
    for j,someOldWord in enumerate( someOldWords ):
        assert isinstance( someOldWord, str ) and len(someOldWord)>=2, f"{someOldWord=}"
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if j > 0: assert someOldWord not in newWord, f"Recursive substitution of '{someOldWord}' into '{newWord}'"
        assert '  ' not in someOldWord
        oldWords.append( someOldWord)
    if newWord not in ('themselves',): # sometimes two->one and sometimes it's a single word
        assert newWord not in newWords, f"{newWord=}"
    if someOldWords[0].startswith(' '): assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    if newWord[-1] in ' ,.:;':
        for someOldWord in someOldWords:
            assert someOldWord[-1] == newWord[-1], f"Mismatched trailing character: {someOldWords} {newWord=}"
    assert '  ' not in newWord
    newWords.append( newWord )
del oldWords, newWords

def moderniseEnglishWords( html:str ) -> bool:
    """
    Convert ancient spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"moderniseEnglishWords( ({len(html)}) )" )

    for oldWords,newWord in ENGLISH_WORD_MAP:
        for oldWord in oldWords:
            html = html.replace( oldWord, newWord )

    return html
# end of createParallelVersePages.moderniseEnglishWords


GERMAN_WORD_MAP = (
    ('Aber','But'),(' aber',' but'),
        (' Arche ',' ark '),
        (' alle ',' all '),(' alle,',' all,'),(' allen ',' all '),  ('Also ','So '), (' alten ',' old '),
        ('Am ','At_the '),(' am ',' in/at/on_the '),
        (' an ',' at '), ('Anfang','beginning'),
        (' auch ',' also '),(' auch.',' also.'), (' aus ',' out of '), (' auf ',' on '),(' aufs ',' onto '),
    ('Älteste','elder'),
        (' andere ',' other '),
        ('ärgerte','annoyed'),('ärgert','annoys'),
    ('Befehl','command'), (' begab ',' gifted '), (' bekleidet',' clothed'),
        ('Blut','blood'),
        (' bösen ',' evil '),
        (' brachte',' brought'), ('Brot ','bread '), ('Brüder','brothers'),('Bruder','brother'),
    ('Christus','Christ'),
    ('Da ','So '),(' da ',' there '),
            (' danach ',' after/thereafter/then '),
            ('Darum','Therefore'),
            (' das ',' the '),
            (' daß ',' that '),
            (' dazu ',' in_addition '),
        (' den ',' the '), ('Denen','Those'), ('Denn ','Because '), ('Der ','The '),(' der ',' the '),(' dem ',' the '),(' des ',' the '),
        (' die ',' the '),
        ('Dies ','This/These '), ('Diese ','This/These '),
        ('Drache','dragon'), (' draußen',' outside'),
            (' drei',' three'),
        ('Du ','You '), (' durch ',' through '),
    ('Engel','angel'),
        ('Erde','earth'), (' erste ',' first '),
        (' ein ',' a '),(' eine ',' one '),(' einen ',' a '), ('eingeborenen','native_born'),
        (' er ',' he '),
        ('Es ','It '),(' es ',' it '), (' essen',' eat'),
        (' etliche ',' several '),
        (' euch',' you'),(' eure ',' your '),
        ('Evangeliums','gospel'),
        (' ewige ',' eternal '),
    ('Feuer','fire'),
        ('Finsternis','darkness'),(' finster ',' dark '),
        ('Fleisch','flesh'),
        ('Füßen ','feet '),
    (' gab,',' gave,'), ('Gajus','Gaius'),
        (' geben ',' give '),
            ('Geist','spirit'),
            ('geliebet','loved'),
            (' gemacht',' made'), ('Gemeinden','communities'),
            (' gesandt',' sent'), ('geschrieben','written'), ('Gesetz','law'), (' gesund ',' healed '),
            (' gewesen ',' been '),
        ('Glauben','faith'), ('glauben','believe'),
        ('Gottes','God’s'),('GOtt','God'),
        ('Grabe ','grave '), (' groß ',' large '), (' große ',' large '),(' großen',' large'),(' großes',' large'),
        (' gut ',' good '),
    ('Habe ','goods '), (' habe ',' have '),(' habe;',' have;'), ('haben','have'), (' habt',' have'),
            (' halten ',' hold '),
            (' hat ',' has '),(' hat,',' has,'), (' hatte ',' had '),
            ('Hauses','houses'),
        (' hebräisch ',' hebrew '),
            (' heilig',' holy'), (' heißt',' is_called'),
            ('heller ','brighter '),
            (' hervor',' out'),
        ('Himmel','heaven'),
        (' höre',' listen'),
    ('Ich ','I '),(' ich ',' I '),
        (' ihm ',' him '),(' ihm.',' him.'), (' ihn ',' him/it '),(' ihn,',' him/it,'), (' ihr ',' her '),
        (' im ',' in_the '),
        (' ist ',' is '),(' ist,',' is,'),(' ist.',' is.'),
    ('JEsus','Yesus'), ('J','Y'),
        ('Jüngern','disciples'),
    (' kamen ',' came '),(' kam ',' came '),
        ('Kinder ','children '),
        ('Kleider ','clothes '),
        (' kommen ',' coming '),
        ('Königs','kings'),('König','king'),
        ('Krone ','crown '),
    ('Lauterkeit','purity/integrity'),
        ('Lebens','life'),('Leben ','life '), ('leer,','empty,'), ('Leib ','body '),
        ('Licht','light'),
            ('Lieben ','loved (one) '), (' liebhabe ',' love '), (' Liebe ',' love '), (' ließ ',' let '),(' ließen ',' leave/let '),
            ('Lippen ','lips '),
    (' machten',' make'), ('Mann ','man '),('Mann.','man.'), ('Märkte ','marketplaces '),
        (' mecum ',' with_me '),
            ('Meer ','sea '),('Meer.','sea.'),
            ('Meine ','My '),(' meinem ',' my '),(' meinen ',' my '), (' mit ',' with '),
        ('Mond ','moon '), ('. Morgan','. Morning'),('Morgan','morning'),
        (' mögest',' may'),
    (' nachdem ',' after '), ('Nacht ','night '), ('Naemi ','Naomi '), (' nahmen ',' took '), (' nämlich ',' namely '),
        (' nicht ',' not '),(' nicht,',' not,'), (' nimmermehr',' nevermore'),
        (' noch ',' still '),
        (' nun ',' now '),
    (' ohne ',' without '), ('Ohren ','ears '),
        ('Ort,','location,'),
    ('Pferd','horse'),
        (' predigte ',' preached '),
    ('Reich ','kingdom '), (' reisete ',' travelled '),
        (' roter ',' red '),
    (' sagt',' says'), (' sah,',' saw,'), ('Samen ','seed/seeds '),('Samen.','seed/seeds.'), (' saß ',' sat '),
        ('Schande ','shame '), (' schied ',' separated '), ('Schiff','ship'), ('Schlüssel ','key '),
        (' sei ',' be '), (' sein ',' his '),(' seine ',' his '),(' seinen ',' his '), (' seit ',' since '),
            (' selbst ',' himself/itself '),
            (' sende ',' send '),
        (' sich ',' itself/yourself/themselves '),(' sie ',' she/they/them '), (' sieben ',' seven '), (' sind ',' are '),
        ('Sohn','son'),
            ('sondern','rather'), ('Sonne','sun'), ('Sonst ','Otherwise '),
        ('Speise ','food '), (' spiritern ',' spirits '), (' sprach ',' spoke '),(' sprach:',' spoke:'),
        ('Städte ','cities '), ('Stamms ','tribe '), (' starb ',' died '), (' stehet',' stands'), (' stund ',' stood '),
        (' schwebete ',' floated '), (' schuf ',' created '),
    ('Tiefe ','depth '), (' timor ',' fear '),
        (' trug ',' wore '),
    ('Und ','And '),(' und ',' and '),
        ('ungläubige','unbelieving'), ('Ungewitter','storm'),
        (' unrein',' unclean'),
        (' unter ',' under '),
    ('Vaterland','fatherland/homeland'), ('Vater ','father '),
        ('verkündigte','announced'), ('verlässest','leave'), ('verloren','lost'), ('versammelt','gathered'),
        (' viel ',' many '), ('Volk','people'), (' vom ',' from_the '), (' von ',' from '), (' vor ',' before/in_front_of '),
    ('Wahrheit','truth'),
            (' war ',' was '),(' war.',' was.'), (' ward ',' was '), (' wären ',' would_be '), # Is 'ward' a mispelling?
            ('Wasser','water'),
        ('Weiber','women'),('Weib ','woman '),('Weib,','woman,'), ('Wein ','wine '),
            ('Welche ','Which '),('welcher ','which '),(' welches ',' which '),(' welchem ',' which_one '), ('Welt','world'),
            (' wenn ',' when '),
            ('Wer ','Who '), (' werden',' become'),(' werde',' become'),
            (' weinete ',' cried '), (' weiße ',' white '),
        (' wieder',' again'), ('Wind ','wind '),
            (' wird ',' becomes '),
            ('Wisset ','Know '),(' wisset ',' know '),
        (' wollte',' wanted'),
            ('Worten','words'),
        (' wurden ',' became '), ('Wurzel ','root '), (' wüst ',' wild '),
    ('Yahre','years'),
    ('zähme ','tame '),
        (' zehn ',' ten '), ('Zeichen ','sign '), (' zeugen',' witness'),
        (' zogen ',' pulled '),
        (' zu ',' to '), ('Zuletzt ','Finally '), (' zum ',' for_the '), (' zusammen ',' together '),
    )
GermanWords, EnglishWords = [], []
for wordMapEntry in GERMAN_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    GermanWord,EnglishWord = wordMapEntry
    assert isinstance( GermanWord, str ) and (len(GermanWord)>=2 or GermanWord in ('J',)), f"{GermanWord=}"
    assert GermanWord not in GermanWords, f"duplicate GermanWord: {GermanWord=} ({EnglishWord=})"
    if GermanWord.startswith(' ') or EnglishWord.startswith(' '): assert GermanWord.startswith(' '), f"Mismatched leading space: {GermanWord=} {EnglishWord=}"
    if GermanWord.endswith(' ') or EnglishWord.endswith(' '): assert GermanWord.endswith(' '), f"Mismatched trailing space: {GermanWord=} {EnglishWord=}"
    if j > 0: assert GermanWord not in EnglishWord, f"Recursive substitution of '{GermanWord}' into '{EnglishWord}'"
    assert '  ' not in GermanWord
    GermanWords.append( GermanWord)
    if GermanWord.startswith(' '): assert EnglishWord.startswith(' '), f"Mismatched leading space:  {GermanWord=} {EnglishWord=}"
    if GermanWord.endswith(' '): assert EnglishWord.endswith(' '), f"Mismatched trailing space: {GermanWord=} {EnglishWord=}"
    if EnglishWord[-1] in ' ,.:;':
        assert GermanWord[-1] == EnglishWord[-1], f"Mismatched trailing character: {GermanWord=} {EnglishWord=}"
    assert '  ' not in EnglishWord
    EnglishWords.append( EnglishWord )
del GermanWords, EnglishWords

def translateGerman( html:str ) -> bool:
    """
    Convert ancient spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"translateGerman( ({len(html)}) )" )

    if html.startswith( 'und '): # Handle common exception that can't be expressed in the word table
        html = f'and {html[4:]}'
    html = html.replace( '»', '‘' ).replace( '«', '’' )
    for GermanWord,EnglishWord in GERMAN_WORD_MAP:
        html = html.replace( GermanWord, EnglishWord )

    return html
# end of createParallelVersePages.translateGerman


LATIN_WORD_MAP = (
    (' ab ',' away '), (' abierunt',' they_are_gone'), (' arbores ',' trees '),
        (' æternam',' eternal'), (' æternum',' eternal'),
        (' aliæ ',' in_another '),
        ('ancillam','maidservant'),
        (' angelum',' a_messenger/angel'), (' annos ',' years '),
        (' appellavit ',' he_called '),
        (' aqua',' water'),
        (' autem ',' however '),
        (' bis ',' twice '),
    (' bona',' good'),
    ('cælum','the_sky'),
        ('circumferentur','are_carried_around'),
        ('congregabit','will_gather'), ('contradictione','contradiction'),
        ('creavit ','created '), ('credit','he_believes'),
    ('dæmonia','demons'), (' daret',' would_give'),
        (' de ',' about '), (' decem ',' ten '), (' dedit',' he_gave'), ('Deus','God'),
        ('dilexit','he_loved'), ('divisit','divided'), ('Dixitque','And_he_said'),
        ('Dominus ','Master '),
    (' eam ',' her '),
        ('Ecce ','Behold '), ('ecclesiis','assemblies/churches'),
        (' effusi ',' poured_out '),
        ('Ego ','I '),(' ego ',' I '),
        (' ei ',' to_him '),
        (' enim',' because'),
        (' epulis ',' food '),
        (' eradicatæ',' eradicated'), (' erant ',' they_were '), (' errore ',' by_mistake '),
        (' es ',' you_are '), (' esset ',' was '), (' est ',' it_is '),(' est,',' it_is,'),
        ('Et ','And '),(' et ',' and '),
        (' eum,',' him,'),
    ('facultatibus','resources'), (' facta ',' facts '),
        (' feri ',' wild '),
        ('Fiat ','Let_it_happen '), ('Filium','Son'),
        ('fluctus ','wave '),
    (' habeat ',' have '), ('habitare','to_live'),
        (' hæc ',' this '),
        ('hebraice','hebrew'),
        ('Hi ','They '),
    (' illis,',' to_them,'),
        (' inter ',' between '),
        (' illos ',' those '),(' illum ',' him '),
    (' legum ',' the_law '),
        (' locum ',' place '),
        (' lucem ',' the_light '), (' lux',' light'),
    (' maculæ',' spots'), (' magnus',' big'),
        (' mercede ',' reward '), (' meum ',' mine '),
        ('millibus','thousands'), ('ministrabant','served'), (' misi ',' I_sent '),
        (' mortuæ',' dead'),
        (' multæ ',' many '), (' mundum',' the_world'),
    (' non ',' not/no '), (' novam',' new'),(' novum ',' new '),
        (' nubes ',' clouds '),
    (' omnis ',' everyone '),
    (' pereat ',' perish '), (' perierunt ',' they_perished '),
        (' post ',' after '),
        ('principio ','at_the_beginning '), ('procella ','storm '), ('Propterea ',"That's_why "),
        (' puteum ',' a_well '),
    (' qua ',' which '),(' quæ ',' which '), (' qualis ',' such_as '), (' quam ',' how '),
        ('qui ','who '), ('quia ','because '), ('quibus ','to_whom '),
        ('quod ','that '),
    (' radix ',' root '),
    (' secundum ',' after/second '), (' sed ',' but '), (' semen ',' seed '), (' septem ',' seven '), (' septimus ',' the_seventh '), (' servata ',' saved '),
        ('Sic ','So '), (' sic ',' so '), (' sidera ',' stars '), (' sine ',' without '),
        (' stella ',' star '),
        (' suam ',' his_own '),(' suas ',' their_own '),(' suis',' to_his_own'),(' sum ',' I_am '), (' sunt ',' are '),(' sunt,',' are,'), (' suo ',' his_own '), (' suum ',' his_own '),
    (' te,',' you(sg),'),(' te.',' you(sg).'), (' tenebris',' darkness'), (' terra ',' earth/land '),(' terram',' the_earth/land'),
        (' tui ',' yours '), ('tulit ','took '), (' tuum ',' your '),
    ('unigenitum','only_born'),
    (' ut ',' as '),
        (' uxorem',' wife'),(' uxor ',' wife '),
    ('Væ ','Alas '),
        (' venit ',' he_came '), (' ventis ',' the_winds '), ('veritatem','words'),
        (' via ',' road '), (' vidi ',' I_saw '),(' vidit ',' he_saw '), (' viro ',' to_the_man '), (' vitæ ',' of_life '), (' vitam ',' life '),
        (' vobis ',' to_you '), ('vocatur ','is_called '), (' voces',' voices'),
    )
LatinWords, EnglishWords = [], []
for wordMapEntry in LATIN_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    LatinWord,EnglishWord = wordMapEntry
    assert isinstance( LatinWord, str ) and len(LatinWord)>=2, f"{LatinWord=}"
    assert LatinWord not in LatinWords, f"duplicate LatinWord: {LatinWord=} ({EnglishWord=})"
    if LatinWord.startswith(' ') or EnglishWord.startswith(' '): assert LatinWord.startswith(' '), f"Mismatched leading space: {LatinWord=} {EnglishWord=}"
    if LatinWord.endswith(' ') or EnglishWord.endswith(' '): assert LatinWord.endswith(' '), f"Mismatched trailing space: {LatinWord=} {EnglishWord=}"
    if j > 0: assert LatinWord not in EnglishWord, f"Recursive substitution of '{LatinWord}' into '{EnglishWord}'"
    assert '  ' not in LatinWord
    LatinWords.append( LatinWord)
    if LatinWord.startswith(' '): assert EnglishWord.startswith(' '), f"Mismatched leading space:  {LatinWord=} {EnglishWord=}"
    if LatinWord.endswith(' '): assert EnglishWord.endswith(' '), f"Mismatched trailing space: {LatinWord=} {EnglishWord=}"
    if EnglishWord[-1] in ' ,.:;':
        assert LatinWord[-1] == EnglishWord[-1], f"Mismatched trailing character: {LatinWord=} {EnglishWord=}"
    assert '  ' not in EnglishWord
    EnglishWords.append( EnglishWord )
del LatinWords, EnglishWords

def adjustLatin( html:str ) -> bool:
    """
    Convert ancient Latin spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"adjustLatin( ({len(html)}) )" )

    if html.startswith( 'et '): # Handle common exception that can't be expressed in the word table
        html = f'and {html[3:]}'
    for LatinWord,EnglishWord in LATIN_WORD_MAP:
        html = html.replace( LatinWord, EnglishWord )

    return html.replace('j','y').replace('J','Y') \
                .replace('Yhes','Jhes') # Change these ones back again -- 'Jhesus' -- was maybe more like French J ???
# end of createParallelVersePages.adjustLatin



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createParallelVersePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createParallelVersePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createParallelVersePages.py
