#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dict.py
#
# Module handling OpenBibleData Bible Dictionary functions
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
Module handling Bible Dictionary functions.

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

from html import makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-06-15' # by RJH
SHORT_PROGRAM_NAME = "Dictionary"
PROGRAM_NAME = "OpenBibleData Dictionary handler"
PROGRAM_VERSION = '0.20'
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

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Preloading Tyndale Open Bible Dictionary '{letter}' from {folderpath}…" )
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
                    assert typeName in ('DictionaryLetter','Article'), f"{name=} {typeName=}"
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
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                thisEntry = f"{thisEntry}{NEW_LINE if thisEntry else ''}{htmlSegment}"
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
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                if 'Textbox' in iiSrc or 'Map' in iiSrc: # They don't supply pictures or charts so might as well discard those here for now
                                    # So we want to save this as an XML paragraph to insert textbox later
                                    htmlSegment = f'<include_items src="{iiSrc}" name="{iiName}"/>'
                                    thisEntry = f"{thisEntry}{NEW_LINE if thisEntry else ''}{htmlSegment}"
                            else: halt
                            partCount += 1
                        stateCounter += 1
                    else: halt
                if thisEntry:
                    TOBDData['Letters'][letter].append( (name,title) )
                    TOBDData['Articles'][name] = thisEntry

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    loadDictLetterXML() loaded {len(TOBDData['Letters'][letter]):,} '{letter}' dict entries." )
# end of Dict.loadDictLetterXML


