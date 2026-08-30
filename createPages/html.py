#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# html.py
#
# Module handling OpenBibleData html functions
#
# Copyright (C) 2023-2026 Robert Hunt
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

makeTop( level:int, versionAbbreviation:str|None, pageType:str, versionSpecificFileOrFolderName:str|None, state:State ) -> str
    Create the very top part of an HTML page.

    This is the HTML <head> segment, including assigning the correct CSS stylesheet.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    (Implemented in Rust -- see createPages/Rust/src/page_chrome.rs.)
makeViewNavListParagraph( level:int, versionAbbreviation:str|None, pageType:str, state:State ) -> str
    Make the "ByDocument/BySection" bar.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
        It can also be the 'OET' pseudo version.
        Can return an empty string.
makeBookNavListParagraph( linksList:list[str], workAbbrevPlus:str, state:State ) -> str
makeBottom( level:int, versionAbbreviation:str|None, pageType:str, state:State ) -> str
_makeFooter( level:int, versionAbbreviation:str|None, pageType:str, state:State ) -> str
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
    2025-01-10 Added container class to html body tag
    2025-01-15 Improved check to find newlines inside HTML title attributes
    2025-01-30 Put added ‘owner’ in quotes in HTML title field
    2025-02-02 Make book selection jump to chapter list selector (not just 1:1#Top)
    2025-02-20 Add OET missing verses link (in TEST MODE only)
    2025-02-21 Created functions
    2025-03-11 Add a couple more checks of spans in checkHtml()
    2025-05-19 Handle doubled T4T figures of speech
    2025-05-31 Added deferred loading to make KB.js work properly
    2025-06-19 Handle more of the varieties in doubled T4T figures of speech
    2025-09-09 Allow for 'kingdom' pages
    2025-12-19 Fix bug that displayed ' 2 YHN2 JHN)' etc. (losing the opening parenthesis) in the book navigation line
    2026-01-06 Added NNBSpace after parallelism markers at line beginnings
    2026-01-19 Added link to https://OET.Bible
    2026-02-03 Allow uncertain ellided markings '\\add ?≡'
    2026-05-09 Upgraded to bos_books_codes_py
    2026-06-11 Handle new % (changed person) \\add format
    2026-08-22 makeTop and makeViewNavListParagraph now delegate to the Rust openbibledata_rust module (page_chrome);
                    deleted the superseded Python _makeNavigationLinks and _makeWorkNavListParagraph implementations.
    2026-08-23 Cached the output of makeBottom (by relying on the global import of state)
    2026-08-25 The OETHandlers functions are now imported from the Rust openbibledata_rust module (the Python OETHandlers.py was deleted).
    2026-08-28 Added preloadCSSStyles() so stylesheet caches are built in the parent before
                    forked multiprocessing children are created (they inherit the cache copy-on-write).
"""
import logging
from datetime import datetime
import re
from collections import defaultdict
from functools import cache

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, BOOKLIST_OT39, BOOKLIST_NT27
import bos_books_codes_py
import openbibledata_rust

from settings import State, state
from openbibledata_rust import getBBBFromOETBookName, checkHtml as _rustCheckHtml


LAST_MODIFIED_DATE = '2026-08-30' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '1.0.5'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

NEWLINE = '\n'


KNOWN_PAGE_TYPES = ('site', 'TopIndex', 'details', 'AllDetails',
                    'book','bookIndex', 'chapter','chapterIndex', 'section','sectionIndex',
                    'relatedPassage','relatedSectionIndex',
                    'topicPassages','topicsIndex', 'kingdom',
                    'parallelVerse', 'interlinearVerse',
                    'dictionaryMainIndex','dictionaryLetterIndex','dictionaryEntry','dictionaryIntro',
                    'word','lemma','morpheme', 'person','location', 'statistics', 'StrongsPage',
                    'wordIndex','lemmaIndex','morphemeIndex', 'personIndex','locationIndex',
                        'statisticsIndex', 'referenceIndex','StrongsIndex', 'kingdomIndex',
                    'search', 'about', 'news', 'OETKey')

_pageChromeConfigCache = None # (id(state), openbibledata_rust.PageChromeConfig) -- see _getPageChromeConfig
def _getPageChromeConfig( state:State ):
    """
    Return the Rust snapshot of the State data needed by the page-top builders.

    The snapshot (version list, decorations, names, safe names, preloaded
    book sets, etc.) is extracted once per State object and reused for every
    page, so generating page tops involves no Python attribute access at all.
    Assumes those State fields are settled before page creation starts
    (which Bibles.loadBibles guarantees).
    """
    global _pageChromeConfigCache
    if _pageChromeConfigCache is None or _pageChromeConfigCache[0] != id(state):
        _pageChromeConfigCache = (id(state), openbibledata_rust.PageChromeConfig(state))
    return _pageChromeConfigCache[1]
# end of html._getPageChromeConfig

def makeTop( level:int, versionAbbreviation:str|None, pageType:str, versionSpecificFileOrFolderName:str|None, state:State ) -> str:
    """
    Create the very top part of an HTML page.

    This is the HTML <head> segment, including assigning the correct CSS stylesheet
        with the 'About', 'News', and 'OET Key' links at the top of the page
            and including the list of versions underneath that line.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.

    The actual work is done by the Rust make_top in openbibledata_rust.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )
    assert pageType in KNOWN_PAGE_TYPES, f"makeTop {level=} {versionAbbreviation=} {pageType=}"

    return openbibledata_rust.make_top( _getPageChromeConfig(state), level, pageType, versionAbbreviation, versionSpecificFileOrFolderName )
