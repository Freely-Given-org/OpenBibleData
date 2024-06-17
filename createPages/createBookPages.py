#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createBookPages.py
#
# Module handling OpenBibleData createBookPages functions
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
Module handling createBookPages functions.

CHANGELOG:
    2023-08-30 Added FRT processing for RV
    2023-12-21 Keep book selection line at top of page
    2024-01-08 Fixed bug when moving to previous/next books for 'ALL' books
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from settings import State, TEST_MODE, reorderBooksForOETVersions, OET_UNFINISHED_WARNING_HTML_PARAGRAPH, JAMES_NOTE_HTML_PARAGRAPH
from usfm import convertUSFMMarkerListToHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from OETHandlers import livenOETWordLinks, getOETTidyBBB, getHebrewWordpageFilename, getGreekWordpageFilename


LAST_MODIFIED_DATE = '2024-06-14' # by RJH
SHORT_PROGRAM_NAME = "createBookPages"
PROGRAM_NAME = "OpenBibleData createBookPages functions"
PROGRAM_VERSION = '0.56'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETBookPages( level:int, folder:Path, rvBible, lvBible, state:State ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    # rvBooks = rvBible.books.keys() if 'ALL' in state.booksToLoad[rvBible.abbreviation] else state.booksToLoad[rvBible.abbreviation]
    # lvBooks = lvBible.books.keys() if 'ALL' in state.booksToLoad[lvBible.abbreviation] else state.booksToLoad[lvBible.abbreviation]
    # BBBsToProcess = reorderBooksForOETVersions( [rvKey for rvKey in rvBooks if rvKey in lvBooks] )
    # print( f"{rvBooks=} {lvBooks=} {BBBsToProcess=}" ); halt
    # iBkList1 = ['index'] + ( list(state.preloadedBibles[rvBible.abbreviation].books.keys()) 
    #                         if len(state.preloadedBibles[rvBible.abbreviation].books)<len(state.preloadedBibles[lvBible.abbreviation].books)
    #                         else list(state.preloadedBibles[lvBible.abbreviation].books.keys()) )
    # assert iBkList == BBBsToProcess
    # print( f"OET {BBBsToProcess=} {iBkList=}" )
    iBkList = ['index'] + state.BBBsToProcess['OET']
    # print( f"{iBkList=}" ); halt
    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks['OET'], 'OET', state)

    processedBBBs, processedFilenames = [], []
    for BBB in state.BBBsToProcess['OET']:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    createOETBookPages {BBB=} {state.BBBsToProcess['OET']} out of {len(state.BBBsToProcess['OET'])}" )
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        ourTidyBBB = getOETTidyBBB( BBB )
        ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )

        # # TODO: Can we delete all this now???
        # if lvBible.abbreviation=='OET-LV' \
        # and BBB in ('INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"A Skipped OET chapters difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
        if rvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[rvBible.abbreviation] \
        and BBB not in state.booksToLoad[rvBible.abbreviation]:
            logging.critical( f"B Skipped OET chapters not-included book: OET-RV {BBB}")
            continue # Only create pages for the requested RV books
        if BBB == 'FRT': # We want this, even though the LV doesn't (yet?) have any FRT
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating book page for OET {BBB}…" )
            processedBBBs.append( BBB )
            # iBkList = ['index'] + state.booksToLoad[rvBible.abbreviation]
            try: # May give ValueError if this book doesn't not occur in this translation
                bkIx = iBkList.index( BBB )
                bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
                bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''
            except ValueError: # this BBB wasn't there in the list for this work
                bkPrevNav = f'''<a title="Previous (book index)" href="index.htm#Top">◄</a> '''
                bkNextNav = f' <a title="Next (first existing book)" href="{iBkList[1]}.htm#Top">►</a>'

            bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">{rvBible.abbreviation} {ourTidyBBBwithNotes}</span>{bkNextNav}</p>
{JAMES_NOTE_HTML_PARAGRAPH}
{OET_UNFINISHED_WARNING_HTML_PARAGRAPH}'''
            verseEntryList, contextList = rvBible.getContextVerseData( (BBB,) )
            assert isinstance( rvBible, ESFMBible.ESFMBible )
            verseEntryList = livenOETWordLinks( level, rvBible, BBB, verseEntryList, state )
            textHtml = convertUSFMMarkerListToHtml( level, rvBible.abbreviation, (BBB,), 'book', contextList, verseEntryList, basicOnly=False, state=state )
            # textHtml = livenIORs( BBB, textHtml )
            textHtml = do_OET_RV_HTMLcustomisations( textHtml )
            bkHtml = f'{bkHtml}{textHtml}'
            filename = f'{BBB}.htm'
            processedFilenames.append( filename )
            # BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}#Top">{ourTidyBBBwithNotes}</a>''' )
            filepath = folder.joinpath( filename )
            top = makeTop( level, rvBible.abbreviation, 'book', f'byDoc/{filename}', state ) \
                    .replace( '__TITLE__', f"{rvBible.abbreviation} {ourTidyBBB} book{' TEST' if TEST_MODE else ''}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {rvBible.abbreviation}, front matter, book, document' ) \
                    .replace( f'''<a title="{state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/byDoc/{filename}#Top">{rvBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/">↑{rvBible.abbreviation}</a>''' )
            bkHtml = f'''{top}<!--book page-->
{navBookListParagraph}
{bkHtml}
{makeBottom( level, 'book', state )}'''
            checkHtml( f'OET Book FRT {rvBible.abbreviation} {BBB}', bkHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
                bkHtmlFile.write( bkHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
            continue
        elif lvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
        and BBB not in state.booksToLoad[lvBible.abbreviation]:
            logging.critical( f"C Skipped OET chapters not-included book: OET-LV {BBB}")
            continue # Only create pages for the requested LV books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for OET {BBB}…" )
        processedBBBs.append( BBB )

        bkIx = iBkList.index( BBB )
        bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
        bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">Open English Translation {ourTidyBBBwithNotes}</span>{bkNextNav}</p>
{f'{JAMES_NOTE_HTML_PARAGRAPH}{NEWLINE}' if BBB=='JAM' else ''}{OET_UNFINISHED_WARNING_HTML_PARAGRAPH}
<div class="RVLVcontainer">
<h2>Readers’ Version</h2>
<h2>Literal Version <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>'''
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,) )
        lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB,) )
        assert isinstance( rvBible, ESFMBible.ESFMBible )
        rvVerseEntryList = livenOETWordLinks( level, rvBible, BBB, rvVerseEntryList, state )
        assert isinstance( lvBible, ESFMBible.ESFMBible )
        lvVerseEntryList = livenOETWordLinks( level, lvBible, BBB, lvVerseEntryList, state )
        # NOTE: We change the version abbreviation here to give the function more indication where we're coming from
        rvHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET-RV', (BBB,), 'book', rvContextList, rvVerseEntryList, basicOnly=False, state=state ) )
        tempLVHtml = convertUSFMMarkerListToHtml( level, 'OET-LV', (BBB,), 'book', lvContextList, lvVerseEntryList, basicOnly=False, state=state )
        if '+' in tempLVHtml: print( f"HAVE_PLUS {tempLVHtml[max(0,tempLVHtml.index('+')-30):tempLVHtml.index('+')+90]}" )
        if '^' in tempLVHtml: print( f"HAVE_HAT {tempLVHtml[max(0,tempLVHtml.index('^')-30):tempLVHtml.index('^')+90]}" )
        if '~' in tempLVHtml: print( f"HAVE_SQUIG {tempLVHtml[max(0,tempLVHtml.index('~')-30):tempLVHtml.index('~')+90]}" )
        lvHtml = do_OET_LV_HTMLcustomisations( tempLVHtml )
        # lvHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET', (BBB,), 'book', lvContextList, lvVerseEntryList, basicOnly=False, state=state ) )

        # Now we have to divide the RV and the LV into an equal number of chunks (so they mostly line up)
        # First get the header and intro chunks
        ixBHend = rvHtml.index( '<!--bookHeader-->' ) + 17
        ixBIend = rvHtml.index( '<!--bookIntro-->', ixBHend ) + 16
        rvSections = [ rvHtml[:ixBHend], rvHtml[ixBHend:ixBIend] ] + rvHtml[ixBIend:].split( '<div class="s1">' )
        ixBHend = lvHtml.index( '<!--bookHeader-->' ) + 17
        try: ixBIend = lvHtml.index( '<!--bookIntro-->', ixBHend ) + 16 # No intro expected in OET-LV
        except ValueError: ixBIend = lvHtml.index( '<span id="C', ixBHend )
        lvChunks, lvRest = [ lvHtml[:ixBHend], lvHtml[ixBHend:ixBIend] ], lvHtml[ixBIend:]
        # Now try to match the rv sections
        for n,rvSectionHtml in enumerate( rvSections[2:] ): # continuing on AFTER the introduction
            # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\n{BBB} {n}: {rvSectionHtml=}" )
            try:
                CclassIndex1 = rvSectionHtml.index( 'id="C' )
                CclassIndex2 = rvSectionHtml.index( '"', CclassIndex1+4 )
                rvStartCV = rvSectionHtml[CclassIndex1+4:CclassIndex2]
                CclassIndex8 = rvSectionHtml.rindex( 'id="C' )
                CclassIndex9 = rvSectionHtml.index( '"', CclassIndex8+4 )
                rvEndCV = rvSectionHtml[CclassIndex8+4:CclassIndex9]
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n  {BBB} {n:,}: {rvStartCV=} {rvEndCV=}")
            except ValueError:
                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages {BBB} {n:,}: No Cid in {rvSectionHtml=}" )
                rvStartCV, rvEndCV = '', 'C1'
                # halt
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"""\nSearching for OET-RV {BBB} ' id="{rvEndCV}"' in '{lvRest}'""" )
            try: ixEndCV = lvRest.rindex( f' id="{rvEndCV}"' )
            except ValueError: # Versification problem if this fails
                logging.warning( f"{BBB} Possible versification problem around {rvEndCV} -- we'll try to handle it." )
                # Let's try for the previous verse -- at least this solves Gen 31:55 not there
                frontBit, backBit = rvEndCV.split( 'V' )
                adjustedRvEndCV = f'{frontBit}V{int(backBit)-1}'
                logging.info( f"{BBB} ixEndCV is now decreased by one verse from '{rvEndCV}' to '{adjustedRvEndCV}'" )
                try: ixEndCV = lvRest.rindex( f' id="{adjustedRvEndCV}"' ) # If this fails, we give up trying to fix versification problem
                except ValueError: # second level 'except'
                    logging.error( f"Gave up trying to fix OET book versification for {BBB} section RV {rvStartCV}-{rvEndCV}")
                    ixEndCV = len(lvRest) - 1 # Will this work???
            try: ixNextCV = lvRest.index( f' id="C', ixEndCV+5 )
            except ValueError: ixNextCV = len( lvRest ) - 1
            # print( f"\n{BBB} {n}: {lvRest[ixEndCV:ixNextCV]=} {lvRest[ixNextCV:ixNextCV+10]=}" )
            # Find our way back to the start of the HTML marker
            for x in range( 30 ):
                lvIndex8 = ixNextCV - x
                if lvRest[lvIndex8] == '<':
                    break
            else:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvRest[lvIndex8-50:lvIndex8+50]}")
                not_far_enough
            # print( f"\n{n}: {lvRest[ixEndCV:lvIndex8]=}" )
            lvEndIx = lvIndex8
            # TODO: Work out why we need these next two sets of lines
            if lvRest[lvEndIx:].startswith( '</span>'): # Occurs at end of MRK (perhaps because of missing SR verses in ending) -- not sure if in other places
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\nNOTE: Fixed </span> end of {BBB} {rvStartCV=} {rvEndCV=} chunk in OET!!! {lvEndIx=} {ixNextCV=}" )
                lvEndIx = ixNextCV + 1
            elif lvRest[lvEndIx:].startswith( '</a>'): # Occurs at end of MAT Why????
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\nNOTE: Fixed </a> end of {BBB} {rvStartCV=} {rvEndCV=} chunk in OET!!! {lvEndIx=} {ixNextCV=}" )
                lvEndIx = ixNextCV + 1
            lvChunk = lvRest[:lvEndIx]
            # Make sure that our split was at a sensible place
            rsLvChunk = lvChunk.rstrip()
            if ixEndCV != len(lvRest)-1: # from second level 'except' above
                assert rsLvChunk[-1]=='>' \
                or (rsLvChunk[-2]=='>' and rsLvChunk[-1] in '.,') \
                or (BBB in ('GENx','RUTx','JNAx','ESTx') and rsLvChunk[-1]=='.'), f"{BBB} {n=} {rvStartCV=} {rvEndCV=} {lvChunk[-40:]=} {lvRest[lvEndIx:lvEndIx+30]=}"
                # Fails on JNA n=4 rvStartCV='C4' rvEndCV='C4V11' lvChunk[-8:]='eat(fs).'
            lvChunks.append( lvChunk )
            lvRest = lvRest[lvEndIx:]

        assert len(lvChunks) == len(rvSections), f"{len(lvChunks)=} {len(rvSections)=}"

        # Now put all the chunks together
        combinedHtml = ''
        for rvSection,lvChunk in zip( rvSections, lvChunks, strict=True ):
            if rvSection.startswith( '<div class="rightBox">' ):
                rvSection = f'<div class="s1">{rvSection}' # This got removed above
            checkHtml( f"OET-RV {BBB} Section", rvSection, segmentOnly=True )
            checkHtml( f"OET-LV {BBB} Chunk", lvChunk, segmentOnly=True )
            combinedHtml = f'''{combinedHtml}<div class="chunkRV">{rvSection}</div><!--chunkRV-->
<div class="chunkLV">{lvChunk}</div><!--chunkLV-->
'''
        filename = f'{BBB}.htm'
        processedFilenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( level, 'OET', 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"OET {ourTidyBBB}{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, book, document, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc/{filename}#Top">OET</a>''',
                          f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET/">↑OET</a>''' )
        bkHtml = f'''{top}<!--book page-->
{navBookListParagraph}
{bkHtml}{removeDuplicateCVids( BBB, combinedHtml )}</div><!--RVLVcontainer-->
{makeBottom( level, 'book', state )}'''
        checkHtml( f'OET Book {BBB}', bkHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now create an overall index page
    filename = 'index.htm'
    processedFilenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'bookIndex', 'byDoc', state ) \
            .replace( '__TITLE__', f"OET Document View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, OET, Open English Translation, book, document' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc">OET</a>''',
                      f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
    indexHtml = f'''{top}
<h1 id="Top">OET book pages</h1>
<h2>Index of books</h2>
{navBookListParagraph}
{makeBottom( level, 'bookIndex', state )}'''
    checkHtml( 'OETBooksIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages() finished processing {len(processedBBBs)} OET books: {processedBBBs}." )
    return processedFilenames
# end of createBookPages.createOETBookPages


def createBookPages( level:int, folder:Path, thisBible, state:State ) -> List[str]:
    """
    This creates a page for each book for all versions other than 'OET'
                                which is considerably more complex (above).
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createBookPages( {level}, {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    # BBBsToProcess = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
    #             else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
    #             else thisBibleBooksToLoad
    # if 'OET' in thisBible.abbreviation:
    #     BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    iBkList = ['index'] + list( state.preloadedBibles[thisBible.abbreviation].books.keys() )
    # print( f"{thisBible.abbreviation=} {BBBsToProcess=} {iBkList=}" )
    navBookListParagraph = makeBookNavListParagraph( state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state )

    processedBBBs, processedFilenames = [], []
    for BBB in state.BBBsToProcess[thisBible.abbreviation]:
        ourTidyBBB = getOETTidyBBB( BBB )
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
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

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for {thisBible.abbreviation} {BBB}…" )
        processedBBBs.append( BBB )

        try: # May give ValueError if this book doesn't not occur in this translation
            bkIx = iBkList.index( BBB )
            bkPrevNav = f'''<a title="Previous {'(book index)' if bkIx==1 else 'book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
            bkNextNav = f' <a title="Next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''
        except ValueError: # this BBB wasn't there in the list for this work
            bkPrevNav = f'''<a title="Previous (book index)" href="index.htm#Top">◄</a> '''
            bkNextNav = f' <a title="Next (first existing book)" href="{iBkList[1]}.htm#Top">►</a>'

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">{thisBible.abbreviation} {ourTidyBBB}</span>{bkNextNav}</p>{f'{NEWLINE}{JAMES_NOTE_HTML_PARAGRAPH}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{NEWLINE}{OET_UNFINISHED_WARNING_HTML_PARAGRAPH}' if 'OET' in thisBible.abbreviation else ''}'''
        verseEntryList, contextList = thisBible.getContextVerseData( (BBB,) )
        if isinstance( thisBible, ESFMBible.ESFMBible ):
            verseEntryList = livenOETWordLinks( level, thisBible, BBB, verseEntryList, state )
        textHtml = convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,), 'book', contextList, verseEntryList, basicOnly=False, state=state )
        # textHtml = livenIORs( BBB, textHtml )
        if thisBible.abbreviation == 'OET-RV':
            textHtml = do_OET_RV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'OET-LV':
            textHtml = do_OET_LV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'LSV':
            textHtml = do_LSV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'T4T':
            textHtml = do_T4T_HTMLcustomisations( textHtml )
        bkHtml = f'{bkHtml}{textHtml}'
        filename = f'{BBB}.htm'
        processedFilenames.append( filename )
        # BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>' )
        filepath = folder.joinpath( filename )
        top = makeTop( level, thisBible.abbreviation, 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"{thisBible.abbreviation} {ourTidyBBB} book{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book, document, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc/{filename}#Top">{thisBible.abbreviation}</a>''',
                          f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        bkHtml = f'''{top}<!--book page-->
{navBookListParagraph}
{bkHtml}
{makeBottom( level, 'book', state )}'''
        checkHtml( f'Book {thisBible.abbreviation} {BBB}', bkHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now create an overall index page
    filename = 'index.htm'
    processedFilenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'bookIndex', 'byDoc', state ) \
            .replace( '__TITLE__', f"{thisBible.abbreviation} Book View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book, document' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc">{thisBible.abbreviation}</a>''',
                      f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">↑{thisBible.abbreviation}</a>''' )
    indexHtml = f'''{top}
<h1 id="Top">{thisBible.abbreviation} book pages</h1>
<h2>Index of books</h2>
{navBookListParagraph}
{makeBottom( level, 'bookIndex', state)}'''
    checkHtml( f'{thisBible.abbreviation} book index', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

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
