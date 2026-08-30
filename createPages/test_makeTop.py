#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# test_makeTop.py
#
# Copyright (C) 2026 Robert Hunt
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
Regression tests for the Rust page-chrome port in openbibledata_rust.

On 2026‑08‑22 html.makeTop / html.makeViewNavListParagraph were migrated to
Rust (createPages/Rust/src/page_chrome.rs). The _ref_* functions below are
verbatim copies of the former Python implementations (extracted from
git commit 0be39ab) and serve as the executable specification that the Rust
port must match byte-for-byte across a wide matrix of parameters.

CHANGELOG:
    2026-08-22 Created to lock down the Rust page-chrome port.
    2026-08-29 Updated _ref_makeTop to the deliberately-changed chrome: every page
        now loads common.css (shared chrome + theme CSS variables) and theme.js,
        and div.topLine carries a right-justified Dark/Light toggle plus an
        independent theme dropdown ("Default" / "Left verse nums"). The header
        record previously noted the reference was frozen; it is regenerated here
        because the page chrome behaviour itself was intentionally extended.
"""
import unittest

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, dPrint

import html as htmlModule
from html import KNOWN_PAGE_TYPES
from settings import State

DEBUGGING_THIS_MODULE = False
NEWLINE = '\n'


# ============================================================================
# The following four functions are VERBATIM copies of the former Python
# implementations in html.py (git commit 0be39ab), renamed with a _ref_
# prefix. Do not edit them to match changed Rust behaviour -- they are
# the specification.
# ============================================================================

def _ref_makeTop( level:int, versionAbbreviation:str|None, pageType:str, versionSpecificFileOrFolderName:str|None, state:State ) -> str:
    """
    Create the very top part of an HTML page.

    This is the HTML <head> segment, including assigning the correct CSS stylesheet
        with the 'About', 'News', and 'OET Key' links at the top of the page
            and including the list of versions underneath that line.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )
    assert pageType in KNOWN_PAGE_TYPES, f"makeTop {level=} {versionAbbreviation=} {pageType=}"

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
    elif pageType in ('word','lemma','morpheme', 'person','location','StrongsPage'):
        cssFilename = 'BibleWord.css'
    elif pageType in ('dictionaryLetterIndex', 'dictionaryEntry','dictionaryIntro'):
        cssFilename = 'BibleDict.css'
    elif pageType in ('site', 'details','AllDetails', 'search', 'about', 'news', 'OETKey', 'TopIndex',
                      'kingdom', 'statistics',
                      'bookIndex','chapterIndex','sectionIndex',
                      'relatedSectionIndex', 'topicsIndex', 'dictionaryMainIndex','StrongsIndex',
                      'wordIndex','lemmaIndex','morphemeIndex','personIndex','locationIndex','statisticsIndex','referenceIndex' ):
        cssFilename = 'BibleSite.css'
    else: unexpected_page_type

    homeLink = f"{state.SITE_NAME}{' TEST' if state.TEST_MODE_FLAG else ''} Home" if pageType=='TopIndex' else f'''<a href="{'../'*level}index.htm#Top">{state.SITE_NAME}{' TEST' if state.TEST_MODE_FLAG else ''} Home</a>'''
    aboutLink = 'About' if pageType=='about' else f'''<a href="{'../'*level}About.htm#Top">About</a>'''
    newsLink = 'News' if pageType=='news' else f'''<a href="{'../'*level}News.htm#Top">News</a>'''
    OETKeyLink = 'OET Key' if pageType=='OETKey' else f'''<a href="{'../'*level}OETKey.htm#Top">OET Key</a>'''
    topLink = f'<p class="site">{homeLink}  {aboutLink}  {newsLink}  {OETKeyLink}</p><!--site-->'
    # Two right-justified, independent controls (wired up by theme.js):
    # a Dark/Light toggle (shows current mode) and a theme dropdown that selects
    # a global theme: "Default", "Left verse nums", or "Large print".
    themeControls = ( '<div class="themeControls">'
                        '<button type="button" id="themeToggle" class="themeToggle" '
                        'title="Switch to dark mode" aria-pressed="false">Light</button>'
                        f'<select id="themeSelect" class="themeSelect" title="Choose a theme">'
                            '<option value="default">Default</option>'
                            '<option value="left">Left verse nums</option>'
                            '<option value="large">Large print</option>'
                        '</select>'
                      '</div><!--themeControls-->' )
    topLink = f'<div class="topLine">{topLink}{themeControls}</div><!--topLine-->'

    top = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="user-scalable=yes, initial-scale=1, minimum-scale=1, width=device-width">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
  <link rel="stylesheet" type="text/css" href="{'../'*level}common.css">
  __SCRIPT__
