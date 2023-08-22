#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createBookPages.py
#
# Module handling OpenBibleData createBookPages functions
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
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from usfm import convertUSFMMarkerListToHtml
from Bibles import tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from createOETReferencePages import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-06-06' # by RJH
SHORT_PROGRAM_NAME = "createBookPages"
PROGRAM_NAME = "OpenBibleData createBookPages functions"
PROGRAM_VERSION = '0.35'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETBookPages( level:int, folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    BBBsToProcess = reorderBooksForOETVersions( rvBible.books.keys() if allBooksFlag else state.booksToLoad[rvBible.abbreviation] )
    BBBs, filenames = [], []
    for BBB in BBBsToProcess:
        ourTidyBBB = tidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(BBBsToProcess) )
        # if not allBooksFlag: rvBible.loadBookIfNecessary( BBB )
        # lvBible.loadBookIfNecessary( BBB )

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

        iBkList = ['index'] + ( state.booksToLoad[rvBible.abbreviation] if len(state.booksToLoad[rvBible.abbreviation])<len(state.booksToLoad[lvBible.abbreviation]) else state.booksToLoad[lvBible.abbreviation] )
        bkIx = iBkList.index( BBB )
        bkPrevNav = f'''<a title="Go to {'book index' if bkIx==1 else 'previous book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
        bkNextNav = f' <a title="Go to next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">Open English Translation {ourTidyBBB}</span>{bkNextNav}</p>
<p class="rem">This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.</p>
<div class="container">
<span> </span>
<div class="buttons">
    <button type="button" id="marksButton" onclick="hide_show_marks()">Hide marks</button>
</div><!--buttons-->
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
  '''
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,) )
        lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB,) )
        if isinstance( rvBible, ESFMBible.ESFMBible ):
            rvVerseEntryList = livenOETWordLinks( rvBible, BBB, rvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
        if isinstance( lvBible, ESFMBible.ESFMBible ):
            lvVerseEntryList = livenOETWordLinks( lvBible, BBB, lvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
        rvHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET', (BBB,), 'book', rvContextList, rvVerseEntryList, basicOnly=False, state=state ) )
        lvHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET', (BBB,), 'book', lvContextList, lvVerseEntryList, basicOnly=False, state=state ) )

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
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"""Searching for ' id="{rvEndCV}"' in '{lvRest}'""" )
            ixEndCV = lvRest.rindex( f' id="{rvEndCV}"' ) # Versification problem if this fails
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
            if lvRest[lvEndIx:].startswith( '</span>'): # Occurs at end of MRK (perhaps because of missing SR verses in ending) -- not sure if in other places
                print( f"\nNOTE: Fixed end of chunk in OET {BBB}!!!" )
                lvEndIx = ixNextCV
            lvChunks.append( lvRest[:lvEndIx])
            lvRest = lvRest[lvEndIx:]

        assert len(lvChunks) == len(rvSections), f"{len(lvChunks)=} {len(rvSections)=}"

        # Now put all the chunks together
        combinedHtml = ''
        for rvSection,lvChunk in zip( rvSections, lvChunks, strict=True ):
            if rvSection.startswith( '<div class="rightBox">' ):
                rvSection = f'<div class="s1">{rvSection}' # This got removed above
            combinedHtml = f'''{combinedHtml}<div class="chunkRV">{rvSection}</div><!--chunkRV-->
<div class="chunkLV">{lvChunk}</div><!--chunkLV-->
'''
        filename = f'{BBB}.htm'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( level, 'OET', 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB}" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, book' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc/{filename}#Top">OET</a>''',
                          f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET/">↑OET</a>''' )
        bkHtml = f'''{top}<!--book page-->''' \
                    + bkHtml + removeDuplicateCVids( BBB, combinedHtml ) \
                    + '</div><!--container-->\n' \
                    + makeBottom( level, 'book', state )
        checkHtml( 'book', bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now create an overall index
    BBBLinks = []
    for BBB in BBBs:
        ourTidyBBB = tidyBBB( BBB )
        filename = f'{BBB}.htm'
        BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{filename}#Top">{ourTidyBBB}</a>''' )
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'book', 'byDoc', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Document View" ) \
            .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byDoc">OET</a>''',
                      f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
    indexHtml = top \
                + '<h1 id="Top">OET book pages</h1><h2>Index of books</h2>\n' \
                + f'''{makeBookNavListParagraph(BBBLinks, state)}\n''' \
                + makeBottom( level, 'book', state )
    checkHtml( 'OETBooksIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETBookPages() finished processing {len(BBBs)} OET books: {BBBs}." )
    return filenames
# end of createBookPages.createOETBookPages


def createBookPages( level:int, folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each book for all versions other than 'OET'
                                which is considerably more complex (above).
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createBookPages( {level}, {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    BBBsToProcess = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
                else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
                else thisBibleBooksToLoad
    if 'OET' in thisBible.abbreviation:
        BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )

    BBBs, filenames = [], []
    for BBB in BBBsToProcess:
        ourTidyBBB = tidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(BBBsToProcess) )
        # if not allBooksFlag: thisBible.loadBookIfNecessary( BBB )
        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"AA Skipped OET chapters difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if thisBibleBooksToLoad not in (['ALL'],['NT']) \
        and BBB not in thisBibleBooksToLoad:
            logging.critical( f"VV Skipped chapters difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating book pages for {thisBible.abbreviation} {BBB}…" )
        BBBs.append( BBB )

        iBkList = ['index'] + state.booksToLoad[thisBible.abbreviation]
        try: # May give ValueError if this book doesn't not occur in this translation
            bkIx = iBkList.index( BBB )
            bkPrevNav = f'''<a title="Go to {'book index' if bkIx==1 else 'previous book'}" href="{iBkList[bkIx-1]}.htm#Top">◄</a> ''' if bkIx>0 else ''
            bkNextNav = f' <a title="Go to next book" href="{iBkList[bkIx+1]}.htm#Top">►</a>' if bkIx<len(iBkList)-1 else ''
        except ValueError: # this BBB wasn't there in the list for this work
            bkPrevNav = f'''<a title="Go to book index" href="index.htm#Top">◄</a> '''
            bkNextNav = f' <a title="Go to first existing book" href="{iBkList[1]}.htm#Top">►</a>'

        bkHtml = f'''<p class="bkNav">{bkPrevNav}<span class="bkHead" id="Top">{thisBible.abbreviation} {ourTidyBBB}</span>{bkNextNav}</p>
{'<p class="rem">This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.</p>' if 'OET' in thisBible.abbreviation else ''}
'''
        verseEntryList, contextList = thisBible.getContextVerseData( (BBB,) )
        if isinstance( thisBible, ESFMBible.ESFMBible ):
            verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
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
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( level, thisBible.abbreviation, 'book', f'byDoc/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} book" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc/{filename}#Top">{thisBible.abbreviation}</a>''',
                          f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        bkHtml = top + '<!--book page-->' + bkHtml + '\n' + makeBottom( level, 'book', state )
        checkHtml( thisBible.abbreviation, bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
            bkHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now create an overall index
    BBBLinks = []
    for BBB in BBBs:
        ourTidyBBB = tidyBBB( BBB )
        filename = f'{BBB}.htm'
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>' )
    # Create index page
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'book', 'byDoc', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} Book View" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, book' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byDoc">{thisBible.abbreviation}</a>''',
                      f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">↑{thisBible.abbreviation}</a>''' )
    indexHtml = top \
                + f'<h1 id="Top">{thisBible.abbreviation} book pages</h1><h2>Index of books</h2>\n' \
                + f'''{makeBookNavListParagraph(BBBLinks, state)}\n''' \
                + makeBottom( level, 'book', state)
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as bkHtmlFile:
        bkHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createBookPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}." )
    return filenames
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