# end of html.makeTop


def makeViewNavListParagraph( level:int, versionAbbreviation:str|None, pageType:str, state:State ) -> str:
    """
    Make the "ByDocument/BySection" bar.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
        It can also be the 'OET' pseudo version.
        Can return an empty string.

    The actual work is done by the Rust make_view_nav_list in openbibledata_rust.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeViewNavListParagraph( {level}, {versionAbbreviation}, {pageType} )" )

    return openbibledata_rust.make_view_nav_list( _getPageChromeConfig(state), level, pageType, versionAbbreviation )
# end of html.makeViewNavListParagraph


HTML_PLUS_LIST = ['ParallelVerse','InterlinearVerse', 'ParallelIndex','InterlinearIndex']
OET_HTML_PLUS_LIST = ['OET'] + HTML_PLUS_LIST
def makeBookNavListParagraph( linksList:list[str], workAbbrevPlus:str, state:State ) -> str:
    """
    Create a 'bkLst' paragraph with the book abbreviation links
        preceded by the work abbreviation (non-link) if specified.

    linksList contains links like '<a title="Generic front matter" href="FRT.htm#Top">FRT</a>', '<a title="Jonah" href="JNA.htm#Top">JNA</a>', '<a title="Mark" href="MRK.htm#Top">MARK</a>'

    workAbbrevPlus is where we're coming from, and can contain a version abbreviation or something like 'interlinearVerse'
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeBookNavListParagraph( {linksList}, {workAbbrevPlus}, ... )" )
    assert workAbbrevPlus in state.preloadedBibles \
        or workAbbrevPlus in OET_HTML_PLUS_LIST \
        or workAbbrevPlus == 'Related OET-RV', workAbbrevPlus

    newList = (['TEST',workAbbrevPlus] if state.TEST_MODE_FLAG else [workAbbrevPlus]) if workAbbrevPlus else (['TEST'] if state.TEST_MODE_FLAG else [])
    for aLink in linksList:
        # print( f"\n{aLink=}")
        if ('>FRT<' in aLink or '>INT<' in aLink) \
        and workAbbrevPlus in HTML_PLUS_LIST:
            continue # Don't include this
        if workAbbrevPlus in HTML_PLUS_LIST: # they're all byVerse options
            # Make the versionAbbreviation links go to 1:1 for the selected book
            ixHrefStart = aLink.index( 'href="' ) + 6
            ixHrefEnd = aLink.index( '.htm', ixHrefStart )
            hrefTextBit, hrefEndBit = aLink[ixHrefStart:ixHrefEnd], aLink[ixHrefEnd:]
            assert hrefEndBit.startswith( '.htm#Top">' ), f"{hrefEndBit=} {workAbbrevPlus=}" # This is set in createSitePages._createSitePages()
            # if 'Index' in workAbbrevPlus:
            hrefEndBit = hrefEndBit.replace( '#Top', '#chLst', 1 ) # Show them the chapter and verse choices (because we're going to plonk them in 1:1)
            aLink = f'''{aLink[:ixHrefStart]}{hrefTextBit}/C1V1{hrefEndBit}''' \
                    .replace( '/index/', '/' ) # Fix error in ParallelIndex
        # TODO: This is very fragile code !!!
        ixDisplayLinkStart = aLink.index( '>' ) + 1
        ixDisplayLinkEnd = aLink.index( '<', ixDisplayLinkStart )
        displayText = aLink[ixDisplayLinkStart:ixDisplayLinkEnd]
        # print( f"  HEREaa {aLink=} {displayText=}")
        if not displayText: # Then we have a span inside the anchor
            # e.g., aLink='<a title="Yonah/(Jonah)" href="../JNA/C1V1.htm#chLst"><span title="Yonah (which is closer to the Hebrew hhh/Yōnāh)">YNA</span> (JNA)</a>'
            ixDisplayLinkStart = aLink.index( '>', ixDisplayLinkEnd ) + 1
            ixDisplayLinkEnd = aLink.index( '<', ixDisplayLinkStart )
            displayText = aLink[ixDisplayLinkStart:ixDisplayLinkEnd]
            # print( f"  HEREbb {aLink=} {displayText=}")
        if len(displayText)==2 and displayText.endswith('\u202f'): # e.g., 1/2/3/ then NBSP for 1 Jhn etc,
            # e.g., aLink='<a title="1 Yohan/(John)" href="../JN1/C1V1.htm#chLst">1\u202f<span title="Yohan (which is closer to the Greek Ἰωάννης/Yōannaʸs)">YHN</span> (1\u202fJHN)</a>' displayText='1\u202f'
            ixDisplayLinkStart = aLink.index( f' ({displayText[0]}', ixDisplayLinkEnd )
            ixDisplayLinkEnd = aLink.index( ')', ixDisplayLinkStart )
            displayText = aLink[ixDisplayLinkStart:ixDisplayLinkEnd]
            # print( f"  HEREcc {aLink=} {displayText=}")
        adjDisplayText = displayText # We use this one for finding the BBB
        if ' (' in adjDisplayText:
            adjDisplayText = adjDisplayText.split(' (')[-1].removesuffix(')')
            # print( f"  HEREdd {aLink=} {adjDisplayText=}")
        assert 3 <= len(adjDisplayText) <= 5, f"{len(adjDisplayText)=} {adjDisplayText=}" # it should be a tidyBBB, e.g., 'GEN' or '1 COR'
        BBB = getBBBFromOETBookName( adjDisplayText, f"makeBookNavListParagraph( {workAbbrevPlus} {aLink=} )" )
        assert bos_books_codes_py.is_valid_bos_book_code( BBB ), f"Bad {BBB=} from {adjDisplayText=} from {aLink=}"
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
        assert newALink.count('(')==newALink.count(')'), f"OOPS, what happened to the parentheses in {workAbbrevPlus}\n{newALink=}\nfrom {aLink=}"
        newList.append( newALink )

    return f'''<p class="bkLst">{' '.join( newList )}</p><!--bkLst-->'''
