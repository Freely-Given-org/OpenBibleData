#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Bibles.py
#
# Module handling OpenBibleData Bibles functions
#
# Copyright (C) 2023 Robert Hunt
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

CHANGELOG:
    2023-07-19 Fix '<class="sn-text">' bug
    2023-08-07 Add allowFourChars to our customised version of tidyBBB
    2023-10-09 Fix a few more uW tN markdown link references
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Optional
# from pathlib import Path
import os.path
import logging
import re
from xml.etree.ElementTree import ElementTree, ParseError

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.ZefaniaXMLBible as ZefaniaXMLBible
import BibleOrgSys.Formats.CSVBible as CSVBible
import BibleOrgSys.Formats.LEBXMLBible as LEBXMLBible
import BibleOrgSys.Formats.VPLBible as VPLBible
import BibleOrgSys.Formats.uWNotesBible as uWNotesBible
import BibleOrgSys.Formats.TyndaleNotesBible as TyndaleNotesBible
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

from html import checkHtml
from OETHandlers import findLVQuote


LAST_MODIFIED_DATE = '2023-10-09' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.54'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEW_LINE = '\n'



def preloadVersions( state ) -> int:
    """
    Note this has a side-effect of removing unused entries from state.BibleVersions.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersions( {state.BibleVersions} )" )
    # from html import makeTop, makeBottom

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading {state.BibleVersions}…" )

    for versionAbbreviation in state.BibleVersions[:]: # copy because we'll be deleting some entries as we go
        if versionAbbreviation == 'OET':
            # This is a combination of two translations, so nothing to load here
            assert 'OET-RV' in state.BibleVersions and 'OET-LV' in state.BibleVersions, state.BibleVersions
            continue
        if versionAbbreviation in state.BibleLocations:
            thisBible = preloadVersion( versionAbbreviation, state.BibleLocations[versionAbbreviation], state )
            if isinstance(thisBible, Bible) \
            or versionAbbreviation in state.selectedVersesOnlyVersions:
                state.preloadedBibles[versionAbbreviation] = thisBible
            else:
                halt # preloadVersion failed
        else:
            logging.critical( f"createPages preloadVersions() has no folder location to find '{versionAbbreviation}'" )
            state.BibleVersions.remove( versionAbbreviation )
    return len(state.preloadedBibles)
# end of Bibles.preloadVersions

TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict = {}, {}
def preloadVersion( versionAbbreviation:str, folderOrFileLocation:str, state ) -> Bible:
    """
    Loads the requested Bible into memory
        and return the Bible object.
    """
    from Dict import loadTyndaleOpenBibleDictXML
    global TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict

    fnPrint( DEBUGGING_THIS_MODULE, f"preloadVersion( '{versionAbbreviation}', '{folderOrFileLocation}', … )" )

    # if versionAbbreviation in ('BSB',): # Single TSV .txt file
    #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading {versionAbbreviation} CSV/TSV Bible…" )
    #     thisBible = CSVBible.CSVBible( folderLocation, givenName=state.BibleNames[versionAbbreviation],
    #                                         givenAbbreviation=versionAbbreviation, encoding='iso-8859-1' )
    #     thisBible.load()
    #     print( f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {thisBible.books.keys()}" )
    if versionAbbreviation in ('BLB','SBL-GNT'): # Single (BLB) or multiple (SBL-GNT) TSV .txt file(s)
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' CSV/TSV Bible…" )
        thisBible = CSVBible.CSVBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
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
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' XML Bible…" )
        thisBible = LEBXMLBible.LEBXMLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif '/TXT/' in folderOrFileLocation: # Custom VPL
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' VPL Bible…" )
        thisBible = VPLBible.VPLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.load() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MRK', '1', '1') )
        # print( f"Mrk 1:1 {verseEntryList=} {contextList=}" )
    elif 'Zefania' in folderOrFileLocation: # Zefania XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' Zefania XML Bible…" )
        thisBible = ZefaniaXMLBible.ZefaniaXMLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif 'OET' in versionAbbreviation or 'ESFM' in folderOrFileLocation: # ESFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading '{versionAbbreviation}' ESFM Bible…" )
        thisBible = ESFMBible.ESFMBible( folderOrFileLocation, givenAbbreviation=versionAbbreviation )
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
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading uW translation notes…" )
        thisBible = uWNotesBible.uWNotesBible( state.BibleLocations[versionAbbreviation], givenName='uWTranslationNotes',
                                            givenAbbreviation='UTN', encoding='utf-8' )
        thisBible.loadBooks() # So we can iterate through them all later
    elif versionAbbreviation == 'TOSN': # We use this to also load non-Bible (non-B/C/V) stuff like Tyndale open Bible dictionary and book intros
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
    elif versionAbbreviation in state.selectedVersesOnlyVersions: # small numbers of sample verses
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' sample verses…" )
        thisBible = loadSelectedVerses( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        # NOTE: thisBible is NOT a Bible object here!!!
        # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
    else: # USFM
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Preloading '{versionAbbreviation}' USFM Bible…" )
        thisBible = USFMBible.USFMBible( folderOrFileLocation, givenAbbreviation=versionAbbreviation,
                                            encoding='utf-8' )
        if versionAbbreviation in ('ULT','UST','UHB','UGNT','SR-GNT'):
            thisBible.uWencoded = True # TODO: Shouldn't be required ???
        if 'ALL' in state.booksToLoad[versionAbbreviation]:
            thisBible.loadBooks() # So we can iterate through them all later
        else: # only load the specific books as we need them
            thisBible.preload()
            for BBB in state.booksToLoad[versionAbbreviation]:
                thisBible.loadBookIfNecessary( BBB )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  preloadVersion() loaded {len(thisBible):,} {versionAbbreviation} verses" if versionAbbreviation in state.selectedVersesOnlyVersions else f"preloadVersion() loaded {thisBible}" )
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


def loadTyndaleBookIntrosXML( abbrev:str, XML_filepath ) -> Dict[str,str]:
    """
    Load the Tyndale book intros or book intro summaries from the XML file
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadTyndaleBookIntrosXML( {abbrev}, {XML_filepath} )" )

    dataDict = {}
    loadErrors:List[str] = []
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
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        # So we want to extract this as an HTML paragraph
                        htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation ) \
				                                                .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                        assert '\\' not in htmlSegment, f"{BBB} {pCount=} {htmlSegment=}"
                        theirClass = None
                        if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant…
                            ixClose = htmlSegment.index( '">', 10 )
                            theirClass = htmlSegment[8:ixClose]
                            htmlSegment = htmlSegment[ixClose+2:]
                        assert theirClass.startswith('intro-')
                        htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                        thisEntry = f"{thisEntry}{NEW_LINE if thisEntry else ''}{htmlSegment}"
                        pCount += 1
                    stateCounter += 1
                else: halt
            if thisEntry:
                dataDict[BBB] = thisEntry

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadTyndaleBookIntrosXML() loaded {len(dataDict):,} {abbrev} book intros." )
    return dataDict
