#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dict.py
#
# Module handling OpenBibleData Bible Dictionary functions
#
# Copyright (C) 2023-2024 Robert Hunt
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
Module handling Bible Dictionary functions.

loadTyndaleOpenBibleDictXML( abbrev:str, folderpath ) -> None
loadDictLetterXML( letter:str, folderpath ) -> None
createTyndaleDictPages( level:int, outputFolderPath, state:State ) -> bool
fixTyndaleDictItemRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str
livenTyndaleTextboxRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str
livenTyndaleMapRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str
loadAndIndexUBSGreekDictJSON( abbrev:str, folderpath ) -> None
loadAndIndexUBSHebrewDictJSON( abbrev:str, folderpath ) -> None
createUBSDictionaryPages( level, outputFolderPath, state:State ) -> None
getLexReferencesHtmlList( level, lexRefs ) -> List[str]
createUBSGreekDictionaryPages( level, outputFolderPath, state:State ) -> None
createUBSHebrewDictionaryPages( level, outputFolderPath, state:State ) -> None
briefDemo() -> None
fullDemo() -> None

CHANGELOG:
    2024-01-30 Load UBS Dictionary of Greek New Testament
    2024-02-22 Load UBS Dictionary of Biblical Hebrew
"""
from gettext import gettext as _
from typing import List
import os.path
import logging
from xml.etree.ElementTree import ElementTree
import json

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from settings import State, TEST_MODE, ALTERNATIVE_VERSION
from html import makeTop, makeBottom, checkHtml
from OETHandlers import getOETTidyBBB


LAST_MODIFIED_DATE = '2024-05-28' # by RJH
SHORT_PROGRAM_NAME = "Dictionary"
PROGRAM_NAME = "OpenBibleData Dictionary handler"
PROGRAM_VERSION = '0.45'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEWLINE = '\n'


TOBDData = {}
def loadTyndaleOpenBibleDictXML( abbrev:str, folderpath ) -> None:
    """
    """
    global TOBDData
    fnPrint( DEBUGGING_THIS_MODULE, f"loadTyndaleOpenBibleDictXML( '{abbrev}', '{folderpath}', ... )")
    TOBDData['Letters'], TOBDData['Articles'], TOBDData['Textboxes'], TOBDData['Maps'] = {}, {}, {}, {}

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading Tyndale Open Bible Dictionary from {folderpath}…" )
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXZ': # Y is ommitted
        if letter=='X': letter = 'XY'
        loadDictLetterXML( letter, folderpath )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadTyndaleOpenBibleDictXML() loaded {len(TOBDData['Letters']):,} letter sets with {len(TOBDData['Articles']):,} total articles." )


    # Now load the introduction
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary introduction from {folderpath}…" )
    XML_filepath = os.path.join( folderpath, '_INTRODUCTION.xml' )

    loadErrors:List[str] = []
    XMLTree = ElementTree().parse( XML_filepath )

    if XMLTree.tag == 'items':
        topLocation = f'TOBD intro'
        BibleOrgSysGlobals.checkXMLNoText( XMLTree, topLocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( XMLTree, topLocation, '1wk8', loadErrors )
        # Process the attributes first
        for attrib,value in XMLTree.items():
            if attrib == 'release':
                releaseVersion = value
            else:
                logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
        assert releaseVersion == '1.6'

        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoText( element, location, '1wk8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            for attrib,value in element.items():
                if attrib == 'typename':
                    assert value == 'FrontMatter'
                elif attrib == 'name':
                    assert value == 'Introduction'
                elif attrib == 'product':
                    assert value == 'TyndaleOpenBibleDictionary'
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
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
                    partCount = 0
                    for bodyelement in subelement:
                        bodyLocation = f'{sublocation}-{bodyelement.tag}-{partCount}'
                        BibleOrgSysGlobals.checkXMLNoTail( bodyelement, bodyLocation, '1wk8', loadErrors )
                        # print( f"{bodyelement} {bodyelement.text=}")
                        assert bodyelement.tag in ('p','table'), f'{title=} {partCount=} {bodyelement.tag=} {bodyLocation=}'
                        if bodyelement.tag == 'p':
                            # Process the attributes first
                            pClass = None
                            for attrib,value in bodyelement.items():
                                if attrib == 'class':
                                    pClass = value
                                    assert pClass in ('h1','h2','h3', 'fl',
                                                        'list','list-space',
                                                        'contributor'), f"Intro {pClass=} {bodyLocation}"
                                else:
                                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                                                                    # .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                            assert '\\' not in htmlSegment, f"Intro {partCount=} {htmlSegment=}"
                            theirClass = 'next'
                            if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant....
                                ixClose = htmlSegment.index( '">', 10 )
                                theirClass = htmlSegment[8:ixClose]
                                htmlSegment = htmlSegment[ixClose+2:]
                            htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                            thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                        elif bodyelement.tag == 'table':
                            BibleOrgSysGlobals.checkXMLNoAttributes( bodyelement, bodyLocation, '1wk8', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoText( bodyelement, bodyLocation, '1wk8', loadErrors )
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                                                                    # .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                            assert '\\' not in htmlSegment, f"Intro {partCount=} {htmlSegment=}"
                            htmlSegment = f'<table>{htmlSegment}</table>'
                            thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                        else: halt
                        partCount += 1
                    stateCounter += 1
                else: halt
            # print( f"Intro {thisEntry=}" )
            assert 'Intro' not in TOBDData
            TOBDData['Intro'] = thisEntry


    # Now load the textboxes
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary textboxes from {folderpath}…" )
    XML_filepath = os.path.join( folderpath, 'Textboxes/', 'Textboxes.xml' )

    loadErrors:List[str] = []
    XMLTree = ElementTree().parse( XML_filepath )

    if XMLTree.tag == 'items':
        topLocation = f'TOBD textboxes'
        BibleOrgSysGlobals.checkXMLNoText( XMLTree, topLocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( XMLTree, topLocation, '1wk8', loadErrors )
        # Process the attributes first
        for attrib,value in XMLTree.items():
            if attrib == 'release':
                releaseVersion = value
            else:
                logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
        assert releaseVersion == '1.6'

        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoText( element, location, '1wk8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            name = None
            for attrib,value in element.items():
                if attrib == 'typename':
                    assert value == 'Textbox'
                elif attrib == 'product':
                    assert value == 'TyndaleOpenBibleDictionary'
                elif attrib == 'name':
                    name = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
            assert name

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
                    partCount = 0
                    for bodyelement in subelement:
                        bodyLocation = f'{sublocation}-{bodyelement.tag}-{partCount}'
                        BibleOrgSysGlobals.checkXMLNoTail( bodyelement, bodyLocation, '1wk8', loadErrors )
                        # print( f"{bodyelement} {bodyelement.text=}")
                        assert bodyelement.tag == 'p', f'{title=} {partCount=} {bodyelement.tag=} {bodyLocation=}'
                        if bodyelement.tag == 'p':
                            # Process the attributes first
                            pClass = None
                            for attrib,value in bodyelement.items():
                                if attrib == 'class':
                                    pClass = value
                                    assert pClass in ('h1','box-h2','box-h2-poetic', 'sp','fl',
                                                        'box-first','box-extract',
                                                        'poetry-1','poetry-1-sp','poetry-2',
                                                        'list'), f"Textbox {pClass=} {bodyLocation}"
                                else:
                                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                                                                    # .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                            assert '\\' not in htmlSegment, f"Textbox {partCount=} {htmlSegment=}"
                            theirClass = 'next'
                            if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant....
                                ixClose = htmlSegment.index( '">', 10 )
                                theirClass = htmlSegment[8:ixClose]
                                htmlSegment = htmlSegment[ixClose+2:]
                            htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                            thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                        else: halt
                        partCount += 1
                    stateCounter += 1
                else: halt
            # print( f"Textbox {thisEntry=}" )
            assert name not in TOBDData['Textboxes']
            TOBDData['Textboxes'][name] = thisEntry
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded Tyndale Open Bible Dictionary {len(TOBDData['Textboxes']):,} textboxes from {folderpath}." )

    # Now load the maps
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary maps from {folderpath}…" )
    XML_filepath = os.path.join( folderpath, 'Maps/', 'Maps.xml' )

    loadErrors:List[str] = []
    XMLTree = ElementTree().parse( XML_filepath )

    if XMLTree.tag == 'items':
        topLocation = f'TOBD maps'
        BibleOrgSysGlobals.checkXMLNoText( XMLTree, topLocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( XMLTree, topLocation, '1wk8', loadErrors )
        # Process the attributes first
        for attrib,value in XMLTree.items():
            if attrib == 'release':
                releaseVersion = value
            else:
                logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
        assert releaseVersion == '1.6'

        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoText( element, location, '1wk8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            name = None
            for attrib,value in element.items():
                if attrib == 'typename':
                    assert value == 'Map'
                elif attrib == 'product':
                    assert value == 'TyndaleOpenBibleDictionary'
                elif attrib == 'name':
                    name = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
            assert name

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
                    partCount = 0
                    for bodyelement in subelement:
                        bodyLocation = f'{sublocation}-{bodyelement.tag}-{partCount}'
                        BibleOrgSysGlobals.checkXMLNoTail( bodyelement, bodyLocation, '1wk8', loadErrors )
                        # print( f"{bodyelement} {bodyelement.text=}")
                        assert bodyelement.tag == 'p', f'{title=} {partCount=} {bodyelement.tag=} {bodyLocation=}'
                        if bodyelement.tag == 'p':
                            # Process the attributes first
                            pClass = None
                            for attrib,value in bodyelement.items():
                                if attrib == 'class':
                                    pClass = value
                                    assert pClass in ('artfile','caption-head','caption-text'), f"Textbox {pClass=} {bodyLocation}"
                                else:
                                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                                                                    # .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                            assert '\\' not in htmlSegment, f"Map {partCount=} {htmlSegment=}"
                            theirClass = 'next'
                            if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant....
                                ixClose = htmlSegment.index( '">', 10 )
                                theirClass = htmlSegment[8:ixClose]
                                htmlSegment = htmlSegment[ixClose+2:]
                            htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                            thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                        else: halt
                        partCount += 1
                    stateCounter += 1
                else: halt
            # print( f"Map {thisEntry=}" )
            assert name not in TOBDData['Maps']
            TOBDData['Maps'][name] = thisEntry
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded Tyndale Open Bible Dictionary {len(TOBDData['Maps']):,} maps from {folderpath}." )
# end of Dict.loadTyndaleOpenBibleDictXML


def loadDictLetterXML( letter:str, folderpath ) -> None:
    """
    """
    global TOBDData
    fnPrint( DEBUGGING_THIS_MODULE, f"loadDictLetterXML( '{letter}', '{folderpath}', ... )")

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary '{letter}' from {folderpath}…" )
    XML_filepath = os.path.join( folderpath, 'Articles/', f'{letter}.xml')

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
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
        assert releaseVersion == '1.6'

        assert letter not in TOBDData['Letters']
        TOBDData['Letters'][letter] = []
        for element in XMLTree:
            location = f"{topLocation}-{element.tag}"
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
            assert element.tag == 'item'
            # Process the attributes first
            name = typeName = None
            for attrib,value in element.items():
                if attrib == 'typename':
                    typeName = value
                    assert typeName in ('DictionaryLetter','Article'), f"{name=} {typeName=}"
                elif attrib == 'name':
                    name = value
                elif attrib == 'product':
                    assert value in ('TyndaleOpenBibleDictionary','TyndaleBibleDict') # Sad inconsistency
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
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
                #                 if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                #         assert name
                #         assert typeName
            else:
                assert typeName == 'Article'
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
                        partCount = 0
                        for bodyelement in subelement:
                            bodyLocation = f'{sublocation}-{bodyelement.tag}-{partCount}'
                            BibleOrgSysGlobals.checkXMLNoTail( bodyelement, bodyLocation, '1wk8', loadErrors )
                            # print( f"{bodyelement} {bodyelement.text=}")
                            assert bodyelement.tag in ('p','include_items'), f'{title=} {partCount=} {bodyelement.tag=} {bodyLocation=}'
                            if bodyelement.tag == 'p':
                                # Process the attributes first
                                pClass = None
                                for attrib,value in bodyelement.items():
                                    if attrib == 'class':
                                        pClass = value
                                        assert pClass in ('h1','h2','h3','h4','h5', 'sp',
                                                          'fl','list','list-text','list-space','list-text-fl','list-0','list-1',
                                                          'h2-preview','preview-list-first','preview-list','preview-list-1','preview-text',
                                                          'h2-list',
                                                          'extract','extract-fl-space','extract-fl',
                                                          'poetry-1-sp','poetry-1','poetry-2','poetry-3'), f"{name} {pClass=} {bodyLocation}"
                                    else:
                                        logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                                # So we want to extract this as an HTML paragraph
                                htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                                                                        # .replace( '<a href="  \?', '<a href="?') # Fix encoding mistake in 1 Tim
                                assert '\\' not in htmlSegment, f"{name} {partCount=} {htmlSegment=}"
                                theirClass = 'next'
                                if htmlSegment.startswith( '<class="'): # e.g., <class="theme-list">The new covenant....
                                    ixClose = htmlSegment.index( '">', 10 )
                                    theirClass = htmlSegment[8:ixClose]
                                    htmlSegment = htmlSegment[ixClose+2:]
                                htmlSegment = f'<p class="{theirClass}">{htmlSegment}</p>'
                                thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                            elif bodyelement.tag == 'include_items':
                                BibleOrgSysGlobals.checkXMLNoText( bodyelement, bodyLocation, '1wk8', loadErrors )
                                BibleOrgSysGlobals.checkXMLNoSubelements( bodyelement, bodyLocation, '1wk8', loadErrors )
                                # Process the attributes first
                                iiSrc = iiName = None
                                for attrib,value in bodyelement.items():
                                    if attrib == 'src':
                                        iiSrc = value
                                        assert iiSrc in ('../Textboxes/Textboxes.xml','../Maps/Maps.xml','../Pictures/Pictures.xml','../Charts/Charts.xml'), f"{title=} {iiSrc=}"
                                    elif attrib == 'name':
                                        iiName = value # Name of a textbox item entry
                                    else:
                                        logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.errorOnXMLWarning: halt
                                if 'Textbox' in iiSrc:
                                    assert iiSrc == '../Textboxes/Textboxes.xml'
                                    # So we want to save this as an XML paragraph to insert textbox later
                                    htmlSegment = f'<include_items src="{iiSrc}" name="{iiName}"/>'
                                    thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                                elif 'Map' in iiSrc:
                                    assert iiSrc == '../Maps/Maps.xml'
                                    # So we want to save this as an XML paragraph to insert map later
                                    htmlSegment = f'<include_items src="{iiSrc}" name="{iiName}"/>'
                                    thisEntry = f"{thisEntry}{NEWLINE if thisEntry else ''}{htmlSegment}"
                                else: # They don't supply pictures or charts so might as well discard those here for now
                                    pass
                            else: halt
                            partCount += 1
                        stateCounter += 1
                    else: halt
                if thisEntry:
                    TOBDData['Letters'][letter].append( (name,title) )
                    assert name not in TOBDData['Articles']
                    TOBDData['Articles'][name] = thisEntry

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    loadDictLetterXML() loaded {len(TOBDData['Letters'][letter]):,} '{letter}' dict entries." )
# end of Dict.loadDictLetterXML


def createTyndaleDictPages( level:int, outputFolderPath, state:State ) -> bool:
    """
    """
    from Bibles import fixTyndaleBRefs

    fnPrint( DEBUGGING_THIS_MODULE, f"createTyndaleDictPages( '{level}', '{outputFolderPath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nCreating Tyndale Open Bible Dict pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    indexLink = '<a title="Go up to main index" href="index.htm#__ID__">Index</a>'
    introLink = '<a title="Go to dict introduction" href="intro.htm#__ID__">Intro</a>'
    TOBD_detailsLink = f'''<a title="Show details" href="{'../'*(level)}AllDetails.htm#TOBD">©</a>'''
    UBS_detailsLink = f'''<a title="Show details" href="{'../'*(level)}UBS/details.htm">©</a>'''

    letterLinkList = [f'''<a title="Go to index page for letter '{l}'" href="index_{l}.htm#Top">{l}</a>''' for l in TOBDData['Letters']]
    lettersParagraph = f'''<p class="dctLtrs">{' '.join(letterLinkList)}</p>'''

    # Make dictionary article pages
    articleList = [a for a in TOBDData['Articles']]
    for j,(articleLinkName,article) in enumerate( TOBDData['Articles'].items() ):
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Making article page for '{articleLinkName}'…" )
        leftLink = f'''<a title="Go to previous article" href="{articleList[j-1]}.htm#__ID__">←</a> ''' if j>0 else ''
        rightLink = f''' <a title="Go to next article" href="{articleList[j+1]}.htm#__ID__">→</a>''' if j<len(articleList)-1 else ''
        navLinks = f'<p id="__ID__" class="dNav">{introLink} {leftLink}{indexLink}{rightLink} {TOBD_detailsLink}</p>'

        article = livenTyndaleTextboxRefs( 'TOBD', level, articleLinkName, article, state )
        article = livenTyndaleMapRefs( 'TOBD', level, articleLinkName, article, state )
        # The textboxes must be inserted before the next two lines so the brefs in the textboxes get fixed
        article = fixTyndaleBRefs( 'TOBD', level, articleLinkName, '', '', article, state ) # Liven their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
        article = fixTyndaleDictItemRefs( 'TOBD', level, articleLinkName, article, state )

        article = article.replace( 'kjv', '<small>KJB</small>' ).replace( 'nlt', '<small>NLT</small>' )

        filename = f'{articleLinkName}.htm'
        filepath = outputFolderPath.joinpath( filename )
        top = makeTop( level, None, 'dictionaryEntry', None, state ) \
                .replace( '__TITLE__', f"Dictionary Article{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, dictionary, {articleLinkName}' )
# <h2 id="Top">{articleLinkName}</h2>
        articleHtml = f'''{top}
{lettersParagraph}
<h1>{'TEST ' if TEST_MODE else ''}Tyndale Open Bible Dictionary</h1>
{navLinks.replace('__ID__','Top')}
{article}
{makeBottom( level, 'dictionaryEntry', state )}'''
        checkHtml( 'DictionaryArticle', articleHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as articleHtmlFile:
            articleHtmlFile.write( articleHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(articleHtml):,} characters written to {filepath}" )

    # Make letter index pages
    letterList = [l for l in TOBDData['Letters']]
    for j,(letter,articleList) in enumerate( TOBDData['Letters'].items() ):
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Making letter summary page for '{letter}'…" )
        leftLink = f'''<a title="Go to previous letter" href="index_{letterList[j-1]}.htm#__ID__">←</a> ''' if j>0 else ''
        rightLink = f''' <a title="Go to next letter" href="index_{letterList[j+1]}.htm#__ID__">→</a>''' if j<len(letterList)-1 else ''
        navLinks = f'<p id="__ID__" class="dNav">{leftLink}{indexLink} {introLink}{rightLink} {TOBD_detailsLink}</p>'
        articleLinkHtml = ''
        for articleLinkName,articleDisplayName in articleList:
            articleLink = f'<a title="Go to article" href="{articleLinkName}.htm#Top">{articleDisplayName}</a>'
            firstLetters = articleLinkName[:2]
            if articleLinkHtml:
                articleLinkHtml = f'''{articleLinkHtml}{' ' if firstLetters==lastFirstLetters else f'{NEWLINE}<br>'}{articleLink}'''
            else: # first entry
                articleLinkHtml = articleLink
            lastFirstLetters = firstLetters
        filename = f'index_{letter}.htm'
        filepath = outputFolderPath.joinpath( filename )
        top = makeTop( level, None, 'dictionaryLetterIndex', None, state ) \
                .replace( '__TITLE__', f"Dictionary Index Letter{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', 'Bible, dictionary' )
        letterIndexHtml = f'''{top}
{lettersParagraph}
<h1>{'TEST ' if TEST_MODE else ''}Tyndale Open Bible Dictionary</h1>
{navLinks.replace('__ID__','Top')}
<h2 id="Top">Index for dictionary letter '{letter}'</h2>
{articleLinkHtml}
{makeBottom( level, 'dictionaryLetterIndex', state )}'''
        checkHtml( 'DictionaryLetterIndex', letterIndexHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as letterIndexHtmlFile:
            letterIndexHtmlFile.write( letterIndexHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(letterIndexHtml):,} characters written to {filepath}" )

    # Make intro page
    filename = 'intro.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'dictionaryIntro', None, state ) \
            .replace( '__TITLE__', f"Dictionary Introduction{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, dictionary, introduction' )
    introHtml = f'''{top}<p class="note"><b>Note</b>: The Tyndale Open Bible Dictionary is included on this site because it contains a wealth of useful information,
even though it was originally designed to supplement the <i>New Living Translation</i>, not our <em>Open English Translation</em>.</p>
<h1 id="Top">Tyndale Open Bible Dictionary <small>{TOBD_detailsLink}</small></h1>
{TOBDData['Intro']}
{makeBottom( level, 'dictionaryIntro', state )}'''
    checkHtml( 'DictionaryIntro', introHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as introHtmlFile:
        introHtmlFile.write( introHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(introHtml):,} characters written to {filepath}" )

    # Make overall index
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'dictionaryMainIndex', None, state ) \
            .replace( '__TITLE__', f"Dictionary Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, dictionary' )
# <p class="dNav"><a id="Go to dict intro" href="intro.htm#Top">Introduction</a></p>
    indexHtml = f'''{top}
<h1 id="Top">Tyndale Open Bible Dictionary <small>{TOBD_detailsLink}</small></h1>
<p class="note">This is a comprehensive Bible dictionary with articles for each Bible ‘book’ as well as for significant people and places and terms. (Read the <a id="Go to dict intro" href="intro.htm#Top">full introduction</a> for more details.)</p>
<p class="note">Note that some of the comments refer specifically to the ‘New Living Translation’ (which we don’t have permission to display on this site), but many of the articles are generally applicable, even to <b>OET</b> issues.</p>
<h2>Index of dictionary letters</h2>
{lettersParagraph}
<h1>UBS Dictionary of New Testament Greek <small>{UBS_detailsLink}</small></h1>
<p class="note">This isn’t fully formatted and implemented yet, but something might be visible <a href="{'../'*(level)}UBS/Grk/">here</a>.</p>
<h1>UBS Dictionary of Biblical Hebrew <small>{UBS_detailsLink}</small></h1>
<p class="note">This isn’t fully formatted and implemented yet, but something might be visible <a href="{'../'*(level)}UBS/Heb/">here</a>.</p>
{makeBottom( level, 'dictionaryMainIndex', state )}'''
    checkHtml( 'DictionaryIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Created {len(TOBDData['Articles']):,} Tyndale Bible Dict articles pages." )
    return True
# end of Dict.createTyndaleDictPages


def fixTyndaleDictItemRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str:
    """
    Most of the parameters are for info messages only

    Livens links between articles
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"fixTyndaleDictItemRefs( {abbrev}, {level}, {articleLinkName} {html}, ... )")

    # Fix their links like '<a href="?item=MarriageMarriageCustoms_Article_TyndaleOpenBibleDictionary">Marriage, Marriage Customs</a>'
    searchStartIndex = 0
    for _safetyCount in range( 25 ): # 19 was too few
        ixStart = html.find( 'href="?item=', searchStartIndex )
        if ixStart == -1: # none/no more found
            break
        ixCloseQuote = html.find( '"', ixStart+12 )
        assert ixCloseQuote != -1
        tyndaleLinkPart = html[ixStart+12:ixCloseQuote]
        # print( f"{abbrev} {BBB} {C}:{V} {tyndaleLinkPart=}" )
        assert tyndaleLinkPart.endswith( '_TyndaleOpenBibleDictionary' ), f"{abbrev} {level} '{articleLinkName}' {tyndaleLinkPart=}"
        tyndaleLinkPart = tyndaleLinkPart[:-27]
        # print( f"{tyndaleLinkPart=}" )
        assert tyndaleLinkPart.count('_') == 1
        assert tyndaleLinkPart.endswith( '_Article' ) or tyndaleLinkPart.endswith( '_Textbox' ) or tyndaleLinkPart.endswith( '_Map' ), f"{abbrev} {level} '{articleLinkName}' {tyndaleLinkPart=}"
        tyndaleName, tyndaleType = tyndaleLinkPart.split( '_' )
        # print( f"{tyndaleName=} {tyndaleType=}" )
        ourNewLink = f"{tyndaleName}.htm#Top"
        # print( f"   {ourNewLink=}" )
        html = f'''{html[:ixStart+6]}{ourNewLink}{html[ixCloseQuote:]}'''
        searchStartIndex = ixStart + 10
    else: need_to_increase_Tyndale_item_loop_counter

    return html
