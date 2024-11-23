#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createTopicPages.py
#
# Module handling OpenBibleData createTopicPages functions
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
Module handling createTopicPages functions.

CHANGELOG:
    2024-11-01 First attempt
    2024-11-09 Added some headings
"""
from gettext import gettext as _
from typing import Tuple, List
from pathlib import Path
import os
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.ESFMBible as ESFMBible
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, getLeadingInt

from settings import State, TEST_MODE, reorderBooksForOETVersions, OET_UNFINISHED_WARNING_HTML_PARAGRAPH, JAMES_NOTE_HTML_PARAGRAPH
from usfm import convertUSFMMarkerListToHtml
from Bibles import getVerseDataListForReference
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    do_LSV_HTMLcustomisations, do_T4T_HTMLcustomisations, \
                    removeDuplicateCVids, \
                    makeTop, makeBottom, makeBookNavListParagraph, checkHtml
from OETHandlers import livenOETWordLinks, getOETTidyBBB, getOETBookName, getBBBFromOETBookName


LAST_MODIFIED_DATE = '2024-11-14' # by RJH
SHORT_PROGRAM_NAME = "createTopicPages"
PROGRAM_NAME = "OpenBibleData createTopicPages functions"
PROGRAM_VERSION = '0.20'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


TOPIC_TABLE = {
    'Advent week one': ['JER_33:14-16', 'PSA_25:1-9', 'TH1_3:9-13', 'LUK_21:25-36'],
    'Advent week two': ['MAL_3:1-4', 'LUK_1:67-79', 'PHP_1:3-11', 'LUK_3:1-6', 'PSA_80'],
    'Advent week three': ['ZEP_3:14-20', 'ISA_12:2-6', 'PHP_4:4-7', 'LUK_3:7-18'],
    'Advent week four': ['MIC_5:2-5a', 'LUK_1:39-56', 'HEB_10:5-10', 'REV_22:6-21'],
    'Advent Christmas': ['ISA_9:2-7', 'PSA_96', 'TIT_2:11-14', 'LUK_2:1-20'],
    'Advent revelation (epiphany)': ['ISA_60:1-6', 'PSA_72', 'EPH_3:1-12', 'MAT_2:1-12'],
    'Advent (all)': ['JER_33:14-16', 'PSA_25:1-9', 'TH1_3:9-13', 'LUK_21:25-36',
                        'MAL_3:1-4', 'LUK_1:67-79', 'PHP_1:3-11', 'LUK_3:1-6', 'PSA_80',
                        'ZEP_3:14-20', 'ISA_12:2-6', 'PHP_4:4-7', 'LUK_3:7-18',
                        'MIC_5:2-5a', 'LUK_1:39-56', 'HEB_10:5-10', 'REV_22:6-21',
                        'ISA_9:2-7', 'PSA_96', 'TIT_2:11-14', 'LUK_2:1-20',
                        'ISA_60:1-6', 'PSA_72', 'EPH_3:1-12', 'MAT_2:1-12'],
    'Basic salvation': ['ROM_6:22-23', 'ROM_3:22-23', 'JHN_3:14-16', 'REV_3:19-21'],
    'Predestination and ‘once saved, always saved’': ['PSA_136:1-2','PSA_138:7-8',
                                'MAT_7:21-23', 'MAT_10:21-22', 'MAT_25:40-41',
                                'MRK_4:16-17',
                                'JHN_6:35-37', 'JHN_6:44-45', 'JHN_10:28-29','JHN_14:16-17',
                                'ROM_5:9-10', 'ROM_8:5-8', 'ROM_8:38-39', 'ROM_11:17-22',
                                'CO1_2:14-15', 'CO1_9:26-27',
                                'GAL_5:3-4',
                                'EPH_1:4-9', 'EPH_1:13-14','EPH_4:29-30',
                                'TI1_2:1-8', 'TI1_4:1-2',
                                'TI2_2:10',
                                'TIT_2:9-12',
                                'HEB_3:11-12','HEB_6:1-8','HEB_9:11-12','HEB_10:26-31',
                                'PE2_2:20-22','PE2_3:1-18',
                                'JN1_1:6-7','JN1_5:11-13',
                                'JAM_5:19-20',
                                'REV_3:4-5'],
    'Yeshua/Jesus not God (Christadelphian)': ['H3 Claim: <span style="background-color:khaki;">Jesus died</span>', 'CO1_15:3-4', 'H3 Claim: <span style="background-color:lightBlue;">God cannot die</span>', 'TI1_1:17',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was tempted </span>', 'HEB_4:14-15', 'H3 Claim: <span style="background-color:lightBlue;">God cannot be tempted</span>', 'JAM_1:13',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was seen</span>', 'JHN_1:29', 'H3 Claim: <span style="background-color:lightBlue;">No man has ever seen God</span>', 'JN1_4:12',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was and is a man</span>', 'TI1_2:5', 'H3 Claim: <span style="background-color:lightBlue;">God is not a man</span>', 'NUM_23:18-19',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus had to grow and learn</span>', 'HEB_5:8-9', 'H3 Claim: <span style="background-color:lightBlue;">God doesn’t ever need to learn</span>', 'ISA_40:28',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus needs salvation</span>', 'HEB_5:7', 'H3 Claim: <span style="background-color:lightBlue;">God does not</span>', 'HEB_5:7',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus grew weary</span>', 'JHN_4:5-6', 'H3 Claim: <span style="background-color:lightBlue;">God can’t grow weary</span>', 'ISA_40:28',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus slept</span>', 'MAT_8:23-24', 'H3 Claim: <span style="background-color:lightBlue;">God doesn’t slumber</span>', 'PSA_121:2-4',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus wasn’t all powerful</span>', 'JHN_5:18-19', 'H3 Claim: <span style="background-color:lightBlue;">God is all powerful (omnipotent)</span>', 'ISA_45:5-7',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus wasn’t all knowing</span>', 'MRK_13:31-32', 'H3 Claim: <span style="background-color:lightBlue;">God is all knowing (omniscient)</span>', 'ISA_46:9-10',
                                        'H3 Only God can do that', 'MRK_2:1-12', 'MAT_9:1-9', 'LUK_5:17-26',
                                        ]
    }
for topic,refs in TOPIC_TABLE.items():
    assert isinstance( topic, str )
    assert isinstance( refs, list )
    for ref in refs:
        assert isinstance( ref, str )
        if not ref.startswith( 'H3 ' ):
            # Assume it's a reference -- either a verse or a verse or chapter range
            assert ' ' not in ref
            BBB, refRest = ref.split( '_' ) # This split will fail if it's not a valid scripture reference
            try:
                C, Vs = refRest.split( ':' )
                assert C.isdigit()
            except ValueError:
                assert refRest.isdigit()

def createTopicPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"\ncreateTopicPages( {level}, {folder}, {state.BibleVersions} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # topics = []
    topicsHtmlsForIndex = []
    for topic,refs in TOPIC_TABLE.items():
        topicWords = [x.title() for x in topic.replace(', ',' ').replace('/','⁄').split()]
        topicFilename = BibleOrgSysGlobals.makeSafeFilename( f'''{''.join(topicWords)}.htm''' )
        createTopicPage( level, folder, topicFilename, topic, refs, state )
        # topics.append( (topic,topicFilename) )
        topicsHtmlsForIndex.append( f'''<a href="{topicFilename}">{topic}</a>''' )

    # Create topic index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'topicsIndex', None, state ) \
            .replace( '__TITLE__', f"Topic View{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, topic, topics, topical' )
    indexHtml = f'''{top}<h1 id="Top">Topic pages</h1>
<p>These pages contain selected passages from the <em>Open English Translation</em> for the given topics. Each page contains the passage from the <em>OET Readers’ Version</em> on the left, with the <em>OET Literal Version</em> on the right. No notes or commentary is included—our aim is simply to conveniently list the passages in one place so that readers can make up their own minds about how the passages should be interpreted.</p>
<h2>Index of topics</h2>
<p>\n{'<br>'.join(topicsHtmlsForIndex)}</p>
<p class="note">Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any topics that you’d like us to add, or any passages that you’d like us to add to any topic page.</p>
{makeBottom( level, 'topicsIndex', state )}'''
    checkHtml( 'topicsIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createTopicPages() finished processing {len(state.allBBBs)} books: {state.allBBBs}" )
    return True
# end of createTopicPages.createTopicPages


def createTopicPage( level:int, folder:Path, filename:str, topic:str, refs:List[str], state:State ) -> bool:
    """
    Create a page for each Bible topic.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPage( {level}, {folder}, '{filename}', '{topic}', {len(refs)}, {state.BibleVersions} )" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createTopicPage for '{topic}' ({filename}) with {len(refs)} Bible passages…" )
    rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']

    combinedHtmlChunks = []
    for rr,ref in enumerate( refs, start=1 ):
        # print( f"  {rr} {topic} {ref=}")
        if ref.startswith( 'H3 '): # Then it's a heading -- we'll remove this part of the string
            combinedHtmlChunks.append( f'''<h3>{ref[3:]}</h3>
<h3></h3>''' ) # Second one is to keep the number of columns matched
        else: # We'll assume it's a scripture reference
            BBB, refRest = ref.split( '_' ) # This split will fail if it's not a valid scripture reference
            try: C, Vs = refRest.split( ':' )
            except ValueError:
                assert refRest.isdigit()
                C, Vs = refRest, None
            # print( f"    {rr} {topic} {ref=} {BBB=} {refRest=} {C=} {Vs=}")
            if Vs is None: # then it's an entire chapter (no verses specified)
                rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C) )
                try: lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB,C) )
                except TypeError: # Book appears to be not available
                    assert TEST_MODE
                    lvVerseEntryList, lvContextList = InternalBibleEntryList(), []
            elif '-' in Vs: # then it's a verse range
                startV, endV = Vs.split( '-' )
                rvVerseEntryList, rvContextList = rvBible.getContextVerseDataRange( (BBB,C,startV), (BBB,C,endV) )
                try: lvVerseEntryList, lvContextList = lvBible.getContextVerseDataRange( (BBB,C,startV), (BBB,C,endV) )
                except TypeError: # Book appears to be not available
                    assert TEST_MODE
                    lvVerseEntryList, lvContextList = InternalBibleEntryList(), []
            elif '–' in Vs: # en-dash, then it's a chapter range
                not_written_yet
            else: # assume it's a single verse
                assert Vs and Vs.isdigit()
                rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C,Vs) )
                try: lvVerseEntryList, lvContextList = lvBible.getContextVerseData( (BBB,C,Vs) )
                except TypeError: # Book appears to be not available
                    assert TEST_MODE
                    lvVerseEntryList, lvContextList = InternalBibleEntryList(), []
            # print( f"{rvVerseEntryList=}" )
            # print( f"{lvVerseEntryList=}" )
            rvVerseEntryList = livenOETWordLinks( level, rvBible, BBB, rvVerseEntryList, state )
            try: lvVerseEntryList = livenOETWordLinks( level, lvBible, BBB, lvVerseEntryList, state )
            except KeyError: # Missing book
                assert TEST_MODE
            rvTextHtml = convertUSFMMarkerListToHtml( level, rvBible.abbreviation, (BBB,C), 'topicalPassage', rvContextList, rvVerseEntryList, basicOnly=False, state=state )
            # rvTextHtml = livenIORs( BBB, rvTextHtml, sections )
            rvTextHtml = do_OET_RV_HTMLcustomisations( rvTextHtml )

            if lvVerseEntryList:
                lvTextHtml = convertUSFMMarkerListToHtml( level, lvBible.abbreviation, (BBB,C), 'topicalPassage', lvContextList, lvVerseEntryList, basicOnly=False, state=state )
                # lvTextHtml = livenIORs( BBB, lvTextHtml, sections )
                lvTextHtml = do_OET_LV_HTMLcustomisations( lvTextHtml )
            else: # We didn't get any LV data
                assert TEST_MODE
                lvTextHtml = f'<h4>No OET-LV {BBB} book available</h4>'

            if rvTextHtml.startswith( '<div class="rightBox">' ):
                rvTextHtml = f'<div class="s1">{rvTextHtml}' # This got removed above
            # Handle footnotes and cross-references so the same fn1 doesn't occur for both chunks if they both have footnotes
            rvTextHtml = rvTextHtml.replace( 'id="fn', f'id="fn{rr}RV' ).replace( 'href="#fn', f'href="#fn{rr}RV' ) \
                                .replace( 'id="xr', f'id="xr{rr}RV' ).replace( 'href="#xr', f'href="#xr{rr}RV' )
            lvTextHtml = lvTextHtml.replace( 'id="fn', f'id="fn{rr}LV' ).replace( 'href="#fn', f'href="#fn{rr}LV' ) \
                                .replace( 'id="xr', f'id="xr{rr}LV' ).replace( 'href="#xr', f'href="#xr{rr}LV' )
            combinedHtmlChunks.append( f'''<h3>OET <a title="View in context of whole book" href="{'../'*level}OET/byDoc/{BBB}.htm#C{C}V{startV}">{getOETTidyBBB(BBB,True,True,True)}</a> <a title="View in context of whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#V{startV}">{refRest}</a></h3>
<h3></h3>
<div class="chunkRV">{rvTextHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvTextHtml}</div><!--chunkLV-->''' )

    combinedHtml = f'''<div class="RVLVcontainer">
<h2>Readers’ Version</h2>
<h2>Literal Version <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>
{NEWLINE.join(combinedHtmlChunks)}</div><!--RVLVcontainer-->'''

    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'topicPassages', None, state ) \
            .replace( '__TITLE__', f"{topic}{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, topic, {topic.replace(' ',', ')}' ) 
            # .replace( f'''<a title="{state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/rel/{sFilename}#Top">{thisRvBible.abbreviation}</a>''',
            #         f'''<a title="Up to {state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/">↑{thisRvBible.abbreviation}</a>''' )
    topicHtml = f'''{top}<!--topic page-->
<p>&lt;<a href="index.htm">Up to topic index page</a>&gt;</p>
<h1>{topic}</h1>
<p>This page contains selected passages from the <em>Open English Translation</em> with the passage from the <em>OET Readers’ Version</em> on the left, and the <em>OET Literal Version</em> on the right. Minimal commentary is included (only some headings)—our aim is simply to conveniently list the passages in one place so that our readers can make up their own minds about what the writer of the passage was intending to communicate.</p>
{removeDuplicateCVids(combinedHtml)}
<p class="note">Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any passages that you’d like us to add to this topic page, or any passages that need a little bit more context around them. (We encourage our readers to always view things in their context, so we discourage use of the word ‘verse’.)</p>
<p>&lt;<a href="index.htm">Go to topic index page</a>&gt;</p>
{makeBottom( level, 'topicPassages', state )}'''
    checkHtml( f'{topic} Topic', topicHtml )
    assert '.htm#aC' not in topicHtml and '.htm#bC' not in topicHtml, topicHtml
    assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as topicHtmlFile:
        topicHtmlFile.write( topicHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(topicHtml):,} characters written to {filepath}" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createTopicPage() finished processing '{topic}' with {len(refs):,} references." )
    return True
# end of createTopicPages.createTopicPage


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createTopicPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createTopicPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createTopicPages.py
