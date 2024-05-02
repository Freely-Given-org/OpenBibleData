#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSitePages.py
#
# Module handling OpenBibleData createSitePages functions
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
Module handling createSitePages functions.

Creates the OpenBibleData site with
    Whole document (‘book’) pages
    Section pages
    Whole chapter pages
    Parallel verse pages
and more pages to come hopefully.

CHANGELOG:
    2023-05-04 Added 'About OBD' page
    2023-05-31 Added BLB
    2023-06-01 Added TSN
    2023-07-19 Converted versions dictkeys to list for nicer display
    2023-07-30 Added selected verses from some other versions
    2023-08-16 Added PHM and put MRK between JHN and MAT
    2023-08-30 Added PHP for RV
    2023-08-31 Added COL for RV
    2023-09-06 Added list of selected versions on details pages (in TEST mode only)
    2023-09-25 Added search page
    2023-10-01 Added ROM for RV
    2023-10-10 Added German Luther 1545 Bible
    2023-10-20 Added CO2 for RV
    2023-10-24 Creates a BCV index into the OET-LV word table
    2023-12-29 Started adding OET OT
    2024-01-02 Make sure all HTML folders contain an index file
    2024-01-11 Load all OET-LV NT books
    2024-03-21 Handle two word tables for OET
    2024-04-04 Create 'OET Key' page
    2024-04-21 Create 'OBD News' page