# end of Bibles.loadTyndaleBookIntrosXML


def formatTyndaleBookIntro( abbrev:str, level:int, BBB:str, segmentType:str, state ) -> str:
    """
    """
    global TyndaleBookIntrosDict, TyndaleBookIntroSummariesDict

    fnPrint( DEBUGGING_THIS_MODULE, f"formatTyndaleBookIntro( {abbrev}, {BBB}, … )" )
    assert abbrev in ('TBI','TBIS')
    assert segmentType == 'parallel'

    sourceDict = {'TBI':TyndaleBookIntrosDict, 'TBIS':TyndaleBookIntroSummariesDict}[abbrev]
    if BBB not in sourceDict:
        logging.critical( f'No Tyndale book intro for {abbrev} {BBB}' )
        return ''

    bHtml = sourceDict[BBB]
    # print( f'{abbrev} {BBB} Intro {html=}' )

    # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
    bHtml = fixTyndaleBRefs( abbrev, level, BBB, "-1", "0", bHtml, state )

    checkHtml( f'{abbrev} {BBB}', bHtml, segmentOnly=True )
    return bHtml
# end of Bibles.formatTyndaleBookIntro


def formatTyndaleNotes( abbrev:str, level:int, BBB:str, C:str, V:str, segmentType:str, state ) -> str: # html
    """
    These are mostly HTML encoded inside USFM fields.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatTyndaleNotes( {BBB}, {C}:{V}, {segmentType=} )" )
    assert abbrev in ('TOSN','TTN')
    assert segmentType in ('parallel','interlinear')

    try:
        verseEntryList, _contextList = state.preloadedBibles[abbrev].getContextVerseData( (BBB, C, V), strict=False, complete=True )
    except (KeyError, TypeError): # TypeError is if None is returned
        logging.warning( f"Tyndale have no notes for {abbrev} {BBB} {C}:{V}" )
        return ''

    nHtml = ''
    lastMarker = None
    for entry in verseEntryList:
        marker, rest = entry.getMarker(), entry.getText()
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{abbrev} {BBB} {C}:{V} {marker}='{rest}'" )
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
            # assert abbrev == 'TTN'
            nHtml = f'{nHtml}\n<ol>'
        elif marker == '¬list':
            assert not rest
            # assert abbrev == 'TTN'
            nHtml = f'{nHtml}</ol>'
        elif marker not in ('id','usfm','ide','intro','c','c#','c~','v','v='):
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{abbrev} {BBB} {C}:{V} {marker}={rest}" )
            unknown_Tyndale_notes_marker
        assert '<class=' not in nHtml, f"{marker=} {rest=} {lastMarker=} {nHtml=}"
        lastMarker = marker

    # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
    nHtml = fixTyndaleBRefs( abbrev, level, BBB, C, V, nHtml, state )

    checkHtml( f'{abbrev} {BBB} {C}:{V}', nHtml, segmentOnly=True )
    # if abbrev=='TTN' and BBB=='MRK' and C=='1' and V=='14': halt
    return nHtml
# end of Bibles.formatTyndaleNotes


def fixTyndaleBRefs( abbrev:str, level:int, BBBorArticleName:str, C:str, V:str, html:str, state ) -> str:
    """
    Most of the parameters are for info messages only
    """
    from createSitePages import ALTERNATIVE_VERSION

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
            ourNewLink = f'''{'../'*level}pa/{tBBB}/C{tC}V{tV}.htm#Top''' # we link to the parallel verse page
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
markdownLinkRegex = re.compile( '\\[(.*?)\\]\\((.*?)\\)' )
NOTE_FILENAME_DICT = {'translate':'03-translate', 'checking':'04-checking'}
def formatUnfoldingWordTranslationNotes( level:int, BBB:str, C:str, V:str, segmentType:str, state ) -> str: # html
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

    TODO: Get the English quote (ULT, OET-LV???) from the Greek words
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUnfoldingWordTranslationNotes( {BBB}, {C}:{V}, {segmentType=} )" )
    assert segmentType in ('parallel','interlinear')

    try:
        verseEntryList, contextList = state.preloadedBibles['UTN'].getContextVerseData( (BBB, C, V), strict=False, complete=True )
    except (KeyError, TypeError): # TypeError is if None is returned
        logging.warning( f"uW TNs have no notes for {BBB} {C}:{V}" )
        return ''
    # print( f"{BBB} {C}:{V} {verseEntryList=}" )

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    # opposite = 'interlinear' if segmentType=='parallel' else 'parallel'
    # oppositeFolder = 'il' if segmentType=='parallel' else 'pa'

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
            # print( f"TN {BBB} {C}:{V} ignored {marker}='{rest}'" )
            continue # not used here
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"TN {BBB} {C}:{V} {marker}='{rest}'" )
        if rest is None:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Skipped TN {BBB} {C}:{V} {marker}='{rest}'" )
            lastMarker = marker
            continue
        assert rest == entry.getFullText().rstrip(), f"TN {BBB} {C}:{V} {marker}='{rest}' ft='{entry.getFullText()}'" # Just checking that we're not missing anything here
        assert marker in ('v', 'm','q1','p','pi1', 'p~', 'im','iq1','ip','ipi'), f"Unexpected marker TN {BBB} {C}:{V} {marker}='{rest}' ({lastMarker=})" # We expect a very limited subset

        if marker == 'v':
            if rest!=V and '-' not in rest:
                logging.critical( f"Why did TN {BBB} {C}:{V} get {marker}='{rest}' from {verseEntryList=}?" )
                # Doesn't seem that we usually need to display this but we will here in case something is wrong
                tnHtml = f'''{' ' if tnHtml else ''}{tnHtml}<span class="v">{V} </span>'''
            # assert rest==V or '-' in rest, f"TN {BBB} {C}:{V} {marker}='{rest}' from {verseEntryList=}"

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
                    logging.critical( f"Missing ResourceContainer path in TA note: {BBB} {C}:{V} '{noteName}'" )
                betterNoteName = noteName.replace( 'figs-', 'figures-of-speech / ' )
                # print( f"{noteName=} {betterNoteName=}" )
                noteCount += 1
                tnHtml = f'{tnHtml}<p class="TARef"><b>Note {noteCount} topic</b>: <a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/{noteFile}.html#{noteName}">{betterNoteName}</a></p>\n'
                occurrenceNumber = 1

            elif lastMarker in ('pi1','ipi'): # Occurrence number
                assert rest
                if rest!='-1' and not rest.isdigit():
                    logging.critical( f"getContextVerseData ({BBB}, {C}, {V}) has unexpected {lastMarker=} {marker=} {rest=}" )
                # assert rest.isdigit() or rest=='-1', f"getContextVerseData ({BBB}, {C}, {V}) has unexpected {marker=} {rest=}" # Jhn 12:15 or 16???
                occurrenceNumber = getLeadingInt(rest) # Shouldn't be necessary but uW stuff isn't well checked/validated

            elif lastMarker in ('q1','iq1'): # An original language quote
                assert rest
                if rest.startswith( 'Connecting Statement' ):
                    assert occurrenceNumber == 0
                    tnHtml = f'{tnHtml}<p class="Gram">{rest}</p>'
                else: # assume it's an original language quote
                    # if BBB!='JHN' and C!='11' and V!='45': # Jn 11:45 and Exo 1:15, etc.
                    #     assert occurrenceNumber != 0, f"TN {BBB} {C}:{V} {occurrenceNumber=} {marker}='{rest}'"
                    if occurrenceNumber == 0:
                        logging.error( f"TN occurrenceNumber is zero with {BBB} {C}:{V} '{rest}'" )
                    lvQuoteHtml = findLVQuote( level, BBB, C, V, occurrenceNumber, rest, state ).replace(' & ',' <small>&</small> ')
                    tnHtml = f'''{tnHtml}<p class="OL">{'' if occurrenceNumber==1 else f'(Occurrence {occurrenceNumber}) '}{rest.replace(' & ',' <small>&</small> ')}</p>
<p class="Trans">{lvQuoteHtml if lvQuoteHtml else f'({transliterate_Greek(rest)})' if NT else f'({transliterate_Hebrew(rest)})'}</p>'''

            elif lastMarker in ('p','ip'): # This is the actual note (which can have markdown formatting)
                # Liven any TA markdown [[links]] (especially in book or chapter introductions)
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
                for _safetyCount in range( 46 ): # 45 wasn't enough for EXO 15:0
                    match = markdownLinkRegex.search( rest, searchStartIndex )
                    if not match: break
                    # print( f"{_safetyCount} getContextVerseData found TN markdown link {BBB} {C}:{V} {match=} {match.groups()=}" )
                    newLink = match.group(1)
                    if match.group(2).startswith( '../' ) and match.group(2).endswith( '.md' ):
                        # Probably something like: [13:20](../13/20.md)
                        linkTarget = match.group(2)[3:-3]
                        if linkTarget.endswith('/'): linkTarget = linkTarget[:-1] # Mistake in TN Rom 2:2
                        # print( f"  Have scripture link {BBB} {C}:{V} {match.group(1)=} {linkTarget=}" )
                        if linkTarget == 'front/intro':
                            pass # TODO: We're being lazy here -- where do we find a book intro?
                        elif linkTarget.count('/') == 2:
                            lUUU, lC, lV = linkTarget.split( '/' ) # Something like '1TI' '01' '77'
                            # Deal with book encoding issues in the uW notes
                            if lUUU == 'i1kg': lUUU = '1Ki' # UTN Mat 17:0
                            elif lUUU.lower() == '2kg': lUUU = '2Ki'
                            assert len(lUUU) == 3, f"{lUUU=} {lC=} {lV=} {linkTarget=} from {BBB} {C}:{V} '{rest}'"
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
                            except ValueError: # TN EXO 4:20 has badly formatted link
                                if lV.startswith('.'): lV = int(lV[1:])
                            newLink = f'<a href="C{lC}V{lV}.htm#Top">{match.group(1)}</a>'
                        else:
                            print( f"{_safetyCount} getContextVerseData found TN markdown link {BBB} {C}:{V} {match=} {match.groups()=}" )
                            logging.critical( f"formatUnfoldingWordTranslationNotes1 ({BBB}, {C}, {V}) has unhandled markdown reference in '{rest}'" )
                    elif match.group(2).startswith( './' ) and match.group(2).endswith( '.md' ):
                        # Probably something like: [Mark 14:22–25](./22.md)
                        linkTarget = match.group(2)[2:-3]
                        # print( f"  Have scripture link {BBB} {C}:{V} {match.group(1)=} {linkTarget=}" )
                        if linkTarget.count('/') == 0:
                            lV = linkTarget
                            newLink = f'<a href="C{C}V{lV}.htm#Top">{match.group(1)}</a>'
                        else:
                            print( f"{_safetyCount} getContextVerseData found TN markdown link {BBB} {C}:{V} {match=} {match.groups()=}" )
                            logging.critical( f"formatUnfoldingWordTranslationNotes2 ({BBB}, {C}, {V}) has unhandled markdown reference in '{rest}'" )
                    else:
                        # e.g., From Ruth 3:9: [2:20](../02/20/zu5f)
                        print( f"{_safetyCount} getContextVerseData found TN markdown link {BBB} {C}:{V} {match=} {match.groups()=}" )
                        logging.critical( f"formatUnfoldingWordTranslationNotes ({BBB}, {C}, {V}) has unhandled markdown link in '{rest}'" )
                    rest = f'{rest[:match.start()]}{newLink}{rest[match.end():]}'
                    # print( f"  {BBB} {C}:{V} with {newLink=}, now {rest=}" )
                    searchStartIndex = match.start() + len(newLink)
                else:
                    logging.critical( f"getContextVerseData found excess TN markdown links in {_safetyCount} {BBB} {C}:{V} {rest=}" )
                    need_to_increase_max_MDLink_loop_count
                if BBB not in ('HAG','MAT'): # uW Hag 1:0, Mat 27:0 have formatting problems
                    assert 'rc://' not in rest, f"TN {BBB} {C}:{V} {lastMarker=} {marker}='{rest}'"
                while '**' in rest:
                    rest = rest.replace( '**', '<b>', 1 ).replace( '**', '</b>', 1 )
                # Add our own little bit of bolding
                rest = ( rest.replace( 'Alternate translation:', '<b>Alternate translation</b>:' )
                            .replace( '{', '<span class="add">' ).replace( '}', '</span>' ) # TN uses braces {} for "add" markers, e.g., GEN 13:8, MRK 6:11
                            .replace( '\\n\\n\\n', '\\n<br>\\n' ) # e.g., Ruth 2:intro (probable mistake)
                            .replace( '\\n', '\n' ) ) # Unescape TSV newlines
                if BBB not in ('EXO','PSA','ROM','CO1'): # uW TN Exo 4:0, Psa 4:0, Rom 16:24, 1Co 15:23 have formatting problems
                    assert '\\' not in rest, f"TN {BBB} {C}:{V} {lastMarker=} {marker}='{rest}'"
                newRestLines = []
                for line in rest.split( '\n' ):
                    if line.startswith( '# '):
                        line = f'<h1>{line[2:]}</h1>'
                    elif line.startswith( '## '):
                        line = f'<h2>{line[3:]}</h2>'
                    elif line.startswith( '### '):
                        line = f'<h3>{line[4:]}</h3>'
                    elif line.startswith( '#### '):
                        line = f'<h4>{line[5:]}</h4>'
                    newRestLines.append( line )
                tnHtml = f'''{tnHtml}<p class="TN{'1' if lastMarker=='pi1' else ''}">{NEW_LINE.join(newRestLines)}</p>\n'''

            else:
                logging.critical( f"formatUnfoldingWordTranslationNotesA ({BBB}, {C}, {V}) has unhandled {marker=} {rest=} {lastMarker=}" )
        elif marker in ('m','q1','p','pi1'):
            assert not rest # Just ignore these markers (but they influence lastMarker)
        else:
            logging.critical( f"formatUnfoldingWordTranslationNotesB ({BBB}, {C}, {V}) has unhandled {marker=} {rest=} {lastMarker=}" )
        lastMarker = marker

    # if not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ): continue # Skip all except NT for now


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

    if BBB not in ('LEV','HAG','MAT'): # We have a problem at Lev 1:3, Hag 1:0, Mat 27:0
        assert 'rc://' not in tnHtml, f"TN {BBB} {C}:{V} {tnHtml=}"
    checkHtml( f'UTN {BBB} {C}:{V}', tnHtml, segmentOnly=True )
    return tnHtml
# end of Bibles.formatUnfoldingWordTranslationNotes


def loadSelectedVerses( fileLocation, givenName:str, givenAbbreviation:str, encoding='utf-8' ) -> Bible:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"loadSelectedVerses( {fileLocation}, {givenName}, {givenAbbreviation}, {encoding} )" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadSelectedVerses() loading {givenAbbreviation} ({givenName}) verse entries from {fileLocation}…" )

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
                assert verseText.strip() == verseText, f"{givenAbbreviation} {j} {ref=} '{verseText[:6]}…{verseText[-6:]}'"
                BBB, CV = ref.split( '_' )
                C, V = CV.split( ':' )
                ourRef = (BBB,C,V)
                assert ourRef not in verseTable
                assert verseText
                verseTable[ourRef] = verseText

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    loadSelectedVerses() loaded {len(verseTable):,} {givenAbbreviation} verse entries from {fileLocation}." )
    return verseTable
# end of Bibles.loadSelectedVerses


def tidyBBB( BBB:str, titleCase:Optional[bool]=False, allowFourChars:Optional[bool]=True ) -> str:
    """
    Our customised version of tidyBBB
    """
    newBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=titleCase, allowFourChars=allowFourChars )
    if newBBB == 'JAM': return 'JAC'
    if newBBB == 'Jam': return 'Jac'
    if newBBB == 'ACTS': return 'ACTs'
    return newBBB
# end of Bibles.tidyBBB



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
