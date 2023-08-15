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


LAST_MODIFIED_DATE = '2023-08-15' # by RJH
SHORT_PROGRAM_NAME = "createParallelPages"
PROGRAM_NAME = "OpenBibleData createParallelPages functions"
PROGRAM_VERSION = '0.72'
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
            BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{BBB}/">{ourTidyBBB}</a>''' )
            BBBNextLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''' )

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
    indexHtml = f'''{top}<h1 id="Top">Parallel verse pages</h1>
<p>Each page only contains a single verse with minimal formatting, but displays it in a large number of different versions. Study notes, theme notes, and translation notes will also be displayed, although not every verse has these.</p>
<h2>Index of books</h2>
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
            .replace( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )

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
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating {'TEST ' if TEST_MODE else ''}parallel pages for {BBB} {C}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createParallelVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            for v in range( 0, numVerses+1 ):
                V = str( v )
                # The following all have a __ID__ string than needs to be replaced
                introLink = f'''<a title="Go to book intro" href="Intro.htm#__ID__">B</a> {f'<a title="Go to chapter intro" href="C{c}V0.htm#__ID__">I</a> ' if c!=-1 else ''}'''
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
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about these works" href="{'../'*(level)}allDetails.htm#Top">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introductions <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{introLink}{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>'
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
                    if versionAbbreviation in ('TOSN','TTN','UTN'):
                        continue # We handle the notes separately at the end

                    thisBible = state.preloadedBibles[versionAbbreviation]
                    # thisBible.loadBookIfNecessary( BBB )
                    textHtml = None
                    if versionAbbreviation in state.selectedVersesOnlyVersions: # then thisBible is NOT a Bible object, but a dict
                        ourRef = (BBB,C,V)
                        try:
                            vHtml = thisBible[ourRef].replace( '\\wj ', '<span class="wj">' ).replace( '\\wj*', '</span>' )
                            vHtml =  f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="Go to {versionAbbreviation} copyright info" href="{'../'*level}allDetails.htm#{versionAbbreviation}">{versionAbbreviation}</a></span> {vHtml}</p>
