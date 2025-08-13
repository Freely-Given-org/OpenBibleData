#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Bibles.py
#
# Module handling OpenBibleData Bibles functions
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
Module handling Bibles functions for OpenBibleData package.


preloadVersions( state:State ) -> int
preloadVersion( versionAbbreviation:str, folderOrFileLocation:str, state:State ) -> Bible

loadTyndaleBookIntrosXML( abbrev:str, XML_filepath ) -> dict[str,str]
formatTyndaleBookIntro( abbrev:str, level:int, BBB:str, segmentType:str, state:State ) -> str
formatTyndaleNotes( abbrev:str, level:int, BBB:str, C:str, V:str, segmentType:str, state:State ) -> str # html
fixTyndaleBRefs( abbrev:str, level:int, BBBorArticleName:str, C:str, V:str, html:str, state:State ) -> str

formatUnfoldingWordTranslationNotes( level:int, BBB:str, C:str, V:str, segmentType:str, state:State ) -> str # html

loadSelectedVersesFile( fileLocation, givenName:str, givenAbbreviation:str, encoding='utf-8' ) -> Bible

getVerseDataListForReference( givenRefString:str, thisBible:Bible, lastBBB:str|None=None, lastC:str|None=None ) -> tuple[str,str,InternalBibleEntryList,list[str]]

getVerseMetaInfoHtml( BBB:str, C:str, V:str ) -> str # html

formatVerseDetailsHtml( verseRef:str ) -> str # html

briefDemo() -> None
fullDemo() -> None


CHANGELOG:
    2023-07-19 Fix '<class="sn-text">' bug
    2023-08-07 Add allowFourChars to our customised version of tidyBBB
    2023-10-09 Fix a few more uW tN markdown link references
    2023-12-29 Started adding OET OT
    2024-01-18 Try to handle backslashes better in TSV (text) Bibles
    2024-05-02 Improve UTN markdown to HTML conversion
    2024-06-10 Save and load pickled Bibles for load speed boost
    2024-07-22 Remove CRs (\\r) from UTNs
    2025-01-31 Do discover() before pickling to save time on the next load
    2025-02-05 Only load certain Bible versions if specified
    2025-03-11 Handle 'Quoted by' in OET-RV xrefs
    2025-03-14 Add link to sentence importance database
    2025-03-17 Update mapIndex format to include both high-res and low-res filenames
    2025-03-21 Handle obsolete pickle in OET-LV which has OT and NT in separate folders
    2025-04-16 Add cross-testament quotes to formatVerseDetailsHtml()
    2025-06-27 Fix bug where getBibleMapperMaps() and getVerseDataListForReference()
                    were forcing the load of Bible books where not wanted
"""
from datetime import datetime
import os, os.path
from pathlib import Path
import logging
import re
from xml.etree.ElementTree import ElementTree, ParseError
import shutil
from collections import defaultdict

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.USXXMLBible as USXXMLBible
import BibleOrgSys.Formats.ZefaniaXMLBible as ZefaniaXMLBible
import BibleOrgSys.Formats.CSVBible as CSVBible
import BibleOrgSys.Formats.LEBXMLBible as LEBXMLBible
import BibleOrgSys.Formats.VPLBible as VPLBible
import BibleOrgSys.Formats.uWNotesBible as uWNotesBible
import BibleOrgSys.Formats.TyndaleNotesBible as TyndaleNotesBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, getLeadingInt

sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew
sys.path.append( '../datasets/crossTestamentQuotes/' )
from load import getIndividualQuotedOTRefs, getIndividualQuotingNTRefs

from settings import State, ALTERNATIVE_VERSION, TEST_MODE, TEST_VERSIONS_ONLY, \
                                ALL_PRODUCTION_BOOKS, TEST_BOOK_LIST, PICKLE_FILENAME_END, TEMP_BUILD_FOLDER
from html import checkHtml
from OETHandlers import findLVQuote, getBBBFromOETBookName
from Dict import loadAndIndexUBSGreekDictJSON, loadAndIndexUBSHebrewDictJSON


LAST_MODIFIED_DATE = '2025-08-12' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.90'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BIBLE_MAPPER_PATH = Path( '../copiedBibles/maps/' )

NEWLINE = '\n'



def preloadVersions( state:State ) -> int:
    """
    Note this has a side-effect of removing unused entries from state.BibleVersions.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersions( {state.BibleVersions} )" )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{datetime.now().strftime('%H:%M')} Preloading {state.BibleVersions}{' in TEST mode' if TEST_MODE else ''}…" )

    for versionAbbreviation in state.BibleVersions[:]: # copy because we'll be deleting some entries as we go
        if TEST_VERSIONS_ONLY and versionAbbreviation not in TEST_VERSIONS_ONLY:
            continue # Skip this version not desired for this test

        if versionAbbreviation == 'OET':
            # This is a combination of two translations, so nothing to load here
            assert 'OET-RV' in state.BibleVersions and 'OET-LV' in state.BibleVersions
            continue

        if ( versionAbbreviation not in state.selectedVersesOnlyVersions
            and versionAbbreviation != 'TOSN' # coz TOSN loads lots of other things as well
            and versionAbbreviation in state.BibleLocations
            ):
            # See if a pickled version is available for a MUCH faster load time
            folderOrFileLocationPath = Path( state.BibleLocations[versionAbbreviation] )
            pickleFilename = f"{versionAbbreviation}__{'_'.join(TEST_BOOK_LIST)}{PICKLE_FILENAME_END}" \
                                if TEST_MODE and not ALL_PRODUCTION_BOOKS and versionAbbreviation not in state.WholeBibleVersions \
                                else f'{versionAbbreviation}{PICKLE_FILENAME_END}'
            pickleFolderPath = folderOrFileLocationPath if folderOrFileLocationPath.is_dir() else folderOrFileLocationPath.parent
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLooking for a pickle for ‘{versionAbbreviation}’{f' in {pickleFolderPath}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}…" )
            pickleFilePath = pickleFolderPath.joinpath( pickleFilename )
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{folderOrFileLocationPath=} {pickleFilename=} {pickleFolderPath=} {pickleFilePath=}" )
            if pickleFilePath.is_file():
                pickleIsObsolete = False
                pickleMTime = pickleFilePath.stat().st_mtime # A large integer
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"preloadVersions found {pickleFilename=}" )
                for somePath in pickleFolderPath.iterdir():
                    dPrint( 'Never', DEBUGGING_THIS_MODULE, f"{pickleFolderPath=} {somePath=} {type(somePath)=}" )
                    if somePath.is_file() and not str(somePath).endswith( PICKLE_FILENAME_END ):
                        fileMTime = somePath.stat().st_mtime # A large integer
                        if fileMTime > pickleMTime:
                            pickleIsObsolete = True
                            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} pickle is obsolete because {somePath.name} is more recent." )
                            break
                    elif versionAbbreviation == 'OET-LV': # This one has the OT and the NT in separate folders
                        if str(somePath).endswith ('intermediateTexts/auto_edited_OT_ESFM') or str(somePath).endswith ('intermediateTexts/auto_edited_VLT_ESFM'):
                            for someSubPath in somePath.iterdir():
                                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Checking file-times in {somePath=} {someSubPath=} {type(someSubPath)=}" )
                                if someSubPath.is_file() and not str(someSubPath).endswith( PICKLE_FILENAME_END ):
                                    fileMTime = someSubPath.stat().st_mtime # A large integer
                                    if fileMTime > pickleMTime:
                                        pickleIsObsolete = True
                                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} pickle is obsolete because {someSubPath.name} is more recent." )
                                        break
                    else:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Ignoring pickle file or folder {somePath=} {somePath.name=}")
                if not pickleIsObsolete:
                    try:
                        newBibleObj = BibleOrgSysGlobals.unpickleObject( pickleFilename, pickleFolderPath )
                        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"newObj is {newBibleObj}" )
                        # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Loaded {versionAbbreviation} {type(newBibleObj)} pickle file: {pickleFilename}." )
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"preloadVersions() loaded pickled {newBibleObj if BibleOrgSysGlobals.verbosityLevel>=2 else versionAbbreviation}" )
                        assert 'discoveryResults' in newBibleObj.__dict__ # .discover() should have been called before it was saved
                        state.preloadedBibles[versionAbbreviation] = newBibleObj
                        continue
                    except EOFError:
                        logging.critical( f"Failed to load {versionAbbreviation} pickle file: Ran out of input from {pickleFilename} in {pickleFolderPath}")
            else:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  No pickle file for {versionAbbreviation}." )

        if versionAbbreviation == 'OET-LV':
            # Load the OT and NT from separate folders, and then combine them into one ESFM Bible object
            thisBibleOT = preloadVersion( versionAbbreviation, state.BibleLocations['OET-LV-OT'], state )
            assert isinstance( thisBibleOT, ESFMBible.ESFMBible )
            thisBibleNT = preloadVersion( versionAbbreviation, state.BibleLocations['OET-LV-NT'], state )
            assert isinstance( thisBibleNT, ESFMBible.ESFMBible )
            # print( f"{len(thisBibleOT)=} {len(thisBibleNT)=}" )
            thisBible = thisBibleOT
            for bookObject in thisBibleNT:
                # print( type(bookObject), bookObject.BBB )
                assert bookObject.BBB not in thisBible.books
                thisBible.books[bookObject.BBB] = bookObject
            # print( f"{len(thisBibleOT)=}" )
            # print( f"{len(thisBibleOT.ESFMWordTables)=}" )
            for wordTableID,wordTable in thisBibleNT.ESFMWordTables.items():
                # print( f"{wordTableID=} {type(wordTable)=}")
                thisBible.ESFMWordTables[wordTableID] = wordTable
            # print( f"{len(thisBible.ESFMWordTables)=}" )
            # For now, use add custom OT and NT sourceFolder variables so that we can load the two different word files
            thisBible.OTsourceFolder = thisBibleOT.sourceFolder
            thisBible.NTsourceFolder = thisBibleNT.sourceFolder
            thisBible.sourceFolder = None
            state.preloadedBibles['OET-LV'] = thisBible
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nDoing discovery for {thisBible.abbreviation} ({thisBible.name})…" )
            thisBible.discover()
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"preloadVersions() loaded {thisBible}" )

            pickleFilename = f"OET-LV__{'_'.join(TEST_BOOK_LIST)}{PICKLE_FILENAME_END}" \
                                if TEST_MODE and not ALL_PRODUCTION_BOOKS and versionAbbreviation not in state.WholeBibleVersions \
                                else f'{versionAbbreviation}{PICKLE_FILENAME_END}'
            pickleFolderPath = state.BibleLocations['OET-LV']
            thisBible.pickle( pickleFilename, pickleFolderPath )

        # Everything other than OET-LV
        elif versionAbbreviation in state.BibleLocations:
            thisBible = preloadVersion( versionAbbreviation, state.BibleLocations[versionAbbreviation], state )
            if isinstance(thisBible, Bible) \
            or versionAbbreviation in state.selectedVersesOnlyVersions:
                state.preloadedBibles[versionAbbreviation] = thisBible
            else:
                halt # preloadVersion failed

        else:
            logging.critical( f"createPages preloadVersions() has no folder location to find ‘{versionAbbreviation}’" )
            assert 'OET' not in versionAbbreviation
            state.BibleVersions.remove( versionAbbreviation )
    return len(state.preloadedBibles)
