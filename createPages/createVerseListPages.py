#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# createVerseListPages.py
#
# Module handling OpenBibleData createVerseListPages functions
#
# Copyright (C) 2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal. 
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling createVerseListPages functions.
    These pages have less formatting than the full parallel verse pages
    and no spelling checks are done on them.

createVerseListPages( level:int, folder:Path, state:State ) -> bool
createVerseListPagesForBook( level:int, folder:Path, BBB:str, BBBLinks:list[str], state:State ) -> bool
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2026-09-16 Adapted from a copy of createParallelVersePages.py
    2026-09-17 Pre-load the sentenceImportance table in the parent before forking so the
                forked per-book workers inherit it copy-on-write and it's loaded/reported once
                (instead of once per worker).
"""
from pathlib import Path
import os
import logging
import multiprocessing
import re
from collections import defaultdict

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, rreplace, BOOKLIST_66
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.OriginalLanguages.Greek as Greek
from BibleOrgSys.Reference.OldBiblicalEnglish import moderniseEnglishWords
from BibleOrgSys.Reference.EuropeanToEnglish import translateGerman, translateLatin
from bible_organisational_system import getSmallLeadingInt
import bos_books_codes_py

from settings import State, state, CNTR_BOOK_ID_MAP, reorderBooksForOETVersions
from Bibles import getVerseMetaInfoHtml
from jsonResources import getFormattedSILOpenTranslationNotes
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    handleAndExtractFootnotes, convert_adds_to_italics, removeDuplicateFNids, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createParallelVersePages import getPlainText
from createSectionPages import findSectionNumber
from createOETReferencePages import OSHB_ADJECTIVE_DICT, OSHB_PARTICLE_DICT, OSHB_NOUN_DICT, OSHB_PREPOSITION_DICT, OSHB_PRONOUN_DICT, OSHB_SUFFIX_DICT
# from spellCheckEnglish import spellCheckAndMarkHTMLText, collectSpellCheckResults, mergeSpellCheckResults, \
#                             load_OET_LV_names, load_OET_RV_names
from openbibledata_rust import convertVerseEntryListToHtml, getOETTidyBBB, getOETBookName, removeVersePunctuationForComparison, removeGreekPunctuation


LAST_MODIFIED_DATE = '2026-09-18' # by RJH
SHORT_PROGRAM_NAME = "createVerseListPages"
PROGRAM_NAME = "OpenBibleData createVerseListPages functions"
PROGRAM_VERSION = '0.2.2'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EN_SPACE = ' '
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
NON_BREAK_SPACE = ' ' # NBSP
WJ = '\u2060' # word joiner (makes Hebrew displays on console ugly and hard to read)


def createVerseListPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVerseListPages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateVerseListPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Move SR-GNT and UHB and BrLXX and Brenton up after OET-RV and OET-LV
    parallelVersions = state.BibleVersions.copy()
    parallelVersions.remove( 'UTN' )

    # Prepare the book links
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Discovered lst {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Reordered to lst {len(reorderBooksForOETVersions(state.allBBBs))} books across {len(state.preloadedBibles)} versions: {reorderBooksForOETVersions(state.allBBBs)}" )
    BBBLinks, BBBNextLinks = [], []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        # Removes INT, FRT, GLS, XXA, XXB, XXC, XXD, OTH, BAK
        if bos_books_codes_py.is_chapter_verse_book( BBB ):
            ourTidyBBB = getOETTidyBBB( BBB )
            ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
            BBBLinks.append( f'''<a title="{getOETBookName(BBB)}" href="{BBB}/index.htm#Top">{ourTidyBBBwithNotes}</a>''' )
            BBBNextLinks.append( f'''<a title="{getOETBookName(BBB)}" href="{'../'*level}{BBB}/index.htm#Top">{ourTidyBBBwithNotes}</a>''' )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Have lst {len(BBBNextLinks)} book links: {BBBNextLinks}" )

    # Now create the actual verse list pages
    state.versesWithImages = defaultdict( list )
    state.possibleUnmatchedProperNames = set()
    mpBookParameters = [] # (level, folder, BBB, BBBNextLinks, parallelVersions) tuples for the forked workers
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if not state.TEST_MODE_FLAG or BBB in state.TEST_BOOK_LIST: # Don't need parallel pages for non-test books
            if bos_books_codes_py.is_chapter_verse_book( BBB ):
                if BibleOrgSysGlobals.maxProcesses > 1 \
                and not BibleOrgSysGlobals.alreadyMultiprocessing: # Use multiprocessing for these parallel verse pages
                    mpBookParameters.append( (level, folder, BBB, BBBNextLinks, parallelVersions) )
                else: # no multiprocessing available -- do this book sequentially
                    createVerseListPagesForBook( level, folder, BBB, BBBNextLinks, parallelVersions, state )
    if mpBookParameters:
        # Pre-load spell-check dictionaries and name sets in the parent process before forking.
        # Each forked child inherits these via copy-on-write, so the lazy-load guard inside
        # spellCheckAndMarkHTMLText() (which checks len(AMERICAN_WORD_SET) < 10_000) will be
        # False in every child — avoiding redundant file I/O per book.
        getVerseMetaInfoHtml( 'GEN', '1', '1' ) # Pre-load the sentenceImportance table in the parent before forking (so the workers inherit it copy-on-write too, and it's only loaded + reported once)
        # NOTE: We use an explicit 'fork' context because Python 3.14 changed the default start method
        #        to 'forkserver' which would NOT inherit our huge module-level state (12 GiB of Bibles).
        #        Forked children share that memory copy-on-write, so this costs almost nothing extra.
        # NOTE: Outputs (including error and warning messages) from the various books may be interspersed.
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if state.TEST_MODE_FLAG else ''}verse list pages for {len(mpBookParameters):,} books using {BibleOrgSysGlobals.maxProcesses:,} forked processes…" )
        BibleOrgSysGlobals.alreadyMultiprocessing = True
        with multiprocessing.get_context('fork').Pool( processes=BibleOrgSysGlobals.maxProcesses, maxtasksperchild=1 ) as pool: # start worker processes (maxtasksperchild=1 so each worker starts with fresh spell-check accumulators)
            results = pool.map( _createVerseListPagesForBook_MP, mpBookParameters ) # have the pool create the pages
            assert len(results) == len(mpBookParameters)
        BibleOrgSysGlobals.alreadyMultiprocessing = False
        # Merge back into OUR state what the children collected for us (their state changes died when they exited)
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Collecting {'TEST ' if state.TEST_MODE_FLAG else ''}verse list page results after processing {len(mpBookParameters):,} books using {BibleOrgSysGlobals.maxProcesses:,} forked processes…" )
        for resultBool, BBB in results:
            assert resultBool is True

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'simpleVerse', None, state ) \
            .replace( '__TITLE__', f"Verse List View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, list, view, display, index' )
    # WAS state.BBBLinks['OET-RV'] as first parameter to makeBookNavListParagraph() but that didn't display other books
    indexHtml = f'''{top}<h1 id="Top">Simple verse list pages</h1>
<p class="note">Each page only contains a single verse with minimal formatting, but displays it in a large number of different versions to enable analysis of different renderings.</p>
<p class="note">Generally the older versions are nearer the bottom, and so reading from the bottom to the top can show how many English vocabulary and punctuation decisions propagated from one version to another.</p>
<p class="note">If you’re a Bible translator or doing serious study, our fuller <a href="{'../'*level}par/">parallel verse pages</a> have more detailed information including study notes, them notes, and translation notes, etc.</p>
<h2>Index of books</h2>
{makeBookNavListParagraph( BBBLinks, 'VerseListIndex', state )}
<p class="note"><small>Note: We would like to display more English Bible versions on these verse list pages to assist our users, but copyright restrictions from the commercial Bible industry and refusals from publishers greatly limit this. (See the <a href="https://SellingJesus.org/graphics">Selling Jesus</a> website for more information on this problem.)</small></p>
{makeBottom( level, None, 'simpleVerse' )}'''
    assert checkHtml( 'parallelIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createVerseListPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )

    return True
# end of createVerseListPages.createVerseListPages


def _createVerseListPagesForBook_MP( parameters ) -> tuple[bool,str]:
    """
    Multiprocessing version! (forked children inherit our module-level state copy-on-write)

    Parameter is a 5-tuple containing the level, destination folder, BBB book code,
        next-book links, and the reordered list of parallel version abbreviations.
    Returns a 5-tuple containing the True result of createVerseListPagesForBook plus the BBB,
        this book's versesWithImages list, its possibleUnmatchedProperNames set, and its
        collected spell-check results -- because changes that a child process makes
        to the inherited state are lost when it exits.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"_createVerseListPagesForBook_MP( {parameters[:3]}… )" )
    level, folder, BBB, BBBNextLinks, parallelVersions = parameters
    resultBool = createVerseListPagesForBook( level, folder, BBB, BBBNextLinks, parallelVersions, state )
    assert resultBool is True
    return (resultBool, BBB)
# end of createVerseListPages._createVerseListPagesForBook_MP


class MissingBookError( Exception ): pass
class UntranslatedVerseError( Exception ): pass