# end of html.makeBookNavListParagraph


# NOTE: We imported state at the module level so it didn't have to be a parameter
@cache
def makeBottom( level:int, versionAbbreviation:str|None, pageType:str ) -> str:
    """
    Create the very bottom part of an HTML page.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeBottom()" )
    assert pageType in KNOWN_PAGE_TYPES, f"{level=} {pageType=}"

    return f'{_makeFooter( level, versionAbbreviation, pageType )}</body></html>'
# end of html.makeBottom

def _makeFooter( level:int, versionAbbreviation:str|None, pageType:str ) -> str:
    """
    Create any links or site map that follow the main content on the page.
    """
    from createSitePages import PROGRAM_NAME_VERSION as SITE_PROGRAM_NAME_VERSION

    # fnPrint( DEBUGGING_THIS_MODULE, f"_makeFooter()" )

    html = f"""<div class="footer" id="footer">
<p class="copyright" id="Bottom"><small><em>{'TEST ' if state.TEST_MODE_FLAG else ''}{state.SITE_NAME}</em> site {state.SITE_COPYRIGHT} <a href="https://Freely-Given.org">Freely-Given.org</a>.
<br>Python source code for creating these static pages is available <a href="https://GitHub.com/Freely-Given-org/OpenBibleData">on GitHub</a> under an <a href="https://GitHub.com/Freely-Given-org/OpenBibleData/blob/main/LICENSE">open licence</a>.{f'{datetime.now().strftime('<br> (Page created: %Y-%m-%d %H:%M')} by OBD {SITE_PROGRAM_NAME_VERSION} with OET {state.OET_VERSION_NUMBER_STRING})' if state.TEST_MODE_FLAG else ''}</small></p>
<p class="copyright"><small>For Bible data copyrights, see the <a href="{'../'*level}AllDetails.htm#Top">details</a> for each displayed Bible version.</small></p>
{f'''<p class="note"><a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="20"> </a><small>The <em>Open English Translation (OET)</em> main site is at <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a> or <a href="https://OET.Bible">OET.Bible</a>.</small></p><!--note-->\n''' if not versionAbbreviation or 'OET' not in versionAbbreviation else ''}</div><!--footer-->"""
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
                # assert endHtml[endHtmlStartIx-5:endHtmlStartIx] == '<span', f"{endHtml[endHtmlStartIx-10:endHtmlStartIx]=} then {endHtml[endHtmlStartIx:endHtmlStartIx+10]=}"
                # assert endHtml[endHtmlStartIx+len(idContents):endHtmlStartIx+len(idContents)+8] == '></span>', f"{endHtml[endHtmlStartIx+len(idContents):endHtmlStartIx+len(idContents)+8]=}"
                if endHtml[endHtmlStartIx-5:endHtmlStartIx] == '<span' \
                and endHtml[endHtmlStartIx+len(idContents):endHtmlStartIx+len(idContents)+8] == '></span>':
                    endHtml = f'{endHtml[:endHtmlStartIx-5]}{endHtml[endHtmlStartIx+len(idContents)+8:]}'
                    html = f'{html[:endIx]}{endHtml}'
                    # assert '<span></span>' not in html
                    # print( f"removeDuplicateCVidsB {endHtmlStartIx=}\nendHtml='…{endHtml[endHtmlStartIx-50:endHtmlStartIx+50]}…'\nhtml='…{html[endIx+endHtmlStartIx-50:endIx+endHtmlStartIx+50]}…'" )
                elif endHtml[endHtmlStartIx-15:endHtmlStartIx] == '<span class="c"' \
                and endHtml[endHtmlStartIx:].startswith( ' id="C' ):
                    # print( f"{idContents=} {endHtml[endHtmlStartIx:endHtmlStartIx+30]=}" )
                    endHtml = f'{endHtml[:endHtmlStartIx]}{endHtml[endHtmlStartIx+len(idContents):]}'
                    html = f'{html[:endIx]}{endHtml}'
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


# These regexs have an extra bit to also allow for a nl inside the double-quotes (re.MULTILINE didn't seem to work for us)
# classAttributeRegex = re.compile( 'class="([^"]+?)"|class="([^"]+?)$' )
# idAttributeRegex = re.compile( 'id="([^"]+?)"|id="([^"]+?)$' )
# titleAttributeRegex = re.compile( 'title="([^"]+?)"|title="([^"]+?)$' )
def checkHtml( where:str, htmlToCheck:str, segmentOnly:bool=False ) -> bool:
    """
    Just do some very quick and basic tests
        that our HTML makes some sense.

    Throws an AssertError or a ValueError for any problems.

    The core validation logic is implemented in Rust (openbibledata_rust.checkHtml) for speed.
    This Python wrapper handles:
      - The wasted <br> fix (mutation of htmlToCheck)
      - CSS style checking (checkHtmlForMissingStyles)
      - TopIndex summary output
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"checkHtml( {where}, {len(htmlToCheck)} )" )

    # Fix wasted <br> before close tags (Python-side mutation)
    if '\n<br></p>' in htmlToCheck or '\n<br></span>' in htmlToCheck:
        logging.warning( f"checkHtml '{where}' {segmentOnly=} needed to fix wasted <br> in {htmlToCheck=}" )
        htmlToCheck = htmlToCheck.replace( '\n<br></span></span></p>', '</span></span></p>' ).replace( '\n<br></span></p>', '</span></p>' ).replace( '\n<br></p>', '</p>' )

    # Delegate all validation checks to the Rust implementation
    _rustCheckHtml( where, htmlToCheck, segmentOnly )

    if segmentOnly:
        return True

    # See if all our classes/styles exist in the stylesheet
    result = checkHtmlForMissingStyles( where, htmlToCheck )
    if where == 'TopIndex': # that's the final page that we build
        # so we output extra info here
        for mm,msg in enumerate( COLLECTED_MESSAGES, start=1 ):
            logging.critical( f"Missing CSS style {mm}/{len(COLLECTED_MESSAGES)}: {msg}" )
        # if 1 or not state.TEST_MODE_FLAG:
        for someStylesheetName,someStyleDict in cachedStyleDicts.items():
            # Only report stylesheets that were actually used by (parent-side) pages,
            #   otherwise a stylesheet preloaded for forked children but never used by
            #   the parent itself would look spuriously all-unused.
            anyUsed = any( sdValue for sdKey,sdValue in someStyleDict.items() if sdKey.startswith( 'used_' ) )
            unusedList = [sdKey[5:] for sdKey,sdValue in someStyleDict.items() if sdKey.startswith( 'used_') and not sdValue]
            if anyUsed and unusedList:
                logging.warning( f"UNUSED STYLES in {someStylesheetName} were ({len(unusedList)})/({len(someStyleDict)}) {unusedList=}" )

    return result