def createTyndaleDictPages( level:int, outputFolderPath, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE
    from Bibles import fixTyndaleBRefs

    fnPrint( DEBUGGING_THIS_MODULE, f"createTyndaleDictPages( '{level}', '{outputFolderPath}', ... )")

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nCreating Tyndale Bible Dict pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    for articleName,article in TOBDData['Articles'].items():
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Making article page for '{articleName}'…" )

        # Fix their links like '<a href="?bref=Mark.4.14-20">4:14-20</a>'
        adjustedArticle = fixTyndaleBRefs( 'TOBD', level, articleName, '', '', article, state )
        adjustedArticle = fixTyndaleItemRefs( 'TOBD', level, articleName, adjustedArticle, state )

        filename = f'{articleName}.htm'
        filepath = outputFolderPath.joinpath( filename )
        top = makeTop( level, None, 'dictionaryEntry', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Dictionary Article" ) \
                .replace( '__KEYWORDS__', f'Bible, dictionary, {articleName}' )
        articleHtml = f'''{top}<h1>Tyndale Open Bible Dictionary <small><a title="Show details" href="{'../'*(level)}allDetails.htm#TOBD">©</a></small></h1>
<h2 id="Top">{articleName}</h2>
{adjustedArticle}
{makeBottom( level, 'dictionaryEntry', state )}'''
        checkHtml( 'DictionaryArticle', articleHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as articleHtmlFile:
            articleHtmlFile.write( articleHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(articleHtml):,} characters written to {filepath}" )

    # Make letter index pages
    for letter,articleList in TOBDData['Letters'].items():
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Making letter summary page for '{letter}'…" )
        # articleLinkList = [f'<a title="Go to article" href="{articleName}.htm">{articleDisplayName}</a>' for articleName,articleDisplayName in articleList]
        articleLinkHtml = ''
        for articleName,articleDisplayName in articleList:
            articleLink = f'<a title="Go to article" href="{articleName}.htm">{articleDisplayName}</a>'
            firstLetters = articleName[:2]
            if articleLinkHtml:
                articleLinkHtml = f'''{articleLinkHtml}{' ' if firstLetters==lastFirstLetters else '\n<br>'}{articleLink}'''
            else: # first entry
                articleLinkHtml = articleLink
            lastFirstLetters = firstLetters
        filename = f'{letter}_index.htm'
        filepath = outputFolderPath.joinpath( filename )
        top = makeTop( level, None, 'dictionaryLetterIndex', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Dictionary" ) \
                .replace( '__KEYWORDS__', f'Bible, dictionary' )
#{' '.join(articleLinkList)}
        letterIndexHtml = f'''{top}<h1>Tyndale Open Bible Dictionary <small><a title="Show details" href="{'../'*(level)}allDetails.htm#TOBD">©</a></small></h1>
<h2 id="Top">Index for dictionary letter '{letter}'</h2>
{articleLinkHtml}
{makeBottom( level, 'dictionaryLetterIndex', state )}'''
        checkHtml( 'DictionaryLetterIndex', letterIndexHtml )
        with open( filepath, 'wt', encoding='utf-8' ) as letterIndexHtmlFile:
            letterIndexHtmlFile.write( letterIndexHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(letterIndexHtml):,} characters written to {filepath}" )

    # Make overall index
    letterLinkList = [f'''<a title="Go to index page for letter '{l}'" href="{l}_index.htm">{l}</a>''' for l in TOBDData['Letters']]
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'dictionaryMainIndex', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Dictionary" ) \
            .replace( '__KEYWORDS__', f'Bible, dictionary' )
    indexHtml = f'''{top}<h1 id="Top">Tyndale Open Bible Dictionary <small><a title="Show details" href="{'../'*(level)}allDetails.htm#TOBD">©</a></small></h1>
<h2>Index of dictionary letters</h2>
{' '.join(letterLinkList)}
{makeBottom( level, 'dictionaryMainIndex', state )}'''
    checkHtml( 'DictionaryIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of Dict.createTyndaleDictPages


def fixTyndaleItemRefs( abbrev:str, level:int, articleName:str, html:str, state ) -> str:
    """
    Most of the parameters are for info messages only
    """
    from createSitePages import ALTERNATIVE_VERSION

    fnPrint( DEBUGGING_THIS_MODULE, f"fixTyndaleItemRefs( {abbrev}, {level}, {articleName} {html}, ... )")

    # Fix their links like '<a href="?item=MarriageMarriageCustoms_Article_TyndaleOpenBibleDictionary">Marriage, Marriage Customs</a>'
    # Doesn't yet handle links like '(see “<a href="?item=FollowingJesus_ThemeNote_Filament">Following Jesus</a>” Theme Note)'
    searchStartIndex = 0
    for _safetyCount in range( 25 ): # 19 was too few
        ixStart = html.find( 'href="?item=', searchStartIndex )
        if ixStart == -1: # none/no more found
            break
        ixCloseQuote = html.find( '"', ixStart+12 )
        assert ixCloseQuote != -1
        tyndaleLinkPart = html[ixStart+12:ixCloseQuote]
        # print( f"{abbrev} {BBB} {C}:{V} {tyndaleLinkPart=}" )
        # if 'Filament' in tyndaleLinkPart: # e.g., in GEN 48:14 '2Chr.28.12_StudyNote_Filament'
        #     logging.critical( f"Ignoring Filament link in {abbrev} {articleName} {tyndaleLinkPart=}" )
        #     searchStartIndex = ixCloseQuote + 6
        #     continue
        assert tyndaleLinkPart.endswith( '_TyndaleOpenBibleDictionary' ), f"{abbrev} {level} '{articleName}' {tyndaleLinkPart=}"
        tyndaleLinkPart = tyndaleLinkPart[:-27]
        # print( f"{tyndaleLinkPart=}" )
        assert tyndaleLinkPart.count('_') == 1
        assert tyndaleLinkPart.endswith( '_Article' ) or tyndaleLinkPart.endswith( '_Textbox' ) or tyndaleLinkPart.endswith( '_Map' ), f"{abbrev} {level} '{articleName}' {tyndaleLinkPart=}"
        tyndaleName, tyndaleType = tyndaleLinkPart.split( '_' )
        # print( f"{tyndaleName=} {tyndaleType=}" )
        ourNewLink = f"{tyndaleName}.htm"
        # print( f"   {ourNewLink=}" )
        html = f'''{html[:ixStart+6]}{ourNewLink}{html[ixCloseQuote:]}'''
        searchStartIndex = ixStart + 10
    else: need_to_increase_Tyndale_item_loop_counter

    return html
# end of Bibles.fixTyndaleItemRefs



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
