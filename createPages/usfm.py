#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# usfm.py
#
# Module handling OpenBibleData USFM to HTML functions
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
Module handling usfm to html functions for OpenBibleData package.

convertVerseEntryListToHtml( level:str, versionAbbreviation:str, refTuple:tuple, segmentType:str,
                        contextList:list, markerList:list, basicOnly:bool=False ) -> str
_convertUSFMCharacterFormatting( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                    usfmField, basicOnly=False, state:State ) -> str
livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                                                        introHtml:str, state:State ) -> str
livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str,
                                                                        state:State ) -> str
livenXRefField( versionAbbreviation:str, refTuple:tuple, segmentType:str,
                    pathPrefix:str, xoText:str, xrefOriginalMiddle:str, state:State ) -> str
to_roman_numerals( num:int|str ) -> str

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
    2025-11-10 Fixed PSA d fields which caused chapter numbers to be displayed twice
    2025-12-01 Added text 'direct-object marker' to pop-up titles for untranslated DOM
    2026-03-13 Remove ⇔ symbol at beginning of verse (which indicates the verse text was reordered)
    2026-03-23 Added special handling for dictVerse segments (no xrefs or CV id fields)
    2026-05-09 Upgraded to bos_books_codes_py
    2026-05-27 Improved handling of 'nb' paragraphs
    2026-05-31 Adding background colouring for OET-RV PSA segments
    2026-06-29 Improved handling of 'mr' lines, plus removed extra space from processed footnote xt fields
    2026-06-30 In Psalms, display C before d field if it exists (rather than before v1)
    2026-07-07 Added OBI images and got USFM figures working
    2026-08-12 Improved handling of jmp links and of usfm pb lines
