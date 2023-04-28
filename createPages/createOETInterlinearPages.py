#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createOETInterlinearPages.py
#
# Module handling OpenBibleData createOETInterlinearPages functions
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
Module handling createOETInterlinearPages functions.

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
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
import BibleOrgSys.Formats.ESFMBible as ESFMBible

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek, transliterate_Hebrew

from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTranslationNotes, tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    makeTop, makeBottom, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP, livenOETWordLinks


LAST_MODIFIED_DATE = '2023-04-28' # by RJH
SHORT_PROGRAM_NAME = "createOETInterlinearPages"
PROGRAM_NAME = "OpenBibleData createOETInterlinearPages functions"
PROGRAM_VERSION = '0.18'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


def createOETInterlinearPages( level:int, folder:Path, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearPages( {level}, {folder}, ... )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateOETInterlinearPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Prepare the book links
    BBBLinks, BBBNextLinks = [], []
    for BBB in state.booksToLoad['OET']:
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            ourTidyBBB = tidyBBB( BBB )
            BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="{BBB}/">{ourTidyBBB}</a>''' )
            BBBNextLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/James')}" href="../{BBB}/">{ourTidyBBB}</a>''' )

    # Now create the actual interlinear pages
    for BBB in state.booksToLoad['OET']:
        if BibleOrgSysGlobals.loadedBibleBooksCodes.isChapterVerseBook( BBB ):
            createOETInterlinearVersePagesForBook( level+1, folder.joinpath(f'{BBB}/'), BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinear', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Interlinear View" ) \
            .replace( '__KEYWORDS__', f'Bible, interlinear' )
    indexHtml = top \
                + '<h1 id="Top">OET interlinear verse pages</h1><h2>Index of books</h2>\n' \
                + f'''<p class="bkLst">{' '.join( BBBLinks )}</p>\n''' \
                + makeBottom( level, 'interlinear', state )
    checkHtml( 'InterlinearIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETInterlinearPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createOETInterlinearPages.createOETInterlinearPages


def createOETInterlinearVersePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state ) -> bool:
    """
    Create a page for every Bible verse
        displaying the interlinear verses.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook {level}, {folder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
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
        # referenceBible.loadBookIfNecessary( BBB )
        numChapters = referenceBible.getNumChapters( BBB )
        if numChapters: break
    else:
        logging.critical( f"createOETInterlinearVersePagesForBook unable to find a valid reference Bible for {BBB}" )
        return False # Need to check what FRT does

    vLinks = []
    if numChapters >= 1:
        lastNumVerses = 0
        for c in range( 1, numChapters+1 ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Creating interlinear pages for {BBB} {c}…" )
            numVerses = referenceBible.getNumVerses( BBB, c )
            if numVerses is None: # something unusual
                logging.critical( f"createOETInterlinearVersePagesForBook: no verses found for {BBB} {c}" )
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
                detailsLink = f''' <a title="Show details about the OET" href="{'../'*(level)}OET/details.htm">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} {c}:{v} <a title="Go to __WHERE__ of page" href="#CV__WHERE__">__ARROW__</a>{rightVLink}{rightCLink}{parallelLink}{detailsLink}</p>'
                iHtml = createOETInterlinearVersePage( level, BBB, c, v, state )
                filename = f'C{c}V{v}.htm'
                # filenames.append( filename )
                filepath = folder.joinpath( filename )
                top = makeTop( level, None, 'interlinear', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {c}:{v} Interlinear View" ) \
                        .replace( '__KEYWORDS__', f'Bible, {ourTidyBBB}, interlinear' ) \
                        .replace( f'''href="{'../'*level}pa/"''', f'''href="{'../'*level}pa/{BBB}/C{c}V{v}.htm"''')
                iHtml = top + '<!--interlinear verse page-->' \
                        + f'<p class="bkLst">{adjBBBLinksHtml}</p>\n<h1 id="Top">OET interlinear {ourTidyBBB} {c}:{v}</h1>\n' \
                        + f"{navLinks.replace('__ID__','CVTop').replace('__ARROW__','↓').replace('__WHERE__','bottom')}\n" \
                        + iHtml \
                        + f"\n{navLinks.replace('__ID__','CVBottom').replace('__ARROW__','↑').replace('__WHERE__','top')}\n" \
                        + makeBottom( level, 'interlinear', state )
                checkHtml( f'Interlinear {BBB} {c}:{v}', iHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as iHtmlFile:
                    iHtmlFile.write( iHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(iHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to interlinear verse page" href="{filename}">{c}:{v}</a>' )
            lastNumVerses = numVerses # for the previous chapter
    else:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {BBB} has {numChapters} chapters!!!" )
        assert BBB in ('INT','FRT',)
        # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePagesForBook {thisBible.books[BBB]=}" )

    # Create index page for this book
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'interlinear', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Interlinear View" ) \
            .replace( '__KEYWORDS__', f'Bible, interlinear' )
    # For Psalms, we don't list every single verse
    ourLinks = f'''<h1 id="Top">OET {ourTidyBBB} interlinear songs index</h1>
<p class="cLinks">{EM_SPACE.join( [f'<a title="Go to interlinear verse page" href="C{ps}V1.htm">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
                if BBB=='PSA' else \
f'''<p class="cLinks">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/James'} {' '.join( [f'<a title="Go to interlinear verse page" href="C{chp}V1.htm">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>
<h1 id="Top">OET {ourTidyBBB} interlinear verses index</h1>
<p class="vLinks">{' '.join( vLinks )}</p>'''
    indexHtml = f'{top}{adjBBBLinksHtml}\n{ourLinks}\n' \
                + makeBottom( level, 'interlinear', state )
    checkHtml( 'InterlinearIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createOETInterlinearVersePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of html.createOETInterlinearVersePagesForBook


def createOETInterlinearVersePage( level:int, BBB:str, c:int, v:int, state ) -> str:
    """
    Create an interlinear page for the Bible verse.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePage( {level}, {BBB} {c}:{v}, … )" )

    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"createOETInterlinearVersePage {level}, {BBB} {c}:{v}, …" )

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = tidyBBB( BBB )
    ourTidyBbb = tidyBBB( BBB, titleCase=True )
    C, V = str(c), str(v)

    lvBible = state.preloadedBibles['OET-LV']
    rvBible = state.preloadedBibles['OET-RV']
    wordTable = state.OETRefData['word_table']

    html = '<h2>SR Greek word order <small>(including unused variants)</small></h2><div class=interlinear><ol class=verse>'
    try:
        lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB, C, V) )
        livenedLvVerseEntryList = livenOETWordLinks( lvBible, BBB, lvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
        lvTextHtml = do_OET_LV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET-LV', (BBB,c,v), 'verse', lvContextList, livenedLvVerseEntryList, basicOnly=True, state=state ) )
        lvHtml = f'''<div class="LV"><p class="LV"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET</a> (<a title="{state.BibleNames['OET-LV']}" href="{'../'*level}OET-LV/byC/{BBB}_C{c}.htm">OET-LV</a>)</span> {lvTextHtml}</p></div><!--LV-->'''
    except (KeyError, TypeError):
        if BBB in lvBible and BBB in rvBible:
            warningText = f'No OET-LV {ourTidyBBB} {c}:{v} verse available'
            lvHtml = f'''<p><span class="wrkName"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET-LV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-LV {ourTidyBBB} book available'
            lvHtml = f'''<p><span class="wrkName">OET-LV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.critical( warningText )
        lvVerseEntryList = []
    try:
        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB, C, V) )
        livenedRvVerseEntryList = livenOETWordLinks( lvBible, BBB, rvVerseEntryList, f"{'../'*level}rf/W/{{n}}.htm", state )
        rvTextHtml = do_OET_RV_HTMLcustomisations( convertUSFMMarkerListToHtml( level, 'OET-RV', (BBB,c,v), 'verse', rvContextList, livenedRvVerseEntryList, basicOnly=True, state=state ) )
        rvHtml = f'''<div class="RV"><p class="RV"><span class="wrkName"><a title="View {state.BibleNames['OET']} chapter" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET</a> (<a title="{state.BibleNames['OET-RV']}" href="{'../'*level}OET-RV/byC/{BBB}_C{c}.htm">OET-RV</a>)</span> {rvTextHtml}</p></div><!--RV-->'''
    except (KeyError, TypeError):
        if BBB in rvBible:
            warningText = f'No OET-RV {ourTidyBBB} {c}:{v} verse available'
            rvHtml = f'''<p><span class="wrkName"><a title="{state.BibleNames['OET']}" href="{'../'*level}OET/byC/{BBB}_C{c}.htm">OET-RV</a></span> <span class="noVerse"><small>{warningText}</small></span></p>'''
        else:
            warningText = f'No OET-RV {ourTidyBBB} book available'
            rvHtml = f'''<p><span class="wrkName">OET-RV</span> <span class="noBook"><small>{warningText}</small></span></p>'''
        logging.critical( warningText )
        rvVerseEntryList = []
    tnHtml = formatTranslationNotes( level, BBB, C, V, 'interlinear', state )
    if tnHtml: tnHtml = f'<div class="TN"><b>uW Translation Notes</b>: {tnHtml}</div><!--end of TN-->\n'

    # We need to find where this BCV is in the wordtable
    # Rather than go thru the entire table, find any wordnumber in the verse, then work back from there
    wordNumberStr = None # in case there's no words
    lvEnglishWordList = []
    for lvVerseEntry in lvVerseEntryList:
        text = lvVerseEntry.getFullText()
        if not text or '¦' not in text: continue # no interest to us here

        # Remove sentence punctuation, break "chosen/messiah"
        #   then split into words
        lvEnglishWordList += text.replace(',','').replace('.','').replace(':','').replace('?','') \
                            .replace('\\add ','').replace('\\add*','') \
                            .replace('\\nd ','').replace('\\nd*','') \
                            .replace('\\sup ','<sup>').replace('\\sup*','</sup>') \
                            .replace('/messiah¦', ' messiah¦') \
                            .replace('_',' ').replace('   ',' ').replace('  ',' ') \
                            .strip().split( ' ' )
        # print( f"Found {BBB} {c}:{v} {lvVerseEntry=}" )
        ixMarker = text.index( '¦' )
        if not wordNumberStr: # We only need to find one word number (preferably the first one) here
            wordNumberStr = ''
            for increment in range( 1, 7 ): # (maximum of six word-number digits)
                if text[ixMarker+increment].isdigit():
                    wordNumberStr = f'{wordNumberStr}{text[ixMarker+increment]}' # Append the next digit
                else: break
        # break
    rvEnglishWordList = []
    for rvVerseEntry in rvVerseEntryList:
        text = rvVerseEntry.getFullText()
        if not text or '¦' not in text: continue # no interest to us here
        
        # Remove sentence punctuation,
        #   then split into words
        rvEnglishWordList += text.replace(',','').replace('.','').replace(':','').replace('?','') \
                            .replace('\\add ','').replace('\\add*','') \
                            .replace('\\nd ','').replace('\\nd*','') \
                            .replace('\\sup ','<sup>').replace('\\sup*','</sup>') \
                            .replace('_',' ').replace('   ',' ').replace('  ',' ') \
                            .strip().split( ' ' )

    # Make the English words into dicts
    lvEnglishWordDict = defaultdict( list )
    for extendedWord in lvEnglishWordList:
        if not extendedWord:
            logging.critical( f"OET-LV {BBB} {c}:{v} why did we get a zero-length word in {lvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.critical( f"OET-LV {BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
            # print( f"OET-LV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
            continue
        number = getLeadingInt( numberStr )
        if number < 1 or number >= len(wordTable):
            logging.critical( f"OET-LV {BBB} {c}:{v} word/number out of range from '{extendedWord}'" )
            # print( f"OET-LV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
        else:
            lvEnglishWordDict[number].append( word )
    rvEnglishWordDict = defaultdict( list )
    for extendedWord in rvEnglishWordList:
        if not extendedWord:
            logging.critical( f"OET-RV {BBB} {c}:{v} why did we get a zero-length word in {rvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.warning( f"OET-RV {BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
            # print( f"OET-RV {BBB} {c}:{v} {text=} {lvEnglishWordList=}")
            continue
        number = getLeadingInt( numberStr )
        if number < 1 or number >= len(wordTable):
            logging.critical( f"OET-RV {BBB} {c}:{v} word/number out of range from '{extendedWord}'" )
            # print( f"OET-RV {BBB} {c}:{v} {text=} {rvEnglishWordList=}")
        else:
            rvEnglishWordDict[number].append( word )

    # print( f"Found {BBB} {c}:{v} ({len(EnglishWordList)}) {EnglishWordList=}" )
    iHtml = ''
    if wordNumberStr: # Now we have a word number from the correct verse
        firstWordNumber = getLeadingInt( wordNumberStr )
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

        # Display the interlinear blocks
        GreekList = ['''<li><ol class="titles">
<li lang="el">Greek word</li>
<li lang="el_LEMMA">Greek lemma</li>
<li lang="en_TRANS"><b>OET-LV words</b></li>
<li lang="en_TRANS"><b>OET-RV words</b></li>
<li lang="en_STRONGS">Strongs</li>
<li lang="en_MORPH">Role/Morphology</li>
<li lang="en_GLOSS">SR Gloss</li>
<li lang="en_CAPS">CAPS codes</li>
<li lang="en_PERCENT">Confidence</li>
<li lang="en_TAGS">OET tags</li>
<li lang="en_WORDNUM">OET word #</li>
</ol></li>''']
        for wordNumber in range( firstWordNumber, firstWordNumber+999 ):
            if wordNumber >= len(wordTable): # we must be in one of the last verses of Rev
                break
            rowStr = wordTable[wordNumber]
            if not rowStr.startswith( f'{BBB}_{c}:{v}w' ): # gone into the next verse
                break
            row = rowStr.split( '\t' )
            #  0    1      2      3           4          5            6           7     8           9
            # 'Ref\tGreek\tLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags'
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
<li lang="en_TRANS"><b>{' '.join(lvEnglishWordDict[wordNumber]) if lvEnglishWordDict[wordNumber] else '-'}</b></li>
<li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
<li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[6][:-1]}.htm">{row[6]}</a></li>
<li lang="en_MORPH">{row[7]}{row[8]}</li>
<li lang="en_GLOSS">{row[3]}</li>
<li lang="en_CAPS">{row[4] if row[4] else '-'}</li>
<li lang="en_PERCENT">{row[5]+'%' if row[5] else 'V'}</li>
<li lang="en_TAGS">{tagsHtml}</li>
<li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}rf/W/{wordNumber}.htm">{wordNumber}</a></li>
</ol></li>''' )
        iHtml = f'{iHtml}{NEWLINE.join( GreekList )}'

    # Now append the OET-RV
    html = f'''{html}{iHtml}</ol></div><!--interlinear-->
{lvHtml}
{rvHtml}
{tnHtml}<h2>OET-LV English word order (‘Reverse’ interlinear)</h2><div class=interlinear><ol class=verse>'''

    # Now create the reverseInterlinear
    riHtml = ''
    reverseList = ['''<li><ol class="titles">
<li lang="en_TRANS"><b>OET-LV words</b></li>
<li lang="en_TRANS"><b>OET-RV words</b></li>
<li lang="en_STRONGS">Strongs</li>
<li lang="el">Greek word</li>
<li lang="el_LEMMA">Greek lemma</li>
<li lang="en_MORPH">Role/Morphology</li>
<li lang="en_GLOSS">SR Gloss</li>
<li lang="en_CAPS">CAPS codes</li>
<li lang="en_PERCENT">Confidence</li>
<li lang="en_TAGS">OET tags</li>
<li lang="en_WORDNUM">OET word #</li>
</ol></li>''']
    lastWordNumber = None
    for extendedWord in lvEnglishWordList:
        if not extendedWord:
            logging.critical( f"{BBB} {c}:{v} why did we get a zero-length word in {lvEnglishWordList}???" )
            continue
        try: word,numberStr = extendedWord.split( '¦' )
        except ValueError:
            logging.critical( f"{BBB} {c}:{v} word/number split failed on '{extendedWord}'" )
        wordNumber = getLeadingInt( numberStr )

        if wordNumber == lastWordNumber: # Put into the last cell
            lastEntry = reverseList.pop()
            lastEntry = lastEntry.replace('</b></li>', f' {word}</b></li>', 1)
            reverseList.append( lastEntry )
        else:
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
<li lang="en_TRANS"><b>{' '.join(rvEnglishWordDict[wordNumber]) if rvEnglishWordDict[wordNumber] else '-'}</b></li>
<li lang="en_STRONGS"><a href="https://BibleHub.com/greek/{row[6][:-1]}.htm">{row[6]}</a></li>
<li lang="el">{row[1]}</li>
<li lang="el_LEMMA">{row[2]}</li>
<li lang="en_MORPH">{row[7]}{row[8]}</li>
<li lang="en_GLOSS">{row[3]}</li>
<li lang="en_CAPS">{row[4] if row[4] else '-'}</li>
<li lang="en_PERCENT">{row[5]+'%' if row[5] else 'V'}</li>
<li lang="en_TAGS">{tagsHtml}</li>
<li lang="en_WORDNUM"><a title="View word details" href="{'../'*level}rf/W/{wordNumber}.htm">{wordNumber}</a></li>
</ol></li>''' )
        lastWordNumber = wordNumber
    riHtml = f'{riHtml}{NEWLINE.join( reverseList )}'


    html = f'''{html}{riHtml}</ol></div><!--interlinear-->
{lvHtml}
{rvHtml}
<p><small><b>Note</b>: The OET-RV is still only a first draft, and only a few words have been (mostly automatically) matched to the Greek words that they’re translated from.</small></p>
{f'<p><b>Acknowledgements</b>: The SR Greek text, lemmas, morphology, and English gloss <small>(7th line)</small> are all thanks to the <a href="https://GreekCNTR.org/collation/index.htm?{CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR-GNT</a>.</p>' if BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ) else ''}'''
    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n\n{iHtml=}" )
    checkHtml( f'Interlinear {BBB} {c}:{v}', html, segmentOnly=True )
    return html
# end of html.createOETInterlinearVersePage



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETInterlinearPages object
    pass
# end of createOETInterlinearPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETInterlinearPages object
    pass
# end of createOETInterlinearPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createOETInterlinearPages.py