# end of Bibles.fixTyndaleDictItemRefs



def livenTyndaleTextboxRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str:
    """
    Most of the parameters are for info messages only

    Convert
        htmlSegment = f'<include_items src="{iiSrc}" name="{iiName}"/>'
    to
        htmlSegment = f'''<div class="Textbox>{TOBDData['Textboxes'][iiName]}</div><!--end of Textbox-->'''
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenTyndaleTextboxRefs( {abbrev}, {level}, {articleLinkName} {html}, ... )")

    # Fails on AntilegomenaTheBooksThatDidnTMakeIt
    tbSearchStartIndex = 0
    for _safetyCount1 in range( 3 ): # 2 was too few
        ixStart = html.find( '<include_items src="../Textboxes/Textboxes.xml" name="', tbSearchStartIndex )
        if ixStart == -1: # none/no more found
            break
        ixCloseQuote = html.find( '"', ixStart+54 )
        assert ixCloseQuote != -1
        textboxName = html[ixStart+54:ixCloseQuote].replace( 'AbrahamSBosom', 'AbrahamsBosom' )
        # print( f"  {articleLinkName=} {textboxName=}" )
        try: textboxData = TOBDData['Textboxes'][textboxName]
        except KeyError: # there's a systematic error in the data
            fixed = False
            # Find a S that should be lowercase, e.g., AbrahamSBosom
            sSearchStartIndex = 1
            for _safetyCount2 in range( 3 ):
                ixS = textboxName.find( 'S', sSearchStartIndex )
                if ixS == -1: break
                if textboxName[ixS+1].isupper():
                    textboxName = f'{textboxName[:ixS]}s{textboxName[ixS+1:]}' # Convert things like AbrahamSBosom to a lowercase s
                    textboxData = TOBDData['Textboxes'][textboxName]
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Fixed S {articleLinkName=} {textboxName=}")
                    fixed = True
                    break
                sSearchStartIndex = ixS + 1
            else: sSearch_needs_more_loops
            if not fixed:
                # Find a T that should be lowercase, e.g., DidnTMake
                tSearchStartIndex = 1
                for _safetyCount3 in range( 4 ):
                    ixT = textboxName.find( 'T', tSearchStartIndex )
                    if ixT == -1: break
                    if textboxName[ixT+1].isupper():
                        textboxName = f'{textboxName[:ixT]}t{textboxName[ixT+1:]}' # Convert things like AntilegomenaTheBooksThatDidnTMakeIt to lowercase t
                        textboxData = TOBDData['Textboxes'][textboxName]
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Fixed T {articleLinkName=} {textboxName=}")
                        fixed = True
                    tSearchStartIndex = ixT + 1
                else: tSearch_needs_more_loops
            if not fixed:
                logging.critical( f"livenTyndaleTextboxRefs failed to find a textbox for {articleLinkName} '{textboxName}'" )
                tbSearchStartIndex = ixStart + 50
                continue
        ourNewLink = f'''<div class="Textbox">{textboxData}</div><!--end of Textbox-->'''
        # print( f"   {ourNewLink=}" )
        html = f'''{html[:ixStart]}{ourNewLink}{html[ixCloseQuote+3:]}'''
        tbSearchStartIndex = ixStart + 10
    else: need_to_increase_Tyndale_textbox_loop_counter

    return html
# end of Bibles.livenTyndaleTextboxRefs


def livenTyndaleMapRefs( abbrev:str, level:int, articleLinkName:str, html:str, state:State ) -> str:
    """
    Most of the parameters are for info messages only

    Convert
        htmlSegment = f'<include_items src="{iiSrc}" name="{iiName}"/>'
    to
        htmlSegment = f'''<div class="Textbox>{TOBDData['Textboxes'][iiName]}</div><!--end of Textbox-->'''
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenTyndaleMapRefs( {abbrev}, {level}, {articleLinkName} {html}, ... )")

    searchStartIndex = 0
    for _safetyCount in range( 5 ): # 4 was too few
        ixStart = html.find( '<include_items src="../Maps/Maps.xml" name="', searchStartIndex )
        if ixStart == -1: # none/no more found
            break
        ixCloseQuote = html.find( '"', ixStart+44 )
        assert ixCloseQuote != -1
        mapName = html[ixStart+44:ixCloseQuote].replace( 'TheDeathofMoses', 'TheDeathOfMoses' ) \
                    .replace( 'TheSevenChurchesofRevelation', 'TheSevenChurchesOfRevelation' ).replace( 'UroftheChaldeans', 'UrOfTheChaldeans' )
        # print( f"{articleLinkName=} {mapName=}" )
        mapData = TOBDData['Maps'][mapName].replace( 'src="artfiles/', 'src="' ).replace( '.pdf"', '.pdf-1.png"' ).replace( '></img>', '/>' )
        # print( f"{articleLinkName} {mapData=}" )
        ourNewLink = f'''<div class="Mapbox">{mapData}</div><!--end of Mapbox-->'''
        # print( f"   {ourNewLink=}" )
        html = f'''{html[:ixStart]}{ourNewLink}{html[ixCloseQuote+3:]}'''
        searchStartIndex = ixStart + 10
    else: need_to_increase_Tyndale_map_loop_counter

    return html
