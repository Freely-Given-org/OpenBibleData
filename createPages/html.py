#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData html functions
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
Module handling html functions.

makeTop( level:int, versionAbbreviation:Optional[str], pageType:str, versionSpecificFileOrFolderName:Optional[str], state:State ) -> str
makeHeader( level:int, versionAbbreviation:str, pageType:str, versionSpecificFileOrFolderName:Optional[str], state:State ) -> str
makeBookNavListParagraph( linksList:List[str], workAbbrevPlus:str, state:State ) -> str
makeBottom( level:int, pageType:str, state:State ) -> str
makeFooter( level:int, pageType:str, state:State ) -> str
removeDuplicateCVids( BBB:str, html:str ) -> str
checkHtml( where:str, htmlToCheck:str, segmentOnly:bool=False ) -> bool
do_OET_RV_HTMLcustomisations( OET_RV_html:str ) -> str
do_OET_LV_HTMLcustomisations( OET_LV_html:str ) -> str
do_LSV_HTMLcustomisations( LSV_html:str ) -> str
do_T4T_HTMLcustomisations( T4T_html:str ) -> str
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2023-07-20 Handled removal of #Vv navigation links to section pages (already had #CcVv)
    2023-08-07 Handle four-letter tidyBBBs
    2023-08-16 Improve byDocument navigation
    2023-08-22 Make removeDuplicateCVids work for larger books
    2023-08-30 Separate extra books in bkLst paragraph
    2023-09-25 Added search
    2023-10-10 Improved OET-LV customisations to be more selective and efficient
    2024-01-25 Added support for 'Related' sections mode
    2024-04-03 Added OET Key page
    2024-04-21 Added News page
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import re

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27

from settings import State, TEST_MODE, SITE_NAME


LAST_MODIFIED_DATE = '2024-04-22' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.77'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '


KNOWN_PAGE_TYPES = ('site', 'topIndex', 'details', 'allDetails',
                    'book','bookIndex', 'chapter','chapterIndex', 'section','sectionIndex',
                    'relatedPassage','relatedSectionIndex', 'parallelVerse', 'interlinearVerse',
                    'dictionaryMainIndex','dictionaryLetterIndex','dictionaryEntry','dictionaryIntro',
                    'word','lemma','morpheme', 'person','location',
                    'wordIndex','lemmaIndex','morphemeIndex', 'personIndex','locationIndex', 'referenceIndex',
                    'search', 'about', 'news', 'OETKey')