ENTIRE_FOOTNOTE_REGEX = re.compile( '\\\\f .+?\\\\f\\*' )
FIRST_PAIRED_VERSIONS, SECOND_PAIRED_VERSIONS = ('BSB','WEBBE'), ('MSB','WMBB')
def createVerseListPagesForBook( level:int, folder:Path, BBB:str, BBBLinks:list[str], parallelVersions:list[str], state:State ) -> bool:
    """
    Create a page for every Bible verse
        displaying the verse for every available version.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVerseListPagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1
    isOT = bos_books_codes_py.is_old_testament_nr( BBB )
    isDC = bos_books_codes_py.is_deuterocanon_nr( BBB )
    isNT = bos_books_codes_py.is_new_testament_nr( BBB )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createVerseListPagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = getOETTidyBBB( BBB )
    ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
    ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
    ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
    # adjBBBLinksHtml = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'VerseList', state ) \
    #         .replace( f'''<a title="{getOETBookName(BBB)}" href="{'../'*level}{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )
    BBBLinksHtml = makeBookNavListParagraph( BBBLinks, 'VerseList', state )
    # Handle <a title="Yonah/(Jonah)" href="{'../'*level}JNA/C1V1.htm#chLst"><span title="Yonah (which is closer to the Hebrew hhh/Yōnāh)">YNA</span> (JNA)</a>
    # was BBBLinksHtml.replace( f'''<a title="{getOETBookName(BBB)}" href="{'../'*level}{BBB}/C1V1.htm#chLst">{ourTidyBBB}</a>''', ourTidyBBB )
    adjBBBLinksHtml = re.sub( f'''<a title="[^"]+?" href="{'../'*level}{BBB}/C1V1.htm#chLst">.+?</a>''', ourTidyBBB, BBBLinksHtml ) \
                                    .replace( f'<span class="OT">{ourTidyBBB}</span>', f'<span class="selectedBook">{ourTidyBBB}</span>' ) \
                                    .replace( f'<span class="DC">{ourTidyBBB}</span>', f'<span class="selectedBook">{ourTidyBBB}</span>' ) \
                                    .replace( f'<span class="NT">{ourTidyBBB}</span>', f'<span class="selectedBook">{ourTidyBBB}</span>' ) \
                                    .replace( f'<span class="XX">{ourTidyBBB}</span>', f'<span class="selectedBook">{ourTidyBBB}</span>' )
    assert adjBBBLinksHtml != BBBLinksHtml, f"Should have been changed for {BBB}: {getOETBookName(BBB)=} {ourTidyBBB=}\n\n{adjBBBLinksHtml}\n\nfrom {BBBLinksHtml}\n\nfrom {BBBLinks}"

    numChapters = None
    for versionAbbreviation in parallelVersions: # Our adjusted order
        if versionAbbreviation == 'OET': continue # that's only a "pseudo-version"!
        try: referenceBible = state.preloadedBibles[versionAbbreviation]
        except KeyError: continue # We don't have that version
        if BBB not in referenceBible: continue # don't want to force loading the book
        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        if numChapters: break
    else:
        logging.critical( f"createVerseListPagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does
    introLinks = [ '<a title="Go to parallel intro page" href="Intro.htm#Top">Intro</a>' ]

    vLinksList = []
    detailsLink = f''' <a title="Show details about these works" href="{'../'*(BBBLevel)}AllDetails.htm#Top">©</a>'''
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( -1, numChapters+1 ):
            C = str( c )
            adjC = 'Intro' if c==-1 else f'C{C}'
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating {'TEST ' if state.TEST_MODE_FLAG else ''}parallel pages for {BBB} {C}…" )

            chapterLinksParagraph = f'''<p class="chLst" id="chLst">{ourTidyBBBwithNotes} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm#vsLst">Sg{ps}</a>' for ps in range(1,numChapters+1) if ps!=c] )}</p><!--chLst-->''' \
                if BBB=='PSA' else \
                    f'''<p class="chLst" id="chLst">{ourTidyBbb if ourTidyBbb!='Yac' else 'Yacob/(James)'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm#vsLst">C{chp}</a>' for chp in range(1,numChapters+1) if chp!=c] )}</p><!--chLst-->'''

            introLink = f'''<a title="Go to book intro" href="Intro.htm#__ID__">B</a> {f'<a title="Go to chapter intro" href="C{c}V0.htm#__ID__">I</a> ' if c!=-1 else ''}'''
            leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a> ' if c>1 else ''
            rightCLink = f' <a title="Go to first chapter" href="C1V1.htm#__ID__">►</a>' if c==-1 \
                    else f' <a title="Next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters \
                    else ''
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.error( f"createVerseListPagesForBook: no verses found for {BBB} {C}" )
                continue
            oetRvPsaHasD = False
            for v in range( 0, numVerses+1 ):
                V = str( v )
                parRef = f'{BBB}_{C}:{V}'
                # There's an EM_SPACE and an EN_SPACE (for the join) in the following line
                vLinksPar = f'''<p class="vsLst" id="vsLst">{ourTidyBbb} {C} {' '.join( [f'<a title="Go to parallel verse page" href="C{C}V{vv}.htm#Top">V{vv}</a>'
                                for vv in range(1,numVerses+1,5 if numVerses>100 else 4 if numVerses>80 else 3 if numVerses>60 else 2 if numVerses>40 else 1) if vv!=v] )}</p><!--vsLst-->'''
                greekWords = {}; greekVersionKeysHtmlSet = set()

                # The following all have a __ID__ string than needs to be replaced
                if v > 3:
                    leftCLink = f'<a title="Go to start of chapter" href="C{c}V1.htm#__ID__">◄</a> ' # instead of PREVIOUS chapter
                leftVLink = f'<a title="Previous verse" href="C{C}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Previous chapter (last verse)" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                # NOTE below: C1V0 may not exist in the version but usually there's uW TNs for 1:0
                rightVLink = f' <a title="Next page is first chapter intro" href="C1V0.htm#__ID__">→</a>' if c==-1 \
                        else f' <a title="Next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses \
                        else ''
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*BBBLevel}par/{BBB}/C{C}V{v}.htm#Top">║</a>'''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introductions <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}{interlinearLink}{detailsLink}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{introLink}{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}{interlinearLink}{detailsLink}</p>'

                debugKJBCompareBit = False #parRef == 'PSA_68:6'
                ancientRefsToPrint = () # ('SA1_31:13',) # For debugging
                cleanedModernisedKJB1769TextHtml = depunctuatedCleanedModernisedKJB1769TextHtml = '' # These two are only used for comparisons -- they're not displayed on the page anywhere
                parallelHtml = getVerseMetaInfoHtml( BBB, C, V )
                for versionAbbreviation in parallelVersions: # our adjusted order
                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have both OET-RV and OET-LV instead
                    assert versionAbbreviation not in ('TOSN','TTN','SOTN','UTN'), f"{versionAbbreviation=}"
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    createVerseListPagesForBook {parRef} processing {versionAbbreviation}…" )
                    assert not parallelHtml.endswith( '\n' )

                    if state.TEST_VERSIONS_ONLY and versionAbbreviation not in state.TEST_VERSIONS_ONLY:
                        continue
                    if versionAbbreviation in (state.VERSIONS_WITHOUT_NT) and isNT:
                        continue
                    if versionAbbreviation in (state.VERSIONS_WITHOUT_OT) and isOT:
                        continue # Skip non-NT books for Koine Greek NT
                    if isDC and versionAbbreviation not in state.VERSIONS_WITH_APOCRYPHA:
                        continue

                    thisBible = state.preloadedBibles[versionAbbreviation]
                    textHtml = None
                    footnotesHtml = translatedFootnotesHtml = ''
                    if versionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
                        try:
                            prefix = ''
                            verseText = thisBible[(BBB,C,V)]
                            if verseText.startswith( '(' ) and verseText[1].isdigit(): # then it's probably a verse range, e.g., (21-23), esp. in MSG
                                prefix, verseText = verseText.split( ' ', 1 )
                                assert prefix[-1] == ')'
                                prefix = f'<b><sup>{prefix}</sup></b>'
                            if verseText.startswith( '\\s1 ' ):
                                verseText.replace( '\\s1 ', '\\s1 <b>', 1 ).replace( '\n', '</b>\n', 1 )
                            verseText = ENTIRE_FOOTNOTE_REGEX.sub( '<sup>†</sup>', verseText ) # Just leave a mark where the footnotes were
                            vHtml = f'{prefix}{verseText}' \
                                .replace( '\\p ', ' ' ) \
                                .replace( '\\q1 ', ' ' ) \
                                .replace( '\\q2 ', ' ⇔' ) \
                                .replace( '\\q3 ', ' ⇔' ) \
                                .replace( '\\m ', ' ' ) \
                                .replace( '\\b', ' ' ) \
                                .replace( '\\pc ', ' ' ) \
                                .replace( '\\li1 ', ' •&nbsp;' ) \
                                .replace( '\\li2 ', ' ◦&nbsp;' ) \
                                .replace( '\\li3 ', ' •&nbsp;' ) \
                                .replace( '\\d ', '◊ ' ) \
                                .replace( '\\s1 ', '\n<br>' ) \
                                .replace( '\\s2 ', '\n<br>' ) \
                                .replace( '\\s3 ', '\n<br>' ) \
                                .replace( '\n', ' ' ).replace( '  ', ' ' )
                            vHtml = vHtml.strip() \
                                .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
                                .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
                                .replace( '\\add ', '<span class="add">' ).replace( '\\add*', '</span>' ) \
                                .replace( '\\nd LORD\\nd*', '\\nd L<span class="ndORD">ORD</span>\\nd*' ) \
                                .replace( '\\nd LORDE\\nd*', '\\nd L<span class="ndORD">ORDE</span>\\nd*' ) \
                                    .replace( '\\nd ', '<span class="nd">' ).replace( '\\nd*', '</span>' ) \
                                .replace( '\\wj ', '<span class="wj">' ).replace( '\\wj*', '</span>' ) \
                                .replace( '\\qs ', '<span class="qs">' ).replace( '\\qs*', '</span>' )
                            # for possiblePrefix in (' ','\n',' ','<br>',' ','\n',' '): # only leave these if they're in the middle of the verse
                            vHtml = vHtml.lstrip().removeprefix( '<br>' ).lstrip()
                            assert '\\' not in vHtml, f"{versionAbbreviation} {parRef} {vHtml=}"
                            assert '*' not in vHtml, f"{versionAbbreviation} {parRef} {vHtml=}"
                            assert '<br><br>' not in vHtml, f"{versionAbbreviation} {parRef} {vHtml=}"
                            if versionAbbreviation == 'SLBL': # We provide a direct link to their website
                                vHtml = f'{vHtml} <a title="Go to the SLBL translation" href="https://psalms.scriptura.org/w/Psalm_Overview_{C}#Close-but-Clear_Translation">‡</a>'
                            vHtml =  f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="Go to {state.BibleNames[versionAbbreviation]} copyright info" href="{'../'*BBBLevel}AllDetails.htm#{versionAbbreviation}">{versionAbbreviation}</a></span> {vHtml}</p>'''
                        except KeyError:
                            vHtml = None # We display nothing at all for these versions that only have a few selected verses
                    else: # should be a Bible object
                        try:
                            if BBB not in thisBible:
                                # print( f"{versionAbbreviation} doesn't have {BBB} available{' in TEST_MODE' if state.TEST_MODE_FLAG else ''}")
                                raise MissingBookError # Requested book is not in this Bible
                            # NOTE: For the book intro, we fetch the whole lot in one go (not line by line)
                            if versionAbbreviation == 'OET-LV' and oetRvPsaHasD and c >= 1: # TODO: Fix with proper versification TEMP TEMP TEMP XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
                                # For these Psalms, the OET-LV calls the \\d field, verse 1, so everything is one verse out
                                verseEntryList, contextList = thisBible.getContextVerseDataRange( (BBB, C, V), (BBB, C, '2') ) if v==1 else thisBible.getContextVerseData( (BBB, C, str(v+1)) )
                            else: # the normal, common case
                                verseEntryList, contextList = thisBible.getContextVerseData( (BBB,C) if c==-1 else (BBB, C, V) )
                                # if 'OET' in versionAbbreviation and BBB=='JER' and c==1 and V!='0':
                                #     print( f"{versionAbbreviation} {parRef=} {contextList=} verseEntryList:")
                                #     for eee,entry in enumerate( verseEntryList ):
                                #         print( f"  {eee}: {entry.getMarker()}\n{entry.getOriginalText()=}\n{entry.getFullText()=}\n{entry.getAdjustedText()=}\n{entry.getCleanText()=}")
                                # if versionAbbreviation=='BSB':
                                #     print( f"BSB {parRef}") #  {verseEntryList=}
                                #     for entry in verseEntryList:
                                #         print( f"  {entry.getMarker()} '{entry.getOriginalText()}'")
                                #         # if entry.getExtras():
                                #         #     print( f"    {entry.getExtras()}")
                                # elif versionAbbreviation=='MSB':
                                #     print( f"MSB {parRef}") #  {verseEntryList=}
                                #     for entry in verseEntryList:
                                #         print( f"  {entry.getMarker()} '{entry.getOriginalText()}'")
                                #         # if entry.getExtras():
                                #         #     print( f"    {entry.getExtras()}")
                                # elif versionAbbreviation=='T4T':
                                #     if parRef == 'EZR_2:2': print( f"---- {versionAbbreviation} {parRef} Got {verseEntryList=}" )
                                #     if parRef == 'EZR_2:3': print( f"---- {versionAbbreviation} {parRef} Got {verseEntryList=}" )
                                # if parRef in ancientRefsToPrint: print( f"---- {versionAbbreviation} {parRef} Got {verseEntryList=}" )
                            # # RUST IMPLEMENTATION TEST
                            # if 0 and parRef in ('GEN_1:0','GEN_1:1', 'LEV_25:34', 'HAG_-1:0','HAG_1:1','HAG_2:2', 'MRK_3:21'):
                            #     with open( f'{versionAbbreviation}_{parRef}_parallel.txt', 'rt', encoding='utf-8') as test_file:
                            #         fileChunks = test_file.read().split( '\n\n' )
                            #     for ff, fileChunk in enumerate( fileChunks[:4] ):
                            #         if ff==0:
                            #             expectedStr = f"{versionAbbreviation=} {parRef=}"
                            #             assert expectedStr == fileChunk, f"{expectedStr=} {fileChunk=}"
                            #         elif ff==1:
                            #             expectedStr = f"{len(contextList)=}"
                            #             assert expectedStr == fileChunk, f"{expectedStr=} {fileChunk=}"
                            #         elif ff==2:
                            #             expectedStr = f"{versionAbbreviation} {BBB} {contextList=}"
                            #             assert expectedStr == fileChunk, f"{expectedStr=} {fileChunk=}"
                            #         elif ff==3:
                            #             expectedStr = f"{len(verseEntryList)=}"
                            #             assert expectedStr == fileChunk, f"{expectedStr=} {fileChunk=}"
                            #     for n,(verseEntry) in enumerate( verseEntryList ):
                            #         expectedStr = f"{n} {verseEntry=}"
                            #         assert expectedStr == fileChunks[n+4], f"CV index mismatch for {versionAbbreviation=} {parRef=}\n{expectedStr=}\n{fileChunks[n+4]=}"
                            if 'GNT' in versionAbbreviation:
                                plainGreekText = getPlainText( verseEntryList )
                                if versionAbbreviation == 'SBL-GNT':
                                    plainGreekText = plainGreekText.replace('1','').replace('2','') # 1 Cor 12:10
                                greekWords[versionAbbreviation] = plainGreekText
                                greekWords[f'{versionAbbreviation}_NoPunct'] = removeGreekPunctuation(  greekWords[versionAbbreviation] )
                                greekClass = Greek.Greek( greekWords[f'{versionAbbreviation}_NoPunct'] )
                                try:
                                    greekWords[f'{versionAbbreviation}_NoAccents'] = greekClass.removeAccents()
                                except Exception as exc:
                                    # print( f"\n{parRef} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}" )
                                    raise exc
                                # print( f"\n{parRef} {versionAbbreviation}\n{greekWords[f'{versionAbbreviation}_NoPunct']=}\n{greekWords[f'{versionAbbreviation}_NoAccents']=}" )
                            if 'OET' in versionAbbreviation: # A few special handling features
                                assert isinstance( thisBible, ESFMBible.ESFMBible )
                                if versionAbbreviation == 'OET-RV' and BBB=='PSA' and C not in ('98',):
                                    # Psa 98 does have a d, but it's in with v1 and the other verses don't change
                                    for entry in verseEntryList:
                                        if entry.getMarker() == 'd':
                                            oetRvPsaHasD = True
                                            break
                                    # We want to save
                            textHtml = convertVerseEntryListToHtml( BBBLevel, versionAbbreviation, (BBB,C,V), 'simpleVerse', contextList, verseEntryList, basicOnly=(c!=-1), state=state, livenWordLinks=('OET' in versionAbbreviation) or thisBible.abbreviation in ('BSB','MSB') )
                            # An exception is https://Freely-Given.org/OBD/KJB-1611/byC/ESG_Intro.htm#Top
                            assert textHtml.count('<hr ')<(3 if versionAbbreviation in ('OET-RV','KJB-1611') else 2), f"{versionAbbreviation} {BBB} {C}:{V} ({textHtml.count('<hr ')}) {textHtml=}"
                            textHtml, footnoteFreeTextHtml, footnotesHtml = handleAndExtractFootnotes( versionAbbreviation, textHtml )
                            if footnoteFreeTextHtml.endswith( ' </span>' ): # e.g., in BrLXX
                                footnoteFreeTextHtml = f'{footnoteFreeTextHtml[:-8]}</span>'
                            # assert ' </span>' not in footnoteFreeTextHtml, f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                            if textHtml.endswith( ' </span>' ): # e.g., in BrLXX
                                textHtml = f'{textHtml[:-8]}</span>'
                            # assert ' </span>' not in textHtml, f"{versionAbbreviation} {parRef} {textHtml=}"
                            if 'OET' in versionAbbreviation:
                                textHtml = textHtml.replace( '~~SCHWA~~', 'ə' ) # Restore protected field in title popups
                            if versionAbbreviation not in ('TCNT','TC-GNT'): # They use this character in footnotes
                                assert '¦' not in textHtml, f"{parRef} {versionAbbreviation} {textHtml=}"
                            assert not textHtml.endswith( '\n' )
                            if textHtml == '◙':
                                NEVER_GETS_HERE
                                raise UntranslatedVerseError

                            if versionAbbreviation == 'KJB-1611':
                                textHtml = textHtml.replace( 'class="add"', 'class="add_KJB-1611"' )
                            elif 'OET' not in versionAbbreviation:
                                # Hardwire added words in non-OET versions to italics
                                textHtml = convert_adds_to_italics( textHtml, f'OET simple verse {parRef}' )

                            if versionAbbreviation == 'OET-RV':
                                textHtml = do_OET_RV_HTMLcustomisations( f'VerseListTxt={parRef}', textHtml )

                            elif versionAbbreviation == 'OET-LV':
                                textHtml, footnoteFreeTextHtml, footnotesHtml = do_OET_LV_HTMLcustomisations( f"VerseListTxt={parRef}", textHtml), do_OET_LV_HTMLcustomisations(f"VerseListFF={parRef}", footnoteFreeTextHtml), do_OET_LV_HTMLcustomisations(f"VerseListFN={parRef}", footnotesHtml)
                                assert checkHtml( f"OET-LV parallel AAA for {parRef}", textHtml, segmentOnly=True ); assert checkHtml( f"OET-LV simple BBB for {parRef}", footnoteFreeTextHtml, segmentOnly=True ); assert checkHtml( f"OET-LV parallel CCC for {parRef}", footnotesHtml, segmentOnly=True )
                            elif versionAbbreviation == 'BSB': # assuming BSB comes BEFORE MSB
                                textHtmlBSB = textHtml # Save it for later comparison
                            elif versionAbbreviation == 'MSB' and textHtml: # assuming BSB comes BEFORE MSB
                                if textHtml.replace( 'MSB', '' ) == textHtmlBSB.replace( 'BSB', '' ):
                                    # print( f"Skipping parallel for MSB {parRef} because same as BSB" )
                                    textHtml = "(Same as <small>BSB</small> above)" # Do we also need to adjust footnotesHtml ???
                                # if parRef == 'NUM_25:8': print( f"{parRef}\n{adjustedTextHtmlBSB=}\n           {textHtml=}" ); assert False, "We want to stop here"
                                else: # MSB is different -- try to highlight the first difference (that's not inside a footnote caller)
                                    anchorIx = textHtml.find( '<a title=' )
                                    fnCallerIx = textHtml.find( '<span class="fnCaller">' )
                                    insideSpan = 0
                                    for zz1, (msbChar,bsbChar) in enumerate( zip( textHtml, textHtmlBSB ) ):
                                        if fnCallerIx!=-1 and zz1 >= fnCallerIx:
                                            break # Too hard -- don't bother marking anything more here in this verse
                                        if anchorIx!=-1 and zz1 >= anchorIx: # TODO: Because we now add word links, this will likely effectively make the MSB/BSB comparison useless???
                                            break # Too hard -- don't bother marking anything more here in this verse
                                        if msbChar == '<': # Could be inside </span> or something like a footnote caller
                                            insideSpan += 1
                                            # break # Too hard -- don't bother marking anything here in this verse
                                        elif msbChar == '>': # Could be inside </span> or something like a footnote caller
                                            insideSpan -= 1
                                        if msbChar != bsbChar:
                                            # print( f"{parRef} {zz1=} {msbChar=} {bsbChar=}\n   {textHtml=}\n{textHtmlBSB=}")
                                            if not insideSpan:
                                                for zz2 in range( zz1+1, len(textHtml) ):
                                                    nextChar = textHtml[zz2]
                                                    # print( f"{zz2=} {nextChar=}" )
                                                    if nextChar in ' <':
                                                        break
                                                textHtml = f'''{textHtml[:zz1]}<span title="Word (or format) different in MSB" class="hilite">{textHtml[zz1:zz2]}</span>{textHtml[zz2:]}'''
                                                break
                            elif versionAbbreviation == 'WEBBE': # assuming WEB/WEBBE comes BEFORE WMB/WMBBB
                                textHtmlWEB = textHtml # Save it
                            elif versionAbbreviation == 'WMBB': # assuming WEB/WEBBE comes BEFORE WMB/WMBB
                                if textHtml and textHtml == textHtmlWEB.replace( 'WEBBE', 'WMBB' ):
                                    # print( f"Skipping parallel for WMB {parRef} because same as WEB" )
                                    textHtml = "(Same as above)"
                            elif versionAbbreviation == 'LSV':
                                textHtml = do_LSV_HTMLcustomisations( f'VerseListTxt={parRef}', textHtml )
                            elif versionAbbreviation == 'T4T':
                                textHtml = do_T4T_HTMLcustomisations( f'VerseListTxt={parRef}', textHtml )
                            elif versionAbbreviation == 'LEB':
                                textHtml = textHtml.replace('⌊','<sub>⌊</sub>').replace('⌋','<sub>⌋</sub>') # Around "idioms"
                            elif footnoteFreeTextHtml and versionAbbreviation in state.ENGLISH_VERSIONS_WITH_MODERNISED_TEXT:
                                # See if we need to add a modernised version of this text underneath the main/original text ???
                                # print( f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}")
                                # rawTextHtml = footnoteFreeTextHtml
                                # if rawTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ):
                                #     assert rawTextHtml.endswith( '</span>' )
                                #     rawTextHtml = rawTextHtml[30+len(versionAbbreviation):-7]
                                # print( f"{versionAbbreviation} {parRef} {rawTextHtml=}")
                                # if V=='4': assert False, "We want to stop here"
                                if versionAbbreviation == 'Wycl': # not sure why it has grave accents in it ???
                                    footnoteFreeTextHtml = footnoteFreeTextHtml.replace( '`', '' )
                                modernisedTextHtml = moderniseEnglishWords( footnoteFreeTextHtml
                                                                                .replace('<span class="nd">L<span style="font-size:.75em;">ORDE</span></span>s','<span class="nd">L<span style="font-size:.75em;">ORD</span></span>\'S')
                                                                                .replace('<span class="nd">L<span style="font-size:.75em;">ORD</span></span>s','<span class="nd">L<span style="font-size:.75em;">ORD</span></span>\'s'),
                                                                        allowOptions=True ) # Can return words like 'hateth/hates'
                                if versionAbbreviation in ('KJB-1611','Bshps','Gnva','Cvdl','TNT','Wycl'):
                                    modernisedTextHtml = modernisedTextHtml.replace( 'J', 'Y' ).replace( 'Ie', 'Ye' ).replace( 'Io', 'Yo' ) \
                                                            .replace( 'YDG', 'JDG' ).replace( 'YDT', 'JDT' ).replace( 'Yew', 'Jew' ) \
                                                            .replace( 'Yourney', 'Journey' ).replace( 'Yoy', 'Joy' ).replace( 'Yudge', 'Judge' ).replace( 'Yuniper', 'Juniper' ).replace( 'Yust', 'Just' ).replace( 'KYB', 'KJB' ) # Fix overreaches
                                modernisedTextDiffers = modernisedTextHtml != footnoteFreeTextHtml # we'll usually only show it if it changed

                                # end of removeVersePunctuationForComparison function
                                # (see the Rust port below the module docstring/changelog comment)

                                # if versionAbbreviation == 'BSB':
                                #     # if parRef in ancientRefsToPrint: print( f"AA {versionAbbreviation} {parRef} ({len(modernisedTextHtml)}) {modernisedTextHtml=}" )
                                #     # NOTE: cleanedModernisedKJB1769TextHtml and depunctuatedCleanedModernisedKJB1769TextHtml are only used for comparisons -- they're not displayed on the page anywhere
                                #     cleanedModernisedBSBTextHtml = ( modernisedTextHtml.replace( versionAbbreviation, '' )
                                #                                             .replace( '⇔ ', '' )
                                #                                             .replace( '<br> ', '') # (with en-space) after Psalm titles
                                #                                             #.replace( 'J', 'Y' ).replace( 'Benjam', 'Benyam' ).replace( 'ij', 'iy' ).replace( 'Ij', 'Iy' ).replace( 'Ie', 'Ye' )
                                #                                             .replace( '<span class="wj">', '' ).replace( '</span>', '' )
                                #                                             .replace( '  ', ' ' ).replace( '> ', '>' ).replace( ' \n', '\n')
                                #                                             .strip() ) # Not sure why there's so many superfluous spaces in this text ???
                                #     depunctuatedCleanedModernisedBSBTextHtml = removeVersePunctuationForComparison( cleanedModernisedBSBTextHtml )
                                if versionAbbreviation == 'KJB-1769':
                                    # if parRef in ancientRefsToPrint: print( f"AA {versionAbbreviation} {parRef} ({len(modernisedTextHtml)}) {modernisedTextHtml=}" )
                                    # NOTE: cleanedModernisedKJB1769TextHtml and depunctuatedCleanedModernisedKJB1769TextHtml are only used for comparisons -- they're not displayed on the page anywhere
                                    cleanedModernisedKJB1769TextHtml = ( modernisedTextHtml.replace( versionAbbreviation, '' )
                                                                            .replace( '⇔ ', '' )
                                                                            .replace( '<br> ', '') # (with en-space) after Psalm titles
                                                                            .replace( 'J', 'Y' ).replace( 'Benjam', 'Benyam' ).replace( 'ij', 'iy' ).replace( 'Ij', 'Iy' ).replace( 'Ie', 'Ye' )
                                                                            .replace( '<span class="wj">', '' ).replace( '</span>', '' )
                                                                            .replace( '  ', ' ' ).replace( '> ', '>' ).replace( ' \n', '\n')
                                                                            .strip() ) # Not sure why there's so many superfluous spaces in this text ???
                                    depunctuatedCleanedModernisedKJB1769TextHtml = removeVersePunctuationForComparison( cleanedModernisedKJB1769TextHtml )
                                    if parRef in ancientRefsToPrint: print( f"BB {versionAbbreviation} {parRef} ({len(depunctuatedCleanedModernisedKJB1769TextHtml)}) {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                # if versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"CC {versionAbbreviation} {parRef} ({len(modernisedTextHtml)}) {modernisedTextHtml=}")
                                # NOTE: cleanedModernisedTextHtml and depunctuatedCleanedModernisedTextHtml are only used for comparisons -- they're not displayed on the page anywhere
                                cleanedModernisedTextHtml = ( modernisedTextHtml.replace( versionAbbreviation, '' )
                                                                        .replace( 'ij', 'iy' )
                                                                        .replace( '<span class="wj">', '' )
                                                                        # .replace( '<span style="fontsize75em">', '' ) # Where does this come from???
                                                                        .replace( '</span>', '' )
                                                                        .replace( 'Yuniper', 'Juniper' )
                                                                        .replace( 'Yesus/Yeshua', 'Yesus' ) )
                                depunctuatedCleanedModernisedTextHtml = removeVersePunctuationForComparison( cleanedModernisedTextHtml )
                                if versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"DD {versionAbbreviation} {parRef} same={cleanedModernisedTextHtml==cleanedModernisedKJB1769TextHtml} ({len(depunctuatedCleanedModernisedTextHtml)}) {depunctuatedCleanedModernisedTextHtml=}")
                                if versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and cleanedModernisedTextHtml == cleanedModernisedKJB1769TextHtml:
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above{' apart from footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and cleanedModernisedTextHtml.lower() == cleanedModernisedKJB1769TextHtml.lower():
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from capitalisation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml == depunctuatedCleanedModernisedKJB1769TextHtml:
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml.lower() == depunctuatedCleanedModernisedKJB1769TextHtml.lower():
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from capitalisation and punctuation{' and footnotes' if footnotesHtml else ''}</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                elif versionAbbreviation in ('Wycl','TNT','Cvdl','Gnva','Bshps','KJB-1611') \
                                and depunctuatedCleanedModernisedTextHtml.lower().replace( '<span class="add">', '' ) \
                                == depunctuatedCleanedModernisedKJB1769TextHtml.lower().replace( '<span class="add">', '' ):
                                    modernisedTextHtml = f"<small>{'Modernised spelling is s' if modernisedTextDiffers else 'S'}ame as from KJB-1769 above, apart from marking of added words (and possibly capitalisation and punctuation{' and footnotes' if footnotesHtml else ''})</small>" # (Will be placed in parentheses below)
                                    if debugKJBCompareBit: print( f"{parRef} {versionAbbreviation} {modernisedTextHtml}" )
                                else: # the modernised text itself will be displayed
                                    if debugKJBCompareBit and versionAbbreviation!='KJB-1769': print( f"\n{parRef} {versionAbbreviation} DIFFERENT" )
                                    if versionAbbreviation == 'KJB-1611':
                                        # if debugThisBit:
                                        #     print( f"  {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                        #     print( f"  {depunctuatedCleanedModernisedTextHtml=}" )
                                        modernisedTextHtml = modernisedTextHtml.replace( 'class="add"', 'class="add_KJB-1611"' )
                                    else: # Hardwire added words to italics
                                        modernisedTextHtml = convert_adds_to_italics( modernisedTextHtml, f'Ancient parallel verse {parRef}' )
                                    modernisedTextHtml = modernisedTextHtml.replace( '_verseTextChunk"', '_mod"' )
                                    # if '<div' in modernisedTextHtml: # Shouldn't put a div inside a span!
                                    #     assert C=='-1' and V=='0'
                                    #     textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})''' # Typically a book heading
                                    # else: # no div
                                if versionAbbreviation=='KJB-1611' and not modernisedTextHtml.startswith('<small>') and not parRef.endswith( ':0' ): # Don't include chapter intros
                                    if debugKJBCompareBit:
                                        print( f"    {depunctuatedCleanedModernisedKJB1769TextHtml=}" )
                                        print( f"  KJB-1611 {depunctuatedCleanedModernisedTextHtml=}" )
                                        print( f"                              {modernisedTextHtml=}")
                                    # When the texts differ,
                                    #   try to highlight the first KJB-1611 word that differs from the KJB-1769
                                    #       (so we can see where a 1769 edit was made)
                                    differentWordHighlighted = False
                                    if debugKJBCompareBit:
                                        print( f"aaa 1769 {depunctuatedCleanedModernisedKJB1769TextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower()}" )
                                        print( f"bbb 1611 {depunctuatedCleanedModernisedTextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower()}" )
                                        print( f"Ccc 1611 {modernisedTextHtml.replace( '<span class="KJB-1611_mod">', '' ).replace( '<span class="add_KJB-1611">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).replace( '</span>', '' ).replace( '¶ ', '' )}" )
                                    doneHighlight = False
                                    changeIndex = (modernisedTextHtml.index('>')+1) if modernisedTextHtml[0]=='<' else 0 # So we only replace words after an initial span marker
                                    for wordNum, (word1611, word1769, wordModTxt) in enumerate( zip( depunctuatedCleanedModernisedTextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower().split(),
                                                                           depunctuatedCleanedModernisedKJB1769TextHtml.replace( '<span class="_verseTextChunk">', '' ).replace( '<span class="add">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).lower().split(),
                                                                           modernisedTextHtml.replace( '<span class="KJB-1611_mod">', '' ).replace( '<span class="add_KJB-1611">', '' ).replace( ' class="', '' ).replace( ' style="', '' ).replace( '</span>', '' ).replace( '¶ ', '' ).replace( '( ', '' ).split() ) ):
                                        if debugKJBCompareBit \
                                        and not word1611==word1769==wordModTxt: print( f"  {parRef} LOOP {wordNum=} {doneHighlight=} {word1611=} {word1769=} {wordModTxt=}{f'/{modernisedTextHtml.count(wordModTxt)}' if modernisedTextHtml.count(wordModTxt)!=1 else ''} {changeIndex=} so '{modernisedTextHtml[changeIndex:changeIndex+20]}...'")
                                        if word1769 != word1611:
                                            if debugKJBCompareBit: print( f"  {parRef} {word1611=} IS DIFFERENT FROM {word1769=}" )
                                            wordModTxtAdj = removeVersePunctuationForComparison( wordModTxt )
                                            if debugKJBCompareBit:
                                                if wordModTxtAdj != wordModTxt: print( f"        {wordModTxtAdj=} ({modernisedTextHtml.count(wordModTxtAdj)})" )
                                                if ( 'spannd' not in wordModTxt
                                                and '-' not in wordModTxt
                                                and (not parRef.startswith('PSA_') or not parRef.endswith(':1')) # first verses of some Psalms have a problem with //d fields
                                                and parRef not in ('KI1_10:15',) ):
                                                    assert wordModTxtAdj in modernisedTextHtml, f"{wordModTxt=} should have been in {modernisedTextHtml=}"
                                            if ( wordModTxtAdj.lower() == word1611
                                            # and (modernisedTextHtml.count(wordModTxt)==1
                                            #      or (len(wordModTxt)>0 and modernisedTextHtml.count(f' {wordModTxt}')==modernisedTextHtml.count(wordModTxt) and modernisedTextHtml.count(f'{wordModTxt} ')==modernisedTextHtml.count(wordModTxt) ) ) # Shorter words can occur inside other words too often
                                            and 'class=' not in wordModTxt
                                            and wordModTxtAdj.lower() not in ('adoniyah',) # Why???
                                            ):
                                                if debugKJBCompareBit: print( f"  {parRef} {modernisedTextHtml=}" )
                                                assert wordModTxt != 'span' or parRef in ('EXO_28:16','EXO_39:9'), f"  {parRef} {wordModTxt=} {modernisedTextHtml=}"
                                                # wordMTadj = removeVersePunctuationForComparison( wordMT )
                                                # Save the correct replacement until after the loop, or we can accidentally replace some of those words
                                                # TODO: Replacing all the words (or parts of words) isn't really very satisfactory
                                                if debugKJBCompareBit:
                                                    tempChangeIndex = max( changeIndex, modernisedTextHtml.find( wordModTxt, changeIndex ))
                                                    print( f"    PPP Now changeIndex = {tempChangeIndex} = max({changeIndex},{modernisedTextHtml.find( wordModTxt, changeIndex )}) so '{modernisedTextHtml[tempChangeIndex:tempChangeIndex+20]}...'" )
                                                changeIndex = max( changeIndex, modernisedTextHtml.find( wordModTxt, changeIndex ))
                                                # We get problems with 'a' or 'an' which occur inside 'span' and other words
                                                if modernisedTextHtml[changeIndex:].startswith( f'{wordModTxt} '):
                                                    modernisedTextHtml = f"{modernisedTextHtml[:changeIndex]}{modernisedTextHtml[changeIndex:].replace('<span title="Possible misspelt word" class="spelling">', 'MMMMM' ).replace('<span','SSSSS').replace('</span>','EEEEEEE').replace( wordModTxt, f'<spanSPAN1>{wordModTxt}</span>' if doneHighlight else f'<spanSPAN2>{wordModTxt}</span>', 1 )}"
                                                    changeIndex += len( '<spanSPANx></span>' ) # Number of added characters = 18
                                                    doneHighlight = True
                                                elif modernisedTextHtml.count(wordModTxt)==1 \
                                                or (len(wordModTxt)>0 and modernisedTextHtml.count(f' {wordModTxt}')==modernisedTextHtml.count(wordModTxt) and modernisedTextHtml.count(f'{wordModTxt} ')==modernisedTextHtml.count(wordModTxt) ): # Shorter words can occur inside other words too often
                                                    modernisedTextHtml = ( f"{modernisedTextHtml[:changeIndex]}{modernisedTextHtml[changeIndex:].replace('<span title="Possible misspelt word" class="spelling">', 'MMMMM' ).replace('<span','SSSSS').replace('</span>','EEEEEEE').replace( wordModTxt, f'<spanSPAN1>{wordModTxt}</span>'
                                                             if modernisedTextHtml[changeIndex:].count(wordModTxt)==1 and not doneHighlight # Consecutive words might be just out of step
                                                                                                        else f'<spanSPAN2>{wordModTxt}</span>')}" )
                                                    changeIndex += len( '<spanSPANx></span>' ) # Number of added characters = 18
                                                    doneHighlight = True
                                                assert '<sp<sp' not in modernisedTextHtml, f"hilighted {parRef} modernisedTextHtml after {wordModTxt=} replacement @ '{modernisedTextHtml[changeIndex-19:changeIndex+20]}...' from {modernisedTextHtml=}"
                                                if debugKJBCompareBit: print( f"    QQQ Now changeIndex += 18 = {changeIndex} so '{modernisedTextHtml[changeIndex:changeIndex+20]}...'" )
                                                differentWordHighlighted = True
                                                if debugKJBCompareBit: print( f"  NOW {modernisedTextHtml=}" )
                                                # break
                                        if not doneHighlight:
                                            # NOTE: The following mostly accounts for spans like '<span class="add_KJB-1611">...</span>'
                                            changeIndex += len(wordModTxt) + 1 # for the space that it was split on
                                            if modernisedTextHtml[changeIndex:].startswith( '<span class="add_KJB-1611">' ):
                                                changeIndex += len( '<span class="add_KJB-1611">' )
                                            elif modernisedTextHtml[changeIndex:].startswith( '/span> ' ):
                                                changeIndex += len( '</span>' )
                                    modernisedTextHtml = modernisedTextHtml.replace( 'SPAN1', ' title="Word (or format) changed in KJB-1769" class="hilite"' ) \
                                                                           .replace( 'SPAN2', ' title="Possible word (or format) changed in KJB-1769" class="possibleHilite"' ) \
                                                                           .replace( 'SSSSS', '<span' ).replace( 'EEEEEEE', '</span>' ) \
                                                                           .replace( 'MMMMM', '<span title="Possible misspelt word" class="spelling">' )# Uncover hidden spans again
                                    assert checkHtml( f"hilighted {versionAbbreviation} {parRef} after replacements: {modernisedTextHtml=}", modernisedTextHtml, segmentOnly=True )
                                    if not differentWordHighlighted and 'class="nd"' not in depunctuatedCleanedModernisedTextHtml:
                                        if debugKJBCompareBit: print( "CHECK THE ABOVE" )
                                        # assert False, "We want to stop here"
                                    # if parRef == 'PSA_68:6': assert False, "We want to stop here"
                                if modernisedTextDiffers or 'KJB-1769 above' in modernisedTextHtml:
                                    # if parRef in ancientRefsToPrint: print( f"YY {versionAbbreviation} {parRef} {modernisedTextDiffers=} {modernisedTextHtml=}" )
                                    textHtml = f'''{textHtml}<br>   ({modernisedTextHtml.replace('<br>','<br>   ')})'''
                                # elif versionAbbreviation=='KJB-1611' and parRef in ancientRefsToPrint: print( f"ZZ {versionAbbreviation} {parRef} {modernisedTextDiffers=} ({len(cleanedModernisedTextHtml)}) {cleanedModernisedTextHtml=} ({len(modernisedTextHtml)}) {modernisedTextHtml=}" )
                            elif versionAbbreviation in ('Luth','ClVg'):
                                translateFunction = translateGerman if versionAbbreviation=='Luth' else translateLatin
                                adjustedForeignTextHtml = None
                                if C!='-1' and V!='0' and textHtml:
                                    # assert footnoteFreeTextHtml.startswith( f'<span class="{versionAbbreviation}_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                    # assert footnoteFreeTextHtml.endswith( '</span>' )
                                    # footnoteFreeTextHtml = footnoteFreeTextHtml[30+len(versionAbbreviation):-7]
                                    # assert f'class="{versionAbbreviation}_verseTextChunk"' not in footnoteFreeTextHtml
                                    adjustedForeignTextHtml = translateFunction( footnoteFreeTextHtml.replace( f'<span class="{versionAbbreviation}_verseTextChunk">', f'<span class="{versionAbbreviation}_trans">') )
                                if adjustedForeignTextHtml and adjustedForeignTextHtml != textHtml: # only show it if it changed
                                    # No longer true since we're now using getFullText (even for basicOnly), e.g., we may have id fields included in a bookHeader div
                                    # assert '</p>' not in textHtml
                                    if '<div ' in textHtml: # it might have had footnotes in a <div>, but we want the transliteration BEFORE the footnotes
                                        assert '</div>' in textHtml
                                        textHtml = textHtml.replace( '<hr', f'''<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})<hr''' ) \
                                                    if '<hr ' in textHtml else f'''{textHtml}<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})'''
                                    else: # no <div>s so should be ok to add a span
                                        assert '</div>' not in textHtml
                                        textHtml = f'''{textHtml}<br>   ({adjustedForeignTextHtml.replace('<br>','<br>   ')})'''
                            elif versionAbbreviation == 'SR-GNT':
                                SRtranscription = grammaticalKeysHtmlList = None
                                # if C!='-1' and V!='0' and textHtml:
                                #     # print( f"{parRef} SR-GNT {verseEntryList=} {textHtml=} {footnoteFreeTextHtml=}" )
                                #     # for verseEntry in verseEntryList: print( f"  {verseEntry=}")
                                #     # if '<' in textHtml or '>' in textHtml or '=' in textHtml or '"' in textHtml:
                                #     #     if '<br>' not in textHtml: # Some verses have a sentence break
                                #     #         print( f"\nunexpected fields in SR-GNT textHtml {parRef} {textHtml}" ); assert False, "We want to stop here"
                                #     # assert textHtml.startswith( '<span class="SR-GNT_verseTextChunk">' )
                                #     # assert textHtml.endswith( '</span>' )
                                #     # textHtml = textHtml[36:-7]
                                #     # if 'span' in textHtml: # This can happen if a verse has a paragraph break in the middle of it
                                #     #     textHtml = textHtml.replace( '<span class="SR-GNT_verseTextChunk">', '' ).replace( '</span>', '' )
                                #     # assert 'span' not in textHtml
                                #     textHtml, grammaticalKeysHtmlList = brightenSRGNT( BBB, C, V, textHtml, verseEntryList, state )
                                #     # textHtml = f'<span class="SR-GNT_verseTextChunk">{textHtml}</span>'
                                #     # assert checkHtml( f'footnoteFreeTextHtml {parRef}', footnoteFreeTextHtml, segmentOnly=True )
                                #     # assert footnoteFreeTextHtml.startswith( '<span class="SR-GNT_verseTextChunk">' ), f"{versionAbbreviation} {parRef} {footnoteFreeTextHtml=}"
                                #     # assert footnoteFreeTextHtml.endswith( '</span>' )
                                #     # footnoteFreeTextHtml = footnoteFreeTextHtml[36:-7]
                                #     # assert 'class="SR-GNT_verseTextChunk"' not in footnoteFreeTextHtml
                                #     footnoteFreeTextHtml, _grammaticalKeysHtmlList = brightenSRGNT( BBB, C, V, footnoteFreeTextHtml, verseEntryList, state )
                                # Add an extra link to the CNTR collation page
                                collationHref = f'https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}'
                                try:
                                    # NOTE: We close the previous paragraph, but leave the key paragraph open
                                    keysHtml = f'''</p><!--?-->\n<p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the <em>OET-RV</em> to the <em>LV</em> is done by some temporary software, hence the <em>RV</em> alignments are incomplete (and may occasionally be wrong).</small>'''
                                except (UnboundLocalError, TypeError): # grammaticalKeysHtmlList
                                    keysHtml = ''
                                if textHtml:
                                    textHtml = f'{textHtml} <a title="Go to the GreekCNTR collation page" href="{collationHref}">‡</a>'
                                if SRtranscription:
                                    textHtml = f'''{textHtml}
<br>   ({SRtranscription.replace('<br>','<br>   ')})'''
                                textHtml = f'{textHtml}{keysHtml}'

                            elif versionAbbreviation == 'UHB':
                                if BBB=='PSA' and 'class="d"' in textHtml:
                                    # There's no special formatting in the original Hebrew, so we don't want it here either
                                    # print( f"\nWas UHB PSA {C} d {textHtml=}" )
                                    dIx = textHtml.index( '<span class="d">')
                                    firstVaIx = textHtml.index( '<span class="va">', dIx+15 )
                                    spanIx1 = textHtml.index( '</span>', firstVaIx+15 ) # Should be the closing "va" span
                                    va1 = textHtml[firstVaIx+17:spanIx1]
                                    # print( f"   {va1=}")
                                    assert va1 == '1'
                                    # while textHtml.find( '<span class="va">', lastVaIx+5 ) != -1: # There can be up to three va's
                                    #     lastVaIx = textHtml.index( '<span class="va">', lastVaIx+5 )
                                    # spanIxN = textHtml.index( '</span>', lastVaIx ) # Should be the last closing "va" span
                                    # NOTE: The va end spans ARE NOT FOLLOWED BY NEWLINE, only the d span is
                                    if '</span>\n' not in textHtml and textHtml.endswith( '</span>'): # No final newline with Rust code -- WHY???
                                        spanEndDIx = len(textHtml) - 7
                                    else:
                                        spanEndDIx = textHtml.index( '</span>\n', spanIx1+7 ) # Should be the closing "d" span
                                    textHtml = f'{textHtml[:dIx]}{textHtml[dIx+16:spanEndDIx]}{textHtml[spanEndDIx+7:]}'
                                    # print( f"Now {textHtml=}" )
                                    # assert textHtml.count( 'class="va"' ) == textHtml.count( '</span>' ), f"{parRef} {textHtml=}" # Not true if there's a footnote caller
                                    # if C=='51': assert False, "We want to stop here"
                                # print( f"{versionAbbreviation} {parRef} {textHtml=}")
                                # assert checkHtml( f'brightenedUHB0 {parRef}', textHtml, segmentOnly=True )
                                uhbTranscription = grammaticalKeysHtmlList = None
                                collationHref = f'https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={bos_books_codes_py.bos_to_osis_book_code(BBB)}&c={C}&v={V}'
                                try:
                                    keysHtml = f'''</p><!--?-->\n<p class="key"><b>Key</b>: <button type="button" id="coloursButton" title="Hide grammatical colours above" onclick="hide_show_colours()">C</button> {', '.join(grammaticalKeysHtmlList)}.
<br><small>Note: Automatic aligning of the OET-RV to the LV is done by some temporary software, hence the OET-RV alignments are incomplete (and may occasionally be wrong).</small>'''
                                except (UnboundLocalError, TypeError): # grammaticalKeysHtmlList
                                    keysHtml = ''
                                textHtml = f'{textHtml} <a title="Go to the OSHB verse page" href="{collationHref}">‡</a>'
                                textHtml = f'{textHtml}{keysHtml}'
                                # assert checkHtml( f'brightenedUHB2 {parRef}', textHtml, segmentOnly=True )

                            if textHtml:
                                # Try to keep all these simple verses on one line
                                if versionAbbreviation=='T4T' and parRef == 'EZR_2:55': print( f"A {textHtml=}" )
                                textHtml = textHtml.replace( '\n<br>&nbsp;&nbsp;&nbsp;&nbsp;', ' ' ).replace( '\n<br>&nbsp;&nbsp;', ' ' ) \
                                                .replace( '<br> ⇔ \n', ' ⇔ ' ).replace( '<br> ⇔ \n', ' ⇔  ') \
                                                .replace( '\n<br>  <ul>', '' ).replace( '\n<br> <ul>', '' ) \
                                                    .replace( '<ul>', '' ).replace( '</ul>', '' ) \
                                                    .replace( '<br>\xa0<span class="li', ' <span class="li' ) \
                                                .replace( '<br>\n<br>', '\n<br>' ).replace( '\n<br>\n', '' ).replace( '<br><br>', '<br>' ).replace( '<br>\n', '<br>' ) \
                                                .replace( '\n\n', '\n' ).replace( ' \n', '\n' ).replace( '\n\n', '\n' ) \
                                                .replace( '   ', ' ' ).replace( '  ', ' ' )
                                if versionAbbreviation=='T4T' and parRef == 'EZR_2:55': print( f"B {textHtml=}" )
                                for possibleSuffix in ('\n', ' '):
                                    textHtml = textHtml.removesuffix( possibleSuffix )
                                assert checkHtml( f'VerseList textHtml {versionAbbreviation} {parRef}', textHtml, segmentOnly=True )
                                # if parRef in ancientRefsToPrint: print( f"aaaa {versionAbbreviation} {parRef} Got {textHtml=}" )
                                assert not textHtml.endswith( '\n' ), f"{versionAbbreviation} {parRef} {textHtml[-30:]=}"
                                if V != '0': # Introductions can have more bits (and so too for the modified/updated bits) than individual verses
                                    if versionAbbreviation != 'OEB': # their Ezekiel is really messed up
                                        assert textHtml.count( '_verseTextChunk"' ) <= (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                    assert textHtml.count( '_mod"' ) <= (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                assert textHtml.count( '_trans"' ) < (2+textHtml.count('¶')+textHtml.count('§')+textHtml.count('⇔')+textHtml.count('•')), f"{versionAbbreviation} {parRef} {textHtml=}"
                                # NOTE: textHtml might have footnotes in a div -- in that case we need special handling because can't put a <div> in a <p> below
                                # assert textHtml.count('<span class="ul">_</span>HNcbsa') < 2, f'''Here3 ({textHtml.count('<span class="ul">_</span>HNcbsa')}) {textHtml=}'''
                                # if versionAbbreviation in ('xUGNT','xSBL-GNT','xRP-GNT','xTC-GNT') \
                                # and 'SR-GNT' in greekWords and greekWords[versionAbbreviation]!=greekWords['SR-GNT']:
                                #     # Here we colour the workname to show critical GNT texts that differ in someway from the SR-GNT
                                #     # print( f"\n{versionAbbreviation}\n{versionAbbreviation}='{greekWords[versionAbbreviation]}'\nSR-GNT='{greekWords['SR-GNT']}'" )
                                #     if greekWords[f'{versionAbbreviation}_NoPunct'] == greekWords['SR-GNT_NoPunct']:
                                #         spanClassName = 'wrkNameDiffPunct'
                                #     elif greekWords[f'{versionAbbreviation}_NoAccents'] == greekWords['SR-GNT_NoAccents']:
                                #         spanClassName = 'wrkNameDiffAccents'
                                #     else:
                                #         spanClassName = 'wrkNameDiffText'
                                #         # Now try to mark the first place where the Greek text differs from the SR-GNT
                                #         srWords, versionWords = greekWords['SR-GNT_NoAccents'].split(), greekWords[f'{versionAbbreviation}_NoAccents'].split()
                                #         for jj, versionWord in enumerate( versionWords ):
                                #             try:
                                #                 if versionWord != srWords[jj]:
                                #                     fullVersionWord = greekWords[versionAbbreviation].split()[jj]
                                #                     # print( f"{versionAbbreviation} {parRef} {jj} {fullVersionWord=} {textHtml=}" )
                                #                     if textHtml.count( fullVersionWord ) == 1: # easy case -- no ambiguity
                                #                         textHtml = textHtml.replace( fullVersionWord, f'<span class="diffGrkWord" title="First word different from SR-GNT">{fullVersionWord}</span>', 1 )
                                #                     else: # oh, more work coz the desired word occurs multiple times
                                #                         # print( f"\n{versionAbbreviation} {parRef} {jj} {fullVersionWord=} HAVE MULTIPLE IN {textHtml=}" )
                                #                         textHtml = textHtml.lstrip()
                                #                         for possiblePrefix in ('¶\u202f','§\u202f','\u2002⇔\u202f','⇔\u202f'):
                                #                             textHtml = textHtml.removeprefix( possiblePrefix )
                                #                         startStr = f'<span class="{versionAbbreviation}_verseTextChunk">'
                                #                         assert textHtml.startswith( startStr ) \
                                #                             or (versionAbbreviation=='TC-GNT' and textHtml.startswith( f'\n{startStr}' )), \
                                #                                 f"{versionAbbreviation} {parRef} {startStr=} {textHtml=}" # \b \m causes a \n it seems TODO: Check this out
                                #                         if 'fn' not in textHtml: # Messes things up -- there's lots in the TC-GNT
                                #                             textHtmlWordList = (textHtml.replace( '<span class="wj">', '' ) if versionAbbreviation=='TC-GNT' else textHtml)[len(startStr):].split( ' ' )
                                #                             if versionAbbreviation not in ('TC-GNT','RP-GNT') or parRef not in ('CO2_10:4','PE1_3:10'): # not sure what's with '-</span><br>\u2003\u2003\u2003' there
                                #                                 assert textHtmlWordList[jj] == fullVersionWord, f"{versionAbbreviation} {parRef} {fullVersionWord=} {jj=} {textHtmlWordList[jj]=} from {textHtmlWordList=}"
                                #                             indexOfDesiredWord = len(startStr) + sum(len(s) for s in textHtmlWordList[:jj]) + jj # For the spaces
                                #                             textHtml = f'{textHtml[:indexOfDesiredWord]}{textHtml[indexOfDesiredWord:].replace( fullVersionWord, f'<span class="diffGrkWord" title="First word different from SR-GNT">{fullVersionWord}</span>', 1 )}'
                                #                     break # Only highlight a maximum of one word
                                #             except IndexError: break #
                                #     greekVersionKeysHtmlSet.add( spanClassName )
                                #     versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                #     if '<div ' in textHtml: # it might be a book intro or footnotes -- we can't put a <div> INSIDE a <p>, so we append it instead
                                #         assert '</div>' in textHtml
                                #         vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="{spanClassName}"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span></p>{textHtml}''' # .replace('<hr','</p><hr')
                                #     else: # no <div>s so should be ok to put inside a paragraph
                                #         assert '</div>' not in textHtml
                                #         vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="{spanClassName}"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                # elif versionAbbreviation=='OET-RV':
                                if versionAbbreviation=='OET-RV':
                                    # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case). Also ensure both 'OET-RV' and 'OET' work as # ids on the URL
                                    sectionNumber = findSectionNumber( 'OET-RV', BBB, C, V, state )
                                    if BBB in BOOKLIST_66:
                                        assert sectionNumber is not None, f"Bad OET-RV verse list section {BBB} {C} {V}"
                                    elif sectionNumber is None:
                                        (logging.critical if isOT or isNT else logging.warning)( f"Bad OET-RV verse list section {BBB} {C} {V}" )
                                    if '<div ' in textHtml: # it might be a book intro or footnotes -- we can't put a <div> INSIDE a <p>, so we append it instead
                                        assert '</div>' in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span id="OET"></span><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} section (side-by-side versions)" href="{'../'*BBBLevel}OET/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} section (by itself)" href="{'../'*BBBLevel}OET-RV/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET-RV</a>)</small></span>{'' if textHtml.startswith('<p ') or textHtml.startswith('<div') else ' '}{textHtml.replace('<div','</p><div',1)}'''
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span id="OET"></span><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="View {state.BibleNames['OET']} section (side-by-side versions)" href="{'../'*BBBLevel}OET/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} section (by itself)" href="{'../'*BBBLevel}OET-RV/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET-RV</a>)</small></span> {textHtml}</p>'''
                                elif versionAbbreviation=='Wycl': # Just add a bit about it being translated from the Latin (not the Greek)
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                    assert '<div' not in textHtml, f"{versionAbbreviation} {parRef} {textHtml=}"
                                    vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter (translated from the Latin)'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                else: # for all the others
                                    versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                    if textHtml.startswith( "(Same as " ):
                                        assert versionAbbreviation in SECOND_PAIRED_VERSIONS
                                        versionAbbreviation1 = FIRST_PAIRED_VERSIONS[SECOND_PAIRED_VERSIONS.index(versionAbbreviation)]
                                        versionNameLink1 = f'''{'../'*BBBLevel}{versionAbbreviation1}/details.htm#Top''' if versionAbbreviation1 in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation1}/byC/{BBB}_{adjC}.htm#V{V}'''
                                        # vHtml = f'''<p id="{versionAbbreviation}" class="closeSimpleVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''
                                        parallelHtml = parallelHtml.replace( f'''<span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation1]} {'details' if versionAbbreviation1 in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink1}">{versionAbbreviation1}</a></span>''',
                                                                            f'''<span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation1]} {'details' if versionAbbreviation1 in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink1}">{versionAbbreviation1}</a></span> & <span id="{versionAbbreviation}" class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span>''' )
                                        continue # Nothing else to add for (this identical verse for) this version
                                    elif '<div ' in textHtml: # it might be a book intro XXXor footnotesXXX wrong it seems
                                        assert '</div>' in textHtml
                                        assert c == -1 # Book intro
                                        # print( f"{parRef} {versionAbbreviation} {textHtml[textHtml.index('<div'):]}")
                                        vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span></p>{textHtml}''' # .replace('<hr','</p><hr')
                                    else: # no <div>s so should be ok to put inside a paragraph
                                        assert '</div>' not in textHtml
                                        vHtml = f'''<p id="{versionAbbreviation}" class="{'closeSimpleVerse' if versionAbbreviation in ('OET-LV','UST','MSB','BLB','WMBB','KJB-1611')
                                                                                    else 'simpleVerse'}"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> {textHtml}</p>'''

                            else: # no textHtml -- can include verses that are not in the OET-LV
                                # if parRef in ancientRefsToPrint: print( f"zzzz {versionAbbreviation} {parRef} No textHtml" )
                                if c==-1 or v==0: # For these edge cases, we don't want the version abbreviation appearing
                                    vHtml = ''
                                else:
                                    vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} {'details' if versionAbbreviation in state.versionsWithoutTheirOwnPages else 'chapter'}" href="{versionNameLink}">{versionAbbreviation}</a></span> <a title="Go to missing verses pages" href="{'../'*BBBLevel}OET/missingVerses.htm">◘</a></p>'''

                            if versionAbbreviation=='TC-GNT': # the final one that we display, so show the key to the colours
                                greekVersionKeysHtmlList = []
                                if 'wrkNameDiffPunct' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffPunct">yellow</span>:punctuation differs' )
                                if 'wrkNameDiffAccents' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffAccents">orange</span>:accents differ' )
                                if 'wrkNameDiffText' in greekVersionKeysHtmlSet: greekVersionKeysHtmlList.append( '<span class="wrkNameDiffText">red</span>:words differ' )
                                if greekVersionKeysHtmlList:
                                    vHtml = f'''{vHtml}<p class="key"><b>Key for above GNTs</b>: {', '.join(greekVersionKeysHtmlList)} (from our <a href="#SR-GNT"><b>SR-GNT</b></a> base).</p>'''

                        except MissingBookError:
                            # if parRef in ancientRefsToPrint: print( f"mmmm {versionAbbreviation} {parRef} Got MissingBookError" )
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            assert BBB not in thisBible
                            warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} details" href="{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top">{versionAbbreviation}</a></span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except UntranslatedVerseError:
                            NEVER_GETS_HERE # TODO: Why not???
                            assert textHtml == '◙'
                            assert versionAbbreviation == 'OET-RV'
                            assert BBB in thisBible
                            # Label it as 'OET (OET-RV) and slip in id's for CV (so footnote returns work) and also for C and V (just in case)
                            # if BBB in thisBible:
                            # print( f"No verse inB OET-RV {BBB} in {thisBible}"); assert False, "We want to stop here"
                            warningText = f'No OET-RV {ourTidyBBBwithNotes} {C}:{V} verse available'
                            sectionNumber = findSectionNumber( versionAbbreviation, BBB, C, V, state )
                            assert sectionNumber is not None, f"Bad OET-RV untranslated verse list section {BBB} {C} {V}"
                            vHtml = f'''<p id="OET-RV" class="simpleVerse"><span id="C{C}V{V}" class="wrkName"><a id="C{C}" title="{state.BibleNames['OET']}" href="{'../'*BBBLevel}OET/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET</a> <small>(<a id="V{V}" title="View {state.BibleNames['OET-RV']} section (by itself)" href="{'../'*BBBLevel}OET-RV/bySec/{BBB}_S{sectionNumber}.htm#V{V}">OET-RV</a>)</small></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                            # else:
                            #     warningText = f'No OET-RV {ourTidyBBBwithNotes} book available'
                            #     vHtml = f'''<p id="OET-RV" class="simpleVerse"><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                            logging.warning( warningText )

                        except KeyError:
                            # if parRef in ancientRefsToPrint: print( f"kkkk {versionAbbreviation} {parRef} Got KeyError" )
                            assert not textHtml, f"{versionAbbreviation} {parRef} {verseEntryList=} {textHtml=}"
                            if c==-1 or v==0:
                                vHtml = ''
                            elif BBB in thisBible:
                                # print( f"No {c}:{v} verse in {versionAbbreviation} {BBB} in {thisBible}"); assert False, "We want to stop here"
                                warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} {C}:{V} verse available'
                                versionNameLink = f'''{'../'*BBBLevel}{versionAbbreviation}/details.htm#Top''' if versionAbbreviation in state.versionsWithoutTheirOwnPages else f'''{'../'*BBBLevel}{versionAbbreviation}/byC/{BBB}_{adjC}.htm#V{V}'''
                                vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{versionNameLink}">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )
                            else:
                                warningText = f'No {versionAbbreviation} {ourTidyBBBwithNotes} book available'
                                vHtml = f'''<p id="{versionAbbreviation}" class="simpleVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>'''
                                logging.warning( warningText )

                    if vHtml:
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                        assert checkHtml( f'VerseList vHtml {versionAbbreviation} {parRef}', vHtml, segmentOnly=True )
                        assert not vHtml.endswith( '\n' )
                        if versionAbbreviation in ('OET-RV','OET-LV'):
                            # if BBB=='NUM': print( f"{vHtml=}" )
                            assert '</p>' in vHtml[-45:], f"\n{vHtml[-45:]=}\n{vHtml=}" # e.g., 'lic.</p><!--class-->\n</div><!--bookIntro-->'
                            vHtml = rreplace( vHtml, '</p>', f'<a title="See design specs on OET main site" href="https://OpenEnglishTranslation.Bible/Design/{'Readers' if versionAbbreviation=='OET-RV' else 'Literal'}Version"><img src="{'../'*BBBLevel}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a></p>''', 1 )
                        assert not parallelHtml.endswith( '\n' )
                        parallelHtml = f"{parallelHtml}{NEWLINE if parallelHtml else ''}{vHtml}"
                        try: assert checkHtml( f'VerseList {versionAbbreviation} {parRef}', parallelHtml, segmentOnly=True )
                        except AssertionError as ae: print( ae ) # Don't assert False, "We want to stop here" if the above check failed
                    try: assert checkHtml( f"End of parallel pass for {versionAbbreviation} {parRef}", parallelHtml.replace('<div class="hideables">\n',''), segmentOnly=True ) # hideables isn't ended yet
                    except AssertionError as ae: print( ae ) # Don't assert False, "We want to stop here" if the above check failed

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'simpleVerse', None, state ) \
                        .replace( '__TITLE__', f"{ourTidyBBB} {C}:{V} Verse List View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                        .replace( '__KEYWORDS__', f'Bible, parallel, verse, list, view, display, {ourTidyBBB}' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*BBBLevel}ilr/"''', f'''href="{'../'*BBBLevel}ilr/{BBB}/C{C}V{V}.htm#Top"''')
                parallelHtml = f'''{top}<!--verse list page-->
{adjBBBLinksHtml}
{chapterLinksParagraph}
{vLinksPar}
<h1>Simple verse list for {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>{f'\n<p class="rem">Note: {state.VERSE_LIST_PAGE_SINGLE_VERSE_HTML_TEXT} {state.OETS_UNFINISHED_WARNING_HTML_TEXT}</p>' if c>-1 and v>0 else ''}
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','BottomNavs').replace('__WHERE__','bottom')}
{parallelHtml}
{navLinks.replace('__ID__','BottomNavs').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, None, 'simpleVerse' )}'''
                assert checkHtml( f'VerseList {parRef}', parallelHtml )
                assert not filepath.is_file() # Check that we're not overwriting anything
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( parallelHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(parallelHtml):,} characters written to {filepath}" )
                vLinksList.append( f'<a title="Go to parallel verse page" href="{filename}#Top">{C}:{V}</a>' )
                if c == -1: # then we're doing the book intro
                    break # no need to loop -- we handle the entire intro in one go
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createVerseListPagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createVerseListPagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename1 = 'index.htm'
    filepath1 = BBBFolder.joinpath( filename1 )
    top = makeTop( BBBLevel, None, 'simpleVerse', None, state ) \
            .replace( '__TITLE__', f"{ourTidyBBB} Verse List View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, list, view, display, index' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel songs index</h1>' if BBB=='PSA' else ''}{chapterLinksParagraph}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel verses index</h1>' if BBB!='PSA' else ''}{f'{NEWLINE}<p class="vsLst">{" ".join( vLinksList )}</p><!--vsLst-->' if BBB!='PSA' else ''}
{makeBottom( BBBLevel, None, 'simpleVerse' )}'''
    assert checkHtml( 'parallelIndex', indexHtml )
    with open( filepath1, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath1}" )

    # Write a second copy of the index page up a level
    # newBBBVLinks = []
    # for vLink in vLinksList:
    #     newBBBVLinks.append( vLink.replace('href="', f'href="{BBB}/') )
    # print( f"\n{vLinksList=}" )
    # print( f"\n{adjBBBLinksHtml=}" )
    # print( f"\n{chapterLinksParagraph=}" )
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, None, 'simpleVerse', None, state ) \
            .replace( '__TITLE__', f"{ourTidyBBB} Verse List View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, parallel, verse, list, view, display, index' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml.replace('href="../', f'href="')}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel songs index</h1>' if BBB=='PSA' else ''}{chapterLinksParagraph.replace('href="', f'href="{BBB}/')}{f'{NEWLINE}<h1 id="Top">{ourTidyBBB} parallel verses index</h1>' if BBB!='PSA' else ''}{f'''{NEWLINE}<p class="vsLst">{" ".join( vLinksList ).replace('href="', f'href="{BBB}/')}</p><!--vsLst-->''' if BBB!='PSA' else ''}
{makeBottom( level, None, 'simpleVerse' )}'''
    assert checkHtml( 'parallelIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createVerseListPagesForBook() finished processing {len(vLinksList):,} {BBB} verses." )
    return True
# end of createVerseListPages.createVerseListPagesForBook



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createVerseListPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createVerseListPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createVerseListPages.py
