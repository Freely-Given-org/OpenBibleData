#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createChapterPages.py
#
# Module handling OpenBibleData createChapterPages functions
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
Module handling createChapterPages functions.

CHANGELOG:
    2023-07-18 Added 'OET' navigation link to OET-RV and OET-LV
    2023-07-19 Livened RV and LV headings for OET parallel pages
    2023-08-29 Also display chapter links at bottom of chapter pages
    2023-08-30 Added FRT processing for RV
    2023-12-22 Broke OET chapters correctly into chunks by section for proper alignment
    2023-12-28 Fix bug where duplicate HTML IDs weren't being removed from chapters
    2024-01-18 Fix bug with overwritten GLS 'chapter' page (e.g., in WEB)
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
# from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList
import BibleOrgSys.Formats.ESFMBible as ESFMBible

from settings import State, TEST_MODE, reorderBooksForOETVersions, UNFINISHED_WARNING_PARAGRAPH, JAMES_NOTE_PARAGRAPH
from usfm import convertUSFMMarkerListToHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, removeDuplicateCVids, checkHtml
from OETHandlers import livenOETWordLinks, getOETTidyBBB


LAST_MODIFIED_DATE = '2024-04-10' # by RJH
SHORT_PROGRAM_NAME = "createChapterPages"
PROGRAM_NAME = "OpenBibleData createChapterPages functions"
PROGRAM_VERSION = '0.65'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEWLINE = '\n'



