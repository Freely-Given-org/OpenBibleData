#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# usfm.py
#
# Module handling OpenBibleData USFM to HTML functions
#
# Copyright (C) 2023-2025 Robert Hunt
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
Module handling usfm to html functions for OpenBibleData package.

convertUSFMMarkerListToHtml( level:str, versionAbbreviation:str, refTuple:tuple, segmentType:str,
                        contextList:list, markerList:list, basicOnly:bool=False ) -> str
convertUSFMCharacterFormatting( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                    usfmField, basicOnly=False, state:State ) -> str
livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                        introHtml:str, state:State ) -> str
livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str,
                                                                        state:State ) -> str
livenXRefField( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                    pathPrefix:str, xoText:str, xrefOriginalMiddle:str, state:State ) -> str
toRomanNumerals( num:int|str ) -> str

briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2023-07-19 Added #Vv navigation links to chapter pages (already had #CcVv)
    2023-07-20 Added #Vv navigation links to section pages (already had #CcVv)
    2023-08-07 Handle extra optional section headings
    2023-08-10 Handle multi-level lists properly
    2023-08-14 Added #Vv navigation links to single chapter books (already had #CcVv)
    2023-08-16 Render id field like a rem
    2023-08-18 Handle additional section headings separated by semicolons
    2023-08-23 Disable display of additional section headings in header boxes and in text
    2023-08-25 Fix missing spaces before verse numbers in OET-RV
    2023-09-23 Link to missing verses page
    2023-10-13 Give error if unable to find xref book
    2023-12-24 Add code to liven section references ( livenSectionReferences() )
                Change to use findSectionNumber() function
    2024-01-17 Add special handling for OT '\\nd LORD\\nd*' and convert \\nd to nominaSacra span in NT
    2024-06-05 Include footnotes now (but not cross-references) in 'basic' mode
    2024-06-06 Fixed bug with closed fields inside footnotes
    2024-06-25 Put NNBSP between sucessive (close) quote marks
    2024-07-11 Put verse text chunks into a style
    2024-07-13 Changed KJB-1611 chapter numbers to Roman numerals
    2024-07-18 Limited the length of footnote title popups
    2025-02-03 Include cross-references for OET-RV parallel verses only (no other versions)
    2025-02-24 Avoid putting <ul> around list in parallelVerse mode
    2025-02-26 Handle /cl else put chapter numbers before /d (in PSA) and /iex (in KJB-1611)
    2025-03-04 Ignore nb markers in OET-LV
    2025-03-11 Liven OSHB footnotes in OET-LV
    2025-04-07 Improve handling of s2 headings
    2025-05-26 Liven KJB-1611 cross-references
    2025-05-30 Tried to improve tables (esp. for T4T Ezra)
    2025-05-31 Add handling of northern/southern kingdom colouring
    2025-06-24 Move livening xrefs into a function, and apply it to xt fields inside footnotes as well.
    2025-07-11 Try to improve handling of 'ver. 4' in a footnote (not an xref)
    2025-09-12 Display verse range numbers on parallel pages
