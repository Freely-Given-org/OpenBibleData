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
removeDuplicateCVids( html:str ) -> str
removeDuplicateFNids( where:str, html:str ) -> str
checkHtml( where:str, htmlToCheck:str, segmentOnly:bool=False ) -> bool
checkHtmlForMissingStyles( where:str, htmlToCheck:str ) -> bool
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
    2024-05-15 Added HTML/CSS style matching checks
    2024-07-19 Added HTML class, id, and title validity checks and missed add processing checks
    2024-10-24 Added title pop-ups on added text classes
    2024-10-31 Added more Hebrew parallelism options
    2024-11-01 Added topic pages
"""
# from gettext import gettext as _
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime
import re
from collections import defaultdict

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27

from settings import State, TEST_MODE, SITE_NAME
from OETHandlers import getBBBFromOETBookName


LAST_MODIFIED_DATE = '2024-11-13' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.91'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
# NARROW_NON_BREAK_SPACE = ' '


KNOWN_PAGE_TYPES = ('site', 'TopIndex', 'details', 'AllDetails',
                    'book','bookIndex', 'chapter','chapterIndex', 'section','sectionIndex',
                    'relatedPassage','relatedSectionIndex',
                    'topicPassages','topicsIndex',
                    'parallelVerse', 'interlinearVerse',
                    'dictionaryMainIndex','dictionaryLetterIndex','dictionaryEntry','dictionaryIntro',
                    'word','lemma','morpheme', 'person','location', 'statistics',
                    'wordIndex','lemmaIndex','morphemeIndex', 'personIndex','locationIndex',
                        'statisticsIndex', 'referenceIndex',
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
    elif pageType == 'topicPassages':
        cssFilename = 'TopicalPassages.css'
    elif pageType == 'parallelVerse':
        cssFilename = 'ParallelVerses.css'
    elif pageType == 'interlinearVerse':
        cssFilename = 'InterlinearVerse.css'
    elif pageType in ('word','lemma','morpheme', 'person','location'):
        cssFilename = 'BibleWord.css'
    elif pageType in ('dictionaryLetterIndex', 'dictionaryEntry','dictionaryIntro'):
        cssFilename = 'BibleDict.css'
    elif pageType in ('site', 'details','AllDetails', 'search', 'about', 'news', 'OETKey', 'TopIndex',
                      'statistics',
                      'bookIndex','chapterIndex','sectionIndex',
                      'relatedSectionIndex', 'topicsIndex', 'dictionaryMainIndex',
                      'wordIndex','lemmaIndex','morphemeIndex','personIndex','locationIndex','statisticsIndex','referenceIndex' ):
        cssFilename = 'BibleSite.css'
    else: unexpected_page_type

    homeLink = f"{SITE_NAME}{' TEST' if TEST_MODE else ''} Home" if pageType=='TopIndex' else f'''<a href="{'../'*level}index.htm#Top">{SITE_NAME}{' TEST' if TEST_MODE else ''} Home</a>'''
    aboutLink = 'About' if pageType=='about' else f'''<a href="{'../'*level}About.htm#Top">About</a>'''
    newsLink = 'News' if pageType=='news' else f'''<a href="{'../'*level}News.htm#Top">News</a>'''
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
  __SCRIPT__
</head>
<body><!--Level{level}-->{topLink}
"""
    # Insert second stylesheet if required
    if pageType == 'OETKey':
        top = top.replace( '__SCRIPT__', f'''<link rel="stylesheet" type="text/css" href="{'../'*level}OETChapter.css">\n  __SCRIPT__''' )
    # Insert javascript file(s) if required
    if (versionAbbreviation and 'OET' in versionAbbreviation) \
    or pageType in ('parallelVerse','topicPassages'):
        top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}Bible.js"></script>\n  __SCRIPT__''' )
    if 'Dict' in cssFilename or 'Word' in cssFilename \
    or pageType in ('chapter','section','book','parallelVerse','interlinearVerse','relatedPassage'):
        top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}KB.js"></script>\n  __SCRIPT__''' )
    top = top.replace( '\n  __SCRIPT__', '' )

    return f'{top}{_makeNavigationLinks( level, versionAbbreviation, pageType, versionSpecificFileOrFolderName, state )}'
# end of html.makeTop

