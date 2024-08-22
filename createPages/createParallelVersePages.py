#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createParallelVersePages.py
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

createParallelVersePages( level:int, folder:Path, state:State ) -> bool
createParallelVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state:State ) -> bool
getPlainText( givenVerseEntryList ) -> str
    Takes a verseEntryList and converts it to a string of plain text words.
    Used to compare critical Greek versions.
removeGreekPunctuation( greekText:str ) -> str
    Converts to lowercase and removes punctuation used in any Greek version.
    Used to compare critical Greek versions.
brightenSRGNT( BBB:str, C:str, V:str, brightenTextHtml:str, verseEntryList, state:State ) -> Tuple[str,List[str]]
    Take the SR-GNT text (which includes punctuation and might also include <br> characters)
        and mark the role participants
brightenUHB( BBB:str, C:str, V:str, brightenUHBTextHtml:str, verseEntryList, state:State ) -> Tuple[str,List[str]]
    Take the UHB text (which includes punctuation and might also include <br> characters)
        and mark the role participants
moderniseEnglishWords( html:str ) -> bool
    Convert ancient spellings to modern ones.
translateGerman( html:str ) -> bool
    Convert ancient spellings to modern ones.
translateLatin( html:str ) -> bool
    Convert ancient Latin spellings to modern ones.
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


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
    2024-04-30 In TEST_MODE, only make parallel verse pages for the actual TEST_BOOK_LIST
    2024-06-05 Allow footnotes (but not cross-references) on these pages
                which includes moving transliteration spans to be placed BEFORE any footnotes
    2024-06-25 Started work on adding maps from BibleMapper.com