# end of Bibles.preloadVersions

TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict = {}, {}
def preloadVersion( versionAbbreviation:str, folderOrFileLocation:str, state:State ) -> Bible:
    """
    Loads the requested Bible into memory
        and return the Bible object.
    """
    from Dict import loadTyndaleOpenBibleDictXML
    global TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict

    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( ‘{versionAbbreviation}’, '{folderOrFileLocation}', … ){' in TEST mode' if TEST_MODE else ''}" )
    versionName = state.BibleNames[versionAbbreviation]

    # if versionAbbreviation in ('BSB',): # Single TSV .txt file
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} CSV/TSV Bible…" )
    #     thisBible = CSVBible.CSVBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='iso-8859-1' )
    #     thisBible.load()
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    if versionAbbreviation in ('BLB','SBL-GNT'): # Single (BLB) or multiple (SBL-GNT) TSV .txt file(s)
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ CSV/TSV Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = CSVBible.CSVBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MRK', '10', '45') )
        # print( f"Mrk 10:45 {verseEntryList=} {contextList=}" )
    # elif versionAbbreviation in ('SBL-GNT',): # .txt file(s)
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} VPL Bible…" )
    #     thisBible = VPLBible.VPLBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='utf-8' )
    #     thisBible.loadBooks() # So we can iterate through them all later
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    elif versionAbbreviation == 'LEB': # Custom XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ XML Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = LEBXMLBible.LEBXMLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif versionAbbreviation in ('Cvdl','Bshps','SLT'): # Custom VPL
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ VPL Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = VPLBible.VPLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.load() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MRK', '1', '1') )
        # print( f"Mrk 1:1 {verseEntryList=} {contextList=}" )
    elif 'Zefania' in folderOrFileLocation: # Zefania XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ Zefania XML Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = ZefaniaXMLBible.ZefaniaXMLBible( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{versionAbbreviation} {thisBible.suppliedMetadata=}" )
        # print( f"{versionAbbreviation} {thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"{versionAbbreviation} Mat 2:1 {verseEntryList=} {contextList=}" )
        # if versionAbbreviation=='Luth': halt
    elif 'OET' in versionAbbreviation or 'ESFM' in folderOrFileLocation: # ESFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ ESFM Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = ESFMBible.ESFMBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation )
        thisBible.loadAuxilliaryFiles = True
        # if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
        #     thisBible.uWencoded = True # TODO: Shouldn't be required ???
        if 'ALL' in state.booksToLoad[versionAbbreviation]:
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
            thisBible.lookForAuxilliaryFilenames()
    elif versionAbbreviation == 'UTN':
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading uW translation notes{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = uWNotesBible.uWNotesBible( state.BibleLocations[versionAbbreviation], givenName='uWTranslationNotes',
                                            givenAbbreviation='UTN', encoding='utf-8' )
        # thisBible.loadBooks() # So we can iterate through them all later
        if 'ALL' in state.booksToLoad[versionAbbreviation]:
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
    elif versionAbbreviation == 'TOSN': # We use this to also load non-Bible (non-B/C/V) stuff
        #   like Tyndale open Bible dictionary and book intros and UBS dictionaries
        sourceFolder = state.BibleLocations[versionAbbreviation]

        # We sneak in some extra loads here
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale book intros from {sourceFolder}…" )
        sourceFilename = 'BookIntros.xml'
        thisExtraAbbreviation = 'TBI'
        TyndaleBookIntrosDict = loadTyndaleBookIntrosXML( thisExtraAbbreviation, os.path.join( sourceFolder, sourceFilename ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale book intro summaries from {sourceFolder}…" )
        sourceFilename = 'BookIntroSummaries.xml'
        thisExtraAbbreviation = 'TBIS'
        TyndaleBookIntroSummariesDict = loadTyndaleBookIntrosXML( thisExtraAbbreviation, os.path.join( sourceFolder, sourceFilename ) )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale Open Bible Dictionary from {sourceFolder}…" )
        thisExtraAbbreviation = 'TOBD'
        loadTyndaleOpenBibleDictXML( thisExtraAbbreviation, os.path.join( sourceFolder, '../OBD/' ) )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale theme notes from {sourceFolder}…" )
        sourceFilename = 'ThemeNotes.xml'
        thisExtraAbbreviation = 'TTN'
        thisBible = TyndaleNotesBible.TyndaleNotesBible( os.path.join( sourceFolder, sourceFilename ), givenName='TyndaleThemeNotes',
                                            givenAbbreviation=thisExtraAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        if isinstance(thisBible, Bible):
            state.preloadedBibles[thisExtraAbbreviation] = thisBible

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale study notes from {sourceFolder}…" )
        sourceFilename = 'StudyNotes.xml'
        thisBible = TyndaleNotesBible.TyndaleNotesBible( os.path.join( sourceFolder, sourceFilename ), givenName='TyndaleStudyNotes',
                                            givenAbbreviation='TOSN', encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later

        loadAndIndexUBSGreekDictJSON( 'UGD', '../../Forked/ubs-open-license/dictionaries/greek/JSON' )
        loadAndIndexUBSHebrewDictJSON( 'UHD', '../../Forked/ubs-open-license/dictionaries/hebrew/JSON' )
    elif versionAbbreviation in state.selectedVersesOnlyVersions: # small numbers of sample verses
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading ‘{versionAbbreviation}’ sample verses…" )
        thisBible = loadSelectedVersesFile( folderOrFileLocation, givenName=versionName,
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        # NOTE: thisBible is NOT a Bible object here!!!
        # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
    elif versionAbbreviation in ('NET',) and 'eBible.org' not in folderOrFileLocation: # USX
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ USX Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = USXXMLBible.USXXMLBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if state.booksToLoad[versionAbbreviation] in (['ALL'],['OT'],['NT']):
            # We assume that we can load all books, even for OT and NT
            #  i.e., we assume (but don't check) that only those books will exist (plus maybe intro, etc.)
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
    else: # USFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading ‘{versionAbbreviation}’ USFM Bible{' in TEST mode' if TEST_MODE else ''}…" )
        thisBible = USFMBible.USFMBible( folderOrFileLocation, givenName=versionName, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
            thisBible.uWencoded = True # TODO: Shouldn't be required ???
        if state.booksToLoad[versionAbbreviation] in (['ALL'],['OT'],['NT']):
            # We assume that we can load all books, even for OT and NT
            #  i.e., we assume (but don't check) that only those books will exist (plus maybe intro, etc.)
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  preloadVersion() loaded {len(thisBible):,} {versionAbbreviation} verses" if versionAbbreviation in state.selectedVersesOnlyVersions else f"preloadVersion() loaded {thisBible}" )

    if ( versionAbbreviation not in state.selectedVersesOnlyVersions # they're dicts not Bible objects
    #and 'Zefania' not in folderOrFileLocation # TODO: these don't work for some reason
    and versionAbbreviation != 'OET-LV' # This one is handled by the calling function because it's more complex (uses two folders)
    and versionAbbreviation != 'TOSN' # This one has different complexities coz it loads various other bits
    ):
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nDoing discovery for {thisBible.abbreviation} ({thisBible.name})…" )
        thisBible.discover()

        pickleFilename = f"{versionAbbreviation}__{'_'.join(TEST_BOOK_LIST)}{PICKLE_FILENAME_END}" \
                            if TEST_MODE and not ALL_PRODUCTION_BOOKS and versionAbbreviation not in state.WholeBibleVersions \
                            else f'{versionAbbreviation}{PICKLE_FILENAME_END}'
        pickleFolderPath = folderOrFileLocation if os.path.isdir( folderOrFileLocation ) else Path( folderOrFileLocation ).parent
        thisBible.pickle( pickleFilename, pickleFolderPath )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Saved pickle file: {pickleFilename}." )

    return thisBible
# end of Bibles.preloadVersion

# The following functions are in BibleOrgSys.InternalBible
    # getNumChapters( self, BBB:str ) -> int:
    # getNumVerses( self, BBB:str, C:str ) -> int:
    # getContextVerseData( self, BCVReference:SimpleVerseKey|tuple[str,str,str,str]] ):
    # getVerseDataList( self, BCVReference:SimpleVerseKey|tuple[str,str,str,str]] ):
    # getVerseText( self, BCVReference, fullTextFlag:bool=False ) -> str:
# The following functions are in BibleOrgSys.InternalBibleBook
    # getNumChapters( self ) -> int:
    # getNumVerses( self, C:str ) -> int:
    # getContextVerseData( self, BCVReference:SimpleVerseKey|tuple[str,str,str,str]] ):

# # We want to add the following functions:
# def eachChapter( thisBible, BBB:str ) -> str:
#     """
#     """
#     yield '1'
#     yield '2'


def loadTyndaleBookIntrosXML( abbrev:str, XML_filepath ) -> dict[str,str]:
    """
    Load the Tyndale book intros or book intro summaries from the XML file
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadTyndaleBookIntrosXML( {abbrev}, {XML_filepath} )" )

    dataDict = {}
    loadErrors:list[str] = []
    XMLTree = ElementTree().parse( XML_filepath )

    if XMLTree.tag == 'items':
        topLocation = 'TBI file'
        BibleOrgSysGlobals.checkXMLNoText( XMLTree, topLocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( XMLTree, topLocation, '1wk8', loadErrors )
        # Process the attributes first
        for attrib,value in XMLTree.items():
            if attrib == 'release':
                releaseVersion = value
            else:
                logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
        assert releaseVersion == '1.25'

        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            name = None
            for attrib,value in element.items():
                if attrib == 'name':
                    name = value
                elif attrib == 'typename':
                    assert value == 'BookIntro' if abbrev=='TBI' else 'BookIntroSummary', f"{name=} {value=}"
                elif attrib == 'product':
                    assert value == 'TyndaleOpenStudyNotes'
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
            assert name

            # Now work thru each item
            stateCounter = 0
            title = None
            thisEntry = ''
            for subelement in element:
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{subelement} {subelement.text=}" )
                sublocation = f"{location}-{subelement.tag}"
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1wk8', loadErrors )
                if stateCounter == 0:
                    assert subelement.tag == 'title'
                    title = subelement.text
                    assert title
                    stateCounter += 1
                elif stateCounter == 1:
                    assert subelement.tag == 'refs'
                    refs = subelement.text
                    assert refs
                    assert '-' in refs
                    # assert refs == ref, f"{refs=} {ref=}" # Hmmh, not sure why some differ e.g., Gen.4.25-26 vs Gen.4.25-5.32
                    firstRef = refs.split('-')[0]
                    assert firstRef.count('.') == 2
                    OSISBkCode, firstC, firstVs = firstRef.split( '.' )
                    if OSISBkCode.endswith('Thes'):
                        OSISBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( OSISBkCode )
                    stateCounter += 1
                elif stateCounter == 2:
                    assert subelement.tag == 'body'
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '1wk8', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                    pCount = 0
                    for bodyelement in subelement:
                        bodyLocation = f'{sublocation}-{bodyelement.tag}-{pCount}'
                        # print( f"{bodyelement} {bodyelement.text=}" )
                        assert bodyelement.tag == 'p'
                        # Process the attributes first
                        pClass = None
                        for attrib,value in bodyelement.items():
                            if attrib == 'class':
                                pClass = value
                                assert pClass.startswith('intro-')
                                classList = ('intro-overview','intro-h1','intro-body-fl','intro-body','intro-body-fl-sp',
                                        'intro-list','intro-list-sp','intro-list-sp',
                                        'intro-poetry-1-sp','intro-poetry-2',
                                        'intro-extract') if abbrev=='TBI' \
                                    else ('intro-title','intro-sidebar-h1','intro-sidebar-body-fl')
                                assert pClass in classList, f"{refs} {pClass=} {bodyLocation}"
                            else:
                                logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                        # So we want to extract this as an HTML paragraph
                        htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation ) \
				                                                .replace( '<a href="  \\?', '<a href="?') # Fix encoding mistake in 1 Tim
                        assert '\\' not in htmlSegment, f"{BBB} {pCount=} {htmlSegment=}"
                        theirClass = None
                        if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant…
                            ixClose = htmlSegment.index( '">', 10 )
                            theirClass = htmlSegment[8:ixClose]
                            htmlSegment = htmlSegment[ixClose+2:]
                        assert theirClass.startswith('intro-')
                        htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                        thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                        pCount += 1
                    stateCounter += 1
                else: halt
            if thisEntry:
                dataDict[BBB] = thisEntry

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadTyndaleBookIntrosXML() loaded {len(dataDict):,} {abbrev} book intros." )
    return dataDict
# end of Bibles.loadTyndaleBookIntrosXML


def formatTyndaleBookIntro( abbrev:str, level:int, BBB:str, segmentType:str, state:State ) -> str:
    """
    """
    global TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict

    fnPrint( DEBUGGING_THIS_MODULE, f"formatTyndaleBookIntro( {abbrev}, {BBB}, … )" )
    assert abbrev in ('TBI','TBIS')
    assert segmentType == 'parallelVerse'

    sourceDict = {'TBI':TyndaleBookIntrosDict, 'TBIS':TyndaleBookIntroSummariesDict}[abbrev]
    if BBB not in sourceDict:
        logging.warning( f'No Tyndale book intro for {abbrev} {BBB}' )
        return ''

    bHtml = sourceDict[BBB]
    # print( f'{abbrev} {BBB} Intro {html=}' )

    # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
    bHtml = fixTyndaleBRefs( abbrev, level, BBB, "-1", "0", bHtml, state )

    assert checkHtml( f'{abbrev} {BBB}', bHtml, segmentOnly=True )
    return bHtml
# end of Bibles.formatTyndaleBookIntro


def formatTyndaleNotes( abbrev:str, level:int, BBB:str, C:str, V:str, segmentType:str, state:State ) -> str: # html
    """
    These are mostly HTML now artificially encoded inside USFM fields.
    """
    ftnRef = f'{BBB}_{C}:{V}'
    fnPrint( DEBUGGING_THIS_MODULE, f"formatTyndaleNotes( {ftnRef}, {segmentType=} )" )
    assert abbrev in ('TOSN','TTN')
    assert segmentType in ('parallelVerse','interlinearVerse')

    try:
        verseEntryList = state.preloadedBibles[abbrev].getVerseDataList( (BBB, C, V) )
    except KeyError:
        logging.warning( f"Tyndale have no notes for {abbrev} {ftnRef}" )
        return ''
    if not verseEntryList: # can be None
        logging.warning( f"Tyndale has no notes for {abbrev} {ftnRef}" )
        return ''

    nHtml = ''
    lastMarker = None
    inList = False
    for entry in verseEntryList:
        marker, rest = entry.getMarker(), entry.getText()
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{abbrev} {ftnRef} {marker}='{rest}'" )
        if marker in ('¬v','¬c','¬p','¬pi1','¬pi2','¬li1','¬chapters'):
            assert not rest; continue # most end markers not needed here
        # if marker == 'v':
        #     if '-' in rest: # It's often a verse range
        #         snHtml = f'{snHtml}<p class="TSNv">Verses {rest}</p>'
        if marker == 'v~':
            assert rest
            assert abbrev == 'TOSN'
            rest = rest.replace( '•', '<br>•' )
            theirClass = None
            if rest.startswith( '<class="'): # e.g., <class="theme-list">The new covenant…
                ixClose = rest.index( '">', 10 )
                theirClass = rest[8:ixClose]
                rest = rest[ixClose+2:]
            rest = rest.replace( ' <class="sn-text">', '</p>\n<p class="sn-text">')
                        # .replace( '<class="sn-text">', '</p>\n<p class="sn-text">')
            nHtml = f'{nHtml}<p class="{theirClass if theirClass else abbrev}">{rest}</p>'
        elif marker in ('s1','s2','s3'): # These have the text in the same entry
            assert rest
            assert abbrev == 'TTN'
            theirClass = None
            if rest.startswith( '<class="'): # e.g., <class="theme-list">The new covenant…
                ixClose = rest.index( '">', 10 )
                theirClass = rest[8:ixClose]
                rest = rest[ixClose+2:]
            if marker=='s1' and not theirClass: theirClass = 'theme-title'
            nHtml = f'{nHtml}\n<p class="{theirClass if theirClass else marker}">{rest}</p>'
        elif marker in ('p','pi1','pi2','li1'): # These have the text in the next entry
            assert not rest
            if marker!='li1': assert abbrev == 'TTN'
            # will be saved as lastMarker for later use
        elif marker == 'p~':
            assert rest
            theirClass = None
            if rest.startswith( '<class="'): # e.g., <class="theme-list">The new covenant…
                ixClose = rest.index( '">', 10 )
                theirClass = rest[8:ixClose]
                rest = rest[ixClose+2:]
            nHtml = f'{nHtml}\n<li>{rest}</li>' if lastMarker=='li1' \
                        else f'{nHtml}\n<p class="{theirClass if theirClass else lastMarker}">{rest}</p>'
        elif marker == 'b':
            assert not rest
            assert abbrev == 'TTN'
            nHtml = f'{nHtml}\n<br>'
        elif marker == 'list':
            assert not rest
            assert not inList
            # assert abbrev == 'TTN'
            nHtml = f'{nHtml}\n<ol>'
            inList = True
        elif marker == '¬list':
            assert not rest
            # assert inList, f"{ftnRef}" # Fails in Romans I think
            # assert abbrev == 'TTN'
            if inList:
                nHtml = f'{nHtml}</ol>'
                inList = False
        elif marker not in ('id','usfm','ide','intro','c','c#','c~','v','v='):
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{abbrev} {ftnRef} {marker}={rest}" )
            unknown_Tyndale_notes_marker
        assert '<class=' not in nHtml, f"{marker=} {rest=} {lastMarker=} {nHtml=}"
        lastMarker = marker
    if inList:
        nHtml = f'{nHtml}</ol>'
    assert nHtml.count( '<ol>' ) == nHtml.count( '</ol>' ), f"formatTyndaleNotes {ftnRef} {nHtml.count('<ol>')} ≠ {nHtml.count('</ol>')}"

    # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
    nHtml = fixTyndaleBRefs( abbrev, level, BBB, C, V, nHtml, state )

    nHtml = nHtml.replace( '<br>\n' , '\n<br>' ) # Make sure it follows our convention (just for tidyness and consistency)
    while '\n\n' in nHtml: nHtml = nHtml.replace( '\n\n', '\n' ) # Remove useless extra newline characters
    assert checkHtml( f'{abbrev} {ftnRef}', nHtml, segmentOnly=True )
    # if abbrev=='TTN' and BBB=='MRK' and C=='1' and V=='14': halt
    return nHtml
# end of Bibles.formatTyndaleNotes


def fixTyndaleBRefs( abbrev:str, level:int, BBBorArticleName:str, C:str, V:str, html:str, state:State ) -> str:
    """
    Most of the parameters are for info messages only
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"fixTyndaleBRefs( {abbrev}, {level}, {BBBorArticleName} {C}:{V} {html}, … )" )

    # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
    # Doesn't yet handle links like '(see “<a href="?item=FollowingJesus_ThemeNote_Filament">Following Jesus</a>” Theme Note)'
    searchStartIndex = 0
    for _safetyCount in range( 870 ): # 54 was enough for TSN ACT 9:2
        # but 110 not for TTN MRK 4:35, 120 not for Josh 13:1, 140 for Psa 97:2, 200 for book intros, 800 for "Animals"
        ixStart = html.find( 'href="?bref=', searchStartIndex )
        if ixStart == -1: # none/no more found
            break
        ixCloseQuote = html.find( '"', ixStart+12 )
        assert ixCloseQuote != -1
        tyndaleLinkPart = html[ixStart+12:ixCloseQuote]
        if not tyndaleLinkPart and BBBorArticleName=='AlTaschith':
            tyndaleLinkPart = 'Ps.58.1-2' # Fix encoding error
        # print( f"{abbrev} {BBBorArticleName} {C}:{V} {tyndaleLinkPart=}" )
        if 'Filament' in tyndaleLinkPart: # e.g., in GEN 48:14 '2Chr.28.12_StudyNote_Filament'
            logging.critical( f"Ignoring Filament link in {abbrev} {BBBorArticleName} {C}:{V} {tyndaleLinkPart=}" )
            searchStartIndex = ixCloseQuote + 6
            continue
        tyndaleLinkPart = tyndaleLinkPart.replace( '–', '-' ) # Convert en-dash to hyphen, esp. for TOBD HoseaBookof : tyndaleLinkPart='Deut.27.9–29.29'
        if '-' in tyndaleLinkPart: # then it's a verse range
            if tyndaleLinkPart == 'Deut.31:30-32.44': tyndaleLinkPart = 'Deut.31.30-32.44' # Fix TTN encoding error in Psa 71:22
            tyndaleLinkPart = tyndaleLinkPart.split('-')[0]
            tyndaleLinkPart = tyndaleLinkPart.split(',')[0] # Might also be a list (in the dict entries at least)
            tBkCode, tC, tV = tyndaleLinkPart.split( '.' )
            if tBkCode.endswith('Thes'):
                tBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
            assert tC.isdigit()
            tV = getLeadingInt( tV ) # in case there's an a or b or something
            # assert tV.isdigit(), f"'{abbrev}' {level=} {BBBorArticleName} {C}:{V} {tBkCode=} {tC=} {tV=}"
            tBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( tBkCode )
            if not tBBB:
                if tBkCode=='Tb': tBBB = 'TOB'
            assert tBBB
            linkVersion = 'OET' if tBBB in state.booksToLoad['OET'] else ALTERNATIVE_VERSION
            ourNewLink = f'''{'../'*level}{linkVersion}/byC/{tBBB}_C{tC}.htm#C{tC}V{tV}''' # Because it's a range, we link to the chapter page
            # print( f"   {ourNewLink=}" )
        elif ',' in tyndaleLinkPart: # then it's a verse list (only found in dictionary entries)
            tyndaleLinkPart = tyndaleLinkPart.split(',')[0]
            tBkCode, tC, tV = tyndaleLinkPart.split( '.' )
            if tBkCode.endswith('Thes'):
                tBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
            assert tC.isdigit()
            assert tV.isdigit()
            tBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( tBkCode )
            if not tBBB:
                if tBkCode=='Tb': tBBB = 'TOB'
            assert tBBB
            linkVersion = 'OET' if tBBB in state.booksToLoad['OET'] else ALTERNATIVE_VERSION
            ourNewLink = f'''{'../'*level}{linkVersion}/byC/{tBBB}_C{tC}.htm#C{tC}V{tV}''' # Because it's a list, we link to the chapter page
            # print( f"   {ourNewLink=}" )
        elif tyndaleLinkPart.count( '.' ) == 1: # it's a chapter
            tBkCode, tC = tyndaleLinkPart.split( '.' )
            if tBkCode.endswith('Thes'):
                tBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
            assert tC.isdigit()
            tBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( tBkCode )
            if not tBBB:
                if tBkCode=='Tb': tBBB = 'TOB'
            assert tBBB, f"'{abbrev}' {level=} {BBBorArticleName} {C}:{V} {tBkCode=} {tC=}"
            ourNewLink = f'''{'../'*level}{linkVersion}/byC/{tBBB}_C{tC}.htm#C{tC}V1''' # Because it's a chapter, we link to the chapter page
            # print( f"   {ourNewLink=}" )
        else: # no hyphen or comma so it's not a range or list
            tBkCode, tC, tV = tyndaleLinkPart.split( '.' )
            if tBkCode.endswith('Thes'):
                tBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
            assert tC.isdigit()
            tV = getLeadingInt( tV ) # in case there's an a or b or something
            # assert tV.isdigit(), f"'{abbrev}' {level=} {BBBorArticleName} {C}:{V} {tBkCode=} {tC=} {tV=}"
            tBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( tBkCode )
            if not tBBB:
                if tBkCode=='Tb': tBBB = 'TOB'
            assert tBBB, f"'{abbrev}' {level=} {BBBorArticleName} {C}:{V} {tBkCode=} {tC=} {tV=}"
            ourNewLink = f'''{'../'*level}par/{tBBB}/C{tC}V{tV}.htm#Top''' # we link to the parallel verse page
            # print( f"   {ourNewLink=}" )
        html = f'''{html[:ixStart+6]}{ourNewLink}{html[ixCloseQuote:]}'''
        searchStartIndex = ixStart + 8
    else: need_to_increase_Tyndale_bref_loop_counter

    return html
# end of Bibles.fixTyndaleBRefs


taMDLinkRegEx = re.compile( '\\[\\[rc://([^/]+?)/ta/man/(translate|checking)/(.+?)\\]\\]' )
taOtherLinkRegEx = re.compile( 'rc://([^/]+?)/ta/man/(translate|checking)/(.+?)[ ,.:;)\\]]' ) # Includes the following character after the link
twMDLinkRegEx = re.compile( '\\[\\[rc://([^/]+?)/tw/dict/bible/(names|kt|other)/(.+?)\\]\\]' )
twOtherLinkRegEx = re.compile( 'rc://([^/]+?)/tw/dict/bible/(names|kt|other)/(.+?)[ ,.:;)\\]]' ) # Includes the following character after the link
markdownLinkRegex = re.compile( '\\[([^[]]*?)\\]\\(([^ ]*?)\\)' )
NOTE_FILENAME_DICT = {'translate':'03-translate', 'checking':'04-checking'}
def formatUnfoldingWordTranslationNotes( level:int, BBB:str, C:str, V:str, segmentType:str, state:State ) -> str: # html
    """
    A typical entry with two notes looks like this (blank lines added):
        0/ v = '8'

        1/ m = ''
        2/ p~ = 'rc://*/ta/man/translate/figs-go'
        3/ ¬m = ''
        4/ q1 = ''
        5/ p~ = 'ἐξελθοῦσαι'
        6/ ¬q1 = ''
        7/ p = ''
        8/ p~ = 'Your language may say “come” rather than **gone** … natural. Alternate translation: “having come out”'
        9/ ¬p = ''

        10/ m = ''
        11/ p~ = 'rc://*/ta/man/translate/figs-abstractnouns'
        12/ ¬m = ''
        13/ q1 = ''
        14/ p~ = 'εἶχεν γὰρ αὐτὰς τρόμος καὶ ἔκστασις'
        15/ ¬q1 = ''
        16/ p = ''
        17/ p~ = 'If your language does not use an abstract noun for… “for they were greatly amazed, and they trembled”'
        18/ ¬p = ''

        19/ m = ''
    Note the superfluous final empty m field

    NOTE: For book and chapter introductions, the p~ entry might contain several markdown paragraphs.

    TODO: Get the English quote (ULT, OET-LV???) from the Greek words
    """
    utnRef = f'{BBB}_{C}:{V}'
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {level}, {utnRef}, {segmentType=} )" )
    assert segmentType in ('parallelVerse','interlinearVerse')

    try:
        verseEntryList = state.preloadedBibles['UTN'].getVerseDataList( (BBB, C, V) )
    except KeyError:
        logging.warning( f"uW TNs have no notes for {utnRef}" )
        return ''
    if not verseEntryList: # can be None
        logging.warning( f"uW TNs has no notes for {utnRef}" )
        return ''

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    # opposite = 'interlinear' if segmentType=='parallelVerse' else 'parallelVerse'
    # oppositeFolder = 'il' if segmentType=='parallelVerse' else 'pa'

    # We tried this, but think it's better to customise our own HTML
    # tnHtml = convertUSFMMarkerListToHtml( level, 'UTN', (BBB,C,V), 'notes', contextList, verseEntryList, basicOnly=True, state=state )

    tnHtml = ''
    lastMarker = None
    noteCount = 0
    occurrenceNumber = 1
    for entry in verseEntryList:
        marker, rest = entry.getMarker(), entry.getText()
        if marker.startswith( '¬' ): assert not rest; continue # end markers not needed here
        if marker in ('c','c#'):
            assert rest
            # print( f"UTN {utnRef} ignored {marker}='{rest}'" )
            continue # not used here
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"UTN {utnRef} {marker}='{rest}'" )
        if rest is None:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {utnRef}, {segmentType=} ) skipped UTN {marker}='{rest}'" )
            lastMarker = marker
            continue
        assert rest == entry.getFullText().rstrip(), f"UTN {utnRef} {marker}='{rest}' ft='{entry.getFullText()}'" # Just checking that we're not missing anything here
        assert marker in ('v', 'm','q1','p','pi1', 'p~', 'im','iq1','ip','ipi'), f"Unexpected marker UTN {utnRef} {marker}='{rest}' ({lastMarker=})" # We expect a very limited subset
        if '\\r' in rest: # TODO: Should this be in BibleOrgSys (when the UTNs are loaded???)
            logging.warning( f"Removed CR from UTN {utnRef}" )
            rest = rest.replace( '\\r', '' )

        if marker == 'v':
            if rest!=V and '-' not in rest:
                logging.error( f"Why did UTN {utnRef} get {marker}='{rest}' from {verseEntryList=}?" )
                # Doesn't seem that we usually need to display this but we will here in case something is wrong
                tnHtml = f'''{' ' if tnHtml else ''}{tnHtml}<span class="v">{V} </span>'''
            # assert rest==V or '-' in rest, f"UTN {utnRef} {marker}='{rest}' from {verseEntryList=}"

        elif marker == 'p~': # This has the text
            if lastMarker in ('m','im'):  # TA reference
                assert rest
                if rest.startswith( 'rc://*/ta/man/translate/' ):
                    noteName = rest[24:]
                    noteFile = '03-translate'
                elif rest.startswith( 'rc://en/ta/man/translate/' ):
                    noteName = rest[25:]
                    noteFile = '03-translate'
                elif rest.startswith( 'rc://*/ta/man/checking/' ):
                    noteName = rest[23:]
                    noteFile = '04-checking'
                else:
                    noteName = rest
                    noteFile = '03-translate'
                    logging.error( f"Missing ResourceContainer path in TA note: {utnRef} '{noteName}'" )
                betterNoteName = noteName.replace( 'figs-', 'figures-of-speech / ' )
                # print( f"{noteName=} {betterNoteName=}" )
                noteCount += 1
                tnHtml = f'''{tnHtml}{NEWLINE if tnHtml else ''}<p class="TARef"><b>Note {noteCount} topic</b>: <a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/{noteFile}.html#{noteName}">{betterNoteName}</a></p>'''
                occurrenceNumber = 1

            elif lastMarker in ('pi1','ipi'): # Occurrence number
                assert rest
                if rest!='-1' and not rest.isdigit():
                    logging.error( f"getContextVerseData ({utnRef}) has unexpected {lastMarker=} {marker=} {rest=}" )
                # assert rest.isdigit() or rest=='-1', f"getContextVerseData ({utnRef}) has unexpected {marker=} {rest=}" # Jhn 12:15 or 16???
                occurrenceNumber = getLeadingInt(rest) # Shouldn't be necessary but uW stuff isn't well checked/validated

            elif lastMarker in ('q1','iq1'): # An original language quote
                assert rest
                if rest.startswith( 'Connecting Statement' ):
                    assert occurrenceNumber == 0, f"{utnRef} Connecting Statement has occurrence={occurrenceNumber}" # UTN PSA 29:6 and onwards has lots of errors with this (that we fixed in our copy)
                    tnHtml = f'''{tnHtml}{NEWLINE if tnHtml else ''}<p class="Gram">{rest}</p>'''
                else: # assume it's an original language quote
                    # if BBB!='JHN' and C!='11' and V!='45': # Jn 11:45 and Exo 1:15, etc.
                    #     assert occurrenceNumber != 0, f"UTN {utnRef} {occurrenceNumber=} {marker}='{rest}'"
                    if occurrenceNumber == 0:
                        logging.error( f"UTN occurrenceNumber is zero with {utnRef} '{rest}'" )
                    lvQuoteHtml = findLVQuote( level, BBB, C, V, occurrenceNumber, rest, state ) \
                                        .replace(' & ',' <small>&amp;</small> ')
                    transQuoteHtml = ( lvQuoteHtml if lvQuoteHtml else f'({transliterate_Greek(rest)})' if NT else f'({transliterate_Hebrew(rest)})' ) \
                                        .replace( '\\sup ', '<sup>' ).replace( '\\sup*', '</sup>' ) # TODO: Check space isn't already _, e.g., http://freely-given.org/OBD/Test/par/JDG/C1V13.htm#Top
                    tnHtml = f'''{tnHtml}<p class="OL">{'' if occurrenceNumber==1 else f'(Occurrence {occurrenceNumber}) '}{rest.replace(' & ',' <small>&amp;</small> ')}</p>
<p class="Trans">{transQuoteHtml}</p>'''

            elif lastMarker in ('p','ip'): # This is the actual note (which can have markdown formatting)
                rest = rest.replace( '\\r', '' ) # Fix formatting inconsistencies in the original notes
                # Liven any TA markdown [[links]] (especially in book or chapter introductions)
                rest = rest.replace( '[ ]', '__SQUARE_BRACKETS__' ) # Protect this
                searchStartIndex = 0
                for _safetyCount in range( 10 ): # 6 wasn't enough for MAT (6?), 9 wasn't enough for REV (1?)
                    match = taMDLinkRegEx.search( rest, searchStartIndex )
                    if not match: break
                    assert match.group(1) in ('*','en') # Language code
                    noteClass, noteName = match.group(2), match.group(3)
                    rest = f'{rest[:match.start()]}<a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/{NOTE_FILENAME_DICT[noteClass]}.html#{noteName}">{noteName}</a>{rest[match.end():]}'
                    searchStartIndex = match.end() + 10 # Approx number of added characters
                else: tn_ta_loop1_range_needs_increasing
                # Liven any TA non-markdown links (especially in book or chapter introductions, e.g., Tit 1:0)
                searchStartIndex = 0
                for _safetyCount in range( 3 ): # 2 wasn't enough for ZEP (3:21?)
                    match = taOtherLinkRegEx.search( rest, searchStartIndex )
                    if not match: break
                    assert match.group(1) in ('*','en') # Language code
                    noteClass, noteName = match.group(2), match.group(3)
                    rest = f'{rest[:match.start()]}<a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/{NOTE_FILENAME_DICT[noteClass]}.html#{noteName}">{noteName}</a>{rest[match.end()-1:]}'
                    searchStartIndex = match.end() + 10 # Approx number of added characters
                else: tn_ta_loop2_range_needs_increasing
                # Liven any TW markdown [[links]] (e.g., JHN 1:40)
                searchStartIndex = 0
                for _safetyCount in range( 9 ): # 8 isn't enough for Job (41?)
                    match = twMDLinkRegEx.search( rest, searchStartIndex )
                    if not match: break
                    assert match.group(1) in ('*','en') # Language code
                    noteClass, noteName = match.group(2), match.group(3)
                    rest = f'{rest[:match.start()]}<a title="View uW TW article" href="https://Door43.org/u/unfoldingWord/en_tw/master/{noteClass}.html#{noteName}">{noteName}</a>{rest[match.end():]}'
                    searchStartIndex = match.end() + 10 # Approx number of added characters
                else: tn_tw_loop1_range_needs_increasing
                # Liven any TW non-markdown links (e.g., JHN 1:6)
                searchStartIndex = 0
                for _safetyCount in range( 2 ):
                    match = twOtherLinkRegEx.search( rest, searchStartIndex )
                    if not match: break
                    assert match.group(1) in ('*','en') # Language code
                    noteClass, noteName = match.group(2), match.group(3)
                    rest = f'{rest[:match.start()]}<a title="View uW TW article" href="https://Door43.org/u/unfoldingWord/en_tw/master/{noteClass}.html#{noteName}">{noteName}</a>{rest[match.end()-1:]}'
                    searchStartIndex = match.end() + 10 # Approx number of added characters
                else: tn_tw_loop2_range_needs_increasing
                # Replace markdown links with something more readable
                searchStartIndex = 0
                for _safetyCount in range( 100 ): # 45 wasn't enough for EXO 15:0, 94 wasn't enough for Lev 4:0
                    match = markdownLinkRegex.search( rest, searchStartIndex )
                    if not match: break
                    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{_safetyCount} getContextVerseData found UTN markdown link {utnRef} {match=} {match.groups()=}" )
                    newLink = match.group(1)
                    if match.group(2).startswith( '../' ) and match.group(2).endswith( '.md' ):
                        # Probably something like: [13:20](../13/20.md)
                        linkTarget = match.group(2)[3:-3]
                        if linkTarget.endswith('/'): linkTarget = linkTarget[:-1] # Mistake in UTN Rom 2:2
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Have scripture link {utnRef} {match.group(1)=} {linkTarget=}" )
                        if linkTarget == 'front/intro':
                            pass # TODO: We're being lazy here -- where do we find a book intro?
                        elif linkTarget.count('/') == 2:
                            lUUU, lC, lV = linkTarget.split( '/' ) # Something like '1TI' '01' '77'
                            # Deal with book encoding issues in the uW notes
                            if lUUU == 'i1kg': lUUU = '1Ki' # UTN Mat 17:0
                            elif lUUU.lower() == '2kg': lUUU = '2Ki'
                            assert len(lUUU) == 3, f"{lUUU=} {lC=} {lV=} {linkTarget=} from {utnRef} '{rest}'"
                            lC = int(lC)
                            try: lV = int(lV)
                            except ValueError:
                                if lV.startswith('.'): lV = int(lV[1:])
                            lBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( lUUU )
                            newLink = f'<a href="../{lBBB}/C{lC}V{lV}.htm#Top">{match.group(1)}</a>'
                        elif linkTarget.count('/') == 1:
                            lC, lV = linkTarget.split( '/' ) # Something like '01' '17'
                            lC = int(lC)
                            try: lV = int(lV)
                            except ValueError: # UTN EXO 4:20 has badly formatted link
                                if lV.startswith('.'): lV = int(lV[1:])
                            newLink = f'<a href="C{lC}V{lV}.htm#Top">{match.group(1)}</a>'
                        else:
                            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{_safetyCount} getContextVerseData found UTN markdown link {utnRef} {match=} {match.groups()=}" )
                            logging.error( f"formatUnfoldingWordTranslationNotes1 ({utnRef}) has unhandled markdown reference in '{rest}'" )
                    elif match.group(2).startswith( './' ) and match.group(2).endswith( '.md' ):
                        # Probably something like: [Mark 14:22–25](./22.md)
                        linkTarget = match.group(2)[2:-3]
                        # print( f"  Have scripture link {utnRef} {match.group(1)=} {linkTarget=}" )
                        if linkTarget.count('/') == 0:
                            lV = linkTarget
                            newLink = f'<a href="C{C}V{lV}.htm#Top">{match.group(1)}</a>'
                        else:
                            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{_safetyCount} getContextVerseData found UTN markdown link {utnRef} {match=} {match.groups()=}" )
                            logging.error( f"formatUnfoldingWordTranslationNotes2 ({utnRef}) has unhandled markdown reference in '{rest}'" )
                    else:
                        # e.g., From Ruth 3:9: [2:20](../02/20/zu5f)
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{_safetyCount} getContextVerseData found UTN markdown link {utnRef} {match=} {match.groups()=}" )
                        logging.error( f"formatUnfoldingWordTranslationNotes ({utnRef}) has unhandled markdown link in '{rest}'" )
                    rest = f'{rest[:match.start()]}{newLink}{rest[match.end():]}'
                    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {utnRef} with {newLink=}, now {rest=}" )
                    searchStartIndex = match.start() + len(newLink)
                else:
                    # logging.error( f"getContextVerseData found excess UTN markdown links in {_safetyCount} {utnRef} {rest=}" )
                    raise ParseError( f"need_to_increase_max_MDLink_loop_count getContextVerseData found excess UTN markdown links in {_safetyCount} for {utnRef} {rest=}" )
                if BBB not in ('HAG','MAT'): # uW Hag 1:0, Mat 27:0 have formatting problems
                    assert 'rc://' not in rest, f"UTN {utnRef} {lastMarker=} {marker}='{rest}'"
                while '**' in rest:
                    rest = rest.replace( '**', '<b>', 1 ).replace( '**', '</b>', 1 )
                # Add our own little bit of bolding
                #   and fix some UTN formatting errors
                rest = ( rest.replace( 'Alternate translation:', '<b>Alternate translation</b>:' )
                            .replace( '{', '<span class="add">' ).replace( '}', '</span>' ) # UTN uses braces {} for "add" markers, e.g., GEN 13:8, MRK 6:11
                            .replace( '\\n', '\n' ) # Unescape TSV newlines
                            .replace( '\n\n\n', '\n\n' ) # e.g., Ruth 2:intro (probable mistake)
                            .replace( '.#', '.\n\n#' ) # Fix markdown formatting mistake in Ruth 33:intro (and maybe other places)
                            .replace( '__SQUARE_BRACKETS__', '[ ]' ) # Unprotect square brackets again
                        )
                if BBB not in ('EXO','PSA','ROM','CO1'): # uW UTN Exo 4:0, Psa 4:0, Rom 16:24, 1Co 15:23 have formatting problems
                    assert '\\' not in rest, f"UTN {utnRef} {lastMarker=} {marker}='{rest}'"
                # if utnRef=='RUT_2:0': print( f"\nUTN {utnRef} {rest=}" )

                thisMarkdownHtml = ''
                openPHtml = f'''<p class="UTN{'1' if lastMarker=='pi1' else ''}">'''
                inParagraph = haveBlankLine = False
                for line in rest.split( '\n' ):
                    # print( f"  UTN {utnRef} {line=}" )
                    if line.startswith( '#### '):
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h4>{line[5:]}</h4>"
                    elif line.startswith( '####'):
                        logging.error( f"Bad markdown formatting in UTN {utnRef} line: {line=}" )
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h4>{line[4:]}</h4>"
                    elif line.startswith( '### '):
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h3>{line[4:]}</h3>"
                    elif line.startswith( '###'):
                        logging.error( f"Bad markdown formatting in UTN {utnRef} line: {line=}" )
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h3>{line[3:]}</h3>"
                    elif line.startswith( '## '):
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h2>{line[3:]}</h2>"
                    elif line.startswith( '##'):
                        logging.error( f"Bad markdown formatting in UTN {utnRef} line: {line=}" )
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h2>{line[2:]}</h2>"
                    elif line.startswith( '# '):
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h1>{line[2:]}</h1>"
                    elif line.startswith( '#'):
                        logging.error( f"Bad markdown formatting in UTN {utnRef} line: {line=}" )
                        if inParagraph:
                            thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                            inParagraph = False
                        thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}<h1>{line[1:]}</h1>"
                    elif line:
                        if not inParagraph:
                            thisMarkdownHtml = f"{thisMarkdownHtml}{NEWLINE if thisMarkdownHtml else ''}{openPHtml}"
                            inParagraph = True
                        thisMarkdownHtml = f'{thisMarkdownHtml}{line}'
                    elif inParagraph:
                        haveBlankLine = True
                if inParagraph:
                    thisMarkdownHtml = f'{thisMarkdownHtml}</p>'
                # if utnRef=='RUT_2:0': print( f"\nUTN2 {utnRef} {thisMarkdownHtml}" )
                assert checkHtml( f'UTN {utnRef}', thisMarkdownHtml, segmentOnly=True )
                tnHtml = f'''{tnHtml}{NEWLINE if tnHtml else ''}{thisMarkdownHtml}'''
                if utnRef not in ('JOS_23:0','PRO_5:0','REV_18:0'): # Has a MD formatting error
                    assert '##' not in tnHtml, f"UTN {utnRef} {tnHtml}" # Can have single hashes in valid URLS, e.g., #Top
                # if utnRef=='RUT_2:0': print( f"\nUTN3 {utnRef} {tnHtml}" )

            else: # not a marker that we were expecting
                logging.critical( f"formatUnfoldingWordTranslationNotesA ({utnRef}) has unhandled {marker=} {rest=} {lastMarker=}" )
        elif marker in ('m','q1','p','pi1'):
            assert not rest # Just ignore these markers (but they influence lastMarker)
        else:
            logging.critical( f"formatUnfoldingWordTranslationNotesB ({utnRef}) has unhandled {marker=} {rest=} {lastMarker=}" )
        lastMarker = marker

    # # Liven the TA link
    # searchStartIndex = 0
    # for _safetyCount in range( 20 ):
    #     match = taRegEx.search( tnHtml, searchStartIndex )
    #     if not match: break
    #     brIx = tnHtml.index( '<br>', match.end() )
    #     noteName = tnHtml[match.start()+24:brIx]
    #     tnHtml = f'{tnHtml[:match.start()]}<a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/03-translate.html#{noteName}">{noteName}</a>{tnHtml[brIx:]}'
    #     searchStartIndex = brIx + 4
    # else: loop_range_needs_increasing

    # # Apply markdown formatting
    # while '**' in tnHtml:
    #     tnHtml = tnHtml.replace( '**', '<b>', 1 ).replace( '**', '</b>', 1 )
    # # Add our own little bit of bolding
    # tnHtml = tnHtml.replace( 'Alternate translation:', '<b>Alternate translation</b>:' )

    if BBB not in ('LEV','HAGx','MATx'): # We have a problem at Lev 1:3, Deu 19:0, Hag 1:0, Mat 27:0 with rc:\\\tw instead of rc:\\*\tw and other errors
        assert 'rc://' not in tnHtml, f"UTN {utnRef} {tnHtml=}"
    tnHtml = tnHtml.replace( '<br>\n' , '\n<br>' ) # Make sure it follows our convention (just for tidyness and consistency)
    while '\n\n' in tnHtml: tnHtml = tnHtml.replace( '\n\n', '\n' ) # Remove useless extra newline characters (as of 2024, the UTNs are full of formatting errors and inconsistencies)
    # assert '\n\n' not in tnHtml, f"UTN {utnRef} {tnHtml=}"
    assert not tnHtml.endswith( '\n' )
    assert checkHtml( f'UTN {utnRef}', tnHtml, segmentOnly=True )
    return tnHtml
# end of Bibles.formatUnfoldingWordTranslationNotes


def loadSelectedVersesFile( fileLocation, givenName:str, givenAbbreviation:str, encoding='utf-8' ) -> Bible:
    """
    These are loaded from simple two-column TSV files
        with reference and verse text.

    Usually they only contain some small number of verses, e.g., 200 - 500 (cf NT. = 8,000, Bible = 31,000)
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadSelectedVersesFile( {fileLocation}, {givenName}, {givenAbbreviation}, {encoding} )" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadSelectedVersesFile() loading {givenAbbreviation} ({givenName}) verse entries from {fileLocation}…" )
    # assert givenAbbreviation in state.selectedVersesOnlyVersions

    verseTable = {}
    with open ( fileLocation, 'rt', encoding=encoding ) as tsv_file:
        for j,line in enumerate( tsv_file ):
            line = line.rstrip( '\n' )
            # print( f"{j}: {line}" )
            if j == 0:
                assert line == 'Reference\tVerseText'
            else:
                ref,verseText = line.split( '\t' )
                assert ref.strip() == ref
                assert verseText.strip() == verseText, f"Unexpected leading or trailing space in {givenAbbreviation} {j} {ref=} '{verseText[:6]}…{verseText[-6:]}'"
                BBB, CV = ref.split( '_' )
                C, V = CV.split( ':' )
                ourRef = (BBB,C,V)
                assert ourRef not in verseTable
                assert verseText
                # TODO: How should this really work (distinguish \\n from \\nd)???
                verseTable[ourRef] = ( verseText.replace('\\\\nd','__ND__')
                                        .replace('\\n','\n').replace('\\\\','\\') # See https://en.wikipedia.org/wiki/Tab-separated_values
                                        .replace('__ND__','\\nd') )

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    loadSelectedVersesFile() loaded {len(verseTable):,} {givenAbbreviation} verse entries from {fileLocation}." )
    return verseTable
# end of Bibles.loadSelectedVersesFile


def getVerseDataListForReference( givenRefString:str, thisBible:Bible, lastBBB:str|None=None, lastC:str|None=None ) -> tuple[str,str,InternalBibleEntryList,list[str]]:
    """
    If a reference doesn't contain a book name abbreviation, we might need to use the (optional) lastBBB parameter (and lastC for verse lists)

    Returns verseEntryList and contextList.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"getVerseDataListForReference( {givenRefString}, {thisBible.abbreviation}, {lastBBB=}, {lastC=} )" )

    # TODO: Most of this next block of code should really be in BibleOrgSys
    adjRefString = givenRefString.replace( ' (LXX)', '' )
    if '(' in adjRefString and ')' in adjRefString: # Remove xref comment
        assert adjRefString.count('(')==1 and adjRefString.count(')')==1
        adjRefString = f"{adjRefString[:adjRefString.index('(')]}{adjRefString[adjRefString.index(')')+1:]}".strip()
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{givenRefString=} {adjRefString=}")
    if thisBible.abbreviation == 'OET-RV':
        adjRefString = adjRefString.replace( 'Quoted by ', '' )
    if ' ' not in adjRefString: adjRefString = f'{lastBBB} {adjRefString}'
    refBits = adjRefString.split( ' ' )
    bookAbbreviation, refCVpart = (refBits[0],refBits[1:]) if len(refBits[0])>1 else (f'{refBits[0]} {refBits[1]}', refBits[2:])
    refBBB = getBBBFromOETBookName( bookAbbreviation )
    if refBBB is None:
        # if thisBible.abbreviation=='OET-RV' and bookAbbreviation[0]=='Y':
        #     refBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( f'J{bookAbbreviation[1:]}' ) # Convert Yoel back to Joel, etc.
        #     dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookAbbreviation=} {refCVpart=} {refBBB=}" )
        # el
        if bookAbbreviation[0].isdigit() and (':' in bookAbbreviation or '-' in bookAbbreviation): # or bookAbbreviation.isdigit() might need to be added
            # It must be another reference in the same book
            refBBB = lastBBB
            assert not refCVpart
            refCVpart = [refBits]
    if refBBB not in thisBible: # Don't force that book to be loaded
        return refBBB, '', InternalBibleEntryList(), []
    # if refBBB is None and thisBible.abbreviation=='OET-RV' and bookAbbreviation[0]=='Y':
    #     refBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( f'J{bookAbbreviation[1:]}' ) # Convert Yoel back to Joel, etc.
    #     print( f"{bookAbbreviation=} {refCVpart=} {refBBB=}" )
    assert refBBB, f"getVerseDataListForReference {givenRefString=} can't get BBB from {bookAbbreviation=} {refCVpart=}"
    refIsSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( refBBB )
    # Special case to handle xref crossing books: '1Sam 16:1–1Ki 2:11'
    if len(refCVpart) > 1: # ['16:1–1Ki', '2:11'] or ['59', 'header']
        assert len(refCVpart) == 2, f"{refCVpart=} from {givenRefString}, {thisBible.abbreviation}, {lastBBB=} {refIsSingleChapterBook=} {lastC=} {refCVpart=}"
        if refCVpart[0].endswith( '1Ki' ):
            refCVpart = [f'{refCVpart[0]} {refCVpart[1]}'] # Put it back together again (and handle properly below)
        elif refBBB=='PSA' and ':' not in refCVpart[0] and refCVpart[1] in ('header',):
            refCVpart = [f'{refCVpart[0]}:0']
    assert isinstance( refCVpart, list ) and len(refCVpart)==1 and isinstance( refCVpart[0], str ), f"{refBBB} {refCVpart=} from {givenRefString=}"
    refCVpart = refCVpart[0]

    verseEntryList, contextList = InternalBibleEntryList(), None
    try:
        if ',' in refCVpart:
            if refCVpart.count(':')==1 and refCVpart.count(',')==1 and refCVpart.count('-')==2: # Could be something like '18:13-14,19-24'
                part1, part2 = refCVpart.split( ',' )
                assert part1.count(':')==1 and part1.count('-')==1 and part2.count('-')==1
                part1a, refEndV = part1.split( '-' )
                refStartC, refStartV = part1a.split( ':' )
                assert refStartC.isdigit() and refStartV.isdigit() and refEndV.isdigit()
                verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,refEndV) )
                refStartV, refEndV = part2.split( '-' )
                assert refStartV.isdigit() and refEndV.isdigit()
                thisVerseEntryList, _contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,refEndV) )
                verseEntryList += thisVerseEntryList
            elif '-' in refCVpart: # comma plus hyphen: expect a verse range
                part1, part2 = refCVpart.split( '-' )
                assert ':' in part1
                if ':' not in part2 and ',' in part2: # Something like 19:5-9,17
                    assert ',' not in part1
                    refStartC, refStartV = part1.split( ':' )
                    assert refStartC.isdigit() and refStartV.isdigit()
                    part2Parts = part2.replace( ', ',',' ).split( ',' )
                    verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,part2Parts[-1]) )
                elif ',' in part1 and ':' not in part2 and ',' not in part2: # Something like 19:5,9-17
                    part1, part2 = refCVpart.split( ',' )
                    assert ':' in part1
                    if '-' not in part1 and '-' in part2:
                        refStartC,refStartV = part1.split( ':' )
                        assert refStartC.isdigit() and refStartV.isdigit()
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{refBBB} {refStartC}:{refStartV}")
                        verseEntryList, contextList = thisBible.getContextVerseData( (refBBB,refStartC,refStartV) )
                        refStartV2, refEndV = part2.split( '-' )
                        assert refStartV2.isdigit() and refEndV.isdigit()
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{refBBB} {refStartC}:{refStartV2}-{refEndV}")
                        thisVerseEntryList, _contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV2), (refBBB,refStartC,refEndV) )
                        verseEntryList += thisVerseEntryList
                    else: unknownCommaRef1a
                else: unknownCommaRef1
            else: # comma but no hyphen: expect a verse list of two or more verses
                if ':' in refCVpart:
                    refStartC, refVpart = refCVpart.split( ':' )
                    assert refStartC.isdigit()
                    for refStartV in refVpart.split( ',' ):
                        assert refStartV.isdigit()
                        thisVerseEntryList, thisContextList = thisBible.getContextVerseData( (refBBB,refStartC) if refStartC=='-1' else (refBBB,refStartC,refStartV) )
                        verseEntryList += thisVerseEntryList
                        if contextList is None: contextList = thisContextList # Keep the first one
                else: noColon3a
        else: # no commas
            if '-' in refCVpart: # no commas, hyphen: expect a verse range
                part1, part2 = refCVpart.split( '-' )
                if ':' not in refCVpart: # it must just be two verse numbers
                    if refIsSingleChapterBook:
                        refStartC = '1'
                    else: # not a single chapter book
                        assert refStartC.isdigit() # From previous loop
                    refStartV, refEndV = part1, part2
                    assert refStartV.isdigit() and refEndV.isdigit()
                    verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,refEndV) )
                elif ':' in part1 and ':' not in part2:
                    refStartC, refStartV = part1.split( ':' )
                    refStartV = str( getLeadingInt( refStartV ) )
                    refEndV = str( getLeadingInt( part2 ) )
                    assert refStartC.isdigit() and refStartV.isdigit() and refEndV.isdigit()
                    verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,refEndV), strict=False )
                elif ':' in part1 and ':' in part2:
                    logging.critical( f"Expected en-dash (not hyphen) in {givenRefString=} section cross-reference {refBBB} {refCVpart}" )
                    halt
                    refStartC, refStartV = part1.split( ':' )
                    refStartV = str( getLeadingInt( refStartV ) )
                    refEndC, refEndV = part2.split( ':' )
                    refEndV = str( getLeadingInt( refEndV ) )
                    assert refStartC.isdigit() and refStartV.isdigit() and refEndC.isdigit() and refEndV.isdigit()
                    verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refStartC,refEndV), strict=False )
                else: noColon1b
            elif '–' in refCVpart: # no commas, but have en-dash: expect a chapter (or rarely, a book) range
                part1, part2 = refCVpart.split( '–' )
                if ':' in part1 and ':' in part2:
                    refStartC, refStartV = part1.split( ':' )
                    assert refStartC.isdigit() and refStartV.isdigit()
                    refEndC, refEndV = part2.split( ':' )
                    assert refEndV.isdigit()
                    if refEndC.isdigit(): # Must have been a chapter range
                        verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB,refEndC,refEndV) )
                    else: # might be a book range like '1Sam 16:1–1Ki 2:11'
                        bookAbbreviation2, refEndC = refEndC.split( ' ' )
                        refBBB2 = getBBBFromOETBookName( bookAbbreviation2 )
                        # if refBBB2 is None and thisBible.abbreviation=='OET-RV' and bookAbbreviation2[0]=='Y':
                        #     refBBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( f'J{bookAbbreviation2[1:]}' ) # Convert Yoel back to Joel, etc.
                        #     dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{bookAbbreviation2=} {refCVpart=} {refBBB2=}" )
                        assert refBBB2, f"getVerseDataListForReference {givenRefString=} can't get BBB2 from {bookAbbreviation2=} {refCVpart=}"
                        verseEntryList, contextList = thisBible.getContextVerseDataRange( (refBBB,refStartC,refStartV), (refBBB2,refEndC,refEndV) )
                elif ':' not in refCVpart: # might be a chapter range, e.g., Num 22–24
                    assert not refIsSingleChapterBook
                    refStartC, refFinalC = refCVpart.split( '–' ) # en-dash
                    assert refStartC.isdigit() and refFinalC.isdigit()
                    verseEntryList, contextList = thisBible.getContextVerseData( (refBBB,refStartC) )
                    for refC in range( int(refStartC)+1, int(refFinalC)+1 ):
                        verseEntryList += thisBible.getVerseDataList( (refBBB,str(refC)) )
                else: noColon2b
            else: # no comma, hyphen or en-dash, so presumably just a single verse or else an entire chapter
                if ':' in refCVpart:
                    refStartC, refVpart = refCVpart.split( ':' )
                    assert refStartC.isdigit()
                    refStartV = str( getLeadingInt(refVpart) )
                    verseEntryList, contextList = thisBible.getContextVerseData( (refBBB,refStartC) if refStartC=='-1' else (refBBB,refStartC,refStartV) )
                elif refIsSingleChapterBook:
                    refStartC, refStartV = '1', refCVpart
                    assert refStartV.isdigit()
                    verseEntryList, contextList = thisBible.getContextVerseData( (refBBB,refStartC,refStartV) )
                else: # not a single chapter book, and has no colon, so let's assume it's an entire chapter
                    print( f"{thisBible.abbreviation} {givenRefString=} {bookAbbreviation=} {refBBB=} {refCVpart=} {refIsSingleChapterBook=} {lastBBB=} {lastC=}" )
                    refStartC = refCVpart
                    verseEntryList, contextList = thisBible.getContextVerseData( (refBBB,refStartC) )
    except KeyError: # if can't find any verseEntries
        logging.error( f"getVerseDataListForReference {givenRefString=} was unable to find {refBBB} {refStartC}:{refStartV} from {givenRefString=}" )

    return refBBB, refStartC, verseEntryList, contextList
