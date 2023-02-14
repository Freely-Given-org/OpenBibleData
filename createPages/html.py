#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData html functions
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
Module handling html functions.

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
import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

# from Bibles import fetchChapter


LAST_MODIFIED_DATE = '2023-02-15' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.18'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def do_OET_LV_HTMLcustomisations( html:str ) -> str:
    """
    OET-LV is often formatted as a new line for each sentence.

    We have to protect fields like periods in '../C2_V2.html' from corruption
        (and then restore them again of course).
    """
    return html \
            .replace( '<!--', '~~COMMENT~~' ) \
            .replace( '../', '~~UP~DIR~~' ).replace( '_V', '~~V' ) \
            .replace( '.html', '~~HTML~~' ).replace( 'https:', '~~HTTPS~~' ) \
            .replace( '.org', '~~ORG~~' ).replace( 'v0.', '~~v0~~' ) \
            .replace( '.', '.<br>\n' ).replace( '?', '?<br>\n' ) \
            .replace( '!', '!<br>\n' ).replace( ':', ':<br>\n' ) \
            .replace( '<span class="add">+', '<span class="addArticle">' ) \
            .replace( '<span class="add">=', '<span class="addCopula">' ) \
            .replace( '<span class="add">~', '<span class="addDirectObject">' ) \
            .replace( '<span class="add">>', '<span class="addExtra">' ) \
            .replace( '<span class="add">^', '<span class="addOwner">' ) \
            .replace( '_', '<span class="ul">_</span>') \
            .replace( '~~COMMENT~~', '<!--' ) \
            .replace( '~~UP~DIR~~', '../' ).replace( '~~V', '_V' ) \
            .replace( '~~HTML~~', '.html' ).replace( '~~HTTPS~~', 'https:' ) \
            .replace( '~~ORG~~', '.org' ).replace( '~~v0~~', 'v0.' )
# end of html.do_OET_LV_HTMLcustomisations


def do_LSV_HTMLcustomisations( html:str ) -> str:
    """
    LSV has lines like:
        v 7 “\\w Blessed|strong="G3107"\\w* [\\w are|strong="G3588"\\w*] \\w they|strong="G2532"\\w* \\w whose|strong="G3739"\\w* lawless \\w acts|strong="G4160"\\w* \\w were|strong="G3588"\\w* forgiven, || \\w And|strong="G2532"\\w* \\w whose|strong="G3739"\\w* \\w sins|strong="G3900"\\w* \\w were|strong="G3588"\\w* \\w covered|strong="G1943"\\w*;

    We need to change the two parallel lines to <br>.
    """
    return html.replace( ' || ', '<br>' ).replace( '||', '<br>' ) # Second one catches any source inconsistencies
# end of html.do_LSV_HTMLcustomisations


def makeTop( level:int, pageType:str, filename:Optional[str], state ) -> str:
    """
    Create the very top part of an HTML page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {pageType} {filename} )" )

    if pageType in ('chapters','book'):
        cssFilename = 'BibleChapter.css'
    elif pageType in ('OETChapters','OETbook'):
        cssFilename = 'OETChapter.css'
    elif pageType == 'parallel':
        cssFilename = 'ParallelVerses.css'
    else: cssFilename = 'BibleSite.css'

    topLink = '<p class="site">Open Bible Data</p>' if level==0 else f'''<p class="site"><a href="{'../'*level}">Open Bible Data</a></p>'''
    top = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}OETChapter.css">
  <script src="{'../'*level}Bible.js"></script>
</head><body><!--Level{level}-->{topLink}
""" if pageType == 'OETChapters' else f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
</head><body><!--Level{level}-->{topLink}
<h3>Prototype quality only—still in development</h3>
"""
    return top + _makeHeader( level, pageType, filename, state ) + '\n'
# end of html.makeTop

def _makeHeader( level:int, pageType:str, filename:Optional[str], state ) -> str:
    """
    Create the navigation that goes before the page content.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_makeHeader( {level}, {pageType} {filename} )" )

    # Add all the version abbreviations
    #   with their style decorators
    #   and with the more specific links if specified.
    versionList = []
    for versionAbbreviation in state.BibleVersions:
        # TODO: This is not good because not all versions have all books
        vLink = f"{'../'*level}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}" if not filename \
                    else f"{'../'*level}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/{filename}"
        versionList.append( f'{state.BibleVersionDecorations[versionAbbreviation][0]}'
                            f'<a title="{state.BibleNames[versionAbbreviation]}" '
                            f'href="{vLink}">{versionAbbreviation}</a>'
                            f'{state.BibleVersionDecorations[versionAbbreviation][1]}'
                            )
    if pageType == 'parallel':
        versionList.append( 'Parallel' )
    else: # add a link for parallel
        versionList.append( f'''{state.BibleVersionDecorations['Parallel'][0]}<a title="Single verse in many translations" href="{'../'*level}parallel/">Parallel</a>{state.BibleVersionDecorations['Parallel'][1]}''' )
    if pageType == 'interlinear':
        versionList.append( 'Interlinear' )
    else: # add a link for interlinear
        versionList.append( f'''{state.BibleVersionDecorations['Interlinear'][0]}<a title="Not done yet" href="{'../'*level}interlinear/">Interlinear</a>{state.BibleVersionDecorations['Interlinear'][1]}''' )

    # vlLen = len(versionList)
    # if vlLen > 16: # split into thirds
    #     html = f'<p class="vLinks">{EM_SPACE.join(versionList[:vlLen//3])}</p>\n' \
    #             f'<p class="vLinks">{EM_SPACE.join(versionList[vlLen//3:vlLen*2//3+1])}</p>' \
    #             f'<p class="vLinks">{EM_SPACE.join(versionList[vlLen*2//3+1:])}</p>'
    # elif vlLen > 10: # split in half
    #     html = f'<p class="vLinks">{EM_SPACE.join(versionList[:vlLen//2])}</p>\n' \
    #             f'<p class="vLinks">{EM_SPACE.join(versionList[vlLen//2:])}</p>'
    # else:
    html = f'<p class="workNav">{EM_SPACE.join(versionList)}</p>'

    # listChunks = [versionList]
    # if vlLen > 16: # split into thirds
    #     listChunks = [versionList[:vlLen//3], versionList[vlLen//3:vlLen*2//3+1], versionList[vlLen*2//3+1:]]
    # elif vlLen > 10: # split in half
    #     listChunks = [versionList[:vlLen//2], versionList[vlLen//2:]]
    # htmlChunks = []
    # for listChunk in listChunks:
    #     htmlChunks.append( f'<p class="workNav">{EM_SPACE.join(listChunk)}</p>' )
    # html = '\n'.join( htmlChunks )

    return f'<div class="header">{html}</div><!--header-->'