"""
from gettext import gettext as _
from typing import Tuple, List
from pathlib import Path
import os
import logging
import re

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.OriginalLanguages.Greek as Greek

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State, TEST_MODE, TEST_BOOK_LIST, reorderBooksForOETVersions, OETS_UNFINISHED_WARNING_HTML_TEXT
from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTyndaleBookIntro, formatUnfoldingWordTranslationNotes, formatTyndaleNotes, getBibleMapperMaps, getVerseDetailsHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    convert_adds_to_italics, removeDuplicateFNids, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP, OSHB_ADJECTIVE_DICT, OSHB_PARTICLE_DICT, OSHB_NOUN_DICT, OSHB_PREPOSITION_DICT, OSHB_PRONOUN_DICT, OSHB_SUFFIX_DICT
from OETHandlers import getOETTidyBBB, getOETBookName, livenOETWordLinks, getHebrewWordpageFilename, getGreekWordpageFilename


LAST_MODIFIED_DATE = '2024-08-16' # by RJH
SHORT_PROGRAM_NAME = "createParallelVersePages"
PROGRAM_NAME = "OpenBibleData createParallelVersePages functions"
PROGRAM_VERSION = '0.96'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EN_SPACE = ' '
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
NON_BREAK_SPACE = ' ' # NBSP
WJ = '\u2060' # word joiner (makes Hebrew displays on console ugly and hard to read)


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
            ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
            BBBNextLinks.append( f'''<a title="{getOETBookName(BBB)}" href="../{BBB}/">{ourTidyBBBwithNotes}</a>''' )

    # Now create the actual parallel pages
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if not TEST_MODE or BBB in TEST_BOOK_LIST: # Don't need parallel pages for non-test books
            if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
                createParallelVersePagesForBook( level, folder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallelVerse', None, state ) \
            .replace( '__TITLE__', f"Parallel Verse View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, view, display, index' )
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
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
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
    cLinksPar = f'''<p class="chLst">{ourTidyBBBwithNotes} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
        if BBB=='PSA' else \
            f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>'''

    vLinksList = []
    detailsLink = f''' <a title="Show details about these works" href="{'../'*(BBBLevel)}AllDetails.htm#Top">©</a>'''
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
                    else f' <a title="Next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters \
                    else ''
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.error( f"createParallelVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            oetRvPsaHasD = False
            # There's an EM_SPACE and an EN_SPACE (for the join) in the following line
            for v in range( 0, numVerses+1 ):
                V = str( v )
                parRef = f'{BBB}_{C}:{V}'
                vLinksPar = f'''<p class="vsLst">{ourTidyBbb} {C} {' '.join( [f'<a title="Go to parallel verse page" href="C{C}V{vv}.htm#Top">V{vv}</a>'
                                for vv in range(1,numVerses+1,5 if numVerses>100 else 4 if numVerses>80 else 3 if numVerses>60 else 2 if numVerses>40 else 1) if vv!=v] )}</p>'''
                doneHideablesDiv = False
                greekWords = {}; greekVersionKeysHtmlSet = set()

                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Previous verse" href="C{C}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Previous chapter (last verse)" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                # NOTE below: C1V0 may not exist in the version but usually there's uW TNs for 1:0
                rightVLink = f' <a title="Next page is first chapter intro" href="C1V0.htm#__ID__">→</a>' if c==-1 \
                        else f' <a title="Next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses \
                        else ''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introductions <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}{hideFieldsButton}{hideTransliterationsButton}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{introLink}{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}{hideFieldsButton}{hideTransliterationsButton}</p>'
                parallelHtml = getVerseDetailsHtml( BBB, C, V )
                for versionAbbreviation in parallelVersions: # our adjusted order
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    createParallelVersePagesForBook {parRef} processing {versionAbbreviation}…" )
                    assert not parallelHtml.endswith( '\n' )

                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have both OET-RV and OET-LV instead
                    if versionAbbreviation in ('UHB','JPS') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB):
                        continue # Skip non-OT books for Hebrew
                    if versionAbbreviation in ('BRN','BrLXX') \
                    and BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip NT books for Brenton (it has deuterocanon/apocrypha)
                    if versionAbbreviation in ('BLB','AICNT','TCNT','TNT', 'SR-GNT','UGNT','SBL-GNT','TC-GNT') \
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
                    footnotesHtml = translatedFootnotesHtml = ''
                    if versionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
                        try:
                            prefix = ''
                            verseText = thisBible[(BBB,C,V)]
                            if verseText.startswith( '(' ) and verseText[1].isdigit(): # then it's probably a verse range, e.g., (21-23), esp. in MSG
                                prefix, verseText = verseText.split( ' ', 1 )
                                assert prefix[-1] == ')'
                                prefix = f'<b><sup>{prefix}</sup></b>'
                            if verseText.startswith( '\\s1 ' ):
                                verseText.replace( '\\s1 ', '\\s1 <b>', 1 ).replace( '\n', '</b>\n', 1 )
                            vHtml = f'{prefix}{verseText}' \
                                .replace( '\\p ', '\n&nbsp;&nbsp;' ) \
                                .replace( '\\q1 ', '\n&nbsp;&nbsp;' ) \
                                .replace( '\\m ', '\n' ) \
                                .replace( '\\pc ', '\n&nbsp;&nbsp;&nbsp;&nbsp;' ) \
                                .replace( '\\li1 ', '\n•&nbsp;' ) \
                                .replace( '\\li2 ', '\n&nbsp;◦&nbsp;' ) \
                                .replace( '\\li3 ', '\n&nbsp;&nbsp;•&nbsp;' ) \
                                .replace( '\\s1 ', '\n' ) \
                                .replace( '\\s2 ', '\n' ) \
                                .replace( '\\s3 ', '\n' ) \
                                .replace( '\n\n', '\n' )
                            # if versionAbbreviation=='CSB' and BBB=='RUT' and 'ORD' in verseText: print( f"{versionAbbreviation} {parRef} {verseText=}" )
                            vHtml = vHtml.strip() \
                                .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
                                .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
                                .replace( '\\add ', '<span class="add">' ).replace( '\\add*', '</span>' ) \
                                .replace( '\\nd LORD\\nd*', '\\nd L<span class="ndORD">ORD</span>\\nd*' ) \
                                .replace( '\\nd LORDE\\nd*', '\\nd L<span class="ndORD">ORDE</span>\\nd*' ) \
                                    .replace( '\\nd ', '<span class="nd">' ).replace( '\\nd*', '</span>' ) \
                                .replace( '\\wj ', '<span class="wj">' ).replace( '\\wj*', '</span>' ) \
                                .replace( '\n', '<br>' )
                            # if versionAbbreviation=='CSB' and BBB=='RUT' and C=='2' and 'ORD' in verseText: print( f"{versionAbbreviation} {parRef} {vHtml=}" ); halt
                            assert '\\' not in vHtml, f"{versionAbbreviation} {parRef} {vHtml=}"
                            assert '<br><br>' not in vHtml, f"{versionAbbreviation} {parRef} {vHtml=}"
                            vHtml =  f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="Go to {state.BibleNames[versionAbbreviation]} copyright info" href="{'../'*BBBLevel}AllDetails.htm#{versionAbbreviation}">{versionAbbreviation}</a></span> {vHtml}</p>'''
                        except KeyError:
                            vHtml = None # We display nothing at all for these versions that only have a few selected verses
                    else: # should be a Bible object
                        try:
                            if BBB not in thisBible: raise MissingBookError # Requested book is not in this Bible
                            # NOTE: For the book intro, we fetch the whole lot in one go (not line by line)
                            if versionAbbreviation == 'OET-LV' and oetRvPsaHasD and c >= 1:
                                # For these Psalms, the OET-LV calls the \\d field, verse 1, so everything is one verse out
                                verseEntryList, contextList = thisBible.getContextVerseDataRange( (BBB, C, V), (BBB, C, '2') ) if v==1 else thisBible.getContextVerseData( (BBB, C, str(v+1)) )
                            else: # the normal, common case
                                verseEntryList, contextList = thisBible.getContextVerseData( (BBB, C) if c==-1 else (BBB, C, V) )
                            if 'GNT' in versionAbbreviation:
                                plainGreekText = getPlainText( verseEntryList )
                                if versionAbbreviation == 'SBL-GNT':
                                    plainGreekText = plainGreekText.replace('1','').replace('2','') # 1 Cor 12:10
                                greekWords[versionAbbreviation] = plainGreekText
                                greekWords[f'{versionAbbreviation}_NoPunct'] = removeGreekPunctuation(  greekWords[versionAbbreviation] )
                                greekClass = Greek.Greek( greekWords[f'{versionAbbreviation}_NoPunct'] )
                                try:
                                    greekWords[f'{versionAbbreviation}_NoAccents'] = greekClass.removeAccents()
                                except Exception as exc:
                                    # print( f"\n{parRef} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}" )
                                    raise exc
                                # print( f"\n{parRef} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}\n{greekWords[f'{versionAbbreviation}_NoAccents']=}" )
                            if 'OET' in versionAbbreviation:
                                assert isinstance( thisBible, ESFMBible.ESFMBible )
                                if versionAbbreviation == 'OET-RV' and BBB=='PSA' and C not in ('98',):
                                    # Psa 98 does have a d, but it's in with v1 and the other verses don't change
                                    for entry in verseEntryList:
                                        if entry.getMarker() == 'd':
                                            oetRvPsaHasD = True
                                            break
                                    # We want to save
                                verseEntryList = livenOETWordLinks( BBBLevel, thisBible, BBB, verseEntryList, state )
                            else: assert not isinstance( thisBible, ESFMBible.ESFMBible )
                            textHtml = convertUSFMMarkerListToHtml( BBBLevel, versionAbbreviation, (BBB,C,V), 'verse', contextList, verseEntryList, basicOnly=(c!=-1), state=state )
                            textHtml, footnoteFreeTextHtml, footnotesHtml = handleAndExtractFootnotes( versionAbbreviation, textHtml )
                            if textHtml.endswith( ' </span>' ): textHtml = f'{textHtml[:-8]}</span>' # Remove superfluous final space
                            if footnoteFreeTextHtml.endswith( ' </span>' ): footnoteFreeTextHtml = f'{footnoteFreeTextHtml[:-8]}</span>' # Remove superfluous final space
                            if 'OET' in versionAbbreviation:
                                textHtml = textHtml.replace( '~~SCHWA~~', 'ə' ) # Restore protected field in title popups
                            if versionAbbreviation not in ('TCNT','TC-GNT'): # They use this character in footnotes
                                assert '¦' not in textHtml, f"{parRef} {versionAbbreviation} {textHtml=}"
                            assert not textHtml.endswith( '\n' )
                            if textHtml == '◙':
                                NEVER_GETS_HERE
                                raise UntranslatedVerseError

                            if versionAbbreviation == 'KJB-1611':
                                textHtml = textHtml.replace( 'class="add"', 'class="add_KJB-1611"' )
                            elif 'OET' not in versionAbbreviation:
                                # Hardwire added words in non-OET versions to italics
                                textHtml = convert_adds_to_italics( textHtml, f'OET parallel verse {parRef}' )

                            if versionAbbreviation == 'OET-RV':
                                # if BBB=='MRK' and C=='7' and V=='16': print( f"AAA {parRef} {versionAbbreviation} {textHtml=}" )
                                textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                                # if BBB=='MRK' and C=='7' and V=='16': print( f"BBB {parRef} {versionAbbreviation} {textHtml=}" )
                            elif versionAbbreviation == 'OET-LV':
                                # if BBB=='MRK' and C=='7' and V=='16': print( f"CCC {parRef} {versionAbbreviation} {textHtml=}" )
                                # assert '<span class="ul">_</span>HNcbsa' not in textHtml, f'''Here1 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                                textHtml, footnoteFreeTextHtml, footnotesHtml = do_OET_LV_HTMLcustomisations(textHtml), do_OET_LV_HTMLcustomisations(footnoteFreeTextHtml), do_OET_LV_HTMLcustomisations(footnotesHtml)
                                # assert textHtml.count('<span class="ul">_</span>HNcbsa') < 2, f'''Here2 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                                # if BBB=='MRK' and C=='7' and V=='16': print( f"DDD {parRef} {versionAbbreviation} {textHtml=}" )
                            elif versionAbbreviation == 'WEB': # assuming WEB comes BEFORE WMB
                                textHtmlWEB = textHtml # Save it
                            elif versionAbbreviation == 'WMB': # assuming WEB comes BEFORE WMB
                                if textHtml == textHtmlWEB.replace( 'WEB', 'WMB' ):
                                    # print( f"Skipping parallel for WMB {parRef} because same as WEB" )
                                    textHtml = "(Same as above)" # Do we also need to adjust footnotesHtml ???
                                # else:
                                #     print( f"Using parallel for WMB {parRef} because different from WEB:" )
                                #     print( f"  {textHtmlWEB=}" )
                                #     print( f"     {textHtml=}" )
                            elif versionAbbreviation == 'LSV':
                                textHtml = do_LSV_HTMLcustomisations( textHtml )
                            elif versionAbbreviation == 'T4T':
                                textHtml = do_T4T_HTMLcustomisations( textHtml )
                            elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1769','KJB-1611'):
                                # See if we need to add a modernised version of this text underneath the main/original text ???
                                # print( f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}")
                                # rawTextHtml = footnoteFreeTextHtml
                                # if rawTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ):
                                #     assert rawTextHtml.endswith( '</span>' )
                                #     rawTextHtml = rawTextHtml[30+len(versionAbbreviation):-7]
                                # print( f"{versionAbbreviation} {parRef} {rawTextHtml=}")
                                # if V=='4': halt
                                modernisedTextHtml = moderniseEnglishWords( footnoteFreeTextHtml )
                                if versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1611'): # all from 1500's
                                    modernisedTextHtml = modernisedTextHtml.replace( 'J', 'Y' ).replace( 'Ie', 'Ye' ).replace( 'Io', 'Yo' ) \
                                                                                .replace( 'Yudge', 'Judge' ).replace( 'KYB', 'KJB' ) # Fix overreaches
                                if versionAbbreviation == 'KJB-1769':
                                    # if parRef=='JDG_6:23': print( f"{versionAbbreviation} {parRef} {modernisedTextHtml=}" )
                                    cleanedModernisedKJV1769TextHtml = modernisedTextHtml.replace( versionAbbreviation, '' )
                                    # if parRef=='JDG_6:23': print( f"{versionAbbreviation} {parRef} {cleanedModernisedKJV1769TextHtml=}" )
                                if modernisedTextHtml != footnoteFreeTextHtml: # only show it if it changed
                                    # if versionAbbreviation == 'KJB-1611' and parRef == 'JDG_6:23': print( f"{versionAbbreviation} {parRef} {modernisedTextHtml=}")
                                    cleanedModernisedTextHtml = modernisedTextHtml.replace( versionAbbreviation, '' )
                                    if versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1611') \
                                    and cleanedModernisedTextHtml == cleanedModernisedKJV1769TextHtml:
                                        modernisedTextHtml = f"<small>Modernised spelling is same as used by KJB-1769 above{' apart from footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1611') \
                                    and cleanedModernisedTextHtml.lower() == cleanedModernisedKJV1769TextHtml.lower():
                                        modernisedTextHtml = f"<small>Modernised spelling is same as used by KJB-1769 above, apart from capitalisation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1611') \
                                    and cleanedModernisedTextHtml.replace(',','').replace('.','').replace(':','').replace(';','').replace('“','').replace('”','').replace('‘','').replace('’','') \
                                    == cleanedModernisedKJV1769TextHtml.replace(',','').replace('.','').replace(':','').replace(';','').replace('“','').replace('”','').replace('‘','').replace('’',''):
                                        modernisedTextHtml = f"<small>Modernised spelling is same as used by KJB-1769 above, apart from punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB-1611') \
                                    and cleanedModernisedTextHtml.replace(',','').replace('.','').replace(':','').replace(';','').replace('“','').replace('”','').replace('‘','').replace('’','').lower() \
                                    == cleanedModernisedKJV1769TextHtml.replace(',','').replace('.','').replace(':','').replace(';','').replace('“','').replace('”','').replace('‘','').replace('’','').lower():
                                        modernisedTextHtml = f"<small>Modernised spelling is same as used by KJB-1769 above, apart from capitalisation and punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    else:
                                        # Hardwire added words to italics
                                        modernisedTextHtml = convert_adds_to_italics( modernisedTextHtml, f'Ancient parallel verse {parRef}' )
                                        modernisedTextHtml = modernisedTextHtml.replace( '_verseTextChunk"', '_mod"' )
                                        # if '<div' in modernisedTextHtml: # Shouldn't put a div inside a span!
                                        #     assert C=='-1' and V=='0'
                                        #     textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})''' # Typically a book heading
                                        # else: # no div
                                    textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})'''
                            elif versionAbbreviation in ('LUT','CLV'):
                                translateFunction = translateGerman if versionAbbreviation=='LUT' else translateLatin
                                adjustedForeignTextHtml = None
                                if C!='-1' and V!='0' and textHtml:
                                    # assert footnoteFreeTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                    # assert footnoteFreeTextHtml.endswith( '</span>' )
                                    # footnoteFreeTextHtml = footnoteFreeTextHtml[30+len(versionAbbreviation):-7]
                                    # assert f'class="{versionAbbreviation}_verseTextChunk"' not in footnoteFreeTextHtml
                                    adjustedForeignTextHtml = translateFunction( footnoteFreeTextHtml.replace( f'<span class="{versionAbbreviation}_verseTextChunk">', f'<span class="{versionAbbreviation}_trans">') )
                                    if footnotesHtml:
                                        translatedFootnotesHtml = removeDuplicateFNids( parRef, f'{footnotesHtml}__JOIN__{translateFunction( footnotesHtml )}' ).split( '__JOIN__' )[1]
                                if adjustedForeignTextHtml and adjustedForeignTextHtml != textHtml: # only show it if it changed
                                    # No longer true since we're now using getFullText (even for basicOnly), e.g., we may have id fields included in a bookHeader div
                                    # assert '</p>' not in textHtml
                                    if '<div ' in textHtml: # it might have had footnotes in a <div>, but we want the transliteration BEFORE the footnotes
                                        assert '</div>' in textHtml
                                        textHtml = textHtml.replace( '<hr', f'''<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})<hr''' ) \
                                                    if '<hr ' in textHtml else f'''{textHtml}<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})'''
                                    else: # no <div>s so should be ok to add a span
                                        assert '</div>' not in textHtml
                                        textHtml = f'''{textHtml}<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})'''
                            elif versionAbbreviation == 'SR-GNT':
                                SRtranscription = grammaticalKeysHtmlList = None
                                if C!='-1' and V!='0' and textHtml:
                                    # print( f"{parRef} SR-GNT {verseEntryList=} {textHtml=} {footnoteFreeTextHtml=}" )
                                    # if '<' in textHtml or '>' in textHtml or '=' in textHtml or '"' in textHtml:
                                    #     if '<br>' not in textHtml: # Some verses have a sentence break
                                    #         print( f"\nunexpected fields in SR-GNT textHtml {parRef} {textHtml}" ); halt
                                    # assert textHtml.startswith( '<span class="SR-GNT_verseTextChunk">' )
                                    # assert textHtml.endswith( '</span>' )
                                    # textHtml = textHtml[36:-7]
                                    # if 'span' in textHtml: # This can happen if a verse has a paragraph break in the middle of it
                                    #     textHtml = textHtml.replace( '<span class="SR-GNT_verseTextChunk">', '' ).replace( '</span>', '' )
                                    # assert 'span' not in textHtml
                                    textHtml, grammaticalKeysHtmlList = brightenSRGNT( BBB, C, V, textHtml, verseEntryList, state )
                                    # textHtml = f'<span class="SR-GNT_verseTextChunk">{textHtml}</span>'
                                    # checkHtml( f'footnoteFreeTextHtml {parRef}', footnoteFreeTextHtml, segmentOnly=True )
                                    # assert footnoteFreeTextHtml.startswith( '<span class="SR-GNT_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                    # assert footnoteFreeTextHtml.endswith( '</span>' )
                                    # footnoteFreeTextHtml = footnoteFreeTextHtml[36:-7]
                                    # assert 'class="SR-GNT_verseTextChunk"' not in footnoteFreeTextHtml
                                    footnoteFreeTextHtml, _grammaticalKeysHtmlList = brightenSRGNT( BBB, C, V, footnoteFreeTextHtml, verseEntryList, state )
                                    SRtranscription = transliterate_Greek( footnoteFreeTextHtml.replace( '<span class="SR-GNT_verseTextChunk">', '<span class="SR-GNT_trans">') ) # Colourisation and nomina sacra gets carried through
                                    if 'Ah' in SRtranscription or ' ah' in SRtranscription or SRtranscription.startswith('ah') \
                                    or 'Eh' in SRtranscription or ' eh' in SRtranscription or SRtranscription.startswith('eh') \
                                    or 'Oh' in SRtranscription or ' oh' in SRtranscription or SRtranscription.startswith('oh') \
                                    or 'Uh' in SRtranscription or ' uh' in SRtranscription or SRtranscription.startswith('uh'):
                                        raise ValueError( f"Bad Greek transcription for {versionAbbreviation} {parRef} {SRtranscription=} from '{textHtml}'" )
                                # Add an extra link to the CNTR collation page
                                collationHref = f'https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}'
                                try:
                                    # NOTE: We close the previous paragraph, but leave the key paragraph open
                                    keysHtml = f'''</p>\n<p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the OET-RV to the LV is done by some temporary software, hence the OET-RV alignments are incomplete (and may occasionally be wrong).</small>'''
                                except (UnboundLocalError, TypeError): # grammaticalKeysHtmlList
                                    keysHtml = ''
                                textHtml = f'{textHtml} <a title="Go to the GreekCNTR collation page" href="{collationHref}">‡</a>'
                                if SRtranscription:
                                    textHtml = f'''{textHtml}
<br>   ({SRtranscription.replace('<br>','<br>   ')})'''
                                textHtml = f'{textHtml}{keysHtml}'

                            elif versionAbbreviation in ('UGNT','SBL-GNT','TC-GNT','BrLXX'):
                                grkTranscription = None
                                if C!='-1' and V!='0' and textHtml:
                                    # print( f"{footnoteFreeTextHtml=}" )
                                    # assert footnoteFreeTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                    # assert footnoteFreeTextHtml.endswith( '</span>' )
                                    # footnoteFreeTextHtml = footnoteFreeTextHtml[30+len(versionAbbreviation):-7]
                                    # assert f'class="{versionAbbreviation}_verseTextChunk"' not in footnoteFreeTextHtml, f"{footnoteFreeTextHtml=}"
                                    grkTranscription = transliterate_Greek(footnoteFreeTextHtml.replace( f'<span class="{versionAbbreviation}_verseTextChunk">', f'<span class="{versionAbbreviation}_trans">'))
                                    if 'Ah' in grkTranscription or ' ah' in grkTranscription or grkTranscription.startswith('ah') \
                                    or 'Eh' in grkTranscription or ' eh' in grkTranscription or grkTranscription.startswith('eh') \
                                    or 'Oh' in grkTranscription or ' oh' in grkTranscription or grkTranscription.startswith('oh') \
                                    or 'Uh' in grkTranscription or ' uh' in grkTranscription or grkTranscription.startswith('uh'):
                                        raise ValueError( f"Bad Greek transcription for {versionAbbreviation} {parRef} {grkTranscription=} from '{textHtml}'" )
                                if grkTranscription:
                                    # No longer true since we're now using getFullText (even for basicOnly), e.g., we may have id fields included in a bookHeader div
                                    # assert '</p>' not in textHtml, f"Parallel verse {versionAbbreviation} {parRef} {textHtml=} {transcription=}"
                                    if '<div ' in textHtml: # it might have had footnotes in a <div>, but we want the transliteration BEFORE the footnotes
                                        assert '</div>' in textHtml
                                        textHtml = textHtml.replace( '<hr', f'''<br> ''  ({grkTranscription.replace('<br>','<br>   ')})<hr''' ) \
                                                    if '<hr ' in textHtml else f'''{textHtml}<br>   ({grkTranscription.replace('<br>','<br>   ')})'''
                                    else: # no <div>s so should be ok to add a span
                                        assert '</div>' not in textHtml
                                        textHtml = f'''{textHtml}<br>   ({grkTranscription.replace('<br>','<br>   ')})'''
                            elif versionAbbreviation == 'UHB':
                                if BBB=='PSA' and 'class="d"' in textHtml:
                                    # There's no special formatting in the original Hebrew, so we don't want it here either
                                    # print( f"\nWas PSA {C} d {textHtml=}" )
                                    dIx = textHtml.index( '<span class="d">')
                                    firstVaIx = textHtml.index( '<span class="va">', dIx+15 )
                                    spanIx1 = textHtml.index( '</span>', firstVaIx+15 ) # Should be the closing "va" span
                                    va1 = textHtml[firstVaIx+17:spanIx1]
                                    # print( f"   {va1=}")
                                    assert va1 == '1'
                                    # while textHtml.find( '<span class="va">', lastVaIx+5 ) != -1: # There can be up to three va's
                                    #     lastVaIx = textHtml.index( '<span class="va">', lastVaIx+5 )
                                    # spanIxN = textHtml.index( '</span>', lastVaIx ) # Should be the last closing "va" span
                                    # NOTE: The va end spans ARE NOT FOLLOWED BY NEWLINE, only the d span is
                                    spanEndDIx = textHtml.index( '</span>\n', spanIx1+7 ) # Should be the closing "d" span
                                    textHtml = f'{textHtml[:dIx]}{textHtml[dIx+16:spanEndDIx]}{textHtml[spanEndDIx+7:]}'
                                    # print( f"Now {textHtml=}" )
                                    # assert textHtml.count( 'class="va"' ) == textHtml.count( '</span>' ), f"{parRef} {textHtml=}" # Not true if there's a footnote caller
                                    # if C=='51': halt
                                # print( f"{versionAbbreviation} {parRef} {textHtml=}")
                                # checkHtml( f'brightenedUHB0 {parRef}', textHtml, segmentOnly=True )
                                uhbTranscription = grammaticalKeysHtmlList = None
                                if C!='-1' and V!='0' and textHtml:
                                    # print( f"{V=} {parRef} UHB {verseEntryList=} {textHtml=} {footnoteFreeTextHtml=}" )
                                    # NOTE: This code only works if there's no internal spans (due to internal paragraph breaks, etc.)
                                    # assert textHtml.startswith( '<span class="UHB_verseTextChunk">' ), f""
                                    # assert textHtml.endswith( '</span>' )
                                    # textHtml = textHtml[33:-7]
                                    # # if 'class="UHB_verseTextChunk"' in textHtml: # This can happen if a verse has a paragraph break in the middle of it
                                    # #     textHtml = textHtml.replace( '<span class="UHB_verseTextChunk">', '' ).replace( '</span>', '' )
                                    # # print( f"  Now {textHtml=}" )
                                    # assert 'class="UHB_verseTextChunk"' not in textHtml
                                    textHtml, grammaticalKeysHtmlList = brightenUHB( BBB, C, V, textHtml, verseEntryList, state )
                                    # textHtml = f'<span class="UHB_verseTextChunk">{textHtml}</span>'
                                    # checkHtml( f'brightenedUHB1 {parRef}', textHtml, segmentOnly=True )
                                    # print( f"{parRef} {footnoteFreeTextHtml=}" )
                                    # checkHtml( f'footnoteFreeTextHtml {parRef}', footnoteFreeTextHtml, segmentOnly=True )
                                    # assert footnoteFreeTextHtml.startswith( '<span class="UHB_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                    # assert footnoteFreeTextHtml.endswith( '</span>' )
                                    # footnoteFreeTextHtml = footnoteFreeTextHtml[33:-7]
                                    # assert 'class="UHB_verseTextChunk"' not in footnoteFreeTextHtml
                                    footnoteFreeTextHtml, _grammaticalKeysHtmlList = brightenUHB( BBB, C, V, footnoteFreeTextHtml, verseEntryList, state )
                                    uhbTranscription = transliterate_Hebrew(footnoteFreeTextHtml.replace( '<span class="UHB_verseTextChunk">', '<span class="UHB_trans">')).replace( 'yəhvāh', 'yhwh' ).replace( 'ə', '<small>ə</small>' )
                                    checkHtml( f'uhbTranscription {parRef}', uhbTranscription, segmentOnly=True )
                                    # if C=='2': halt
                                collationHref = f'https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation(BBB)}&c={C}&v={V}'
                                try:
                                    keysHtml = f'''</p>\n<p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the OET-RV to the LV is done by some temporary software, hence the OET-RV alignments are incomplete (and may occasionally be wrong).</small>'''
                                except (UnboundLocalError, TypeError): # grammaticalKeysHtmlList
                                    keysHtml = ''
                                textHtml = f'{textHtml} <a title="Go to the OSHB verse page" href="{collationHref}">‡</a>'
                                if uhbTranscription:
                                    if parRef == 'JOS_16:0': halt
                                    textHtml = f'''{textHtml}
<br>   ({uhbTranscription.replace('<br>','<br>   ')})'''
                                textHtml = f'{textHtml}{keysHtml}'
                                # checkHtml( f'brightenedUHB2 {parRef}', textHtml, segmentOnly=True )

                            if textHtml:
                                assert not textHtml.endswith( '\n' ), f"{versionAbbreviation} {parRef} {textHtml[-30:]=}"
                                if V != '0': # Introductions can have more bits (and so too for the modified/updated bits) than individual verses
                                    if versionAbbreviation != 'OEB': # their Ezekiel is really messed up
                                        assert textHtml.count( '_verseTextChunk"' ) <= (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                    assert textHtml.count( '_mod"' ) <= (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                assert textHtml.count( '_trans"' ) < (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                # NOTE: textHtml might have footnotes in a div -- in that case we need special handling because can't put a <div> in a <p> below
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
                                    if '<div ' in textHtml: # it might be a book intro or footnotes -- we can't put a <div> INSIDE a <p>, so we append it instead
                                        assert '</div>' in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="{spanClassName}"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span></p>{textHtml}''' # .replace('<hr','</p><hr')
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="{spanClassName}"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                elif versionAbbreviation=='OET-RV':
                                    # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case)
                                    if '<div ' in textHtml: # it might be a book intro or footnotes -- we can't put a <div> INSIDE a <p>, so we append it instead
                                        assert '</div>' in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} chapter (side-by-side versions)" href="{'../'*BBBLevel}OET/byC/{BBB}_C{C}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_C{C}.htm#Top">OET-RV</a>)</small></span></p>{textHtml}'''
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} chapter (side-by-side versions)" href="{'../'*BBBLevel}OET/byC/{BBB}_C{C}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_C{C}.htm#Top">OET-RV</a>)</small></span> {textHtml}</p>'''
                                elif versionAbbreviation=='WYC': # Just add a bit about it being translated from the Latin (not the Greek)
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                    assert '<div' not in textHtml, f"{versionAbbreviation} {parRef} {textHtml=}"
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter (translated from the Latin)'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                else: # for all the others
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                    if textHtml.startswith( "(Same as " ):
                                        assert versionAbbreviation in ('WMB',)
                                        vHtml = f'''<p id="{versionAbbreviation}" class="closeVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                    elif '<div ' in textHtml: # it might be a book intro or footnotes
                                        assert '</div>' in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span></p>{textHtml}''' # .replace('<hr','</p><hr')
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                vHtml = f'{vHtml}{footnotesHtml}'
                                if translatedFootnotesHtml and translatedFootnotesHtml!=footnotesHtml: # can happen with CLV
                                    vHtml = f'{vHtml}{translatedFootnotesHtml}'
                            else: # no textHtml -- can include verses that are not in the OET-LV
                                if c==-1 or v==0: # For these edge cases, we don't want the version abbreviation appearing
                                    vHtml = ''
                                else:
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> <a title="Go to missing verses pages" href="{'../'*level}OET/missingVerse.htm">◘</a></p>'''
                            if versionAbbreviation=='TC-GNT': # the final one that we display, so show the key to the colours
                                greekVersionKeysHtmlList = []
                                if 'wrkNameDiffPunct' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffPunct">yellow</span>:punctuation differs' )
                                if 'wrkNameDiffAccents' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffAccents">orange</span>:accents differ' )
                                if 'wrkNameDiffText' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffText">red</span>:words differ' )
                                if greekVersionKeysHtmlList:
                                    vHtml = f'''{vHtml}<p class="key"><b>Key for above GNTs</b>: {', '.join(greekVersionKeysHtmlList)} (from our <b>SR-GNT</b> base).</p>'''

                        except MissingBookError:
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            assert BBB not in thisBible
                            warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except UntranslatedVerseError:
                            NEVER_GETS_HERE
                            assert textHtml == '◙'
                            assert versionAbbreviation == 'OET-RV'
                            assert BBB in thisBible
                            # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case)
                            # if BBB in thisBible:
                            # print( f"No verse inB OET-RV {BBB} in {thisBible}"); halt
                            warningText = f'No OET-RV {ourTidyBBBwithNotes} {C}:{V} verse available'
                            vHtml = f'''<p id="OET-RV" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="{state.BibleNames['OET']}" href="{'../'*BBBLevel}OET/byC/{BBB}_C{C}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_C{C}.htm#Top">OET-RV</a>)</small></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                            # else:
                            #     warningText = f'No OET-RV {ourTidyBBBwithNotes} book available'
                            #     vHtml = f'''<p id="OET-RV" class="parallelVerse"><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except KeyError:
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            if c==-1 or v==0:
                                vHtml = ''
                            elif BBB in thisBible:
                                # print( f"No verse inKT {versionAbbreviation} {BBB} in {thisBible}"); halt
                                warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} {C}:{V} verse available'
                                versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top'''
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{versionNameLink}">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )
                            else:
                                warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} book available'
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )

                    if vHtml:
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                        checkHtml( f'Parallel vHtml {versionAbbreviation} {parRef}', vHtml, segmentOnly=True )
                        assert not parallelHtml.endswith( '\n' )
                        assert not vHtml.endswith( '\n' )
                        parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{vHtml}"
                    checkHtml( f"End of parallel pass for {versionAbbreviation} {parRef}", parallelHtml.replace('<div class="hideables">\n',''), segmentOnly=True ) # hideables isn't ended yet

                # Close the hideable div
                if not TEST_MODE: assert doneHideablesDiv # Fails if no Bible versions were included that go in the hideable div
                if doneHideablesDiv:
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
                # Handle uW translation notes 'UTN'
                utnHtml = formatUnfoldingWordTranslationNotes( BBBLevel, BBB, C, V, 'parallelVerse', state )
                if utnHtml:
                    utnHtml = f'''<div id="UTN" class="parallelUTN"><a title="Go to UTN copyright page" href="{'../'*BBBLevel}UTN/details.htm#Top">UTN</a> <b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n{utnHtml}'

                # Handle BibleMapper maps and notes
                bmmHtml = getBibleMapperMaps( BBBLevel, BBB, C, V, None, None, state.preloadedBibles['OET-RV'] )
                if bmmHtml:
                    bmmHtml = f'''<div id="BMM" class="parallelBMM"><a title="Go to BMM copyright page" href="{'../'*BBBLevel}BMM/details.htm#Top">BMM</a> <b><a href="https://BibleMapper.com" target="_blank" rel="noopener noreferrer">BibleMapper.com</a> Maps</b>: {bmmHtml}</div><!--end of BMM-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n{bmmHtml}'

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'parallelVerse', None, state ) \
                        .replace( '__TITLE__', f"{ourTidyBBB} {C}:{V} Parallel Verse View{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', f'Bible, parallel, verse, view, display, {ourTidyBBB}' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*BBBLevel}ilr/"''', f'''href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top"''')
                parallelHtml = f'''{top}<!--parallel verse page-->
{adjBBBLinksHtml}
{cLinksPar}
{vLinksPar}
<h1>Parallel {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>
<p class="rem">Note: This view shows ‘verses’ which are not natural language units and hence sometimes only part of a sentence will be visible. This view is only designed for doing comparisons of different translations. Click on any Bible version abbreviation to see the verse in more of its context. {OETS_UNFINISHED_WARNING_HTML_TEXT}</p>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{parallelHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, 'parallelVerse', state )}'''
                checkHtml( f'Parallel {parRef}', parallelHtml )
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
            .replace( '__TITLE__', f"{ourTidyBBB} Parallel Verse View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, view, display, index' )
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
            .replace( '__TITLE__', f"{ourTidyBBB} Parallel Verse View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, view, display, index' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel songs index</h1>' if BBB=='PSA' else ''}{cLinksPar}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel verses index</h1>' if BBB!='PSA' else ''}{f'{NEWLINE}<p class="vsLst">{" ".join( newBBBVLinks )}</p>' if BBB!='PSA' else ''}
{makeBottom( level, 'parallelVerse', state )}'''
    checkHtml( 'parallelIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook() finished processing {len(vLinksList):,} {BBB} verses." )
    return True
# end of createParallelVersePages.createParallelVersePagesForBook


# <span class="fnCaller">[<a title="Note: K אחד" href="#fnUHB4">fn</a>]</span>
footnoteRegex = re.compile( '<span class="fnCaller">.+?</span>' )
def handleAndExtractFootnotes( versionAbbreviation:str, verseHtml:str ) -> Tuple[str,str,str]:
    """
    Given verseHtml that may contain a footnotes division,
        separate off the footnotes.
    """
    if '<div class="footnotes">' in verseHtml:
        assert '<hr ' in verseHtml, f"{versionAbbreviation} {verseHtml=}"
        assert '</div>' in verseHtml

        # Handle footnotes so the same fn1 doesn't occur for multiple versions
        verseHtml = verseHtml.replace( 'id="fn', f'id="fn{versionAbbreviation}' ).replace( 'href="#fn', f'href="#fn{versionAbbreviation}' )

        verseHtml, footnoteHtml = verseHtml.split( '<hr ' )
        verseHtml = verseHtml.rstrip()
        footnoteFreeVerseHtml, numFootnotesRemoved = footnoteRegex.subn( '', verseHtml )
        # print( f"{numFootnotesRemoved} footnotes removed from {versionAbbreviation} {verseHtml=} gives {footnoteFreeVerseHtml=}")
        return verseHtml, footnoteFreeVerseHtml, f'<hr {footnoteHtml}'
    else:
        assert '<hr ' not in verseHtml
        return verseHtml, verseHtml, ''
# end of createParallelVersePages.handleAndExtractFootnotes


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
GREEK_CASE_CLASS_KEY_DICT = { 'grkVrb':'<span class="grkVrb">khaki</span>:verbs',
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
    brRef = f'{BBB}_{C}:{V}'

    wordFileName = 'OET-LV_NT_word_table.tsv'

    cleanedbrightenTextHtml = ( brightenTextHtml.replace( '¶', ' ' ).replace( '⇔', ' ' ).replace( '§', ' ' )
                            #  .replace( '’ ”', '’”' ).replace( '” ’', '”’' ).replace( NARROW_NON_BREAK_SPACE, ' ' ) # Leave NNBSP
                                .replace( NARROW_NON_BREAK_SPACE, ' ' ).replace( NON_BREAK_SPACE, ' ' )
                                .replace( EN_SPACE, ' ' ).replace( EM_SPACE, ' ' )
                                .replace( '<span class="SR-GNT_verseTextChunk">', '' ).replace( '</span>', '' )
                                .replace( '<br>', ' ' ).replace( '   ', ' ' ).replace( '  ', ' ' )
                                .rstrip()
                                )
    punctuatedGrkWords = [punctuatedGrkWord for punctuatedGrkWord in cleanedbrightenTextHtml.split() if punctuatedGrkWord not in ('’','’,','”','”,','’;')]
    strippedGrkWords = [punctuatedGrkWord.lstrip( '“‘˚(' ).rstrip( '.,?!:’ ”·;)–…' ) for punctuatedGrkWord in punctuatedGrkWords] # Includes (now) space between speech closing marks

    # Match Greek words to word numbers
    firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][brRef]
    currentWordNumber = firstWordNumber
    grkWordNumbers = []
    for strippedGrkWord in strippedGrkWords:
        assert strippedGrkWord, f"{brRef} {strippedGrkWords=} from {punctuatedGrkWords=} from {cleanedbrightenTextHtml=} from {brightenTextHtml=}"
        # print( f"  {brRef} {strippedGrkWord=} {currentWordNumber=} from ({firstWordNumber},{lastWordNumber})" )
        ref, greekWord, SRLemma, _GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
        # print( f"    A {currentWordNumber=} {ref=} {greekWord=}" )
        while not probability and currentWordNumber < lastWordNumber:
            currentWordNumber += 1
            ref, greekWord, SRLemma, _GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
            # print( f"    B {currentWordNumber=} {ref=} {greekWord=}" )
        assert probability, f"  {ref} {greekWord=} {currentWordNumber=} {probability=}"
        if not greekWord.startswith('κρ') and not greekWord.startswith('μακρ') and not greekWord.startswith('γενν'): # Seems there were some spelling changes
            # and greekWord not in ('κράββατον','κράββατόν'):
            if greekWord.lower() != strippedGrkWord.lower():
                logging.critical( f"Unable to find word number for {brRef} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {len(grkWordNumbers)=}" )
                break # We failed to match -- it's not critical so we'll just stop here (meaning we won't have all the word numbers for this verse)
            # assert greekWord.lower() == strippedGrkWord.lower(), f"{brRef} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {grkWordNumbers=}"
        grkWordNumbers.append( currentWordNumber )
        assert currentWordNumber <= lastWordNumber
        currentWordNumber += 1
    if len(grkWordNumbers) != len(punctuatedGrkWords):
        logging.error( f"brighten SR-GNT was unable to find word numbers for all words for {brRef} (got {len(grkWordNumbers)} out of {len(punctuatedGrkWords)})" )

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
            # print( f"brightenSRGNT {brRef} {rawGrkWord=} from {punctuatedGrkWords=} from {brightenTextHtml=}" )
            ixRawGrkWord = brightenTextHtml.index( rawGrkWord, searchStartIndex )
            # except ValueError:
            #     logging.critical( f"brightenSRGNT {brRef} couldn't find {rawGrkWord=} from {punctuatedGrkWords=} from {searchStartIndex=} {brightenTextHtml[searchStartIndex:searchStartIndex+3]=} in {brightenTextHtml=}" )
            #     halt
            #     continue
            # print( f"  aE {wordNumberIndex=} {rawGrkWord=} {searchStartIndex=} {ix=} {extraIndexOffset=}")
            # assert ix != -1
            simpleGrkWord = rawGrkWord.lstrip( '“‘˚(' )
            ixRawGrkWord += len(rawGrkWord) - len(simpleGrkWord) # Adjust for removal of any leading punctuation
            simpleGrkWord = simpleGrkWord.lstrip( ' ' ).rstrip( '.,?!:”’ ·;)–…' ) # Includes NNBSP
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
                wordLink = f'../../ref/GrkWrd/{getGreekWordpageFilename(grkWordNumbers[_safetyCount1], state)}#Top' # We'd prefer to link to our own word pages
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
                    # print( f"{BBB} {C}:{V} {currentWordNumber=} {rawGrkWord=} {simpleGrkWord=} {attribDict=}" )
                    raise KeyError
            else: caseClassName = None
            if caseClassName: classKeySet.add( caseClassName )
            caseClassHtml = '' if not caseClassName else f'''class="{caseClassName}" ''' # Has a trailing space
            linkHtml = f'''<a title="{attribDict['role']}-{attribDict['morph']}" {caseClassHtml}href="{wordLink}">{simpleGrkWord}</a>'''
            beforeHtml = brightenTextHtml[:ixRawGrkWord]
            assert not beforeHtml.endswith( '.htm#Top">' ), f"brightenSRGNT about to wrongly embed an anchor after ...{beforeHtml[-80:]=}"
            brightenTextHtml = f'''{brightenTextHtml[:ixRawGrkWord-1]}<b>˚{linkHtml}</b>{brightenTextHtml[ixRawGrkWord+len(simpleGrkWord):]}''' \
                        if '˚' in rawGrkWord else \
                        f'''{beforeHtml}{linkHtml}{brightenTextHtml[ixRawGrkWord+len(simpleGrkWord):]}'''
            wordNumberIndex += 1
            if wordNumberIndex >= len(punctuatedGrkWords):
                break
            searchStartIndex = ixRawGrkWord + len(linkHtml)
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
HEBREW_CASE_CLASS_KEY_DICT = { 'hebVrb':'<span class="hebVrb">khaki</span>:verbs',
                            #   'hebNom':'<span class="hebNom">light-green</span>:nominative/subject',
                            #   'hebAcc':'<span class="hebAcc">orange</span>:accusative/object',
                            #   'hebGen':'<span class="hebGen">pink</span>:genitive/possessor',
                            #   'hebDat':'<span class="hebDat">cyan</span>:dative/indirect object',
                            #   'hebVoc':'<span class="hebVoc">magenta</span>:vocative',
                              'hebNeg':'<span class="hebNeg">red</span>:negative',
                              'hebEl':'<span class="hebEl">blue</span>:Elohim',
                              'hebYhwh':'<span class="hebYhwh">green</span>:YHWH',
                              }
def brightenUHB( BBB:str, C:str, V:str, brightenUHBTextHtml:str, verseEntryList, state:State ) -> Tuple[str,List[str]]:
    """
    Take the UHB text (which includes punctuation and might also include <br> characters and footnote callers)
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
    UHBRef = f'{BBB}_{C}:{V}'
    fnPrint( DEBUGGING_THIS_MODULE, f"brightenUHB( {UHBRef} {brightenUHBTextHtml}, {verseEntryList}, … )" )

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
        ixStartSpan =  adjustedBrightenUHBTextHtml.index( '<span class="va">' )
        ixEndSpan = adjustedBrightenUHBTextHtml.index( '</span> ', ixStartSpan+17 )
        vaText = adjustedBrightenUHBTextHtml[ixStartSpan+17:ixEndSpan]
        adjustedBrightenUHBTextHtml = f'{adjustedBrightenUHBTextHtml[:ixStartSpan]}{adjustedBrightenUHBTextHtml[ixEndSpan+8:]}' # Remove this non-Hebrew bit before we divide it into words
        vC, vV = vaText.split(':') if ':' in vaText else (C, vaText)
    assert 'class="va"' not in adjustedBrightenUHBTextHtml
    while '<span class="d">' in adjustedBrightenUHBTextHtml: # First one is at Psalm 3
        # print( f"d in brightenUHB {adjustedBrightenUHBTextHtml=} from {UHBRef} {brightenUHBTextHtml=}" )
        # This one's different because the contents of the span are Hebrew words
        ixStartSpan =  adjustedBrightenUHBTextHtml.index( '<span class="d">' )
        ixEndSpan = adjustedBrightenUHBTextHtml.index( '</span>\n', ixStartSpan+16 )
        dText = adjustedBrightenUHBTextHtml[ixStartSpan+16:ixEndSpan]
        # print( f"{dText=} from {UHBRef} {brightenUHBTextHtml=}" ); halt
        adjustedBrightenUHBTextHtml = f'{adjustedBrightenUHBTextHtml[:ixStartSpan]}{dText}{adjustedBrightenUHBTextHtml[ixEndSpan+8:]}' # Remove only the non-Hebrew formatting bits before we divide it into words
        # print( f"  {UHBRef} {dText=} {adjustedBrightenUHBTextHtml=}" ); halt
        # vC, vV = dText.split(':') if ':' in vaText else (C, vaText)
    assert 'class="d"' not in adjustedBrightenUHBTextHtml
    while '<span class="fnCaller">' in adjustedBrightenUHBTextHtml: # First one is at Psalm 3
        # print( f"fnCaller in brightenUHB {adjustedBrightenUHBTextHtml=} from {UHBRef} {brightenUHBTextHtml=}" )
        # This one's different because the contents of the span are Hebrew words
        ixStartSpan =  adjustedBrightenUHBTextHtml.index( '<span class="fnCaller">' )
        ixEndSpan = adjustedBrightenUHBTextHtml.index( '</span>', ixStartSpan+23 )
        fnCallerText = adjustedBrightenUHBTextHtml[ixStartSpan+23:ixEndSpan]
        # print( f"{dText=} from {UHBRef} {brightenUHBTextHtml=}" ); halt
        adjustedBrightenUHBTextHtml = f'{adjustedBrightenUHBTextHtml[:ixStartSpan]}{adjustedBrightenUHBTextHtml[ixEndSpan+7:]}' # # Remove this non-Hebrew bit before we divide it into words
        # print( f"  {UHBRef} {fnCallerText=} {adjustedBrightenUHBTextHtml=}" )
        # vC, vV = dText.split(':') if ':' in vaText else (C, vaText)
    assert 'class="fnCaller"' not in adjustedBrightenUHBTextHtml
    # The following line is no longer true, because we now include footnotes on these pages
    # assert 'span' not in adjustedBrightenUHBTextHtml, f"{UHBRef} {adjustedBrightenUHBTextHtml=} from {brightenUHBTextHtml=}"
    checkHtml( f'adjustedBrightenUHBTextHtml {UHBRef}', adjustedBrightenUHBTextHtml, segmentOnly=True ) # TODO: REMOVE This should be irrelevant/unnecessary
    cleanedAdjustedBrightenUHBTextHtml = ( adjustedBrightenUHBTextHtml.replace( '\n<br>', ' ').replace( '<br>', ' ')
                          .replace( NARROW_NON_BREAK_SPACE, ' ' ) # Used after variant verse numbers (\\va fields)
                          .replace( '<span class="UHB_verseTextChunk">', '' ).replace( '</span>', '' )
                          .replace( '¶', ' ')
                          .replace( '־', ' ־ ') # We surrounded maqaf by spaces so it's processed like a word
                          .replace( '׀', ' ׀ ' ) # Same for HEBREW PUNCTUATION PASEQ U+05C0
                          .replace( ' פ ', ' ') # Remove stand-alone pe, first one at Gen 35:22
                          .replace( ' ס ', ' ') # Remove stand-alone samekh, first one at Deu 2:8
                        #   .replace( ' ס', '') # Remove stand-alone samekh at end of strong, first one at Exo 14:25 XXX THIS IS DELETING SAMEKH AT START OF WORDS!!!!
                          .replace( '  ', ' ').replace( '   ', ' ')
                        #   .replace( '\n<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n', '' )
                          )
    try:
        cleanedAdjustedBrightenUHBTextHtml, _footnoteStuff = cleanedAdjustedBrightenUHBTextHtml.split( '<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n' )
        # print( f"{_footnoteStuff}" )
    except ValueError: # No footnotes
        assert 'class="fn"' not in cleanedAdjustedBrightenUHBTextHtml
    assert 'width:40%' not in cleanedAdjustedBrightenUHBTextHtml, f"{UHBRef} {cleanedAdjustedBrightenUHBTextHtml=}"
    if cleanedAdjustedBrightenUHBTextHtml.endswith(' פ'):
        cleanedAdjustedBrightenUHBTextHtml = cleanedAdjustedBrightenUHBTextHtml[:-2] # Remove final stand-alone samekh
        # print( f"{UHBRef} Did extra clean-up '{cleanedAdjustedBrightenUHBTextHtml.replace(WJ,'')}'")
    punctuatedHebWords = cleanedAdjustedBrightenUHBTextHtml.split( ' ' )
    strippedHebWords = []
    for punctuatedHebWord in punctuatedHebWords:
        if punctuatedHebWord.endswith( '׃׆ס' ):
            punctuatedHebWord = punctuatedHebWord[:-3] # Remove 'sof pasuq' and 'reverse nun' and 'samekh' Hebrew characters
        if punctuatedHebWord.endswith( '׃פ' ) or punctuatedHebWord.endswith( '׃ס' ): # We don't want to remove these from the end of normal words
            punctuatedHebWord = punctuatedHebWord[:-2] # Remove 'sof pasuq' and 'pe' or 'samekh' Hebrew characters
        strippedHebWords.append( punctuatedHebWord.lstrip( '“‘˚(' ).rstrip( '.,?!:”’·;)–…׃') ) # Last rstrip one is 'sof pasuq' and 'pe' & 'samekh' Hebrew characters
    # print( f"  brightenUHB strippedHebWords={str(strippedHebWords).replace(WJ,'')}" )

    # Match Hebrew words to word numbers -- we use the original numbering which is marked as variant in UHB
    try: firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{vC}:{vV}']
    except KeyError as e:
        logging.error( f"brightenUHB() {UHBRef} nothing for {e}" )
        return brightenUHBTextHtml, []

    currentWordNumber = firstWordNumber
    hebWordNumbers = []
    for strippedHebWord in strippedHebWords:
        # print( f"  {UHBRef} strippedHebWord='{strippedHebWord.replace(WJ,'')}' {currentWordNumber=} from ({firstWordNumber},{lastWordNumber})" )
        ref, rowType, morphemeRowList, lemmaRowList, strongs, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tags = state.OETRefData['word_tables'][wordFileName][currentWordNumber].split( '\t' )
        hebWordNumbers.append( currentWordNumber )
        # TODO: probably d field in PSA is a problem
        # NOTE: Next two lines temporarily disabled 5Jun24
        # if BBB!='PSA' and not f'{BBB}_{C}' in ('NUM_26','SA1_20','KI1_22','CH1_12','JOB_41'): # Num 26:1/25:19 and SA1 20:42 is a very complicated versification issue (chapter break in middle of alternative verse)
        #     assert currentWordNumber <= lastWordNumber, f"{currentWordNumber=} {firstWordNumber=} {lastWordNumber=}"
        currentWordNumber += 1
    if len(hebWordNumbers) != len(strippedHebWords):
        logging.error( f"brighten UHB was unable to find word numbers for all words for {UHBRef} (got {len(hebWordNumbers)} out of {len(strippedHebWords)})" )

    # TODO: Not totally sure that we need these extras from https://github.com/Center-for-New-Testament-Restoration/SR files
    #           now that we have the word numbers for the Hebrew words
    allExtras = None
    for verseEntry in verseEntryList:
        # print( f"    vE {verseEntry=}" )
        marker, extras = verseEntry.getMarker(), verseEntry.getExtras()
        if extras: # Extras contain the info we need, like: ww @ 4 = 'Ἀρχὴ|lemma="ἀρχή" x-koine="αρχη" x-strong="G07460" x-morph="Gr,N,....NFS"'
            # print( f"      ME {marker=} {extras=}" )
            if allExtras is None:
                allExtras = list( extras )
            else: allExtras += list( extras )

    checkHtml( f'Middle of brightenedUHB {UHBRef}', brightenUHBTextHtml, segmentOnly=True )
    classKeySet = set()
    if allExtras:
        # Find each word in brightenTextHtml, find the word info in allExtras, and then update brightenTextHtml with more classes
        searchStartIndex = verseWordNumberIndex = extraIndexOffset = 0
        for _safetyCount1 in range( len(strippedHebWords)+1 ):
            checkHtml( f'Extras loop top for brightenedUHB {UHBRef} {_safetyCount1=}', brightenUHBTextHtml, segmentOnly=True )
            rawHebWord = strippedHebWords[verseWordNumberIndex]
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Start of {UHBRef} loop1 {_safetyCount1=} {verseWordNumberIndex=} {rawHebWord=}" )
            # assert 'span' not in rawHebWord # No longer true now that we have footnotes included for display
            assert '\n' not in rawHebWord
            attribDict = {}
            if rawHebWord in '־׀': # maqaf and paseq
                attribDict['lang'] = 'He'
                attribDict['morph'] = ['maqaf' if rawHebWord=='־' else 'paseq']
                verseWordNumberIndex += 1
                if verseWordNumberIndex >= len(strippedHebWords):
                    break
                # searchStartIndex = ixRawHebWord + len(simpleHebWord)
                searchStartIndex += 1
                extraIndexOffset -= 1 # Stops the extras from advancing
                continue # nothing more to do in this loop
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  About to search for {rawHebWord=} in {searchStartIndex=} {brightenUHBTextHtml[searchStartIndex:]=} {brightenUHBTextHtml[searchStartIndex:].count(rawHebWord)=}")
            try: ixRawHebWord = brightenUHBTextHtml.index( rawHebWord, searchStartIndex )
            except ValueError as e:
                logging.critical( f"brightenUHB {UHBRef} couldn't find {rawHebWord=} {searchStartIndex=} in {brightenUHBTextHtml}, {verseEntryList}: {e}" )
                halt
                verseWordNumberIndex += 1
                if verseWordNumberIndex >= len(strippedHebWords):
                    break
                continue # TODO: Why did this happen?
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  aE {verseWordNumberIndex=} ({len(rawHebWord)}) {rawHebWord=} {searchStartIndex=} {ixRawHebWord=} {extraIndexOffset=}")
            assert ixRawHebWord != -1
            simpleHebWord = rawHebWord.lstrip( '“‘˚(' ) # TODO: Why do we need to do this again? Seems redundant
            # print( f"({len(simpleHebWord)}) {simpleHebWord=}" )
            ixRawHebWord += len(rawHebWord) - len(simpleHebWord) # Adjust for removal of any leading punctuation
            simpleHebWord = simpleHebWord.rstrip( '.,?!:”’·;)–…׃' ) # Last ones are 'sof pasuq' and was 'pe' & samekh Hebrew characters
            # if '\u2060' not in simpleHebWord: # word joiner '⁠' -- this fails for words like 'בְּ\u2060רֵאשִׁ֖ית' which has a word-joiner in it
            #     assert simpleHebWord.isalpha(), f"{simpleHebWord=}" # This doesn't seem to work for Hebrew, e.g., word 'בָּרָ֣א' fails
            #       so do this instead
            assert ',' not in simpleHebWord and ':' not in simpleHebWord and '.' not in simpleHebWord and '¦' not in simpleHebWord, f"brightenUHB {UHBRef} {simpleHebWord=} from {adjustedBrightenUHBTextHtml=} from {brightenUHBTextHtml=}"
            if '־' in simpleHebWord: halt # maqaf
            for _safetyCount2 in range( 4 ): # we use this instead of while True to use extraIndexOffset to step past any possible footnotes, etc.
                # print( f"     Loop2 {_safetyCount2} {verseWordNumberIndex=} {extraIndexOffset=} sum={verseWordNumberIndex+extraIndexOffset} {len(allExtras)=}")
                try: extraEntry = allExtras[verseWordNumberIndex+extraIndexOffset]
                except IndexError: break # not sure why wordNumberIndex is too high (even with extraIndexOffset=0) and this happens -- first one at Gen 3:15
                # print( f"     {brightenUHBTextHtml[ixRawHebWord:ixRawHebWord+20]=}… {extraEntry=}")
                extraType, extraText = extraEntry.getType(), extraEntry.getText()
                # print( f"       TyTxClTx {extraType=} {extraText=} {extraEntry.getCleanText()=}")
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
                        # print( f"    {extraTextChunk=}")
                        fieldName, fieldValue = extraTextChunk.split( '=', 1 )
                        fieldValue = fieldValue.strip( '"' )
                        if fieldName.startswith( 'x-' ): fieldName = fieldName[2:]
                        if fieldName == 'strong':
                            # assert 'H' in fieldValue, f"{fieldValue=}" # Can be something like 'b:H7225' or "l"
                            assert fieldValue.count( 'H' ) <= 1, f"{fieldValue=}" # Can be something like 'b:H7225' or "l"
                            # Seems that the ':' is a morpheme separator
                            strongs = []
                            for subFieldValue in fieldValue.split( ':' ):
                                # print( f"      strong {subFieldValue=}" )
                                if subFieldValue[0] == 'H':
                                    subFieldValue = subFieldValue[1:]
                                    # assert subFieldValue.isdigit() # Fails on '7760a'
                                assert 1 <= len(subFieldValue) <= 5
                                strongs.append( subFieldValue )
                            fieldValue = strongs
                        elif fieldName == 'morph':
                            # print( f"      morph field {fieldValue=}")
                            if ':' in attribDict['strong']: # 'strong' in attribDict and
                                assert fieldValue.count(':') == attribDict['strong'].count( ':' )
                            assert fieldValue.startswith( 'He,' ) or fieldValue.startswith( 'Ar,' ), f"{fieldValue=}"
                            attribDict['lang'] = fieldValue[:2]
                            fieldValue = fieldValue[3:] # Remove unneeded? language prefix
                            # Seems that the ':' is a morpheme separator in the UHB
                            morphs = []
                            for subFieldValue in fieldValue.split( ':' ):
                                # print( f"        morph {subFieldValue=}" )
                                assert 1 <= len(subFieldValue) <= 6
                                morphs.append( subFieldValue )
                            fieldValue = morphs
                        # print( f"     {simpleHebWord} {fieldName}='{fieldValue}'" )
                        attribDict[fieldName] = fieldValue
                    break
                # print( f"Oops!!! No match for {simpleHebWord=} {extraText=}")
                # TODO: Why do we have to disable the next two lines for NEH 7:68
            #     halt
            # else: need_to_increase_count2_for_brightenUHB
            # print( f"    {attribDict=}" )
            try:
                wordLink = f'../../ref/HebWrd/{getHebrewWordpageFilename(hebWordNumbers[_safetyCount1], state)}#Top' # We'd prefer to link to our own word pages
            except IndexError:
                wordLink = f'''https://BibleHub.com/greek/{attribDict['strong'][:-1]}.htm''' # default to BibleHub by Strongs number if we don't know the word number
            # NOTE: We have almost identical code in livenOETWordLinks() in OETHandlers.py
            caseClassName = None
            try:
                for subMorph in attribDict['morph']:
                    if subMorph[0] == 'V':
                        caseClassName = 'hebVrb'
                        break
            except KeyError:
                logging.error( f"Error: {UHBRef} no morph available for {simpleHebWord=} from {rawHebWord=} from {strippedHebWords=}" )
            try:
                for subStrong in attribDict['strong']:
                    # print( f"{subStrong=}" )
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
            except KeyError:
                logging.error( f"Error: {UHBRef} no strongs available for {simpleHebWord=} from {rawHebWord=} from {strippedHebWords=}" )
            # elif attribDict['morph'][4] != '.':
            #     try:
            #         caseClassName = f'''heb{HEBREW_CASE_CLASS_DICT[attribDict['morph'][4]]}'''
            #     except KeyError:
            #         print( f"{UHBRef} {currentWordNumber=} {rawHebWord=} {simpleHebWord=} {attribDict=}" )
            #         raise KeyError
            if caseClassName: classKeySet.add( caseClassName )
            caseClassHtml = '' if not caseClassName else f'''class="{caseClassName}" ''' # Has a trailing space
            adjusted_morphology_fields = []
            if 'morph' in attribDict:
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
            # print( f"            {titleHtml=} {caseClassHtml=} {wordLink=} {simpleHebWord=}" )
            linkHtml = f'<a {titleHtml}{caseClassHtml}href="{wordLink}">{simpleHebWord}</a>'
            # print( f"            {linkHtml=}" )
            beforeHtml = brightenUHBTextHtml[:ixRawHebWord]
            # print( f"              {beforeHtml=}" )
            # afterHtml = brightenUHBTextHtml[ixRawHebWord+len(simpleHebWord):]
            # print( f"              {afterHtml=}" )
            assert not beforeHtml.endswith( '.htm#Top">' ), f"brightenUHB about to wrongly embed an anchor after ...{beforeHtml[-80:]=}"
            # print( f"              after='{brightenUHBTextHtml[ixRawHebWord+len(simpleHebWord):]}'" )
            brightenUHBTextHtml = f'{beforeHtml}{linkHtml}{brightenUHBTextHtml[ixRawHebWord+len(simpleHebWord):]}'
            checkHtml( f'Extras loop bottomA for brightenedUHB {UHBRef} {_safetyCount1=}', brightenUHBTextHtml, segmentOnly=True )
            verseWordNumberIndex += 1
            if verseWordNumberIndex >= len(strippedHebWords):
                break
            searchStartIndex = ixRawHebWord + len(linkHtml)
            searchHtml = brightenUHBTextHtml[searchStartIndex:]
            # print( f"              {searchHtml=}" )
            checkHtml( f'Extras loop bottomB for brightenedUHB {UHBRef} {_safetyCount1=}', brightenUHBTextHtml, segmentOnly=True )
        else: need_to_increase_safetyCount1_for_brightenUHB

    # Get the colour keys into the correct order
    classKeyList = []
    for classKey,classKeyHtml in HEBREW_CASE_CLASS_KEY_DICT.items():
        if classKey in classKeySet:
            classKeyList.append( classKeyHtml )
    # assert classKeyList # TODO: re-enable once the above is working better

    checkHtml( f'Finished brightenedUHB {UHBRef}', brightenUHBTextHtml, segmentOnly=True )
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
    (('token his ',),'took his '),
    ((' to many:',),' too many:'), # CB Jdg 7:4
    (('the see ',),'the sea '),
    (('we han ',),'we have '),
    (('with greet',),'with great'),

    # Two words into one word
    (('a fore honde','afore hand','aforehande'),'aforehand'),
    ((' all wayes ',),' always '),
    ((' any thyng',' eny thinge',' any thing'),' anything'),
    ((' can not ',),' cannot '),
    ((' `eere ryngis ',),' earrings '),
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
    (('ouerbody cote',),'overcoat'),
    (('sea syde','sea side'),'seaside'),
    (('stiffe necked',),'stiff-necked'),
    (('strayght waye','streight waye'),'straightway'),
    (('taske maisters',),'taskmasters'),
    (('them selues',),'themselves'),
    (('thy selfe','thi silf','yi self'),'thyself/yourself'),
    ((' to gedder',' to geder',' to gidir'),' together'),
    (('with outen',),'without'),
    (('whom soeuer ',),'whomsoever '),
    (('youre selues',),'yourselves'),

    # One word into two
    ((' assoone ',' assone '),' as soon '),
    (('gendride',),'begat/gave_birth_to'), # middle-English
    (('riythond','riythalf'),'right hand'),
    (('shalbe ',),'shall be '),(('shalbe.',),'shall be.'),
    ((' wilbe ',),' will be '),

    # Change single words (esp. middle English)
    ((' reuth ',),' pity/sorrow '),
    ((' strondis ',),' riverbeds '),

    # Single words
    ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' abyde ',),' abide '),
            ((' aboute',),' about'), ((' aboue ',),' above '),
            ((' abrode',' abroade'),' abroad'),
            ((' abstayne ',),' abstain '),
            (('abundaunce',),'abundance'),
        ((' accorde ',' acorde '),' accord '),((' acordynge',' acordinge'),' according'), (('knoulechide',),'acknowledged'),
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
            (('answerden','answerede','answerde','answeriden','answeride','aunswered'),'answered'),((' aunswere ',' answere '),' answer '),((' aunswere,',),' answer,'),((' aunswere:',' answere:'),' answer:'),
            ((' ony ',' eny '),' any '), (('enythinge',),'anything'),
        (('apostlis',),'apostles'),
            (('appearaunce',),'appearance'),(('appearynge','apperynge','apperinge','appearyng'),'appearing'),((' apperiden',' appered',' apperide'),' appeared'),((' appeare ',),' appear '), (('appoynted',),'appointed'),(('appoynte','apoynte'),'appoint'),
        (('archaungel',),'archangel'), ((' aryse',),' arise'),(('Aryse ',),'Arise '), (('Arke ',),'ark '),((' arcke ',' arke '),' ark '), ((' arte ',),' art '),
        (('ascencioun',),'ascension'),
            ((' asshes',),' ashes'),
             ((' askeden',' axiden',' axide',' axed'),' asked'), ((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            (('Asse ',),'Ass '),((' asse,',),' ass,'),
            (('astonnied','astonied','astonnyed','astonyed'),'astonished'), (('astromyenes',),'astronomers'),
        ((' eeten,',' eten,'),' ate,'), ((' athyrst',),' athirst'), ((' attayne ',' attaine '),' attain '),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
        ((' auoyded',),' avoided'),
        ((' awaye',' awei'),' away'),
    ((' backe ',),' back '), (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            (('basskettes','baskettes'),'baskets'), (('bastardes',),'bastards'),
            ((' batels',),' battles'),
        ((' bee ',),' be '),
            ((' bearinge',' bearynge',' beringe',' berynge'),' bearing'),((' beare ',' bere '),' bear '), (('beastes','beestes','beestis'),'beasts/animals'),((' beesti',' beeste',' beest'),' beast/animal'),
            ((' beed ',' bedde '),' bed '),
            ((' bene ',' ben '),' been '),
            ((' bifore',' bifor'),' before'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), ((' bigat ',' begate '),' begat '), ((' beggere',' begger'),' beggar'), ((' beggide',),' begged'), (('bigynnyng','beginnynge','beginnyng','begynnynge','begynnyng','begynninge'),'beginning'), (('bigetun ','begotte '),'begotten '),
            (('behelde','biheeld'),'beheld'), ((' behinde',' bihynde',' behynde'),' behind'), ((' biholdinge',),' beholding'),(('Biholde','Beholde'),'Behold'),((' biholdist ',' biholde ', ' beholde '),' behold '),((' beholde,',),' behold,'), ((' bihoueth',),' behoves'),
            ((' beynge ',' beyng '),' being '),
            (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), (('Bileue ','Beleeue ','Beleue ','Beleve '),'Believe '),((' beleue',' beleeue',' beleve',' bileue'),' believe'),
                ((' bellie ',),' belly '),
                ((' belonge ',),' belong '), ((' beloued',' beloven'),' beloved'),
            ((' berith',),' beareth'),
            (('beseeching','besechyng'),'beseeching/imploring'),(('biseche ','beseech '),'beseech/implore '),(('biseche,','beseech,'),'beseech/implore,'), ((' besydes',' bisidis'),' besides'),((' besyde',),' beside'),
            (('Bethanie ','Bethania ','Bethanye ','Betanye '),'Bethany '), (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '),(('Bethleem,',),'Bethlehem,'), (('bitraiede','betraied'),'betrayed'),(('bitraye ','betraye ','betraie '),'betray '), ((' betere ',),' better '), ((' bitwixe',' betweene',' betwene'),' between'),
            ((' beyonde',' biyende',' biyondis',' beionde'),' beyond'),
        ((' byd ',),' bid '), ((' byde ',),' bide/stay '),
            ((' bynde',),' bind'),
            ((' briddis',),' birds'), ((' birthe',),' birth'),
            ((' bitternesse',' bytternes'),' bitterness'),
        (('Blessid ',),'Blessed '),(('blesside','blissid'),'blessed'), (('blessynge',),'blessing'),
            (('blynde','blynd','blinde'),'blind'),
            (('bloude','bloud'),'blood'),
        ((' bootys',),' boats'),
            ((' bodili ',),' bodily '),((' boddy ',' bodi '),' body '),((' bodie,',' bodi,'),' body,'),
            ((' booke ',' boke '),' book '),((' booke,',),' book,'),
            ((' boond ',),' bond '),
            ((' borderyng',' borderinge'),' bordering'), ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'),
            ((' bosome ',' bosum '),' bosom '),
            ((' bothe ',),' both '), (('bottomlesse',),'bottomless'),
            ((' boundun ',' bounde '),' bound '),
            ((' bowe ',),' bow '),
        ((' braunches',),' branches'),((' braunch',' braunche'),' branch'),
            ((' breake ',),' break '), ((' brest ',),' breast/chest '), (('britheren',),'brethren/brothers'),(('brethre ',),'brethren/brothers '),(('brithre.',),'brethren/brothers.'),(('brethren:','brethre:'),'brethren/brothers:'),
            (('brycke','bricke','bryck'),'brick'), ((' bryde',),' bride'), (('bryngeth',),'bringeth/brings'),(('bryngyng',),'bringing'), (('Brynge ','Bryng '),'Bring '),((' brynge ',' bryng ',' bringe '),' bring '),
            ((' brookes',' brokes'),' brooks'), ((' brouyten ',' brouyte ',' broughte '),' brought '),
        (('buyldynges','buildynges','bildyngis'),'buildings'),(('buyldinge',),'building'),
            ((' buriall',),' burial'),((' birieden ',' biried ',' buryed '),' buried '),((' buryinge',' biriyng'),' burying'), ((' brent',),' burnt'),((' burne ',),' burn '),
            ((' bysy ',),' busy '),((' busines',' busynesse',' busynes'),' business'),(('businesss',),'business'), ((' byers',' biggeris'),' buyers'),
            ((' botere.',),' butter.'),
            ((' bie ',),' buy '),((' bie;',),' buy;'),
        (('Bi ',),'By '),((' bi ',),' by '),
    (('Cæsar','Cesar'),'Caesar'),
            ((' clepiden',' clepide',' clepid'),' called'),(('calleth','clepith'),'calleth/calls'),((' callyng',),' calling'),((' cal ',),' call '),
            ((' cam ',' camen '),' came '),((' cam,',' camen,'),' came,'), ((' campe ',),' camp '),
            ((' kunne ',),' can '), (('Chanaanites','Cananites'),'Canaanites'), ((' candlestickes',' candelstyckes',' candlestyckes',' candilstikis'),' candlesticks'),((' candilstike',),' candlestick'),
            (('Captaine','Captayne'),'Captain'), (('captiues',),'captives'),(('captyue',),'captive'),
            (('carnall ',),'carnal '), (('carpeter',),'carpenter'), ((' carieth',' caried'),' carried'),((' cary ',),' carry '),
            ((' castynge',' castyng',' castinge'),' casting/throwing'),((' castiden ',' kesten '),' cast/throw '),((' caste ',' keste '),' cast/threw '), (('casteles','castels'),'castles'),
            ((' cattell',' catell ',' catel'),' cattle'),
        ((' ceesside',' ceessid',' ceassed'),' ceased'),((' ceesse ',' ceasse '),' cease '),((' ceesse,',' ceasse,'),' cease,'),
            (('centurien',),'centurion'),
            ((' certayne',' certein',' certaine'),' certain'),
        (('cheynes','chaines'),'chains'),
                (('chamber','chaumber','chambre'),'chamber/room'),
                (('chaunced','chaunsed'),'chanced'), (('chaungeris',),'changers'), (('chaunginge','chaungyng','chaunging'),'changing'),
                (('charettes','charets','charis'),'chariots'), (('charite',),'charity'),
                (('chastisynge',),'chastising'),(('chastisith','chasteneth'),'chastens/disciplines'),
            ((' cheife ',' chefe '),' chief '), (('chyldren',),'children'),(('childre ',),'children '), (('chylde,','childe,'),'child,'),(('chylde.','childe.'),'child.'), (('chymney',),'chimney'),
            ((' chese ',),' choose '), (('chosun',),'chosen'),
            (('chirchis',),'churches'),(('chirche',),'church'),(('Churche ',),'Church '),(('Churche,',),'Church,'),
            (('Christes',),'Christ’s'),(('Christe','Crist'),'Christ'),
        (('citeseyns',),'citizens'), ((' citees',),' cities'),((' cyte ',' citie ',' citee '),' city '),((' citie,',' citee,',' cite,'),' city,'),((' citie.',' citee.',' cite.'),' city.'),((' citie:',' citee:',' cite:'),' city:'),((' citie;',' citee;',' cite;'),' city;'),
        ((' claye ',' cley '),' clay '),((' clei,',' cley,',' claye,'),' clay,'),
            ((' cleane ',),' clean '),
            (('climbeth','clymmeth','clymeth','climeth'),'climbeth/climbs'),
            (('cloothis','clothis'),'clothes'), ((' cloudis',' cloudes'),' clouds'),((' cloude ',),' cloud '),((' cloude,',),' cloud,'), ((' clouen',),' cloven'),
        ((' coostis',' coastes'),' coasts'), ((' cootis',' coottes',' coates',' cotes'),' coats'),((' cote,',),' coat,'),
            ((' coold ',),' cold '), ((' coolte ',),' colt '),
            ((' cometh',' commeth'),' cometh/comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming'),' coming'),
                ((' conforted',' coforted',' coumfortid'),' comforted'),((' coumfortour',),' comforter'), ((' coumforten ',' comforte '),' comfort '),
                (('commaundementes','commandementes','commandements'),'commandments'),(('commaundement','comaundement','commandement'),'commandment'),(('comaundide','comaundid','commaunded','comaunded'),'commanded'), ((' commaunde ',' commaund '),' command '), ((' comyn',),' common'), ((' comunicacion',),' communication'),
                (('companyons',),'companions'), (('companye',),'company'), (('complaynte',),'complaint'), (('comprehendiden',),'comprehended'),
            (('conseyue ',),'conceive '),
                (('cofessing','confessynge','confessyng'),'confessing'), (('confessioun',),'confession'),
                (('congregacions','cogregacios'),'congregations'),(('congregacion',),'congregation'),
                (('consyderest','considerest'),'consider'), (('consolacion',),'consolation'),
                (('contynued',),'continued'),(('contynuynge',),'continuing'),
                (('conueniently','coueniently'),'conveniently'),
            (('Corinthyans',),'Corinthians'), ((' corne ',),' corn '),
            ((' coulde',' coude'),' could'),
                ((' councill',' councell',' councel',' counsell'),' council/counsel'), ((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre'),' country'),
            (('Couenant',),'Covenant'),((' couenaunt',' couenaut',' couenant'),' covenant'), ((' couered',),' covered'), ((' couereth',),' covereth'),
        ((' crieden',' criede',' cryed'),' cried'), (('crepell',),'crippled'),
            ((' crokid',),' crooked'), ((' crosse ',' cros '),' cross '),((' crosse,',),' cross,'), (('crownes','crounes'),'crowns'),(('coroun','croune','crowne',),'crown'),
            ((' crye ',' crie '),' cry '),((' crye,',' crie,'),' cry,'), ((' Christall',' christall',' chrystall'),' crystal'),
        ((' kunnyng',),' cunning/knowledge'),
            ((' cuppe',),' cup'),
    ((' dayly',' daylie'),' daily'),
            ((' daunger ',),' danger '),
            (('derknessis','darkenesse','darknesse','darcknes','darkenes'),'darkness'),((' derknesse,',),' darkness,'),((' darknes.',),' darkness.'),((' darcke ',),' dark '),
            (('douytris','doughters'),'daughters'),
            (('Daiud',),'David'),
            ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),((' daye:',' daie:',' dai:'),' day:'),
        ((' dekenes',),' deacons'), ((' deed',),' dead'), (('Deare ',),'Dear '),((' deare ',' dere '),' dear '), ((' deeth',' deth',' derth'),' death'),
            (('disseyve','disceaue','deceave','deceiue'),'deceive'),
            ((' degre ',),' degree '),
            ((' delyte',),' delight'), (('delyueraunce','delyuerauce','deliueraunce','deliuerance'),'deliverance'),((' deliuered',' delyuerede',' delyuered'),' delivered'),((' deliuerer',),' deliverer'),((' delyuer ',' deliuer '),' deliver '),
            ((' denne ',' deen '),' den '), ((' denyede',' denyed'),' denied'),
            ((' departide',' departid'),' departed'),(('Departe ',),'Depart '),((' departe ',),' depart '),
            (('descendinge',),'descending'),(('descende ',),'descend '),
                ((' deseert ',' deserte '),' desert '),((' deseert.',' deserte.'),' desert.'),
                ((' desirith',' desyreth',' desireth'),' desires'), ((' desyred',),' desired'),
                ((' despysed',' dispiside'),' despised'),((' despyse ',' dispise '),' despise '),
                ((' distriede',' destroied',' destried'),' destroyed'),((' distrie ',' destroye ',' distroye '),' destroy '),
            ((' deuelis',' devylles',' devvyls',' deuils',' deuyls',' deuels'),' devils'),((' devyll',' deuell',' deuyll'),' devil'),
        ((' dyd ',' diden ',' dide '),' did '),((' dide,',),' did,'),
            ((' dyeth ',' dieth '),' dieth/dies '), ((' dieden ',' dyed '),' died '),((' diede,',),' died,'),((' dye.',),' die.'),
            ((' discerne:',),' discern:'), (('disciplis',),'disciples'),
                (('disdayned',),'disdained'),(('disdaine ',),'disdain '),
                ((' dysshe.',' disshe.'),' dish.'),
                (('disputacio?',),'disputation?'),(('disputyng',),'disputing'),
            ((' dyvers',' diuerse ',' diuers'),' diverse/various'), (('devided','deuided','deuyded'),'divided'), (('devorsement','deuorcemet','diuorcement'),'divorcement'),
        ((' doe ',),' do '),((' doe?',),' do?'),
            (('doctryne',),'doctrine'),
            ((' doist ',),' doest '),
            ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),((' doon;',),' done;'),
            ((' doores',' dores'),' doors'),((' doore',' dore'),' door'),
            ((' dubble.',),' double.'),((' doute,',),' doubt,'),
            ((' doue',),' dove'),
            ((' downe',' doune',' doun'),' down'),
        (('dredden','dredde'),'dreaded'),(('drede ',),'dread '), ((' dryncke',' drynke',' drynk',' drinke'),' drink'), ((' driveth',' driueth'),' driveth/drives'), ((' driue',' dryue'),' drive'),
            ((' drave',' droue'),' drove'), ((' drie ',),' dry '),((' dryed',),' dried'),
        ((' duyk ',),' duke '), ((' duste ',),' dust '), ((' duetie ',),' duty '),
        (('dwelliden','dwellide','dwellyde'),'dwelled/dwelt'),(('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
    ((' ech ',),' each '),
            ((' eerli',' erly'),' early'), ((' eares ',' eeris ',' eris '),' ears '),((' eares,',),' ears,'), ((' erthe',' erth',' `erthe'),' earth'),
            (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'), ((' easyer',),' easier'), ((' eest ',),' east '),
            ((' etynge',' eatyng'),' eating'),((' eate ',' ete '),' eat '),((' eate,',' ete,'),' eat,'),((' eate.',' ete.'),' eat.'),((' eate:',' ete:'),' eat:'),((' eate;',' ete;'),' eat;'),
        (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
        (('Egipte','Egipt'),'Egypt'), (('Egipcians',),'Egyptians'),
        (('Effraym',),'Ephraim'),
        ((' eldere ',),' elder '), (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'),
            ((' els ',),' else '),((' els,',),' else,'),
        (('Emperours',),'Emperors'),((' emperours',),' emperors'),(('Emperoure',),'Emperor'),((' emperoure',),' emperor'), ((' emptie,',),' empty,'),
        ((' ende ',),' end '),((' ende,',),' end,'),
            ((' enemyes',),' enemies'),
            (('ynough','inough'),'enough'),
            ((' entred',' entriden',' entride',' entrid'),' entered'),((' entereth',' entreth'),' entereth/enters'),((' entre ',),' enter '),
        (('Hester',),'Esther'),
        (('euangelisynge',),'evangelising'),
            (('Euen ',),'Even '),((' euene ',' euen '),' even '),(('>euen<',),'>even<'), ((' euenyng',' euening'),' evening'),((' euentid ',),' eventide/evening '), (('euen ',),'even '), # At beginning of sentence
            (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' eueremore',' euermore'),' evermore'), (('Euery',),'Every'),((' euery',),' every'), ((' euer ',),' ever '),
        ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll',' evell',' yuel'),' evil'),
        (('excedyngly','exceadingly','exceedyngly'),'exceedingly'),((' exceade ',),' exceed '), ((' excepte ',),' except '), ((' exercyse ',),' exercise '),
        ((' iyen,',),' eyes,'),((' iyen.',),' eyes.'),((' iyen;',),' eyes;'),
    ((' failinge',),' failing'), ((' fayle ',),' fail '), ((' faynte ',' faynt '),' faint '), ((' feith',' fayth'),' faith'),
            ((' falle ',),' fall '),
            ((' farre ',' fer '),' far '),((' farre.',' fer.'),' far.'),
            ((' fastynge',' fastyng',' fastinge'),' fasting'),
            ((' fadris',),' fathers'),((' fadir',),' father'), (('fatherlesse ',),'fatherless '), ((' fauoureth',),' favoureth/favours'),((' fauoured',),' favoured'),((' fauoure',),' favour'),
        ((' feare ',),' fear '), ((' feete',' fete'),' feet'), ((' fel ',),' fell '), ((' felowis',),' fellows'),((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),((' feawe.',' fewe.'),' few.'),
        ((' fielde',' feeld',' felde'),' field'), ((' feendis',),' fiends'),
            ((' figges',' fygges'),' figs'),((' fygge ',' fyge ',' figge ',' fige ',),' fig '), ((' fiytyng',),' fighting'),(('Fyght',),'Fight'),((' fyght',' fighte',' fiyte'),' fight'),
            ((' filleth ',' fylleth '),' filleth/fills '),((' fillide ',' fillid ',' fylled '),' filled '),((' fyll ',),' fill '), (('fylthynesse','filthynes'),'filthiness'),
            ((' fynde ',' finde '),' find '), ((' fynger ',' fyngur '),' finger '), ((' fynnyssher',' fynissher',' finissher'),' finisher'),
            ((' fier ',' fyre '),' fire '),((' fier,',' fyre,'),' fire,'),((' fyre:',),' fire:'),((' fier;',),' fire;'), ((' fyrste',' firste',' fyrst'),' first'),
            (('fischis','fysshes','fyshes'),'fishes'),(('fisscheris','fisshers','fysshers'),'fishers'),
            ((' fyue',' fyve',' fiue'),' five'),
        ((' flye ',' fleen ',' fle '),' flee '), ((' fleischli ',),' fleshly '),((' flesshe',' fleshe',' fleische',' fleisch'),' flesh'),
            ((' flyght ',),' flight '),
            (('flockis',),'flocks'),
                (('floude,',),'flood,'),
                (('flowith ','floweth '),'floweth/flows '),
        ((' foale ',),' foal '),
            ((' foold ',),' fold '), ((' folkis',),' folks/people'), ((' followeth',' foloweth'),' followeth/follows'),((' folowed',' folewiden',' sueden',' suede'),' followed'),((' folowe',' folow',' suen'),' follow'), (('Folowe','Folow'),'Follow'), ((' foli ',),' folly '),
            (('foolishnesse','folishnes'),'foolishness'), ((' foote ',' fote '),' foot '),
            (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '),
                ((' fourme,',' forme,'),' form,'),
                ((' fornicacion',),' fornication'),
                ((' forsooke',' forsoke',),' forsook'),((' foorth',' forthe'),' forth'),
                ((' fourtie',' fourtye',' fourti'),' forty'),
            ((' founden ',' founde ',' foond ',' foud '),' found '), ((' fowre',' foure',' fower'),' four'),
            ((' foules ',),' fowls/birds '),((' foule ',),' fowl/bird(s) '),
            (('frogges',),'frogs'),
        ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'),
            ((' freend',' frende'),' friend'), (('Fro ',),'From '),((' fro ',),' from '), ((' fruyt ',' frute ',' fruite '),' fruit '),
        ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
    (('Gayus',),'Gaius'), (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'),(('Galile.',),'Galilee.'), ((' galoun',),' gallon'),
            ((' garmentes',' garmetes'),' garments'),((' garmente ',),' garment '), (('garnisshed','garnysshed'),'garnished'),
            ((' yate',),' gate'), (('gadirid','gaderid','gaddered','gadered','gaddred'),'gathered'),((' gadere ',' gaddre ',' gadre ',' geder '),' gather '),
            ((' yaf ',' gaue ',' yauen '),' gave '),
        (('generacios',),'generations'),(('generacioun','generacion'),'generation'),((' gentyls',),' gentiles'),
        ((' goost',),' ghost'),
        ((' yyueth',' geueth'),' giveth/gives'), ((' geven',' giuen',' geuen',' youun',' youe',' yyuen'),' given'), (('Geue ','Giue '),'Give '),((' geve ',' geue ',' giue ',' yyue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'),((' yyue?',' geue?',' geve?'),' give?'),
        ((' girdil',' gerdyll',' gerdell'),' girdle'),
        (('gladli',),'gladly'),((' gladde ',),' glad '), ((' glorie',),' glory'),
        ((' goddes',' goddis'),' gods'),
            (('Goo ','Goe '),'Go '),(('Goo,','Goe,'),'Go,'),((' goe ',' goo '),' go '),((' goe.',' goo.'),' go.'),
            ((' goeth ',' goith '),' goeth/goes '), ((' goinge ',' goyng ',' gon '),' going '),
            ((' goldun ',),' golden '),((' golde ',),' gold '),((' golde.',),' gold.'),
            ((' goon ',),' gone '),
            ((' goodis',),' goods'),
            (('Gospell',),'Gospel'),((' gospell',),' gospel'),
        (('Graunte ','Graunt '),'Grant '),((' graunte ',' graunt ',' graut '),' grant '), ((' graue ',),' grave '),((' graue.',),' grave.'),
            (('grettere','gretter'),'greater'),(('greate ','grete ','greet ','grett ','gret '),'great '),(('grett.','greate.','greet.'),'great.'),
            (('greeueth ',),'grieveth/grieves '),(('greeuous','grieuous'),'grievous'),
            (('growne ',),'grown '),
            (('grounde',),'ground'), (('grutchyng',),'groutching/grudging'),
        ((' ghest',' geest',' gest'),' guest'),
            ((' guyle',),' guile'),
    ((' hadden ',' hadde '),' had '),((' hadde;',),' had;'),
            ((' hayle ',' haile '),' hail '), ((' heeris',),' hairs'),((' haire,',' heere,',' heer,'),' hair,'),((' heer ',),' hair '),
            (('halewide',),'hallowed/consecrated'),
            ((' handes',' hondes',' hoondis',' hondis'),' hands'),((' hande ',' honde ',' hoond ',' hond '),' hand '),((' hond,',' hande,'),' hand,'),
            ((' happe ',),' happen '), ((' happili',' haply'),' happily'),
            ((' hardnesse ',' hardnes '),' hardness '), ((' haruest',' heruest'),' harvest'),
            ((' hath ',),' hath/has '),
            (('Haue ',),'Have '),((' haue ',' han '),' have '),((' haue?',),' have?'), ((' havinge',' hauinge',' hauing',' hauynge',' havynge',' hauyng'),' having'),
        ((' hee ',),' he '),
            ((' heades',' heddes',' heedis'),' heads'), ((' helide',' heelid'),' healed'), ((' helthe ',),' health '), ((' hearde',' herden',' herde',' herd'),' heard'),((' herynge',' hearyng',' heryng',' hearinge',' heringe',' hering'),' hearing'),((' heareth',' herith'),' hears'),((' heare',' heere'),' hear'),
                (('Heythen',),'Heathen'),((' hethene',),' heathen'),
                ((' heyre ',' heire '),' heir '),
                ((' hertis',' hertes',' heartes'),' hearts'),((' herte ',' hert '),' heart '),((' herte,',' hert,'),' heart,'),((' herte.',),' heart.'), ((' heate',' heete'),' heat'), ((' heauens',' heuenes'),' heavens'), ((' heauen',' heuene',' heven', ' heaue'),' heaven'),
            (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), (('Hebrewe ','Hebrue ','Ebreu '),'Hebrew '),((' hebrue ',),' hebrew '),
            ((' hede ',' heede '),' heed '),
            ((' helde ',),' held '), ((' helle ',),' hell '), ((' helpe ',),' help '),
            ((' hir ',' hyr '),' her '),((' hir,',),' her,'),((' hir.',),' her.'),((' hir;',),' her;'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), (('Erodians',),'Herodians'),(('Herodes',),"Herod's"),(('Herode ','Eroude '),'Herod '), (('Eroude,',),'Herod,'),
        ((' hidde ',' hyd '),' hid '),((' hydeth ',),' hideth/hides '),
            ((' hiyeste',' hiyest'),' highest'),((' hye ',' hie ',' hiy '),' high '),
            ((' hil ',),' hill '),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',' hi:'),' him:'),((' hym?',),' him?'), (('himselfe',),'himself'),
            ((' hiryd',' hyred',' hirid'),' hired'), ((' hyreling',),' hireling'),
            ((' hise ',' hys '),' his '),
            ((' hyther',' hidder',' hidir'),' hither'),
            (('Heuites','Hiuites','Heuytes','Euey'),'Hivites'),
        ((' holdeth',),' holdeth/holds'),((' hoolde ',' holde '),' hold '),
                ((' holynesse',' holynes'),' holiness'),((' holines ',),' holiness '),((' hooli ',' holie '),' holy '),((' hooli.',' holie.'),' holy.'),
            (('honeste','honestye','honestie'),'honesty'), ((' hony',' honie'),' honey'), ((' onoure',' onour'),' honour'),(('honoure,',),'honour,'),
            ((' hornettes',),' hornets'),
            (('Hosyanna','Osanna'),'Hosanna'), ((' hoste ',' hoast ',' hoost '),' host '),
            ((' houres',),' hours'),((' houre ',),' hour '), ((' housis ',),' houses '),((' housse ',' hous ',' hows '),' house '),((' housse',),' house'),((' hous,',),' house,'), (('houssholde','housholde'),'household'),
            ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
        ((' hundrid',),' hundred'), ((' hungren',),' hungering'),((' hungride',' hungred',' hugred'),' hungered'),((' hungur',' honger'),' hunger'), ((' hurte ',),' hurt '), (('husbande','hosebonde'),'husband'),
        ((' hypocrisie',' ypocrisye'),' hypocrisy'),
    (('Y ',),'I '),(('Y,',),'I,'),(('Y;',),'I;'),
        ((' Yd',),' Id'), ((' idel ',),' idle '), ((' ydols',),' idols'),
        (('Yf ',),'If '),((' yff ',' yf '),' if '), ((' `ymage',' ymage'),' image'), (('Ys ',),'Is '),((' ys ',),' is '), ((' yssue',),' issue'),
        (('encreased',),'increased'), (('indignacioun',),'indignation'), ((' inheret ',' inherite '),' inherit '), (('interpretacion',),'interpretation'),(('interprete ',),'interpret '),
        (('immediatelye','immediatly'),'immediately'),
        (('enclyned',),'inclined'), (('inuention',),'invention'),
        ((' yron',),' iron'),
        (('Yt ',),'It '),((' yt ',),' it '),
    (('Ielous',),'Jealous'),((' ielous',' gelous'),' jealous'), ((' ioperdy',),' jeopardy'),
        (('Iorney',),'Journey'),(('iourney',),'journey'),
            ((' ioyous',),' joyous'),((' ioye ',' ioy '),' joy '),
        ((' demyde ',),' judged '), (('iudgement','iudgment'),'judgement'),((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'), ((' iust ',),' just '),
    ((' keperis',),' keepers'),((' keepeth ',' kepith ',' kepeth '),' keepeth/keeps '),((' keepe ',' kepe '),' keep '),
            ((' keyes',' keies'),' keys'),((' kaye ',' keye '),' key '),
        ((' killiden',' kylled',' kyllid'),' killed'),((' kyll ',),' kill '),((' kyll.',),' kill.'),
            ((' kinrede',),' kindred'), ((' kyndes',' kindes'),' kinds'),((' kynde ',' kyn '),' kind '), (('kingdome','kyngdoom','kyngdome','kyngdom'),'kingdom'), ((' kynges',' kyngis',' kinges'),' kings'),((' kynge ',' kyng '),' king '),((' kynge,',' kyng,'),' king,'),((' kynge.',' kyng.'),' king.'), ((' kynysman',' kynesman',' kynsman'),' kinsman'),((' kynnysmen',),' kinsmen'), ((' kynne',),' kin'),((' kyn,',),' kin,'),
            ((' kiste ',' kyssed '),' kissed '),
        (('knewest','knewen','knewe'),'knew'),
        (('knowith ','knoweth ',),'knoweth/knows '),(('knowyng',),'knowing'), (('knowlege',),'knowledge'), (('knowne','knowun','knowen'),'known'), (('Knowe',),'Know'),((' knowe',' woot'),' know'),
    ((' labor',),' labour'), ((' lomb ',' lambe ',' labe '),' lamb '),(('Lambe',),'Lamb'), ((' lastynge',),' lasting'),
            ((' lande ',' londe ',' lond ',' lode '),' land '),((' lande,',' londe,',' lond,'),' land,'),((' loond.',' lande.',' londe.',' lond.'),' land.'),((' lande:',),' land:'),((' lande;',' londe;',' lond;'),' land;'),
            ((' laste ',),' last '),
            ((' laye ',),' lay '), ((' layed',' layde',' leiden', ' leyd',' layd'),' laid'),
            ((' leeueful',' leueful',' laufull',' lawfull'),' lawful'), (('Lawe.',),'Law.'),((' lawe ',),' law '),((' lawe,',),' law,'),((' lawe.',),' law.'),
        (('ledith','ledeth'),'leadeth/leads'),((' lede ',),' lead '), (('learnyng','learninge','lernynge'),'learning'),((' learne ',' lerne '),' learn '),(('Learne ','Lerne '),'Learn '), ((' leest',),' least'), ((' leeues',' leaues',' leves'),' leaves'), ((' leeue ',' leaue ',' leue ',' leve '),' leave '), ((' leauen',' leuen',' leven'),' leaven'),
            ((' ledde ',' leden '),' led '),
            ((' leften',' leeft',' lefte'),' left'),
            (('Leuite',),'Levite'), (('Leuy.',),'Levi.'),
        (('lyberte','libertie'),'liberty'),
            ((' lyes ',),' lies '),
            ((' lyffe',' lyfe',' lijf'),' life'),
            ((' leityngis',' lyghtnynges',' lightnynges'),' lightnings'), (('Liyt ',),'Light '),((' lyght',' liyt'),' light'),
            (('Lykewyse',),'Likewise'),(('lykewyse','likewyse'),'likewise'), ((' lyke',' lijk',' lijc'),' like'),
            ((' lynage ',),' lineage '),
            ((' litil',' lytell',' lytle',' litle'),' little'),
            ((' liueth',' lyueth'),' liveth/lives'),((' liues',' lyues'),' lives'),((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),((' liue ',' lyue '),' live '),((' liue,',' lyue,'),' live,'),
        (('Loe,',),'Lo,'),
            ((' looues',' loaues'),' loaves'),
            ((' locustes',),' locusts'),
            ((' loynes',' loines'),' loins'),
            ((' longe ',),' long '),((' longe,',),' long,'),
            ((' lokide',' loked'),' looked'),((' loketh',),' looketh/looks'),(('lokynge',),'looking'),(('Lokyng ',),'Looking '),(('Loke ',),'Look '),((' looke ',' loke '),' look '), ((' loosyng',' loosinge'),' loosing'),
            ((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),
            (('Loth',),'Lot'),
            ((' loude ',),' loud '),
            ((' louede',' loued',' louyde'),' loved'),((' loveth',' loueth'),' loveth/loves'),((' lovest',' louest'),' lovest/love'),((' louen ',' loue '),' love '),((' loue.',),' love.'),
    ((' maad',),' made'),
            ((' maydens',),' maidens'),((' mayden ',),' maiden '), ((' maydes',),' maids'),((' mayde ',' maide '),' maid '),((' mayde,',),' maid,'), ((' maymed',),' maimed'),
            ((' makynge',),' making'),((' makere ',),' maker '),
            ((' mannus',),' man\'s'),((' ma ',),' man '), ((' mankynde',),' mankind'),((' mankinde,',),' mankind,'), ((' manere',' maner'),' manner'), ((' manye ',),' many '),
            ((' mariage',),' marriage'), ((' maried',),' married'), (('marueyled','marueiled','merveled','marueled','merveyled','marveled'),'marvelled'), (('Maryes',),"Mary's/Maria's"),(('Marye','Marie'),'Mary/Maria'),
            (('Maister','Maistir'),'Master'),((' maister',),' master'),
            ((' maiestie',),' majesty'),((' mayest',' mayste',' mayst',' maiest'),' mayest/may'),((' maye ',' maie '),' may '),((' maye.',),' may.'),(('Maye ',),'May '),
        ((' mee ',),' me '),
            ((' meanynge',),' meaning'), ((' mesure',),' measure'),
                ((' `metis ',' metis '),' meats '),((' meate ',),' meat '),
            ((' mekely',),' meekly'),((' meeke ',' meke '),' meek '),((' meeke:',' meke:'),' meek:'), ((' metinge',' metyng'),' meeting'),((' meete ',' mete '),' meet '),((' meete,',' mete,'),' meet,'),((' meete:',' mete:'),' meet:'), (('meekenes','mekenes','meknes'),'meekness'),
            ((' mendynge',' mendyng',' mendinge'),' mending'),
            ((' mercyfull ',' mercifull '),' merciful '),((' mercyfull:',' mercifull:'),' merciful:'),((' merci ',),' mercy '),
            (('messangeris',),'messengers'),(('messauger',),'messenger'),
        (('Michah ','Micha '),'Micah '),
            (('Madianites',),'Midianites'),((' myddil',),' middle'),
            ((' myghty ',' mightie ',' miyti '),' mighty '),((' myyte ',' myght ',' mighte '),' might '),
            ((' mylke ',' milke '),' milk '),((' mylke,',' mylk,',' milke,'),' milk,'),((' milke:',),' milk:'), (('mylstone','milstone'),'millstone'),
            ((' myndes',' mindes'),' minds'),((' mynde',),' mind'), ((' myne ',' myn '),' mine '), (('ministred','mynistred','mynystriden'),'ministered'),((' mynyster',' mynister'),' minister'),
            ((' myracles',),' miracles'),
        ((' mony',),' money'), ((' monethe',' moneth'),' month'),
            ((' moone ',' mone '),' moon '),
            (('Mardochee','Mardocheus'),'Mordecai'),
                (('Moreouer','Morouer'),'Moreover/What\'s_more'),(('morouer',),'moreover/what\'s_more'), ((' moare ',' mowe '),' more '),
                ((' morninge',' mornynge',' mornyng',' morewtid',' morewe'),' morning'),
                ((' morowe',' morow'),' morrow'),
            (('Moises','Moyses'),'Moses'), ((' moost ',),' most '),
            ((' moder ',' modir '),' mother '),
            ((' mouthes ',),' mouths '), ((' mountaynes',' moutaynes',' mountaines'),' mountains'),((' mountayne',' mountaine'),' mountain'), ((' moute ',),' mount '), ((' mornen ',' mourne ',' morne '),' mourn '),((' mornen,',' mourne,',' morne,'),' mourn,'),((' mornen:',' mourne:',' morne:'),' mourn:'),
            ((' mouyng',),' moving'),((' moued',),' moved'),((' moue ',),' move '),
        ((' myche',' moche',' moch',' muche'),' much'), (('multiplie ',),'multiply '), (('murthurers',),'murderers'),(('murthurer',),'murderer'),
    (('Naomy','Naemi'),'Naomi'),
            ((' naciouns',' nacions'),' nations'), ((' natiue',),' native'),
        ((' neere ',' neare '),' near '),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),
            ((' nedeful',),' needful'),((' nedes',),' needs'),((' neede ',' neade ',' nede '),' need '),
            ((' neiyboris',' neghboures',' neghbours',' neyghbours'),' neighbours'),((' neiybore',' neyghbour',' neghboure'),' neighbour'), (('Nether ',),'Neither '),((' nether',' nethir'),' neither'),(('(nether',),'(neither'),
            ((' nettes',' nettis'),' nets'),
            (('Neverthelesse ','Neuerthelesse ','Neuertheles '),'Nevertheless '),(('Neuertheles,',),'Nevertheless,'), ((' neuere',' neuer'),' never'),
            ((' newe ',),' new '),
            ((' nexte',),' next'),
        ((' neer ',' nyer ',' nier '),' nigher/nearer '),((' nyy ',' nye '),' nigh/near '),((' nyy.',' nye.'),' nigh/near.'), ((' nyyti',' nyyt',' nyght',' nighte'),' night'),
            ((' nyenth',' nynthe',' nynth'),' ninth'),
        ((' noyse ',),' noise '),
            ((' ner ',' ne '),' nor '), (('northwarde',),'northward'),
            (('nothinge','nothyng'),'nothing'),
            ((' nouyt',),' nought/nothing'),
        (('Nowe ',),'Now '),((' nowe ',),' now '),
        (('numbred',),'numbered'),(('noumbre','nombre','nomber'),'number'),
    ((' oke ',' ook '),' oak '), ((' othe ',' ooth '),' oath '),
        ((' obteyne ',' obteine '),' obtain '),
        ((' of;',),' off;'), ((' offende ',),' offend '),((' offende,',),' offend,'), ((' offerynge',' offring'),' offering'), ((' offred',),' offered'),
        ((' oyle ',),' oil '),((' oyle,',' oile,'),' oil,'), ((' oyled',),' oiled'), ((' oynement',' oyntment'),' ointment'),
        ((' eeld ',' eld ',' olde '),' old '),((' eeld,',' olde,'),' old,'),
            (('Oliuete','olivete'),'Olivet'),(('Olyues','Oliues'),'Olives'),((' olyues',),' olives'), (('Oliue',),'Olive'),((' olyue ',' olyve ',' oliue '),' olive '),
        ((' onys,',),' once,'), ((' oon ',),' one '),((' oon.',),' one.'), ((' onely ',' `oon '),' only '),
        ((' openyde',' openyd'),' opened'),((' openeth',' openith'),' openeth/opens'),
            ((' opynyouns',),' opinions'),
            ((' oppressith',),' oppresses'),((' oppressid',),' oppressed'),((' oppresse ',),' oppress '),((' oppressio ',),' oppression '),((' oppressour',' oppresser'),' oppressor'),
        ((' ordayned',' ordeined',' ordeynede',' ordeyned'),' ordained'),((' ordayne ',),' ordain '),
        (('Othere','Othir','Wother'),'Other'),((' othere',' othir', ' tothir'),' other'),
        ((' oure ',),' our '),
            ((' outwarde',),' outward'), ((' oute.',),' out.'),
        ((' ouer ',),' over '), (('ouercommeth','ouercometh'),'overcometh/overcomes'), ((' ouercome',),' overcome'),
        ((' awne ',' owne '),' own '),
        ((' oxun',),' oxen'),
    ((' paynes',),' pains'),((' payne',),' pain'),
            ((' paulsie',' palsie',' palsye'),' palsy'),
            ((' parablis',),' parables'), ((' partynge',),' parting'), ((' parts',' parties',' partis'),' parts'),((' parte ',),' part '),
            (('Passeouer','Passouer'),'Passover'),((' passiden',' passide'),' passed'),((' passynge',),' passing'),((' passe ',),' pass '),((' passe?',),' pass?'),((' passe:',),' pass:'),
            ((' pathes',' paches',' pathhis'),' paths'), ((' pacience',),' patience'),
            (('Pavl',),'Paul'),
            ((' paye ',),' pay '),
        (('Pees',),'Peace'),((' pees',),' peace'),
            (('penaunce',),'penance'), ((' penie ',' peny '),' penny '),((' penie,',' peny,'),' penny,'),
            (('puplis',),'peoples'),((' `puple',' puple',' pople'),' people'),
            (('perceiued','perceaved','perceaued'),'perceived'),(('Perceave','Perceiue'),'Perceive'),((' witen',' perceiue'),' perceive'),
                ((' perfaicte ',),' perfect '), (('perfourmeth ','performeth '),'performeth/performs ' ),((' perfourme ',' performe '),' perform '),
                ((' perel ',),' peril '),((' perel.',),' peril.'), ((' perische',' perisshe',' perishe'),' perish'),
                (('Pherezites','Pheresites'),'Perizzites'),
                (('persecucioun','persecucion'),'persecution'),
                (('perteyneth',),'pertaineth/pertains'),(('perteyninge','parteyning','pertayninge'),'pertaining'),(('pertayne ',),'pertain '),
                (('peruert ',),'pervert '),(('perverteth ','peruerteth '),'perverteth/perverts '),
            (('Petir',),'Peter'),
        (('Pharao ','Farao '),'Pharaoh '),(('Pharao,','Farao,'),'Pharaoh,'), (('Fariseis','Farisees','Pharises','pharisees','pharises'),'Pharisees'), (('Philippe',),'Philip'),
        ((' peaces',' peeces',' peces'),' pieces'), ((' pearced',),' pierced'),
            ((' pylgrym',),' pilgrim'),
            ((' pyned',),' pined'),
            ((' pytte',' pytt',' pyt'),' pit'), ((' reuthe',' pitie ',' pite '),' pity'),
        (('playnely','playnly','plainely'),'plainly'), ((' playne ',' plaine '),' plain '),
            ((' plese ',),' please '), ((' pleside',' plesid'),' pleased'), (('plentyful',),'plentiful'),((' plente ',),' plenty '),
            ((' plucke ',),' pluck '),
        ((' poole ',),' pool '), ((' poore ',' povre ',' pore '),' poor '),
            (('possessyoun','possessioun'),'possession'),(('possesse ',),'possess '),
            ((' pottere',),' potter'),
            ((' powdir',),' powder'),
        (('praysed',),'praised'), (('preyeden','preiede','praied'),'prayed'),(('preier',),'prayer'),(('preyng',),'praying'),((' preye ',' praye '),' pray '),((' praye:',),' pray:'),((' praye.',),' pray.'),
            (('prechiden','prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ','preache '),'preach '),
                (('preserue',),'preserve'),
                (('preuent',),'prevent'),
            (('prijs ',),'price '), (('preestis','prestis','prestes','priestes'),'priests'),(('Priestes','Prestes'),'Priests'),(('prieste','preste','preest','prest',),'priest'), (('princis','prynces'),'princes'),(('prynce ',),'prince '),
                (('prisouneris','presoners'),'prisoners'), (('pryuatly',),'privately'),
            (('proceaded',),'proceeded'),
                (('proffet',),'profit'),
                (('promysed','bihiyten'),'promised'),
                (('Prophetes',),'Prophets'),(('profetis','prophetes'),'prophets'), (('Prophete',),'Prophet'),((' prophete ',),' prophet '),((' prophete,',),' prophet,'),((' prophete.',),' prophet.'),((' prophete?',' profete?'),' prophet?'),
                (('proude',),'proud'),
                ((' preued',),' proved'),((' proue ',' preue '),' prove '), (('prouerbe',),'proverb'), (('prouynces','prouinces'),'provinces'),
        (('publysshed',),'published'),
            ((' punishe ',),' punish '),
            ((' pourses',),' purses'), (('Sue ',),'Pursue '),
            ((' putteth ',),' putteth/puts '), ((' puttide ',),' put '),
    (('quenchid','queched'),'quenched'), (('questioun',),'question'),
        (('quike',),'quick/alive'),
    (('Rabi',),'Rabbi'), ((' raysed',),' raised'),((' reise',' reyse',' rayse'),' raise'),
        ((' redi ',),' ready '), ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'),
            ((' resseyueth',' receaveth',' receaueth',' receiueth'),' receives'),((' resseyueden',' resseyuede',' receaved',' receaued',' receiued'),' received'),((' resseyue',' receave',' receaue',' receiue'),' receive'), (('recompence',),'recompense'), ((' recorde ',),' record '), (('recouering',),'recovering'),
            ((' redde ',' reed '),' red '),
            (('refrayne ',),'refrain '),
            (('regardest',),'regard'),
            ((' raygne ',),' reign '),
            ((' reioyce ',' reioyse '),' rejoice '),
            ((' religioun',),' religion'),
            (('remayneth ','remaineth '),'remaineth/remains '),(('remayned',),'remained'),(('remaynynge','remayninge','remayning'),'remaining'),(('remayne','remaine'),'remain'),
                (('remembraunce',),'remembrance'),
                (('remyssion','remissioun'),'remission'),
                ((' remooue ',),' remove '),((' remoued ',),' removed '),
            (('repentaunce',),'repentance'),
                ((' reproued',),' reproved'), ((' reprooue ',' reproue '),' reprove '),
                ((' reptils',),' reptiles'),
            ((' reste ',),' rest '), (('ressurreccioun','resurreccion'),'resurrection'),
            ((' returne ',),' return '),
            (('reuerence',),'reverence'),
            ((' rewarde ',),' reward '),((' rewarde.',),' reward.'),
        ((' riche ',),' rich '),
            ((' ryght ',' riyt '),' right '),((' riyt.',),' right.'), (('riytwisnesse ','rightewesnes ','rightousnesse ','righteousnes '),'righteousness '),(('riytwisnesse,','rightewesnes,','righteousnesse,','righteousnes,'),'righteousness,'),(('riytwisnesse:','rightewesnes:','righteousnes:'),'righteousness:'),((' ryghteous',),' righteous'),
            ((' risith',),' riseth/rises'), ((' ryse ',),' rise '),
            ((' ryuer',' riuer'),' river'),
        ((' rocke ',),' rock '),
            ((' rodde ',),' rod/staff '),((' rodde:',),' rod/staff:'),
            ((' roofe',' rofe'),' roof'), ((' roume',' rowme'),' room'), ((' rootis',),' roots'),((' roote',' rote'),' root'),
            ((' roos ',),' rose '),
            ((' rounde ',),' round '),
        (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
    (('Sabbathes',),'Sabbaths'),((' sabatys',),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabat',' saboth'),' sabbath'),
            (('sackecloth',),'sackcloth'), ((' sacrifise',),' sacrifice'),
            (('Saduceis','Saduces','Sadduces'),'Sadducees'),
            ((' saaf',),' safe'),
            ((' seyden',' seiden',' seide',' seid',' sayde',' sayd',' saide', ' seien'),' said'),
            ((' saltid',),' salted'),
            (('Sampson',),'Samson'),
            ((' sondes',),' sands'),((' sande',),' sand'),
            ((' sate ',),' sat '), (('Sathanas','Sathan'),'Satan'), ((' satisfie ',),' satisfy '),
            ((' saued',),' saved'),((' saue ',),' save '),((' sauyng',' sauinge',' sauing',' savinge'),' saving'), ((' sauery',),' savoury'),
            ((' sawe ',' sai ',' sayn ',' siy '),' saw '),
            ((' seist',),' sayest'),((' sayege',' sayinge',' saynge'),' saying'), ((' seith ',' sayth '),' saith/says '), ((' seie ',' seye ',' saye ',' saie '),' say '),((' seie,',' saye,'),' say,'),((' seie:',' saye:'),' say:'),
        ((' scornefull',),' scornful'),
            (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
        ((' sealeth',),' sealeth/seals'), (('seesyde ' ,'seeside ',),'seaside '), ((' seete ',' seet ',' seate '),' seat '),((' seate.',),' seat.'),
            ((' secounde ',' seconde '),' second '),
            ((' seynge',' seinge',' seyng',' seing'),' seeing'),(('Se ',),'See '),((' seiy ',' se '),' see '),((' se.',),' see.'), ((' seede ',' sede '),' seed '), ((' sekynge',),' seeking'),((' seken ',' seeke ',' seke '),' seek '), ((' semeth',),' seemeth/seems'),((' semen ',' seeme ',' seme '),' seem '), ((' seyn ',' seene ',' sene '),' seen '),((' seyn,',' seene,',' sene,'),' seen,'),
            ((' silfe ',' silf ',' selfe '),' self '),((' selfe,',),' self,'),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'), ((' silleris',),' sellers'), ((' selues',),' selves'),
            ((' symnell ',' symnel '),' semnel/small_loaf '),
            ((' sendeth',' sendith'),' sendeth/sends'),((' sende ',),' send '), ((' senten ',' sente '),' sent '),
            ((' sermoun',),' sermon'),
                (('Serue ',),'Serve '),((' serue ',),' serve '),((' serued',' serueden'),' served'), (('seruauntis','seruauntes','servauntes','seruants','servantes'),'servants'),((' seruaunt',' servaunt',' seruant',' seruaut',' servaut'),' servant'), ((' seruice ',' seruyce '),' service '),
            ((' settide ',' sette '),' set '),
            (('seuenthe ','seuenth '),'seventh '),(('Seuene ','Seuen '),'Seven '),((' seuene ',' seuen ',' seue '),' seven '),
        ((' schal ',' shal ',),' shall '),((' schalt ',),' shalt '), ((' shappe ',),' shape '),
            (('Sche ',),'She '),((' sche ',' shee '),' she '), (('sheddinge',),'shedding'), (('sheepefolde','sheepfolde','shepefolde'),'sheepfold'), ((' scheep ',' sheepe ',' shepe '),' sheep '),((' scheep,',' sheepe,',' shepe,'),' sheep,'),((' scheep)',' sheepe)',' shepe)'),' sheep)'), (('scheepherdis',),'shepherds'),(('scheepherde','shepeherde','shepherde','sheephearde','shephearde','shepheard'),'shepherd'),
            (('schyneth','shyneth'),'shineth/shines'),(('schynynge',),'shining'), ((' shippes',),' ships'),((' shyppe',' shyp',' shippe',' schip'),' ship'),
            ((' shooes',),' shoes'),((' shue',),' shoe'),((' schoo.',),' shoe.'), ((' shoore',),' shore'), (('shouldest','schulen','schuldist'),'should'),((' schulden ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '), (('shoute ','showte '),'shout '), (('shewyng','shewinge','shewing'),'showing'),(('schewide','schewid','shewed'),'showed'),((' schewe ',' shewe '),' show '),
        (('sijknessis',),'sicknesses'),((' syknesse',' sicknesse',' sickenes'),' sickness'),((' sicke',' sijk'),' sick'),
            ((' syde ',),' side '),((' syde.',),' side.'),((' syde:',),' side:'),
            ((' syght ',' sighte ',' siyt '),' sight '),((' sighte,',),' sight,'), ((' signes',),' signs'),((' signe ',),' sign '),
            ((' siluer',),' silver'),
            (('Synay',),'Sinai'),
            (('Symount','Symon'),'Simon'), ((' simulacion',),' simulation'),
            ((' sence ',' sithen '),' since '), ((' synners',' synneris'),' sinners'),((' synner',),' sinner'), ((' synfull',' synful'),' sinful'),((' sinnes',' synnes'),' sins'),((' synnede',' synned'),' sinned'),((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),
            ((' sistris',' systers'),' sisters'),((' sistir',),' sister'),
            ((' sittynge',' syttyng',' sittinge'),' sitting'),((' sitten ',' sitte ',' syt '),' sit '), ((' liggynge',),' situated'),
            ((' sixte ',' sixt '),' sixth '), ((' sixe ',),' six '),
        ((' skynne ',' skyn ',' skinne '),' skin '),((' skynne,',' skyn,'),' skin,'),
        ((' slayne',' slayn',' slaine'),' slain/killed'),((' sleye ',' slaye ',' sle '),' slay/kill '),((' sle.',),' slay/kill.'), (('sclaundrid',),'slandered/disgraced'),
            ((' slepith',),' sleeps'),((' slepte ',),' slept '),(('Sleepe ','Slepe '),'Sleep '),((' sleepe',' slepe'),' sleep'), ((' slewe ',' slue '),' slew '),
            ((' slyme ',),' slime/mud '),
        ((' smale ',),' small '),
            ((' smyte ',),' smite '),
        ((' sokettes',' sockettes'),' sockets'),((' sokett',),' socket'),
            (('Sodome ','zodom '),'Sodom '),
            ((' soiourne',),' sojourn'),
            ((' solde ',),' sold '), ((' solitarie',),' solitary'),
            ((' summe ',),' some '), (('somwhat','sumwhat'),'somewhat'),
            ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,','Sone,'),'Son,'),
            ((' sorewis',' sorowes'),' sorrows'),((' sorewe ',),' sorrow '),((' sorowe,',),' sorrow,'), ((' sory ',),' sorry '),
            ((' souyten',),' sought'), ((' sounde',),' sound'), (('southwarde',),'southward'), (('souereynes',),'sovereigns'),
        ((' spette ',' spate '),' spat '),
            (('speakynge','spekynge','speakinge','spekinge','speakyng'),'speaking'),(('spekith ','speaketh '),'speaketh/speaks '),((' speake',),' speak'),
            ((' spyed',),' spied'), ((' spirites',' spiritis',' spretes'),' spirits'),(('Spiryt',),'Spirit'),((' spirite',' sprete'),' spirit'), (('spotil','spetil','spettle'),'spittle'),
            ((' spoyled',),' spoiled'), ((' spak ',),' spoke '),
            ((' spredden ',' sprede ',' spred '),' spread '),
        ((' staffe ',),' staff '), (('stondinge','standyng','stodinge'),'standing'),((' stondith',),' standeth/stands'),((' stande ',' stonde '),' stand '),((' stonde.',),' stand.'), ((' starre',),' star'),
            ((' steale.',),' steal.'),(('Steppe ',),'Step '),
            ((' styffnecked',' styfnecked',' stiffnecked'),' stiff-necked'), ((' styll',),' still'),
            ((' stockis',),' stocks'),
                ((' stomacke ',' stomac '),' stomach '),
                ((' stoonys',),' stones'),((' stoone',' stoon'),' stone'),
                ((' stoode',' stonden',' stoden',' stode'),' stood'), ((' stoupe',' stowpe'),' stoop'),
                ((' storme,',),' storm,'),
            (('strayght','streyght'),'straight'), (('straunger',),'stranger'),(('straunge ',),'strange '),
                ((' streames',' stremys'),' streams'), (('streetes',),'streets'),(('streete','streate','strete'),'street'), ((' strewiden ',' strawed ',' strowed '),' strewed '),
                ((' strijf',' stryfe'),' strife'),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'),(('stryve','stryue','striue'),'strive'),
                ((' stronge ',),' strong '),
            (('stubborne',),'stubborn'), (('stumbleth','stombleth','stomblith'),'stumbles'),
        (('subiection','subieccion'),'subjection'),((' suget',),' subject'), (('substaunce',),'substance'), ((' subtill ',' subtil '),' subtle '),
            ((' soch ',' suche ',' siche ',' sich '),' such '),((' suche.',),' such.'), ((' soucke ',' sucke '),' suck '),
            (('suffrith',),'suffereth/suffers'),((' suffride',' suffred'),' suffered'),(('Suffre ',),'Suffer '),((' suffre ',),' suffer '), (('suffysed','suffised'),'sufficed'),
            (('Sommer',),'Summer'),((' sommer ',' somer '),' summer '),
            ((' sunne ',),' sun '),
            (('superscripcion',),'superscription'), ((' soper ',),' supper '), (('supplicacion',),'supplication'),
            (('Shushan','Susan'),'Susa'), # What about Susanna in NT?
        (('swete ',),'sweet '), (('sworde',),'sword'),
        (('synagoge',),'synagogue'),
    (('tabernaclis',),'tabernacles/tents'),
            ((' takun',),' taken'), ((' takynge',),' taking'),(('Takyng',),'Taking'),
            ((' talentis',),' talents'), ((' talke ',),' talk '),((' talke.',),' talk.'), ((' talkinge ',),' talking '),
            ((' taried',),' tarried/waited'),(('Tarye ','Tary '),'Tarry/Wait '),((' tarry ',' tarie ',' tary '),' tarry/wait '),
            (('taskemasters:',),'taskmasters:'), ((' taist ',),' taste '),
            ((' tauyte',),' taught'),
        (('techyng','teching'),'teaching'),(('teacheth','techith'),'teacheth/teaches'),((' teachest',' teache',' techist',' teche'),' teach'),
            (('temptacioun','temptacion','teptacion','tentation'),'temptation'), (('temptiden','temptid'),'tempted'), ((' tempte ',' tepte '),' tempt '),
            ((' tenauntes',),' tenants'), ((' tendre',' teder'),' tender'), ((' tentes',),' tents'), ((' tenthe',),' tenth'),
            (('testifie ','testifye ','testyfye '),'testify '), (('testimoniall',),'testimonial'),
        (('thankes','thakes'),'thanks'),(('thanke ',),'thank '), (('Thilke ',),'That '),((' thilke ',),' that '),
            ((' theyr ',),' their '),
                ((' hem ',),' them '),((' hem,',' the,'),' them,'),((' hem.',' the.'),' them.'), (('themselues',),'themselves'), (('Thanne ',),'Then '),((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),
                ((' therynne ',),' therein '), ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
                ((' therfore',' therfor'),' therefore'),(('Therfor ',),'Therefore '), (('therto',),'thereto'), (('Thei ',),'They '),((' thei ',),' they '),
            ((' thieues',' theeues',' theves',' theues'),' thieves'),((' thiefe',' theefe',' theef',' thefe'),' thief'), ((' thyne ',' thine '),' thine/your '), ((' thynne ',),' thin '), ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'),
                ((' thridde',' thyrde',' thirde'),' third'), ((' thristen',),' thirsting'),((' thyrst ',' thurst ',' thirste '),' thirst '),((' thirste,',),' thirst,'), ((' thretti ',' thirtie '),' thirty '),
            (('thwong',),'thong'), ((' thou ',),' thou/you '), ((' thouy ',),' though '), ((' thouytis ',' thoughtes '),' thoughts '),((' thouyte ',),' thought '),((' thoughte:',),' thought:'), (('thousynde','thousande'),'thousand'),
            ((' threed',),' thread'), (('thretenede',),'threatened'), ((' thre ',),' three '),
                ((' throte.',),' throat.'), ((' trone ',),' throne '), (('thorowout',),'throughout'), (('thorow ','thorou '),'through '),(('thorow,',),'through,'), (('throwen',),'thrown'),
            (('thundringes','thundrings','thondringes','thundris'),'thunderings'),(('thundryng',),'thundering'),(('thounder','thonder','thuder'),'thunder'),
        ((' tydynges',' tidynges',' tydinges',' tydings'),' tidings/news'),(('Tydinges',),'Tidings'), ((' tyde',),' tide'),
            ((' tyed ',),' tied '), ((' tiel ',),' tile '),
            ((' tyll ',),' till '),
            ((' tyme',),' time'),
        (('togidir','togidere','togidre','togedder'),'together'),
            ((' tokene ',),' token '),
            ((' tolde ',),' told '),
            ((' tungis',' tunges',' toges'),' tongues'),((' tonge ',),' tongue '),((' tonge,',),' tongue,'),((' tonge.',' tunge.'),' tongue.'),
            ((' tokun ',' toke ',' tooke '),' took '),
            ((' turment ',),' torment '),
            ((' touche ',),' touch '),
            ((' townes',' tounes'),' towns'),((' towne ',' toune '),' town '),
        (('ttasfigured',),'transfigured'), ((' trauelid',),' travelled'),
            (('treasurie','tresorie'),'treasury'), ((' tre ',),' tree '),((' tre,',),' tree,'), (('trespasse ',),'trespass '),
            (('trybe ',),'tribe '),(('trybes',),'tribes'), (('tribulacioun',),'tribulation'), ((' tryed',),' tried'),
            ((' truble ',),' trouble '),
            (('Treuli','Sotheli'),'Truly'),(('truely','treuli','sotheli'),'truly'), (('sothfast',),'truthful'), ((' trewthe',' trueth',' treuthe',' verite'),' truth'),
            ((' trye ',),' try '),
        ((' turneden',' turnede'),' turned'),(('Turne ',),'Turn '),((' tourne ',' turne '),' turn '),((' turne,',),' turn,'),
        (('twolue','twelue'),'twelve'), (('twentie ','twenti ','twentye '),'twenty '),
            ((' twyse',' twise'),' twice'), (('twynnes','twinnes','twyns'),'twins'), ((' twei ',' tweyne ',' tweyn ',' twey ', ' twaine '),' two '),
    (('vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'), (('vnbeleuing','vnbeleuynge'),'unbelieving'),
        (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'),
            ((' vnderstande',' vnderstand'),' understand'),(('Vnderstonde',),'Understood'),(('vnderstonde','vnderstoode','vnderstode','vndirstood'),'understood'), ((' vnder',' vndur'),' under'), ((' vndon.',),' undone.'),
            (('vnfeithful',),'unfaithful'), (('vnfensed',),'unfenced'),
            (('vnleauened','vnleuened'),'unleavened'), ((' vnloose',),' unloose'),
            ((' vnsauerie',' unsauery',' unsavery'),' unsavoury'),
            ((' vntieden',),' untied'), (('Untyll ','Vntill '),'Until '),(('vntill','vntyll'),'until'), (('Vnto ',),'Unto '),((' vnto',),' unto'), ((' vntiynge',),' untying'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon ',' upo ',' apon '),' upon '),(('Vpon ',),'Upon '),
        ((' vs',),' us'),
            ((' vn',),' un'), # Special case for all remaining un- words
            ((' vp',),' up'), # Special case for all remaining up- words
    ((' valey',),' valley'), (('vanisshed','vanysshed'),'vanished'), (('vanyte ','vanitie '),'vanity '),
        ((' vayle',' vaile',' vail'),' veil'),
            (('Ueryly','Verely','Veryly'),'Verily/Truly'),((' verely',' veryly'),' verily/truly'),
            ((' vessell',),' vessel'),
        (('vyneyarde','vynyarde','vynyerd','vineyarde'),'vineyard'), ((' vertu',),' virtue'), ((' visite ',' vyset '),' visit '),
        ((' voyce',' vois'),' voice'), ((' voyde',' voide'),' void'),
    ((' wayte ',),' wait '),((' waite,',),' wait,'),
        (('walkynge','walkinge'),'walking'),((' walkid',),' walked'),((' walke ',),' walk '),((' walke,',),' walk,'),
             ((' warres',),' wars'),((' warre ',),' war '),((' warre,',),' war,'), ((' warme,',),' warm,'),
             ((' waisschide',' wasshed',' wesshed'),' washed'),((' waisschun',' waischun'),' washing'),((' wesshe ',' washe '),' wash '),((' wassche;',),' wash;'),
             ((' watred',),' watered'),((' watris',),' waters'),((' watir',' watre'),' water'),
                ((' wayes',' weies'),' ways'),((' waye ',' weie ',' weye '),' way '),((' waye,',' weie,',' weye,'),' way,'),((' waye.',' weie.',' weye.'),' way.'),((' waye:',' weie:',' weye:'),' way:'),
        ((' wee ',),' we '),
            ((' weryed',' weried'),' wearied'),((' weery',' wery'),' weary'),
            ((' wepe ',),' weep '),((' wepyng',),' weeping'),
            ((' welde ',),' weld '), ((' wel ',),' well '),
            ((' wenten ',' wente ',' wete ',' yeden ',' yede '),' went '),
            ((' wepte',),' wept'),
            ((' weren ',),' were '), (('westwarde',),'westward'),
        (('Whatsoeuer',),'Whatsoever'),(('whatsoeuer',),'whatsoever'),
            ((' wheete ',),' wheat '),
                (('Whanne ','Whan '),'When '),((' whanne ',' whan ',' whe '),' when '), ((' whennus ',),' whence '),
                (('Wherfore ',),'Wherefore '),
                ((' whethir',),' whether'),
            (('Whiche ',),'Which '),((' whiche ',),' which '), ((' whill ',' whyll ',' whyle '),' while '), (('whyte ','whijt '),'white '),
            ((' whoale',),' whole'), ((' whome',),' whom'),(('whomsoeuer',),'whomsoever'), (('Whosoeuer',),'Whosoever'),(('whosoeuer',),'whosoever'),
            ((' whi ',),' why '),
        (('wickednesse',),'wickedness'), ((' wickid',),' wicked'),
            ((' wyde ',),' wide '), (('widewis','wyddowes','widowes'),'widows'),(('widewe ','wyddowe ',' wydowe ','widdowe ','widowe '),'widow '),(('widewe,','widowe,'),'widow,'), (('wyldernesse','wildirnesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf'),' wife'),
            ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),((' wylt ',' wilt '),' wilt/will '),
            ((' winne ',' wynne '),' win '), ((' wyndis',' wyndes',' windes'),' winds'),((' wynde ',' wynd ',' winde '),' wind '),((' winde,',' wynd,'),' wind,'),((' winde?',),' wind?'), ((' wengis',' wynges'),' wings'), (('Wynter',),'Winter'),((' wyntir.',' wynter.'),' winter.'),
            ((' wipte',' wyped'),' wiped'),
            (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'), ((' wyse ',),' wise '),
            ((' withynne',),' within'),((' wi ',' wt '),' with '), (('widdred','wythred','wythered','wyddred'),'withered'),
                (('withouten ',),'without '), (('witnessyng',),'witnessing'),((' wytnesse ',' witnesse ',' witnes '),' witness '),((' wytnesse,',),' witness,'),
            ((' wyues',' wiues'),' wives'),
        (('Woo ','Wo '),'Woe '),((' wo ',),' woe '),
            ((' womman',),' woman'), ((' wombe',),' womb'), ((' wymmen',' wemen'),' women'),
            ((' wonne ',),' won '), (('wondriden','wondride'),'wondered'),
            ((' wordis',' wordys',' wordes'),' words'),((' worde',),' word'), ((' workes',' werkis'),' works'),((' worche ',' worke ',' werke ',' werk '),' work '),((' worke,',' werk,'),' work,'),((' worche.',),' work.'), ((' worlde',),' world'), ((' wormes ',),' worms '),((' worme ',),' worm '), (('worschipide','worshypped'),'worshipped'),(('worschipe ','worshipe '),'worship '), ((' worthie',' worthi'),' worthy'),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),
        ((' wryncles',' wrinckles'),' wrinkles'), ((' writyng',),' writing'),((' wryte ',),' write '), (('wrytten','wrytte','writun'),'written'), ((' wroote ',' wroot '),' wrote '), (('wrought','wrouyt'),'wrought/done'),
    (('Iaakob','Iacob'),'Yacob'), (('Iames','James'),'Yames/Yacob'), (('Iauan',),'Yavan'),
        (('Ye ',),'Ye/You_all '),((' ye ',' yee '),' ye/you_all '), ((' thi ',' thy '),' thy/your '), ((' youre ',),' your(pl) '),
            ((' yhe,',),' yea/yes,'), ((' yeres',),' years'),((' yeare',' yeere',' yeer',' yere'),' year'),
            (('Iehouah ',),'Yehovah '),
            (('Hierusalem','Ierusalem','Ierusale','Jerusalem'),'Yerusalem'),
            (('Iesus',),'Yesus/Yeshua'),(('Iesu ',),'Yesu '),(('Iesu.',),'Yesu.'),
            ((' yit ',),' yet '),
            (('Iewry ',),'Yewry '), (('Iewes ','Jewis '),'Yews '),
        (('Ioanna','Joone'),'Yoanna'), (('Iohn','Ihon','Joon'),'Yohn'),
            (('Iordane ','Iordan ','Iorden ','Iorda ','Jordan '),'Yordan '),(('Iordane,','Iordan,','Iorden,','Iorda,','Jordan,'),'Yordan,'),
            (('Ioseph',),'Yoseph'), (('Ioses','Joses'),'Yoses'),
        (('Iudas','Ivdas','Judas'),'Yudas'), (('Iudah','Iuda','Judah','Juda'),'Yudah'), (('Iudea','Judee'',Judaea'),'Yudea'), (('Iude',),'Yude'), (('Iury','Iurie'),'Yury/Yudea'), (('Iewry',),'Yewry'),
    (('Zebedeus ','zebede ','Zebede '),'Zebedee '), (('Zebedeus,','zebede,','Zebede,'),'Zebedee,'),

    # Roman numerals
    (('.iii.',),'3'), (('.vii.','vii.'),'7'), ((' x.',),' 10'), (('xii.',),'12'), ((' xl ',),' 40 '),

    # Symbols
    ((' & ',),' and '),
    )
oldWords, newWords = [], []
for wordMapEntry in ENGLISH_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    someOldWords,newWord = wordMapEntry
    assert isinstance( someOldWords, tuple ), f"{someOldWords=} should be a tuple"
    assert isinstance( newWord, str )
    for sowIx,someOldWord in enumerate( someOldWords ):
        assert isinstance( someOldWord, str ) and len(someOldWord)>=2, f"{someOldWord=}"
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if sowIx > 0: assert someOldWord not in newWord, f"Recursive substitution of '{someOldWord}' into '{newWord}'"
        assert '  ' not in someOldWord
        oldWords.append( someOldWord)
    if newWord not in ('themselves',): # sometimes two->one and sometimes it's a single word
        assert newWord not in newWords, f"{newWord=}"
    if someOldWords[0].startswith(' '): assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    if newWord[-1] in ' ,.:;)':
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
        (' alle ',' all '),(' alle,',' all,'),(' allen ',' all '),(' alles ',' all/everything '), ('allmächtige','almighty'),
            ('Also ','So '),
            ('Altar ','altar '), (' alten ',' old '),(' alt ',' old '),
        ('Angesicht ','face '), (' antwortete ',' replied '),
        ('Am ','At_the '),(' am ',' in/at/on_the '),
        (' an ',' at '), (' anbeten',' worship'), (' andern ',' change '), ('Anfang','beginning'), ('Antwort','answer'),
        ('Arche ','ark '),
        ('Asche ','ash '),
        (' außen ',' outside '),
            (' auch ',' also '),(' auch.',' also.'),
            (' auf ',' on '),(' auf,',' on,'), (' aufs ',' onto '),
            ('Aus ','Out of '),(' aus ',' out of '),(' aus.',' out.'),
    ('Ägypten','Egypt'),
        ('Ältesten','elders'), ('Älteste','elder'),
        (' andere ',' other '),
        ('ärgerte','annoyed'),('ärgert','annoys'),
    (' bald ',' soon '),
            ('Barmherzigkeit','compassion'),
        ('bedecken','cover'),
            ('Befehl','command'),
            (' begab ',' gifted '), (' begraben ',' buried '),
            (' bei ',' at '),
            (' bekleidet',' clothed'),
            (' beraubt',' robbed'),
                (' bereitete',' prepared'),
                ('Berge Sinai','Mt. Sinai'), ('Berge ','mountains/hills '),('Berg ','mountain/hill '),
                (' bersten',' burst/crack/break'),
            (' betaget',' old'),
        (' bin,',' am,'), (' bis ',' until '), (' bist ',' are '),
        (' bleibe ',' stay '),(' bleiben ',' remain '), ('Blut','blood'),
        (' bösen ',' evil '),
        (' brachte',' brought'), ('Brot ','bread '), ('Brüder','brothers'),('Bruder','brother'),
    ('Christus','Christ'),
    ('Da ','So '),(' da ',' there '),
            ('Daher ','Therefore '),
            (' damit ',' with_it/so_that '),
            (' danach ',' after/thereafter/then '),
            (' darauf ',' on_it '), ('Darum','Therefore'), (' darum ',' therefore '),
            ('Das ','The '),(' das ',' the '), ('daselbst','there'),
            ('Daß ','That '),(' daß ',' that '),
            (' dazu ',' in_addition '),
        (' dein ',' your '),(' deine ',' your '),
            (' dem ',' to_him '),(' dem,',' to_him,'),
            (' den ',' the '), ('Denen','Those'), ('Denn ','Because '),(' denn ',' because '), (' denselben ',' the_same '),
            ('Der ','The '),(' der ',' the/of_the '),
            (' des ',' the '),
        (' dich ',' you/yourself '),
            ('Die ','The '),(' die ',' the '), ('Dienst','service'), ('Dies ','This/These '),(' dies ',' this/these '), ('Diese ','This/These '),(' diese ',' this/these '),(' diese:',' this/these:'), (' diesem ',' this_one '),
            (' dir ',' you '),
        (' doch ',' though/but '),
        ('Drachen','dragons'),('Drache','dragon'), (' draußen',' outside'), (' drauf',' on_it'),
            ('dreißig','thirty'),(' drei',' three'),
        ('Du ','You '),(' du ',' you '),(' du,',' you,'),
            ('Dunkel ','darkness '),
            (' durch ',' through '),
    (' ehe ',' before '),
        (' eifriger ',' more_eager '),
        ('Engel','angel'),
        ('Erbe ','heritage '), ('Erde','earth'), (' erste ',' first '),
        (' ein ',' a '),(' eine ',' one '),(' einem ',' one '),(' einen ',' a '),(' einer,',' one,'),(' eines ',' one '), ('eingeborenen','native_born'),
        ('Er ','He '),(' er ',' he '),
            (' ergrimmete ',' enraged '),
            (' erlösete',' redeemed'),
            (' erschien',' appeared'),  (' ersterben',' die'),
            (' erwürget',' strangled'),
        ('Es ','It '),(' es ',' it '), (' essen',' eat'),
        (' etliche ',' several '),
            (' etwa ',' approximately '),
        (' euch',' you'),
            (' euren ',' yours '),(' eure ',' your '),
        ('Evangeliums','gospel'),
        (' ewige ',' eternal '),
    (' fahre ',' drive '), (' fast ',' nearly '),
        (' fehlet ',' mistake '), (' ferne;',' distance;'), ('Feuer','fire'),
        (' findet ',' finds '), ('Finsternis','darkness'),(' finster ',' dark '),
        ('Fleisch','flesh'),
        (' folgen ',' follow/obey '),(' folgeten ',' followed '),
        ('Freunde','friends'),
        ('Fuß','foot'),
        ('Füßen ','feet '),('Füße ','feet '), (' führen',' lead'),(' führest',' lead'), (' für ',' for '),
    (' gab ',' gave '),(' gab,',' gave,'),(' gaben ',' gave '), ('Gajus','Gaius'), (' gar ',' even '),
        (' geben ',' give '),(' geben.',' give.'), (' gebe ',' give '), ('Gebirge ','mountains '), (' geboten ',' offered '),
            (' gedachte',' thought'),
            (' geführet',' guided'),
            (' gegeben',' given'),
            (' gehe ',' go '),(' gehen',' go'),
            ('Geist','spirit'),
            ('gekehret','swept'),
            ('Geld ','money '), ('geliebet','loved'),
            (' gemacht',' made'), ('Gemeinden','communities'),
            (' genugsam',' enough'),(' genug',' enough'),
            (' gesagt',' said'), (' gesandt',' sent'), ('geschrieben','written'), ('Gesellen','fellows'), ('Gesetz','law'), (' gesund ',' healed '),
            ('Getreide ','grain '),
            (' gewesen ',' been '),
        ('Gib ','Give '),(' gib ',' give '), (' ging ',' went '),
        ('Glauben','faith'), ('glauben','believe'), ('Glied','member/element'),
        (' goß ',' poured/cast '),('Gottes','God’s'),('GOtt','God'),('Götter','gods'),
        ('Grabe ','grave '), (' groß ',' large '), (' große ',' large '),(' großen',' large'),(' großes',' large'),
        (' gut ',' good '),(' guter ',' good '),('Gutes ','Goodness '), ('Gütern ','goods '),
    ('Habe ','goods '), (' habe ',' have '),(' habe,',' have,'),(' habe.',' have.'),(' habe;',' have;'), ('haben','have'), (' habt',' have'),
            (' halben ',' half '), ('halsstarrig','stubborn'), (' halten ',' hold '),
            ('Händen','hands'),('Hände','hands'),
            (' harre ',' wait '),
            (' hasse ',' hate '), (' hast ',' have '),
            (' hat ',' has '),(' hat,',' has,'),(' hat:',' has:'), (' hatte ',' had '),(' hatte;',' had;'),
            ('Hauses','houses'),('Hause ','house '), ('Haut ','skin '),
        (' hebräisch ',' hebrew '),
            (' heilig',' holy'), (' heißt',' is_called'),
            ('heller ','brighter '),
            ('HErrn','LORD'),('HErr','LORD'), (' hervor',' out'), ('Herz','heart'),
        (' hie ',' here '), (' hieß ',' was_called '),(' hieß.',' was_called.'), (' hießet ',' is_called '),
            ('Himmel','heaven'),
            (' hin ',' there '),(' hin,',' there,'), (' hinab ',' down '), (' hinauf ',' up '), (' hinaufzog',' pulled_up'),
        ('Hölle','hell'),
            (' hörete',' heard'),(' höre',' listen'),
        (' hundert ',' hundred '), ('Hütte ','hut/cabin '),
    ('Ich ','I '),(' ich ',' I '),(' ich,',' I,'),
        (' ihm ',' him '),(' ihm.',' him.'),(' ihm:',' him:'),(' ihm!',' him!'), (' ihn ',' him/it '),(' ihn,',' him/it,'), (' ihr ',' her '), (' ihre ',' their/her '), (' ihren ',' your '), (' ihrer ',' of_their/her '),
        (' im ',' in_the '), (' immerdar',' forever'),
        (' innen ',' inside '), (' ins ',' into_the '),
        (' ist ',' is '),(' ist,',' is,'),(' ist.',' is.'),(' ist;',' is;'),
    (' je ',' each/ever '),
        (' jemand ',' someone '),
        ('JEsus','Yesus'), ('J','Y'),
        ('Jüngern','disciples'),
    (' kamen ',' came '), (' kam ',' came '), (' kaufen ',' buy '),
        (' keine ',' no '), (' keinen ',' none '),
        ('Kinder ','children '),
        ('Kleider ','clothes '),('Kleid ','garment '),
        ('Komm ','Come '),(' komme ',' come '),(' kommen ',' coming '),(' kommt ',' comes '),
        (' konnten ',' could '),
        ('Königs','kings'),('König','king'),
        ('Krone ','crown '),
    ('Lager ','camp '),
            ('Lande','land'), (' lang,',' long,'),(' länger ',' longer '),
            (' lasse ',' let '),
            (' laß ',' let '),
            ('Lauterkeit','purity/integrity'),
        ('Lebens','life'),('Leben ','life '),(' leben',' life'), (' lebet',' lives'),
            ('leer,','empty,'),
            ('Leib ','body '),
        ('Licht','light'),
            ('Lieben ','loved (one) '), (' lieber ',' dear '), (' liebhabe ',' love '), ('Liebe ','love '),
                (' ließ ',' let '),(' ließen ',' leave/let '), (' liegen',' lie/lay'), (' lieten',' lead'),
            ('Lippen ','lips '),
            ('List ','cunning '),
    (' mache ',' make '),(' machen ',' make '),(' machten',' make'),(' machte ',' made '),
            (' mag ',' like '),
            ('Männer ','men '), ('Manne ','man '), ('Mann ','man '),('Mann.','man.'),
            ('Märkte ','marketplaces '),
        (' mecum ',' with_me '),
            ('Meeres','sea'),('Meer ','sea '),('Meer.','sea.'),
            ('Meinest ','Mine '),('Meine ','My '),(' meinem ',' my '),(' meinen ',' my '),(' meiner ',' my '),(' meine ',' my '),('Mein ','My '),(' mein ',' my '),(' mein,',' my,'),
            ('Mensch ','person '),
        (' mich ',' me '),
            (' mir ',' to_me '),(' mir;',' to_me;'),
            ('Missetat ','misdeed/iniquity '),
            (' mit ',' with '),
        ('Mond ','moon '),
            ('. Morgan','. Morning'),('Morgan','morning'),
        (' mögest',' may'),
        (' muß ',' must '),
        ('Mutter ','mother '),
    (' nachdem ',' after '),('Nach ','After '),(' nach ',' after '),(' nach.',' after.'), ('Nacht ','night '),
            ('Naemi ','Naomi '),
            (' nahmen ',' took '),(' nahm ',' took '),
            ('Namen ','names '), (' nämlich ',' namely '),
        (' neben ',' next_to '),
            (' nehmen',' take'),
            ('Nest ','nest '),
            (' neun ',' nine '),
        (' nicht ',' not '),(' nicht,',' not,'),(' nicht;',' not;'),
            (' niemand',' no_one'),
            (' nimmermehr',' nevermore'),
        (' noch ',' still '),
        ('Nun ','Now '),(' nun ',' now '),
    (' oben ',' above '), ('Oberste ','top '),
        (' oder ',' or '),
        (' offene ',' open '),
        (' ohne ',' without '), ('Ohren ','ears '),
        ('Ort ','location '),('Ort,','location,'),
    (' öde ',' dull '),
    ('Pferd','horse'),
        (' predigte ',' preached '),
    ('Rat ','advice '),
        (' redeten',' talked'),(' redete ',' talked '), (' redet ',' talks '),
            ('Reich ','kingdom '), (' reisen ',' travel '),(' reisete ',' travelled '),
        (' roter ',' red '),
        (' ruchbar',' noticeable'),
    (' sagen',' say'),(' sagt',' says'),(' sage ',' said '),
            (' sah ',' saw '),(' sah,',' saw,'),(' sahen',' saw'),
            ('Samen ','seed/seeds '),('Samen.','seed/seeds.'),
            ('Sand','sand'),
            (' saß ',' sat '),
        ('Schande ','shame '),
                (' schied ',' separated '), ('Schiff','ship'),
                ('Schlüssel ','key '),
                (' schlugen ',' hit/beat '),(' schlug ',' hit/beat '),
                (' schrieen ',' screamed '),
                (' schuf ',' created '),
                (' schwebete ',' floated '),
        ('Segen','blessing'),
            (' sehe ',' see '), (' sehen',' see'),
            ('Sei ','Be '),(' sei ',' be '), (' seihe',' see'), (' sein ',' his '),(' seine ',' his '),(' seinem ',' his '),(' seinen ',' his '),(' seiner ',' his '), (' seit ',' since '), ('Seite ','side '),
            (' selbst ',' himself/itself '),
            (' sende ',' send '),(' senden ',' send '),
            (' setzten ',' put/set/sat '), (' setzte ',' sat '),
        (' sich ',' itself/yourself/themselves '),(' sich.',' itself/yourself/themselves.'),
            ('Sie ','They/She '),(' sie ',' they/she/them '), ('Sieben ','Seven '),(' sieben ',' seven '), (' sienem ',' his '),
            (' sind ',' are '),(' sind,',' are,'),
            (' sitzen',' sit'),(' sitzt',' sits'),
        ('Sohn','son'),('Söhne','sons'),
            (' solch ',' such '), (' soll ',' should '),(' sollst ',' should '),
            ('sondern','rather'), ('Sonne','sun'), ('Sonst ','Otherwise '),
        ('Speise ','food '),
            (' spiritern ',' spirits '),
            (' sprachen',' said'),(' sprach ',' spoke '),(' sprach:',' spoke:'),
        ('Städte ','cities '),('Städten ','cities '), ('Stadt ','city '),('Stadt,','city,'),
            ('Stamms ','tribe '),('Stamm ','tribe '), (' starb ',' died '), ('Staube ','dust '),('Staub ','dust '),
            (' stehet',' stands'),
                (' steigen',' climb'),
                (' sterben',' die'),(' sterbe',' die'),
            (' stille ',' silence '),
            ('streite ','argue/battle '),('streiten','argue/battle'),
            (' stund ',' stood '),
    ('Tage ','days '), (' täglich',' daily'), (' tat ',' did '),
        ('Teile','parts'),(' teile ',' share '),
        ('Tiefe ','depth '), ('Tier ','animal '), (' timor ',' fear '), ('Tisch ','table '),
        ('Tor ','goal/doorway '),
            (' toter ',' dead '),
            (' töte ',' kill '),(' töten.',' kill.'),
        (' trat ',' stepped '),
            (' trieb ',' drove '), (' trinken',' drink'),
            (' tröstet ',' comforts '),
            (' trug ',' wore '),
    (' über ',' above '),
        (' um ',' around/by/for '), (' umher ',' around/about '),
        ('Und ','And '),(' und ',' and '),
        ('ungläubige','unbelieving'), ('Ungewitter','storm'),
        (' unrecht',' wrong'), (' unrein',' unclean'),
        (' uns ',' us/to_us/ourselves '),
        (' unten',' below'),(' unter ',' under '),
    ('Vaterland','fatherland/homeland'), ('Vater ','father '),('Väter ','fathers '),
        ('vergeben','forgive'), ('verkündigte','announced'), ('verlässest','leave'),('verließen','left'), ('verloren','lost'), ('versammelt','gathered'), ('versöhnen','reconcile'), ('verständig','sensible'),
        (' viel ',' many '), (' vier ',' four '), (' vierte ',' fourth '),
        ('Volk','people'),('Völker','peoples'),
            (' vom ',' from_the '),
            (' von ',' from '),
            (' vor ',' before/in_front_of '), ('vorüberging','passed_by'),
    ('Wahrheit','truth'),
            (' war ',' was '),(' war,',' was,'),(' war.',' was.'), (' ward ',' was '), (' wären ',' would_be '), (' warf ',' threw '), # Is 'ward' a mispelling?
            ('Was ','What '), ('Wasser','water'),
        ('Weg ','path '),
            ('Weiber','women'),('Weib ','woman '),('Weib,','woman,'), (' weil ',' because '),  ('Wein ','wine '),  (' weiß ',' know '),
            ('Welche ','Which '),('welcher ','which '),(' welches ',' which '),(' welchem ',' which_one '), ('Welt','world'),
            ('Wenn ','When '),(' wenn ',' when '),
            ('Wer ','Who '),(' wer ',' who '), (' werden',' become'),(' werde',' become'),
            (' weinete ',' cried '), (' weiße ',' white '),
        (' wider ',' against '), ('Wie ','How '),(' wie ',' like '), (' wiederum',' again/in_turn'),(' wieder',' again'), ('Wind ','wind '), ('Winkel ','corner '),
            (' wird ',' becomes '), (' wirst ',' will '), ('Wir ','We '),(' wir ',' we/us '),
            ('Wisset ','Know '),(' wisset ',' know '),
        ('Wo ','Where '),
            (' wohl ',' probably '), (' wohltun',' do_good'),
            (' wollte',' wanted'),
            ('Worten','words'),('Worte ','words '),
        (' wurden ',' became '), ('Wurzel ','root '),
            ('Wüste','desert'), (' wüst ',' wild '),
            (' wußte ',' knew '),(' wußten',' knew'),
    ('Yahre','years'),
    ('zähme ','tame '),('Zähne ','teeth '),
        (' zehn ',' ten '), ('Zeichen ','sign '), (' zeugen',' witness'), ('Zeugnis','transcript'),
        (' zog ',' pulled '),(' zogen ',' pulled '), ('Zorn','anger'),
        (' zu ',' to '),(' zu,',' to,'), ('Zuletzt ','Finally '), (' zum ',' for_the '), (' zur ',' to '), (' zusammen ',' together '),
    )
GermanWords, EnglishWords = [], []
for wordMapEntry in GERMAN_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    GermanWord,EnglishWord = wordMapEntry
    assert isinstance( GermanWord, str ) and (len(GermanWord)>=2 or GermanWord in ('J',)), f"{GermanWord=}"
    assert GermanWord not in GermanWords, f"duplicate GermanWord: {GermanWord=} ({EnglishWord=})"
    if GermanWord.startswith(' ') or EnglishWord.startswith(' '): assert GermanWord.startswith(' '), f"Mismatched leading space: {GermanWord=} {EnglishWord=}"
    if GermanWord.endswith(' ') or EnglishWord.endswith(' '): assert GermanWord.endswith(' '), f"Mismatched trailing space: {GermanWord=} {EnglishWord=}"
    if sowIx > 0: assert GermanWord not in EnglishWord, f"Recursive substitution of '{GermanWord}' into '{EnglishWord}'"
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
    (' ab ',' away '), (' abierunt',' they_are_gone'), (' abiit ',' he_is_gone '), (' arbores ',' trees '),
        (' æternam',' eternal'), (' æternum',' eternal'),
        (' absque ',' without '),
        (' ad ',' to '), (' adverso ',' on_the_contrary '),
        (' ait ',' he_said '),
        (' alia ',' other '), (' aliæ ',' in_another '), (' aliud',' something_else'), (' alleviabit',' will_relieve'),
        ('amaræ','bitter'),
        ('ancillam','maidservant'),
            (' angelum',' a_messenger/angel'),
            (' annos ',' years '),
            (' ante ',' before '),(' antequam ',' before '),
        (' appellavit ',' he_called '),
        (' aqua',' water'),
        (' audi ',' listen '), (' autem',' however'),
        (' bis ',' twice '),
    (' bibere ',' to_drink '),
        (' bona ',' good '),
    ('cælum','the_sky'), (' calida ',' hot '),
        (' ceciderunt',' they_fell'),(' cecidit',' fell'),
            ('Centum ','Hundred '),(' centum ',' hundred '),
            ('Cerno ','I_see '), (' cervicis ',' of_the_neck '),
        ('Chananæum','Canaanites'),
        ('circumferentur','are_carried_around'),
            ('civitatis','of_the_city'),
        ('clamantis','crying'),
        ('Collisi ','I_collided '),
            ('congregabit','will_gather'), ('conspectu','in_sight'), ('continetur','is_contained'), (' contra ',' on_the_contrary '), ('contradictione','contradiction'),
            (' cor ',' heart '), (' corpus',' body'), (' corrigit ',' corrects '),
        ('creavit ','created '), ('credit','he_believes'),
        ('Cum ','Since '),(' cum ',' when/with '),
    ('dæmonia','demons'), (' daret ',' would_give '),(' daretur',' would_be_given'),
        (' de ',' about '),
            (' decem ',' ten '),(' decem,',' ten,'),
            (' dedit',' he_gave'), ('Deditque','And_he_gave'),
            ('Dei','God'),
            (' deserto ',' desert '),(' desertum',' desert'),
            ('Deum','God'),('Deus','God'),
        ('dicat','let_him_say'), ('dicentes','saying'), (' dices:',' you_say:'), (' dicit:',' he_says:'), ('dicitur','it_is_said'),
            (' diebus ',' days '), ('Dies ','The_day '),(' dies',' days'),
            ('dilexit','he_loved'),
            ('dimittere','to_release'),('dimittuntur','they_are_released'),
            ('divisit','divided'),
            ('Dixitque','And_he_said'), (' dixit ',' he_said '),
        (' docebo ',' I_will_teach '), (' docet',' teaches'),
            (' dolor ',' pain '),
            ('Domini ','Master '),('Domini,','Master,'),('Dominus','Master'), (' domum ',' home '), (' domus ',' home '),
        ('donec ','until '),
        (' ductus ',' leadership '), (' duo ',' two '), (' duræ ',' hard '),
    (' eam ',' her '),
            (' earum',' of_them'),
        ('Ecce ','Behold '), ('ecclesiis','assemblies/churches'),
        (' effusi ',' poured_out '),
        ('Ego ','I '),(' ego ',' I '),
        (' ei ',' to_him '),(' ei.',' to_him.'),(' eis ',' to_them '),
        (' ejus',' his'),
        (' enim',' because'),
        (' eorum',' their'), (' eos',' them'),
        (' epulis ',' food '),
        (' eradicatæ',' eradicated'), (' erant ',' they_were '),(' erant.',' they_were.'), (' erat',' was'),
            (' erit ',' will_be '),(' erit.',' will_be.'),
            (' ero.',' I_will_be.'), (' errore ',' by_mistake '),
        (' es ',' you_are '), (' essent ',' they_would_be '), (' esset ',' was '), (' est ',' it_is '),(' est,',' it_is,'),(' est:',' it_is:'),
        ('Et ','And '),(' et ',' and '), (' etiam ',' also '),
        (' eum ',' him '),(' eum,',' him,'),(' eum.',' him.'),(' eum?',' him?'),
        (' ex ',' from '), (' expecto ',' I_wait '),
    (' faciat ',' let_him_do '), (' faciem ',' face '), (' facite ',' do_it '), (' facta ',' facts '), ('facultatibus','resources'),
        (' feri ',' wild '),
        ('Fiat ','Let_it_happen '),
            (' fidei',' of_faith'),(' fidem ',' faith '),
            (' filia',' daughter'),('Filiæ','Daughters'),('Filii','Children'),(' filii',' children'),('filiorum','of_children'),('Filium','Son'),('Fili,','Son,'),
        ('fluctus ','wave '),
        ('fratrem','brother'),('fratres','brothers'),('fratrum','brothers'),
        (' fuerit',' has_been'),
            (' fugabunt ',' they_will_flee '),
            (' funiculi ',' rope '),
            (' fur ',' a_thief '),
    (' genere ',' in_general '),
    (' habeat ',' have '),(' habes,',' you_have,'), ('habitare','to_live'),
        ('Hæc ','This '),(' hæc ',' this '), ('hæreditatem','inheritance'),
        ('hebraice','hebrew'), ('Hethæum','Hittites'),  ('Hevæum','Hivites'),
        ('Hi ','They '), (' hic ',' this '),(' hic.',' this.'),
        ('Hoc ','This '), (' homo ',' human '),
        (' hunc ',' this_one '),
    ('Ibi ','There '),(' ibi ',' there '),
        ('Id ','That '),
        (' illis,',' to_them,'),
            (' illos ',' those '),(' illum ',' him '),
        ('imperium','government'),
        (' infirmum',' weak'),
            ('Initium ','The_beginning '),(' initium ',' the_beginning '),
            (' inter ',' between '), ('intravit','he_entered'), ('introëas','enter'),
        (' ipse ',' himself '),(' ipsos ',' themselves '),
        (' iste ',' this '),
        (' itaque ',' therefore '), (' iterum',' again'),
    ('Jordanem','Yordan'),
        (' justa.',' just.'),('Justi ','Just '), (' juxta ',' next_to '),
    (' laganum ',' pancake '),
        (' legum ',' the_law '),
        (' liberis ',' freedom '), ('Licet ','It’s_possible '),
        (' loco ',' instead '), (' locum ',' place '), (' locutus ',' spoke '),
            (' longious ',' farther '),
        (' lucem ',' the_light '), (' lux',' light'),
    (' maculæ',' spots'),
            (' magnus',' big'),
            (' malum ',' evil '),
            (' manu ',' by_hand '),(' manum ',' hand '), (' manus ',' hands '),
            (' mare ',' the_sea '),(' mari ',' of_the_sea '),
        (' mea.',' my.'), (' meæ ',' my '),
            (' mecum ',' with_me '),
            (' medio ',' in_the_middle '),
            (' mei ',' my/mine '),(' mei.',' my/mine.'),
            (' membra ',' members '),
            (' meo ',' mine '), (' mercede ',' reward '),
            (' meum ',' mine '),(' meum,',' mine,'),(' meum.',' mine.'), (' meus ',' mine '),(' meus,',' mine,'),
        (' mihi ',' to_me '),
            (' millia ',' thousands '),('millibus','thousands'),
            ('ministrabant','served'),
            (' misi ',' I_sent '),
            (' mitto ',' I_send '),
        (' monte ',' mountain '),
            (' mortuæ',' dead'),
            ('Moysi','of_Moses'),
        (' multæ ',' many '), (' mundum',' the_world'),
    ('Nati ','born '), (' navi:',' by_ship:'),
        (' nec ',' but_not '),
        (' nobis ',' us '),
            (' non ',' not/no '), ('Nonne ','Isn\'t_it '), (' nonne ',' isn\'t_it '),
            (' nos ',' we '),(' nos,',' we,'), (' nostri ',' our '), ('nostrorum','of_ours'), (' nostros',' ours'),
            (' novam',' new'),(' novum ',' new '),
        (' nubes ',' clouds '),
            (' nunc ',' now '),
    (' oleum ',' oil '),
        (' omnes ',' everyone '), (' omni ',' all '), ('Omnia ','Everything '),(' omnia ',' everything '),(' omnia,',' everything,'), (' omnis ',' everyone '), (' omnipotens',' omnipotent'),
        (' oratio ',' speech '), (' orbatus',' bereaved'),
        (' ostiis ',' the_doors '),
    (' panis ',' bread '),
            (' patris ',' of_the_father '),
        (' peccata ',' sins '),(' peccatis ',' sins '), ('peccatorum','sinners'),
            (' pedibus',' feet'),
            (' peperit ',' gave_birth '),
            (' per ',' through '), (' perductus ',' conducted '), (' pereat ',' perish '), (' perflata ',' blown_away '), (' perierunt',' they_perished'), (' pertinet',' belongs'),
        ('placabilem','appeasable'),
        ('Pones ','Put '), (' ponit',' puts'),
            (' populum',' the_people'),
            ('possederunt','they_possesed'), ('possessionem','possession'), (' post ',' after '),
            (' poterant ',' they_could '), (' potius ',' rather '),
        ('præcepit','ordered'),
            ('prima ','the_first '), ('princeps ','prince '), ('principio ','at_the_beginning '), ('principum','of_the_princes'), (' prius',' first/before'),
            ('procedens','proceeding'), ('procella ','storm '), ('proprie ','properly '), ('Propterea ',"That's_why "),
        (' putabunt ',' they_will_think '), (' puteum ',' a_well '),
    (' qua ',' which '),(' quæ ',' which '),(' quambis ',' with_which '),
            (' qualis ',' such_as '),
            (' quam ',' how '),
            (' quando ',' when '),
            (' quasi ',' as_if '),
            (' quatuor',' four'),
        (' quem ',' which '),
        ('Qui ','Who '),(' qui ',' who '), ('quia ','because '), ('Quibus ','To_whom '),('quibus ','to_whom '), ('Quis ','Who '),('quis ','who/any '),
        ('Quod ','That '),('quod ','that '), ('quos ','which '),
    (' radix ',' root '),
        (' rectas ',' correct '),
            (' regis',' king'),(' regnum',' kingdom'),
            (' reliqui ',' I_left '),
            ('remittat','let_him_go'), ('remittentur','they_will_be_released'),
            (' retia ',' net '),
            (' reus ',' guilty '),
        (' rursum',' again'),
    ('sacerdotis','of_the_priest'),
            (' salvabit',' will_save'),
            (' sanctum',' holy'), (' sanguinis',' blood'),
            (' sapientiam',' wisdom'),
        (' secuti ',' followed '), (' secundum ',' after/second '),
            ('Sed ','But '),(' sed ',' but '),
            (' semen ',' seed '), (' semitas ',' path '), (' semper ',' always '),
            ('senioribus','seniors'),
            (' sepelierunt',' they_buried'), (' septem ',' seven '), (' septimus ',' the_seventh '),
            (' servata ',' saved '), (' servierunt ',' they_served '),
        ('Si ','When/But_if '),(' si ',' when/but_if '),
            ('Sic ','So '),(' sic ',' so '), (' sicut ',' like '),
            (' sidera ',' stars '),
            (' sine ',' without '),
            (' sit ',' let_it_be '),(' sit,',' let_it_be,'),(' sit:',' let_it_be:'), (' situ ',' situation '),
            (' sive ',' if/or '),
        (' sortem ',' lot '),
        (' stare',' to_stand'), (' statim ',' immediately '),
            (' stella ',' star '),
        (' sua ',' his_own '),(' suam ',' his_own '),(' suam,',' his_own,'), (' suas ',' their_own '),
            ('Sub ','Under '),(' sub ',' under '),
            (' suis',' to_his_own'),(' sum ',' I_am '),
            (' sunt ',' are '),(' sunt,',' are,'),(' sunt.',' are.'),
            (' suo ',' his_own '),
            (' super ',' over '),
            (' surdos ',' the_deaf '),
            (' suum ',' his_own '),(' suum,',' his_own,'),
    (' tace,',' be_silent,'),
            (' tantum ',' only '),
        (' te ',' you(sg) '),(' te,',' you(sg),'),(' te.',' you(sg).'),
            ('Tectum ','The_roof '),(' tectum ',' roof '),
            (' tenebris',' darkness'), (' tenet',' holds'),
            (' terga ',' back '), (' terra ',' earth/land '),(' terram',' the_earth/land'),
            (' testimonium',' testimony'),
        (' tibi ',' to_you '),
        ('Tollens ','Taking_off '),
        (' tradidit ',' he_delivered '), (' trans ',' across '),
        (' tua ',' your '),(' tua.',' your.'),
            (' tui ',' yours '),
            ('tulerunt','they_took'), ('tulit ','took '),
            (' tuos ',' yours '),
            (' tuum ',' your '),
    ('Ubi ','Where '),(' ubi ',' where '),
        (' unctionis',' anointing'), (' unctus ',' anointed '),
            (' unde ',' whence '),
            ('unigenitum','only_born'), (' unius',' of_one'),
            (' unum ',' one '),(' unum.',' one.'),
        (' urbe ',' city '), (' urbem',' city'),
        (' usus ',' use '),
        (' ut ',' as '),
            (' uxorem',' wife'),(' uxor ',' wife '),
    ('Væ ','Alas '),
        (' vel ',' or '),
            ('Veneruntque','And_they_came'),(' veniat ',' let_him_come '),(' veniret ',' would_come '),(' venit ',' he_came '), (' ventis ',' the_winds '),
            ('veritatem','words'), ('vero,','indeed/yet,'),
            ('vestimenta','clothes'), ('vestras','your'),('vestrum','of_you'),
        (' via ',' road '),(' viam ',' road '),
            (' vidi ',' I_saw '),(' vidisset ',' had_seen '),(' vidit ',' he_saw '),
            (' vir ',' man '), (' virga',' rod/staff'), (' viro ',' to_the_man '), (' virorum',' of_men'), (' viros ',' men '),
            (' vis ',' you_want '),
            (' vitæ ',' of_life '), (' vitam ',' life '),
            (' vivat',' he_lives'),
        (' vobis ',' to_you '), ('vobiscum','with_you'),
            ('vocans ','calling '), ('vocatur ','is_called '), (' voces',' voices'), ('Vox ','The_voice '),
        (' vulva ',' womb '),
    )
LatinWords, EnglishWords = [], []
for wordMapEntry in LATIN_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    LatinWord,EnglishWord = wordMapEntry
    assert isinstance( LatinWord, str ) and len(LatinWord)>=2, f"{LatinWord=}"
    assert LatinWord not in LatinWords, f"duplicate LatinWord: {LatinWord=} ({EnglishWord=})"
    if LatinWord.startswith(' ') or EnglishWord.startswith(' '): assert LatinWord.startswith(' '), f"Mismatched leading space: {LatinWord=} {EnglishWord=}"
    if LatinWord.endswith(' ') or EnglishWord.endswith(' '): assert LatinWord.endswith(' '), f"Mismatched trailing space: {LatinWord=} {EnglishWord=}"
    if sowIx > 0: assert LatinWord not in EnglishWord, f"Recursive substitution of '{LatinWord}' into '{EnglishWord}'"
    assert '  ' not in LatinWord
    LatinWords.append( LatinWord)
    if LatinWord.startswith(' '): assert EnglishWord.startswith(' '), f"Mismatched leading space:  {LatinWord=} {EnglishWord=}"
    if LatinWord.endswith(' '): assert EnglishWord.endswith(' '), f"Mismatched trailing space: {LatinWord=} {EnglishWord=}"
    if EnglishWord[-1] in ' ,.:;':
        assert LatinWord[-1] == EnglishWord[-1], f"Mismatched trailing character: {LatinWord=} {EnglishWord=}"
    assert '  ' not in EnglishWord
    EnglishWords.append( EnglishWord )
del LatinWords, EnglishWords

def translateLatin( html:str ) -> bool:
    """
    Convert ancient Latin spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"translateLatin( ({len(html)}) )" )

    if html.startswith( 'et '): # Handle common exception that can't be expressed in the word table
        html = f'and {html[3:]}'
    elif html.startswith( 'qui '):
        html = f'who {html[4:]}'
    for LatinWord,EnglishWord in LATIN_WORD_MAP:
        html = html.replace( LatinWord, EnglishWord )

    return html.replace('j','y').replace('J','Y') \
                .replace('Yust ','Just ').replace('yust','just') \
                .replace('Yhes','Jhes') # Change these ones back again -- 'Jhesus' -- was maybe more like French J ???
# end of createParallelVersePages.translateLatin



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
