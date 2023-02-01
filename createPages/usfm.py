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


LAST_MODIFIED_DATE = '2023-02-01' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '0.10'
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
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {len(markerList)} )" )

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
        marker = entry.getMarker()
        rest = entry.getText() if basicOnly else entry.getFullText()
        if rest:
            if 'OET' in versionAbbreviation:
                rest = rest.replace( "'", "’" ) # Replace apostrophes
            elif versionAbbreviation in ('ULT','UST'):
                rest = rest.replace( '{', '\\add ' ).replace( '}', '\\add*' ) # Replace braces
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{n} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )
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
        elif marker in ('s1','s2','s3','s4', 'is1','is2','is3'):
            assert not inRightDiv
            if marker == 's1':
                if inSection == 's1': # Shouldn't happen
                    logger = logging.warning if segmentType=='verse' else logging.error
                    logger( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                    if not basicOnly:
                        html = f'{html}</div><!--{marker}-->\n'
                    inSection = None
                elif inSection: # seems we had a s2/3/4 that wasn't closed
                    should_not_be_in_section
                assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
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
            assert inSection == marker[1:] and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=}"
            if not basicOnly:
                html = f'{html}</div><!--{marker[1:]}-->\n'
            inSection = None
        elif marker in ('mt1','mt2','mt3','mt4', 'ms1','ms2','ms3','ms4'):
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
                html = f'{html}<p class="{marker}">{formatUSFMText(versionAbbreviation, refTuple, segmentType, rest, basicOnly)}</p>\n'
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
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, versionAbbreviation , refTuple)
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
                logging.warning( f"{versionAbbreviation} {refTuple} Finished chapter inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            elif inSection and marker == '¬chapters':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished book inside section" )
                if not basicOnly:
                    html = f'{html}</div><!--s1-->\n'
                inSection = None
            elif inParagraph and marker == '¬c':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished paragraph inside section" )
                if not basicOnly:
                    html = f'{html}</p>\n'
                inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
        elif marker in ('ip', 'io1','io2','io3','io4'):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<p class="{marker}">{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}</p>\n'
        elif marker in ('iot',):
            assert rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText( versionAbbreviation, refTuple, segmentType, rest, basicOnly )}</p>\n'
        elif marker in ('¬iot',):
            assert not rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}</div><!--{marker[1:]}-->\n'
        elif marker in ('¬intro', 'chapters'):
            assert refTuple[1] == -1, refTuple
            print( f"Aborting loop after intro for {versionAbbreviation} {refTuple} {C}:{V}" )
            break # For the intro, we don't want the entire book
        elif marker not in ('id','usfm','ide',
                            'headers','h', 'toc1','toc2','toc3', '¬headers',
                            'intro', 'ie', '¬intro',
                            'chapters', 'v=', 'c#', '¬c', '¬chapters'): # We can ignore all of these
            logging.critical( f"Unexpected '{marker}' marker at {versionAbbreviation} {refTuple} {C}:{V}" )
            halt
        # if versionAbbreviation == 'SR-GNT': dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{html=}" )
        if '\\f ' not in html and '\\x ' not in html:
            if '\\' in html:
                logging.error( f"Left-over backslash in {versionAbbreviation} {refTuple} {C}:{V} '{html}'" )
                leftover_backslash
    if not basicOnly or refTuple not in (('JHN',7),):
        assert (not inSection or inSection=='s1') and not inParagraph and not inListEntry, f"convertUSFMMarkerListToHtml final {refTuple} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
    if inList: logging.warning( f"convertUSFMMarkerListToHtml finished with {inList} list for {refTuple}" )

    # Handle all footnotes in one go (we don't check for matching \fr fields)
    footnotesCount = 0
    footnotesHtml = ''
    searchStartIx = 0
    while True:
        fStartIx = html.find( '\\f ', searchStartIx )
        if fStartIx == -1: break # all done
        footnotesCount += 1
        frIx = html.find( '\\fr ', fStartIx+3 ) # Might be absent
        ftIx = html.find( '\\ft ', fStartIx+3 )
        assert ftIx != -1
        assert fStartIx+5 <= ftIx <= fStartIx+16, f"{fStartIx=} {ftIx=} '{html[fStartIx:fStartIx+20]}'" # Skips ' + \\fr c:v '
        if frIx == -1:
            frText = ''
        else: # we have one
            assert fStartIx+5 <= frIx <= fStartIx+6, f"{fStartIx=} {frIx=} '{html[fStartIx:fStartIx+20]}'" # Skips ' + '
            frText = html[frIx+3:ftIx].strip()
        fEndIx = html.find( '\\f*', ftIx+3 )
        assert fEndIx != -1
        fnoteMiddle = html[ftIx+4:fEndIx]
        internalOpenCount = fnoteMiddle.count( '\\ft ') + fnoteMiddle.count( '\\fqa ')
        if internalOpenCount > 0:
            internalCloseCount = fnoteMiddle.count( '\\ft*') + fnoteMiddle.count( '\\fqa*')
            internalMarkerCount = internalOpenCount - internalCloseCount
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Footnote middle has {internalOpenCount=} {internalCloseCount=} {internalMarkerCount=} '{fnoteMiddle}'" )
            inSpan = None
            internalSearchStartIx = 0
            while True:
                internalStartIx = fnoteMiddle.find( '\\', internalSearchStartIx )
                if internalStartIx == -1: break # all done
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found backslash at {internalStartIx} in '{fnoteMiddle}'" )
                fMarker = ''
                while internalStartIx + len(fMarker) < len(fnoteMiddle):
                    if fnoteMiddle[internalStartIx+len(fMarker)+1].islower():
                        fMarker += fnoteMiddle[internalStartIx+len(fMarker)+1]
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Forming {fMarker=}" )
                    else: break
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got {fMarker=}" )
                if fnoteMiddle[internalStartIx+len(fMarker)+1] == ' ': # It's an opening marker
                    span = f'<span class="{fMarker}">'
                    if inSpan:
                        span = f'</span>{span}'
                        inSpan = None
                    inSpan = marker
                    fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{fnoteMiddle[internalStartIx+len(fMarker)+2:]}'
                elif fnoteMiddle[internalStartIx+len(fMarker)+1] == '*': # It's a closing marker
                    assert inSpan
                    fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{fnoteMiddle[internalStartIx+len(fMarker)+2:]}</span>'
                    inSpan = None
                else: unexpected_char in footnote
                internalSearchStartIx += len(fMarker) + 2
            if inSpan: # at end
                fnoteMiddle = f'{fnoteMiddle}</span>'
            assert '\\' not in fnoteMiddle, f"{fnoteMiddle[fnoteMiddle.index(f'{BACKSLASH}x')-10:fnoteMiddle.index(f'{BACKSLASH}x')+12]}"
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{BBB} {fnote}" )
        fnoteCaller = f'<span class="fnCaller" title="Note: {fnoteMiddle}">[<a href="#fn{footnotesCount}">fn</a>]</span>'
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
    if footnotesHtml:
        html = f'{html}<hr><div class="footnotes">\n{footnotesHtml}</div><!--footnotes-->\n'
    assert '\\f' not in html, f"{html[html.index(f'{BACKSLASH}f')-10:html.index(f'{BACKSLASH}f')+12]}"

    # Now handle all cross-references in one go (we don't check for matching \xo fields)
    crossReferencesCount = 0
    crossReferencesHtml = ''
    searchStartIx = 0
    while True:
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
    if crossReferencesHtml:
        html = f'{html}<hr><div class="crossRefs">\n{crossReferencesHtml}</div><!--crossRefs-->\n'
    assert '\\x' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}"

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
    openCount, closeCount = usfmField.count('\\bk '), usfmField.count('\\bk*')
    assert openCount == closeCount, f"'bk' open={openCount} close={closeCount} from '{usfmField}'"
    openCount, closeCount = usfmField.count('\\ior '), usfmField.count('\\ior*')
    assert openCount == closeCount, f"'ior' open={openCount} close={closeCount} from '{usfmField}'"

    html = usfmField.replace( '\\+', '\\') # We don't want the embedded USFM marker style here

    # Handle \\w markers (mostly only occur if basicOnly is false)
    if basicOnly and versionAbbreviation in ('NET',): # \\w fields in NET seem to only now contain the English word
        usfmField = usfmField.replace( '\\w ', '' ).replace( '\\w*', '' )
    else: # Fields like \\w of|x-occurrence="1" x-occurrences="3"\\w* for ULT/UST, WEB has strongs
        searchStartIx = 0
        while True:
            wStartIx = html.find( '\\w ', searchStartIx )
            if wStartIx == -1: break # no more to find -- all done
            pipeIx = html.find( '|', wStartIx+3 )
            assert pipeIx != -1
            wEndIx = html.find( '\\w*', pipeIx+1 )
            assert wEndIx != -1
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {refTuple} {segmentType} {searchStartIx} {wStartIx} {pipeIx} {wEndIx} '{html[wStartIx:wEndIx+3]}'" )
            word = html[wStartIx+3:pipeIx]
            # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {refTuple} {segmentType} '{word}' from '{html[wStartIx:wEndIx+3]}'" )
            html = f'{html[:wStartIx]}{word}{html[wEndIx+3:]}'
            searchStartIx += len(word) # coz we've made the html much shorter
        assert '\\w ' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}" # Note: can still be \\wj in text

    html = html \
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
            .replace( '\\add ', '<span class="add">' ).replace( '\\add*', '</span>' ) \
            .replace( '\\ior ', '<span class="ior">' ).replace( '\\ior*', '</span>' )
    # if refTuple not in (('HEB',9,12),):
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
