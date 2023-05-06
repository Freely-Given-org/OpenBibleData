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
from Bibles import formatTranslationNotes, tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, checkHtml
from createOETReferencePages import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-05-06' # by RJH
SHORT_PROGRAM_NAME = "createParallelPages"
PROGRAM_NAME = "OpenBibleData createParallelPages functions"
PROGRAM_VERSION = '0.57'
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
<p class="bkLst">{' '.join( BBBLinks )}</p>
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
    adjBBBLinksHtml = ' '.join(BBBLinks).replace( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )

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
        for c in range( 1, numChapters+1 ):
            C = str( c )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating parallel pages for {BBB} {C}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createParallelVersePagesForBook: no verses found for {BBB} {C}" )
                continue
            for v in range( 1, numVerses+1 ):
                V = str( v )
                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Go to previous verse" href="C{C}V{v-1}.htm#__ID__">←</a>{EM_SPACE}' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a>{EM_SPACE}' if c>1 \
                        else ''
                rightVLink = f'{EM_SPACE}<a title="Go to next verse" href="C{C}V{v+1}.htm#__ID__">→</a>' if v<numVerses else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a>{EM_SPACE}' if c>1 else ''
                rightCLink = f'{EM_SPACE}<a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters else ''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about these works" href="{'../'*(level)}allDetails.htm">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#CV__WHERE__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>'
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
                    thisBible = state.preloadedBibles[versionAbbreviation]
                    # thisBible.loadBookIfNecessary( BBB )
                    try:
                        if BBB not in thisBible: raise MissingBookError # Requested book is not in this Bible
                        verseEntryList, contextList = thisBible.getContextVerseData( (BBB, C, V) )
                        if isinstance( thisBible, ESFMBible.ESFMBible ):
                            verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
                        textHtml = convertUSFMMarkerListToHtml( level, versionAbbreviation, (BBB,c,v), 'verse', contextList, verseEntryList, basicOnly=True, state=state )
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
                            if (modernisedTextHtml:=moderniseEnglishWords(textHtml)) != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({modernisedTextHtml})'
                        elif versionAbbreviation in ('CLV',):
                            if (adjustedTextHtml:=adjustLatin(textHtml)) != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({adjustedTextHtml})'
                        elif versionAbbreviation in ('SR-GNT','UGNT','SBL-GNT','TC-GNT','BrLXX'):
                            # print( f"{versionAbbreviation} {BBB} {C}:{V} {textHtml=}")
                            transcription = transliterate_Greek(textHtml)
                            # print( f"{versionAbbreviation} {BBB} {C}:{V} {transcription=}")
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
                        vHtml = f'''
<p><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{C}.htm">OET-RV</a>)</span> {textHtml}</p>
''' if versionAbbreviation=='OET-RV' else f'''
<p><span class="wrkName"><a title="View {state.BibleNames[versionAbbreviation]} chapter" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> {textHtml}</p>
'''
                    except MissingBookError:
                        assert BBB not in thisBible
                        warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                        vHtml = f'''<p><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )
                    except UntranslatedVerseError:
                        assert versionAbbreviation == 'OET-RV'
                        assert BBB in thisBible
                        if BBB in thisBible:
                            # print( f"No verse inB {versionAbbreviation} {BBB} in {thisBible}"); halt
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                            vHtml = f'''<p><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
'''
                        else:
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                            vHtml = f'''<p><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )
                    except KeyError:
                        if BBB in thisBible:
                            # print( f"No verse inKT {versionAbbreviation} {BBB} in {thisBible}"); halt
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} {C}:{V} verse available'
                            vHtml = f'''<p><span class="wrkName"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{C}.htm">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
'''
                        else:
                            warningText = f'No {versionAbbreviation} {ourTidyBBB} book available'
                            vHtml = f'''<p><span class="wrkName">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )
                    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                    checkHtml( f'{versionAbbreviation} {BBB} {C}:{V}', vHtml, segmentOnly=True )
                    pHtml = f'{pHtml}{vHtml}'

                tnHtml = formatTranslationNotes( level, BBB, C, V, 'parallel', state )
                if tnHtml: tnHtml = f'<div class="TN">TN <b>uW Translation Notes</b>: {tnHtml}</div><!--end of TN-->\n'
                pHtml = f'{pHtml}{tnHtml}'

                filename = f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'parallel', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {C}:{V} Parallel View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {ourTidyBBB}, parallel' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*level}il/"''', f'''href="{'../'*level}il/{BBB}/C{C}V{V}.htm"''')
                pHtml = f'''{top}<!--parallel verse page-->
<p class="bkLst">{adjBBBLinksHtml}</p>
<h1 id="Top">Parallel {ourTidyBBB} {C}:{V}</h1>
{navLinks.replace('__ID__','CVTop').replace('__ARROW__','↓').replace('__WHERE__','bottom')}
{pHtml}
{navLinks.replace('__ID__','CVBottom').replace('__ARROW__','↑').replace('__WHERE__','top')}
{makeBottom( level, 'parallel', state )}'''
                checkHtml( f'Parallel {BBB} {C}:{V}', pHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( pHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(pHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to parallel verse page" href="{filename}">{C}:{V}</a>' )
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
    ourLinks = f'''<h1 id="Top">{ourTidyBBB} parallel songs index</h1>
<p class="cLinks">{EM_SPACE.join( [f'<a title="Go to parallel verse page" href="C{ps}V1.htm">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="cLinks">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/James'} {' '.join( [f'<a title="Go to parallel verse page" href="C{chp}V1.htm">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">{ourTidyBBB} parallel verses index</h1>
<p class="vLinks">{' '.join( vLinks )}</p>'''
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


def moderniseEnglishWords( html:str ) -> bool:
    """
    Convert ancient spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"moderniseEnglishWords( ({len(html)}) )" )

    for oldWords,newWord in ( # Place longer words first,
                              #     use space before to prevent accidental matches since we're only doing string matches
            ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' aboute',),' about'), ((' accorde ',' acorde '),' accord '), ((' aftir',),' after'), ((' agayne','againe'),' again'),
                (('agaynst',),'against'),
                ((' alle ',' al '),' all '),(('Alle ',),'All '), ((' aloone',),' alone'),
                (('amased',),'amazed'), ((' amonge',' amoge'),' among'),
                (('Andrewe',),'Andrew'), ((' aungel',),' angel'), (('answerede','answeride','aunswered'),'answered'), ((' ony ',),' any '),
                (('appearynge','apperynge','appearyng'),'appearing'), ((' appoynte','apoynte'),' appoint'),
                ((' aryse',),' arise'),
                (('astonnied',),'astonished'),
                ((' ete ',),' ate '), ((' athyrst',),' athirst'), ((' attayne ','attaine '),' attain '),
                (('aucthoritie','authoritie'),'authority'),
            (('baptysed','baptisid'),'baptised'), (('baptisynge',),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
                ((' bee ',),' be '), ((' beastes','beestes','beestis'),' beasts'),((' beesti',),' beast'), ((' beed ',' bedde '),' bed '), ((' ben ',),' been '), ((' bifor',),' before'),
                    ((' beganne',' begane'),' began'), (('bigynnyng','beginnynge','begynnynge','begynnyng'),'beginning'), (('bigetun',),'begotten'), ((' behinde',),' behind'),
                    (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), ((' beleue',' beleeue',' beleve',' bileue'),' believe'),
                    ((' bisidis',),' beside'), (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '),
                ((' bynde',),' bind'),
                ((' borun ',' borne '),' born '), ((' boundun ',' bounde '),' bound '),
                (('britheren',),'brethren'), ((' bryde',),' bride'), ((' bryngyng',),' bringing'),
                ((' brent',),' burnt'), (('busynesse','busynes','busines'),'business'),(('businesss',),'business'),
                ((' bi ',),' by '),
            ((' clepid',),' called'),((' cal ',),' call '), ((' cam ',' camen '),' came '), (('Captaine',),'Captain'), ((' castynge',' castyng',' castinge'),' casting'),
                ((' certayne',' certein'),' certain'),
                (('cheynes','chaines'),'chains'), (('chaunced','chaunsed'),'chanced'), (('chyldren',),'children'), (('chymney',),'chimney'), (('chirche',),'church'), (('Churche ',),'Church '),
                    (('Christe','Crist'),'Christ'),
                ((' cyte ',' citie '),' city '),
                ((' clouen',),' cloven'),
                ((' commeth','cometh'),' comes'), ((' comynge',),' coming'), (('commaundement','comaundement','commandement'),'commandment'),
                    (('confessioun',),'confession'), (('contynued',),'continued'),(('contynuynge',),'continuing'), ((' coulde','coude'),' could'), ((' cuntree',' cuntrey',' cuntre',' cuntrei',' countrey',' countre'),' country'),
                ((' criede',),' cried'),
            ((' dayly',' daylie'),' daily'), ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),
                ((' deed',),' dead'), ((' deeth',' deth',' derth'),' death'), ((' delyte',),' delight'), ((' deliuered',),' delivered'), (('descendinge',),'descending'),  ((' deseert',),' desert'),  ((' desirith',' desyreth',' desireth'),' desires'), ((' distrie',' destroye'),' destroy'),
                ((' dyd ',' dide '),' did '), (('disciplis',),'disciples'), (('devided','deuided','deuyded'),'divided'),
                (('doctryne',),'doctrine'), ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),
                    ((' dore',),' door'), ((' doue',),' dove'), ((' downe',),' down'), (('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
                (('dredde',),'dreaded'), ((' driueth','driveth'),' drives'), ((' driue',' dryue'),' drive'), ((' drave',' droue'),' drove'),
            ((' ech ',),' each '), ((' ete ',),' eat '),
                (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
                (('ynough','inough'),'enough'), ((' entred',' entride'),' entered'),
                ((' euen ',),' even '), (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' euer ',),' ever '), ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll'),' evil'),
            ((' fadir',),' father'), ((' feith','fayth'),' faith'),
                ((' feete',' fete'),' feet'), ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),
                (('Fyght',),'Fight'),((' fyght',' fighte'),' fight'), ((' fisscheris','fisshers','fysshers'),' fishers'), ((' fyue',' fyve',' fiue'),' five'),
                ((' flye ',' fle '),' flee '), ((' flesshe',' fleshe',' fleische'),' flesh'),
                (('folowed','folewiden'),'followed'), ((' folowe',' folow'),' follow'), (('Folowe','Folow'),'Follow'),
                    (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '), ((' forsooke',' forsoke',),' forsook'),((' foorth',),' forth'),
                    ((' fourtie',' fourtye',' fourti'),' forty'), ((' foure',' fower'),' four'),
                ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'), ((' freend',),' friend'),
                ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
            (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'), ((' yaf ',' gaue '),' gave '), (('gadirid',),'gathered'),
                ((' goost',),' ghost'),
                ((' geve ',' geue ',' giue '),' give '), ((' geven',' giuen'),' given'),
                ((' girdil',' gerdyll',' gerdell'),' girdle'),
                ((' goe ',' goo '),' go '), ((' goon ',),' gone '), ((' gospell',),' gospel'), (('Gospell',),'Gospel'),
                ((' greate ',' grete '),' great '),
            ((' hadde ',),' had '), ((' heeris',),' hairs'), ((' handes',' hondes',' hoondis'),' hands'),((' hande',' honde',' hoond'),' hand'), ((' haue ',),' have '), ((' hauynge',' havynge','hauing'),' having'),
                ((' hee ',),' he '), ((' hir ',),' her '),((' hir,',),' her,'),((' hir.',),' her.'), ((' hearde',' herde'),' heard'), ((' heareth',' herith'),' hears'), ((' hertis',' hertes',' heartes'),' hearts'), ((' heauens',' heuenes'),' heavens'), ((' heauen',),' heaven'),
                    (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), ((' hede ',' heede '),' heed '), ((' hir ',),' her '),
                ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',),' him:'),
                    ((' hiryd',' hyred'),' hired'), ((' hise ',' hys '),' his '),
                (('honeste','honestye','honestie'),'honesty'), ((' hony',),' honey'), ((' houres',),' hours'), ((' housse ',' hous '),' house '), ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
                ((' hungur',),' hunger'), (('husbande','hosebonde'),'husband'),
            (('Y ',),'I '),
                ((' yf ',),' if '), (('Yf ',),'If '),
                (('encreased',),'increased'),
                (('immediatly',),'immediately'),
            ((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'),
            # (('Jhesus',),'Jesus'),(('Jhesu ',),'Jesu '), (('Joon',),'John'),
            ((' keepe',' kepe'),' keep'), (('kingdome','kyngdoom','kyngdome'),'kingdom'), ((' kynges',' kyngis'),' kings'),((' kynge ',' kyng '),' king '),
                (('knewe',),'knew'), (('knowe',),'know'), (('knowyng',),'knowing'),
            ((' lande ',' londe '),' land '),((' lande,',' londe,'),' land,'),((' lande.',' londe.'),' land.'), ((' laye ',),' lay '), ((' layed',' layde',' leiden'),' laid'),
                (('learnyng','learninge'),'learning'), ((' leften',' leeft',' lefte'),' left'),
                ((' lyfe',' lijf'),' life'), ((' lyght',' liyt'),' light'), ((' lyke',' lijk'),' like'), ((' litil',' lytell',' lytle',' litle'),' little'), ((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),
                ((' loynes',),' loins'), ((' lokide',' loked'),' looked'),
                    ((' lordes',),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '), ((' louede',' loued',' louyde'),' loved'), ((' loue ',),' love '),
            ((' maad',),' made'), ((' makynge',),' making'), ((' maner',),' manner'), (('merveled',),'marvelled'), ((' maister',),' master'), ((' maye ',),' may '),
                (('meekenes','mekenes','meknes'),'meekness'), ((' mendynge',' mendyng',' mendinge'),' mending'), ((' mesure',),' measure'),
                ((' myghty',' mightie',' miyti'),' mighty'),((' myyte',),' might'), ((' mynde ',),' mind '), (('ministred','mynistred','mynystriden'),'ministered'),
                ((' moder ',),' mother '),
                ((' moch',),' much'),
            ((' nether',),' neither'), ((' nettes',' nettis'),' nets'), ((' nyyti',),' night'),
                ((' ner ',),' nor '), ((' nexte',),' next'),
                (('noumbre','nombre','nomber'),'number'),
            ((' onely ',' `oon '),' only '), ((' oure ',),' our '), ((' ouer',),' over'), ((' awne ',' owne '),' own '),
            ((' parablis',),' parables'), ((' passide',),' passed'), ((' pacience',),' patience'),
                (('penaunce',),'penance'), ((' puple',' pople'),' people'), (('perceiued','perceaved'),'perceived'), ((' perische',' perisshe',' perishe'),' perish'),
                ((' pearced',),' pierced'), ((' pylgrym',),' pilgrim'),
                ((' pleside',' plesid'),' pleased'),
                (('praysed',),'praised'), (('preyeden',),'prayed'), (('preier',),'prayer'),
                    (('prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ',),'preach '),
                    (('preestis','prestes','priestes'),'priests'),(('Priestes',),'Priests'), (('princis',),'princes'),
            ((' reise',),' raise'),
                ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'), ((' receave',),' receive'), (('remayned',),'remained'), (('remyssion','remissioun'),'remission'), (('repentaunce',),'repentance'), (('resurreccion',),'resurrection'),
                ((' ryse ',),' rise '),
                ((' roofe',' rofe'),' roof'), ((' roume',),' room'), ((' roote',' rote'),' root'),
                (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
            ((' sabat',' saboth'),' sabbath'), (('Saduceis','Saduces','Sadduces'),'Sadducees'), ((' saaf',),' safe'), ((' seiden',' seide',' sayde',' saide'),' said'), (('Sathanas','Sathan'),'Satan'), ((' saued',),' saved'), ((' sawe ',),' saw '),
                    ((' sayege',' sayinge'),' saying'), ((' seith ',),' says '), ((' seie ',' saye '),' say '),
                (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
                ((' se ',),' see '), ((' seyn ',' seene ',' sene '),' seen '), ((' silfe ',' silf ',' selfe '),' self '), ((' selues',),' selves'), ((' sente ',),' sent '),
                    ((' serue ',),' serve '), (('seruauntis','seruauntes','servauntes','seruauntes','seruants'),'servants'),((' seruaunt',' servaunt'),' servant'), ((' seuen ',' seue '),' seven '),
                ((' schal ',' shal '),' shall '), ((' shyppe',' shippe'),' ship'), ((' shoulde ',' shulde ',' shuld '),' should '), ((' schewe',' shewe'),' show '),
                ((' sicke ',' sijk '),' sick '),((' sicke,',' sijk,'),' sick,'),((' sicke.',' sijk.'),' sick.'),
                    ((' syde ',),' side '),
                    ((' sinnes','synnes'),' sins'), ((' sistir',),' sister'), ((' syttyng',),' sitting'),
                ((' skynne ',' skyn ',' skinne '),' skin '),
                ((' slepe',),' sleep'), ((' slepith',),' sleeps'),
                ((' smale ',),' small '),
                ((' soiourne',),' sojourn'), ((' summe ',),' some '), ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,',),'Son,'),
                    ((' sorewis',' sorowes'),' sorrows'),
                ((' speake',),' speak'), ((' spirite',' sprete'),' spirit'),
                ((' styll',),' still'), ((' stockis',),' stocks'), ((' stoone',),' stone'), ((' stoupe',' stowpe'),' stoop'), (('stumbleth','stombleth','stomblith'),'stumbles'),
                ((' souyten',),' sought'), ((' sounde',),' sound'), (('souereynes',),'sovereigns'),
                (('subiection',),'subjection'), ((' soch ',' suche ',' siche '),' such '), (('supplicacion',),'supplication'),
                (('synagoge',),'syngagogue'),
            ((' takun',),' taken'), ((' takynge',),' taking'),(('Takyng',),'Taking'), ((' tauyte',),' taught'),
                (('temptid',),'tempted'),
                ((' hem ',),' them '),((' hem.',),' them.'), (('themselues',),'themselves'), ((' thanne ',),' then '), ((' thennus',),' thence'),
                    ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
                    ((' therfor',),' therefore'),(('Therfor ',),'Therefore '), ((' thei ',),' they '),
                    ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'), ((' thyrst',),' thirst'),
                ((' tyme',),' time'),
                ((' togidir',),' together'), ((' toke ',),' took '),
                (('Treuli',),'Truly'),
                ((' twolue','twelue'),' twelve'), ((' twei ',' twey ', ' twaine '),' two '),
            (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'), ((' vnder',),' under'), ((' vnloose',),' unloose'),
                ((' vntill',' vntyll'),' until'), ((' vnto',),' unto'),
                ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon',),' upon'), ((' vs ',),' us '),((' vs,',),' us,'),((' vs.',),' us.'),
            (('Ueryly','Verely'),'Verily'),
                ((' voyce',' vois'),' voice'),
            ((' walke ',),' walk '), ((' watir',),' water'), ((' watris',),' waters'),
                ((' wente ',' wete '),' went '),
                ((' whanne ',' whan '),' when '), ((' whanne ',' wha '),' when '), ((' whiche ',),' which '),
                    ((' whoale',),' whole'), ((' whome',),' whom'), (('whosoeuer',),'whosoever'),
                (('widewis','wyddowes','widowes'),'widows'), (('wyldernesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
                    ((' wyfe',' wijf'),' wife'), ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),
                    (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'),  (('widdred','wythred','wythered'),'withered'),
                ((' womman',),' woman'), ((' wymmen',' wemen'),' women'), ((' worde',),' word'), ((' worke ',' werk '),' work '),((' werk',),' work'), ((' worlde',),' world'),
            (('Iames',),'Yames'),
                    (('Iesus',),'Yesus'),(('Iesu ',),'Yesu '), (('Iewry ',),'Yewry '), (('Iewes ','Jewis '),'Yews '),
                    (('Iohn','Ihon','Joon'),'Yohn'), (('Iordane','Iordan'),'Yordan'),
                    (('Iudas','Ivdas','Judas'),'Yudas'), (('Iuda','Juda'),'Yudah'), (('Iudea','Judee'),'Yudea'),
                ((' ye ',' yee '),' you_all '), ((' thi ',' thy '),' your '), ((' youre ',' thy '),' your(pl) '),
            (('Zebedeus ','zebede ','Zebede '),'Zebedee '), (('Zebedeus,','zebede,','Zebede,'),'Zebedee,'),

            ((' xl ',),' 40 '),

            ((' & ',),' and '),

            # Pairs of words
            (('Hooli Goost',),'Holy Ghost'),
            (('the see ',),'the sea '),

            # Two words into one
            ((' in to ',),' into '),
            ((' for euer',),' forever'),
            (('strayght waye',),'straightway'),
            ((' youre selues',),' yourselves'),

            # One word into two
            ((' shalbe ',),' shall be '),
            ):
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
