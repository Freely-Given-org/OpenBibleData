#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData createSynopticPassagePages functions
#
# Copyright (C) 2024 Robert Hunt
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
Module handling createSynopticPassagePages functions.

CHANGELOG:
    2024-01-14 First attempt
"""
from gettext import gettext as _
from typing import Tuple, List
from pathlib import Path
import os
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.OriginalLanguages.Greek as Greek

from usfm import convertUSFMMarkerListToHtml
from Bibles import formatTyndaleBookIntro, formatUnfoldingWordTranslationNotes, formatTyndaleNotes, tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from createOETReferencePages import CNTR_BOOK_ID_MAP
from OETHandlers import livenOETWordLinks


LAST_MODIFIED_DATE = '2024-01-14' # by RJH
SHORT_PROGRAM_NAME = "createSynopticPassagePages"
PROGRAM_NAME = "OpenBibleData createSynopticPassagePages functions"
PROGRAM_VERSION = '0.01'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


SYNOPTIC_FILE_LOCATION = Path( '../SynopticPassages.tsv' )


def createSynopticPassagePages( level:int, folder:Path, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createSynopticPassagePages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateSynopticPassagePages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Load the file of links
    verseTable = {}
    pastPassageRef = None
    with open ( SYNOPTIC_FILE_LOCATION, 'rt', encoding='utf-8' ) as tsv_file:
        for j,line in enumerate( tsv_file ):
            line = line.rstrip( '\n' )
            print( f"{j}: {line}" )
            if not line or line.startswith( '#' ): continue
            if j == 0:
                assert line == 'PassageRef\tVerseRef\tRef1\tRef2\tRef3'
            else:
                bits = line.split( '\t' )
                assert len(bits) == 5
                passageRef, verseRef, ref1, ref2, ref3 = bits
                if passageRef:
                    assert passageRef.strip() == passageRef
                    passageRef1, passageRef2 = passageRef.split( '-' )
                    BBB, CV = passageRef1.split( '_' )
                    assert len(BBB) == 3
                    C, V = CV.split( ':' )
                    assert C.isdigit() and V.isdigit()
                    lastPassageRef = (BBB,C,V)
                    if BBB not in verseTable:
                        verseTable[BBB] = {}
                else: assert lastPassageRef
                assert verseRef and verseRef.strip() == verseRef
                assert ref1 and ref1.strip() == ref1
                assert ref2.strip() == ref2 # These last two are optional
                assert ref3.strip() == ref3
                verseBBB, verseCV = verseRef.split( '_' )
                assert verseBBB == lastPassageRef[0]
                verseC, verseV = verseCV.split( ':' )
                ourRef = (verseC,verseV)
                assert ourRef not in verseTable[verseBBB]
                assert ref1 and ref1.strip() == ref1
                BBB1, CV1 = ref1.split( '_' )
                assert BBB1 != lastPassageRef[0]
                C1, V1 = CV1.split( ':' )
                refs = [(BBB1,C1,V1)]
                if ref2:
                    assert ref2.strip() == ref2
                    BBB2, CV2 = ref2.split( '_' )
                    assert BBB2 != lastPassageRef[0]
                    C2, V2 = CV2.split( ':' )
                    refs.append( (BBB2,C2,V2) )
                    if ref3:
                        assert ref3.strip() == ref3
                        BBB3, CV3 = ref3.split( '_' )
                        assert BBB3 != lastPassageRef[0]
                        C3, V3 = CV3.split( ':' )
                        refs.append( (BBB3,C3,V3) )
                else: assert not ref3
                verseTable[verseBBB][ourRef] = refs
    print( f"{verseTable=}" )

    # Prepare the book links
    BBBNextLinks = []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BBB in verseTable:
            ourTidyBBB = tidyBBB( BBB )
            # BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{BBB}/">{ourTidyBBB}</a>''' )
            BBBNextLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''' )

    # Now create the actual synoptic pages
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BBB in verseTable:
            # BBBFolder = folder.joinpath(f'{BBB}/')
            createSynopticPassagePagesForBook( level, folder, BBB, BBBNextLinks, state )

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'synopticPassage', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Synoptic View" ) \
            .replace( '__KEYWORDS__', 'Bible, synoptic' )
    indexHtml = f'''{top}<h1 id="Top">Synoptic verse pages</h1>
<p class="note">Each page only contains a single verse with minimal formatting, but displays it in a large number of different versions to enable analysis of different translation decisions. Study notes, theme notes, and translation notes will also be displayed, although not every verse has these.</p>
<p class="note">Generally the older versions are nearer the bottom, and so reading from the bottom to the top can show how many English vocabulary and punctuation decisions propagated from one version to another.</p>
<h2>Index of books</h2>
{makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'synopticIndex', state)}
<p class="note"><small>Note: We would like to display more English Bible versions on these synoptic pages to assist Bible translation research, but copyright restrictions from the commercial Bible industry and refusals from publishers greatly limit this. (See the <a href="https://SellingJesus.org/graphics">Selling Jesus</a> website for more information on this problem.)</small></p>
{makeBottom( level, 'synopticPassage', state )}'''
    checkHtml( 'synopticIndex', indexHtml )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSynopticPassagePages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    halt
    return True
# end of createSynopticPassagePages.createSynopticPassagePages


class MissingBookError( Exception ): pass
class UntranslatedVerseError( Exception ): pass

def createSynopticPassagePagesForBook( level:int, folder:Path, BBB:str, BBBLinks:List[str], state ) -> bool:
    """
    Create a page for every Bible passage that has related verses in other synoptic gospels.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createSynopticPassagePagesForBook( {level}, {folder}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1


    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSynopticPassagePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = tidyBBB( BBB )
    ourTidyBbb = tidyBBB( BBB, titleCase=True )
    adjBBBLinksHtml = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'parallelVerse', state) \
            .replace( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )

    numChapters = None
    referenceBible = state.preloadedBibles['OET-LV']
    numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
    introLinks = [ '<a title="Go to parallel intro page" href="Intro.htm#Top">Intro</a>' ]
    cLinksPar = f'''<p class="chLst">{EM_SPACE.join( introLinks + [f'<a title="Go to parallel verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
        if BBB=='PSA' else \
            f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/(James)'} {' '.join( introLinks + [f'<a title="Go to parallel verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>'''

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
                interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*BBBLevel}il/{BBB}/C{C}V{V}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
                detailsLink = f''' <a title="Show details about these works" href="{'../'*(BBBLevel)}allDetails.htm#Top">©</a>'''
                navLinks = f'<p id="__ID__" class="vNav">{leftCLink}{leftVLink}{ourTidyBbb} Book Introductions <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>' if c==-1 \
                        else f'<p id="__ID__" class="vNav">{introLink}{leftCLink}{leftVLink}{ourTidyBbb} {C}:{V} <a title="Go to __WHERE__ of page" href="#__LINK__">__ARROW__</a>{rightVLink}{rightCLink}{interlinearLink}{detailsLink}</p>'
                synopticHtml = ''

                # ....

                filename = 'Intro.htm' if c==-1 else f'C{C}V{V}.htm'
                # filenames.append( filename )
                filepath = BBBFolder.joinpath( filename )
                top = makeTop( BBBLevel, None, 'synopticPassage', None, state ) \
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} {C}:{V} Synoptic View" ) \
                        .replace( '__KEYWORDS__', f'Bible, synoptic, {ourTidyBBB}' )
                if BBB in state.booksToLoad['OET']:
                    top = top.replace( f'''href="{'../'*BBBLevel}il/"''', f'''href="{'../'*BBBLevel}il/{BBB}/C{C}V{V}.htm#Top"''')
                synopticHtml = f'''{top}<!--synoptic passage page-->
{adjBBBLinksHtml}
{cLinksPar}
<h1>Synoptic {ourTidyBBB} {'Intro' if c==-1 else f'{C}:{V}'}</h1>
{navLinks.replace('__ID__','Top').replace('__ARROW__','↓').replace('__LINK__','Bottom').replace('__WHERE__','bottom')}
{synopticHtml}
{navLinks.replace('__ID__','Bottom').replace('__ARROW__','↑').replace('__LINK__','Top').replace('__WHERE__','top')}
{makeBottom( BBBLevel, 'synopticPassage', state )}'''
                checkHtml( f'Synoptic {BBB} {C}:{V}', synopticHtml )
                with open( filepath, 'wt', encoding='utf-8' ) as pHtmlFile:
                    pHtmlFile.write( synopticHtml )
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(synopticHtml):,} characters written to {filepath}" )
                vLinks.append( f'<a title="Go to synoptic passage page" href="{filename}#Top">{C}:{V}</a>' )

    # Create index page for this book
    filename1 = 'index.htm'
    filepath1 = BBBFolder.joinpath( filename1 )
    top = makeTop( BBBLevel, None, 'synopticPassage', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Synoptic View" ) \
            .replace( '__KEYWORDS__', 'Bible, synoptic' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}
{f'<h1 id="Top">{ourTidyBBB} synoptic songs index</h1>' if BBB=='PSA' else ''}
{cLinksPar}
{f'<h1 id="Top">{ourTidyBBB} synoptic verses index</h1>' if BBB!='PSA' else ''}
{f'<p class="vsLst">{" ".join( vLinks )}</p>' if BBB!='PSA' else ''}
{makeBottom( BBBLevel, 'synopticPassage', state )}'''
    checkHtml( 'synopticIndex', indexHtml )
    with open( filepath1, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath1}" )

    # Write a second copy of the index page up a level
    newBBBVLinks = []
    for vLink in vLinks:
        newBBBVLinks.append( vLink.replace('href="', f'href="{BBB}/') )
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, None, 'synopticPassage', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{ourTidyBBB} Synoptic View" ) \
            .replace( '__KEYWORDS__', 'Bible, synoptic' )
    # For Psalms, we don't list every single verse
    indexHtml = f'''{top}{adjBBBLinksHtml}
{f'<h1 id="Top">{ourTidyBBB} synoptic songs index</h1>' if BBB=='PSA' else ''}
{cLinksPar}
{f'<h1 id="Top">{ourTidyBBB} synoptic verses index</h1>' if BBB!='PSA' else ''}
{f'<p class="vsLst">{" ".join( newBBBVLinks )}</p>' if BBB!='PSA' else ''}
{makeBottom( level, 'synopticPassage', state )}'''
    checkHtml( 'synopticIndex', indexHtml )
    with open( filepath2, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath2}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSynopticPassagePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of createSynopticPassagePages.createSynopticPassagePagesForBook


def getPlainText( givenVerseEntryList ) -> str:
    """
    Takes a verseEntryList and converts it to a string of plain text words.

    Used to compare critical Greek versions.
    """
    plainTextStringBits = []
    for entry in givenVerseEntryList:
        # print( entry )
        marker, cleanText = entry.getMarker(), entry.getCleanText()
        # print( f"{marker=} {cleanText=}")
        if marker in ('v~','p~'):
            plainTextStringBits.append( cleanText )

    return ' '.join( plainTextStringBits )
# end of createSynopticPassagePages.getPlainText


def removeGreekPunctuation( greekText:str ) -> str:
    """
    Converts to lowercase and removes punctuation used in any Greek version.

    Used to compare critical Greek versions.
    """
    return ( greekText.lower()
                .replace(',','').replace('.','').replace('!','') # English punctuation marks
                .replace('?','').replace(';','') # English and Greek question marks
                .replace(';','').replace('·','').replace('·','').replace(':','') # English and Greek semicolons and colon
                .replace('(','').replace(')','').replace('[','').replace(']','') # Parentheses and square brackets
                .replace('“','').replace('”','').replace('‘','').replace('’','') # Double and single typographic quotation marks
                .replace('⸀','').replace('⸂','').replace('⸃','').replace('⸁','').replace('⸄','').replace('⸅','').replace('⟦','').replace('⟧','')
                .replace('ʼ','')
                .replace('˚','') # Used by SR-GNT to mark Nomina Sacra
                .replace('—',' ').replace('–',' ').replace('…',' ') # Em and en dashes and ellipsis are converted to spaces
                .replace('   ',' ').replace('  ',' ') # Clean up spaces
            .strip() )
# end of createSynopticPassagePages.removeGreekPunctuation


GREEK_CASE_CLASS_DICT = { 'N':'Nom','n':'Nom', 'G':'Gen','g':'Gen', 'A':'Acc','a':'Acc', 'D':'Dat','d':'Dat', 'V':'Voc','v':'Voc', }
GREEK_CASE_CLASS_KEY_DICT = { 'greekVrb':'<span class="greekVrb">yellow</span>:verbs',
                              'greekNom':'<span class="greekNom">light-green</span>:nominative/subject',
                              'greekAcc':'<span class="greekAcc">orange</span>:accusative/object',
                              'greekGen':'<span class="greekGen">pink</span>:genitive/possessor',
                              'greekDat':'<span class="greekDat">cyan</span>:dative/indirect object',
                              'greekVoc':'<span class="greekVoc">magenta</span>:vocative',
                              'greekNeg':'<span class="greekNeg">red</span>:negative'}
def brightenSRGNT( BBB, C, V, textHtml, verseEntryList, state ) -> Tuple[str,List[str]]:
    """
    Take the SR-GNT text (which includes punctuation and might also include <br> characters)
        and mark the role participants
    """
    # dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"brightenSRGNT( {BBB} {C}:{V} {textHtml}, {verseEntryList}, … )…" )

    punctuatedGrkWords = textHtml.replace( '<br>', ' ').split( ' ' )
    strippedGrkWords = [punctuatedGrkWord.lstrip( '“‘˚(' ).rstrip( '.,?!:”’·;)–…' ) for punctuatedGrkWord in punctuatedGrkWords]
    # print( f"  gW {grkWords=}" )

    # Match Greek words to word numbers
    firstWordNumber,lastWordNumber = state.OETRefData['word_table_index'][f'{BBB}_{C}:{V}']
    currentWordNumber = firstWordNumber
    grkWordNumbers = []
    for strippedGrkWord in strippedGrkWords:
        # print( f"  {BBB} {C}:{V} {strippedGrkWord=} {currentWordNumber=} from ({firstWordNumber},{lastWordNumber})" )
        ref, greekWord, SRLemma, _GrkLemma, glossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_table'][currentWordNumber].split( '\t' )
        while not probability and currentWordNumber < lastWordNumber:
            currentWordNumber += 1
            ref, greekWord, SRLemma, _GrkLemma, glossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = state.OETRefData['word_table'][currentWordNumber].split( '\t' )
        assert probability
        if not greekWord.startswith('κρ') and not greekWord.startswith('μακρ') and not greekWord.startswith('γενν'): # Seems there were some spelling changes
            # and greekWord not in ('κράββατον','κράββατόν'):
            if greekWord.lower() != strippedGrkWord.lower():
                logging.critical( f"Unable to find word number for {BBB} {C}:{V} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {len(grkWordNumbers)=}" )
                break # We failed to match -- it's not critical so we'll just stop here (meaning we won't have all the word numbers for this verse)
            # assert greekWord.lower() == strippedGrkWord.lower(), f"{BBB} {C}:{V} {currentWordNumber=} {greekWord=} {strippedGrkWord=} {len(punctuatedGrkWords)=} {grkWordNumbers=}"
        grkWordNumbers.append( currentWordNumber )    
        assert currentWordNumber <= lastWordNumber
        currentWordNumber += 1
    if len(grkWordNumbers) != len(punctuatedGrkWords):
        logging.critical( f"brighten SR-GNT was unable to find word numbers for all words for {BBB} {C}:{V} (got {len(grkWordNumbers)} out of {len(punctuatedGrkWords)})" )

    # TODO: Not totally sure that we need these extras from https://github.com/Center-for-New-Testament-Restoration/SR files
    #           now that we have the word numbers for the Greek words
    allExtras = None
    for verseEntry in verseEntryList:
        # print( f"    vE {verseEntry=}" )
        marker, extras = verseEntry.getMarker(), verseEntry.getExtras()
        if extras: # Extras contain the info we need, like: ww @ 4 = 'Ἀρχὴ|lemma="ἀρχή" x-koine="αρχη" x-strong="G07460" x-morph="Gr,N,....NFS"'
            # print( f"      ME {marker=} {extras=}" )
            if allExtras is None:
                allExtras = list( extras )
            else: allExtras += list( extras )

    classKeySet = set()
    if allExtras:
        # Find each word in textHtml, find the word info in allExtras, and then update textHtml with more classes
        searchStartIndex = wordNumberIndex = extraIndexOffset = 0
        for _safetyCount1 in range( len(punctuatedGrkWords)+1 ):
            rawGrkWord = punctuatedGrkWords[wordNumberIndex]
            ix = textHtml.index( rawGrkWord, searchStartIndex )
            # print( f"  aE {wordNumberIndex=} {rawGrkWord=} {searchStartIndex=} {ix=} {extraIndexOffset=}")
            assert ix != -1
            simpleGrkWord = rawGrkWord.lstrip( '“‘˚(' )
            ix += len(rawGrkWord) - len(simpleGrkWord) # Adjust for removal of any leading punctuation
            simpleGrkWord = simpleGrkWord.rstrip( '.,?!:”’·;)–…' )
            assert simpleGrkWord.isalpha(), f"{simpleGrkWord=}"
            attribDict = {}
            for _safetyCount2 in range( 4 ):
                extraEntry = allExtras[wordNumberIndex+extraIndexOffset]
                # print( f"     {textHtml[ix:ix+20]=}… {extraEntry=}")
                extraType, extraText = extraEntry.getType(), extraEntry.getText()
                # print( f"       TyTxClTx {extraType=} {extraText=} {extraEntry.getCleanText()=}")
                if extraType != 'ww': extraIndexOffset += 1; continue # it could be a footnote or something
                if extraText.startswith( f'{simpleGrkWord}|' ):
                    extraText = extraText[len(simpleGrkWord)+1:] # Remove the word that we've just confirmed, left with something like 'lemma="ἁμαρτία" x-koine="αμαρτιασ" x-strong="G02660" x-morph="Gr,N,....AFP"'
                    for chunk in extraText.split( ' ' ):
                        fieldName, fieldValue = chunk.split( '=', 1 )
                        fieldValue = fieldValue.strip( '"' )
                        if fieldName.startswith( 'x-' ): fieldName = fieldName[2:]
                        if fieldName == 'morph':
                            assert fieldValue.startswith( 'Gr,' )
                            attribDict['role'] = fieldValue[3]
                            fieldValue = fieldValue[5:] # Get only the morph bit
                            assert len(fieldValue) == 7
                        elif fieldName == 'strong':
                            assert fieldValue[0] == 'G', f"{fieldValue=}"
                            fieldValue = fieldValue[1:] # Get only the numerical bit
                        # print( f"     {simpleGrkWord} {fieldName}='{fieldValue}'" )
                        attribDict[fieldName] = fieldValue
                    break
                print( f"Oops!!! {simpleGrkWord=} {extraText=}"); halt
            else: need_to_increase_count2_for_brightenSRGNT
            # print( f"    {attribDict=}" )
            try:
                wordLink = f'../../ref/GrkWrd/{grkWordNumbers[_safetyCount1]}.htm#Top' # We'd prefer to link to our own word pages
            except IndexError:
                wordLink = f'''https://BibleHub.com/greek/{attribDict['strong'][:-1]}.htm''' # default to BibleHub by Strongs number if we don't know the word number
            if attribDict['role'] == 'V':
                caseClassName = 'greekVrb'
            elif attribDict['strong'] == '37560': # Greek 'οὐ' (ou) 'not'
                caseClassName = 'greekNeg'
            elif attribDict['morph'][4] != '.':
                try:
                    caseClassName = f'''greek{GREEK_CASE_CLASS_DICT[attribDict['morph'][4]]}'''
                except KeyError:
                    print( f"{BBB} {C}:{V} {currentWordNumber=} {rawGrkWord=} {simpleGrkWord=} {attribDict=}" )
                    raise KeyError
            else: caseClassName = None
            if caseClassName: classKeySet.add( caseClassName )
            caseClassHtml = '' if not caseClassName else f'''class="{caseClassName}" ''' # Has a trailing space
            textHtml = f'''{textHtml[:ix-1]}<b>˚<a title="{attribDict['role']}-{attribDict['morph']}" {caseClassHtml}href="{wordLink}">{simpleGrkWord}</a></b>{textHtml[ix+len(simpleGrkWord):]}''' \
                        if '˚' in rawGrkWord else \
                        f'''{textHtml[:ix]}<a title="{attribDict['role']}-{attribDict['morph']}" {caseClassHtml}href="{wordLink}">{simpleGrkWord}</a>{textHtml[ix+len(simpleGrkWord):]}'''
            wordNumberIndex += 1
            if wordNumberIndex >= len(punctuatedGrkWords):
                break
            searchStartIndex = ix + len(simpleGrkWord)
        else: need_to_increase_count1_for_brightenSRGNT

    # Get the colour keys into the correct order
    classKeyList = []
    for classKey,classKeyHtml in GREEK_CASE_CLASS_KEY_DICT.items():
        if classKey in classKeySet:
            classKeyList.append( classKeyHtml )
    assert classKeyList

    return textHtml, classKeyList
# end of createSynopticPassagePages.brightenSRGNT


ENGLISH_WORD_MAP = ( # Place longer words first,
                     #     use space before to prevent accidental partial-word matches
                     #     since we're only doing string matches (but they're case sensitive)
    # Pairs of words (two words to two words)
    ((' a boot',),' a boat'),
    ((' afarre off',' afarre of',' a farre of'),' afar off'),
    ((' a none ',),' anon '),
    (('at euen ','at even ',),'at evening '),(('when euen ','when even '),'when evening '),(('when the euen ','when the even '),'when the evening '),
    (('carest for',),'care for/about'),
    (('fro God',),'from God'),
    (('get bred',),'get bread'),
    (('Hooli Goost',),'Holy Ghost'),
    (('loves have',),'loaves have'),
    (('nynthe our',),'ninth hour'),
    (('righte hade','right honde','riythalf'),'right hand'),
    (('sche felde ',),'she fell '),
    (('swete breed','swete bred'),'sweet bread'),
    (('the see ',),'the sea '),
    (('we han ',),'we have '),
    (('with greet',),'with great'),

    # Two words into one word
    (('a fore honde','afore hand','aforehande'),'aforehand'),
    ((' all wayes ',),' always '),
    ((' any thyng',' eny thinge',' any thing'),' anything'),
    ((' can not ',),' cannot '),
    (('even tyde',),'eventide/evening'),
    (('fare wel ',),'farewell '),
    (('Hos anna ',),'Hosanna '),
    ((' in deede ',' in dede '),' indeed '),
    ((' for o ',),' into '),
    ((' for euer',),' forever'),
    ((' her selfe',' her self',' hir selfe',' hir self'),' herself'),
    ((' hym silf',' hym selfe',' him selfe'),' himself'),
    ((' it selfe',' it self',' it silfe',' it silf',),' itself'),
    ((' lyke wyse',),' likewise'),
    (('money chaungeris','money chaungers'),'moneychangers'),
    (('sea syde','sea side'),'seaside'),
    (('strayght waye','streight waye'),'straightway'),
    (('taske maisters',),'taskmasters'),
    (('them selues',),'themselves'),
    (('thy selfe','thi silf','yi self'),'thyself/yourself'),
    ((' to gedder',' to geder',' to gidir'),' together'),
    (('with outen',),'without'),
    (('youre selues',),'yourselves'),

    # One word into two
    ((' assoone ',' assone '),' as soon '),
    ((' shalbe ',),' shall be '),((' shalbe.',),' shall be.'),
    ((' wilbe ',),' will be '),

    # Change single words (esp. middle English)
    ((' reuth ',),' pity/sorrow '),

    # Single words
    ((' abideth',),' abides'),((' abydinge',),' abiding'), ((' abyde ',),' abide '), ((' aboute',),' about'), ((' abrode',' abroade'),' abroad'), ((' abstayne ',),' abstain '),
        ((' accorde ',' acorde '),' accord '), (('knoulechide',),'acknowledged'),
        ((' affliccion',),' affliction'), ((' afrayed',' afrayde',' afraide'),' afraid'), ((' aftir ',' afer ',' eft '),' after '),(('Aftir',),'After'),
        ((' agaynste',' agaynst',' ageynste',' ayens'),' against'), ((' ayen,',),' again,'),((' agayne',' againe'),' again'),(('Againe',),'Again'),
        ((' aliaunt',),' alien/foreigner'), ((' aliue',' alyue',' alyve'),' alive'),
            (('Alle ',),'All '),((' alle ',' al '),' all '),((' alle,',' al,'),' all,'),
            ((' aloone',),' alone'),
            ((' alredy',),' already'),
            ((' altare',' aulter',' auter'),' altar'),
            ((' allwayes',' alwayes',' alwaies',' allwaie'),' always'),
        (('amased',),'amazed'), ((' amede',),' amend'), ((' amonge',' amoge'),' among'),
        (('Andrewe',),'Andrew'),
            ((' aungel',),' angel'), ((' angwische',),' anguish'),
            (('anoyntiden','anointide','annoynted','anoynted'),'anointed'),(('Annoynted',),'Anointed'),((' annoynt',' anoynte',' anoynt'),' anoint'),
                ((' anoon ',' anone ',' anon '),' anon/immediately '), (('Anothir',),'Another'),((' anothir',),' another'),
            (('answerden','answerede','answerde','answeride','aunswered'),'answered'),((' aunswere ',' answere '),' answer '),
            ((' ony ',' eny '),' any '), (('enythinge',),'anything'),
        (('apostlis',),'apostles'),
            (('appearaunce',),'appearance'),(('appearynge','apperynge','apperinge','appearyng'),'appearing'), (('appoynte','apoynte'),'appoint'),
        (('archaungel',),'archangel'), ((' aryse',),' arise'),(('Aryse ',),'Arise '), (('Arke ',),'ark '),((' arcke ',' arke '),' ark '), ((' arte ',),' art '),
        (('ascencioun',),'ascension'), ((' askeden',' axiden',' axide',' axed'),' asked'), ((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            (('astonnied','astonied','astonnyed','astonyed'),'astonished'), (('astromyenes',),'astronomers'),
        ((' eeten,',' eten,'),' ate,'), ((' athyrst',),' athirst'), ((' attayne ',' attaine '),' attain '),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
        ((' auoyded',),' avoided'),
        ((' awaye',' awei'),' away'),
    ((' backe ',),' back '), (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            (('basskettes','baskettes'),'baskets'), (('bastardes',),'bastards'),
            ((' batels',),' battles'),
        ((' bee ',),' be '),
            ((' bearinge',' beringe',' berynge'),' bearing'),((' beare ',' bere '),' bear '), (('beastes','beestes','beestis'),'beasts'),((' beesti',),' beast'),
            ((' beed ',' bedde '),' bed '),
            ((' bene ',' ben '),' been '),
            ((' bifore',' bifor'),' before'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), ((' bigat ',' begate '),' begat '), ((' beggere',' begger'),' beggar'), ((' beggide',),' begged'), (('bigynnyng','beginnynge','begynnynge','begynnyng','begynninge'),'beginning'), (('bigetun ','begotte '),'begotten '),
            (('behelde','biheeld'),'beheld'), ((' behinde',' bihynde',' behynde'),' behind'), ((' biholdinge',),' beholding'),(('Biholde','Beholde'),'Behold'),((' biholdist ',' biholde ', ' beholde '),' behold '),((' beholde,',),' behold,'), ((' bihoueth',),' behoves'),
            (('bileueden','beleeued','beleued','beleved'),'believed'), ((' bileueth',' beleueth',' beleeueth'),' believes'), (('Bileue ','Beleeue ','Beleue ','Beleve '),'Believe '),((' beleue',' beleeue',' beleve',' bileue'),' believe'), ((' belonge ',),' belong '), ((' beloued',' beloven'),' beloved'),
            ((' berith',),' beareth'),
            (('beseeching','besechyng'),'beseeching/imploring'),(('biseche ','beseech '),'beseech/implore '),(('biseche,','beseech,'),'beseech/implore,'), ((' besydes',),' besides'),((' bisidis',),' beside'),
            (('Bethanie ','Bethania ','Bethanye ','Betanye '),'Bethany '), (('Bethlehe ','Bethleem ','Bethlee '),'Bethlehem '), (('bitraiede','betraied'),'betrayed'),(('bitraye ','betraye ','betraie '),'betray '), ((' betere ',),' better '), ((' bitwixe',' betweene',' betwene'),' between'),
            ((' beyonde',' biyende',' biyondis'),' beyond'),
        ((' byd ',),' bid '), ((' byde ',),' bide/stay '), ((' bynde',),' bind'), ((' birthe',),' birth'),
        (('Blessid ',),'Blessed '),(('blesside','blissid'),'blessed'),
            (('blynde','blynd','blinde'),'blind'),
            (('bloude','bloud'),'blood'),
        ((' bootys',),' boats'),
            ((' boddy ',' bodi '),' body '),
            ((' booke ',' boke '),' book '),
            ((' boond ',),' bond '),
            ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'),
            ((' bosome ',' bosum '),' bosom '),
            ((' bothe ',),' both '),
            ((' boundun ',' bounde '),' bound '),
        ((' braunches',),' branches'),((' braunch',' braunche'),' branch'),
            (('britheren',),'brethren/brothers'),(('brithre.',),'brethren/brothers.'),(('brethren:','brethre:'),'brethren/brothers:'),
            ((' bryde',),' bride'), ((' bryngyng',),' bringing'), (('Brynge ','Bryng '),'Bring '),((' brynge ',),' bring '),
            ((' brouyten ',),' brought '),
        (('buyldynges','buildynges','bildyngis'),'buildings'),(('buyldinge',),'building'),
            ((' buriall',),' burial'),((' buryinge',' biriyng'),' burying'), ((' brent',),' burnt'),
            ((' busines',' busynesse',' busynes'),' business'),(('businesss',),'business'), ((' byers',' biggeris'),' buyers'),
        (('Bi ',),'By '),((' bi ',),' by '),
    ((' clepide',' clepid'),' called'),(('calleth','clepith'),'calleth/calls'),((' cal ',),' call '),
            ((' cam ',' camen '),' came '),((' cam,',' camen,'),' came,'),
            ((' kunne ',),' can '),
            (('Captaine','Captayne'),'Captain'), (('captiues',),'captives'),(('captyue',),'captive'),
            (('carpeter',),'carpenter'), ((' carieth',' caried'),' carried'),((' cary ',),' carry '),
            ((' castynge',' castyng',' castinge'),' casting/throwing'),((' castiden ',' kesten '),' cast/throw '),((' caste ',' keste '),' cast/threw '), (('casteles',),'castles'),
            ((' cattell',' catel'),' cattle'),
        (('Cæsar','Cesar'),'Caesar'),
            (('centurien',),'centurion'),
            ((' certayne',' certein',' certaine'),' certain'),
        (('cheynes','chaines'),'chains'), (('chamber','chaumber','chambre'),'chamber/room'), (('chaunced','chaunsed'),'chanced'), (('chaungeris',),'changers'), (('chastisith','chasteneth'),'chastens/disciplines'),
            ((' cheife ',' chefe '),' chief '), (('chyldren',),'children'),(('chylde,','childe,'),'child,'), (('chymney',),'chimney'),
            ((' chese ',),' choose '), (('chosun',),'chosen'),
            (('chirche',),'church'),(('Churche ',),'Church '),(('Churche,',),'Church,'),
            (('Christe','Crist'),'Christ'),
        ((' citees',),' cities'),((' cyte ',' citie ',' citee '),' city '),((' citie,',' citee,',' cite,'),' city,'),((' citie.',' citee.',' cite.'),' city.'),
        ((' claye ',' cley '),' clay '),((' clei,',' cley,',' claye,'),' clay,'),
            (('climbeth','clymmeth','clymeth','climeth'),'climbeth/climbs'),
            ((' clothis',),' clothes'), ((' cloudis',' cloudes'),' clouds'), ((' clouen',),' cloven'),
        ((' coostis',' coastes'),' coasts'), ((' cootis',' coottes',' coates',' cotes'),' coats'),
            ((' coold ',),' cold '), ((' coolte ',),' colt '),
            ((' cometh',' commeth'),' cometh/comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming'),' coming'),
                ((' conforted',' coforted',' coumfortid'),' comforted'),((' coumfortour',),' comforter'),
                (('commaundementes','commandementes','commandements'),'commandments'),(('commaundement','comaundement','commandement'),'commandment'),(('comaundide','commaunded','comaunded'),'commanded'), ((' commaunde ',' commaund '),' command '), ((' comyn',),' common'),
                (('companye',),'company'), (('comprehendiden',),'comprehended'),
            (('conseyue ',),'conceive '), (('confessioun',),'confession'), (('congregacion',),'congregation'), (('consyderest','considerest'),'consider'), (('consolacion',),'consolation'), (('contynued',),'continued'),(('contynuynge',),'continuing'), (('conueniently','coueniently'),'conveniently'),
            ((' corne ',),' corn '),
            ((' coulde',' coude'),' could'), ((' councill',' councell',' counsell'),' council'), ((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre'),' country'),
            ((' couered',),' covered'),
        ((' crieden',' criede',' cryed'),' cried'), (('crepell',),'crippled'),
            ((' crokid',),' crooked'), (('coroun ','croune ','crowne ',),'crown '), ((' crye ',' crie '),' cry '),((' crye,',' crie,'),' cry,'),
        ((' cuppe',),' cup'),
    ((' dayly',' daylie'),' daily'),
            ((' daunger ',),' danger '),
            (('derknessis','darkenesse','darknesse','darcknes'),'darkness'),
            (('douytris','doughters'),'daughters'),
            (('Daiud',),'David'),
            ((' daies',' dayes'),' days'), ((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),((' daye:',' daie:',' dai:'),' day:'),
        ((' dekenes',),' deacons'), ((' deed',),' dead'), (('Deare ',),'Dear '),((' deare ',' dere '),' dear '), ((' deeth',' deth',' derth'),' death'),
            (('disseyve','disceaue','deceave','deceiue'),'deceive'),
            ((' degre ',),' degree '),
            ((' delyte',),' delight'), (('delyuerauce','deliueraunce','deliuerance'),'deliverance'),((' deliuered',),' delivered'),((' delyuer ',' deliuer '),' deliver '),
            ((' denne ',' deen '),' den '), ((' denyede',' denyed'),' denied'),
            ((' departid',),' departed'),(('Departe ',),'Depart '),((' departe ',),' depart '),
            (('descendinge',),'descending'),(('descende ',),'descend '),
                ((' deseert ',' deserte '),' desert '),
                ((' desirith',' desyreth',' desireth'),' desires'), ((' desyred',),' desired'),
                ((' despysed',' dispiside'),' despised'),((' despyse ',' dispise '),' despise '),
                ((' distriede',),' destroyed'),((' distrie ',' destroye ',' distroye '),' destroy '),
            ((' deuelis',' devylles',' deuils',' deuyls'),' devils'),((' devyll',' deuell',' deuyll'),' devil'),
        ((' dyd ',' dide '),' did '),((' dide,',),' did,'),
            ((' dyeth ',' dieth '),' dieth/dies '), ((' dieden ',),' died '),((' diede,',),' died,'),
            ((' discerne:',),' discern:'), (('disciplis',),'disciples'), (('disdayned',),'disdained'),(('disdaine ',),'disdain '),
                ((' dyvers',' diuers'),' diverse/various'), (('devided','deuided','deuyded'),'divided'), (('devorsement','deuorcemet','diuorcement'),'divorcement'),
        ((' doe ',),' do '),((' doe?',),' do?'),
            (('doctryne',),'doctrine'),
            ((' doist ',),' doest '),
            ((' don ',),' done '),((' don,',),' done,'),((' don.',),' done.'),((' doon;',),' done;'),
            ((' doores',' dores'),' doors'),((' doore',' dore'),' door'),
            ((' doute,',),' doubt,'),
            ((' doue',),' dove'),
            ((' downe',' doune',' doun'),' down'),
        (('dredden','dredde'),'dreaded'), ((' dryncke',' drynke', ' drinke'),' drink'), ((' driueth',' driveth'),' drives'), ((' driue',' dryue'),' drive'),
            ((' drave',' droue'),' drove'), ((' drie ',),' dry '),((' dryed',),' dried'),
        ((' duste ',),' dust '), ((' duetie ',),' duty '),
        (('dwelliden','dwellide','dwellyde'),'dwelled/dwelt'),(('dwelleth','dwellith'),'dwells'), (('dwellynge','dwellinge'),'dwelling'),
    ((' ech ',),' each '),
            ((' eerli',' erly'),' early'), ((' eares ',' eeris ',' eris '),' ears '), ((' erthe',' erth'),' earth'),
            ((' easyer',),' easier'), ((' eest ',),' east '),
            ((' etynge',),' eating'),((' eate ',' ete '),' eat '),((' eate,',' ete,'),' eat,'),((' eate.',' ete.'),' eat.'),((' eate:',' ete:'),' eat:'),((' eate;',' ete;'),' eat;'),
        (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'),
        (('Egipte ',),'Egypt '),(('Egipt,',),'Egypt,'),
        ((' eldere ',),' elder '), (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'),
            ((' els ',),' else '),((' els,',),' else,'),
        (('Emperours',),'Emperors'),((' emperours',),' emperors'),(('Emperoure',),'Emperor'),((' emperoure',),' emperor'),
        ((' ende ',),' end '), (('ynough','inough'),'enough'), ((' entred',' entriden',' entride',' entrid'),' entered'),((' entereth',' entreth'),' entereth/enters'),((' entre ',),' enter '),
        (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'),
        (('Euen ',),'Even '),((' euen ',),' even '), ((' euenyng',' euening'),' evening'),((' euentid ',),' eventide/evening '),
            (('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' eueremore',' euermore'),' evermore'), (('Euery',),'Every'),((' euery',),' every'), ((' euer ',),' ever '),
        ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euyll'),' evil'),
        (('excedyngly','exceadingly','exceedyngly'),'exceedingly'), ((' excepte ',),' except '), ((' exercyse ',),' exercise '),
        ((' iyen,',),' eyes,'),((' iyen.',),' eyes.'),((' iyen;',),' eyes;'),
    ((' failinge',),' failing'), ((' faynte ',' faynt '),' faint '), ((' feith',' fayth'),' faith'),
            ((' falle ',),' fall '),
            ((' farre ',),' far '),((' farre.',' fer.'),' far.'),
            ((' fastynge',' fastyng',' fastinge'),' fasting'),
            ((' fadris',),' fathers'),((' fadir',),' father'), ((' fauoure',),' favour'),
        ((' feete',' fete'),' feet'), ((' fel ',),' fell '), ((' felowe',),' fellow'), ((' feawe ',' fewe '),' few '),((' feawe.',' fewe.'),' few.'),
        ((' fielde',' feeld',' felde'),' field'), ((' feendis',),' fiends'),
            ((' figges',' fygges'),' figs'),((' fygge ',' fyge ',' figge ',' fige ',),' fig '), ((' fiytyng',),' fighting'),(('Fyght',),'Fight'),((' fyght',' fighte'),' fight'),
            ((' fynde ',' finde '),' find '),((' fynnyssher',' fynissher',' finissher'),' finisher'),
            ((' fier ',' fyre '),' fire '),((' fier,',' fyre,'),' fire,'),((' fyre:',),' fire:'), ((' fyrste',' firste',' fyrst'),' first'),
            (('fischis','fysshes','fyshes'),'fishes'),(('fisscheris','fisshers','fysshers'),'fishers'),
            ((' fyue',' fyve',' fiue'),' five'),
        ((' flye ',' fleen ',' fle '),' flee '), ((' flesshe',' fleshe',' fleische',' fleisch'),' flesh'),
            ((' flyght ',),' flight '),
            (('flockis',),'flocks'), (('flowith ','floweth '),'floweth/flows '),
        ((' foale ',),' foal '),
            ((' foold ',),' fold '), ((' folkis',),' folks/people'), ((' folowed',' folewiden',' suede'),' followed'), ((' folowe',' folow',' suen'),' follow'), (('Folowe','Folow'),'Follow'),
            ((' foote ',' fote '),' foot '),
            (('forgeven','foryouun','forgeuen','forgiuen'),'forgiven'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '),
                ((' fornicacion',),' fornication'),
                ((' forsooke',' forsoke',),' forsook'),((' foorth',' forthe'),' forth'),
                ((' fourtie',' fourtye',' fourti'),' forty'),
            ((' founden ',' founde ',' foond ',' foud '),' found '), ((' fowre',' foure',' fower'),' four'),
        ((' gobetis',),' fragments'), ((' fre ',),' free '),((' fre.',),' free.'), ((' freli',),' freely'),
            ((' freend',' frende'),' friend'), (('Fro ',),'From '),((' fro ',),' from '), ((' fruyt ',' frute ',' fruite '),' fruit '),
        ((' ful ',),' full '), (('fulfillid','fulfylled'),'fulfilled'), ((' fornace',),' furnace'),
    (('Gayus',),'Gaius'), (('Galile ',),'Galilee '),(('Galile,',),'Galilee,'), ((' galoun',),' gallon'),
            ((' garmentes',' garmetes'),' garments'),((' garmente ',),' garment '),
            ((' yate',),' gate'), (('gadirid','gaderid','gadered','gaddred'),'gathered'),((' gadere ',' gaddre ',' geder '),' gather '),
            ((' yaf ',' gaue '),' gave '),
        (('generacioun','generacion'),'generation'),((' gentyls',),' gentiles'),
        ((' goost',),' ghost'),
        ((' yyueth',' geueth'),' giveth/gives'), ((' geven',' giuen',' geuen',' youun',' youe',' yyuen'),' given'), (('Geue ','Giue '),'Give '),((' geve ',' geue ',' giue ',' yyue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'),((' yyue?',' geue?',' geve?'),' give?'),
        ((' girdil',' gerdyll',' gerdell'),' girdle'),
        ((' gladde ',),' glad '), ((' glorie',),' glory'),
        (('Goo ','Goe '),'Go '),((' goe ',' goo '),' go '),((' goe.',' goo.'),' go.'),
            ((' goeth ',' goith '),' goeth/goes '), ((' goinge ',' goyng '),' going '),
            ((' golde ',),' gold '),((' golde.',),' gold.'),
            ((' goon ',),' gone '),
            (('Gospell',),'Gospel'),((' gospell',),' gospel'),
        (('Graunte ','Graunt '),'Grant '),((' graunte ',' graunt ',' graut '),' grant '),
            ((' gretter',),' greater'),((' greate ',' grete '),' great '),
            (('greeueth ',),'grieves '),
            (('growne ',),'grown '),
            (('grounde',),'ground'), (('grutchyng',),'groutching/grudging'),
        ((' ghest',' geest',' gest'),' guest'),
    ((' hadden ',' hadde '),' had '),((' hadde;',),' had;'), ((' heeris',),' hairs'),
            ((' handes',' hondes',' hoondis',' hondis'),' hands'),((' hande ',' honde ',' hoond ',' hond '),' hand '),
            ((' happe ',),' happen '), ((' happili',' haply'),' happily'),
            ((' hardnesse ',' hardnes '),' hardness '), ((' haruest',' heruest'),' harvest'),
            ((' hath ',),' hath/has '),
            (('Haue ',),'Have '),((' haue ',' han '),' have '), ((' havinge',' hauinge',' hauing',' hauynge',' havynge',' hauyng'),' having'),
        ((' hee ',),' he '),
            ((' helide',' heelid'),' healed'), ((' helthe ',),' health '), ((' hearde',' herden',' herde',' herd'),' heard'),((' herynge',' hearinge',' heringe',' hering'),' hearing'),((' heareth',' herith'),' hears'),((' heare',' heere'),' hear'),
                (('Heythen',),'Heathen'),((' hethene',),' heathen'),
                ((' heyre ',' heire '),' heir '),
                ((' hertis',' hertes',' heartes'),' hearts'),((' herte ',' hert '),' heart '), ((' heate',' heete'),' heat'), ((' heauens',' heuenes'),' heavens'), ((' heauen',' heuene',' heven'),' heaven'),
            (('Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'),
            ((' hede ',' heede '),' heed '),
            ((' helde ',),' held '), ((' helle ',),' hell '), ((' helpe ',),' help '),
            ((' hir ',' hyr '),' her '),((' hir,',),' her,'),((' hir.',),' her.'),((' hir;',),' her;'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), (('Erodians',),'Herodians'),(('Herodes',),"Herod's"),(('Herode ','Eroude '),'Herod '), (('Eroude,',),'Herod,'),
        ((' hidde ',),' hid '),
            ((' hiyeste',' hiyest'),' highest'),((' hye ',' hie ',' hiy '),' high '),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',' hi:'),' him:'),((' hym?',),' him?'), (('himselfe',),'himself'),
            ((' hiryd',' hyred'),' hired'), ((' hise ',' hys '),' his '),
            ((' hyther',' hidder',' hidir'),' hither'),
        ((' holde ',),' hold '), ((' holynesse',' holynes'),' holiness'),((' holines ',),' holiness '),
            (('honeste','honestye','honestie'),'honesty'), ((' hony',),' honey'), ((' onoure',' onour'),' honour'),(('honoure,',),'honour,'),
            (('Hosyanna','Osanna'),'Hosanna'),
            ((' houres',),' hours'),((' houre ',),' hour '), ((' housse ',' hous '),' house '),((' housse',),' house'),((' hous,',),' house,'), (('houssholde','housholde'),'household'),
            ((' hou ',' howe '),' how '),(('Hou ','Howe '),'How '),
        ((' hungren',),' hungering'),((' hungride',' hungred',' hugred'),' hungered'),((' hungur',' honger'),' hunger'), (('husbande','hosebonde'),'husband'),
        ((' hypocrisie',' ypocrisye'),' hypocrisy'),
    (('Y ',),'I '),((' Y ',),' I '),((' Y;',),' I;'),
        ((' Yd',),' Id'),
        (('Yf ',),'If '),((' yf ',),' if '), ((' ymage ',),' image '), (('Ys ',),'Is '),((' ys ',),' is '), ((' yssue',),' issue'),
        (('Yt ',),'It '),((' yt ',),' it '),
        (('encreased',),'increased'), (('indignacioun',),'indignation'), ((' inheret ',' inherite '),' inherit '), (('interpretacion',),'interpretation'),(('interprete ',),'interpret '),
        (('immediatelye','immediatly'),'immediately'),
    ((' ioperdy',),' jeopardy'),
        (('Iorney',),'Journey'),(('iourney',),'journey'),
            ((' ioye ',' ioy '),' joy '),
        (('iudgement','iudgment'),'judgement'),((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'), ((' iust ',),' just '),
    ((' keperis',),' keepers'),((' keepeth',' kepith',' kepeth'),' keepeth/keeps'),((' keepe',' kepe'),' keep'), ((' keyes',' keies'),' keys'),
        ((' killiden',' kylled',' kyllid'),' killed'),
            (('kingdome','kyngdoom','kyngdome','kyngdom'),'kingdom'), ((' kynges',' kyngis'),' kings'),((' kynge ',' kyng '),' king '),((' kynge,',' kyng,'),' king,'),((' kynge.',' kyng.'),' king.'), ((' kynnysmen',),' kinsmen'), ((' kynne',),' kin'),((' kyn,',),' kin,'),
            ((' kiste ',' kyssed '),' kissed '),
        (('knewest','knewen','knewe'),'knew'), (('knowyng',),'knowing'), (('knowne','knowun','knowen'),'known'), (('Knowe',),'Know'),((' knowe',' woot'),' know'),
    ((' labor',),' labour'), ((' lomb ',' lambe ',' labe '),' lamb '),(('Lambe',),'Lamb'), ((' lastynge',),' lasting'),
            ((' lande ',' londe ',' lond ',' lode '),' land '),((' lande,',' londe,',' lond,'),' land,'),((' loond.',' lande.',' londe.',' lond.'),' land.'),((' lande;',' londe;',' lond;'),' land;'),
            ((' laste ',),' last '),
            ((' laye ',),' lay '), ((' layed',' layde',' leiden', ' leyd',' layd'),' laid'),
            ((' leeueful',' leueful',' laufull',' lawfull'),' lawful'), (('Lawe.',),'Law.'),((' lawe ',),' law '),((' lawe,',),' law,'),((' lawe.',),' law.'),
        (('ledith','ledeth'),'leadeth/leads'), (('learnyng','learninge','lernynge'),'learning'),((' learne ',' lerne '),' learn '),(('Learne ','Lerne '),'Learn '), ((' leest',),' least'), ((' leeues',' leaues',' leves'),' leaves'), ((' leeue ',' leaue ',' leue ',' leve '),' leave '),
            ((' ledde ',' leden '),' led '),
            ((' leften',' leeft',' lefte'),' left'),
            (('Leuite',),'Levite'),
        (('lyberte','libertie'),'liberty'),
            ((' lyffe',' lyfe',' lijf'),' life'),
            ((' lyght',' liyt'),' light'),
            (('Lykewyse',),'Likewise'),(('lykewyse',),'likewise'), ((' lyke',' lijk',' lijc'),' like'),
            ((' litil',' lytell',' lytle',' litle'),' little'),
            ((' liueth',' lyueth'),' liveth/lives'),((' liues',),' lives'),((' lyuynge',' lyuyng',' liuing',' livynge'),' living'),((' liue ',' lyue '),' live '),((' liue,',' lyue,'),' live,'),
        ((' looues',' loaues'),' loaves'),
            ((' loynes',),' loins'),
            ((' longe ',),' long '),((' longe,',),' long,'),
            ((' lokide',' loked'),' looked'),(('lokynge',),'looking'),(('Lokyng ',),'Looking '),(('Loke ',),'Look '),((' looke ',' loke '),' look '), ((' loosyng',' loosinge'),' loosing'),
            ((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),
            (('Loth ',),'Lot '),
            ((' louede',' loued',' louyde'),' loved'),((' loveth',' loueth'),' loveth/loves'),((' lovest',' louest'),' lovest/love'),((' louen ',' loue '),' love '),
    ((' maad',),' made'),
            ((' maymed',),' maimed'),
            ((' makynge',),' making'),((' makere ',),' maker '),
            ((' mannus',),' man\'s'),((' ma ',),' man '), ((' maner',),' manner'), ((' manye ',),' many '),
            ((' mariage',),' marriage'), (('marueyled','marueiled','merveled','marueled','merveyled','marveled'),'marvelled'), (('Maryes',),"Mary's/Maria's"),(('Marye','Marie'),'Mary/Maria'),
            (('Maister','Maistir'),'Master'),((' maister',),' master'),
            ((' mayest',' mayst'),' mayest/may'),((' maye ',' maie '),' may '),((' maye.',),' may.'),(('Maye ',),'May '),
        ((' `metis ',' metis '),' meats '),((' meate ',),' meat '),
            ((' meeke ',' meke '),' meek '),((' meeke:',' meke:'),' meek:'), ((' metinge',' metyng'),' meeting'),((' meete ',' mete '),' meet '),((' meete,',' mete,'),' meet,'),((' meete:',' mete:'),' meet:'), (('meekenes','mekenes','meknes'),'meekness'),
            ((' mendynge',' mendyng',' mendinge'),' mending'),
            ((' mercyfull ',' mercifull '),' merciful '),((' mercyfull:',' mercifull:'),' merciful:'),
            ((' mesure',),' measure'),
        ((' myddil',),' middle'),
            ((' myghty',' mightie',' miyti'),' mighty'),((' myyte',' myght'),' might'),
            ((' mylke ',' milke '),' milk '), (('mylstone','milstone'),'millstone'),
            ((' myndes',' mindes'),' minds'),((' mynde',),' mind'), ((' myne ',' myn '),' mine '), (('ministred','mynistred','mynystriden'),'ministered'),((' mynyster',' mynister'),' minister'),
            ((' myracles',),' miracles'),
        ((' mony',),' money'),
            (('Moreouer','Morouer'),'Moreover/What\'s_more'),(('morouer',),'moreover/what\'s_more'), ((' moare ',' mowe '),' more '), ((' morninge',' mornynge',' mornyng',' morewtid'),' morning'), ((' morowe',' morow'),' morrow'),
            (('Moises','Moyses'),'Moses'),
            ((' moder ',' modir '),' mother '),
            ((' mountayne',' mountaine'),' mountain'), ((' moute ',),' mount '), ((' mornen ',' mourne ',' morne '),' mourn '),((' mornen,',' mourne,',' morne,'),' mourn,'),((' mornen:',' mourne:',' morne:'),' mourn:'),
            ((' moued',),' moved'),
        ((' myche',' moche',' moch',' muche'),' much'), (('murthurers',),'murderers'),(('murthurer',),'murderer'),
    ((' naciouns',' nacions'),' nations'), ((' natiue',),' native'),
        ((' neere ',' neare '),' near '),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),
            ((' nedeful',),' needful'),((' nedes',),' needs'),((' neede ',' neade ',' nede '),' need '),
            ((' neiyboris',' neghboures',' neghbours',' neyghbours'),' neighbours'), (('Nether ',),'Neither '),((' nether',' nethir'),' neither'),(('(nether',),'(neither'),
            ((' nettes',' nettis'),' nets'),
            (('Neuertheles ',),'Nevertheless '), ((' neuer',),' never'),
            ((' nexte',),' next'),
        ((' neer ',' nyer ',' nier '),' nigher/nearer '),((' nyy ',' nye '),' nigh/near '),((' nyy.',' nye.'),' nigh/near.'), ((' nyyti',' nyyt',' nyght'),' night'), ((' nyenth',' nynthe',' nynth'),' ninth'),
        ((' ner ',' ne '),' nor '), (('northwarde',),'northward'),
            (('nothinge','nothyng'),'nothing'),
        (('Nowe ',),'Now '),((' nowe ',),' now '),
        (('numbred',),'numbered'),(('noumbre','nombre','nomber'),'number'),
    ((' obteyne ',' obteine '),' obtain '),
        ((' of;',),' off;'), ((' offende ',),' offend '),((' offende,',),' offend,'), ((' offerynge',),' offering'),
        ((' oyle ',),' oil '),((' oyle,',),' oil,'), ((' oynement',' oyntment'),' ointment'),
        ((' eeld ',' eld ',' olde '),' old '),((' eeld,',' olde,'),' old,'),
            (('Oliuete','olivete'),'Olivet'),(('Olyues','Oliues'),'Olives'),
        ((' oon ',),' one '),((' oon.',),' one.'), ((' onely ',' `oon '),' only '),
        ((' openyde',' openyd'),' opened'), ((' opynyouns',),' opinions'), ((' oppressith',),' oppresses'),
        (('Othere','Othir','Wother'),'Other'),((' othere ',),' other '),
        ((' oure ',),' our '),
            ((' outwarde',),' outward'), ((' oute.',),' out.'),
        ((' ouer',),' over'),
        ((' awne ',' owne '),' own '),
    ((' parablis',),' parables'), ((' partynge',),' parting'), ((' parts',' parties'),' parts/region'),
            (('Passeouer','Passouer'),'Passover'),((' passiden',' passide'),' passed'),((' passynge',),' passing'),((' passe ',),' pass '),((' passe?',),' pass?'),((' passe:',),' pass:'),
            ((' pacience',),' patience'),
            (('Pavl',),'Paul'),
            ((' paye ',),' pay '),
        ((' pees',),' peace'),
            (('penaunce',),'penance'), ((' penie ',' peny '),' penny '),((' penie,',' peny,'),' penny,'),
            (('puplis',),'peoples'),((' puple',' pople'),' people'),
            (('perceiued','perceaved','perceaued'),'perceived'),(('Perceave','Perceiue'),'Perceive'),((' witen',),' perceive'),
                ((' perfaicte ',),' perfect '), ((' perfourme ',),' perform '),
                ((' perel ',),' peril '), ((' perische',' perisshe',' perishe'),' perish'),
                (('persecucioun','persecucion'),'persecution'),
                (('perteyneth',),'pertaineth/pertains'),(('pertayne ',),'pertain '),
            (('Petir',),'Peter'),
        (('Fariseis','Farisees','Pharises','pharisees','pharises'),'Pharisees'), (('Philippe',),'Philip'),
        ((' peaces',' peeces',' peces'),' pieces'), ((' pearced',),' pierced'), ((' pylgrym',),' pilgrim'), ((' pyned',),' pined'), ((' reuthe',),' pity'),
        (('playnely','playnly','plainely'),'plainly'), ((' playne ',' plaine '),' plain '),
            ((' pleside',' plesid'),' pleased'), ((' plente ',),' plenty '),
            ((' plucke ',),' pluck '),
        ((' poole ',),' pool '), ((' poore ',' povre ',' pore '),' poor '), (('possessyoun',),'possession'),(('possesse ',),'possess '), ((' powdir',),' powder'),
        (('praysed',),'praised'), (('preyeden','preiede','praied'),'prayed'),(('preier',),'prayer'),(('preyng',),'praying'),((' preye ',' praye '),' pray '),
            (('prechiden','prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge'),'preaching'), (('preche ','preache '),'preach '), (('preuent',),'prevent'),
            (('preestis','prestis','prestes','priestes'),'priests'),(('Priestes','Prestes'),'Priests'),(('prieste','preste','prest',),'priest'), (('princis','prynces'),'princes'),
                (('prisouneris','presoners'),'prisoners'), (('pryuatly',),'privately'),
            (('promysed','bihiyten'),'promised'), (('Prophetes',),'Prophets'),(('profetis','prophetes'),'prophets'), (('Prophete',),'Prophet'),((' prophete ',),' prophet '),((' prophete,',),' prophet,'),((' prophete.',),' prophet.'),((' prophete?',' profete?'),' prophet?'),
                ((' preued',),' proved'),((' proue ',),' prove '), (('prouerbe',),'proverb'),
        (('publysshed',),'published'),
            ((' pourses',),' purses'), (('Sue ',),'Pursue '),
            ((' putteth ',),' putteth/puts '),
    (('quenchid','queched'),'quenched'),
    (('Rabi',),'Rabbi'), ((' raysed',),' raised'),((' reise',' reyse',' rayse'),' raise'),
        ((' redi ',),' ready '), ((' realme',' rewme'),' realm'), (('reasonyng','reasoninge'),'reasoning'),
            ((' resseyueth',' receaveth',' receaueth',' receiueth'),' receives'),((' resseyueden',' receaved',' receaued',' receiued'),' received'),((' resseyue',' receave',' receaue',' receiue'),' receive'), (('recompence',),'recompense'), ((' recorde ',),' record '), (('recouering',),'recovering'),
            (('refrayne ',),'refrain '),
            (('regardest',),'regard'),
            ((' raygne ',),' reign '),
            (('remayned',),'remained'),(('remaynynge','remayninge','remayning'),'remaining'), (('remembraunce',),'remembrance'), (('remyssion','remissioun'),'remission'),
            (('repentaunce',),'repentance'),
            ((' reste ',),' rest '), (('ressurreccioun','resurreccion'),'resurrection'),
            ((' returne ',),' return '),
            ((' rewarde ',),' reward '),((' rewarde.',),' reward.'),
        ((' riche ',),' rich '),
            ((' ryght ',' riyt '),' right '), (('riytwisnesse ','rightewesnes ','righteousnes '),'righteousness '),(('riytwisnesse,','rightewesnes,','righteousnes,'),'righteousness,'),(('riytwisnesse:','rightewesnes:','righteousnes:'),'righteousness:'),((' ryghteous',),' righteous'),
            ((' risith',),' riseth/rises'), ((' ryse ',),' rise '),
        ((' rodde ',),' rod/staff '),((' rodde:',),' rod/staff:'),
            ((' roofe',' rofe'),' roof'), ((' roume',' rowme'),' room'), ((' rootis',),' roots'),((' roote',' rote'),' root'),
            ((' roos ',),' rose '),
        (('ruleth','rueleth'),'rules'), ((' rulars',),' rulers'),
    (('Sabbathes',),'Sabbaths'),((' sabatys',),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabat',' saboth'),' sabbath'),
            ((' sacrifise',),' sacrifice'),
            (('Saduceis','Saduces','Sadduces'),'Sadducees'),
            ((' saaf',),' safe'),
            ((' seyden',' seiden',' seide',' seid',' sayde',' sayd',' saide', ' seien'),' said'),
            ((' saltid',),' salted'),
            ((' sate ',),' sat '), (('Sathanas','Sathan'),'Satan'), ((' satisfie ',),' satisfy '),
            ((' saued',),' saved'),((' saue ',),' save '),((' sauyng',' sauinge',' sauing',' savinge'),' saving'), ((' sauery',),' savoury'),
            ((' sawe ',' sai ',' sayn ',' siy '),' saw '),
            ((' seist',),' sayest'),((' sayege',' sayinge',' saynge'),' saying'), ((' seith ',' sayth '),' saith/says '), ((' seie ',' seye ',' saye '),' say '),((' seie,',' saye,'),' say,'),((' seie:',' saye:'),' say:'),
        (('Scrybes',),'Scribes'), ((' scribis',' scrybes'),' scribes'),
        (('seesyde ' ,'seeside ',),'seaside '), ((' seet ',),' seat '),
            ((' secounde ',' seconde '),' second '),
            ((' seynge',' seinge',' seyng'),' seeing'),((' seiy ',' se '),' see '),((' se.',),' see.'), ((' seede ',' sede '),' seed '), ((' seken ',' seeke ',' seke '),' seek '), ((' semen ',' seeme ',' seme '),' seem '), ((' seyn ',' seene ',' sene '),' seen '),((' seyn,',' seene,',' sene,'),' seen,'),
            ((' silfe ',' silf ',' selfe '),' self '),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'), ((' silleris',),' sellers'), ((' selues',),' selves'),
            ((' sendeth',' sendith'),' sendeth/sends'),((' sende ',),' send '), ((' senten ',' sente '),' sent '),
            ((' sermoun',),' sermon'), ((' serue ',),' serve '), (('seruauntis','seruauntes','servauntes','seruants','servantes'),'servants'),((' seruaunt',' servaunt',' seruant'),' servant'),
            ((' sette ',),' set '),
            (('seuenthe ','seuenth '),'seventh '),((' seuene ',' seuen ',' seue '),' seven '),
        ((' schal ',' shal ',),' shall '),
            (('Sche ',),'She '),((' sche ',' shee '),' she '), (('sheepefolde','sheepfolde','shepefolde'),'sheepfold'), ((' scheep ',' sheepe ',' shepe '),' sheep '),((' scheep,',' sheepe,',' shepe,'),' sheep,'), (('scheepherdis',),'shepherds'),(('scheepherde','shepeherde','shepherde','sheephearde','shephearde','shepheard'),'shepherd'),
            (('schyneth','shyneth'),'shineth/shines'),(('schynynge',),'shining'), ((' shippes',),' ships'),((' shyppe',' shyp',' shippe',' schip'),' ship'),
            ((' shue',),' shoe'),((' schoo.',),' shoe.'), ((' shoore',),' shore'), (('shouldest','schulen'),'should'),((' schulden ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '), (('shoute ','showte '),'shout '), (('schewide','schewid','shewed'),'showed'),((' schewe ',' shewe '),' show '),
        ((' syknesse',' sicknesse',' sickenes'),' sickness'),((' sicke',' sijk'),' sick'),
            ((' syde ',),' side '),((' syde.',),' side.'),((' syde:',),' side:'),
            ((' syght ',' sighte '),' sight '),((' sighte,',),' sight,'), ((' signes',),' signs'),((' signe ',),' sign '),
            ((' siluer',),' silver'),
            (('Symount','Symon'),'Simon'), ((' simulacion',),' simulation'),
            ((' synners',),' sinners'),((' synner',),' sinner'), ((' synfull',' synful'),' sinful'),((' sinnes',' synnes'),' sins'),((' synnede',' synned'),' sinned'),((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),
            ((' sistris',' systers'),' sisters'),((' sistir',),' sister'),
            ((' syttyng',),' sitting'),((' sitten ',' sitte ',' syt '),' sit '), ((' liggynge',),' situated'),
            ((' sixte ',' sixt '),' sixth '), ((' sixe ',),' six '),
        ((' skynne ',' skyn ',' skinne '),' skin '),
        ((' slayn',' slaine'),' slain/killed'), (('sclaundrid',),'slandered/disgraced'), ((' slepith',),' sleeps'),((' slepte ',),' slept '),(('Sleepe ','Slepe '),'Sleep '),((' sleepe',' slepe'),' sleep'),
        ((' smale ',),' small '),
        (('Sodome ','zodom '),'Sodom '),
            ((' soiourne',),' sojourn'),
            ((' solde ',),' sold '), ((' solitarie',),' solitary'),
            ((' summe ',),' some '),
            ((' sonnes',' sones'),' sons'), ((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),  (('Sonne ',),'Son '),(('Sonne,',),'Son,'),
            ((' sorewis',' sorowes'),' sorrows'),((' sorewe ',),' sorrow '),((' sorowe,',),' sorrow,'), ((' sory ',),' sorry '),
            ((' souyten',),' sought'), ((' sounde',),' sound'), (('southwarde',),'southward'), (('souereynes',),'sovereigns'),
        ((' spette ',' spate '),' spat '),
            (('speakynge','spekynge','speakinge','spekinge','speakyng'),'speaking'),((' spekith',' speaketh'),' speaks'),((' speake',),' speak'),
            ((' spyed',),' spied'), ((' spirite',' sprete'),' spirit'), (('spotil','spetil','spettle'),'spittle'),
            ((' spak ',),' spoke '),
            ((' sprede ',' spred '),' spread '),
        ((' staffe ',),' staff '), ((' stondith',),' standeth/stands'),((' stande ',' stonde '),' stand '),((' stonde.',),' stand.'),
            (('Steppe ',),'Step '),
            ((' styll',),' still'),
            ((' stockis',),' stocks'), ((' stoonys',),' stones'),((' stoone',' stoon'),' stone'), ((' stoode ',' stoden ',' stode '),' stood '), ((' stoupe',' stowpe'),' stoop'),
            (('strayght',),'straight'), (('straunger',),'stranger'),(('straunge ',),'strange '), ((' strewiden ',' strawed ',' strowed '),' strewed '), ((' strijf ',' stryfe '),' strife '),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'), (('stumbleth','stombleth','stomblith'),'stumbles'),
        (('subiection','subieccion'),'subjection'),((' suget',),' subject'), (('substaunce',),'substance'),
            ((' soch ',' suche ',' siche '),' such '), ((' soucke ',' sucke '),' suck '),
            (('suffrith',),'suffereth/suffers'),((' suffride',' suffred'),' suffered'),(('Suffre ',),'Suffer '),((' suffre ',),' suffer '), (('suffysed','suffised'),'sufficed'),
            (('Sommer',),'Summer'),((' sommer ',' somer '),' summer '),
            ((' sunne ',),' sun '),
            (('superscripcion',),'superscription'), (('supplicacion',),'supplication'),
        (('swete ',),'sweet '),
        (('synagoge',),'synagogue'),
    (('tabernaclis',),'tabernacles/tents'),
            ((' takun',),' taken'), ((' takynge',),' taking'),(('Takyng',),'Taking'),
            ((' talke.',),' talk.'),
            ((' taried',),' tarried/waited'),(('Tarye ','Tary '),'Tarry/Wait '),
            (('taskemasters:',),'taskmasters:'), ((' taist ',),' taste '),
            ((' tauyte',),' taught'),
        (('techyng','teching'),'teaching'),((' teachest',' teache',' techist',' teche'),' teach'),
            (('temptacioun','temptacion','teptacion','tentation'),'temptation'), (('temptiden','temptid'),'tempted'), ((' tempte ',' tepte '),' tempt '),
            ((' tenauntes',),' tenants'), ((' tendre',' teder'),' tender'), ((' tentes',),' tents'), ((' tenthe',),' tenth'),
            (('testifie ','testifye '),'testify '), (('testimoniall',),'testimonial'),
        (('thankes','thakes'),'thanks'),(('thanke ',),'thank '), (('Thilke ',),'That '),((' thilke ',),' that '),
            ((' theyr ',),' their '),
                ((' hem ',),' them '),((' hem,',' the,'),' them,'),((' hem.',' the.'),' them.'), (('themselues',),'themselves'), (('Thanne ',),'Then '),((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),
                ((' ther ',),' there '), (('thidir','thyther','thither'),'there'),
                ((' therfore',' therfor'),' therefore'),(('Therfor ',),'Therefore '), (('Thei ',),'They '),((' thei ',),' they '),
            ((' thieues',' theeues',' theves',' theues'),' thieves'),((' thiefe',' theefe',' theef',' thefe'),' thief'), ((' thyne ',' thine '),' thine/your '), ((' thinges',' thingis',' thynges'),' things'),((' thinge',' thyng'),' thing'), ((' thenkynge',),' thinking'), ((' thynke',' thenken'),' think'),
                ((' thridde',' thyrde',' thirde'),' third'), ((' thristen',),' thirsting'),((' thyrst ',' thurst ',' thirste '),' thirst '),((' thirste,',),' thirst,'),
            (('thwong',),'thong'), ((' thou ',),' thou/you '), ((' thouy ',),' though '), (('thousynde','thousande'),'thousand'),
            ((' thre ',),' three '), ((' trone ',),' throne '), (('thorowout',),'throughout'), (('thorow ','thorou '),'through '),(('thorow,',),'through,'), (('throwen',),'thrown'),
            (('thundryng',),'thundering'), (('thounder','thonder'),'thunder'),
        ((' tydynges',' tidynges',' tydinges',' tydings'),' tidings/news'),(('Tydinges',),'Tidings'), ((' tyed ',),' tied '), ((' tyll ',),' till '), ((' tyme',),' time'),
        (('togidir','togidere','togidre','togedder'),'together'), ((' tokene ',),' token '), ((' tokun ',' toke ',' tooke '),' took '), ((' townes',' tounes'),' towns'),((' towne ',' toune '),' town '),
        (('ttasfigured',),'transfigured'), ((' trauelid',),' travelled'),
            (('treasurie','tresorie'),'treasury'), ((' tre,',),' tree,'),
            (('tribulacioun',),'tribulation'), ((' tryed',),' tried'),
            (('Treuli','Sotheli'),'Truly'),(('truely','treuli','sotheli'),'truly'), (('sothfast',),'truthful'), ((' trueth',' treuthe',' verite'),' truth'),
        ((' turneden',' turnede'),' turned'),(('Turne ',),'Turn '),((' tourne ',' turne '),' turn '),
        (('twolue','twelue'),'twelve'), ((' twyse',' twise'),' twice'), ((' twei ',' tweyne ',' tweyn ',' twey ', ' twaine '),' two '),
    (('vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'),
        (('vncerteyn',),'uncertain'), (('vncleane','vnclene'),'unclean'), (('vncovered','vncouered'),'uncovered'),
            ((' vnderstande',' vnderstand'),' understand'),(('Vnderstonde',),'Understood'),(('vnderstonde','vnderstoode','vnderstode'),'understood'), ((' vnder',),' under'),
            (('vnleauened','vnleuened'),'unleavened'), ((' vnloose',),' unloose'),
            ((' vnsauerie',' unsauery',' unsavery'),' unsavoury'),
            ((' vntieden',),' untied'), (('Untyll ','Vntill '),'Until '),(('vntill','vntyll'),'until'), (('Vnto ',),'Unto '),((' vnto',),' unto'), ((' vntiynge',),' untying'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'), ((' vpon ',' apon '),' upon '),(('Vpon ',),'Upon '),
        ((' vs',),' us'),
            ((' vn',),' un'), # Special case for all remaining un- words
            ((' vp',),' up'), # Special case for all remaining up- words
    (('vanyte ','vanitie '),'vanity '),
        (('Ueryly','Verely','Veryly'),'Verily/Truly'),((' verely',' veryly'),' verily/truly'), ((' vessell',),' vessel'),
        (('vyneyarde','vynyarde','vynyerd','vineyarde'),'vineyard'), ((' vertu',),' virtue'),
        ((' voyce',' vois'),' voice'),
    (('walkynge','walkinge'),'walking'),((' walkid',),' walked'),((' walke ',),' walk '),((' walke,',),' walk,'),
             ((' warres',),' wars'),((' warre ',),' war '),
             ((' waisschide',' wasshed',' wesshed'),' washed'),((' waisschun',),' washing'),((' wesshe ',' washe '),' wash '),((' wassche;',),' wash;'),
             ((' watred',),' watered'),((' watris',),' waters'),((' watir',' watre'),' water'),
                ((' wayes',' weies'),' ways'),((' waye ',' weie ',' weye '),' way '),((' waye,',' weie,',' weye,'),' way,'),((' waye.',' weie.',' weye.'),' way.'),((' waye:',' weie:',' weye:'),' way:'),
        ((' wee ',),' we '),
            ((' weryed',' weried'),' wearied'),((' weery',' wery'),' weary'),
            ((' wepe ',),' weep '),
            ((' welde ',),' weld '), ((' wel ',),' well '),
            ((' wenten ',' wente ',' wete ',' yeden ',' yede '),' went '),
            ((' wepte',),' wept'),
            ((' weren ',),' were '), (('westwarde',),'westward'),
        (('Whatsoeuer',),'Whatsoever'),(('whatsoeuer',),'whatsoever'),
            (('Whanne ',),'When '),((' whanne ',' whan '),' when '), ((' whethir',),' whether'),
            (('Whiche ',),'Which '),((' whiche ',),' which '), ((' whill ',' whyll ',' whyle '),' while '),
            ((' whoale',),' whole'), ((' whome',),' whom'), (('Whosoeuer',),'Whosoever'),(('whosoeuer',),'whosoever'),
            ((' whi ',),' why '),
        ((' wickid',),' wicked'),
            ((' wyde ',),' wide '), (('widewis','wyddowes','widowes'),'widows'),(('widewe ','wyddowe ','widdowe ','widowe '),'widow '), (('wyldernesse','wildirnesse','wyldernes','wildernesse'),'wilderness'), (('wildernes ',),'wilderness '),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf'),' wife'),
            ((' wilde ',' wylde '),' wild '), ((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wyll,',' wil,',' wole,'),' will,'),((' wylt ',' wilt '),' wilt/will '),
            ((' wyndis',' wyndes',' windes'),' winds'),((' wynde ',' wynd ',' winde '),' wind '), ((' wengis',' wynges'),' wings'), (('Wynter',),'Winter'),((' wyntir.',' wynter.'),' winter.'),
            ((' wipte',' wyped'),' wiped'),
            (('wyssdome','wysedome','wysdome','wisedome'),'wisdom'), ((' wyse ',),' wise '),
            ((' withynne',),' within'),((' wi ',' wt '),' with '), (('widdred','wythred','wythered','wyddred'),'withered'),
                (('withouten ',),'without '), (('witnessyng',),'witnessing'),((' wytnesse ',' witnesse ',' witnes '),' witness '),
            ((' wyues',),' wives'),
        (('Woo ','Wo '),'Woe '),((' wo ',),' woe '),
            ((' womman',),' woman'), ((' wombe',),' womb'), ((' wymmen',' wemen'),' women'),
            (('wondriden','wondride'),'wondered'),
            ((' worde',),' word'), ((' workes',' werkis'),' works'),((' worche ',' worke ',' werke ',' werk '),' work '),((' worke,',' werk,'),' work,'),((' worche.',),' work.'), ((' worlde',),' world'), ((' worme ',),' worm '), (('worschipide','worshypped'),'worshipped'), ((' worthie',' worthi'),' worthy'),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),
        ((' writyng',),' writing'),((' wryte ',),' write '), ((' wrytten',' writun'),' written'), ((' wroote ',' wroot '),' wrote '), (('wrought','wrouyt'),'wrought/done'),
    (('Iacob',),'Yacob'), (('Iames','James'),'Yames/Yacob'),
        (('Ye ',),'Ye/You_all '),((' ye ',' yee '),' ye/you_all '), ((' thi ',' thy '),' thy/your '), ((' youre ',),' your(pl) '),
            ((' yhe,',),' yea/yes,'), ((' yeres',),' years'),((' yeer',' yeare'),' year'),
            (('Hierusalem','Ierusalem','Ierusale','Jerusalem'),'Yerusalem'),
            (('Iesus',),'Yesus/Yeshua'),(('Iesu ',),'Yesu '),
            ((' yit ',),' yet '),
            (('Iewry ',),'Yewry '), (('Iewes ','Jewis '),'Yews '),
        (('Iohn','Ihon','Joon'),'Yohn'),
            (('Iordane ','Iordan ','Iorden ','Iorda ','Jordan '),'Yordan '),(('Iordane,','Iordan,','Iorden,','Iorda,','Jordan,'),'Yordan,'),
            (('Ioses','Joses'),'Yoses'),
        (('Iudas','Ivdas','Judas'),'Yudas'), (('Iuda','Juda'),'Yudah'), (('Iudea','Judee'',Judaea'),'Yudea'), (('Iude',),'Yude'), (('Iury','Iurie'),'Yury/Yudea'), (('Iewry',),'Yewry'),
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
    assert isinstance( someOldWords, tuple ), f"{someOldWords=}"
    assert isinstance( newWord, str )
    for j,someOldWord in enumerate( someOldWords ):
        assert isinstance( someOldWord, str ) and len(someOldWord)>=2, f"{someOldWord=}"
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if j > 0: assert someOldWord not in newWord, f"Recursive substitution of '{someOldWord}' into '{newWord}'"
        assert '  ' not in someOldWord
        oldWords.append( someOldWord)
    if newWord not in ('themselves',): # sometimes two->one and sometimes it's a single word
        assert newWord not in newWords, f"{newWord=}"
    if someOldWords[0].startswith(' '): assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    if newWord[-1] in ' ,.:;':
        for someOldWord in someOldWords:
            assert someOldWord[-1] == newWord[-1], f"Mismatched trailing character: {someOldWords} {newWord=}"
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
# end of createSynopticPassagePages.moderniseEnglishWords


GERMAN_WORD_MAP = (
    ('Aber ','But '),
        (' Arche ',' ark '),
        (' alle ',' all '),
        (' auch.',' also.'), (' aus ',' out of '), (' auf ',' on '),(' aufs ',' onto '),
    ('Älteste','elder'),
    ('Befehl','command'), ('Blut','blood'),
    (' das ',' the '),('Der ','The '),(' der ',' the '),(' dem ',' the '),(' den ',' the '),(' des ',' the '),(' die ',' the '),
        (' drei',' three'),
        ('Du ','You '),
    ('Erde','earth'),
        (' ein ',' a '),(' eine ',' one '),(' einen ',' a '),
    ('Gajus','Gaius'),
        ('Geist','spirit'),
        ('Glauben','faith'),
        ('Gottes ','God’s '), (' große ',' great '),(' großen',' great'),
    ('Hauses','houses'), ('Himmel','heaven'),
    (' ich ',' I '),(' ihm ',' him '),(' ihm.',' him.'), (' ihn ',' him '),
    ('JEsus','Yesus'), ('J','Y'),
        ('Jüngern ','disciples '),
    (' kamen ',' came '),(' kam ',' came '),
        (' kommen ',' coming '),
    ('Lieben ','loved (one) '), (' liebhabe ',' love '), (' ließ ',' let '),
    (' machten',' make'), ('Meer ','sea '),('Meer.','sea.'), (' mit ',' with '), ('. Morgan','. Morning'),('Morgan','morning'),
    ('Nacht ','night '), (' nicht ',' not '),
    ('Samen ','seed '),
        ('Schiff','ship'),
        (' sein ',' his '),(' seine ',' his '),
        (' sieben ',' seven '), (' sind ',' are '),
        ('Sohn!','son!'), ('Sonne','sun'),
        (' sprach ',' spoke '),
    ('Und ','And '),(' und ',' and '), ('Ungewitter','storm'),
    ('Vaterland','fatherland/homeland'),
        (' viel ',' many '), ('Volks','people'), (' von ',' from '),
    ('Wahrheit','truth'), ('Wasser','water'),
        ('Weib ','woman '), ('Welt','world'), (' wenn ',' when '),
        ('Wind ','wind '),
    (' zu ',' to '), ('Zuletzt ','Finally '),
    )
def translateGerman( html:str ) -> bool:
    """
    Convert ancient spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"translateGerman( ({len(html)}) )" )

    for GermanWord,EnglishWord in GERMAN_WORD_MAP:
        html = html.replace( GermanWord, EnglishWord )

    return html
# end of createSynopticPassagePages.translateGerman


def adjustLatin( html:str ) -> bool:
    """
    Convert ancient Latin spellings to modern ones.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"adjustLatin( ({len(html)}) )" )

    return html.replace('j','y').replace('J','Y') \
                .replace('Yhes','Jhes') # Change this one back again -- 'Jhesus' -- was maybe more like French J ???
# end of createSynopticPassagePages.adjustLatin



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createSynopticPassagePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createSynopticPassagePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createSynopticPassagePages.py