# end of html.checkHtml


classRegex = re.compile( '<([^>]+?) [^>]*?class="([^>"]+?)"' )
cachedStyleDicts = {}

# Every stylesheet that can appear in a page's <head>.
#   (Hand-kept in step with the Rust css_filename_for mapping in page_chrome.rs.)
PAGE_STYLESHEET_NAMES = (
    'OETChapter.css', 'BibleChapter.css',
    'ParallelPassages.css', 'TopicalPassages.css',
    'ParallelVerses.css', 'InterlinearVerse.css',
    'BibleWord.css', 'BibleDict.css', 'BibleSite.css',
)

def preloadCSSStyles() -> None:
    """
    Load every stylesheet into the module-level cache BEFORE any forked
    multiprocessing children are created.

    Forked children inherit cachedStyleDicts copy-on-write; doing this in the
    parent means each child (and the parent) shares the same already-parsed
    dictionaries instead of each re-reading the CSS files independently.
    """
    for stylesheetName in PAGE_STYLESHEET_NAMES:
        loadCSSStyles( stylesheetName )
# end of html.preloadCSSStyles


def loadCSSStyles( lsStylesheetName:str ) -> dict[str,bool|list[str]]:
    """
    Load the stylesheet and cache it for next time.

    Adds a used_{} entry (set to False) so we can set at the end,
        which stylesheet entries are never used.
    """
    if lsStylesheetName in cachedStyleDicts:
        return cachedStyleDicts[lsStylesheetName]
    
    print( f"loadCSSStyles {lsStylesheetName=}" )
    with open( f'../htmlPages/{lsStylesheetName}' if 'pagefind' in lsStylesheetName else lsStylesheetName, 'rt', encoding='utf-8') as ssFile:
        lsStyleDict = defaultdict( list )
        for ssLine in ssFile:
            if ' + ' in ssLine: continue # Don't need these
            # print( f"  {ssLine=}" )
            if ssLine.startswith( 'select.' ):
                className = ssLine[7:].split( ' ', 1 )[0]
                if lsStylesheetName == 'common.css':
                    className = className.removesuffix( ',\n' )
                print( f"    select {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                # assert 'select' not in lsStyleDict[className], f"{lsStylesheetName=} {className=} {lsStyleDict[className]=}"
                if 'select' not in lsStyleDict[className]:
                    lsStyleDict[className].append( 'select' )
                    lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'button.' ):
                className = ssLine[7:].replace(':',',').split( ',', 1 )[0]
                print( f"    button {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                # assert 'button' not in lsStyleDict[className], f"{lsStylesheetName=} {className=} {lsStyleDict[className]=}"
                if 'button' not in lsStyleDict[className]:
                    lsStyleDict[className].append( 'button' )
                    lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'span.' ):
                className = ssLine[5:].split( ' ', 1 )[0]
                # print( f"    span {className=}")
                if lsStylesheetName == 'common.css':
                    className = className.removesuffix( ',\n' )
                assert ' ' not in className and ',' not in className, f"{className=}"
                if lsStylesheetName != 'common.css':
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
                    if lsStylesheetName != 'common.css':
                        assert 'p' not in lsStyleDict[className], f"{lsStylesheetName=} {className=} {lsStyleDict[className]=}"
                    lsStyleDict[className].append( 'p' )
                    lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'div.' ):
                className = ssLine[4:].split( ' ', 1 )[0]
                # print( f"    div {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                if lsStylesheetName != 'common.css':
                    assert 'div' not in lsStyleDict[className], f"DIV already in {lsStyleDict[className]=} {ssLine=}"
                lsStyleDict[className].append( 'div' )
                lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'h1.' ) or ssLine.startswith( 'h2.' ):
                elementName = ssLine[:2]
                className = ssLine[3:].split( ' ', 1 )[0]
                # print( f"    {elementName} {className=}")
                if className.endswith( ',' ): className = className[:-1] # Can have h1.PromisedLand, p.PromisedLand { color:gold; }
                assert ' ' not in className and ',' not in className, f"{className=}"
                assert elementName not in lsStyleDict[className]
                lsStyleDict[className].append( elementName )
                lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'ol.' ):
                elementName = ssLine[:2]
                className = ssLine[3:].split( ' ', 1 )[0]
                # print( f"    {elementName} {className=}")
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
            elif ssLine.startswith( 'body.' ):
                elementName = ssLine[:4]
                className = ssLine[5:].split( ' ', 1 )[0]
                # print( f"    {elementName} {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                assert elementName not in lsStyleDict[className]
                lsStyleDict[className].append( elementName )
                lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'img.' ):
                elementName = ssLine[:3]
                className = ssLine[4:].split( ' ', 1 )[0]
                # print( f"    {elementName} {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                assert elementName not in lsStyleDict[className]
                lsStyleDict[className].append( elementName )
                lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'hr.' ):
                elementName = ssLine[:2]
                className = ssLine[3:].split( ' ', 1 )[0]
                # print( f"    {lsStylesheetName} {elementName} {className=}")
                assert ' ' not in className and ',' not in className, f"{className=}"
                assert elementName not in lsStyleDict[className]
                lsStyleDict[className].append( elementName )
                lsStyleDict[f'used_{className}'] = False
            elif ssLine.startswith( 'a.' ):
                elementName = ssLine[:1]
                className = ssLine[2:].split( ' ', 1 )[0]
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

