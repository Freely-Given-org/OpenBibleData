#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# jsonResources.py
#
# Module handling BibleAquifer JSON resources
#
# Copyright (C) 2026 Robert Hunt
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
Module handling BibleAquifer JSON resources.



briefDemo() -> None
fullDemo() -> None


CHANGELOG:
"""
from pathlib import Path
import json
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.PTX8Bible as PTX8Bible
import BibleOrgSys.Formats.USXXMLBible as USXXMLBible
import BibleOrgSys.Formats.ZefaniaXMLBible as ZefaniaXMLBible
import BibleOrgSys.Formats.CSVBible as CSVBible
import BibleOrgSys.Formats.LEBXMLBible as LEBXMLBible
import BibleOrgSys.Formats.VPLBible as VPLBible
import BibleOrgSys.Formats.uWNotesBible as uWNotesBible
import BibleOrgSys.Formats.TyndaleNotesBible as TyndaleNotesBible
from BibleOrgSys.Bible import Bible
from bible_organisational_system import InternalBibleEntryList, getSmallLeadingInt
import bos_books_codes_py

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

# from bos_books_codes_py import english_name_to_reference_abbrev_py  # This is the PyO3/Rust module

from settings import State
from html import checkHtml
from OETHandlers import findLVQuote, getBBBFromOETBookName
from Dict import loadAndIndexUBSGreekDictJSON, loadAndIndexUBSHebrewDictJSON


LAST_MODIFIED_DATE = '2026-03-28' # by RJH
SHORT_PROGRAM_NAME = "JSONResources"
PROGRAM_NAME = "Bible Aquifer JSON resources handler"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



def load_SIL_OTN( BBB:str, state:State ) -> str | None:
    """
    Import SIL Open Translator’s Notes JSON book files as required

    Note: Not all books are available yet
    """
    try: status,indexedBookJsonData = state.SOTN[BBB]
    except AttributeError:
        state.SOTN = {}
        status = None
    except KeyError:
        status = None
    if status == 'Failed': return None # We couldn't load this book

    if status is None: # We haven't tried getting this book yet
        bookNumber = bos_books_codes_py.get_reference_number( BBB )
        # print( f"  Got {bookNumber=}" )
        if bookNumber > 66:
            state.SOTN[BBB] = ('Failed',None)
            return None
        filename = f'{bookNumber:02d}.content.json'
        # print( f"  Got {filename=}" )
        filepath = Path(state.BibleLocations['SOTN']).joinpath( filename)
        # print( f"  Got {filepath=}" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {BBB} SIL Open Translator’s Notes{' in TEST mode' if state.TEST_MODE_FLAG else ''} from {filepath}…" )
        try:
            with open( filepath, 'rt', encoding='utf-8' ) as jsonFile:
                bookJsonData = json.load( jsonFile )
            # print( f"  Have {BBB} {len(bookJsonData)=:,} JSON entries" )
        except FileNotFoundError:
            logging.critical( f"No SIL Open Translator’s Notes available for {BBB}" )
            state.SOTN[BBB] = ('Failed',None)
            return None
        indexedBookJsonData = {}
        for entryDict in bookJsonData:
            # print( f"    {entryDict=}")
            indexReference = entryDict['index_reference']
            # print( f"      {indexReference=}")
            assert len(indexReference) == 8
            bookNumber, chapterNumber, verseNumber = indexReference[:2], indexReference[2:5], indexReference[5:]
            assert int(bookNumber) == bos_books_codes_py.get_reference_number( BBB )
            c, v = int(chapterNumber), int(verseNumber)
            indexedBookJsonData[(str(c),str(v))] = entryDict
        state.SOTN[BBB] = ('Loaded',indexedBookJsonData)
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded {BBB} {len(indexedBookJsonData)=:,} JSON entries" )
        return indexedBookJsonData

    # This book was already loaded and indexed
    assert status == 'Loaded'
    return indexedBookJsonData
# end of Bibles.load_SIL_OTN


def getFormattedSILOpenTranslationNotes( level:int, BBB:str, C:str, V:str, where:str, state:State ) -> str | None:
    """
    """
    bookJson = load_SIL_OTN( BBB, state )
    if not bookJson: return None

    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"getFormattedSILOpenTranslationNotes( {level=} {BBB} {C}:{V}, {where} ... )" )
    if (C,V) == ('1','1'): dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Have {len(bookJson):,} JSON entries for {BBB}" )

    try: jsonEntry = bookJson[(C,V)]
    except KeyError: # e.g., for introductions, etc.
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"   WARNING: No SIL OTN data for {BBB} {C}:{V}" )
        return None

    # The content field seems to be already formatted as an HTML div, etc.,
    #   except that it contains unclassed <span> fields that seem pointless???
    htmlEntry = jsonEntry['content']
    # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {htmlEntry=}")
    return htmlEntry
# end of Bibles.getFormattedSILOpenTranslationNotes



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
# end of jsonResources.py
