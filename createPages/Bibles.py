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
import BibleOrgSys.Formats.ZefaniaXMLBible as ZefaniaXMLBible
import BibleOrgSys.Formats.CSVBible as CSVBible
import BibleOrgSys.Formats.LEBXMLBible as LEBXMLBible
import BibleOrgSys.Formats.VPLBible as VPLBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.UnknownBible import UnknownBible


LAST_MODIFIED_DATE = '2023-03-01' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.15'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


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
            thisBible = preloadVersion( versionAbbreviation, state.BibleLocations[versionAbbreviation], state )
            if isinstance(thisBible, Bible):
                state.preloadedBibles[versionAbbreviation] = thisBible
        else:
            logging.critical( f"createPages preloadVersions() has no folder location to find '{versionAbbreviation}'")
            state.BibleVersions.remove( versionAbbreviation )
    return len(state.preloadedBibles)
# end of Bibles.preloadVersions

def preloadVersion( versionAbbreviation:str, folderOrFileLocation:str, state ) -> Bible:
    """
    Loads the requested Bible into memory
        and return the Bible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( '{versionAbbreviation}', '{folderOrFileLocation}', ... )")

    # if versionAbbreviation in ('BSB',): # Single TSV .txt file
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} CSV/TSV Bible…" )
    #     thisBible = CSVBible.CSVBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='iso-8859-1' )
    #     thisBible.load()
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    if versionAbbreviation in ('SBL-GNT',): # Multiple TSV .txt file(s)
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' CSV/TSV Bible…" )
        thisBible = CSVBible.CSVBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
    # elif versionAbbreviation in ('SBL-GNT',): # .txt file(s)
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} VPL Bible…" )
    #     thisBible = VPLBible.VPLBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='utf-8' )
    #     thisBible.loadBooks() # So we can iterate through them all later
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    elif versionAbbreviation == 'LEB': # Custom XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' XML Bible…" )
        thisBible = LEBXMLBible.LEBXMLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        print( f"{thisBible.suppliedMetadata=}" )
        print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif '/TXT/' in folderOrFileLocation: # Custom VPL
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' XML Bible…" )
        thisBible = VPLBible.VPLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.load() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        print( f"{thisBible.suppliedMetadata=}" )
        print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif 'Zefania' in folderOrFileLocation: # Zefania XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' Zefania XML Bible…" )
        thisBible = ZefaniaXMLBible.ZefaniaXMLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        print( f"{thisBible.suppliedMetadata=}" )
        print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    else: # USFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading '{versionAbbreviation}' USFM Bible…" )
        thisBible = USFMBible.USFMBible( folderOrFileLocation, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
            thisBible.uWencoded = True # TODO: Shouldn't be required ???
        if 'ALL' in state.booksToLoad[versionAbbreviation]:
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them later
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