def createOETSideBySideChapterPages( level:int, folder:Path, rvBible, lvBible, state:State ) -> List[str]:
    """
    The OET is a pseudo-version which includes the OET-RV and OET-LV side-by-side.

    (The actual OET-RV and OET-LV are processed by the regular function below.)
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETSideBySideChapterPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETSideBySideChapterPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # allBooksFlag = 'ALL' in state.booksToLoad[rvBible.abbreviation]
    # BBBsToProcess = reorderBooksForOETVersions( rvBible.books.keys() if allBooksFlag else state.booksToLoad[rvBible.abbreviation] )
    # rvBooks = rvBible.books.keys() if 'ALL' in state.booksToLoad[rvBible.abbreviation] else state.booksToLoad[rvBible.abbreviation]
    # lvBooks = lvBible.books.keys() if 'ALL' in state.booksToLoad[lvBible.abbreviation] else state.booksToLoad[lvBible.abbreviation]
    # BBBsToProcess = reorderBooksForOETVersions( [rvKey for rvKey in rvBooks if rvKey in lvBooks] )
    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks['OET'], 'OET', state)

    BBBs, filenames = [], []
    for BBB in state.BBBsToProcess['OET']:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for OET {BBB}…" )
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        ourTidyBBB = getOETTidyBBB( BBB )
        # print( f"{BBB=} {BBBsToProcess}"); print( len(state.BBBsToProcess[thisBible.abbreviation]) )
        # if not allBooksFlag: rvBible.loadBookIfNecessary( BBB )
        # lvBible.loadBookIfNecessary( BBB )

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
            BBBs.append( BBB )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {rvBible.abbreviation} {rvBible.books[BBB]=}" )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for {rvBible.abbreviation} {BBB}…" )
            chapterHtml = f'<h1 id="Top">{rvBible.abbreviation} {BBB}</h1>\n'
            verseEntryList, contextList = rvBible.getContextVerseData( (BBB, '-1') )
            if isinstance( rvBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( rvBible, BBB, verseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rvBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            chapterHtml = f'''{chapterHtml}{convertUSFMMarkerListToHtml( level, rvBible.abbreviation, (BBB,'-1'), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )}'''
            filename = f'{BBB}.htm'
            filenames.append( filename )
            # BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>''' )
            filepath = folder.joinpath( filename )
            top = makeTop( level, rvBible.abbreviation, 'chapter', f'byC/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{rvBible.abbreviation} {BBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {rvBible.abbreviation}, front matter, chapter, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/byC/{filename}#Top">{rvBible.abbreviation}</a>''',
                              f'''<a title="Up to {state.BibleNames[rvBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(rvBible.abbreviation)}/">↑{rvBible.abbreviation}</a>''' )
            chapterHtml = f'''{top}<!--chapter page-->
{chapterHtml}
{makeBottom( level, 'chapter', state )}'''
            checkHtml( rvBible.abbreviation, chapterHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chapterHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(chapterHtml):,} characters written to {filepath}" )
            continue
        elif lvBible.abbreviation in state.booksToLoad \
        and 'ALL' not in state.booksToLoad[lvBible.abbreviation] \
        and BBB not in state.booksToLoad[lvBible.abbreviation]:
            logging.critical( f"C Skipped OET chapters not-included book: OET-LV {BBB}")
            continue # Only create pages for the requested LV books

        BBBs.append( BBB )

        numChapters = rvBible.getNumChapters( BBB )
        cLinks = [f'<a title="Choose “book”" href="./">{ourTidyBBB}</a>']
        if numChapters >= 1:
            if rvBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm#Top">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                cLinks.append( f'<a title="View chapter page" href="{BBB}_C{c}.htm#Top">C{c}</a>' )
        else:
            c = '0' # TODO: for now
            halt
        cLinksPar = f'<p class="chLst">{" ".join( cLinks )}</p>'

        assert rvBible.getNumVerses( BBB, '-1' ) # OET always has intro
        assert not rvBible.getNumVerses( BBB, '0' ) # OET has no chapter zero
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for OET {BBB} {c}…" )
                documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
                if c == -1: # Intro
                    leftLink = ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C1.htm#Top">►</a>' if c<numChapters else ''
                elif c == 0:
                    continue
                elif c == 1:
                    leftLink = f'<a title="Book introduction" href="{BBB}_Intro.htm#Top">◄</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm#Top">►</a>' if c<numChapters else ''
                else: # c > 1
                    assert c > 1
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C{c-1}.htm#Top">◄</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm#Top">►</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}par/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">║</a>'''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}ilr/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''
                cNav = f'<p class="cNav">{leftLink}{documentLink} {"Intro" if c==-1 else c}{rightLink}{parallelLink}{interlinearLink}{detailsLink}</p>'
                chapterHtml = f'''<h1 id="Top">Open English Translation {ourTidyBBB} Introduction</h1>
{cNav}
{f'{JAMES_NOTE_PARAGRAPH}{NEWLINE}' if BBB=='JAM' else ''}<div class="RVLVcontainer">
<h2><a title="View just the Readers’ Version" href="{'../'*level}OET-RV/byC/{BBB}_Intro.htm#Top">Readers’ Version</a></h2>
<h2><a title="View just the Literal Version" href="{'../'*level}OET-LV/byC/{BBB}_Intro.htm#Top">Literal Version</a></h2>''' if c==-1 else f'''<h1 id="Top">Open English Translation {ourTidyBBB} Chapter {c}</h1>
{cNav}
{f'{JAMES_NOTE_PARAGRAPH}{NEWLINE}' if BBB=='JAM' else ''}<div class="RVLVcontainer">
<h2><a title="View just the Readers’ Version" href="{'../'*level}OET-RV/byC/{BBB}_C{c}.htm#Top">Readers’ Version</a></h2>
<h2><a title="View just the Literal Version" href="{'../'*level}OET-LV/byC/{BBB}_C{c}.htm#Top">Literal Version</a> <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>'''
                try: rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    if c == 0: continue # Usually no chapter zero
                    logging.critical( f"No chapter found for {rvBible.abbreviation} {BBB} {c=}" )
                    halt # continue
                assert isinstance( rvBible, ESFMBible.ESFMBible )
                rvVerseEntryList = livenOETWordLinks( rvBible, BBB, rvVerseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
                # print( f"OET-RV {BBB} {c} got {len(rvVerseEntryList)} verse entries, {len(rvContextList)} context entries")
                try: lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    logging.critical( f"createOETSideBySideChapterPages probable versification error for {lvBible.abbreviation} {BBB} {c=}" )
                    lvVerseEntryList, lvContextList = InternalBibleEntryList(), []
                assert isinstance( lvBible, ESFMBible.ESFMBible )
                lvVerseEntryList = livenOETWordLinks( lvBible, BBB, lvVerseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
                # rvHtml = livenIORs( BBB, convertUSFMMarkerListToHtml( 'OET', (BBB,c), 'chapter', rvContextList, rvVerseEntryList ), numChapters )
                rvHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET', (BBB,str(c)), 'chapter', rvContextList, rvVerseEntryList, basicOnly=False, state=state ) )
                lvHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET', (BBB,str(c)), 'chapter', lvContextList, lvVerseEntryList, basicOnly=False, state=state ) )

                if c < 1:
                    rvHtml = f'''<div class="chunkRV">{rvHtml}</div><!--chunkRV-->\n'''
                    lvHtml = f'''<div class="chunkLV">{lvHtml}</div><!--chunkLV-->\n'''
                    combinedHtml = f'{rvHtml}{lvHtml}'
                else: # we have a normal chapter
                    # Now we have to divide the RV and the LV into an equal number of chunks (so they mostly line up)
                    rvSections = rvHtml.split( '<div class="s1">' )
                    if not rvSections[0]: rvSections.pop( 0 ) # It must start with a section heading, so remove the first blank 'section'
                    assert 'bookIntro' not in lvHtml
                    lvChunks, lvRest = [], lvHtml
                    # Now try to match the RV sections
                    for n,rvSectionHtml in enumerate( rvSections ):
                        # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"\n{BBB} {n}: {rvSectionHtml=}" )
                        try:
                            CclassIndex1 = rvSectionHtml.index( 'id="C' )
                            CclassIndex2 = rvSectionHtml.index( '"', CclassIndex1+4 )
                            rvStartCV = rvSectionHtml[CclassIndex1+4:CclassIndex2]
                            CclassIndex8 = rvSectionHtml.rindex( 'id="C' )
                            CclassIndex9 = rvSectionHtml.index( '"', CclassIndex8+4 )
                            rvEndCV = rvSectionHtml[CclassIndex8+4:CclassIndex9]
                            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n  {BBB} {n:,}: {rvStartCV=} {rvEndCV=}")
                        except ValueError as e:
                            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages {BBB} {c=} {n:,}/{len(rvSections):,}: No Cid in {rvSectionHtml=} {e=}" )
                            rvStartCV, rvEndCV = '', 'C1'
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"""Searching for ' id="{rvEndCV}"' in '{lvRest}'""" )
                        try:
                            ixEndCV = lvRest.rindex( f' id="{rvEndCV}"' ) # Versification problem if this fails
                        except ValueError as e: # this can happen if the section end is part-way through the next chapter
                            # i.e., the section crosses chapter boundaries
                            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages {BBB} {c=} {n:,}/{len(rvSections):,}: section seems to cross chapter boundary {rvStartCV=} {rvEndCV=} {e=}")
                            if BBB == 'MAL' and c==4:
                                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETChapterPages aborting {BBB} {c=} {n:,}/{len(rvSections):,}" )
                                lvChunks.append( '<p>Unsolved versification error for Malachi 4!</p>' )
                                break # This versification is giving too many versification problems (with entire c4 missing)
                            if BBB not in ('JOBx','PSAx','EZEx','JOLx'): # TODO: Not sure what's going on with ms1 and mr in PSA and EZE 4 and Joel 2
                                if n != len(rvSections)-1: # It should be the final section
                                    logging.critical( f"createOETChapterPagesA {BBB} {c=} {n:,}/{len(rvSections):,} seems to have a versification problem around {rvStartCV=} {rvEndCV=}" )
                                    while len(lvChunks) < len(rvSections):
                                        lvChunks.append( f"<p>Oops, missing OET-LV section (probably from a versification error).</p>" )
                                    break
                            ixEndCV = len(lvRest) - 1
                        try: ixNextCV = lvRest.index( f' id="C', ixEndCV+5 )
                        except ValueError: ixNextCV = len(lvRest) - 1
                        # print( f"\n{BBB} {n}: {lvRest[ixEndCV:ixNextCV]=} {lvRest[ixNextCV:ixNextCV+10]=}" )
                        # Find our way back to the start of the HTML marker
                        for x in range( 30 ):
                            lvIndex8 = ixNextCV - x
                            if lvRest[lvIndex8] == '<':
                                break
                        else:
                            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvRest[lvIndex8-50:lvIndex8+50]}")
                            if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: not_far_enough
                            break
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
                        if ixEndCV < len(lvRest)-1 \
                        and n < len(rvSections)-1:
                            rsLvChunk = lvChunk.rstrip()
                            assert rsLvChunk[-1]=='>' \
                            or (rsLvChunk[-2]=='>' and rsLvChunk[-1] in '.,?'), f"ASSERT createOETChapterPages {BBB} {c=} {n:,}/{len(rvSections):,}: {lvChunk[-8:]=} {rsLvChunk[-5:]=}"
                        lvChunks.append( lvChunk )
                        lvRest = lvRest[lvEndIx:]
                        if not lvRest:
                            logging.critical( f"createOETChapterPagesB {BBB} {c=} {n:,}/{len(rvSections):,} seems to have a versification problem around {rvStartCV=} {rvEndCV=}" )
                            while len(lvChunks) < len(rvSections):
                                lvChunks.append( f"<p>Oops, no more OET-LV sections (probably from a versification error).</p>" )
                            # assert BBB == 'EZE' # This happens at EZE 20 (and in GEN???)
                            break

                    assert len(lvChunks) == len(rvSections), f"{len(lvChunks)=} {len(rvSections)=}"

                    # Now put all the chunks together
                    combinedHtml = ''
                    for rvSection,lvChunk in zip( rvSections, lvChunks, strict=True ):
                        if rvSection.startswith( '<div class="rightBox">' ):
                            rvSection = f'<div class="s1">{rvSection}' # This got removed above
                        combinedHtml = f'''{combinedHtml}<div class="chunkRV">{rvSection}</div><!--chunkRV-->
<div class="chunkLV">{lvChunk}</div><!--chunkLV-->
'''
                filename = f'{BBB}_Intro.htm' if c==-1 else f'{BBB}_C{c}.htm'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, 'OET', 'chapter', f'byC/{filename}', state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB} introduction" if c==-1 else f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB} chapter {c}" ) \
                        .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter, {ourTidyBBB}' ) \
                        .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{filename}#Top">OET</a>''',
                                  f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
                chapterHtml = f'''{top}<!--chapter page-->
{navBookListParagraph}
{cLinksPar}
{chapterHtml}{removeDuplicateCVids( BBB, combinedHtml )}</div><!--RVLVcontainer-->
{cNav}
{cLinksPar}
{makeBottom( level, 'chapter', state )}'''
                checkHtml( 'OETChapterIndex', chapterHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( chapterHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(chapterHtml):,} characters written to {filepath}" )
        else: # This book has no chapters
            # TODO: Not completely finished yet
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETSideBySideChapterPages {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT',)
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createOETSideBySideChapterPages {rvBible.books[BBB]=}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for OET {BBB} {c}…" )
            # chapterHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
            # # verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
            verseEntryList, contextList = lvBible.getContextVerseData( (BBB, '-1') )
            if isinstance( lvBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( lvBible, BBB, verseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{lvBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            chapterHtml = f'''{chapterHtml}{convertUSFMMarkerListToHtml( level, (BBB,str(c)), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )}'''
            filename = f'{BBB}_C{c}.htm'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            top = makeTop( level, 'OET', 'chapter', f'byC/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{filename}#Top">OET</a>''',
                                f'''<a title="Up to {state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
            chapterHtml = f'''{top}<!--chapter page-->
{cLinksPar}
{chapterHtml}
{makeBottom( level, 'chapter', state )}'''
            checkHtml( chapterHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chapterHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(chapterHtml):,} characters written to {filepath}" )
            halt

        # Now create an index page for this book
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter index page for OET {BBB}…" )
        # filename = f'{BBB}_index.htm' if numChapters>0 else f'{BBB}.htm' # for FRT, etc.
        filename = f'{BBB}.htm'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        top = makeTop( level, 'OET', 'chapter', 'byC/', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET {ourTidyBBB}" ) \
                .replace( '__KEYWORDS__', f'Bible, OET, Open English Translation, chapter, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">OET</a>''', 'OET' )
        chapterHtml = f'''{top}<!--chapters indexPage-->
{navBookListParagraph}
{cLinksPar}
{makeBottom( level, 'chapter', state )}'''
        checkHtml( 'OETChaptersIndex', chapterHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( chapterHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(chapterHtml):,} characters written to {filepath}" )

    # Create overall OET chapter index page
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "  Creating overall OET chapter index page…" )
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, 'OET', 'chapterIndex', 'byC', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Chapter View" ) \
            .replace( '__KEYWORDS__', 'Bible, OET, Open English Translation, chapters' ) \
            .replace( f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC">OET</a>''',
                      f'''<a title="{state.BibleNames['OET']}" href="{'../'*level}OET">↑OET</a>''' )
    indexHtml = f'''{top}
<h1 id="Top">OET chapter pages</h1>
<h2>Index of books</h2>
{navBookListParagraph}
{makeBottom( level, 'chapterIndex', state )}'''
    checkHtml( 'OETBooksIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETSideBySideChapterPages() finished processing {len(BBBs)} OET books: {BBBs}." )
    return filenames
# end of createChapterPages.createOETSideBySideChapterPages


def createChapterPages( level:int, folder:Path, thisBible, state:State ) -> List[str]:
    """
    This creates a page for each chapter for all versions
        other than 'OET' which is considerably more complex (above).
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createChapterPages( {level}, {folder}, {thisBible.abbreviation} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createChapterPages( {level}, {folder}, {thisBible.abbreviation} )…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    thisBibleBooksToLoad = state.booksToLoad[thisBible.abbreviation]
    # BBBsToProcess = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
    #             else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
    #             else thisBibleBooksToLoad
    # if 'OET' in thisBible.abbreviation:
    #     BBBsToProcess = reorderBooksForOETVersions( BBBsToProcess )
    navBookListParagraph = makeBookNavListParagraph( state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state )

    BBBs, filenames = [], []
    for BBB in state.BBBsToProcess[thisBible.abbreviation]:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for {thisBible.abbreviation} {BBB}…" )
        NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
        ourTidyBBB = getOETTidyBBB( BBB )
        # print( f"{BBB=} {state.BBBsToProcess[thisBible.abbreviation]}"); print( len(state.BBBsToProcess[thisBible.abbreviation]) )
        # if not allBooksFlag: thisBible.loadBookIfNecessary( BBB )

        # if thisBible.abbreviation=='OET-LV' \
        # and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'):
        #     logging.critical( f"AA Skipped OET chapters difficult book: OET-LV {BBB}")
        #     continue # Too many problems for now
        if thisBibleBooksToLoad not in (['ALL'],['NT']) \
        and BBB not in state.booksToLoad[thisBible.abbreviation]:
            logging.critical( f"VV Skipped chapters difficult book: {thisBible.abbreviation} {BBB}")
            continue # Only create pages for the requested books

        BBBs.append( BBB )
        try: numChapters = thisBible.getNumChapters( BBB )
        except KeyError:
            logging.critical( f"Can't get number of chapters for {thisBible.abbreviation} {BBB}")
            continue

        cLinks = [f'<a title="Choose “book”" href="./">{ourTidyBBB}</a>']
        if numChapters >= 1:
            if thisBible.discoveryResults[BBB]['haveIntroductoryText']:
                cLinks.append( f'<a title="View document introduction" href="{BBB}_Intro.htm#Top">Intro</a>' )
            for c in range( 1, numChapters+1 ):
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createChapterPages getNumVerses( {thisBible.abbreviation} {BBB} {c} )")
                numVerses = thisBible.getNumVerses( BBB, c )
                if numVerses: # make sure it's a normal chapter, e.g., in ESG book which lacks chapters 1-9
                    cLinks.append( f'<a title="View chapter page" href="{BBB}_C{c}.htm#Top">C{c}</a>' )
        else:
            cLinks.append( f'<a title="View document" href="{BBB}.htm#Top">{ourTidyBBB}</a>' )
        cLinksPar = f'<p class="chLst">{" ".join( cLinks )}</p>'

        haveBookIntro = thisBible.getNumVerses( BBB, '-1' )
        haveChapterZero = thisBible.getNumVerses( BBB, '0' )
        if numChapters >= 1:
            for c in range( -1, numChapters+1 ):
                try: numVerses = thisBible.getNumVerses( BBB, c )
                except KeyError:
                    logging.critical( f"Can't get number of verses for {thisBible.abbreviation} {BBB} {c}")
                    continue
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
                oetLink = f'''<a title="Full OET side-by-side view" href="{'../'*level}OET/byC/{f'{BBB}_Intro' if c==-1 else f'{BBB}_C{c}'}.htm#Top"><small>OET</small></a> ''' if thisBible.abbreviation in ('OET-RV','OET-LV') else ''
                if c == -1:
                    leftLink = ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{0 if haveChapterZero else 1}.htm#Top">►</a>'
                elif c == 0:
                    leftLink = f'<a title="Book introduction" href="{BBB}_Intro.htm#Top">◄</a> ' if haveBookIntro else ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C1.htm#Top">►</a>'
                elif c == 1:
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C0.htm#Top">◄</a> ' if haveChapterZero \
                            else f'<a title="Book introduction" href="{BBB}_Intro.htm#Top">◄</a> ' if haveBookIntro \
                            else ''
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm#Top">►</a>' if c<numChapters else ''
                else: # c > 1
                    assert c > 1
                    leftLink = f'<a title="Previous chapter" href="{BBB}_C{c-1}.htm#Top">◄</a> '
                    rightLink = f' <a title="Next chapter" href="{BBB}_C{c+1}.htm#Top">►</a>' if c<numChapters else ''
                documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}par/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">║</a>'''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}ilr/{BBB}/C{'1' if c==-1 else c}V1.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''
                cNav = f'<p class="cNav">{oetLink}{leftLink}{documentLink} {"Intro" if c==-1 else c}{rightLink}{parallelLink}{interlinearLink}{detailsLink}</p>'
                chapterHtml = f'''<h1 id="Top">{thisBible.abbreviation} {ourTidyBBB} Introduction</h1>
{cNav}{f'{NEWLINE}{JAMES_NOTE_PARAGRAPH}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{NEWLINE}{UNFINISHED_WARNING_PARAGRAPH}' if 'OET' in thisBible.abbreviation else ''}''' \
    if c==-1 else f'''<h1 id="Top">{thisBible.abbreviation} {ourTidyBBB} Chapter {c}</h1>
{cNav}{f'{NEWLINE}{JAMES_NOTE_PARAGRAPH}' if 'OET' in thisBible.abbreviation and BBB=='JAM' else ''}{f'{NEWLINE}{UNFINISHED_WARNING_PARAGRAPH}' if 'OET' in thisBible.abbreviation else ''}'''
                if thisBible.abbreviation == 'OET-LV':
                    chapterHtml = f'''{chapterHtml}<div class="buttons">
    <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button>
</div><!--buttons-->'''
                try: verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c)) )
                except KeyError:
                    if c == 0: continue # Usually no chapter zero
                    logging.critical( f"No chapter found for {thisBible.abbreviation} {BBB} {c=}" )
                    continue
                if isinstance( thisBible, ESFMBible.ESFMBible ): # e.g., OET-RV and OET-LV
                    verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
                textHtml = convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,str(c)), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )
                # textHtml = livenIORs( BBB, textHtml, numChapters )
                if thisBible.abbreviation == 'OET-RV':
                    textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                elif thisBible.abbreviation == 'OET-LV':
                    textHtml = do_OET_LV_HTMLcustomisations( textHtml )
                elif thisBible.abbreviation == 'LSV':
                    textHtml = do_LSV_HTMLcustomisations( textHtml )
                elif thisBible.abbreviation == 'T4T':
                    textHtml = do_T4T_HTMLcustomisations( textHtml )
                chapterHtml = f'{chapterHtml}{textHtml}'
                filename = f'{BBB}_Intro.htm' if c==-1 else f'{BBB}_C{c}.htm'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, thisBible.abbreviation, 'chapter', f'byC/{filename}', state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} introduction"
                                        if c==-1 else f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} chapter {c}" ) \
                        .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter, {ourTidyBBB}' ) \
                        .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC/{filename}#Top">{thisBible.abbreviation}</a>''',
                                  f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
                chapterHtml = f'''{top}<!--chapter page-->
{cLinksPar}
{chapterHtml}
{cNav}
{cLinksPar}
{makeBottom( level, 'chapter', state )}'''
                checkHtml( thisBible.abbreviation, chapterHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( chapterHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(chapterHtml):,} characters written to {filepath}" )

            # Now create an index page for this book
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating chapter index page for {thisBible.abbreviation} {BBB}…" )
            # filename = f'{BBB}_index.htm' if numChapters>0 else f'{BBB}.htm' # for FRT, etc.
            filename = f'{BBB}.htm'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            # BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>' )
            top = makeTop( level, thisBible.abbreviation, 'chapter', 'byC/', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
            chapterHtml = f'''{top}<!--chapters indexPage-->
{cLinksPar}
{makeBottom( level, 'chapter', state )}'''
            checkHtml( thisBible.abbreviation, chapterHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chapterHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(chapterHtml):,} characters written to {filepath}" )

        else: # a non-chapter book
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT','OTH','GLS','XXA','XXB','XXC','XXD')
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createChapterPages {thisBible.abbreviation} {thisBible.books[BBB]=}" )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for {thisBible.abbreviation} {BBB}…" )
            chapterHtml = f'<h1 id="Top">{thisBible.abbreviation} {BBB}</h1>\n'
            verseEntryList, contextList = thisBible.getContextVerseData( (BBB, '-1') )
            if isinstance( thisBible, ESFMBible.ESFMBible ):
                verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}ref/{'GrkWrd' if NT else 'HebWrd'}/{{n}}.htm#Top", state )
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.abbreviation} {BBB} {verseEntryList} {contextList}" )
            chapterHtml = f'''{chapterHtml}{convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,'-1'), 'chapter', contextList, verseEntryList, basicOnly=False, state=state )}'''
            filename = f'{BBB}.htm'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            top = makeTop( level, thisBible.abbreviation, 'chapter', f'byC/{filename}', state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {BBB}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapter, {ourTidyBBB}' ) \
                    .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC/{filename}#Top">{thisBible.abbreviation}</a>''',
                              f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
            chapterHtml = f'''{top}<!--chapter page-->
{chapterHtml}
{makeBottom( level, 'chapter', state )}'''
            checkHtml( thisBible.abbreviation, chapterHtml )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( chapterHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(chapterHtml):,} characters written to {filepath}" )

    # Create overall chapter index page
    filename = 'index.htm'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    top = makeTop( level, thisBible.abbreviation, 'chapterIndex', 'byC', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} Chapter View" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, chapters' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/byC">{thisBible.abbreviation}</a>''',
                      f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">↑{thisBible.abbreviation}</a>''' )
    indexHtml = f'''{top}
<h1 id="Top">{thisBible.abbreviation} chapter pages</h1>
<h2>Index of books</h2>
{navBookListParagraph}
{makeBottom( level, 'chapterIndex', state)}'''
    checkHtml( thisBible.abbreviation, indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
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
