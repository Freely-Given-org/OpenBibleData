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
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import re

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
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

from html import checkHtml
from OETHandlers import findLVQuote


LAST_MODIFIED_DATE = '2023-05-03' # by RJH
SHORT_PROGRAM_NAME = "Bibles"
PROGRAM_NAME = "OpenBibleData Bibles handler"
PROGRAM_VERSION = '0.26'
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
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
    elif '/TXT/' in folderOrFileLocation: # Custom VPL
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Loading '{versionAbbreviation}' XML Bible…" )
        thisBible = VPLBible.VPLBible( folderOrFileLocation, givenName=state.BibleNames[versionAbbreviation],
                                            givenAbbreviation=versionAbbreviation, encoding='utf-8' )
        thisBible.load() # So we can iterate through them all later
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} loaded ({len(thisBible.books.keys())}) {list(thisBible.books.keys())}" )
        # print( f"{thisBible.suppliedMetadata=}" )
        # print( f"{thisBible.settingsDict=}" )
        # verseEntryList, contextList = thisBible.getContextVerseData( ('MAT', '2', '1') )
        # print( f"Mat 2:1 {verseEntryList=} {contextList=}" )
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


def preloadUwTranslationNotes( state ) -> None:
    """
    Load the unfoldingWord translation notes from the TSV files
        but masquerade them into an internal pseudo-Bible
        that can be accessed by B/C/V.
    """
    fnPrint( DEBUGGING_THIS_MODULE, "preloadUwTranslationNotes( ... )")
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading uW translation notes…" )

    state.TNBible = uWNotesBible.uWNotesBible( '../copiedBibles/English/unfoldingWord.org/TN/', givenName='TranslationNotes',
                                        givenAbbreviation='TN', encoding='utf-8' )
    state.TNBible.loadBooks() # So we can iterate through them all later

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"preloadUwTranslationNotes() loaded uW translation notes." )
# end of Bibles.preloadUwTranslationNotes