# end of Bibles.livenTyndaleMapRefs


USB_GNT_DATA = []
USB_GNT_ID_INDEX, USB_GNT_LEMMA_INDEX = {}, {}
def loadAndIndexUBSGreekDictJSON( abbrev:str, folderpath ) -> None:
    """
    """
    global USB_GNT_DATA, USB_GNT_ID_INDEX, USB_GNT_LEMMA_INDEX
    # print( f"loadAndIndexUBSGreekDictJSON( '{abbrev}', {type(folderpath)} {folderpath=}, ... )" )
    fnPrint( DEBUGGING_THIS_MODULE, f"loadAndIndexUBSGreekDictJSON( '{abbrev}', '{folderpath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading UBS Dictionary of the Greek New Testament from {folderpath}…" )
    filepath = os.path.join( folderpath, 'UBSGreekNTDic-v1.0-en.JSON')
    # print( f"{filepath=}" )
    with open( filepath, 'rt', encoding='utf-8' ) as json_file:
        tempList = json.load(json_file)

    # Something like
    # UGD entry 0/5507: tempList[0]={'MainId': '000001000000000', 'Lemma': 'α', 'Version': '0', 'HasAramaic': False, 'InLXX': False, 'AlphaPos': 'α', 'StrongCodes': [], 'Authors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '000001001000000', 'PartsOfSpeech': ['noun-name, n.'], 'Inflections': [{'Lemma': 'α', 'BaseFormIndex': 1, 'Form': '', 'Realizations': [], 'Comments': [{'LanguageCode': 'en', 'Meaning': 'indeclinable'}, {'LanguageCode': 'zhT', 'Meaning': '無語尾變化'}]}], 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': None, 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '000001001001000', 'LEXIsBiblicalTerm': 'Y', 'LEXEntryCode': '60.46', 'LEXIndent': 0, 'LEXDomains': ['Number'], 'LEXSubDomains': ['First, Second, Third, Etc. [Ordinals]'], 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2021-05-24 13:06:09', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': 'first in a series involving time, space, or set', 'Glosses': ['first'], 'Comments': 'Occurring only in titles of NT writings: πρὸς Κορινθίους α ‘First Letter to the Corinthians’; Ἰωάννου α ‘First Epistle of John.’'}], 'LEXIllustrations': None, 'LEXReferences': ['04600100000000', '05200100000000', '05400100000000', '06000100000000', '06200100000000'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': None, 'CONMeanings': None}]}]}
    # UGD entry 1/5507: tempList[1]={'MainId': '000002000000000', 'Lemma': 'Ἀαρών', 'Version': '0', 'HasAramaic': False, 'InLXX': False, 'AlphaPos': 'α', 'StrongCodes': ['G0002'], 'Authors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '000002001000000', 'PartsOfSpeech': ['noun-name, m.'], 'Inflections': [{'Lemma': 'Ἀαρών', 'BaseFormIndex': 1, 'Form': '', 'Realizations': [], 'Comments': [{'LanguageCode': 'en', 'Meaning': 'indeclinable'}, {'LanguageCode': 'zhT', 'Meaning': '無語尾變化'}]}], 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': None, 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '000002001001000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '93.1', 'LEXIndent': 0, 'LEXDomains': ['Names of Persons and Places'], 'LEXSubDomains': ['Persons'], 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2021-05-24 13:08:56', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': 'the elder brother of Moses and Israel’s first high priest', 'Glosses': ['Aaron'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['04200100500044', '04400704000006', '05800500400030', '05800701100062', '05800900400044'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': None, 'CONMeanings': None}]}]}
    # UGD entry -1/5507: tempList[-1]={'MainId': '005507000000000', 'Lemma': 'ὠφέλιμος', 'Version': '0', 'HasAramaic': False, 'InLXX': False, 'AlphaPos': 'ω', 'StrongCodes': ['G5624'], 'Authors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '005507001000000', 'PartsOfSpeech': ['adjc.'], 'Inflections': [{'Lemma': 'ὠφέλιμος', 'BaseFormIndex': 1, 'Form': '', 'Realizations': ['-ον'], 'Comments': []}], 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': [{'Word': 'ὠφελέω', 'Meanings': []}], 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '005507001001000', 'LEXIsBiblicalTerm': 'Y', 'LEXEntryCode': '65.40', 'LEXIndent': 0, 'LEXDomains': ['Value'], 'LEXSubDomains': ['Advantageous, Not Advantageous'], 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2022-06-13 14:12:01', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': 'pertaining to a benefit to be derived from some ob ject, event, or state', 'Glosses': ['advantage', 'benefit', 'beneficial'], 'Comments': 'In a number of languages the equivalent of ‘benefit’ or ‘beneficial’ is often ‘that which helps.’ Accordingly, in {S:05400400800028} one may render ἡ γὰρ σωματικὴ γυμνασία πρὸς ὀλίγον ἐστὶν ὠφέλιμος as ‘physical exercise helps to a small extent’ or ‘if one exercises one’s body, that helps a little.’'}], 'LEXIllustrations': None, 'LEXReferences': ['05400400800016', '05400400800028', '05500301600010', '05600300800044'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': None, 'CONMeanings': None}]}]}
    # print( f"{abbrev} entry 0/{len(tempList)}: {tempList[0]=}")
    # print( f"{abbrev} entry 1/{len(tempList)}: {tempList[1]=}")
    # print( f"{abbrev} entry -1/{len(tempList)}: {tempList[-1]=}")

    # Index and remove Chinese comments at the same time
    USB_GNT_DATA = []
    for n,entry in enumerate( tempList ):
        # print( f"\n\n{n}: {entry}")
        assert entry['MainId'] not in USB_GNT_ID_INDEX
        assert entry['Lemma'] not in USB_GNT_LEMMA_INDEX
        USB_GNT_ID_INDEX[entry['MainId']] = USB_GNT_LEMMA_INDEX['Lemma'] = n
        for b, baseForm in enumerate( entry['BaseForms'] ):
            # print( f"  {b}: {type(baseForm)} {baseForm=}" )
            if baseForm['Inflections']:
                for i, inflection in enumerate( baseForm['Inflections']):
                    # print( f"    {i}: {type(inflection)} {inflection=}" )
                    for c, comment in enumerate( inflection['Comments'][:]): # Use a copy coz we're going to delete stuff
                        # print( f"      {c}: {type(comment)} {comment=}" )
                        if comment['LanguageCode'] == 'zhT':
                            # print( f"        Deleting {c}: {type(comment)} {comment=}" )
                            inflection['Comments'].pop( c )
                            # print( f"  {n}: {entry}")
        USB_GNT_DATA.append( entry )
    del tempList

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadAndIndexUBSGreekDictJSON() loaded {len(USB_GNT_DATA):,} GNT Dictionary entries." )
# end of Bibles.loadAndIndexUBSGreekDictJSON


