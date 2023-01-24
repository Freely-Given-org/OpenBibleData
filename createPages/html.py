#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData html functions
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
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from Bibles import eachChapter, fetchChapter


LAST_MODIFIED_DATE = '2023-01-23' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.03'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createChapterPages( folder:Path, thisBible, state ) -> List[str]:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createChapterPages( {folder}, {thisBible.abbreviation} )")
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there


    BBBs, filenames = [], []
    for BBB in thisBible.books:
        # if not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ): continue # Skip all except NT for now
        if thisBible.abbreviation=='OET-LV' \
        and BBB in ('FRT','INT','NUM','SA1','SA2','CH1','EZR','NEH','JOB','SNG','JER','DAN'): continue # Too many problems for now
        if BBB not in ('MRK','JN3'): continue
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating chapter pages for {thisBible.abbreviation} {BBB}…" )
        BBBs.append( BBB )
        numChapters = thisBible.getNumChapters( BBB )
        if numChapters >= 1:
            for c in range(1, numChapters+1 ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
                cHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
                verseEntryList, contextList = fetchChapter( thisBible, BBB, c)
                cHtml += convertUSFMMarkerListToHtml( (BBB,c), 'chapter', contextList, verseEntryList )
                filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html'
                filenames.append( filename )
                filepath = folder.joinpath( filename )
                with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                    cHtmlFile.write( makeTop(3, 'chapters', state) + '<!--chapter page-->' + cHtml + makeBottom(3, 'chapters', state) )
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
        else:
            print( f"{BBB} has {numChapters} chapters!!!")
            assert BBB in ('INT','FRT',)
            print( thisBible.books[BBB] )
            c = '-1'
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating (non)chapter pages for {thisBible.abbreviation} {BBB} {c}…" )
            cHtml = f'<h1>{thisBible.abbreviation} {BBB} Chapter {c}</h1>\n'
            # verseEntryList, contextList = fetchChapter( thisBible, BBB, c)
            verseEntryList, contextList = thisBible.getContextVerseData( (BBB, c, '1') )
            print( f"{thisBible.abbreviation} {BBB} {verseEntryList} {contextList}")
            cHtml += convertUSFMMarkerListToHtml( (BBB,c), 'chapter', contextList, verseEntryList )
            filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html'
            filenames.append( filename )
            filepath = folder.joinpath( filename )
            with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
                cHtmlFile.write( makeTop(3, 'chapters', state) + '<!--chapter page-->' + cHtml + makeBottom(3, 'chapters', state) )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
            halt
    # Now create index pages for each book and an overall one
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Creating chapter index pages for {thisBible.abbreviation}…" )
    BBBLinks = []
    for BBB in BBBs:
        # tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB(BBB)
        tidyBBB = (BBB[2]+BBB[:2]) if BBB[2].isdigit() else BBB
        filename = f'{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}.html'
        filenames.append( filename )
        filepath = folder.joinpath( filename )
        BBBLinks.append( f'<a href="{filename}">{tidyBBB}</a>' )
        numChapters = thisBible.getNumChapters( BBB )
        cLinks = []
        if numChapters >= 1:
            for c in range(1, numChapters+1 ):
                cLinks.append( f'<a href="{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}_{BBB}_C{c}.html">C{c}</a>' )
        else:
            pass # TODO: for now
        cHtml = makeTop(3, 'chapters', state) + '<!--chapters indexPage-->' + EM_SPACE.join( cLinks ) + makeBottom(3, 'chapters', state)
        with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
            cHtmlFile.write( cHtml )
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    {len(cHtml):,} characters written to {filepath}" )
    filename = 'index.html'
    filenames.append( filename )
    filepath = folder.joinpath( filename )
    indexHtml = makeTop(3, 'chapters', state) + '<!--chapters books indexPage-->' + EM_SPACE.join( BBBLinks ) + makeBottom(3, 'chapters', state)
    with open( filepath, 'wt', encoding='utf-8' ) as cHtmlFile:
        cHtmlFile.write( indexHtml )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )

    return filenames
# end of html.createChapterPages