def makeTop( level:int, versionAbbreviation:Optional[str], pageType:str, versionSpecificFileOrFolderName:Optional[str], state:State ) -> str:
    """
    Create the very top part of an HTML page.

    This is the HTML <head> segment, including assigning the correct CSS stylesheet.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )
    assert pageType in KNOWN_PAGE_TYPES, f"{level=} {versionAbbreviation=} {pageType=}"

    if pageType in ('chapter','section','book'):
        cssFilename = 'OETChapter.css' if 'OET' in versionAbbreviation else 'BibleChapter.css'
    elif pageType == 'relatedPassage':
        cssFilename = 'ParallelPassages.css'
    elif pageType == 'parallelVerse':
        cssFilename = 'ParallelVerses.css'
    elif pageType == 'interlinearVerse':
        cssFilename = 'InterlinearVerse.css'
    elif pageType in ('word','lemma','morpheme', 'person','location'):
        cssFilename = 'BibleWord.css'
    elif pageType in ('dictionaryLetterIndex', 'dictionaryEntry','dictionaryIntro'):
        cssFilename = 'BibleDict.css'
    elif pageType in ('site', 'details','allDetails', 'search', 'about', 'news', 'OETKey', 'topIndex',
                      'bookIndex','chapterIndex','sectionIndex',
                      'relatedSectionIndex', 'dictionaryMainIndex',
                      'wordIndex','lemmaIndex','morphemeIndex','personIndex','locationIndex','referenceIndex' ):
        cssFilename = 'BibleSite.css'
    else: unexpected_page_type

    homeLink = f"{SITE_NAME}{' TEST' if TEST_MODE else ''} Home" if pageType=='topIndex' else f'''<a href="{'../'*level}about.htm#Top">About</a>'''
    aboutLink = 'About' if pageType=='about' else f'''<a href="{'../'*level}about.htm#Top">About</a>'''
    newsLink = 'News' if pageType=='news' else f'''<a href="{'../'*level}news.htm#Top">News</a>'''
    OETKeyLink = 'OET Key' if pageType=='OETKey' else f'''<a href="{'../'*level}OETKey.htm#Top">OET Key</a>'''
    topLink = f'<p class="site">{homeLink}  {aboutLink}  {newsLink}  {OETKeyLink}</p>'

    top = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="user-scalable=yes, initial-scale=1, minimum-scale=1, width=device-width">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
  <script src="{'../'*level}Bible.js"></script>
</head>
<body><!--Level{level}-->{topLink}
""" if (versionAbbreviation and 'OET' in versionAbbreviation) or pageType=='parallelVerse' \
else f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="user-scalable=yes, initial-scale=1, minimum-scale=1, width=device-width">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
</head>
<body><!--Level{level}-->{topLink}
<h3>Demonstration version—prototype quality only—still in development</h3>
"""
    return f'{top}{_makeHeader( level, versionAbbreviation, pageType, versionSpecificFileOrFolderName, state )}'
# end of html.makeTop

def _makeHeader( level:int, versionAbbreviation:str, pageType:str, versionSpecificFileOrFolderName:Optional[str], state:State ) -> str:
    """
    Create the navigation that goes before the page content.

    This includes the list of versions, and possibly the "ByDocument/BySection" bar as well.
        (It doesn't include book, chapter, or verse selector bars.)

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_makeHeader( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )

    # Add all the version abbreviations (except for the selected-verses-only verses)
    #   with their style decorators
    #   and with the more specific links if specified.
    initialVersionList = ['TEST'] if TEST_MODE else []
    for loopVersionAbbreviation in state.BibleVersions:
        if loopVersionAbbreviation in ('TOSN','TTN','UTN'): # Skip notes
            continue
        if loopVersionAbbreviation in state.versionsWithoutTheirOwnPages: # Skip versions without their own pages
            continue
        if pageType in ('section','section'):
            try:
                thisBible = state.preloadedBibles['OET-RV' if loopVersionAbbreviation=='OET' else loopVersionAbbreviation]
                if not thisBible.discoveryResults['ALL']['haveSectionHeadings']:
                    continue # skip this one
            except AttributeError: # no discoveryResults
                continue

        # Note: This is not good because not all versions have all books -- we try to fix that below
        vLink = '../'*level if loopVersionAbbreviation == versionAbbreviation else \
                f"{'../'*level}{BibleOrgSysGlobals.makeSafeString(loopVersionAbbreviation)}/{versionSpecificFileOrFolderName}" \
                    if versionSpecificFileOrFolderName else \
                f"{'../'*level}{BibleOrgSysGlobals.makeSafeString(loopVersionAbbreviation)}"
        initialVersionList.append( f'{state.BibleVersionDecorations[loopVersionAbbreviation][0]}'
                            f'<a title="{state.BibleNames[loopVersionAbbreviation]}" '
                            f'href="{vLink}">{loopVersionAbbreviation}</a>'
                            f'{state.BibleVersionDecorations[loopVersionAbbreviation][1]}'
                            )
    if pageType in ('relatedPassage','relatedSectionIndex'):
        initialVersionList.append( 'Related' )
    else: # add a link for parallel
        initialVersionList.append( f'''{state.BibleVersionDecorations['Related'][0]}<a title="Single OET-RV section with related verses from other books" href="{'../'*level}rel/">Related</a>{state.BibleVersionDecorations['Related'][1]}''' )
    if pageType == 'parallelVerse':
        initialVersionList.append( 'Parallel' )
    else: # add a link for parallel
        initialVersionList.append( f'''{state.BibleVersionDecorations['Parallel'][0]}<a title="Single verse in many different translations" href="{'../'*level}par/">Parallel</a>{state.BibleVersionDecorations['Parallel'][1]}''' )
    if pageType == 'interlinearVerse':
        initialVersionList.append( 'Interlinear' )
    else: # add a link for interlinear
        initialVersionList.append( f'''{state.BibleVersionDecorations['Interlinear'][0]}<a title="Single verse in interlinear word view" href="{'../'*level}ilr/">Interlinear</a>{state.BibleVersionDecorations['Interlinear'][1]}''' )
    if pageType == 'dictionaryMainIndex':
        initialVersionList.append( 'Dictionary' )
    else: # add a link for dictionary
        initialVersionList.append( f'''{state.BibleVersionDecorations['Dictionary'][0]}<a title="Dictionary index" href="{'../'*level}dct/">Dictionary</a>{state.BibleVersionDecorations['Dictionary'][1]}''' )
    if pageType == 'search':
        initialVersionList.append( 'Search' )
    else: # add a link for dictionary
        initialVersionList.append( f'''{state.BibleVersionDecorations['Search'][0]}<a title="Find Bible words" href="{'../'*level}search.htm">Search</a>{state.BibleVersionDecorations['Search'][1]}''' )

    # This code tries to adjust links to books which aren't in a version, e.g., UHB has no NT books, SR-GNT and UGNT have no OT books
    # It does this by adjusting the potential bad link to the next level higher.
    newVersionList = []
    for entry in initialVersionList:
        # if pageType == 'parallelVerse':
        #     print( f"  _makeHeader processing {entry=} ({level=} {versionAbbreviation=} {pageType=} {fileOrFolderName=})" )
        if '/par/' in entry or '/ilr/' in entry:
            newVersionList.append( entry )
            continue # Should always be able to link to these
        entryBBB = None
        for tryBBB in state.allBBBs: # from all loaded versions
            if f'{tryBBB}.' in entry or f'{tryBBB}_' in entry or f'{tryBBB}/' in entry:
                assert not entryBBB # Make sure we only found exactly one of them
                entryBBB = tryBBB
        if entryBBB:
            startIndex = entry.index('">') + 2
            loopVersionAbbreviation = entry[startIndex:entry.index('<',startIndex)]
            if loopVersionAbbreviation == 'OET': loopVersionAbbreviation = 'OET-RV' # We look here in this case
            thisBible = state.preloadedBibles[loopVersionAbbreviation]
            if entryBBB in thisBible:
                # if pageType == 'parallelVerse': print( f"    Appended {thisVersionAbbreviation} {entryBBB} as is (from {entry})")
                newVersionList.append( entry )
                continue # Should always be able to link to these
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Might not be able to link to {pageType} {loopVersionAbbreviation} {entry}???" )
            replacement = ''
            if '/' in versionSpecificFileOrFolderName:
                ix = versionSpecificFileOrFolderName.index( '/' )
                if ix>0 and ix<len(versionSpecificFileOrFolderName)-1: # The slash is in the middle -- not at the beginning or the end
                    replacement = versionSpecificFileOrFolderName[:ix+1]
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"          Can we adapt {pageType} '{versionSpecificFileOrFolderName}' to '{replacement}'" )
            newEntry = entry.replace( versionSpecificFileOrFolderName, replacement ) # Effectively links to a higher level folder
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"       Changed {pageType} link entry to {newEntry}")
            newVersionList.append( newEntry )
        else:
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Couldn't find a BBB so should be able to link ok to {pageType} {entry}" )
            newVersionList.append( entry )
    assert len(newVersionList) == len(initialVersionList)
    versionHtml = f'''<p class="wrkLst">{' '.join(newVersionList)}</p>'''
    # if pageType == 'parallelVerse':
    #     print( f"    {newVersionList=}" )
    #     halt

    viewLinks = []
    if pageType in ('book','section','chapter', 'details',
                    'bookIndex','sectionIndex','chapterIndex') \
    and versionAbbreviation not in ('TOSN','TTN','TOBD','UTN','UBS') \
    and versionAbbreviation not in state.versionsWithoutTheirOwnPages:
        if TEST_MODE: viewLinks.append( 'TEST' )
        if not versionAbbreviation: versionAbbreviation = 'OET'
        viewLinks.append( f'''<a title="Select a different version" href="{'../'*level}">{versionAbbreviation}</a>''' )
        viewLinks.append( f'''<a title="View entire document" href="{'../'*level}{versionAbbreviation}/byDoc/">By Document</a>'''
                            if 'book' not in pageType else 'By Document' )
        if state.preloadedBibles['OET-RV' if versionAbbreviation=='OET' else versionAbbreviation].discoveryResults['ALL']['haveSectionHeadings']:
            viewLinks.append( f'''<a title="View section" href="{'../'*level}{versionAbbreviation}/bySec/">By Section</a>'''
                            if 'section' not in pageType else 'By Section' )
        viewLinks.append( f'''<a title="View chapter" href="{'../'*level}{versionAbbreviation}/byC/">By Chapter</a>'''
                            if 'chapter' not in pageType else 'By Chapter' )
        viewLinks.append( f'''<a title="View version details" href="{'../'*level}{versionAbbreviation}/details.htm#Top">Details</a>'''
                            if pageType!='details' else 'Details' )
    viewHtml = f'''<p class="viewLst">{' '.join(viewLinks)}</p>''' if viewLinks else ''

    return f'''<div class="header">{versionHtml}{NEWLINE if viewHtml else ''}{viewHtml}</div><!--header-->'''