COLLECTED_MESSAGES = []
def checkHtmlForMissingStyles( where:str, htmlToCheck:str ) -> bool:
    """
    Given an html page,
        determine the stylesheet and load it if not already cached,
        and then check that all classes are in the stylesheet.
    """
    startedCheck = False
    styleDict = {}
    for line in htmlToCheck.split( '\n' ):
        if not startedCheck or where=='OETKey': # OETKey has two stylesheets
            if 'rel="stylesheet"' in line:
                ixStart = line.index( 'href="' )
                ixEnd = line.index( '">', ixStart+6 )
                stylesheetName = line[ixStart+6:ixEnd].replace( '../', '' )
                styleDict.update( loadCSSStyles( stylesheetName ) )
                styleDict.update( loadCSSStyles( 'common.css' ) )
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
                        if msg not in COLLECTED_MESSAGES:
                            COLLECTED_MESSAGES.append( msg )
                            logging.critical( f"{len(COLLECTED_MESSAGES)}: CSS style {msg} in {where=}" )
                    styleDict[f'used_{className}'] = True

    # # The unused CSS entries should get less and less with each page checked
    # unusedList = [sdKey[5:] for sdKey,sdValue in styleDict.items() if sdKey.startswith( 'used_') and not sdValue]
    # if unusedList and len(unusedList) < len(styleDict)//6:
    #     print( f"{stylesheetName} {where=} ({len(unusedList)})/({len(styleDict)}) {unusedList=}" )

    return True
