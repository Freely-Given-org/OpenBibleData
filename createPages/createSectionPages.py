#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSectionPages.py
#
# Module handling OpenBibleData createSectionPages functions
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
Module handling createSectionPages functions.

Assumes that all books are already loaded.
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
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from usfm import convertUSFMMarkerListToHtml
from html import do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, removeDuplicateCVids, checkHtml


LAST_MODIFIED_DATE = '2023-03-12' # by RJH
SHORT_PROGRAM_NAME = "createSectionPages"
PROGRAM_NAME = "OpenBibleData createSectionPages functions"
PROGRAM_VERSION = '0.13'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '

REASON_NAME_DICT = { 'Headers':'Headers', 'is1':'Introduction section heading',
                     'c':'Start of chapter', 's1':'Section heading', 'c/s1':'Section heading',
                     'ms1':'Main section', 'ms1/s1':'Main section with section heading' }


def createOETSectionPages( folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETSectionPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )
    assert rvBible.discoveryResults['ALL']['haveSectionHeadings']
    assert not lvBible.discoveryResults['ALL']['haveSectionHeadings']
    rvBible.makeSectionIndex() # These aren't made automatically

    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    BBBsToProcess = reorderBooksForOETVersions( rvBible.books.keys() if allBooksFlag else state.booksToLoad[rvBible.abbreviation] )
    BBBs = []
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {BBB=} {BBBsToProcess}/{len(BBBsToProcess)}")

        # TODO: Can we delete all this now???
        if lvBible.abbreviation=='OET-LV' \
        and BBB in ('INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"A Skipped OET sections difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if rvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[rvBible.abbreviation] \
        and BBB not in state.booksToLoad[rvBible.abbreviation]:
            logging.critical( f"B Skipped OET sections not-included book: OET-RV {BBB}")
            continue # Only create pages for the requested RV books
        if lvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
        and BBB not in state.booksToLoad[lvBible.abbreviation]:
            logging.critical( f"C Skipped OET sections not-included book: OET-LV {BBB}")
            continue # Only create pages for the requested LV books

        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rvBible.abbreviation} {type(rvBible[BBB]._SectionIndex)=} {rvBible[BBB]._SectionIndex=}" )
        if not rvBible[BBB]._SectionIndex: # no sections in this book, e.g., FRT
            continue

        # First, get our list of sections
        BBBs.append( BBB )
        bkObject = rvBible[BBB]
        sections = []
        for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = REASON_NAME_DICT[reasonMarker]
            startC,startV = startCV
            endC,endV = sectionIndexEntry.getEndCV()
            rvVerseEntryList, rvContextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            filename = f'{BBB}_S{n}.html'
            sections.append( (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,filename) )

        # Now, make the actual pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for OET {BBB}…" )
        for n, (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,filename) in enumerate( sections ):
            documentLink = f'<a href="../byDocument/{BBB}.html">{tidyBBB}</a>'
            startChapterLink = f'''<a href="../byChapter/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.html">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a href="../byChapter/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.html">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a href="{BBB}_S{n-1}.html">←</a> ' if n>0 else ''
            rightLink = f' <a href="{BBB}_S{n+1}.html">→</a>' if n<len(bkObject._SectionIndex)-1 else ''
            parallelLink = f' <a href="../../../parallel/{BBB}/C{startC}V{startV}.html">║</a>'
            detailsLink = f' <a href="../details.html">©</a>'

            bkHtml = f'''<h1 id="Top">Open English Translation {tidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<h1>{sectionName}</h1>
<p class="cnav">{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{parallelLink}{detailsLink}</p>
<div class="container">
<span> </span>
<div class="buttons">
    <button type="button" id="underlineButton" onclick="hide_show_underlines()">Hide underlines</button>
</div><!--buttons-->
<h2>Readers’ Version</h2>
<h2>Literal Version</h2>
'''
            rvHtml = convertUSFMMarkerListToHtml( rvBible.abbreviation, (BBB,startC), 'section', rvContextList, rvVerseEntryList )
            rvHtml = livenIORs( BBB, rvHtml, sections )
            # Get the info for the first LV verse
            try:
                lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, startC, startV) )
            except KeyError: # this can fail in the introduction which is missing from LV
                logging.critical( f"Seems OET-LV {BBB} is missing section starting with {startC}:{startV}" )
                lvVerseEntryList, lvContextList = [], []
            # then concatenate the verse lists for the following LV verses
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Concatenating OET-LV {BBB} from {startC}:{startV} to {endC}:{endV}" )
            C = int(startC)
            V = getLeadingInt(startV) + 1 # Handles strings like '4b'
            for _safetyCount in range( 100 ):
                # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Looking for {C}:{V}" )
                endVint = getLeadingInt(endV)
                if C > int(endC) \
                or (C==int(endC) and V >= endVint):
                    break
                # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Adding {C}:{V}" )
                try:
                    thisVerseEntryList = lvBible.getVerseDataList( (BBB, str(C), str(V) ) )
                except KeyError:
                    if startC == '-1': # This is expected, because LV doesn't have intros, so endV will be excessive
                        assert endC == '-1'
                        assert V > 9 # We should have got some lines
                        break
                    else: # We're in a chapter and may have reached the end
                        if startC != endC:
                            numVerses = lvBible.getNumVerses( BBB, startC )
                            if V > numVerses:
                                C += 1
                                V = 1
                                # Try again with the first verse of the next chapter
                                thisVerseEntryList = lvBible.getVerseDataList( (BBB, str(C), str(V) ) )
                            else: raise KeyError
                        else: raise KeyError
                lvVerseEntryList += thisVerseEntryList
                V += 1
            else:
                loop_counter_too_small
            if isinstance( lvBible, ESFMBible.ESFMBible ):
                verseEntryList,wordList = lvBible.livenESFMWordLinks( BBB, lvVerseEntryList, '../../../W/{n}.htm' )
            lvHtml = convertUSFMMarkerListToHtml( lvBible.abbreviation, (BBB,startC), 'section', lvContextList, lvVerseEntryList )
            lvHtml = do_OET_LV_HTMLcustomisations( lvHtml )
            combinedHtml = f'''<div class="chunkRV">{rvHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvHtml}</div><!--chunkLV-->
'''
            filepath = folder.joinpath( filename )
            top = makeTop( 3, 'OETSection', f'bySection/{BBB}.html', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {tidyBBB} section" ) \
                    .replace( '__KEYWORDS__', f'Bible, OET, section' ) \
                    .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*3}versions/OET/bySection/{filename}">OET</a>''',
                            f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*3}versions/OET/">↑OET</a>''' )
            bkHtml = top + '<!--section page-->' \
                    + bkHtml + removeDuplicateCVids( combinedHtml ) \
                    + '</div><!--container-->\n' \
                    + makeBottom( 3, 'OETSection', state )
            checkHtml( rvBible.abbreviation, bkHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( bkHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
        # Now make the section index file for this book
        filename = f'{BBB}.html'
        filepath = folder.joinpath( filename )
        top = makeTop( 3, 'OETSection', f'bySection/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {tidyBBB} sections" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, sections' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*3}versions/OET/bySection/{filename}">OET</a>''',
                        f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*3}versions/OET/">↑OET</a>''' )
        bkHtml = f'<h1 id="Top">Index of sections for OET {tidyBBB}</h1>\n'
        for startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in sections:
            bkHtml = f'''{bkHtml}<p>{'Intro' if startC=='-1' else startC}:{startV} <a href="{filename}"><b>{sectionName}</b></a> ({reasonName})</p>'''
        bkHtml = top + '<!--sections page-->' + bkHtml + '\n' + makeBottom( 3, 'OETSection', state )
        checkHtml( 'OET section', bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now an overall index for sections
    BBBLinks = []
    for BBB in BBBs:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        filename = f'{BBB}.html'
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
    # Create index page
    filename = 'index.html'
    # filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'OETSection', 'bySection/', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Sections View" ) \
            .replace( '__KEYWORDS__', f'Bible, OET, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*3}versions/OET">OET</a>''', 'OET' )
    indexHtml = top \
                + '<h1 id="Top">OET section pages</h1><h2>Index of OET books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom(3, 'OETSection', state)
    checkHtml( 'OET sections', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages() finished processing {len(BBBs)} OET books: {BBBs}." )
# end of createSectionPages.createOETSectionPages


def createSectionPages( folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each section for all versions other than 'OET'
                                which is considerably more complex (above).
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createSectionPages( {folder}, {thisBible.abbreviation} )" )
    assert thisBible.discoveryResults['ALL']['haveSectionHeadings']
    thisBible.makeSectionIndex() # These aren't made automatically

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages( {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    allBooksFlag = 'ALL' in state.booksToLoad[thisBible.abbreviation]
    BBBsToProcess = thisBible.books.keys() if allBooksFlag else state.booksToLoad[thisBible.abbreviation]
    if 'OET' in thisBible.abbreviation:
        BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    BBBs = []
    for BBB in BBBsToProcess:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {BBB=} {BBBsToProcess}/{len(BBBsToProcess)}")

        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"AA Skipped OET sections difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if thisBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[thisBible.abbreviation] \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped sections difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {type(thisBible[BBB]._SectionIndex)=} {thisBible[BBB]._SectionIndex=}" )
        if not thisBible[BBB]._SectionIndex: # no sections in this book, e.g., FRT
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"No section headings in {thisBible.abbreviation} {BBB} -- skipping section pages" )
            filename = f'{BBB}.html'
            filepath = folder.joinpath( filename )
            top = makeTop( 3, 'section', f'bySection/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB} sections" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySection/{filename}">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            bkHtml = f'<h1 id="Top">{thisBible.abbreviation} {tidyBBB} has NO section headings</h1>\n'
            bkHtml = top + '<!--no sections page-->' + bkHtml + '\n' + makeBottom( 3, 'section', state )
            checkHtml( thisBible.abbreviation, bkHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( bkHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
            continue

        # First, get our list of sections
        BBBs.append( BBB )
        bkObject = thisBible[BBB]
        sections = []
        for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = REASON_NAME_DICT[reasonMarker]
            startC,startV = startCV
            endC,endV = sectionIndexEntry.getEndCV()
            verseEntryList, contextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            filename = f'{BBB}_S{n}.html'
            sections.append( (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) )

        # Now, make the actual pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for {thisBible.abbreviation} {BBB}…" )
        for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( sections ):
            documentLink = f'<a href="../byDocument/{BBB}.html">{tidyBBB}</a>'
            startChapterLink = f'''<a href="../byChapter/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.html">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a href="../byChapter/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.html">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a href="{BBB}_S{n-1}.html">←</a> ' if n>0 else ''
            rightLink = f' <a href="{BBB}_S{n+1}.html">→</a>' if n<len(bkObject._SectionIndex)-1 else ''
            parallelLink = f' <a href="../../../parallel/{BBB}/C{startC}V{startV}.html">║</a>'
            detailsLink = f' <a href="../details.html">©</a>'

            bkHtml = f'''<h1>{thisBible.abbreviation} {tidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<h1>{sectionName}</h1>
<p class="cnav">{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{parallelLink}{detailsLink}</p>
'''
            textHtml = convertUSFMMarkerListToHtml( thisBible.abbreviation, (BBB,startC), 'section', contextList, verseEntryList )
            textHtml = livenIORs( BBB, textHtml, sections )
            if thisBible.abbreviation == 'OET-LV':
                textHtml = do_OET_LV_HTMLcustomisations( textHtml )
            elif thisBible.abbreviation == 'LSV':
                textHtml = do_LSV_HTMLcustomisations( textHtml )
            bkHtml = f'{bkHtml}{textHtml}'

            filepath = folder.joinpath( filename )
            top = makeTop( 3, 'section', f'bySection/{BBB}.html', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB} section" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, section' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySection/{filename}">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            bkHtml = top + '<!--section page-->' + bkHtml + makeBottom( 3, 'section', state )
            checkHtml( thisBible.abbreviation, bkHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( bkHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )
        # Now make the section index file for this book
        filename = f'{BBB}.html'
        filepath = folder.joinpath( filename )
        top = makeTop( 3, 'section', f'bySection/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {tidyBBB} sections" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySection/{filename}">{thisBible.abbreviation}</a>''',
                        f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        bkHtml = f'<h1 id="Top">Index of sections for {thisBible.abbreviation} {tidyBBB}</h1>\n'
        for startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in sections:
            bkHtml = f'''{bkHtml}<p>{'Intro' if startC=='-1' else startC}:{startV} <a href="{filename}"><b>{sectionName}</b></a> ({reasonName})</p>'''
        bkHtml = top + '<!--sections page-->' + bkHtml + '\n' + makeBottom( 3, 'section', state )
        checkHtml( thisBible.abbreviation, bkHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( bkHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(bkHtml):,} characters written to {filepath}" )

    # Now an overall index for sections
    BBBLinks = []
    for BBB in BBBs:
        tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
        filename = f'{BBB}.html'
        BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}">{tidyBBB}</a>' )
    # Create index page
    filename = 'index.html'
    # filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( 3, 'section', 'bySection/', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} Sections View" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*3}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    indexHtml = top \
                + f'<h1 id="Top">{thisBible.abbreviation} section pages</h1><h2>Index of {thisBible.abbreviation} books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom(3, 'section', state)
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}." )
    # return filenames
# end of createSectionPages.createSectionPages


def livenIORs( BBB:str, sectionHTML:str, bookSections:List ) -> str:
    """
    We have to find which section each starting reference is in.
    """
    assert '\\ior' not in sectionHTML

    searchStartIx = 0
    for _safetyCount1 in range( 15 ):
        # First find each link
        ixSpanStart = sectionHTML.find( '<span class="ior">', searchStartIx )
        if ixSpanStart == -1: break
        ixEnd = sectionHTML.find( '</span>', ixSpanStart+18 )
        assert ixEnd != -1
        guts = sectionHTML[ixSpanStart+18:ixEnd].replace('–','-') # Convert any en-dash to hyphen
        # print(f"{BBB} {guts=} {bookHTML[ix-20:ix+20]} {searchStartIx=} {ixSpanStart=} {ixEnd=}")
        startGuts = guts.split('-')[0]
        # print(f"  Now {guts=}")
        if ':' in startGuts:
            assert startGuts.count(':') == 1 # We expect a single C:V at this stage
            Cstr, Vstr = startGuts.strip().split( ':' )
        elif BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB ):
            Cstr, Vstr = '1', startGuts.strip() # Only a verse was given
        else: Cstr, Vstr = startGuts.strip(), '1' # Only a chapter was given

        # Now find which section that IOR starts in
        for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( bookSections ):
            if startC==Cstr and endC==Cstr:
                try:
                    if int(startV) <= int(Vstr) <= int(endV): # It's in here
                        break
                except ValueError: pass # but it might be the one we want???
        else:
            logging.critical( f"unable_to_find_IOR for {BBB} {Cstr}:{Vstr} {[f'{startC}:{startV}--{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in bookSections]}" )
            unable_to_find_IOR # Need to write more code

        # Now liven the link
        new_guts = f'<a href="{BBB}_S{n}.html">{guts}</a>'
        sectionHTML = f'{sectionHTML[:ixSpanStart+18]}{new_guts}{sectionHTML[ixEnd:]}'
        searchStartIx = ixEnd + 26 # Approx number of chars that we add
    else:
        # logging.critical( f"inner_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_innerSafetyCount=}" )
        section_liven_IOR_loop_needed_to_break

    return sectionHTML
# end of createSectionPages.livenIORs function


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSectionPages object
    pass
# end of createSectionPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSectionPages object
    pass
# end of createSectionPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createSectionPages.py