# end of html._makeHeader


HTML_PLUS_LIST = ['parallelVerse','interlinearVerse', 'parallelIndex','interlinearIndex']
OET_HTML_PLUS_LIST = ['OET'] + HTML_PLUS_LIST
def makeBookNavListParagraph( linksList:List[str], workAbbrevPlus:str, state:State ) -> str:
    """
    Create a 'bkLst' paragraph with the book abbreviation links
        preceded by the work abbreviation (non-link) if specified.

    linksList contains links like '<a title="Generic front matter" href="FRT.htm#Top">FRT</a>', '<a title="Jonah" href="JNA.htm#Top">JNA</a>', '<a title="Mark" href="MRK.htm#Top">MARK</a>'
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeBookNavListParagraph( {linksList}, {workAbbrevPlus}, ... )" )
    assert workAbbrevPlus in state.preloadedBibles \
        or workAbbrevPlus in OET_HTML_PLUS_LIST \
        or workAbbrevPlus == 'Related OET-RV', workAbbrevPlus

    newList = (['TEST',workAbbrevPlus] if TEST_MODE else [workAbbrevPlus]) if workAbbrevPlus else (['TEST'] if TEST_MODE else [])
    for aLink in linksList:
        # print( f"{aLink=}")
        if '>FRT<' in aLink and workAbbrevPlus in HTML_PLUS_LIST: continue # Don't include this
        if workAbbrevPlus in HTML_PLUS_LIST: # they're all byVerse options
            # Make the versionAbbreviation links go to 1:1 for the selected book
            ixHrefStart = aLink.index( 'href="' ) + 6
            ixHrefEnd = aLink.index( '.htm', ixHrefStart )
            hrefText = aLink[ixHrefStart:ixHrefEnd]
            aLink = f'''{aLink[:ixHrefStart]}{'' if 'Index' in workAbbrevPlus else '../'}{hrefText}/C1V1{aLink[ixHrefEnd:]}'''
        ixDisplayLinkStart = aLink.index( '>' ) + 1
        ixDisplayLinkEnd = aLink.index( '<', ixDisplayLinkStart )
        displayText = aLink[ixDisplayLinkStart:ixDisplayLinkEnd]
        # print( f"  {aLink=} {displayText=}")
        assert 3 <= len(displayText) <= 4 # it should be a tidyBBB
        BBB = ( 'JNA' if displayText=='YNA'
                else 'JHN' if displayText=='YHN'
                else 'JAM' if displayText=='YAC'
                else 'JN1' if displayText=='1YHN' else 'JN2' if displayText=='2YHN' else 'JN3' if displayText=='3YHN'
                else 'JDE' if displayText=='YUD'
                else 'PS2' if displayText=='2PS'
                else BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( displayText ) )
        # print( f"   {aLink=} {displayText=} {BBB=}")
        assert BBB, f"{displayText=}"
        newALink = f'{aLink[:ixDisplayLinkStart]}{displayText}{aLink[ixDisplayLinkEnd:]}'
        if BBB in ('INT','FRT','OTH','GLS','XXA','XXB','XXC','XXD'):
            newALink = f'<span class="XX">{newALink}</span>'
        elif BBB in BOOKLIST_OT39:
            newALink = f'<span class="OT">{newALink}</span>'
        elif BBB in BOOKLIST_NT27:
            newALink = f'<span class="NT">{newALink}</span>'
        else: # DC book
            newALink = f'<span class="DC">{newALink}</span>'
        # print( f"    {aLink=} {displayText=} {BBB=} {newALink=}")
        newList.append( newALink )

    return f'''<p class="bkLst">{' '.join( newList )}</p>'''
# end of html.makeBookNavListParagraph


def makeBottom( level:int, pageType:str, state:State ) -> str:
    """
    Create the very bottom part of an HTML page.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeBottom()" )
    assert pageType in KNOWN_PAGE_TYPES, f"{level=} {pageType=}"

    return _makeFooter( level, pageType, state ) + '</body></html>'
