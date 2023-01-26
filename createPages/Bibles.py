#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Bibles.py
#
# Module handling OpenBibleData Bibles functions
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
Module handling Bibles functions.

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
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.UnknownBible import UnknownBible


LAST_MODIFIED_DATE = '2023-01-27' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.07'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True


def preloadVersions( state ) -> int:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersions( {state.BibleVersions} )")
    # from html import makeTop, makeBottom

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading {state.BibleVersions}…" )

    for versionAbbreviation in state.BibleVersions[:]: # copy because we'll be deleting some entries as we go
        if versionAbbreviation == 'OET':
            # This is a combination of two translations, so nothing to load here
            assert 'OET-RV' in state.BibleVersions and 'OET-LV' in state.BibleVersions, state.BibleVersions
            continue
        if versionAbbreviation in state.BibleLocations:
            thisBible = preloadVersion( versionAbbreviation, state.BibleLocations[versionAbbreviation][0], state )
            if isinstance(thisBible, Bible):
                state.preloadedBibles[versionAbbreviation] = thisBible
        else:
            logging.critical( f"createPages preloadVersions() has no folder location to find '{versionAbbreviation}'")
            state.BibleVersions.remove( versionAbbreviation )
    return len(state.preloadedBibles)
# end of Bibles.preloadVersions

def preloadVersion( versionAbbreviation:str, folderLocation:str, state ) -> Bible:
    """
    Loads the requested Bible into memory
        and return the Bible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( {versionAbbreviation} )")
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading {versionAbbreviation}…" )

    if versionAbbreviation in ('BSB',): # txt file
        unknownBible = UnknownBible( folderLocation ) # Only creates the class
        print( f"A {unknownBible}")
        result = unknownBible.search( autoLoad=True )
        print( f"B {unknownBible} {result=}")
        if result == 'None found': halt
    else: # USFM
        thisBible = USFMBible.USFMBible( folderLocation, givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
            thisBible.uWencoded = True # TODO: Shouldn't be required ???
        if 'ALL' in state.booksToLoad[versionAbbreviation]:
            thisBible.loadBooks()
        else: # only load the books as we need them later
            thisBible.preload()
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"preloadVersion() loaded {thisBible}" )
    return thisBible
# end of Bibles.preloadVersion

# The following functions are in BibleOrgSys.InternalBible
    # getNumChapters( self, BBB:str ) -> int:
    # getNumVerses( self, BBB:str, C:str ) -> int:
    # getContextVerseData( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
    # getVerseDataList( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
    # getVerseText( self, BCVReference, fullTextFlag:bool=False ) -> str:
# The following functions are in BibleOrgSys.InternalBibleBook
    # getNumChapters( self ) -> int:
    # getNumVerses( self, C:str ) -> int:
    # getContextVerseData( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):

# # We want to add the following functions:
# def eachChapter( thisBible, BBB:str ) -> str:
#     """
#     """
#     yield '1'
#     yield '2'


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