"""
from gettext import gettext as _
import re
import unicodedata
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, dPrint, vPrint, rreplace
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_NT27

from settings import State
from html import checkHtml
from OETHandlers import getBBBFromOETBookName


LAST_MODIFIED_DATE = '2025-09-22' # by RJH
SHORT_PROGRAM_NAME = "usfm"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '0.94'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BACKSLASH = '\\'
NEWLINE = '\n'
# EM_SPACE = ' '
THIN_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
NON_BREAK_SPACE = ' ' # NBSP

MAX_FOOTNOTE_CHARS = 11_500 # 1,029 in FBV, 1,688 in BrTr, 10,426 in ClVg JOB!
MAX_NET_FOOTNOTE_CHARS = 18_000 # 17,145 in NET ECC

spClassDict = {'The groom':'groom', 'The bride':'bride', 'Yerushalem’s young women':'women','Bride’s older brothers':'brothers'}

XRefRegEx = re.compile( '\\\\x .+?\\\\x\\*' )
spanClassRegEx = re.compile( '<span class=".+?">' )
def convertUSFMMarkerListToHtml( level:int, versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, markerList:list, basicOnly:bool, state:State ) -> str:
    """
    Loops through the given list of USFM lines
        and converts to a HTML segment as required.

    basicOnly ignores things like section headings (s1),
                        cross-references (x, apart from in OET-RV parallel verses), etc.
                    (but includes footnotes).

    TODO: Should this have had 'includeFootnotes' and 'includeXrefs' as separate parameters???
    """
    from createSectionPages import findSectionNumber # Doesn't cause a circular reference import problem
    from createSectionPages import livenSectionReferences # Doesn't cause a circular reference import problem
    # if segmentType=='relatedPassage' and refTuple[0]=='JHN' and refTuple[1]=='1':
    #     print( f"\n{refTuple}\n{contextList=}\n{markerList=}")

    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {markerList} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList=} {len(markerList)=} )" )
    assert segmentType in ('book','section','chapter','parallelVerse','interlinearVerse','relatedPassage','topicalPassage'), f"Unexpected {segmentType=}"
    BBB = refTuple[0] # Compulsory
    maxFootnoteChars = MAX_NET_FOOTNOTE_CHARS if versionAbbreviation=='NET' else MAX_FOOTNOTE_CHARS

    # if 'KJB' in versionAbbreviation and BBB=='PSA' and len(refTuple)>1 and refTuple[1] in ('98','99','100'):
    #     print( f"\nconvertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList=} {[(entry.getMarker(),entry.getFullText()) for entry in markerList]} )\n" )
        # if refTuple[2] == '2': halt
    # if versionAbbreviation=='NET' and refTuple==('JOB','36','4'): print( f"\nconvertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList=} {[entry.getFullText() for entry in markerList]} )\n" )
    # if versionAbbreviation=='OET-RV' and refTuple==('CH2','23'): print( f"\nconvertUSFMMarkerListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList=} {[(entry.getMarker(),entry.getFullText()) for entry in markerList]} )\n" )
    # # Check that we don't have any duplicated verses in the segment
    # lastV = None
    # for entry in markerList:
    #     marker, text = entry.getMarker(), entry.getFullText()
    #     print( f"convertUSFMMarkerListToHtml {versionAbbreviation} {refTuple} {segmentType} {marker}={text}" )
    #     if marker == 'v':
    #         assert text != lastV
    #         lastV = text

    inMainDiv = inParagraph = inSection = inList = inListEntry = inTable = inTableRow = inSPdiv = None
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
        elif segmentType.endswith('Verse'):
            if marker not in ('chapters', 'c'):
                Exception( f"Unexpected context for '{segmentType}': {contextList}" )
        elif marker not in ('chapters', 'c'):
            if refTuple[0] not in ('EXO','NUM') or marker!='list': Exception( f"Unexpected context for '{segmentType}': {contextList}" )

    C = V = None
    if len(refTuple) > 1:
        C = refTuple[1]
        assert isinstance(C, str), f"{refTuple=}"
    if len(refTuple) > 2:
        V = refTuple[2]
        assert isinstance(V, str), f"{refTuple=}"
    isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( BBB )

    # numChapters = 0
    cPrinted = True
    for MLIndex, entry in enumerate( markerList ):
        marker = entry.getMarker()
        # rest = entry.getText() if basicOnly and 'OET' not in versionAbbreviation else entry.getFullText() # getText() has notes removed but doesn't work with wordlink numbers in OET
        # The following line means we get all footnotes, etc.
        rest = entry.getFullText() # getText() has notes removed but doesn't work with wordlink numbers in OET
        if rest: # Special handling for some versions
            assert '\\nd \\nd ' not in rest, f"Unexpected doubled nd’s in verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {marker=} {rest=}"
            assert '\\nd*\\nd*' not in rest, f"Unexpected closing nd’s in verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {marker=} {rest=}"
            if 'OET' in versionAbbreviation:
                rest = rest.replace( "'", "’" ) # Replace apostrophes
            elif versionAbbreviation in ('ULT','UST'):
                rest = rest.replace( '{', '\\add ' ).replace( '}', '\\add*' ) # Replace UST braces
            elif versionAbbreviation in ('Cvdl',):
                assert '\\nd LORDE\\nd*' not in rest
                rest = rest.replace( 'LORDE', '\\nd LORDE\\nd*' )
            elif versionAbbreviation == 'Luth':
                assert '\\nd HErr\\nd*' not in rest
                rest = rest.replace( 'HErrn', 'HErr’s' ).replace( 'HErr', '\\nd HErr\\nd*' )
            else:
                rest = rest.replace( '\\nd  ', '\\nd ' ) # Fix an eBible.org USFM error
            rest = rest.replace( '’”', '’ ”' ).replace( '’ ”', '’ ”' ).replace( '”’', '” ’' ).replace( '” ’', '” ’' ) # Insert NNBSP

            if basicOnly \
            and (versionAbbreviation!='OET-RV' or segmentType!='parallelVerse') \
            and '\\x ' in rest:
                # Completely remove cross-references
                rest, xCount = XRefRegEx.subn( '', rest )
                # print( f"Removed {xCount} cross-references from {refTuple} {rest=} now {xrest=}")
                # if xCount > 1: halt
                # rest = xrest
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{n}/{len(markerList)} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {inList=} {inListEntry=}" )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )

        # We try to put these in order of probability
        if marker in ('p~','v~'): # This has the actual verse text
            if not rest:
                logging.error( f"Expected verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            html = f'''{html}<span class="{versionAbbreviation}_{'chapterIntro' if V=='0' else 'verseTextChunk'}">{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>'''
        elif marker == 'v': # This is where we want the verse marker
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            V = rest.strip() # Play safe
            # We don't display the verse number below for verse 1 (after chapter number)
            # NOTE: For sections (which can include multiple chapters), have to take care not to get duplicate V{v} id attributes
            if segmentType not in ('parallelVerse','interlinearVerse') \
            or '-' in rest: # No need for verse numbers at all if we're only displaying one verse
                if cPrinted or segmentType in ('parallelVerse','interlinearVerse'):
                    cID = ''
                else:
                    cID = f'<span id="C{C}"></span>'
                    cPrinted = True
                if '-' in V: # it's a verse range
                    assert V[0].isdigit() and V[-1].isdigit(), f"Expected a verse number digit with {BBB} {C}:{V=} {rest=}"
                    assert ':' not in V # We don't handle chapter ranges here yet (and probably don't need to)
                    V1, V2 = V.split( '-' )
                    # We want both verse numbers to be searchable
                    if int(V2) != int(V1)+1: # We don't handle 3+ verse reordering well yet
                        logging.warning( f" Not handling 3+ verse bridge well yet at {versionAbbreviation} {refTuple} {C}:{V}" )
                    if segmentType in ('parallelVerse','interlinearVerse'): # We just want the reader to be able to see the verse range
                        html = f'''{html}{"" if html.endswith(">") else " "}<span class="v">{rest}</span>{THIN_SPACE}'''
                    else: # it's in a section or book type view
                        vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V{V1}.htm#Top">{V1}</a>'''
                        html = f'{html}{"" if html.endswith(">") else " "}' \
                                + f'''{f"""{cID}<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}V1">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</span>""" if V1=='1' else f"""<span class="v" id="C{C}V{V1}">{vLink}-</span>"""}''' \
                                + (f'<span id="V{V1}"></span><span id="V{V2}"></span>' if (segmentType in ('chapter','section','relatedPassage') or isSingleChapterBook) and f'id="V{V1}"' not in html and f'id="V{V2}"' not in html else '') \
                                + f'<span class="v" id="C{C}V{V2}">{V2}{NARROW_NON_BREAK_SPACE}</span>' \
                                + (rest if rest else '=◘=')
                else: # it's a simple verse number
                    if not V.isdigit():
                        logging.error( f"Expected a verse number digit at {versionAbbreviation} {refTuple} {C}:{V} {rest=}" )
                    cLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V1.htm#Top">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</a>'''
                    vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">{V}</a>'''
                    html = f'''{html}{'' if html.endswith('"p">') or html.endswith('—') or html.endswith('—</span>') else ' '}''' \
                            + (f'<span id="V{V}"></span>' if (segmentType in ('chapter','section','relatedPassage') or isSingleChapterBook) and f'id="V{V}"' not in html else '') \
                            + f'''{f"""{cID}<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}V1">{cLink}{NARROW_NON_BREAK_SPACE}</span>""" if V=='1'
                                   else f"""<span class="v" id="C{C}V{V}">{vLink}{NARROW_NON_BREAK_SPACE}</span>"""}'''
                # html = f'{html} <span class="v" id="C{refTuple[1]}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('¬v', ): # We can ignore these end markers
            assert not rest
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi', 'nb',
                            'pi1','pi2', 'pc','pm','pmc','pmo','po','pr', 'qm1','qm2', 'qr', 'cls'):
            assert not rest, f"Unexpected rest {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {marker}={rest}"
            if inMainDiv: # this can happen in INT module
                html = f'{html}</div><!--{inMainDiv}-->'
                inMainDiv = None
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if inParagraph:
                logging.warning( f"Already in paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                html = f'{html}</p>\n'
                inParagraph = None
            if inTableRow:
                assert inTable
                html = f'{html}</tr>\n'
                inTableRow = None
            if inTable:
                html = f'{html}</table>\n'
                inTable = None
            # TODO: Shouldn't this apply to all markers???
            if inList: # refTuple==('EXO',10,11)
                # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, versionAbbreviation , refTuple)
                inListMarker, inListDepth = inList.split( '_', 1 )
                inListDepth = int( inListDepth )
                while inListDepth > 0:
                    if inListDepth>1 and inListEntry:
                        if inListEntry == True:
                            html = f'{html}</li>\n'
                            inListEntry = None
                    html = f'{html}</{inListMarker}>\n'
                    inListDepth -= 1
                inList = None
            if basicOnly:
                # if html: html = f"{html}<br>{NARROW_NON_BREAK_SPACE if '1' in marker else NON_BREAK_SPACE if '2' in marker else ''}{'¶' if 'p' in marker else '⇔' if 'q' in marker else '§'}{NARROW_NON_BREAK_SPACE}" # Just start the new paragraph on a new line with a pilcrow
                if html: html = f"{html}<br>{' ' if '1' in marker else ' ' if '2' in marker else NON_BREAK_SPACE}{'¶' if 'p' in marker else '⇔' if 'q' in marker else '§'}{NARROW_NON_BREAK_SPACE}" # Just start the new paragraph on a new line with a pilcrow
            elif versionAbbreviation != 'OET-LV': # not basicOnly and not OET-LV (we ignore them there)
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi', '¬nb',
                            '¬pi1','¬pi2', '¬pc','¬pm','¬pmc','¬pmo','¬po','¬pr', '¬qm1','¬qm2', '¬qr', '¬cls'):
            assert not rest
            if inParagraph and inParagraph != marker[1:]:
                logging.error( f"Closing wrong paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker=}" )
            if not basicOnly and inParagraph:
                html = f'{html}</p>\n'
                inParagraph = None
        elif marker in ('s1','s2','s3','s4'):
            if not rest:
                logging.error( f"Expected heading text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inSPdiv:
                html = f'{html}</div><!--SP_{inSPdiv}-->\n'
                inSPdiv = None
            if inRightDiv:
                assert marker != 's1'
                if versionAbbreviation not in ('OET','OET-RV') or marker!='s4':
                    # It mustn't be our "kingdom marker", e.g., 'Northern kingdom'
                    html = f'{html}</div><!--rightBox-->\n'
                    inRightDiv = False
            if inTable:
                logging.warning( f"Table should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                html = f'{html}</table>\n'
                inTable = None
            if inList:
                logging.warning( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                inListMarker, inListDepth = inList.split( '_', 1 )
                inListDepth = int( inListDepth )
                while inListDepth > 0:
                    if inListDepth > 1:
                        if inListEntry == True:
                            html = f'{html}</li>\n'
                            inListEntry = None
                    html = f'{html}</{inListMarker}>\n'
                    inListDepth -= 1
                inList = None
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
            else: # not in periph
                if marker == 's1':
                    if segmentType=='relatedPassage' and inParagraph: # Can be disjointed verses
                        html = f'{html}</p>\n'
                        inParagraph = None
                    if inSection == 's1': # Shouldn't happen
                        logger = logging.warning if segmentType.endswith('Verse') else logging.error
                        logger( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                        if not basicOnly:
                            html = f'{html}</div><!--{marker}-->\n'
                        inSection = None
                    elif inSection: # seems we had a s2/3/4 that wasn't closed
                        logging.critical( f"Should not be in section '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=}" )
                        should_not_be_in_section
                    assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest} {contextList=}"
                else: logging.warning( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    rest = rest.replace( ' / ', f'{NON_BREAK_SPACE}/ ' ) # Stop forward slash from starting next line in section boxes
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            # TODO: Check what happens if V is a verse range
                            #   (Might need to add one to the end part, not the start part???)
                            if segmentType in ('section','relatedPassage'):
                                # print( f"\n  {C=} {V=} {marker}='{rest}'")
                                if V is None:
                                    for nextEntry in markerList[MLIndex+1:]: # Skip through next markers
                                        nextMarker = nextEntry.getMarker()
                                        if nextMarker == 'v':
                                            nextV = nextEntry.getCleanText()
                                            break
                                    else: failed_here
                                else: nextV = V
                                # if segmentType=='relatedPassage' and refTuple[0]=='JHN' and refTuple[1]=='1':
                                #     print( f"{nextV=}")
                                #     halt
                            else:
                                nextV = '1' if V is None else getLeadingInt(V)+1 # Why  do we add 1 ???
                            if ( segmentType == 'section' # Don't want a link to ourself
                            or '\\f' in rest ): # Would otherwise end up with an anchor embedded inside an anchor at Jhn 7:53 (unless we write more code)
                                html = f'''{html}<div class="{marker}"><div class="rightBox"><p class="{marker}"><span class="s1cv">{C}:{nextV}</span> {convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'''
                            else:
                                sectionNumber = findSectionNumber( 'OET-RV', BBB, C, str(nextV), state )
                                assert sectionNumber is not None, f"Bad OET-RV {refTuple} /s1 section reference: {rest=}"
                                html = f'''{html}<div class="{marker}"><div class="rightBox"><p class="{marker}"><span class="s1cv">{C}:{nextV}</span> <a title="Go to section view" href="{'../'*level}OET/bySec/{BBB}_S{sectionNumber}.htm#C{C}V{nextV}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</a></p>\n'''
                            inRightDiv = True
                        else: # not OET
                            html = f'{html}<div class="{marker}"><p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                        inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section division
                    if not basicOnly:
                        if marker=='s4' and versionAbbreviation in ('OET','OET-RV'): # and 'KINGDOM' in rest.upper(): # it's our kingdom marker
                            additionalClassName = rest.replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )
                            html = rreplace( html, 'div class="s1"', f'''div class="s1 {additionalClassName}"''', 1 )
                            guts = convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)
                            guts = f'''<a title="Go to {rest.replace('king','King').replace('land','Land')} information page" href="{'../'*level}OET/{additionalClassName}.htm">{guts}</a>'''
                            html = f'''{html}<p class="{marker} {additionalClassName}">{guts}</p>\n'''
                        else: html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('¬s1','¬s2','¬s3','¬s4',):
            assert not rest
            assert inSection == marker[1:] and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=}"
            if not basicOnly:
                # if inRightDiv: # shouldn't really happen, but just in case
                #     html = f'{html}</div><!--rightBox-->\n'
                #     inRightDiv = False
                #     halt # Why were we in a rightDiv
                html = f'{html}</div><!--{marker[1:]}-->\n'
            inSection = None
        elif marker == 'r': # usually following a \\s1 (but maybe a \\s2) -- either way there could be a \\rem in between
            # The following is not true for the ULT at least (e.g., see ULT Gen 5:1)
            # assert rest[0]=='(' and rest[-1]==')', f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            assert not inTable
            assert '\\' not in rest
            if not basicOnly:
                assert inSection, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                if 'OET' in versionAbbreviation:
                    assert inRightDiv, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest} prevEntry={markerList[MLIndex-1]} {html[-50:]}"
                html = f'{html}<p class="{marker}">{livenSectionReferences( versionAbbreviation, refTuple, segmentType, rest, state )}</p>\n'
        elif marker == 'c':
            # if segmentType == 'chapter':
            C, V = rest.strip(), '0' # Play safe
            # html = f'{html}<span class="{marker}" id="C{C}">{C}{NARROW_NON_BREAK_SPACE}</span>'
            # numChapters += 1
            cPrinted = False
        elif marker == 'c#':
            assert rest and rest.isdigit()
            # Below is not necessarily true -- fails on OET-RV chapter basicOnly=False ('PSA', '1') 1:0 inSection='s1' inParagraph='p' c#=1
            # if len(refTuple)>1 and refTuple[1] != '-1':
            #     assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"

            # if state.TEST_MODE and versionAbbreviation != 'SR-GNT':
            #     html = f'{html}<span class="{'cPsa' if BBB=='PSA' else 'c'}">C###{toRomanNumerals(rest) if versionAbbreviation=='KJB-1611' else rest}</span>{NARROW_NON_BREAK_SPACE}'
        elif marker in ('mt1','mt2','mt3','mt4'):
            assert rest
            if versionAbbreviation == 'KJB-1611':
                rest = rest.replace( '   ', ' &nbsp; ' ) # We sometimes have three spaces which html normally loses, so try to prevent it
            if not inMainDiv:
                inMainDiv = 'bookHeader'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection != 'periph':
                if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
                    html = f'{html}</q1></div>\n'
                    inSection = inParagraph = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('imt1','imt2','imt3','imt4'):
            assert rest
            if inMainDiv == 'bookHeader':
                    html = f'{html}</div><!--{inMainDiv}-->'
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
                html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('is1','is2','is3'):
            assert rest
            # if not rest:
            #     logging.critical( f"Expected heading text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            assert not inRightDiv
            if inMainDiv == 'bookHeader':
                    assert not inTable and not inList and not inParagraph
                    html = f'{html}</div><!--{inMainDiv}-->'
                    inMainDiv = None
            if inTable:
                logging.warning( f"Table should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inTable=} {inListEntry=} {marker=}" )
                html = f'{html}</table>\n'
                inTable = None
            if inList:
                logging.warning( f"List should have been closed already {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
                inListMarker, inListDepth = inList.split( '_', 1 )
                inListDepth = int( inListDepth )
                while inListDepth > 0:
                    if inListDepth > 1:
                        if inListEntry == True:
                            html = f'{html}</li>\n'
                            inListEntry = None
                    html = f'{html}</{inListMarker}>\n'
                    inListDepth -= 1
                inList = None
            if inParagraph:
                html = f'{html}</p>\n'
                inParagraph = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
            else: # not in periph
                if marker == 's1':
                    if inSection == 's1': # Shouldn't happen
                        logger = logging.warning if segmentType.endswith('Verse') else logging.error
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
                            html = f'{html}<div class="{marker}"><div class="rightBox"><p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                            inRightDiv = True
                        else:
                            html = f'{html}<div class="{marker}"><p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                    inSection = marker
                else: # for s2/3/4 we add a heading, but don't consider it a section
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        # We also treat the id field exactly like a rem field
        elif marker in ('rem','id'): # rem's can sort of be anywhere!
            assert rest
            rest = rest.replace( "Open English Translation", "<em>Open English Translation</em>" )
            if versionAbbreviation=='OEB': rest = rest.replace( '->', '→' ) # In the book introductions '-&gt;'
            if rest.startswith( '/' ):
                if inRightDiv:
                    assert not inParagraph
                    given_marker = rest[1:].split( ' ', 1 )[0]
                    assert given_marker in ('s1','s2','s3','r','d')
                    # NOTE: the following lines were disabled 23Aug2023
                    # marker = f"extra_{given_marker}" # Sets the html <p> class below
                    # rest = rest[len(given_marker)+2:] # Drop the '/marker ' from the displayed portion
                    # if not basicOnly:
                    #     for sectionChunk in rest.split( '; ' ):
                    #         html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, sectionChunk, basicOnly, state)}</p>\n'
                else: # it's probably a section marker added at a different spot
                    given_marker = rest[1:].split( ' ', 1 )[0]
                    assert given_marker in ('s1','s2','s3','r','d','qa')
                    # NOTE: the following lines were disabled 23Aug2023
                    # marker = f"alt_{given_marker}" # Sets the html <p> class below
                    # rest = rest[len(given_marker)+2:] # Drop the '/marker ' from the displayed portion
                    # # NOTE: inParagraph is not necessarily helpful here, because we might already be at the end of the paragraph
                    # for offset in range( 1, 8 ):
                    #     try: nextMarker = markerList[n+offset].getMarker()
                    #     except IndexError: # at end of the book or chapter or verse -- no next marker
                    #         nextMarker = '¬p' # so it's certain to end any open paragraph
                    #         break
                    #     if nextMarker!='rem' and nextMarker!='¬v': break
                    # if not inParagraph \
                    # or nextMarker in ('p','m','¬p'):
                    #     if inParagraph:
                    #         html = f'{html}</p>\n'
                    #         inParagraph = None
                    #     if not basicOnly:
                    #         for sectionChunk in rest.split( '; ' ):
                    #             html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, sectionChunk, basicOnly, state)}</p>\n'
                    # else:
                    #     print( f"{BBB} {C}:{V} {inParagraph=} {nextMarker=} has UNUSED INFLOW ALTERNATIVE {given_marker}={rest}")
            else:
                assert not inRightDiv
                if inParagraph:
                    html = f'{html}<span class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</span>\n'
                elif not basicOnly:
                    html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        # The following should all have their own data and get converted to a simple <p class="xx">…</p> field
        elif marker in ('mr','sr', 'cl', 'd', 'sp', 'cp', 'qa','qc','qd'):
            if not rest:
                logging.error( f"Source problem for {versionAbbreviation}: Expected field text {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inRightDiv:
                html = f'{html}</div><!--rightBox-->\n'
                inRightDiv = False
            if inParagraph:
                logging.error( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly
                html = f'{html}</p>\n'
                inParagraph = None
            if marker == 'cl' and not basicOnly:
                if segmentType == 'chapter':
                    html = f'{html}<p class="cl" id="C{C}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
                else: # probably whole document/book, so make a chapter link
                    html = f'{html}<p class="cl" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</a></p>\n'
                cPrinted = True
            elif basicOnly:
                if marker == 'd': # These are canonical so MUST be included
                    # NOTE: In basicOnly mode, we put \\d paragraphs in a SPAN, not in a PARAGRAPH (like we do further below)
                    html = f'{html}<span class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</span>\n'
                    if not checkHtml( f'\\d at convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
                        if DEBUGGING_THIS_MODULE or state.TEST_MODE: halt
            else: # not basicOnly
                if cPrinted:
                    cBit = ''
                else:
                    cBit = f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</span> ''' \
                        if segmentType == 'chapter' else \
                            f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</a></span> '''
                    cPrinted = True
                if versionAbbreviation=='OET-RV' and marker=='sp':
                    assert BBB == 'SNG'
                    if inSPdiv:
                        html = f'{html}</div><!--SP_{inSPdiv}-->\n'
                    spClass = spClassDict[rest]
                    # except KeyError:
                    #     logging.critical( f"No SP (speaker) dict entry for {rest=} {versionAbbreviation} {refTuple} {segmentType}" )
                    #     spClass = 'None'
                    html = f'{html}<div class={spClass}>'
                    inSPdiv = spClass
                html = f'{html}<p class="{marker}">{cBit}{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
        elif marker in ('b','ib'):
            html = f'{html}<br>'
        elif marker in ('list','ilist'):
            # NOTE: BibleOrgSys only creates one list/¬list pair, even if it contains embedded li2 entries
            #   so we have to handle that
            assert not rest
            assert not inList, f"inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            if segmentType != 'parallelVerse':
                html = f'{html}<ul>\n'
                inList = 'ul_1'
        elif marker in ('¬list','¬ilist'):
            assert not rest
            if not basicOnly and not inList:
                logging.warning( f"Not inList A {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inList:
                inListMarker, inListDepth = inList.split( '_', 1 )
                inListDepth = int( inListDepth )
                while inListDepth > 0:
                    if inListDepth > 1:
                        if inListEntry == True:
                            html = f'{html}</li>\n'
                            inListEntry = None
                    html = f'{html}</{inListMarker}>\n'
                    inListDepth -= 1
                inList = None
        elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4'):
            markerListLevel = int( marker[-1] )
            assert 1 <= markerListLevel <= 4
            currentListLevel = 0 if inList is None else int( inList[-1] )
            assert 0 <= currentListLevel <= 4
            if basicOnly:
                # We only do it with a span (because a list couldn't go inside a paragraph anyway, and most snippets end up put inside paragraphs)
                html = f'''{html}{'<br>' if '•' in html else ''}{'&nbsp;'*markerListLevel}<span class="{marker}">•{' ' if markerListLevel==1 else ' '}{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>'''
            else: # not basic only
                if markerListLevel > currentListLevel:
                    logging.warning( f"Not inList B {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    if markerListLevel == currentListLevel + 1: # it's one level up
                        if markerListLevel > 1:
                            assert not inListEntry
                            if html.endswith( '</li>\n' ):
                                html = f'{html[:-6]}\n' # Open the last li entry back up
                                inListEntry = True
                    else: # it's more than one level up
                        assert markerListLevel > currentListLevel + 1
                        if markerListLevel > 1:
                            assert not inListEntry
                            if html.endswith( '</li>\n' ):
                                html = f'{html[:-6]}\n' # Open the last li entry back up
                                inListEntry = True
                        currentListLevel += 1
                        while html.endswith('<br>') or html.endswith('\n'):
                            if html.endswith('<br>'): html = html[:-4]
                            if html.endswith('\n'): html = html[:-1]
                        html = f"{html}\n{' '*currentListLevel}<ul>\n"
                    while html.endswith('<br>') or html.endswith('\n'):
                        if html.endswith('<br>'): html = html[:-4]
                        if html.endswith('\n'): html = html[:-1]
                    html = f"{html}\n{' '*(markerListLevel-1)}<ul>\n"
                    inList = f'ul_{currentListLevel+1}'
                elif markerListLevel < currentListLevel:
                    if markerListLevel < currentListLevel - 1: # it's more than one level down
                        html = f'{html}</ul>\n'
                        currentListLevel -= 1
                    assert markerListLevel == currentListLevel - 1, f"{markerListLevel=} {currentListLevel=} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}"
                    logging.warning( f"Not inList C {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    html = f'{html}</ul>\n'
                    inList = f'ul_{currentListLevel-1}'
                if isinstance( inListEntry, str ):
                    logging.warning( f"already inListEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    html = f'{html}</li>\n'
                    inListEntry = None
                html = f"{html}{' '*markerListLevel}<li>{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}"
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
            assert not inList and not inListEntry, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
            if not inTable:
                if inParagraph:
                    html = f'{html}</p>\n'
                    inParagraph = None
                html = f'{html}<table>'
                inTable = 'table'
            assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
            if inTableRow:
                html = f'{html}</tr>\n'
                inTableRow = None
            # print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} TR {rest=}" )
            if rest and rest.strip():
                html = f'{html}<tr>{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}'
            else:
                html = f'{html}<tr>'
                inTableRow = 'tr'
        elif marker in ('tc1','tc2','tc3'):
            assert not inParagraph and not inList and not inListEntry and inTable and inTableRow, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {inTable=} {inTableRow=} {marker=} {rest=}"
            print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {inTable=} {inTableRow=} {marker=} {rest=}" )
            halt
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
                # if not basicOnly:
                html = f'{html}</p>\n'
                inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
        elif marker in ('ms1','ms2','ms3','ms4'):
            if inParagraph:
                logging.warning( f"Why still in paragraph {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</p>\n'
                inParagraph = None
            if inSection:
                logging.warning( f"Why still in section {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</div><!--{inSection}-->\n'
                inSection = None
            # if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
            #     html = '{html}</q1></div>\n'
            #     inSection = inParagraph = None
            # assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                # NOTE: We don't treat it like a large section (which it is), but simply as a heading
                html = f'{html}<p class="{marker}">{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}</p>\n'
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
            html = f'{html}{NARROW_NON_BREAK_SPACE}{convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state)}{NARROW_NON_BREAK_SPACE}'
        # The following should all have their own data and get converted to a simple <p>…</p> field
        elif marker in ('ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3', 'io1','io2','io3','io4'):
            assert rest, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}='{rest}'"
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            introHtml = convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )
            if marker in ('io1','io2','io3','io4'):
                introHtml = livenIORs( versionAbbreviation, refTuple, segmentType, introHtml, state )
            else:
                introHtml = livenIntroductionLinks( versionAbbreviation, refTuple, segmentType, introHtml, state )
            html = f'{html}<p class="{marker}">{introHtml}</p>\n'
        elif marker in ('iot',):
            assert rest, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}='{rest}'"
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<div class="{marker}"><p class="{marker}">{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p>\n'
        elif marker in ('¬iot',):
            assert not rest
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}</div><!--{marker[1:]}-->\n'
        elif marker == 'iex': # Possible chapter intro
            assert versionAbbreviation == 'KJB-1611' # Only one so far
            assert not inRightDiv
            assert not inSection
            assert not inParagraph
            assert rest
            # if not rest:
            #     logging.error( f"Expected text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if segmentType in ('parallelVerse','interlinearVerse'):
                assert basicOnly or refTuple[1]=='-1', f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C=}:{V=} {inSection=} {inParagraph=} {marker}={rest}"
            else:
                assert not basicOnly
                if cPrinted:
                    cBit = ''
                else:
                    cBit = f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</span> ''' \
                        if segmentType == 'chapter' else \
                            f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{toRomanNumerals(C) if versionAbbreviation=='KJB-1611' else C}</a></span> '''
                    cPrinted = True
                html = f'''{html}<p class="{versionAbbreviation}_chapterIntro">{cBit}{convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p>\n'''
        elif marker in ('periph',):
            assert rest
            assert not basicOnly
            if inParagraph:
                html = f'{html}</p>\n'
                inParagraph = None
            if inSection == 'periph':
                html = f'{html}</div><!--periph-->\n'
                inSection = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<hr style="width:60%;margin-left:0;margin-top: 0.3em">\n<div class="periph">\n<h1>{rest}</h1>\n'
            inSection = marker
        elif marker == 'headers':
            assert not rest
            if C != '-1' :
                assert segmentType not in ('parallelVerse','interlinearVerse'), f"{versionAbbreviation} {segmentType=} {refTuple} {C}:{V}"
                assert not basicOnly
            assert not inMainDiv
            # if not inMainDiv:
            inMainDiv = 'bookHeader'
            html = f'{html}<div class="{inMainDiv}">'
        elif marker == 'intro':
            assert not rest
            if C != '-1' :
                assert segmentType not in ('parallelVerse','interlinearVerse'), f"{versionAbbreviation} {segmentType=} {refTuple} {C}:{V} {markerList=}"
                assert not basicOnly
            if inMainDiv == 'bookHeader':
                html = f'{html}</div><!--{inMainDiv}-->'
                inMainDiv = None
            assert not inMainDiv
            assert not inTable and not inList
            if inParagraph:
                html = f'{html}</p>\n'
                inParagraph = None
            inMainDiv = 'bookIntro'
            html = f'{html}<div class="{inMainDiv}">'
        elif marker in ('ie', '¬intro', 'chapters'):
            assert not rest
            if C != '-1' :
                assert segmentType not in ('parallelVerse','interlinearVerse')
                assert not basicOnly
            if inMainDiv:
                html = f'{html}</div><!--{inMainDiv}-->'
                inMainDiv = None
        elif marker not in ('usfm','ide', 'sts',
                            'h', 'toc1','toc2','toc3', 'toca1','toca2','toca3', '¬headers',
                            'v=', 'cl¤', '¬c', '¬chapters'): # We can ignore all of these -- 'c#' now handled above
            if versionAbbreviation in ('ULT','UST'):
            # Can't list faulty books for uW stuff because there's too many errors keep popping up
            # and ('ACT' in refTuple or 'PSA' in refTuple or 'KI2' in refTuple): # Bad USFM encoding at UST Act 26:29-30
                logging.warning( f"Unexpected {versionAbbreviation} '{marker}' marker at {segmentType} {basicOnly=} {refTuple} {C}:{V} {rest=}" )
            else:
                raise Exception( f"Unexpected '{marker}' marker {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {rest=}" )
        if '\\f ' not in html and '\\x ' not in html: # they're handled down below
            if '\\' in html:
                (logging.warning if versionAbbreviation in ('ULT','UST') else logging.error)( f"Left-over backslash in {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'" )
                if versionAbbreviation not in ('ULT','UST') \
                or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'JER' not in refTuple and 'DEU' not in refTuple and 'JOB' not in refTuple and 'SNG' not in refTuple): # ULT Gen 14:21, ISA and UST MAT has an encoding fault in 12:20 14Feb2023
                    raise Exception( f"Left-over backslash {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} '{html}'" )

    # Check for left-over unclosed segments
    logger = logging.error if segmentType=='book' else logging.warning
    if inParagraph:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</p>\n'
    if inTableRow:
        assert inTable
        html = f'{html}</tr>\n'
    if inTable:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed table {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</table>\n'
    if inListEntry:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed listEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</li>\n'
    if inList:
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed list {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        inListMarker, inListDepth = inList.split( '_', 1 )
        inListDepth = int( inListDepth )
        while inListDepth > 0:
            if inListDepth > 1:
                if inListEntry == True:
                    html = f'{html}</li>\n'
                    inListEntry = None
            html = f'{html}</{inListMarker}>\n'
            inListDepth -= 1
    if inSPdiv:
        html = f'{html}</div><!--SP-->\n'
    if inSection in ('s1','periph'):
        if not basicOnly:
            logger( f"convertUSFMMarkerListToHtml final unclosed '{inSection}' section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        if inRightDiv:
            html = f'{html}</div><!--rightBox-->\n'
            inRightDiv = False
        html = f'{html}</div><!--{inSection}-->\n'
    if inMainDiv:
            logger( f"convertUSFMMarkerListToHtml final unclosed '{inMainDiv}' main section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
            html = f'{html}</div><!--{inMainDiv}-->'


    # Handle all footnotes in one go (but we don't check here for matching \fr fields)
    pathPrefix = '../../OET/byC/' if segmentType in ('parallelVerse','interlinearVerse') \
                        else '../OET/byC/' if segmentType in ('topicalPassage',) \
                        else '' if segmentType=='chapter' \
                        else '../byC/'
    footnotesCount = 0
    footnotesHtml = ''
    searchStartIx = 0
    for _outerSafetyCount in range( 6_900 if segmentType in ('book','section','relatedPassage') else 260 ): # max number of footnotes in segment (more than 250 in LEB DEU 12, more than 8,000 in NET PSA)
        fStartIx = html.find( '\\f ', searchStartIx )
        if fStartIx == -1: break # all done
        footnotesCount += 1
        fEndIx = html.find( '\\f*', fStartIx+3 )
        assert fEndIx != -1, f"Can't find footnote end {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {fStartIx=} {html[fStartIx:fStartIx+2*maxFootnoteChars]}"
        assert fEndIx < 9_999_999 # Or logic in next dozen lines below won't work
        assert fStartIx+4 < fEndIx < fStartIx+maxFootnoteChars, f"Unexpected footnote size {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {fEndIx-fStartIx} {html[fStartIx:fStartIx+2*maxFootnoteChars]}"
        frIx = html.find( '\\fr ', fStartIx+3 ) # Might be absent or in the next footnote
        if frIx > fEndIx: frIx = -1 # If it's in the next footnote, then there's no fr in this one

        # Find the first \f(something) or \xt field
        fFirstContentIx = html.find( '\\f', fStartIx+3 if frIx==-1 else frIx+3 )
        if fFirstContentIx >= fEndIx: fFirstContentIx = -1
        if fFirstContentIx == -1: fFirstContentIx = 9_999_999
        xFirstContentIx = html.find( '\\xt ', fStartIx+3 if frIx==-1 else frIx+3 )
        if xFirstContentIx >= fEndIx: xFirstContentIx = -1
        if xFirstContentIx == -1: xFirstContentIx = 9_999_999
        firstContentIx = min( fFirstContentIx, xFirstContentIx )
        if firstContentIx == 9_999_999:
            logging.warning( f"No internal footnote markers {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {html[fStartIx:fStartIx+2*maxFootnoteChars]}" )
            firstContentIx = fStartIx + (5 if html[fStartIx:].startswith( '\\f + ') else 3)
        else:
            assert html[firstContentIx+1:firstContentIx+3] in ('ft','fq','fk','fl','fw','fp','fv', 'fn') if versionAbbreviation=='NET' else ('ft','fq','fk','fl','fw','fp','fv'), \
                f"Unexpected '{html[firstContentIx+1:firstContentIx+3]}' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {html[fStartIx:fStartIx+2*maxFootnoteChars]}"
        assert html[firstContentIx:firstContentIx+3] != '\\f*'
        if fStartIx+5 > firstContentIx > fStartIx+16:
            logging.error( f"Unexpected footnote start {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {fStartIx=} {firstContentIx=} '{html[fStartIx:fStartIx+20]}'" ) # Skips ' + \\fr c:v '
        if frIx == -1:
            frText = ''
        else: # we have one
            assert fStartIx+5 <= frIx <= fStartIx+6, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fStartIx=} {frIx=} '{html[fStartIx:fStartIx+20]}'" # Skips ' + '
            frText = html[frIx+3:firstContentIx].strip()
        fnoteMiddle = html[firstContentIx:fEndIx]
        internalOpenCount = fnoteMiddle.count( '\\ft ') + fnoteMiddle.count( '\\fq ') + fnoteMiddle.count( '\\fqa ') + fnoteMiddle.count( '\\fk ') + fnoteMiddle.count( '\\fl ') + fnoteMiddle.count( '\\fp ') \
                                + fnoteMiddle.count( '\\xt ') \
                                + fnoteMiddle.count( '\\it ') + fnoteMiddle.count( '\\bd ') + fnoteMiddle.count( '\\bdit ') + fnoteMiddle.count( '\\em ')
        if versionAbbreviation=='NET': internalOpenCount += fnoteMiddle.count( '\\fn ') # Seems to be a NET Bible special
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\nProcessing {versionAbbreviation} {segmentType} {refTuple} footnote from '{fnoteMiddle}'" )
        if internalOpenCount > 0:
            if DEBUGGING_THIS_MODULE:
                internalCloseCount = fnoteMiddle.count( '\\ft*') + fnoteMiddle.count( '\\fq*') + fnoteMiddle.count( '\\fqa*') + fnoteMiddle.count( '\\fk*') + fnoteMiddle.count( '\\xt*')
                internalMarkerCount = internalOpenCount - internalCloseCount
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Footnote middle has {internalOpenCount=} {internalCloseCount=} {internalMarkerCount=} '{fnoteMiddle}'" )
            inSpan = None
            internalSearchStartIx = 0
            for _innerSafetyCount in range( 520 ): # max number of fields in footnote -- 25 not enough for ClVg, 400 not enough for NET ECC
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    Searching from {internalSearchStartIx}: '{fnoteMiddle[internalSearchStartIx:]}' from {fnoteMiddle=}")
                internalStartIx = fnoteMiddle.find( '\\', internalSearchStartIx )
                if internalStartIx == -1: break # all done
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Found backslash at index {internalStartIx} in '{fnoteMiddle}'" )
                fMarker = ''
                while internalStartIx + len(fMarker) < len(fnoteMiddle):
                    if fnoteMiddle[internalStartIx+len(fMarker)+1].islower():
                        fMarker = f'{fMarker}{fnoteMiddle[internalStartIx+len(fMarker)+1]}'
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Forming {fMarker=} from '{fnoteMiddle[internalStartIx:internalStartIx+20]}…'" )
                    else: break
                if fnoteMiddle[internalStartIx+len(fMarker)+1] == ' ': # It's an opening marker
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got {versionAbbreviation} {refTuple} opening {fMarker=} with {inSpan=} from '{fnoteMiddle[internalStartIx:internalStartIx+20]}…'" )
                    span = f'<span class="{fMarker}">' # 15 characters + len(fMarker)
                    internalSearchStartIx = internalStartIx + 15 + len(fMarker)
                    if inSpan:
                        span = f'</span>{span}'
                        internalSearchStartIx += 7
                        inSpan = None
                    if fMarker == 'xt':
                        fNoteXTrest = fnoteMiddle[internalStartIx+len(fMarker)+1:]
                        fNoteXTrestEndIx = fNoteXTrest.find( '\\' )
                        if fNoteXTrestEndIx == -1: # no more subfields in this
                            fNoteContinuation = ''
                            livenedFootnoteXref = livenXRefField( 'f', versionAbbreviation, refTuple, segmentType, pathPrefix, frText, fNoteXTrest, state )
                            fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{livenedFootnoteXref}' # {fnoteMiddle[internalStartIx+len(fMarker)+2:]}
                        else: # Only go up to the next field
                            fNoteXTrest, fNoteContinuation = fNoteXTrest[:fNoteXTrestEndIx], fNoteXTrest[fNoteXTrestEndIx:]
                            # print( f"{fNoteXTrest=} {fNoteContinuation=}" )
                        livenedFootnoteXref = livenXRefField( 'f', versionAbbreviation, refTuple, segmentType, pathPrefix, frText, fNoteXTrest, state )
                        fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{livenedFootnoteXref}{fNoteContinuation}'
                    else: # it's a regular footnote format field (not an xt field inside a footnote)
                        fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}{span}{fnoteMiddle[internalStartIx+len(fMarker)+2:]}'
                    inSpan = fMarker
                elif fnoteMiddle[internalStartIx+len(fMarker)+1] == '*': # It's a closing marker
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Got closing {fMarker=} with {inSpan=} from '{fnoteMiddle[internalStartIx:internalStartIx+20]}…'" )
                    assert inSpan
                    fnoteMiddle = f'{fnoteMiddle[:internalStartIx]}</span>{fnoteMiddle[internalStartIx+len(fMarker)+2:]}'
                    inSpan = None
                    internalSearchStartIx = internalStartIx + 7
                else: unexpected_char in footnote
            else:
                logging.critical( f"inner_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_innerSafetyCount=}" )
                inner_fn_loop_needed_to_break
            if inSpan: # at end
                fnoteMiddle = f'{fnoteMiddle}</span>'
            assert '\\' not in fnoteMiddle, f"{fnoteMiddle[fnoteMiddle.index(f'{BACKSLASH}x')-10:fnoteMiddle.index(f'{BACKSLASH}x')+12]}"
        dPrint( 'Info' if '"xt"' in fnoteMiddle else 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {refTuple} {fnoteMiddle=}" )
        if versionAbbreviation == 'OET-LV': # then we don't want equals or underlines in the footnote to get converted into spans later
            fnoteMiddle = fnoteMiddle.replace('.', '--fnPERIOD--').replace(':', '--fnCOLON--') # So we protect them -- gets fixed in do_OET_LV_HTMLcustomisations() in html.py
        assert '<br>' not in fnoteMiddle, f"{versionAbbreviation} {segmentType} {refTuple} {fnoteMiddle=}"
        sanitisedFnoteMiddle = fnoteMiddle
        if versionAbbreviation == 'OET-LV':
            if ' note--fnCOLON--' not in sanitisedFnoteMiddle and 'Note--fnCOLON--' not in sanitisedFnoteMiddle:
                sanitisedFnoteMiddle = f'Note--fnCOLON-- {sanitisedFnoteMiddle}'
        else: # not OET-LV
            if ' note:' not in sanitisedFnoteMiddle and 'Note:' not in sanitisedFnoteMiddle:
                sanitisedFnoteMiddle = f'Note: {sanitisedFnoteMiddle}'
        if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '</span>', '' )
            sanitisedFnoteMiddle = spanClassRegEx.sub( '', sanitisedFnoteMiddle )
            for charMarker in ('em','i','b', 'sup','sub'): # These are HTML markers
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<{charMarker}>', '' ).replace( f'</{charMarker}>', '' )
            # if versionAbbreviation == 'OET-LV': # then we don't want equals or underlines in the sanitised footnote to get converted into spans later
            #     sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace('_', '--fnUNDERLINE--').replace('=', '--fnEQUAL--') # So we protect them -- gets fixed in do_OET_LV_HTMLcustomisations() in html.py
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {refTuple} {sanitisedFnoteMiddle=}" )
            # if '_' in sanitisedFnoteMiddle or 'UNDERLINE' in sanitisedFnoteMiddle \
            # or '=' in sanitisedFnoteMiddle or 'EQUAL' in sanitisedFnoteMiddle: halt
            if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
                logging.warning( f"Left-over HTML chars in {versionAbbreviation} {refTuple} {sanitisedFnoteMiddle=}" )
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '"', '&quot;' ).replace( '<', '&lt;' ).replace( '>', '&gt;' )
                # if versionAbbreviation != 'LEB': # LEB MRK has sanitisedFnoteMiddle='Note: A quotation from Isa 40:3|link-href="None"'
                #     halt # in case it's a systematic problem
        if versionAbbreviation == 'OET-LV': # then we don't want equals or underlines in the sanitised footnote to get converted into spans later
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace('.', '--fnPERIOD--').replace(':', '--fnCOLON--') # So we protect them -- gets fixed in do_OET_LV_HTMLcustomisations() in html.py
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace('_', '--fnUNDERLINE--').replace('=', '--fnEQUAL--') # So we protect them -- gets fixed in do_OET_LV_HTMLcustomisations() in html.py
            assert ':' not in sanitisedFnoteMiddle and '.' not in sanitisedFnoteMiddle \
                and '_' not in sanitisedFnoteMiddle and '=' not in sanitisedFnoteMiddle
        assert '"' not in sanitisedFnoteMiddle and '<' not in sanitisedFnoteMiddle and '>' not in sanitisedFnoteMiddle, f"Left-over HTML chars in {versionAbbreviation} {refTuple} {sanitisedFnoteMiddle=}"
        footnotePopup = sanitisedFnoteMiddle if len(sanitisedFnoteMiddle) < 1010 else f'{sanitisedFnoteMiddle[:999]}…'
        fnoteCaller = f'<span class="fnCaller">[<a title="{unicodedata.normalize('NFC',footnotePopup)}" href="#fn{footnotesCount}">fn</a>]</span>'
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
            assert frText[-1] != '\n'
            fnoteRef = f'<span class="fnRef"><a title="Return to text" href="{frCV}">{frText}</a></span> '
        if versionAbbreviation=='OET-LV' and fnoteMiddle.startswith( 'OSHB '):
            fnoteMiddle = fnoteMiddle.replace( 'OSHB ', '<a href="https://hb.OpenScriptures.org">OSHB</a> ', 1 ) # Make it a live link
        fnoteText = f'<p class="fn" id="fn{footnotesCount}">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p>\n'
        if segmentType.endswith('Verse') and f'">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p>\n' in footnotesHtml:
            # We already have an identical footnote created, e.g., in OET-LV Job 8:16
            #   so all we have to do, is add the additional id to the existing note
            #       but can't have multiple id's on one element, so have to add an extra empty span.
            #   We only do this for single verses because the backwards link can't work for both.
            dupIx = footnotesHtml.index( f'">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p>\n' )
            footnotesHtml = f'{footnotesHtml[:dupIx]}"><span id="fn{footnotesCount}"></span>{footnotesHtml[dupIx+2:]}'
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesHtml=}" )
        else: # append this footnote to go at the bottom
            footnotesHtml = f'{footnotesHtml}{fnoteText}'
        html = f'{html[:fStartIx]}{fnoteCaller}{html[fEndIx+3:]}'
        # searchStartIx = fEndIx + 3
        searchStartIx = fStartIx + len(fnoteCaller)
        # if searchStartIx < fEndIx+3:
        #     print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fStartIx:,=} {fEndIx+3:,=} {searchStartIx:,=} '{html[searchStartIx:searchStartIx+10]}'" )
    else:
        logging.critical( f"outer_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_outerSafetyCount=}" )
        outer_fn_loop_needed_to_break
    if footnotesHtml:
        if not checkHtml( f"Footnotes for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fnoteMiddle=}", footnotesHtml, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE: halt
        # if '<a title="Variant note' in html:
        #     nIx = html.index( '<a title="Variant note' )
        #     print( f"FOUND FN TITLE {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} '{html[nIx:nIx+80]}'" )
        assert '<a title="Variant note:\n<br>' not in html # Check this before we append the actual footnote content to the end.
        html = f'{html}<hr style="width:35%;margin-left:0;margin-top: 0.3em">\n<div id="footnotes" class="footnotes">\n{footnotesHtml}</div><!--footnotes-->\n'
    # TODO: Find out why these following exceptions occur
    if versionAbbreviation not in ('T4T','BrTr','ClVg','TCNT','TC-GNT'): # T4T ISA 33:8, BrTr KI1 6:36a, ClVg MRK 3:10, TCNT&TC-GNT INT \\fp Why???
        assert '\\f' not in html, f"{versionAbbreviation} {refTuple} html='…{html[html.index(f'{BACKSLASH}f')-10:html.index(f'{BACKSLASH}f')+maxFootnoteChars]}…'"


    # Now handle all cross-references in one go (we don't check for matching \xo fields)
    crossReferencesCount = 0
    crossReferencesHtml = ''
    searchStartIx = 0
    for _safetyCount1 in range( 999 if segmentType=='book' else 99 ):
        xStartIx = html.find( '\\x ', searchStartIx )
        if xStartIx == -1: break # all done
        # if versionAbbreviation=='KJB-1611': print( f"{versionAbbreviation} {refTuple} {segmentType=} got {xStartIx=}" )
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

        # Liven the cross-references (xrefs) themselves
        xrefLiveMiddle = xrefOriginalMiddle = html[xtIx+4:xEndIx]
        # if versionAbbreviation=='KJB-1611': print( f"{versionAbbreviation} {refTuple} {segmentType=} got {xrefOriginalMiddle}" )
        xrefOriginalMiddle = xrefOriginalMiddle.replace('\\xo ','').replace('\\xt ','') # Fix things like "Gen 25:9-10; \\xo b \\xt Gen 35:29."
        # print( f" {xrefLiveMiddle=}")
        assert xrefLiveMiddle.count('\\xo ') == xrefLiveMiddle.count('\\xo '), f"{xrefLiveMiddle=}"
        xrefLiveMiddle = xrefLiveMiddle.replace('\\xo ','<b>').replace('\\xt ','</b>') # Fix things like "Gen 25:9-10; \\xo b \\xt Gen 35:29."
        xrefLiveMiddle = livenXRefField( 'x', versionAbbreviation, refTuple, segmentType, pathPrefix, xoText, xrefLiveMiddle, state )

        # Now create the caller and the actual xref
        xrefCaller = f'<span class="xrCaller">[<a title="See also {xrefOriginalMiddle}" href="#xr{crossReferencesCount}">ref</a>]</span>' # was †
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
        html = f'{html}<hr style="width:30%;margin-left:0;margin-top: 0.3em">\n<div id="crossRefs" class="crossRefs">\n{crossReferencesHtml}</div><!--crossRefs-->\n'
    if versionAbbreviation not in ('BrTr',): # BrTr ISA 52
        assert '\\x' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}"
    # if refTuple==('DAN','1','2') or refTuple==('DAN','1','18'): halt

    # Some final styling and cleanups
    if 'OET' in versionAbbreviation:
        html = html \
                .replace( '◘', f'''<a title="Go to missing verses pages" href="{'../'*level}OET/missingVerses.htm">◘</a>''' )
        if versionAbbreviation == 'OET-LV':
            html = html.replace( 'ə', '<small>ə</small>' )

    if BBB == 'PSA':
        html = html.replace( 'class="d"> <span class="va"', 'class="d"><span class="va"' ) # Happens in UHB somehow

    if basicOnly: # remove leading, trailing, and internal blank lines
        while '<br><br>' in html:
            html = html.replace( '<br><br>', '<br>' )
        while html.startswith( '<br>' ): # BSB and OEB seems particularly bad with blank lines
            html = html[4:]
        while html.endswith( '<br>' ): # LEB also
            html = html[:-4]

    if '<br>\n' in html:
        ix = html.index( '<br>\n' )
        print( f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} …{html[ix-20:ix]}{html[ix:ix+20]}…" )
        halt
    html = html.replace( '<br>\n', '\n<br>' ) # This is our consistent (arbitrary) choice in OBD
    if '\n\n' in html:
        ix = html.index( '\n\n' )
        print( f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} …{html[ix-20:ix]}{html[ix:ix+20]}…" )
        halt
    html = html.replace( '\n\n', '\n' )

    while html.endswith( '\n' ): html = html[:-1] # We don't end our html with a newline
    while html.endswith( '<br>' ):
        html = html[:-4] # We don't end our html with a newline
        while html[-1] == '\n': html = html[:-1] # We don't end our html with a newline

    # Some final checks
    if versionAbbreviation not in ('ULT','UST'): # uW stuff has too many USFM encoding errors
        assert 'strong="' not in html, f"{level=} ‘{versionAbbreviation}’ {refTuple} {segmentType=} {len(contextList)=} {len(markerList)=} {basicOnly=} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
    if not checkHtml( f'convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
        if DEBUGGING_THIS_MODULE and versionAbbreviation!='OEB': # OEB has error in Job 26:14
            halt
    # print( f"convertUSFMMarkerListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=}) ended with newline: {html.endswith(NEWLINE)}" )
    return html
# end of usfm.convertUSFMMarkerListToHtml


def convertUSFMCharacterFormatting( versionAbbreviation:str, refTuple:tuple, segmentType:str, usfmField:str, basicOnly:bool, state:State ) -> str:
    """
    Handles character formatting inside USFM lines.

    This includes \\fig and \\jmp

    Automatically changes \\nd to Nomina Sacra for OET NT books

    Seems that the basicOnly flag doesn't currently affect anything???
    """
    from createSectionPages import findSectionNumber
    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMCharacterFormatting( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMCharacterFormatting( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
    for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers + ['untr','fig']:
        openCount, closeCount = usfmField.count( f'\\{charMarker} ' ), usfmField.count( f'\\{charMarker}*' )
        if openCount != closeCount:
            logging.error( f"Mismatched USFM character markers: '{charMarker}' open={openCount} close={closeCount} from {versionAbbreviation} {refTuple} '{usfmField}'" )

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
                    elif segmentType.endswith( 'Verse' ):
                        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"convertUSFMCharacterFormatting( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
                        # print( f"{versionAbbreviation}, {refTuple}, {ourBBB=} {refC=} {refV=} {jmpDisplay=}" )
                        newLink = f'<a title="Go to internal jump link reference verse" href="C{refC}V{refV}.htm#Top">{jmpDisplay}</a>'
                    elif segmentType in ('section','relatedPassage'):
                        if 1:
                        # try: # Now find which section that reference starts in
                            # print( f"{state.sectionsLists[versionAbbreviation][ourBBB]=}" )
                            n = findSectionNumber( versionAbbreviation, ourBBB, refC, refV, state )
                            # intV = getLeadingInt( refV )
                            # found = False
                            # for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sFilename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                            #     if startC==refC and endC==refC:
                            #         if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                            #             found = True
                            #             break
                            #     elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                            #         found = True
                            #         break
                            #     elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                            #         found = True
                            #         break
                            # if found:
                            if n is not None:
                                newLink = f'<a title="Go to to section page with reference" href="{ourBBB}_S{n}.htm#Top">{jmpDisplay}</a>'
                            else:
                                logging.critical( f"unable_to_find_reference for {ourBBB} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation]]}" )
                                newLink = jmpDisplay # Can't make a link
                                unable_to_find_reference # Need to write more code
                        # except KeyError:
                        #     logging.critical( f"convertUSFMCharacterFormatting for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
                        #     newLink = guts # Can't make a link
                    else:
                        dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"convertUSFMCharacterFormatting( {versionAbbreviation}, {refTuple}, {segmentType}, '{usfmField}' )" )
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
                raise Exception( f"convertUSFMCharacterFormatting() w loop needed to break at {versionAbbreviation} {refTuple} '{segmentType}' with ({wCount:,}) '{usfmField}'" )
            assert '\\w ' not in html and '\\+w ' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}" # Note: can still be \\wj in text

    if '\\tc' in usfmField:
        html = html.replace( '\\tc1 ', '<td>' ).replace( '\\tc2 ', '</td><td>' ).replace( '\\tc3 ', '</td><td>' ).replace( '\\tc4 ', '</td><td>' ).replace( '\\tc5 ', '</td><td>' )
    assert '\\tr' not in html, f"TR {versionAbbreviation} {refTuple} {segmentType} {basicOnly=} {usfmField=} {html=}"

    # Replace the character markers which have specific HMTL equivalents
    # NOTE: Embedded markers like \\+em have already had the + removed above
    html = html \
            .replace( '\\bdit ', '<b><i>' ).replace( '\\bdit*', '</i></b>' ) \
            .replace( '\\bd ', '<b>' ).replace( '\\bd*', '</b>' ) \
            .replace( '\\it ', '<i>' ).replace( '\\it*', '</i>' ) \
            .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
            .replace( '\\sup ', '<sup>' ).replace( '\\sup*', '</sup>' )

    # Special handling for OT '\\nd LORD\\nd*' (this is also in createParallelVersePages)
    html = html.replace( '\\nd LORD\\nd*', '\\nd L<span style="font-size:.75em;">ORD</span>\\nd*' )

    # Now replace all the other character markers into HTML spans, e.g., \\add \\nd \\bk
    expandedCharMarkers = BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers + ['untr'] # Our custom addition
    if versionAbbreviation == 'NET': expandedCharMarkers += ['heb','theb','grk','tgrk','ver','src','fx']
    # assert 'qac' in expandedCharMarkers, f"({len(expandedCharMarkers)}) {expandedCharMarkers}"
    for charMarker in expandedCharMarkers:
        if charMarker=='nd' and 'OET' in versionAbbreviation and ourBBB in BOOKLIST_NT27:
            html = html.replace( '\\nd ', '<span class="nominaSacra">' ).replace( '\\nd*', '</span>' )
        else:
            html = html.replace( f'\\{charMarker} ', f'<span class="{charMarker}">' ).replace( f'\\{charMarker}*', '</span>' )

    if 'OET' in versionAbbreviation: # Append "untranslated" to titles/popup-boxes for untranslated words in OET-LV
        # count = 0
        searchStartIndex = 0
        for _safetyCount in range( 900 ):
            ix = html.find( '<span class="untr"><a title="', searchStartIndex )
            if ix == -1: break # all done
            ixEnd = html.index( '" href=', ix+29 )
            html = f'{html[:ixEnd]} (untranslated){html[ixEnd:]}'
            # count += 1
            searchStartIndex = ixEnd + 5
        else: need_to_increase_loop_count_for_untranslated_words

    # Final checking
    if versionAbbreviation not in ('UST','ULT'): # uW stuff has too many USFM encoding errors and inconsistencies
        assert 'strong="' not in html, f"‘{versionAbbreviation}’ {refTuple} {segmentType=} {basicOnly=} {usfmField=}\n  html='{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
    if '\\ts\\*' in html:
        logging.critical( f"Removing ts marker in {versionAbbreviation} {refTuple} {segmentType} {basicOnly=}…")
        html = html.replace( '\\ts\\*', '' )
    if '\\f ' not in html and '\\x ' not in html:
        # AssertionError: versionAbbreviation='ULT' refTuple=('ISA',) segmentType='book' 'usfmField='\\w to|x-occurrence="1" x-occurrences="2"\\w* \\w dishonor|x-occurrence="1" x-occurrences="1"\\w* \\zaln-s |x-strong="H1347" x-lemma="גָּאוֹן" x-morph='' basicOnly=False 'to dishonor \zaln-s |x-strong="H1347" x-lemma="גָּאוֹן" x-morph='
        if (versionAbbreviation not in ('TCNT','TC-GNT') or 'INT' not in refTuple) \
        and (versionAbbreviation not in ('ULT','UST') \
            or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'JER' not in refTuple and 'DEU' not in refTuple and 'JOB' not in refTuple and 'SNG' not in refTuple)): # ULT Gen 14:20, ISA and UST MAT has an encoding fault in 12:20 14Feb2023
            assert '\\' not in html, f"{versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
    if not checkHtml( f'convertUSFMCharacterFormatting({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
        if DEBUGGING_THIS_MODULE and versionAbbreviation!='OEB': # OEB ISA has a \\em mismatch
            halt
    return html
# end of usfm.convertUSFMCharacterFormatting


# TODO: Currently 'about Jesus the messiah (Acts 12:25, 13:13).' this wrongly thinks 13:13 is in the current book!
singleBCVRefRegex = re.compile( '([(])([^()]+?) ([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?([ ,.?!:;)])' )
singleCVRefRegex = re.compile( '([ (])([1-9][0-9]{0,2}):([1-9][0-9]{0,2})([-–][1-9][0-9]{0,2})?([ ,.?!:;)])' )
def livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str, introHtml:str, state:State ) -> str:
    """
    Liven general links in the introduction, e.g., 'was named Mary (Acts 12:12)' or 'accompanied Peter (1 Peter 5:13)'
        or 'about Jesus the messiah (Acts 12:25, 13:13).'
    """
    from createSectionPages import findSectionNumber
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )…" )
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
        if refB.startswith( 'See ' ): refB =refB[4:]
        refBBB = getBBBFromOETBookName( refB )
        if not refBBB:
            logging.warning( f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' ) failed to  find BBB for {refB=} from intro ref CV match with '{preChar}' '{guts}' '{postChar}' -> {match.groups()=}")
            # newGuts = guts # Can't make a link
            refBBB = ourBBB # Assume it's an internal link to this book
        if segmentType == 'book':
            newGuts = f'<a title="Go to reference document" href="{refBBB}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Go to reference chapter" href="{refBBB}_C{refC}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType.endswith( 'Verse' ): # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{refC}V{refV}.htm#Top">{guts}</a>'
        elif segmentType in ('section','relatedPassage'):
            if 1:
            # try: # Now find which section that reference starts in
                # print( f"{state.sectionsLists[versionAbbreviation][refBBB]=}" )
                n = findSectionNumber( versionAbbreviation, refBBB, refC, refV, state )
                # intV = getLeadingInt(refV)
                # found = False
                # for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sFilename) in enumerate( state.sectionsLists[versionAbbreviation][refBBB] ):
                #     if startC==refC and endC==refC:
                #         if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                #             found = True
                #             break
                #     elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                #         found = True
                #         break
                #     elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                #         found = True
                #         break
                # if found:
                if n is not None:
                    newGuts = f'<a title="Go to to section page with reference" href="{refBBB}_S{n}.htm#Top">{guts}</a>'
                else:
                    logging.critical( f"unable_to_find_reference for {versionAbbreviation} {refBBB} {refC}:{refV}" )
                    # logging.critical( f"   {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation][refBBB]]}" )
                    # for n, something in enumerate( state.sectionsLists[versionAbbreviation][refBBB] ):
                    #     logging.critical( f"  {n}: {something}")
                    #     assert isinstance( something, tuple )
                    #     startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_filename = something
                    #     logging.critical( f"    f'{startC}:{startV}…{endC}:{endV}'" )
                    newGuts = guts # Can't make a link
                    unable_to_find_reference # Need to write more code
            # except KeyError:
            #     logging.critical( f"livenIntroductionLinks for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
            #     newGuts = guts # Can't make a link
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
        logging.warning( f"Assuming {versionAbbreviation} {ourBBB} intro '{guts}' ref is a self-reference BUT THIS COULD EASILY BE WRONG" )
        if segmentType == 'book':
            newGuts = f'<a title="Jump down to reference" href="#C{refC}V{refV}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Jump to chapter page with reference" href="{ourBBB}_C{refC}.htm#C{refC}V{refV}">{guts}</a>'
        elif segmentType.endswith( 'Verse' ): # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{refC}V{refV}.htm#Top">{guts}</a>'
        elif segmentType in ('section','relatedPassage'):
            if 1:
            # try: # Now find which section that reference starts in
                n = findSectionNumber( versionAbbreviation, ourBBB, refC, refV, state )
                # intV = getLeadingInt(refV)
                # found = False
                # for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sFilename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                #     if startC==refC and endC==refC:
                #         if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                #             found = True
                #             break
                #     elif startC==refC and intV>=getLeadingInt(startV): # It's in the first chapter
                #         found = True
                #         break
                #     elif endC==refC and intV<=getLeadingInt(endV): # It's in the second chapter
                #         found = True
                #         break
                # if found:
                if n is not None:
                    newGuts = f'<a title="Jump to section page with reference" href="{ourBBB}_S{n}.htm#Top">{guts}</a>'
                else:
                    # for something in state.sectionsLists[versionAbbreviation][ourBBB]:
                    #     print( f"  {type(something)=} {len(something)=} {something=}" )
                    logging.error( f"PROBABLY WRONGLY GUESSED BOOK: unable_to_find_reference for {ourBBB=} {refC}:{refV} {[f'{startC}:{startV}…{endC}:{endV}' for _n,startC,startV,endC,endV,_sectionName,_reasonName,_contextList,_verseEntryList,_sFilename in state.sectionsLists[versionAbbreviation][ourBBB]]}" )
                    newGuts = guts # Can't make a link
                    # unable_to_find_reference # Need to write more code
            # except KeyError:
            #     logging.critical( f"livenIntroductionLinks for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
            #     newGuts = guts # Can't make a link
        else:
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            ooopsie2
        introHtml = f"{introHtml[:match.start()]}{preChar}{newGuts}{postChar}{introHtml[match.end():]}"
        searchStartIx = match.end() + len(newGuts)+2 - len(guts) # Approx chars that we added

    return introHtml
# end of usfm.livenIntroductionLinks


def livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str, state:State ) -> str:
    """
    Given some html, search for <span class="ior"> (these are usually in introduction \\iot lines)
        and liven those IOR links.
    """
    from createSectionPages import findSectionNumber
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )" )
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )…" )
    assert '\\ior' not in ioLineHtml

    ourBBB = refTuple[0]
    isSingleChapterBook = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( ourBBB )

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
        elif isSingleChapterBook:
            Cstr, Vstr = '1', startGuts.strip() # Only a verse was given
        else: Cstr, Vstr = startGuts.strip(), '1' # Only a chapter was given
        if segmentType == 'book':
            newGuts = f'<a title="Jump down to reference" href="#C{Cstr}V{Vstr}">{guts}</a>'
        elif segmentType == 'chapter':
            newGuts = f'<a title="Jump to chapter page with reference" href="{ourBBB}_C{Cstr}.htm#C{Cstr}V{Vstr}">{guts}</a>'
        elif segmentType.endswith( 'Verse' ): # For an introduction (so 'verse' is 'line')
            # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
            assert refTuple[1] == '-1', f"{refTuple=}"
            # print( f"{versionAbbreviation}, {refTuple}, {refBBB=} {refC=} {refV=} {guts=}" )
            newGuts = f'<a title="Go to reference verse" href="C{Cstr}V{Vstr}.htm#Top">{guts}</a>'
        elif segmentType in ('section','relatedPassage'):
            if 1:
            # try: # Now find which section that IOR starts in
                n = findSectionNumber( versionAbbreviation, ourBBB, Cstr, Vstr, state )
                # intV = getLeadingInt(Vstr)
                # found = False
                # for n, (startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sFilename) in enumerate( state.sectionsLists[versionAbbreviation][ourBBB] ):
                #     if startC==Cstr and endC==Cstr:
                #         # print( f"Single chapter {startC}=={Cstr}=={endC} {getLeadingInt(startV)=} {intV=} {getLeadingInt(endV)=}")
                #         if getLeadingInt(startV) <= intV <= getLeadingInt(endV): # It's in this single chapter
                #             found = True
                #             break
                #     elif startC==Cstr and intV>=getLeadingInt(startV): # It's in the first chapter
                #         found = True
                #         break
                #     elif endC==Cstr and intV<=getLeadingInt(endV): # It's in the second chapter
                #         found = True
                #         break
                # if found:
                if n is not None:
                    newGuts = f'<a title="Jump to section page with reference" href="{ourBBB}_S{n}.htm#Top">{guts}</a>'
                else:
                    logging.critical( f"unable_to_find_IOR for {ourBBB} {Cstr}:{Vstr} {[f'{startC}:{startV}…{endC}:{endV}' for startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,sFilename in state.sectionsLists[versionAbbreviation][ourBBB]]}" )
                    newGuts = guts # Can't make a link
                    unable_to_find_reference # Need to write more code
            # except KeyError:
            #     logging.critical( f"livenIORs for {versionAbbreviation}, {refTuple}, {segmentType} can't find section list for {ourBBB}" )
            #     newGuts = guts # Can't make a link
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


myKJB1611XrefTable = {
    'Actes':'ACT', 'Acts':'ACT', 'Act':'ACT', 'actes':'ACT', 'acts':'ACT', 'act':'ACT',
    'Amos':'AMO', 'amos':'AMO',
    'Apoc':'REV','apoc':'REV',
    '1. Chron':'CH1', '1.Chron':'CH1','1.chron':'CH1', '1 Chron':'CH1', '1.Chro':'CH1', '1.chro':'CH1', '1 chron':'CH1',
    '2.Chron':'CH2','2.chron':'CH2', '2.Chro':'CH2','2.chro':'CH2', '2.Chr':'CH2','2.chr':'CH2',
    '1.Corin':'CO1','1.corin':'CO1','1.Cor':'CO1','1.cor':'CO1',
    '2.Cor':'CO2','2.cor':'CO2',
    'coloss':'COL', 'Col':'COL', 'col':'COL',
    'Dan':'DAN',
    'Deut':'DEU','deut':'DEU', 'Deu':'DEU','deu':'DEU',
    'Eccles':'ECC','eccles':'ECC',
    'Ephes':'EPH', 'ephes':'EPH', 'Eph':'EPH', 'eph':'EPH', 'ephe':'EPH',
    'Ester':'EST', 'Esth':'EST', 'Es':'EST', 'esth':'EST',
    'Exod':'EXO','exod':'EXO', 'Exo':'EXO',
    'Ezech':'EZE','ezech':'EZE', 'Ezek':'EZE','ezek':'EZE', 'ezec':'EZE',
    'Ezra':'EZR',
    'Gene':'GEN','Gen':'GEN',
    'Galat':'GAL','galat':'GAL', 'Gal':'GAL','gal':'GAL',
    'Habac':'HAB','hab':'HAB', 'Abak':'HAB', 'Abac':'HAB',
    'Hagge':'HAG', 'Agge':'HAG','agge':'HAG',
    'Hebr':'HEB', 'hebr':'HEB', 'Heb':'HEB', 'heb':'HEB',
    'Hose':'HOS', 'Hos':'HOS','hos':'HOS', 'Osee':'HOS', 'Ose':'HOS','ose':'HOS', 'Os':'HOS',
    'Isai':'ISA','isai':'ISA', 'Esai':'ISA', 'Esa':'ISA','esa':'ISA', 'Esay':'ISA','esay':'ISA', 'esai':'ISA', 'Isa':'ISA','isa':'ISA',
    'Iames':'JAM', 'Iam':'JAM', 'iam':'JAM',
    'Iude':'JDE','iude':'JDE','Iud':'JDE','iud':'JDE',
    'iuges':'JDG', 'Iudg':'JDG','iudg':'JDG',
    'iudith':'JDT', 'iudit':'JDT',
    'Ier':'JER','ier':'JER','Ierem':'JER', 'Iere':'JER', 'iere':'JER', 'ierem':'JER', 'Iee':'JER',
    'Ioh':'JHN','ioh':'JHN','Iohn':'JHN','iohn':'JHN',
    '1.Iohn':'JN1','1.iohn':'JN1', 'I.Iohn':'JN1', '1.Ioh':'JN1','1.ioh':'JN1',
    'Iona':'JNA',
    'Iob':'JOB','iob':'JOB',
    'Ioel':'JOL','ioel':'JOL',
    'Iosh':'JOS','iosh':'JOS','Ios':'JOS','Iosu':'JOS',
    '1.Kings':'KI1', '1.King':'KI1', '1.king':'KI1', '1 King':'KI1', '1.Kin':'KI1','1.kin':'KI1', '1 kin':'KI1',
            '1.Reg':'KI1',
    '2.Kings':'KI2', '2.King':'KI2','2.king':'KI2', '2 king':'KI2', '2.Kin':'KI2','2.kin':'KI2',
    'Lam':'LAM', 'lam':'LAM',
    '4.Esdr':'LES','4.Esd':'LES',
    'Leuit':'LEV','leuit':'LEV', 'Leui':'LEV','leui':'LEV', 'Leu':'LEV',
    'Luc':'LUK','luc':'LUK', 'Luk':'LUK', 'Luke':'LUK','luke':'LUK','luk':'LUK',
    '1.Macc':'MA1', '1 macc':'MA1', '1.Mac':'MA1',
    '2.Macc':'MA2','2.macc':'MA2', '2.mac':'MA2',
    'Malac':'MAL', 'Mala':'MAL', 'Mal':'MAL',
    'Matth':'MAT', 'Matt':'MAT','Mat':'MAT','mat':'MAT', 'matth':'MAT', 'matt':'MAT',
    'mica':'MIC',
    'Marke':'MRK','marke':'MRK', 'Mark':'MRK','mark':'MRK', 'Marc':'MRK', 'Mar':'MRK','mar':'MRK',
    'naum':'NAH',
    'Nehem':'NEH', 'nehem':'NEH', 'Nehe':'NEH', 'nehe':'NEH',
    'Numb':'NUM','numb':'NUM', 'Num':'NUM', 'num':'NUM', 'nnm':'NUM',
    '1.Pet':'PE1', '1.pet':'PE1',
    '2.Pet':'PE2','2.pet':'PE2',
    'Phil':'PHP', 'phil':'PHP',
    'Psal':'PSA', 'psal':'PSA', 'psalme':'PSA', 'Psa':'PSA', 'Ps':'PSA', 'psa':'PSA',
    'Prou':'PRO', 'Pro':'PRO', 'pro':'PRO', 'prou':'PRO',
    '1.Sam':'SA1','1.sam':'SA1', '1 Sam':'SA1',
    '2.Sam':'SA2',
    '1.Thess':'TH1','1.thess':'TH1', '1 thess':'TH1', '1.Thes':'TH1','1.thes':'TH1',
    '2.thes':'TH2', '2 thess':'TH2',
    '1.tim':'TI1',
    '2.tim':'TI2',
    'Tit':'TIT',
    'tob':'TOB',
    'Reuel':'REV','reuel':'REV', 'reue':'REV', 'Reu':'REV','reu':'REV',
    'Rom':'ROM', 'rom':'ROM',
    'ecclus':'SIR', 'Ecclus':'SIR','Ecclu':'SIR','ecclu':'SIR', # Sirach / Ecclesiasticus
    '1.Tim':'TI1',
    'Wisd':'WIS', 'Wis':'WIS', 'wisd':'WIS', 'wis':'WIS',
    'Zach':'ZEC','zach':'ZEC',  'Zac':'ZEC',
    }
BCVRefRegEx = re.compile( '(?: ?and)? ?([1234I]?[ .]?[A-Za-z][a-z]{1,12})\\.? ?([1-9][0-9]{0,2})[:.–] ?([1-9][0-9]{0,2})' ) # Can have en-dash for chapter range
BVRefRegEx = re.compile( '([1234I]?[ .]?[A-Za-z][a-z]{0,12})\\.? ?([1-9][0-9]{0,2})' ) # For single-chapter book or for whole chapter
CVRefRegEx = re.compile( '([1-9][0-9]{0,2})[:.]([1-9][0-9]{0,2})' )
def livenXRefField( fieldType:str, versionAbbreviation:str, refTuple:tuple, segmentType:str, pathPrefix:str, xoText:str, xrefOriginalMiddle:str, state:State ) -> str:
    """
    Given the middle of a cross-reference or the xt field from a footnote,
        return the text but with the xref(s) in it livened.

    State parameter is only used for the OET-RV.
    """
    from createSectionPages import findSectionNumber
    fnPrint( DEBUGGING_THIS_MODULE, f"livenXRefField( {fieldType}, {versionAbbreviation}, {refTuple}, {segmentType}, '{pathPrefix}', {xoText=}, {xrefOriginalMiddle=} )" )
    assert fieldType in 'fx'

    # TODO: The following code does not work for one chapter books (Jude 5), additional Vs (Mrk 3:4,5), or additional CVs (Mrk 3:4; 4:5)
    # TODO: The following code is untidy, not including combined verses in the link, e.g., Mrk 3:4-5
    BBB = refTuple[0] # Compulsory
    xrefLiveMiddle = xrefOriginalMiddle

    if versionAbbreviation == 'RV':
        xrefLiveMiddle = ( xrefLiveMiddle \
                            .replace( ' iii ',' iii.') # Fixes an inconsistency
                            .replace( 'xxxix.', '39.' ).replace( 'xxxviii.', '38.' ).replace( 'xxxvii.', '37.' ).replace( 'xxxvi.', '36.' ).replace( 'xxxv.', '35.' ).replace( 'xxxiv.', '34.' ).replace( 'xxxiii.', '33.' ).replace( 'xxxii.', '32.' ).replace( 'xxxi.', '31.' ).replace( 'xxx.', '30.' )
                            .replace( 'xxix.', '29.').replace( 'xxviii.', '28.').replace( 'xxvii.', '27.').replace( 'xxvi.', '26.').replace( 'xxv.', '25.').replace( 'xxiv.', '24.').replace( 'xxiii.', '23.').replace( 'xxii.', '22.').replace( 'xxi.', '21.').replace( 'xx.', '20.')
                            .replace( 'xix.', '19.' ).replace( 'xviii.', '18.' ).replace( 'xvii.', '17.' ).replace( 'xvi.', '16.' ).replace( 'xv.', '15.' ).replace( 'xiv.', '14.' ).replace( 'xiii.', '13.' ).replace( 'xii.', '12.' ).replace( 'xi.', '11.' ).replace( 'x.', '10.' )
                            .replace( 'ix.', '9.' ).replace( 'viii.', '8.' ).replace( 'vii.', '7.' ).replace( 'vi.', '6.' ).replace( 'iv.', '4.' ).replace( 'v.', '5.' ).replace( 'iii.', '3.' ).replace( 'ii.', '2.' ).replace( 'i.', '1.' )
                        )
    elif versionAbbreviation == 'KJB-1611':
        xrefLiveMiddle = xrefLiveMiddle.replace( 'A&s', 'Acts' )

    reStartIx, lastXBBB = 0, BBB
    for _safetyCount2 in range( 999 if segmentType=='book' else 99 ):
        if reStartIx>0: dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Now searching {refTuple} from {xrefLiveMiddle[reStartIx:]=}" )
        matchBCV = BCVRefRegEx.search( xrefLiveMiddle, reStartIx )
        matchBV = BVRefRegEx.search( xrefLiveMiddle, reStartIx )
        matchCV = CVRefRegEx.search( xrefLiveMiddle, reStartIx )
        if not matchBCV and not matchBV and not matchCV:
            break # neither one was found - all done here
        try: indexBCV = matchBCV.start()
        except AttributeError: indexBCV = 999_999
        try: indexBV = matchBV.start()
        except AttributeError: indexBV = 999_999
        try: indexCV = matchCV.start()
        except AttributeError: indexCV = 999_999
        firstIndex = min( indexBCV, indexBV, indexCV )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {refTuple} {xrefLiveMiddle=} {firstIndex=} {indexBCV=} {indexBV=} {indexCV=}" )
        assert firstIndex != 999_999

        xBBB = None
        if firstIndex == indexCV: # process matchCV
            match = matchCV # process matchCV
            xC, xV = match.groups()
            xBBB = lastXBBB
        else: # either matchBCV or matchCV
            # See if we can find a bookcode
            match = matchBCV if firstIndex==indexBCV else matchBV
            xB = match.group( 1 ).lstrip() # For books without a book number like 1 Cor, the BCV regex may capture an extra space before the book abbreviation
            if xB == 'Songs':
                xBBB = 'SNG'
            elif versionAbbreviation in ('KJB-1611','RV') and xB in ('and','c','ca'): # 'ca' stands for 'circa' = 'around'
                xBBB = lastXBBB # Same as last book
            elif versionAbbreviation=='KJB-1611' and xB in ('As','See','the','to','Dodo','Elishua','Vzziah'): # First one is a range, 2nd is in a footnote
                # print( f"{match=} {match.start()=} {match.end()=} {match.groups()=}" )
                reStartIx = match.end() if xB=='to' else match.start()+len(match.group( 1 ))
                continue # I think we can just ignore it here
            elif versionAbbreviation=='KJB-1611' and xB in ('Chap','Cha','chap','cha'):
                xBBB = BBB # This same book where the xref is located
            # elif versionAbbreviation=='KJB-1611' and xB in ('Verse','Vers'):
            #     xBBB = BBB # This same book where the xref is located
            #     print( f"{refTuple=} {BBB} {xB} {xC}:{xV} {firstIndex=} {indexBCV=} {indexBV=} {indexCV=}" )
            #     halt
            elif versionAbbreviation == 'KJB-1611':
                try: xBBB = myKJB1611XrefTable[xB]
                except KeyError:
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {versionAbbreviation} {BBB}  '{xB}'  wasn't in the table from '{xrefOriginalMiddle}'")
                    adjXB = ( xB # Fix KJB-1611 spellings -- what's Apoc/apoc and nnm ???
                            .replace( '1.','1 ' ).replace( '2.','2 ' ).replace( '3.','3 ' ).replace( '4.','4 ' ) # Should BOS handle this???
                            .replace( 'I.','1 ' )

                            .replace( 'Ie', 'Je' )
                            .replace( 'Io', 'Jo' )
                            )
                    xBBB = getBBBFromOETBookName( adjXB )
                if not xBBB:
                    logging.critical( f"Unable to liven cross-reference from {versionAbbreviation} {refTuple} for {xBBB=} from {xrefLiveMiddle=} from {xoText=} {xrefOriginalMiddle=}" )
            else: # not KJB-1611
                xBBB = getBBBFromOETBookName( xB )
            # We can leave this block of code without being successful finding xBBB -- it's checked below
        if firstIndex==indexBV and firstIndex!=indexBCV: # process matchBV (if it's not also a matchBCV)
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {refTuple} {xoText=} {xrefLiveMiddle=} {matchBV.groups()=}" )
            xCorV = match.group( 2 )
            if versionAbbreviation in ('KJB-1611','RV') and xB in ('Verse','verse','Vers','vers','Ver','ver','v','and'):
                xBBB, xV = BBB, xCorV # This same book where the xref is located
                try: xC = refTuple[1]
                except IndexError: # no chapter number given there -- use the xoText instead
                    xC = xoText.split( ':' )[0] if xoText and xoText.count(':')==1 else '?'
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {refTuple=} {xB=} {BBB} {xC}:{xV}" )
                assert xC.isdigit(), f"{versionAbbreviation} {refTuple=} {xB=} {BBB} {xC}:{xV} from {xoText=} {xrefOriginalMiddle=}"
            else: # Could be a single-chapter book
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Possible single-chapter book: {versionAbbreviation} {refTuple} {xB=}" )
                if not xBBB:
                    logging.critical( f"Unable to liven cross-reference from {versionAbbreviation} {refTuple} for {xBBB=} from {xB=} from {xrefLiveMiddle=} from {xoText=} {xrefOriginalMiddle=}" )
                try: singleChapterFlag = BibleOrgSysGlobals.loadedBibleBooksCodes.isSingleChapterBook( xBBB )
                except KeyError: singleChapterFlag = True # default to True
                if singleChapterFlag:
                    xC, xV = '1', xCorV
                else: # it could be a chapter reference (so we link to the first verse only)
                    # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Possible chapter reference: {versionAbbreviation} {refTuple} {xB=}" )
                    xC, xV = xCorV, '1'
        elif firstIndex != indexCV: # process matchBCV
            assert firstIndex == indexBCV
            # match = matchBCV
            # NOTE: This match also captures chapter ranges, e.g., it gets Lev 1:2, but also Lev 1–2
            xC, xV = match.group( 2 ), match.group( 3 )
            if '–' in match.group(): # For a chapter range, change our search to v1
                # print( f"                       Changed {xB} {xC}–{xV} to {xC}:1")
                xV = '1' # (rather than thinking the second chapter of the range is the verse number)
            # elif versionAbbreviation == 'KJB-1611':
            #     try: xBBB = myKJB1611XrefTable[xB]
            #     except KeyError:
            #         dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {versionAbbreviation} {BBB}  '{xB}'  wasn't in the table from '{xrefOriginalMiddle}'")
            #         adjXB = ( xB # Fix KJB-1611 spellings -- what's Apoc/apoc and nnm ???
            #                 .replace( '1.','1 ' ).replace( '2.','2 ' ).replace( '3.','3 ' ).replace( '4.','4 ' ) # Should BOS handle this???
            #                 .replace( 'I.','1 ' )

            #                 .replace( 'Ie', 'Je' )
            #                 .replace( 'Io', 'Jo' )
            #                 )
            #         xBBB = getBBBFromOETBookName( adjXB )
            #     if not xBBB:
            #         logging.critical( f"Unable to liven cross-reference from {versionAbbreviation} {refTuple} for {xBBB=} {xC=} {xV=} from {adjXB=} from {xrefOriginalMiddle=}" )
            #         # if adjXB not in ('Apoc','apoc','nnm'): halt # What are these???
            # else: # not KJB-1611
            #     xBBB = getBBBFromOETBookName( xB )
            #     if not xBBB:
            #         logging.critical( f"Unable to liven cross-reference from {versionAbbreviation} {refTuple} for {xBBB=} {xC=} {xV=} from {xB=} from {xrefOriginalMiddle=}" )
            # # if versionAbbreviation=='KJB-1611' and not xBBB: # still
            # #     print( f"  {versionAbbreviation} {xBBB=} {xC=} {xV=} from {xB=} from {xrefOriginalMiddle=}" )
        assert xBBB and xBBB not in ('SAM','CHR',), f"livenXRefField {fieldType} {versionAbbreviation} {refTuple} {xBBB=} from {xB=} from {xrefOriginalMiddle=}"
        lastXBBB = xBBB
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {versionAbbreviation} {xBBB} from {refTuple} {match.groups()=} from {xoText=} {xrefLiveMiddle=}" )
        assert xC.isdigit(), f"{versionAbbreviation} {refTuple} {xC=} {match.groups()}"
        assert xV.isdigit(), f"{versionAbbreviation} {refTuple} {xV=} {match.groups()}"
        if versionAbbreviation=='KJB-1611' and not xBBB:
            logging.critical( f"Unable to make {versionAbbreviation} {BBB} xref: {xBBB=} {xC=} {xV=} from {xrefLiveMiddle=} from {xoText=} {xrefOriginalMiddle=}" )
            reStartIx = match.end() # exact number of characters that we add (otherwise we get mistakes/overlaps)
            continue
        # Now check for a verse or chapter range and include them in our find
        matchInner = match.group()
        matchEnd = match.end()
        try:
            while xrefLiveMiddle[matchEnd] in '-–1234567890abc:': # includes en-dash for chapter ranges
                # print( f"        Stepping past '{xrefLiveMiddle[matchEnd]}'" )
                matchInner = f'{matchInner}{xrefLiveMiddle[matchEnd]}'
                matchEnd += 1
        except IndexError: # (can happen if xref inner doesn't end with a period)
            pass # Reached end of string

        if xBBB:
            # assert int(xC) <= BibleOrgSysGlobals.loadedBibleBooksCodes.getMaxChapters( xBBB ), f"Bad xref {xBBB} {match.groups()} from {versionAbbreviation} {refTuple} {segmentType}"
            if int(xC) > BibleOrgSysGlobals.loadedBibleBooksCodes.getMaxChapters( xBBB ):
                logging.critical( f"Not enough chapters in {xBBB} ({BibleOrgSysGlobals.loadedBibleBooksCodes.getMaxChapters(xBBB)}) for {match.groups()} from {versionAbbreviation} {refTuple} {segmentType=} {xoText=} {xrefOriginalMiddle=}" )
                reStartIx = match.end() # exact number of characters that we add (otherwise we get mistakes/overlaps)
                continue
        else:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"livenXRefField( {versionAbbreviation} {refTuple} '{segmentType}' from {xoText=} {xrefOriginalMiddle=} ) with {BBB=} {xBBB=} {lastXBBB=}" )
            logging.critical( f"Failed to find xref book from '{xB}' from '{xrefOriginalMiddle}' in {match.groups()} for {versionAbbreviation} {segmentType} {segmentType=} {refTuple}")
        if versionAbbreviation == 'OET-RV': # We want to link to the section page, (not the chapter page)
            sectionNumber = findSectionNumber( 'OET-RV', xBBB, xC, xV, state )
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml for {versionAbbreviation} {refTuple} '{segmentType}' findSectionNumber( 'OET-RV', {xBBB} {xC}:{xV} ) returned {sectionNumber}" )
            assert sectionNumber is not None, f"Bad OET-RV {refTuple} cross-reference: {xBBB} {xC}:{xV} from {xrefLiveMiddle=}"
            if not state.TEST_MODE:
                assert sectionNumber > 0, f"ZERO OET-RV {refTuple} cross-reference: {xBBB} {xC}:{xV} from {xrefLiveMiddle=}"
            # print( f"       {level=} {versionAbbreviation} {refTuple} {segmentType} {pathPrefix=}")
            adjPathPrefix = pathPrefix.replace('byC','bySec') if pathPrefix else '../bySec/'
            assert 'bySec' in adjPathPrefix, f"{pathPrefix=} {adjPathPrefix=}"
            inside = f'<a title="View {'cross ' if fieldType=='x' else ''}reference" href="{adjPathPrefix.replace('byC','bySec')}{xBBB}_S{sectionNumber}.htm#C{xC}V{xV}">{matchInner}</a>'
            xrefLiveMiddle = f'''{xrefLiveMiddle[:match.start()]}{inside}{xrefLiveMiddle[matchEnd:]}'''
        else: # not OET-RV -- link to the chapter page
            inside = f'<a title="View {'cross ' if fieldType=='x' else ''}reference" href="{pathPrefix}{xBBB}_C{xC}.htm#C{xC}V{xV}">{matchInner}</a>'
            xrefLiveMiddle = f'{xrefLiveMiddle[:match.start()]}{inside}{xrefLiveMiddle[matchEnd:]}'
        reStartIx = match.start() + len(inside) # exact number of characters that we add (otherwise we get mistakes/overlaps)
        # # NOTE: The above code can leave us pointing to a range, e.g., Deu 1:19-2:2 would leave us at the hyphen
        # while xrefLiveMiddle[reStartIx] in ' -123456789;.,abc':
        #     print( f"        Stepping past '{xrefLiveMiddle[reStartIx]}'" )
        #     reStartIx += 1 # Step past extra parts (like a range) so they don't get false thought to be another valid ref
    else:
        logging.critical( f"Inner xref loop needed to break for {versionAbbreviation} {segmentType} {segmentType=} {refTuple}" )
        inner_xr_loop_needed_to_break

    return xrefLiveMiddle
# end of usfm.livenXRefField function


# ROMAN_DICT = { 1000:'M', 900:'CM', 500:'D', 400:'CD', 100:'C', 90:'XC', 50:'L', 40:'XL', 10:'X', 9:'IX', 5:'V', 4:'IV', 1:'I' }
# We only use this for chapter numbers, so maximum is 151
ROMAN_DICT = { 100:'C', 90:'XC', 50:'L', 40:'XL', 10:'X', 9:'IX', 5:'V', 4:'IV', 1:'I' }
def toRomanNumerals( num:int|str ) -> str:
    """
    Adapted from https://stackoverflow.com/questions/28777219/basic-program-to-convert-integer-to-roman-numerals
    """
    if not isinstance(num, int): num = int( num )

    def roman_num(num):
        for r in ROMAN_DICT.keys():
            x, y = divmod(num, r)
            yield ROMAN_DICT[r] * x
            num -= (r * x)
            if num <= 0:
                break

    return ''.join([a for a in roman_num(num)])
# end of usfm.toRomanNumerals function


def briefDemo() -> None:

    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the usfm object

# end of usfm.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the usfm object
    pass

    # Demo the cross-references
    state = State()
    for testField in ( 'Exod. 17.5 and 20:9 &c.', 'Verse. 7', 'Verse.7' ):
        print( f"\n{testField=}" )
        result = livenXRefField( 'f', 'KJB-1611', ('GEN','1','1'), '', '', '1:1', testField, state )
        print( f"  {result=}" )
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