def _makeNavigationLinks( level:int, versionAbbreviation:str, pageType:str, versionSpecificFileOrFolderName:Optional[str], state:State ) -> str:
    """
    Create the navigation that goes before the page content.

    This includes the list of versions, and possibly the "ByDocument/BySection" bar as well.
        (It doesn't include book, chapter, or verse selector bars.)

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_makeNavigationLinks( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )

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
    else: # add a link for related
        initialVersionList.append( f'''{state.BibleVersionDecorations['Related'][0]}<a title="Single OET-RV section with related verses from other books" href="{'../'*level}rel/">Related</a>{state.BibleVersionDecorations['Related'][1]}''' )
    if pageType in ('topicPassages','topicsIndex'):
        initialVersionList.append( 'Topics' )
    else: # add a link for topics
        initialVersionList.append( f'''{state.BibleVersionDecorations['Topics'][0]}<a title="Collections of OET passages organised by topic" href="{'../'*level}tpc/">Topics</a>{state.BibleVersionDecorations['Topics'][1]}''' )
    if pageType == 'parallelVerse':
        initialVersionList.append( 'Parallel' )
    else: # add a link for parallel
        initialVersionList.append( f'''{state.BibleVersionDecorations['Parallel'][0]}<a title="Single verse in many different translations" href="{'../'*level}par/">Parallel</a>{state.BibleVersionDecorations['Parallel'][1]}''' )
    if pageType == 'interlinearVerse':
        initialVersionList.append( 'Interlinear' )
    else: # add a link for interlinear
        initialVersionList.append( f'''{state.BibleVersionDecorations['Interlinear'][0]}<a title="Single verse in interlinear word view" href="{'../'*level}ilr/">Interlinear</a>{state.BibleVersionDecorations['Interlinear'][1]}''' )
    if pageType == 'referenceIndex':
        initialVersionList.append( 'Reference' )
    else: # add a link for reference
        initialVersionList.append( f'''{state.BibleVersionDecorations['Reference'][0]}<a title="Reference index" href="{'../'*level}ref/">Reference</a>{state.BibleVersionDecorations['Reference'][1]}''' )
    if pageType == 'dictionaryMainIndex':
        initialVersionList.append( 'Dictionary' )
    else: # add a link for dictionary
        initialVersionList.append( f'''{state.BibleVersionDecorations['Dictionary'][0]}<a title="Dictionary index" href="{'../'*level}dct/">Dictionary</a>{state.BibleVersionDecorations['Dictionary'][1]}''' )
    if pageType == 'search':
        initialVersionList.append( 'Search' )
    else: # add a link for search
        initialVersionList.append( f'''{state.BibleVersionDecorations['Search'][0]}<a title="Find Bible words" href="{'../'*level}Search.htm">Search</a>{state.BibleVersionDecorations['Search'][1]}''' )

    # This code tries to adjust links to books which aren't in a version, e.g., UHB has no NT books, SR-GNT and UGNT have no OT books
    # It does this by adjusting the potential bad link to the next level higher.
    newVersionList = []
    for entry in initialVersionList:
        # if pageType == 'parallelVerse':
        #     print( f"  _makeNavigationLinks processing {entry=} ({level=} {versionAbbreviation=} {pageType=} {fileOrFolderName=})" )
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
    and versionAbbreviation not in ('TOSN','TTN','TOBD','UTN','UBS','THBD','BMM') \
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
# end of html._makeNavigationLinks


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
                else getBBBFromOETBookName( displayText ) )
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
<br>Python source code for creating these static pages is available <a href="https://GitHub.com/Freely-Given-org/OpenBibleData">on GitHub</a> under an <a href="https://GitHub.com/Freely-Given-org/OpenBibleData/blob/main/LICENSE">open licence</a>.{datetime.now().strftime('<br> (Page created: %Y-%m-%d %H:%M)') if TEST_MODE else ''}</small></p>
<p class="copyright"><small>For Bible data copyrights, see the <a href="{'../'*level}AllDetails.htm#Top">details</a> for each displayed Bible version.</small></p>
<p class="note"><small>The <em>Open English Translation (OET)</em> main site is at <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</small></p>
</div><!--footer-->"""
    return html
# end of html._makeFooter

