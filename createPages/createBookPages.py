#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# createBookPages.py
#
# Module handling OpenBibleData createBookPages functions
#
# Copyright (C) 2023-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling createBookPages functions.

CHANGELOG:
    2023-08-30 Added FRT processing for RV
    2023-12-21 Keep book selection line at top of page
    2024-01-08 Fixed bug when moving to previous/next books for 'ALL' books
    2025-03-03 Tried to improve breaking into sections, esp. handling of /ms1 titles
    2025-03-24 Liven Readers' Version and Literal Version headings
    2025-09-25 Make all SR-GNT verse text into live links to collation pages
    2026-01-07 Added OET Logo
    2026-08-22 Import convertVerseEntryListToHtml directly from openbibledata_rust (convert.py deleted)
    2026-08-25 The OETHandlers functions are now imported from the Rust openbibledata_rust module (the Python OETHandlers.py was deleted).
    2026-09-03 Stop applying the Heb/Grk grammatical colourisation classes on book pages because their CSS doesn't style them -- the shared dark-mode rules were painting those words unreadably.
    2026-09-04 Disable the TEST_MODE 'noLinkYet' highlighting on OET-RV single-column book pages (which have no OET-LV alongside), via addNoLinkYetSpans=False.
    2026-09-09 Use multiprocessing for the OET side-by-side book pages: per-book work is now _createOETBookPagesForBook, run by one forked worker per book.
    2026-09-15 ESFM word-link livening is now fused (single-pass) into openbibledata_rust.convertVerseEntryListToHtml via its new livenWordLinks/colouriseWordClasses/addNoLinkYetSpans keyword args, so the old livenOETWordLinks/livenOETCompatibleBereanWordLinks calls in the book-page hot paths have been removed.
    2026-09-24 Added extra warnings when OET-RV or OET-LV are shown alone
    2026-10-12 Map complete OET-RV passages to OET-LV with BOS before rendering side-by-side rows.
    2026-10-16 Report worker failures promptly via BOS, including abnormal process exits.
    2026-10-24 Use traditional book abbreviations on other versions' document pages.