# end of Bibles.getVerseDataListForReference


BMM_INDEX = defaultdict( set )
BMM_TEXT_CACHE = {}
def getBibleMapperMaps( level:int, BBB:str, startC:str, startV:str|None, endC:str|None, endV:str|None, referenceBible:Bible ) -> str: # html
    """
    Can be called for a verse, a chapter, or a section
    """
    global BMM_INDEX, BMM_TEXT_CACHE

    fnPrint( DEBUGGING_THIS_MODULE, f"getBibleMapperMaps( {level}, {BBB} {startC}:{startV}–{endC}:{endV} )" )

    if not BMM_INDEX:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"getBibleMapperMaps( {level}, {startC}:{startV}–{endC}:{endV} ) needs to load map index…")
        mapIndexFilepath = '../copiedBibles/maps/mapIndex.tsv'
        with open( mapIndexFilepath, 'rt', encoding='utf-8' ) as tsvFile:
            for line in tsvFile: # Five-column TSV
                if line.startswith( 'ReferenceRange' ): continue # It's the header line
                mapRef, hiResMapFilename, lowResMapFilename, supplementaryMapFilename, _optionalComment = line.rstrip( '\n' ).split( '\t' )
                mapName = hiResMapFilename.split( '_' )[0]
                mapBBB, mapCVstuff = mapRef.split( '_' )
                if mapBBB not in referenceBible:
                    continue # if we continue below, it will force that book to become loaded
                chapters:set[str] = set()
                if '–' in mapCVstuff: # enDash: it's a chapter range
                    startCVstuff, endCVstuff = mapCVstuff.split( '–' )
                    # print( f"Chapter range: {mapBBB} {startCVstuff} to {endCVstuff} = '{mapFilename}'")
                    try: iStartC, iStartV = startCVstuff.split( ':' )
                    except ValueError: iStartC, iStartV = startCVstuff, '1'
                    try: iEndC, iEndV = endCVstuff.split( ':' )
                    except ValueError: iEndC, iEndV = endCVstuff, referenceBible.getNumVerses( mapBBB, endCVstuff )
                    # print( f"   so {startC}:{startV} to {endC}:{endV}" )
                    for c in range( int(iStartC), int(iEndC)+1 ):
                        chapters.add( str(c) )
                        for v in range( int(iStartV) if c==int(iStartC) else 1, (int(iEndV) if c==int(iEndC) else referenceBible.getNumVerses( mapBBB, c ))+1 ):
                            BMM_INDEX[f'{mapBBB}_{c}:{v}'].add( (mapName,hiResMapFilename,lowResMapFilename,supplementaryMapFilename) )
                elif '-' in mapCVstuff: # hyphen: it's a verse range
                    startCVstuff, endCVstuff = mapCVstuff.split( '-' )
                    # print( f"Verse range: {mapBBB} {startCVstuff} to {endCVstuff} = '{mapFilename}'")
                    assert ':' not in endCVstuff
                    mapC, iStartV = startCVstuff.split( ':' )
                    chapters.add( mapC )
                    iEndV = endCVstuff
                    # print( f"   so {mapC}:{startV} to {mapC}:{endV}" )
                    for v in range( int(iStartV), int(iEndV)+1 ):
                        BMM_INDEX[f'{mapBBB}_{mapC}:{v}'].add( (mapName,hiResMapFilename,lowResMapFilename,supplementaryMapFilename) )
                elif ':' in mapCVstuff: # it's a single verse
                    # print( f"Single verse: {mapBBB} {mapCVstuff} = '{mapFilename}'")
                    mapC = mapCVstuff.split( ':' )[0]
                    chapters.add( mapC )
                    BMM_INDEX[mapRef].add( (mapName,hiResMapFilename,lowResMapFilename,supplementaryMapFilename) )
                else: # it's a single chapter
                    mapC = mapCVstuff
                    # print( f"Single chapter: {mapBBB} {mapC} = '{mapFilename}'")
                    chapters.add( mapC )
                    for v in range( 1, referenceBible.getNumVerses( mapBBB, mapC)+1 ):
                        BMM_INDEX[f'{mapBBB}_{mapC}:{v}'].add( (mapName,hiResMapFilename,lowResMapFilename,supplementaryMapFilename) )
                for mapC in chapters:
                    BMM_INDEX[f'{mapBBB}_{mapC}:None'].add( (mapName,hiResMapFilename,lowResMapFilename,supplementaryMapFilename) )
        # print( f"({len(BMM_INDEX)}) {BMM_INDEX.keys()=}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  getBibleMapperMaps() loaded {len(BMM_INDEX):,} verse and chapter entries.")

    # First get the range of verses that we want to scan and collect all the map filenames for that set
    mapFilenamesSet = set()
    if endC is None: # Then it's not a chapter range
        assert endV is None
        mapFilenamesSet = BMM_INDEX[f'{BBB}_{startC}:{startV}'] # Either a single verse or a single chapter
    else: # it must be a chapter range
        assert startV and endV # Neither of these can be None (can be string '0', shouldn't be integer 0)
        for c in range( int(startC), int(endC)+1 ):
            for v in range( getLeadingInt(startV) if c==int(startC) else 1, (getLeadingInt(endV) if c==int(endC) else referenceBible.getNumVerses( BBB, c ))+1 ):
                # print( f"  Chapter range {BBB} {c}:{v}")
                mapFilenamesSet.update( BMM_INDEX[f'{BBB}_{c}:{v}'] )

    if not mapFilenamesSet: # No maps for this reference / reference range
        return ''

    destinationFolderpath = TEMP_BUILD_FOLDER. joinpath( 'BMM/' )
    try: os.makedirs( destinationFolderpath )
    except FileExistsError: pass

    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"getBibleMapperMaps( {level}, {startC}:{startV}–{endC}:{endV} ) got {mapFilenamesSet=}" )
    ourHtml = ''
    for mapName,hiResFilename,loResFilename,supplementaryFilename in mapFilenamesSet:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"getBibleMapperMaps( {level}, {startC}:{startV}–{endC}:{endV} ) got {hiResFilename=}" )

        try: htmlTextSegment = BMM_TEXT_CACHE[hiResFilename]
        except KeyError: # not cached yet
            textFilepath = BIBLE_MAPPER_PATH.joinpath( f'{mapName}.htmlSegment' )
            with open( textFilepath, 'rt', encoding='utf-8' ) as txtFile:
                htmlTextSegment = txtFile.read()
            assert htmlTextSegment.startswith( '<h2 class="mapTitle">' ), f"{hiResFilename=} {textFilepath=}"
            assert checkHtml( f"Map {hiResFilename}", htmlTextSegment, segmentOnly=True )
            # TODO: Liven links in htmlSegment
            htmlTextSegment = htmlTextSegment.rstrip() # Remove trailing newlines, etc.
            BMM_TEXT_CACHE[hiResFilename] = htmlTextSegment

        if loResFilename: # Display the low-res image but link it to the hi-res one
            imageFilename = loResFilename
            imageHtml = f'''<p><a title="Click to view high-resolution image" href="{'../'*level}BMM/{hiResFilename}"><img src="{'../'*level}BMM/{imageFilename}" alt="Map" width="98%" style="max-width:1000px; display:block; margin:auto;"></a></p>\n'''
            if not destinationFolderpath.joinpath( hiResFilename ).is_file():
                # Save the hi-res image file here (the default one is saved below)
                # print( f"    getBibleMapperMaps( {level}, {BBB} {startC}:{startV}–{endC}:{endV} ): Saving hi-res {destinationFolderpath}/{hiResFilename}…" )
                # assert not destinationFolderpath.joinpath( hiResFilename ).is_file(), f"getBibleMapperMaps( {level}, {BBB} {startC}:{startV}–{endC}:{endV} ): Why does hi-res {destinationFolderpath}/{hiResFilename} already exist?"
                sourceImageFilepath = BIBLE_MAPPER_PATH.joinpath( hiResFilename )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                shutil.copy2( sourceImageFilepath, destinationFolderpath )
        else: # Only seem to have a hi-res file
            imageFilename = hiResFilename
            imageHtml = f'''<p><img src="{'../'*level}BMM/{imageFilename}" alt="Map" width="98%" style="max-width:1000px; display:block; margin:auto;"></p>\n'''
        if not destinationFolderpath.joinpath( imageFilename ).is_file():
            # Save the default image file
            # print( f"    getBibleMapperMaps( {level}, {BBB} {startC}:{startV}–{endC}:{endV} ): Saving default {destinationFolderpath}/{imageFilename}…" )
            # assert not destinationFolderpath.joinpath( imageFilename ).is_file(), f"getBibleMapperMaps( {level}, {BBB} {startC}:{startV}–{endC}:{endV} ): Why does default {destinationFolderpath}/{imageFilename} already exist?"
            sourceImageFilepath = BIBLE_MAPPER_PATH.joinpath( imageFilename )
            # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
            shutil.copy2( sourceImageFilepath, destinationFolderpath )
            if supplementaryFilename:
                supplementaryImageFilename = f'{supplementaryFilename}_high.jpg'
                supplementarySourceImageFilepath = BIBLE_MAPPER_PATH.joinpath( supplementaryImageFilename )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                shutil.copy2( supplementarySourceImageFilepath, destinationFolderpath )
        supplementaryImageHtml = ''
        if supplementaryFilename:
            supplementaryImageFilename = f'{supplementaryFilename}_high.jpg'
            supplementaryImageHtml = f'''<p><img src="{'../'*level}BMM/{supplementaryImageFilename}" alt="Map" width="98%" style="max-width:1000px; display:block; margin:auto;"></p>\n'''

        ourHtml = f'''{ourHtml}
{imageHtml}{supplementaryImageHtml}{htmlTextSegment}'''

    assert checkHtml( f'BibleMapperMap@{BBB}_{startC}:{startV}–{endC}:{endV} with {mapFilenamesSet}', ourHtml, segmentOnly=True )
    return ourHtml