# end of html.makeBottom

def _makeFooter( level:int, pageType:str, state:State ) -> str:
    """
    Create any links or site map that follow the main content on the page.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"_makeFooter()" )
    html = f"""<div class="footer">
<p class="copyright"><small><em>{'TEST ' if TEST_MODE else ''}{SITE_NAME}</em> site copyright © 2023-2024 <a href="https://Freely-Given.org">Freely-Given.org</a>.
<br>Python source code for creating these static pages is available <a href="https://GitHub.com/Freely-Given-org/OpenBibleData">here</a> under an <a href="https://GitHub.com/Freely-Given-org/OpenBibleData/blob/main/LICENSE">open licence</a>.{datetime.now().strftime('<br> (Page created: %Y-%m-%d %H:%M)') if TEST_MODE else ''}</small></p>
<p class="copyright"><small>For Bible data copyrights, see the <a href="{'../'*level}allDetails.htm#Top">details</a> for each displayed Bible version.</small></p>
<p class="note"><small>The <em>Open English Translation (OET)</em> main site is at <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</small></p>
</div><!--footer-->"""
    return html
# end of html._makeFooter

def removeDuplicateCVids( BBB:str, html:str ) -> str:
    """
    Where we have OET parallel RV and LV, we get doubled ids like <span id="V6"></span><span class="v" id="C2V6">

    This function removes the second id field in each case (which should be in the LV text).

    Assert statements are disabled because this function can be quite slow for an entire OET book
    """
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Removing duplicate IDs (#CV & #V) for {BBB} ({len(html):,} chars)…" )
    
    endIx = 0 # This is where we start searching
    while True:
        startVIx = html.find( ' id="V', endIx )
        if startVIx == -1: startVIx = 99_999_999
        startCIx = html.find( ' id="C', endIx )
        if startCIx == -1: startCIx = 99_999_999
        startIx = min( startVIx, startCIx )
        if startIx == 99_999_999: break # None / no more
        endIx = html.find( '>', startIx+8 ) # The end of the first id field found -- any duplicates will be AFTER this
        # assert endIx != -1
        idContents = html[startIx:endIx]
        # print( f"    {startIx} {idContents=}")
        # assert 7 < len(idContents) < 14, f"{idContents=} {len(idContents)=}"
        # idCount = html.count( idContents, startIx ) # It's quicker if we don't do this
        # if startIx == startCIx:
        #     assert 1 <= idCount <= 2, f"{BBB} {idContents=} {idCount=} {html}"
        # else: # for #V entries, in large multi-chapter sections there can be several
        #     assert 1 <= idCount <= 5, f"{BBB} {idContents=} {idCount=} {html}"
        # if idCount > 1:
        html = f"{html[:endIx]}{html[endIx:].replace( idContents, '' )}"
            # assert html.count( idContents ) == 1
    return html
# end of html.removeDuplicateCVids


titleRegex = re.compile( 'title="(.+?)"' )
def checkHtml( where:str, htmlToCheck:str, segmentOnly:bool=False ) -> bool:
    """
    Just do some very quick and basic tests
        that our HTML makes some sense.

    Throws an AssertError for any problems.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"checkHtml( {where}, {len(htmlToCheck)} )" )

    if '\n\n' in htmlToCheck:
        ix = htmlToCheck.index( '\n\n' )
        # print( f"checkHtml({where=} {segmentOnly=}) found \\n\\n in …{htmlToCheck[ix-30:ix]}{htmlToCheck[ix:ix+50]}…" )
        raise ValueError( f"checkHtml({where}) found unexpected double newlines in {htmlToCheck=}" )
    if '<br>\n' in htmlToCheck:
        ix = htmlToCheck.index( '<br>\n' )
        # print( f"checkHtml({where=} {segmentOnly=}) found <br> in …{htmlToCheck[ix-30:ix]}{htmlToCheck[ix:ix+50]}…" )
        raise ValueError( f"checkHtml({where}) found <br> followed by unexpected newline in {htmlToCheck=}" )
            
    if 'TCNT' not in where and 'TC-GNT' not in where: # These two versions use the '¦' character in their footnotes
        assert '¦' not in htmlToCheck, f"checkHtml() found unprocessed word number marker in {where} {htmlToCheck=}"

    for marker,startMarker in (('html','<html'),('head','<head>'),('body','<body>')):
        if segmentOnly:
            assert htmlToCheck.count( startMarker ) == htmlToCheck.count( f'</{marker}>' ), htmlToCheck[htmlToCheck.index(startMarker):]
        else:
            assert htmlToCheck.count( startMarker ) == 1, f"checkHtml() found {htmlToCheck.count( startMarker )} '{startMarker}' markers"
            assert htmlToCheck.count( f'</{marker}>' ) == 1

    for marker,startMarker in (('div','<div'),('p','<p '),('h1','<h1'),('h2','<h2'),('h3','<h3'),('em','<em>'),('i','<i>'),('b','<b>'),('sup','<sup>'),('sub','<sub>')):
        startCount = htmlToCheck.count( startMarker )
        if startMarker.endswith( ' ' ): startCount += htmlToCheck.count( f'<{marker}>' )
        endCount = htmlToCheck.count( f'</{marker}>' )
        if startCount != endCount:
            # try: errMsg = f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {html.count(startMarker)}!={html.count(f'</{marker}>')} …{html[html.index(startMarker):]}"
            # except ValueError: errMsg = f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {html.count(startMarker)}!={html.count(f'</{marker}>')} {html[:html.index(f'</{marker}>')]}…"
            # logging.critical( errMsg )
            ixStartMarker = htmlToCheck.find( startMarker )
            ixEndMarker = htmlToCheck.find( f'</{marker}>' )
            ixMinStart = min( 9999999 if ixStartMarker==-1 else ixStartMarker, 9999999 if ixEndMarker==-1 else ixEndMarker )
            ixRStartMarker = htmlToCheck.rfind( startMarker )
            ixREndMarker = htmlToCheck.rfind( f'</{marker}>' )
            ixMinEnd = min( ixRStartMarker, ixREndMarker )
            logging.critical( f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {startCount}!={endCount}"
                              f" {'…' if ixMinStart>0 else ''}{htmlToCheck[ixMinStart:ixMinEnd+5]}{'…' if ixMinEnd+5<len(htmlToCheck) else ''}" )
            if DEBUGGING_THIS_MODULE: print( f"\ncheckHtml: complete {htmlToCheck=}\n")
            return False

    if '\n<br></p>' in htmlToCheck or '\n<br></span>' in htmlToCheck:
        logging.critical( f"{where}' {segmentOnly=} has wasted <br> in {htmlToCheck=} THIS IS BEING CHANGED!!!" )
        htmlToCheck = htmlToCheck.replace( '\n<br></span></span></p>', '</span></span></p>' ).replace( '\n<br></span></p>', '</span></p>' ).replace( '\n<br></p>', '</p>' )

    # Check for illegal characters in title popups
    searchStartIndex = 0
    while True: # Look for links that we could maybe liven
        match = titleRegex.search( htmlToCheck, searchStartIndex )
        if not match:
            break
        titleAttributeGuts = match.group(1)
        assert '\n' not in titleAttributeGuts, f"Bad title attribute with newline in {htmlToCheck=}"
        assert '<br' not in titleAttributeGuts, f"Bad title attribute with BR in {htmlToCheck=}"
        assert '<span' not in titleAttributeGuts, f"Bad title attribute with SPAN in {htmlToCheck=}"
        searchStartIndex = match.end()

    return True
