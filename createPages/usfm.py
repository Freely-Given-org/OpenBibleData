#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# usfm.py
#
# Module handling OpenBibleData USFM to HTML functions
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
Module handling usfm to html functions.

convertUSFMMarkerListToHtml( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                        contextList:list, markerList:list, basicOnly:bool=False ) -> str
formatUSFMText( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                    usfmField, basicOnly=False ) -> str

briefDemo() -> None
fullDemo() -> None
main calls fullDemo()
"""
from gettext import gettext as _
# from typing import Dict, List, Tuple
from pathlib import Path
# import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from html import checkHtml


LAST_MODIFIED_DATE = '2023-02-07' # by RJH
SHORT_PROGRAM_NAME = "usfm"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '0.16'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '

MAX_FOOTNOTE_CHARS = 1800 # 1029 in FBV, 1688 in BRN!


def convertUSFMMarkerListToHtml( versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, markerList:list, basicOnly:bool=False ) -> str:
    """
    Loops through a list of USFM lines
        and converts to a HTML segment as required.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {markerList} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {len(markerList)} )" )

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
    if len(refTuple) > 1: C = refTuple[1]
    if len(refTuple) > 2: V = refTuple[2]

    for n, entry in enumerate(markerList):
        marker = entry.getMarker()
        rest = entry.getText() if basicOnly else entry.getFullText()
        if rest:
            if 'OET' in versionAbbreviation:
                rest = rest.replace( "'", "’" ) # Replace apostrophes
            elif versionAbbreviation in ('ULT','UST'):
                rest = rest.replace( '{', '\\add ' ).replace( '}', '\\add*' ) # Replace braces
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{n} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )
        # We try to put these in order of probability
        if marker in ('p~','v~'): # This has the actual verse text
            if not rest:
                logging.error( f"Expected verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            html = f'{html}{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}'
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
                vLink = f'<a href="../../../parallel/{BBB}/C{C}_V{V1}.html">{V1}</a>'
                html = f'{html}{"" if html.endswith(">") else " "}' \
                        + f'{f"""<span id="C{C}"></span><span class="c" id="C{C}V1">{C}</span>""" if V1=="1" else f"""<span class="v" id="C{C}V{V1}">{vLink}-</span>"""}' \
                        + f'<span class="v" id="C{C}V{V2}">{V2}{NARROW_NON_BREAK_SPACE}</span>' \
                        + (rest if rest else '≈')
            else: # it's a simple verse number
                if segmentType != 'verse': # No need for verse numbers at all if we're only displaying one verse
                    if not V.isdigit():
                        logging.critical( f"Expected a verse number digit at {versionAbbreviation} {refTuple} {C}:{V} {rest=}" )
                    cLink = f'<a href="../../../parallel/{BBB}/C{C}_V1.html">{C}</a>'
                    vLink = f'<a href="../../../parallel/{BBB}/C{C}_V{V}.html">{V}</a>'
                    html = f'{html}{"" if html.endswith(">") or html.endswith("—") else " "}' \
                            + f'{f"""<span id="C{C}"></span><span class="c" id="C{C}V1">{cLink}{NARROW_NON_BREAK_SPACE}</span>""" if V=="1" else f"""<span class="v" id="C{C}V{V}">{vLink}{NARROW_NON_BREAK_SPACE}</span>"""}'
                # html = f'{html} <span class="v" id="C{refTuple[1]}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('¬v', ): # We can ignore these end markers
            assert not rest
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi', 'nb',
                            'pi1','pi2', 'pc','pm','pmo','po','pr', 'qm1','qm2', 'qr', 'cls'):
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
            # TODO: Shouldn't this apply to all markers???
            if marker=='m' and inList=='ul': # refTuple==('EXO',10,11)
                html = f'{html}</ul>\n'
                inList = None
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, versionAbbreviation , refTuple)
            if not basicOnly:
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi', '¬nb',
                            '¬pi1','¬pi2', '¬pc','¬pm','¬pmo','¬po','¬pr', '¬qm1','¬qm2', '¬qr', '¬cls'):
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
            if inList:
                logging.critical( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</{inList}>\n'
                inList = None
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
                else: logging.critical( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
                            inRightDiv = True
                        else:
                            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
                    inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
            # if segmentType == 'chapters':
            C = rest.strip() # Play safe
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
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
            if inList:
                logging.critical( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</{inList}>\n'
                inList = None
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
                else: logging.critical( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
                            inRightDiv = True
                        else:
                            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
                    inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
        elif marker == 'rem': # This one can sort of be anywhere!
            assert rest
            assert not inRightDiv
            if inParagraph:
                html = f'{html}<span class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</span>\n'
            elif not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
        # The following should all have their own data and get converted to a simple <p>...</p> field
        elif marker in ('mr','sr', 'd', 'sp', 'cp', 'qa','qc','qd'):
            if not rest:
                logging.critical( f"Expected field text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if inParagraph:
                logging.critical( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
            if not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
                logging.critical( f"Not inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inList:
                html = f'{html}</{inList}>{rest}'
                inList = None
        elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4'):
            if not basicOnly:
                if not inList:
                    logging.critical( f"Not inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    inList = 'ul'
                    html = f'{html}<{inList}>\n'
            if inListEntry:
                logging.critical( f"already inListEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                html = f'{html}</li>\n'
                inListEntry = None
            html = f'{html}<li>{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}'
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
            assert not rest
            if not inTable:
                inTable = True
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
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
            html = f'{html}{NARROW_NON_BREAK_SPACE}{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}{NARROW_NON_BREAK_SPACE}'
        # The following should all have their own data and get converted to a simple <p>...</p> field
        elif marker in ('ip','im', 'io1','io2','io3','io4'):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<p class="{marker}">{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}</p>\n'
        elif marker in ('iot',):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}</p>\n'
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
            html = f'{html}<hr><div class="periph">\n<h1>{rest}</h1>\n'
            inSection = marker
        elif marker == 'headers':
            assert not rest
            if not inMainDiv:
                inMainDiv = 'bookHeader'
                html = f'{html}<div class="{inMainDiv}">'
        elif marker == 'intro':
            assert not rest
            if inMainDiv == 'bookHeader':
                html = f'{html}</div><!--{inMainDiv}-->\n'
                inMainDiv = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
        elif marker in ('ie', '¬intro', 'chapters'):
            assert not rest
            if inMainDiv:
                html = f'{html}</div><!--{inMainDiv}-->\n'
                inMainDiv = None
        elif marker not in ('id','usfm','ide', 'sts',
                            'h', 'toc1','toc2','toc3', '¬headers',
                            'v=', 'c#', 'cl¤', '¬c', '¬chapters'): # We can ignore all of these
            # logging.critical( f"Unexpected '{marker}' marker at {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {rest=}" )
            raise Exception( f"Unexpected marker {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
        if '\\f ' not in html and '\\x ' not in html: # they're handled down below
            if '\\' in html:
                logging.critical( f"Left-over backslash in {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} '{html}'" )
                raise Exception( f"Left-over backslash {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} '{html}'" )
    if inParagraph:
        if not basicOnly:
            logging.critical( f"convertUSFMMarkerListToHtml final unclosed paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</p>\n'
    if inListEntry:
        if not basicOnly:
            logging.critical( f"convertUSFMMarkerListToHtml final unclosed listEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</li>\n'
    if inList:
        if not basicOnly:
            logging.critical( f"convertUSFMMarkerListToHtml final unclosed list {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</{inList}>\n'
    if inSection in ('s1','periph'):
        if not basicOnly:
            logging.critical( f"convertUSFMMarkerListToHtml final unclosed '{inSection}' section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</div><!--{inSection}-->\n'
    if inMainDiv == 'bookHeader':
            logging.critical( f"convertUSFMMarkerListToHtml final unclosed '{inMainDiv}' main section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
            html = f'{html}</div><!--{inMainDiv}-->\n'

    # Handle all footnotes in one go (we don't check for matching \fr fields)
    footnotesCount = 0
    footnotesHtml = ''
    searchStartIx = 0
    for _safetyCount1 in range( 999 if segmentType=='book' else 199 ):
        fStartIx = html.find( '\\f ', searchStartIx )
        if fStartIx == -1: break # all done
        footnotesCount += 1
        fEndIx = html.find( '\\f*', fStartIx+3 )
        assert fEndIx != -1
        assert fStartIx+4 < fEndIx < fStartIx+MAX_FOOTNOTE_CHARS, f"Unexpected footnote size {versionAbbreviation} {segmentType} {basicOnly=} {BBB} {footnotesCount=} {fEndIx-fStartIx} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}"
        frIx = html.find( '\\fr ', fStartIx+3 ) # Might be absent
        fContentIx = html.find( '\\f', fStartIx+3 if frIx==-1 else frIx+3 )
        if fContentIx == fEndIx: fContentIx = -1
        if fContentIx == -1:
            logging.critical( f"No internal footnote markers {versionAbbreviation} {segmentType} {basicOnly=} {BBB} {footnotesCount=} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}" )
            fContentIx = fStartIx + (5 if html[fStartIx:].startswith( '\\f + ') else 3)
        else:
            assert html[fContentIx+1:fContentIx+3] in ('ft','fq','fk','fl','fw','fp','fv'), \
                f"Unexpected '{html[fContentIx+1:fContentIx+3]}' {versionAbbreviation} {segmentType} {basicOnly=} {BBB} {footnotesCount=} {html[fStartIx:fStartIx+2*MAX_FOOTNOTE_CHARS]}"
        assert html[fContentIx:fContentIx+3] != '\\f*'
        if fStartIx+5 > fContentIx > fStartIx+16:
            logging.critical( f"Unexpected footnote start {versionAbbreviation} {segmentType} {basicOnly=} {BBB} {footnotesCount=} {fStartIx=} {fContentIx=} '{html[fStartIx:fStartIx+20]}'" ) # Skips ' + \\fr c:v '
        if frIx == -1:
            frText = ''
        else: # we have one
            assert fStartIx+5 <= frIx <= fStartIx+6, f"{fStartIx=} {frIx=} '{html[fStartIx:fStartIx+20]}'" # Skips ' + '
            frText = html[frIx+3:fContentIx].strip()
        fnoteMiddle = html[fContentIx:fEndIx]
        internalOpenCount = fnoteMiddle.count( '\\ft ') + fnoteMiddle.count( '\\fq ') + fnoteMiddle.count( '\\fqa ')
        if internalOpenCount > 0:
            # internalCloseCount = fnoteMiddle.count( '\\ft*') + fnoteMiddle.count( '\\fq*') + fnoteMiddle.count( '\\fqa*')
            # internalMarkerCount = internalOpenCount - internalCloseCount
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Footnote middle has {internalOpenCount=} {internalCloseCount=} {internalMarkerCount=} '{fnoteMiddle}'" )
            inSpan = None
            internalSearchStartIx = 0
            for _safetyCount2 in range( 25 ):
                internalStartIx = fnoteMiddle.find( '\\', internalSearchStartIx )
                if internalStartIx == -1: break # all done
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found backslash at index {internalStartIx} in '{fnoteMiddle}'" )
                fMarker = ''
                while internalStartIx + len(fMarker) < len(fnoteMiddle):
                    if fnoteMiddle[internalStartIx+len(fMarker)+1].islower():
                        fMarker = f'{fMarker}{fnoteMiddle[internalStartIx+len(fMarker)+1]}'
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Forming {fMarker=}" )
                    else: break
                if fnoteMiddle[internalStartIx+len(fMarker)+1] == ' ': # It's an opening marker
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got opening {fMarker=}" )
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
            else: inner_fn_loop_needed_to_break
            if inSpan: # at end
                fnoteMiddle = f'{fnoteMiddle}</span>'
            assert '\\' not in fnoteMiddle, f"{fnoteMiddle[fnoteMiddle.index(f'{BACKSLASH}x')-10:fnoteMiddle.index(f'{BACKSLASH}x')+12]}"
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{BBB} {fnoteMiddle=}" )
        sanitisedFnoteMiddle = fnoteMiddle
        if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '</span>', '' )
            for footnoteMarker in ('ft','xt', 'fq','fqa', 'fk','fl','fw','fp','fv', 'add'):
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<span class="{footnoteMarker}">', '' )
            for charMarker in ('em','i', 'b','sup', 'sub'):
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<{charMarker}>', '' ).replace( f'</{charMarker}>', '' )
            if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
                logging.critical( f"Left-over HTML chars in {BBB} {sanitisedFnoteMiddle=}" )
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '"', '&quot;' ).replace( '<', '&lt;' ).replace( '>', '&gt;' )
        assert '"' not in sanitisedFnoteMiddle and '<' not in sanitisedFnoteMiddle and '>' not in sanitisedFnoteMiddle, f"Left-over HTML chars in {BBB} {sanitisedFnoteMiddle=}"
        fnoteCaller = f'<span class="fnCaller" title="Note: {sanitisedFnoteMiddle}">[<a href="#fn{footnotesCount}">fn</a>]</span>'
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
            fnoteRef = f'<span class="fnRef"><a href="{frCV}">{frText}</a></span> '
        fnoteText = f'<p class="fn" id="fn{footnotesCount}">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p>\n'
        footnotesHtml = f'{footnotesHtml}{fnoteText}'
        html = f'{html[:fStartIx]}{fnoteCaller}{html[fEndIx+3:]}'
        searchStartIx = fEndIx + 3
    else: outer_fn_loop_needed_to_break
    if footnotesHtml:
        checkHtml( f"{versionAbbreviation} {segmentType} {basicOnly=} {BBB} footnote {fnoteMiddle=}", footnotesHtml, segmentOnly=True )
        html = f'{html}<hr><div class="footnotes">\n{footnotesHtml}</div><!--footnotes-->\n'
    if versionAbbreviation not in ('T4T','BRN',): # T4T ISA 33:8, BRN KI1 6:36a
        assert '\\f' not in html, f"{html[html.index(f'{BACKSLASH}f')-10:html.index(f'{BACKSLASH}f')+12]}"

    # Now handle all cross-references in one go (we don't check for matching \xo fields)
    crossReferencesCount = 0
    crossReferencesHtml = ''
    searchStartIx = 0
    for _safetyCount in range( 999 if segmentType=='book' else 99 ):
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
        xrefMiddle = html[xtIx+4:xEndIx].replace('\\xo ','').replace('\\xt ','') # Fix things like "Gen 25:9-10; \xo b \xt Gen 35:29."
        xrefCaller = f'<span class="xrCaller" title="See also {xrefMiddle}">[<a href="#xr{crossReferencesCount}">ref</a>]</span>' # was †
        xrefRef = ''
        if xoText:
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
            xrefRef = f'<span class="xrRef"><a href="{xrCV}">{xoText}</a></span> '
        xrefText = f'<p class="xr" id="xr{crossReferencesCount}">{xrefRef}<span class="xrText">{xrefMiddle}</span></p>\n'
        crossReferencesHtml = f'{crossReferencesHtml}{xrefText}'
        html = f'{html[:xStartIx]}{xrefCaller}{html[xEndIx+3:]}'
        searchStartIx = xEndIx + 3
    else: outer_xr_loop_needed_to_break
    if crossReferencesHtml:
        checkHtml( f"{versionAbbreviation} {segmentType} {basicOnly=} {BBB} xref {xrefMiddle=}", crossReferencesHtml, segmentOnly=True )
        html = f'{html}<hr><div class="crossRefs">\n{crossReferencesHtml}</div><!--crossRefs-->\n'
    if versionAbbreviation not in ('BRN',): # BRN ISA 52
        assert '\\x' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}"

    checkHtml( f'convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True )
    return html
# end of usfm.convertUSFMMarkerListToHtml


def formatUSFMText( versionAbbreviation:str, refTuple:tuple, segmentType:str, usfmField, basicOnly=False ) -> str:
    """
    Handles character formatting inside USFM lines.

    This includes \\fig
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers + ['fig']:
        openCount, closeCount = usfmField.count( f'\\{charMarker} ' ), usfmField.count( f'\\{charMarker}*' )
        if openCount != closeCount:
            logging.critical( f"Mismatched USFM character markers: '{charMarker}' open={openCount} close={closeCount} from {versionAbbreviation} {refTuple} '{usfmField}'" )

    html = usfmField.replace( '\\+', '\\') # We don't want the embedded USFM marker style here

    if '\\fig' in usfmField:
        searchStartIx = 0
        for _safetyCount in range( 99 ):
            figStartIx = html.find( '\\fig ', searchStartIx )
            if figStartIx == -1: break # no more to find -- all done
            pipeIx = html.find( '|', figStartIx+5 )
            assert pipeIx != -1
            figEndIx = html.find( '\\fig*', pipeIx+1 )
            assert figEndIx != -1
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Handling fig {versionAbbreviation} {refTuple} {segmentType} {searchStartIx} {figStartIx} {pipeIx} {figEndIx} '{html[figStartIx:figEndIx+5]}'" )
            figGuts = html[figStartIx+5:figEndIx]
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got fig {versionAbbreviation} {refTuple} {segmentType} '{figGuts}' from '{html[figStartIx:figEndIx+5]}'" )
            word = '(Figure skipped)'
            html = f'{html[:figStartIx]}{word}{html[figEndIx+5:]}'
            searchStartIx += len(word) # coz we've made the html much shorter
        else: fig_loop_needed_to_break

    # Handle \\w markers (mostly only occur if basicOnly is false)
    if '\\w ' in usfmField:
        # if versionAbbreviation in ('NET',): # \\w fields in NET seem to now only contain the English word
            # assert '|' not in usfmField, f"Found pipe {versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
        if '|' not in usfmField:
            usfmField = usfmField.replace( '\\w ', '' ).replace( '\\w*', '' )
        else: # Fields like \\w of|x-occurrence="1" x-occurrences="3"\\w* for ULT/UST, WEB has strongs
            # NET from eBible.org seems to have a mix,
            #   e.g., "\\w So|strong="H6213"\\w* \\w the king\\w* \\w stayed\\w*"
            searchStartIx = 0
            for _safetyCount in range( 199 ):
                wStartIx = html.find( '\\w ', searchStartIx )
                if wStartIx == -1: break # no more to find -- all done
                pipeIx = html.find( '|', wStartIx+3 ) # Might be -1 if there's no more, or might be more than wEndIx if there's none in this word
                wEndIx = html.find( '\\w*', wStartIx+3 )
                assert wEndIx != -1
                if pipeIx > wEndIx: # then it must be in the next word!
                    pipeIx = -1 # so just act as if there wasn't one :)
                if pipeIx != -1:
                    assert wStartIx+3 < pipeIx < wEndIx, f"{searchStartIx=} {wStartIx=} {pipeIx=} {wEndIx=}"
                word = html[wStartIx+3:wEndIx] if pipeIx==-1 else html[wStartIx+3:pipeIx]
                html = f'{html[:wStartIx]}{word}{html[wEndIx+3:]}'
                searchStartIx += len(word) # coz we've made the html much shorter
            else: w_loop_needed_to_break
            assert '\\w ' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}" # Note: can still be \\wj in text

    # First replace the character markers which have specific HMTL equivalents
    html = html \
            .replace( '\\bdit ', '<b><i>' ).replace( '\\bdit*', '</i></b>' ) \
            .replace( '\\bd ', '<b>' ).replace( '\\bd*', '</b>' ) \
            .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
            .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
            .replace( '\\sup ', '<sup>' ).replace( '\\sup*', '</sup>' )
    # Now replace all the other character markers into HTML spans
    for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers:
        html = html.replace( f'\\{charMarker} ', f'<span class="{charMarker}">' ).replace( f'\\{charMarker}*', '</span>' )

    # Final checking
    if '\\ts\\*' in html:
        logging.critical( f"Removing ts marker in {versionAbbreviation} {refTuple} {segmentType} {basicOnly=}…")
        html = html.replace( '\\ts\\*', '' )
    if '\\f ' not in html and '\\x ' not in html:
        assert '\\' not in html, f"{versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
    checkHtml( f'formatUSFMText({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True )
    return html
# end of usfm.formatUSFMText


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