'''
                        except KeyError:
                            vHtml = None # We display nothing at all for these versions that only have a few selected verses
                    else: # should be a Bible object
                        try:
                            if BBB not in thisBible: raise MissingBookError # Requested book is not in this Bible
                            # NOTE: For the book intro, we fetch the whole lot in one go (not line by line)
                            verseEntryList, contextList = thisBible.getContextVerseData( (BBB, C) if c==-1 else (BBB, C, V) )
                            if isinstance( thisBible, ESFMBible.ESFMBible ):
                                verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm#Top", state )
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
                                    halt_on_bad_greek_transcription
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
                                if transcription:
                                    textHtml = f'{textHtml}<br>  ({transcription})'
                                # print( textHtml)
                            elif versionAbbreviation in ('UHB',):
                                # print( f"{versionAbbreviation} {BBB} {C}:{V} {textHtml=}")
                                textHtml = f'{textHtml}<br>  ({transliterate_Hebrew(textHtml)})'
                                # print( textHtml)
                            if textHtml:
                                vHtml = f'''
    <p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#Top">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{C}.htm#Top">OET-RV</a>)</span> {textHtml}</p>
    ''' if versionAbbreviation=='OET-RV' else f'''
    <p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} chapter" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top">{versionAbbreviation}</a></span> {textHtml}</p>
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
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
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
                                vHtml = f'''<p id="{versionAbbreviation}" class="parallelVerse"><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm#Top">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
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

                if c == -1: # Handle Tyndale book intro summaries and book intros
                    tbisHtml = formatTyndaleBookIntro( 'TBIS', level, BBB, 'parallel', state )
                    if tbisHtml:
                        tbisHtml = f'''<div id="TBIS" class="parallelTBI"><a title="Go to TSN copyright page" href="{'../'*level}TSN/details.htm#Top">TBIS</a> <b>Tyndale Book Intro Summary</b>: {tbisHtml}</div><!--end of TBI-->\n'''
                        pHtml = f'{pHtml}{tbisHtml}'
                    tbiHtml = formatTyndaleBookIntro( 'TBI', level, BBB, 'parallel', state )
                    if tbiHtml:
                        tbiHtml = f'''<div id="TBI" class="parallelTBI"><a title="Go to TSN copyright page" href="{'../'*level}TSN/details.htm#Top">TBI</a> <b>Tyndale Book Intro</b>: {tbiHtml}</div><!--end of TBI-->\n'''
                        pHtml = f'{pHtml}{tbiHtml}'

                # Handle Tyndale open study notes and theme notes
                tsnHtml = formatTyndaleNotes( 'TOSN', level, BBB, C, V, 'parallel', state )
                if tsnHtml:
                    tsnHtml = f'''<div id="TSN" class="parallelTSN"><a title="Go to TSN copyright page" href="{'../'*level}TSN/details.htm#Top">TSN</a> <b>Tyndale Study Notes</b>: {tsnHtml}</div><!--end of TSN-->\n'''
                    pHtml = f'{pHtml}{tsnHtml}'
                ttnHtml = formatTyndaleNotes( 'TTN', level, BBB, C, V, 'parallel', state )
                if ttnHtml:
                    ttnHtml = f'''<div id="TTN" class="parallelTTN"><a title="Go to TSN copyright page" href="{'../'*level}TSN/details.htm#Top">TTN</a> <b>Tyndale Theme Notes</b>: {ttnHtml}</div><!--end of TTN-->\n'''
                    pHtml = f'{pHtml}{ttnHtml}'
                # Handle uW translation notes
                utnHtml = formatUnfoldingWordTranslationNotes( level, BBB, C, V, 'parallel', state )
                if utnHtml:
                    utnHtml = f'''<div id="UTN" class="parallelUTN"><a title="Go to UTN copyright page" href="{'../'*level}UTN/details.htm#Top">UTN</a> <b>uW Translation Notes</b>: {utnHtml}</div><!--end of UTN-->\n'''
                    pHtml = f'{pHtml}{utnHtml}'

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'parallel', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {C}:{V} Parallel View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {ourTidyBBB}, parallel' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*level}il/"''', f'''href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top"''')
                pHtml = f'''{top}<!--parallel verse page-->
{adjBBBLinksHtml}
<h1>Parallel {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>
<p class="rem">Note: This view shows ‘verses’ which are not natural language units and hence sometimes only part of a sentence will be visible. This view is only designed for doing comparisons of different translations. Click on the version abbreviation to see the verse in more of its context.</p>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{pHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( level, 'parallel', state )}'''
                checkHtml( f'Parallel {BBB} {C}:{V}', pHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( pHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(pHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to parallel verse page" href="{filename}#Top">{C}:{V}</a>' )
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
    introLinks = [ '<a title="Go to parallel intro page" href="Intro.htm#Top">Intro</a>' ]
    ourLinks = f'''<h1 id="Top">{ourTidyBBB} parallel songs index</h1>
<p class="chLst">{EM_SPACE.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/(James)'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
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
    # Pairs of words (two words to two words)
    ((' a boot',),' a boat'),
    ((' a none ',),' anon '),
    (('at euen ','at even ',),'at evening '),(('when euen ','when even '),'when evening '),(('when the euen ','when the even '),'when the evening '),
    (('fro God',),'from God'),
    (('get bred',),'get bread'),
    (('Hooli Goost',),'Holy Ghost'),
    (('loves have',),'loaves have'),
    (('righte hade','right honde','riythalf'),'right hand'),
    (('sche felde ',),'she fell '),
    (('swete breed','swete bred'),'sweet bread'),
    (('the see ',),'the sea '),
    (('we han ',),'we have '),
    (('with greet',),'with great'),

    # Two words into one word
    (('a fore honde','afore hand','aforehande'),'aforehand'),
    ((' in deede ',' in dede '),' indeed '),
    (('fare wel ',),'farewell '),
    ((' for o ',),' into '),
    ((' for euer',),' forever'),
    ((' her selfe',' her self',' hir selfe',' hir self'),' herself'),
    ((' hym silf',' hym selfe',' him selfe'),' himself'),
    (('strayght waye','streight waye'),'straightway'),
    (('them selues',),'themselves'),
    (('thy selfe','thi silf','yi self'),'thyself/yourself'),
    ((' to gedder',' to geder',' to gidir'),' together'),
    (('with outen',),'without'),
    (('youre selues',),'yourselves'),

    # One word into two
    ((' shalbe ',),' shall be '),
    ((' wilbe ',),' will be '),

    # Change single words (esp. middle English)
    ((' reuth ',),' pity/sorrow '),

    # Single words
    ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' abyde ',),' abide '), ((' aboute',),' about'),
        ((' accorde ',' acorde '),' accord '), (('knoulechide',),'acknowledged'),
         ((' afrayed',),' afraid'), ((' aftir',),' after'),(('Aftir',),'After'),
        ((' agaynst',' ayens'),' against'), ((' agayne',' againe'),' again'),(('Againe',),'Again'),
        ((' aliaunt',),' alien/foreigner'), ((' aliue',' alyue',' alyve'),' alive'),
            ((' alle ',' al '),' all '),(('Alle ',),'All '),
            ((' aloone',),' alone'),
            ((' altare',' aulter',' auter'),' altar'),
            ((' alwayes',' alwaies',' allwaie'),' always'),
        (('amased',),'amazed'), ((' amede',),' amend'), ((' amonge',' amoge'),' among'),
        (('Andrewe',),'Andrew'), ((' aungel',),' angel'), (('anoyntiden','annoynted','anoynted'),'anointed'),(('Annoynted',),'Anointed'),((' annoynt',' anoynte',' anoynt'),' anoint'),
            ((' anoon ',' anone ',' anon '),' anon/immediately '), (('Anothir',),'Another'),
            (('answerden','answerede','answeride','aunswered'),'answered'),((' aunswere ',' answere '),' answer '), ((' ony ',' eny '),' any '),
        (('apostlis',),'apostles'), (('appearynge','apperynge','apperinge','appearyng'),'appearing'), (('appoynte','apoynte'),'appoint'),
        ((' aryse',),' arise'),(('Aryse ',),'Arise '), ((' arte ',),' art '),
        (('ascencioun',),'ascension'), ((' axiden',' axide',' axed'),' asked'), ((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            (('astonnied','astonied','astonnyed','astonyed'),'astonished'),
        ((' eeten,',' eten,'),' ate,'), ((' athyrst',),' athirst'), ((' attayne ',' attaine '),' attain '),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
        ((' awaye',),' away'),
    ((' backe ',),' back '), (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            (('basskettes','baskettes'),'baskets'), (('bastardes',),'bastards'),
            ((' batels',),' battles'),
        ((' bee ',),' be '), ((' bearinge',' beringe',' berynge'),' bearing'),((' beare ',' bere '),' bear '), (('beastes','beestes','beestis'),'beasts'),((' beesti',),' beast'), ((' beed ',' bedde '),' bed '), ((' bene ',' ben '),' been '), ((' bifore',' bifor'),' before'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), (('bigynnyng','beginnynge','begynnynge','begynnyng'),'beginning'), (('bigetun ','begotte '),'begotten '),
            (('behelde','biheeld'),'beheld'), ((' behinde',' bihynde',' behynde'),' behind'), ((' biholdinge',),' beholding'),((' biholde',),' behold'), ((' bihoueth',),' behoves'),
            (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), ((' beleue',' beleeue',' beleve',' bileue'),' believe'),
            ((' berith',),' beareth'),
            (('besechyng','beseeching'),'beseeching/imploring'),((' biseche',' beseech'),' beseech/implore'), ((' bisidis',),' beside'),
            (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '), (('bitraiede','betraied'),'betrayed'),(('bitraye ','betraye ','betraie '),'betray '), ((' bitwixe',' betweene',' betwene'),' between'),
            ((' beyonde',' biyende'),' beyond'),
        ((' byde ',),' bide/stay '), ((' bynde',),' bind'),
        (('Blessid ',),'Blessed '),(('blesside',),'blessed'),
            (('blynde','blinde'),'blind'),
            (('bloude','bloud'),'blood'),
        ((' bootys',),' boats'),
            ((' boddy ',' bodi '),' body '),
            ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'),
            ((' bosome ',' bosum '),' bosom '),
            ((' bothe ',),' both '),
            ((' boundun ',' bounde '),' bound '),
        ((' braunches',),' branches'),((' braunch',' braunche'),' branch'),
            (('britheren',),'brethren/brothers'),(('brithre.',),'brethren/brothers.'), ((' bryde',),' bride'), ((' bryngyng',),' bringing'),
        (('buyldynges','buildynges','bildyngis'),'buildings'),(('buyldinge',),'building'),
            ((' buriall',),' burial'),((' buryinge',' biriyng'),' burying'), ((' brent',),' burnt'),
            ((' busynesse',' busynes',' busines'),' business'),(('businesss',),'business'),
        ((' bi ',),' by '),
    ((' clepide',' clepid'),' called'),((' cal ',),' call '),
            ((' cam ',' camen '),' came '),((' cam,',' camen,'),' came,'),
            (('Captaine','Captayne'),'Captain'), (('captiues',),'captives'),(('captyue',),'captive'),
            (('carpeter',),'carpenter'),
            ((' castynge',' castyng',' castinge'),' casting'),((' castiden ',' caste '),' cast '), (('casteles',),'castles'),
            ((' cattell',' catel'),' cattle'),
        (('centurien',),'centurion'), ((' certayne',' certein'),' certain'),
        (('cheynes','chaines'),'chains'), (('chamber','chaumber','chambre'),'chamber/room'), (('chaunced','chaunsed'),'chanced'), (('chastisith','chasteneth'),'chastens/disciplines'),
            ((' cheife ',' chefe '),' chief '), (('chyldren',),'children'), (('chymney',),'chimney'),
            ((' chese ',),' choose '), (('chosun',),'chosen'),
            (('chirche',),'church'),(('Churche ',),'Church '),(('Churche,',),'Church,'),
            (('Christe','Crist'),'Christ'),
        ((' citees',),' cities'),((' cyte ',' citie ',' citee '),' city '),((' citie,',' citee,',' cite,'),' city,'),((' citie.',' citee.',' cite.'),' city.'),
        ((' cloudis',' cloudes'),' clouds'), ((' clouen',),' cloven'),
        ((' coostis',' coastes'),' coasts'), ((' cootis',' coottes',' coates',' cotes'),' coats'),
            ((' commeth',' cometh'),' comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming'),' coming'),
                ((' coumfortour',),' comforter'),
                (('commaundementes','commandementes','commandements'),'commandments'),(('commaundement','comaundement','commandement'),'commandment'),(('comaundide','commaunded'),'commanded'), ((' comyn',),' common'),
                (('companye',),'company'), (('comprehendiden',),'comprehended'),
            (('confessioun',),'confession'), (('congregacion',),'congregation'), (('consolacion',),'consolation'), (('contynued',),'continued'),(('contynuynge',),'continuing'), (('conueniently','coueniently'),'conveniently'),
            ((' corne ',),' corn '),
            ((' coulde',' coude'),' could'), ((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre'),' country'),
        ((' criede',),' cried'), (('coroun ','croune ','crowne ',),'crown '),
        ((' cuppe',),' cup'),
    ((' dayly',' daylie'),' daily'),
            (('derknessis','darkenesse','darknesse','darcknes'),'darkness'),
            ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),((' daye:',' daie:',' dai:'),' day:'),
        ((' dekenes',),' deacons'), ((' deed',),' dead'), (('Deare ',),'Dear '),(('deare ',),'dear '), ((' deeth',' deth',' derth'),' death'),
            (('disseyve','disceaue','deceave','deceiue'),'deceive'),
            ((' delyte',),' delight'), (('delyuerauce','deliueraunce','deliuerance'),'deliverance'),((' deliuered',),' delivered'),((' delyuer ',' deliuer '),' deliver '),
            ((' denyede',' denyed'),' denied'),
            (('Departe ',),'Depart '),((' departe ',),' depart '),
            (('descendinge',),'descending'),(('descende ',),'descend '),
                ((' deseert',),' desert'),
                ((' desirith',' desyreth',' desireth'),' desires'), ((' desyred',),' desired'),
                ((' despysed',' dispiside'),' despised'),((' despyse ',' dispise '),' despise '),
                ((' distriede',),' destroyed'),((' distrie ',' destroye '),' destroy '),
            ((' deuelis',' devylles',' deuils',' deuyls'),' devils'),((' devyll',' deuell',' deuyll'),' devil'),
        ((' dyd ',' dide '),' did '),((' dieden ',),' died '),
            ((' discerne:',),' discern:'), (('disciplis',),'disciples'), (('disdayned',),'disdained'),(('disdaine ',),'disdain '),
                ((' dyvers',' diuers'),' diverse/various'), (('devided','deuided','deuyded'),'divided'),
        ((' doe ',),' do '),
            (('doctryne',),'doctrine'),
            ((' doist ',),' doest '),
            ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),
            ((' doores',' dores'),' doors'),((' doore',' dore'),' door'),
            ((' doue',),' dove'),
            ((' downe',' doune',' doun'),' down'),
        (('dredde',),'dreaded'), ((' dryncke',' drynke', ' drinke'),' drink'), ((' driueth',' driveth'),' drives'), ((' driue',' dryue'),' drive'),
            ((' drave',' droue'),' drove'), ((' drie ',),' dry '),
        ((' duste ',),' dust '),
        (('dwelliden','dwellide','dwellyde'),'dwelled/dwelt'),(('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
    ((' ech ',),' each '),
            ((' eares ',' eeris ',' eris '),' ears '), ((' erthe',),' earth'),
            ((' easyer',),' easier'),
            ((' etynge',),' eating'),((' eate ',' ete '),' eat '),((' eate,',' ete,'),' eat,'),((' eate.',' ete.'),' eat.'),((' eate:',' ete:'),' eat:'),((' eate;',' ete;'),' eat;'),
        (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
        (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'),
        ((' ende ',),' end '), (('ynough','inough'),'enough'), ((' entred',' entriden',' entride',' entrid'),' entered'),
        (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'),
        (('Euen ',),'Even '),((' euen ',),' even '), ((' euenyng',),' evening'),((' euentid ',),' eventide/evening '), (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' euermore',),' evermore'), ((' euery',),' every'), ((' euer ',),' ever '), ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll'),' evil'),
        ((' exercyse ',),' exercise '),
    ((' failinge',),' failing'), ((' faynte ',' faynt '),' faint '), ((' feith',' fayth'),' faith'),
            ((' farre ',),' far '),((' farre.',' fer'),' far.'),
            ((' fastynge',' fastyng',' fastinge'),' fasting'),
            ((' fadris',),' fathers'),((' fadir',),' father'), ((' fauoure',),' favour'),
        ((' feete',' fete'),' feet'), ((' fel ',),' fell '), ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),
        ((' fielde',' feeld',' felde'),' field'), ((' feendis',),' fiends'),
            ((' fygge ',' fyge ',' figge ',' fige ',),' fig '), ((' fiytyng',),' fighting'),(('Fyght',),'Fight'),((' fyght',' fighte'),' fight'),
            ((' fynde ',),' find '),((' fynnyssher',' fynissher',' finissher'),' finisher'),
            ((' fyrste',' firste',' fyrst'),' first'),
            (('fischis','fysshes','fyshes'),'fishes'),(('fisscheris','fisshers','fysshers'),'fishers'),
            ((' fyue',' fyve',' fiue'),' five'),
        ((' flye ',' fle '),' flee '), ((' flesshe',' fleshe',' fleische',' fleisch'),' flesh'), (('flockis',),'flocks'),
        (('folowed','folewiden'),'followed'), ((' folowe',' folow'),' follow'), (('Folowe','Folow'),'Follow'),
            ((' foote ',),' foot '),
            (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '), ((' forsooke',' forsoke',),' forsook'),((' foorth',),' forth'),
            ((' foond ',' founde '),' found '), ((' fourtie',' fourtye',' fourti'),' forty'), ((' fowre',' foure',' fower'),' four'),
        ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'),
            ((' freend',' frende'),' friend'), (('Fro ',),'From '),
        ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
    (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'), ((' galoun',),' gallon'),
            ((' garmente',),' garment'),
            ((' yate',),' gate'), (('gadirid','gadered'),'gathered'),((' gadere ',' gaddre ',' geder '),' gather '),
            ((' yaf ',' gaue '),' gave '),
        ((' gentyls',),' gentiles'),
        ((' goost',),' ghost'),
        ((' geve ',' geue ',' giue ',' yyue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'), ((' geven',' giuen',' geuen',' youun', ' youe'),' given'),
        ((' girdil',' gerdyll',' gerdell'),' girdle'),
        ((' gladde ',),' glad '), ((' glorie',),' glory'),
        (('Goo ',),'Go '),((' goe ',' goo '),' go '), ((' golde ',),' gold '),((' golde.',),' gold.'), ((' goon ',),' gone '), ((' gospell',),' gospel'), (('Gospell',),'Gospel'),
        (('Graunte ','Graunt '),'Grant '),((' graunt ',' graut '),' grant '),
            ((' gretter',),' greater'),((' greate ',' grete '),' great '),
            (('grounde',),'ground'), (('grutchyng',),'groutching/grudging'),
        ((' ghest',' geest',' gest'),' guest'),
    ((' hadden ',' hadde '),' had '),((' hadde;',),' had;'), ((' heeris',),' hairs'),
            ((' handes',' hondes',' hoondis'),' hands'),((' hande',' honde',' hoond'),' hand'),
            ((' haue ',),' have '), ((' hauynge',' havynge',' hauyng',' hauing'),' having'),
        ((' hee ',),' he '),
            ((' helide',' heelid'),' healed'), ((' hearde',' herden',' herde',' herd'),' heard'),((' herynge',' hearinge',' hering'),' hearing'),((' heareth',' herith'),' hears'),((' heare',' heere'),' hear'),
            (('Heythen',),'Heathen'),((' hethene',),' heathen'), 
            ((' hertis',' hertes',' heartes'),' hearts'), ((' heauens',' heuenes'),' heavens'), ((' heauen',' heuene',' heven'),' heaven'),
            (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), ((' hede ',' heede '),' heed '), ((' hir ',),' her '),((' hir,',),' her,'),((' hir.',),' her.'),((' hir;',),' her;'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), (('Herode ','Eroude '),'Herod '),
        ((' hiyeste',' hiyest'),' highest'),((' hye ',' hie '),' high '),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',),' him:'),((' hym?',),' him?'), (('himselfe',),'himself'),
            ((' hiryd',' hyred'),' hired'), ((' hise ',' hys '),' his '),
        ((' holde ',),' hold '), (('honeste','honestye','honestie'),'honesty'), ((' hony',),' honey'), ((' onoure',),' honour'), ((' houres',),' hours'), ((' housse ',' hous '),' house '),((' housse',),' house'),((' hous,',),' house,'), ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
        ((' hungur',),' hunger'), (('husbande','hosebonde'),'husband'),
    (('Y ',),'I '),
        ((' yf ',),' if '), (('Yf ',),'If '), ((' ys ',),' is '), ((' yt ',),' it '), (('Yt ',),'It '),
        (('encreased',),'increased'), (('indignacioun',),'indignation'), (('interpretacion',),'interpretation'),(('interprete ',),'interpret '),
        (('immediatly',),'immediately'),
    (('iourney',),'journey'),(('Iorney',),'Journey'),
            ((' ioye ',' ioy '),' joy '),
        (('iudgement','iudgment'),'judgement'),((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'), ((' iust ',),' just '),
    ((' keperis',),' keepers'),((' keepe',' kepe'),' keep'), ((' keyes',' keies'),' keys'),
        ((' kylled',),' killed'), (('kingdome','kyngdoom','kyngdome','kyngdom'),'kingdom'), ((' kynges',' kyngis'),' kings'),((' kynge ',' kyng '),' king '), ((' kynnysmen',),' kinsmen'), ((' kynne',),' kin'),
        (('knewest','knewe'),'knew'), (('knowe',),'know'),(('Knowe',),'Know'), (('knowyng',),'knowing'),
    ((' lomb ',' lambe ',' labe '),' lamb '),(('Lambe',),'Lamb'),
            ((' lande ',' londe ',' lond ',' lode '),' land '),((' lande,',' londe,',' lond,'),' land,'),((' lande.',' londe.',' lond.'),' land.'),((' lande;',' londe;',' lond;'),' land;'),
            ((' laye ',),' lay '), ((' layed',' layde',' leiden', ' leyd',' layd'),' laid'),
            ((' leeueful',' laufull',' lawfull'),' lawful'), (('Lawe.',),'Law.'),((' lawe ',),' law '),((' lawe,',),' law,'),((' lawe.',),' law.'),
        (('learnyng','learninge','lernynge'),'learning'),((' learne ',' lerne '),' learn '),(('Learne ','Lerne '),'Learn '), ((' leeues',' leaues',' leves'),' leaves'), ((' leeue ',' leaue ',' leue '),' leave '),
            ((' ledde ',),' led '),
            ((' leften',' leeft',' lefte'),' left'),
            (('Leuite',),'Levite'),
        (('lyberte','libertie'),'liberty'),
            ((' lyfe',' lijf'),' life'),
            ((' lyght',' liyt'),' light'),
            (('lykewyse',),'likewise'),((' lyke',' lijk'),' like'),
            ((' litil',' lytell',' lytle',' litle'),' little'),
            ((' liues',),' lives'),((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),
        ((' looues',' loaues'),' loaves'), ((' loynes',),' loins'), ((' longe ',),' long '),((' longe,',),' long,'), ((' lokide',' loked'),' looked'),(('lokynge',),'looking'),(('Lokyng ',),'Looking '),(('Loke ',),'Look '),
            ((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),
            (('Loth ',),'Lot '),
            ((' louede',' loued',' louyde'),' loved'),((' loueth',' loveth'),' loves'),((' louen ',' loue '),' love '),
    ((' maad',),' made'), ((' makynge',),' making'),((' makere ',),' maker '),
            ((' mannus',),' man\'s'),((' ma ',),' man '), ((' maner',),' manner'), ((' manye ',),' many '),
            (('marueyled','marueiled','merveled','marueled','merveyled'),'marvelled'),
            ((' maister',),' master'),(('Maister',),'Master'),
            ((' mayest',' mayst'),' mayest/may'),((' maye ',),' may '),((' maye.',),' may.'),(('Maye ',),'May '),
        ((' meate ',),' meat '),
            ((' meete ',' mete '),' meet '), (('meekenes','mekenes','meknes'),'meekness'), ((' mendynge',' mendyng',' mendinge'),' mending'), ((' mesure',),' measure'), ((' `metis ',' metis '),' meats '),
        ((' myddil',),' middle'),
            ((' myghty',' mightie',' miyti'),' mighty'),((' myyte',' myght'),' might'),
            ((' myndes',' mindes'),' minds'),((' mynde',),' mind'), ((' myne ',),' mine '), (('ministred','mynistred','mynystriden'),'ministered'),((' mynyster',' mynister'),' minister'),
        ((' mony',),' money'), (('Moreouer','Morouer'),'Moreover/What\'s_more'), ((' moder ',' modir '),' mother '), ((' moute ',),' mount '), ((' mowe ',),' more '),
        ((' myche',' moche',' moch',' muche'),' much'),
    ((' naciouns',),' nations'), ((' natiue',),' native'),
        ((' neere ',' neare '),' near '),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),
            ((' nedes',),' needs'), ((' nether',),' neither'),(('(nether',),'(neither'), ((' nettes',' nettis'),' nets'),
            ((' nexte',),' next'),
        ((' nyy ',' nye '),' nigh/near '),((' nyy.',' nye.'),' nigh/near.'), ((' nyyti',),' night'),
        ((' ner ',),' nor '), (('northwarde',),'northward'),
            (('nothinge','nothyng'),'nothing'),
        (('Nowe ',),'Now '),((' nowe ',),' now '),
        (('numbred',),'numbered'),(('noumbre','nombre','nomber'),'number'),
    ((' oyle ',),' oil '),((' oyle,',),' oil,'),
        (('Olyues',),'Olives'),
        ((' oon ',),' one '), ((' onely ',' `oon '),' only '),
        ((' opynyouns',),' opinions'),
        (('Othir','Wother'),'Other'),
        ((' oure ',),' our '),
        ((' ouer',),' over'),
        ((' awne ',' owne '),' own '),
    ((' parablis',),' parables'), ((' parts',' parties'),' parts/region'),
            (('Passeouer','Passouer'),'Passover'),((' passide',),' passed'),((' passe ',),' pass '),((' passe?',),' pass?'),((' passe:',),' pass:'),
            ((' pacience',),' patience'),
        (('penaunce',),'penance'),
            (('puplis',),'peoples'),((' puple',' pople'),' people'),
            (('perceiued','perceaved'),'perceived'),(('Perceave','Perceiue'),'Perceive'), ((' perfaicte ',),' perfect '), ((' perische',' perisshe',' perishe'),' perish'), (('Sue ',),'Pursue '),
            (('Petir',),'Peter'),
        (('Fariseis','Pharises'),'Pharisees'), (('Philippe',),'Philip'),
        ((' peaces',' peeces',' peces'),' pieces'), ((' pearced',),' pierced'), ((' pylgrym',),' pilgrim'),
        (('playnely','playnly','plainely'),'plainly'), ((' playne ',' plaine '),' plain '),
            ((' pleside',' plesid'),' pleased'), ((' plente ',),' plenty '),
            ((' plucke ',),' pluck '),
        ((' poore ',' povre ',' pore '),' poor '), (('possessyoun',),'possession'), ((' powdir',),' powder'),
        (('praysed',),'praised'), (('preyeden',),'prayed'),(('preier',),'prayer'),((' preye ',' praye '),' pray '),
            (('prechiden','prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ','preache '),'preach '),
            (('preestis','prestis','prestes','priestes'),'priests'),(('Priestes','Prestes'),'Priests'),(('prieste','preste','prest',),'priest'), (('princis','prynces'),'princes'),
                (('prisouneris','presoners'),'prisoners'), (('pryuatly',),'privately'),
            (('promysed','bihiyten'),'promised'), (('Prophetes',),'Prophets'),(('profetis','prophetes'),'prophets'), (('Prophete',),'Prophet'),((' prophete ',),' prophet '),((' prophete,',),' prophet,'),((' prophete.',),' prophet.'),((' prophete?',' profete?'),' prophet?'),
                ((' preued',),' proved'),((' proue ',),' prove '),
        (('publysshed',),'published'), ((' pourses',),' purses'),
    (('Rabi',),'Rabbi'), ((' raysed',),' raised'),((' reise',),' raise'),
        ((' redi ',),' ready '), ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'),
            ((' resseyueth',' receaveth',' receaueth',' receiueth'),' receives'),((' resseyueden',' receaved',' receaued',' receiued'),' received'),((' resseyue',' receave',' receaue',' receiue'),' receive'), (('recompence',),'recompense'), ((' recorde ',),' record '), (('recouering',),'recovering'),
            ((' raygne ',),' reign '),
            (('remayned',),'remained'), (('remembraunce',),'remembrance'), (('remyssion','remissioun'),'remission'),
            (('repentaunce',),'repentance'),
            (('resurreccion',),'resurrection'),
        ((' riche ',),' rich '), ((' ryght ',' riyt '),' right '), ((' ryghteous',),' righteous'), ((' ryse ',),' rise '),
        ((' rodde ',),' rod/staff '),((' rodde:',),' rod/staff:'),
            ((' roofe',' rofe'),' roof'), ((' roume',' rowme'),' room'), ((' roote',' rote'),' root'),
            ((' roos ',),' rose '),
        (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
    (('Sabbathes',),'Sabbaths'),((' sabatys',),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabat',' saboth'),' sabbath'), (('Saduceis','Saduces','Sadduces'),'Sadducees'), ((' saaf',),' safe'), ((' seiden',' seide',' sayde',' sayd',' saide'),' said'),
            (('Sathanas','Sathan'),'Satan'), ((' satisfie ',),' satisfy '),
            ((' saued',),' saved'),((' saue ',),' save '),
            ((' sawe ',' sai '),' saw '),
            ((' seist',),' sayest'),((' sayege',' sayinge'),' saying'), ((' seith ',' sayth '),' saith/says '), ((' seie ',' saye '),' say '),
        (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
        (('seeside',),'seaside'), ((' seet ',),' seat '),
            ((' se ',),' see '), ((' seede ',' sede '),' seed '), ((' seken ',' seeke ',' seke '),' seek '), ((' semen ',' seeme ',' seme '),' seem '), ((' seyn ',' seene ',' sene '),' seen '), ((' silfe ',' silf ',' selfe '),' self '),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'), ((' selues',),' selves'),
            ((' sendeth',' sendith'),' sendeth/sends'),((' sende ',),' send '), ((' senten ',' sente '),' sent '),
            ((' sermoun',),' sermon'), ((' serue ',),' serve '), (('seruauntis','seruauntes','servauntes','seruants'),'servants'),((' seruaunt',' servaunt',' seruant'),' servant'),
            ((' sette ',),' set '),
            (('seuenthe ','seuenth '),'seventh '),((' seuene ',' seuen ',' seue '),' seven '),
        ((' schal ',' shal ',' schulen '),' shall '),
            (('Sche ',),'She '),((' sche ',' shee '),' she '), ((' scheep ',' sheepe ',' shepe '),' sheep '),((' scheep,',' sheepe,',' shepe,'),' sheep,'), (('scheepherdis',),'shepherds'),
            (('schyneth','shyneth'),'shineth/shines'), ((' shippes',),' ships'),((' shyppe',' shyp',' shippe',' schip'),' ship'),
            ((' shue',),' shoe'),((' schoo.',),' shoe.'), ((' shoore',),' shore'), (('shouldest',),'should'),((' schulden ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '), (('schewide','shewed'),'showed'),((' schewe ',' shewe '),' show '),
        ((' sicke ',' sijk '),' sick '),((' sicke,',' sijk,'),' sick,'),((' sicke.',' sijk.'),' sick.'),
            ((' syde ',),' side '),((' syde.',),' side.'),((' syde:',),' side:'),
            ((' syght ',' sighte '),' sight '),((' sighte,',),' sight,'), ((' signe ',),' sign '),
            ((' siluer',),' silver'),
            (('Symon',),'Simon'),
            ((' synners',),' sinners'),((' synful',),' sinful'),((' sinnes',' synnes'),' sins'),((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),
            ((' sistris',' systers'),' sisters'),((' sistir',),' sister'),
            ((' syttyng',),' sitting'),((' sitten ',' sitte ',' syt '),' sit '),
            ((' sixte ',' sixt '),' sixth '),
        ((' skynne ',' skyn ',' skinne '),' skin '),
        ((' slayn',' slaine'),' slain/killed'), ((' slepe',),' sleep'), ((' slepith',),' sleeps'),
        ((' smale ',),' small '),
        (('Sodome ','zodom '),'Sodom '), ((' soiourne',),' sojourn'), ((' summe ',),' some '), ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,',),'Son,'),
            ((' sorewis',' sorowes'),' sorrows'),
            ((' souyten',),' sought'), ((' sounde',),' sound'), (('southwarde',),'southward'), (('souereynes',),'sovereigns'),
        (('speakynge','spekynge','speakinge','spekinge','speakyng'),'speaking'),((' spekith',' speaketh'),' speaks'),((' speake',),' speak'),
            ((' spyed',),' spied'), ((' spirite',' sprete'),' spirit'),
            ((' spak ',),' spoke '),
        ((' staffe ',),' staff '), ((' stande ',),' stand '),
            (('Steppe ',),'Step '),
            ((' styll',),' still'),
            ((' stockis',),' stocks'), ((' stoonys',),' stones'),((' stoone',),' stone'), ((' stoode ',' stode '),' stood '), ((' stoupe',' stowpe'),' stoop'),
            (('strayght',),'straight'), (('straunger',),'stranger'),(('straunge ',),'strange '), ((' strijf ',' stryfe '),' strife '),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'), (('stumbleth','stombleth','stomblith'),'stumbles'),
        (('subiection','subieccion'),'subjection'),((' suget',),' subject'), (('substaunce',),'substance'),
            ((' soch ',' suche ',' siche '),' such '),
            (('suffrith',),'suffereth/suffers'),((' suffride',),' suffered'),(('Suffre ',),'Suffer '),((' suffre ',),' suffer '), (('suffysed','suffised'),'sufficed'),
            (('Sommer',),'Summer'),((' sommer ',' somer '),' summer '),
            (('supplicacion',),'supplication'),
        (('swete ',),'sweet '),
        (('synagoge',),'synagogue'),
    (('tabernaclis',),'tabernacles/tents'), ((' takun',),' taken'), ((' taried',),' tarried/waited'), ((' takynge',),' taking'),(('Takyng',),'Taking'), ((' tauyte',),' taught'),
        (('techyng','teching'),'teaching'),((' teache',' teche'),' teach'),
            (('temptacioun','temptacion','teptacion','tentation'),'temptation'), (('temptid',),'tempted'),
            ((' tendre',' teder'),' tender'), ((' tentes',),' tents'), ((' tenthe',),' tenth'),
            (('testifie ','testifye '),'testify '), (('testimoniall',),'testimonial'),
        (('thankes','thakes'),'thanks'), ((' theyr ',),' their '),
            ((' hem ',),' them '),((' hem.',' the.'),' them.'), (('themselues',),'themselves'), (('Thanne ',),'Then '),((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),
            ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
            ((' therfore',' therfor'),' therefore'),(('Therfor ',),'Therefore '), ((' thei ',),' they '),
            ((' thyne ',' thine '),' thine/your '), ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'),
                ((' thridde',' thyrde',' thirde'),' third'), ((' thyrst',),' thirst'),
            (('thwong',),'thong'), ((' thou ',),' thou/you '), (('thousynde','thousande'),'thousand'),
            ((' trone ',),' throne '), (('thorowout',),'throughout'), (('thorow ',),'through '),(('thorow,',),'through,'), (('throwen',),'thrown'),
            (('thundryng',),'thundering'), (('thounder','thonder'),'thunder'),
        ((' tydynges',' tidynges',' tydinges',' tydings'),' tidings/news'),(('Tydinges',),'Tidings'), ((' tyme',),' time'),
        (('togidir','togidere','togidre','togedder'),'together'), ((' tokene ',),' token '), ((' toke ',),' took '), ((' townes',' tounes'),' towns'),
        ((' tryed',),' tried'), (('Treuli',),'Truly'), ((' trueth',' treuthe',' verite'),' truth'),
        ((' turneden',' turnede'),' turned'),((' tourne ',' turne '),' turn '),
        (('twolue','twelue'),'twelve'), ((' twyse',' twise'),' twice'), ((' twei ',' tweyne ',' tweyn ',' twey ', ' twaine '),' two '),
    (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'),
        ((' vnderstonde',' vnderstande',' vnderstode',' vnderstand'),' understand'),(('Vnderstonde',),'Understood'), ((' vnder',),' under'), (('vnleauened','vnleuened'),'unleavened'), ((' vnloose',),' unloose'),
        (('Untyll ','Vntill '),'Until '),(('vntill','vntyll'),'until'), (('Vnto ',),'Unto '),((' vnto',),' unto'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon ',' apon '),' upon '),(('Vpon ',),'Upon '), ((' vs ',),' us '),((' vs,',),' us,'),((' vs.',),' us.'),
        (('vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'),
            ((' vn',),' un'), # Special case for all remaining un- words
            ((' vp',),' up'), # Special case for all remaining up- words
    (('vanyte ','vanitie '),'vanity '),
        ((' verely',),' verily'),(('Ueryly','Verely'),'Verily'), ((' vertu',),' virtue'),
        ((' voyce',' vois'),' voice'),
    (('walkynge','walkinge'),'walking'),((' walkid',),' walked'),((' walke ',),' walk '),((' walke,',),' walk,'),
             ((' warres',),' wars'),((' warre ',),' war '),
             ((' watred',),' watered'),((' watris',),' waters'),((' watir',),' water'), ((' waye ',' weie ',' weye '),' way '),((' waye.',' weie.',' weye.'),' way.'),((' waye:',' weie:',' weye:'),' way:'),
        ((' wee ',),' we '),
            ((' weryed',' weried'),' wearied'),((' weery',' wery'),' weary'),
            ((' wel ',),' well '),
            ((' wenten ',' wente ',' wete ',' yeden ',' yede '),' went '),
            ((' weren ',),' were '), (('westwarde',),'westward'),
        (('whatsoeuer',),'whatsoever'),(('Whatsoeuer',),'Whatsoever'), ((' whanne ',' whan '),' when '), ((' whethir',),' whether'), ((' whiche ',),' which '),
            ((' whoale',),' whole'), ((' whome',),' whom'), (('whosoeuer',),'whosoever'),
        ((' wickid',),' wicked'),
            (('widewis','wyddowes','widowes'),'widows'), (('wyldernesse','wildirnesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf'),' wife'),
            ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),((' wylt ',' wilt '),' wilt/will '),
            ((' wyndis',' wyndes',' windes'),' winds'), ((' wengis',' wynges'),' wings'),
            (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'),
            ((' withynne',),' within'),((' wi ',' wt '),' with '), (('widdred','wythred','wythered','wyddred'),'withered'),
                (('withouten ',),'without '), (('witnessyng',),'witnessing'),((' wytnesse ',' witnesse ',' witnes '),' witness '),
            ((' wyues',),' wives'),
        ((' womman',),' woman'), ((' wymmen',' wemen'),' women'),
            (('wondriden','wondride'),'wondered'),
            ((' worde',),' word'), ((' worke ',' werk '),' work '),((' worke,',' werk,'),' work,'), ((' worlde',),' world'),
            (('worschipide','worshypped'),'worshipped'),
            ((' worthie',' worthi'),' worthy'),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),
        (('wrouyt','wrought'),'wrought/done'),
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

    # Roman numerals
    (('.iii.',),'3'), (('.vii.',),'7'), ((' xl ',),' 40 '),

    # Symbols
    ((' & ',),' and '),
    )
oldWords, newWords = [], []
for wordMapEntry in ENGLISH_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    someOldWords,newWord = wordMapEntry
    for someOldWord in someOldWords:
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        assert '  ' not in someOldWord
        oldWords.append( someOldWord)
    if newWord not in ('themselves',): # sometimes two->one and sometimes it's a single word
        assert newWord not in newWords, f"{newWord=}"
    if someOldWords[0].startswith(' '): assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    assert '  ' not in newWord
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
