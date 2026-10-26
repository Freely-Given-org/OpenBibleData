#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# createOETInterlinearPages.py
#
# Module handling OpenBibleData createOETInterlinearPages functions
#
# Copyright (C) 2023-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling createOETInterlinearPages functions.

createOETInterlinearPages( level:int, folder:Path, state:State ) -> bool
createOETInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:list[str], state:State ) -> bool
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
    2025-02-02 Added vLinksPar and added ID to clinksPar (at top of page only), make OET/OET-RV go to section instead of chapter
    2025-02-03 Chapter selector now goes to verse selector (#vsLst) not #Top
    2025-12-15 Grey out currently selected book
    2026-01-07 Added OET Logo
    2026-02-10 Upgraded to VLT v3
    2026-04-09 Changed to use getPositiveLeadingInt
    2026-04-19 Added SOTN (SIL Open Translators Notes)
    2026-08-22 Import convertVerseEntryListToHtml directly from openbibledata_rust (convert.py deleted)
    2026-08-25 The OETHandlers functions are now imported from the Rust openbibledata_rust module (the Python OETHandlers.py was deleted).
    2026-09-01 Fixed bad links on second book index page
    2026-09-09 The per-word word-splitting chains and interlinear row builder now call the Rust openbibledata_rust ports
    2026-09-09 Use multiprocessing for the interlinear pages: per-book work is now _createOETInterlinearVersePagesForBook_MP, run by one forked worker per book
    2026-09-15 ESFM word-link livening is now fused (single-pass) into openbibledata_rust.convertVerseEntryListToHtml via its new livenWordLinks/addNoLinkYetSpans keyword args. The RV interlinear call explicitly passes addNoLinkYetSpans=False to replicate the old quirk where lvBible was (wrongly) passed to the liven, disabling the TEST_MODE OET-RV noLinkYet gate.
    2026-10-16 Report worker failures promptly via BOS, including abnormal process exits.
    2026-10-17 Use supported OET navigation books for links and jobs; handle absent chapter counts.
    2026-10-24 Keep traditional abbreviations alongside OET names for the selected book.
    2026-10-26 Include all Psalm headings in interlinear pages and verse/chapter navigation.
    2026-10-26 Add explained pages for alternate verse addresses after all ordinary pages finish.

TODO:
    Add colour keys for LV and RV words
"""
from pathlib import Path
import os
import logging
from collections import defaultdict
import re
from parallel import runParallelPages

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from bible_organisational_system import getPositiveLeadingInt
import bos_books_codes_py

from versification import navigationVersification, _mapReference, combinedPassageLabel, parallelVersePassage
from oetWords import passageWordRows
from navigation import navigationBookList, referenceHref, verseNavigationFirstVerses
from alternateVersePages import createAlternateVersePages
from oetPassages import _namespaceIds
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingError
from settings import State, state, CNTR_BOOK_ID_MAP, reorderBooksForOETVersions
from Bibles import formatUnfoldingWordTranslationNotes, formatTyndaleNotes
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createSectionPages import findSectionNumber
from jsonResources import getFormattedSILOpenTranslationNotes
from openbibledata_rust import convertVerseEntryListToHtml, getOETBookName, getOETTidyBBB, getHebrewWordpageFilename, getGreekWordpageFilename, splitOETLVInterlinearWords, splitOETRVInterlinearWords, buildInterlinearWordRows


LAST_MODIFIED_DATE = '2026-10-26'
SHORT_PROGRAM_NAME = "createOETInterlinearPages"
PROGRAM_NAME = "OpenBibleData createOETInterlinearPages functions"
PROGRAM_VERSION = '0.70'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETInterlinearPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 5: fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearPages( {level}, {folder}, ... )" )
    assert level == 1

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateOETInterlinearPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Prepare the book links
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDiscovered ilr {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Reordered to ilr {len(reorderBooksForOETVersions(state.allBBBs))} books across {len(state.preloadedBibles)} versions: {reorderBooksForOETVersions(state.allBBBs)}" )
    navigationBBBs = navigationBookList(reorderBooksForOETVersions(state.booksToLoad['OET']), state, 'interlinear')
    BBBLinks, BBBNextLinks = [], []
    for BBB in navigationBBBs:
        ourTidyBBB = getOETTidyBBB( BBB )
        ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
        BBBLinks.append( f'''<a title="{getOETBookName(BBB)}" href="{BBB}/index.htm#Top">{ourTidyBBBwithNotes}</a>''' )
        BBBNextLinks.append( f'''<a title="{getOETBookName(BBB)}" href="../{BBB}/index.htm#Top">{ourTidyBBBwithNotes}</a>''' )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Have ilr {len(BBBNextLinks)} book links: {BBBNextLinks}" )

    # Now create the actual interlinear pages
    mpBookParameters = [] # (level, folder, BBB, BBBNextLinks) tuples for the forked workers
    for BBB in navigationBBBs:
        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Use multiprocessing for these interlinear pages
            mpBookParameters.append( (level, folder, BBB, BBBNextLinks) )
        else: # no multiprocessing available -- do this book sequentially
            createOETInterlinearVersePagesForBook( level, folder, BBB, BBBNextLinks, state )
    if mpBookParameters:
        # NOTE: We use an explicit 'fork' context because Python 3.14 changed the default start method
        #        to 'forkserver' which would NOT inherit our huge module-level state (12 GiB of Bibles).
        #        Forked children share that memory copy-on-write, so this costs almost nothing extra.
        # NOTE: Outputs (including error and warning messages) from the various books may be interspersed.
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if state.TEST_MODE_FLAG else ''}interlinear pages for {len(mpBookParameters):,} books using {BibleOrgSysGlobals.maxProcesses:,} forked processes…" )
        results = runParallelPages(_createOETInterlinearVersePagesForBook_MP, mpBookParameters,
            taskNames=[f'book {p[2]}' for p in mpBookParameters])
        assert len(results) == len(mpBookParameters)
        assert all(results)

    # Add alternate-numbered addresses only once every ordinary target exists.
    createAlternateVersePages(folder, state.booksToLoad['OET'], state, 'interlinear')

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinearVerse', None, state ) \
            .replace( '__TITLE__', f"Interlinear View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    indexHtml = f'''{top}
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">OET interlinear verse pages</h1>
<h2>Index of books</h2>
<p class="note">These pages show single OET verses with each Hebrew or Greek word aligned with the English word(s) that it was translated to, along with any translation notes and study notes for the verse. Finally, at the bottom of each page there's a <em>Reverse Interlinear</em> with the same information but in English word order.</p><!--note-->
{makeBookNavListParagraph(BBBLinks, 'InterlinearIndex', state )}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'interlinearVerse' )}'''
    assert checkHtml( 'interlinearIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETInterlinearPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createOETInterlinearPages.createOETInterlinearPages


def _createOETInterlinearVersePagesForBook_MP( parameters ) -> bool:
    """
    Multiprocessing version! (forked children inherit our module-level state copy-on-write)

    Parameter is a 4-tuple containing the level, destination folder, BBB book code,
        and the next-book links.
    Returns the True result from createOETInterlinearVersePagesForBook.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"_createOETInterlinearVersePagesForBook_MP( {parameters[:3]}… )" )
    level, folder, BBB, BBBNextLinks = parameters
    resultBool = createOETInterlinearVersePagesForBook( level, folder, BBB, BBBNextLinks, state )
    assert resultBool is True
    return resultBool
