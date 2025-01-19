#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createOETInterlinearPages.py
#
# Module handling OpenBibleData createOETInterlinearPages functions
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
Module handling createOETInterlinearPages functions.

createOETInterlinearPages( level:int, folder:Path, state:State ) -> bool
createOETInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state:State ) -> bool
    Create a page for every Bible verse
createOETInterlinearVerseInner( level:int, BBB:str, c:int, v:int, state:State ) -> str # Returns the HTML
    Create an interlinear page for the Bible verse.
briefDemo() -> None
    Brief demo to check class is working
fullDemo() -> None
    Full demo to check class is working

CHANGELOG:
    2023-07-19 Fixed untr marker detection
    2023-10-25 Make use of word table index
    2024-01-07 Add chapter bar at top
    2024-04-08 Handle OT as well
    2024-07-19 Fixed OT Strongs links
    2025-01-17 Display untranslated words better in the NT

TODO:
    Add colour keys for LV and RV words
"""
# from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging
from collections import defaultdict

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

from settings import State, TEST_MODE
from usfm import convertUSFMMarkerListToHtml
from Bibles import formatUnfoldingWordTranslationNotes, formatTyndaleNotes
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP
from OETHandlers import livenOETWordLinks, getOETBookName, getOETTidyBBB, getHebrewWordpageFilename, getGreekWordpageFilename


LAST_MODIFIED_DATE = '2025-01-17' # by RJH
SHORT_PROGRAM_NAME = "createOETInterlinearPages"
PROGRAM_NAME = "OpenBibleData createOETInterlinearPages functions"
PROGRAM_VERSION = '0.57'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETInterlinearPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearPages( {level}, {folder}, ... )" )
    assert level == 1

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateOETInterlinearPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBLinks, BBBNextLinks = [], []

    # Now create the actual interlinear pages
    for BBB in state.booksToLoad['OET']:
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            createOETInterlinearVersePagesForBook( level, folder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinearVerse', None, state ) \
            .replace( '__TITLE__', f"Interlinear View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    indexHtml = f'''{top}
<h1 id="Top">OET interlinear verse pages</h1>
<p class="note">These pages show single OET verses with each Hebrew or Greek word aligned with the English word(s) that it was translated to, along with any translation notes and study notes for the verse. Finally, at the bottom of each page there's a <em>Reverse Interlinear</em> with the same information but in English word order.</p>
<h2>Index of books</h2>
{makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'interlinearIndex', state)}
{makeBottom( level, 'interlinearVerse', state )}'''
    checkHtml( 'interlinearIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETInterlinearPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createOETInterlinearPages.createOETInterlinearPages


def createOETInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state:State ) -> bool:
    """
    Create a page for every Bible verse
        displaying the interlinear verses.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    assert level == 1
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    adjBBBLinksHtml = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'interlinearVerse', state) \
            .replace( f'''<a title="{getOETBookName(BBB)}" href="../{BBB}/">{ourTidyBBBwithNotes}</a>''', ourTidyBBB )

    numChapters = None
    for versionAbbreviation in state.BibleVersions:
        if versionAbbreviation == 'OET': continue # that's only a "pseudo-version"!
        referenceBible = state.preloadedBibles[versionAbbreviation]
        # referenceBible.loadBookIfNecessary( BBB )
        numChapters = referenceBible.getNumChapters( BBB )
        if numChapters: break
    else:
        logging.critical( f"createOETInterlinearVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does
    chapterLinks = []
    cLinksPar = f'''<p class="chLst">{EM_SPACE.join( chapterLinks + [f'<a title="Go to interlinear verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
        if BBB=='PSA' else \
            f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( chapterLinks + [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>'''

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( 1, numChapters+1 ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating interlinear pages for {BBB} {c}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.error( f"createOETInterlinearVersePagesForBook: no verses found for {BBB} {c}" )
                continue
            for v in range( 1, numVerses+1 ):
                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Previous verse" href="C{c}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                rightVLink = f' <a title="Next verse" href="C{c}V{v+1}.htm#__ID__">→</a>' if v<numVerses else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a> ' if c>1 else ''
                rightCLink = f' <a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*BBBLevel}par/{BBB}/C{c}V{v}.htm#Top">║</a>'''
                detailsLink = f''' <a title="Show details about the OET" href="{'../'*(BBBLevel)}OET/details.htm#Top">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBBBwithNotes} {c}:{v} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}{detailsLink}</p>'
                iHtml = createOETInterlinearVerseInner( BBBLevel, BBB, c, v, state )
                assert iHtml
                assert '\n\n' not in iHtml
                filename = f'C{c}V{v}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'interlinearVerse', None, state ) \
                        .replace( '__TITLE__', f"{ourTidyBBB} {c}:{v} Interlinear View{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', f'Bible, interlinear, {ourTidyBBB}' ) \
                        .replace( f'''href="{'../'*BBBLevel}par/"''', f'''href="{'../'*BBBLevel}par/{BBB}/C{c}V{v}.htm#Top"''')
                iHtml = f'''{top}<!--interlinear verse page-->
{adjBBBLinksHtml}
{cLinksPar}
<h1>OET interlinear {ourTidyBBBwithNotes} {c}:{v}</h1>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{iHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, 'interlinearVerse', state )}'''
                checkHtml( f'Interlinear page {BBB} {c}:{v}', iHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as iHtmlFile:
                    iHtmlFile.write( iHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(iHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to interlinear verse page" href="{filename}#Top">{c}:{v}</a>' )
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename1 = 'index.htm'
    filepath1 = BBBFolder.joinpath( filename1 )
    top = makeTop( BBBLevel, None, 'interlinearVerse', None, state) \
            .replace( '__TITLE__', f"{ourTidyBBB} Interlinear View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear songs index</h1>
<p class="chLst">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear verses index</h1>
<p class="vsLst">{' '.join( vLinks )}</p>'''
    indexHtml = f'''{top}{adjBBBLinksHtml}
{ourLinks}
{makeBottom( BBBLevel, 'interlinearVerse', state )}'''
    checkHtml( 'interlinearIndex', indexHtml )
    with open( filepath1, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath1}" )

    # Write a second copy of the index page up a level
    newBBBVLinks = []
    for vLink in vLinks:
        newBBBVLinks.append( vLink.replace('href="', f'href="{BBB}/') )
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, None, 'interlinearVerse', None, state) \
            .replace( '__TITLE__', f"{ourTidyBBB} Interlinear View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear songs index</h1>
<p class="chLst">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear verses index</h1>
<p class="vsLst">{' '.join( newBBBVLinks )}</p>'''
    indexHtml = f'''{top}{adjBBBLinksHtml}
{ourLinks}
{makeBottom( level, 'interlinearVerse', state )}'''
    checkHtml( 'interlinearIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of html.createOETInterlinearVersePagesForBook


def createOETInterlinearVerseInner( level:int, BBB:str, c:int, v:int, state:State ) -> str: # Returns the HTML
    """
    Create an interlinear page for the Bible verse.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVerseInner( {level}, {BBB} {c}:{v}, … )" )

    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVerseInner {level}, {BBB} {c}:{v}, …" )

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    wordFileName = 'OET-LV_NT_word_table.tsv' if NT else 'OET-LV_OT_word_table.tsv'

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    C, V = str(c), str(v)

    lvBible = state.preloadedBibles['OET-LV']
    rvBible = state.preloadedBibles['OET-RV']
    wordTable = state.OETRefData['word_tables'][wordFileName]

    try:
        lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, C, V) )
        livenedLvVerseEntryList = livenOETWordLinks( level, lvBible, BBB, lvVerseEntryList, state )
        lvTextHtml = do_OET_LV_HTMLcustomisations( f"Interlinear={BBB}_{C}:{V}", convertUSFMMarkerListToHtml( level, 'OET-LV', (BBB,C,V), 'verse', lvContextList, livenedLvVerseEntryList, basicOnly=True, state=state ) )
        lvTextHtml = lvTextHtml.replace( 'id="fn', 'id="fnLV' ).replace( 'href="#fn', 'href="#fnLV' )
        lvHtml = f'''<div class="LV"><p class="LV"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm#Top">OET</a> (<a title="{state.BibleNames['OET-LV']}" href="{'../'*level}OET-LV/byC/{BBB}_C{c}.htm#Top">OET-LV</a>)</span> {lvTextHtml}</p></div><!--LV-->'''
    except (KeyError, TypeError):
        if BBB in lvBible and BBB in rvBible:
            warningText = f'No OET-LV {ourTidyBBBwithNotes} {c}:{v} verse available'
            lvHtml = f'''<p class="ilNote"><span class="wrkName"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm#Top">OET-LV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-LV {ourTidyBBBwithNotes} book available'
            lvHtml = f'''<p class="ilNote"><span class="wrkName">OET-LV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.warning( warningText )
        lvVerseEntryList = []
    try:
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB, C, V) )
        livenedRvVerseEntryList = livenOETWordLinks( level, lvBible, BBB, rvVerseEntryList, state )
        rvTextHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET-RV', (BBB,C,V), 'verse', rvContextList, livenedRvVerseEntryList, basicOnly=True, state=state ) )
        rvTextHtml = rvTextHtml.replace( 'id="fn', 'id="fnRV' ).replace( 'href="#fn', 'href="#fnRV' )
        rvHtml = f'''<div class="RV"><p class="RV"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm#Top">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{c}.htm#Top">OET-RV</a>)</span> {rvTextHtml}</p></div><!--RV-->'''
    except (KeyError, TypeError):
        if BBB in rvBible:
            warningText = f'No OET-RV {ourTidyBBBwithNotes} {c}:{v} verse available'
            rvHtml = f'''<p class="ilNote"><span class="wrkName"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm#Top">OET-RV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-RV {ourTidyBBBwithNotes} book available'
            rvHtml = f'''< class="ilNote"><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.warning( warningText )
        rvVerseEntryList = []
    # Handle (uW) translation notes and (Tyndale) study notes
    utnHtml = formatUnfoldingWordTranslationNotes( level, BBB, C, V, 'interlinearVerse', state )
    if utnHtml: utnHtml = f'<div class="UTN"><b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->\n'
    tsnHtml = formatTyndaleNotes( 'TOSN', level, BBB, C, V, 'interlinearVerse', state )
    if tsnHtml: tsnHtml = f'<div class="TSN">TSN <b>Tyndale Study Notes</b>: {tsnHtml}</div><!--end of TSN-->\n'

    # We need to find where this BCV is in the wordtable
    # Rather than go thru the entire table, find any wordnumber in the verse, then work back from there
    wordNumberStr = None # in case there's no words
    lvEnglishWordList = []
    for lvVerseEntry in lvVerseEntryList:
        cleanLVText, fullLVText = lvVerseEntry.getCleanText(), lvVerseEntry.getFullText()
        if not fullLVText or '¦' not in fullLVText: continue # no interest to us here

        # Remove sentence punctuation, break "chosen/messiah"
        #   then split into words
        lvEnglishWordList += ( cleanLVText # This has all formatting (like \\add fields) removed
                            .replace(',','').replace('.','').replace(':','').replace('?','')
                            .replace('>','').replace('<','') \
                            # .replace('\\add ','').replace('\\add*','')
                            # .replace('\\nd ','').replace('\\nd*','')
                            # .replace('\\sup ','<sup>').replace('\\sup*','</sup>')
                            # .replace('\\untr ','').replace('\\untr*','')
                            .replace('/messiah¦', ' messiah¦')
                            .replace('_',' ').replace('=',' ').replace('÷',' ')
                            .replace('   ',' ').replace('  ',' ')
                            .strip().split( ' ' )
                            )
        # print( f"Found {BBB} {c}:{v} {lvVerseEntry=}" )
        ixMarker = fullLVText.index( '¦' )
        if not wordNumberStr: # We only need to find one word number (preferably the first one) here
            wordNumberStr = ''
            for increment in range( 1, 7 ): # (maximum of six word-number digits)
                if fullLVText[ixMarker+increment].isdigit():
                    wordNumberStr = f'{wordNumberStr}{fullLVText[ixMarker+increment]}' # Append the next digit
                else: break
        # break
    rvEnglishWordList = []
    for rvVerseEntry in rvVerseEntryList:
        fullRVText = rvVerseEntry.getFullText()
        if not fullRVText or '¦' not in fullRVText: continue # no interest to us here

        # Remove sentence punctuation,
        #   then split into words
        rvEnglishWordList += fullRVText.replace(',','').replace('.','').replace(':','').replace('?','') \
                            .replace('\\add >','').replace('\\add <','') \
                            .replace('\\add ','').replace('\\add*','') \
                            .replace('\\nd ','').replace('\\nd*','') \
                            .replace('\\sup ','<sup>').replace('\\sup*','</sup>') \
                            .replace('_',' ').replace('   ',' ').replace('  ',' ') \
                            .strip().split( ' ' )

    # Make the English words into dicts
    lvEnglishWordDict = defaultdict( list )
    for extendedWord in lvEnglishWordList:
        if not extendedWord:
            logging.critical( f"OET-LV {BBB} {c}:{v} why did we get a zero-length word in {lvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError: # normal for footnotes
            logging.warning( f"OET-LV {BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
            # print( f"OET-LV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
            continue
        number = getLeadingInt( numberStr )
        if number < 1 or number >= len(wordTable):
            logging.critical( f"OET-LV {BBB} {c}:{v} word/number out of range from '{extendedWord}'" )
            # print( f"OET-LV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
        else:
            lvEnglishWordDict[number].append( word )
    rvEnglishWordDict = defaultdict( list )
    for extendedWord in rvEnglishWordList:
        if not extendedWord:
            logging.critical( f"OET-RV {BBB} {c}:{v} why did we get a zero-length word in {rvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.warning( f"OET-RV {BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
            # print( f"OET-RV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
            continue
        number = getLeadingInt( numberStr )
        if number < 1 or number >= len(wordTable):
            logging.critical( f"OET-RV {BBB} {c}:{v} word/number out of range from '{extendedWord}'" )
            # print( f"OET-RV {BBB} {c}:{v} {text=} {rvEnglishWordList=}")
        else:
            rvEnglishWordDict[number].append( word )

    if NT: # See if we have variants
        firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{C}:{V}']
        haveVariants = False
        for wordNumber in range( firstWordNumber, lastWordNumber+1 ):
            if not wordTable[wordNumber].split('\t')[7]: # probability
                haveVariants = True
                break # no need to look further

    # print( f"Found {BBB} {c}:{v} ({len(EnglishWordList)}) {EnglishWordList=}" )
    ivHtml = f'''<h2>{'SR Greek' if NT else 'Hebrew'} word order{' <small>(including unused variant words in grey)</small>' if NT and haveVariants else ''}</h2>
<div class=interlinear><ol class=verse>'''
    if wordNumberStr: # Now we have a word number from the correct verse
        # Display the interlinear blocks
        if NT:
            GreekList = ['''<li><ol class="titles">
  <li lang="el">Greek word</li>
  <li lang="el_LEMMA">Greek lemma</li>
  <li lang="en_TRANS"><b>OET-LV words</b></li>
  <li lang="en_TRANS"><b>OET-RV words</b></li>
  <li lang="en_STRONGS">Strongs</li>
  <li lang="en_MORPH">Role/Morphology</li>
  <li lang="en_GLOSS">OET Gloss</li>
  <li lang="en_GLOSS">VLT Gloss</li>
  <li lang="en_CAPS">CAPS codes</li>
  <li lang="en_PERCENT">Confidence</li>
  <li lang="en_TAGS">OET tags</li>
  <li lang="en_WORDNUM">OET word #</li>
</ol><!--titles--></li>''']
            for wordNumber in range( firstWordNumber, lastWordNumber+1 ):
                # if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                #     break
                rowStr = wordTable[wordNumber]
                assert rowStr.startswith( f'{BBB}_{c}:{v}w' )
                # if not rowStr.startswith( f'{BBB}_{c}:{v}w' ): # gone into the next verse
                #     break
                row = rowStr.split( '\t' )
                assert len(row) == 12
                #  0    1          2        3           4              5              6          7            8           9     10          11
                # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
                if row[11]:
                    tags = row[11].split( ';' )
                    for t,tag in enumerate( tags ):
                        tagPrefix, tag = tag[0], tag[1:]
                        if tagPrefix == 'P':
                            tags[t] = f'''Person=<a title="View person details" href="{'../'*level}ref/Per/{tag}.htm#Top">{tag}</a>'''
                        elif tagPrefix == 'L':
                            tags[t] = f'''Location=<a title="View place details" href="{'../'*level}ref/Loc/{tag}.htm#Top">{tag}</a>'''
                    tagsHtml = '; '.join( tags )
                else: tagsHtml = '-'
                GreekList.append( f'''<li><ol class="{'word' if row[7] else 'variant'}">
  <li lang="el">{row[1]}</li>
  <li lang="el_LEMMA">{row[2]}</li>
  <li lang="en_TRANS">{'<span class="untr" title="Word typically omitted from English translations">' if row[4][0]=='¬' else '<b>'}{' '.join(lvEnglishWordDict[wordNumber]) if lvEnglishWordDict[wordNumber] else '-'}{'</span>' if row[4][0]=='¬' else '</b>'}</li>
  <li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
  <li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[8][:-1]}.htm">{row[8]}</a></li>
  <li lang="en_MORPH">{row[9]}{row[10]}</li>
  <li lang="en_GLOSS">{row[5]}</li>
  <li lang="en_GLOSS">{row[4]}</li>
  <li lang="en_CAPS">{row[6] if row[6] else '-'}</li>
  <li lang="en_PERCENT">{row[7]+'%' if row[7] else 'V'}</li>
  <li lang="en_TAGS">{tagsHtml}</li>
  <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/GrkWrd/{getGreekWordpageFilename(wordNumber, state)}#Top">{wordNumber}</a></li>
</ol><!--{'word' if row[7] else 'variant'}--></li>''' )
            ivHtml = f'{ivHtml}{NEWLINE.join( GreekList )}'
        else: # OT
            HebrewList = ['''<li><ol class="titles">
  <li lang="he">Hebrew word</li>
  <li lang="he_LEMMA">Hebrew lemma</li>
  <li lang="en_TRANS"><b>OET-LV words</b></li>
  <li lang="en_TRANS"><b>OET-RV words</b></li>
  <li lang="en_STRONGS">Strongs</li>
  <li lang="en_MORPH">Role/Morphology</li>
  <li lang="en_GLOSS">Gloss</li>
  <li lang="en_CAPS">CAPS codes</li>
  <li lang="en_TAGS">OET tags</li>
  <li lang="en_WORDNUM">OET word #</li>
</ol><!--titles--></li>''']
            firstWordNumber,lastWordNumber = state.OETRefData['word_table_indexes'][wordFileName][f'{BBB}_{C}:{V}']
            for wordNumber in range( firstWordNumber, lastWordNumber+1 ):
                # if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                #     break
                rowStr = wordTable[wordNumber]
                assert rowStr.startswith( f'{BBB}_{c}:{v}' )
                # if not rowStr.startswith( f'{BBB}_{c}:{v}w' ): # gone into the next verse
                #     break
                row = rowStr.split( '\t' )
                assert len(row) == 19, f"({len(row)}) {row=}"
                #  0    1        2                3             4        5           6     7                8                9                          10         11                   12                   13                14          15           16    17       18
                # 'Ref\tRowType\tMorphemeRowList\tLemmaRowList\tStrongs\tMorphology\tWord\tNoCantillations\tMorphemeGlosses\tContextualMorphemeGlosses\tWordGloss\tContextualWordGloss\tGlossCapitalisation\tGlossPunctuation\tGlossOrder\tGlossInsert\tRole\tNesting\tTags'
                gloss = row[11] if row[11] else row[10] if row[10] else row[9] if row[9] else row[8]
                strongsList = [f'<a href="https://BibleHub.com/hebrew/{nn}.htm">{nn}</a>' for nn in row[4].split(',') if nn.isdigit()]
                if row[18]:
                    tags = row[18].split( ';' )
                    for t,tag in enumerate( tags ):
                        tagPrefix, tag = tag[0], tag[1:]
                        if tagPrefix == 'P':
                            tags[t] = f'''Person=<a title="View person details" href="{'../'*level}ref/Per/{tag}.htm#Top">{tag}</a>'''
                        elif tagPrefix == 'L':
                            tags[t] = f'''Location=<a title="View place details" href="{'../'*level}ref/Loc/{tag}.htm#Top">{tag}</a>'''
                    tagsHtml = '; '.join( tags )
                else: tagsHtml = '-'
                HebrewList.append( f'''<li><ol class="word">
  <li lang="he">{row[7]}</li>
  <li lang="he_LEMMA">{row[2]}</li>
  <li lang="en_TRANS"><b>{' '.join(lvEnglishWordDict[wordNumber]) if lvEnglishWordDict[wordNumber] else '-'}</b></li>
  <li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
  <li lang="en_STRONGS">{','.join(strongsList)}</li>
  <li lang="en_MORPH">{row[16]}-{row[5]}</li>
  <li lang="en_GLOSS">{gloss}</li>
  <li lang="en_CAPS">{row[12] if row[12] else '-'}</li>
  <li lang="en_TAGS">{tagsHtml}</li>
  <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/HebWrd/{wordNumber}.htm#Top">{wordNumber}</a></li>
</ol><!--word--></li>''' )
            ivHtml = f'{ivHtml}{NEWLINE.join( HebrewList )}'

    # Now append the OET-RV
    ivHtml = f'''{ivHtml}
</ol><!--verse--></div><!--interlinear-->
{lvHtml}
{rvHtml}
{utnHtml}
{tsnHtml}
<h2>OET-LV English word order (‘Reverse’ interlinear)</h2><div class=interlinear><ol class=verse>'''

    # Now create the reverseInterlinear
    rivHtml = ''
    if NT:
        reverseList = ['''<li><ol class="titles">
  <li lang="en_TRANS"><b>OET-LV words</b></li>
  <li lang="en_TRANS"><b>OET-RV words</b></li>
  <li lang="en_STRONGS">Strongs</li>
  <li lang="el">Greek word</li>
  <li lang="el_LEMMA">Greek lemma</li>
  <li lang="en_MORPH">Role/Morphology</li>
  <li lang="en_GLOSS">OET Gloss</li>
  <li lang="en_GLOSS">VLT Gloss</li>
  <li lang="en_CAPS">CAPS codes</li>
  <li lang="en_PERCENT">Confidence</li>
  <li lang="en_TAGS">OET tags</li>
  <li lang="en_WORDNUM">OET word #</li>
</ol><!--titles--></li>''']
    else: # OT
        reverseList = ['''<li><ol class="titles">
  <li lang="en_TRANS"><b>OET-LV words</b></li>
  <li lang="en_TRANS"><b>OET-RV words</b></li>
  <li lang="en_STRONGS">Strongs</li>
  <li lang="he">Hebrew word</li>
  <li lang="he_LEMMA">Hebrew lemma</li>
  <li lang="en_MORPH">Role/Morphology</li>
  <li lang="en_GLOSS">Gloss</li>
  <li lang="en_CAPS">CAPS codes</li>
  <li lang="en_TAGS">OET tags</li>
  <li lang="en_WORDNUM">OET word #</li>
</ol><!--titles--></li>''']
    lastWordNumber = None
    for extendedWord in lvEnglishWordList:
        if not extendedWord:
            logging.critical( f"{BBB} {c}:{v} why did we get a zero-length word in {lvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.critical( f"{BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
        wordNumber = getLeadingInt( numberStr )

        if wordNumber == lastWordNumber: # Put into the last cell
            lastEntry = reverseList.pop()
            lastEntry = lastEntry.replace('</b></li>', f' {word}</b></li>', 1)
            reverseList.append( lastEntry )
        else:
            # Display the reverse interlinear blocks
            rowStr = wordTable[wordNumber]
            if NT:
                assert rowStr.startswith( f'{BBB}_{c}:{v}w' )
                row = rowStr.split( '\t' )
                assert len(row) == 12
                #  0    1          2        3           4              5              6          7            8           9     10          11
                # 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
                if row[11]:
                    tags = row[11].split( ';' )
                    for t,tag in enumerate( tags ):
                        tagPrefix, tag = tag[0], tag[1:]
                        if tagPrefix == 'P':
                            tags[t] = f'''Person=<a title="View person details" href="{'../'*level}ref/Per/{tag}.htm#Top">{tag}</a>'''
                        elif tagPrefix == 'L':
                            tags[t] = f'''Location=<a title="View place details" href="{'../'*level}ref/Loc/{tag}.htm#Top">{tag}</a>'''
                    tagsHtml = '; '.join( tags )
                else: tagsHtml = '-'
                reverseList.append( f'''<li><ol class="word">
  <li lang="en_TRANS">{'<span class="untr" title="Word typically omitted from English translations">' if row[4][0]=='¬' else '<b>'}{word}{'</span>' if row[4][0]=='¬' else '</b>'}</li>
  <li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
  <li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[8][:-1]}.htm">{row[8]}</a></li>
  <li lang="el">{row[6]}</li>
  <li lang="el_LEMMA">{row[2]}</li>
  <li lang="en_MORPH">{row[9]}-{row[10]}</li>
  <li lang="en_GLOSS">{row[5]}</li>
  <li lang="en_GLOSS">{row[4]}</li>
  <li lang="en_CAPS">{row[6] if row[6] else '-'}</li>
  <li lang="en_PERCENT">{row[7]+'%' if row[7] else 'V'}</li>
  <li lang="en_TAGS">{tagsHtml}</li>
  <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/GrkWrd/{getGreekWordpageFilename(wordNumber, state)}#Top">{wordNumber}</a></li>
</ol><!--word--></li>''' )
            else: # OT
                assert rowStr.startswith( f'{BBB}_{c}:{v}' )
                row = rowStr.split( '\t' )
                assert len(row) == 19, f"({len(row)}) {row=}"
                #  0    1        2                3             4        5           6     7                8                9                          10         11                   12                   13                14          15           16    17       18
                # 'Ref\tRowType\tMorphemeRowList\tLemmaRowList\tStrongs\tMorphology\tWord\tNoCantillations\tMorphemeGlosses\tContextualMorphemeGlosses\tWordGloss\tContextualWordGloss\tGlossCapitalisation\tGlossPunctuation\tGlossOrder\tGlossInsert\tRole\tNesting\tTags'
                if row[18]:
                    tags = row[18].split( ';' )
                    for t,tag in enumerate( tags ):
                        tagPrefix, tag = tag[0], tag[1:]
                        if tagPrefix == 'P':
                            tags[t] = f'''Person=<a title="View person details" href="{'../'*level}ref/Per/{tag}.htm#Top">{tag}</a>'''
                        elif tagPrefix == 'L':
                            tags[t] = f'''Location=<a title="View place details" href="{'../'*level}ref/Loc/{tag}.htm#Top">{tag}</a>'''
                    tagsHtml = '; '.join( tags )
                else: tagsHtml = '-'
                strongsList = [f'<a href="https://BibleHub.com/hebrew/{nn}.htm">{nn}</a>' for nn in row[3].split(',') if nn.isdigit()]
                reverseList.append( f'''<li><ol class="word">
    <li lang="en_TRANS"><b>{word}</b></li>
    <li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
    <li lang="en_STRONGS">{','.join(strongsList)}</li>
    <li lang="he">{row[1]}</li>
    <li lang="he_LEMMA">{row[2]}</li>
    <li lang="en_MORPH">{row[16]}-{row[5]}</li>
    <li lang="en_GLOSS">{gloss}</li>
    <li lang="en_CAPS">{row[12] if row[12] else '-'}</li>
    <li lang="en_TAGS">{tagsHtml}</li>
    <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/HebWrd/{wordNumber}.htm#Top">{wordNumber}</a></li>
</ol><!--word--></li>''' )
            lastWordNumber = wordNumber
    rivHtml = f'{rivHtml}{NEWLINE.join( reverseList )}'


    ivHtml = f'''{ivHtml}{rivHtml}
</ol><!--verse--></div><!--interlinear-->
{lvHtml.replace( 'id="fnLV', 'id="fnRvLV' ).replace( 'href="#fnLV', 'href="#fnRvLV' )}
{rvHtml.replace( 'id="fnRV', 'id="fnRvRV' ).replace( 'href="#fnRV', 'href="#fnRvRV' )}
<p class="note"><small><b>Note</b>: The OET-RV is still only a first draft, and so far only a few words have been (mostly automatically) matched to the Hebrew or Greek words that they’re translated from.</small></p>
<p class="thanks"><b>Acknowledgements</b>: {f'The SR Greek text, lemmas, morphology, and VLT gloss are all thanks to the <a href="https://GreekCNTR.org/collation/index.htm?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR-GNT</a>.</p>' if BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
                                       else f'The Hebrew text, lemmas, and morphology are all thanks to the <a href="https://hb.openscriptures.org/">OSHB</a> and some of the glosses are from <a href="https://GitHub.com/Clear-Bible/macula-hebrew">Macula Hebrew</a>.'}'''
    
    # ivHtml = ivHtml.replace( '<br>\n' , '\n<br>' ) # Make sure it follows our convention (just for tidyness and consistency)
    while '\n\n' in ivHtml: ivHtml = ivHtml.replace( '\n\n', '\n' ) # Remove useless extra newline characters
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n\n{ivHtml=}" )
    checkHtml( f'Interlinear verse inner {BBB} {c}:{v}', ivHtml, segmentOnly=True )
    return ivHtml
# end of html.createOETInterlinearVerseInner



def briefDemo() -> None:
    """
    Brief demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETInterlinearPages object
    pass
# end of createOETInterlinearPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETInterlinearPages object
    pass
# end of createOETInterlinearPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createOETInterlinearPages.py