taRegEx = re.compile( 'rc://\\*/ta/man/translate/' )
markdownLinkRegex = re.compile( '\\[(.*?)\\]\\((.*?)\\)' )
def formatTranslationNotes( level:int, BBB, C:str, V:str, segmentType:str, state ) -> str: # html
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
    fnPrint( DEBUGGING_THIS_MODULE, f"formatTranslationNotes( {BBB}, {C}:{V}, {segmentType=} )")
    assert segmentType in ('parallel','interlinear')

    try:
        verseEntryList, contextList = state.TNBible.getContextVerseData( (BBB, C, V) )
    except (KeyError, TypeError): # TypeError is if None is returned
        logging.warning( f"uW TNs have no notes for {BBB} {C}:{V}")
        return ''
    # print( f"{BBB} {C}:{V} {verseEntryList=}" )

    NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
    # opposite = 'interlinear' if segmentType=='parallel' else 'parallel'
    # oppositeFolder = 'il' if segmentType=='parallel' else 'pa'

    # We tried this, but think it's better to customise our own HTML
    # tnHtml = convertUSFMMarkerListToHtml( level, 'TN', (BBB,C,V), 'notes', contextList, verseEntryList, basicOnly=True, state=state )

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
        dPrint( 'Never', DEBUGGING_THIS_MODULE, f"TN {BBB} {C}:{V} {marker}='{rest}'")
        assert rest == entry.getFullText().rstrip(), f"TN {BBB} {C}:{V} {marker}='{rest}' ft='{entry.getFullText()}'" # Just checking that we're not missing anything here
        assert marker in ('v','m','q1','p','pi1','p~',), marker # We expect a very limited subset
        if marker == 'v':
            if rest!=V and '-' not in rest:
                logging.critical( f"Why did TN {BBB} {C}:{V} get {marker}='{rest}' from {verseEntryList=}?" )
                # Doesn't seem that we usually need to display this but we will here in case something is wrong
                tnHtml = f'''{' ' if tnHtml else ''}{tnHtml}<span class="v">{V} </span>'''
            # assert rest==V or '-' in rest, f"TN {BBB} {C}:{V} {marker}='{rest}' from {verseEntryList=}"
        elif marker == 'p~': # This has the text
            if lastMarker == 'm':  # TA reference
                assert rest
                if rest.startswith( 'rc://*/ta/man/translate/' ):
                    noteName = rest[24:]
                else:
                    noteName = rest
                    logging.error( f"Missing ResourceContainer path in TA note: {BBB} {C}:{V} '{noteName}'" )
                betterNoteName = noteName.replace( 'figs-', 'figures-of-speech / ' )
                # print( f"{noteName=} {betterNoteName=}")
                noteCount += 1
                tnHtml = f'{tnHtml}<p class="TARef"><b>Note {noteCount} topic</b>: <a title="View uW TA article" href="https://Door43.org/u/unfoldingWord/en_ta/master/03-translate.html#{noteName}">{betterNoteName}</a></p>\n'
                occurrenceNumber = 1
            elif lastMarker == 'pi1': # Occurrence number
                assert rest
                if rest!='-1' and not rest.isdigit():
                    logging.critical( f"getContextVerseData ({BBB}, {C}, {V}) has unexpected {lastMarker=} {marker=} {rest=}" )
                # assert rest.isdigit() or rest=='-1', f"getContextVerseData ({BBB}, {C}, {V}) has unexpected {marker=} {rest=}" # Jhn 12:15 or 16???
                occurrenceNumber = getLeadingInt(rest) # Shouldn't be necessary but uW stuff isn't well checked/validated
            elif lastMarker == 'q1': # An original language quote
                assert rest
                if rest.startswith( 'Connecting Statement' ):
                    assert occurrenceNumber == 0
                    tnHtml = f'{tnHtml}<p class="Gram">{rest}</p>'
                else: # assume it's an original language quote
                    # if BBB!='JHN' and C!='11' and V!='45': # Jn 11:45 and Exo 1:15, etc.
                    #     assert occurrenceNumber != 0, f"TN {BBB} {C}:{V} {occurrenceNumber=} {marker}='{rest}'"
                    if occurrenceNumber == 0:
                        logging.critical( f"TN occurrenceNumber is zero with {BBB} {C}:{V} '{rest}'" )
                    lvQuoteHtml = findLVQuote( level, BBB, C, V, occurrenceNumber, rest, state ).replace(' & ',' <small>&</small> ')
                    tnHtml = f'''{tnHtml}<p class="OL">{'' if occurrenceNumber==1 else f'(Occurrence {occurrenceNumber}) '}{rest.replace(' & ',' <small>&</small> ')}</p>
<p class="Trans">{lvQuoteHtml if lvQuoteHtml else f'({transliterate_Greek(rest)})' if NT else f'({transliterate_Hebrew(rest)})'}</p>'''
            elif lastMarker == 'p': # This is the actual note (which can have markdown formatting)
                # Replace markdown links with something more readable
                searchStartIndex = 0
                for _safetyCount in range( 10 ):
                    match = markdownLinkRegex.search( rest, searchStartIndex )
                    if not match: break
                    # print( f"getContextVerseData found markdown link {BBB} {C}:{V} {match=} {match.groups()=}" )
                    newLink = match.group(1)
                    if match.group(2).startswith( '../' ) and match.group(2).endswith( '.md' ):
                        linkTarget = match.group(2)[3:-3]
                        if linkTarget.endswith('/'): linkTarget = linkTarget[:-1] # Mistake in TN Rom 2:2
                        # print( f"  Have scripture link {BBB} {C}:{V} {match.group(1)=} {linkTarget=}")
                        if linkTarget == 'front/intro':
                            pass # TODO: We're being lazy here -- where do we find a book intro?
                        elif linkTarget.count('/') == 2:
                            lUUU, lC, lV = linkTarget.split( '/' ) # Something like '1TI' '01' '77'
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
                            logging.critical( f"getContextVerseData ({BBB}, {C}, {V}) has unhandled markdown reference in '{rest}'" )
                    else:
                        logging.critical( f"getContextVerseData ({BBB}, {C}, {V}) has unhandled markdown link in '{rest}'" )
                    rest = f'{rest[:match.start()]}{newLink}{rest[match.end():]}'
                    # print( f"  {BBB} {C}:{V} with {newLink=}, now {rest=}" )
                    searchStartIndex = match.start() + len(newLink)
                else: need_to_increase_max_loop_count
                while '**' in rest:
                    rest = rest.replace( '**', '<b>', 1 ).replace( '**', '</b>', 1 )
                # Add our own little bit of bolding
                rest = rest.replace( 'Alternate translation:', '<b>Alternate translation</b>:' )
                tnHtml = f'''{tnHtml}<p class="TN{'1' if lastMarker=='pi1' else ''}">{rest}</p>\n'''
            else:
                logging.critical( f"getContextVerseDataA ({BBB}, {C}, {V}) has unhandled {marker=} {rest=} {lastMarker=}")
        elif marker in ('m','q1','p','pi1'):
            assert not rest # Just ignore these markers (but they influence lastMarker)
        else:
            logging.critical( f"getContextVerseDataB ({BBB}, {C}, {V}) has unhandled {marker=} {rest=} {lastMarker=}")
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

    checkHtml( f'TN {BBB} {C}:{V}', tnHtml, segmentOnly=True )
    return tnHtml
# end of Bibles.formatTranslationNotes


def tidyBBB( BBB:str, titleCase:Optional[bool]=False ) -> str:
    """
    Our customised version of tidyBBB
    """
    newBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=titleCase )
    if newBBB == 'JAM': return 'JAC'
    if newBBB == 'Jam': return 'Jac'
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
