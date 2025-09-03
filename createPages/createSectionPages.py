#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# createSectionPages.py
#
# Module handling OpenBibleData createSectionPages functions
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
Module handling createSectionPages functions.

Assumes that all books are already loaded.

createOETSectionLists( rvBible:ESFMBible, state:State ) -> bool
createOETSectionPages( level:int, folder:Path, rvBible:ESFMBible, lvBible:ESFMBible, state:State ) -> list[str]
createSectionPages( level:int, folder:Path, thisBible, state:State ) -> list[str]
findSectionNumber( versionAbbreviation:str, refBBB:str, refC:str, refV:str, state:State ) -> int|None
livenSectionReferences( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                sectionReferenceText:str, state:State ) -> str
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()

CHANGELOG:
    2023-08-07 Handle additional ESFM section headings, etc.
    2023-08-18 Handle additional section headings separated by semicolons
    2023-12-24 Added findSectionNumber() and livenSectionReferences() functions
    2024-01-24 Use new BibleOrgSys getContextVerseDataRange() function for OET-LV verse range
    2024-01-27 Add 'related section' links for OET and OET-RV pages
    2024-03-10 Add chapter bars to section pages, and add navigation to bottom of the pages as well
    2024-06-14 Make section cross-ref clicks go to parallel passage pages
    2024-06-26 Added BibleMapper.com maps to OET sections
    2025-02-02 Added ID to clinksPar (at top of page only)
    2025-03-24 Liven Readers' Version and Literal Version headings
    2025-05-21 Remove superfluous section headings in Psalms on the five "book" boundaries (chapters 1,42,73,90,107)