# end of createOETInterlinearPages._createOETInterlinearVersePagesForBook_MP


def createOETInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:list[str], state:State ) -> bool:
    """
    Create a page for every Bible verse
        displaying the interlinear verses.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 5: fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    assert level == 1
    referenceBible = navigationVersification(state.navigationVersification)
    try: numChapters = referenceBible.getNumChapters(BBB)
    except KeyError: numChapters = None
    if not numChapters:
        logging.warning(f'Skipping interlinear book {BBB}: no chapter information in '
            f'navigation versification {state.navigationVersification!r}')
        return True
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    adjBBBLinksHtml = makeBookNavListParagraph( BBBLinks, 'InterlinearVerse', state, currentBBB=BBB )

    chapterLinks = []
    firstVerses = verseNavigationFirstVerses(BBB, numChapters, ('OET-LV','OET-RV'), state)
    chapterLinksParagraph = f'''<p class="chLst" id="chLst">{EM_SPACE.join( chapterLinks + [f'<a title="Go to interlinear verse page" href="C{ps}V{firstVerses[ps]}.htm#vsLst">Sg{ps}</a>' for ps in range(1,numChapters+1)] )}</p><!--chLst-->''' \
        if BBB=='PSA' else \
            f'''<p class="chLst" id="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( chapterLinks + [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm#vsLst">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p><!--chLst-->'''

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( 1, numChapters+1 ):
            C = str( c )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating interlinear pages for {BBB} {C}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.error( f"createOETInterlinearVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            firstVerse = firstVerses[c]
            for v in range(firstVerse, numVerses+1):
                vLinksPar = f'''<p class="vsLst" id="vsLst">{ourTidyBbb} {C} {' '.join( [f'<a title="Go to interlinear verse page" href="C{C}V{vv}.htm#Top">V{vv}</a>'
                                for vv in ([0] if firstVerse==0 else []) + list(range(1,numVerses+1,5 if numVerses>100 else 4 if numVerses>80 else 3 if numVerses>60 else 2 if numVerses>40 else 1)) if vv!=v] )}</p><!--vsLst-->'''

                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Previous verse" href="C{C}V{v-1}.htm#__ID__">←</a> ' if v>firstVerse \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                rightVLink = f' <a title="Next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses \
                        else f' <a title="Next chapter (first verse)" href="C{c+1}V{firstVerses[c+1]}.htm#__ID__">→</a>' if c<numChapters else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V{firstVerses[c-1]}.htm#__ID__">◄</a> ' if c>1 else ''
                rightCLink = f' <a title="Go to next chapter" href="C{c+1}V{firstVerses[c+1]}.htm#__ID__">►</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*BBBLevel}par/{BBB}/C{C}V{v}.htm#Top">║</a>'''
                verseListLink = f''' <a title="Simple verse list view" href="{'../'*BBBLevel}lst/{BBB}/C{C}V{v}.htm#Top">≡</a>'''
                detailsLink = f''' <a title="Show details about the OET" href="{'../'*(BBBLevel)}OET/details.htm#Top">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBBBwithNotes} {C}:{v} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}{verseListLink}{detailsLink}</p>'
                iHtml = createOETInterlinearVerseInner( BBBLevel, BBB, c, v, state )
                if iHtml is None: continue
                assert iHtml
                assert '\n\n' not in iHtml
                filename = f'C{C}V{v}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'interlinearVerse', None, state ) \
                        .replace( '__TITLE__', f"{ourTidyBBB} {C}:{v} Interlinear View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                        .replace( '__KEYWORDS__', f'Bible, interlinear, {ourTidyBBB}' ) \
                        .replace( f'''href="{'../'*BBBLevel}par/"''', f'''href="{'../'*BBBLevel}par/{BBB}/C{C}V{v}.htm#Top"''')
                iHtml = f'''{top}<!--interlinear verse page-->
{adjBBBLinksHtml}
{chapterLinksParagraph}
{vLinksPar}
<h1>OET interlinear {ourTidyBBBwithNotes} {C}:{v}</h1>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','BottomNavs').replace('__WHERE__','bottom')}
{iHtml}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*BBBLevel}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{navLinks.replace('__ID__','BottomNavs').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, None, 'interlinearVerse' )}'''
                assert checkHtml( f'Interlinear page {BBB} {C}:{v}', iHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as iHtmlFile:
                    iHtmlFile.write( iHtml )
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(iHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to interlinear verse page" href="{filename}#Top">{C}:{v}</a>' )
            lastNumVerses = numVerses # for the previous chapter
    else:
        if BibleOrgSysGlobals.verbosityLevel >= 4: dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename1 = 'index.htm'
    filepath1 = BBBFolder.joinpath( filename1 )
    top = makeTop( BBBLevel, None, 'interlinearVerse', None, state ) \
            .replace( '__TITLE__', f"{ourTidyBBB} Interlinear View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear songs index</h1>
<p class="chLst" id="chLst">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="C{ps}V{firstVerses[ps]}.htm#Top">Sg{ps}</a>' for ps in range(1,numChapters+1)] )}</p><!--chLst-->''' \
                if BBB=='PSA' else \
f'''<p class="chLst" id="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p><!--chLst-->
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*BBBLevel}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear verses index</h1>
<p class="vsLst">{' '.join( vLinks )}</p><!--vsLst-->'''
    indexHtml = f'''{top}{adjBBBLinksHtml}
{ourLinks}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*BBBLevel}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( BBBLevel, None, 'interlinearVerse' )}'''
    assert checkHtml( 'interlinearIndex', indexHtml )
    with open( filepath1, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath1}" )

    # Write a second copy of the index page up a level
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, None, 'interlinearVerse', None, state ) \
            .replace( '__TITLE__', f"{ourTidyBBB} Interlinear View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear songs index</h1>
<p class="chLst" id="chLst">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="PSA/C{ps}V{firstVerses[ps]}.htm#Top">Sg{ps}</a>' for ps in range(1,numChapters+1)] )}</p><!--chLst-->''' \
                if BBB=='PSA' else \
f'''<p class="chLst" id="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( [f'<a title="Go to interlinear verse page" href="{BBB}/C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p><!--chLst-->
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">OET {ourTidyBBBwithNotes} interlinear verses index</h1>
<p class="vsLst">{' '.join( vLinks ).replace('href="', f'href="{BBB}/')}</p><!--vsLst-->'''
    indexHtml = f'''{top}{adjBBBLinksHtml.replace('href="../', f'href="')}
{ourLinks}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'interlinearVerse' )}'''
    assert checkHtml( 'interlinearIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of html.createOETInterlinearVersePagesForBook


def createOETInterlinearVerseInner( level:int, BBB:str, c:int, v:int, state:State ) -> str|None: # Returns the HTML
    """
    Create an interlinear page for the Bible verse.
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 5: fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVerseInner( {level}, {BBB} {c}:{v}, … )" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVerseInner {level}, {BBB} {c}:{v}, …" )

    NT = bos_books_codes_py.is_new_testament_nr( BBB )
    wordFileName = 'OET-LV_NT_word_table.tsv' if NT else 'OET-LV_OT_word_table.tsv'

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    C, V = str(c), str(v)
    sectionNumber = findSectionNumber( 'OET-RV', BBB, C, V, state )
    if sectionNumber is None:
        logging.critical( f"Bad OET-RV interlinear section {BBB} {C} {V}" )
        return None


    lvBible = state.preloadedBibles['OET-LV']
    rvBible = state.preloadedBibles['OET-RV']
    wordTable = state.OETRefData['word_tables'][wordFileName]
    unnumberedTitle = v == 0 and any(d.code == 'UNDECLARED_TITLE' for d in
        _mapReference(state.navigationVersification, state.navigationVersification, (BBB,C,V,None)).diagnostics)

    nativeWordNumbers = ()
    try:
        if unnumberedTitle:
            lvPortions, lvPassageLabel = parallelVersePassage('OET-LV', lvBible, (BBB,C,V), state, {})
            if not any(entry.getMarker() == 'd' for _ref, entries, _context in lvPortions for entry in entries):
                raise KeyError((BBB,C,V)) # The LV may include the heading within numbered verse 1.
        else:
            lvPassage = lvBible.getMappedPassage(state.navigationVersification, ((BBB,C,V),), expandGroups=True)
            nativeWordNumbers = passageWordRows(lvPassage, state)
            lvPortions, lvPassageLabel = lvPassage.portions, combinedPassageLabel(lvPassage)
        lvVerseEntryList = [entry for _ref, entries, _context in lvPortions for entry in entries]
        lvParts = []
        for partNumber, (nativeRef, entries, context) in enumerate(lvPortions):
            text = do_OET_LV_HTMLcustomisations(f'Interlinear={nativeRef}',
                convertVerseEntryListToHtml(level, 'OET-LV', nativeRef, 'interlinearVerse', context, entries,
                    basicOnly=True, state=state, livenWordLinks=True))
            label = f'<small>({nativeRef[0]} {nativeRef[1]}:{nativeRef[2]})</small> ' if nativeRef != (BBB,C,V) else ''
            lvParts.append(label + _namespaceIds(text, f'LV{partNumber}_'))
        lvTextHtml = lvPassageLabel + ' '.join(lvParts)
        nativeLink = referenceHref(level, lvPortions[0][0], 'OET-LV')
        lvHtml = f'<div class="LV"><p class="LV"><span class="wrkName"><a title="View Literal Version passage" href="{nativeLink}">OET-LV</a></span> {lvTextHtml}</p></div><!--LV-->'
    except (KeyError, TypeError, VersificationMappingError) as error:
        warningText = (f'OET-LV alignment unavailable ({error.result.status.value})'
                       if isinstance(error, VersificationMappingError) else 'Mapped OET-LV passage is not available')
        lvHtml = f'<p class="ilNote"><span class="wrkName">OET-LV</span> <span class="noVerse">{warningText}</span></p>'
        logging.warning('%s %s %s:%s: %s', warningText, BBB,C,V,error)
        lvVerseEntryList = []
        nativeWordNumbers = ()
    try:
        if unnumberedTitle:
            rvPortions, rvPassageLabel = parallelVersePassage('OET-RV', rvBible, (BBB,C,V), state, {})
        else:
            rvPassage = rvBible.getMappedPassage(state.navigationVersification, ((BBB,C,V),), combineAdjacent=True, expandGroups=True)
            rvPortions, rvPassageLabel = rvPassage.portions, combinedPassageLabel(rvPassage)
        rvVerseEntryList = [entry for _ref, entries, _context in rvPortions for entry in entries]
        # NOTE: The old code used lvBible for the liven (a quirk), so no TEST_MODE OET-RV
        # noLinkYet highlighting/preprocessing ever ran here -- we replicate that with addNoLinkYetSpans=False.
        rvTextHtml = ' '.join(do_OET_RV_HTMLcustomisations(f'Interlinear={nativeRef}',
            convertVerseEntryListToHtml(level, 'OET-RV', nativeRef, 'interlinearVerse',
                context, entries, basicOnly=True, state=state,
                livenWordLinks=True, addNoLinkYetSpans=False)) for nativeRef, entries, context in rvPortions)
        rvTextHtml = rvPassageLabel + rvTextHtml
        rvTextHtml = rvTextHtml.replace( 'id="footnotes', 'id="footnotesRV' ).replace( 'id="crossRefs', 'id="crossRefsRV' ).replace( 'id="fn', 'id="fnRV' ).replace( 'href="#fn', 'href="#fnRV' )
        rvHtml = f'''<div class="RV"><p class="RV"><span class="wrkName"><a title="View {state.BibleNames['OET']} section" href="{'../'*level}OET/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET-RV</a>)</span> {rvTextHtml}</p></div><!--RV-->'''
    except (KeyError, TypeError, VersificationMappingError):
        if BBB in rvBible:
            warningText = f'No OET-RV {ourTidyBBBwithNotes} {c}:{v} verse available'
            rvHtml = f'''<p class="ilNote"><span class="wrkName"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET-RV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-RV {ourTidyBBBwithNotes} book available'
            rvHtml = f'''<p class="ilNote"><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.warning( warningText )
        rvVerseEntryList = []
    if unnumberedTitle:
        # These titles have no whole-verse mapping. Their ESFM links still
        # identify the exact Hebrew rows, even when the LV stores them in v1.
        nativeWordNumbers = tuple(sorted({int(n) for entry in lvVerseEntryList + rvVerseEntryList
            if entry.getMarker() == 'd' for n in re.findall(r'¦(\d+)', entry.getOriginalText() or '')}))
    # Handle (SIL and uW) translation notes and (Tyndale) study notes
    sotnHtml = getFormattedSILOpenTranslationNotes( level, BBB, C, V, 'interlinearVerse', state )
    if sotnHtml: sotnHtml = f'<div class="SOTN"><b>SIL Open Translator’s Notes</b>: {sotnHtml}</div><!--end of SOTN-->\n'
    utnHtml = formatUnfoldingWordTranslationNotes( level, BBB, C, V, 'interlinearVerse', state )
    if utnHtml: utnHtml = f'<div class="UTN"><b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->\n'
    tsnHtml = formatTyndaleNotes( 'TOSN', level, BBB, C, V, 'interlinearVerse', state )
    if tsnHtml: tsnHtml = f'<div class="TSN">TSN <b>Tyndale Study Notes</b>: {tsnHtml}</div><!--end of TSN-->\n'

    # Text and word rows have both been selected in native coordinates.
    lvEnglishWordList = []
    for lvVerseEntry in lvVerseEntryList:
        cleanLVText, fullLVText = lvVerseEntry.getCleanText(), lvVerseEntry.getOriginalText()
        # if not cleanLVText: print( f"createOETInterlinearVerseInner {BBB} {c}:{v} {lvVerseEntry.getMarker()} {fullLVText=} {cleanLVText=}" )
        if not fullLVText or '¦' not in fullLVText: continue # no interest to us here

        # Remove sentence punctuation, break "chosen/messiah"
        #   then split into words (Rust port of the per-entry clean/split chain)
        lvEnglishWordList += splitOETLVInterlinearWords( cleanLVText )
        # print( f"Found {BBB} {c}:{v} {lvVerseEntry=}" )
    rvEnglishWordList = []
    for rvVerseEntry in rvVerseEntryList:
        fullRVText = rvVerseEntry.getOriginalText()
        if not fullRVText or '¦' not in fullRVText: continue # no interest to us here

        # Remove sentence punctuation,
        #   then split into words (Rust port of the per-entry clean/split chain)
        rvEnglishWordList += splitOETRVInterlinearWords( fullRVText )

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
        number = getPositiveLeadingInt( numberStr )
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
        number = getPositiveLeadingInt( numberStr )
        if number < 1 or number >= len(wordTable):
            logging.critical( f"OET-RV {BBB} {c}:{v} word/number out of range from '{extendedWord}'" )
            # print( f"OET-RV {BBB} {c}:{v} {text=} {rvEnglishWordList=}")
        else:
            rvEnglishWordDict[number].append( word )

    haveVariants = NT and any(wordTable[n].split('\t')[7] != 'X' for n in nativeWordNumbers)

    # print( f"Found {BBB} {c}:{v} ({len(EnglishWordList)}) {EnglishWordList=}" )
    # Removed <li lang="en_PERCENT">{row[7]+'%' if row[7]=='X' else 'V'}</li>
    ivHtml = f'''<h2>{'SR Greek' if NT else 'Hebrew'} word order{' <small>(including unused variant words in grey)</small>' if NT and haveVariants else ''}</h2>
<div class=interlinear><ol class=verse>'''
    if nativeWordNumbers:
        # word_table_indexes[wordTableName][BCV] -> (firstRowIndex, lastRowIndex): inclusive row numbers of this verse's rows in state.OETRefData['word_tables'] (built in Rust, see createSitePages)
        # Display the interlinear blocks (per-word rows are built in Rust for speed)
        wordRows, wordNumbers, wordpageFilenames = [], [], []
        for wordNumber in nativeWordNumbers:
            rowStr = wordTable[wordNumber]
            wordRows.append( rowStr.split( '\t' ) )
            wordNumbers.append( wordNumber )
            wordpageFilenames.append( getGreekWordpageFilename(wordNumber, state ) if NT else f'{wordNumber}.htm' )
        # The Rust port also emits the title row, tags (Person=/Location=),
        #   gloss selection, Strongs links, and word-number links
        ivHtml = f'{ivHtml}{buildInterlinearWordRows( level, NT, wordRows, wordNumbers, wordpageFilenames, lvEnglishWordDict, rvEnglishWordDict )}'
    # Now append the OET-RV
