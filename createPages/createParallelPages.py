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
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, checkHtml
from createOETReferencePages import livenOETWordLinks


LAST_MODIFIED_DATE = '2023-04-10' # by RJH
SHORT_PROGRAM_NAME = "createParallelPages"
PROGRAM_NAME = "OpenBibleData createParallelPages functions"
PROGRAM_VERSION = '0.49'
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

    BBBLinks, BBBNextLinks = [], []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
            BBBLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="{BBB}/">{tidyBBB}</a>' )
            BBBNextLinks.append( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="../{BBB}/">{tidyBBB}</a>' )
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
    indexHtml = top \
                + '<h1 id="Top">Parallel verse pages</h1><h2>Index of books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom( level, 'parallel', state )
    checkHtml( 'ParallelIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of html.createParallelPages

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
    tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
    tidyBbb = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=True )
    adjBBBLinksHtml = ' '.join(BBBLinks).replace( f'<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)}" href="../{BBB}/">{tidyBBB}</a>', tidyBBB )

    numChapters = None
    for versionAbbreviation in state.BibleVersions:
        if versionAbbreviation == 'OET': continue # that's only a "pseudo-version"!
        referenceBible = state.preloadedBibles[versionAbbreviation]
        # referenceBible.loadBookIfNecessary( BBB )
        numChapters = referenceBible.getNumChapters( BBB )
        if numChapters: break
    else:
        logging.critical( f"createParallelVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( 1, numChapters+1 ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating parallel pages for {BBB} {c}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createParallelVersePagesForBook: no verses found for {BBB} {c}" )
                continue
            for v in range( 1, numVerses+1 ):
                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Go to previous verse" href="C{c}V{v-1}.htm#__ID__">←</a>{EM_SPACE}' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a>{EM_SPACE}' if c>1 \
                        else ''
                rightVLink = f'{EM_SPACE}<a title="Go to next verse" href="C{c}V{v+1}.htm#__ID__">→</a>' if v<numVerses else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a>{EM_SPACE}' if c>1 else ''
                rightCLink = f'{EM_SPACE}<a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters else ''
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}il/{BBB}/C{c}V{v}.htm#Top">═</a>'''
                navLinks = f'<p id="__ID__" class="vnav">{leftCLink}{leftVLink}{tidyBbb} {c}:{v} <a title="Go to __WHERE__ of page" href="#CV__WHERE__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}</p>'
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
                        verseEntryList, contextList = thisBible.getContextVerseData( (BBB, str(c), str(v)) )
                        if isinstance( thisBible, ESFMBible.ESFMBible ):
                            verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
                        textHtml = convertUSFMMarkerListToHtml( level, versionAbbreviation, (BBB,c,v), 'verse', contextList, verseEntryList, basicOnly=True, state=state )
                        if textHtml == '◘': raise KeyError # This is an OET-RV marker to say "Not translated yet"

                        if versionAbbreviation == 'OET-RV':
                            textHtml = do_OET_RV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation == 'OET-LV':
                            textHtml = do_OET_LV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation == 'WEB': # assuming WEB comes BEFORE WMB
                            textHtmlWEB = textHtml # Save it
                        elif versionAbbreviation == 'WMB': # assuming WEB comes BEFORE WMB
                            if textHtml == textHtmlWEB:
                                # print( f"Skipping parallel for WMB {BBB} {c}:{v} because same as WEB" )
                                continue
                            # else:
                            #     print( f"Using parallel for WMB {BBB} {c}:{v} because different from WEB:" )
                            #     print( f"  {textHtmlWEB=}" )
                            #     print( f"     {textHtml=}" )
                        elif versionAbbreviation == 'LSV':
                            textHtml = do_LSV_HTMLcustomisations( textHtml )
                        elif versionAbbreviation in ('WYC','TNT','CB','GNV','BB','KJB'):
                            if (modernisedTextHtml:=moderniseEnglishWords(textHtml)) != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({modernisedTextHtml})'
                        elif versionAbbreviation in ('CLV',):
                            if (adjustedTextHtml:=adjustLatin(textHtml)) != textHtml: # only show it if it changed
                                textHtml = f'{textHtml}<br>  ({adjustedTextHtml})'
                        elif versionAbbreviation in ('SR-GNT','UGNT','SBL-GNT','TC-GNT','BrLXX'):
                            # print( f"{versionAbbreviation} {BBB} {c}:{v} {textHtml=}")
                            textHtml = f'{textHtml}<br>  ({transliterate_Greek(textHtml)})'
                            # print( textHtml)
                        elif versionAbbreviation in ('UHB',):
                            # print( f"{versionAbbreviation} {BBB} {c}:{v} {textHtml=}")
                            textHtml = f'{textHtml}<br>  ({transliterate_Hebrew(textHtml)})'
                            # print( textHtml)
                        vHtml = f'''
<p><span class="workNav"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{c}.htm">OET-RV</a>)</span> {textHtml}</p>
''' if versionAbbreviation=='OET-RV' else f'''
<p><span class="workNav"><a title="View {state.BibleNames[versionAbbreviation]} chapter" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{c}.htm">{versionAbbreviation}</a></span> {textHtml}</p>
'''
                    except (KeyError, TypeError):
                        if BBB in thisBible:
                            warningText = f'No {versionAbbreviation} {tidyBBB} {c}:{v} verse available'
                            vHtml = f'''<p><span class="workNav"><a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*level}{versionAbbreviation}/byC/{BBB}_C{c}.htm">{versionAbbreviation}</a></span> <span class="noVerse"><small>{warningText}</small></span></p>
'''
                        else:
                            warningText = f'No {versionAbbreviation} {tidyBBB} book available'
                            vHtml = f'''<p><span class="workNav">{versionAbbreviation}</span> <span class="noBook"><small>{warningText}</small></span></p>
'''
                        logging.warning( warningText )
                    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"\n\n{pHtml=} {vHtml=}" )
                    checkHtml( f'{versionAbbreviation} {BBB} {c}:{v}', vHtml, segmentOnly=True )
                    pHtml = f'{pHtml}{vHtml}'
                filename = f'C{c}V{v}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'parallel', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{tidyBBB} {c}:{v} Parallel View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {tidyBBB}, parallel' ) \
                        .replace( f'''href="{'../'*level}il/"''', f'''href="{'../'*level}il/{BBB}/C{c}V{v}.htm"''')
                pHtml = top + '<!--parallel verse page-->' \
                        + f'{adjBBBLinksHtml}\n<h1 id="Top">Parallel {tidyBBB} {c}:{v}</h1>\n' \
                        + f"{navLinks.replace('__ID__','CVTop').replace('__ARROW__','↓').replace('__WHERE__','Bottom')}\n" \
                        + pHtml \
                        + f"\n{navLinks.replace('__ID__','CVBottom').replace('__ARROW__','↑').replace('__WHERE__','Top')}\n" \
                        + makeBottom( level, 'parallel', state )
                checkHtml( f'Parallel {BBB} {c}:{v}', pHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( pHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(pHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to parallel verse page" href="{filename}">{c}:{v}</a>' )
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createParallelVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallel', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{tidyBBB} Parallel View" ) \
            .replace( '__KEYWORDS__', f'Bible, parallel' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">{tidyBBB} parallel songs index</h1>
<p class="cLinks">{EM_SPACE.join( [f'<a title="Go to parallel verse page" href="C{ps}V1.htm">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="cLinks">{tidyBbb} {' '.join( [f'<a title="Go to parallel verse page" href="C{chp}V1.htm">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">{tidyBBB} parallel verses index</h1>
<p class="vLinks">{' '.join( vLinks )}</p>'''
    indexHtml = f'{top}{adjBBBLinksHtml}\n{ourLinks}\n' \
                + makeBottom( level, 'parallel', state )
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
            ((' abideth',),' abides'), ((' aftir',),' after'), ((' agayne','againe'),' again'),
                ((' aloone',),' alone'),
                (('amased',),'amazed'),
                (('answerede','aunswered'),'answered'),
                ((' aryse',),' arise'),
                (('astonnied',),'astonished'),
                ((' aungel',),' angel'),
            ((' beesti',),' beast'), ((' beed ',' bedde '),' bed '), ((' bifor',),' before'),
                    (('bigynnyng','beginnynge','begynnynge','begynnyng'),'beginning'), ((' beleue',' beleeue',' beleve'),' believe'),
                    ((' bisidis',),' beside'),
                ((' bryngyng',),' bringing'),
            ((' cam ',' camen '),' came '), ((' certayne',),' certain'),
                (('Crist',),'Christ'),
                ((' comynge',),' coming'), ((' coulde','coude'),' could'), ((' cuntree',),' country'),
            ((' daies',' dayes'),' days'),
                ((' deliuered',),' delivered'), ((' deseert',),' desert'),
                (('disciplis',),'disciples'),
                ((' dore',),' door'), ((' doue',),' dove'), ((' downe',),' down'), ((' dwelleth',),' dwells'), ((' dwellynge',),' dwelling'),
            (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
                (('ynough','inough'),'enough'), ((' entred',' entride'),' entered'),
            ((' feith','fayth'),' faith'),
                ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),
                ((' fisscheris','fisshers','fysshers'),' fishers'),
                ((' folowed',),' followed'), ((' folowe',' folow'),' follow'), (('Folowe','Folow'),'Follow'),
                    (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '), ((' foorth',),' forth'),
                    ((' fourtie',' fourtye'),' forty'), ((' foure',' fower'),' four'),
                   ((' freend',),' friend'),
                (('fulfillid','fulfylled'),'fulfilled'),
            (('Galile,',),'Galilee,'), ((' goost',),' ghost'),
                ((' geve ',' geue ',' giue '),' give '),
                ((' goe ',' goo '),' go '), ((' gospell',),' gospel'), (('Gospell',),'Gospel'),
            ((' hadde ',),' had '), ((' hande',' honde',' hoond'),' hand'), ((' hauynge',),' having'),
                ((' hee ',),' he '), ((' hearde',' herde'),' heard'), ((' hertis',' hertes',' heartes'),' hearts'), ((' heauen',),' heaven'), ((' hede ',' heede '),' heed '), ((' hir ',),' her '),
                ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',),' him:'),
                    ((' hise ',),' his '),
                ((' houres',),' hours'), ((' housse ',' hous '),' house '),
            (('Y ',),'I '),
                ((' yf ',),' if '),
                (('immediatly',),'immediately'),
            # (('Jhesus',),'Jesus'),(('Jhesu ',),'Jesu '), (('Joon',),'John'),
            ((' kingdome',' kyngdoom',' kyngdome'),' kingdom'), ((' kyng',),' king'),
                ((' knowe',),' know'),
            ((' laye',),' lay'),
                ((' lyght',' liyt'),' light'), ((' lyke',),' like'),
                ((' loued',' louyde'),' loved'),
            ((' maad',),' made'), ((' maye ',),' may '),
                (('ministred','mynistred','mynystriden'),'ministered'),
                ((' moch',),' much'),
            ((' nether',),' neither'), ((' nettes',' nettis'),' nets'), ((' nyyti',),' night'),
            ((' oure ',),' our '), ((' ouer',),' over'), ((' awne ',' owne '),' own '),
            ((' passide',),' passed'), (('penaunce',),'penance'), (('perceiued','perceaved'),'perceived'),
                ((' puple',),' people'),
                (('praysed',),'praised'), (('prechide',),'preached'), (('preachyng',),'preaching'),
            ((' reise',),' raise'),
                ((' receave',),' receive'), (('reasonyng','reasoninge'),'reasoning'),
                ((' ryse ',),' rise '),
                ((' roofe',' rofe'),' roof'), ((' roume',),' room'),
            ((' seide',' sayde',' saide'),' said'), (('Sathanas','Sathan'),'Satan'), ((' sawe ',),' saw '),
                    ((' seith ',),' says '),
                ((' scribis',' scrybes'),' scribes'),
                ((' seyn',),' seen'),
                ((' schal ',' shal '),' shall '),
                ((' sicke ',' sijk '),' sick '),((' sicke,',' sijk,'),' sick,'),((' sicke.',' sijk.'),' sick.'),
                    ((' sinnes','synnes'),' sins'), ((' sistir',),' sister'), ((' syttyng',),' sitting'),
                ((' slepe',),' sleep'), ((' slepith',),' sleeps'),
                ((' summe ',),' some '), ((' sonne ',' sone '),' son '), (('Sonne ',),'Son '),
                ((' speake',),' speak'), ((' spirite',' sprete'),' spirit'),
                ((' styll',),' still'), ((' stoone',),' stone'), (('stumbleth','stombleth','stomblith'),'stumbles'),
                ((' souyten',),' sought'),
                ((' soch ',),' such '),
                (('synagoge',),'syngagogue'),
            ((' takun',),' taken'), ((' tauyte',),' taught'),
                (('temptid',),'tempted'),
                ((' hem ',),' them '), ((' thanne ',),' then '),
                    ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
                    ((' therfor',),' therefore'),(('Therfor ',),'Therefore '), ((' thei ',),' they '),
                    ((' thingis',),' things'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'),
                ((' tyme',),' time'),
                ((' toke ',),' took '),
                ((' twolue','twelue'),' twelve'), ((' twei',),' two'),
            (('vncerteyn',),'uncertain'), (('vncovered','vncouered'),'uncovered'),
            ((' vnto',),' unto'), ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon',),' upon'), ((' vs ',),' us '),((' vs,',),' us,'),((' vs.',),' us.'),
            ((' walke ',),' walk '), ((' watir',),' water'), (('widdred','wythred','wythered'),'withered'), ((' wente',),' went'),
                ((' whanne ',),' when '), ((' whanne ',' wha '),' when '), ((' whiche ',),' which '),
                ((' wilde ',' wylde '),' wild '), ((' wyll ',' wil '),' will '),
                ((' worlde',),' world'),
            (('Iesus',),'Yesus'),(('Iesu ',),'Yesu '), (('Iewes ','Jewis '),'Yews '), (('Iohn','Ihon'),'Yohn'), (('Iudea','Judee'),'Yudea'),
                ((' ye ',' yee '),' you_all '), ((' thi ',' thy '),' your '), ((' youre ',' thy '),' your(pl) '),

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
