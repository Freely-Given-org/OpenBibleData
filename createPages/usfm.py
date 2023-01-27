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
# from typing import Dict, List, Tuple
from pathlib import Path
# import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from html import checkHtml


LAST_MODIFIED_DATE = '2023-01-27' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '0.07'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def convertUSFMMarkerListToHtml( versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, markerList:list, basicOnly:bool=False ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {markerList} )" )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {len(markerList)} )" )

    inParagraph = inSection = inList = inListEntry = inTable = None
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
    BBB, C = refTuple[0], refTuple[1]
    if len(refTuple)==3: V = refTuple[2]

    for n, entry in enumerate(markerList):
        marker, rest = entry.getMarker(), entry.getText()
        if rest and 'OET' in versionAbbreviation:
            rest = rest.replace( "'", "’" ) # Replace apostrophes
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{n} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # print( f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )
        if marker == 'c':
            # if segmentType == 'chapters':
            C = rest
            # html = f'{html}<span class="{marker}" id="C{C}">{C}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker == 'v': # This is where we want the verse marker
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            V = rest
            # We don't display the verse number below for verse 1 (after chapter number)
            if '-' in V: # it's a verse range
                assert V[0].isdigit() and V[-1].isdigit(), f"Expected a verse number digit with {BBB} {C}:{V=} {rest=}"
                assert ':' not in V # We don't handle chapter ranges here yet (and probably don't need to)
                V1, V2 = V.split( '-' )
                # We want both verse numbers to be searchable
                if int(V2) != int(V1)+1: # We don't handle 3+ verse reordering well yet
                    logging.critical( f" Not handling 3+ verse bridge well yet at {versionAbbreviation} {refTuple} {C}:{V}" )
                html = f'{html}{"" if html.endswith(">") else " "}' \
                        + f'{f"""<span id="C{C}"></span><span class="c" id="C{C}V1">{C}</span>""" if V1=="1" else f"""<span class="v" id="C{C}V{V1}">{V1}-</span>"""}' \
                        + f'<span class="v" id="C{C}V{V2}">{V2}{NARROW_NON_BREAK_SPACE}</span>' \
                        + (rest if rest else '≈')
            else: # it's a simple verse number
                if segmentType != 'verse': # No need for verse numbers at all if we're only displaying one verse
                    assert V.isdigit(), f"Expected a verse number digit with {V=} {rest=}"
                    html = f'{html}{"" if html.endswith(">") or html.endswith("—") else " "}' \
                            + f'{f"""<span id="C{C}"></span><span class="c" id="C{C}V1">{C}{NARROW_NON_BREAK_SPACE}</span>""" if V=="1" else f"""<span class="v" id="C{C}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>"""}'
                # html = f'{html} <span class="v" id="C{refTuple[1]}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('s1','s2','s3','s4'):
            assert not inRightDiv
            if marker == 's1':
                if inSection == 's1': # Shouldn't happen
                    logger = logging.warning if segmentType=='verse' else logging.critical
                    logger( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                    if not basicOnly:
                        html = f'{html}</div><!--{marker}-->\n'
                    inSection = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            else: logging.critical( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
            if not basicOnly:
                if 'OET' in versionAbbreviation:
                    html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
                    inRightDiv = True
                else:
                    html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
            inSection = marker
        elif marker in ('¬s1','¬s2','¬s3','¬s4',):
            assert not rest
            assert inSection == marker[1:] and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=}"
            if not basicOnly:
                html = f'{html}</div><!--{marker[1:]}-->\n'
            inSection = None
        elif marker in ('ms1','ms2','ms3','ms4'):
            if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
                html = f'{html}</q1></div>\n'
                inSection = inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
        elif marker == 'r':
            assert inSection, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            assert not inTable
            assert rest[0]=='(' and rest[-1]==')'
            if not basicOnly:
                assert inRightDiv
                html = f'{html}<p class="{marker}">{rest}</p>\n'
        elif marker in ('mr','sr', 'd', 'sp', 'rem'):
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if marker!='rem': assert not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{rest}</p>\n'
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi', 'nb', 'pi1','pi2'):
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if refTuple not in (('MRK',9),('JHN',8),):
                assert not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if inParagraph:
                if not basicOnly:
                    html = f'{html}</p>\n'
                inParagraph = None
            assert not rest, f"{marker}={rest}"
            if marker=='m' and inList=='ul': # refTuple==('EXO',10,11)
                html = f'{html}</ul>\n'
                inList = None
                print( versionAbbreviation , refTuple)
            if not basicOnly:
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi', '¬nb', '¬pi1','¬pi2'):
            assert not rest
            if not basicOnly and refTuple not in (('MRK',9),('JHN',8),):
                assert inParagraph == marker[1:], f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker=}"
            if not basicOnly:
                html = f'{html}</p>\n'
                inParagraph = None
        elif marker in ('p~','v~'): # This has the actual verse text
            html += formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )
        elif marker == 'b':
            html = f'{html}<br>\n'
        elif marker == 'list':
            assert not rest
            assert not inList, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}<ul>\n'
            inList = 'ul'
        elif marker == '¬list':
            if refTuple[0] not in ('EXO','NUM'): # TODO: Temp for OET-RV
                assert inList and not inListEntry, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
                html = f'{html}</{inList}>{rest}'
            inList = None
        elif marker in ('li1','li2','li3','li4'):
            assert inList and not inListEntry, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}<li>{rest}'
            inListEntry = marker
        elif marker in ('¬li1','¬li2','¬li3','¬li4'):
            assert not rest
            assert inList and inListEntry == marker[1:], f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}</li>\n'
            inListEntry = None
        elif marker in ('¬v', ): # We can ignore these end markers
            assert not rest
        elif segmentType=='chapter' and marker in ('¬c','¬chapters'): # We can ignore this
            if inSection and marker == '¬c':
                logging.critical( f"{versionAbbreviation} {refTuple} Finished chapter inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            elif inSection and marker == '¬chapters':
                logging.critical( f"{versionAbbreviation} {refTuple} Finished book inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            elif inParagraph and marker == '¬c':
                logging.critical( f"{versionAbbreviation} {refTuple} Finished paragraph inside section" )
                if not basicOnly:
                    html = f'{html}</p>\n'
                inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
        elif marker not in ('v=', 'c#', '¬c', '¬chapters'): # We can ignore all of these
            unexpected_marker
        # if versionAbbreviation == 'SR-GNT': print( f"{html=}" )
        if '\\' in html:
            logging.critical( f"Left-over backslash in {versionAbbreviation} {refTuple} {C}:{V} '{html}'" )
            if refTuple not in (('HEB',9,12),): leftover_backslash
    if not basicOnly or refTuple not in (('JHN',7),):
        assert (not inSection or inSection=='s1') and not inParagraph and not inListEntry, f"convertUSFMMarkerListToHtml final {refTuple} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
    if inList: logging.critical( f"convertUSFMMarkerListToHtml finished with {inList} list for {refTuple}" )
    checkHtml( f'convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True )
    return html
# end of usfm.convertUSFMMarkerListToHtml

def formatUSFMText( versionAbbreviation:str, refTuple:tuple, segmentType:str, usfmField, basicOnly=False ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"formatUSFMText( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    openCount, closeCount = usfmField.count('\\add '), usfmField.count('\\add*')
    if versionAbbreviation != 'UST':
    # or refTuple not in (('MRK',13,13), ('ROM',8,27),('ROM',9,1),('ROM',11,19),('ROM',11,31)):
        assert openCount == closeCount, f"'add' open={openCount} close={closeCount} from '{usfmField}'"
    openCount, closeCount = usfmField.count('\\em '), usfmField.count('\\em*')
    assert openCount == closeCount, f"'em' open={openCount} close={closeCount} from '{usfmField}'"
    openCount, closeCount = usfmField.count('\\it '), usfmField.count('\\it*')
    assert openCount == closeCount, f"'it' open={openCount} close={closeCount} from '{usfmField}'"
    openCount, closeCount = usfmField.count('\\bd '), usfmField.count('\\bd*')
    assert openCount == closeCount, f"'bd' open={openCount} close={closeCount} from '{usfmField}'"
    openCount, closeCount = usfmField.count('\\bdit '), usfmField.count('\\bdit*')
    assert openCount == closeCount, f"'bdit' open={openCount} close={closeCount} from '{usfmField}'"
    if versionAbbreviation in ('NET',): # \\w fields seem to only now contain the English word
        usfmField = usfmField.replace( '\\w ', '' ).replace( '\\w*', '' )
    html = usfmField.replace( '\\+', '\\') \
            .replace( '\\bdit ', '<b><i>' ).replace( '\\bdit*', '</i></b>' ) \
            .replace( '\\bd ', '<b>' ).replace( '\\bd*', '</b>' ) \
            .replace( '\\it ', '<it>' ).replace( '\\it*', '</it>' ) \
            .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
            .replace( '\\ca ', '<span class="ca">' ).replace( '\\ca*', '</span>' ) \
            .replace( '\\va ', '<span class="va">' ).replace( '\\va*', '</span>' ) \
            .replace( '\\sup ', '<span class="sup">' ).replace( '\\sup*', '</span>' ) \
            .replace( '\\sc ', '<span class="sc">' ).replace( '\\sc*', '</span>' ) \
            .replace( '\\no ', '<span class="no">' ).replace( '\\no*', '</span>' ) \
            .replace( '\\png ', '<span class="png">' ).replace( '\\png*', '</span>' ) \
            .replace( '\\tl ', '<span class="tl">' ).replace( '\\tl*', '</span>' ) \
            .replace( '\\sls ', '<span class="sls">' ).replace( '\\sls*', '</span>' ) \
            .replace( '\\sig ', '<span class="sig">' ).replace( '\\sig*', '</span>' ) \
            .replace( '\\qt ', '<span class="qt">' ).replace( '\\qt*', '</span>' ) \
            .replace( '\\bk ', '<span class="bk">' ).replace( '\\bk*', '</span>' ) \
            .replace( '\\wj ', '<span class="wj">' ).replace( '\\wj*', '</span>' ) \
            .replace( '\\nd ', '<span class="nd">' ).replace( '\\nd*', '</span>' ) \
            .replace( '\\add ', '<span class="added">' ).replace( '\\add*', '</span>' )
    if refTuple not in (('HEB',9,12),):
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