# end of html.checkHtml


def do_OET_RV_HTMLcustomisations( OET_RV_html:str ) -> str:
    """
    OET-RV is formatted in paragraphs.
    """
    return (OET_RV_html \
            # Adjust specialised add markers
            .replace( '<span class="add">', '<span class="RVadd">' )
            )
# end of html.do_OET_RV_HTMLcustomisations


digitPunctDigitRegex = re.compile( '[0-9][:.][0-9]' )
def do_OET_LV_HTMLcustomisations( OET_LV_html:str ) -> str:
    """
    OET-LV is often formatted as a new line for each sentence.

    We have to protect fields like periods in '../C2_V2.htm' from corruption
        (and then restore them again of course).
    """
    assert '<br>\n' not in OET_LV_html
    assert '\n<br></p>' not in OET_LV_html and '\n<br></span>' not in OET_LV_html, f"Wasted <br> in {OET_LV_html=}"

    # Preserve the colon in times like 12:30 and in C:V and v0.1 fields
    searchStartIndex = 0
    while True: # Look for links that we could maybe liven
        match = digitPunctDigitRegex.search( OET_LV_html, searchStartIndex )
        if not match:
            break
        guts = match.group(0) # Entire match
        assert len(guts)==3 and (guts.count(':') + guts.count('.'))==1
        OET_LV_html = f'''{OET_LV_html[:match.start()]}{guts.replace(':','~~COLON~~',1).replace('.','~~PERIOD~~',1)}{OET_LV_html[match.end():]}'''
        searchStartIndex = match.end() + 8 # We've added that many characters

    OET_LV_html = (OET_LV_html \
            # Protect fields we need to preserve
            .replace( '<!--', '~~COMMENT~~' ).replace( '_V', '~~V' )
            .replace( '../', '~~PERIOD~~~~PERIOD~~/' )
            .replace( '.htm', '~~PERIOD~~htm' ).replace( 'https:', 'https~~COLON~~' )
            .replace( '.org', '~~PERIOD~~org' ).replace( '.tsv', '~~PERIOD~~tsv' )
            # .replace( 'v0.', 'v0~~PERIOD~~' )
            .replace( '.\\f*', '~~PERIOD~~\\f*' ).replace( 'Note:', 'Note~~COLON~~').replace( '."', '~~PERIOD~~"' ) # These last two are inside the footnote callers
            # In <hr>
            .replace( 'width:', 'width~~COLON~~' ).replace( 'margin-left:', 'margin-left~~COLON~~' ).replace( 'margin-top:', 'margin-top~~COLON~~' )
            # Make each sentence start a new line
            .replace( '.', '.\n<br>' ).replace( '?', '?\n<br>' )
            .replace( '!', '!\n<br>' ).replace( ':', ':\n<br>' )
            # Adjust specialised add markers
            .replace( '<span class="add">+', '<span class="addArticle">' )
            .replace( '<span class="add">-', '<span class="unusedArticle">' )
            .replace( '<span class="add">=', '<span class="addCopula">' )
            .replace( '<span class="add">~', '<span class="addDirectObject">' )
            .replace( '<span class="add">>', '<span class="addExtra">' )
            .replace( '<span class="add">^', '<span class="addOwner">' )
            # Put all underlines into a span with a class (then we will have a button to hide them)
            .replace( '="', '~~EQUAL"' ) # Protect class=, id=, etc.
            .replace( '=', '_' ).replace( '÷', '_' ) # For OT morphemes
            .replace( '~~EQUAL"', '="' ) # Unprotect class=, id=, etc.
            .replace( '_', '<span class="ul">_</span>')
            # Now unprotect everything again
            .replace( '--fnUNDERLINE--', '_' ).replace( '--fnEQUAL--', '=' ).replace( '--fnCOLON--', ':' ).replace( '--fnPERIOD--', '.' ) # Unprotect sanitised footnotes (see usfm.py)
            .replace( '~~COMMENT~~', '<!--' ).replace( '~~V', '_V' )
            .replace( '~~COLON~~', ':' ).replace( '~~PERIOD~~', '.' )
            # TODO: Not sure that this is the best place to do this next one for the OT
            .replace( ' DOM ',' <span class="dom">DOM</span> ')
            )
    # TODO: I was unable to figure out why this is happening to one particular exegesis footnote in 2 Kings 6:25
    # assert '\n<br></p>' not in OET_LV_html and '\n<br></span>' not in OET_LV_html, f"Wasted <br> in {OET_LV_html=}"
    OET_LV_html = OET_LV_html.replace( '\n<br></span></span></p>', '</span></span></p>' ).replace( '\n<br></span></p>', '</span></p>' ).replace( '\n<br></p>', '</p>' )

    # Tidyup
    if OET_LV_html.endswith( '\n' ): OET_LV_html = OET_LV_html[:-1] # We don't end our html with a newline
    if OET_LV_html.endswith( '<br>' ):
        OET_LV_html = OET_LV_html[:-4] # We don't end our html with a newline
        if OET_LV_html[-1] == '\n': OET_LV_html = OET_LV_html[:-1] # We don't end our html with a newline

    # assert '+' not in html, f"{html[html.index('+')-20:html.index('+')+30]}"
    # assert '^' not in html, f"{html[html.index('^')-20:html.index('^')+30]}"
    # assert '<span class="add">' not in html, f'''{html[html.index('<span class="add">')-20:html.index('<span class="add">')+50]}'''
    return OET_LV_html
