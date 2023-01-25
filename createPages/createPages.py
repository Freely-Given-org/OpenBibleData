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
from html import createChapterPages, createOETChapterPages, createInterlinearPages, createParallelPages, makeTop, makeBottom, createIndexPage


LAST_MODIFIED_DATE = '2023-01-25' # by RJH
SHORT_PROGRAM_NAME = "createPages"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.05'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True


class State:
    BibleVersions = ['OET','OET-RV','OET-LV', 'SR-GNT', 'ASV','KJV', 'UHB','UGNT','ULT','UST']
    BibleLocations = {
                'OET-RV':['../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',],
                'OET-LV':['../../OpenEnglishTranslation--OET/translatedTexts/LiteralVersion/',],
                # 'SR-GNT':['../../Forked/CNTR-SR/SR usfm/',],
                # 'ASV':['../copiedBibles/English/eBible.org/ASV/',],
                # 'KJV':['../copiedBibles/English/eBible.org/KJV/',],
                # 'UHB':['../copiedBibles/Original/unfoldingWord.org/UHB/',],
                # 'UGNT':['../copiedBibles/Original/unfoldingWord.org/UGNT/',],
                # 'ULT':['../copiedBibles/English/unfoldingWord.org/ULT/',],
                # 'UST':['../copiedBibles/English/unfoldingWord.org/UST/',],
                }
    booksToLoad = {
                'OET':['MRK',],
                'OET-RV':['MRK',],
                'OET-LV':['MRK',],
                'SR-GNT':['MRK',],
                'UHB':['MRK',],
                'UGNT':['MRK',],
                'ULT':['FRT','MRK',],
                'UST':['FRT','TIT',], # MRK 13:13 gives \add error (24Jan2023)
                }
    preloadedBibles = {}

state = State()


def createPages() -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, "createPages()")

    # We'll define all our settings here for now
    indexFolder = Path( '../htmlPages/' )
    cleanHTMLFolders( indexFolder )

    numLoadedVersions = preloadVersions( state )

    # Ok, let's go do it
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating pages for OET…" )
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
        createInterlinearPages( indexFolder.joinpath(f'{thisBible.abbreviation}_interlinear'), thisBible, state )
        indexHtml = '<a href="byChapter">By Chapter</a>'
        filepath = versionFolder.joinpath( 'index.html' )
        with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
            indexHtmlFile.write( makeTop(1, 'site', state) + indexHtml + makeBottom(1, 'site', state) )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
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
    return True
# end of createPages.cleanHTMLFolders

def createVersionPages( folder:Path, thisBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVersionPages( {folder}, {thisBible.abbreviation} )")
    _chapterFilenames = createChapterPages( folder.joinpath('byChapter'), thisBible, state )
# end of createPages.createVersionPages

def createOETVersionPages( folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETVersionPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    _chapterFilenames = createOETChapterPages( folder.joinpath('byChapter'), rvBible, lvBible, state )
# end of createPages.createOETVersionPages


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