def convertUSFMMarkerListToHtml( refTuple, segmentType, contextList, markerList, basicOnly=False ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {refTuple} '{segmentType}' {contextList} {markerList} )")
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"convertUSFMMarkerListToHtml( {refTuple} '{segmentType}' {contextList} {len(markerList)} )")

    inParagraph = inSection = inList = inListEntry = None
    html = ''
    for marker in contextList:
        if marker == 's1':
            rest = '--unknown--'
            if not basicOnly:
                html = f'{html}<div class="{marker}"><p class="{marker}">{rest}</p>\n'
            inSection = marker
        elif marker == 'p':
            if not basicOnly:
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker not in ('chapters', 'c'):
            if refTuple[0] not in ('EXO','NUM') or marker!='list': unexpected_context_at_start_of_chapter
    for n, entry in enumerate(markerList):
        marker, rest = entry.getMarker(), entry.getText()
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{n} {refTuple}: {marker}={rest}" )
        # print( f"{marker} '{rest=}' '{entry.getCleanText()=}' '{entry.getFullText()=}'  '{entry.getOriginalText()=}'  extras={entry.getExtras()}")
        if marker == 'c':
            # if segmentType == 'chapters':
            html = f'{html}<span class="{marker}" id="C{rest}">{rest}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker == 'v': # This is where we want the verse marker
            html = f'{html}<span class="{marker}" id="C{refTuple[1]}V{rest}">{rest}{NARROW_NON_BREAK_SPACE}</span>'
        elif marker in ('s1','s2','s3','s4'):
            assert not inSection and not inParagraph, f"{inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<div class="{marker}"><p class="{marker}">{formatUSFMText(rest, basicOnly)}</p>\n'
            inSection = marker
        elif marker in ('¬s1','¬s2','¬s3','¬s4',):
            assert not rest
            assert inSection == marker[1:] and not inParagraph, f"{inSection=} {inParagraph=} {inList=} {marker=}"
            html = f'{html}</div><!--{marker[1:]}-->\n'
            inSection = None
        elif marker in ('ms1','ms2','ms3','ms4'):
            if refTuple[0] == 'JOB' and inSection=='s1' and inParagraph=='q1': # TODO: Fix something for OET-LV
                html = f'{html}</q1></div>\n'
                inSection = inParagraph = None
            assert not inSection and not inParagraph, f"{inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{formatUSFMText(rest, basicOnly)}</p>\n'
        elif marker in ('r','mr','sr', 'd', 'sp', 'rem'):
            if marker=='r': assert inSection, f"{inSection=} {inParagraph=} {marker}={rest}"
            if marker!='rem': assert not inParagraph, f"{inSection=} {inParagraph=} {marker}={rest}"
            if not basicOnly:
                html = f'{html}<p class="{marker}">{rest}</p>\n'
        elif marker in ('p', 'q1','q2','q3','q4', 'm','mi', 'nb', 'pi'):
            if refTuple not in (('JHN',8),):
                assert not inParagraph, f"{inSection=} {inParagraph=} {marker}={rest}"
            assert not rest, f"{marker}={rest}"
            if marker=='m' and inList=='ul': # refTuple==('EXO',10,11)
                html = f'{html}</ul>\n'
                inList = None
                print( refTuple)
            if not basicOnly:
                html = f'{html}<p class="{marker}">'
                inParagraph = marker
        elif marker in ('¬p', '¬q1','¬q2','¬q3','¬q4', '¬m','¬mi', '¬nb', '¬pi'):
            assert not rest
            if refTuple not in (('JHN',8),):
                assert inParagraph == marker[1:], f"{inSection=} {inParagraph=} {marker=}"
            html = f'{html}</p>\n'
            inParagraph = None
        elif marker in ('p~','v~'): # This has the actual verse text
            html += formatUSFMText( rest, basicOnly )
        elif marker == 'b':
            html = f'{html}<br>\n'
        elif marker == 'list':
            assert not rest
            assert not inList, f"{inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}<ul>\n'
            inList = 'ul'
        elif marker == '¬list':
            if refTuple[0] not in ('EXO','NUM'): # TODO: Temp for OET-RV
                assert inList and not inListEntry, f"{inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
                html = f'{html}</{inList}>{rest}'
            inList = None
        elif marker in ('li1','li2','li3','li4'):
            assert inList and not inListEntry, f"{inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}<li>{rest}'
            inListEntry = marker
        elif marker in ('¬li1','¬li2','¬li3','¬li4'):
            assert not rest
            assert inList and inListEntry == marker[1:], f"{inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
            html = f'{html}</li>\n'
            inListEntry = None
        elif marker in ('¬v', ): # We can ignore these end markers
            assert not rest
        elif segmentType=='chapter' and marker in ('¬c','¬chapters'): # We can ignore this
            if inSection and marker == '¬c':
                logging.critical( f"{refTuple} Finished chapter inside section")
            else:assert not inSection and not inParagraph, f"{inSection=} {inParagraph=} {marker}={rest}"
        elif marker not in ('v=', 'c#', '¬c'): # We can ignore all of these
            unexpected_marker
        if '\\' in html: print(html); leftover_backslash
    if refTuple not in (('JHN',7),):
        assert (not inSection or inSection=='s1') and not inParagraph and not inListEntry, f"convertUSFMMarkerListToHtml final {inSection=} {inParagraph=} {inList=} {inListEntry=} {marker=}"
    if inList: logging.critical( f"convertUSFMMarkerListToHtml finished with {inList} list for {refTuple}")
    return html