# end of html._makeHeader

def makeBottom( level:int, pageType:str, state ) -> str:
    """
    Create the very bottom part of an HTML page.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeBottom()" )
    return _makeFooter( level, pageType, state ) + '</body></html>'
# end of html.makeBottom

def _makeFooter( level:int, pageType:str, state ) -> str:
    """
    Create any links or site map that follow the main content on the page.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"_makeFooter()" )
    html = """<div class="footer">
<p class="copyright"><small><em>Open Bible Data</em> site copyright © 2023 <a href="https://Freely-Given.org">Freely-Given.org</a></small></p>
<p class="copyright"><small>For Bible data copyrights, see the details for each displayed Bible version.</small></p>
</div><!--footer-->"""
    return html
# end of html._makeFooter

def removeDuplicateCVids( html:str ) -> str:
    """
    Where we have OET parallel RV and LV, we get doubled ids like <span class="v" id="C2V6">

    This function removes the second id field in each case (which should be in the LV text).
    """
    startSearchIndex = 0
    while True:
        startIx = html.find( ' id="C', startSearchIndex )
        if startIx == -1: break # None / no more
        endIx = html.find( '>', startIx+6 )
        assert endIx != -1
        idContents = html[startIx:endIx]
        assert 7 < len(idContents) < 14
        idCount = html.count( idContents, startIx )
        assert 1 <= idCount <= 2
        if idCount == 2:
            html = f"{html[:endIx]}{html[endIx:].replace( idContents, '', 1 )}"
            assert html.count( idContents ) == 1
        startSearchIndex += len( idContents )
    return html
# end of html.removeDuplicateCVids

def checkHtml( where:str, html:str, segmentOnly:bool=False ) -> bool:
    """
    Just do some very quick and basic tests
        that our HTML makes some sense.

    Throws an AssertError for any problems.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"checkHtml( {where}, {len(html)} )" )

    for marker,startMarker in (('html','<html'),('head','<head>'),('body','<body>')):
        if segmentOnly:
            assert html.count( startMarker ) == html.count( f'</{marker}>' ), html[html.index(startMarker):]
        else:
            assert html.count( startMarker ) == 1
            assert html.count( f'</{marker}>' ) == 1

    for marker,startMarker in (('div','<div'),('p','<p '),('h1','<h1'),('h2','<h2'),('h3','<h3'),('em','<em>'),('i','<i>'),('b','<b>'),('sup','<sup>'),('sub','<sub>')):
        if html.count( startMarker ) != html.count( f'</{marker}>' ):
            # try: errMsg = f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {html.count(startMarker)}!={html.count(f'</{marker}>')} …{html[html.index(startMarker):]}"
            # except ValueError: errMsg = f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {html.count(startMarker)}!={html.count(f'</{marker}>')} {html[:html.index(f'</{marker}>')]}…"
            # logging.critical( errMsg )
            ixStartMarker = html.find( startMarker )
            ixEndMarker = html.find( f'</{marker}>' )
            ixMinStart = min( 9999999 if ixStartMarker==-1 else ixStartMarker, 9999999 if ixEndMarker==-1 else ixEndMarker )
            ixRStartMarker = html.rfind( startMarker )
            ixREndMarker = html.rfind( f'</{marker}>' )
            ixMinEnd = min( ixRStartMarker, ixREndMarker )
            logging.critical( f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {html.count(startMarker)}!={html.count(f'</{marker}>')}"
                              f" {'…' if ixMinStart>0 else ''}{html[ixMinStart:ixMinEnd+5]}{'…' if ixMinEnd+5<len(html) else ''}" )
            if DEBUGGING_THIS_MODULE: print( f"\nComplete {html=}\n")
            return False

    return True
# end of html.checkHtml


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of html.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of html.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of html.py