# end of html.checkHtmlForMissingStyles


def convert_adds_to_italics( htmlSegment:str, where:str|None=None ) -> str:
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
def do_OET_RV_HTMLcustomisations( where:str, OET_RV_html:str ) -> str:
    """
    OET-RV is formatted in paragraphs.

    Handle the various OET-RV "/add" fields,
        plus the parallelism markers in Psalms and other poetry.

    See https://OpenEnglishTranslation.Bible/Resources/Formats for descriptions of add subfields.
    """
    # assert '<span class="add">+' not in OET_RV_html # Only expected in OET-LV
    # assert '<span class="add">-' not in OET_RV_html # Only expected in OET-LV # WE ALLOW IT NOW as HYPHEN (not as a special char)
    assert '<span class="add">=' not in OET_RV_html # Only expected in OET-LV
    # assert '<span class="add">?≡' not in OET_RV_html # Doesn't make sense -- used in PRO_21:18
    # assert checkHtml( where, OET_RV_html, segmentOnly=True)

    # testResult = (OET_RV_html \
    #         # Adjust specialised add markers
    #         .replace( '<span class="add">?<a title=', '<span class="RVadd unsure" title="added info (less certain)"><a title=' ) # Only happens in '\add ?' then a word that got a word number on it
    #         .replace( '<span class="add">?<span', '<span class="RVadd unsure" title="added info (less certain)"><span' ) # Only happens in TEST_MODE with noLinkYet spans
    #         .replace( '<span class="add">?<', '<span class="addDirectObject unsure" title="added direct object (less certain)">' )
    #         .replace( '<span class="add"><span ', '__PROTECT_SPAN__' )
    #         .replace( '<span class="add"><a title', '__PROTECT_A__' )
    #         .replace( '<span class="add"><', '<span class="addDirectObject" title="added direct object">' )
    #         .replace( '__PROTECT_A__', '<span class="add"><a title' )
    #         .replace( '__PROTECT_SPAN__', '<span class="add"><span ' )
    #         )
    # if where == 'ParallelVerseTxt=JOB_24:1': print( f"{testResult=}\nfrom {OET_RV_html=}" )
    # assert checkHtml( where, testResult, segmentOnly=True)

    result = (OET_RV_html \
            # Adjust specialised add markers
            .replace( '<span class="add">?<a title=', '<span class="RVadd unsure" title="added info (less certain)"><a title=' ) # Only happens in '\add ?' then a word that got a word number on it
            .replace( '<span class="add">?<span', '<span class="RVadd unsure" title="added info (less certain)"><span' ) # Only happens in TEST_MODE with noLinkYet spans
            .replace( '<span class="add">?<', '<span class="addDirectObject unsure" title="added direct object (less certain)">' )
            .replace( '<span class="add"><span ', '__PROTECT_SPAN__' )
            .replace( '<span class="add"><a title', '__PROTECT_A__' )
            .replace( '<span class="add"><', '<span class="addDirectObject" title="added direct object">' )
            .replace( '__PROTECT_A__', '<span class="add"><a title' )
            .replace( '__PROTECT_SPAN__', '<span class="add"><span ' )
            .replace( '<span class="add">?>', '<span class="addExtra unsure" title="added implied info (less certain)">' )
            .replace( '<span class="add">>', '<span class="addExtra" title="added implied info">' )
            .replace( '<span class="add">?+', '<span class="addArticle unsure" title="added article (less certain)">' )
            .replace( '<span class="add">+', '<span class="addArticle" title="added article">' )
            .replace( '<span class="add">?≡', '<span class="addElided unsure" title="added elided info (less certain)">' )
            .replace( '<span class="add">≡', '<span class="addElided" title="added elided info">' )
            .replace( '<span class="add">?&', '<span class="addOwner unsure" title="added ‘owner’ (less certain)">' )
            .replace( '<span class="add">&', '<span class="addOwner" title="added ‘owner’">' )
            .replace( '<span class="add">?@', '<span class="addReferent unsure" title="inserted referent (less certain)">' )
            .replace( '<span class="add">@', '<span class="addReferent" title="inserted referent">' )
            .replace( '<span class="add">?*', '<span class="addPronoun unsure" title="used pronoun (less certain)">' )
            .replace( '<span class="add">*', '<span class="addPronoun" title="used pronoun">' )
            .replace( '<span class="add">?#', '<span class="addNumberChange unsure" title="changed number (less certain)">' )
            .replace( '<span class="add">#', '<span class="addNumberChange" title="changed number">' )
            .replace( '<span class="add">?%', '<span class="addPersonChange unsure" title="changed person (less certain)">' )
            .replace( '<span class="add">%', '<span class="addPersonChange" title="changed person">' )
            .replace( '<span class="add">?^', '<span class="addNegated unsure" title="negated (less certain)">' )
            .replace( '<span class="add">^', '<span class="addNegated" title="negated">' )
            .replace( '<span class="add">?≈', '<span class="addReword unsure" title="reworded (less certain)">' )
            .replace( '<span class="add">≈', '<span class="addReword" title="reworded">' )
            .replace( '<span class="add">?', '<span class="RVadd unsure" title="added info (less certain)">' )
            .replace( '<span class="add">', '<span class="RVadd" title="added info">' )
            .replace( '≈', '<span class="synonParr" title="synonymous parallelism">≈ </span>')
            .replace( '^', '<span class="antiParr" title="antithetic parallelism">^ </span>')
            .replace( '→', '<span class="synthParr" title="synthetic parallelism">→ </span>')
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

    assert checkHtml( where, result, segmentOnly=True)
    return result
# end of html.do_OET_RV_HTMLcustomisations


digitPunctDigitRegex = re.compile( '[0-9][:.][0-9]' )
def do_OET_LV_HTMLcustomisations( where:str, OET_LV_html:str ) -> str:
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
            .replace( '../', '~~PERIOD~~~~PERIOD~~/' ) # Protect paths like ../../somewhere.htm
            .replace( '.htm', '~~PERIOD~~htm' ).replace( 'https:', 'https~~COLON~~' )
            .replace( '.org', '~~PERIOD~~org' ).replace( '.tsv', '~~PERIOD~~tsv' )
            # .replace( 'v0.', 'v0~~PERIOD~~' )
            .replace( '.\\f*', '~~PERIOD~~\\f*' ).replace( 'Note:', 'Note~~COLON~~').replace( '."', '~~PERIOD~~"' ) # These last two are inside the footnote callers
            # In <hr>
            .replace( 'width:', 'width~~COLON~~' ).replace( 'margin-left:', 'margin-left~~COLON~~' ).replace( 'margin-top:', 'margin-top~~COLON~~' )
            # Make each sentence start a new line
            .replace( '.', '.\n<br>' ).replace( '?', '?\n<br>' ) # NOTE: DANGEROUS if periods in HMTL title fields (like morphology), etc.
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
    assert checkHtml( f"do_OET_LV_HTMLcustomisations {where=}", OET_LV_html, segmentOnly=True )
    return OET_LV_html
# end of html.do_OET_LV_HTMLcustomisations


def do_LSV_HTMLcustomisations( where:str, LSV_html:str ) -> str:
    """
    LSV has lines like:
        v 7 “\\w Blessed|strong="G3107"\\w* [\\w are|strong="G3588"\\w*] \\w they|strong="G2532"\\w* \\w whose|strong="G3739"\\w* lawless \\w acts|strong="G4160"\\w* \\w were|strong="G3588"\\w* forgiven, || \\w And|strong="G2532"\\w* \\w whose|strong="G3739"\\w* \\w sins|strong="G3900"\\w* \\w were|strong="G3588"\\w* \\w covered|strong="G1943"\\w*;

    We need to change the two parallel lines to <br>.
    """
    return LSV_html.replace( ' || ', '<br>' ).replace( '||', '<br>' ) # Second one catches any source inconsistencies
# end of html.do_LSV_HTMLcustomisations


T4T_FOS_TYPES = ( ('APO','apostrophe'), ('CHI','chiasmus'), ('DOU','doublet'), ('EUP','euphemism'),
                ('HEN','hendiadys'), ('HYP','hyperbole'), ('IDM','idiom'), ('IRO','irony'), ('LIT','litotes'),
                ('MET','metaphor'), ('MTY','metonymy'), ('PRS','personification'), ('RHQ','rhetorical question'),
                ('SIM','simile'), ('SYM','symbol'), ('SAR','sarcasm'), ('SYN','synecdoche'), ('TRI','triple') )
def do_T4T_HTMLcustomisations( where:str, T4T_html:str ) -> str:
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
    It also has things like [EUP, MTY] and [EUP/MTY]
    """
    if '[' in T4T_html or ']' in T4T_html:
        T4T_html = (T4T_html
                    .replace( '[SIL]', '[SIM]' ) # Error in Psa 63:1
                    .replace( 'birth MET]', 'birth [MET]' ) # Error in Mat 24:8
                    )
        for FoS,fosType in T4T_FOS_TYPES:
            fullFoS = f'[{FoS}]'
            T4T_html = T4T_html.replace( fullFoS, f'<span class="t4tFoS" title="{fosType} (figure of speech)">LEFTBRACKET{FoS}RIGHTBRACKET</span>' )
        if '[' in T4T_html: # still (we don't want to run these nested loops unnecessarily, especially for something that occurs relatively rarely)
            for FoS1,fosType1 in T4T_FOS_TYPES:
                for FoS2,fosType2 in T4T_FOS_TYPES:
                    if FoS2 != FoS1:
                        # T4T is not consistent here in use of commas and forward slashes
                        fullFoSs = f'[{FoS1}, {FoS2}]'
                        T4T_html = T4T_html.replace( fullFoSs, f'LEFTBRACKET<span class="t4tFoS" title="{fosType1} (figure of speech)">{FoS1}</span>, <span class="t4tFoS" title="{fosType2} (figure of speech)">{FoS2}</span>RIGHTBRACKET' )
                        fullFoSs = f'[{FoS1}/{FoS2}]'
                        T4T_html = T4T_html.replace( fullFoSs, f'LEFTBRACKET<span class="t4tFoS" title="{fosType1} (figure of speech)">{FoS1}</span>/<span class="t4tFoS" title="{fosType2} (figure of speech)">{FoS2}</span>RIGHTBRACKET' )
            # Double-check that we got them all
            for FoS1,fosType1 in T4T_FOS_TYPES:
                for FoS2,fosType2 in T4T_FOS_TYPES:
                    if FoS2 != FoS1:
                        # if 'GEN_13' not in where and 'GEN_25' not in where and 'GEN_48' not in where \
                        # and 'MRK_2' not in where and 'MRK_16' not in where:
                        assert f'[{FoS1}' not in T4T_html, f"[{FoS1} {where} {T4T_html}"
                        assert f'{FoS2}]' not in T4T_html, f"{FoS2}] {where} {T4T_html}"
        T4T_html = T4T_html.replace( 'LEFTBRACKET', '[' ).replace( 'RIGHTBRACKET', ']' )
    return T4T_html.replace( '◄', '<span title="alternative translation">◄</span>' )
# end of html.do_T4T_HTMLcustomisations


# <span class="fnCaller">[<a title="Note: K אחד" href="#fnUHB4">fn</a>]</span>
footnoteRegex = re.compile( '<span class="fnCaller">.+?</span>' )
def handleAndExtractFootnotes( versionAbbreviation:str, verseHtml:str ) -> tuple[str,str,str]:
    """
    Given verseHtml that may contain a footnotes division,
        separate off the footnotes.

    If there's also cross-references, they won't be split off separately.
        (If they occur after the footnotes, then they'll be included with the footnotes.)
    """
    if '<div id="footnotes" class="footnotes">' in verseHtml:
        assert verseHtml.count('<hr ') >= 1, f"{versionAbbreviation} ({verseHtml.count('<hr ')}) {verseHtml=}"
        if verseHtml.count('<hr ') > 1:
            assert '<div id="crossRefs" class="crossRefs">' in verseHtml, f"{versionAbbreviation} ({verseHtml.count('<hr ')}) {verseHtml=}"
        assert verseHtml.count('</div>') == verseHtml.count( '<div ' )

        # Handle footnotes so the same fn1 doesn't occur for multiple versions
        verseHtml = verseHtml.replace( 'id="footnotes', f'id="footnotes{versionAbbreviation}' ).replace( 'id="fn', f'id="fn{versionAbbreviation}' ).replace( 'href="#fn', f'href="#fn{versionAbbreviation}' )

        verseHtml, footnoteHtml = verseHtml.split( '<hr ', 1 ) # Split at the first horizontal rule
        # try: verseHtml, footnoteHtml = verseHtml.split( '<hr ' )
        # except ValueError as err: # usually too many values to unpack
        #     ix1 = verseHtml.index( '<hr ' )
        #     ix2 = verseHtml.index( '<hr ', ix1+5 )
        #     logging.critical( f"Too many parts: '{versionAbbreviation} {verseHtml[ix1:ix1+30]}'  and also  '{verseHtml[ix2:ix2+30]}'")
        #     return verseHtml, verseHtml, ''

        verseHtml = verseHtml.rstrip()
        footnoteFreeVerseHtml, numFootnotesRemoved = footnoteRegex.subn( '', verseHtml )
        # print( f"{numFootnotesRemoved} footnotes removed from {versionAbbreviation} {verseHtml=} gives {footnoteFreeVerseHtml=}")
        return verseHtml, footnoteFreeVerseHtml, f'<hr {footnoteHtml}'
    else:
        if 'class="footnotes"' in verseHtml: print( "{versionAbbreviation} {verseHtml=}" ); assert False, "We want to stop here"
        if versionAbbreviation != 'OET-RV':
            assert '<hr ' not in verseHtml, f"{versionAbbreviation=} {verseHtml=}"
        return verseHtml, verseHtml, ''
# end of createParallelVersePages.handleAndExtractFootnotes



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