USB_HEB_DOMAIN_DATA, USB_HEB_DATA = [], []
USB_HEB_ID_INDEX, USB_HEB_LEMMA_INDEX = {}, {}
def loadAndIndexUBSHebrewDictJSON( abbrev:str, folderpath ) -> None:
    """
    """
    global USB_HEB_DOMAIN_DATA, USB_HEB_DATA, USB_HEB_ID_INDEX, USB_HEB_LEMMA_INDEX
    # print( f"loadAndIndexUBSHebrewDictJSON( '{abbrev}', {type(folderpath)} {folderpath=}, ... )" )
    fnPrint( DEBUGGING_THIS_MODULE, f"loadAndIndexUBSHebrewDictJSON( '{abbrev}', '{folderpath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Preloading UBS Dictionary of the Biblical Hebrew from {folderpath}…" )
    filepath = os.path.join( folderpath, 'UBSHebrewDicLexicalDomains-v0.9.1-en.JSON')
    # print( f"{filepath=}" )
    with open( filepath, 'rt', encoding='utf-8' ) as json_file:
        USB_HEB_DOMAIN_DATA = json.load(json_file)

    # Something like
    # UHD domain entry 0/417: USB_HEB_DOMAIN_DATA[0]={'SemanticDomainLocalizations': [{'LanguageCode': 'en', 'Label': 'Objects', 'Description': 'All animate and inanimate entities, both natural and supernatural', 'Opposite': '', 'Comment': ''}], 'Level': 1, 'Prototype': '', 'Reference': '', 'Code': '001', 'HasSubDomains': True, 'Entries': []}
    # UHD domain entry 1/417: USB_HEB_DOMAIN_DATA[1]={'SemanticDomainLocalizations': [{'LanguageCode': 'en', 'Label': 'Beings', 'Description': 'All living beings, whether natural or supernatural', 'Opposite': '', 'Comment': ''}], 'Level': 2, 'Prototype': '', 'Reference': '', 'Code': '001001', 'HasSubDomains': True, 'Entries': []}
    # UHD domain entry -1/417: USB_HEB_DOMAIN_DATA[-1]={'SemanticDomainLocalizations': [{'LanguageCode': 'en', 'Label': 'Timers', 'Description': '', 'Opposite': '', 'Comment': ''}], 'Level': 2, 'Prototype': '', 'Reference': '', 'Code': '004009', 'HasSubDomains': False, 'Entries': []}
    # print( f"{abbrev} domain entry 0/{len(USB_HEB_DOMAIN_DATA)}: {USB_HEB_DOMAIN_DATA[0]=}")
    # print( f"{abbrev} domain entry 1/{len(USB_HEB_DOMAIN_DATA)}: {USB_HEB_DOMAIN_DATA[1]=}")
    # print( f"{abbrev} domain entry -1/{len(USB_HEB_DOMAIN_DATA)}: {USB_HEB_DOMAIN_DATA[-1]=}")
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadAndIndexUBSHebrewDictJSON() loaded {len(USB_HEB_DOMAIN_DATA):,} HEB Domain entries." )

    filepath = os.path.join( folderpath, 'UBSHebrewDic-v0.9.1-en.JSON')
    # print( f"{filepath=}" )
    with open( filepath, 'rt', encoding='utf-8' ) as json_file:
        tempList = json.load(json_file)

    # Something like
    # UHD entry 0/7223: tempList[0]={'MainId': '000001000000000', 'Lemma': 'אֵב', 'Version': '5', 'HasAramaic': True, 'InLXX': False, 'AlphaPos': 'א', 'StrongCodes': ['H0003', 'A0004'], 'Authors': ['Reinier de Blois'], 'Contributors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '000001001000000', 'PartsOfSpeech': ['nsm'], 'Inflections': None, 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': [{'Word': '', 'Meanings': []}], 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '000001001001000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '001003', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Vegetation'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2020-05-18 16:00:24', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= part of a plant or tree that is typically surrounded by brightly colored petals and will eventually develop into a fruit', 'Glosses': ['blossom', 'flower'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['02200601100016'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': [{'DomainCode': '125', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Plant'}], 'CONMeanings': None}, {'LEXID': '000001001002000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '002001001057', 'DomainSource': 'Vegetation', 'DomainSourceCode': '001003', 'Domain': 'Stage'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': ['בְּאֵב'], 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2017-03-19 12:46:16', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= state in which a plant or tree has developed blossoms', 'Glosses': ['blossom'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['01800801200006'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': [{'DomainCode': '125', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Plant'}], 'CONMeanings': None}, {'LEXID': '000001001003000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '001004003004', 'DomainSource': 'Vegetation', 'DomainSourceCode': '001003', 'Domain': 'Fruits'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2020-05-18 16:00:24', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= part of a plant or tree that carries the seed and is often edible', 'Glosses': ['fruit'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['02700400900008', '02700401100032', '02700401800010'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': [{'DomainCode': '125', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Plant'}], 'CONMeanings': None}]}]}
    # UHD entry 1/7223: tempList[1]={'MainId': '000002000000000', 'Lemma': 'אַב', 'Version': '5', 'HasAramaic': True, 'InLXX': False, 'AlphaPos': 'א', 'StrongCodes': ['A0002'], 'Authors': ['Reinier de Blois'], 'Contributors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '000002001000000', 'PartsOfSpeech': ['nsm'], 'Inflections': None, 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': None, 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '000002001001000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '001001002003012', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Relatives'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2017-12-31 13:15:24', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= direct male progenitor; ► who normally provides protection, care, instruction, and discipline; ≈ is usually regarded with respect and associated with wisdom, security, and comfort', 'Glosses': ['father'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['02700500200032', '02700501100026', '02700501100054', '02700501100068', '02700501300052', '02700501800034'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': [{'DomainCode': '062', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Family'}, {'DomainCode': '121', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Parenthood'}, {'DomainCode': '129', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Posterity'}], 'CONMeanings': None}, {'LEXID': '000002001002000', 'LEXIsBiblicalTerm': 'M', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '001001002003012', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Relatives'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2017-12-31 13:15:24', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= indirect male progenitor', 'Glosses': ['forefather', 'ancestor'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['01500401500014', '01500501200010', '02700202300006'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': [{'DomainCode': '129', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Posterity'}], 'CONMeanings': None}]}]}
    # UHD entry -1/7223: tempList[-1]={'MainId': '007965000000000', 'Lemma': 'תַּתְּנַי', 'Version': '4', 'HasAramaic': True, 'InLXX': False, 'AlphaPos': 'ת', 'StrongCodes': ['A8674'], 'Authors': ['Reinier de Blois'], 'Contributors': [], 'AlternateLemmas': [], 'MainLinks': [], 'Notes': [], 'Localizations': None, 'Dates': None, 'ContributorNote': '', 'BaseForms': [{'BaseFormID': '007965001000000', 'PartsOfSpeech': ['np'], 'Inflections': None, 'Constructs': None, 'Etymologies': None, 'RelatedLemmas': None, 'RelatedNames': None, 'MeaningsOfName': None, 'CrossReferences': None, 'BaseFormLinks': [], 'LEXMeanings': [{'LEXID': '007965001001000', 'LEXIsBiblicalTerm': 'Y', 'LEXEntryCode': '', 'LEXIndent': 0, 'LEXDomains': [{'DomainCode': '003001007', 'DomainSource': None, 'DomainSourceCode': None, 'Domain': 'Names of People'}], 'LEXSubDomains': None, 'LEXForms': None, 'LEXValencies': None, 'LEXCollocations': None, 'LEXSynonyms': None, 'LEXAntonyms': None, 'LEXCrossReferences': None, 'LEXSenses': [{'LanguageCode': 'en', 'LastEdited': '2020-09-18 13:26:15', 'LastEditedBy': '', 'DefinitionLong': '', 'DefinitionShort': '= man; ► governor of the province west of the {L:Euphrates<SDBH:פְּרָת>} during the Persian empire', 'Glosses': ['Tattenai'], 'Comments': ''}], 'LEXIllustrations': None, 'LEXReferences': ['01500500300010', '01500500600010', '01500600600004', '01500601300004'], 'LEXLinks': None, 'LEXImages': None, 'LEXVideos': [], 'LEXCoordinates': None, 'LEXCoreDomains': None, 'CONMeanings': None}]}]}
    # print( f"{abbrev} entry 0/{len(tempList)}: {tempList[0]=}")
    # print( f"{abbrev} entry 1/{len(tempList)}: {tempList[1]=}")
    # print( f"{abbrev} entry -1/{len(tempList)}: {tempList[-1]=}")

    # Index and remove Chinese comments at the same time
    USB_HEB_DATA = []
    for n,entry in enumerate( tempList ):
        # print( f"\n\n{n}: {entry}")
        assert entry['MainId'] not in USB_HEB_ID_INDEX
        assert entry['Lemma'] not in USB_HEB_LEMMA_INDEX
        USB_HEB_ID_INDEX[entry['MainId']] = USB_HEB_LEMMA_INDEX['Lemma'] = n
        for b, baseForm in enumerate( entry['BaseForms'] ):
            # print( f"  {b}: {type(baseForm)} {baseForm=}" )
            if baseForm['Inflections']:
                for i, inflection in enumerate( baseForm['Inflections']):
                    # print( f"    {i}: {type(inflection)} {inflection=}" )
                    for c, comment in enumerate( inflection['Comments'][:]): # Use a copy coz we're going to delete stuff
                        # print( f"      {c}: {type(comment)} {comment=}" )
                        if comment['LanguageCode'] == 'zhT':
                            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"        Deleting {c}: {type(comment)} {comment=}" )
                            inflection['Comments'].pop( c )
                            # print( f"  {n}: {entry}")
        USB_HEB_DATA.append( entry )
    del tempList

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadAndIndexUBSHebrewDictJSON() loaded {len(USB_HEB_DATA):,} HEB Dictionary entries." )
# end of Bibles.loadAndIndexUBSHebrewDictJSON


