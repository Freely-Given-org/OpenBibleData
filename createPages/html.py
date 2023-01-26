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
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

# from Bibles import fetchChapter


LAST_MODIFIED_DATE = '2023-01-27' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.07'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def doOET_LV_HTMLcustomisations( html:str ) -> str:
    """
    """
    return html \
            .replace( '.', '.<br>' ).replace( '?', '?<br>' ).replace( '!', '!<br>' ).replace( ':', ':<br>' ) \
            .replace( '<span class="added">+', '<span class="addedArticle">' ) \
            .replace( '<span class="added">=', '<span class="addedCopula">' ) \
            .replace( '<span class="added">~', '<span class="addedDirectObject">' ) \
            .replace( '<span class="added">>', '<span class="addedExtra">' ) \
            .replace( '<span class="added">^', '<span class="addedOwner">' ) \
            .replace( '_', '<span class="ul">_</span>')
# end of html.doOET_LV_HTMLcustomisations

def makeTop( level:int, pageType:str, state ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {pageType} )" )

    if pageType == 'chapters':
        cssFilename = 'BibleChapter.css'
    elif pageType == 'OETChapters':
        cssFilename = 'OETChapter.css'
    else: cssFilename = 'BibleSite.css'

    top = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}OETChapter.css">
  <script src="{'../'*level}Bible.js"></script>
</head>
<body>
""" if pageType == 'OETChapters' else f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
</head>
<body>
"""
    return top + makeHeader( level, pageType, state ) + '\n'
# end of html.makeTop

def makeHeader( level:int, pageType:str, state ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeHeader( {level}, {pageType} )" )
    html = ''
    versionList = []
    for versionAbbreviation in state.BibleVersions:
        versionList.append( f'''<a href="{'../'*level}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}">{versionAbbreviation}</a>''' )
    if pageType == 'parallel':
        versionList.append( 'Parallel' )
    else: # add a link for parallel
        versionList.append( f'''<a href="{'../'*level}parallel/">Parallel</a>''' )
    if pageType == 'interlinear':
        versionList.append( 'Interlinear' )
    else: # add a link for parallel
        versionList.append( f'''<a href="{'../'*level}interlinear/">Interlinear</a>''' )
    return f'<div class="header">{EM_SPACE.join(versionList)}</div><!--header-->'
# end of html.makeHeader

def makeBottom( level:int, pageType:str, state ) -> str:
    """
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeBottom()" )
    return makeFooter( level, pageType, state ) + '</body></html>'
# end of html.makeBottom

def makeFooter( level:int, pageType:str, state ) -> str:
    """
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeFooter()" )
    html = """<div class="footer">
<p><small><em>Open Bible Data</em> site copyright © 2023 <a href="https://Freely-Given.org">Freely-Given.org</a></small></p>
<p><small>For Bible data copyrights, see the licence for each displayed Bible version.</small></p>
</div><!--footer-->
"""
    return html
# end of html.makeFooter

def checkHtml( where:str, html:str, segmentOnly:bool=False ) -> None:
    """
    Just do some very quick and basic tests
        that our HTML makes some sense.

    Throws an AssertError for any problems.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"checkHtml( {where}, {len(html)} )" )
    if segmentOnly:
        assert html.count( '<html' ) == html.count( '</html>' ), html[html.index('<html'):]
        assert html.count( '<head>' ) == html.count( '</head>' ), html[html.index('<head>'):]
        assert html.count( '<body>' ) == html.count( '</body>' ), html[html.index('<body>'):]
    else:
        assert html.count( '<html' ) == 1
        assert html.count( '</html>' ) == 1
        assert html.count( '<head>' ) == 1
        assert html.count( '</head>' ) == 1
        assert html.count( '<body>' ) == 1
        assert html.count( '</body>' ) == 1

    try: assert html.count( '<div' ) == html.count( '</div>' ), f"{where} {html[html.index('<div'):]}"
    except ValueError: assert html.count( '<div' ) == html.count( '</div>' ), f"{where} {html[:html.index('</div>')+5]}"
    try: assert html.count( '<p' ) == html.count( '</p>' ), f"{where} {html[html.index('<p'):]}"
    except ValueError: assert html.count( '<p' ) == html.count( '</p>' ), f"{where} {html[:html.index('</p>')+4]}"
    # if where not in ('UST MRK 13:13','Parallel MRK 13:13',
    #                  'UST ROM 8:27','Parallel ROM 8:27',
    #                  'UST ROM 9:1','Parallel ROM 9:1',
    #                  'UST ROM 11:19','Parallel ROM 11:19',
    #                  'UST ROM 11:31','Parallel ROM 11:31'):
    if 'UST ' not in where and 'ULT ' not in where and 'Parallel ' not in where:
        assert html.count( '<span' ) == html.count( '</span>' ), f"{where} {html[html.index('<span'):]}"

    assert html.count( '<h1' ) == html.count( '</h1>' ), html[html.index('<h1'):]
    assert html.count( '<h2' ) == html.count( '</h2>' ), html[html.index('<h2'):]
    assert html.count( '<h3' ) == html.count( '</h3>' ), html[html.index('<h3'):]

    assert html.count( '<em>' ) == html.count( '</em>' ), html[html.index('<em>'):]
    assert html.count( '<i>' ) == html.count( '</i>' ), html[html.index('<i>'):]
    assert html.count( '<b>' ) == html.count( '</b>' ), html[html.index('<b>'):]
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
