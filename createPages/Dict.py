#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dict.py
#
# Module handling OpenBibleData Dictionary functions
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
# from pathlib import Path
import os.path
import logging
import re
from xml.etree.ElementTree import ElementTree, ParseError

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
# from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

# from html import checkHtml
# from OETHandlers import findLVQuote


LAST_MODIFIED_DATE = '2023-06-14' # by RJH
SHORT_PROGRAM_NAME = "Dictionary"
PROGRAM_NAME = "OpenBibleData Dictionary handler"
PROGRAM_VERSION = '0.02'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEW_LINE = '\n'


TOBDData = {}
def loadTyndaleOpenBibleDictXML( abbrev:str, folderpath ) -> None:
    """
    """
    global TOBDData
    fnPrint( DEBUGGING_THIS_MODULE, f"loadTyndaleOpenBibleDictXML( '{abbrev}', '{folderpath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale Open Bible Dictionary from {folderpath}…" )
    TOBDData['Letters'] = {}
    TOBDData['Articles'] = {}
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXZ': # Y is ommitted
        if letter=='X': letter = 'XY'
        loadDictLetterXML( letter, folderpath )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadTyndaleOpenBibleDictXML() loaded {len(TOBDData['Letters']):,} letter sets with {len(TOBDData['Articles']):,} total articles." )
# end of Dict.loadTyndaleOpenBibleDictXML


def loadDictLetterXML( letter:str, folderpath ) -> None:
    """
    """
    global TOBDData
    fnPrint( DEBUGGING_THIS_MODULE, f"loadDictLetterXML( '{letter}', '{folderpath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary '{letter}' from {folderpath}…" )
    XML_filepath = os.path.join( folderpath, 'Articles/', f'{letter}.xml')

    dataDict = {}
    loadErrors:List[str] = []
    XMLTree = ElementTree().parse( XML_filepath )

    if XMLTree.tag == 'items':
        topLocation = f'TOBD {letter} file'
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
        assert releaseVersion == '1.6'

        TOBDData['Letters'][letter] = []
        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            name = typeName = None
            for attrib,value in element.items():
                if attrib == 'name':
                    name = value
                elif attrib == 'typename':
                    typeName = value
                    assert typeName in ('DictionaryLetter','Articles'), f"{name=} {typeName=}"
                elif attrib == 'product':
                    assert value in ('TyndaleOpenBibleDictionary','TyndaleBibleDict') # Sad inconsistency
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            assert name
            assert typeName

            if typeName == 'DictionaryLetter':
                assert name == letter
                # Here we get a list of all the articles for this letter
                #   but we don't really need it as we can make our own list later
                # for subelement in element:
                #     dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{subelement} {subelement.text=}" )
                #     assert subelement.tag == 'body'
                #     sublocation = f"{location}-{subelement.tag}"
                #     BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                #     BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '1wk8', loadErrors )
                #     BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1wk8', loadErrors )

                #     for sub2element in subelement:
                #         dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{sub2element} {sub2element.text=}" )
                #         assert sub2element.tag == 'p'
                #         sub2location = f"{location}-{sub2element.tag}"
                #         BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, '1wk8', loadErrors )
                #         BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, '1wk8', loadErrors )
                #         # Process the attributes first
                #         name = typeName = None
                #         for attrib,value in element.items():
                #             if attrib == 'name':
                #                 name = value
                #             elif attrib == 'typename':
                #                 typeName = value
                #                 assert typeName in ('DictionaryLetter','Articles'), f"{name=} {typeName=}"
                #             elif attrib == 'product':
                #                 assert value == 'TyndaleOpenBibleDictionary'
                #             else:
                #                 logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                #                 loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                #                 if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #         assert name
                #         assert typeName
            else:
                assert typeName == 'Articles'
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
                        assert subelement.tag == 'body'
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '1wk8', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                        pCount = 0
                        for bodyelement in subelement:
                            bodyLocation = f'{sublocation}-{bodyelement.tag}-{pCount}'
                            # print( f"{bodyelement} {bodyelement.text=}")
                            assert bodyelement.tag == 'p'
                            # Process the attributes first
                            pClass = None
                            for attrib,value in bodyelement.items():
                                if attrib == 'class':
                                    pClass = value
                                    assert pClass in ('h1','h2','fl','list','list-text'), f"{name} {pClass=} {bodyLocation}"
                                else:
                                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation ) \
                                                                    .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                            assert '\\' not in htmlSegment, f"{name} {pCount=} {htmlSegment=}"
                            theirClass = None
                            if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant....
                                ixClose = htmlSegment.index( '">', 10 )
                                theirClass = htmlSegment[8:ixClose]
                                htmlSegment = htmlSegment[ixClose+2:]
                            htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                            thisEntry = f"{thisEntry}{NEW_LINE if thisEntry else ''}{htmlSegment}"
                            pCount += 1
                        stateCounter += 1
                    else: halt
                if thisEntry:
                    TOBDData['Letters'][letter].append( name )
                    TOBDData['Articles'][name] = thisEntry

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    loadDictLetterXML() loaded {len(TOBDData['Letters'][letter]):,} '{letter}' dict entries." )
# end of Dict.loadDictLetterXML



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Dict object
    # loadTyndaleOpenBibleDictXML( 'TOBD', )
# end of Dict.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the Dict object
    # loadTyndaleOpenBibleDictXML( 'TOBD', )
# end of Dict.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of Dict.py
