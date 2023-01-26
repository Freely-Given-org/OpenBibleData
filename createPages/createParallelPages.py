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

from usfm import convertUSFMMarkerListToHtml
from html import doOET_LV_HTMLcustomisations, makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-01-26' # by RJH
SHORT_PROGRAM_NAME = "html"
PROGRAM_NAME = "OpenBibleData HTML functions"
PROGRAM_VERSION = '0.06'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = True

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createParallelPages( folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelPages( {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    BBBLinks = []
    for BBB in state.allBBBs:
        BBBFolder = folder.joinpath(f'{BBB}/')
        createParallelBookPages( BBBFolder, BBB, state )
        BBBLinks.append( f'<a href="{BBBFolder}/">{BBB}</a>' )

    # Create index page
    filename = 'index.html'
    filepath = folder.joinpath( filename )
    top = makeTop(1, 'parallel', state) \
            .replace( '__TITLE__', f'Parallel View' ) \
            .replace( '__KEYWORDS__', f'Bible, parallel' )
    indexHtml = top \
                + '<h1>Parallel verse pages</h1><h2>Index of books</h2>\n' \
                + EM_SPACE.join( BBBLinks ) \
                + makeBottom(1, 'parallel', state)
    checkHtml( 'ParallelIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of html.createParallelPages

def createParallelBookPages( folder:Path, BBB:str, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelBookPages( {folder}, {BBB}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    referenceBible = state.preloadedBibles['OET-LV']
    numChapters = referenceBible.getNumChapters( BBB )
    vLinks = []
    if numChapters >= 1:
        for c in range( 1, numChapters+1 ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating parallel pages for {BBB} {c}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            for v in range( 1, numVerses ):
                pHtml = f'<h1>Parallel {BBB} {c}:{v}</h1>\n'
                for versionAbbreviation in state.BibleVersions:
                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have OET-RV and OET-LV
                    if versionAbbreviation in ('UHB',) \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB):
                        continue # Skip non-OT books for Hebrew
                    if versionAbbreviation in ('SR-GNT','UGNT') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip non-NT books for Koine Greek NT
                    thisBible = state.preloadedBibles[versionAbbreviation]
                    vHtml = f'<h2>{versionAbbreviation}</h2>\n'
                    try:
                        verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c), str(v)) )
                        vHtml += convertUSFMMarkerListToHtml( versionAbbreviation, (BBB,c,v), 'verse', contextList, verseEntryList, basicOnly=True )
                    except (KeyError, TypeError):
                        text = f'No {BBB} {c}:{v} verse available'
                        logging.critical( text )
                        vHtml += f'<p>{text}</p>'
                    if versionAbbreviation == 'OET-LV':
                        vHtml = doOET_LV_HTMLcustomisations( vHtml )
                    # print( f"\n\n{pHtml=} {vHtml=}" )
                    checkHtml( f'{versionAbbreviation} {BBB} {c}:{v}', vHtml, segmentOnly=True )
                    pHtml += vHtml
                filename = f'{BBB}_C{c}_V{v}.html'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( 2, 'parallel', state ) \
                        .replace( '__TITLE__', f'Parallel {BBB} {c}:{v}' ) \
                        .replace( '__KEYWORDS__', f'Bible, {BBB}, parallel' )
                pHtml = top + '<!--chapter page-->' + pHtml + makeBottom(2, 'parallel', state)
                checkHtml( f'Parallel {BBB} {c}:{v}', pHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( pHtml )
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    {len(pHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a href="{filename}">{c}:{v}</a>' )
    else:
        print( f"createParallelBookPages {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # print( f"createParallelBookPages {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename = 'index.html'
    filepath = folder.joinpath( filename )
    top = makeTop(2, 'parallel', state) \
            .replace( '__TITLE__', f'Parallel View' ) \
            .replace( '__KEYWORDS__', f'Bible, parallel' )
    indexHtml = f'{top}<h1>{BBB} parallel verses index</h1>\n' \
                + EM_SPACE.join( vLinks ) \
                + makeBottom(2, 'parallel', state)
    checkHtml( 'ParallelIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelBookPages() finished processing {len(vLinks):,} BBB verses" )
    return True
# end of html.createParallelBookPages


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
