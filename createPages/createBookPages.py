#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createBookPages.py
#
# Module handling OpenBibleData createBookPages functions
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
Module handling createBookPages functions.
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

from usfm import convertUSFMMarkerListToHtml
from html import do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, removeDuplicateCVids, checkHtml


LAST_MODIFIED_DATE = '2023-02-07' # by RJH
SHORT_PROGRAM_NAME = "createBookPages"
PROGRAM_NAME = "OpenBibleData createBookPages functions"
PROGRAM_VERSION = '0.16'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETBookPages( folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETBookPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBs, filenames = [], []
    allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    BBBsToProcess = rvBible.books.keys() if allBooksFlag else state.booksToLoad[rvBible.abbreviation]
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(BBBsToProcess) )
        if not allBooksFlag: rvBible.loadBookIfNecessary( BBB )
        lvBible.loadBookIfNecessary( BBB )

        # TODO: Can we delete all this now???
        if lvBible.abbreviation=='OET-LV' \
        and BBB in ('INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"A Skipped OET chapters difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if rvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[rvBible.abbreviation] \
        and BBB not in state.booksToLoad[rvBible.abbreviation]:
            logging.critical( f"B Skipped OET chapters not-included book: OET-RV {BBB}")
            continue # Only create pages for the requested RV books
        if lvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
        and BBB not in state.booksToLoad[lvBible.abbreviation]:
            logging.critical( f"C Skipped OET chapters not-included book: OET-LV {BBB}")
            continue # Only create pages for the requested LV books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for OET {BBB}…" )
        BBBs.append( BBB )
        bkHtml = f'''<h1>Open English Translation {tidyBBB}</h1>
<div class="container">
<span> </span>
<div class="buttons">
    <button type="button" id="underlineButton" onclick="hide_show_underlines()">Hide underlines</button>
</div><!--buttons-->
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
'''
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,) )
        lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB,) )
        rvHtml = livenIORs( convertUSFMMarkerListToHtml( 'OET', (BBB,), 'book', rvContextList, rvVerseEntryList ) )
        lvHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( 'OET', (BBB,), 'book', lvContextList, lvVerseEntryList ) )

        # Now we have to divide the RV and the LV into an equal number of chunks (so they mostly line up)
        # First get the header and intro chunks
        ixBHend = rvHtml.index( '<!--bookHeader-->\n' ) + 18
        ixBIend = rvHtml.index( '<!--bookIntro-->\n', ixBHend ) + 17
        rvSections = [ rvHtml[:ixBHend], rvHtml[ixBHend:ixBIend] ] + rvHtml[ixBIend:].split( '<div class="s1">' )
        ixBHend = lvHtml.index( '<!--bookHeader-->\n' ) + 18
        try: ixBIend = lvHtml.index( '<!--bookIntro-->\n', ixBHend ) + 17 # No intro expected in OET-LV
        except ValueError: ixBIend = lvHtml.index( '<span id="C', ixBHend )
        lvChunks, lvRest = [ lvHtml[:ixBHend], lvHtml[ixBHend:ixBIend] ], lvHtml[ixBIend:]
        # Now try to match the rv sections
        for n,rvSectionHtml in enumerate( rvSections[2:] ):
            # print( f"\n{n}: {rvSectionHtml=}" )
            try:
                CclassIndex1 = rvSectionHtml.index( 'id="C' )
                CclassIndex2 = rvSectionHtml.index( '"', CclassIndex1+4 )
                rvStartCV = rvSectionHtml[CclassIndex1+4:CclassIndex2]
                CclassIndex8 = rvSectionHtml.rindex( 'id="C' )
                CclassIndex9 = rvSectionHtml.index( '"', CclassIndex8+4 )
                rvEndCV = rvSectionHtml[CclassIndex8+4:CclassIndex9]
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n  {BBB} {n:,}: {rvStartCV=} {rvEndCV=}")
            except ValueError:
                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {n:,}: No Cid in {rvSectionHtml=}" )
                rvStartCV, rvEndCV = '', 'C1'
                # halt
            ixEndCV = lvRest.rindex( f' id="{rvEndCV}"' )
            try: ixNextCV = lvRest.index( f' id="C', ixEndCV+5 )
            except ValueError: ixNextCV = len( lvRest ) - 1
            # print( f"\n{n}: {lvRest[ixEndCV:ixNextCV+10]=}" )
            # Find our way back to the start of the HTML marker
            for x in range( 30 ):
                LVindex8 = ixNextCV - x
                if lvRest[LVindex8] == '<':
                    break
            else:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvRest[LVindex8-50:LVindex8+50]}")
                not_far_enough
            # print( f"\n{n}: {lvRest[ixEndCV:LVindex8]=}" )
            lvChunks.append( lvRest[:LVindex8])
            lvRest = lvRest[LVindex8:]

        assert len(lvChunks) == len(rvSections), f"{len(lvChunks)=} {len(rvSections)=}"

        # Now put all the chunks together
        combinedHtml = ''
        for rvSection,lvChunk in zip( rvSections, lvChunks, strict=True ):
            if rvSection.startswith( '<div class="rightBox">' ):
                rvSection = f'<div class="s1">{rvSection}' # This got removed above
            combinedHtml = f'''{combinedHtml}<div class="chunkRV">{rvSection}</div><!--chunkRV-->
<div class="chunkLV">{lvChunk}</div><!--chunkLV-->
'''
        filename = f'{BBB}.html'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( 3, 'OETbook', f'byDocument/{filename}', state ) \
                .replace( '__TITLE__', f'OET {tidyBBB}' ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, book' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*3}versions/OET/byDocument/{filename}">OET</a>''',
                          f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*3}versions/OET/">↑OET</a>''' )
        bkHtml = top + '<!--book page-->' \
                    + bkHtml + removeDuplicateCVids( combinedHtml ) \
                    + '</div><!--container-->\n' \
                    + makeBottom( 3, 'OETbook', state )
        checkHtml( 'OETbook', bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
    # Now create index pages for each book and then an overall one
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, "    Creating book index pages for OET…" )
    BBBLinks = []
    for BBB in BBBs:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        filename = f'{BBB}.html'
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
    filename = 'index.html'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'OETbook', None, state ) \
            .replace( '__TITLE__', f'OET Chapter View' ) \
            .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapters' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*3}versions/OET">OET</a>''', 'OET' )
    indexHtml = top \
                + '<h1>OET book pages</h1><h2>Index of books</h2>\n' \
                + f'<p class="bLinks">{EM_SPACE.join( BBBLinks )}</p>\n' \
                + makeBottom( 3, 'OETbook', state )
    checkHtml( 'OETBooksIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages() finished processing {len(BBBs)} OET books: {BBBs}" )
    return filenames
# end of createBookPages.createOETBookPages

def createBookPages( folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each book for all versions
        other than 'OET' which is considerably more complex (above).
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createBookPages( {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages( {folder}, {thisBible.abbreviation} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBs, filenames = [], []
    allBooksFlag = 'ALL' in state.booksToLoad[thisBible.abbreviation]
    BBBsToProcess = thisBible.books.keys() if allBooksFlag else state.booksToLoad[thisBible.abbreviation]
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(BBBsToProcess) )
        if not allBooksFlag: thisBible.loadBookIfNecessary( BBB )
        # if not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ): continue # Skip all except NT for now
        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"AA Skipped OET chapters difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if thisBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[thisBible.abbreviation] \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped chapters difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for {thisBible.abbreviation} {BBB}…" )
        BBBs.append( BBB )
        bkHtml = f'''<h1>{thisBible.abbreviation} {tidyBBB}</h1>
'''
        verseEntryList, contextList = thisBible.getContextVerseData( (BBB,) )
        textHtml = convertUSFMMarkerListToHtml( thisBible.abbreviation, (BBB,), 'book', contextList, verseEntryList )
        textHtml = livenIORs( textHtml )
        if thisBible.abbreviation == 'OET-LV':
            textHtml = do_OET_LV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'LSV':
            textHtml = do_LSV_HTMLcustomisations( textHtml )
        bkHtml = f'{bkHtml}{textHtml}'
        filename = f'{BBB}.html'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( 3, 'book', f'byDocument/{filename}', state ) \
                .replace( '__TITLE__', f'{thisBible.abbreviation} {tidyBBB} book' ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDocument/{filename}">{thisBible.abbreviation}</a>''',
                          f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        bkHtml = top + '<!--book page-->' + bkHtml + '\n' + makeBottom( 3, 'book', state )
        checkHtml( thisBible.abbreviation, bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
    # Now create index pages for each book and then an overall one
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating book index pages for {thisBible.abbreviation}…" )
    BBBLinks = []
    for BBB in BBBs:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        filename = f'{BBB}.html'
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
    # Create index page
    filename = 'index.html'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'book', None, state ) \
            .replace( '__TITLE__', f'{thisBible.abbreviation} Book View' ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    indexHtml = top \
                + '<h1>Book pages</h1><h2>Index of books</h2>\n' \
                + f'<p class="bLinks">{EM_SPACE.join( BBBLinks )}</p>\n' \
                + makeBottom(3, 'book', state)
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}" )
    return filenames
# end of createBookPages.createBookPages


def livenIORs( bookHTML:str ) -> str:
    """
    """
    assert '\\ior' not in bookHTML

    searchStartIx = 0
    while True:
        ixSpanStart = bookHTML.find( '<span class="ior">', searchStartIx )
        if ixSpanStart == -1: break
        ixEnd = bookHTML.find( '</span>', ixSpanStart+18 )
        assert ixEnd != -1
        guts = bookHTML[ixSpanStart+18:ixEnd].replace('–','-') # Convert any en-dash to hyphen
        # print(f"{BBB} {guts=} {bookHTML[ix-20:ix+20]} {searchStartIx=} {ixSpanStart=} {ixEnd=}")
        startGuts = guts.split('-')[0]
        # print(f"  Now {guts=}")
        if ':' in startGuts:
            assert startGuts.count(':') == 1 # We expect a single C:V at this stage
            Cstr, Vstr = startGuts.strip().split( ':' )
        else: Cstr, Vstr = startGuts.strip(), '1' # Only a chapter was given
        new_guts = f'<a href="#C{Cstr}V{Vstr}">{guts}</a>'
        bookHTML = f'{bookHTML[:ixSpanStart+18]}{new_guts}{bookHTML[ixEnd:]}'
        searchStartIx = ixEnd + 10

    return bookHTML
# end of createBookPages.livenIORs function


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
