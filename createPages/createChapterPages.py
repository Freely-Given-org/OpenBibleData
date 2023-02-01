#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createChapterPages.py
#
# Module handling OpenBibleData createChapterPages functions
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
Module handling createChapterPages functions.

BibleOrgSys uses a three-character book code to identify books.
    These referenceAbbreviations are nearly always represented as BBB in the program code
            (although formally named referenceAbbreviation
                and possibly still represented as that in some of the older code),
        and in a sense, this is the centre of the BibleOrgSys.
    The referenceAbbreviation/BBB always starts with a letter, and letters are always UPPERCASE
        so 2 Corinthians is 'CO2' not '2Co' or anything.
        This was because early versions of HTML ID fields used to need
                to start with a letter (not a digit),
            (and most identifiers in computer languages still require that).
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
from html import doOET_LV_HTMLcustomisations, makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-02-01' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData createChapterPages functions"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETChapterPages( folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETChapterPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBs, filenames = [], []
    for BBB in state.booksToLoad[rvBible.abbreviation]:
        rvBible.loadBookIfNecessary( BBB )
        lvBible.loadBookIfNecessary( BBB )
        # if not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ): continue # Skip all except NT for now
        if lvBible.abbreviation=='OET-LV' \
        and BBB in ('INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"A Skipped OET chapters difficult book: OET-LV {BBB}")
            halt
            continue # Too many problems for now
        if rvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[rvBible.abbreviation] \
        and BBB not in state.booksToLoad[rvBible.abbreviation]:
            logging.critical( f"B Skipped OET chapters not-included book: OET-RV {BBB}")
            halt
            continue # Only create pages for the requested RV books
        if lvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
        and BBB not in state.booksToLoad[lvBible.abbreviation]:
            logging.critical( f"C Skipped OET chapters not-included book: OET-LV {BBB}")
            continue # Only create pages for the requested LV books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for OET {BBB}…" )
        BBBs.append( BBB )
        numChapters = rvBible.getNumChapters( BBB )
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for OET {BBB} {c}…" )
                leftLink = f'<a href="{BBB}_C{c-1}.html">←</a>{EM_SPACE}' if c>1 \
                            else f'<a href="{BBB}_Intro.html">←</a>{EM_SPACE}' if c==1 else ''
                rightLink = f'{EM_SPACE}<a href="{BBB}_C{c+1}.html">→</a>' if c<numChapters else ''
                parallelLink = f'{EM_SPACE}<a href="../../../parallel/{BBB}/C{c}_V1.html">║</a>'
                cHtml = f'''<h1>Open English Translation {BBB} Introduction</h1>
<p class="cnav">{leftLink}{BBB} Intro{rightLink}{parallelLink}</p>
<div class="container">
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
''' if c==-1 else f'''<h1>Open English Translation {BBB} Chapter {c}</h1>
<p class="cnav">{leftLink}{BBB} {c}{rightLink}{parallelLink}</p>
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
                    if c == 0: continue # No chapter zero
                    halt
                # NOTE: -1 (wrongly) gets the entire book (as at Feb2023)
                # print( f"OET-RV {BBB} {c} got {len(rvVerseEntryList)} verse entries, {len(rvContextList)} context entries")
                lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, str(c)) )
                rvHtml = convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', rvContextList, rvVerseEntryList )
                lvHtml = doOET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', lvContextList, lvVerseEntryList ) )
                rvHtml = '<div class="chunkRV">' + rvHtml + '</div><!--chunkRV-->\n'
                lvHtml = '<div class="chunkLV">' + lvHtml + '</div><!--chunkLV-->\n'
                filename = f'{BBB}_Intro.html' if c==-1 else f'{BBB}_C{c}.html'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( 3, 'OETChapters', state ) \
                        .replace( '__TITLE__', f'OET {BBB} introduction' if c==-1 else f'OET {BBB} chapter {c}' ) \
                        .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter' ) \
                        .replace( f'''<a href="{'../'*3}versions/OET">OET</a>''', 'OET' )
                cHtml = top + '<!--chapter page-->' \
                            + cHtml + rvHtml + lvHtml \
                            + '</div><!--container-->\n' \
                            + makeBottom(3, 'OETChapters', state)
                checkHtml( 'OETChapterIndex', cHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( cHtml )
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
        else:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETChapterPages {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT',)
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETChapterPages {rvBible.books[BBB]=}" )
            c = '-1'
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for OET {BBB} {c}…" )
            # cHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
            # # verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
            verseEntryList, contextList = lvBible.getContextVerseData( (BBB, c, '1') )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{lvBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            # cHtml += convertUSFMMarkerListToHtml( (BBB,c), 'chapter', contextList, verseEntryList )
            # filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html'
            # filenames.append( filename )
            # filepath = folder.joinpath( filename )
            # top = makeTop( 3, 'OETChapters', state ) \
            #         .replace( '__TITLE__', f'{thisBible.abbreviation} {BBB}' ) \
            #         .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' )
            # chtml = top + '<!--chapter page-->' + cHtml + makeBottom(3, 'OETChapters', state)
            # checkHtml( chtml )
            # with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            #     cHtmlFile.write( chtml )
            # vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
            halt
    # Now create index pages for each book and an overall one
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "    Creating chapter index pages for OET…" )
    BBBLinks = []
    for BBB in BBBs:
        # tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB(BBB)
        tidyBBB = (BBB[2]+BBB[:2]) if BBB[2].isdigit() else BBB
        filename = f'OET_{BBB}.html'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        BBBLinks.append( f'<a href="{filename}">{tidyBBB}</a>' )
        numChapters = rvBible.getNumChapters( BBB )
        cLinks = []
        if numChapters >= 1:
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a href="{BBB}_C{c}.html">C{c}</a>' )
        else:
            pass # TODO: for now
        top = makeTop( 3, 'OETChapters', state ) \
                .replace( '__TITLE__', f'OET {BBB} chapter {c}' ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter' ) \
                .replace( f'''<a href="{'../'*3}versions/OET">OET</a>''', 'OET' )
        cHtml = top + '<!--chapters indexPage-->' + EM_SPACE.join( cLinks ) + makeBottom(3, 'OETChapters', state)
        checkHtml( 'OETChaptersIndex', cHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( cHtml )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
    filename = 'index.html'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'OETChapters', state ) \
            .replace( '__TITLE__', f'OET Chapter View' ) \
            .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapters' )
    indexHtml = top \
                + '<h1>OET chapter pages</h1><h2>Index of books</h2>\n' \
                + EM_SPACE.join( BBBLinks ) \
                + makeBottom(3, 'OETChapters', state)
    checkHtml( 'OETBooksIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages() finished processing {len(BBBs)} OET books: {BBBs}" )
    return filenames
# end of createChapterPages.createOETChapterPages

def createChapterPages( folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each chapter for all versions
        other than 'OET' which is considerably more complex (above).
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createChapterPages( {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createChapterPages( {folder}, {thisBible.abbreviation} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBs, filenames = [], []
    for BBB in state.booksToLoad[thisBible.abbreviation]:
        thisBible.loadBookIfNecessary( BBB )
        # if not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ): continue # Skip all except NT for now
        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"AA Skipped OET chapters difficult book: OET-LV {BBB}")
            halt
            continue # Too many problems for now
        if thisBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[thisBible.abbreviation] \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped chapters difficult book: {thisBible.abbreviation} {BBB}")
            halt
            continue # Only create pages for the requested books

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for {thisBible.abbreviation} {BBB}…" )
        BBBs.append( BBB )
        numChapters = thisBible.getNumChapters( BBB )
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
                leftLink = f'<a href="{BBB}_C{c-1}.html">←</a>{EM_SPACE}' if c>1 \
                            else f'<a href="{BBB}_Intro.html">←</a>{EM_SPACE}' if c==1 else ''
                rightLink = f'{EM_SPACE}<a href="{BBB}_C{c+1}.html">→</a>' if c<numChapters else ''
                parallelLink = f'{EM_SPACE}<a href="../../../parallel/{BBB}/C{c}_V1.html">║</a>'
                cHtml = f'''<h1>{thisBible.abbreviation} {BBB} Introduction</h1>\n
<p class="cnav">{leftLink}{BBB} Intro{rightLink}{parallelLink}</p>
''' if c==-1 else f'''<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n
<p class="cnav">{leftLink}{BBB} {c}{rightLink}{parallelLink}</p>
'''
                try: verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    if c == 0: continue # No chapter zero
                    halt
                cHtml += convertUSFMMarkerListToHtml( thisBible.abbreviation, (BBB,c), 'chapter', contextList, verseEntryList )
                # filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html'
                filename = f'{BBB}_Intro.html' if c==-1 else f'{BBB}_C{c}.html'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( 3, 'chapters', state ) \
                        .replace( '__TITLE__', f'{thisBible.abbreviation} {BBB} introduction' if c==-1 else f'{thisBible.abbreviation} {BBB} chapter {c}' ) \
                        .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                        .replace( f'''<a href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
                cHtml = top + '<!--chapter page-->' + cHtml + makeBottom(3, 'chapters', state)
                checkHtml( thisBible.abbreviation, cHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( cHtml )
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
        else:
            # TODO: We haven't been able to make this work at all yet!
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT',)
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {thisBible.books[BBB]=}" )
            c = '1'
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
            # cHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
            # # verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
            # verseEntryList, contextList = thisBible.getContextVerseData( (BBB, c, '1') )
            # halt
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            # cHtml += convertUSFMMarkerListToHtml( (BBB,c), 'chapter', contextList, verseEntryList )
            # filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html'
            # filenames.append( filename )
            # filepath = folder.joinpath( filename )
            # top = makeTop( 3, 'chapters', state ) \
            #         .replace( '__TITLE__', f'{thisBible.abbreviation} {BBB}' ) \
            #         .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' )
            # chtml = top + '<!--chapter page-->' + cHtml + makeBottom(3, 'chapters', state)
            # checkHtml( chtml )
            # with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            #     cHtmlFile.write( chtml )
            # vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
    # Now create index pages for each book and an overall one
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating chapter index pages for {thisBible.abbreviation}…" )
    BBBLinks = []
    for BBB in BBBs:
        # tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB(BBB)
        tidyBBB = (BBB[2]+BBB[:2]) if BBB[2].isdigit() else BBB
        filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}.html'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        BBBLinks.append( f'<a href="{filename}">{tidyBBB}</a>' )
        numChapters = thisBible.getNumChapters( BBB )
        cLinks = []
        if numChapters >= 1:
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a href="{BBB}_C{c}.html">C{c}</a>' )
        else:
            c = '-1' # TODO: for now
        top = makeTop( 3, 'chapters', state ) \
                .replace( '__TITLE__', f'{thisBible.abbreviation} {BBB} chapter {c}' ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter' ) \
                .replace( f'''<a href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
        cHtml = top + '<!--chapters indexPage-->' + EM_SPACE.join( cLinks ) + makeBottom(3, 'chapters', state)
        checkHtml( thisBible.abbreviation, cHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( cHtml )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(cHtml):,} characters written to {filepath}" )
    # Create index page
    filename = 'index.html'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'chapters', state ) \
            .replace( '__TITLE__', f'{thisBible.abbreviation} Chapter View' ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapters' )
    indexHtml = top \
                + '<h1>Chapter pages</h1><h2>Index of books</h2>\n' \
                + EM_SPACE.join( BBBLinks ) \
                + makeBottom(3, 'chapters', state)
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createChapterPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}" )
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
