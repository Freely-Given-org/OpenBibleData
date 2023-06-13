#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData createParallelPages functions
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
Module handling createParallelPages functions.
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTyndaleBookIntro, formatUnfoldingWordTranslationNotes, formatTyndaleNotes, tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-06-13' # by RJH
SHORT_PROGRAM_NAME = "createParallelPages"
PROGRAM_NAME = "OpenBibleData createParallelPages functions"
PROGRAM_VERSION = '0.64'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createParallelPages( level:int, folder:Path, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelPages( {level}, {folder}, {state.BibleVersions} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateParallelPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Prepare the book links
    BBBLinks, BBBNextLinks = [], []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            ourTidyBBB = tidyBBB( BBB )
            BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="{BBB}/">{ourTidyBBB}</a>''' )
            BBBNextLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="../{BBB}/">{ourTidyBBB}</a>''' )

    # Now create the actual parallel pages
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            BBBFolder = folder.joinpath(f'{BBB}/')
            createParallelVersePagesForBook( level+1, BBBFolder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallel', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Parallel View" ) \
            .replace( '__KEYWORDS__', f'Bible, parallel' )
    indexHtml = f'''{top}<h1 id="Top">Parallel verse pages</h1><h2>Index of books</h2>
{makeBookNavListParagraph(BBBLinks, state)}
{makeBottom( level, 'parallel', state )}'''
    checkHtml( 'ParallelIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of html.createParallelPages

class MissingBookError( Exception ): pass
class UntranslatedVerseError( Exception ): pass

def createParallelVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state ) -> bool:
    """
    Create a page for every Bible verse
        displaying the verse for every available version.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook {level}, {folder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = tidyBBB( BBB )
    ourTidyBbb = tidyBBB( BBB, titleCase=True )
    adjBBBLinksHtml = makeBookNavListParagraph(BBBLinks, state) \
            .replace( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )

    numChapters = None
    for versionAbbreviation in state.BibleVersions:
        if versionAbbreviation == 'OET': continue # that's only a "pseudo-version"!
        referenceBible = state.preloadedBibles[versionAbbreviation]
        if BBB not in referenceBible: continue # don't want to force loading the book
        # referenceBible.loadBookIfNecessary( BBB )
        numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
        if numChapters: break
    else:
        logging.critical( f"createParallelVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( -1, numChapters+1 ):
            C = str( c )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating parallel pages for {BBB} {C}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createParallelVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            for v in range( 0, numVerses+1 ):
                V = str( v )
                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Go to previous verse" href="C{C}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                # NOTE below: C1V0 may not exist in the version but usually there's uW TNs for 1:0
                rightVLink = f' <a title="Go to first chapter intro" href="C1V0.htm#__ID__">→</a>' if c==-1 \
                        else f' <a title="Go to next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses \
                        else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a> ' if c>1 else ''
                rightCLink = f' <a title="Go to first chapter" href="C1V1.htm#__ID__">►</a>' if c==-1 \
                        else f' <a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters \
                        else ''
                introLink = '<a title="Go to book intro" href="Intro.htm#__ID__">I</a> ' if v==0 \
                        else f'<a title="Go to chapter intro" href="C{c}V0.htm#__ID__">I</a> ' if v==1 \
                        else ''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about these works" href="{'../'*(level)}allDetails.htm">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introduction <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{introLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>'
                pHtml = ''
                for versionAbbreviation in state.BibleVersions:
                    if versionAbbreviation == 'OET': continue # Skip this pseudo-version as we have OET-RV and OET-LV
                    if versionAbbreviation in ('UHB','JPS') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB):
                        continue # Skip non-OT books for Hebrew
                    if versionAbbreviation in ('BRN','BrLXX') \
                    and BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip NT books for Brenton (it has deuterocanon/apocrypha)
                    if versionAbbreviation in ('TCNT','TNT', 'SR-GNT','UGNT','SBL-GNT','TC-GNT') \
                    and not BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB):
                        continue # Skip non-NT books for Koine Greek NT
                    if versionAbbreviation in ('TSN','TTN','UTN'):
                        continue # We handle the notes separately at the end

                    thisBible = state.preloadedBibles[versionAbbreviation]
                    # thisBible.loadBookIfNecessary( BBB )
                    textHtml = None
                    try:
                        if BBB not in thisBible: raise MissingBookError # Requested book is not in this Bible
                        # NOTE: For the book intro, we fetch the whole lot in one go (not line by line)
                        verseEntryList, contextList = thisBible.getContextVerseData( (BBB, C) if c==-1 else (BBB, C, V) )
                        if isinstance( thisBible, ESFMBible.ESFMBible ):
                            verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
                        textHtml = convertUSFMMarkerListToHtml( level, versionAbbreviation, (BBB,C,V), 'verse', contextList, verseEntryList, basicOnly=(c!=-1), state=state )
                        if textHtml == '◘': raise UntranslatedVerseError

                        if versionAbbreviation == 'OET-RV':
                            textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation == 'OET-LV':
                            textHtml = do_OET_LV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation == 'WEB': # assuming WEB comes BEFORE WMB
                            textHtmlWEB = textHtml # Save it
                        elif versionAbbreviation == 'WMB': # assuming WEB comes BEFORE WMB
                            if textHtml == textHtmlWEB:
                                # print( f"Skipping parallel for WMB {BBB} {C}:{V} because same as WEB" )
                                continue
                            # else:
                            #     print( f"Using parallel for WMB {BBB} {C}:{V} because different from WEB:" )
                            #     print( f"  {textHtmlWEB=}" )
                            #     print( f"     {textHtml=}" )
                        elif versionAbbreviation == 'LSV':
                            textHtml = do_LSV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation == 'T4T':
                            textHtml = do_T4T_HTMLcustomisations( textHtml )
                        elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB'):
                            modernisedTextHtml = moderniseEnglishWords( textHtml )
                            if versionAbbreviation in ('WYC','TNT'):
                                modernisedTextHtml = modernisedTextHtml.replace( 'J', 'Y' ).replace( 'Ie', 'Ye' ).replace( 'Io', 'Yo' )
                            if modernisedTextHtml != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({modernisedTextHtml})'
                        elif versionAbbreviation in ('CLV',):
                            if (adjustedTextHtml:=adjustLatin(textHtml)) != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({adjustedTextHtml})'
                        elif versionAbbreviation in ('SR-GNT','UGNT','SBL-GNT','TC-GNT','BrLXX'):
                            # print( f"{versionAbbreviation} {BBB} {C}:{V} {textHtml=}")
                            transcription = transliterate_Greek(textHtml)
                            if 'Ah' in transcription or ' ah' in transcription or transcription.startswith('ah') \
                            or 'Eh' in transcription or ' eh' in transcription or transcription.startswith('eh') \
                            or 'Oh' in transcription or ' oh' in transcription or transcription.startswith('oh') \
                            or 'Uh' in transcription or ' uh' in transcription or transcription.startswith('uh'):
                                print( f"{versionAbbreviation} {BBB} {C}:{V} {transcription=} from '{textHtml}'")
                                bad_greek_transcription
                            if versionAbbreviation == 'SR-GNT': # for the transcription, bolden nomina sacra words
                                searchStartIndex = 0
                                while '˚' in transcription:
                                    ixNS = transcription.index( '˚', searchStartIndex )
                                    ixComma = transcription.find( ',', ixNS+1 )
                                    if ixComma == -1: ixComma = 9999
                                    ixPeriod = transcription.find( '.', ixNS+1 )
                                    if ixPeriod == -1: ixPeriod = 9999
                                    ixSpace = transcription.find( ' ', ixNS+1 )
                                    if ixSpace == -1: ixSpace = 9999
                                    ixEnd = min( ixComma, ixPeriod, ixSpace, len(transcription) )
                                    transcription = f'''{transcription[:ixNS]}<span class="nominaSacra">{transcription[ixNS+1:ixEnd]}</span>{transcription[ixEnd:]}'''
                                    searchStartIndex = ixEnd
                                # print( f"Now {transcription=}" )
                                # if '<span' in transcription: halt
                            textHtml = f'{textHtml}<br>  ({transcription})'
                            # print( textHtml)
                        elif versionAbbreviation in ('UHB',):
                            # print( f"{versionAbbreviation} {BBB} {C}:{V} {textHtml=}")
                            textHtml = f'{textHtml}<br>  ({transliterate_Hebrew(textHtml)})'
                            # print( textHtml)
                        if textHtml:
                            vHtml = f'''
<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{C}.htm">OET-RV</a>)</span> {textHtml}</p>
''' if versionAbbreviation=='OET-RV' else f'''
<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} chapter" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> {textHtml}</p>
'''
                        else: # no textHtml -- can include verses that are not in the OET-LV
                            if c==-1 or v==0: # For these edge cases, we don't want the version abbreviation appearing
                                vHtml = ''

                    except MissingBookError:
                        assert not textHtml, f"{versionAbbreviation} {BBB} {C}:{V} {verseEntryList=} {textHtml=}"
                        assert BBB not in thisBible
                        warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                        vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )

                    except UntranslatedVerseError:
                        assert textHtml == '◘'
                        assert versionAbbreviation == 'OET-RV'
                        assert BBB in thisBible
                        if BBB in thisBible:
                            # print( f"No verse inB {versionAbbreviation} {BBB} in {thisBible}"); halt
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
'''
                        else:
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )

                    except KeyError:
                        assert not textHtml, f"{versionAbbreviation} {BBB} {C}:{V} {verseEntryList=} {textHtml=}"
                        if c==-1 or v==0:
                            vHtml = ''
                        elif BBB in thisBible:
                            # print( f"No verse inKT {versionAbbreviation} {BBB} in {thisBible}"); halt
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
'''
                            logging.warning( warningText )
                        else:
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                            vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                            logging.warning( warningText )

                    if vHtml:
                        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                        checkHtml( f'{versionAbbreviation} {BBB} {C}:{V}', vHtml, segmentOnly=True )
                        pHtml = f'{pHtml}{vHtml}'

                if c == -1: # Handle Tyndale book intros
                    tbiHtml = formatTyndaleBookIntro( level, BBB, 'parallel', state )
                    if tbiHtml:
                        pHtml = f'{pHtml}{tbiHtml}'

                # Handle Tyndale open study notes and theme notes
                tsnHtml = formatTyndaleNotes( 'TSN', level, BBB, C, V, 'parallel', state )
                if tsnHtml:
                    tsnHtml = f'''<div id="TSN" class="parallelTSN"><a id="Go to TSN copyright page" href="{'../'*level}TSN/details.htm">TSN</a> <b>Tyndale Study Notes</b>: {tsnHtml}</div><!--end of TSN-->\n'''
                    pHtml = f'{pHtml}{tsnHtml}'
                ttnHtml = formatTyndaleNotes( 'TTN', level, BBB, C, V, 'parallel', state )
                if ttnHtml:
                    ttnHtml = f'''<div id="TTN" class="parallelTTN"><a id="Go to TSN copyright page" href="{'../'*level}TSN/details.htm">TTN</a> <b>Tyndale Theme Notes</b>: {ttnHtml}</div><!--end of TTN-->\n'''
                    pHtml = f'{pHtml}{ttnHtml}'
                # Handle uW translation notes
                utnHtml = formatUnfoldingWordTranslationNotes( level, BBB, C, V, 'parallel', state )
                if utnHtml:
                    utnHtml = f'''<div id="UTN" class="parallelUTN"><a id="Go to UTN copyright page" href="{'../'*level}UTN/details.htm">UTN</a> <b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->\n'''
                    pHtml = f'{pHtml}{utnHtml}'

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'parallel', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {C}:{V} Parallel View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {ourTidyBBB}, parallel' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*level}il/"''', f'''href="{'../'*level}il/{BBB}/C{C}V{V}.htm"''')
                pHtml = f'''{top}<!--parallel verse page-->
{adjBBBLinksHtml}
<h1>Parallel {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{pHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( level, 'parallel', state )}'''
                checkHtml( f'Parallel {BBB} {C}:{V}', pHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( pHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(pHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to parallel verse page" href="{filename}">{C}:{V}</a>' )
                if c == -1: # then we're doing the book intro
                    break # no need to loop -- we handle the entire intro in one go
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallel', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Parallel View" ) \
            .replace( '__KEYWORDS__', f'Bible, parallel' )
    # For Psalms, we don't list every single verse
    introLinks = [ '<a title="Go to parallel intro page" href="Intro.htm">Intro</a>' ]
    ourLinks = f'''<h1 id="Top">{ourTidyBBB} parallel songs index</h1>
<p class="chLst">{EM_SPACE.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/James'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">{ourTidyBBB} parallel verses index</h1>
<p class="vsLst">{' '.join( vLinks )}</p>'''
    indexHtml = f'''{top}{adjBBBLinksHtml}
{ourLinks}
{makeBottom( level, 'parallel', state )}'''
    checkHtml( 'ParallelIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelVersePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of html.createParallelVersePagesForBook


ENGLISH_WORD_MAP = ( # Place longer words first,
                     #     use space before to prevent accidental partial-word matches
                     #     since we're only doing string matches (but they're case sensitive)
    # Pairs of words
    (('at euen ','at even ',),'at evening '),(('when euen ','when even '),'when evening '),(('when the euen ','when the even '),'when the evening '),
    (('fro God',),'from God'),
    (('Hooli Goost',),'Holy Ghost'),
    (('righte hade','right honde','riythalf'),'right hand'),
    (('sche felde ',),'she fell '),
    (('the see ',),'the sea '),
    (('we han ',),'we have '),
    (('with greet',),'with great'),

    # Two words into one
    ((' in deede ',' in dede '),' indeed '),
    ((' for o ',),' into '),
    ((' for euer',),' forever'),
    ((' her selfe',' her self',' hir selfe',' hir self'),' herself'),
    ((' hym silf',' hym selfe',' him selfe'),' himself'),
    (('strayght waye','streight waye'),'straightway'),
    (('thy selfe','thi silf','yi self'),'thyself/yourself'),
    ((' to gedder',),' together'),
    (('with outen',),'without'),
    (('youre selues',),'yourselves'),

    # One word into two
    ((' shalbe ',),' shall be '),
    ((' wilbe ',),' will be '),

    # Single words
    ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' abyde ',),' abide '), ((' aboute',),' about'),
        ((' accorde ',' acorde '),' accord '), (('knoulechide',),'acknowledged'),
         ((' afrayed',),' afraid'), ((' aftir',),' after'),(('Aftir',),'After'),
        ((' agaynst',' ayens'),' against'), ((' agayne',' againe'),' again'),(('Againe',),'Again'),
        ((' aliaunt',),' alien/foreigner'), ((' aliue',' alyue',' alyve'),' alive'), ((' alle ',' al '),' all '),(('Alle ',),'All '), ((' aloone',),' alone'), ((' altare',' aulter',' auter'),' altar'),
        (('amased',),'amazed'), ((' amede',),' amend'), ((' amonge',' amoge'),' among'),
        (('Andrewe',),'Andrew'), ((' aungel',),' angel'), (('annoynted',),'annointed'),(('Annoynted',),'Annointed'), (('Anothir',),'Another'), (('answerede','answeride','aunswered'),'answered'),((' aunswere ',' answere '),' answer '), ((' ony ',' eny '),' any '),
        (('apostlis',),'apostles'), (('appearynge','apperynge','apperinge','appearyng'),'appearing'), (('appoynte','apoynte'),'appoint'),
        ((' aryse',),' arise'), ((' arte ',),' art '),
        (('ascencioun',),'ascension'), ((' axiden',' axed'),' asked'), ((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            (('astonnied','astonied','astonnyed','astonyed'),'astonished'),
        ((' athyrst',),' athirst'), ((' attayne ',' attaine '),' attain '),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
    ((' backe ',),' back '), (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            ((' bastardes',),' bastards'),
            ((' batels',),' battles'),
        ((' bee ',),' be '), ((' beare ',' bere '),' bear '), (('beastes','beestes','beestis'),'beasts'),((' beesti',),' beast'), ((' beed ',' bedde '),' bed '), ((' bene ',' ben '),' been '), ((' bifore',' bifor'),' before'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), (('bigynnyng','beginnynge','begynnynge','begynnyng'),'beginning'), (('bigetun ','begotte '),'begotten '),
            (('behelde','biheeld'),'beheld'), ((' behinde',' bihynde',' behynde'),' behind'), ((' biholdinge',),' beholding'),((' biholde',),' behold'), ((' bihoueth',),' behoves'),
            (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), ((' beleue',' beleeue',' beleve',' bileue'),' believe'),
            ((' berith',),' beareth'),
            ((' biseche',),' beseech/implore'), ((' bisidis',),' beside'),
            (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '), (('bitraiede','betraied'),'betrayed'), ((' bitwixe',' betweene',' betwene'),' between'),
            ((' beyonde',' biyende'),' beyond'),
        (('  byde ',),' bide/stay '), ((' bynde',),' bind'),
        ((' bloude',' bloud'),' blood'),
        ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'), ((' bosome ',' bosum '),' bosom '), ((' bothe ',),' both '),((' boundun ',' bounde '),' bound '),
        ((' braunches',),' branches'),((' braunch',' braunche'),' branch'),
            (('britheren',),'brethren/brothers'),(('brithre.',),'brethren/brothers.'), ((' bryde',),' bride'), ((' bryngyng',),' bringing'),
        (('buyldynges','buildynges','bildyngis'),'buildings'),(('buyldinge',),'building'), ((' brent',),' burnt'), ((' busynesse',' busynes',' busines'),' business'),(('businesss',),'business'),
        ((' bi ',),' by '),
    ((' clepide',' clepid'),' called'),((' cal ',),' call '),
            ((' cam ',' camen '),' came '),((' cam,',' camen,'),' came,'), (('Captaine',),'Captain'),
            (('carpeter',),'carpenter'),
            ((' castynge',' castyng',' castinge'),' casting'), (('casteles',),'castles'),
            ((' cattell',' catel'),' cattle'),
        ((' certayne',' certein'),' certain'),
        (('cheynes','chaines'),'chains'), (('chaunced','chaunsed'),'chanced'), (('chastisith','chasteneth'),'chastens/disciplines'),
            ((' cheife ',' chefe '),' chief '), (('chyldren',),'children'), (('chymney',),'chimney'),
            ((' chese ',),' choose '), (('chosun',),'chosen'),
            (('chirche',),'church'), (('Churche ',),'Church '),
            (('Christe','Crist'),'Christ'),
        ((' citees',),' cities'),((' cyte ',' citie '),' city '),
        ((' cloudis',' cloudes'),' clouds'), ((' clouen',),' cloven'),
        ((' cootis',' coottes',' coates',' cotes'),' coats'),
            ((' commeth',' cometh'),' comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming'),' coming'),
                ((' coumfortour',),' comforter'),
                (('commaundementes','commandementes','commandements'),'commandments'),(('commaundement','comaundement','commandement'),'commandment'),(('comaundide','commaunded'),'commanded'), ((' comyn',),' common'),
                (('comprehendiden',),'comprehended'),
            (('confessioun',),'confession'), (('consolacion',),'consolation'), (('contynued',),'continued'),(('contynuynge',),'continuing'), ((' coulde',' coude'),' could'), ((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre'),' country'),
        ((' criede',),' cried'),
        ((' cuppe',),' cup'),
    ((' dayly',' daylie'),' daily'),
            (('derknessis','darkenesse','darknesse','darcknes'),'darkness'),
            ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),
        ((' dekenes',),' deacons'), ((' deed',),' dead'), (('Deare ',),'Dear '),(('deare ',),'dear '), ((' deeth',' deth',' derth'),' death'),
            (('disseyve','disceaue','deceave','deceiue'),'deceive'),
            ((' delyte',),' delight'), ((' deliuered',),' delivered'),((' delyuer ',' deliuer '),' deliver '),
            ((' denyede',' denyed'),' denied'),
            (('Departe ',),'Depart '),((' departe ',),' depart '),
            (('descendinge',),'descending'),(('descende ',),'descend '),
                ((' deseert',),' desert'),
                ((' desirith',' desyreth',' desireth'),' desires'), ((' desyred',),' desired'),
                ((' despysed',' dispiside'),' despised'),((' despyse ',' dispise '),' despise '),
                ((' distriede',),' destroyed'),((' distrie ',' destroye '),' destroy '),
            ((' deuelis',' deuils'),' devils'),((' devyll',' deuell',' deuyll'),' devil'),
        ((' dyd ',' dide '),' did '),((' dieden ',),' died '),
            ((' discerne:',),' discern:'), (('disciplis',),'disciples'), (('disdayned',),'disdained'),(('disdaine ',),'disdain '), (('devided','deuided','deuyded'),'divided'),
        ((' doe ',),' do '),
            (('doctryne',),'doctrine'),
            ((' doist ',),' doest '),
            ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),
            ((' doores',' dores'),' doors'),((' dore',),' door'), ((' doue',),' dove'), ((' downe',' doun'),' down'),
        (('dredde',),'dreaded'), ((' dryncke',' drynke', ' drinke'),' drink'), ((' driueth',' driveth'),' drives'), ((' driue',' dryue'),' drive'), ((' drave',' droue'),' drove'),
        ((' duste ',),' dust '),
        (('dwelliden','dwellide','dwellyde'),'dwelled/dwelt'),(('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
    ((' ech ',),' each '),
            ((' eares ',' eeris '),' ears '), ((' erthe',),' earth'),
            ((' easyer',),' easier'),
            ((' ete ',),' eat '),((' eate,',' ete,'),' eat,'),
        (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
        (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'),
        ((' ende ',),' end '), (('ynough','inough'),'enough'), ((' entred',' entriden',' entride'),' entered'),
        (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'),
        (('Euen ',),'Even '),((' euen ',),' even '), ((' euenyng',),' evening'),((' euentid ',),' eventide/evening '), (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' euery',),' every'), ((' euer ',),' ever '), ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll'),' evil'),
        ((' exercyse ',),' exercise '),
    ((' failinge',),' failing'), ((' faynte ',' faynt '),' faint '), ((' feith',' fayth'),' faith'),
            ((' fadris',),' fathers'),((' fadir',),' father'), ((' fauoure',),' favour'),
        ((' feete',' fete'),' feet'), ((' fel ',),' fell '), ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),
        ((' fielde',' feeld',' felde'),' field'), ((' fygge ',' fyge ',' figge ',' fige ',),' fig '), ((' fiytyng',),' fighting'),(('Fyght',),'Fight'),((' fyght',' fighte'),' fight'),
            ((' fynde ',),' find '),((' fynnyssher',' fynissher',' finissher'),' finisher'),
            ((' fyrste',' firste',' fyrst'),' first'),
            (('fisscheris','fisshers','fysshers'),'fishers'),
            ((' fyue',' fyve',' fiue'),' five'),
        ((' flye ',' fle '),' flee '), ((' flesshe',' fleshe',' fleische',' fleisch'),' flesh'), (('flockis',),'flocks'),
        (('folowed','folewiden'),'followed'), ((' folowe',' folow'),' follow'), (('Folowe','Folow'),'Follow'),
            ((' foote ',),' foot '),
            (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '), ((' forsooke',' forsoke',),' forsook'),((' foorth',),' forth'),
            ((' foond ',' founde '),' found '), ((' fourtie',' fourtye',' fourti'),' forty'), ((' foure',' fower'),' four'),
        ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'),
            ((' freend',' frende'),' friend'),
        ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
    (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'), ((' garmente',),' garment'), (('gadirid',),'gathered'),((' gadere ',' gaddre ',' geder '),' gather '), ((' yaf ',' gaue '),' gave '),
        ((' goost',),' ghost'),
        ((' geve ',' geue ',' giue ',' yyue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'), ((' geven',' giuen',' geuen',' youun', ' youe'),' given'),
        ((' girdil',' gerdyll',' gerdell'),' girdle'),
        ((' glorie',),' glory'),
        ((' goe ',' goo '),' go '), ((' golde ',),' gold '),((' golde.',),' gold.'), ((' goon ',),' gone '), ((' gospell',),' gospel'), (('Gospell',),'Gospel'),
        (('Graunte ','Graunt '),'Grant '),((' graunt ',' graut '),' grant '),
            ((' gretter',),' greater'),((' greate ',' grete '),' great '),
            (('grutchyng',),'groutching/grudging'),
    ((' hadde ',),' had '), ((' heeris',),' hairs'),
            ((' handes',' hondes',' hoondis'),' hands'),((' hande',' honde',' hoond'),' hand'),
            ((' haue ',),' have '), ((' hauynge',' havynge',' hauyng',' hauing'),' having'),
        ((' hee ',),' he '),
        ((' helide',),' healed'), ((' hearde',' herden',' herde',' herd'),' heard'),((' herynge',' hearinge',' hering'),' hearing'),((' heareth',' herith'),' hears'),((' heare',' heere'),' hear'),
            ((' hertis',' hertes',' heartes'),' hearts'), ((' heauens',' heuenes'),' heavens'), ((' heauen',' heuene',' heven'),' heaven'),
            (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), ((' hede ',' heede '),' heed '), ((' hir ',),' her '),((' hir,',),' her,'),((' hir.',),' her.'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), (('Herode ','Eroude '),'Herod '),
        ((' hiyeste',' hiyest'),' highest'),((' hye ',' hie '),' high '),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',),' him:'), (('himselfe',),'himself'),
            ((' hiryd',' hyred'),' hired'), ((' hise ',' hys '),' his '),
        ((' holde ',),' hold '), (('honeste','honestye','honestie'),'honesty'), ((' hony',),' honey'), ((' onoure',),' honour'), ((' houres',),' hours'), ((' housse ',' hous '),' house '),((' housse',),' house'),((' hous,',),' house,'), ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
        ((' hungur',),' hunger'), (('husbande','hosebonde'),'husband'),
    (('Y ',),'I '),
        ((' yf ',),' if '), (('Yf ',),'If '), ((' yt ',),' it '), (('Yt ',),'It '),
        (('encreased',),'increased'), (('indignacioun',),'indignation'), (('interpretacion',),'interpretation'),(('interprete ',),'interpret '),
        (('immediatly',),'immediately'),
    (('iourney',),'journey'),(('Iorney',),'Journey'),
            ((' ioye ',' ioy '),' joy '),
        (('iudgement','iudgment'),'judgement'),((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'), ((' iust ',),' just '),
    ((' keperis',),' keepers'),((' keepe',' kepe'),' keep'),
        (('kingdome','kyngdoom','kyngdome'),'kingdom'), ((' kynges',' kyngis'),' kings'),((' kynge ',' kyng '),' king '), ((' kynnysmen',),' kinsmen'), ((' kynne',),' kin'),
        (('knewest','knewe'),'knew'), (('knowe',),'know'),(('Knowe',),'Know'), (('knowyng',),'knowing'),
    ((' lomb ',' lambe ',' labe '),' lamb '),(('Lambe',),'Lamb'),
            ((' lande ',' londe ',' lond ',' lode '),' land '),((' lande,',' londe,',' lond,'),' land,'),((' lande.',' londe.',' lond.'),' land.'),((' lande;',' londe;',' lond;'),' land;'),
            ((' laye ',),' lay '), ((' layed',' layde',' leiden', ' leyd',' layd'),' laid'),
            ((' lawe ',),' law '),((' lawe,',),' law,'),
        ((' lyfte ',),' left '), (('learnyng','learninge','lernynge'),'learning'),((' learne ',' lerne '),' learn '),(('Learne ','Lerne '),'Learn '), ((' leeues',' leaues',' leves'),' leaves'),
            ((' ledde ',),' led '),
            ((' leften',' leeft',' lefte'),' left'),
            (('Leuite',),'Levite'),
        ((' lyfe',' lijf'),' life'), ((' lyght',' liyt'),' light'), (('lykewyse',),'likewise'),((' lyke',' lijk'),' like'), ((' litil',' lytell',' lytle',' litle'),' little'), ((' liues',),' lives'),((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),
        ((' looues',),' loaves'), ((' loynes',),' loins'), ((' longe ',),' long '),((' longe,',),' long,'), ((' lokide',' loked'),' looked'),(('lokynge',),'looking'),(('Lokyng ',),'Looking '),(('Loke ',),'Look '),
            ((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),
            (('Loth ',),'Lot '),
            ((' louede',' loued',' louyde'),' loved'),((' loueth',' loveth'),' loves'),((' loue ',),' love '),
    ((' maad',),' made'), ((' makynge',),' making'),((' makere ',),' maker '),
            ((' mannus',),' man\'s'),((' ma ',),' man '), ((' maner',),' manner'), ((' manye ',),' many '), (('marueyled','marueiled','merveled','marueled','merveyled'),'marvelled'), ((' maister',),' master'),(('Maister',),'Master'), ((' maye ',),' may '),((' maye.',),' may.'),(('Maye ',),'May '),
        (('meekenes','mekenes','meknes'),'meekness'), ((' mendynge',' mendyng',' mendinge'),' mending'), ((' mesure',),' measure'), ((' `metis ',' metis '),' meats '),
        ((' myddil',),' middle'), ((' myghty',' mightie',' miyti'),' mighty'),((' myyte',' myght'),' might'), ((' myndes',' mindes'),' minds'),((' mynde ',),' mind '), ((' myne ',),' mine '), (('ministred','mynistred','mynystriden'),'ministered'),((' mynyster',' mynister'),' minister'),
        ((' mony',),' money'), (('Moreouer','Morouer'),'Moreover/What\'s_more'), ((' moder ',' modir '),' mother '), ((' moute ',),' mount '), ((' mowe ',),' more '),
        ((' myche',' moche',' moch'),' much'),
    ((' naciouns',),' nations'), ((' natiue',),' native'),
        ((' neere ',' neare '),' near '),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),
            ((' nedes',),' needs'), ((' nether',),' neither'),(('(nether',),'(neither'), ((' nettes',' nettis'),' nets'),
            ((' nexte',),' next'),
        ((' nyy ',' nye '),' nigh/near '),((' nyy.',' nye.'),' nigh/near.'), ((' nyyti',),' night'),
        ((' ner ',),' nor '), (('northwarde',),'northward'),
            (('nothinge','nothyng'),'nothing'),
        (('Nowe ',),'Now '),
        (('numbred',),'numbered'),(('noumbre','nombre','nomber'),'number'),
    ((' oyle ',),' oil '),((' oyle,',),' oil,'),
        (('Olyues',),'Olives'),
        ((' oon ',),' one '), ((' onely ',' `oon '),' only '),
        ((' opynyouns',),' opinions'),
        (('Othir','Wother'),'Other'),
        ((' oure ',),' our '),
        ((' ouer',),' over'),
        ((' awne ',' owne '),' own '),
    ((' parablis',),' parables'), ((' passide',),' passed'),((' passe ',),' pass '),((' passe?',),' pass?'),((' passe:',),' pass:'), ((' pacience',),' patience'),
        (('penaunce',),'penance'),
            (('puplis',),'peoples'),((' puple',' pople'),' people'),
            (('perceiued','perceaved'),'perceived'),(('Perceave','Perceiue'),'Perceive'), ((' perfaicte ',),' perfect '), ((' perische',' perisshe',' perishe'),' perish'), (('Sue ',),'Pursue '),
            (('Petir',),'Peter'),
        (('Fariseis','Pharises'),'Pharisees'), (('Philippe',),'Philip'),
        ((' peaces',' peeces',' peces'),' pieces'), ((' pearced',),' pierced'), ((' pylgrym',),' pilgrim'),
        (('playnely','playnly','plainely'),'plainly'), ((' playne ',' plaine '),' plain '), ((' pleside',' plesid'),' pleased'), ((' plente ',),' plenty '),
        (('possessyoun',),'possession'), ((' powdir',),' powder'),
        (('praysed',),'praised'), (('preyeden',),'prayed'),(('preier',),'prayer'),((' preye ',' praye '),' pray '),
            (('prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ',),'preach '),
            (('preestis','prestis','prestes','priestes'),'priests'),(('Priestes','Prestes'),'Priests'), (('princis','prynces'),'princes'), (('pryuatly',),'privately'),
            (('Prophetes',),'Prophets'),(('profetis','prophetes'),'prophets'), (('Prophete',),'Prophet'),((' prophete ',),' prophet '),((' prophete,',),' prophet,'),((' prophete?',' profete?'),' prophet?'),  ((' proue ',),' prove '),
        (('publysshed',),'published'), ((' pourses',),' purses'),
    (('Rabi',),'Rabbi'), ((' reise',),' raise'),
        ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'), ((' resseyueth',' receaveth',' receaueth',' receiueth'),' receives'),((' resseyueden',' receaved',' receaued',' receiued'),' received'),((' receave',),' receive'), (('recompence',),'recompense'), ((' recorde ',),' record '),
            ((' raygne ',),' reign '),
            (('remayned',),'remained'), (('remyssion','remissioun'),'remission'), (('repentaunce',),'repentance'), (('resurreccion',),'resurrection'),
        ((' riche ',),' rich '), ((' ryght ',' riyt '),' right '), ((' ryghteous',),' righteous'), ((' ryse ',),' rise '),
        ((' rodde ',),' rod/staff '),((' rodde:',),' rod/staff:'), ((' roofe',' rofe'),' roof'), ((' roume',),' room'), ((' roote',' rote'),' root'),
            ((' roos ',),' rose '),
        (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
    (('Sabbathes',),'Sabbaths'),((' sabatys',),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabat',' saboth'),' sabbath'), (('Saduceis','Saduces','Sadduces'),'Sadducees'), ((' saaf',),' safe'), ((' seiden',' seide',' sayde',' sayd',' saide'),' said'), (('Sathanas','Sathan'),'Satan'),
            ((' saued',),' saved'),((' saue ',),' save '), ((' sawe ',' sai '),' saw '),
            ((' seist',),' sayest'),((' sayege',' sayinge'),' saying'), ((' seith ',' sayth '),' saith/says '), ((' seie ',' saye '),' say '),
        (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
        (('seeside',),'seaside'), ((' seet ',),' seat '),
            ((' se ',),' see '), ((' seede ',' sede '),' seed '), ((' seken ',' seeke ',' seke '),' seek '), ((' semen ',' seeme ',' seme '),' seem '), ((' seyn ',' seene ',' sene '),' seen '), ((' silfe ',' silf ',' selfe '),' self '),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'), ((' selues',),' selves'),
            ((' sende ',),' send '), ((' senten ',' sente '),' sent '),
            ((' sermoun',),' sermon'), ((' serue ',),' serve '), (('seruauntis','seruauntes','servauntes','seruants'),'servants'),((' seruaunt',' servaunt',' seruant'),' servant'), ((' seuen ',' seue '),' seven '),
        ((' schal ',' shal ',' schulen '),' shall '),
            ((' sche ',' shee '),' she '), ((' scheep ',' sheepe ',' shepe '),' sheep '),((' scheep,',' sheepe,',' shepe,'),' sheep,'), (('scheepherdis',),'shepherds'),
            (('schyneth','shyneth'),'shineth/shines'), ((' shyppe',' shippe'),' ship'),
            ((' shue',),' shoe'),((' schoo.',),' shoe.'), ((' shoore',),' shore'), (('shouldest',),'should'),((' schulden ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '), (('schewide','shewed'),'showed'),((' schewe ',' shewe '),' show '),
        ((' sicke ',' sijk '),' sick '),((' sicke,',' sijk,'),' sick,'),((' sicke.',' sijk.'),' sick.'),
            ((' syde ',),' side '),((' syde.',),' side.'),((' syde:',),' side:'),
            ((' sighte ',),' sight '),((' sighte,',),' sight,'), ((' signe ',),' sign '),
            ((' siluer',),' silver'),
            (('Symon',),'Simon'),
            ((' synners',),' sinners'),((' synful',),' sinful'),((' sinnes',' synnes'),' sins'),((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),
            ((' sistris',' systers'),' sisters'),((' sistir',),' sister'),
            ((' syttyng',),' sitting'),((' sitten ',' sitte ',' syt '),' sit '),
            ((' sixte ',' sixt '),' sixth '),
        ((' skynne ',' skyn ',' skinne '),' skin '),
        ((' slepe',),' sleep'), ((' slepith',),' sleeps'),
        ((' smale ',),' small '),
        (('Sodome ','zodom '),'Sodom '), ((' soiourne',),' sojourn'), ((' summe ',),' some '), ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,',),'Son,'),
            ((' sorewis',' sorowes'),' sorrows'),
        (('speakynge','spekynge','speakinge','spekinge','speakyng'),'speaking'),((' spekith',' speaketh'),' speaks'),((' speake',),' speak'),
            ((' spyed',),' spied'), ((' spirite',' sprete'),' spirit'),
        ((' staffe ',),' staff '), ((' styll',),' still'), ((' stockis',),' stocks'), ((' stoonys',),' stones'),((' stoone',),' stone'), ((' stoode ',' stode '),' stood '), ((' stoupe',' stowpe'),' stoop'),
            (('strayght',),'straight'), (('straunger',),'stranger'),(('straunge ',),'strange '), ((' strijf ',' stryfe '),' strife '),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'), (('stumbleth','stombleth','stomblith'),'stumbles'),
        ((' souyten',),' sought'), ((' sounde',),' sound'), (('southwarde',),'southward'), (('souereynes',),'sovereigns'),
        (('subiection','subieccion'),'subjection'),((' suget',),' subject'), (('substaunce',),'substance'),
            ((' soch ',' suche ',' siche '),' such '),
            ((' suffride',),' suffered'),
            (('Sommer',),'Summer'),((' sommer ',' somer '),' summer '),
            (('supplicacion',),'supplication'),
        (('synagoge',),'synagogue'),
    (('tabernaclis',),'tabernacles/tents'), ((' takun',),' taken'), ((' takynge',),' taking'),(('Takyng',),'Taking'), ((' tauyte',),' taught'),
        (('techyng','teching'),'teaching'),((' teache',' teche'),' teach'), (('temptid',),'tempted'),
            ((' tendre',' teder'),' tender'), ((' tentes',),' tents'), ((' tenthe',),' tenth'), (('testimoniall',),'testimonial'),
        ((' theyr ',),' their '),
            ((' hem ',),' them '),((' hem.',),' them.'), (('themselues',),'themselves'), ((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),
            ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
            ((' therfore',' therfor'),' therefore'),(('Therfor ',),'Therefore '), ((' thei ',),' they '),
            ((' thyne ',' thine '),' thine/your '), ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'), ((' thyrst',),' thirst'),
            (('thwong',),'thong'), ((' thou ',),' thou/you '),
            ((' trone ',),' throne '), (('thorow ',),'through '), (('throwen',),'thrown'),
            (('thundryng',),'thundering'), (('thounder','thonder'),'thunder'),
        ((' tidynges',),' tidings/news'), ((' tyme',),' time'),
        (('togidir','togidere','togedder'),'together'), ((' tokene ',),' token '), ((' toke ',),' took '), ((' townes',' tounes'),' towns'),
        (('Treuli',),'Truly'), ((' trueth',' treuthe',' verite'),' truth'),
        ((' turnede',),' turned'),((' tourne ',' turne '),' turn '),
        (('twolue','twelue'),'twelve'), ((' twyse',' twise'),' twice'), ((' twei ',' tweyne ',' twey ', ' twaine '),' two '),
    (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'),
        ((' vnderstonde',' vnderstande',' vnderstode',' vnderstand'),' understand'),(('Vnderstonde',),'Understood'), ((' vnder',),' under'), ((' vnloose',),' unloose'),
        (('Untyll ','Vntill '),'Until '),(('vntill','vntyll'),'until'), (('Vnto ',),'Unto '),((' vnto',),' unto'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon ',' apon '),' upon '),(('Vpon ',),'Upon '), ((' vs ',),' us '),((' vs,',),' us,'),((' vs.',),' us.'),
        (('vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'),
            ((' vn',),' un'), # Special case for all remaining un- words
    ((' verely',),' verily'),(('Ueryly','Verely'),'Verily'), ((' vertu',),' virtue'),
        ((' voyce',' vois'),' voice'),
    (('walkynge','walkinge'),'walking'),((' walke ',),' walk '),
             ((' warres',),' wars'),((' warre ',),' war '),
             ((' watred',),' watered'),((' watris',),' waters'),((' watir',),' water'), ((' waye ',' weie ',' weye '),' way '),
        ((' wee ',),' we '), ((' weryed',' weried'),' wearied'),((' weery',' wery'),' weary'), ((' wente ',' wete ',' yede '),' went '), ((' weren ',),' were '), (('westwarde',),'westward'),
        ((' whanne ',' whan '),' when '), ((' whethir',),' whether'), ((' whiche ',),' which '),
            ((' whoale',),' whole'), ((' whome',),' whom'), (('whosoeuer',),'whosoever'),
        ((' wickid',),' wicked'),
            (('widewis','wyddowes','widowes'),'widows'), (('wyldernesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf'),' wife'),
                ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),
                ((' wyndis',' wyndes',' windes'),' winds'), ((' wengis',' wynges'),' wings'),
                (('withouten ',),'without '), (('witnessyng',),'witnessing'),((' wytnesse ',' witnesse ',' witnes '),' witness '),
            (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'),  ((' wi ',' wt '),' with '), (('widdred','wythred','wythered'),'withered'), ((' wyues',),' wives'),
        ((' womman',),' woman'), ((' wymmen',' wemen'),' women'),
            (('wondriden','wondride'),'wondered'),
            ((' worde',),' word'), ((' worke ',' werk '),' work '),((' worke,',' werk,'),' work,'), ((' worlde',),' world'),
            (('worschipide','worshypped'),'worshipped'),
            ((' worthie',' worthi'),' worthy'),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),
    (('Iames',),'Yames'),
            ((' yeres',),' years'),((' yeer',' yeare'),' year'),
                (('Ierusalem','Hierusalem'),'Yerusalem'),
                (('Iesus',),'Yesus'),(('Iesu ',),'Yesu '),
                ((' yit ',),' yet '),
                (('Iewry ',),'Yewry '), (('Iewes ','Jewis '),'Yews '),
            (('Iohn','Ihon','Joon'),'Yohn'),
                (('Iordane ','Iordan ','Iorden ','Iorda ','Jordan '),'Yordan '),(('Iordane,','Iordan,','Iorden,','Iorda,','Jordan,'),'Yordan,'),
            (('Iudas','Ivdas','Judas'),'Yudas'), (('Iuda','Juda'),'Yudah'), (('Iudea','Judee'),'Yudea'),
        (('Ye ',),'Ye/You_all '),((' ye ',' yee '),' ye/you_all '), ((' thi ',' thy '),' thy/your '), ((' youre ',),' your(pl) '),
    (('Zebedeus ','zebede ','Zebede '),'Zebedee '), (('Zebedeus,','zebede,','Zebede,'),'Zebedee,'),

    ((' xl ',),' 40 '),

    ((' & ',),' and '),
    )
oldWords, newWords = [], []
for someOldWords,newWord in ENGLISH_WORD_MAP:
    for someOldWord in someOldWords:
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        oldWords.append( someOldWord)
    assert newWord not in newWords, f"{newWord=}"
    if someOldWords[0].startswith(' '): assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    newWords.append( newWord )
del oldWords, newWords

def moderniseEnglishWords( html:str ) -> bool:
    """
    Convert ancient spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"moderniseEnglishWords( ({len(html)}) )" )

    for oldWords,newWord in ENGLISH_WORD_MAP:
        for oldWord in oldWords:
            html = html.replace( oldWord, newWord )

    return html
# end of html.moderniseEnglishWords

def adjustLatin( html:str ) -> bool:
    """
    Convert ancient Latin spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"adjustLatin( ({len(html)}) )" )

    return html.replace('j','y').replace('J','Y')
# end of html.adjustLatin


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