"""
import re
import unicodedata
import shutil
import logging
from os import makedirs
from pathlib import Path

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, dPrint, vPrint, rreplace, BOOKLIST_NT27
from usfm_markers_py import USFM_ALL_BIBLE_PARAGRAPH_MARKERS
import bos_books_codes_py
from openbibledata_rust import liven_introduction_links, liven_iors, to_roman_numerals, convert_usfm_character_formatting, liven_xref_field

from settings import State
from html import checkHtml
#from OETHandlers import getBBBFromOETBookName
from Bibles import getOpenBibleImages


LAST_MODIFIED_DATE = '2026-08-17' # by RJH
SHORT_PROGRAM_NAME = "usfm"
PROGRAM_NAME = "OpenBibleData USFM to HTML functions"
PROGRAM_VERSION = '1.1.5'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


BACKSLASH = '\\'
NEWLINE = '\n'
THIN_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
NON_BREAK_SPACE = ' ' # NBSP

MAX_FOOTNOTE_CHARS = 11_500 # 1,029 in FBV, 1,688 in BrTr, 10,426 in ClVg JOB!
MAX_NET_FOOTNOTE_CHARS = 18_000 # 17,145 in NET ECC

XREF_REGEX = re.compile( '\\\\x .+?\\\\x\\*' )
FOOTNOTE_REGEX = re.compile( '\\\\f .+?\\\\f\\*' )

SPAN_CLASS_REGEX = re.compile( '<span class=".+?">' )

FIG_SRC_REGEX = re.compile( 'src="([^"]+?)"' )
FIG_SIZE_REGEX = re.compile( 'size="([^"]+?)"' )
FIG_REF_REGEX = re.compile( 'ref="([^"]+?)"' )
FIG_ALT_REGEX = re.compile( 'alt="([^"]+?)"' )
FIG_LOC_REGEX = re.compile( 'loc="([^"]+?)"' )
FIG_COPY_REGEX = re.compile( 'copy="([^"]+?)"' )

SP_CLASS_DICT = {
    'The groom':'groom', 'The bride':'bride', 'Yerushalem’s young women':'women','Bride’s older brothers':'brothers',
    'Yirmeyah':'Yirmeyah', 'The people':'people',
    }


def convertVerseEntryListToHtml( level:int, versionAbbreviation:str, refTuple:tuple, segmentType:str, contextList:list, verseEntryList:list, basicOnly:bool, state:State ) -> str:
    """
    Loops through the given list of processed USFM lines (verseEntryList)
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

    fnPrint( DEBUGGING_THIS_MODULE, f"convertVerseEntryListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList} {verseEntryList} )" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertVerseEntryListToHtml( {versionAbbreviation} {refTuple} '{segmentType}' {contextList=} {len(verseEntryList)=} )" )
    assert segmentType in ('book','section','chapter','parallelVerse','interlinearVerse','dictVerse','relatedPassage','topicalPassage'), f"Unexpected {segmentType=}"
    BBB = refTuple[0] # Compulsory
    maxFootnoteChars = MAX_NET_FOOTNOTE_CHARS if versionAbbreviation=='NET' else MAX_FOOTNOTE_CHARS


    def _convertUSFMCharacterFormatting( versionAbbreviation:str, refTuple:tuple, segmentType:str, usfmField:str, basicOnly:bool, state:State ) -> str:
        """
        Handles character formatting inside USFM lines using Rust backend.

        This includes \\fig and \\jmp
        Automatically changes \\nd to Nomina Sacra for OET NT books
        Side-effect: in PSA, this function can alter backgroundColour variable in the surrounding context
        """
        nonlocal backgroundColour
        fnPrint( DEBUGGING_THIS_MODULE, f"_convertUSFMCharacterFormatting( {versionAbbreviation}, {refTuple}, {segmentType}, {usfmField}, {basicOnly=} )" )
        
        # Validation
        if '\\add <<' not in usfmField and '\\add ?<<' not in usfmField:
            assert '<<' not in usfmField, f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} {usfmField=}"
        for charMarker in BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers + ['untr','fig']:
            openCount, closeCount = usfmField.count( f'\\{charMarker} ' ), usfmField.count( f'\\{charMarker}*' )
            if openCount != closeCount:
                logging.critical( f"Mismatched USFM character markers: '{charMarker}' open={openCount} close={closeCount} from {versionAbbreviation} {refTuple} '{usfmField}'" )

        ourBBB = refTuple[0]
        
        # Prepare arguments for Rust function
        expanded_char_markers = list(BibleOrgSysGlobals.USFMAllExpandedCharacterMarkers) + ['untr']
        booklist_nt27 = list(BOOKLIST_NT27)
        is_net_version = (versionAbbreviation == 'NET')
        
        # Call Rust implementation
        result = convert_usfm_character_formatting(
            versionAbbreviation,
            ourBBB,
            segmentType,
            usfmField,
            basicOnly,
            expanded_char_markers,
            booklist_nt27,
            is_net_version
        )
        
        # Extract results
        html = result['html']
        if result['background_colour'] is not None:
            backgroundColour = result['background_colour']
        
        # Handle file copying for figures
        for src_path, dest_filename in result['files_to_copy']:
            try:
                figSrcPath = Path( src_path )
                if figSrcPath.is_file():
                    imagesDestinationFolder = state.DESTINATION_FOLDER.joinpath( 'images/' )
                    try: makedirs( imagesDestinationFolder )
                    except FileExistsError: pass
                    figDestinationFilepath = imagesDestinationFolder.joinpath( dest_filename )
                    if not figDestinationFilepath.is_file():
                        try:
                            shutil.copy2( figSrcPath, imagesDestinationFolder )
                            print( f"Fig: copied '{dest_filename}' from {figSrcPath} to {imagesDestinationFolder}" )
                        except FileNotFoundError:
                            logging.critical( f"Fig: unable to find '{src_path}' image" )
                else:
                    logging.critical( f"Fig: source path {figSrcPath} is not a file" )
            except Exception as e:
                logging.critical( f"Fig: error copying {src_path}: {e}" )
        
        # Validation checks
        if versionAbbreviation not in ('UST','ULT'):
            assert 'strong="' not in html, f"'{versionAbbreviation}' {refTuple} {segmentType=} {basicOnly=} {usfmField=}\n  html='{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
        if '\\ts\\*' in html:
            logging.critical( f"Removing ts marker in {versionAbbreviation} {refTuple} {segmentType} {basicOnly=}…")
            html = html.replace( '\\ts\\*', '' )
        if '\\f ' not in html and '\\x ' not in html:
            if (versionAbbreviation not in ('TCNT','TC-GNT') or 'INT' not in refTuple) \
            and (versionAbbreviation not in ('ULT','UST') \
                or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'JER' not in refTuple and 'DEU' not in refTuple and 'JOB' not in refTuple and 'SNG' not in refTuple)):
                assert '\\' not in html, f"{versionAbbreviation=} {refTuple=} {segmentType=} '{usfmField=}' {basicOnly=} '{html}'"
        if not checkHtml( f'_convertUSFMCharacterFormatting({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE and versionAbbreviation!='OEB':
                assert False, "We want to stop here"
        return html
    # end of usfm._convertUSFMCharacterFormatting


    # Start of main code for convertVerseEntryListToHtml function
    inMainDiv = inParagraph = inSection = inList = inListEntry = inTable = inTableRow = inSPdiv = None
    inRightDiv = False
    backgroundColour = None
    html = ''
    for marker in contextList:
        if marker == 's1':
            rest = '--unknown--'
            if not basicOnly:
                html = f'{html}<div class="section"><p class="{marker}">{rest}</p><!--section-->\n'
                inSection = 's1'
        elif marker == 'p':
            if not basicOnly:
                html = f'{html}<p class="{marker}">'
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
    is_single_chapter_book_py = bos_books_codes_py.is_single_chapter_book( BBB )

    cPrinted = True
    just_had_d = False
    for velIndex, entry in enumerate( verseEntryList ):
        marker = entry.getMarker()
        # print( f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} {velIndex}: {marker} {entry.getCleanText()} {inSection=}" )
        if marker=='nb' and segmentType=='chapter': # An independent chapter can start with 'nb', in which case the final entry in contextList should have the current paragraph marker
            if contextList[-1] in USFM_ALL_BIBLE_PARAGRAPH_MARKERS:
                marker = contextList[-1] # Put the current paragraph marker there to replace the 'nb' (not quite a perfect solution, but near enough)
                # NOTE: This will also work better when the end paragraph marker is reached (if it's in this chapter)

        # rest = entry.getOriginalText() if basicOnly and 'OET' not in versionAbbreviation else entry.getOriginalText() # getText() has notes removed but doesn't work with wordlink numbers in OET
        # The following line means we get all footnotes, etc.
        rest = entry.getFullText() # getAdjustedText() has notes removed but doesn't work with wordlink numbers in OET
        if rest:
            assert '\\nd \\nd ' not in rest, f"Unexpected doubled nd’s in verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {marker=} {rest=}"
            assert '\\nd*\\nd*' not in rest, f"Unexpected closing nd’s in verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {marker=} {rest=}"
            # Special handling for some versions
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
            and '\\x ' in rest: # Completely remove cross-references
                rest, xCount = XREF_REGEX.subn( '', rest )
                # print( f"Removed {xCount} cross-references from {refTuple} {rest=} now {xrest=}")
                # if xCount > 1: assert False, "We want to stop here"
                # rest = xrest
            if basicOnly and segmentType=='dictVerse' and '\\f ' in rest: # Completely remove footnotes
                rest, fCount = FOOTNOTE_REGEX.subn( '', rest )
                # print( f"Removed {fCount} footnotes from {refTuple} {rest=} now {xrest=}")
                # if fCount > 1: assert False, "We want to stop here"
                # rest = xrest
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{n}/{len(markerList)} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V}: {marker}={rest}" )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {inList=} {inListEntry=}" )
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getOriginalText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}" )

        # We try to put these in order of probability
        if marker == 'v~': # This has the actual verse text
            assert rest.count('\\add ')==rest.count('\\add*'), f"Bad add counts in {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} v~ line: {rest.count('\\add ')} != {rest.count('\\add*')}"
            if not rest:
                logging.error( f"Expected verse text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            elif versionAbbreviation=='OET-RV' and rest[0]=='⇔': # Reordered verse
                assert marker == 'v~' # Should only occur at the beginning of the verse
                rest = rest[1:] # Just delete the reordering marker -- it's completely irrelevant for display use (it's used for connecting words)
            else:
                assert '⇔' not in rest, f"Unexpected ⇔ char {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}" # Check for typos
            html = f'''{html}<span class="{versionAbbreviation}_{'chapterIntro' if V=='0' else 'verseTextChunk'}">{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>'''
        elif marker == 'v': # This is where we want the verse marker
            if inRightDiv:
                html = f'{html}</div><!--{inRightDiv}-->\n'
                inRightDiv = False
            V = rest.strip() # Play safe
            # We don't display the verse number below for verse 1 (after chapter number)
            # NOTE: For sections (which can include multiple chapters), have to take care not to get duplicate V{v} id attributes
            if segmentType not in ('parallelVerse','interlinearVerse') \
            or '-' in rest: # No need for verse numbers at all if we're only displaying one verse
                if cPrinted or segmentType in ('parallelVerse','interlinearVerse'):
                    cID = ''
                    cLink = ''
                else:
                    cID = f'<span id="C{C}"></span>'
                    cLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V1.htm#Top">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</a>'''
                    cPrinted = True
                if '-' in V: # it's a verse range
                    assert V[0].isdigit() and V[-1].isdigit(), f"Expected a verse number digit with {BBB} {C}:{V=} {rest=}"
                    assert ':' not in V # We don't handle chapter ranges here yet (and probably don't need to)
                    V1, V2 = V.split( '-' )
                    # We want both verse numbers to be searchable
                    # print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}\n{[ve for ve in verseEntryList]}" )
                    if int(V2) != int(V1)+1: # We don't handle 3+ verse reordering well yet
                        logging.warning( f" Not handling 3+ verse bridge well yet at {versionAbbreviation} {refTuple} {C}:{V}" )
                    if segmentType in ('parallelVerse','interlinearVerse'): # We just want the reader to be able to see the verse range
                        html = f'''{html}{"" if html.endswith(">") else " "}<span class="v">{rest}</span>{THIN_SPACE}'''
                    else: # it's in a section or book type view
                        vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V{V1}.htm#Top">{V1}</a>'''
                        idField1 = '' if segmentType=='dictVerse' else f' id="C{C}V{V1}"'
                        idField2 = '' if segmentType=='dictVerse' else f' id="C{C}V{V2}"'
                        html = f'{html}{"" if html.endswith(">") else " "}' \
                                + f'''{f"""{cID}<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}V1">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</span>""" if V1=='1' and not cPrinted else f"""<span class="v"{idField1}>{vLink}-</span>"""}''' \
                                + (f'<span id="V{V1}"></span><span id="V{V2}"></span>' if (segmentType in ('chapter','section','relatedPassage') or is_single_chapter_book_py) and f'id="V{V1}"' not in html and f'id="V{V2}"' not in html else '') \
                                + f'<span class="v"{idField2}>{V2}{NARROW_NON_BREAK_SPACE}</span>' \
                                + (rest if rest else '=◘=')
                else: # it's a simple verse number
                    if not V.isdigit():
                        logging.error( f"Expected a verse number digit at {versionAbbreviation} {refTuple} {C}:{V} {rest=}" )
                    vLink = f'''<a title="Go to verse in parallel view" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">{V}</a>'''
                    idField = '' if segmentType=='dictVerse' else f' id="C{C}V{V}"'
                    html = f'''{html}{'' if html.endswith('"p">') or html.endswith('—') or html.endswith('—</span>') else ' '}''' \
                            + (f'<span id="V{V}"></span>' if (segmentType in ('chapter','section','relatedPassage') or is_single_chapter_book_py) and f'id="V{V}"' not in html else '') \
                            + f'''{f"""{cID}<span class="{'cPsa' if BBB=='PSA' else 'c'}"{idField}>{cLink}{NARROW_NON_BREAK_SPACE}</span>""" if V=='1' and not just_had_d
                              else f"""<span class="v"{idField}>{vLink}{NARROW_NON_BREAK_SPACE}</span>"""}'''
                # html = f'{html} <span class="v" id="C{refTuple[1]}V{V}">{V}{NARROW_NON_BREAK_SPACE}</span>'
            just_had_d = False
            if versionAbbreviation == 'OET-RV' and segmentType in ('chapter','section','book','relatedPassage'):
                if obiHtml := getOpenBibleImages( level, segmentType, BBB, C, V, None, None, state.preloadedBibles['OET-RV'], state ):
                    html = f'{html}{obiHtml}'
                    if segmentType == 'chapter': state.chaptersWithImages[BBB].append( C )
        elif marker == '¬v': # We can ignore these end markers
            # Sections can cross chapters
            assert rest==V or segmentType=='section', f'''Why does {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} '¬v' have {rest=}\nfrom {[(entry.getMarker(),f"{'...' if entry.getMarker() == 'v~' else entry.getOriginalText()}") for entry in verseEntryList]}\nwith {[(entry.getMarker(),f"{'...' if entry.getMarker() == 'v~' else entry.getCleanText()}") for entry in verseEntryList]}\nand {[(entry.getMarker(),f"{'...' if entry.getMarker() == 'v~' else entry.getFullText()}") for entry in verseEntryList]}'''
        elif marker == 'v=': # The next marker should be a section heading, and this gives the verse number for the section start
            assert rest and rest[0].isdigit()
            # We also get this before the 's4' kingdom marker (but we don't have any use for that here)
            if velIndex==len(verseEntryList)-1 or verseEntryList[velIndex+1].getMarker() == 's4': continue # ignore this 'v='
            assert not inRightDiv, f'''Already in {inRightDiv=} with 'v=' followed by '{verseEntryList[velIndex+1].getMarker()}' at {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {rest=}\nwith {[(entry.getMarker(),f"{'...' if entry.getMarker() == 'v~' else entry.getCleanText()}") for entry in verseEntryList]}'''
            if versionAbbreviation != 'TCNT': # TODO: Rust code needs fixing
                assert not inParagraph, f'''Already in {inParagraph=} with 'v=' followed by '{verseEntryList[velIndex+1].getMarker()}' at {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {rest=}\nwith {[(entry.getMarker(),f"{'...' if entry.getMarker() == 'v~' else entry.getCleanText()}") for entry in verseEntryList]}'''
            # Note that this verse number can have a letter, e.g., '7b' if the next section starts in the middle of a verse
            V = rest.strip() # Play safe
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi',
                            'pi1','pi2', 'pc','pm','pmc','pmo','po','pr', 'qm1','qm2', 'qr', 'cls'):
            assert not rest, f"Unexpected rest {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {marker}={rest}"
            if inMainDiv: # this can happen in INT module
                html = f'{html}</div><!--{inMainDiv}-->'
                inMainDiv = None
            if inRightDiv:
                html = f'{html}</div><!--{inRightDiv}-->\n'
                inRightDiv = False
            if inParagraph:
                logging.warning( f"Already in paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                html = f'{html}</p><!--{inParagraph}-->\n'
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
        elif marker == '¬nb': # We should normally hit this one before the 'nb' because it should be at the end of the previous chapter
                              #  except that in the OET-LV, every chapter starts with a 'nb' marker (including chapter 1) and none of them are given end markers
            assert not rest
            assert versionAbbreviation != 'OET-LV'
            assert basicOnly or (inParagraph and inParagraph != '¬nb'), f"Have nb: {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inRightDiv=} {inParagraph=}"
        elif marker == 'nb': # This one will be closed at some point by the ORIGINAL paragraph marker (that crossed chapters)
                             #  except that the OET-LV has NO other paragraph markers
                             # An independent chapter can start with 'nb', in which case the final entry in contextList should have the current paragraph marker
            assert not rest, f"Unexpected rest {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {marker}={rest}"
            if versionAbbreviation != 'OET-LV': # In OET-LV each chapter starts with a 'nb' which is effectively a NOP
                # print( f"Have nb: {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inRightDiv=} {inParagraph=}" )
                markerList = [entry.getMarker() for entry in verseEntryList]
                # if len(markerList)>2 and markerList[-1]=='¬chapters' and markerList[-2]!='¬c': print( f"{markerList=}" )
                assert basicOnly or inParagraph or segmentType in ('chapter','section'), f"nb {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inParagraph=} {inRightDiv=} {inTable=} {inList=}{rest=} {[entry.getMarker() for entry in verseEntryList]} {contextList=}"
                assert not (inRightDiv or inTableRow or inTable or inList), f"nb {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inRightDiv=} {inTable=} {inList=}{rest=}"
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi',
                            '¬pi1','¬pi2', '¬pc','¬pm','¬pmc','¬pmo','¬po','¬pr', '¬qm1','¬qm2', '¬qr', '¬cls'):
            assert not rest
            if inParagraph and inParagraph != marker[1:]:
                logging.error( f"Closing wrong paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker=}" )
            if basicOnly: assert not inParagraph
            if not basicOnly and inParagraph:
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
        elif marker in ('s1','s2','s3','s4'):
            if not rest:
                logging.error( f"Expected heading text {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if inSPdiv:
                html = f'{html}</div><!--SP_{inSPdiv}-->\n'
                inSPdiv = None
            if inRightDiv:
                assert marker != 's1', f"Unexpected s1 inRightDiv {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=}\n{[m for m in verseEntryList]}"
                if versionAbbreviation not in ('OET','OET-RV') or marker!='s4':
                    # It mustn't be our "kingdom marker", e.g., 'Northern kingdom'
                    html = f'{html}</div><!--{inRightDiv}-->\n'
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
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
            else: # not in periph
                if marker == 's1':
                    if segmentType=='relatedPassage' and inParagraph: # Can be disjointed verses
                        html = f'{html}</p><!--{inParagraph}-->\n'
                        inParagraph = None
                    if inSection == 'section': # Shouldn't happen
                        halt
                        (logging.warning if segmentType.endswith('Verse') else logging.error)( f"Why wasn't previous s1 section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                        if not basicOnly:
                            html = f'{html}</div><!--section-->\n'
                        inSection = None
                    elif inSection: # seems we had a s2/3/4 that wasn't closed
                        logging.critical( f"Should not be in {versionAbbreviation} section '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=}" )
                        assert False, f"Should not be in {versionAbbreviation} section '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=}"
                    assert not inParagraph, f"Why are we getting s1 while still in a paragraph: {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest} {contextList=} {[ve for ve in verseEntryList]}"
                else: logging.warning( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    rest = rest.replace( ' / ', f'{NON_BREAK_SPACE}/ ' ) # Stop forward slash from starting next line in section boxes
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            # if BBB=='LUK' and C=='23' and V=='56':
                            #     print( f"\n\nLUKE 23:56 s1 {rest}" )
                            #     for nextEntry in verseEntryList[MLIndex+1:]: # Skip through next markers
                            #             nextMarker, nextText = nextEntry.getMarker(), nextEntry.getCleanText()
                            #             print( f"   {nextMarker} {nextText=}")
                            # # TODO: Check what happens if V is a verse range
                            # #   (Might need to add one to the end part, not the start part???)
                            # if segmentType in ('section','relatedPassage'):
                            #     # print( f"\n  {C=} {V=} {marker}='{rest}'")
                            #     if V is None:
                            #         for nextEntry in verseEntryList[MLIndex+1:]: # Skip through next markers
                            #             nextMarker = nextEntry.getMarker()
                            #             if nextMarker == 'v':
                            #                 nextV = nextEntry.getCleanText()
                            #                 break
                            #         else: failed_here
                            #     else: nextV = V
                            #     # if segmentType=='relatedPassage' and refTuple[0]=='JHN' and refTuple[1]=='1':
                            #     #     print( f"{nextV=}")
                            #     #     assert False, "We want to stop here"
                            # else: # book or chapter
                            #     # The following line fails if a section heading is in the middle of a verse
                            #     # WAS nextV = '1' if V is None else getSmallLeadingInt(V)+1 # Add one because usually the section heading is BEFORE the verse that it applies to
                            #     for nextEntry in verseEntryList[MLIndex+1:]: # Skip through next markers
                            #         nextMarker = nextEntry.getMarker()
                            #         # print( f"   {nextMarker} {nextEntry.getCleanText()=}")
                            #         if nextMarker == 'v':
                            #             nextV = nextEntry.getCleanText()
                            #             break
                            #         elif nextMarker == '¬v':
                            #             nextV = f'{V}b'
                            #             break
                            #     else: failed_here
                            # Just prove that we had no need to calculate the nextV
                            if V is None: V = '1'
                            # TODO: The following line fails for (some?) Psalms (e.g., Psa 25 chapter) because V is '0' but nextV was '1'
                            # assert nextV == V, f"Expected {nextV=} to be same as {V=} for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest} {contextList=} {[ve for ve in verseEntryList]}"
                            if ( segmentType == 'section' # Don't want a link to ourself
                            or '\\f' in rest ): # Would otherwise end up with an anchor embedded inside an anchor at Jhn 7:53 (unless we write more code)
                                html = f'''{html}<div class="s1"><div class="rightS1Box"><p class="{marker}"><span class="s1cv">{C}:{V}</span> {_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'''
                            else:
                                sectionNumber = findSectionNumber( 'OET-RV', BBB, C, V, state )
                                assert sectionNumber is not None, f"Bad OET-RV {refTuple} {BBB} {C}:{V} /s1 section reference: {rest=}"
                                html = f'''{html}<div class="{marker}"><div class="rightS1Box"><p class="{marker}"><span class="s1cv">{C}:{V}</span> <a title="Go to section view" href="{'../'*level}OET/bySec/{BBB}_S{sectionNumber}.htm#C{C}V{V}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</a></p><!--{marker}-->\n'''
                            inRightDiv = 'rightS1Box'
                        else: # not OET
                            html = f'{html}<div class="{marker}"><p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                        inSection = marker
                elif marker == 's2':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="rightS2Box"><p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                            inRightDiv = 'rightS2Box'
                        else:
                            html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                else: # for s3/s4 we add a heading, but don't consider it a section division
                    if not basicOnly:
                        if marker=='s4' and versionAbbreviation in ('OET','OET-RV'): # and 'KINGDOM' in rest.upper(): # it's our kingdom marker
                            additionalClassName = rest.replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )
                            html = rreplace( html, 'div class="section"', f'''div class="section {additionalClassName}"''', 1 )
                            guts = _convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )
                            guts = f'''<a title="Go to {rest.replace('king','King').replace('land','Land')} information page" href="{'../'*level}ref/Kingdoms/{additionalClassName}.htm">{guts}</a>'''
                            html = f'''{html}<p class="{marker} {additionalClassName}">{guts}</p><!--{marker}-->\n'''
                        else: html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
        elif marker in ('¬s1','¬s2','¬s3','¬s4'):
            assert not rest, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=} {rest=}"
            if 'OET' not in versionAbbreviation and not basicOnly and inParagraph:
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if marker == '¬s1' and segmentType not in ('chapter','parallelVerse','interlinearVerse'):
                if DEBUGGING_THIS_MODULE:
                    print( f"Closed section {contextList=} ({len(verseEntryList)})" )
                    for vvv, verseEntry in enumerate( verseEntryList ):
                        if vvv < velIndex-4: continue
                        print( f"{'-> ' if vvv==velIndex else '   '}{vvv}/ {repr(verseEntry)}" )
                        if vvv > velIndex+5: print( "   ..." ); break
                assert inSection=='s1' and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
                assert inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=}"
            if basicOnly:
                assert inSection is None # for end of s2,s3,s4 sections
            elif inSection=='s1':
                # if inRightDiv: # shouldn't really happen, but just in case
                #     html = f'{html}</div><!--{inRightDiv}-->\n'
                #     inRightDiv = False
                #     assert False, "We want to stop here" # Why were we in a rightDiv
                html = f'{html}</div><!--{inSection}-->\n'
                inSection = None
        elif marker == 'r': # usually following a \\s1 (but maybe a \\s2) -- either way there could be a \\rem in between
            # The following is not true for the ULT at least (e.g., see ULT Gen 5:1)
            # assert rest[0]=='(' and rest[-1]==')', f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            assert not inParagraph
            assert not inTable
            assert '\\' not in rest
            if not basicOnly:
                if segmentType != 'relatedPassage': # because these can jump in anywhere
                    assert inSection, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                    if 'OET' in versionAbbreviation:
                        assert inRightDiv, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest} prevEntry={verseEntryList[velIndex-1]} {html[-50:]}"
                html = f'{html}<p class="{marker}">{livenSectionReferences( versionAbbreviation, refTuple, segmentType, rest, state )}</p><!--{marker}-->\n'
                assert '()' not in html, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker=} {rest=}"
        elif marker == 'c':
            # if segmentType == 'chapter':
            C, V = rest.strip(), '0' # Play safe
            # html = f'{html}<span class="{marker}" id="C{C}">{C}{NARROW_NON_BREAK_SPACE}</span>'
            # numChapters += 1
            cPrinted = False
            backgroundColour = None
        elif marker == 'c#':
            assert rest and rest.isdigit()
            # Below is not necessarily true -- fails on OET-RV chapter basicOnly=False ('PSA', '1') 1:0 inSection='s1' inParagraph='p' c#=1
            # if len(refTuple)>1 and refTuple[1] != '-1':
            #     assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"

            # if state.TEST_MODE_FLAG and versionAbbreviation != 'SR-GNT':
            #     html = f'{html}<span class="{'cPsa' if BBB=='PSA' else 'c'}">C###{to_roman_numerals(rest) if versionAbbreviation=='KJB-1611' else rest}</span>{NARROW_NON_BREAK_SPACE}'
        elif marker in ('mt1','mt2','mt3','mt4'):
            assert rest
            if versionAbbreviation == 'KJB-1611':
                rest = rest.replace( '   ', ' &nbsp; ' ) # We sometimes have three spaces which html normally loses, so try to prevent it
            if not inMainDiv:
                inMainDiv = 'bookHeader'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection != 'periph':
                if refTuple[0] == 'JOB' and inSection=='section' and inParagraph=='q1': # TODO: Fix something for OET-LV
                    html = f'{html}</q1></div><!--section-->\n'
                    inSection = inParagraph = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
        elif marker in ('imt1','imt2','imt3','imt4'):
            assert rest
            if inMainDiv == 'bookHeader':
                    html = f'{html}</div><!--{inMainDiv}-->'
                    inMainDiv = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection != 'periph':
                if refTuple[0] == 'JOB' and inSection=='section' and inParagraph=='q1': # TODO: Fix something for OET-LV
                    html = f'{html}</q1></div><!--section-->\n'
                    inSection = inParagraph = None
                assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
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
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if not inMainDiv:
                inMainDiv = 'bookIntro'
                html = f'{html}<div class="{inMainDiv}">'
            if inSection == 'periph': # We don't put s1 in sections here
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
            else: # not in periph
                if marker == 's1':
                    if inSection == 's1': # Shouldn't happen
                        (logging.warning if segmentType.endswith('Verse') else logging.error)( f"Why wasn't previous section closed??? {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                        if not basicOnly:
                            html = f'{html}</div><!--s1-->\n'
                        inSection = None
                    elif inSection: # seems we had a s2/3/4 that wasn't closed
                        should_not_be_in_section
                    assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
                else: logging.warning( f"Section heading levels might not work yet: {versionAbbreviation} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                if marker == 's1':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="section"><div class="rightS1Box"><p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                            inRightDiv = 'rightS1Box'
                        else:
                            html = f'{html}<div class="section"><p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                    inSection = 's1'
                elif marker == 's2':
                    if not basicOnly:
                        if 'OET' in versionAbbreviation:
                            html = f'{html}<div class="rightS2Box"><p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                            inRightDiv = 'rightS2Box'
                        else:
                            html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
                else: # for s3/s4 we add a heading, but don't consider it a section division
                    if not basicOnly:
                        html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
        # We also treat the id field exactly like a rem field
        elif marker in ('rem','id'): # rem's can sort of be anywhere!
            assert rest
            rest = rest.replace( "Open English Translation", "<em>Open English Translation</em>" )
            if versionAbbreviation=='OEB': rest = rest.replace( '->', '→' ) # In the book introductions '-&gt;'
            if rest.startswith( '/' ):
                if inRightDiv:
                    assert not inParagraph
                    given_marker = rest[1:].split( ' ', 1 )[0]
                    assert given_marker in ('s1','s2','s3','r','d'), f"Unexpected inRightDiv REM {given_marker=} text for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
                    # NOTE: the following lines were disabled 23Aug2023
                    # marker = f"extra_{given_marker}" # Sets the html <p> class below
                    # rest = rest[len(given_marker)+2:] # Drop the '/marker ' from the displayed portion
                    # if not basicOnly:
                    #     for sectionChunk in rest.split( '; ' ):
                    #         html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, sectionChunk, basicOnly, state )}</p><!--{marker}-->\n'
                else: # it's probably a section marker added at a different spot
                    given_marker = rest[1:].split( ' ', 1 )[0]
                    assert given_marker in ('s1','s2','s3','r','d','qa'), f"Unexpected REM {given_marker=} text for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
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
                    #         html = f'{html}</p><!--{inParagraph}-->\n'
                    #         inParagraph = None
                    #     if not basicOnly:
                    #         for sectionChunk in rest.split( '; ' ):
                    #             html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, sectionChunk, basicOnly, state )}</p><!--{marker}-->\n'
                    # else:
                    #     print( f"{BBB} {C}:{V} {inParagraph=} {nextMarker=} has UNUSED INFLOW ALTERNATIVE {given_marker}={rest}")
            elif rest.startswith( 'was /' ): # That's how we comment out USFM lines
                assert not inRightDiv
            else:
                assert not inRightDiv
                if inParagraph:
                    html = f'{html}<span class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>\n'
                elif not basicOnly:
                    html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'

        elif marker == 'd': # These are canonical so MUST be included
            if not rest:
                logging.error( f"Source problem for {versionAbbreviation}: Expected 'd' field text {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=}" )
            if inRightDiv:
                html = f'{html}</div><!--{inRightDiv}-->\n'
                inRightDiv = False
            if inParagraph:
                logging.error( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if basicOnly: # In basicOnly mode, we put /d paragraphs in a SPAN, not in a PARAGRAPH (like we do further below)
                html = f'{html}<span class="d">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>\n'
                assert checkHtml( f'\\d at convertVerseEntryListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True )
            else: # not basicOnly
                if cPrinted or segmentType in ('parallelVerse','interlinearVerse'):
                    cBit = ''
                else: # We need to display the chapter number here
                    cBit = f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</span> ''' \
                        if segmentType == 'chapter' else \
                            f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</a></span> '''
                    cPrinted = True
                html = f'{html}<p class="d">{cBit}{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--d-->\n'
            just_had_d = True

        # The following should all have their own data and get converted to a simple <p class="xx">…</p> field
        elif marker in ('sr', 'cl', 'sp', 'cp', 'qa','qc','qd'):
            if not rest:
                logging.error( f"Source problem for {versionAbbreviation}: Expected '{marker}' field text {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=}" )
            if inRightDiv:
                html = f'{html}</div><!--{inRightDiv}-->\n'
                inRightDiv = False
            if inParagraph:
                logging.error( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
                assert not basicOnly
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if marker == 'cl' and not basicOnly:
                if segmentType == 'chapter':
                    html = f'{html}<p class="cl" id="C{C}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--cl-->\n'
                else: # probably whole document/book, so make a chapter link
                    html = f'{html}<p class="cl" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</a></p><!--cl-->\n'
                cPrinted = True
            elif not basicOnly:
                if cPrinted or marker == 'd':
                    cBit = ''
                else:
                    cBit = f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</span> ''' \
                        if segmentType == 'chapter' else \
                            f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</a></span> '''
                    cPrinted = True
                if versionAbbreviation=='OET-RV' and marker=='sp':
                    assert BBB == 'SNG' or BBB == 'JER' # Latter is experimental
                    if inSPdiv:
                        html = f'{html}</div><!--SP_{inSPdiv}-->\n'
                    # print( f"sp {rest=} from {markerList=}")
                    # for eeee, entry in enumerate( markerList ):
                    #     print( f"  {eeee} {entry=}" )
                    spClass = SP_CLASS_DICT[rest]
                    # except KeyError:
                    #     logging.critical( f"No SP (speaker) dict entry for {rest=} {versionAbbreviation} {refTuple} {segmentType}" )
                    #     spClass = 'None'
                    html = f'{html}<div class={spClass}>'
                    inSPdiv = spClass
                html = f'{html}<p class="{marker}">{cBit}{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'

        elif marker in ('b','ib'):
            assert not rest
            html = f'{html}<br>'
        elif marker == 'pb': # page-break
            assert not rest
            html = f'{html}<br><!--Should be PAGE BREAK-->' # TODO: How should we be handling this???

        # Handle lists
        elif marker in ('list','ilist'):
            # NOTE: BibleOrgSys only creates one list/¬list pair, even if it contains embedded li2 entries
            #   so we have to handle that
            assert not rest
            assert not inList, f"inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            if DEBUGGING_THIS_MODULE:
                print( f"Have '(i)list' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                print( f"Opened list {contextList=} ({len(verseEntryList)})" )
                for vvv, verseEntry in enumerate( verseEntryList ):
                    if vvv < velIndex-4: continue
                    print( f"{'-> ' if vvv==velIndex else '   '}{vvv}/ {repr(verseEntry)}" )
                    if vvv > velIndex+5: print( "   ..." ); break
            if segmentType != 'parallelVerse':
                html = f'{html}<ul>\n'
                inList = 'ul_1'
        elif marker in ('¬list','¬ilist'):
            assert not rest
            if not basicOnly and not inList:
                logging.warning( f"Not inList A {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            if DEBUGGING_THIS_MODULE:
                print( f"Ended '(i)list' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                print( f"Ended list {contextList=} ({len(verseEntryList)})" )
                for vvv, verseEntry in enumerate( verseEntryList ):
                    if vvv < velIndex-4: continue
                    print( f"{'-> ' if vvv==velIndex else '   '}{vvv}/ {repr(verseEntry)}" )
                    if vvv > velIndex+5: print( "   ..." ); break
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
        elif marker in ('li1','li2','li3','li4', 'ili1','ili2'):
            markerListLevel = int( marker[-1] )
            assert 1 <= markerListLevel <= 4
            currentListLevel = 0 if inList is None else int( inList[-1] )
            assert 0 <= currentListLevel <= 4
            if basicOnly:
                # We only do it with a span (because a list couldn't go inside a paragraph anyway, and most snippets end up put inside paragraphs)
                html = f'''{html}{'<br>' if html else ''}{'&nbsp;'*markerListLevel}<span class="{marker}">•{' ' if markerListLevel==1 else ' '}{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</span>'''
            else: # not basic only
                if DEBUGGING_THIS_MODULE:
                    print( f"Have 'lix' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {markerListLevel=} {currentListLevel=} {marker}={rest}" )
                    print( f"Opened list entry {contextList=} ({len(verseEntryList)})" )
                    for vvv, verseEntry in enumerate( verseEntryList ):
                        if vvv < velIndex-4: continue
                        print( f"{'-> ' if vvv==velIndex else '   '}{vvv}/ {repr(verseEntry)}" )
                        if vvv > velIndex+5: print( "   ..." ); break
                if markerListLevel > currentListLevel:
                    if DEBUGGING_THIS_MODULE:
                        print( f"Not inList B {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    # if markerListLevel == currentListLevel + 1: # it's one level up
                    #     if markerListLevel > 1:
                    #         # The following code seems wrong
                    #         # assert not inListEntry, f"Not inList B2 {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {markerListLevel=} {currentListLevel=} {marker}={rest}"
                    #         # if html.endswith( '</li>\n' ):
                    #         #     html = f'{html[:-6]}\n' # Open the last li entry back up
                    #         #     inListEntry = True
                    # else: # it's more than one level up
                    #     assert markerListLevel > currentListLevel + 1
                    #     if markerListLevel > 1:
                    #         assert not inListEntry
                    #         if html.endswith( '</li>\n' ):
                    #             html = f'{html[:-6]}\n' # Open the last li entry back up
                    #             inListEntry = True
                    #     currentListLevel += 1
                    #     while html.endswith('<br>') or html.endswith('\n'):
                    #         if html.endswith('<br>'): html = html[:-4]
                    #         if html.endswith('\n'): html = html[:-1]
                    #     html = f"{html}\n{' '*currentListLevel}<ul>\n"
                    # while html.endswith('<br>') or html.endswith('\n'):
                    #     if html.endswith('<br>'): html = html[:-4]
                    #     if html.endswith('\n'): html = html[:-1]
                    # assert not inListEntry # Otherwise the nesting markers must have been wrong # Not true: li2 can be inside li1
                    # if inListEntry:
                    #     assert inListEntry.endswith( str(currentListLevel) ), f"{inListEntry=} {currentListLevel=} {inList=} {markerListLevel=}"
                    #     html = f'{html}</li>\n' # No, this list is embedded inside the other list entry
                    #     inListEntry = None
                    html = f"{html}\n{' '*(markerListLevel-1)}<ul>\n"
                    inList = f'ul_{currentListLevel+1}'
                elif markerListLevel < currentListLevel:
                    if markerListLevel < currentListLevel - 1: # it's more than one level down
                        html = f'{html}{' '*(currentListLevel-1)}</ul>\n'
                        currentListLevel -= 1
                    assert markerListLevel == currentListLevel - 1, f"{markerListLevel=} {currentListLevel=} {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}"
                    logging.warning( f"Not inList C {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    html = f'{html}{' '*(currentListLevel-1)}</ul>\n'
                    inList = f'ul_{currentListLevel-1}'
                if isinstance( inListEntry, str ):
                    logging.warning( f"already inListEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker}={rest}" )
                    html = f'{html}</li>\n'
                    inListEntry = None
                html = f"{html}{' '*markerListLevel}<li>{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}"
                inListEntry = marker
        elif marker in ('¬li1','¬li2','¬li3','¬li4', '¬ili1','¬ili2'):
            assert not rest
            markerListLevel = int( marker[-1] )
            assert 1 <= markerListLevel <= 4
            currentListLevel = 0 if inList is None else int( inList[-1] )
            assert 0 <= currentListLevel <= 4
            # Related passages can jump right into the middle of things
            if not basicOnly and segmentType!='relatedPassage' and versionAbbreviation not in ('BSB','MSB','LEB'): # These ones from spreadsheets are too difficult
                assert inList, f"Unexpected list close marker @ {velIndex=} when not inList {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}\nfrom {verseEntryList=}"
                # assert inListEntry == marker[1:], f"Unexpected list close marker @ {velIndex=} when not inListEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            if DEBUGGING_THIS_MODULE:
                print( f"Have '¬lix' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {markerListLevel=} {currentListLevel=} {marker}={rest}" )
                print( f"Closed list entry {contextList=} ({len(verseEntryList)})" )
                for vvv, verseEntry in enumerate( verseEntryList ):
                    if vvv < velIndex-4: continue
                    print( f"{'-> ' if vvv==velIndex else '   '}{vvv}/ {repr(verseEntry)}" )
                    if vvv > velIndex+5: print( "   ..." ); break
            if inListEntry:
                html = f'{html}</li>\n'
                inListEntry = None
            elif inList in ('ul_2', 'ul_3'): # Can happen when we get ¬li2 followed immediately by ¬li1
                html = f'{html}</ul>\n'
                inList = f'ul_{int(inList[-1]) - 1}'

        # Handle tables
        elif marker == 'tr':
            assert not inList and not inListEntry, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
            if not inTable:
                if inParagraph:
                    html = f'{html}</p><!--{inParagraph}-->\n'
                    inParagraph = None
                html = f'{html}<table>'
                inTable = 'table'
            assert not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=} {rest=}"
            if inTableRow:
                html = f'{html}</tr>\n'
                inTableRow = None
            # print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} TR {rest=}" )
            if rest and rest.strip():
                html = f'{html}<tr>{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}'
            else:
                html = f'{html}<tr>'
                inTableRow = 'tr'

        elif marker in ('tc1','tc2','tc3','tc4'):
            halt # Shouldn't happen because these are 'character' markers
            assert not inParagraph and not inList and not inListEntry and inTable and inTableRow, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {inTable=} {inTableRow=} {marker=} {rest=}"
            print( f"Table column {marker} in {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {inTable=} {inTableRow=} {rest=}" )
            assert False, "We want to stop here"

        elif segmentType=='chapter' and marker in ('¬c','¬chapters'): # Just do some finishing off at the end of our chapter
            if inSection=='s1' and marker == '¬c':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished chapter inside {inSection} section" )
                if not basicOnly:
                    html = f'{html}</div><!--{inSection}-->\n'
                inSection = None
            elif inSection=='s1' and marker == '¬chapters':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished book inside {inSection} section" )
                if not basicOnly:
                    html = f'{html}</div><!--{inSection}-->\n'
                inSection = None
            if inParagraph and marker == '¬c':
                logging.warning( f"{versionAbbreviation} {refTuple} Finished chapter inside {inParagraph} paragraph" )
                # if not basicOnly:
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"

        elif marker in ('ms1','ms2','ms3','ms4'):
            if inParagraph:
                logging.error( f"Why still in paragraph {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if inSection:
                logging.error( f"Why still in section {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {marker}={rest}" )
                html = f'{html}</div><!--{inSection}-->\n'
                inSection = None
            # if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
            #     html = '{html}</q1></div>\n'
            #     inSection = inParagraph = None
            # assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                # NOTE: We don't treat it like a large section (which it is), but simply as a heading
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
        elif marker== 'mr':
            if not rest:
                logging.error( f"Source problem for {versionAbbreviation}: Expected field text {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}" )
            assert last_marker=='ms1' or 'OET' not in versionAbbreviation, f"Have 'mr' {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {last_marker=}"
            assert not inRightDiv and not inParagraph and not inSection
            # if inRightDiv:
            #     html = f'{html}</div><!--{inRightDiv}-->\n'
            #     inRightDiv = False
            # if inParagraph:
            #     logging.error( f"Unexpected inParagraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}" )
            #     assert not basicOnly
            #     html = f'{html}</p><!--{inParagraph}-->\n'
            #     inParagraph = None
            if not basicOnly:
                html = f'{html}<p class="{marker}">{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
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
            html = f'{html}{NARROW_NON_BREAK_SPACE}{_convertUSFMCharacterFormatting(versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}{NARROW_NON_BREAK_SPACE}'
        # The following should all have their own data and get converted to a simple <p>…</p> field
        elif marker in ('ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3', 'io1','io2','io3','io4'):
            assert rest, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}='{rest}'"
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            introHtml = _convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )
            if marker in ('io1','io2','io3','io4'):
                introHtml = livenIORs( versionAbbreviation, refTuple, segmentType, introHtml, state )
            else:
                introHtml = liven_introduction_links( versionAbbreviation, refTuple, segmentType, introHtml, state )
            html = f'{html}<p class="{marker}">{introHtml}</p><!--{marker}-->\n'
        elif marker == 'iot':
            assert rest, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}='{rest}'"
            assert not inSection and not inParagraph, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            html = f'{html}<div class="{marker}"><p class="{marker}">{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{marker}-->\n'
            # inSection = 'iot'
        elif marker == '¬iot':
            assert not rest
            assert not inParagraph and not inSection, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {marker}={rest}"
            # if inSection == 'iot':
            html = f'{html}</div><!--iot-->\n'
            # else: unexpected_section
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
                    cBit = f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</span> ''' \
                        if segmentType == 'chapter' else \
                            f'''<span class="{'cPsa' if BBB=='PSA' else 'c'}" id="C{C}"><a title="View single {'Psalm' if BBB=='PSA' else 'chapter'}" href="../byC/{BBB}_C{C}.htm#Top">{to_roman_numerals(C) if versionAbbreviation=='KJB-1611' else C}</a></span> '''
                    cPrinted = True
                html = f'''{html}<p class="{versionAbbreviation}_chapterIntro">{cBit}{_convertUSFMCharacterFormatting( versionAbbreviation, refTuple, segmentType, rest, basicOnly, state )}</p><!--{versionAbbreviation}_chapterIntro-->\n'''
        elif marker in ('periph',):
            assert rest
            assert not basicOnly
            if inParagraph:
                html = f'{html}</p><!--{inParagraph}-->\n'
                inParagraph = None
            if inSection == 'periph':
                html = f'{html}</div><!--{inSection}-->\n'
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
                assert segmentType not in ('parallelVerse','interlinearVerse'), f"{versionAbbreviation} {segmentType=} {refTuple} {C}:{V} {verseEntryList=}"
                assert not basicOnly
            if inMainDiv == 'bookHeader':
                html = f'{html}</div><!--{inMainDiv}-->'
                inMainDiv = None
            assert not inMainDiv
            assert not inTable and not inList
            if inParagraph:
                html = f'{html}</p><!--{inParagraph}-->\n'
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
        elif marker == 'pb': # page-break
            assert not rest
            html = f'{html}<br><!--Should be PAGE BREAK-->' # TODO: How should we be handling this???
        elif marker not in ('usfm','ide', 'sts',
                            'h', 'toc1','toc2','toc3', 'toca1','toca2','toca3', '¬is1', '¬headers',
                            'cl¤', '¬c', '¬chapters'): # We can ignore all of these -- 'c#' now handled above
            if versionAbbreviation in ('ULT','UST'):
            # Can't list faulty books for uW stuff because there's too many errors keep popping up
            # and ('ACT' in refTuple or 'PSA' in refTuple or 'KI2' in refTuple): # Bad USFM encoding at UST Act 26:29-30
                logging.warning( f"Unexpected {versionAbbreviation} '{marker}' marker at {segmentType} {basicOnly=} {refTuple} {C}:{V} {rest=}" )
            else:
                raise Exception( f"Unexpected '{marker}' marker {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {rest=}" )
        if '\\f ' not in html and '\\x ' not in html: # they're handled down below
            if '\\' in html:
                (logging.warning if versionAbbreviation in ('ULT','UST') else logging.error)( f"Left-over backslash in {versionAbbreviation} '{segmentType}' {basicOnly=} {refTuple} {C}:{V} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'" )
                if versionAbbreviation not in ('ULT','UST'):
                # or ('GEN' not in refTuple and 'MAT' not in refTuple and 'PSA' not in refTuple and 'ISA' not in refTuple and 'JER' not in refTuple and 'DEU' not in refTuple and 'JOB' not in refTuple and 'SNG' not in refTuple): # ULT Gen 14:21, ISA and UST MAT has an encoding fault in 12:20 14Feb2023
                    raise Exception( f"Left-over backslash {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} '{html}'\nfrom {[ve for ve in verseEntryList]}" )
        last_marker = marker

    # Check for left-over unclosed segments
    logger = logging.error if segmentType=='book' else logging.warning
    if inParagraph:
        if not basicOnly:
            logger( f"convertVerseEntryListToHtml final unclosed paragraph {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</p><!--{inParagraph}-->\n'
    if inTableRow:
        assert inTable
        html = f'{html}</tr>\n'
    if inTable:
        if not basicOnly:
            logger( f"convertVerseEntryListToHtml final unclosed table {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</table>\n'
    if inListEntry:
        if not basicOnly:
            logger( f"convertVerseEntryListToHtml final unclosed listEntry {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        html = f'{html}</li>\n'
    if inList:
        if not basicOnly:
            logger( f"convertVerseEntryListToHtml final unclosed list {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
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
            logger( f"convertVerseEntryListToHtml final unclosed '{inSection}' section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
        if inRightDiv:
            html = f'{html}</div><!--{inRightDiv}-->\n'
            inRightDiv = False
        html = f"{html}</div><!--{inSection}-->\n"
    elif inSection: missing_some_code_here
    if inMainDiv:
            logger( f"convertVerseEntryListToHtml final unclosed '{inMainDiv}' main section {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {C}:{V} {inSection=} {inParagraph=} {inList=} {inListEntry=} last {marker=}" )
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
            fFirstMarkerLength = 3 if html[firstContentIx+3]==' ' else 4 if html[firstContentIx+4]==' ' else 2 if html[firstContentIx+2]==' ' else 99
            fFirstMarker = html[firstContentIx+1:firstContentIx+fFirstMarkerLength]
            assert fFirstMarker != '\\f*'
            assert fFirstMarker in ('ft','fq','fk','fl','fw','fp','fv', 'fn') if versionAbbreviation=='NET' else ('ft','fq','fk','fl','fw','fp','fv'), \
                f"Unexpected {fFirstMarker=} in {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesCount=} {html[fStartIx:fStartIx+2*maxFootnoteChars]}"
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
                        fNoteXTrest = fnoteMiddle[internalStartIx+len(fMarker)+2:] # Go past the space that's part of the marker
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
                else: raise TypeError( f"Unexpected character in footnote: {versionAbbreviation} {refTuple} {segmentType} {basicOnly=} {fnoteMiddle=} from {html=}" )
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

        # Can't allow HTML formatting into the footnote popup (title) text
        sanitisedFnoteMiddle = fnoteMiddle
        if versionAbbreviation == 'OET-LV':
            if ' note--fnCOLON--' not in sanitisedFnoteMiddle and 'Note--fnCOLON--' not in sanitisedFnoteMiddle:
                sanitisedFnoteMiddle = f'Note--fnCOLON-- {sanitisedFnoteMiddle}'
        else: # not OET-LV
            if ' note:' not in sanitisedFnoteMiddle and 'Note:' not in sanitisedFnoteMiddle:
                sanitisedFnoteMiddle = f'Note: {sanitisedFnoteMiddle}'
        if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
            sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '</span>', '' )
            sanitisedFnoteMiddle = SPAN_CLASS_REGEX.sub( '', sanitisedFnoteMiddle )
            for charMarker in ('em','i','b', 'sup','sub'): # These are HTML markers
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( f'<{charMarker}>', '' ).replace( f'</{charMarker}>', '' )
            # if versionAbbreviation == 'OET-LV': # then we don't want equals or underlines in the sanitised footnote to get converted into spans later
            #     sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace('_', '--fnUNDERLINE--').replace('=', '--fnEQUAL--') # So we protect them -- gets fixed in do_OET_LV_HTMLcustomisations() in html.py
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {refTuple} {sanitisedFnoteMiddle=}" )
            # if '_' in sanitisedFnoteMiddle or 'UNDERLINE' in sanitisedFnoteMiddle \
            # or '=' in sanitisedFnoteMiddle or 'EQUAL' in sanitisedFnoteMiddle: assert False, "We want to stop here"
            if '"' in sanitisedFnoteMiddle or '<' in sanitisedFnoteMiddle or '>' in sanitisedFnoteMiddle:
                logging.warning( f"Left-over HTML chars in {versionAbbreviation} {refTuple} {sanitisedFnoteMiddle=}" )
                sanitisedFnoteMiddle = sanitisedFnoteMiddle.replace( '"', '&quot;' ).replace( '<', '&lt;' ).replace( '>', '&gt;' )
                # if versionAbbreviation != 'LEB': # LEB MRK has sanitisedFnoteMiddle='Note: A quotation from Isa 40:3|link-href="None"'
                #     assert False, "We want to stop here" # in case it's a systematic problem
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
        fnoteText = f'<p class="fn" id="fn{footnotesCount}">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p><!--fn-->\n'
        if segmentType.endswith('Verse') and f'">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p><!--fn-->\n' in footnotesHtml:
            # We already have an identical footnote created, e.g., in OET-LV Job 8:16
            #   so all we have to do, is add the additional id to the existing note
            #       but can't have multiple id's on one element, so have to add an extra empty span.
            #   We only do this for single verses because the backwards link can't work for both.
            dupIx = footnotesHtml.index( f'">{fnoteRef}<span class="fnText">{fnoteMiddle}</span></p><!--fn-->\n' )
            footnotesHtml = f'{footnotesHtml[:dupIx]}"><span id="fn{footnotesCount}"></span>{footnotesHtml[dupIx+2:]}'
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {footnotesHtml=}" )
        else: # append this footnote to go at the bottom
            footnotesHtml = f'{footnotesHtml}{fnoteText}'
        html = f'{html[:fStartIx]}{fnoteCaller}{html[fEndIx+3:]}'
        # searchStartIx = fEndIx + 3
        searchStartIx = fStartIx + len(fnoteCaller)
        # if searchStartIx < fEndIx+3:
        #     print( f"{versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fStartIx=:,} {fEndIx+3=:,} {searchStartIx=:,} '{html[searchStartIx:searchStartIx+10]}'" )
    else:
        logging.critical( f"outer_fn_loop_needed_to_break {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {_outerSafetyCount=}" )
        outer_fn_loop_needed_to_break
    if footnotesHtml:
        if not checkHtml( f"Footnotes for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} {fnoteMiddle=}", footnotesHtml, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
        # if '<a title="Variant note' in html:
        #     nIx = html.index( '<a title="Variant note' )
        #     print( f"FOUND FN TITLE {versionAbbreviation} {segmentType} {basicOnly=} {refTuple} '{html[nIx:nIx+80]}'" )
        assert '<a title="Variant note:\n<br>' not in html # Check this before we append the actual footnote content to the end.
        html = f'{html}\n<hr class="line-before-footnotes"><div id="footnotes" class="footnotes">\n{footnotesHtml}</div><!--footnotes-->\n'
    # TODO: Find out why these following exceptions occur
    if versionAbbreviation not in ('T4T','BrTr','ClVg','TCNT','TC-GNT'): # T4T ISA 33:8, BrTr KI1 6:36a, ClVg MRK 3:10, TCNT&TC-GNT INT \\fp Why???
        assert '\\f' not in html, f"{versionAbbreviation} {refTuple} html='…{html[html.index(f'{BACKSLASH}f')-10:html.index(f'{BACKSLASH}f')+maxFootnoteChars]}…'"


    # Now handle all cross-references in one go (we don't check for matching \xo fields)
    crossReferencesCount = 0
    crossReferencesHtml = ''
    searchStartIx, lastSearchStartIx = 0, -1
    for _safetyCount1 in range( 599 if segmentType=='book' else 99 ):
        if searchStartIx == lastSearchStartIx: # then we didn't make any progress in the last loop iteration
            logging.critical( f"Seems we made no progress with {versionAbbreviation} {refTuple} {segmentType=} xref handling at '{html[searchStartIx:searchStartIx+30]}…'" )
            break # Better than an infinite loop
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
            assert xStartIx+5 <= xoIx <= xStartIx+6, f"Is this an xref (\\xo) encoding error? {xStartIx=} {xoIx=} '{html[xStartIx:xStartIx+20]}'" # Skips ' + '
            xoText = html[xoIx+3:xtIx].strip()
        xEndIx = html.find( '\\x*', xtIx+3 )
        assert xEndIx != -1

        # Liven the cross-references (xrefs) themselves
        xrefLiveMiddle = xrefOriginalMiddle = html[xtIx+4:xEndIx]
        if len(xrefOriginalMiddle) > 165 and (BBB!='JER' or versionAbbreviation!='UST'): # OET-RV HOS 1 is 162 (although will eventually be split into 5 pieces)
            print( f"Suspiciously long {versionAbbreviation} {refTuple} {segmentType=} got ({len(xrefOriginalMiddle)}) {xrefOriginalMiddle=}" ); halt
        xrefOriginalMiddle = xrefOriginalMiddle.replace('\\xo ','').replace('\\xt ','') # Fix things like "Gen 25:9-10; \\xo b \\xt Gen 35:29."
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" {xrefLiveMiddle=}" )
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
        xrefText = f'<p class="xr" id="xr{crossReferencesCount}">{xrefRef}<span class="xrText">{xrefLiveMiddle}</span></p><!--xr-->\n'
        crossReferencesHtml = f'{crossReferencesHtml}{xrefText}'
        html = f'{html[:xStartIx]}{xrefCaller}{html[xEndIx+3:]}'
        lastSearchStartIx = searchStartIx
        searchStartIx = xEndIx + 3
    else:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Processing xref {_safetyCount1} loop break {versionAbbreviation} {refTuple} {segmentType=} {xoText=} {xrefOriginalMiddle=}" )
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{verseEntryList=}" )
        dPrint( 'Info', DEBUGGING_THIS_MODULE,  f"{html[xStartIx:]=}" )
        # outer_xr_loop_needed_to_break
    if crossReferencesHtml:
        if not checkHtml( f"Cross-references for {versionAbbreviation} {segmentType} {basicOnly=} {refTuple}", crossReferencesHtml, segmentOnly=True ):
            if DEBUGGING_THIS_MODULE: assert False, "We want to stop here"
        html = f'{html}\n<hr class="line-before-xrefs"><div id="crossRefs" class="crossRefs">\n{crossReferencesHtml}</div><!--crossRefs-->\n'
    if versionAbbreviation not in ('BrTr',): # BrTr ISA 52
        assert '\\x' not in html, f"{html[html.index(f'{BACKSLASH}x')-10:html.index(f'{BACKSLASH}x')+12]}"
    # if refTuple==('DAN','1','2') or refTuple==('DAN','1','18'): assert False, "We want to stop here"

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
        # print( f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} …{html[ix-20:ix]}{html[ix:ix+20]}…" )
        assert False, "We want to stop here"
    html = html.replace( '<br>\n', '\n<br>' ) # This is our consistent (arbitrary) choice in OBD
    if '\n\n' in html:
        ix = html.index( '\n\n' )
        # print( f"{versionAbbreviation} {refTuple} {segmentType} {basicOnly=} …{html[ix-20:ix]}{html[ix:ix+20]}…" )
        assert False, "We want to stop here"
    html = html.replace( '\n\n', '\n' )

    while html.endswith( '\n' ): html = html[:-1] # We don't end our html with a newline
    while html.endswith( '<br>' ):
        html = html[:-4] # We don't end our html with a newline
        while html[-1] == '\n': html = html[:-1] # We don't end our html with a newline

    # Some final checks
    if versionAbbreviation not in ('ULT','UST'): # uW stuff has too many USFM encoding errors
        assert 'strong="' not in html, f"{level=} ‘{versionAbbreviation}’ {refTuple} {segmentType=} {len(contextList)=} {len(verseEntryList)=} {basicOnly=} '{html if len(html)<4000 else f'{html[:2000]} ....... {html[-2000:]}'}'"
    if not checkHtml( f'convertVerseEntryListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=})', html, segmentOnly=True ):
        if DEBUGGING_THIS_MODULE and versionAbbreviation!='OEB': # OEB has error in Job 26:14
            assert False, "We want to stop here"
    # print( f"convertVerseEntryListToHtml({versionAbbreviation} {refTuple} {segmentType} {basicOnly=}) ended with newline: {html.endswith(NEWLINE)}" )
    return html
# end of usfm.convertVerseEntryListToHtml


def livenIntroductionLinks( versionAbbreviation:str, refTuple:tuple, segmentType:str, introHtml:str, state:State ) -> str:
    """
    Liven general links in the introduction, e.g., 'was named Mary (Acts 12:12)' or 'accompanied Peter (1 Peter 5:13)'
        or 'about Jesus the messiah (Acts 12:25, 13:13).'
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIntroductionLinks( {versionAbbreviation}, {refTuple}, {segmentType}, '{introHtml}' )" )
    return liven_introduction_links( versionAbbreviation, refTuple, segmentType, introHtml, state )
# end of usfm.livenIntroductionLinks


def livenIORs( versionAbbreviation:str, refTuple:tuple, segmentType:str, ioLineHtml:str, state:State ) -> str:
    """
    Given some html, search for <span class="ior"> (these are usually in introduction \\iot lines)
        and liven those IOR links.
    Uses the Rust implementation for performance.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenIORs( {versionAbbreviation}, {refTuple}, {segmentType}, '{ioLineHtml}' )" )
    assert '\ior' not in ioLineHtml

    ourBBB = refTuple[0]
    is_single_chapter_book = bos_books_codes_py.is_single_chapter_book( ourBBB )

    # Use Rust implementation for all segment types (including section/relatedPassage via findSectionNumber callback)
    try:
        return liven_iors( ourBBB, segmentType, ioLineHtml, is_single_chapter_book, state )
    except Exception as e:
        logging.error( f"Error in Rust liven_iors for {versionAbbreviation} {refTuple} {segmentType}: {e}" )
        raise
# end of usfm.livenIORs function


myKJB1611XrefTable = {
    'Actes':'ACT','actes':'ACT', #'Acts':'ACT', 'Act':'ACT', 'acts':'ACT', 'act':'ACT',
    #'Amos':'AMO', 'amos':'AMO',
    'Apoc':'REV','apoc':'REV',
    #'1. Chron':'CH1', '1.Chron':'CH1','1.chron':'CH1', '1 Chron':'CH1', '1.Chro':'CH1', '1.chro':'CH1', '1 chron':'CH1',
    #'2.Chron':'CH2','2.chron':'CH2', '2.Chro':'CH2','2.chro':'CH2', '2.Chr':'CH2','2.chr':'CH2',
    #'1.Corin':'CO1','1.corin':'CO1','1.Cor':'CO1','1.cor':'CO1',
    #'2.Cor':'CO2','2.cor':'CO2',
    #'coloss':'COL', 'Col':'COL', 'col':'COL',
    #'Dan':'DAN',
    #'Deut':'DEU','deut':'DEU', 'Deu':'DEU','deu':'DEU',
    # 'Eccles':'ECC','eccles':'ECC',
    #'Ephes':'EPH', 'ephes':'EPH', 'Eph':'EPH', 'eph':'EPH', 'ephe':'EPH',
    'hest':'EST', #'Ester':'EST', 'Esth':'EST', 'Es':'EST', 'esth':'EST',
    'exe':'EXO', #'Exod':'EXO','exod':'EXO', 'Exo':'EXO',
    'Ezech':'EZE','ezech':'EZE', 'Exek':'EZE', 'ezec':'EZE', #'Ezek':'EZE','ezek':'EZE',
    'eszr':'EZR', # 'Ezra':'EZR',
    # 'Gene':'GEN','Gen':'GEN',
    # 'Galat':'GAL','galat':'GAL', 'Gal':'GAL','gal':'GAL',
    'Abacuc':'HAB', 'Habac':'HAB','habac':'HAB', 'Abak':'HAB', 'Abac':'HAB','abac':'HAB',
    'Hagge':'HAG', 'Agge':'HAG','agge':'HAG', 'agg':'HAG',
    # 'Hebr':'HEB', 'hebr':'HEB', 'Heb':'HEB', 'heb':'HEB',
    'Osee':'HOS', 'Ose':'HOS','ose':'HOS', 'Os':'HOS','os':'HOS',
        # 'Hose':'HOS', 'Hos':'HOS','hos':'HOS',
    'Esai':'ISA', 'Esa':'ISA','esa':'ISA', 'Esay':'ISA','esay':'ISA', 'esai':'ISA', 'Isay':'ISA',
        # 'Isai':'ISA','isai':'ISA', 'Isa':'ISA','isa':'ISA',
    'Iames':'JAM','iames':'JAM', 'Iam':'JAM', 'iam':'JAM',
    'Iude':'JDE','iude':'JDE','Iud':'JDE','iud':'JDE',
    'iudges':'JDG', 'iuges':'JDG', 'Iudg':'JDG','iudg':'JDG',
    'iudith':'JDT', 'iudit':'JDT', 'iudet':'JDT',
    'Ier':'JER','ier':'JER','Ierem':'JER', 'Iere':'JER', 'iere':'JER', 'ierem':'JER', 'Iee':'JER',
    'Ioh':'JHN','ioh':'JHN','Iohn':'JHN','iohn':'JHN',
    '1.Iohn':'JN1','1.iohn':'JN1', 'I.Iohn':'JN1', '1.Ioh':'JN1','1.ioh':'JN1',
    'ionas':'JNA', 'Iona':'JNA', 'ion':'JNA',
    'Iob':'JOB','iob':'JOB',
    'Ioel':'JOL','ioel':'JOL',
    'Iosh':'JOS','iosh':'JOS','Ios':'JOS','Iosu':'JOS',
    # '1.Kings':'KI1', '1.King':'KI1', '1.king':'KI1', '1 King':'KI1', '1.Kin':'KI1','1.kin':'KI1', '1 kin':'KI1',
            '1.Reg':'KI1',
    # '2.Kings':'KI2', '2.King':'KI2','2.king':'KI2', '2 king':'KI2', '2.Kin':'KI2','2.kin':'KI2',
    # 'Lam':'LAM', 'lam':'LAM',
    '4.Esdr':'LES','4.Esd':'LES',
    'Leuit':'LEV','leuit':'LEV', 'Leui':'LEV','leui':'LEV', 'Leu':'LEV',
    'Luc':'LUK','luc':'LUK', #'Luk':'LUK', 'Luke':'LUK','luke':'LUK','luk':'LUK',
    # '1.Macc':'MA1', '1 macc':'MA1', '1.Mac':'MA1',
    # '2.Macc':'MA2','2.macc':'MA2', '2.mac':'MA2',
    # 'Malac':'MAL', 'Mala':'MAL', 'Mal':'MAL',
    # 'Matth':'MAT', 'Matt':'MAT','Mat':'MAT','mat':'MAT', 'matth':'MAT', 'matt':'MAT',
    # 'mica':'MIC',
    'Marke':'MRK','marke':'MRK', 'Marc':'MRK', #'Mark':'MRK','mark':'MRK', 'Mar':'MRK','mar':'MRK',
    'naum':'NAH',
    # 'Nehem':'NEH', 'nehem':'NEH', 'Nehe':'NEH', 'nehe':'NEH',
    'nnm':'NUM', # 'Numb':'NUM','numb':'NUM', 'Num':'NUM', 'num':'NUM',
    # '1.Pet':'PE1', '1.pet':'PE1',
    # '2.Pet':'PE2','2.pet':'PE2',
    # 'Phil':'PHP', 'phil':'PHP',
    'psalme':'PSA', # 'Psal':'PSA', 'psal':'PSA', 'Psa':'PSA', 'Ps':'PSA', 'psa':'PSA',
    'Prou':'PRO', 'prou':'PRO', # 'Pro':'PRO', 'pro':'PRO',
    # '1.Sam':'SA1','1.sam':'SA1', '1 Sam':'SA1',
    # '2.Sam':'SA2','2.sam':'SA2',
    # '1.Thess':'TH1','1.thess':'TH1', '1 thess':'TH1', '1.Thes':'TH1','1.thes':'TH1',
    # '2.thes':'TH2', '2 thess':'TH2',
    # '1.tim':'TI1',
    # '2.tim':'TI2',
    # 'Tit':'TIT',
    # 'tob':'TOB',
    'Reuel':'REV','reuel':'REV', 'Reue':'REV','reue':'REV', 'Reu':'REV','reu':'REV',
    # 'Rom':'ROM', 'rom':'ROM',
    # 'ecclus':'SIR', 'Ecclus':'SIR','Ecclu':'SIR','ecclu':'SIR', # Sirach / Ecclesiasticus
    'Sophan':'ZEP',
    # '1.Tim':'TI1',
    # 'Wisd':'WIS', 'Wis':'WIS', 'wisd':'WIS', 'wis':'WIS',
    'Zach':'ZEC','zach':'ZEC',  'Zac':'ZEC','zac':'ZEC',
    }
BCVRefRegEx = re.compile( '(?: ?and)?( ?[1234I]?[ .]?[A-Za-z][a-z]{1,12})\\.? ?([1-9][0-9]{0,2}|ver)[:.–] ?([1-9][0-9]{0,2})' ) # Can have en-dash for chapter range
                # Note above that single-chapter books can have 'ver' instead of the chapter number '1'
BVRefRegEx = re.compile( '([1234I]?[ .]?[A-Za-z][a-z]{0,12})\\.? ?(?:ver)?\\.? ?([1-9][0-9]{0,2})' ) # For single-chapter book or for whole chapter
CVRefRegEx = re.compile( '([1-9][0-9]{0,2})[:.]([1-9][0-9]{0,2})' )
NextVRefRegEx = re.compile( ',([1-9][0-9]{0,2})')
def livenXRefField( fieldType:str, versionAbbreviation:str, refTuple:tuple, segmentType:str, pathPrefix:str, xoText:str, xrefOriginalMiddle:str, state:State ) -> str:
    """
    Given the middle of a cross-reference or the xt field from a footnote,
        return the text but with the xref(s) in it livened.

    State parameter is only used for the OET-RV.
    Uses the Rust implementation for performance.
    """
    BBB = refTuple[0]
    C = refTuple[1] if len(refTuple) > 1 else '0'
    V = refTuple[2] if len(refTuple) > 2 else '0'
    return liven_xref_field( fieldType, versionAbbreviation, BBB, C, V, segmentType, pathPrefix, xoText, xrefOriginalMiddle, state )
# end of usfm.livenXRefField function


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

    # Demo liven_introduction_links (Rust implementation)
    print( "\nTesting liven_introduction_links (Rust PyO3)..." )
    for testIntro, ourBBB, segType, expectedResult in (
        ( 'was named Mary (Acts 12:12)', 'MAT', 'book', 'was named Mary (<a title="Go to reference document" href="ACT.htm#C12V12">Acts 12:12</a>)' ),
        ( 'accompanied Peter (1 Peter 5:13)', 'MAT', 'chapter', 'accompanied Peter (<a title="Go to reference chapter" href="PE1_C5.htm#C5V13">1 Peter 5:13</a>)' ),
        ( 'see (Col. 4:10).', 'COL', 'Verse', 'see (<a title="Go to reference verse" href="C4V10.htm#Top">Col. 4:10</a>).' ),
        ( 'see (Col. 4:10).', 'MAT', 'Verse', 'see (<a title="Go to reference verse" href="../COL/C4V10.htm#Top">Col. 4:10</a>).' ),
        ( 'about Yeshua the messiah (Acts 12:25, 13:13).', 'MRK', 'book', 'about Yeshua the messiah (<a title="Go to reference document" href="ACT.htm#C12V25">Acts 12:25</a>, <a title="Go to reference document" href="ACT.htm#C13V13">13:13</a>).' ),
        ( 'about Yeshua the messiah (Acts 12:25, 13:13).', 'MRK', 'chapter','about Yeshua the messiah (<a title="Go to reference chapter" href="ACT_C12.htm#C12V25">Acts 12:25</a>, <a title="Go to reference chapter" href="ACT_C13.htm#C13V13">13:13</a>).' ),
        ( 'something (12:25)', 'MRK', 'chapter', 'something (<a title="Jump to chapter page with reference" href="MRK_C12.htm#C12V25">12:25</a>)' ),
    ):
        print( f"\n{testIntro=} ({ourBBB=}, {segType=})" )
        result = liven_introduction_links( 'OET-RV', (ourBBB, '-1', '1'), segType, testIntro, state )
        print( f"{'Expected' if result==expectedResult else 'DIFFERENT'} {result=}{f' {expectedResult=}' if result!=expectedResult else ''}")
        assert result == expectedResult, f"  {result=}"

    # Demo to_roman_numerals (Rust implementation)
    print( "\nTesting to_roman_numerals (Rust PyO3)..." )
    for testNum in ( 0, 1, 4, 9, 14, 40, 50, 90, 99, 100, 119, 150, '151' ):
        result = to_roman_numerals( testNum )
        print( f"  {testNum} -> {result}" )
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
