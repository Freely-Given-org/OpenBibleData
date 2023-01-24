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
# import sys
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
from BibleOrgSys import UnknownBible, Bible


LAST_MODIFIED_DATE = '2023-01-23' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.03'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True


def preloadVersions( state ) -> int:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersions( {state.BibleVersions} )")
    # from html import makeTop, makeBottom

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading {state.BibleVersions}…" )

    for versionName in state.BibleVersions[:]: # copy because we'll be deleting some entries as we go
        if versionName in state.BibleLocations:
            thisBible = preloadVersion( versionName, state.BibleLocations[versionName][0] )
            if thisBible:
                state.preloadedBibles[versionName] = thisBible
        else:
            logging.critical( f"createPages preloadVersions() has no folder location to find '{versionName}'")
            state.BibleVersions.remove( versionName )
    return len(state.preloadedBibles)
# end of Bibles.preloadVersions

def preloadVersion( versionName:str, folderLocation:str ) -> Bible:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( {versionName} )")
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading {versionName}…" )

    thisBible = USFMBible.USFMBible( folderLocation, givenAbbreviation=versionName, encoding='utf-8' )
    # thisBible.preload()
    thisBible.loadBooks()
    # try: thisBible.loadBooks()
    # except AssertionError: pass # might still be able to load individual books later?
    # thisBible = UnknownBible.UnknownBible( folderLocation )
    # if 'abbreviation' not in dir(thisBible):
    #     thisBible.abbreviation = versionName
    print( thisBible )
    return thisBible
# end of Bibles.preloadVersion

def fetchChapter( thisBible, BBB:str, c:str ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"fetchChapter( {thisBible.abbreviation}, {BBB}, {c} )")
    # getNumChapters( self, BBB:str ) -> int:
    # getNumVerses( self, BBB:str, C:str ) -> int:
    # getContextVerseData( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
    # getVerseDataList( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
    # getVerseText( self, BCVReference, fullTextFlag:bool=False ) -> str:
    verseEntryList, contextList = [], []
    numVerses = thisBible.getNumVerses( BBB, c )
    for v in range(0, numVerses+1 ):
        refTuple = (BBB, str(c), str(v),)
        print( f"Finding {refTuple}")
        try:
            if not verseEntryList and not contextList:
                verseEntryList, contextList = thisBible.getContextVerseData( refTuple )
                if contextList not in (['chapters', 'c'],
                        ['chapters', 's1', 'c'], ['chapters', 'c', 's1'], # Check why we can have both
                        ['chapters', 's1', 'p', 'c']): # This is when a section crosses a chapter boundary
                    logging.critical( f"fetchChapter unexpected context: {refTuple} {contextList=}")
            else:
                verseEntryList.extend( thisBible.getVerseDataList( refTuple ) )
        except KeyError:
            logging.critical( f"No {refTuple} for {thisBible.abbreviation} (likely versification error")
        # print( 'gVT', thisBible.getVerseText( refTuple ) )
    # print( len(verseEntryList) )
    return verseEntryList, contextList
# end of Bibles.fetchChapter

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

# We want to add the following functions:
def eachChapter( thisBible, BBB:str ) -> str:
    """
    """
    yield '1'
    yield '2'


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Bibles object
    preloadVersions( ['OET-RV','OET-LV', 'ULT','UST'] )
# end of Bibles.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Bibles object
    preloadVersions( ['OET-RV','OET-LV', 'ULT','UST'] )
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