"""
from gettext import gettext as _
# from typing import Dict, List, Tuple
from pathlib import Path
import os
import shutil
import glob
from datetime import date #, datetime
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27

sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import load_transliteration_table

from settings import State, state, reorderBooksForOETVersions, TEST_MODE, SITE_NAME, SITE_ABBREVIATION, \
    TEMP_BUILD_FOLDER, ALL_PRODUCTION_BOOKS, UPDATE_ACTUAL_SITE_WHEN_BUILT, DESTINATION_FOLDER, BY_DOCUMENT_PARAGRAPH
from Bibles import preloadVersions
from OETHandlers import getOETTidyBBB, getOETBookName
from createBookPages import createOETBookPages, createBookPages
from createChapterPages import createOETSideBySideChapterPages, createChapterPages
from createSectionPages import createOETSectionPages, createSectionPages
from createParallelPassagePages import createParallelPassagePages
from createParallelVersePages import createParallelVersePages
from createOETInterlinearPages import createOETInterlinearPages
from createOETReferencePages import createOETReferencePages
from Dict import createTyndaleDictPages, createUBSDictionaryPages
from html import makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2024-05-02' # by RJH
SHORT_PROGRAM_NAME = "createSitePages"
PROGRAM_NAME = "OpenBibleData (OBD) Create Site Pages"
PROGRAM_VERSION = '0.96'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False # Adds debugging output

NEWLINE = '\n'


def _createSitePages() -> bool:
    """
    Build all the pages in a temporary location
    """
    fnPrint( DEBUGGING_THIS_MODULE, "_createSitePages()")
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"_createSitePages() running in {'TEST' if TEST_MODE else 'production'} mode with {'all production books' if ALL_PRODUCTION_BOOKS else 'reduced books being loaded'} for {len(state.BibleLocations):,} Bible versions…" )

    try: os.makedirs( TEMP_BUILD_FOLDER )
    except FileExistsError:
        assert os.path.isdir( TEMP_BUILD_FOLDER )
        _cleanHTMLFolders( TEMP_BUILD_FOLDER, state )

    # Preload our various Bibles
    for versionAbbreviation in state.BibleVersions:
        state.booksToLoad[versionAbbreviation] = BOOKLIST_OT39 if state.booksToLoad[versionAbbreviation]==['OT'] \
                                            else BOOKLIST_NT27 if state.booksToLoad[versionAbbreviation]==['NT'] \
                                            else state.booksToLoad[versionAbbreviation] # NOTE: We don't replace ['ALL'] because that is 'all available', including 'FRT','XXA', etc.
    numLoadedVersions = preloadVersions( state )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nPreloaded {len(state.preloadedBibles)} Bible versions: {list(state.preloadedBibles.keys())}" )
    # preloadUwTranslationNotes( state )
    # fillSelectedVerses( state )

    # Load our OET worddata tables
    state.OETRefData = {} # This is where we will store all our temporary ref data
    state.OETRefData['word_tables'] = {}
    lvBible = state.preloadedBibles['OET-LV']
    assert len(lvBible.ESFMWordTables) == 2, f"{len(lvBible.ESFMWordTables)=}"
    # print( f"{lvBible.ESFMWordTables=}" )
    for wordTableFilename in lvBible.ESFMWordTables:
        assert wordTableFilename.endswith( '.tsv' )
        if lvBible.ESFMWordTables[wordTableFilename] is None:
            lvBible.loadESFMWordFile( wordTableFilename )
        # print( f"{type(lvBible.ESFMWordTables[wordTableFilename])}" )
        state.OETRefData['word_tables'][wordTableFilename] = lvBible.ESFMWordTables[wordTableFilename]
        columnHeaders = state.OETRefData['word_tables'][wordTableFilename][0]
        # print( f"{columnHeaders=}")
        if '_OT_' in wordTableFilename:
            assert columnHeaders == 'Ref\tRowType\tMorphemeRowList\tLemmaRowList\tStrongs\tMorphology\tWord\tNoCantillations\tMorphemeGlosses\tContextualMorphemeGlosses\tWordGloss\tContextualWordGloss\tGlossCapitalisation\tGlossPunctuation\tGlossOrder\tGlossInsert\tRole\tNesting\tTags' # If not, probably need to fix some stuff
        elif '_NT_' in wordTableFilename:
            assert columnHeaders == 'Ref\tGreekWord\tSRLemma\tGreekLemma\tVLTGlossWords\tOETGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags' # If not, probably need to fix some stuff

    # Make a BCV index to the OET word tables
    state.OETRefData['word_table_indexes'] = {}
    for wordTableFilename in lvBible.ESFMWordTables:
        state.OETRefData['word_table_indexes'][wordTableFilename] = {}
        lastBCVref = None
        startIx = 1
        for n, columns_string in enumerate( state.OETRefData['word_tables'][wordTableFilename][1:], start=1 ):
            wordRef = columns_string.split( '\t', 1 )[0] # Something like 'MAT_1:1w1'
            BCVref = wordRef.split( 'w', 1 )[0] # Something like 'MAT_1:1'
            if BCVref != lastBCVref:
                if lastBCVref is not None:
                    state.OETRefData['word_table_indexes'][wordTableFilename][lastBCVref] = (startIx,n-1)
                startIx = n
                lastBCVref = BCVref
        state.OETRefData['word_table_indexes'][wordTableFilename][lastBCVref] = (startIx,n) # Save the final one

    load_transliteration_table( 'Greek' )
    load_transliteration_table( 'Hebrew' )

    # Determine our inclusive list of books for all versions
    allBBBs = set()
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        for versionAbbreviation in state.BibleVersions:
            if versionAbbreviation == 'OET': continue # OET is a pseudo version (OET-RV plus OET-LV)
            # if versionAbbreviation not in ('TTN',) \
            if versionAbbreviation in state.versionsWithoutTheirOwnPages:
                continue # We don't worry about these few selected verses here
            for entry in state.booksToLoad[versionAbbreviation]:
                if entry == BBB or entry == 'ALL':
                    if BBB in state.preloadedBibles[versionAbbreviation]:
                        allBBBs.add( BBB )
    # Now put them in the proper print order
    state.allBBBs = BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( allBBBs )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDiscovered {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )

    # Determine our list of books to process for each version
    state.BBBsToProcess, state.BBBLinks = {}, {}
    for versionAbbreviation in state.BibleVersions:
        # if versionAbbreviation == 'OET': continue # This isn't a real version
        if versionAbbreviation == 'OET': # This isn't a real version
            lvBible = state.preloadedBibles['OET-LV']
            rvBible = state.preloadedBibles['OET-RV']
            rvBooks = rvBible.books.keys() if 'ALL' in state.booksToLoad[rvBible.abbreviation] else state.booksToLoad[rvBible.abbreviation]
            lvBooks = lvBible.books.keys() if 'ALL' in state.booksToLoad[lvBible.abbreviation] else state.booksToLoad[lvBible.abbreviation]
            state.BBBsToProcess['OET'] = reorderBooksForOETVersions( [rvKey for rvKey in rvBooks if rvKey in lvBooks] )
            state.BBBLinks['OET'] = []
            for BBB in state.BBBsToProcess['OET']:
                filename = f'{BBB}.htm'
                ourTidyBBB = getOETTidyBBB( BBB )
                state.BBBLinks['OET'].append( f'''<a title="{getOETBookName(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>''' )
        else: # not OET
            thisBible = state.preloadedBibles[versionAbbreviation]
            thisBibleBooksToLoad = state.booksToLoad[versionAbbreviation]
            # print( f'{versionAbbreviation}: {thisBible=} {thisBibleBooksToLoad=}' )
            # if versionAbbreviation in state.selectedVersesOnlyVersions:
            #     state.BBBsToProcess[versionAbbreviation] = []
            #     assert isinstance( thisBible, dict )
            #     for BBB,_C,_V in thisBible: # a dict with keys like ('REV', '1', '3')
            #         if BBB not in state.BBBsToProcess[versionAbbreviation]:
            #             state.BBBsToProcess[versionAbbreviation].append( BBB )
            # else: # not selectedVersesOnlyVersions
            if versionAbbreviation not in state.selectedVersesOnlyVersions:
                state.BBBsToProcess[versionAbbreviation] = thisBible.books.keys() 
                if 'OET' in versionAbbreviation:
                    state.BBBsToProcess[versionAbbreviation] = reorderBooksForOETVersions( state.BBBsToProcess[versionAbbreviation] )
                state.BBBLinks[versionAbbreviation] = []
                ourBBBsToProcess = BOOKLIST_NT27 if state.BBBsToProcess[versionAbbreviation]==['NT'] \
                            else BOOKLIST_OT39 if state.BBBsToProcess[versionAbbreviation]==['OT'] \
                            else state.BBBsToProcess[versionAbbreviation]
                for BBB in ourBBBsToProcess:
                    # We include FRT here if there is one, but it will be excluded later where irrelevant
                    if BBB=='FRT' \
                    or 'ALL' in thisBibleBooksToLoad \
                    or BBB in thisBibleBooksToLoad:
                        filename = f'{BBB}.htm'
                        ourTidyBBB = getOETTidyBBB( BBB )
                        state.BBBLinks[versionAbbreviation].append( f'''<a title="{getOETBookName(BBB)}" href="{filename}#Top">{ourTidyBBB}</a>''' )

    # Ok, let's go create some static pages
    # discoverStartTime = datetime.now()
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDoing discovery on OET…" )
        state.preloadedBibles['OET-RV'].discover() # Now that all required books are loaded
        state.preloadedBibles['OET-LV'].discover() #     ..ditto..
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}version pages for OET…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'OET/' )
        _createOETVersionPages( 1, versionFolder, state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV'], state )
        _createOETMissingVersePage( 1, versionFolder )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        # if versionAbbreviation not in ('TTN',) \
        if versionAbbreviation in state.versionsWithoutTheirOwnPages:
            if versionAbbreviation == 'TTN': continue # These ones don't even have a folder
            # We just write a very bland index page here
            versionName = state.BibleNames[versionAbbreviation]
            indexHtml = f'<h1 id="Top">{versionName}</h1>'
            top = makeTop( 1, None, 'site', None, state ) \
                            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                            .replace( '__KEYWORDS__', f'Bible, {versionAbbreviation}, {versionName}' )
            folder = TEMP_BUILD_FOLDER.joinpath( f'{versionAbbreviation}/' )
            os.makedirs( folder )
            filepath = folder.joinpath( 'index.htm' )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
                indexHtmlFile.write( f'''{top}{indexHtml}\n<p class="note"><a href="details.htm">See copyright details.</p>\n{makeBottom( 1, 'site', state )}''' )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
        else:
            thisBible.discover() # Now that all required books are loaded
            if 'haveSectionHeadings' not in thisBible.discoveryResults['ALL']: # probably we have no books that actually loaded
                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Adding discoveryResults 'haveSectionHeadings' for {thisBible.abbreviation}: no books loaded?" )
                thisBible.discoveryResults['ALL']['haveSectionHeadings'] = False # We need this in several places
            if TEST_MODE and versionAbbreviation in ('OEB','WEB','WMB','NET','LSV','FBV','TCNT','T4T','LEB',
                                                     'BBE','MOF','JPS','ASV','DRA','YLT','DBY','RV','WBS',
                                                     'KJB','BB','GNV','CB','TNT','WYC'):
                # In test mode, we don't usually need to make all those pages, even just for the test books
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}version pages for {thisBible.abbreviation}…" )
                versionFolder = TEMP_BUILD_FOLDER.joinpath( f'{thisBible.abbreviation}/' )
                _createVersionPages( 1, versionFolder, thisBible, state )
    # print( f"Discovery time {datetime.now()-discoverStartTime}" ); halt

    # We do this later than the _createVersionPages above
    #   because we need all versions to have all books loaded and 'discovered', i.e., analysed
    #   so we know in advance which versions have section headings
    if 'OET' in state.BibleVersions: # this is a special case
        rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']
        if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings']:
            versionFolder = TEMP_BUILD_FOLDER.joinpath( f'OET/' )
            createOETSectionPages( 2, versionFolder.joinpath('bySec/'), rvBible, lvBible, state )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        if versionAbbreviation not in ('TTN',) \
        and versionAbbreviation in state.versionsWithoutTheirOwnPages: continue # We don't worry about these few selected verses here
        if versionAbbreviation not in ('TOSN','TTN','UTN'): # We don't make separate notes pages
            if thisBible.discoveryResults['ALL']['haveSectionHeadings']:
                versionFolder = TEMP_BUILD_FOLDER.joinpath( f'{thisBible.abbreviation}/' )
                createSectionPages( 2, versionFolder.joinpath('bySec/'), thisBible, state )

    # TODO: We could use multiprocessing to do all these at once
    #   (except that state is quite huge with all preloaded versions and hence expensive to pickle)
    createParallelVersePages( 1, TEMP_BUILD_FOLDER.joinpath('par/'), state )
    createOETInterlinearPages( 1, TEMP_BUILD_FOLDER.joinpath('ilr/'), state )
    createParallelPassagePages( 1, TEMP_BUILD_FOLDER.joinpath('rel/'), state )

    createUBSDictionaryPages( 1, TEMP_BUILD_FOLDER.joinpath('UBS/'), state )
    createTyndaleDictPages( 1, TEMP_BUILD_FOLDER.joinpath('dct/'), state )
    createOETReferencePages( 1, TEMP_BUILD_FOLDER.joinpath('ref/'), state )

    _createDetailsPages( 0, TEMP_BUILD_FOLDER, state )
    _createSearchPage( 0, TEMP_BUILD_FOLDER, state )
    _createAboutPage( 0, TEMP_BUILD_FOLDER, state )
    _createNewsPage( 0, TEMP_BUILD_FOLDER, state )
    _createOETKeyPage( 0, TEMP_BUILD_FOLDER, state )

    _createMainIndexPage( 0, TEMP_BUILD_FOLDER, state )

    state.preloadedBibles = None # Reduce memory use now

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n{TEMP_BUILD_FOLDER} is {_getFolderSize(TEMP_BUILD_FOLDER)//1_000_000:,} MB" )

    if UPDATE_ACTUAL_SITE_WHEN_BUILT:
        # Clean away any existing folders so we can copy in the newly built stuff
        try: os.makedirs( f'{DESTINATION_FOLDER}/' )
        except FileExistsError: # they were already there
            assert os.path.isdir( DESTINATION_FOLDER )
            _cleanHTMLFolders( DESTINATION_FOLDER, state )

        try: # Now move the site from our temporary build location to overwrite the destination location
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Moving files and folders from {TEMP_BUILD_FOLDER}/ to {DESTINATION_FOLDER}/…" )
            count = 0
            for fileOrFolderPath in glob.glob( f'{TEMP_BUILD_FOLDER}/*' ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Moving {fileOrFolderPath} to {DESTINATION_FOLDER}/…" )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                shutil.move( fileOrFolderPath, f'{DESTINATION_FOLDER}/', copy_function=shutil.copy2)
                count += 1
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Moved {count:,} folders and files into {DESTINATION_FOLDER}/." )

            # We also need to copy the TOBD maps across
            TOBDmapSourceFolder = os.path.join( state.BibleLocations['TOSN'], '../OBD/Maps/artfiles/' )
            TOBDmapDestinationFolder = DESTINATION_FOLDER.joinpath( 'dct/' )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copying TOBD maps from {TOBDmapSourceFolder} to {TOBDmapDestinationFolder}/…" )
            count = 0
            for imgFilepath in glob.glob( f'{TOBDmapSourceFolder}/*.png' ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Copying {imgFilepath} to {TOBDmapDestinationFolder}/…" )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                try:
                    shutil.copy2( imgFilepath, f'{TOBDmapDestinationFolder}/' )
                    count += 1
                except FileNotFoundError as e:
                    logging.critical( f"TOBD image file problem: {e}" )
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Copied {count:,} maps into {TOBDmapDestinationFolder}/." )

            # We need to copy the .css files and Bible.js across
            count = 0
            for filepath in glob.glob( '*.css' ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Copying {filepath}…" )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                shutil.copy2( filepath, DESTINATION_FOLDER )
                count += 1
            shutil.copy2( 'Bible.js', DESTINATION_FOLDER )
            count += 1
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copied {count:,} stylesheets and scripts into {DESTINATION_FOLDER}/." )
        except Exception as e:
            logging.critical( f"Oops, something went wrong copying files into {DESTINATION_FOLDER}/: {e}" )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f'''\nNOW RUN "npx pagefind --glob "{{OET,par}}/**/*.{{htm}}" --site ../htmlPages{'/Test' if TEST_MODE else ''}/" to create search index!''' )
    else:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"NOT UPDATING the actual {'TEST ' if TEST_MODE else ''}site (as requested)." )
# end of createSitePages._createSitePages


def _cleanHTMLFolders( folder:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_cleanHTMLFolders( {folder} )")
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Cleaning away any existing folders at {folder}/…")

    try: os.unlink( folder.joinpath( 'index.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'AllDetails.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'About.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'News.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'OETKey.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'Search.htm' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'rel/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'par/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'ilr/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'ref/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'dct/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'UBS/' ) )
    except FileNotFoundError: pass
    for versionAbbreviation in state.allBibleVersions + ['UTN','TOSN','TOBD']:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Removing tree at {folder.joinpath( f'{versionAbbreviation}/' )}/…")
        try: shutil.rmtree( folder.joinpath( f'{versionAbbreviation}/' ) )
        except FileNotFoundError: pass
    return True
# end of createSitePages._cleanHTMLFolders


def _createOETVersionPages( level:int, folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createOETVersionPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    createOETBookPages( level+1, folder.joinpath('byDoc/'), rvBible, lvBible, state )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    createOETSideBySideChapterPages( level+1, folder.joinpath('byC/'), rvBible, lvBible, state )

    versionName = state.BibleNames['OET']
    indexHtml = f'''<h1 id="Top">{versionName}</h1>
{BY_DOCUMENT_PARAGRAPH}
<p class="viewLst">OET <a href="byDoc">By Document</a> <a href="bySec">By Section</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
''' if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings'] else \
f'''<h1 id="Top">{versionName}</h1>
{BY_DOCUMENT_PARAGRAPH}
<p class="viewLst">OET <a href="byDoc">By Document</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                    .replace( '__KEYWORDS__', f'Bible, OET, {versionName}' ) \
                    .replace( f'''<a title="{versionName}" href="{'../'*level}OET">OET</a>''', 'OET' )
    filepath = folder.joinpath( 'index.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{indexHtml}
{makeBottom( level, 'site', state )}''' )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages._createOETVersionPages

def _createVersionPages( level:int, folder:Path, thisBible, state:State ) -> bool:
    """
    Create a page for the given Bible version
        that then allows the user to choose by document/section/chapter or display version details
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createVersionPages( {level}, {folder}, {thisBible.abbreviation} )")
    createBookPages( level+1, folder.joinpath('byDoc/'), thisBible, state )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    createChapterPages( level+1, folder.joinpath('byC/'), thisBible, state )

    versionName = state.BibleNames[thisBible.abbreviation]
    indexHtml = f'''<h1 id="Top">{versionName}</h1>
{BY_DOCUMENT_PARAGRAPH}
<p class="viewLst">{thisBible.abbreviation} <a href="byDoc">By Document</a> <a href="bySec">By Section</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
''' if thisBible.discoveryResults['ALL']['haveSectionHeadings'] else \
f'''<h1 id="Top">{versionName}</h1>
{BY_DOCUMENT_PARAGRAPH}
<p class="viewLst">{thisBible.abbreviation} <a href="byDoc">By Document</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {versionName}' ) \
                    .replace( f'''<a title="{versionName}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    filepath = folder.joinpath( 'index.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{indexHtml}{makeBottom( level, 'site', state )}''' )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages._createVersionPages