# end of html.convertUSFMMarkerListToHtml

def formatUSFMText( usfmField, basicOnly=False ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"formatUSFMText( {usfmField}, {basicOnly=} )")
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"formatUSFMText( {usfmField}, {basicOnly=} )")
    assert usfmField.count('\\add ') == usfmField.count('\\add*')
    assert usfmField.count('\\em ') == usfmField.count('\\em*')
    assert usfmField.count('\\it ') == usfmField.count('\\it*')
    html = usfmField \
            .replace( '\\add ', '<span class="added">' ).replace( '\\add*', '</span>' ) \
            .replace( '\\em ', '<em>' ).replace( '\\em*', '</em>' ) \
            .replace( '\\it ', '<it>' ).replace( '\\it*', '</it>' )
    assert '\\' not in html, html
    return html
# end of html.formatUSFMText

def createInterlinearPages( folder:Path, thisBible, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createInterlinearPages( {folder}, {thisBible.abbreviation} )")
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there
# end of html.createInterlinearPages

def createParallelPages( folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelPages( {folder}, {state.BibleVersions} )")
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there
# end of html.createParallelPages

def createIndexPage( level, folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createIndexPage( {level}, {folder}, {state.BibleVersions} )")
    html = makeTop( level, state ) \
            .replace( '__TITLE__', 'Open Bible Data' ) \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    bodyHtml = """<h1>Open Bible Data</h1>
"""
    html += bodyHtml + makeBottom()
    filepath = folder.joinpath( 'index.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of html.createIndexPage

def makeTop( level:int, pageType:str, state ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeTop( {level}, {pageType} )")

    if pageType == 'chapters':
        cssFilename = 'BibleChapters.css'
    else: cssFilename = 'BibleSite.css'

    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>__TITLE__</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="keywords" content="__KEYWORDS__">
  <link rel="stylesheet" type="text/css" href="{'../'*level}{cssFilename}">
</head>
<body>
""" + makeHeader( level, pageType, state ) + '\n'
    #<script src="content.js"></script>
# end of html.makeTop

def makeHeader( level:int, pageType:str, state ) -> str:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"makeHeader( {level}, {pageType} )")
    html = ''
    versionList = []
    for versionName in state.BibleVersions:
        versionList.append( f'<a href="versions/{BibleOrgSysGlobals.makeSafeString(versionName)}">{versionName}</a>' )
    return f'<div class="header">{EM_SPACE.join(versionList)}</div><!--header-->'
# end of html.makeHeader

def makeBottom( level:int, pageType:str, state ) -> str:
    """
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeBottom()")
    return makeFooter( level, pageType, state ) + '</body></html>'
# end of html.makeBottom

def makeFooter( level:int, pageType:str, state ) -> str:
    """
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"makeFooter()")
    html = """<div class="footer">
</div><!--footer-->
"""
    return html
# end of html.makeFooter


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
