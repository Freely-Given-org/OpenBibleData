#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# html.py
#
# Module handling OpenBibleData createParallelPassagePages functions
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
Module handling createParallelPassagePages functions.

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
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt

from usfm import convertUSFMMarkerListToHtml
from Bibles import tidyBBB
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    removeDuplicateCVids, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from OETHandlers import livenOETWordLinks


LAST_MODIFIED_DATE = '2024-01-15' # by RJH
SHORT_PROGRAM_NAME = "createParallelPassagePages"
PROGRAM_NAME = "OpenBibleData createParallelPassagePages functions"
PROGRAM_VERSION = '0.04'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


PARALLEL_FILE_LOCATION = Path( '../ParallelPassages.tsv' )
ONLY_MAKE_PAGES_WHICH_HAVE_PARALLELS = True


PARALLEL_VERSE_TABLE = {}
def createParallelPassagePages( level:int, folder:Path, state ) -> bool:
    """
    """
    from createSitePages import TEST_MODE, reorderBooksForOETVersions
    fnPrint( DEBUGGING_THIS_MODULE, f"createParallelPassagePages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    if not loadSynopticVerseTable():
        return False

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateParallelPassagePages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # Prepare the book links
    BBBNextLinks = []
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BBB in PARALLEL_VERSE_TABLE:
            ourTidyBBB = tidyBBB( BBB )
            # BBBLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{BBB}/">{ourTidyBBB}</a>''' )
            BBBNextLinks.append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''' )

    # Now create the actual synoptic pages
    rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']
    for BBB in reorderBooksForOETVersions( state.allBBBs ):
        if BBB in PARALLEL_VERSE_TABLE:
            # BBBFolder = folder.joinpath(f'{BBB}/')
            createSynopticSectionPassagePagesForBook( level, folder, rvBible, BBB, BBBNextLinks, state )
            # createSynopticChapterPassagePagesForBook( level, folder, lvBible, BBB, BBBNextLinks, state ) # No section headings in OET-LV

    # Create index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'parallelSectionIndex', None, state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Synoptic View" ) \
            .replace( '__KEYWORDS__', 'Bible, synoptic' )
    indexHtml = f'''{top}<h1 id="Top">Synoptic verse pages</h1>
<h2>Index of books</h2>
{makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'OET-RV', state)}
{makeBottom( level, 'parallelPassage', state )}'''
    checkHtml( 'parallelSectionIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createParallelPassagePages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createParallelPassagePages.createParallelPassagePages


def loadSynopticVerseTable() -> bool:
    """
    """
    global PARALLEL_VERSE_TABLE
    fnPrint( DEBUGGING_THIS_MODULE, f"loadSynopticVerseTable()" )

    # Load the file of links
    pastPassageRef = None
    numLinks = 0
    with open ( PARALLEL_FILE_LOCATION, 'rt', encoding='utf-8' ) as tsv_file:
        for j,line in enumerate( tsv_file ):
            line = line.rstrip( '\n' )
            print( f"{j}: {line}" )
            if not line or line.startswith( '#' ): continue
            if j == 0:
                assert line == 'PassageRef\tVerseRef\tRef1\tRef2\tRef3'
            else:
                bits = line.split( '\t' )
                assert 3 <= len(bits) <= 5
                passageRef, verseRef, ref1, = bits[0:3]
                ref2 = bits[3] if len(bits)>3 else None
                ref3 = bits[4] if len(bits)>4 else None
                if passageRef:
                    assert passageRef.strip() == passageRef
                    passageRef1, passageRef2 = passageRef.split( '-' )
                    BBB, CV = passageRef1.split( '_' )
                    assert len(BBB) == 3
                    C, V = CV.split( ':' )
                    assert C.isdigit() and V.isdigit()
                    lastPassageRef = (BBB,C,V)
                    if BBB not in PARALLEL_VERSE_TABLE:
                        PARALLEL_VERSE_TABLE[BBB] = {}
                else: assert lastPassageRef

                assert verseRef and verseRef.strip() == verseRef
                verseBBB, verseCV = verseRef.split( '_' )
                assert '-' not in verseCV # Must be individual verses from inside the passage
                assert verseBBB == lastPassageRef[0]
                verseC, verseV = verseCV.split( ':' )
                ourVerseRef = (verseC,verseV)
                assert ourVerseRef not in PARALLEL_VERSE_TABLE[verseBBB]

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
                PARALLEL_VERSE_TABLE[verseBBB][ourVerseRef] = refs
                numLinks += 1
    # print( f"({len(PARALLEL_VERSE_TABLE)}) {PARALLEL_VERSE_TABLE=}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  loadSynopticVerseTable() loaded {numLinks:,} links for {len(PARALLEL_VERSE_TABLE)} books." )
    return True
# end of createParallelPassagePages.loadSynopticVerseTable


class MissingBookError( Exception ): pass
class UntranslatedVerseError( Exception ): pass

def createSynopticSectionPassagePagesForBook( level:int, folder:Path, thisBible, BBB:str, BBBLinks:List[str], state ) -> bool:
    """
    Create a page for every Bible passage that has related verses in other synoptic gospels.
    """
    from createSitePages import TEST_MODE
    fnPrint( DEBUGGING_THIS_MODULE, f"createSynopticSectionPassagePagesForBook( {level}, {folder}, {thisBible.abbreviation}, {BBB}, {BBBLinks}, {state.BibleVersions} )" )
    BBBFolder = folder.joinpath(f'{BBB}/')
    BBBLevel = level + 1


    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSynopticSectionPassagePagesForBook {BBBLevel}, {BBBFolder}, {BBB} from {len(BBBLinks)} books, {len(state.BibleVersions)} versions…" )
    try: os.makedirs( BBBFolder )
    except FileExistsError: pass # they were already there

    # We don't want the book link for this book to be a recursive link, so remove <a> marking
    ourTidyBBB = tidyBBB( BBB )
    ourTidyBbb = tidyBBB( BBB, titleCase=True )
    adjBBBLinksHtml = makeBookNavListParagraph(state.BBBLinks['OET-RV'], 'OET-RV', state) \
            .replace( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="../{BBB}/">{ourTidyBBB}</a>''', ourTidyBBB )
    numBBBSections = len(thisBible[BBB]._SectionIndex)
    navBookListParagraph = makeBookNavListParagraph(state.BBBLinks[thisBible.abbreviation], thisBible.abbreviation, state)

    numChapters = None
    referenceBible = state.preloadedBibles['OET-LV']
    numChapters = referenceBible.getNumChapters( BBB ) # Causes the book to be loaded if not already
    introLinks = [ '<a title="Go to synoptic intro page" href="Intro.htm#Top">Intro</a>' ]
    # cLinksPar = f'''<p class="chLst">{EM_SPACE.join( introLinks + [f'<a title="Go to synoptic verse page" href="C{ps}V1.htm#Top">Ps{ps}</a>' for ps in range(1,numChapters+1)] )}</p>''' \
    #     if BBB=='PSA' else \
    #         f'''<p class="chLst">{ourTidyBbb if ourTidyBbb!='Jac' else 'Jacob/(James)'} {' '.join( introLinks + [f'<a title="Go to synoptic verse page" href="C{chp}V1.htm#Top">C{chp}</a>' for chp in range(1,numChapters+1)] )}</p>'''

    # Now, make the actual pages
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Creating synoptic section pages for {thisBible.abbreviation} {BBB}…" )
    usedParallels = []
    for n,startC,startV,endC,endV,sectionName,reasonName,contextList,verseEntryList,filename in state.sectionsLists[thisBible.abbreviation][BBB]:
        if endC == '?': # Then these are the OET-RV additional/alternative headings
            assert thisBible.abbreviation == 'OET-RV'
            assert endV == '?'
            continue
        documentLink = f'<a title="Whole document view" href="../byDoc/{BBB}.htm#Top">{ourTidyBBB}</a>'
        startChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if startC=='-1' else f'C{startC}'}.htm#Top">{'Intro' if startC=='-1' else startC}</a>'''
        endChapterLink = f'''<a title="Chapter view" href="../byC/{BBB}_{'Intro' if endC=='-1' else f'C{endC}'}.htm#Top">{'Intro' if endC=='-1' else endC}</a>'''
        leftLink = f'<a title="Previous section" href="{BBB}_S{n-1}.htm#Top">←</a> ' if n>0 else ''
        rightLink = f' <a title="Next section" href="{BBB}_S{n+1}.htm#Top">→</a>' if n<numBBBSections-1 else ''
        parallelLink = f''' <a title="Parallel verse view" href="{'../'*level}par/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">║</a>'''
        interlinearLink = f''' <a title="Interlinear verse view" href="{'../'*level}ilr/{BBB}/C{'1' if startC=='-1' else startC}V{startV}.htm#Top">═</a>''' if BBB in state.booksToLoad['OET'] else ''
        detailsLink = f''' <a title="Show details about this work" href="{'../'*(level-1)}details.htm#Top">©</a>'''

        synopticSectionHtml = f'''<h1><span title="{state.BibleNames[thisBible.abbreviation]}">{thisBible.abbreviation}</span> by synoptic section {ourTidyBBB} {'Intro' if startC=='-1' else startC}:{startV}</h1>
<p class="secNav">{leftLink}{documentLink} {startChapterLink}:{startV}–{endChapterLink}:{endV}{rightLink}{parallelLink}{interlinearLink}{detailsLink}</p>
{'<p class="rem">This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.</p>' if 'OET' in thisBible.abbreviation else ''}
<h1>{sectionName}</h1>
'''
        if isinstance( thisBible, ESFMBible.ESFMBible ): # e.g., OET-RV
            verseEntryList = livenOETWordLinks( thisBible, BBB, verseEntryList, f"{'../'*level}ref/GrkWrd/{{n}}.htm#Top", state )
        textHtml = convertUSFMMarkerListToHtml( level, thisBible.abbreviation, (BBB,startC), 'parallelPassage', contextList, verseEntryList, basicOnly=False, state=state )
        # textHtml = livenIORs( BBB, textHtml, sections )
        if thisBible.abbreviation == 'OET-RV':
            textHtml = do_OET_RV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'OET-LV':
            textHtml = do_OET_LV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'LSV':
            textHtml = do_LSV_HTMLcustomisations( textHtml )
        elif thisBible.abbreviation == 'T4T':
            textHtml = do_T4T_HTMLcustomisations( textHtml )
        sectionHtmlList = [textHtml]
        sectionHeadingsList = [ourTidyBbb]
        sectionBBBList = [BBB]

        # Ok, we do a first pass to count how many parallel versions there are (to get our number of columns)
        intEndC, intEndV = int(endC), int(endV)
        intC, intV = int(startC), int(startV)
        synopticBBBSet = set()
        for _safetyCount in range( 100 ):
            strC, strV = str(intC), str(intV)
            try:
                refs = PARALLEL_VERSE_TABLE[BBB][(strC,strV)]
            except KeyError:
                refs = ()
            for refBBB,_refC,_refV in refs:
                print( f"{BBB} {strC}:{strV} {refBBB} {_refC}:{_refV}")
                synopticBBBSet.add( refBBB )

            intV += 1
            try: numVerses = thisBible.getNumVerses( BBB, intC )
            except KeyError:
                logging.critical( f"Can't get number of verses for {thisBible.abbreviation} {BBB} {intC}")
                halt
                continue
            if intV > numVerses:
                intC += 1
                intV = 1
            if intC>intEndC \
            or (intC==intEndC and intV>intEndV):
                break # We've passed the end of our current section
        else: # need to increase _safetyCount for long section
            print( f"Need to increase _safetyCount {_safetyCount} for {thisBible.abbreviation} {BBB} {startC}:{startV} {endC}:{endV}")
        print( f"Got BBB set for {BBB} {strC}:{strV} ({len(synopticBBBSet)}) {synopticBBBSet=}")
        if BBB == 'MAT':
            if 'MRK' in synopticBBBSet: sectionBBBList.append( 'MRK' ); sectionHeadingsList.append( 'Mark' )
            if 'LUK' in synopticBBBSet: sectionBBBList.append( 'LUK' ); sectionHeadingsList.append( 'Luke' )
            if 'JHN' in synopticBBBSet: sectionBBBList.append( 'JHN' ); sectionHeadingsList.append( 'John' )
        elif BBB == 'MRK':
            if 'MAT' in synopticBBBSet: sectionBBBList.append( 'MAT' ); sectionHeadingsList.append( 'Matt.' )
            if 'LUK' in synopticBBBSet: sectionBBBList.append( 'LUK' ); sectionHeadingsList.append( 'Luke' )
            if 'JHN' in synopticBBBSet: sectionBBBList.append( 'JHN' ); sectionHeadingsList.append( 'John' )
        elif BBB == 'LUK':
            if 'MRK' in synopticBBBSet: sectionBBBList.append( 'MRK' ); sectionHeadingsList.append( 'Mark' )
            if 'MAT' in synopticBBBSet: sectionBBBList.append( 'MAT' ); sectionHeadingsList.append( 'Matt.' )
            if 'JHN' in synopticBBBSet: sectionBBBList.append( 'JHN' ); sectionHeadingsList.append( 'John' )
        elif BBB == 'JHN':
            if 'MRK' in synopticBBBSet: sectionBBBList.append( 'MRK' ); sectionHeadingsList.append( 'Mark' )
            if 'MAT' in synopticBBBSet: sectionBBBList.append( 'MAT' ); sectionHeadingsList.append( 'Matt.' )
            if 'LUK' in synopticBBBSet: sectionBBBList.append( 'LUK' ); sectionHeadingsList.append( 'Luke' )
        else: unexpected_BBB
        assert len(sectionHeadingsList) == len(synopticBBBSet) + 1
        assert len(sectionBBBList) == len(sectionHeadingsList)
        for j in range( len(sectionHeadingsList)-1 ): sectionHtmlList.append( '' )
        assert len(sectionHtmlList) == len(sectionHeadingsList)
        if len(sectionBBBList) > 1:
            usedParallels.append( (startC,startV) )
        elif ONLY_MAKE_PAGES_WHICH_HAVE_PARALLELS:
            continue

        # Ok, now we do the second pass to actually form the parallel verses
        intEndC, intEndV = int(endC), int(endV)
        intC, intV = int(startC), int(startV)
        for _safetyCount in range( 100 ):
            strC, strV = str(intC), str(intV)
            try:
                refs = PARALLEL_VERSE_TABLE[BBB][(strC,strV)]
            except KeyError:
                refs = ()
            for refBBB,refC,refV in refs:
                print( f"{BBB} {strC}:{strV} {refBBB} {refC}:{refV}")
                assert refBBB != BBB
                verseEntryList, contextList = thisBible.getContextVerseData( (refBBB, refC) if refC=='-1' else (refBBB, refC, refV) )
                if isinstance( thisBible, ESFMBible.ESFMBible ):
                    verseEntryList = livenOETWordLinks( thisBible, refBBB, verseEntryList, f"{'../'*BBBLevel}ref/GrkWrd/{{n}}.htm#Top", state )
                refHtml = convertUSFMMarkerListToHtml( BBBLevel, thisBible.abbreviation, (refBBB,refC,refV), 'verse', contextList, verseEntryList, basicOnly=(refC!='-1'), state=state )
                print( f"{BBB} {strC}:{strV} {refBBB} {refC}:{refV} {refHtml=}")
                BBBix = sectionBBBList.index( refBBB )
                sectionHtmlList[BBBix] = f'{sectionHtmlList[BBBix]}\n<span class="parCV">{refC}:{refV}</span> {refHtml}'

            intV += 1
            try: numVerses = thisBible.getNumVerses( BBB, intC )
            except KeyError:
                logging.critical( f"Can't get number of verses for {thisBible.abbreviation} {BBB} {intC}")
                halt
                continue
            if intV > numVerses:
                intC += 1
                intV = 1
            if intC>intEndC \
            or (intC==intEndC and intV>intEndV):
                break # We've passed the end of our current section
        else: # need to increase _safetyCount for long section
            print( f"Need to increase _safetyCount {_safetyCount} for {thisBible.abbreviation} {BBB} {startC}:{startV} {endC}:{endV}")

        # Now we need to create the columns
        containerClassname = f'container{len(sectionHeadingsList)}'
        synopticSectionHtml = f'''{synopticSectionHtml}<div class="{containerClassname}">'''
        for bkNameAbbrev in sectionHeadingsList:
            synopticSectionHtml = f'''{synopticSectionHtml}<h2>{bkNameAbbrev}</h2>'''
        for htmlChunk in sectionHtmlList:
            synopticSectionHtml = f'''{synopticSectionHtml}\n<div class="chunkRV">{htmlChunk}</div><!--chunkRV-->'''
        synopticSectionHtml = f'''{synopticSectionHtml}\n</div><!--{containerClassname}-->'''

        filepath = BBBFolder.joinpath( filename )
        top = makeTop( BBBLevel, thisBible.abbreviation, 'parallelPassage', f'con/{BBB}.htm', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} section" ) \
                .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, synoptic, parallel, {ourTidyBBB}' ) \
                .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/con/{filename}#Top">{thisBible.abbreviation}</a>''',
                        f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
        synopticSectionHtml = f'''{top}<!--synoptic section page-->
{navBookListParagraph}
{removeDuplicateCVids( BBB, synopticSectionHtml )}
{makeBottom( level, 'parallelPassage', state )}'''
        checkHtml( thisBible.abbreviation, synopticSectionHtml )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
            sectionHtmlFile.write( synopticSectionHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(synopticSectionHtml):,} characters written to {filepath}" )

    # Create index page for this book
    # Now make the section index file for this book
    filename = 'index.htm'
    filepath = BBBFolder.joinpath( filename )
    top = makeTop( BBBLevel, thisBible.abbreviation, 'parallelSectionIndex', f'con/{filename}', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} sections" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, {ourTidyBBB}' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/con/{filename}#Top">{thisBible.abbreviation}</a>''',
                    f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
    synopticSectionHtml = f'<h1 id="Top">Index of parallel sections for {thisBible.abbreviation} {ourTidyBBB}</h1>\n'
    for _nnn,startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in state.sectionsLists[thisBible.abbreviation][BBB]:
        if (startC,startV) not in usedParallels: continue # Only make the index for sections that we made pages for
        reasonString = '' if reasonName=='Section heading' and not TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
        # NOTE: word 'Alternate ' is defined in the above OET function at start of main loop
        synopticSectionHtml = f'''{synopticSectionHtml}<p class="{'alternateHeading' if reasonName.startswith('Alternate ') else 'sectionHeading'}"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
        # sectionHtml = f'''{sectionHtml}<p class="sectionHeading"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
    synopticSectionHtml = f'''{top}<!--sections page-->
{navBookListParagraph}
{synopticSectionHtml}
{makeBottom( level, 'parallelSectionIndex', state )}'''
    checkHtml( thisBible.abbreviation, synopticSectionHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( synopticSectionHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(synopticSectionHtml):,} characters written to {filepath}" )

    # Write a second copy of the index page up a level
    filename2 = f'{BBB}.htm'
    filepath2 = folder.joinpath( filename2 )
    top = makeTop( level, thisBible.abbreviation, 'parallelSectionIndex', f'con/{filename}', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{thisBible.abbreviation} {ourTidyBBB} sections" ) \
            .replace( '__KEYWORDS__', f'Bible, {thisBible.abbreviation}, sections, {ourTidyBBB}' ) \
            .replace( f'''<a title="{state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/con/{filename}#Top">{thisBible.abbreviation}</a>''',
                    f'''<a title="Up to {state.BibleNames[thisBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}/">↑{thisBible.abbreviation}</a>''' )
    synopticSectionHtml = f'<h1 id="Top">Index of parallel sections for {thisBible.abbreviation} {ourTidyBBB}</h1>\n'
    for _nnn,startC,startV,_endC,_endV,sectionName,reasonName,_contextList,_verseEntryList,filename in state.sectionsLists[thisBible.abbreviation][BBB]:
        if (startC,startV) not in usedParallels: continue # Only make the index for sections that we made pages for
        reasonString = '' if reasonName=='Section heading' and not TEST_MODE else f' ({reasonName})' # Suppress '(Section Heading)' appendages in the list
        # NOTE: word 'Alternate ' is defined in the above OET function at start of main loop
        synopticSectionHtml = f'''{synopticSectionHtml}<p class="{'alternateHeading' if reasonName.startswith('Alternate ') else 'sectionHeading'}"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
        # sectionHtml = f'''{sectionHtml}<p class="sectionHeading"><a title="View section" href="{filename}#Top">{'Intro' if startC=='-1' else startC}:{startV} <b>{sectionName}</b>{reasonString}</a></p>\n'''
    synopticSectionHtml = f'''{top}<!--sections page-->
{navBookListParagraph}
{synopticSectionHtml}
{makeBottom( level, 'parallelSectionIndex', state )}'''
    checkHtml( thisBible.abbreviation, synopticSectionHtml )
    assert not filepath2.is_file() # Check that we're not overwriting anything
    with open( filepath2, 'wt', encoding='utf-8' ) as sectionHtmlFile:
        sectionHtmlFile.write( synopticSectionHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(synopticSectionHtml):,} characters written to {filepath2}" )

    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createSynopticSectionPassagePagesForBook() finished processing {len(vLinks):,} {BBB} verses." )
    return True
# end of createParallelPassagePages.createSynopticSectionPassagePagesForBook


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createParallelPassagePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createParallelPassagePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createParallelPassagePages.py