"""
from pathlib import Path
from parallel import runParallelPages
import os
import re
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, BOOKLIST_OT39, BOOKLIST_NT27
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import bos_books_codes_py

from settings import State, state, CNTR_BOOK_ID_MAP
from navigation import bookAbbreviation
from oetPassages import renderOETSideBySideChunks
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from openbibledata_rust import convertVerseEntryListToHtml, getOETTidyBBB, getHebrewWordpageFilename, getGreekWordpageFilename


LAST_MODIFIED_DATE = '2026-10-24' # by RJH
SHORT_PROGRAM_NAME = "createBookPages"
PROGRAM_NAME = "OpenBibleData createBookPages functions"
PROGRAM_VERSION = '0.73'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
NARROW_NON_BREAK_SPACE = ' '



def _createOETBookPagesForBook( level:int, folder:Path, rvBible, lvBible, state:State, BBB:str ) -> tuple[bool,str,list[str]]:
    """
    Write the OET side-by-side whole-book page for one book.

    This is the per-book body of createOETBookPages.
    Returns (True, BBB, the list of filenames written).
    """
    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks['OET'], 'OET', state )
    iBkList = ['index'] + state.BBBsToProcess['OET']
    processedFilenames = []
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    createOETBookPages {BBB=} {state.BBBsToProcess['OET']} out of {len(state.BBBsToProcess['OET'])}" )
    NT = bos_books_codes_py.is_new_testament_nr( BBB )
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )

    # # RUST IMPLEMENTATION TEST
    # if BBB in ('HAG','MRK'):
    #     if 0: # writing
    #         with open( f'OET-RV_{BBB}_CVs.txt', 'wt', encoding='utf-8') as test_file:
    #             test_file.write( f"OET-RV {BBB} {len(rvBible[BBB]._CVIndex)}\n" )
    #             for n,(startCV, CVIndexEntry) in enumerate( rvBible[BBB]._CVIndex.items() ):
    #                 test_file.write( f"{n} {startCV=} {CVIndexEntry=}\n" )
    #         with open( f'OET-LV_{BBB}_CVs.txt', 'wt', encoding='utf-8') as test_file:
    #             test_file.write( f"OET-RV {BBB} {len(lvBible[BBB]._CVIndex)}\n" )
    #             for n,(startCV, CVIndexEntry) in enumerate( lvBible[BBB]._CVIndex.items() ):
    #                 test_file.write( f"{n} {startCV=} {CVIndexEntry=}\n" )
    #     else: # Reading and checking
    #         for ii, internalBibleEntry in enumerate( rvBible[BBB] ):
    #             print( f"OET-RV {BBB} {ii} {internalBibleEntry.marker=} {internalBibleEntry.cleanText=}")
    #         for n,(startCV, CVIndexEntry) in enumerate( rvBible[BBB]._SectionIndex.items() ):
    #             print( f"  {n} {BBB} {startCV=} {CVIndexEntry=}" )
    #         with open( f'OET-RV_{BBB}_CVs.txt', 'rt', encoding='utf-8') as test_file:
    #             fileChunks = test_file.read().split( '\n' )
    #         expectedStr = f"OET-RV {BBB} {len(rvBible[BBB]._CVIndex)}"
    #         assert expectedStr == fileChunks[0], f"{expectedStr=} {fileChunks[0]=}"
    #         for n,(startCV, CVIndexEntry) in enumerate( rvBible[BBB]._CVIndex.items() ):
    #             expectedStr = f"{n} {startCV=} {CVIndexEntry=}"
    #             assert expectedStr == fileChunks[n+1], f"Section index mismatch for OET-RV {BBB} {n} {startCV=}\n    {expectedStr=}\n{fileChunks[n+1]=}"

    if rvBible.abbreviation in state.booksToLoad \
    and 'ALL' not in state.booksToLoad[rvBible.abbreviation] \
    and BBB not in state.booksToLoad[rvBible.abbreviation]:
        logging.critical( f"B Skipped OET chapters not-included book: OET-RV {BBB}")
        return ( True, BBB, [] ) # Skip this book entirely

    if BBB in ('INT','FRT'): # We want these, even though the LV doesn't (yet?) have any FRT
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating book page for OET {BBB}…" )
        # iBkList = ['index'] + state.booksToLoad[rvBible.abbreviation]
        try: # May give ValueError if this book doesn't not occur in this translation
            bkIx = iBkList.index( BBB )
            bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
            bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''
        except ValueError: # this BBB wasn't there in the list for this work
            bkPrevNav = f'''<a title="Previous (book index)" href="index.htm#Top">◄</a> '''
            bkNextNav = f' <a title="Next (first existing book)" href="{iBkList[1]}.htm#Top">►</a>'

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">{rvBible.abbreviation} {ourTidyBBBwithNotes}</span>{bkNextNav}</p>
{state.JAMES_NAME_NOTE_HTML_PARAGRAPH}
{state.OET_UNFINISHED_BOOK_WARNING_HTML_PARAGRAPH}'''
        verseEntryList, contextList = rvBible.getContextVerseData( (BBB,) )
        assert isinstance( rvBible, ESFMBible.ESFMBible )
        textHtml = convertVerseEntryListToHtml( level, rvBible.abbreviation, (BBB,), 'book', contextList, verseEntryList, basicOnly=False, state=state, livenWordLinks=True, colouriseWordClasses=False, addNoLinkYetSpans=False )
        # textHtml = livenIORs( BBB, textHtml )
        textHtml = do_OET_RV_HTMLcustomisations( f'BookA={BBB}', textHtml )
        bkHtml = f'{bkHtml}{textHtml}'
        filename = f'{BBB}.htm'
        processedFilenames.append( filename )
        # BBBLinks.append( f'''<a title="{bos_books_codes_py.get_english_name_nr(BBB)}" href="{filename}#Top">{ourTidyBBBwithNotes}</a>''' )
        filepath = folder.joinpath( filename )
        top = makeTop( level, rvBible.abbreviation, 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"{rvBible.abbreviation} {ourTidyBBB} book{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, {rvBible.abbreviation}, front matter, book, document' ) \
                .replace( f'''<a title="{state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/byDoc/{filename}#Top">{rvBible.abbreviation}</a>''',
                        f'''<a title="Up to {state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/">↑{rvBible.abbreviation}</a>''' )
        bkHtml = f'''{top}<!--book page-->
{navBookListParagraph}
{bkHtml}
{makeBottom( level, rvBible.abbreviation, 'book' )}'''
        assert checkHtml( f'OET Book FRT {rvBible.abbreviation} {BBB}', bkHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
        return ( True, BBB, processedFilenames ) # Finished the special case book (no full-book page)

    # This obsolete code used to prevent building of OET-RV DC books as there's no OET-LV version -- removed 2026-09-02
    # elif lvBible.abbreviation in state.booksToLoad \
    # and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
    # and BBB not in state.booksToLoad[lvBible.abbreviation]:
    #     logging.critical( f"C Skipped OET chapters not-included book: OET-LV {BBB}")
    #     continue # Only create pages for the requested LV books

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for OET {BBB}…" )
    bkIx = iBkList.index( BBB )
    bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
    bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''

    bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">Open English Translation {ourTidyBBBwithNotes}</span>{bkNextNav}</p>
{f'{state.JAMES_NAME_NOTE_HTML_PARAGRAPH}{NEWLINE}' if BBB=='JAM' else ''}{state.OET_UNFINISHED_BOOK_WARNING_HTML_PARAGRAPH}
<div class="RVLVcontainer">
<h2><a title="View just the Readers’ Version by itself" href="{'../'*level}OET-RV/byDoc/{BBB}.htm#Top">Readers’ Version</a></h2>
<h2><a title="View just the Literal Version by itself" href="{'../'*level}OET-LV/byDoc/{BBB}.htm#Top">Literal Version</a> <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>'''
    combinedHtml, _firstNative = renderOETSideBySideChunks(
        level, rvBible, lvBible, BBB, 'book', state )
    filename = f'{BBB}.htm'
    processedFilenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'book', f'byDoc/{filename}', state ) \
            .replace( '__TITLE__', f"OET {ourTidyBBB}{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, book, document, {ourTidyBBB}' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc/{filename}#Top">OET</a>''',
                      f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET/">↑OET</a>''' )
    bkHtml = f'''{top}<!--book page-->
{navBookListParagraph}
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
{bkHtml}
{removeDuplicateCVids( combinedHtml )}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a></div><!--RVLVcontainer-->
{makeBottom( level, 'OET', 'book' )}'''
    assert checkHtml( f'OET Book {BBB}', bkHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( bkHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    return ( True, BBB, processedFilenames )
# end of createBookPages.py._createOETBookPagesForBook

def _createOETBookPagesForBook_MP( parameters ) -> tuple[bool,str,list[str]]:
    """
    Multiprocessing version! (forked children inherit our module-level state copy-on-write)

    Parameter is a 3-tuple containing the level, destination folder, and BBB.
    Returns the (True, BBB, filenames) result from _createOETBookPagesForBook.
    """
    level, folder, BBB = parameters
    rvBible = state.preloadedBibles['OET-RV']
    lvBible = state.preloadedBibles['OET-LV']
    resultBool, BBBResult, filenames = _createOETBookPagesForBook( level, folder, rvBible, lvBible, state, BBB )
    assert resultBool is True
    return ( resultBool, BBBResult, filenames )
# end of createBookPages.py._createOETBookPagesForBook_MP


def createOETBookPages( level:int, folder:Path, rvBible, lvBible, state:State ) -> list[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks['OET'], 'OET', state )

    # Now create the actual OET book pages (one forked worker per book)
    processedBBBs, processedFilenames = [], []
    mpBookParameters = [] # (level, folder, BBB) tuples for the forked workers
    for BBB in state.BBBsToProcess['OET']:
        if BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Use multiprocessing for these OET book pages
            mpBookParameters.append( (level, folder, BBB) )
        else: # no multiprocessing available -- do this book sequentially
            resultBool, BBBResult, bookFilenames = _createOETBookPagesForBook( level, folder, rvBible, lvBible, state, BBB )
            assert resultBool is True
            if bookFilenames:
                processedBBBs.append( BBBResult ); processedFilenames.extend( bookFilenames )
    if mpBookParameters:
        # NOTE: We use an explicit 'fork' context because Python 3.14 changed the default start method
        #        to 'forkserver' which would NOT inherit our huge module-level state (12 GiB of Bibles).
        #        Forked children share that memory copy-on-write, so this costs almost nothing extra.
        # NOTE: Outputs (including error and warning messages) from the various books may be interspersed.
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if state.TEST_MODE_FLAG else ''}OET book pages for {len(mpBookParameters):,} books using {BibleOrgSysGlobals.maxProcesses:,} forked processes…" )
        results = runParallelPages(_createOETBookPagesForBook_MP, mpBookParameters,
            taskNames=[f'book {p[2]}' for p in mpBookParameters])
        assert len(results) == len(mpBookParameters)
        for resultBool, BBBResult, bookFilenames in results:
            assert resultBool is True
            if bookFilenames:
                processedBBBs.append( BBBResult ); processedFilenames.extend( bookFilenames )
    # Now create an overall index page
    filename = 'index.htm'
    processedFilenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'bookIndex', 'byDoc', state ) \
            .replace( '__TITLE__', f"OET Document View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, OET, Open English Translation, book, document' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc">OET</a>''',
                      f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
    indexHtml = f'''{top}
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">OET book pages</h1>
<h2>Index of books</h2>
{state.WHOLE_BOOKS_WARNING_HTML_PARAGRAPH}
{navBookListParagraph}
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, 'OET', 'bookIndex' )}'''
    assert checkHtml( 'OETBooksIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages() finished processing {len(processedBBBs)} OET books: {processedBBBs}." )
    return processedFilenames
# end of createBookPages.createOETBookPages


CV_REGEX = re.compile( '/C(\\d{1,3})V(\\d{1,3}).htm' )
def createBookPages( level:int, folder:Path, thisBible, state:State ) -> list[str]:
    """
    This creates a page for each book for all versions other than 'OET'
                                which is considerably more complex (above).
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createBookPages( {level}, {folder}, {thisBible.abbreviation} )" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    # BBBsToProcess = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
    #             else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
    #             else thisBibleBooksToLoad
    # if 'OET' in thisBible.abbreviation:
    #     BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    # iBkList = ['index'] + list( state.preloadedBibles[thisBible.abbreviation].books.keys() )
    iBkList = ['index'] + state.BBBsToProcess[thisBible.abbreviation]
    # print( f"createBookPages {thisBible.abbreviation=} {state.BBBsToProcess[thisBible.abbreviation]=} {iBkList=}" ); assert False, "We want to stop here"
    navBookListParagraph = makeBookNavListParagraph( state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state )

    processedBBBs, processedFilenames = [], []
    for BBB in state.BBBsToProcess[thisBible.abbreviation]:
        ourTidyBBB = bookAbbreviation( BBB, thisBible.abbreviation )
        NT = bos_books_codes_py.is_new_testament_nr( BBB )
        # print( f"{BBB=} {state.BBBsToProcess[thisBible.abbreviation]}"); print( len(BBBsToProcess) )
        # if not allBooksFlag: thisBible.loadBookIfNecessary( BBB )

        # if thisBible.abbreviation=='OET-LV' \
        # and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"AA Skipped OET chapters difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
        if thisBibleBooksToLoad not in (['ALL'],['OT'],['NT']) \
        and BBB not in thisBibleBooksToLoad:
            logging.error( f"VV Skipped difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for {thisBible.abbreviation} {BBB}…" )
        processedBBBs.append( BBB )

        try: # May give ValueError if this book doesn't not occur in this translation
            bkIx = iBkList.index( BBB )
            bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
            bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''
        except ValueError: # this BBB wasn't there in the list for this work
            bkPrevNav = f'''<a title="Previous (book index)" href="index.htm#Top">◄</a> '''
            bkNextNav = f' <a title="Next (first existing book)" href="{iBkList[1]}.htm#Top">►</a>'

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">{thisBible.abbreviation} {ourTidyBBB}</span>{bkNextNav}</p>{f'{NEWLINE}{state.JAMES_NAME_NOTE_HTML_PARAGRAPH}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{NEWLINE}{state.OET_UNFINISHED_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET' else f'{NEWLINE}{state.RV_ONLY_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET-RV' else f'{NEWLINE}{state.LV_ONLY_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET-LV' else '' if bos_books_codes_py.is_single_chapter_book(BBB) else state.WHOLE_BOOK_WARNING_HTML_PARAGRAPH}{f'{state.BLACK_LETTER_FONT_HTML_PARAGRAPH}{NEWLINE}' if thisBible.abbreviation=='KJB-1611' else ''}'''
        verseEntryList, contextList = thisBible.getContextVerseData( (BBB,) )
        textHtml = convertVerseEntryListToHtml( level, thisBible.abbreviation, (BBB,), 'book', contextList, verseEntryList, basicOnly=False, state=state, livenWordLinks=isinstance( thisBible, ESFMBible.ESFMBible ) or thisBible.abbreviation in ('BSB','MSB'), colouriseWordClasses=False, addNoLinkYetSpans=False )
        # textHtml = livenIORs( BBB, textHtml )
        if thisBible.abbreviation == 'OET-RV':
            textHtml = f'''{do_OET_RV_HTMLcustomisations( f'BookB={BBB}', textHtml )}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>'''
        elif thisBible.abbreviation == 'OET-LV':
            textHtml = f'''{do_OET_LV_HTMLcustomisations( f'BookB={BBB}', textHtml )}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>'''
        elif thisBible.abbreviation == 'LSV':
            textHtml = do_LSV_HTMLcustomisations( f'BookB={BBB}', textHtml )
        elif thisBible.abbreviation == 'T4T':
            textHtml = do_T4T_HTMLcustomisations( f'BookB={BBB}', textHtml )
        elif thisBible.abbreviation == 'SR-GNT':
            # print( f"Have SR-GNT {BBB} book {verseEntryList=}" )
            startIndex = 0
            while True:
                match = CV_REGEX.search( textHtml, startIndex )
                if not match: break
                C, V = match.group(1), match.group(2)
                ix = textHtml.index( '<span class="SR-GNT_verseTextChunk">', match.end() ) + 36 # chars in search string
                textHtml = f'''{textHtml[:ix]}<a title="Go to the GreekCNTR collation page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">{textHtml[ix:].replace( '</span>', '</a></span>', 1 )}'''
                startIndex = ix + 99 # Approx number of added characters
        bkHtml = f'{bkHtml}{textHtml}'
        filename = f'{BBB}.htm'
        processedFilenames.append( filename )
        # BBBLinks.append( f'<a title="{bos_books_codes_py.get_english_name_nr(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>' )
        filepath = folder.joinpath( filename )
        top = makeTop( level, thisBible.abbreviation, 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"{thisBible.abbreviation} {ourTidyBBB} book{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book, document, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc/{filename}#Top">{thisBible.abbreviation}</a>''',
                          f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        bkHtml = f'''{top}<!--book page-->
{f'<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>\n' if 'OET' in thisBible.abbreviation else ''}{navBookListParagraph}
{bkHtml}
{makeBottom( level, thisBible.abbreviation, 'book' )}'''
        assert checkHtml( f'Book {thisBible.abbreviation} {BBB}', bkHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now create an overall index page
    filename = 'index.htm'
    processedFilenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'bookIndex', 'byDoc', state ) \
            .replace( '__TITLE__', f"{thisBible.abbreviation} Book View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book, document' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc">{thisBible.abbreviation}</a>''',
                      f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">↑{thisBible.abbreviation}</a>''' )
    indexHtml = f'''{top}
{f'<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>\n' if 'OET' in thisBible.abbreviation else ''}<h1 id="Top">{thisBible.abbreviation} book pages</h1>
<h2>Index of books</h2>
{state.WHOLE_BOOKS_WARNING_HTML_PARAGRAPH}{f'<a title="See design specs on OET main site" href="https://OpenEnglishTranslation.Bible/Design/{'Readers' if thisBible.abbreviation=='OET-RV' else 'Literal'}Version"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>' if 'OET' in thisBible.abbreviation else ''}{f'{NEWLINE}{state.JAMES_NAME_NOTE_HTML_PARAGRAPH}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{NEWLINE}{state.OET_UNFINISHED_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET' else f'{NEWLINE}{state.RV_ONLY_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET-RV' else f'{NEWLINE}{state.LV_ONLY_BOOK_WARNING_HTML_PARAGRAPH}' if thisBible.abbreviation=='OET-LV' else state.WHOLE_BOOK_WARNING_HTML_PARAGRAPH}
{navBookListParagraph}
{makeBottom( level, thisBible.abbreviation, 'bookIndex' )}'''
    assert checkHtml( f'{thisBible.abbreviation} book index', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages() finished processing {len(processedBBBs)} {thisBible.abbreviation} books: {processedBBBs}." )
    return processedFilenames
# end of createBookPages.createBookPages



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createBookPages object
    pass
# end of createBookPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createBookPages object
    pass
# end of createBookPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createBookPages.py
