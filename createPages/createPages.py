#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createPages.py
#
# Module handling OpenBibleData createPages functions
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
Module handling createPages functions.

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
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from Bibles import preloadVersions
from createChapterPages import createOETChapterPages, createChapterPages
from createParallelPages import createParallelPages
from createInterlinearPages import createInterlinearPages
from html import makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-01-27' # by RJH
SHORT_PROGRAM_NAME = "createPages"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.07'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


class State:
    BibleVersions = ['OET','OET-RV','OET-LV',
                'ULT','UST',
                'BSB',
                'WEB','NET','LSV','T4T',
                'ASV','YLT','DBY','RV','KJB',
                'TNT','Wycliffe',
                'UHB',
                'SR-GNT','UGNT','SBL-GNT']
    BibleNames = {
                'OET': 'Open English Translation (2024)',
                'OET-RV': 'Open English Translation—Readers’ Version (2025)',
                'OET-LV': 'Open English Translation—Literal Version (2024)',
                'ULT': 'unfoldingWord Literal Text (2023)',
                'UST': 'unfoldingWord Simplified Text (2023)',
                'WEB': 'World English Bible',
                'NET': 'New English Translation',
                'T4T': 'Translation for Translators',
                'ASV': 'American Standard Version (1901)',
                'YLT': 'Youngs Literal Translation (1898)',
                'DBY': 'Darby Translation (1890)',
                'RV': 'Revised Version (1885)',
                'KJB': 'King James Bible (1769)',
                'TNT': 'Tyndale New Testament (1526)',
                'Wycliffe': 'Wycliffe Bible (1382)',
                'UHB': 'unfoldingWord Hebrew Bible (2022)',
                'SR-GNT': 'Statistic Restoration Greek New Testament (2022)',
                'UGNT': 'unfoldingWord Greek New Testament (2022)',
                'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2020???)',
                }
    BibleLocations = {
                'OET-RV': ['../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',],
                'OET-LV': ['../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_USFM/',],
                'ULT': ['../copiedBibles/English/unfoldingWord.org/ULT/',],
                'UST': ['../copiedBibles/English/unfoldingWord.org/UST/',],
                # 'BSB': ['../copiedBibles/English/OpenBible.com/BSB/',],
                'WEB': ['../copiedBibles/English/eBible.org/WEB/',],
                'NET': ['../copiedBibles/English/eBible.org/NET/',],
                'LSV': ['../copiedBibles/English/eBible.org/LSV/',],
                'T4T': ['../copiedBibles/English/eBible.org/T4T/',],
                'ASV': ['../copiedBibles/English/eBible.org/ASV/',],
                'YLT': ['../copiedBibles/English/eBible.org/YLT/',],
                'DBY': ['../copiedBibles/English/eBible.org/DBY/',],
                'RV': ['../copiedBibles/English/eBible.org/RV/',],
                'KJB': ['../copiedBibles/English/eBible.org/KJB/',],
                'UHB': ['../copiedBibles/Original/unfoldingWord.org/UHB/',],
                'SR-GNT': ['../../Forked/CNTR-SR/SR usfm/',],
                'UGNT': ['../copiedBibles/Original/unfoldingWord.org/UGNT/',],
                # 'SBL-GNT': ['../../Forked/SBLGNT/data/sblgnt/text/',],
                }
    booksToLoad = {
                'OET':['MRK',],
                'OET-RV':['MRK',],
                'OET-LV':['MRK',],
                'ULT':['FRT','MRK','TIT'],
                'UST':['MRK','TIT',], # MRK 13:13 gives \add error (24Jan2023)
                'BSB':['MRK',],
                'WEB':['MRK',],
                'NET':['MRK',],
                'LSV':['MRK',],
                'T4T':['MRK',],
                'ASV':['MRK',],
                'YLT':['MRK',],
                'DBY':['MRK',],
                'RV':['MRK',],
                'KJB':['MRK',],
                'UHB':['JNA',],
                'SR-GNT':['MRK',],
                'UGNT':['MRK',],
                'SBL-GNT':['MRK',],
                }
    assert len(BibleVersions)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad)-1 >= len(BibleLocations) # OET is a pseudo-version
    preloadedBibles = {}

state = State()


def createPages() -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, "createPages()")

    # We'll define all our settings here for now
    indexFolder = Path( '../htmlPages/' )
    cleanHTMLFolders( indexFolder )

    # Preload our various Bibles
    numLoadedVersions = preloadVersions( state )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloaded {len(state.preloadedBibles)} Bible versions: {state.preloadedBibles.keys()}" )

    # Ok, let's go create some static pages
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating pages for OET…" )
        versionFolder = indexFolder.joinpath( f'versions/OET/' )
        createOETVersionPages( versionFolder, state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV'], state )
        # createInterlinearPages( indexFolder.joinpath(f'{thisBible.abbreviation}_interlinear'), thisBible, state )
        indexHtml = '<a href="byChapter">By Chapter</a>'
        filepath = versionFolder.joinpath( 'index.html' )
        with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
            indexHtmlFile.write( makeTop(1, 'site', state) + indexHtml + makeBottom(1, 'site', state) )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    for versionAbbreviation, thisBible in state.preloadedBibles.items():
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating pages for {thisBible.abbreviation}…" )
        versionFolder = indexFolder.joinpath( f'versions/{thisBible.abbreviation}/' )
        createVersionPages( versionFolder, thisBible, state )
        createInterlinearPages( indexFolder.joinpath('interlinear'), thisBible, state )
        indexHtml = '<a href="byChapter">By Chapter</a>'
        filepath = versionFolder.joinpath( 'index.html' )
        with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
            indexHtmlFile.write( makeTop(1, 'site', state) + indexHtml + makeBottom(1, 'site', state) )
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
    # Now put them in the proper order
    state.allBBBs = []
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        if BBB in allBBBs:
            state.allBBBs.append( BBB )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Discovered {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )

    createParallelPages( indexFolder.joinpath('parallel'), state )

    createIndexPage( 0, indexFolder, state )
# end of createPages.createPages

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
# end of createPages.cleanHTMLFolders

def createOETVersionPages( folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETVersionPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    _chapterFilenames = createOETChapterPages( folder.joinpath('byChapter'), rvBible, lvBible, state )
    return True
# end of createPages.createOETVersionPages

def createVersionPages( folder:Path, thisBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVersionPages( {folder}, {thisBible.abbreviation} )")
    _chapterFilenames = createChapterPages( folder.joinpath('byChapter'), thisBible, state )
    return True
# end of createPages.createVersionPages

def createIndexPage( level, folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createIndexPage( {level}, {folder}, {state.BibleVersions} )" )
    html = makeTop( level, 'topIndex', state ) \
            .replace( '__TITLE__', 'Open Bible Data' ) \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    bodyHtml = """<h1>Open Bible Data</h1>
"""
    html += bodyHtml + makeBottom( level, 'topIndex', state )
    filepath = folder.joinpath( 'index.html' )
    checkHtml( 'TopIndex', html )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of html.createIndexPage


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createPages object
    createPages()
# end of createPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createPages object
    createPages()
# end of createPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createPages.py
