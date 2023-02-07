#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSitePages.py
#
# Module handling OpenBibleData createSitePages functions
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
Module handling createSitePages functions.

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
import shutil
import glob
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from Bibles import preloadVersions
from createBookPages import createOETBookPages, createBookPages
from createChapterPages import createOETChapterPages, createChapterPages
from createParallelPages import createParallelPages
from createInterlinearPages import createInterlinearPages
from html import makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-02-07' # by RJH
SHORT_PROGRAM_NAME = "createSitePages"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.17'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False
ALL_PRODUCTION_BOOKS = True # Set to False for a faster test build

TEMP_BUILD_FOLDER = Path( '/tmp/OBDHtmlPages/' )
DESTINATION_FOLDER = Path( '../htmlPages/' )
DEBUG_DESTINATION_FOLDER = DESTINATION_FOLDER.joinpath( 'Test/')


OET_BOOK_LIST = ['MRK','JHN','EPH','TIT','JN3']
OET_BOOK_LIST_WITH_FRT = ['FRT','INT','MRK','JHN','EPH','TIT','JN3']
NT_BOOK_LIST_WITH_FRT = ['FRT','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL',
                'TH1','TH2','TI1','TI2','TIT','PHM','HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV']
assert len(NT_BOOK_LIST_WITH_FRT) == 27+1
OT_BOOK_LIST_WITH_FRT = ['FRT','GEN','EXO','LEV','NUM','DEU',
                'JOS','JDG','RUT','SA1','SA2','KI1','KI2','CH1','CH2',
                'EZR','NEH','EST','JOB','PSA','PRO','ECC','SNG','ISA','JER','LAM',
                'EZE','DAN','HOS','JOL','AMO','OBA','JNA', 'MIC','NAH','HAB','ZEP','HAG','ZEC','MAL']
assert len(OT_BOOK_LIST_WITH_FRT) == 39+1

EM_SPACE = ' '