def _createOETMissingVersePage( level:int, buildFolder:Path ) -> bool:
    """
    """
    textHtml = '''<h1>OET Missing Verse page</h1>
<p class="note">The <em>Open English Translation Readers’ Version</em> uses the <b>◘</b> symbol
to indicate places where we intentionally did not include the translation of an <b>entire</b> verse.
This is not because we’re trying to trying to hide anything that was in the original scriptures,
but rather it’s because the majority of scholars believe that the verse was added later by a scribe
and most likely was not written by the original author of the book or letter.</p>
<p class="note">It’s clear that the oldest copies of the manuscripts that we have, are not the originals which were first dictated by their authors,
but rather they’re copies made over the next few centuries.
Often, the copyists wanted to fix errors which they believed earlier copyists may have made,
or add additional information that they thought would help the reader.
And then of course, some of them introduced accidental errors of their own,
especially in the New Testament era where scribes often were not professionals.</p>
<p class="note"><small>Note: Your browser back button should return you to your previous page.</small></p>
<p class="note">In the interest of complete transparency, here is a list of the passages that we didn’t include with a rough, literal translation of each:</p>
<ul>
<li><a href="byC/JHN_C5.htm#V4">Yohan (John) 5:4</a>: For a messenger of the master went down into the pool and stirred up the water at certain times, and then the one having first stepped in after the stirring of the water was healed from whatever disease he suffered from.</li>
<li><a href="bySec/JHN_S28.htm#V53">Yohan (John) 7:53–8:11</a>: Then each went to his own house. Now Yeshua went to the Mount of Olives. Now early in the morning he came to the temple again, and all the people came to him. Now the scribes and the Pharisees brought a woman caught in adultery, and they placed her in the middle. The priests say to him, testing him in order to have an accusation against him, Teacher, this woman has been caught in the act of adultery. Now in the law, Moses commanded us to stone such ones, but what do you say now? But Yeshua, having bent down, began to write on the ground with his finger. But when they continued asking him questions, he stood up and said to them, Let the blameless one among you throw a stone at her first. And again, having stooped down, he wrote on the ground with his finger. But each of the Jews went out, beginning with the oldest, so that they all went out, and he was left alone, with the woman being in the midst. And Yeshua, having stood up, said to the woman, Where are they? Did no one condemn you? And she said to him, No one, master. And he said, Neither do I condemn you. Go, from now sin no longer.</li>
<li><a href="byC/MRK_C7.htm#V16">Mark 7:16</a>: If anyone has ears to hear, let him hear.</li>
<li><a href="byC/MRK_C9.htm#V44">Mark 9:44</a>: where their worm does not end, and the fire is not quenched.</li>
<li><a href="byC/MRK_C9.htm#V46">Mark 9:46</a>: where their worm does not end, and the fire is not quenched.</li>
<li><a href="byC/MRK_C11.htm#V26">Mark 11:26</a>: But if you do not forgive, neither will your father who is in the heavens forgive your trespasses.</li>
<li><a href="byC/MRK_C15.htm#V28">Mark 15:28</a>: And the scripture was fulfilled that says, And he was counted with lawless ones. (<a href="byC/ISA_C53.htm#V12">Isa 53:12</a>)</li>
<li><a href="byC/MAT_C16.htm#V2">Matthew 16:2–3</a>: Evening having come, you say, It will be fair weather, for the sky is red.’ And in early morning, ‘Today will be stormy, for the sky is red, being overcast. You know to interpret the face of the sky, but the signs of the times you are not able.</li>
<li><a href="byC/MAT_C17.htm#V21">Matthew 17:21</a>: But this kind does not go out except by prayer and fasting.</li>
<li><a href="byC/MAT_C18.htm#V11">Matthew 18:11</a>: For the son of man came to save the one that has been lost.</li>
<li><a href="byC/MAT_C23.htm#V14">Matthew 23:14</a>: But woe to you, scribes and Pharisees, hypocrites, for you devour the houses of widows, also for a pretext praying at length. For this reason, you will receive greater judgment.</li>
<li><a href="byC/LUK_C17.htm#V36">Luke 17:36</a>: Two in a field; one will be taken and the other will be left.</li>
<li><a href="byC/LUK_C22.htm#V43">Luke 22:43–44</a>: And a messenger from heaven appeared to him, strengthening him. And being in agony, he was praying more earnestly, and his sweat became like drops of blood falling on the ground.</li>
<li><a href="byC/LUK_C23.htm#V17">Luke 23:17</a>: But he had obligation to release to them one at every feast.</li>
<li><a href="byC/ACT_C8.htm#V37">Acts 8:37</a>: And Philip said to him, If you believe from your whole heart, you will be saved. And answering he said, I believe in messiah, the son of God.</li>
<li><a href="byC/ACT_C15.htm#V34">Acts 15:34</a>: But it seemed good to Silas for them to remain there, so only Yudas travelled.</li>
<li><a href="byC/ACT_C24.htm#V6">Acts 24:6–8</a>: and we wanted to judge him according to our law, but Lysias, the chiliarch, coming with much force, took him away from our hands, commanding his accusers to come to you.</li>
<li><a href="byC/ACT_C28.htm#V29">Acts 28:29</a>: And when he had said these things, the Jews went away, having a great dispute among themselves.</li>
<li><a href="byC/ROM_C16.htm#V24">Romans 16:24</a>: The grace of our master Yeshua the messiah be with all of you. Amen.</li>
</ul>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Missing Verses" ) \
                    .replace( '__KEYWORDS__', 'Bible, OET, missing, verses' ) \
                    .replace( f'''<a title="OET" href="{'../'*level}OET">OET</a>''', 'OET' )
    filepath = buildFolder.joinpath( 'missingVerse.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{textHtml}{makeBottom( level, 'site', state )}''' )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    {len(textHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages._createOETMissingVersePage


def _createDetailsPages( level:int, buildFolder:Path, state:State ) -> bool:
    """
    Creates and saves details (copyright, licence, etc.) pages for each version
        plus a summary page of all the versions.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createDetailsPages( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}details pages for {len(state.BibleVersions)} versions…" )

    allDetailsHTML = ''
    for versionAbbreviation in ['OET'] + [versAbbrev for versAbbrev in state.preloadedBibles] + ['UBS']:
        if versionAbbreviation == 'TTN': # we only need the one for TOSN I think
            versionAbbreviation = 'TOBD' # Put this one in instead

        versionName =  state.BibleNames[versionAbbreviation]

        if 'OET' not in versionAbbreviation and versionAbbreviation not in ('TOBD',): # (These don't have a BibleLocation)
            if versionAbbreviation in state.BibleLocations:
                # Do some preparation for creating the details pages
                if 'eBible' in state.BibleLocations[versionAbbreviation]:
                    # This code scrapes info from eBible.org copr.htm files, and hence is very fragile (susceptible to upstream changes)
                    with open( os.path.join(state.BibleLocations[versionAbbreviation], 'copr.htm'), 'rt', encoding='utf-8' ) as coprFile:
                            fullCoprText = coprFile.read()
                    ixStart = fullCoprText.index( '''<p align="center"><a href='copyright.htm'>''' ) + 42
                    ixEnd = fullCoprText.index( '</a>', ixStart )
                    actualCoprText = fullCoprText[ixStart:ixEnd]
                    # print( f"  {ixStart=} {ixEnd=} '{actualCoprText}'")
                    state.detailsHtml[versionAbbreviation]['copyright'] = \
                            state.detailsHtml[versionAbbreviation]['copyright'].replace( '(coming)', actualCoprText ) \
                                    .replace( '© ©', '©' ).replace( 'Copyright © Public Domain', 'Public Domain' )
                    if 'Public Domain' in actualCoprText:
                            state.detailsHtml[versionAbbreviation]['licence'] = \
                            state.detailsHtml[versionAbbreviation]['licence'].replace( '(coming)', 'Public Domain' )
                    elif 'creativecommons.org/licenses/by-sa/4.0' in actualCoprText:
                            state.detailsHtml[versionAbbreviation]['licence'] = \
                            state.detailsHtml[versionAbbreviation]['licence'].replace( '(coming)', '<a href="https://CreativeCommons.org/licenses/by-sa/4.0/">Creative Commons Attribution Share-Alike license 4.0</a>' )
                    else: dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Unrecognised eBible {versionAbbreviation} copyright: '{actualCoprText}'")
                    state.detailsHtml[versionAbbreviation]['acknowledgements'] = \
                            state.detailsHtml[versionAbbreviation]['acknowledgements'].replace( '(coming)',
                                'Thanks to <a href="https://eBible.org/Scriptures/">eBible.org</a> for supplying the USFM files' )
                elif '/TXT/' in state.BibleLocations[versionAbbreviation]:
                    state.detailsHtml[versionAbbreviation]['acknowledgements'] = \
                            state.detailsHtml[versionAbbreviation]['acknowledgements'].replace( '(coming)',
                                'Thanks to <a href="https://www.BibleSuperSearch.com/bible-downloads/">BibleSuperSearch.com</a> for supplying the source file' )

        topHtml = makeTop( level+1, versionAbbreviation, 'details', 'details.htm', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName} Details" ) \
                .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' ) \
                .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.htm#Top">{versionAbbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )

        extraHTML = '''<h2>Key to Abbreviations</h2>
<p class="note">See key and more information <a href="byDoc/FRT.htm#Top">here</a>.</p>
''' if versionAbbreviation == 'T4T' else ''

        detailsHtml = f'''{extraHTML}<h2>About the {versionAbbreviation}</h2>{state.detailsHtml[versionAbbreviation]['about']}
<h2>Copyright</h2>{state.detailsHtml[versionAbbreviation]['copyright']}
<h2>Licence</h2>{state.detailsHtml[versionAbbreviation]['licence']}'''
        if 'acknowledgements' in state.detailsHtml[versionAbbreviation]:
            detailsHtml = f'''{detailsHtml}
<h2>Acknowledgements</h2>{state.detailsHtml[versionAbbreviation]['acknowledgements']}'''
        if 'notes' in state.detailsHtml[versionAbbreviation]:
            detailsHtml = f'''{detailsHtml}
<h2>Notes</h2>{state.detailsHtml[versionAbbreviation]['notes']}'''

        if TEST_MODE and versionAbbreviation in state.selectedVersesOnlyVersions:
            # Add a list of links to verses containing this version
            selectedVerseLinksList = [f'<a href="../par/{BBB}/C{C}V{V}.htm#Top">{getOETTidyBBB( BBB, titleCase=True )} {C}:{V}</a>' for BBB,C,V in state.preloadedBibles[versionAbbreviation]]
        #     for BBB,C,V in state.preloadedBibles[versionAbbreviation]:
        #         ourTidyBBB = getOETTidyBBB( BBB, titleCase=True )
        #         selectedVerseLinksList.append( f'<a href="../par/{BBB}/C{C}V{V}.htm#Top">{getOETTidyBBB( BBB, titleCase=True )} {C}:{V}</a>' )
            detailsHtml = f'''{detailsHtml}
<h2>Available selections</h2>
<p class="rem">The following parallel verse pages feature this version:</p>
<p class="selectedLinks">{' '.join(selectedVerseLinksList)}</p>
'''

        bodyHtml = f'''<!--_createDetailsPages--><h1 id="Top">{versionName} Details</h1>
{detailsHtml}<hr style="width:40%;margin-left:0;margin-top: 0.3em">
<p class="note">See details for ALL included translations and reference materials <a title="All versions’ details" href="../AllDetails.htm#Top">here</a>.</p>
'''

        allDetailsHTML = f'''{allDetailsHTML}{'<hr style="width:40%;margin-left:0;margin-top: 0.3em">' if allDetailsHTML else ''}<h2 id="{versionAbbreviation}">{versionName}</h2>
{detailsHtml.replace('h2','h3')}'''

        html = f"{topHtml}{bodyHtml}{makeBottom( level+1, 'details', state )}"
        checkHtml( f'{versionAbbreviation} details', html )

        versionFolder = buildFolder.joinpath( f'{versionAbbreviation}/' )
        try: os.makedirs( versionFolder )
        except FileExistsError: pass # they were already there

        filepath = versionFolder.joinpath( 'details.htm' )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
            htmlFile.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

    # Make a summary page with details for all versions
    topHtml = makeTop( level, None, 'AllDetails', 'details.htm', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}All Versions Details" ) \
            .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' )
            # .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.htm#Top">{versionAbbreviation}</a>''',
            #             f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )
    html = f'''{topHtml}<h1 id="Top">Details for all versions</h1>
<p class="note">If you’re the copyright owner of a Bible translation and would like to see it listed on this site,
  please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
{allDetailsHTML}{makeBottom( level, 'AllDetails', state )}'''
    checkHtml( 'AllDetails', html )

    filepath = buildFolder.joinpath( 'AllDetails.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createDetailsPages


def _createSearchPage( level:int, buildFolder:Path, state:State ) -> bool:
    """
    Creates and saves the OBD search page.

    We use https://pagefind.app/
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createSearchPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}search page…" )

    searchHTML = f'''<h1 id="Top">Search {SITE_NAME}</h1>
<p class="note">Searching should find English and Latin words, plus Hebrew and Greek words and their English transliterations.</p>
{('<p class="note">Note that only limited Bible books are indexed on these TEST pages.</p>'+NEWLINE) if TEST_MODE else ''}<div id="search"></div>
<script>
    window.addEventListener('DOMContentLoaded', (event) => {{
        new PagefindUI({{ element: "#search", showSubResults: false }});
    }});
</script>
'''
    topHtml = makeTop( level, None, 'search', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Search OBD" ) \
                .replace( '__KEYWORDS__', 'Bible, search, OBD' ) \
                .replace( '</head>', '''  <link rel="stylesheet" href="pagefind/pagefind-ui.css">
  <script src="pagefind/pagefind-ui.js"></script>
</head>''')
    html = f'''{topHtml}{searchHTML}<p class="note">Search functionality is provided thanks to <a href="https://Pagefind.app/">Pagefind</a>.</p>
<p class="note"><small>OBD pages last rebuilt: {date.today()}</small></p>{makeBottom( level, 'search', state )}'''
    checkHtml( 'Search', html )

    filepath = buildFolder.joinpath( 'Search.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createSearchPage


def _createAboutPage( level:int, buildFolder:Path, state:State ) -> bool:
    """
    Creates and saves the About OBD page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createAboutPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating {'TEST ' if TEST_MODE else ''}about page…" )

    aboutHTML = f'''<h1 id="Top">About {SITE_NAME}</h1>
<p class="about">{SITE_NAME} ({SITE_ABBREVIATION}) is a large set of static webpages created for several main reasons:</p>
<ol>
<li>As a way to <b>showcase the <em>Open English Translation</em></b> of the Bible which is designed to be read with the <em>Readers’ Version</em> and the very <em>Literal Version</em> side-by-side.
    (Most existing Bible apps don’t allow for this.)
    Also, the <em>OET</em> renames some Bible ‘books’ and places them into a different order,
        and even modernises terminology like ‘Old Testament’ and ‘New Testament’
            with ‘The Hebrew Scriptures’ and ‘The Messianic Update’.</li>
<li>To <b>showcase how <em>OET-RV</em> section headings are formatted</b> so as not to break the flow of the text.
    Section headings are available as a help to the reader, but were not in the original manuscripts,
        and the original flow of the text was not designed to be arbitrarily divided into sections.</li>
<li>To <b>promote other open-licenced Bible translations</b>, including those developed as resources for Bible translators themselves. We believe that God’s Message should be freely available to all.</li>
<li>As a way to <b>showcase open-licenced Bible datasets</b>.
    Hence every word in the <em>OET-LV</em> is linked to the Greek word that they are translated from.
    In addition, most pronouns like ‘he’ or ‘she’ are linked to the earlier referrents in the text.</li>
<li>For the <b>comparison and evaluation of the history and quality and distinctives of various Bible translations</b>.
    So on the parallel verse pages, you can track Biblical wording right from the Biblical Hebrew or Greek,
        then up through the Latin (near the bottom of the page) and then Wycliffe’s and Tyndale’s early English translations,
        then right up through more modern translations all the way back up to the <em>OET</em> at the top.</li>
<li>We try to <b>downplay chapter and verse divisions</b>, and encourage readers to read narratives as narratives and letters as letters—would
        you take a letter or email from your mother, draw lines through it to divide it into random sections/chapters,
        and then read different sections on different days?</li>
</ol>
<p class="about">You might especially note the following features:</p>
<ul>
<li>Our <b>Related passage view</b> shows the <em>OET-RV</em> by section,
        along with any other parallel or related sections,
        and then with all the cross-references expanded underneath that.</li>
<li>Our <b>Parallel verse view</b> shows individual <em>OET</em> verses at the top,
        but if you’re interested in English Bible translation history,
        go to the bottom of the page (and then scroll up through any Study Notes) until you find the original language (Hebrew or Greek) versions.
    Then work your way upwards, through the Latin to the Wycliffe and Tyndale translations,
        and then other early English translations until you see that English spelling becomes standardised with the proliferation of mass-produced books by the time of the 1769 revision of the KJB.
    As you work upwards in chronological order, it’s fascinating to see two things:
    <ol>
    <li>how spelling in early English books was phonetic (sounding out the words) and quite variable
            <small>(and so we try to help you with a conversion to modern English in parentheses)</small>, and</li>
    <li>how translators often reused phrases from earlier English translations, but other times chose to disagree.</li>
    </ol></li>
<li>Our <b>Interlinear verse view</b> shows word-for-word interlinear and reverse-interlinear views of the <em>OET</em> and the original languages.</li>
<li>Our <b>Search page</b> allows you to search for English, Latin, Hebrew, and Greek words.</li>
<li>On the negative side, note that <b>our Old Testament pages are still much less developed than our New Testament ones</b>—both a still very much a work-in-progress, but for the Old Testament, we're still waiting for corrections from some of our partners before we can improve our own side more.</li>
</ul>
<p class="about">We would welcome any others who would like to contribute open datasets or code to this endeavour.
    Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.
    We consider this {SITE_ABBREVIATION} project to be part of the very first stage of contributing to the development of an open-licensed Bible-study app
        to rival the commercial ones (like ‘Logos’—not the plural of ‘logo’).</p>
<p class="about">You’ll possibly notice that not many large, commercial Bibles are included in these pages because of their strict limits on the use of their texts.
    We highly recommend that our readers find better translations that are more influenced by discipleship priorities, and less by finances.
    <small>(See <a href="https://SellingJesus.org/">SellingJesus.org</a> if you want to learn more about commercialism of Christian publications.)</small></p>
<p class="about"><b>Acknowledgement</b>: The overall design of the site was influenced by <a href="https://BibleHub.com/">BibleHub.com</a>
        and their <a href="https://OpenBible.com/">OpenBible.com</a> which have many features that we like
        (and likely many overlapping goals).</p>
<h3>Technical details</h3>
<p class="about">These pages are created by a Python program that takes the open-licenced resources and combines them in different ways on different pages.
    The program is still being developed, and hence this site (or this part of the site), is still at the prototype stage,
        especially with respect to navigation around the pages which is still being improved.</p>
<p class="about">Also, several Bible ‘books’ are not yet included because no draft of the <em>OET</em> is available,
    so you might find some dead links, i.e., “Page Not Found” errors, that will eventually be fixed.</p>
<p class="about">If you are the copyright owner of a Bible translation or a relevant dataset and would like to see it listed on this site,
        please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
<p class="about">The source code for the Python program that produces these pages can be found at <a href="https://github.com/Freely-Given-org/OpenBibleData">GitHub.com/Freely-Given-org/OpenBibleData</a>.
    You can also advise us of any errors by clicking on <em>New issue</em> <a href="https://github.com/Freely-Given-org/OpenBibleData/issues">here</a> and telling us the problem.</p>'''
    topHtml = makeTop( level, None, 'about', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}About {SITE_ABBREVIATION}" ) \
                .replace( '__KEYWORDS__', f'Bible, about, {SITE_ABBREVIATION}' )
    html = f'''{topHtml}
{aboutHTML}
<p class="note"><small>Last rebuilt: {date.today()}</small></p>
{makeBottom( level, 'about', state )}'''
    checkHtml( 'About', html )

    filepath = buildFolder.joinpath( 'About.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createAboutPage


def _createNewsPage( level:int, buildFolder:Path, state:State ) -> bool:
    """
    Creates and saves the OBD News page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createNewsPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating {'TEST ' if TEST_MODE else ''}news page…" )

    newsHTML = f'''<h1 id="Top">{SITE_NAME} News</h1>
<p class="about">Recent {SITE_NAME} ({SITE_ABBREVIATION}) site developments:</p>
<ul>
<li><b>2024-Apr-20</b>: We added the <a href="{'../'*level}AICNT">AI Critical New Testament</a> (AICNT), mainly so that we can start to evaluate (on our <a href="{'../'*level}par/MRK/C1V1.htm#Top">Parallel Pages</a>) how well current, so-called ‘AI’ technologies might affect the Bible translation world.</li>
<li><b>2024-Feb-15</b>: We added <a href="{'../'*level}rel/">Related Passages pages</a>—displaying related passages side-by-side, e.g., <a href="{'../'*level}rel/MRK/MRK_S3.htm#Top">here</a> (if you have a wide screen).</li>
</ul>
<p class="about">If you are the copyright owner of a Bible translation or a relevant dataset and would like to see it listed on this {SITE_ABBREVIATION} site,
        please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
<p class="about">The source code for the Python program that produces these pages can be found at <a href="https://github.com/Freely-Given-org/OpenBibleData">GitHub.com/Freely-Given-org/OpenBibleData</a>.
    You can also advise us of any errors by clicking on <em>New issue</em> <a href="https://github.com/Freely-Given-org/OpenBibleData/issues">here</a> and telling us the problem.</p>'''
    topHtml = makeTop( level, None, 'news', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{SITE_ABBREVIATION} News" ) \
                .replace( '__KEYWORDS__', f'Bible, news, {SITE_ABBREVIATION}' )
    html = f'''{topHtml}
{newsHTML}
{makeBottom( level, 'news', state )}'''
    checkHtml( 'News', html )

    filepath = buildFolder.joinpath( 'News.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createNewsPage


def _createOETKeyPage( level:int, buildFolder:Path, state:State ) -> bool:
    """
    Creates and saves the About OBD page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createOETKeyPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating {'TEST ' if TEST_MODE else ''}OET Key page…" )

    keyHTML = f'''<h1 id="Top">Key to the <em>OET</em></h1>
<p class="note">The <em>Open English Translation</em> of the Bible is not tied to tradition (and especially not to traditional mistakes or misunderstandings) so it has a number of changes from more common Bible translations.</p>
<p class="note">We also aim to educate our readers better about how our Bibles get to us and we have many different kinds of links on the site, so that’s a second reason why it differs from usual, and hence requires this key to explain some of the features.</p>
<h1>The Hebrew Scriptures <small>(Old Testament)</small><sup>*</sup></h1>
<p class="note">We are experimenting in the <em>OET-RV</em> with marking parallel Hebrew poetry lines with the symbol <b><span class="parr">≈</span></b>.
English tends to use rhyming for poetry (and rap is extreme rhyming), but we can also use things like shorter line/sentence lengths instead.
<a href="https://en.wikipedia.org/wiki/Biblical_poetry">Hebrew poetry</a> tends to use parallelism—shortish pairs of lines where the second line might say almost the same thing using synonyms, etc., or it might say the opposite thing (or it might just conclude the thought/argument).
Wherever, we believe that we have a retelling of almost the same thought in poetry, we try to assist the reader to see this by preceding the second line with the <span class="parr">≈</span> character (the mathematical ‘approximately equal’ sign).</p>
<p class="note">More to come...</p>
<h1>The Messianic Update <small>(New Testament)</small></h1>
<p class="note">Still coming...</p>
<h1>Transliterations</h1>
<p class="note">The <em>OET</em> uses a unique set of characters for transliterating Hebrew and Greek characters, taking advantage of the modern Unicode character set which is now available to us.
This has the disadvantage of being different from the transliterations commonly used in academia, but the advantage of being designed with the less technical reader in mind, i.e., we’ve tried to make it easier for the non-expert who's familiar with the English alphabet to guess at the sound of the letter.
We’ve also tried to take advantage of single Unicode characters like <b>æ</b> and <b>ʦ</b> to represent two English letters as a match for the single letters in the other languages.</p>
<p class="note">Long vowels are indicated with the macron over the vowel, i.e., ‘ā ē ī ō ū’ versus the normal ‘a e i o u’.</p>
<p class="note">More to come...</p>
<h1>Names of people and places</h1>
<p class="note">Imagine that your mother named you ‘Charlotte’ (pronounced <i><b>shar</b>-lot</i>) after your grandmother,
but when you moved to another country where they weren’t so familiar with the name,
people there read it and pronounced it as <i>char-<b>lot</b>-tee</i>.
You’d basically have two choices:</p>
<ol><li>Correct them and tell them that you are <i><b>shar</b>-lot</i> not <i>char-<b>lot</b>-tee</i>, or</li>
<li>Just put up with it and hope your mother never visits that place or she’d be horrified.</li></ol>
<p class="note">If you’d choose #1 above, imagine that your name was Yacobos but all English Bible readers called you James, which is totally and utterly different from your real name.
Would it bug you? If it would, hopefully you’ll appreciate the <em>OET</em> more than those people who’d have chosen #2.</p>
<p class="note">The <em>OET</em> can make us uncomfortable if we’re happy to continue to mispronounce people’s names.
If that’s you, please just continue to enjoy your old Bible.
But if you’d prefer to be more considerate to others, then make the effort to pronounce their names better,
even if it’s hard for us now to get those old, wrong names out of our minds.</p>
<h1>Other</h1>
<p class="note">Omitted verses are marked with the character ◘ (with a link to our <a href="{'../'*level}OET/missingVerse.htm">missing verses page</a>) to indicate that we didn’t accidentally miss translating it.
The reason why such verses are not included is usually because the original language text was missing in the oldest manuscripts and thus believed to be a later addition in later copies.</p>
<p class="note">More to come...</p>
<p class="footnote"><b><sup>*</sup></b> The <em>OET</em> avoids the word ‘Testament’ because it’s not used in modern English (except perhaps by lawyers),
plus we dislike ‘Old’ and ‘New’ because ‘new’ might (wrongly) imply that the ‘old’ is no longer required.
Note that the terms ‘Old Testament’ and ‘New Testament’ don’t occur in any ancient manuscripts.</p>'''
    topHtml = makeTop( level, None, 'OETKey', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Key to the Open English Translation" ) \
                .replace( '__KEYWORDS__', 'Bible, key, OET' )
    html = f'''{topHtml}
{keyHTML}
{makeBottom( level, 'OETKey', state )}'''
    checkHtml( 'OETKey', html )

    filepath = buildFolder.joinpath( 'OETKey.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createOETKeyPage


def _createMainIndexPage( level, folder:Path, state:State ) -> bool:
    """
    Creates and saves the main index page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_createMainIndexPage( {level}, {folder}, {state.BibleVersions} )" )

    # Create the very top level index file
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating {'TEST ' if TEST_MODE else ''}main index page for {len(state.BibleVersions)} versions…" )
    html = makeTop( level, None, 'TopIndex', None, state ) \
            .replace( '__TITLE__', f'TEST {SITE_NAME} Home' if TEST_MODE else f'{SITE_NAME} Home') \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    if TEST_MODE:
        html = html.replace( '<body>', '<body><p class="note"><a href="../">UP TO MAIN NON-TEST SITE</a></p>')
    bodyHtml = f'<!--_createMainIndexPage--><h1 id="Top">{SITE_NAME} TEST Home</h1>' \
        if TEST_MODE else f'<!--_createMainIndexPage--><h1 id="Top">{SITE_NAME} Home</h1>'
    html = f'''{html}
{bodyHtml}
<p class="note">Welcome to this <em>{SITE_NAME}</em> site created to share God’s fantastic message with everyone,
    and with a special interest in helping Bible translators around the world.</p>
<p class="note">Choose a version abbreviation above to view Bible ‘books’ <b>by document</b> or <b>by section</b> or <b>by chapter</b>.</p>
<p class="note">The <b><a href="rel/">Related</a> passage</b> option shows OET-RV sections with any parallel or related content (especially in the ‘Messiah accounts’: John, Mark, Matthew, and Luke), as well as listing out all of the cross-references.</p>
<p class="note">For individual ‘verses’ you can see the OET-RV with the OET-LV underneath it, plus many other different translations, plus some translation notes in the <b><a href="par/">Parallel</a> verse</b> view.</p>
<p class="note">The <b><a href="ilr/">Interlinear</a> verse</b> view shows the OET-RV and OET-LV aligned with the original Hebrew or Greek words (including a ‘reverse interlinear’).</p>
<p class="note">The <b><a href="dct/">Dictionary</a></b> link takes you to the <i>Tyndale Bible Dictionary</i>, with UBS dictionaries also coming...</p>
<p class="note">The <b><a href="Search.htm">Search</a></b> link allows you to find English words (from a range of versions), or even Greek/Hebrew words, within the Bible text.</p>
<p class="note"><small>Last rebuilt: {date.today()}</small></p>
{makeBottom( level, 'TopIndex', state )}'''
    checkHtml( 'TopIndex', html )

    filepath = folder.joinpath( 'index.htm' )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

#     # Create the versions index file (in case it's needed)
#     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating versions {'TEST ' if TEST_MODE else ''}index page for {len(state.BibleVersions)} versions…" )
#     html = makeTop( level+1, None, 'TopIndex', None, state ) \
#             .replace( '__TITLE__', 'TEST {SITE_NAME} Versions' if TEST_MODE else '{SITE_NAME} Versions') \
#             .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
#     if TEST_MODE:
#         html = html.replace( '<body>', '<body><p class="index"><a href="{'../'*level}">UP TO MAIN NON-TEST SITE</a></p>')
#     bodyHtml = """<!--createVersionsIndexPage--><h1 id="Top">{SITE_NAME} TEST Versions</h1>
# """ if TEST_MODE else """<!--_createMainIndexPage--><h1 id="Top">{SITE_NAME} Versions</h1>
# """

#     bodyHtml = f'{bodyHtml}<p class="index">Select one of the above Bible version abbreviations for views of entire documents (‘<i>books</i>’) or sections or chapters, or else select either of the Parallel or Interlinear verse views.</p>\n<ol>'
#     for versionAbbreviation in state.BibleVersions:
#         bodyHtml = f'{bodyHtml}<li><b>{versionAbbreviation}</b>: {state.BibleNames[versionAbbreviation]}</li>'
#     bodyHtml = f'{bodyHtml}</ol>'

#     html += bodyHtml + f'<p class="index"><small>Last rebuilt: {date.today()}</small></p>' + makeBottom( level, 'TopIndex', state )
#     checkHtml( 'VersionIndex', html )

#     filepath = folder.joinpath( 'index.htm' )
        # assert not filepath.is_file() # Check that we're not overwriting anything
#     with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
#         htmlFile.write( html )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages._createMainIndexPage


def _getFolderSize( start_path='.' ) -> int:
    """
    Adapted from https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size
# end of createSitePages._getFolderSize


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    _createSitePages()
# end of createSitePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    _createSitePages()
# end of createSitePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createSitePages.py