def removeDuplicateCVids( html:str ) -> str:
    """
    Where we have OET parallel RV and LV, we get doubled ids like <span id="V6"></span><span class="v" id="C2V6">

    This function removes the second id field in each case (which should be in the LV text).

    # Assert statements are disabled because this function can be quite slow for an entire OET book
    """
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Removing duplicate IDs (#CV & #V) for ({len(html):,} chars)…" )

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
        endHtml = html[endIx:]
        # NOTE: In a section that includes multiple chapters, we might have multiple 'id="V1"'s
        # print( f"removeDuplicateCVids {BBB} {idContents=} {startIx=} {endIx=}" )
        while (endHtmlStartIx := endHtml.find( idContents ) ) != -1:
            # if endHtmlStartIx == -1: continue # No duplicate found
            # print( f"removeDuplicateCVidsA {endHtmlStartIx=} '{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}'" )
            if ( (idContents.startswith( ' id="C' ) and 'V' not in idContents) # don't want ' id="C1V1'
            or idContents.startswith( ' id="V' ) ): # Only in side-by-side chapters (not in entire books)
                # then from something like '<span id="C123"></span>', if we delete the id bit, we get useless '<span></span>'
                #   so let's delete the whole lot
                assert endHtml[endHtmlStartIx-5:endHtmlStartIx] == '<span', f"{endHtml[endHtmlStartIx-5:endHtmlStartIx]=}"
                assert endHtml[endHtmlStartIx+len(idContents):endHtmlStartIx+len(idContents)+8] == '></span>', f"{endHtml[endHtmlStartIx+len(idContents):endHtmlStartIx+len(idContents)+8]=}"
                endHtml = f'{endHtml[:endHtmlStartIx-5]}{endHtml[endHtmlStartIx+len(idContents)+8:]}'
                html = f'{html[:endIx]}{endHtml}'
                # assert '<span></span>' not in html
                # print( f"removeDuplicateCVidsB {endHtmlStartIx=}\nendHtml='…{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}…'\nhtml='…{html[endIx+endHtmlStartIx-50:endIx+endHtmlStartIx+50]}…'" )
            else:
                endHtml = f'{endHtml[:endHtmlStartIx]}{endHtml[endHtmlStartIx+len(idContents):]}'
                html = f'{html[:endIx]}{endHtml}'
                # assert '<span></span>' not in html
                # print( f"removeDuplicateCVidsC {endHtmlStartIx=}\nendHtml='…{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}…'\nhtml='…{html[endIx+endHtmlStartIx-50:endIx+endHtmlStartIx+50]}…'" )
        assert html.count( idContents ) == 1, f"{idContents=} {html.count(idContents)=}"

    assert '<span></span>' not in html # it used to be there when we deleted id fields from the already empty spans
    return html
# end of html.removeDuplicateCVids

def removeDuplicateFNids( where:str, html:str ) -> str:
    """
    Where we have translated or transliterated footnotes (in parallel verse displays),
        we get doubled ids like <p class="fn" id="fnClVg1">

    This function removes the second id field in each case (which should be in the translated/transliterated footnote).

    # Assert statements are disabled because this function can be quite slow for an entire OET book
    """
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Removing duplicate footnote IDs for {where} ({len(html):,} chars)…" )

    endIx = 0 # This is where we start searching
    while True:
        startIx = html.find( ' id="fn', endIx )
        if startIx == -1: break # None / no more
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
        endHtml = html[endIx:]
        # NOTE: In a section that includes multiple chapters, we might have multiple 'id="V1"'s
        # print( f"removeDuplicateFNids {BBB} {idContents=} {startIx=} {endIx=}" )
        while (endHtmlStartIx := endHtml.find( idContents ) ) != -1:
            # if endHtmlStartIx == -1: continue # No duplicate found
            # print( f"removeDuplicateFNidsA {endHtmlStartIx=} '{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}'" )
            endHtml = f'{endHtml[:endHtmlStartIx]}{endHtml[endHtmlStartIx+len(idContents):]}'
            html = f'{html[:endIx]}{endHtml}'
            # assert '<span></span>' not in html
            # print( f"removeDuplicateFNidsC {endHtmlStartIx=}\nendHtml='…{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}…'\nhtml='…{html[endIx+endHtmlStartIx-50:endIx+endHtmlStartIx+50]}…'" )
        assert html.count( idContents ) == 1, f"{idContents=} {html.count(idContents)=}"

    return html
# end of html.removeDuplicateFNids


classAttributeRegex = re.compile( 'class="(.+?)"' )
idAttributeRegex = re.compile( 'id="(.+?)"' )
titleAttributeRegex = re.compile( 'title="(.+?)"' )
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

    if ( 'TCNT' not in where and 'TC-GNT' not in where  # These two versions use the '¦' character in their footnotes
    and not where.startswith('Parallel ') and not where.startswith('End of parallel') ): # and they also appear on parallel pages
        assert '¦' not in htmlToCheck, f"checkHtml() found unprocessed word number marker in '{where}' {htmlToCheck=}"

    for marker,startMarker in (('html','<html'),('head','<head'),('body','<body')):
        if segmentOnly:
            assert htmlToCheck.count( startMarker ) == htmlToCheck.count( f'</{marker}>' ), htmlToCheck[htmlToCheck.index(startMarker):]
        else:
            assert htmlToCheck.count( startMarker ) == 1, f"checkHtml() found {htmlToCheck.count( startMarker )} '{marker}' markers in '{where}'"
            assert htmlToCheck.count( f'</{marker}>' ) == 1

    if ('ULT' not in where and 'UST' not in where
    and 'OEB' not in where
    # Parallel pages
    and 'PSA' not in where # uW really messes up \\qs Selah\\qs* amongst other things
    and 'JOB' not in where # UST I think
    and 'PRO' not in where # UST I think
    and 'JOL' not in where # UST I think
    and 'MAT' not in where # UST I think
    and 'ROM' not in where # Maybe AICNT Rom 9:32, but probably UST
    and 'CO2' not in where # Maybe AICNT 2 Cor 8:22, but probably UST
    and 'GAL' not in where # Maybe AICNT Gal 2:2, but probably UST
    and 'HEB' not in where # Heb 4:3
    and 'REV' not in where # Rev 2:9
    # and 'JOB_17:5' not in where # UST I think
    # and 'JOB_24:18' not in where # UST maybe or BSB???
    # and 'JOB_29:12' not in where # UST maybe or BSB???
    # and 'JOB_30:26' not in where # UST maybe or BSB???
    # and 'JOB_30:26' not in where # UST maybe or BSB???
    ):
        # Check (nested) spans
        spanNestingLevel = searchStartIndex = 0
        while True:
            # print( f"{spanNestingLevel=} {searchStartIndex=} {len(htmlToCheck)=}")
            spanIx = htmlToCheck.find( '<span', searchStartIndex )
            if spanIx == -1: spanIx = 99_999_999
            endSpanIx = htmlToCheck.find( '</span>', searchStartIndex )
            if endSpanIx == -1: endSpanIx = 99_999_999
            if spanIx == endSpanIx: # No more spans or end spans
                assert spanIx == 99_999_999
                break
            elif spanIx < endSpanIx: # it's a new span
                assert spanNestingLevel < 8, f"Too many nested spans {spanNestingLevel} '{where}' {segmentOnly=} {htmlToCheck=}"
                spanNestingLevel += 1
                # print( f"Found new span in '{where}' {segmentOnly=} '{'' if spanIx==0 else '…'}{htmlToCheck[spanIx:spanIx+200]}…'"
                #             if spanNestingLevel == 1 else
                #        f"Found nested level{spanNestingLevel} span in '{where}' {segmentOnly=} '{'' if spanIx==0 else '…'}{htmlToCheck[spanIx:spanIx+200]}…' then …{htmlToCheck[lastSpanIx:lastSpanIx+200]}" )
                lastSpanIx = spanIx
                searchStartIndex = spanIx + 7
            else: # endSpanIx < spanIx
                assert spanNestingLevel > 0, f"Extra close span in '{where}' {segmentOnly=} '{'' if endSpanIx==0 else '…'}{htmlToCheck[endSpanIx:endSpanIx+200]}…'"
                spanNestingLevel -= 1
                searchStartIndex = endSpanIx + 7
        assert spanNestingLevel==0, f"Unclosed span in '{where}' {segmentOnly=} '{'' if lastSpanIx==0 else '…'}{htmlToCheck[lastSpanIx:lastSpanIx+200]}…' FROM {htmlToCheck=}"

    if not segmentOnly or '<span class="add"><' not in htmlToCheck: # < is one of our add field sub-classifiers
        assert '<<' not in htmlToCheck, f"<span> '{where}' {segmentOnly=} …{htmlToCheck[htmlToCheck.index('<<')-180:htmlToCheck.index('<<')+180]}…"
    if not segmentOnly or '<span class="add">>' not in htmlToCheck: # > is one of our add field sub-classifiers
        if where not in ('UTN ZEP_1:0','Parallel ZEP_1:0'):
            assert '>>' not in htmlToCheck, f"<span> '{where}' {segmentOnly=} …{htmlToCheck[htmlToCheck.index('>>')-180:htmlToCheck.index('>>')+180]}…"
    assert '<span>' not in htmlToCheck, f"<span> '{where}' {segmentOnly=} …{htmlToCheck[htmlToCheck.index('<span>')-180:htmlToCheck.index('<span>')+180]}…"
    assert '>span class' not in htmlToCheck, f"'>span class' '{where}' {segmentOnly=} …{htmlToCheck[htmlToCheck.index('>span class')-180:htmlToCheck.index('>span class')+180]}…"
    for marker,startMarker in (('div','<div'),('p','<p '),('h1','<h1'),('h2','<h2'),('h3','<h3'),('h4','<h4'),
                               ('span','<span'),
                               ('ol','<ol'),('ul','<ul'),
                               ('em','<em>'),('i','<i>'),('b','<b>'),('small','<small '),('sup','<sup>'),('sub','<sub>')):
        startCount = htmlToCheck.count( startMarker )
        if startMarker.endswith( ' ' ): startCount += htmlToCheck.count( f'<{marker}>' )
        endMarker = f'</{marker}>'
        endCount = htmlToCheck.count( endMarker )
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
            logging.error( f"Mismatched '{marker}' start and end markers '{where}' {segmentOnly=} {startCount}!={endCount}"
                              f" {'…' if ixMinStart>0 else ''}{htmlToCheck[ixMinStart:ixMinEnd+5]}{'…' if ixMinEnd+5<len(htmlToCheck) else ''}" )
            if DEBUGGING_THIS_MODULE:
                print( f"\nMismatched '{marker}' start and end markers '{where}' {segmentOnly=} {startCount}!={endCount}"
                              f" {'…' if ixMinStart>0 else ''}{htmlToCheck[ixMinStart:ixMinEnd+5]}{'…' if ixMinEnd+5<len(htmlToCheck) else ''}" )
                print( f"checkHtml: complete {htmlToCheck=}\n")
            if TEST_MODE and ('JOB' not in where and 'OEB' not in where # why are these bad???
            and 'UTN' not in where and 'ULT' not in where
            and 'Parallel' not in where and 'Interlinear' not in where ): # Probably it's in UTN on parallel and interlinear pages
                print( f"'{where}' {segmentOnly=} {marker=} Bad html = {htmlToCheck=}")
                print( f"'{where}' {segmentOnly=} {marker=} {startMarker=} {startCount=} {endCount=}")
                if 'book' not in where.lower():
                    if 'ULT' not in where and 'UST' not in where and 'PSA' not in where: # UST PSA has totally messed up \\qs encoding
                        halt
            return False
        # Checked for accidentally doubled nesting
        if startMarker.endswith( '>' ):
            assert f'{startMarker}{startMarker}' not in htmlToCheck, f"Doubled {startMarker} in {where}' {segmentOnly=}"
            assert f'{startMarker} {startMarker}' not in htmlToCheck, f"Doubled {startMarker} in {where}' {segmentOnly=}"
        if marker not in ('span','div'): # nested spans and divs are ok
            assert f'{endMarker}{endMarker}' not in htmlToCheck, f"Doubled end {endMarker} in {where}' {segmentOnly=}"
            assert f'{endMarker} {endMarker}' not in htmlToCheck, f"Doubled end {endMarker} in {where}' {segmentOnly=}"

    # Should be no <a ...> anchors embedded inside other anchors
    if not segmentOnly or '<span class="add"><a ' not in htmlToCheck: # Temporary fields can confuse our check, e.g., '<span class="add"><a word</span>'
        searchStartIndex = 0
        while True:
            aIx = htmlToCheck.find( '<a ', searchStartIndex )
            if aIx == -1: break
            endIx = htmlToCheck.index( '</a>', aIx+3 )
            nextAIx = htmlToCheck.find( '<a ', aIx+3 )
            if nextAIx != -1:
                assert endIx < nextAIx, f"Nested anchors in '{where}' {segmentOnly=} '{'' if aIx==0 else '…'}{htmlToCheck[aIx:aIx+200]}…'"
            searchStartIndex = endIx + 4

    if '<li>' in htmlToCheck or '<li ' in htmlToCheck or '</li>' in htmlToCheck:
        assert '<ol>' in htmlToCheck or '<ol ' in htmlToCheck or '<ul>' in htmlToCheck or '<ul ' in htmlToCheck
        assert '</ol>' in htmlToCheck or '</ul>' in htmlToCheck

    if '\n<br></p>' in htmlToCheck or '\n<br></span>' in htmlToCheck:
        logging.warning( f"checkHtml '{where}' {segmentOnly=} needed to fix wasted <br> in {htmlToCheck=}" )
        htmlToCheck = htmlToCheck.replace( '\n<br></span></span></p>', '</span></span></p>' ).replace( '\n<br></span></p>', '</span></p>' ).replace( '\n<br></p>', '</p>' )
    if '\n</a>' in htmlToCheck:
        logging.critical( f"'{where}' {segmentOnly=} has unexpected newline before anchor close in {htmlToCheck=}" )
        halt

    # Check classes
    searchStartIndex = 0
    while True:
        match = classAttributeRegex.search( htmlToCheck, searchStartIndex )
        if not match:
            break
        classGuts = match.group(1) # might be something like 'KJB-1611_verseTextChunk'
        assert len(classGuts) <= 23, f"'{where}' {segmentOnly=} class is too long ({len(classGuts)}) {classGuts=}"
        assert '\n' not in classGuts, f"'{where}' {segmentOnly=} Bad class with newline in {classGuts=} FROM {htmlToCheck=}"
        assert '<' not in classGuts, f"'{where}' {segmentOnly=} Bad class with < in {classGuts=} FROM {htmlToCheck=}"
        assert '>' not in classGuts, f"'{where}' {segmentOnly=} Bad class with > in {classGuts=} FROM {htmlToCheck=}"
        searchStartIndex = match.end()

    # Check IDs
    idDict = {} # Used to make sure that they're all unique
    searchStartIndex = 0
    while True:
        match = idAttributeRegex.search( htmlToCheck, searchStartIndex )
        if not match:
            break
        idGuts = match.group(1) # might be something like 'C18V27' or 'BottomTransliterationsButton' or Tyndale dict 'The18thand19thCenturiesNewDiscoveriesofEarlierManuscriptsandIncreasedKnowledgeoftheOriginalLanguages'
        assert len(idGuts) <= (100 if where=='DictionaryArticle' else 28), f"'{where}' {segmentOnly=} id is too long ({len(idGuts)}) {idGuts=}"
        assert ' ' not in idGuts, f"'{where}' {segmentOnly=} Bad id with space in {idGuts=} FROM {htmlToCheck=}"
        assert '\n' not in idGuts, f"'{where}' {segmentOnly=} Bad id with newline in {idGuts=} FROM {htmlToCheck=}"
        assert '<' not in idGuts, f"'{where}' {segmentOnly=} Bad id with < in {idGuts=} FROM {htmlToCheck=}"
        assert '>' not in idGuts, f"'{where}' {segmentOnly=} Bad id with > in {idGuts=} FROM {htmlToCheck=}"
        if 'OEB' not in where and 'Moff' not in where and 'Wycl' not in where: # OEB SNG,JER and Moff PSA and Wyc SA2 have verse number problems
            assert idGuts not in idDict, f''''{where}' {segmentOnly=} Duplicate id="{idGuts}" FROM ‘…{htmlToCheck[max(0,idDict[idGuts][0]-300):idDict[idGuts][1]+300]}…’ THEN FROM ‘…{htmlToCheck[match.start()-300:match.end()+300]}…’'''
        idDict[idGuts] = (match.start(),match.end())
        searchStartIndex = match.end()
    del idDict

    # Check for illegal characters in title popups
    searchStartIndex = 0
    while True:
        match = titleAttributeRegex.search( htmlToCheck, searchStartIndex )
        if not match:
            break
        titleGuts = match.group(1) # Can be an entire footnote or can be a parsing of a word (with some fields still expanded like --fnColon--)
        assert len(titleGuts) <= (1010 if titleGuts.startswith('Note') or titleGuts.startswith('Variant note') or 'NET' in where or 'TCNT' in where or 'TC-GNT' in where or 'T4T' in where or 'Parallel' in where or 'End of parallel' in where else 150), f"'{where}' {segmentOnly=} title is too long ({len(titleGuts)}) {titleGuts=}"
        assert '\n' not in titleGuts, f"'{where}' {segmentOnly=} Bad title with newline in {titleGuts=} FROM {htmlToCheck=}"
        assert '<br' not in titleGuts, f"'{where}' {segmentOnly=} Bad title with BR in {titleGuts=} FROM {htmlToCheck=}"
        assert '<span' not in titleGuts, f"'{where}' {segmentOnly=} Bad title with SPAN in {titleGuts=} FROM {htmlToCheck=}"
        searchStartIndex = match.end()

    assert '<span class="nd"><span class="nd">' not in htmlToCheck, f"""'{where}' {segmentOnly=} Found {htmlToCheck.count('<span class="nd"><span class="nd">')} doubled ND spans in {htmlToCheck}""" # in case we accidentally apply it twice

    if segmentOnly:
        return True

    # The following are not actual HTML errors, but rather, our own processing errors
    #   (We don't check segments, because some of these things are processed later on)
    if 'OET' in where or 'Parallel' in where:
        for char,reason in (('+','added article'),('-','dropped article'),('=','added copula'),('>','implied object'),
                    ('≡','repeat ellided'),('≡','repeat ellided'),('&','added ownwer'),('@','expanded pronoun'),('*','reduced to pronoun'),
                    ('#','changed number'),('^','used opposite'),('≈','reworded'),('?','unsure'),):
            if 'NAH_2:7' not in where and 'GAL_5:10' not in where \
            and 'CO1_10:24' not in where and 'EPH_2:22' not in where: # LEB has 'added text' starting with '='   :)
                assert f'<span class="add">{char}' not in htmlToCheck, f''''{where}' {segmentOnly=} Missed ADD {reason} in …{htmlToCheck[max(0,htmlToCheck.index(f'<span class="add">{char}')-50):htmlToCheck.index(f'<span class="add">{char}')+100]}…'''
        # We have to check this one separately: ('<','implied direct object') because it might be the start of the next field
        searchStartIndex = 0
        while True:
            try: ix = htmlToCheck.index( '<span class="add"><', searchStartIndex )
            except ValueError: # substring not found
                break
            next = htmlToCheck[ix+18:ix+50]
            if not next.startswith( '<a title=' ) and not next.startswith( '<span ' ):
                raise ValueError( f"Unprocessed add field with {next=} '{where}' {segmentOnly=}" )
            searchStartIndex = ix + 18

    # See if all our classes/styles exist in the stylesheet
    result = checkHtmlForMissingStyles( where, htmlToCheck )
    if where == 'TopIndex': # that's the final page that we build
        # so we output extra info here
        for mm,msg in enumerate( collectedMsgs, start=1 ):
            logging.critical( f"Missing CSS style {mm}/{len(collectedMsgs)}: {msg}" )
        if not TEST_MODE:
            for someStylesheetName,someStyleDict in cachedStyleDicts.items():
                unusedList = [sdKey[5:] for sdKey,sdValue in someStyleDict.items() if sdKey.startswith( 'used_') and not sdValue]
                if unusedList:
                    logging.warning( f"UNUSED STYLES in {someStylesheetName} were ({len(unusedList)})/({len(someStyleDict)}) {unusedList=}" )

    return result
# end of html.checkHtml

classRegex = re.compile( '<([^>]+?) [^>]*?class="([^>"]+?)"' )
cachedStyleDicts = {}
collectedMsgs = []
def checkHtmlForMissingStyles( where:str, htmlToCheck:str ) -> bool:
    """
    Given an html page,
        determine the stylesheet and load it if not already cached,
        and then check that all classes are in the stylesheet.
    """
    def loadCSSStyles( lsStylesheetName:str ) -> Dict[str,Union[bool,List[str]]]:
        """
        Load the stylesheet and cache it for next time.

        Adds a used_{} entry (set to False) so we can set at the end,
            which stylesheet entries are never used.
        """
        # print( f"loadCSSStyles {lsStylesheetName=}" )
        if lsStylesheetName in cachedStyleDicts:
            return cachedStyleDicts[lsStylesheetName]
        with open( f'../htmlPages/{lsStylesheetName}' if 'pagefind' in lsStylesheetName else lsStylesheetName, 'rt', encoding='utf-8') as ssFile:
            lsStyleDict = defaultdict( list )
            for ssLine in ssFile:
                if ' + ' in ssLine: continue # Don't need these
                # print( f"  {ssLine=}" )
                if ssLine.startswith( 'span.' ):
                    className = ssLine[5:].split( ' ', 1 )[0]
                    # print( f"    span {className=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    assert 'span' not in lsStyleDict[className], f"{lsStylesheetName=} {className=} {lsStyleDict[className]=}"
                    lsStyleDict[className].append( 'span' )
                    lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( 'p.' ):
                    classNames = ssLine[2:].split( ' ', 1 )[0]
                    # print( f"    p {classNames=} {ssLine[len(classNames)+4:]=}")
                    for className in classNames.split( ',' ):
                        className = className.replace( 'p.', '' )
                        # if not ssLine[len(className)+4:].startswith( '+ '): # p.mt1 + p.mt2, p.mt2 + p.mt1 { margin-top:-0.5em; }
                        assert ' ' not in className and ',' not in className, f"{lsStylesheetName=} {className=}"
                        assert 'p' not in lsStyleDict[className], f"{lsStylesheetName=} {className=} {lsStyleDict[className]=}"
                        lsStyleDict[className].append( 'p' )
                        lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( 'div.' ):
                    className = ssLine[4:].split( ' ', 1 )[0]
                    # print( f"    div {className=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    assert 'div' not in lsStyleDict[className]
                    lsStyleDict[className].append( 'div' )
                    lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( 'h1.' ) or ssLine.startswith( 'h2.' ):
                    elementName = ssLine[:2]
                    className = ssLine[3:].split( ' ', 1 )[0]
                    # print( f"    {elementName} {className=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    assert elementName not in lsStyleDict[className]
                    lsStyleDict[className].append( elementName )
                    lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( 'ol.' ):
                    className = ssLine[3:].split( ' ', 1 )[0]
                    # print( f"    ol {className=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    if className not in ('verse',): # In InterlinearVerse.css these are specified for each language
                        assert 'ol' not in lsStyleDict[className], f"{className=} {lsStyleDict[className]=} {ssLine=}"
                    if 'ol' not in lsStyleDict[className]:
                        lsStyleDict[className].append( 'ol' )
                        lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( 'li.' ):
                    elementName = ssLine[:2]
                    className = ssLine[3:].split( ' ', 1 )[0]
                    # print( f"    {elementName} {className=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    assert elementName not in lsStyleDict[className]
                    lsStyleDict[className].append( elementName )
                    lsStyleDict[f'used_{className}'] = False
                elif ssLine.startswith( '.' ):
                    className = ssLine[1:].split( ' ', 1 )[0]
                    # print( f"    {className=} {ssLine[len(className)+2:]=}")
                    assert ' ' not in className and ',' not in className, f"{className=}"
                    if not ssLine[len(className)+2:].startswith( 'a {'): # .wrkLst a { text-decoration:none; color:white; }
                        assert '' not in lsStyleDict[className]
                        lsStyleDict[className].append( '' )
                        lsStyleDict[f'used_{className}'] = False
        # print( f"{lsStylesheetName=} ({len(lsStyleDict)//2}) {lsStyleDict=}" )
        cachedStyleDicts[lsStylesheetName] = lsStyleDict
        return lsStyleDict
    # end of loadCSSStyles function

    startedCheck = False
    styleDict = {}
    for line in htmlToCheck.split( '\n' ):
        if not startedCheck or where=='OETKey': # OETKey has two stylesheets
            if 'rel="stylesheet"' in line:
                ixStart = line.index( 'href="' )
                ixEnd = line.index( '">', ixStart+6 )
                stylesheetName = line[ixStart+6:ixEnd].replace( '../', '' )
                styleDict.update( loadCSSStyles( stylesheetName ) )
            # Search.htm has two stylesheets, but we're only interested in the first one
            # elif '</head>' in line:
                startedCheck = True
        else: # startedCheck
            for elementName,classNames in classRegex.findall( line ):
                # print( f"  {elementName=} {classNames=}" )
                for className in classNames.split( ' '):
                    # assert className in styleDict and (elementName in styleDict[className] or '' in styleDict[className]), f"{elementName}.{className} not in {stylesheetName} in {where=}"
                    if className not in styleDict \
                    or (elementName not in styleDict[className] and '' not in styleDict[className]):
                        msg = f"{elementName}.{className} not in {stylesheetName}"
                        if msg not in collectedMsgs:
                            collectedMsgs.append( msg )
                            logging.critical( f"{len(collectedMsgs)}: CSS style {msg} in {where=}" )
                    styleDict[f'used_{className}'] = True

    # # The unused CSS entries should get less and less with each page checked
    # unusedList = [sdKey[5:] for sdKey,sdValue in styleDict.items() if sdKey.startswith( 'used_') and not sdValue]
    # if unusedList and len(unusedList) < len(styleDict)//6:
    #     print( f"{stylesheetName} {where=} ({len(unusedList)})/({len(styleDict)}) {unusedList=}" )

    return True
# end of html.checkHtmlForMissingStyles


def convert_adds_to_italics( htmlSegment:str, where:Optional[str]=None ) -> str:
    """
    """
    # Hardwire added words in non-OET versions to italics
    for _cati_safetyCheck in range( 30 ): # 20 was too few (because this might include an intro paragraph)
        ix = htmlSegment.find( '<span class="add">' )
        if ix == -1: break
        htmlSegment = htmlSegment.replace( '<span class="add">', '<i>', 1 )
        # TODO: What if there was another span inside the add field ???
        htmlSegment = f"{htmlSegment[:ix]}{htmlSegment[ix:].replace('</span>','</i>',1)}"
    else: not_enough_loops

    return htmlSegment
# end of html.convert_adds_to_italics


RV_ADD_REGEX = re.compile( '<span class="RVadd">' )
def do_OET_RV_HTMLcustomisations( OET_RV_html:str ) -> str:
    """
    OET-RV is formatted in paragraphs.

    See https://OpenEnglishTranslation.Bible/Resources/Formats for descriptions of add subfields.
    """
    # assert '<span class="add">+' not in OET_RV_html # Only expected in OET-LV
    # assert '<span class="add">-' not in OET_RV_html # Only expected in OET-LV # WE ALLOW IT NOW as HYPHEN (not as a special char)
    assert '<span class="add">=' not in OET_RV_html # Only expected in OET-LV
    assert '<span class="add">?≡' not in OET_RV_html # Doesn't make sense
    result = (OET_RV_html \
            # Adjust specialised add markers
            .replace( '<span class="add">?<', '<span class="unsure addDirectObject" title="added direct object (uncertain)">' )
            .replace( '<span class="add"><span ', '__PROTECT_SPAN__' )
            .replace( '<span class="add"><a title', '__PROTECT_A__' )
            .replace( '<span class="add"><', '<span class="addDirectObject" title="added direct object">' )
            .replace( '__PROTECT_A__', '<span class="add"><a title' )
            .replace( '__PROTECT_SPAN__', '<span class="add"><span ' )
            .replace( '<span class="add">?>', '<span class="unsure addExtra" title="added implied info (uncertain)">' )
            .replace( '<span class="add">>', '<span class="addExtra" title="added implied info">' )
            .replace( '<span class="add">?+', '<span class="unsure addArticle" title="added article (uncertain)">' )
            .replace( '<span class="add">+', '<span class="addArticle" title="added article">' )
            .replace( '<span class="add">≡', '<span class="addElided" title="added elided info">' )
            .replace( '<span class="add">?&', '<span class="unsure addOwner" title="added owner (uncertain)">' )
            .replace( '<span class="add">&', '<span class="addOwner" title="added owner">' )
            .replace( '<span class="add">?@', '<span class="unsure addReferent" title="inserted referent (uncertain)">' )
            .replace( '<span class="add">@', '<span class="addReferent" title="inserted referent">' )
            .replace( '<span class="add">?*', '<span class="unsure addPronoun" title="used pronoun (uncertain)">' )
            .replace( '<span class="add">*', '<span class="addPronoun" title="used pronoun">' )
            .replace( '<span class="add">?#', '<span class="unsure addPluralised" title="changed number (uncertain)">' )
            .replace( '<span class="add">#', '<span class="addPluralised" title="changed number">' )
            .replace( '<span class="add">?^', '<span class="unsure addNegated" title="negated (uncertain)">' )
            .replace( '<span class="add">^', '<span class="addNegated" title="negated">' )
            .replace( '<span class="add">?≈', '<span class="unsure addReword" title="reworded (uncertain)">' )
            .replace( '<span class="add">≈', '<span class="addReword" title="reworded">' )
            .replace( '<span class="add">?', '<span class="unsure RVadd" title="added info (uncertain)">' )
            .replace( '<span class="add">', '<span class="RVadd" title="added info">' )
            .replace( '≈', '<span class="synonParr" title="synonymous parallelism">≈</span>')
            .replace( '^', '<span class="antiParr" title="antithetic parallelism">^</span>')
            .replace( '≥', '<span class="synthParr" title="synthetic parallelism">≥</span>')
            )

    # Just do an additional check inside '<span class="RVadd">' spans
    startSearchIndex = 0
    for _safetyCount in range( 3_000 ): # 2_000 wasn't enough
        match = RV_ADD_REGEX.search( result, startSearchIndex )
        if not match: break
        startSearchIndex = match.end()
        # print( f"{startSearchIndex=} {nextChar=} {result[match.start():match.start()+30]}" )
        nextChars = result[startSearchIndex:]
        if not ( nextChars.startswith( '<a title' )
                or nextChars.startswith( '<span class="wj">' ) or nextChars.startswith( '<span class="nominaSacra">') ):
            nextChar = result[startSearchIndex]
            # NOTE: 1/ 2/ 3/ are used in OET-RV EXO 23
            assert nextChar.isalpha() or nextChar in '(,‘’—123☺', f"{startSearchIndex=} {nextChar=} {result[match.start():match.start()+80]}"
    else: NOT_ENOUGH_LOOPS

    return result
# end of html.do_OET_RV_HTMLcustomisations


digitPunctDigitRegex = re.compile( '[0-9][:.][0-9]' )
def do_OET_LV_HTMLcustomisations( OET_LV_html:str ) -> str:
    """
    OET-LV is often formatted as a new line for each sentence.

    We have to protect fields like periods in '../C2_V2.htm' from corruption
        (and then restore them again of course).

    See https://OpenEnglishTranslation.Bible/Resources/Formats for descriptions of add subfields.
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

    assert '<span class="add">-' not in OET_LV_html # Only expected in OET-RV
    assert '<span class="add">*' not in OET_LV_html # Only expected in OET-RV
    assert '<span class="add">@' not in OET_LV_html # Only expected in OET-RV
    assert '<span class="add">~' not in OET_LV_html # Only expected in OET-RV
    assert '<span class="add">≈' not in OET_LV_html # Only expected in OET-RV
    assert '<span class="add">?' not in OET_LV_html # Only expected in OET-RV
            # .replace( '<span class="add">-', '<span class="unusedArticle">' )
    OET_LV_html = (OET_LV_html \
            # Protect fields we need to preserve
            .replace( '_V', '~~ULINE~~V' ).replace( '_verseText', '~~ULINE~~verseText' )
            .replace( '<!--', '~~COMMENT~~' )
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
            .replace( '<span class="add">=', '<span class="addCopula">' )
            .replace( '<span class="add"><a title', '~~PROTECT~~' )
            .replace( '<span class="add"><', '<span class="addDirectObject">' )
            .replace( '~~PROTECT~~', '<span class="add"><a title' )
            .replace( '<span class="add">>', '<span class="addExtra">' )
            .replace( '<span class="add">&', '<span class="addOwner">' )
            # Put all underlines into a span with a class (then we will have a button to hide them)
            .replace( '="', '~~EQUAL"' ) # Protect class=, id=, etc.
            .replace( '=', '_' ).replace( '÷', '_' ) # For OT morphemes
            .replace( '~~EQUAL"', '="' ) # Unprotect class=, id=, etc.
            .replace( '_', '<span class="ul">_</span>') # THIS IS ONE THAT CAN OVERREACH
            # Now unprotect everything again
            .replace( '--fnUNDERLINE--', '_' ).replace( '--fnEQUAL--', '=' ).replace( '--fnCOLON--', ':' ).replace( '--fnPERIOD--', '.' ) # Unprotect sanitised footnotes (see usfm.py)
            .replace( '~~COMMENT~~', '<!--' )
            .replace( '~~ULINE~~', '_' ).replace( '~~COLON~~', ':' ).replace( '~~PERIOD~~', '.' )
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
        T4T_html = T4T_html.replace( fullFoS, f'<span class="t4tFoS" title="{fosType} (figure of speech)">{fullFoS}</span>' )
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