class State:
    BibleVersions = ['OET','OET-RV','OET-LV', # NOTE: OET is a "pseudo-version" containing both OET-RV and OET-LV side-by-side
                'ULT','UST', 'OEB',
                'BSB','ISV',
                'WEB','NET','LSV','FBV','T4T','BBE',
                'ASV','YLT','DBY','RV','KJB','GNV',
                'TNT','WYC',
                'JPS','DRA','BRN',
                'UHB',
                'SR-GNT','UGNT','SBL-GNT']
    BibleVersionDecorations = { 'OET':('<b>','</b>'),'OET-RV':('<b>','</b>'),'OET-LV':('<b>','</b>'),
                'ULT':('',''),'UST':('',''),'OEB':('',''),
                'BSB':('',''),'ISV':('',''),
                'WEB':('',''),'NET':('',''),'LSV':('',''),'FBV':('',''),'T4T':('',''),'BBE':('',''),
                'ASV':('',''),'YLT':('',''),'DBY':('',''),'RV':('',''),'KJB':('',''),'GNV':('',''),
                'TNT':('',''),'WYC':('',''),
                'JPS':('<small>','</small>'),'DRA':('<small>','</small>'),'BRN':('<small>','</small>'),
                'UHB':('',''),
                'SR-GNT':('<b>','</b>'),'UGNT':('<small>','</small>'),'SBL-GNT':('<small>','</small>'),
                'Parallel':('<b>','</b>'), 'Interlinear':('<small>','</small>'),
                }
    BibleNames = {
                'OET': 'Open English Translation (2025)',
                'OET-RV': 'Open English Translation—Readers’ Version (2025)',
                'OET-LV': 'Open English Translation—Literal Version (2024)',
                'ULT': 'unfoldingWord Literal Text (2023)',
                'UST': 'unfoldingWord Simplified Text (2023)',
                'OEB': 'Open English Bible (in progress)',
                'BSB': 'Berean Study/Standard Bible (2020)',
                'ISV': 'International Standard Version (2020?)',
                'WEB': 'World English Bible (2020)',
                'NET': 'New English Translation (2016)',
                'LSV': 'Literal Standard Version (2020)',
                'FBV': 'Free Bible Version (2018)',
                'T4T': 'Translation for Translators (2017)',
                'BBE': 'Bible in Basic English (1965)',
                'ASV': 'American Standard Version (1901)',
                'YLT': 'Youngs Literal Translation (1898)',
                'DBY': 'Darby Translation (1890)',
                'RV': 'Revised Version (1885)',
                'KJB': 'King James Bible (1769)',
                'GNV': 'Geneva Bible (1599)',
                'TNT': 'Tyndale New Testament (1526)',
                'WYC': 'Wycliffe Bible (1382)',
                'JPS': 'Jewish Publication Society TaNaKH (1917)',
                'DRA': 'Douay-Rheims American Edition (1899)',
                'BRN' : 'Brenton Septuagint Translation (1851)',
                'UHB': 'unfoldingWord Hebrew Bible (2022)',
                'SR-GNT': 'Statistic Restoration Greek New Testament (2022)',
                'UGNT': 'unfoldingWord Greek New Testament (2022)',
                'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2020???)',
                }
    BibleLocations = {
                # NOTE: The program will still run if some of these are commented out or removed (e.g., for a faster test)
                'OET-RV': ['../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/'],
                'OET-LV': ['../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_USFM/'], # No OT here yet
                'ULT': ['../copiedBibles/English/unfoldingWord.org/ULT/'],
                'UST': ['../copiedBibles/English/unfoldingWord.org/UST/'],
                'OEB': ['../copiedBibles/English/OEB/'],
                'BSB': ['../copiedBibles/English/Berean.Bible/BSB/'],
                'WEB': ['../copiedBibles/English/eBible.org/WEB/'],
                'NET': ['../copiedBibles/English/eBible.org/NET/'],
                'LSV': ['../copiedBibles/English/eBible.org/LSV/'],
                'FBV': ['../copiedBibles/English/eBible.org/FBV/'],
                'T4T': ['../copiedBibles/English/eBible.org/T4T/'],
                'BBE': ['../copiedBibles/English/eBible.org/BBE/'],
                'ASV': ['../copiedBibles/English/eBible.org/ASV/'],
                'YLT': ['../copiedBibles/English/eBible.org/YLT/'],
                'DBY': ['../copiedBibles/English/eBible.org/DBY/'],
                'RV': ['../copiedBibles/English/eBible.org/RV/'], # with deuterocanon
                'KJB': ['../copiedBibles/English/eBible.org/KJB/'], # with deuterocanon
                'GNV': ['../copiedBibles/English/eBible.org/GNV/'],
                'TNT': ['../copiedBibles/English/eBible.org/TNT/'],
                'WYC': ['../copiedBibles/English/eBible.org/Wycliffe/'],
                'JPS': ['../copiedBibles/English/eBible.org/JPS/'],
                'DRA': ['../copiedBibles/English/eBible.org/DRA/'],
                'BRN': ['../copiedBibles/English/eBible.org/Brenton/'], # with deuterocanon and OTH,XXA,XXB,XXC,
                'UHB': ['../copiedBibles/Original/unfoldingWord.org/UHB/'],
                'SR-GNT': ['../../Forked/CNTR-SR/SR usfm/'],
                'UGNT': ['../copiedBibles/Original/unfoldingWord.org/UGNT/'],
                'SBL-GNT': ['../../Forked/SBLGNT/data/sblgnt/text/'],
                }
    booksToLoad = {
                'OET': OET_BOOK_LIST_WITH_FRT,
                'OET-RV': OET_BOOK_LIST_WITH_FRT,
                'OET-LV': OET_BOOK_LIST,
                'ULT': ['ALL'],
                'UST': ['ALL'], # MRK 13:13 gives \add error (24Jan2023)
                'OEB': ['ALL'],
                'BSB': ['ALL'],
                'WEB': ['ALL'],
                'NET': ['ALL'],
                'LSV': ['ALL'],
                'FBV': ['ALL'],
                'T4T': ['ALL'],
                'BBE': ['ALL'],
                'ASV': ['ALL'],
                'YLT': ['ALL'],
                'DBY': ['ALL'],
                'RV': ['ALL'],
                'KJB': ['ALL'],
                'GNV': ['ALL'],
                'TNT': ['ALL'],
                'WYC': ['ALL'],
                'JPS': ['ALL'],
                'DRA': ['ALL'],
                'BRN': ['ALL'],
                'UHB': ['ALL'],
                'SR-GNT': ['ALL'],
                'UGNT': ['ALL'],
                'SBL-GNT': ['ALL'],
            } if ALL_PRODUCTION_BOOKS else {
                'OET': ['FRT','MRK'],
                'OET-RV': ['FRT','MRK'],
                'OET-LV': ['MRK'],
                'ULT': ['FRT','MRK'],
                'UST': ['MRK'], # MRK 13:13 gives \add error (24Jan2023)
                'OEB': ['MRK'],
                'BSB': ['MRK'],
                'WEB': ['MRK'],
                'NET': ['MRK'],
                'LSV': ['MRK'],
                'FBV': ['MRK'],
                'T4T': ['MRK'],
                'BBE': ['MRK'],
                'ASV': ['MRK'],
                'YLT': ['MRK'],
                'DBY': ['MRK'],
                'RV': ['MRK'],
                'KJB': ['MRK'],
                'GNV': ['MRK'],
                'TNT': ['MRK'],
                'WYC': ['MRK'],
                'JPS': ['RUT'],
                'DRA': ['MRK'],
                'BRN': ['RUT'],
                'UHB': ['RUT'],
                'SR-GNT': ['MRK'],
                'UGNT': ['MRK'],
                'SBL-GNT': ['MRK'],
            }
    assert len(BibleVersionDecorations) == len(BibleVersions)+2, f"{len(BibleVersionDecorations)=} {len(BibleVersions)=}" # Adds Parallel and Interlinear
    assert len(BibleVersions)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(BibleNames)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad)-1 >= len(BibleLocations) # OET is a pseudo-version
    preloadedBibles = {}