</head>
<body class="container" data-page-type="{pageType}"><!--Level{level}-->
{topLink}
"""
    # theme.js must run before paint so the saved/system theme applies without a flash
    top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}theme.js"></script>\n  __SCRIPT__''' )
    # Insert second stylesheet if required
    if pageType == 'OETKey':
        top = top.replace( '__SCRIPT__', f'''<link rel="stylesheet" type="text/css" href="{'../'*level}OETChapter.css">\n  __SCRIPT__''' )
    # Insert javascript file(s) if required
    if (versionAbbreviation and 'OET' in versionAbbreviation and pageType!='sectionIndex') \
    or pageType in ('parallelVerse','topicPassages'):
        top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}Bible.js"></script>\n  __SCRIPT__''' )
    if 'Dict' in cssFilename or 'Word' in cssFilename:
        top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}Dict.js" defer></script>\n  __SCRIPT__''' )
    if 'Dict' in cssFilename or 'Word' in cssFilename \
    or pageType in ('chapter','section','sectionIndex','book','parallelVerse','interlinearVerse','relatedPassage','topicPassages','kingdom'):
        top = top.replace( '__SCRIPT__', f'''<script src="{'../'*level}KB.js" defer></script>\n  __SCRIPT__''' )
    top = top.replace( '\n  __SCRIPT__', '' )

    return f'{top}{_ref_makeNavigationLinks( level, versionAbbreviation, pageType, versionSpecificFileOrFolderName, state )}'



def _ref_makeNavigationLinks( level:int, versionAbbreviation:str|None, pageType:str, versionSpecificFileOrFolderName:str|None, state:State ) -> str:
    """
    Create the navigation that goes before the page content.

    This includes the list of versions, and possibly the "ByDocument/BySection" bar as well.
        (It doesn't include book, chapter, or verse selector bars.)

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_ref_makeNavigationLinks( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )
    assert pageType in KNOWN_PAGE_TYPES, f"_ref_makeNavigationLinks {level=} {versionAbbreviation=} {pageType=}"

    versionHtml = _ref_makeWorkNavListParagraph( level, versionAbbreviation, pageType, versionSpecificFileOrFolderName, state )
    viewHtml = _ref_makeViewNavListParagraph( level, versionAbbreviation, pageType, state )

    return f'''<div class="header">{versionHtml}{NEWLINE if viewHtml else ''}{viewHtml}</div><!--header-->'''



def _ref_makeWorkNavListParagraph( level:int, versionAbbreviation:str|None, pageType:str, versionSpecificFileOrFolderName:str|None, state:State ) -> str:
    """
    Create the list of available versions.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
    """
    # DEBUGGING_THIS_MODULE = 99; print()
    fnPrint( DEBUGGING_THIS_MODULE, f"_ref_makeWorkNavListParagraph( {level}, {versionAbbreviation}, {pageType}, {versionSpecificFileOrFolderName} )" )
    assert pageType in KNOWN_PAGE_TYPES, f"_ref_makeWorkNavListParagraph {level=} {versionAbbreviation=} {pageType=}"

    # Add all the version abbreviations (except for the versionsWithoutTheirOwnPages)
    #   with their style decorators
    #   and with the more specific links if specified.
    initialVersionList = ['TEST'] if state.TEST_MODE_FLAG else []
    for loopVersionAbbreviation in state.BibleVersions:
        if loopVersionAbbreviation in ('TOSN','TTN','SOTN','UTN'): # Skip notes
            continue
        if loopVersionAbbreviation in state.versionsWithoutTheirOwnPages: # Skip versions without their own pages
            continue
        if state.TEST_VERSIONS_ONLY and loopVersionAbbreviation not in state.TEST_VERSIONS_ONLY:
            continue
        # Rather than leave out versions without sections, we will now point them to chapter pages (further below)
        # if pageType in ('section','sectionIndex'):
        #     try:
        #         thisBible = state.preloadedBibles['OET-RV' if loopVersionAbbreviation=='OET' else loopVersionAbbreviation]
        #         if not thisBible.discoveryResults['ALL']['haveSectionHeadings']:
        #             continue # skip this one
        #     except AttributeError: # no discoveryResults
        #         continue

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
    # It does this by adjusting the potential bad link to the next level higher
    #   except for section pages that don't exist will be changed to chapter pages.
    newVersionList = []
    for initial_entry in initialVersionList:
        # if pageType in ('section','sectionIndex'):
        #     print( f"  _ref_makeNavigationLinks processing {loopVersionAbbreviation=} from {initial_entry=} ({level=} {versionAbbreviation=} {pageType=} {versionSpecificFileOrFolderName=})" )
        if '/par/' in initial_entry or '/ilr/' in initial_entry:
            newVersionList.append( initial_entry )
            continue # Should always be able to link to these
        elif '/bySec/' in initial_entry:
            assert pageType in ('section','sectionIndex')
            startIndex = initial_entry.index('">') + 2
            loopVersionAbbreviation = initial_entry[startIndex:initial_entry.index('<',startIndex)]
            try:
                thisBible = state.preloadedBibles['OET-RV' if loopVersionAbbreviation=='OET' else loopVersionAbbreviation]
                haveSectionHeadings = thisBible.discoveryResults['ALL']['haveSectionHeadings']
            except AttributeError: # no discoveryResults
                haveSectionHeadings = False
            if not haveSectionHeadings:
                initial_entry = initial_entry.replace( '/bySec/', '/byC/' )
                assert '/S' not in initial_entry.replace('/SLT/','/sLT/').replace('/SR-GNT/','/sR-GNT/').replace('/SA','/sA').replace('/SIR','/sIR').replace('/SUS','/sUS').replace('/SNG','/sNG'), f"Found a possible section reference {initial_entry=}"
        entryBBB = None
        for tryBBB in state.allBBBs: # from all loaded versions
            if f'{tryBBB}.' in initial_entry or f'{tryBBB}_' in initial_entry or f'{tryBBB}/' in initial_entry:
                assert not entryBBB # Make sure we only found exactly one of them
                entryBBB = tryBBB
        if entryBBB:
            startIndex = initial_entry.index('">') + 2
            loopVersionAbbreviation = initial_entry[startIndex:initial_entry.index('<',startIndex)]
            if loopVersionAbbreviation == 'OET': loopVersionAbbreviation = 'OET-RV' # We look here in this case
            try: thisBible = state.preloadedBibles[loopVersionAbbreviation]
            except KeyError:
                assert state.TEST_MODE_FLAG
                thisBible = []
            if entryBBB in thisBible:
                # if pageType in ('section','sectionIndex'): print( f"    Appended {loopVersionAbbreviation} {entryBBB} as is (from {initial_entry})")
                newVersionList.append( initial_entry )
                continue # Should always be able to link to these
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Might not be able to link to {pageType} {loopVersionAbbreviation} {initial_entry}???" )
            replacement = ''
            if '/' in versionSpecificFileOrFolderName:
                ix = versionSpecificFileOrFolderName.index( '/' )
                if ix>0 and ix<len(versionSpecificFileOrFolderName)-1: # The slash is in the middle -- not at the beginning or the end
                    replacement = versionSpecificFileOrFolderName[:ix+1]
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"          Can we adapt {pageType} '{versionSpecificFileOrFolderName}' to '{replacement}'" )
            newEntry = initial_entry.replace( versionSpecificFileOrFolderName, replacement ) # Effectively links to a higher level folder
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"       Changed {pageType} link entry to {newEntry}")
            newVersionList.append( newEntry )
        else:
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Couldn't find a BBB so should be able to link ok to {pageType} {initial_entry}" )
            newVersionList.append( initial_entry )

    assert len(newVersionList) == len(initialVersionList)
    # if pageType in ('section','sectionIndex'): print( f"_ref_makeWorkNavListParagraph {'\n'.join(newVersionList)}\n from {'\n'.join(initialVersionList)}" ); assert False, "We want to stop here"
    return f'''<p class="wrkLst">{' '.join(newVersionList)}</p><!--wrkLst-->'''



