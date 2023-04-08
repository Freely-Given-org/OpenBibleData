#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createChapterPages.py
#
# Module handling OpenBibleData createChapterPages functions
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
Module handling createChapterPages functions.
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
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from usfm import convertUSFMMarkerListToHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, removeDuplicateCVids, checkHtml
from createOETReferencePages import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-04-08' # by RJH
SHORT_PROGRAM_NAME = "createChapterPages"
PROGRAM_NAME = "OpenBibleData createChapterPages functions"
PROGRAM_VERSION = '0.32'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
# NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '


def createOETChapterPages( level:int, folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETChapterPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    BBBsToProcess = reorderBooksForOETVersions( rvBible.books.keys() if allBooksFlag else state.booksToLoad[rvBible.abbreviation] )
    BBBs, filenames = [], []
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
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

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for OET {BBB}…" )
        BBBs.append( BBB )
        numChapters = rvBible.getNumChapters( BBB )
        assert rvBible.getNumVerses( BBB, '-1' ) # OET always has intro
        assert not rvBible.getNumVerses( BBB, '0' ) # OET has no chapter zero
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for OET {BBB} {c}…" )
                documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm">{tidyBBB}</a>'
                if c == -1: # Intro
                    leftLink = ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C1.htm">→</a>' if c<numChapters else ''
                elif c == 0:
                    continue
                elif c == 1:
                    leftLink = f'<a title="Book introduction" href="{BBB}_Intro.htm">←</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm">→</a>' if c<numChapters else ''
                else: # c > 1
                    assert c > 1
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C{c-1}.htm">←</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm">→</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="../../pa/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">║</a>'''
                detailsLink = f' <a title="Show details about this work" href="../details.htm">©</a>'
                cHtml = f'''<h1 id="Top">Open English Translation {tidyBBB} Introduction</h1>
<p class="cnav">{leftLink}{documentLink} Intro{rightLink}{parallelLink}{detailsLink}</p>
<div class="container">
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
''' if c==-1 else f'''<h1 id="Top">Open English Translation {tidyBBB} Chapter {c}</h1>
<p class="cnav">{leftLink}{documentLink} {c}{rightLink}{parallelLink}{detailsLink}</p>
<div class="container">
<span> </span>
<div class="buttons">
    <button type="button" id="underlineButton" onclick="hide_show_underlines()">Hide underlines</button>
</div><!--buttons-->
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
'''
                try: rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    if c == 0: continue # Usually no chapter zero
                    logging.critical( f"No chapter found for {rvBible.abbreviation} {BBB} {c=}" )
                    halt # continue
                if isinstance( rvBible, ESFMBible.ESFMBible ):
                    rvVerseEntryList = livenOETWordLinks( rvBible, BBB, rvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm" )
                # print( f"OET-RV {BBB} {c} got {len(rvVerseEntryList)} verse entries, {len(rvContextList)} context entries")
                lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, str(c)) )
                if isinstance( lvBible, ESFMBible.ESFMBible ):
                    lvVerseEntryList = livenOETWordLinks( lvBible, BBB, lvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm" )
                # rvHtml = livenIORs( BBB, convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', rvContextList, rvVerseEntryList ), numChapters )
                rvHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', rvContextList, rvVerseEntryList, basicOnly=False, state=state ) )
                lvHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', lvContextList, lvVerseEntryList, basicOnly=False, state=state ) )
                rvHtml = '<div class="chunkRV">' + rvHtml + '</div><!--chunkRV-->\n'
                lvHtml = '<div class="chunkLV">' + lvHtml + '</div><!--chunkLV-->\n'
                combinedHtml = removeDuplicateCVids( BBB, f'{rvHtml}{lvHtml}' )
                filename = f'{BBB}_Intro.htm' if c==-1 else f'{BBB}_C{c}.htm'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, 'OET', 'chapter', f'byC/{filename}', state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {tidyBBB} introduction" if c==-1 else f"{'TEST ' if TEST_MODE else ''}OET {tidyBBB} chapter {c}" ) \
                        .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter' ) \
                        .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{filename}">OET</a>''',
                                  f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
                cHtml = top + '<!--chapter page-->' \
                            + cHtml + combinedHtml \
                            + '</div><!--container-->\n' \
                            + makeBottom( level, 'chapter', state )
                checkHtml( 'OETChapterIndex', cHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( cHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
        else:
            # TODO: Not completely finished yet
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETChapterPages {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT',)
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETChapterPages {rvBible.books[BBB]=}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for OET {BBB} {c}…" )
            # cHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
            # # verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
            verseEntryList, contextList = lvBible.getContextVerseData( (BBB, '-1') )
            if isinstance( lvBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( lvBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm" )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{lvBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            cHtml += convertUSFMMarkerListToHtml( (BBB,c), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )
            filename = f'{BBB}_C{c}.htm'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            top = makeTop( level, 'OET', 'chapter', f'byC/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                    .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{filename}">OET</a>''',
                                f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
            chtml = top + '<!--chapter page-->' + cHtml + makeBottom( level, 'chapter', state )
            checkHtml( chtml )
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
            halt
    # Now create index pages for each book and then an overall one
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "    Creating chapter index pages for OET…" )
    BBBLinks = []
    for BBB in BBBs:
        filename = f'{BBB}.htm'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
        numChapters = rvBible.getNumChapters( BBB )
        cLinks = []
        if numChapters >= 1:
            if rvBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a title="View chapter page" href="{BBB}_C{c}.htm">C{c}</a>' )
        else:
            c = '0' # TODO: for now
            halt
        top = makeTop( level, 'OET', 'chapter', 'byC/', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {tidyBBB} chapter {c}" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">OET</a>''', 'OET' )
        cHtml = top + f'''<!--chapters indexPage--><p class="cLinks">{' '.join( cLinks )}</p>\n''' \
                    + makeBottom( level, 'chapter', state )
        checkHtml( 'OETChaptersIndex', cHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( cHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'chapter', 'byC', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Chapter View" ) \
            .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapters' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC">OET</a>''',
                      f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
    indexHtml = top \
                + '<h1 id="Top">OET chapter pages</h1><h2>Index of books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom( level, 'chapter', state )
    checkHtml( 'OETBooksIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages() finished processing {len(BBBs)} OET books: {BBBs}." )
    return filenames
# end of createChapterPages.createOETChapterPages

def createChapterPages( level:int, folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each chapter for all versions
        other than 'OET' which is considerably more complex (above).
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createChapterPages( {level}, {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createChapterPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    allBooksFlag = 'ALL' in state.booksToLoad[thisBible.abbreviation]
    BBBsToProcess = thisBible.books.keys() if allBooksFlag else state.booksToLoad[thisBible.abbreviation]
    if 'OET' in thisBible.abbreviation:
        BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    BBBs, filenames = [], []
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(BBBsToProcess) )
        # if not allBooksFlag: thisBible.loadBookIfNecessary( BBB )
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

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for {thisBible.abbreviation} {BBB}…" )
        BBBs.append( BBB )
        try: numChapters = thisBible.getNumChapters( BBB )
        except KeyError:
            logging.critical( f"Can't get number of chapters for {thisBible.abbreviation} {BBB}")
            continue
        haveBookIntro = thisBible.getNumVerses( BBB, '-1' )
        haveChapterZero = thisBible.getNumVerses( BBB, '0' )
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                try: numVerses = thisBible.getNumVerses( BBB, c )
                except KeyError:
                    logging.critical( f"Can't get number of verses for {thisBible.abbreviation} {BBB} {c}")
                    continue
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
                documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm">{tidyBBB}</a>'
                if c == -1:
                    leftLink = ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{0 if haveChapterZero else 1}.htm">→</a>'
                elif c == 0:
                    leftLink = f'<a title="Book introduction" href="{BBB}_Intro.htm">←</a> ' if haveBookIntro else ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C1.htm">→</a>'
                elif c == 1:
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C0.htm">←</a> ' if haveChapterZero \
                            else f'<a title="Book introduction" href="{BBB}_Intro.htm">←</a> ' if haveBookIntro \
                            else ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm">→</a>' if c<numChapters else ''
                else: # c > 1
                    assert c > 1
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C{c-1}.htm">←</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm">→</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="../../pa/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">║</a>'''
                detailsLink = f' <a title="Show details about this work" href="../details.htm">©</a>'
                cHtml = f'''<h1 id="Top">{thisBible.abbreviation} {tidyBBB} Introduction</h1>
<p class="cnav">{leftLink}{documentLink} Intro{rightLink}{parallelLink}{detailsLink}</p>
''' if c==-1 else f'''<h1 id="Top">{thisBible.abbreviation} {tidyBBB} Chapter {c}</h1>
<p class="cnav">{leftLink}{documentLink} {c}{rightLink}{parallelLink}{detailsLink}</p>
'''
                try: verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    if c == 0: continue # Usually no chapter zero
                    logging.critical( f"No chapter found for {thisBible.abbreviation} {BBB} {c=}" )
                    continue
                if isinstance( thisBible, ESFMBible.ESFMBible ):
                    verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm" )
                textHtml = convertUSFMMarkerListToHtml( thisBible.abbreviation, (BBB,c), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )
                # textHtml = livenIORs( BBB, textHtml, numChapters )
                if thisBible.abbreviation == 'OET-RV':
                    textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                elif thisBible.abbreviation == 'OET-LV':
                    textHtml = do_OET_LV_HTMLcustomisations( textHtml )
                elif thisBible.abbreviation == 'LSV':
                    textHtml = do_LSV_HTMLcustomisations( textHtml )
                cHtml = f'{cHtml}{textHtml}'
                filename = f'{BBB}_Intro.htm' if c==-1 else f'{BBB}_C{c}.htm'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, thisBible.abbreviation, 'chapter', f'byC/{filename}', state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB} introduction"
                                        if c==-1 else f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB} chapter {c}" ) \
                        .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                        .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC/{filename}">{thisBible.abbreviation}</a>''',
                                  f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
                cHtml = top + '<!--chapter page-->' + cHtml + '\n' + makeBottom( level, 'chapter', state )
                checkHtml( thisBible.abbreviation, cHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( cHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
        else: # a non-chapter book
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT','OTH','GLS','XXA','XXB','XXC')
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {thisBible.books[BBB]=}" )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for {thisBible.abbreviation} {BBB}…" )
            cHtml = f'<h1 id="Top">{thisBible.abbreviation} {BBB}</h1>\n'
            verseEntryList, contextList = thisBible.getContextVerseData( (BBB, '-1') )
            if isinstance( thisBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm" )
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            cHtml += convertUSFMMarkerListToHtml( thisBible.abbreviation, (BBB,'-1'), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )
            filename = f'{BBB}.htm'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            top = makeTop( level, thisBible.abbreviation, 'chapter', f'byC/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {BBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC/{filename}">{thisBible.abbreviation}</a>''',
                              f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            chtml = top + '<!--chapter page-->\n' + cHtml + makeBottom( level, 'chapter', state )
            checkHtml( thisBible.abbreviation, chtml )
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
    # Now create index pages for each book and then an overall one
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating chapter index pages for {thisBible.abbreviation}…" )
    BBBLinks = []
    for BBB in BBBs:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        filename = f'{BBB}_index.htm'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
        try: numChapters = thisBible.getNumChapters( BBB )
        except KeyError:
            logging.critical( f"Can't get number of chapters for {thisBible.abbreviation} {BBB}")
            continue
        cLinks = []
        if numChapters >= 1:
            if thisBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createChapterPages getNumVerses( {thisBible.abbreviation} {BBB} {c} )")
                numVerses = thisBible.getNumVerses( BBB, c )
                if numVerses: # make sure it's a normal chapter, e.g., in ESG book which lacks chapters 1-9
                    cLinks.append( f'<a title="View chapter page" href="{BBB}_C{c}.htm">C{c}</a>' )
        else:
            cLinks.append( f'<a title="View document" href="{BBB}.htm">{tidyBBB}</a>' )
        top = makeTop( level, thisBible.abbreviation, 'chapter', 'byC/', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB}" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
        cHtml = top + f'''<!--chapters indexPage--><p class="cLinks">{' '.join( cLinks )}</p>\n''' \
                        + makeBottom( level, 'chapter', state)
        checkHtml( thisBible.abbreviation, cHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( cHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
    # Create index page
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'chapter', 'byC', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} Chapter View" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapters' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC">{thisBible.abbreviation}</a>''',
                      f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">↑{thisBible.abbreviation}</a>''' )
    indexHtml = top \
                + f'<h1 id="Top">{thisBible.abbreviation} chapter pages</h1><h2>Index of books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom( level, 'chapter', state)
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createChapterPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}…" )
    return filenames
# end of createChapterPages.createChapterPages



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createChapterPages object
    pass
# end of createChapterPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createChapterPages object
    pass
# end of createChapterPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createChapterPages.py
