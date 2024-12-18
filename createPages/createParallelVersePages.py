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
    2024-09-20 Split out language data tables
    2024-09-23 Link to actual verse in version chapter pages (rather than #Top)
    2024-11-18 Use colour hilight on (apparent) word changes between KJB-1611 and 1769
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

from settings import State, TEST_MODE, TEST_BOOK_LIST, VERSIONS_WITHOUT_NT, VERSIONS_WITHOUT_OT, VERSIONS_WITH_APOCRYPHA, \
                                reorderBooksForOETVersions, OET_SINGLE_VERSE_HTML_TEXT, OETS_UNFINISHED_WARNING_HTML_TEXT
from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTyndaleBookIntro, formatUnfoldingWordTranslationNotes, formatTyndaleNotes, getBibleMapperMaps, getVerseDetailsHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    convert_adds_to_italics, removeDuplicateFNids, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP, OSHB_ADJECTIVE_DICT, OSHB_PARTICLE_DICT, OSHB_NOUN_DICT, OSHB_PREPOSITION_DICT, OSHB_PRONOUN_DICT, OSHB_SUFFIX_DICT
from OETHandlers import getOETTidyBBB, getOETBookName, livenOETWordLinks, getHebrewWordpageFilename, getGreekWordpageFilename
from LanguageHandlers import moderniseEnglishWords, translateGerman, translateLatin


LAST_MODIFIED_DATE = '2024-12-12' # by RJH
SHORT_PROGRAM_NAME = "createParallelVersePages"
PROGRAM_NAME = "OpenBibleData createParallelVersePages functions"
PROGRAM_VERSION = '0.98'
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

    # Move SR-GNT and UHB and BrLXX and Brenton up after OET-RV and OET-LV
    parallelVersions = state.BibleVersions[:]
    parallelVersions.remove('SR-GNT'); parallelVersions.insert( 3, 'SR-GNT' )
    parallelVersions.remove('UHB'); parallelVersions.insert( 4, 'UHB' )
    parallelVersions.remove('BrLXX'); parallelVersions.insert( 5, 'BrLXX' )
    parallelVersions.remove('BrTr'); parallelVersions.insert( 6, 'BrTr' )
    parallelVersions.remove('NETS'); parallelVersions.insert( 7, 'NETS' )

    # Load version comments
    state.versionComments = {}
    with open( '../datasets/VersionComments.tsv', 'rt', encoding='utf-8' ) as versionCommentsFile:
        for ll,line in enumerate( versionCommentsFile ):
            line = line.rstrip( '\n' )
            assert line.count( '\t' ) == 3 # Four columns
            if ll == 0:
                assert line == 'Version\tVerseReference\tOptionalTextSegment\tComment'
                continue
            versionAbbreviation, verseRef, optionalTextSegment, comment = line.split( '\t' )
            if versionAbbreviation not in state.versionComments: state.versionComments[versionAbbreviation] = {}
            assert verseRef not in state.versionComments[versionAbbreviation] # or this duplicate would be lost
            state.versionComments[versionAbbreviation][verseRef] = (optionalTextSegment,comment)
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded {ll:,} version comments for {len(state.versionComments)} different versions." )

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
                createParallelVersePagesForBook( level, folder, BBB, BBBNextLinks, parallelVersions, state )

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

def createParallelVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], parallelVersions:List[str], state:State ) -> bool:
    """
    Create a page for every Bible verse
        displaying the verse for every available version.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1
    # isNT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

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
            adjC = 'Intro' if c==-1 else f'C{C}'
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

                debugKJBCompareBit = False
                ancientRefsToPrint = () # ('SA1_31:13',) # For debugging
                cleanedModernisedKJB1769TextHtml = depunctuatedCleanedModernisedKJB1769TextHtml = '' # These two are only used for comparisons -- they're not displayed on the page anywhere
                parallelHtml = getVerseDetailsHtml( BBB, C, V )
                for versionAbbreviation in parallelVersions: # our adjusted order
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    createParallelVersePagesForBook {parRef} processing {versionAbbreviation}…" )
                    assert not parallelHtml.endswith( '\n' )

                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have both OET-RV and OET-LV instead
                    if versionAbbreviation in (VERSIONS_WITHOUT_NT) \
                    and BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                        continue
                    if versionAbbreviation in (VERSIONS_WITHOUT_OT) \
                    and BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                        continue # Skip non-NT books for Koine Greek NT
                    if BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ) \
                    and versionAbbreviation not in VERSIONS_WITH_APOCRYPHA:
                        continue
                    if versionAbbreviation in ('TOSN','TTN','UTN'):
                        continue # We handle the notes separately at the end

                    if not doneHideablesDiv and versionAbbreviation not in ('OET-RV','OET-LV', 'SR-GNT','UHB', 'BrLXX','BrTr','NETS', 'ULT','UST', 'NET', 'BSB','BLB'):
                        assert not parallelHtml.endswith( '\n' )
                        parallelHtml = f'{parallelHtml}\n<div class="hideables">\n<hr style="width:60%;margin-left:0;margin-top: 0.3em">'
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
                                # if parRef in ancientRefsToPrint: print( f"---- {versionAbbreviation} {parRef} Got {verseEntryList=}" )
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
                            elif versionAbbreviation in ('WEBBE','WEB'): # assuming WEB/WEBBE comes BEFORE WMB/WMBBB
                                textHtmlWEB, footnotesHtmlWeb = textHtml, footnotesHtml # Save it
                            elif versionAbbreviation in ('WMBB','WMB'): # assuming WEB/WEBBE comes BEFORE WMB/WMBB
                                if textHtml and textHtml == textHtmlWEB.replace( 'WEBBE', 'WMBB' ).replace( 'WEB', 'WMB' ):
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
                            elif footnoteFreeTextHtml and versionAbbreviation in ('KJB-1769','KJB-1611','Bshps','Gnva','Cvdl','TNT','Wycl'):
                                # See if we need to add a modernised version of this text underneath the main/original text ???
                                # print( f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}")
                                # rawTextHtml = footnoteFreeTextHtml
                                # if rawTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ):
                                #     assert rawTextHtml.endswith( '</span>' )
                                #     rawTextHtml = rawTextHtml[30+len(versionAbbreviation):-7]
                                # print( f"{versionAbbreviation} {parRef} {rawTextHtml=}")
                                # if V=='4': halt
                                modernisedTextHtml = moderniseEnglishWords( footnoteFreeTextHtml )
                                if versionAbbreviation in ('KJB-1611','Bshps','Gnva','Cvdl','TNT','Wycl'):
                                    modernisedTextHtml = modernisedTextHtml.replace( 'J', 'Y' ).replace( 'Ie', 'Ye' ).replace( 'Io', 'Yo' ) \
                                                                                .replace( 'Yudge', 'Judge' ).replace( 'KYB', 'KJB' ) # Fix overreaches
                                modernisedTextDiffers = modernisedTextHtml != footnoteFreeTextHtml # we'll usually only show it if it changed

                                def removeVersePunctuationForComparison( htmlText:str ) -> str:
                                    """
                                    Punctuation was used differently over the centuries, so remove it from the verse
                                        so we can compare two verses and see if they differ only by punctuation.
                                    """
                                    return ( htmlText
                                            .replace(',','').replace('.','').replace(':','').replace(';','')
                                            .replace('!','').replace('?','') # Yes, even question mark is added punctuation
                                            .replace('-','')
                                            .replace('“','').replace('”','')
                                            .replace('‘','').replace('’','')
                                            .replace('(','').replace(')','')
                                            .replace('¶ ','').replace('¶','')
                                            .replace('  ',' ') # Around (now-removed) brackets 2Sam 4:10
                                            )
                                # end of removeVersePunctuationForComparison function

                                if versionAbbreviation == 'KJB-1769':
                                    # if parRef in ancientRefsToPrint: print( f"AA {versionAbbreviation} {parRef} ({len(modernisedTextHtml)}) {modernisedTextHtml=}" )
                                    # NOTE: cleanedModernisedKJB1769TextHtml and depunctuatedCleanedModernisedKJB1769TextHtml are only used for comparisons -- they're not displayed on the page anywhere
                                    cleanedModernisedKJB1769TextHtml = modernisedTextHtml.replace( versionAbbreviation, '' ) \
                                                                            .replace( '⇔ ', '' ) \
                                                                            .replace( 'J', 'Y' ).replace( 'Benjam', 'Benyam' ).replace( 'ij', 'iy' ).replace( 'Ij', 'Iy' ).replace( 'Ie', 'Ye' ) \
                                                                            .replace( '<span class="wj">', '' ).replace( '</span>', '' ) \
                                                                            .replace( '  ', ' ' ).replace( '> ', '>' ) \
                                                                            .strip() # Not sure why there's so many superfluous spaces in this text ???
                                    depunctuatedCleanedModernisedKJB1769TextHtml = removeVersePunctuationForComparison( cleanedModernisedKJB1769TextHtml )
                                    if parRef in ancientRefsToPrint: print( f"BB {versionAbbreviation} {parRef} ({len(depunctuatedCleanedModernisedKJB1769TextHtml)}) {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                # if versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"CC {versionAbbreviation} {parRef} ({len(modernisedTextHtml)}) {modernisedTextHtml=}")
                                # NOTE: cleanedModernisedTextHtml and depunctuatedCleanedModernisedTextHtml are only used for comparisons -- they're not displayed on the page anywhere
                                cleanedModernisedTextHtml = modernisedTextHtml.replace( versionAbbreviation, '' ) \
                                                                        .replace( 'ij', 'iy' ) \
                                                                        .replace( '<span class="wj">', '' ) \
                                                                        .replace( '<span style="fontsize75em">', '' ) \
                                                                        .replace( '</span>', '' ) \
                                                                        .replace( 'Yuniper', 'Juniper' ) \
                                                                        .replace( 'Yesus/Yeshua', 'Yesus' )
                                depunctuatedCleanedModernisedTextHtml = removeVersePunctuationForComparison( cleanedModernisedTextHtml )
                                if versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"DD {versionAbbreviation} {parRef} same={cleanedModernisedTextHtml==cleanedModernisedKJB1769TextHtml} ({len(depunctuatedCleanedModernisedTextHtml)}) {depunctuatedCleanedModernisedTextHtml=}")
                                if versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and cleanedModernisedTextHtml == cleanedModernisedKJB1769TextHtml:
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above{' apart from footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and cleanedModernisedTextHtml.lower() == cleanedModernisedKJB1769TextHtml.lower():
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from capitalisation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml == depunctuatedCleanedModernisedKJB1769TextHtml:
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml.lower() == depunctuatedCleanedModernisedKJB1769TextHtml.lower():
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from capitalisation and punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml.lower().replace( '<span class="add">', '' ) \
                                == depunctuatedCleanedModernisedKJB1769TextHtml.lower().replace( '<span class="add">', '' ):
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from marking of added words (and possibly capitalisation and punctuation{' and footnotes' if footnotesHtml else ''})</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                else: # the modernised text itself will be displayed
                                    if debugKJBCompareBit and versionAbbreviation!='KJB-1769': print( f"{parRef} {versionAbbreviation} DIFFERENT" )
                                    if versionAbbreviation == 'KJB-1611':
                                        # if debugThisBit:
                                        #     print( f"  {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                        #     print( f"  {depunctuatedCleanedModernisedTextHtml=}" )
                                        modernisedTextHtml = modernisedTextHtml.replace( 'class="add"', 'class="add_KJB-1611"' )
                                    else: # Hardwire added words to italics
                                        modernisedTextHtml = convert_adds_to_italics( modernisedTextHtml, f'Ancient parallel verse {parRef}' )
                                    modernisedTextHtml = modernisedTextHtml.replace( '_verseTextChunk"', '_mod"' )
                                    # if '<div' in modernisedTextHtml: # Shouldn't put a div inside a span!
                                    #     assert C=='-1' and V=='0'
                                    #     textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})''' # Typically a book heading
                                    # else: # no div
                                if versionAbbreviation=='KJB-1611' and not modernisedTextHtml.startswith('<small>') and not parRef.endswith( ':0' ): # Don't include chapter intros
                                    if debugKJBCompareBit:
                                        print( f"    {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                        print( f"  KJB-1611 {depunctuatedCleanedModernisedTextHtml=}" )
                                        print( f"                              {modernisedTextHtml=}")
                                    # When the texts differ,
                                    #   try to highlight the first KJB-1611 word that differs from the KJB-1769
                                    #       (so we can see where an edit was made)
                                    differentWordHighlighted = False
                                    if debugKJBCompareBit:
                                        print( f"AAA {depunctuatedCleanedModernisedTextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower()}" )
                                        print( f"BBB {depunctuatedCleanedModernisedKJB1769TextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower()}" )
                                        print( f"CCC {modernisedTextHtml.replace( '<span class="KJB-1611_mod">', '' ).replace( '<span class="add_KJB-1611">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).replace( '</span>', '' ).replace( '¶ ', '' )}" )
                                    doneHighlight = False
                                    changeIndex = 0 # So we only replace words after that
                                    for wordNum, (word1611, word1769, wordModTxt) in enumerate( zip( depunctuatedCleanedModernisedTextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower().split(),
                                                                           depunctuatedCleanedModernisedKJB1769TextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower().split(),
                                                                           modernisedTextHtml.replace( '<span class="KJB-1611_mod">', '' ).replace( '<span class="add_KJB-1611">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).replace( '</span>', '' ).replace( '¶ ', '' ).replace( '( ', '' ).split() ) ):
                                        if debugKJBCompareBit \
                                        and not word1611==word1769==wordModTxt: print( f"  LOOP {parRef} {wordNum} {changeIndex} {doneHighlight=} {word1611=} {word1769=} {wordModTxt=}")
                                        if word1769 != word1611:
                                            wordModTxtAdj = removeVersePunctuationForComparison( wordModTxt )
                                            if debugKJBCompareBit:
                                                if wordModTxtAdj != wordModTxt: print( f"        {wordModTxtAdj=} ({modernisedTextHtml.count(wordModTxtAdj)})" )
                                                if ( 'spannd' not in wordModTxt
                                                and '-' not in wordModTxt
                                                and (not parRef.startswith('PSA_') or not parRef.endswith(':1')) # first verses of some Psalms have a problem with //d fields
                                                and parRef not in ('KI1_10:15',) ):
                                                    assert wordModTxtAdj in modernisedTextHtml, f"{wordModTxt=} should have been in {modernisedTextHtml=}"
                                            if ( wordModTxtAdj.lower() == word1611
                                            and (modernisedTextHtml.count(wordModTxt)==1
                                                 or (len(wordModTxt)>0 and modernisedTextHtml.count(f' {wordModTxt}')==modernisedTextHtml.count(wordModTxt) and modernisedTextHtml.count(f'{wordModTxt} ')==modernisedTextHtml.count(wordModTxt) ) ) # Shorter words can occur inside other words too often
                                            and 'class=' not in wordModTxt
                                            and wordModTxtAdj.lower() not in ('adoniyah',) ):
                                                if debugKJBCompareBit: print( f"{parRef}\n{depunctuatedCleanedModernisedTextHtml=}\n{depunctuatedCleanedModernisedKJB1769TextHtml=}\n{modernisedTextHtml=}" )
                                                assert wordModTxt != 'span'
                                                # wordMTadj = removeVersePunctuationForComparison( wordMT )
                                                # Save the correct replacement until after the loop, or we can accidentally replace some of those words
                                                # TODO: Replacing all the words (or parts of words) isn't really very satisfactory
                                                changeIndex = max( changeIndex, modernisedTextHtml.find( wordModTxt, changeIndex ))
                                                modernisedTextHtml = f"{modernisedTextHtml[:changeIndex]}{modernisedTextHtml[changeIndex:].replace( wordModTxt, f'<span SPAN1>{wordModTxt}</span>' 
                                                             if modernisedTextHtml[changeIndex:].count(wordModTxt)==1 and not doneHighlight # Consecutive words might be just out of step
                                                                                                        else f'<span SPAN2>{wordModTxt}</span>')}"
                                                changeIndex += 19 # The minimum number of added characters
                                                doneHighlight = True
                                                checkHtml( f'hilighted {parRef} modernisedTextHtml after {wordModTxt=} replacement', modernisedTextHtml, segmentOnly=True )
                                                differentWordHighlighted = True
                                                if debugKJBCompareBit: print( f"  NOW {modernisedTextHtml=}" )
                                                # break
                                        if not doneHighlight:
                                            changeIndex += len(wordModTxt) + 1 # for the space that it was split on
                                    modernisedTextHtml = modernisedTextHtml.replace( 'SPAN1', 'title="Word (or format) changed in KJB-1769" class="hilite"' ) \
                                                                           .replace( 'SPAN2', 'title="Possible word (or format) changed in KJB-1769" class="possibleHilite"' )
                                    if not differentWordHighlighted and 'class="nd"' not in depunctuatedCleanedModernisedTextHtml:
                                        if debugKJBCompareBit: print( "CHECK THE ABOVE" )
                                        # halt
                                    # if 'KI2_3:' in parRef: halt
                                if modernisedTextDiffers or 'KJB-1769 above' in modernisedTextHtml:
                                    # if parRef in ancientRefsToPrint: print( f"YY {versionAbbreviation} {parRef} {modernisedTextDiffers=} {modernisedTextHtml=}" )
                                    textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})'''
                                # elif versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"ZZ {versionAbbreviation} {parRef} {modernisedTextDiffers=} ({len(cleanedModernisedTextHtml)}) {cleanedModernisedTextHtml=} ({len(modernisedTextHtml)}) {modernisedTextHtml=}" )
                            elif versionAbbreviation in ('Luth','ClVg'):
                                translateFunction = translateGerman if versionAbbreviation=='Luth' else translateLatin
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
                                if textHtml:
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
                                    if uhbTranscription.endswith( '.ş' ):
                                        uhbTranscription = uhbTranscription[:-1] # Drop the final discourse mark
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
                                # if parRef in ancientRefsToPrint: print( f"aaaa {versionAbbreviation} {parRef} Got {textHtml=}" )
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
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
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
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} chapter (side-by-side versions)" href="{'../'*BBBLevel}OET/byC/{BBB}_{adjC}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_{adjC}.htm#Top">OET-RV</a>)</small></span></p>{textHtml}'''
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} chapter (side-by-side versions)" href="{'../'*BBBLevel}OET/byC/{BBB}_{adjC}.htm#Top">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_{adjC}.htm#Top">OET-RV</a>)</small></span> {textHtml}</p>'''
                                elif versionAbbreviation=='Wycl': # Just add a bit about it being translated from the Latin (not the Greek)
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                    assert '<div' not in textHtml, f"{versionAbbreviation} {parRef} {textHtml=}"
                                    vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter (translated from the Latin)'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                else: # for all the others
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                    if textHtml.startswith( "(Same as " ):
                                        assert versionAbbreviation in ('WMBB','WMB')
                                        if footnotesHtmlWeb:
                                            if footnotesHtml == footnotesHtmlWeb.replace( 'WEBBE', 'WMBB' ).replace( 'WEB', 'WMB' ):
                                                footnotesHtml = '' # No need to repeat these either
                                                textHtml = textHtml.replace( 'above)', 'above including footnotes)' )
                                            # "closeVerse" class writes WMBB/WMB text on top of WEBBE/WEB footnotes -- probably should be fixed in CSS, but not sure how so will fix it here
                                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                        else: # WEB had no footnotes, so ok to use "closeVerse" class
                                            vHtml = f'''<p id="{versionAbbreviation}" class="closeVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                    elif '<div ' in textHtml: # it might be a book intro or footnotes
                                        assert '</div>' in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span></p>{textHtml}''' # .replace('<hr','</p><hr')
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                # Now append the footnotes (if any) for this version
                                vHtml = f'{vHtml}{footnotesHtml}'
                                if translatedFootnotesHtml and translatedFootnotesHtml!=footnotesHtml: # can happen with ClVg
                                    vHtml = f'{vHtml}{translatedFootnotesHtml}'

                            else: # no textHtml -- can include verses that are not in the OET-LV
                                # if parRef in ancientRefsToPrint: print( f"zzzz {versionAbbreviation} {parRef} No textHtml" )
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
                            # if parRef in ancientRefsToPrint: print( f"mmmm {versionAbbreviation} {parRef} Got MissingBookError" )
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            assert BBB not in thisBible
                            warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} details" href="{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top">{versionAbbreviation}</a></span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except UntranslatedVerseError:
                            NEVER_GETS_HERE # TODO: Why not???
                            assert textHtml == '◙'
                            assert versionAbbreviation == 'OET-RV'
                            assert BBB in thisBible
                            # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case)
                            # if BBB in thisBible:
                            # print( f"No verse inB OET-RV {BBB} in {thisBible}"); halt
                            warningText = f'No OET-RV {ourTidyBBBwithNotes} {C}:{V} verse available'
                            vHtml = f'''<p id="OET-RV" class="parallelVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="{state.BibleNames['OET']}" href="{'../'*BBBLevel}OET/byC/{BBB}_{adjC}.htm#V{V}">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} chapter (by itself)" href="{'../'*BBBLevel}OET-RV/byC/{BBB}_{adjC}.htm#Top">OET-RV</a>)</small></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                            # else:
                            #     warningText = f'No OET-RV {ourTidyBBBwithNotes} book available'
                            #     vHtml = f'''<p id="OET-RV" class="parallelVerse"><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except KeyError:
                            # if parRef in ancientRefsToPrint: print( f"kkkk {versionAbbreviation} {parRef} Got KeyError" )
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            if c==-1 or v==0:
                                vHtml = ''
                            elif BBB in thisBible:
                                # print( f"No verse inKT {versionAbbreviation} {BBB} in {thisBible}"); halt
                                warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} {C}:{V} verse available'
                                versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
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
                    if versionAbbreviation in state.versionComments \
                    and parRef in state.versionComments[versionAbbreviation]:
                        optionalTextSegment,comment = state.versionComments[versionAbbreviation][parRef]                 
                        parallelHtml = f'''{parallelHtml}{NEWLINE if parallelHtml else ''}<p class="editorsNote"><b>OET editor’s note on {versionAbbreviation}</b>: {f"<i>{optionalTextSegment}</i>: " if optionalTextSegment else ''}{comment}</p>'''
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
                    parallelHtml = f'{parallelHtml}\n<hr style="width:50%;margin-left:0;margin-top: 0.3em">\n{tsnHtml}'
                ttnHtml = formatTyndaleNotes( 'TTN', BBBLevel, BBB, C, V, 'parallelVerse', state )
                if ttnHtml:
                    ttnHtml = f'''<div id="TTN" class="parallelTTN"><a title="Go to TSN copyright page" href="{'../'*BBBLevel}TSN/details.htm#Top">TTN</a> <b>Tyndale Theme Notes</b>: {ttnHtml}</div><!--end of TTN-->'''
                    parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{ttnHtml}"
                # Handle uW translation notes 'UTN'
                utnHtml = formatUnfoldingWordTranslationNotes( BBBLevel, BBB, C, V, 'parallelVerse', state )
                if utnHtml:
                    utnHtml = f'''<div id="UTN" class="parallelUTN"><a title="Go to UTN copyright page" href="{'../'*BBBLevel}UTN/details.htm#Top">UTN</a> <b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:50%;margin-left:0;margin-top: 0.3em">\n{utnHtml}'

                # Handle BibleMapper maps and notes
                bmmHtml = getBibleMapperMaps( BBBLevel, BBB, C, V, None, None, state.preloadedBibles['OET-RV'] )
                if bmmHtml:
                    bmmHtml = f'''<div id="BMM" class="parallelBMM"><a title="Go to BMM copyright page" href="{'../'*BBBLevel}BMM/details.htm#Top">BMM</a> <b><a href="https://BibleMapper.com" target="_blank" rel="noopener noreferrer">BibleMapper.com</a> Maps</b>: {bmmHtml}</div><!--end of BMM-->'''
                    parallelHtml = f'{parallelHtml}\n<hr style="width:50%;margin-left:0;margin-top: 0.3em">\n{bmmHtml}'

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
<p class="rem">Note: {OET_SINGLE_VERSE_HTML_TEXT} Click on any Bible version abbreviation down the left-hand side to see the verse in more of its context. {OETS_UNFINISHED_WARNING_HTML_TEXT}</p>
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
        cleanedAdjustedBrightenUHBTextHtml, _footnoteStuff = cleanedAdjustedBrightenUHBTextHtml.split( '<hr style="width:35%;margin-left:0;margin-top: 0.3em">\n' )
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