# end of Bibles.getBibleMapperMaps


VERSE_DETAILS_TABLE_FILEPATH = Path( '../datasets/sentenceImportance/sentenceImportance.tsv' )
VERSE_DETAILS_TABLE = {}
def getVerseMetaInfoHtml( BBB:str, C:str, V:str ) -> str: # html
    """
    Return a short string with information from our database
        about Textual Critism, Clarity, etc., of the particular verse.
    """
    global VERSE_DETAILS_TABLE

    if not VERSE_DETAILS_TABLE:
        # We have to load it on the first call
        with open( VERSE_DETAILS_TABLE_FILEPATH, 'rt', encoding='utf-8' ) as tableFilepath:
            headerLine = tableFilepath.readline().rstrip( '\n' )
            assert headerLine == 'FGRef	Importance	TextualIssue	Clarity	Comment'
            while True:
                dataLine = tableFilepath.readline()
                if not dataLine: break # EOF presumably
                dataFields = dataLine.rstrip( '\n' ).split( '\t' )
                assert dataFields[0] not in VERSE_DETAILS_TABLE
                VERSE_DETAILS_TABLE[dataFields[0]] = (dataFields[1],dataFields[2],dataFields[3])
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loaded {len(VERSE_DETAILS_TABLE):,} sets of verse details." )

    verseDetails = ''
    ref = f'{BBB}_{C}:{V}'
    if ref in VERSE_DETAILS_TABLE:
        verseDetails = formatVerseDetailsHtml( ref )
    else: # assume the verse is divided into parts
        for part in 'abcde': # we really only expect 'a' or 'b'
            partRef = f'{ref}{part}'
            if partRef in VERSE_DETAILS_TABLE:
                verseDetails += f"{'<br>' if verseDetails else ''}{formatVerseDetailsHtml( partRef )}"

    return f'''<p class="verseDetails">{verseDetails}{'<br>' if 'Segment' in verseDetails else ' '}<small style="color:grey;">(<a title="See database" href="https://GitHub.com/Freely-Given-org/OpenBibleData/tree/main/datasets/sentenceImportance">All still tentative</a>.)</small></p>'''