"""
from gettext import gettext as _
from pathlib import Path
import os
import logging
from collections import defaultdict

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_66
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
from BibleOrgSys.Formats.ESFMBible import ESFMBible as ESFMBible

from settings import State, reorderBooksForOETVersions
from usfm import convertUSFMMarkerListToHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from Bibles import getBibleMapperMaps
from OETHandlers import livenOETWordLinks, getOETTidyBBB, getBBBFromOETBookName


LAST_MODIFIED_DATE = '2025-08-24' # by RJH
SHORT_PROGRAM_NAME = "createSectionPages"
PROGRAM_NAME = "OpenBibleData createSectionPages functions"
PROGRAM_VERSION = '0.72'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEWLINE = '\n'

SECTION_REASON_NAME_DICT = { 'Headers':'Headers', 'is1':'Introduction section heading',
                         'c':'Start of chapter', 's1':'Section heading', 'c/s1':'Section heading',
                         'ms1':'Main section', 'ms1/c':'Main section', 'ms1/s1':'Main section with section heading', 'ms1/c/s1':'Main section with section heading' }


def createOETSectionLists( rvBible:ESFMBible, state:State ) -> bool:
    """
    Make our list of section headings
       The BibleOrgSys section index already contains a list of sections
    """
    rvBible.makeSectionIndex() # These aren't made automatically

    state.sectionsLists = {}
    state.sectionsLists['OET-RV'] = {}
    for BBB in state.BBBsToProcess['OET']:
        # Firstly, make a list of additional section headings (\\rem /s1 fields in OET-RV)
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
                assert given_marker in ('s1','r','s2','s3','d'), f"OET-RV {BBB} {C}:{V} {given_marker=}"
                rest = rest[len(given_marker)+2:] # Drop the '/marker ' from the displayed portion
                plusOneV = str( getLeadingInt(V) + 1 ) # Also handles verse ranges
                for sectionChunk in rest.split( '; ' ):
                    additionalSectionHeadingsDict[(C,plusOneV)].append( (given_marker,sectionChunk) )
        # if additionalSectionHeadingsDict: print( f"HERE1 {BBB} {additionalSectionHeadingsDict}" )

        if not rvBible[BBB]._SectionIndex: # no sections in this book, e.g., FRT
            continue

        # Now create the main sections list for this book
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
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {NEWLINE*2}createOETSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} {sectionIndexEntry=}" )
                # Insert any additional section headings BEFORE this one
                for (c,v),additionalFieldList in additionalSectionHeadingsDict.copy().items():
                    # print( f"{c}:{v} {additionalFieldList}" )
                    if int(c) < intStartC \
                    or c==startC and int(v) < intStartV:
                        for additionalMarker,additionalFieldText in additionalFieldList:
                            if additionalMarker in ('s1','s2','s3'):
                                additionalMarkerName = { 's1':'section heading', 's2':'2nd level section heading', 's3':'3rd level section heading' }[additionalMarker]
                                # NOTE: word 'Alternate ' is searched for below
                                state.sectionsLists['OET-RV'][BBB].append( (n,c,v,'?','?',additionalFieldText,f'Alternate {additionalMarkerName}',[],[],sectionFilename) )
                            else:
                                logging.warning( f"createOETSectionPages ignored additional \\{additionalMarker} at OET-RV {BBB} {c}:{v}" )
                        del additionalSectionHeadingsDict[(c,v)]
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            sectionName = sectionName.replace( "'", "’" ) # Replace apostrophes
            sectionFilename = f'{BBB}_S{n}.htm'
            # if additionalSectionHeadingsDict:
            #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = SECTION_REASON_NAME_DICT[reasonMarker]
            rvVerseEntryList, rvContextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            # Check that we don't have any duplicated verses in the section
            lastV = None
            for entry in rvVerseEntryList:
                marker, text = entry.getMarker(), entry.getFullText()
                # dPrint( 'Info', DEBUGGING_THIS_MODULE, ( f"createOETSectionLists {marker}={text}" )
                if marker == 'v':
                    assert text != lastV
                    lastV = text
            state.sectionsLists['OET-RV'][BBB].append( (n,startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,sectionFilename) )
        if additionalSectionHeadingsDict:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{BBB} didn't use {additionalSectionHeadingsDict=}")
        # Handle left-over additions
        for (c,v),additionalFieldList in additionalSectionHeadingsDict.copy().items():
            # print( f"{c}:{v} {additionalFieldList}" )
            for additionalMarker,additionalFieldText in additionalFieldList:
                additionalMarkerName = { 's1':'section heading', 's3':'sub-heading3', 'r':'section cross-reference', 'd':'song/Psalm details' }[additionalMarker]
                # NOTE: word 'Alternate ' is searched for below and in findSectionNumber()
                state.sectionsLists['OET-RV'][BBB].append( (n,c,v,'?','?',additionalFieldText,f'Alternate {additionalMarkerName}',[],[],sectionFilename) )
            del additionalSectionHeadingsDict[(c,v)]
        if additionalSectionHeadingsDict:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{BBB} didn't use {additionalSectionHeadingsDict=}")
            halt
        assert len(state.sectionsLists['OET-RV'][BBB]) >= len(bkObject._SectionIndex), f"{BBB}: {len(state.sectionsLists['OET-RV'][BBB])=} {len(bkObject._SectionIndex)=}"

    return True
# end of createSectionPages.createOETSectionLists

def createOETSectionPages( level:int, folder:Path, rvBible:ESFMBible, lvBible:ESFMBible, state:State ) -> list[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETSectionPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )
    assert rvBible.discoveryResults['ALL']['haveSectionHeadings']
    assert not lvBible.discoveryResults['ALL']['haveSectionHeadings']

    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # rvBooks = rvBible.books.keys() if 'ALL' in state.booksToLoad[rvBible.abbreviation] else state.booksToLoad[rvBible.abbreviation]
    # lvBooks = lvBible.books.keys() if 'ALL' in state.booksToLoad[lvBible.abbreviation] else state.booksToLoad[lvBible.abbreviation]
    # BBBsToProcess = reorderBooksForOETVersions( [rvKey for rvKey in rvBooks if rvKey in lvBooks] )
    navBookListParagraph = makeBookNavListParagraph( state.BBBLinks['OET'], 'OET', state )

    # Now, make the actual section pages
    BBBs = []
    state.sectionsWithMaps = defaultdict( list )
    for BBB in state.BBBsToProcess['OET']:
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        ourTidyBBB = getOETTidyBBB( BBB )
        ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {BBB=} {state.BBBsToProcess['OET']}/{len(state.BBBsToProcess['OET'])}")

        # # TODO: Can we delete all this now???
        # if lvBible.abbreviation=='OET-LV' \
        # and BBB in ('INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"A Skipped OET sections difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
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

        numChapters = rvBible.getNumChapters( BBB )
        cLinks = [f'<a title="Choose “book”" href="./">{ourTidyBBBwithNotes}</a>']
        if numChapters >= 1:
            if rvBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm#Top">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a title="View chapter page instead" href="../byC/{BBB}_C{c}.htm#Top">{'Sg' if BBB=='PSA' else 'C'}{c}</a>' )
        else:
            c = '0' # TODO: for now
            halt
        cLinksPar = f'<p class="chLst">{" ".join( cLinks )}</p>'

        # # First, get our list of sections
        BBBs.append( BBB )
        numBBBSections = len(rvBible[BBB]._SectionIndex)
        # bkObject = rvBible[BBB]
        # state.sectionsLists['OET-RV'][BBB] = []
        # for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
        #     # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"OET {NEWLINE*2}createOETSectionPages {n}: {BBB}_{startC}:{startV} {type(sectionIndexEntry)} ({len(sectionIndexEntry)}) {sectionIndexEntry=}" )
        #     sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
        #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
        #     reasonName = REASON_NAME_DICT[reasonMarker]
        #     startC,startV = startCV
        #     endC,endV = sectionIndexEntry.getEndCV()
        #     rvVerseEntryList, rvContextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
        #     sectionFilename = f'{BBB}_S{n}.htm'
        #     state.sectionsLists['OET-RV'][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,sectionFilename) )

        # Now, make the actual section pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for OET {BBB}…" )
        # numExtrasSkipped = 0
        documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBBwithNotes}</a>'
        sectionIndexLink = f'<a title="Go up to OET section index" href="{BBB}.htm#Top">⌂</a> '
        detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''
        for n,startC,startV,endC,endV,sectionName,reasonName,rvContextList,rvVerseEntryList,sectionFilename in state.sectionsLists['OET-RV'][BBB]:
            if endC == '?': # Then these are the additional/alternative headings
                assert endV == '?'
                # numExtrasSkipped += 1
                continue
            # if BBB=='KI2' and n==5:
            #     print( f"{BBB} S{n}")
            #     for entry in rvVerseEntryList:
            #         print( f"   {entry}")
            #     # halt
            # if 'Psalm' in sectionName or 'Songs' in sectionName:
            #     print( f"OET {sectionName=}" ); halt
            # n2 = n1 - numExtrasSkipped
            startChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.htm#Top">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.htm#Top">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a title="Previous section" href="{BBB}_S{n-1}.htm#Top">←</a> ' if n>0 else ''
            rightLink = f' <a title="Next section" href="{BBB}_S{n+1}.htm#Top">→</a>' if n<numBBBSections-1 else ''
            relatedLink = f''' <a title="Related section view" href="{'../'*level}rel/{BBB}/{sectionFilename}#Top">◘</a>'''
            parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}par/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">║</a>'''
            interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}ilr/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''

            sectionHtml = f'''<h1 id="Top"><span title="Open English Translation">OET</span> by section {ourTidyBBBwithNotes} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<p class="secNav">{sectionIndexLink}{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{relatedLink}{parallelLink}{interlinearLink}{detailsLink}</p>
<h1>{'TEST ' if state.TEST_MODE else ''}{sectionName}</h1>
{state.OET_UNFINISHED_WARNING_HTML_PARAGRAPH}
<div class="RVLVcontainer">
<h2><a title="View just the Readers’ Version by itself" href="{'../'*level}OET-RV/bySec/{BBB}_S{n}.htm#Top">Readers’ Version</a></h2>
<h2><a title="View just the Literal Version (chapter) by itself" href="{'../'*level}OET-LV/byC/{BBB}_C{startC}.htm#V{startV}">Literal Version</a> <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>'''
            if isinstance( rvBible, ESFMBible ):
                rvVerseEntryList = livenOETWordLinks( level, rvBible, BBB, rvVerseEntryList, state )
            rvHtml = convertUSFMMarkerListToHtml( level, rvBible.abbreviation, (BBB,startC, startV), 'section', rvContextList, rvVerseEntryList, basicOnly=False, state=state )
            rvHtml = do_OET_RV_HTMLcustomisations( f'SectionA={BBB}_{startC}', rvHtml )
            # rvHtml = livenIORs( BBB, rvHtml, sections )

            try:
                lvVerseEntryList, lvContextList = lvBible.getContextVerseDataRange( (BBB, startC, startV), (BBB, endC, endV) )
            except KeyError: # this can fail in the introduction which is missing from LV
                logging.critical( f"Seems OET-LV {BBB} is missing section starting with {startC}:{startV}" )
                lvVerseEntryList, lvContextList = [], []
            if isinstance( lvBible, ESFMBible ):
                lvVerseEntryList = livenOETWordLinks( level, lvBible, BBB, lvVerseEntryList, state )
            lvHtml = convertUSFMMarkerListToHtml( level, lvBible.abbreviation, (BBB,startC), 'section', lvContextList, lvVerseEntryList, basicOnly=False, state=state )
            lvHtml = do_OET_LV_HTMLcustomisations( f'SectionA={BBB}_{startC}', lvHtml )
            # Handle footnotes so the same fn1 doesn't occur for both chunks if they both have footnotes
            rvHtml = rvHtml.replace( 'id="footnotes', 'id="footnotesRV' ).replace( 'id="crossRefs', 'id="crossRefsRV' ).replace( 'id="fn', 'id="fnRV' ).replace( 'href="#fn', 'href="#fnRV' )
            lvHtml = lvHtml.replace( 'id="footnotes', 'id="footnotesLV' ).replace( 'id="crossRefs', 'id="crossRefsLV' ).replace( 'id="fn', 'id="fnLV' ).replace( 'href="#fn', 'href="#fnLV' )
            combinedHtml = f'''<div class="chunkRV">{rvHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvHtml}</div><!--chunkLV-->
'''
            combinedHtml = f'{removeDuplicateCVids( combinedHtml )}</div><!--RVLVcontainer-->'
            
            # Handle BibleMapper maps and notes -- could be zero or more for any one section
            bmmHtml = getBibleMapperMaps( level, BBB, startC, startV, endC, endV, state.preloadedBibles['OET-RV'], state )
            if bmmHtml:
                # print( f"{BBB} {startC}:{startV} to {endC}:{endV} got {len(bmmHtml)} map(s)")
                bmmHtml = f'''<div id="BMM" class="parallelBMM"><a title="Go to BMM copyright page" href="{'../'*level}BMM/details.htm#Top">BMM</a> <b><a href="https://BibleMapper.com" target="_blank" rel="noopener noreferrer">BibleMapper.com</a> Maps</b>: {bmmHtml}</div><!--end of BMM-->'''
                combinedHtml = f'{combinedHtml}\n<hr style="width:45%;margin-left:0;margin-top: 0.3em">\n{bmmHtml}'
                state.sectionsWithMaps[BBB].append( n )

            filepath = folder.joinpath( sectionFilename )
            top = makeTop( level, 'OET', 'section', f'bySec/{BBB}.htm', state ) \
                    .replace( '__TITLE__', f"OET {ourTidyBBB} section{' TEST' if state.TEST_MODE else ''}" ) \
                    .replace( '__KEYWORDS__', f'Bible, OET, section, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/bySec/{sectionFilename}#Top">OET</a>''',
                            f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET/">↑OET</a>''' )
            sectionHtml = f'''{top}<!--section page-->
{navBookListParagraph}
{cLinksPar.replace( 'class="chLst">', 'class="chLst" id="chLst">', 1 )}
{sectionHtml}
{combinedHtml}
<p class="secNav">{sectionIndexLink}{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{relatedLink}{parallelLink}{interlinearLink}{detailsLink}</p>
{cLinksPar}
{makeBottom( level, 'section', state )}'''
            assert checkHtml( f'{rvBible.abbreviation} {BBB} section', sectionHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )

        # Now make the section index file for this book
        indexFilename = f'{BBB}.htm'
        indexFilepath = folder.joinpath( indexFilename )
        top = makeTop( level, 'OET', 'sectionIndex', f'bySec/{indexFilename}', state ) \
                .replace( '__TITLE__', f"OET {ourTidyBBB} sections{' TEST' if state.TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, sections, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*2}OET/bySec/{indexFilename}#Top">OET</a>''',
                        f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*2}OET/">↑OET</a>''' )
        sectionHtml = f'<h1 id="Top">Index of sections for OET {ourTidyBBBwithNotes}</h1>'
        for _nnn,startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,sectionFilename in state.sectionsLists['OET-RV'][BBB]:
            # print( f"HERE8 {BBB} {startC}:{startV} {_endC}:{endV} '{sectionName=}' '{reasonName=}' '{filename=}'" )
            reasonString = '' if reasonName=='Section heading' and not state.TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
            # NOTE: word 'Alternate ' is defined above at start of main loop
            sectionHtml = f'''{sectionHtml}\n<p class="{'alternateHeading' if reasonName.startswith('Alternate ') else 'sectionHeading'}"><a title="View section" href="{sectionFilename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>'''

        sectionHtml = f'''{top}<!--sections page-->
{navBookListParagraph}
{sectionHtml}
{makeBottom( level, 'sectionIndex', state )}'''
        assert checkHtml( 'OET section index', sectionHtml )
        assert not indexFilepath.is_file() # Check that we're not overwriting anything
        with open( indexFilepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( sectionHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {indexFilepath}" )

    # Now a single overall index page for sections
    indexFilename = 'index.htm'
    # filenames.append( filename )
    indexFilepath = folder.joinpath( indexFilename )
    top = makeTop( level, 'OET', 'sectionIndex', 'bySec/', state ) \
            .replace( '__TITLE__', f"OET Sections View{' TEST' if state.TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, OET, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*2}OET">OET</a>''', 'OET' )
    indexHtml = f'''{top}
<h1 id="Top">OET section pages</h1>
<h2>Index of OET books</h2>
{navBookListParagraph}
{makeBottom( level, 'sectionIndex', state)}'''
    assert checkHtml( 'OET sections index', indexHtml )
    assert not indexFilepath.is_file() # Check that we're not overwriting anything
    with open( indexFilepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {indexFilepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETSectionPages() finished processing {len(BBBs)} OET books: {BBBs}." )
# end of createSectionPages.createOETSectionPages


def createSectionPages( level:int, folder:Path, thisBible, state:State ) -> list[str]:
    """
    This creates a page for each section for all versions other than 'OET' (dual columns)
                                which is considerably more complex (above).
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createSectionPages( {level}, {folder}, {thisBible.abbreviation} )" )
    assert thisBible.abbreviation != 'OET'
    assert thisBible.discoveryResults['ALL']['haveSectionHeadings']
    thisBible.makeSectionIndex() # These aren't made automatically by BibleOrgSys

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state)

    # Firstly make our list of section headings
    # if thisBible.abbreviation != 'OET-RV': # that's been done already in the above function WRONG Might not have been done for all books
    if thisBible.abbreviation != 'OET-RV':
        assert thisBible.abbreviation not in state.sectionsLists, f"{thisBible.abbreviation=} {state.sectionsLists.keys()=}"
        state.sectionsLists[thisBible.abbreviation] = {}
    for BBB in state.BBBsToProcess[thisBible.abbreviation]:
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        # if thisBible.abbreviation=='OET-LV' \
        # and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"AA Skipped OET sections difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
        if thisBibleBooksToLoad not in (['ALL'],['NT']) \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped sections difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books
        if thisBible.abbreviation=='OET-RV' and BBB in state.sectionsLists[thisBible.abbreviation]:
            continue # We've already done it
        bkObject = thisBible[BBB]
        state.sectionsLists[thisBible.abbreviation][BBB] = []
        for n,(startCV, sectionIndexEntry) in enumerate( bkObject._SectionIndex.items() ):
            # if thisBible.abbreviation == 'BSB' and BBB=='PSA':
            #     dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {NEWLINE}createSectionPages {n}: {BBB}_{startCV} {type(sectionIndexEntry)} {sectionIndexEntry=}" )
            sectionName, reasonMarker = sectionIndexEntry.getSectionNameReason()
            if 'OET' in thisBible.abbreviation:
                sectionName = sectionName.replace( "'", "’" ) # Replace apostrophes
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE,  f"{sectionName=} {reasonMarker=}" )
            reasonName = SECTION_REASON_NAME_DICT[reasonMarker]
            startC,startV = startCV
            endC,endV = sectionIndexEntry.getEndCV()
            verseEntryList, contextList = bkObject._SectionIndex.getSectionEntriesWithContext( startCV )
            if isinstance( thisBible, ESFMBible ):
                verseEntryList = livenOETWordLinks( level, thisBible, BBB, verseEntryList, state )
            sectionFilename = f'{BBB}_S{n}.htm'
            state.sectionsLists[thisBible.abbreviation][BBB].append( (n,startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sectionFilename) )
        assert len(state.sectionsLists[thisBible.abbreviation][BBB]) >= len(bkObject._SectionIndex)

    # Now, make the actual pages
    BBBs = []
    for BBB in state.BBBsToProcess[thisBible.abbreviation]:
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        ourTidyBBB = getOETTidyBBB( BBB )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {BBB=} {state.BBBsToProcess[thisBible.abbreviation]}/{len(state.BBBsToProcess[thisBible.abbreviation])}")

        # if thisBible.abbreviation=='OET-LV' \
        # and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"AA Skipped OET sections difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
        if thisBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[thisBible.abbreviation] \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped sections difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        numChapters = thisBible.getNumChapters( BBB )
        if numChapters >= 1:
            cLinks = [f'<a title="Choose “book”" href="./">{ourTidyBBB}</a>']
            if thisBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm#Top">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a title="View chapter page instead" href="../byC/{BBB}_C{c}.htm#Top">{'Sg' if 'OET' in thisBible.abbreviation and BBB=='PSA' else 'Ps' if BBB=='PSA' else 'C'}{c}</a>' )
            cLinksPar = f'<p class="chLst">{" ".join( cLinks )}</p>' if cLinks else ''
        else:
            # c = '0' # TODO: for now
            cLinksPar = ''

        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {type(thisBible[BBB]._SectionIndex)=} {thisBible[BBB]._SectionIndex=}" )
        if not thisBible[BBB]._SectionIndex: # no sections in this book, e.g., FRT
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"No section headings in {thisBible.abbreviation} {BBB} -- skipping section pages" )
            sectionFilename = f'{BBB}.htm'
            filepath = folder.joinpath( sectionFilename )
            top = makeTop( level, thisBible.abbreviation, 'section', f'bySec/{sectionFilename}', state ) \
                    .replace( '__TITLE__', f"{thisBible.abbreviation} {ourTidyBBB} sections{' TEST' if state.TEST_MODE else ''}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{sectionFilename}#Top">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            sectionHtml = f'<h1 id="Top">{thisBible.abbreviation} {ourTidyBBB} has NO section headings</h1>'

            sectionHtml = f'''{top}<!--no sections page-->
{navBookListParagraph}
{sectionHtml}
{makeBottom( level, 'section', state )}'''
            assert checkHtml( f'{thisBible.abbreviation} {BBB} section', sectionHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )
            continue

        # First, get our list of sections
        BBBs.append( BBB )
        numBBBSections = len(thisBible[BBB]._SectionIndex)
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
        #     sectionFilename = f'{BBB}_S{n}.htm'
        #     state.sectionsLists[thisBible.abbreviation][BBB].append( (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sectionFilename) )

        # Now, make the actual pages
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating section pages for {thisBible.abbreviation} {BBB}…" )
        documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
        sectionIndexLink = f'<a title="Go up to section index" href="{BBB}.htm#Top">⌂</a> '
        detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''
        for n,startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sectionFilename in state.sectionsLists[thisBible.abbreviation][BBB]:
            if endC == '?': # Then these are the OET-RV additional/alternative headings
                assert thisBible.abbreviation == 'OET-RV'
                assert endV == '?'
                continue
            if sectionName.startswith( 'Psalms '):
                # print( f"{thisBible.abbreviation} {sectionName=}" )
                sectionName = sectionName.replace( 'Psalms', 'Song' if 'OET' in thisBible.abbreviation else 'Psalm' )
            startChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.htm#Top">{'Intro' if startC=='-1' else startC}</a>'''
            endChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.htm#Top">{'Intro' if endC=='-1' else endC}</a>'''
            leftLink = f'<a title="Previous section" href="{BBB}_S{n-1}.htm#Top">←</a> ' if n>0 else ''
            rightLink = f' <a title="Next section" href="{BBB}_S{n+1}.htm#Top">→</a>' if n<numBBBSections-1 else ''
            relatedLink = f''' <a title="Related section view" href="{'../'*level}rel/{BBB}/{sectionFilename}#Top">◘</a>''' if thisBible.abbreviation=='OET-RV' else ''
            parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}par/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">║</a>'''
            interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}ilr/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''

            sectionHtml = f'''<h1><span title="{state.BibleNames[thisBible.abbreviation]}">{thisBible.abbreviation}</span> by section {ourTidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<p class="secNav">{sectionIndexLink}{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{relatedLink}{parallelLink}{interlinearLink}{detailsLink}</p>
{f'{state.JAMES_NOTE_HTML_PARAGRAPH}{NEWLINE}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{state.OET_UNFINISHED_WARNING_HTML_PARAGRAPH}{NEWLINE}' if 'OET' in thisBible.abbreviation else ''}{f'{state.BLACK_LETTER_FONT_HTML_PARAGRAPH}{NEWLINE}' if thisBible.abbreviation=='KJB-1611' else ''}<h1>{sectionName}</h1>'''
            if isinstance( thisBible, ESFMBible ): # e.g., OET-RV
                verseEntryList = livenOETWordLinks( level, thisBible, BBB, verseEntryList, state )
            textHtml = convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,startC), 'section', contextList, verseEntryList, basicOnly=False, state=state )
            # textHtml = livenIORs( BBB, textHtml, sections )
            if thisBible.abbreviation == 'OET-RV':
                textHtml = do_OET_RV_HTMLcustomisations( f'SectionB={BBB}_{startC}', textHtml )
            elif thisBible.abbreviation == 'OET-LV':
                textHtml = do_OET_LV_HTMLcustomisations( f'SectionB={BBB}_{startC}', textHtml )
            elif thisBible.abbreviation == 'LSV':
                textHtml = do_LSV_HTMLcustomisations( f'SectionB={BBB}_{startC}', textHtml )
            elif thisBible.abbreviation == 'T4T':
                textHtml = do_T4T_HTMLcustomisations( f'SectionB={BBB}_{startC}', textHtml )
            elif thisBible.abbreviation == 'KJB-1611':
                textHtml = textHtml.replace( 'class="add"', 'class="add_KJB-1611"' )
            sectionHtml = f'''{sectionHtml}{textHtml}
<p class="secNav">{sectionIndexLink}{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{relatedLink}{parallelLink}{interlinearLink}{detailsLink}</p>'''

            filepath = folder.joinpath( sectionFilename )
            top = makeTop( level, thisBible.abbreviation, 'section', f'bySec/{BBB}.htm', state ) \
                    .replace( '__TITLE__', f"{thisBible.abbreviation} {ourTidyBBB} section{' TEST' if state.TEST_MODE else ''}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, section, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{sectionFilename}#Top">{thisBible.abbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            sectionHtml = f'''{top}<!--section page-->
{navBookListParagraph}
{cLinksPar.replace( 'class="chLst">', 'class="chLst" id="chLst">', 1 )}
{sectionHtml}
{cLinksPar}
{makeBottom( level, 'section', state )}'''
            assert checkHtml( f'{thisBible.abbreviation} {BBB} section', sectionHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
                sectionHtmlFile.write( sectionHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {filepath}" )

        # Now make the section index file for this book
        sectionFilename = f'{BBB}.htm'
        indexFilepath = folder.joinpath( sectionFilename )
        top = makeTop( level, thisBible.abbreviation, 'sectionIndex', f'bySec/{sectionFilename}', state ) \
                .replace( '__TITLE__', f"{thisBible.abbreviation} {ourTidyBBB} sections{' TEST' if state.TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/bySec/{sectionFilename}#Top">{thisBible.abbreviation}</a>''',
                        f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        sectionHtml = f'<h1 id="Top">Index of sections for {thisBible.abbreviation} {ourTidyBBB}</h1>\n'
        for _nnn,startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,sectionFilename in state.sectionsLists[thisBible.abbreviation][BBB]:
            reasonString = '' if reasonName=='Section heading' and not state.TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
            # NOTE: word 'Alternate ' is defined in the above OET function at start of main loop
            sectionHtml = f'''{sectionHtml}<p class="{'alternateHeading' if reasonName.startswith('Alternate ') else 'sectionHeading'}"><a title="View section" href="{sectionFilename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>'''
            # sectionHtml = f'''{sectionHtml}<p class="sectionHeading"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
        sectionHtml = f'''{top}<!--sections page-->
{navBookListParagraph}
{sectionHtml}
{makeBottom( level, 'sectionIndex', state )}'''
        assert checkHtml( f'{thisBible.abbreviation} section index', sectionHtml )
        assert not indexFilepath.is_file() # Check that we're not overwriting anything
        with open( indexFilepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( sectionHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(sectionHtml):,} characters written to {indexFilepath}" )

    # Now an overall index for sections
    sectionFilename = 'index.htm'
    # filenames.append( filename )
    indexFilepath = folder.joinpath( sectionFilename )
    top = makeTop( level, thisBible.abbreviation, 'sectionIndex', 'bySec/', state ) \
            .replace( '__TITLE__', f"{thisBible.abbreviation} Sections View{' TEST' if state.TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, books' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    indexHtml = f'''{top}
<h1 id="Top">{thisBible.abbreviation} section pages</h1>
<h2>Index of {thisBible.abbreviation} books</h2>
{navBookListParagraph}
{makeBottom( level, 'sectionIndex', state)}'''
    assert checkHtml( f'{thisBible.abbreviation} sections index', indexHtml )
    assert not indexFilepath.is_file() # Check that we're not overwriting anything
    with open( indexFilepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {indexFilepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSectionPages() finished processing {len(BBBs)} {thisBible.abbreviation} books: {BBBs}." )
    # return filenames
# end of createSectionPages.createSectionPages


def findSectionNumber( versionAbbreviation:str, refBBB:str, refC:str, refV:str, state:State ) -> int|None:
    """
    Given a BCV reference and a Bible that has s1 section headings,
        return the section number containing the given reference.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"findSectionNumber( {versionAbbreviation}, {refBBB} {refC}:{refV} )" )

    if not refBBB:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, "findSectionNumber: No refBBB parameter given -- returning None" )
        return None # Can't do anything without a valid BBB
    if refBBB not in BOOKLIST_66 and versionAbbreviation not in state.VERSIONS_WITH_APOCRYPHA:
        logging.warning( f"Unable to continue in findSectionNumber( {versionAbbreviation}, {refBBB} {refC}:{refV} )" )
        return None # Can't do anything here
    if refBBB not in state.sectionsLists[versionAbbreviation]: # No section headings for this book
        if state.TEST_MODE:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, "default to introduction for state.TEST_MODE (because it doesn't contain all the books)" )
            return 0 # default to introduction for testing (because it doesn't contain all the books)
        else:
            logger = logging.critical if DEBUGGING_THIS_MODULE else logging.error
            logger( f"findSectionNumber: No {versionAbbreviation} sectionsLists for {refBBB} -- only have {state.sectionsLists[versionAbbreviation].keys()} -- returning None" )
            return None

    if refV == '0':
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"findSectionNumber: adjusting {versionAbbreviation} search for {refBBB} {refC}:{refV} to verse 1" )
        refV = '1'
    intRefV = getLeadingInt( refV )

    for n,startC,startV,endC,endV,_sectionName,reasonName,_contextList,_verseEntryList,_filename in state.sectionsLists[versionAbbreviation][refBBB]:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\nLOOP {n} finding {versionAbbreviation} {refBBB} {refC}:{refV} in {startC}:{startV}-{endC}:{endV} {_sectionName=},{reasonName=},_contextList,_verseEntryList,{_filename}" )
        if reasonName.startswith( 'Alternate ' ): continue # ignore these ones

        # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  findSectionNumber for {versionAbbreviation} {refBBB} {refC}:{refV} got {state.sectionsLists[versionAbbreviation][refBBB][n]}")
        if startC==refC and endC==refC: # This section only spans a single chapter (or part of a chapter)
            if getLeadingInt(startV) <= intRefV <= getLeadingInt(endV): # It's in this single chapter
                return n
        else: # This section spans two or more chapters
            if startC==refC and intRefV>=getLeadingInt(startV): # It's in the first chapter
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found {refBBB} {refC}:{refV} in first chapter of {startC}:{startV}-{endC}:{endV}" )
                return n
            elif endC==refC and intRefV<=getLeadingInt(endV): # It's in the last chapter
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found {refBBB} {refC}:{refV} in last chapter of {startC}:{startV}-{endC}:{endV}" )
                return n
            elif int(startC) < int(refC) < int(endC): # It's in one of the middle chapters
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found {refBBB} {refC}:{refV} in middle chapter of {startC}:{startV}-{endC}:{endV}" )
                return n

    dPrint( 'Info', DEBUGGING_THIS_MODULE, "findSectionNumber: Couldn't find a section match -- returning None" )
    return None
# end of createSectionPages.findSectionNumber


def livenSectionReferences( versionAbbreviation:str, refTuple:tuple, segmentType:str, sectionReferenceText:str, state:State ) -> str:
    """
    Given some text (from USFM \\r field),
        convert the list of references (often enclosed in parenthesis) into live links

    NOTE: We remove any spaces after commas, which means we can't necessarily restore them exactly the same
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' )" )
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' )…" )
    assert '\\' not in sectionReferenceText

    # ourBBB = refTuple[0]

    # Remove enclosing parentheses if any, e.g., in '(Luk. 3:23-38)'
    enclosedByParentheses = sectionReferenceText[0]=='(' and sectionReferenceText[-1]==')'
    if enclosedByParentheses: sectionReferenceText = sectionReferenceText[1:-1]

    # Tokenise
    # NOTE: We remove any spaces after commas, which means we can't necessarily restore them exactly the same
    tokens = sectionReferenceText.replace(';',',,').replace(', ',',').split( ',' )

    def livenSectionReferencesDigits( versionAbbreviation:str, refTuple:tuple, segmentType:str, refBBB:str, sectionReferenceDigitsText:str, state:State ) -> str:
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"livenSectionReferencesDigits( {versionAbbreviation}, {refTuple}, {segmentType}, {refBBB}, '{sectionReferenceDigitsText}' )" )
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"livenSectionReferencesDigits( {versionAbbreviation}, {refTuple}, {segmentType}, {refBBB} '{sectionReferenceDigitsText}' )…" )
        assert refBBB in BOOKLIST_66, f"livenSectionReferencesDigits( {versionAbbreviation}, {refTuple}, {segmentType}, {refBBB}, '{sectionReferenceDigitsText}' )"
        assert ' ' not in sectionReferenceDigitsText and ',' not in sectionReferenceDigitsText and ';' not in sectionReferenceDigitsText

        isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( refBBB )

        # The link will always be to the beginning of a span
        if '-' in sectionReferenceDigitsText or '–' in sectionReferenceDigitsText or '—' in sectionReferenceDigitsText:
            # so throw away anything after the beginning of the reference
            sectionReferenceDigitsText = sectionReferenceDigitsText.replace('–','-').replace('—','-').split( '-' )[0]

        # sectionReferenceLink = ''
        if sectionReferenceDigitsText.count( ':' ) == 1:
            refC,refV = sectionReferenceDigitsText.split( ':' )
            # assert segmentType in ('book','chapter','section')
            if segmentType == 'relatedPassage':
                # print( f"{state.sectionsLists[versionAbbreviation]}")
                sectionNumber = findSectionNumber( versionAbbreviation, refBBB, refC, refV, state )
                if sectionNumber is not None:
                    sectionReferenceLink = f'../{refBBB}/{refBBB}_S{sectionNumber}.htm#V{refV}'
                else:
                    logging.critical( f"unable_to_find_reference for {refBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation]]}" )
                    unable_to_find_reference # Need to write more code
                # print( f"  {sectionNumber=} {sectionReferenceLink=}")
            elif segmentType == 'topicalPassage':
                sectionReferenceLink = f'{refBBB}.htm#C{refC}V{refV}' # What's expected here ??? TMP XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            elif 'OET' in versionAbbreviation \
            and segmentType in ('book','chapter','section'):
                # Always go to a related passage display
                # print( f"{state.sectionsLists[versionAbbreviation]}")
                sectionNumber = findSectionNumber( versionAbbreviation, refBBB, refC, refV, state )
                if sectionNumber is not None:
                    sectionReferenceLink = f'../../rel/{refBBB}/{refBBB}_S{sectionNumber}.htm#V{refV}'
                else:
                    logging.critical( f"unable_to_find_reference for {refBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation]]}" )
                    unable_to_find_reference # Need to write more code
                # print( f"  {sectionNumber=} {sectionReferenceLink=}")
            elif segmentType == 'book':
                sectionReferenceLink = f'{refBBB}.htm#C{refC}V{refV}' 
            elif segmentType == 'chapter':
                sectionReferenceLink = f'{refBBB}_C{refC}.htm#V{refV}' 
            elif segmentType == 'section':
                # print( f"{state.sectionsLists[versionAbbreviation]}")
                sectionNumber = findSectionNumber( versionAbbreviation, refBBB, refC, refV, state )
                if sectionNumber is not None:
                    sectionReferenceLink = f'{refBBB}_S{sectionNumber}.htm#V{refV}'
                else:
                    logging.critical( f"unable_to_find_reference for {refBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation]]}" )
                    unable_to_find_reference # Need to write more code
                # print( f"  {sectionNumber=} {sectionReferenceLink=}")
            else: raise ValueError( f"Not a recognised {segmentType=}" )
        else:
            logging.warning( f"Not one colon from livenSectionReferencesDigits( {versionAbbreviation}, {refTuple}, {segmentType}, {refBBB} '{sectionReferenceDigitsText}' )" )
            sectionReferenceLink = sectionReferenceDigitsText

        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' ) about to return {sectionReferenceLink=}" )
        return sectionReferenceLink
    # end of usfm.livenSectionReferences.livenSectionReferencesDigits function
        
    sectionReferenceHtml = ''
    currentBBB = None
    for n,token in enumerate( tokens ):
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f" livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' ) processing {n}: {token=}…" )
        if not token: # then the previous one was ended by a semi-colon
            # Usually this means a change of book or chapter
            pass # We don't actually need to do anything here
        elif token.startswith('1 ') or token.startswith('2 ') or token.startswith('3 ') \
          or token.startswith('I ') or token.startswith('II ') or token.startswith('III ') \
          or token.startswith('Song of'):
            # Then we expect the token to start with something like '1 Cor.'
            assert token.count( ' ' ) >= 2, f"Bad {token=} from {versionAbbreviation} {refTuple} {segmentType} {currentBBB} {sectionReferenceText=}"
            bookAbbrev, rest = token.rsplit( ' ', 1 )
            currentBBB = getBBBFromOETBookName( bookAbbrev )
            assert currentBBB in BOOKLIST_66, f"{currentBBB=} from {bookAbbrev=} in livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' ) processing {n}: {token=}…"
            if currentBBB is None:
                logging.critical( f"livenSectionReferences1 was unable to find a book for '{token}' from '{sectionReferenceText}'" )
                liveLink = None
            else:
                liveLink = livenSectionReferencesDigits( versionAbbreviation, refTuple, segmentType, currentBBB, rest, state )
            tokenSectionReferenceHtml = f'<a href="{liveLink}">{token}</a>' \
                if liveLink and ('ALL' in state.booksToLoad[versionAbbreviation] or currentBBB in state.booksToLoad[versionAbbreviation]) \
                else token
            delimiter = '' if not sectionReferenceHtml else ', ' if n<2 or token[n-1] else '; '
            sectionReferenceHtml = f'{sectionReferenceHtml}{delimiter}{tokenSectionReferenceHtml}'
        elif (currentBBB is None or token[0].isalpha()) \
        and token.count(' ') == 1:
            # Then we expect the token to start with a bookname abbreviation
            # assert token.count( ' ' ) == 1, f"livenSectionReferences expected exactly one space in {versionAbbreviation}, {refTuple}, {segmentType}, '{token}' from '{sectionReferenceText}'"
            bookAbbrev, rest = token.split( ' ' ) # Assumes only one space
            currentBBB = getBBBFromOETBookName( bookAbbrev )
            if currentBBB is None:
                logging.error( f"livenSectionReferences2 was unable to find a book for '{token}' from '{sectionReferenceText}'" )
                liveLink = None
            else:
                liveLink = livenSectionReferencesDigits( versionAbbreviation, refTuple, segmentType, currentBBB, rest, state )
            tokenSectionReferenceHtml = f'<a href="{liveLink}">{token}</a>' \
                if liveLink and ('ALL' in state.booksToLoad[versionAbbreviation] or currentBBB in state.booksToLoad[versionAbbreviation]) \
                else token
            delimiter = '' if not sectionReferenceHtml else ', ' if n<2 or token[n-1] else '; '
            sectionReferenceHtml = f'{sectionReferenceHtml}{delimiter}{tokenSectionReferenceHtml}'
        else:
            logging.error( f"livenSectionReferences was unable to parse '{token}' from {versionAbbreviation} {refTuple} {segmentType} '{sectionReferenceText}'" )

    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  livenSectionReferences( {versionAbbreviation}, {refTuple}, {segmentType}, '{sectionReferenceText}' ) about to return {sectionReferenceHtml=}" )
    return f'({sectionReferenceHtml})' if enclosedByParentheses else sectionReferenceHtml 
# end of usfm.livenSectionReferences function



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
