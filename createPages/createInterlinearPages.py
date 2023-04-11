#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createInterlinearPages.py
#
# Module handling OpenBibleData createInterlinearPages functions
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
Module handling createInterlinearPages functions.

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
from collections import defaultdict

# sys.path.append( '../../BibleOrgSys/BibleOrgSys/' )
# import BibleOrgSysGlobals
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

from usfm import convertUSFMMarkerListToHtml
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, \
                    makeTop, makeBottom, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP, livenOETWordLinks


LAST_MODIFIED_DATE = '2023-04-11' # by RJH
SHORT_PROGRAM_NAME = "createInterlinearPages"
PROGRAM_NAME = "OpenBibleData createInterlinearPages functions"
PROGRAM_VERSION = '0.12'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createInterlinearPages( level:int, folder:Path, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createInterlinearPages( {level}, {folder}, ... )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateInterlinearPages( {level}, {folder}, {state.BibleVersions} )" )
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
            createInterlinearVersePagesForBook( level+1, BBBFolder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinear', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Interlinear View" ) \
            .replace( '__KEYWORDS__', f'Bible, interlinear' )
    indexHtml = top \
                + '<h1 id="Top">Interlinear verse pages</h1><h2>Index of books</h2>\n' \
                + f'''<p class="bLinks">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom( level, 'interlinear', state )
    checkHtml( 'InterlinearIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createInterlinearPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createInterlinearPages.createInterlinearPages


def createInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state ) -> bool:
    """
    Create a page for every Bible verse
        displaying the interlinear verses.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createInterlinearVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createInterlinearVersePagesForBook {level}, {folder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
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
        logging.critical( f"createInterlinearVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( 1, numChapters+1 ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating interlinear pages for {BBB} {c}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createInterlinearVersePagesForBook: no verses found for {BBB} {c}" )
                continue
            for v in range( 1, numVerses+1 ):
                # The following all have a __ID__ string than needs to be replaced
                leftVLink = f'<a title="Go to previous verse" href="C{c}V{v-1}.htm#__ID__">←</a> ' if v>1 \
                        else f'<a title="Go to last verse of previous chapter" href="C{c-1}V{lastNumVerses}.htm#__ID__">↨</a> ' if c>1 \
                        else ''
                rightVLink = f' <a title="Go to next verse" href="C{c}V{v+1}.htm#__ID__">→</a>' if v<numVerses else ''
                leftCLink = f'<a title="Go to previous chapter" href="C{c-1}V1.htm#__ID__">◄</a> ' if c>1 else ''
                rightCLink = f' <a title="Go to next chapter" href="C{c+1}V1.htm#__ID__">►</a>' if c<numChapters else ''
                parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}pa/{BBB}/C{c}V{v}.htm#Top">║</a>'''
                navLinks = f'<p id="__ID__" class="vnav">{leftCLink}{leftVLink}{tidyBbb} {c}:{v} <a title="Go to __WHERE__ of page" href="#CV__WHERE__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}</p>'
                iHtml = createInterlinearVersePage( level, BBB, c, v, state )
                filename = f'C{c}V{v}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'interlinear', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{tidyBBB} {c}:{v} Interlinear View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {tidyBBB}, interlinear' ) \
                        .replace( f'''href="{'../'*level}pa/"''', f'''href="{'../'*level}pa/{BBB}/C{c}V{v}.htm"''')
                iHtml = top + '<!--interlinear verse page-->' \
                        + f'{adjBBBLinksHtml}\n<h1 id="Top">Interlinear {tidyBBB} {c}:{v}</h1>\n' \
                        + f"{navLinks.replace('__ID__','CVTop').replace('__ARROW__','↓').replace('__WHERE__','Bottom')}\n" \
                        + iHtml \
                        + f"\n{navLinks.replace('__ID__','CVBottom').replace('__ARROW__','↑').replace('__WHERE__','Top')}\n" \
                        + makeBottom( level, 'interlinear', state )
                checkHtml( f'Interlinear {BBB} {c}:{v}', iHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as iHtmlFile:
                    iHtmlFile.write( iHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(iHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to interlinear verse page" href="{filename}">{c}:{v}</a>' )
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createInterlinearVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createInterlinearVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinear', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{tidyBBB} Interlinear View" ) \
            .replace( '__KEYWORDS__', f'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">{tidyBBB} interlinear songs index</h1>
<p class="cLinks">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="C{ps}V1.htm">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="cLinks">{tidyBbb} {' '.join( [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">{tidyBBB} interlinear verses index</h1>
<p class="vLinks">{' '.join( vLinks )}</p>'''
    indexHtml = f'{top}{adjBBBLinksHtml}\n{ourLinks}\n' \
                + makeBottom( level, 'interlinear', state )
    checkHtml( 'InterlinearIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createInterlinearVersePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of html.createInterlinearVersePagesForBook


def createInterlinearVersePage( level:int, BBB:str, c:int, v:int, state ) -> str:
    """
    Create an interlinear page for the Bible verse.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createInterlinearVersePage( {level}, {BBB} {c}:{v}, … )" )

    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createInterlinearVersePage {level}, {BBB} {c}:{v}, …" )

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    tidyBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB )
    tidyBbb = BibleOrgSysGlobals.loadedBibleBooksCodes.tidyBBB( BBB, titleCase=True )

    lvBible = state.preloadedBibles['OET-LV']
    rvBible = state.preloadedBibles['OET-RV']
    wordTable = state.OETRefData['word_table']

    html = '<h2>Greek word order <small>(including variants)</small></h2><div class=interlinear><ol class=verse>'
    iHtml = ''
    try:
        lvVerseEntryList, _lvContextList = lvBible.getContextVerseData( (BBB, str(c), str(v)) )
        # rvVerseEntryList, _rvContextList = rvBible.getContextVerseData( (BBB, str(c), str(v)) )
    except (KeyError, TypeError):
        if BBB in lvBible and BBB in rvBible:
            warningText = f'No OET {tidyBBB} {c}:{v} verse available'
            iHtml = f'''<p><span class="workNav"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET {tidyBBB} book available'
            iHtml = f'''<p><span class="workNav">OET</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.critical( warningText )
        lvVerseEntryList = []

    # We need to find where this BCV is in the wordtable
    # Rather than go thru the entire table, find any wordnumber in the verse, then work back from there
    wordNumberStr = None
    EnglishWordList = []
    for lvVerseEntry in lvVerseEntryList:
        text = lvVerseEntry.getFullText()
        if not text or '¦' not in text: continue # no interest to us here
        EnglishWordList += text.replace(',','').replace('.','').replace(':','').replace('?','') \
                            .replace('/','').replace(')','').replace('˲','') \
                            .replace('\\add ','').replace('\\add*','') \
                            .replace('\\nd ','').replace('\\nd*','') \
                            .replace('_',' ').replace('  ',' ') \
                            .strip().split( ' ' )
        # print( f"Found {BBB} {c}:{v} {lvVerseEntry=}" )
        ixMarker = text.index( '¦' )
        wordNumberStr = ''
        for increment in range( 1, 7 ):
            if text[ixMarker+increment].isdigit():
                wordNumberStr = f'{wordNumberStr}{text[ixMarker+increment]}'
            else: break
        break

    # print( f"Found {BBB} {c}:{v} ({len(EnglishWordList)}) {EnglishWordList=}" )
    if wordNumberStr: # Now we have a word number from the correct verse
        firstWordNumber = int( wordNumberStr )
        rowStr = wordTable[firstWordNumber]
        #  0    1      2      3           4          5            6           7     8           9
        # 'Ref\tGreek\tLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
        assert rowStr.startswith( f'{BBB}_{c}:{v}w' )
        # Search backwards through the word-table until we find the first word number still in the verse (includes variants)
        while firstWordNumber > 1:
            firstWordNumber -= 1
            if not wordTable[firstWordNumber].startswith( f'{BBB}_{c}:{v}w' ):
                firstWordNumber += 1 # We went too far
                break

        # Make the English words into a dict
        EnglishWordDict = defaultdict( list )
        for extendedWord in EnglishWordList:
            if not extendedWord:
                logging.critical( f"{BBB} {c}:{v} why did we get a zero-length word in {EnglishWordList}???" )
                continue
            try: word,numberStr = extendedWord.split( '¦' )
            except ValueError:
                logging.critical( f"{BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
            number = int( numberStr )
            EnglishWordDict[number].append( word )

        # Display the interlinear blocks
        GreekList = ['''<li><ol class="word">
<li lang="el">Greek word</li>
<li lang="el_LEMMA">Greek lemma</li>
<li lang="en_TRANS"><b>OET-LV words</b></li>
<li lang="en_STRONGS">Strongs</li>
<li lang="en_MORPH">Role/Morphology</li>
<li lang="en_GLOSS">SR Gloss</li>
<li><small>CAPS codes</small></li>
<li><small>Confidence</small></li>
<li>OET tags</li>
<li>OET word #</li>
</ol></li>''']
        for wordNumber in range( firstWordNumber, firstWordNumber+999 ):
            rowStr = wordTable[wordNumber]
            if not rowStr.startswith( f'{BBB}_{c}:{v}w' ): # gone into the next verse
                break
            row = rowStr.split( '\t' )
            if row[9]:
                tags = row[9].split( ';' )
                for t,tag in enumerate( tags ):
                    tagPrefix, tag = tag[0], tag[1:]
                    if tagPrefix == 'P':
                        tags[t] = f'''Person=<a title="View person details" href="{'../'*level}rf/P/{tag}.htm">{tag}</a>'''
                    elif tagPrefix == 'L':
                        tags[t] = f'''Location=<a title="View place details" href="{'../'*level}rf/L/{tag}.htm">{tag}</a>'''
                tagsHtml = '; '.join( tags )
            else: tagsHtml = '-'
            GreekList.append( f'''<li><ol class="{'word' if row[5] else 'variant'}">
<li lang="el">{row[1]}</li>
<li lang="el_LEMMA">{row[2]}</li>
<li lang="en_TRANS"><b>{' '.join(EnglishWordDict[wordNumber]) if EnglishWordDict[wordNumber] else '-'}</b></li>
<li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[6][:-1]}.htm">{row[6]}</a></li>
<li lang="en_MORPH">{row[7]}{row[8]}</li>
<li lang="en_GLOSS">{row[3]}</li>
<li><small>{row[4] if row[4] else '-'}</small></li>
<li><small>{row[5]+'%' if row[5] else 'V'}</small></li>
<li><small>{tagsHtml}</small></li>
<li><small><a title="View word details" href="{'../'*level}rf/W/{wordNumber}.htm">{wordNumber}</a></small></li>
</ol></li>''' )
        iHtml = f'{iHtml}{NEWLINE.join( GreekList )}'

    # Now append the OET-RV
    try:
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB, str(c), str(v)) )
        if isinstance( rvBible, ESFMBible.ESFMBible ):
            rvVerseEntryList = livenOETWordLinks( lvBible, BBB, rvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
        rvTextHtml = convertUSFMMarkerListToHtml( level, 'OET-RV', (BBB,c,v), 'verse', rvContextList, rvVerseEntryList, basicOnly=True, state=state )
        rvTextHtml = do_OET_RV_HTMLcustomisations( rvTextHtml )

        rvHtml = f'''<p><span class="workNav"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{c}.htm">OET-RV</a>)</span> {rvTextHtml}</p>'''
    except (KeyError, TypeError):
        if BBB in rvBible:
            warningText = f'No OET-RV {tidyBBB} {c}:{v} verse available'
            rvHtml = f'''<p><span class="workNav"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET-RV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-RV {tidyBBB} book available'
            rvHtml = f'''<p><span class="workNav">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.critical( warningText )

    html = f'''{html}{iHtml}</ol></div><!--interlinear-->
{rvHtml}
<p><b>Acknowledgements</b>: The Greek text, lemmas, morphology, and English gloss <small>(6th line)</small> are all thanks to the <a href="https://GreekCNTR.org/collation/index.htm?{CNTR_BOOK_ID_MAP[BBB]}{str(c).zfill(3)}{str(v).zfill(3)}">SR-GNT</a>.</p>
<h2>OET-LV English word order (‘Reverse’ interlinear)</h2><div class=interlinear><ol class=verse>'''

    # Now create the reverseInterlinear
    riHtml = ''
    reverseList = ['''<li><ol class="word">
<li lang="en_TRANS"><b>OET-LV words</b></li>
<li lang="en_STRONGS">Strongs</li>
<li lang="el">Greek word</li>
<li lang="el_LEMMA">Greek lemma</li>
<li lang="en_MORPH">Role/Morphology</li>
<li lang="en_GLOSS">SR Gloss</li>
<li><small>CAPS codes</small></li>
<li><small>Confidence</small></li>
<li>OET tags</li>
<li>OET word #</li>
</ol></li>''']
    for extendedWord in EnglishWordList:
        if not extendedWord:
            logging.critical( f"{BBB} {c}:{v} why did we get a zero-length word in {EnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.critical( f"{BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
        wordNumber = int( numberStr )

        # Display the reverse interlinear blocks
        rowStr = wordTable[wordNumber]
        assert rowStr.startswith( f'{BBB}_{c}:{v}w' )
        row = rowStr.split( '\t' )
        if row[9]:
            tags = row[9].split( ';' )
            for t,tag in enumerate( tags ):
                tagPrefix, tag = tag[0], tag[1:]
                if tagPrefix == 'P':
                    tags[t] = f'''Person=<a title="View person details" href="{'../'*level}rf/P/{tag}.htm">{tag}</a>'''
                elif tagPrefix == 'L':
                    tags[t] = f'''Location=<a title="View place details" href="{'../'*level}rf/L/{tag}.htm">{tag}</a>'''
            tagsHtml = '; '.join( tags )
        else: tagsHtml = '-'
        reverseList.append( f'''<li><ol class="word">
<li lang="en_TRANS"><b>{word}</b></li>
<li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[6][:-1]}.htm">{row[6]}</a></li>
<li lang="el">{row[1]}</li>
<li lang="el_LEMMA">{row[2]}</li>
<li lang="en_MORPH">{row[7]}{row[8]}</li>
<li lang="en_GLOSS">{row[3]}</li>
<li><small>{row[4] if row[4] else '-'}</small></li>
<li><small>{row[5]+'%' if row[5] else 'V'}</small></li>
<li><small>{tagsHtml}</small></li>
<li><small><a title="View word details" href="{'../'*level}rf/W/{wordNumber}.htm">{wordNumber}</a></small></li>
</ol></li>''' )
    riHtml = f'{riHtml}{NEWLINE.join( reverseList )}'


    html = f'''{html}{riHtml}</ol></div><!--interlinear-->
{rvHtml}'''
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n\n{iHtml=}" )
    checkHtml( f'Interlinear {BBB} {c}:{v}', html, segmentOnly=True )
    return html
# end of html.createInterlinearVersePage



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createInterlinearPages object
    pass
# end of createInterlinearPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createInterlinearPages object
    pass
# end of createInterlinearPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createInterlinearPages.py