# end of html.do_OET_LV_HTMLcustomisations


def do_LSV_HTMLcustomisations( LSV_html:str ) -> str:
    """
    LSV has lines like:
        v 7 “\\w Blessed|strong="G3107"\\w* [\\w are|strong="G3588"\\w*] \\w they|strong="G2532"\\w* \\w whose|strong="G3739"\\w* lawless \\w acts|strong="G4160"\\w* \\w were|strong="G3588"\\w* forgiven, || \\w And|strong="G2532"\\w* \\w whose|strong="G3739"\\w* \\w sins|strong="G3900"\\w* \\w were|strong="G3588"\\w* \\w covered|strong="G1943"\\w*;

    We need to change the two parallel lines to <br>.
    """
    return LSV_html.replace( ' || ', '<br>' ).replace( '||', '<br>' ) # Second one catches any source inconsistencies
# end of html.do_LSV_HTMLcustomisations


def do_T4T_HTMLcustomisations( T4T_html:str ) -> str:
    """
    T4T has:
        We have tried to indicate the beginning of an alternative by a ‘◄’ and the ending of each alternative by a ‘►’.
        We have identified the different figures of speech where each occurs in the text, but these symbols are hidden in the data-file.
            [APO] = apostrophe
            [CHI] = chiasmus
            [DOU] = doublet
            [EUP] = euphemism
            [HEN] = hendiadys
            [HYP] = hyperbole
            [IDM] = idiom
            [IRO] = irony
            [LIT] = litotes
            [MET] = metaphor
            [MTY] = metonymy
            [PRS] = personification
            [RHQ] = rhetorical question
            [SIM] = simile
            [SYM] = symbol
            [SAR] = sarcasm
            [SYN] = synecdoche
            [TRI] = triple
    """
    for FoS,fosType in ( ('APO','apostrophe'), ('CHI','chiasmus'), ('DOU','doublet'), ('EUP','euphemism'),
                         ('HEN','hendiadys'), ('HYP','hyperbole'), ('IDM','idiom'), ('IRO','irony'), ('LIT','litotes'),
                         ('MET','metaphor'), ('MTY','metonymy'), ('PRS','personification'), ('RHQ','rhetorical question'),
                         ('SIM','simile'), ('SYM','symbol'), ('SAR','sarcasm'), ('SYN','synecdoche'), ('TRI','triple') ):
        fullFoS = f'[{FoS}]'
        T4T_html = T4T_html.replace( fullFoS, f'<span class="FoS" title="{fosType} (figure of speech)">{fullFoS}</span>' )
    return T4T_html.replace( '◄', '<span title="alternative translation">◄</span>' )
# end of html.do_T4T_HTMLcustomisations


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