def createUBSDictionaryPages( level, outputFolderPath, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createUBSDictionaryPages( {level}, '{outputFolderPath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nCreating UBS Dict pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    createUBSHebrewDictionaryPages( level+1, outputFolderPath.joinpath( 'Heb/'), state )
    createUBSGreekDictionaryPages ( level+1, outputFolderPath.joinpath( 'Grk/'), state )
# end of Bibles.createUBSDictionaryPages


BOOK_NUM_TABLE = { '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', 
                  '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '001':'GEN', '066':'REV', }
def getLexReferencesHtmlList( level, lexRefs ) -> List[str]:
    """
    """
    lexRefsHtmlList = []
    for fullLexRef in lexRefs:
        # print( f"{fullLexRef=}")
        lexRef, lexRefExtra = fullLexRef[0:14], fullLexRef[14:]
        assert len(lexRef) == 14
        assert lexRef.isdigit()
        bkNum, C, V, last5Digits = int(lexRef[0:3]), int(lexRef[3:6]), int(lexRef[6:9]), lexRef[9:]
        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bkNum )
        ourTidyBBB = getOETTidyBBB( BBB )
        # TODO: We're not yet using last5Digits, e.g., '00046', or lexRefExtra, e.g., '{N:001}'
        lexLink = f'''<a href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">{ourTidyBBB} {C}:{V}</a>'''
        lexRefsHtmlList.append( f'''{lexLink}''' )

    return lexRefsHtmlList
# end of Bibles.getLexReferencesHtmlList


def createUBSGreekDictionaryPages( level, outputFolderPath, state:State ) -> None:
    """
    """
    global USB_GNT_DATA, USB_GNT_ID_INDEX, USB_GNT_LEMMA_INDEX
    fnPrint( DEBUGGING_THIS_MODULE, f"createUBSGreekDictionaryPages( {level}, '{outputFolderPath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Creating UBS Greek Bible Dict pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    indexLink = '<a title="Go up to main index" href="index.htm#__ID__">Index</a>'
    introLink = '<a title="Go to dict introduction" href="intro.htm#__ID__">Intro</a>'
    detailsLink = f'''<a title="Show details" href="{'../'*(level)}AllDetails.htm#UBS">©</a>'''

    # Make dictionary article pages
    lemmaList = [a['Lemma'] for a in USB_GNT_DATA]
    for e,entry in enumerate( USB_GNT_DATA ): # each entry is a dict
        lemma = entry['Lemma']
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Making article page for '{lemma}'…" )
        leftLink = f'''<a title="Go to previous article" href="{lemmaList[e-1]}.htm#__ID__">←</a> ''' if e>0 else ''
        rightLink = f''' <a title="Go to next article" href="{lemmaList[e+1]}.htm#__ID__">→</a>''' if e<len(lemmaList)-1 else ''
        navLinks = f'<p id="__ID__" class="dNav">{introLink} {leftLink}{indexLink}{rightLink} {detailsLink}</p>'

        entryHtml = f'<h2>{lemma}</h2>'
        for key,data in entry.items():
            if data is None or data=='' or data==[]: continue # Don't display blank stuff
            if key == 'Lemma': continue # Already used that
            if key == 'BaseForms':
                entryHtml = f'''{entryHtml}<p class="GDict"><b>{key}</b>:</p><ol>'''
                for bf,bfEntry in enumerate( data ):
                    bfEntryHtml = ''
                    for bfKey,bfData in bfEntry.items():
                        if bfData is None or bfData=='' or bfData==[]: continue # Don't display blank stuff
                        if bfKey in ('Inflections','LEXMeanings'):
                            bfEntryHtml = f'''{bfEntryHtml}<p class="GDict"><b>{bfKey}</b>:</p><ol>'''
                            for lm,lmEntry in enumerate( bfData ):
                                lmEntryHtml = ''
                                for lmKey,lmData in lmEntry.items():
                                    if lmData is None or lmData=='' or lmData==[]: continue # Don't display blank stuff
                                    if lmKey == 'LEXSenses':
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="GDict"><b>{lmKey}</b>:</p><ol>'''
                                        for ls,lsEntry in enumerate( lmData ):
                                            lsEntryHtml = ''
                                            for lsKey,lsData in lsEntry.items():
                                                if lsData is None or lsData=='' or lsData==[]: continue # Don't display blank stuff
                                                lsEntryHtml = f'''{lsEntryHtml}<p class="GDict"><b>{lsKey}</b>: {lsData[0] if isinstance(lsData, list) and len(lsData)==1 else lsData}</p>'''
                                            lmEntryHtml = f'''{lmEntryHtml}<li class="GDict">{lsEntryHtml}</li>'''
                                        lmEntryHtml = f'''{lmEntryHtml}</ol>'''
                                    elif lmKey == 'LEXReferences':
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="GDict"><b>LEXReferences</b>: {', '.join(getLexReferencesHtmlList(level, lmData))}</p>'''
                                    else:
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="GDict"><b>{lmKey}</b>: {lmData[0] if isinstance(lmData, list) and len(lmData)==1 else lmData}</p>'''
                                bfEntryHtml = f'''{bfEntryHtml}<li class="GDict">{lmEntryHtml}</li>'''
                            bfEntryHtml = f'''{bfEntryHtml}</ol>'''
                        else:
                            bfEntryHtml = f'''{bfEntryHtml}<p class="GDict"><b>{bfKey}</b>: {bfData[0] if isinstance(bfData, list) and len(bfData)==1 else bfData}</p>'''
                    entryHtml = f'''{entryHtml}<li class="GDict">{bfEntryHtml}</li>'''
                entryHtml = f'''{entryHtml}</ol>'''
            else:
                entryHtml = f'''{entryHtml}<p class="GDict"><b>{key}</b>: {data[0] if isinstance(data, list) and len(data)==1 else data}</p>'''

        filepath = outputFolderPath.joinpath( f"{entry['Lemma']}.htm" )
        top = makeTop( level, None, 'dictionaryEntry', None, state ) \
                .replace( '__TITLE__', f"UBS Greek Dictionary Article{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, dictionary, {lemma}' )
        articleHtml = f'''{top}
<h1>{'TEST ' if TEST_MODE else ''}UBS Dictionary of the Greek New Testament</h1>
{navLinks.replace('__ID__','Top')}
{entryHtml}
{makeBottom( level, 'dictionaryEntry', state )}'''
        checkHtml( 'DictionaryArticle', articleHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as articleHtmlFile:
            articleHtmlFile.write( articleHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(articleHtml):,} characters written to {filepath}" )
# end of Bibles.createUBSGreekDictionaryPages


def createUBSHebrewDictionaryPages( level, outputFolderPath, state:State ) -> None:
    """
    """
    global USB_HEB_DOMAIN_DATA, USB_HEB_DATA, USB_HEB_ID_INDEX, USB_HEB_LEMMA_INDEX

    fnPrint( DEBUGGING_THIS_MODULE, f"createUBSHebrewDictionaryPages( {level}, '{outputFolderPath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Creating UBS Hebrew Bible Dict pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    indexLink = '<a title="Go up to main index" href="index.htm#__ID__">Index</a>'
    introLink = '<a title="Go to dict introduction" href="intro.htm#__ID__">Intro</a>'
    detailsLink = f'''<a title="Show details" href="{'../'*(level)}AllDetails.htm#UBS">©</a>'''

    # Make dictionary article pages
    lemmaList = [a['Lemma'] for a in USB_HEB_DATA]
    for e,entry in enumerate( USB_HEB_DATA ): # each entry is a dict
        lemma = entry['Lemma']
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Making article page for '{lemma}'…" )
        leftLink = f'''<a title="Go to previous article" href="{lemmaList[e-1]}.htm#__ID__">←</a> ''' if e>0 else ''
        rightLink = f''' <a title="Go to next article" href="{lemmaList[e+1]}.htm#__ID__">→</a>''' if e<len(lemmaList)-1 else ''
        navLinks = f'<p id="__ID__" class="dNav">{introLink} {leftLink}{indexLink}{rightLink} {detailsLink}</p>'

        entryHtml = f'<h2>{lemma}</h2>'
        for key,data in entry.items():
            if data is None or data=='' or data==[]: continue # Don't display blank stuff
            if key == 'Lemma': continue # Already used that
            if key == 'BaseForms':
                entryHtml = f'''{entryHtml}<p class="HDict"><b>{key}</b>:</p><ol>'''
                for bf,bfEntry in enumerate( data ):
                    bfEntryHtml = ''
                    for bfKey,bfData in bfEntry.items():
                        if bfData is None or bfData=='' or bfData==[]: continue # Don't display blank stuff
                        if bfKey in ('Inflections','LEXMeanings'):
                            bfEntryHtml = f'''{bfEntryHtml}<p class="HDict"><b>{bfKey}</b>:</p><ol>'''
                            for lm,lmEntry in enumerate( bfData ):
                                lmEntryHtml = ''
                                for lmKey,lmData in lmEntry.items():
                                    if lmData is None or lmData=='' or lmData==[]: continue # Don't display blank stuff
                                    if lmKey == 'LEXSenses':
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="HDict"><b>{lmKey}</b>:</p><ol>'''
                                        for ls,lsEntry in enumerate( lmData ):
                                            lsEntryHtml = ''
                                            for lsKey,lsData in lsEntry.items():
                                                if lsData is None or lsData=='' or lsData==[]: continue # Don't display blank stuff
                                                lsEntryHtml = f'''{lsEntryHtml}<p class="HDict"><b>{lsKey}</b>: {lsData[0] if isinstance(lsData, list) and len(lsData)==1 else lsData}</p>'''
                                            lmEntryHtml = f'''{lmEntryHtml}<li class="HDict">{lsEntryHtml}</li>'''
                                        lmEntryHtml = f'''{lmEntryHtml}</ol>'''
                                    elif lmKey == 'LEXReferences':
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="HDict"><b>LEXReferences</b>: {', '.join(getLexReferencesHtmlList(level, lmData))}</p>'''
                                    else:
                                        lmEntryHtml = f'''{lmEntryHtml}<p class="HDict"><b>{lmKey}</b>: {lmData[0] if isinstance(lmData, list) and len(lmData)==1 else lmData}</p>'''
                                bfEntryHtml = f'''{bfEntryHtml}<li class="HDict">{lmEntryHtml}</li>'''
                            bfEntryHtml = f'''{bfEntryHtml}</ol>'''
                        else:
                            bfEntryHtml = f'''{bfEntryHtml}<p class="HDict"><b>{bfKey}</b>: {bfData[0] if isinstance(bfData, list) and len(bfData)==1 else bfData}</p>'''
                    entryHtml = f'''{entryHtml}<li class="HDict">{bfEntryHtml}</li>'''
                entryHtml = f'''{entryHtml}</ol>'''
            else:
                entryHtml = f'''{entryHtml}<p class="HDict"><b>{key}</b>: {data[0] if isinstance(data, list) and len(data)==1 else data}</p>'''

        filepath = outputFolderPath.joinpath( f"{entry['Lemma']}.htm" )
        top = makeTop( level, None, 'dictionaryEntry', None, state ) \
                .replace( '__TITLE__', f"UBS Hebrew Dictionary Article{' TEST' if TEST_MODE else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, dictionary, {lemma}' )
        articleHtml = f'''{top}
<h1>{'TEST ' if TEST_MODE else ''}UBS Dictionary of the Hebrew New Testament</h1>
{navLinks.replace('__ID__','Top')}
{entryHtml.replace( f'{NEWLINE}</p>', '</p>' )}
{makeBottom( level, 'dictionaryEntry', state )}'''
        checkHtml( 'DictionaryArticle', articleHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as articleHtmlFile:
            articleHtmlFile.write( articleHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(articleHtml):,} characters written to {filepath}" )
# end of Bibles.createUBSHebrewDictionaryPages


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
