#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSectionPages.py
#
# Module handling OpenBibleData createSectionPages functions
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
Module handling createSectionPages functions.

Assumes that all books are already loaded.

CHANGELOG:
    2023-08-07 Handle additional ESFM section headings, etc.
    2023-08-18 Handle additional section headings separated by semicolons
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging
from collections import defaultdict

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from usfm import convertUSFMMarkerListToHtml
from Bibles import tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from OETHandlers import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-12-14' # by RJH
SHORT_PROGRAM_NAME = "createSectionPages"
PROGRAM_NAME = "OpenBibleData createSectionPages functions"
PROGRAM_VERSION = '0.43'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '

REASON_NAME_DICT = { 'Headers':'Headers', 'is1':'Introduction section heading',
                     'c':'Start of chapter', 's1':'Section heading', 'c/s1':'Section heading',
                     'ms1':'Main section', 'ms1/s1':'Main section with section heading' }


def createOETSectionPages( level:int, folder:Path, rvBible, lvBible, state ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETSectionPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )
    assert rvBible.discoveryResults['ALL']['haveSectionHeadings']
    assert not lvBible.discoveryResults['ALL']['haveSectionHeadings']
    rvBible.makeSectionIndex() # These aren't made automatically

    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBsToProcess = reorderBooksForOETVersions( rvBible.books.keys() if 'ALL' in state.booksToLoad[rvBible.abbreviation] else state.booksToLoad[rvBible.abbreviation] )
    BBBLinks = []
    for BBB in BBBsToProcess:
        if BBB=='FRT' \
        or 'ALL' in state.booksToLoad[lvBible.abbreviation] \
        or BBB in state.booksToLoad[lvBible.abbreviation]:
            filename = f'{BBB}.htm'
            ourTidyBBB = tidyBBB( BBB )
            BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{filename}#Top">{ourTidyBBB}</a>''' )
    navListParagraph = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'OET', state)

    # Firstly make our list of section headings
    #   The BibleOrgSys section index already contains a list of sections
    state.sectionsLists = {}
    state.sectionsLists['OET-RV'] = {}
    for BBB in BBBsToProcess:
        # Firstly, make a list of additional section headings
        additionalSectionHeadingsDict = defaultdict( list )
        rvVerseEntryList, _rvContextList = rvBible.getContextVerseData( (BBB,) )
        C = V = '0'
        for n, entry in enumerate( rvVerseEntryList ):
            marker = entry.getMarker()
            if marker not in ('c','v','rem'): continue
            rest = entry.getText()
            if marker == 'c': C, V = rest, '0'
            elif marker == 'v': V = rest
            elif marker == 'rem':
                if not rest.startswith( '/' ): continue
                given_marker = rest[1:].split( ' ', 1 )[0]
                assert given_marker in ('s1','r','s2','s3','d')
                rest = rest[len(given_marker)+2:] # Drop the '/marker ' from the displayed portion
                plusOneV = str( getLeadingInt(V) + 1 ) # Also handles verse ranges
                for sectionChunk in rest.split( '; ' ):
                    additionalSectionHeadingsDict[(C,plusOneV)].append( (given_marker,sectionChunk) )
        # if additionalSectionHeadingsDict: print( f"HERE1 {BBB} {additionalSectionHeadingsDict}" )

        if not rvBible[BBB]._SectionIndex: # no sections in this book, e.g., FRT
            continue

        bkObject = rvBible[BBB]
        state.sectionsLists['OET-RV'][BBB] = []
        for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
            startC,startV = startCV
            # if additionalSectionHeadingsDict: print( f"{startCV=} {startC}:{startV}" )
            endC,endV = sectionIndexEntry.getEndCV()
            # if additionalSectionHeadingsDict: print( f"End {endC}:{endV}" )
            if additionalSectionHeadingsDict:
                # print( f"{startCV=} {startC}:{startV} {sectionIndexEntry=}" )
                intStartC, intStartV = int(startC), getLeadingInt(startV)
            if additionalSectionHeadingsDict:
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} {sectionIndexEntry=}" )
                # Insert any additional section headings BEFORE this one
                for (c,v),additionalFieldList in additionalSectionHeadingsDict.copy().items():
                    # print( f"{c}:{v} {additionalFieldList}" )
                    if int(c) < intStartC \
                    or c==startC and int(v) < intStartV:
                        for additionalMarker,additionalFieldText in additionalFieldList:
                            if additionalMarker in ('s1','s2','s3'):
                                additionalMarkerName = { 's1':'section heading', 's2':'2nd level section heading' }[additionalMarker]
                                # NOTE: word 'Alternate ' is searched for below
                                state.sectionsLists['OET-RV'][BBB].append( (c,v,'?','?',additionalFieldText,f'Alternate {additionalMarkerName}',[],[],filename) )
                            else: vPrint( 'Info', DEBUGGING_THIS_MODULE, f"createOETSectionPages ignored additional \{additionalMarker} at {BBB} {c}:{v}" )
                        del additionalSectionHeadingsDict[(c,v)]
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            sectionName = sectionName.replace( "'", "’" ) # Replace apostrophes
            filename = f'{BBB}_S{n}.htm'
            # if additionalSectionHeadingsDict:
            #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = REASON_NAME_DICT[reasonMarker]
            rvVerseEntryList, rvContextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            state.sectionsLists['OET-RV'][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,filename) )
        if additionalSectionHeadingsDict:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{BBB} didn't use {additionalSectionHeadingsDict=}")
        # Handle left-over additions
        for (c,v),additionalFieldList in additionalSectionHeadingsDict.copy().items():
            # print( f"{c}:{v} {additionalFieldList}" )
            for additionalMarker,additionalFieldText in additionalFieldList:
                additionalMarkerName = { 's1':'section heading', 'r':'section cross-reference' }[additionalMarker]
                # NOTE: word 'Alternate ' is searched for below
                state.sectionsLists['OET-RV'][BBB].append( (c,v,'?','?',additionalFieldText,f'Alternate {additionalMarkerName}',[],[],filename) )
            del additionalSectionHeadingsDict[(c,v)]
        if additionalSectionHeadingsDict:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{BBB} didn't use {additionalSectionHeadingsDict=}")
            halt


    # Now, make the actual section pages
    BBBs = []
    for BBB in BBBsToProcess:
        ourTidyBBB = tidyBBB( BBB )
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

        # # First, get our list of sections
        BBBs.append( BBB )
        # bkObject = rvBible[BBB]
        # state.sectionsLists['OET-RV'][BBB] = []
        # for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
        #     # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
        #     sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
        #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
        #     reasonName = REASON_NAME_DICT[reasonMarker]
        #     startC,startV = startCV
        #     endC,endV = sectionIndexEntry.getEndCV()
        #     rvVerseEntryList, rvContextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
        #     filename = f'{BBB}_S{n}.htm'
        #     state.sectionsLists['OET-RV'][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,filename) )

        # Now, make the actual section pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for OET {BBB}…" )
        numExtrasSkipped = 0
        for n1, (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,filename) in enumerate( state.sectionsLists['OET-RV'][BBB] ):
            if endC == '?': # Then these are the additional headings
                assert endV == '?'
                numExtrasSkipped += 1
                continue
            n = n1 - numExtrasSkipped
            documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
            startChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.htm#Top">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.htm#Top">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a title="Previous section" href="{BBB}_S{n-1}.htm#Top">←</a> ' if n>0 else ''
            rightLink = f' <a title="Next section" href="{BBB}_S{n+1}.htm#Top">→</a>' if n<len(bkObject._SectionIndex)-1 else ''
            parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}pa/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">║</a>'''
            interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
            detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''

            sectionHtml = f'''<h1 id="Top"><span title="Open English Translation">OET</span> by section {ourTidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<p class="secNav">{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{parallelLink}{interlinearLink}{detailsLink}</p>
<h1>{sectionName}</h1>
<p class="rem">This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.</p>
<div class="container">
<h2>Readers’ Version</h2>
<h2>Literal Version <button type="button" id="marksButton" onclick="hide_show_marks()">Hide marks</button></h2>
'''
# <span> </span>
# <div class="buttons">
#     <button type="button" id="marksButton" onclick="hide_show_marks()">Hide marks</button>
# </div><!--buttons-->
            if isinstance( rvBible, ESFMBible.ESFMBible ):
                rvVerseEntryList = livenOETWordLinks( rvBible, BBB, rvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
            rvHtml = convertUSFMMarkerListToHtml( level, rvBible.abbreviation, (BBB,startC, startV), 'section', rvContextList, rvVerseEntryList, basicOnly=False, state=state )
            rvHtml = do_OET_RV_HTMLcustomisations( rvHtml )
            # rvHtml = livenIORs( BBB, rvHtml, sections )
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
                    assert isinstance( thisVerseEntryList, InternalBibleEntryList )
                except KeyError:
                    if startC == '-1': # This is expected, because LV doesn't have intros, so endV will be excessive
                        assert endC == '-1'
                        assert V > 9 # We should have got some lines
                        break
                    else: # We're in a chapter and may have reached the end
                        if startC != endC:
                            numVerses = lvBible.getNumVerses( BBB, str(C) )
                            if V > numVerses:
                                C += 1
                                V = 0
                                # Try again with the first verse of the next chapter
                                thisVerseEntryList = lvBible.getVerseDataList( (BBB, str(C), str(V) ) )
                                assert isinstance( thisVerseEntryList, InternalBibleEntryList )
                            else: raise KeyError
                        else: raise KeyError
                lvVerseEntryList += thisVerseEntryList
                V += 1
            else:
                loop_counter_too_small
            if isinstance( lvBible, ESFMBible.ESFMBible ):
                lvVerseEntryList = livenOETWordLinks( lvBible, BBB, lvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
            lvHtml = convertUSFMMarkerListToHtml( level, lvBible.abbreviation, (BBB,startC), 'section', lvContextList, lvVerseEntryList, basicOnly=False, state=state )
            lvHtml = do_OET_LV_HTMLcustomisations( lvHtml )
            combinedHtml = f'''<div class="chunkRV">{rvHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvHtml}</div><!--chunkLV-->
'''
            filepath = folder.joinpath( filename )
            top = makeTop( level, 'OET', 'section', f'bySec/{BBB}.htm', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB} section" ) \
                    .replace( '__KEYWORDS__', f'Bible, OET, section' ) \
                    .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/bySec/{filename}#Top">OET</a>''',
                            f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET/">↑OET</a>''' )
            sectionHtml = f'''{top}<!--section page-->
{navListParagraph}
{sectionHtml}
{removeDuplicateCVids( BBB, combinedHtml )}</div><!--container-->
{makeBottom( level, 'section', state )}'''
            checkHtml( rvBible.abbreviation, sectionHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )

        # Now make the section index file for this book
        filename = f'{BBB}.htm'
        filepath = folder.joinpath( filename )
        top = makeTop( level, 'OET', 'section', f'bySec/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB} sections" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, sections' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*2}OET/bySec/{filename}#Top">OET</a>''',
                        f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*2}OET/">↑OET</a>''' )
        sectionHtml = f'<h1 id="Top">Index of sections for OET {ourTidyBBB}</h1>\n'
        for startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in state.sectionsLists['OET-RV'][BBB]:
            # print( f"HERE8 {BBB} {startC}:{startV} {_endC}:{endV} '{sectionName=}' '{reasonName=}' '{filename=}'" )
            reasonString = '' if reasonName=='Section heading' and not TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
            # NOTE: word 'Alternate ' is defined above at start of main loop
            sectionHtml = f'''{sectionHtml}<p class="{'alternateHeading' if reasonName.startswith('Alternate ') else 'sectionHeading'}"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
        sectionHtml = f'''{top}<!--sections page-->
{navListParagraph}
{sectionHtml}
{makeBottom( level, 'section', state )}'''
        checkHtml( 'OET section', sectionHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( sectionHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )

    # Now a single overall index page for sections
    filename = 'index.htm'
    # filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'section', 'bySec/', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Sections View" ) \
            .replace( '__KEYWORDS__', f'Bible, OET, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*2}OET">OET</a>''', 'OET' )
    indexHtml = f'''{top}
<h1 id="Top">OET section pages</h1>
<h2>Index of OET books</h2>
{navListParagraph}
{makeBottom( level, 'section', state)}'''
    checkHtml( 'OET sections', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages() finished processing {len(BBBs)} OET books: {BBBs}." )
# end of createSectionPages.createOETSectionPages


def createSectionPages( level:int, folder:Path, thisBible, state ) -> List[str]:
    """
    This creates a page for each section for all versions other than 'OET'
                                which is considerably more complex (above).
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createSectionPages( {level}, {folder}, {thisBible.abbreviation} )" )
    assert thisBible.discoveryResults['ALL']['haveSectionHeadings']
    thisBible.makeSectionIndex() # These aren't made automatically

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    BBBsToProcess = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
                else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
                else thisBibleBooksToLoad
    if 'OET' in thisBible.abbreviation:
        BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    BBBLinks = []
    for BBB in BBBsToProcess:
        if BBB=='FRT' \
        or 'ALL' in thisBibleBooksToLoad \
        or BBB in thisBibleBooksToLoad:
            filename = f'{BBB}.htm'
            ourTidyBBB = tidyBBB( BBB )
            BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{filename}#Top">{ourTidyBBB}</a>''' )
    navListParagraph = makeBookNavListParagraph(state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state)

    # Firstly make our list of section headings
    state.sectionsLists[thisBible.abbreviation] = {}
    for BBB in BBBsToProcess:
        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
            logging.critical( f"AA Skipped OET sections difficult book: OET-LV {BBB}")
            continue # Too many problems for now
        if thisBibleBooksToLoad not in (['ALL'],['NT']) \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped sections difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books
        bkObject = thisBible[BBB]
        state.sectionsLists[thisBible.abbreviation][BBB] = []
        for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            if 'OET' in thisBible.abbreviation:
                sectionName = sectionName.replace( "'", "’" ) # Replace apostrophes
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = REASON_NAME_DICT[reasonMarker]
            startC,startV = startCV
            endC,endV = sectionIndexEntry.getEndCV()
            verseEntryList, contextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            if isinstance( thisBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
            filename = f'{BBB}_S{n}.htm'
            state.sectionsLists[thisBible.abbreviation][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) )

    # Now, make the actual pages
    BBBs = []
    # state.sectionsLists[thisBible.abbreviation] = {}
    for BBB in BBBsToProcess:
        ourTidyBBB = tidyBBB( BBB )
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
            filename = f'{BBB}.htm'
            filepath = folder.joinpath( filename )
            top = makeTop( level, thisBible.abbreviation, 'section', f'bySec/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} sections" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{filename}#Top">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            sectionHtml = f'<h1 id="Top">{thisBible.abbreviation} {ourTidyBBB} has NO section headings</h1>\n'
            sectionHtml = f'''{top}<!--no sections page-->
{navListParagraph}
{sectionHtml}
{makeBottom( level, 'section', state )}'''
            checkHtml( thisBible.abbreviation, sectionHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )
            continue

        # First, get our list of sections
        BBBs.append( BBB )
        # bkObject = thisBible[BBB]
        # state.sectionsLists[thisBible.abbreviation][BBB] = []
        # for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
        #     # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {NEWLINE*2}createSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
        #     sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
        #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
        #     reasonName = REASON_NAME_DICT[reasonMarker]
        #     startC,startV = startCV
        #     endC,endV = sectionIndexEntry.getEndCV()
        #     verseEntryList, contextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
        #     filename = f'{BBB}_S{n}.htm'
        #     state.sectionsLists[thisBible.abbreviation][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) )

        # Now, make the actual pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for {thisBible.abbreviation} {BBB}…" )
        for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( state.sectionsLists[thisBible.abbreviation][BBB] ):
            documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
            startChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.htm#Top">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.htm#Top">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a title="Previous section" href="{BBB}_S{n-1}.htm#Top">←</a> ' if n>0 else ''
            rightLink = f' <a title="Next section" href="{BBB}_S{n+1}.htm#Top">→</a>' if n<len(bkObject._SectionIndex)-1 else ''
            parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}pa/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">║</a>'''
            interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
            detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''

            sectionHtml = f'''<h1><span title="{state.BibleNames[thisBible.abbreviation]}">{thisBible.abbreviation}</span> by section {ourTidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<p class="secNav">{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{parallelLink}{interlinearLink}{detailsLink}</p>
{'<p class="rem">This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.</p>' if 'OET' in thisBible.abbreviation else ''}
<h1>{sectionName}</h1>
'''
            textHtml = convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,startC), 'section', contextList, verseEntryList, basicOnly=False, state=state )
            # textHtml = livenIORs( BBB, textHtml, sections )
            if thisBible.abbreviation == 'OET-RV':
                textHtml = do_OET_RV_HTMLcustomisations( textHtml )
            elif thisBible.abbreviation == 'OET-LV':
                textHtml = do_OET_LV_HTMLcustomisations( textHtml )
            elif thisBible.abbreviation == 'LSV':
                textHtml = do_LSV_HTMLcustomisations( textHtml )
            elif thisBible.abbreviation == 'T4T':
                textHtml = do_T4T_HTMLcustomisations( textHtml )
            sectionHtml = f'{sectionHtml}{textHtml}'

            filepath = folder.joinpath( filename )
            top = makeTop( level, thisBible.abbreviation, 'section', f'bySec/{BBB}.htm', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} section" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, section' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{filename}#Top">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            sectionHtml = f'''{top}<!--section page-->
{navListParagraph}
{sectionHtml}
{makeBottom( level, 'section', state )}'''
            checkHtml( thisBible.abbreviation, sectionHtml )
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )
        # Now make the section index file for this book
        filename = f'{BBB}.htm'
        filepath = folder.joinpath( filename )
        top = makeTop( level, thisBible.abbreviation, 'section', f'bySec/{filename}', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} sections" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{filename}#Top">{thisBible.abbreviation}</a>''',
                        f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        sectionHtml = f'<h1 id="Top">Index of sections for {thisBible.abbreviation} {ourTidyBBB}</h1>\n'
        for startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in state.sectionsLists[thisBible.abbreviation][BBB]:
            reasonString = '' if reasonName=='Section heading' and not TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
            sectionHtml = f'''{sectionHtml}<p class="sectionHeading"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
        sectionHtml = f'''{top}<!--sections page-->
{navListParagraph}
{sectionHtml}
{makeBottom( level, 'section', state )}'''
        checkHtml( thisBible.abbreviation, sectionHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( sectionHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )

    # Now an overall index for sections
    filename = 'index.htm'
    # filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'section', 'bySec/', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} Sections View" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    indexHtml = f'''{top}
<h1 id="Top">{thisBible.abbreviation} section pages</h1>
<h2>Index of {thisBible.abbreviation} books</h2>
{navListParagraph}
{makeBottom( level, 'section', state)}'''
    checkHtml( thisBible.abbreviation, indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}." )
    # return filenames
# end of createSectionPages.createSectionPages



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