# end of State class

state = State()


def createSitePages() -> bool:
    """
    Build all the pages in a temporary location
    """
    fnPrint( DEBUGGING_THIS_MODULE, "createSitePages()")

    # Preload our various Bibles
    numLoadedVersions = preloadVersions( state )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nPreloaded {len(state.preloadedBibles)} Bible versions: {state.preloadedBibles.keys()}" )

    try: os.makedirs( TEMP_BUILD_FOLDER )
    except FileExistsError: pass # they were already there
    cleanHTMLFolders( TEMP_BUILD_FOLDER )
    createIndexPage( 0, TEMP_BUILD_FOLDER, state )

    # Ok, let's go create some static pages
    try: os.makedirs( TEMP_BUILD_FOLDER.joinpath( 'versions/' ) )
    except FileExistsError: pass # they were already there
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating version pages for OET…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/OET/' )
        if createOETVersionPages( versionFolder, state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV'], state ):
            indexHtml = f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a>{EM_SPACE}<a href="byChapter">By Chapter</a></p>
'''
            filepath = versionFolder.joinpath( 'index.html' )
            versionName = state.BibleNames['OET']
            with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
                indexHtmlFile.write( makeTop( 2, 'site', None, state ) \
                                            .replace( '__TITLE__', f"{versionName}" ) \
                                            .replace( '__KEYWORDS__', f"Bible, OET, {versionName}" ) \
                                            .replace( f'''<a title="{versionName}" href="{'../'*2}versions/OET">OET</a>''', 'OET' ) \
                                        + indexHtml + '\n' + makeBottom( 1, 'site', state ) )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    for versionAbbreviation, thisBible in state.preloadedBibles.items():
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating version pages for {thisBible.abbreviation}…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/{thisBible.abbreviation}/' )
        if createVersionPages( versionFolder, thisBible, state ):
            createInterlinearPages( TEMP_BUILD_FOLDER.joinpath('interlinear'), thisBible, state )
            indexHtml = f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a>{EM_SPACE}<a href="byChapter">By Chapter</a></p>
'''
            filepath = versionFolder.joinpath( 'index.html' )
            versionName = state.BibleNames[thisBible.abbreviation]
            with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
                indexHtmlFile.write( makeTop( 2, 'site', None, state ) \
                                            .replace( '__TITLE__', f'{versionName}' ) \
                                            .replace( '__KEYWORDS__', f'Bible, {versionName}' ) \
                                            .replace( f'''<a title="{versionName}" href="{'../'*2}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation ) \
                                        + indexHtml + makeBottom( 1, 'site', state ) )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )

    # Find our inclusive list of books
    allBBBs = set()
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        for versionAbbreviation in state.BibleVersions:
            if versionAbbreviation == 'OET': continue # OET is a pseudo version (OET-RV plus OET-LV)
            for entry in state.booksToLoad[versionAbbreviation]:
                if entry == BBB or entry == 'ALL':
                    if BBB in state.preloadedBibles[versionAbbreviation]:
                        allBBBs.add( BBB )
    # Now put them in the proper print order
    state.allBBBs = BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( allBBBs )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDiscovered {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )

    createParallelPages( TEMP_BUILD_FOLDER.joinpath('parallel'), state )

    # Now move the site from our temporary location to overwrite the destination location
    destinationFolder = DEBUG_DESTINATION_FOLDER if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else DESTINATION_FOLDER
    cleanHTMLFolders( destinationFolder )
    # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
    count = 0
    for filepath in glob.glob( f'{TEMP_BUILD_FOLDER}/*' ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Moving {filepath} to {destinationFolder}…" )
        shutil.move( filepath, destinationFolder, copy_function=shutil.copy2)
        count += 1
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Moved {count} files and folders into {destinationFolder}." )
    # else:
    #     vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLeft files and folders in {TEMP_BUILD_FOLDER}." )
    if destinationFolder != DESTINATION_FOLDER:
        count = 0
        for filepath in glob.glob( f'{DESTINATION_FOLDER}/*.css' ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Copying {filepath}…" )
            shutil.copy2( filepath, destinationFolder )
            count += 1
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copied {count} stylesheets to {destinationFolder}." )
# end of createSitePages.createSitePages


def cleanHTMLFolders( folder:Path ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"cleanHTMLFolders( {folder} )")
    try: os.unlink( folder.joinpath( 'index.html') )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'versions/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'parallel/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'interlinear/' ) )
    except FileNotFoundError: pass
    return True
# end of createSitePages.cleanHTMLFolders


def createOETVersionPages( folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETVersionPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    createOETBookPages( folder.joinpath('byDocument'), rvBible, lvBible, state )
    createOETChapterPages( folder.joinpath('byChapter'), rvBible, lvBible, state )
    # _chapterFilenameList = createOETChapterPages( folder.joinpath('byChapter'), rvBible, lvBible, state )
    return True
# end of createSitePages.createOETVersionPages

def createVersionPages( folder:Path, thisBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVersionPages( {folder}, {thisBible.abbreviation} )")
    createBookPages( folder.joinpath('byDocument'), thisBible, state )
    createChapterPages( folder.joinpath('byChapter'), thisBible, state )
    # _chapterFilenameList = createChapterPages( folder.joinpath('byChapter'), thisBible, state )
    return True
# end of createSitePages.createVersionPages


def createIndexPage( level, folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createIndexPage( {level}, {folder}, {state.BibleVersions} )" )
    html = makeTop( level, 'topIndex', None, state ) \
            .replace( '__TITLE__', 'Open Bible Data' ) \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        html = html.replace( '<body>', '<body><p><a href="../">UP TO MAIN NON-TEST SITE</a></p>')
    bodyHtml = """<!--createIndexPage--><h1>Open Bible Data TEST</h1>
""" if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else """<!--createIndexPage--><h1>Open Bible Data</h1>
"""
    html += bodyHtml + '\n' + makeBottom( level, 'topIndex', state )
    filepath = folder.joinpath( 'index.html' )
    checkHtml( 'TopIndex', html )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of html.createIndexPage


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    createSitePages()
# end of createSitePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    createSitePages()
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