#  <li lang="en_PERCENT">{row[7]+'%' if row[7] else 'V'}</li>
    ivHtml = f'''{ivHtml}
</ol><!--verse--></div><!--interlinear-->
{lvHtml}
{rvHtml}
{sotnHtml}
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
            logging.critical( f"OET-LV {BBB} {c}:{v} why did we get a zero-length word in {lvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.critical( f"OET-LV {BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
        wordNumber = getPositiveLeadingInt( numberStr )

        if wordNumber == lastWordNumber: # Put into the last cell
            lastEntry = reverseList.pop()
            lastEntry = lastEntry.replace('</b></li>', f' {word}</b></li>', 1)
            reverseList.append( lastEntry )
        else:
            # Display the reverse interlinear blocks
            rowStr = wordTable[wordNumber]
            if NT:
                assert wordNumber in nativeWordNumbers
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
  <li lang="en_TAGS">{tagsHtml}</li>
  <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/GrkWrd/{getGreekWordpageFilename(wordNumber, state )}#Top">{wordNumber}</a></li>
</ol><!--word--></li>''' )
            else: # OT
                assert wordNumber in nativeWordNumbers
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
    <li lang="he">{row[6]}</li>
    <li lang="he_LEMMA">{row[2]}</li>
    <li lang="en_MORPH">{row[16]}-{row[5]}</li>
    <li lang="en_GLOSS">{row[11] or row[10] or row[9] or row[8]}</li>
    <li lang="en_CAPS">{row[12] if row[12] else '-'}</li>
    <li lang="en_TAGS">{tagsHtml}</li>
    <li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}ref/HebWrd/{wordNumber}.htm#Top">{wordNumber}</a></li>
