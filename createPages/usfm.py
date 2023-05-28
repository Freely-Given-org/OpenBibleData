#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# usfm.py
#
# Module handling OpenBibleData USFM to HTML functions
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
Module handling usfm to html functions.

convertUSFMMarkerListToHtml( level:str, versionAbbreviation:str, refTuple:tuple, segmentType:str,
                        contextList:list, markerList:list, basicOnly:bool=False ) -> str
formatUSFMText( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                    usfmField, basicOnly=False, state ) -> str
livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                        introHtml:str, state ) -> str
livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str,
                                                                        state ) -> str
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()
"""
from gettext import gettext as _
from typing import Tuple
from pathlib import Path
import re
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, dPrint, vPrint
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

from html import checkHtml


LAST_MODIFIED_DATE = '2023-05-28' # by RJH
SHORT_PROGRAM_NAME = "usfm"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '0.46'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
NON_BREAK_SPACE = ' ' # NBSP

MAX_FOOTNOTE_CHARS = 11_000 # 1029 in FBV, 1688 in BRN, 10426 in CLV JOB!


def convertUSFMMarkerListToHtml( level:int, versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, markerList:list, basicOnly:bool, state ) -> str:
    """
    Loops through the given list of USFM lines
        and converts to a HTML segment as required.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {markerList} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {len(markerList)} )" )
    assert segmentType in ('book','section','chapter','verse'), f"Unexpected {segmentType=}"

    inMainDiv = inParagraph = inSection = inList = inListEntry = inTable = None
    inRightDiv = False
    html = ''
    for marker in contextList:
        if marker == 's1':
            rest = '--unknown--'
            if not basicOnly:
                html = f'{html}<div class="{marker}"><p class="s1">{rest}</p>\n'
                inSection = marker
        elif marker == 'p':
            if not basicOnly:
                html = f'{html}<p class="p">'
                inParagraph = marker
        elif segmentType == 'verse':
            if marker not in ('chapters', 'c'):
                Exception( f"Unexpected context for '{segmentType}': {contextList}" )
        elif marker not in ('chapters', 'c'):
            if refTuple[0] not in ('EXO','NUM') or marker!='list': Exception( f"Unexpected context for '{segmentType}': {contextList}" )

    C = V = None
    BBB = refTuple[0]
    if len(refTuple) > 1:
        C = refTuple[1]
        assert isinstance(C, str), f"{refTuple=}"
    if len(refTuple) > 2:
        V = refTuple[2]
        assert isinstance(V, str), f"{refTuple=}"

    for n, entry in enumerate(markerList):
        marker = entry.getMarker()
        rest = entry.getText() if basicOnly and 'OET' not in versionAbbreviation else entry.getFullText() # getText() has notes removed but doesn't work with wordlink numbers in OET
        if rest:
            if 'OET' in versionAbbreviation:
                rest = rest.replace( "'", "’" ) # Replace apostrophes
            elif versionAbbreviation in ('ULT','UST'):
                rest = rest.replace( '{', '\\add ' ).replace( '}', '\\add*' ) # Replace UST braces
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{n} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )
        # We try to put these in order of probability
        if marker in ('p~','v~'): # This has the actual verse text
            if not rest:
                logging.error( f"Expected verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            html = f'{html}{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}'
        elif marker == 'v': # This is where we want the verse marker
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            V = rest.strip() # Play safe
            # We don't display the verse number below for verse 1 (after chapter number)
            if '-' in V: # it's a verse range
                assert V[0].isdigit() and V[-1].isdigit(), f"Expected a verse number digit with {BBB} {C}:{V=} {rest=}"
                assert ':' not in V # We don't handle chapter ranges here yet (and probably don't need to)
                V1, V2 = V.split( '-' )
                # We want both verse numbers to be searchable
                if int(V2) != int(V1)+1: # We don't handle 3+ verse reordering well yet
                    logging.critical( f" Not handling 3+ verse bridge well yet at {versionAbbreviation} {refTuple} {C}:{V}" )
                vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}pa/{BBB}/C{C}V{V1}.htm">{V1}</a>'''
                html = f'{html}{"" if html.endswith(">") else " "}' \
                        + f'''{f"""<span id="C{C}"></span><span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}V1">{C}</span>""" if V1=="1" else f"""<span class="v" id="C{C}V{V1}">{vLink}-</span>"""}''' \
                        + f'<span class="v" id="C{C}V{V2}">{V2}{NARROW_NON_BREAK_SPACE}</span>' \
                        + (rest if rest else '≈')
            else: # it's a simple verse number
                if segmentType != 'verse': # No need for verse numbers at all if we're only displaying one verse
                    if not V.isdigit():
                        logging.critical( f"Expected a verse number digit at {versionAbbreviation} {refTuple} {C}:{V} {rest=}" )
                    cLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}pa/{BBB}/C{C}V1.htm">{C}</a>'''
                    vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}pa/{BBB}/C{C}V{V}.htm">{V}</a>'''
                    html = f'{html}{"" if html.endswith(">") or html.endswith("—") else " "}' \
                            + f'''{f"""<span id="C{C}"></span><span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}V1">{cLink}{NARROW_NON_BREAK_SPACE}</span>""" if V=="1" else f"""<span class="v" id="C{C}V{V}">{vLink}{NARROW_NON_BREAK_SPACE}</span>"""}'''
                # html = f'{html} <span class="v" id="C{refTuple[1]}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('¬v', ): # We can ignore these end markers
            assert not rest
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi', 'nb',
                            'pi1','pi2', 'pc','pm','pmc','pmo','po','pr', 'qm1','qm2', 'qr', 'cls'):
            assert not rest, f"Unexpected rest {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {marker}={rest}"
            if inMainDiv: # this can happen in INT module
                html = f'{html}</div><!--{inMainDiv}-->\n'
                inMainDiv = None
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if inParagraph:
                logging.critical( f"Already in paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                html = f'{html}</p>\n'
                inParagraph = None
            if inTable:
                html = f'{html}</inTable>\n'
                inTable = None
            # TODO: Shouldn't this apply to all markers???
            if marker=='m' and inList=='ul': # refTuple==('EXO',10,11)
                html = f'{html}</ul>\n'
                inList = None
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, versionAbbreviation , refTuple)
            if basicOnly:
                if html: html = f'{html}<br>' # Just start the new paragraph on a new line
            else: # not basicOnly
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi', '¬nb',
                            '¬pi1','¬pi2', '¬pc','¬pm','¬pmc','¬pmo','¬po','¬pr', '¬qm1','¬qm2', '¬qr', '¬cls'):
            assert not rest
            if inParagraph and inParagraph != marker[1:]:
                logging.critical( f"Closing wrong paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker=}" )
            if not basicOnly and inParagraph:
                html = f'{html}</p>\n'
                inParagraph = None
        elif marker in ('s1','s2','s3','s4'):
            if not rest:
                logging.critical( f"Expected heading text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            assert not inRightDiv
            if inTable:
                logging.critical( f"Table should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</{inTable}>\n'
                inTable = None
            if inList:
                logging.critical( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</{inList}>\n'
                inList = None
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
            else: # not in periph
                if marker == 's1':
                    if inSection == 's1': # Shouldn't happen
                        logger = logging.warning if segmentType=='verse' else logging.error
                        logger( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                        if not basicOnly:
                            html = f'{html}</div><!--{marker}-->\n'
                        inSection = None
                    elif inSection: # seems we had a s2/3/4 that wasn't closed
                        should_not_be_in_section
                    assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                else: logging.warning( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    rest = rest.replace( ' / ', f'{NON_BREAK_SPACE}/ ' ) # Stop forward slash from starting next line in section boxes
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            # TODO: Check what happens if V is a verse range
                            #   (Might need to add one to the end part, not the start part???)
                            nextV = '1' if V is None else V if segmentType=='section' else getLeadingInt(V)+1
                            html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}"><span class="s1cv">{C}:{nextV}</span> {formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                            inRightDiv = True
                        else:
                            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                        inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('¬s1','¬s2','¬s3','¬s4',):
            assert not rest
            assert inSection == marker[1:] and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=}"
            if not basicOnly:
                html = f'{html}</div><!--{marker[1:]}-->\n'
            inSection = None
        elif marker == 'r':
            # The following is not true for the ULT (e.g., see ULT Gen 5:1)
            # assert rest[0]=='(' and rest[-1]==')', f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            assert not inTable
            if not basicOnly:
                assert inSection, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                if 'OET' in versionAbbreviation:
                    assert inRightDiv, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                html = f'{html}<p class="{marker}">{rest}</p>\n'
        elif marker == 'c':
            # if segmentType == 'chapter':
            C, V = rest.strip(), '0' # Play safe
            # html = f'{html}<span class="{marker}" id="C{C}">{C}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('mt1','mt2','mt3','mt4'):
            assert rest
            if not inMainDiv:
                inMainDiv = 'bookHeader'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection != 'periph':
                if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
                    html = f'{html}</q1></div>\n'
                    inSection = inParagraph = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('imt1','imt2','imt3','imt4'):
            assert rest
            if inMainDiv == 'bookHeader':
                    html = f'{html}</div><!--{inMainDiv}-->\n'
                    inMainDiv = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection != 'periph':
                if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
                    html = f'{html}</q1></div>\n'
                    inSection = inParagraph = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('is1','is2','is3'):
            assert rest
            # if not rest:
            #     logging.critical( f"Expected heading text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inMainDiv == 'bookHeader':
                    html = f'{html}</div><!--{inMainDiv}-->\n'
                    inMainDiv = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
            assert not inRightDiv
            if inTable:
                logging.critical( f"Table should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inTable=} {inListEntry=} {marker=}" )
                html = f'{html}</inTable>\n'
                inTable = None
            if inList:
                logging.critical( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</{inList}>\n'
                inList = None
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
            else: # not in periph
                if marker == 's1':
                    if inSection == 's1': # Shouldn't happen
                        logger = logging.warning if segmentType=='verse' else logging.error
                        logger( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                        if not basicOnly:
                            html = f'{html}</div><!--{marker}-->\n'
                        inSection = None
                    elif inSection: # seems we had a s2/3/4 that wasn't closed
                        should_not_be_in_section
                    assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                else: logging.warning( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                            inRightDiv = True
                        else:
                            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                    inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker == 'rem': # This one can sort of be anywhere!
            assert rest
            assert not inRightDiv
            if inParagraph:
                html = f'{html}<span class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</span>\n'
            elif not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        # The following should all have their own data and get converted to a simple <p>…</p> field
        elif marker in ('mr','sr', 'd', 'sp', 'cp', 'qa','qc','qd'):
            if not rest:
                logging.critical( f"Expected field text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if inParagraph:
                logging.critical( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
            if basicOnly:
                if marker == 'd':
                    html = f'{html}<span class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</span>\n'
            else: #no basicOnly
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('b','ib'):
            html = f'{html}<br>'
        elif marker in ('list','ilist'):
            assert not rest
            assert not inList, f"inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}<ul>\n'
            inList = 'ul'
        elif marker in ('¬list','¬ilist'):
            assert not rest
            if not basicOnly and not inList:
                logging.critical( f"Not inList A {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inList:
                html = f'{html}</{inList}>{rest}'
                inList = None
        elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4'):
            if not basicOnly:
                if not inList:
                    logging.critical( f"Not inList B {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    inList = 'ul'
                    html = f'{html}<{inList}>\n'
            if inListEntry:
                logging.critical( f"already inListEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                html = f'{html}</li>\n'
                inListEntry = None
            html = f'{html}<li>{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}'
            inListEntry = marker
        elif marker in ('¬li1','¬li2','¬li3','¬li4', '¬ili1','¬ili2','¬ili3','¬ili4'):
            assert not rest
            if not basicOnly:
                assert inList, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
                assert inListEntry == marker[1:], f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            if inListEntry:
                html = f'{html}</li>\n'
                inListEntry = None
        elif marker == 'tr':
            if not inTable:
                html = f'{html}<table>'
                inTable = 'table'
            html = f'{html}<tr>{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</tr>'
        elif segmentType=='chapter' and marker in ('¬c','¬chapters'): # We can ignore this
            # Just do some finishing off
            if inSection=='s1' and marker == '¬c':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished chapter inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            elif inSection=='s1' and marker == '¬chapters':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished book inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            if inParagraph and marker == '¬c':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished paragraph inside section" )
                if not basicOnly:
                    html = f'{html}</p>\n'
                inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
        elif marker in ('ms1','ms2','ms3','ms4'):
            if inParagraph:
                logging.critical( f"Why still in paragraph {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</{inParagraph}>\n'
                inParagraph = None
            if inSection:
                logging.critical( f"Why still in section {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</div><!--{inSection}--\n'
                inSection = None
            # if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
            #     html = '{html}</q1></div>\n'
            #     inSection = inParagraph = None
            # assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                # NOTE: We don't treat it like a large section (which it is), but simply as a heading
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('¬ms1','¬ms2','¬ms3','¬ms4'):
            assert not rest
            # Nothing else to do here, because not treated (above) as a large section
        elif marker == 'vp#': # The "published" verse number (separated out from the other data)
            assert rest
            assert not inRightDiv
            html = f'{html}<span class="vp">{NARROW_NON_BREAK_SPACE}v{rest}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker == 'c~': # Stuff after the chapter number
            assert rest
            assert not inRightDiv
            html = f'{html}{NARROW_NON_BREAK_SPACE}{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}{NARROW_NON_BREAK_SPACE}'
        # The following should all have their own data and get converted to a simple <p>…</p> field
        elif marker in ('ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3', 'io1','io2','io3','io4'):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            introHtml = formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )
            if marker in ('io1','io2','io3','io4'):
                introHtml = livenIORs( versionAbbreviation, refTuple, segmentType, introHtml, state )
            else:
                introHtml = livenIntroductionLinks( versionAbbreviation, refTuple, segmentType, introHtml, state )
            html = f'{html}<p class="{marker}">{introHtml}</p>\n'
        elif marker in ('iot',):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p>\n'
        elif marker in ('¬iot',):
            assert not rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}</div><!--{marker[1:]}-->\n'
        elif marker in ('periph',):
            assert rest
            assert not basicOnly
            if inParagraph:
                html = f'{html}</p>'
                inParagraph = None
            if inSection == 'periph':
                html = f'{html}</div><!--periph-->\n'
                inSection = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<hr>\n<div class="periph">\n<h1>{rest}</h1>\n'
            inSection = marker
        elif marker == 'headers':
            assert not rest
            if C != '-1' :
                assert segmentType != 'verse', f"{versionAbbreviation} {segmentType=} {refTuple} {C}:{V}"
                assert not basicOnly
            assert not inMainDiv
            # if not inMainDiv:
            inMainDiv = 'bookHeader'
            html = f'{html}<div class="{inMainDiv}">'
        elif marker == 'intro':
            assert not rest
            if C != '-1' :
                assert segmentType != 'verse'
                assert not basicOnly
            if inMainDiv == 'bookHeader':
                html = f'{html}</div><!--{inMainDiv}-->\n'
                inMainDiv = None
            assert not inMainDiv
            # if not inMainDiv:
            inMainDiv = 'bookIntro'
            html = f'{html}<div class="{inMainDiv}">'
        elif marker in ('ie', '¬intro', 'chapters'):
            assert not rest
            if C != '-1' :
                assert segmentType != 'verse'
                assert not basicOnly
            if inMainDiv:
                html = f'{html}</div><!--{inMainDiv}-->\n'
                inMainDiv = None
        elif marker not in ('id','usfm','ide', 'sts',
                            'h', 'toc1','toc2','toc3', '¬headers',
                            'v=', 'c#', 'cl¤', '¬c', '¬chapters'): # We can ignore all of these
            if versionAbbreviation in ('ULT','UST'):
            # Can't list faulty books for uW stuff because there's too many errors keep popping up
            # and ('ACT' in refTuple or 'PSA' in refTuple or 'KI2' in refTuple): # Bad USFM encoding at UST Act 26:29-30
                logging.critical( f"Unexpected '{marker}' marker at {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {rest=}" )
            else:
                raise Exception( f"Unexpected '{marker}' marker {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {rest=}" )
        if '\\f ' not in html and '\\x ' not in html: # they're handled down below
            if '\\' in html:
                logging.critical( f"Left-over backslash in {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'" )
                if versionAbbreviation not in ('ULT','UST') \
                or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'DEU' not in refTuple): # ULT Gen 14:21, ISA and UST MAT has an encoding fault in 12:20 14Feb2023
                    raise Exception( f"Left-over backslash {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} '{html}'" )
    
    # Check for left-over unclosed segments
    logger = logging.critical if segmentType=='book' else logging.warning
    if inParagraph:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</p>\n'
    if inTable:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed table {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</{inTable}>\n'
    if inListEntry:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed listEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</li>\n'
    if inList:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed list {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</{inList}>\n'
    if inSection in ('s1','periph'):
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed '{inSection}' section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</div><!--{inSection}-->\n'
    if inMainDiv:
            logger( f"convertUSFMMarkerListToHtml final unclosed '{inMainDiv}' main section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
            html = f'{html}</div><!--{inMainDiv}-->\n'

    # Handle all footnotes in one go (we don't check here for matching \fr fields)
    footnotesCount = 0
    footnotesHtml = ''
    searchStartIx = 0
    for _outerSafetyCount in range( 2299 if segmentType in ('book','section') else 200 ): # max number of footnotes in segment (more than 250 in LEB DEU 12)
        fStartIx = html.find( '\\f ', searchStartIx )
        if fStartIx == -1: break # all done
        footnotesCount += 1
        fEndIx = html.find( '\\f*', fStartIx+3 )
        assert fEndIx != -1
        assert fStartIx+4 < fEndIx < fStartIx+MAX_FOOTNOTE_CHARS, f"Unexpected footnote size {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {fEndIx-fStartIx} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}"
        frIx = html.find( '\\fr ', fStartIx+3 ) # Might be absent
        fContentIx = html.find( '\\f', fStartIx+3 if frIx==-1 else frIx+3 )
        if fContentIx == fEndIx: fContentIx = -1
        if fContentIx == -1:
            logging.critical( f"No internal footnote markers {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}" )
            fContentIx = fStartIx + (5 if html[fStartIx:].startswith( '\\f + ') else 3)
        else:
            assert html[fContentIx+1:fContentIx+3] in ('ft','fq','fk','fl','fw','fp','fv'), \
                f"Unexpected '{html[fContentIx+1:fContentIx+3]}' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}"
        assert html[fContentIx:fContentIx+3] != '\\f*'
        if fStartIx+5 > fContentIx > fStartIx+16:
            logging.critical( f"Unexpected footnote start {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {fStartIx=} {fContentIx=} '{html[fStartIx:fStartIx+20]}'" ) # Skips ' + \\fr c:v '
        if frIx == -1:
            frText = ''
        else: # we have one
            assert fStartIx+5 <= frIx <= fStartIx+6, f"{fStartIx=} {frIx=} '{html[fStartIx:fStartIx+20]}'" # Skips ' + '
            frText = html[frIx+3:fContentIx].strip()
        fnoteMiddle = html[fContentIx:fEndIx]
        internalOpenCount = fnoteMiddle.count( '\\ft ') + fnoteMiddle.count( '\\fq ') + fnoteMiddle.count( '\\fqa ') + fnoteMiddle.count( '\\fk ') + fnoteMiddle.count( '\\fp ')
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\nProcessing {versionAbbreviation} {segmentType} {refTuple} footnote from '{fnoteMiddle}'" )
        if internalOpenCount > 0:
            # internalCloseCount = fnoteMiddle.count( '\\ft*') + fnoteMiddle.count( '\\fq*') + fnoteMiddle.count( '\\fqa*') + fnoteMiddle.count( '\\fk*')
            # internalMarkerCount = internalOpenCount - internalCloseCount
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Footnote middle has {internalOpenCount=} {internalCloseCount=} {internalMarkerCount=} '{fnoteMiddle}'" )
            inSpan = None
            internalSearchStartIx = 0
            for _innerSafetyCount in range( 70 ): # max number of fields in footnote -- 25 not enough for CLV
                internalStartIx = fnoteMiddle.find( '\\', internalSearchStartIx )
                if internalStartIx == -1: break # all done
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found backslash at index {internalStartIx} in '{fnoteMiddle}'" )
                fMarker = ''
                while internalStartIx + len(fMarker) < len(fnoteMiddle):
                    if fnoteMiddle[internalStartIx+len(fMarker)+1].islower():
                        fMarker = f'{fMarker}{fnoteMiddle[internalStartIx+len(fMarker)+1]}'
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Forming {fMarker=} from '{fnoteMiddle[internalStartIx:internalStartIx+10]}'" )
                    else: break
                if fnoteMiddle[internalStartIx+len(fMarker)+1] == ' ': # It's an opening marker
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got opening {fMarker=} from '{fnoteMiddle[internalStartIx:internalStartIx+10]}'" )
                    span = f'<span class="{fMarker}">'
                    if inSpan:
                        span = f'</span>{span}'
                        inSpan = None
                    inSpan = marker
                    fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{fnoteMiddle[internalStartIx+len(fMarker)+2:]}'
                elif fnoteMiddle[internalStartIx+len(fMarker)+1] == '*': # It's a closing marker
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got closing {fMarker=}" )
                    assert inSpan
                    fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{fnoteMiddle[internalStartIx+len(fMarker)+2:]}</span>'
                    inSpan = None
                else: unexpected_char in footnote
                internalSearchStartIx += len(fMarker) + 2
            else:
                logging.critical( f"inner_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_innerSafetyCount=}" )
                inner_fn_loop_needed_to_break
            if inSpan: # at end
                fnoteMiddle = f'{fnoteMiddle}</span>'
            assert '\\' not in fnoteMiddle, f"{fnoteMiddle[fnoteMiddle.index(f'{BACKSLASH}x')-10:fnoteMiddle.index(f'{BACKSLASH}x')+12]}"
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {refTuple} {fnoteMiddle=}" )
        sanitisedFnoteMiddle = fnoteMiddle
        if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '</span>', '' )
            for footnoteMarker in ('ft','xt', 'fq','fqa', 'fk','fl','fw','fp','fv', 'add', 'sc', 'wh','wg', 'jmp'): # These are USFM markers (and will be span classes)
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<span class="{footnoteMarker}">', '' )
            for charMarker in ('em','i', 'b', 'sup','sub'): # These are HTML markers
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<{charMarker}>', '' ).replace( f'</{charMarker}>', '' )
            if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
                logging.critical( f"Left-over HTML chars in {refTuple} {sanitisedFnoteMiddle=}" )
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '"', '&quot;' ).replace( '<', '&lt;' ).replace( '>', '&gt;' )
        assert '"' not in sanitisedFnoteMiddle and '<' not in sanitisedFnoteMiddle and '>' not in sanitisedFnoteMiddle, f"Left-over HTML chars in {refTuple} {sanitisedFnoteMiddle=}"
        fnoteCaller = f'<span class="fnCaller">[<a title="Note: {sanitisedFnoteMiddle}" href="#fn{footnotesCount}">fn</a>]</span>'
        fnoteRef = ''
        if frText:
            frCV = frText
            if '-' in frText or '–' in frText:
                frCV = frText.replace('–','-').split('-',1)[0]
            if ':' in frCV:
                frC, frV = frCV.split(':',1)
                frCV = f'#C{frC}V{frV}'
            elif '.' in frCV:
                frC, frV = frCV.split('.',1)
                frCV = f'#C{frC}V{frV}'
            else:
                logging.critical( f"What is CV ref for footnote ref: '{frText}'")
                frCV = ''
            fnoteRef = f'<span class="fnRef"><a title="Return to text" href="{frCV}">{frText}</a></span> '
        fnoteText = f'<p class="fn" id="fn{footnotesCount}">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p>\n'
        footnotesHtml = f'{footnotesHtml}{fnoteText}'
        html = f'{html[:fStartIx]}{fnoteCaller}{html[fEndIx+3:]}'
        searchStartIx = fEndIx + 3
    else:
        logging.critical( f"outer_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_outerSafetyCount=}" )
        outer_fn_loop_needed_to_break
    if footnotesHtml:
        if not checkHtml( f"Footnotes for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fnoteMiddle=}", footnotesHtml, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE: halt
        html = f'{html}<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n<div class="footnotes">\n{footnotesHtml}</div><!--footnotes-->\n'
    # TODO: Find out why these following exceptions occur
    if versionAbbreviation not in ('T4T','BRN','CLV','TCNT','TC-GNT'): # T4T ISA 33:8, BRN KI1 6:36a, CLV MRK 3:10, TCNT&TC-GNT INT \\fp Why???
        assert '\\f' not in html, f"{html[html.index(f'{BACKSLASH}f')-10:html.index(f'{BACKSLASH}f')+MAX_FOOTNOTE_CHARS]}"

    # Now handle all cross-references in one go (we don't check for matching \xo fields)
    pathPrefix = '' if segmentType=='chapter' else '../byC/'
    crossReferencesCount = 0
    crossReferencesHtml = ''
    searchStartIx = 0
    for _safetyCount1 in range( 999 if segmentType=='book' else 99 ):
        xStartIx = html.find( '\\x ', searchStartIx )
        if xStartIx == -1: break # all done
        crossReferencesCount += 1
        xoIx = html.find( '\\xo ', xStartIx+3 ) # Might be absent
        xtIx = html.find( '\\xt ', xStartIx+3 )
        assert xtIx != -1
        if xoIx == -1:
            xoText = ''
        else: # we have one
            assert xStartIx+5 <= xoIx <= xStartIx+6, f"{xStartIx=} {xoIx=} '{html[xStartIx:xStartIx+20]}'" # Skips ' + '
            xoText = html[xoIx+3:xtIx].strip()
        xEndIx = html.find( '\\x*', xtIx+3 )
        assert xEndIx != -1

        # Liven the cross-references themselves
        xrefLiveMiddle = xrefOriginalMiddle = html[xtIx+4:xEndIx]
        xrefOriginalMiddle = xrefOriginalMiddle.replace('\\xo ','').replace('\\xt ','') # Fix things like "Gen 25:9-10; \\xo b \\xt Gen 35:29."
        # print( f" {xrefLiveMiddle=}")
        assert xrefLiveMiddle.count('\\xo ') == xrefLiveMiddle.count('\\xo '), f"{xrefLiveMiddle=}"
        xrefLiveMiddle = xrefLiveMiddle.replace('\\xo ','<b>').replace('\\xt ','</b>') # Fix things like "Gen 25:9-10; \\xo b \\xt Gen 35:29."
        # TODO: The following code does not work for one chapter books (Jude 5), additional Vs (Mrk 3:4,5), or additional CVs (Mrk 3:4; 4:5)
        # TODO: The following code is untidy, not including combined verses in the link, e.g., Mrk 3:4-5
        refRegEx = re.compile( '([1-3]? ?[A-Z][a-z]{0,3}) ([1-9][0-9]{0,2}):([1-9][0-9]{0,2})' )
        reStartIx = 0
        for _safetyCount2 in range( 999 if segmentType=='book' else 99 ):
            match = refRegEx.search( xrefLiveMiddle, reStartIx )
            if not match: break
            # print( match.groups() )
            xB, xC, xV = match.groups()
            xBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( xB )
            xrefLiveMiddle = f'{xrefLiveMiddle[:match.start()]}<a title="View cross reference" href="{pathPrefix}{xBBB}_C{xC}.htm#C{xC}V{xV}">{match.group()}</a>{xrefLiveMiddle[match.end():]}'
            reStartIx = match.end() + 55 + len(pathPrefix) # approx number of characters that we add
        else:
            logging.critical( f"Inner xref loop needed to break for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple}" )
            inner_xr_loop_needed_to_break
        # print( f"  {xrefLiveMiddle=}")

        # Now create the caller and the actual xref
        xrefCaller = f'<span class="xrCaller">[<a  title="See also {xrefOriginalMiddle}" href="#xr{crossReferencesCount}">ref</a>]</span>' # was †
        xrefRef = ''
        if xoText:
            # TODO: The following code is untidy, marking b, c, d, in bold (above), but including a in the first link (which returns to the caller)
            xrCV = xoText
            if '-' in xoText or '–' in xoText:
                xrCV = xoText.replace('–','-').split('-',1)[0]
            if ':' in xrCV:
                xrC, xrV = xrCV.split(':',1)
                if ':' in xrV: # still -- presumably at end
                    xrV = xrV.split(':',1)[0]
                xrCV = f'#C{xrC}V{xrV}'
            else:
                logging.critical( f"What is CV ref for xref ref: '{xoText}'")
                xrCV = ''
            xrefRef = f'<span class="xrRef"><a title="Return to text" href="{xrCV}">{xoText}</a></span> '
        xrefText = f'<p class="xr" id="xr{crossReferencesCount}">{xrefRef}<span class="xrText">{xrefLiveMiddle}</span></p>\n'
        crossReferencesHtml = f'{crossReferencesHtml}{xrefText}'
        html = f'{html[:xStartIx]}{xrefCaller}{html[xEndIx+3:]}'
        searchStartIx = xEndIx + 3
    else: outer_xr_loop_needed_to_break
    if crossReferencesHtml:
        if not checkHtml( f"Cross-references for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple}", crossReferencesHtml, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE: halt
        html = f'{html}<hr style="width:40%;margin-left:0;margin-top: 0.3em">\n<div class="crossRefs">\n{crossReferencesHtml}</div><!--crossRefs-->\n'
    if versionAbbreviation not in ('BRN',): # BRN ISA 52
        assert '\\x' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}"

    if basicOnly: # remove leading, trailing, and internal blank lines
        while '<br><br>' in html:
            html = html.replace( '<br><br>', '<br>')
        while html.startswith( '<br>' ): # BSB and OEB seems particularly bad with blank lines
            html = html[4:]
        while html.endswith( '<br>' ): # LEB also
            html = html[:-4]

    if versionAbbreviation not in ('ULT','UST'): # uW stuff has too many USFM encoding errors
        assert 'strong="' not in html, f"{level=} '{versionAbbreviation}' {refTuple} {segmentType=} {len(contextList)=} {len(markerList)=} {basicOnly=} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
    if not checkHtml( f'convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
        if DEBUGGING_THIS_MODULE: halt
    return html
# end of usfm.convertUSFMMarkerListToHtml


def formatUSFMText( versionAbbreviation:str, refTuple:tuple, segmentType:str, usfmField:str, basicOnly:bool, state ) -> str:
    """
    Handles character formatting inside USFM lines.

    This includes \\fig and \\jmp
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers + ['fig']:
        openCount, closeCount = usfmField.count( f'\\{charMarker} ' ), usfmField.count( f'\\{charMarker}*' )
        if openCount != closeCount:
            logging.critical( f"Mismatched USFM character markers: '{charMarker}' open={openCount} close={closeCount} from {versionAbbreviation} {refTuple} '{usfmField}'" )

    ourBBB = refTuple[0]

    html = usfmField.replace( '\\+', '\\') # We don't want the embedded USFM marker style here

    # For now, we just remove \\fig entries
    if '\\fig' in usfmField: # e.g., \fig Jesus was immersed by John.|src="41_Mk_01_06_RG.jpg" size="col" loc="1:9" copy="© Sweet Publishing" ref="1:9"\fig*
        searchStartIx = 0
        for _safetyCount in range( 99 ):
            figStartIx = html.find( '\\fig ', searchStartIx )
            if figStartIx == -1: break # no more to find -- all done
            figPipeIx = html.find( '|', figStartIx+5 )
            assert figPipeIx != -1
            figEndIx = html.find( '\\fig*', figPipeIx+1 )
            assert figEndIx != -1
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Handling fig {versionAbbreviation} {refTuple} {segmentType} {searchStartIx} {figStartIx} {figPipeIx} {figEndIx} '{html[figStartIx:figEndIx+5]}'" )
            figGuts = html[figStartIx+5:figEndIx]
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got fig {versionAbbreviation} {refTuple} {segmentType} '{figGuts}' from '{html[figStartIx:figEndIx+5]}'" )
            word = '(Figure skipped)'
            html = f'{html[:figStartIx]}{word}{html[figEndIx+5:]}'
            searchStartIx = figStartIx + len(word) # coz we've made the html much shorter
        else: fig_loop_needed_to_break

    # Turn \\jmp entries into active links
    if '\\jmp' in usfmField: # e.g., \jmp debating|link-href="https://textandcanon.org/a-case-for-the-longer-ending-of-mark"\jmp*
        searchStartIx = 0
        for _safetyCount in range( 99 ):
            jmpStartIx = html.find( '\\jmp ', searchStartIx )
            if jmpStartIx == -1: break # no more to find -- all done
            jmpPipeIx = html.find( '|', jmpStartIx+5 )
            assert jmpPipeIx != -1
            jmpEndIx = html.find( '\\jmp*', jmpPipeIx+1 )
            assert jmpEndIx != -1
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Handling jmp {versionAbbreviation} {refTuple} {segmentType} {searchStartIx} {jmpStartIx} {jmpPipeIx} {jmpEndIx} '{html[jmpStartIx:jmpEndIx+5]}'" )
            jmpDisplay, jmpLinkBit = html[jmpStartIx+5:jmpPipeIx], html[jmpPipeIx+1:jmpEndIx]
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got jmp {versionAbbreviation} {refTuple} {segmentType} {jmpDisplay=} and {jmpLinkBit=} from '{html[jmpStartIx:jmpEndIx+5]}'" )
            assert jmpLinkBit.startswith( 'link-href="' ) and jmpLinkBit.endswith( '"' )
            jmpLink = jmpLinkBit[11:-1]
            if jmpLink.startswith( 'http' ): # then it's an external internet link
                newLink = f'<a title="Go to external jump link" href="{jmpLink}">{jmpDisplay}</a>'
            else: # it's likely to be a link into another work
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"What is this '{jmpDisplay}' link to '{jmpLink}' expecting to jump to?" )
                if jmpLink.startswith( '#' ):
                    assert jmpLink.startswith( '#C' ), f"Got internal jmp {versionAbbreviation} {refTuple} {segmentType} {jmpDisplay=} and {jmpLink=} from '{html[jmpStartIx:jmpEndIx+5]}'"
                    assert 'V' in jmpLink, f"Got internal jmp {versionAbbreviation} {refTuple} {segmentType} {jmpDisplay=} and {jmpLink=} from '{html[jmpStartIx:jmpEndIx+5]}'"
                    Vix = jmpLink.index( 'V' )
                    refC, refV = jmpLink[2:Vix], jmpLink[Vix+1:]
                    # print( f"{jmpLink=} {ourBBB=} {refC=} {refV=}")
                    if segmentType == 'book':
                        newLink = f'<a title="Go to internal jump link reference document" href="{jmpLink}">{jmpDisplay}</a>'
                    elif segmentType == 'chapter':
                        newLink = f'<a title="Go to internal jump link reference chapter" href="{ourBBB}_C{refC}.htm#C{refC}V{refV}">{jmpDisplay}</a>'
                    elif segmentType == 'verse':
                        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
                        # print( f"{versionAbbreviation}, {refTuple}, {ourBBB=} {refC=} {refV=} {jmpDisplay=}" )
                        newLink = f'<a title="Go to internal jump link reference verse" href="C{refC}V{refV}.htm#Top">{jmpDisplay}</a>'
                    elif segmentType == 'section':
                        try: # Now find which section that reference starts in
                            # print( f"{state.sectionsLists[versionAbbreviation][ourBBB]=}" )
                            intV = getLeadingInt(refV)
                            found = False
                            for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                                if startC==refC and endC==refC:
                                    if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                                        found = True
                                        break
                                elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                                    found = True
                                    break
                                elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                                    found = True
                                    break
                            if found:
                                newLink = f'<a title="Go to to section page with reference" href="{ourBBB}_S{n}.htm">{jmpDisplay}</a>'
                            else:
                                logging.critical( f"unable_to_find_reference for {ourBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in state.sectionsLists[versionAbbreviation]]}" )
                                newLink = jmpDisplay # Can't make a link
                                unable_to_find_reference # Need to write more code
                        except KeyError:
                            logging.critical( f"formatUSFMText for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
                            newLink = guts # Can't make a link
                    else:
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, '{usfmField}' )" )
                        jmp_ooopsie
                    newLink = f'<a title="Go to internal jump link" href="{jmpLink}">{jmpDisplay}</a>'
                    # print( f"Got {newLink=}")
                else: # unknown link type
                    unknown_jmp_link_type
            html = f'{html[:jmpStartIx]}{newLink}{html[jmpEndIx+5:]}'
            searchStartIx = jmpStartIx + len(newLink) # coz we've changed the size of the html
        else: jmp_loop_needed_to_break

    # Handle \\w markers (mostly only occur if basicOnly is false)
    if '\\w ' in usfmField or '\\+w ' in usfmField:
        # if versionAbbreviation in ('NET',): # \\w fields in NET seem to now only contain the English word
            # assert '|' not in usfmField, f"Found pipe {versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
        if '|' not in usfmField:
            usfmField = usfmField.replace( '\\w ', '' ).replace( '\\w*', '' ) \
                                 .replace( '\\+w ', '' ).replace( '\\+w*', '' )
        else: # Fields like \\w of|x-occurrence="1" x-occurrences="3"\\w* for ULT/UST, WEB has strongs
            # NET from eBible.org seems to have a mix,
            #   e.g., "\\w So|strong="H6213"\\w* \\w the king\\w* \\w stayed\\w*"
            searchStartIx = 0
            for _safetyCount in range( 299 ):
                searchString = '\\w '
                wStartIx = html.find( searchString, searchStartIx )
                if wStartIx == -1:
                    searchString = '\\+w '
                    wStartIx = html.find( searchString, searchStartIx )
                if wStartIx == -1: # still
                    break # no more to find -- all done
                pipeIx = html.find( '|', wStartIx+len(searchString) ) # Might be -1 if there's no more, or might be more than wEndIx if there's none in this word
                wEndIx = html.find( f'{searchString[:-1]}*', wStartIx+len(searchString) )
                assert wEndIx != -1
                if pipeIx > wEndIx: # then it must be in the next word!
                    pipeIx = -1 # so just act as if there wasn't one :)
                if pipeIx != -1:
                    assert wStartIx+len(searchString) < pipeIx < wEndIx, f"{searchStartIx=} {wStartIx=} {pipeIx=} {wEndIx=}"
                word = html[wStartIx+len(searchString):wEndIx] if pipeIx==-1 else html[wStartIx+len(searchString):pipeIx]
                html = f'{html[:wStartIx]}{word}{html[wEndIx+len(searchString):]}'
                searchStartIx += len(word) # coz we've made the html much shorter
            else:
                wCount = usfmField.count( '\\w ' ) + usfmField.count( '\\+w ' )
                raise Exception( f"formatUSFMText() w loop needed to break at {versionAbbreviation} {refTuple} '{segmentType}' with ({wCount:,}) '{usfmField}'" )
            assert '\\w ' not in html and '\\+w ' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}" # Note: can still be \\wj in text

    # Replace the character markers which have specific HMTL equivalents
    html = html \
            .replace( '\\bdit ', '<b><i>' ).replace( '\\bdit*', '</i></b>' ) \
            .replace( '\\bd ', '<b>' ).replace( '\\bd*', '</b>' ) \
            .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
            .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
            .replace( '\\sup ', '<sup>' ).replace( '\\sup*', '</sup>' )
    # Now replace all the other character markers into HTML spans, e.g., \\add \\nd \\bk
    for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers:
        html = html.replace( f'\\{charMarker} ', f'<span class="{charMarker}">' ).replace( f'\\{charMarker}*', '</span>' )

    # Final checking
    if versionAbbreviation not in ('UST','ULT'): # uW stuff has too many USFM encoding errors and inconsistencies
        assert 'strong="' not in html, f"'{versionAbbreviation}' {refTuple} {segmentType=} {basicOnly=} {usfmField=}\n  html='{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
    if '\\ts\\*' in html:
        logging.critical( f"Removing ts marker in {versionAbbreviation} {refTuple} {segmentType} {basicOnly=}…")
        html = html.replace( '\\ts\\*', '' )
    if '\\f ' not in html and '\\x ' not in html:
        # AssertionError: versionAbbreviation='ULT' refTuple=('ISA',) segmentType='book' 'usfmField='\\w to|x-occurrence="1" x-occurrences="2"\\w* \\w dishonor|x-occurrence="1" x-occurrences="1"\\w* \\zaln-s |x-strong="H1347" x-lemma="גָּאוֹן" x-morph='' basicOnly=False 'to dishonor \zaln-s |x-strong="H1347" x-lemma="גָּאוֹן" x-morph='
        if (versionAbbreviation not in ('TCNT','TC-GNT') or 'INT' not in refTuple) \
        and (versionAbbreviation not in ('ULT','UST') \
            or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'DEU' not in refTuple)): # ULT Gen 14:20, ISA and UST MAT has an encoding fault in 12:20 14Feb2023
            assert '\\' not in html, f"{versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
    if not checkHtml( f'formatUSFMText({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
        if DEBUGGING_THIS_MODULE: halt
    return html
# end of usfm.formatUSFMText


# TODO: Currently 'about Jesus the messiah (Acts 12:25, 13:13).' this wrongly thinks 13:13 is in the current book!
singleBCVRefRegex = re.compile( '([(])([^()]+?) ([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?([ ,.?!:;)])' )
singleCVRefRegex = re.compile( '([ (])([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?([ ,.?!:;)])' )
def livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str, introHtml:str, state ) -> str:
    """
    Liven general links in the introduction, e.g., 'was named Mary (Acts 12:12)' or 'accompanied Peter (1 Peter 5:13)'
        or 'about Jesus the messiah (Acts 12:25, 13:13).'
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
    assert '\\ior' not in introHtml
    assert 'class="ior"' not in introHtml

    ourBBB = refTuple[0]

    # Search for B/C/V string in parentheses, e.g., '(Acts 12:12)' or '(Col. 4:10)' or '(1 Peter 5:13)'
    #   or surrounded by spaces or space and punctuation
    searchStartIx = 0
    while True:
        match = singleBCVRefRegex.search( introHtml, searchStartIx )
        if not match: break
        guts = match.group(0)[1:-1] # Remove the parentheses or other surrounding chars
        preChar, refB, refC, refV, refRest, postChar = match.groups()
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {versionAbbreviation} intro ref CV match with '{preChar}' '{guts}' '{postChar}' -> {match.groups()=}" )
        refBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( refB )
        if segmentType == 'book':
            newGuts = f'<a title="Go to reference document" href="{refBBB}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Go to reference chapter" href="{refBBB}_C{refC}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'verse': # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{refC}V{refV}.htm#Top">{guts}</a>'
        elif segmentType == 'section':
            try: # Now find which section that reference starts in
                # print( f"{state.sectionsLists[versionAbbreviation][refBBB]=}" )
                intV = getLeadingInt(refV)
                found = False
                for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( state.sectionsLists[versionAbbreviation][refBBB] ):
                    if startC==refC and endC==refC:
                        if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                            found = True
                            break
                    elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                        found = True
                        break
                    elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                        found = True
                        break
                if found:
                    newGuts = f'<a title="Go to to section page with reference" href="{refBBB}_S{n}.htm">{guts}</a>'
                else:
                    logging.critical( f"unable_to_find_reference for {refBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in state.sectionsLists[versionAbbreviation]]}" )
                    newGuts = guts # Can't make a link
                    unable_to_find_reference # Need to write more code
            except KeyError:
                logging.critical( f"livenIntroductionLinks for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
                newGuts = guts # Can't make a link
        else:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            ooopsie1
        introHtml = f"{introHtml[:match.start()]}{preChar}{newGuts}{postChar}{introHtml[match.end():]}"
        searchStartIx = match.end() + len(newGuts)+2 - len(guts) # Approx chars that we added

    # Search for C/V string in parentheses, e.g., '(12:12)' or '(16:9-20)'
    #   or surrounded by spaces or space and punctuation
    searchStartIx = 0
    while True:
        match = singleCVRefRegex.search( introHtml, searchStartIx )
        if not match: break
        guts = match.group(0)[1:-1] # Remove the parentheses or other surrounding chars
        preChar, refC, refV, refRest, postChar = match.groups()
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {versionAbbreviation} intro ref CV match with '{preChar}' '{guts}' '{postChar}' -> {match.groups()=}" )
        logging.critical( f"Assuming '{guts}' ref in {ourBBB} intro is a self-reference BUT THIS IS QUITE LIKELY WRONG" )
        if segmentType == 'book':
            newGuts = f'<a title="Jump down to reference" href="#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Jump to chapter page with reference" href="{ourBBB}_C{refC}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'verse': # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{refC}V{refV}.htm#Top">{guts}</a>'
        elif segmentType == 'section':
            try: # Now find which section that reference starts in
                intV = getLeadingInt(refV)
                found = False
                for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                    if startC==refC and endC==refC:
                        if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                            found = True
                            break
                    elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                        found = True
                        break
                    elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                        found = True
                        break
                if found:
                    newGuts = f'<a title="Jump to section page with reference" href="{ourBBB}_S{n}.htm">{guts}</a>'
                else:
                    logging.critical( f"PROBABLY WRONGLY GUESSED BOOK: unable_to_find_reference for {ourBBB=} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in state.sectionsLists[versionAbbreviation][ourBBB]]}" )
                    newGuts = guts # Can't make a link
                    # unable_to_find_reference # Need to write more code
            except KeyError:
                logging.critical( f"livenIntroductionLinks for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
                newGuts = guts # Can't make a link
        else:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            ooopsie2
        introHtml = f"{introHtml[:match.start()]}{preChar}{newGuts}{postChar}{introHtml[match.end():]}"
        searchStartIx = match.end() + len(newGuts)+2 - len(guts) # Approx chars that we added

    return introHtml
# end of usfm.livenIntroductionLinks


def livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str, state ) -> str:
    """
    Given some html, search for <span class="ior"> (these are usually in introduction \\iot lines)
        and liven those IOR links.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )" )
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )" )
    assert '\\ior' not in ioLineHtml

    ourBBB = refTuple[0]

    searchStartIx = 0
    for _safetyCount in range( 15 ):
        ixSpanStart = ioLineHtml.find( '<span class="ior">', searchStartIx ) # Length of this string is 18 chars (used below)
        if ixSpanStart == -1: break
        ixEnd = ioLineHtml.find( '</span>', ixSpanStart+18 )
        assert ixEnd != -1
        guts = ioLineHtml[ixSpanStart+18:ixEnd].replace('–','-') # Convert any en-dash to hyphen
        # print(f"{BBB} {guts=} {bookHTML[ix-20:ix+20]} {searchStartIx=} {ixSpanStart=} {ixEnd=}")
        startGuts = guts.split('-')[0]
        # print(f"  Now {guts=}")
        if ':' in startGuts:
            assert startGuts.count(':') == 1 # We expect a single C:V at this stage
            Cstr, Vstr = startGuts.strip().split( ':' )
        elif BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( ourBBB ):
            Cstr, Vstr = '1', startGuts.strip() # Only a verse was given
        else: Cstr, Vstr = startGuts.strip(), '1' # Only a chapter was given
        if segmentType == 'book':
            newGuts = f'<a title="Jump down to reference" href="#C{Cstr}V{Vstr}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Jump to chapter page with reference" href="{ourBBB}_C{Cstr}.htm#C{Cstr}V{Vstr}">{guts}</a>'
        elif segmentType == 'verse': # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{Cstr}V{Vstr}.htm#Top">{guts}</a>'
        elif segmentType == 'section':
            try: # Now find which section that IOR starts in
                intV = getLeadingInt(Vstr)
                found = False
                for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                    if startC==Cstr and endC==Cstr:
                        # print( f"Single chapter {startC}=={Cstr}=={endC} {getLeadingInt(startV)=} {intV=} {getLeadingInt(endV)=}")
                        if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                            found = True
                            break
                    elif startC==Cstr and intV>=getLeadingInt(startV): # It's in the first chapter
                        found = True
                        break
                    elif endC==Cstr and intV<=getLeadingInt(endV): # It's in the second chapter
                        found = True
                        break
                if found:
                    newGuts = f'<a title="Jump to section page with reference" href="{ourBBB}_S{n}.htm">{guts}</a>'
                else:
                    logging.critical( f"unable_to_find_IOR for {ourBBB} {Cstr}:{Vstr} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in state.sectionsLists[versionAbbreviation][ourBBB]]}" )
                    newGuts = guts # Can't make a link
                    unable_to_find_reference # Need to write more code
            except KeyError:
                logging.critical( f"livenIORs for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
                newGuts = guts # Can't make a link
        else:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )" )
            ooops

        ioLineHtml = f'{ioLineHtml[:ixSpanStart+18]}{newGuts}{ioLineHtml[ixEnd:]}'
        searchStartIx = ixEnd + len(newGuts) - len(guts) # Approx number of chars that we add
    else:
        # logging.critical( f"inner_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_innerSafetyCount=}" )
        usfm_liven_IOR_loop_needed_to_break

    return ioLineHtml
# end of usfm.livenIORs function


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the usfm object
    pass
# end of usfm.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the usfm object
    pass
# end of usfm.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of usfm.py