def _ref_makeViewNavListParagraph( level:int, versionAbbreviation:str|None, pageType:str, state:State ) -> str:
    """
    Make the "ByDocument/BySection" bar.

    Note: versionAbbreviation can be None for parallel, interlinear and word pages, etc.
        It can also be the 'OET' pseudo version.
        Can return an empty string.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"_ref_makeViewNavListParagraph( {level}, {versionAbbreviation}, {pageType} )" )

    viewLinks = []
    if pageType in ('book','section','chapter', 'details',
                    'workIndex','bookIndex','sectionIndex','chapterIndex') \
    and versionAbbreviation not in ('PLBL','HAP','TOSN','TTN','TOBD','SOTN','UTN','UBS','THBD','BMM','OBI') \
    and versionAbbreviation not in state.versionsWithoutTheirOwnPages:
        if state.TEST_MODE_FLAG: viewLinks.append( 'TEST' )
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
        if state.TEST_MODE_FLAG and 'OET' in versionAbbreviation:
            viewLinks.append( f'''<a title="View verses not included in the OET" href="{'../'*level}OET/missingVerses.htm#Top"><small>Missing verses</small></a>''' )

    return f'''<p class="viewLst">{' '.join(viewLinks)}</p><!--viewLst-->''' if viewLinks else ''




class StubBible:
    def __init__( self, books, sections=True ):
        self._books = set( books )
        self.discoveryResults = {'ALL': {'haveSectionHeadings': sections}}

    def __contains__( self, item ):
        return item in self._books


BBBS = ['FRT', 'GEN', 'EXO', 'PSA', 'ISA', 'MRK', 'GAL']

def get_stub_state() -> State:
    """
    Build a small consistent fake State mirroring what Bibles.py sets up.

    Note: BibleVersions is kept consistent with preloadedBibles because the
    bySec branch of _ref_makeWorkNavListParagraph KeyErrors on unpreloaded
    versions (exactly like the original).
    """
    state = State()
    ot = StubBible( ['GEN', 'EXO', 'PSA', 'ISA'] )
    nt = StubBible( ['MRK', 'GAL'] )
    state.allBBBs = BBBS
    state.BibleVersions = ['OET', 'OET-RV', 'OET-LV', 'UHB', 'SR-GNT', 'T4T', 'LSV', 'TOSN']
    state.preloadedBibles = {
        'OET-RV': StubBible( BBBS ), 'OET-LV': StubBible( BBBS ),
        'UHB': ot, 'SR-GNT': nt,
        'T4T': StubBible( BBBS, sections=False ),  # no section headings
        'LSV': StubBible( BBBS, sections=False ),  # no section headings
    }
    if not hasattr( state, 'versionsWithoutTheirOwnPages' ):
        state.versionsWithoutTheirOwnPages = set()
    state.TEST_VERSIONS_ONLY = None
    return state


CASES = []
for __level in (0, 1, 2):
    for __va in ('OET-RV', 'UHB', 'SR-GNT', 'T4T', 'LSV', None):
        for __pt in ('chapter', 'section', 'book', 'sectionIndex',
                     'parallelVerse', 'interlinearVerse', 'relatedPassage',
                     'topicPassages', 'word', 'dictionaryEntry', 'TopIndex',
                     'about', 'news', 'OETKey', 'search'):
            for __ff in ('byC/GEN_C1.htm', 'bySec/MRK_S5.htm', 'GAL_3_16.htm',
                         'GEN_3_16.htm', None):
                # Skip combinations Python itself would crash on:
                if __pt in ('chapter', 'section', 'book') and __va is None:
                    continue # 'OET' in None would TypeError in Python
                if __ff is None and __pt in ('chapter', 'section', 'book',
                                             'parallelVerse', 'interlinearVerse',
                                             'relatedPassage', 'topicPassages', 'word'):
                    continue # adaptation path needs a filename once a BBB matches
                if __ff == 'bySec/MRK_S5.htm' and __pt not in ('section', 'sectionIndex'):
                    continue # Python asserts bySec links only on section pages
                CASES.append( (__level, __va, __pt, __ff) )


VIEW_BAR_CASES = [( __level, __va, __pt )
                  for __level in (0, 2)
                  for __va in ('OET-RV', 'OET-LV', 'UHB', 'T4T', 'LSV', 'OET', None,
                               'PLBL', 'UGNT', 'TOSN')
                  for __pt in ('book', 'chapter', 'section', 'details',
                               'workIndex', 'bookIndex', 'sectionIndex', 'chapterIndex')]


class TestMakeTopRustFidelity( unittest.TestCase ):

    def setUp( self ):
        self.state = get_stub_state()

    def test_makeTop_matches_reference_across_matrix( self ):
        """html.makeTop must be byte-identical to the former Python code."""
        for level, va, pt, ff in CASES:
            with self.subTest( level=level, va=va, pageType=pt, ff=ff ):
                expected = _ref_makeTop( level, va, pt, ff, self.state )
                actual = htmlModule.makeTop( level, va, pt, ff, self.state )
                self.assertEqual( actual, expected )

    def test_makeViewNavListParagraph_matches_reference( self ):
        """html.makeViewNavListParagraph must be byte-identical to the former Python code."""
        for level, va, pt in VIEW_BAR_CASES:
            with self.subTest( level=level, va=va, pageType=pt ):
                expected = _ref_makeViewNavListParagraph( level, va, pt, self.state )
                actual = htmlModule.makeViewNavListParagraph( level, va, pt, self.state )
                self.assertEqual( actual, expected )

    def test_known_page_types_all_covered( self ):
        """
        Every KNOWN_PAGE_TYPES member must produce output without error,
        except 'kingdomIndex', which the original Python elif chain also
        didn't cover (it crashed there with a NameError).
        """
        for pt in KNOWN_PAGE_TYPES:
            if pt == 'kingdomIndex':
                continue # see docstring
            with self.subTest( pageType=pt ):
                va = 'OET-RV' if pt in ('chapter', 'section', 'book') else None
                ff = 'byC/GEN_C1.htm' if pt in ('chapter', 'section', 'book') else \
                     ('bySec/MRK_S5.htm' if pt in ('section',) else None)
                result = htmlModule.makeTop( 1, va, pt, ff, self.state )
                self.assertTrue( result.startswith( '<!DOCTYPE html>' ) )


if __name__ == '__main__':
    unittest.main()