# end of Bibles.getVerseMetaInfoHtml

IMPORTANCE_TABLE = { 'T':'<span style="color:grey;">trivial</span>', 'M':'<span style="color:black;">normal</span>', 'I':'<span style="color:orange;">important</span>', 'V':'<span style="color:red;">vital</span>' }
TEXTUAL_ISSUE_TABLE = { '0':'<span style="color:green;">none</span>', '1':'<span style="color:pink;">minor spelling</span>', '2':'<span style="color:orange;">small word differences</span>', '3':'<span style="color:red;">major</span>' }
CLARITY_TABLE = { 'O':'<span style="color:red;">obscure</span>', 'U':'<span style="color:orange;">unclear</span>', 'C':'<span style="color:green;">clear</span>' }
def formatVerseDetailsHtml( verseRef:str ) -> str: # html
    """
    Return a short string with information from our database
        about Textual Critism, Clarity, etc., of the particular verse or verse segment.

    NOTE: verseRef might be part of a verse, e.g., 'GEN_1:1:a'
        but it's guaranteed to be in the VERSE_DETAILS_TABLE.

    The importance values are:
        - 0=T=Trivial (like a forgotten cloak, or greetings from some person we know longer know)
        - 1=M=Medium/Normal (the great majority of sentences in the Bible)
        - 2=I=Important (specific statements that are commonly considered to be more important, and hence often memorised)
        - 3=V=Vital (specific statements that are commonly found in doctrinal statements)

    The textual issue values are:
        - 0=No issue (so most translations are working from the same Hebrew/Greek text here)
        - 1=Minor spelling or word order issues (with pretty-much no effect on meaning)
        - 2=Minor word changes (some words vary in manuscripts of different origins)
        - 3=Major differences (any translations might be expected to have a footnote her to explain textual differences in the source)

    The clarity (understandbility) values are:
        - 0=O=Obscure (we can only really guess at what was meant, and hence we might expect translations to differ widely)
        - 1=U=Unclear (we’re unsure exactly what was meant, like the parchment example above)
        - 2=C=Clear (it seems clear enough what the author or speaker meant, as far as we know)
    """
    global VERSE_DETAILS_TABLE, TEXTUAL_ISSUE_TABLE, CLARITY_TABLE, IMPORTANCE_TABLE

    importance, textualIssue, clarity = VERSE_DETAILS_TABLE[verseRef]
    result = f"{'' if textualIssue=='0' else '<b>'}Text critical issues{'' if textualIssue=='0' else '</b>'}={TEXTUAL_ISSUE_TABLE[textualIssue]} " \
             f"{'' if clarity=='C' else '<b>'}Clarity{'' if clarity=='C' else '</b>'} of original={CLARITY_TABLE[clarity]} " \
             f"{'' if importance=='M' else '<b>'}Importance to us{'' if importance=='M' else '</b>'}={IMPORTANCE_TABLE[importance]}"

    verseRefDescription = '' if verseRef[-1].isdigit() else f'Part <b>{verseRef[-1]}</b>: '
    return f"{verseRefDescription}{result}"
# end of Bibles.formatVerseDetailsHtml



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Bibles object
    preloadVersions( ['OET','OET-RV','OET-LV', 'ULT','UST'] )
# end of Bibles.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Bibles object
    preloadVersions( ['OET','OET-RV','OET-LV', 'ULT','UST'] )
# end of Bibles.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Bibles.py