</ol><!--word--></li>''' )
            lastWordNumber = wordNumber
    rivHtml = f'{rivHtml}{NEWLINE.join( reverseList )}'


    cntrLinks = []
    if NT:
        for wordNumber in nativeWordNumbers:
            sourceRef = wordTable[wordNumber].split('\t', 1)[0]
            sourceBBB, sourceCV = sourceRef.split('_', 1)
            sourceC, sourceV = sourceCV.split('w', 1)[0].split(':')
            link = f'<a href="https://GreekCNTR.org/collation/index.htm?v={CNTR_BOOK_ID_MAP[sourceBBB]}{sourceC.zfill(3)}{sourceV.zfill(3)}">CNTR</a>'
            if link not in cntrLinks: cntrLinks.append(link)

    ivHtml = f'''{ivHtml}{rivHtml}
</ol><!--verse--></div><!--interlinear-->
{_namespaceIds(lvHtml, 'reverse_')}
{_namespaceIds(rvHtml, 'reverse_')}
<p class="note"><small><b>Note</b>: The OET-RV is still only a first draft, and so far only a few words have been (mostly automatically) matched to the Hebrew or Greek words that they’re translated from.</small></p><!--note-->
<p class="thanks"><b>Acknowledgements</b>: {f'The SR Greek text, lemmas, morphology, and VLT gloss are all thanks to the {" / ".join(cntrLinks) or "CNTR"}.</p>' if bos_books_codes_py.is_new_testament_nr( BBB )
                                       else f'The Hebrew text, lemmas, and morphology are all thanks to the <a href="https://hb.openscriptures.org/">OSHB</a> and some of the glosses are from <a href="https://GitHub.com/Clear-Bible/macula-hebrew">Macula Hebrew</a>.'}'''

    # ivHtml = ivHtml.replace( '<br>\n' , '\n<br>' ) # Make sure it follows our convention (just for tidyness and consistency)
    while '\n\n' in ivHtml: ivHtml = ivHtml.replace( '\n\n', '\n' ) # Remove useless extra newline characters
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n\n{ivHtml=}" )
    assert checkHtml( f'Interlinear verse inner {BBB} {c}:{v}', ivHtml, segmentOnly=True )
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
