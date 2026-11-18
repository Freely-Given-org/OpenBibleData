#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2024 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# createTopicPages.py
#
# Module handling OpenBibleData createTopicPages functions
#
# Copyright (C) 2024-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling createTopicPages functions.

CHANGELOG:
    2024-11-01 First attempt
    2024-11-09 Added some headings
    2025-02-03 Accept and process lemma page links
    2025-06-27 Fix bug where we were forcing the load of Bible books where not wanted
    2025-09-07 Add Kingdom pages
    2025-10-29 Add an index for kingdom pages
    2026-01-07 Added OET Logo
    2026-03-01 Added IMPORTANT people index
    2026-06-01 Improve unusual book codes (like Yac) and improve navigation
    2026-08-22 Import convertVerseEntryListToHtml directly from openbibledata_rust (convert.py deleted)
    2026-08-25 The OETHandlers functions are now imported from the Rust openbibledata_rust module (the Python OETHandlers.py was deleted).
    2026-09-03 Stop applying the Heb/Grk grammatical colourisation classes on topic pages because their CSS doesn't style them -- the shared dark-mode rules were painting those words unreadably.
    2026-09-15 ESFM word-link livening is now fused (single-pass) into openbibledata_rust.convertVerseEntryListToHtml via its new livenWordLinks/colouriseWordClasses keyword args, so the old livenOETWordLinks calls in the topical-passage hot paths have been removed.
    2026-10-30 Add forty passage collections covering Christian doctrine and everyday discipleship, God’s character, discernment, service and daily relationships.
                    Prefer Yahweh in topic titles and headings when selected passages use the name.
    2026-10-30 Repair kingdom scripture and people-index destinations.
    2026-10-30 Identify the topic, edition and reference when passage retrieval fails.
    2026-10-30 Link the people, places and dictionary entries tagged in selected passages.
    2026-10-31 Add approved kingdom readings and verified person/place navigation.
    2026-10-31 Connect kingdom browsing to the available dictionary indexes.
    2026-11-02 Group indented kingdom reading previews before their section links.
    2026-11-03 Correct Strong's in reference-index labels.
    2026-11-05 Describe site resources and navigation pages in their search metadata.
    2026-11-18 Moved TOPIC_TABLE into topicTable.py, expanded it to 300 topics, and grouped them under subject headings
                on the topic index page (with a contents list), with each topic page linking back to its subject.
"""
from pathlib import Path
import os

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from bible_organisational_system import InternalBibleEntryList

from oetPassages import renderOETLVPassage
from navigation import scriptureLink
from studyReferences import topicFilename,topicReferenceMaterial,ENTITY_FOLDER
from topicTable import TOPIC_GROUPS, TOPIC_TABLE, TOPIC_GROUP_OF
from referenceEntities import loadReferenceEntities,entityLink,kingdomArticleLinks,KINGDOM_ENTITIES
from referencePassages import parseReferenceSelection,renderReferencePassageGroup
from referenceIndexes import referenceIndexLinks
from settings import State
from Bibles import getBibleMapperMaps
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    removeDuplicateCVids, \
                    makeTop, makeBottom, checkHtml
from openbibledata_rust import convertVerseEntryListToHtml, getOETTidyBBB


LAST_MODIFIED_DATE = '2026-11-18' # by RJH
SHORT_PROGRAM_NAME = "createTopicPages"
PROGRAM_NAME = "OpenBibleData createTopicPages functions"
PROGRAM_VERSION = '0.42'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


# The topic data (subject groups, topics and passages) is in topicTable.py

TOPIC_LIST = []
def topicGroupId( group:str ) -> str:
    """
    Make an HTML id (for the topic index page) from a subject heading,
        e.g., 'Christmas/Advent' -> 'ChristmasAdvent'
    """
    return ''.join( char for char in group.title() if char.isascii() and char.isalnum() )
# end of createTopicPages.topicGroupId

assert len( {topicGroupId(group) for group in TOPIC_GROUPS} ) == len( TOPIC_GROUPS ) # Check our ids are unique


def topicGroupLink( topic:str ) -> str:
    """
    Return a HTML paragraph linking a topic page back to its subject heading on the topic index page
        (or an empty string if the topic isn't in a group).
    """
    try: group = TOPIC_GROUP_OF[topic]
    except KeyError: return ''
    return f'''<p class="topicGroup">Subject: <a title="See all the topics on this subject" href="index.htm#{topicGroupId(group)}">{group}</a></p>\n'''
# end of createTopicPages.topicGroupLink


def makeTopicIndexHtml() -> str:
    """
    Return the HTML for the topic index: a contents list of the subject headings,
        then each subject heading followed by the links to its topics.
    """
    contentsHtml = ' · '.join( f'<a href="#{topicGroupId(group)}">{group}</a>' for group in TOPIC_GROUPS )
    groupHtmls = []
    for group,topics in TOPIC_GROUPS.items():
        topicLinks = '<br>'.join( f'<a href="{topicFilename(topic)}#Top">{topic}</a>' for topic in topics )
        groupHtmls.append( f'''<h2 id="{topicGroupId(group)}">{group}</h2>
<p>{topicLinks}</p>
<p class="pageNav"><small><a title="Back to the list of subjects" href="#Subjects">↑ Subjects</a></small></p>''' )
    return f'''<h2 id="Subjects">Subjects</h2>
<p class="topicGroups">{contentsHtml}</p>
{NEWLINE.join(groupHtmls)}'''
# end of createTopicPages.makeTopicIndexHtml


def createTopicPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    global TOPIC_LIST
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateTopicPages( {level}, {folder} with {state.booksToLoad['OET']} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # First make our list of topics (mostly for the Prev/Next links)
    assert len(TOPIC_LIST) == 0
    for topic,refsList in TOPIC_TABLE.items():
        TOPIC_LIST.append( (topic,topicFilename(topic),refsList) )

    for tt in range( 0, len(TOPIC_LIST) ):
        createTopicPage( level, folder, tt, state )

    # Create topic index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop(level, None, 'topicsIndex', None, state, metadata=(
        'Bible passages by topic',
        f'Choose from {len(TOPIC_TABLE)} topics, grouped by subject, to explore selected Bible passages in the Open English Translation.'))
    indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">Topic pages</h1>
<p>These pages contain selected passages from the <em>Open English Translation</em> for the given topics. Each page contains the passage from the <em>OET Readers’ Version</em> on the left, with the <em>OET Literal Version</em> on the right. No notes or commentary is included—our aim is simply to conveniently list the passages in one place so that readers can make up their own minds about how the passages should be interpreted.</p>
{makeTopicIndexHtml()}
<p class="note">Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any topics that you’d like us to add, or any passages that you’d like us to add to any topic page.</p>
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'topicsIndex' )}'''
    assert checkHtml( 'topicsIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createTopicPages() finished processing {len(TOPIC_TABLE)} topics: {str(TOPIC_TABLE.keys()).replace('dict_keys([','').replace('])','')}" )
    return True
# end of createTopicPages.createTopicPages


def createTopicPage( level:int, folder:Path, topicNumber:int, state:State ) -> bool:
    """
    Create a page for each Bible topic.

    topicNumber is an index into the global TOPIC_LISTS[ (topic,topicFilename,refsList) ]

    Note: The above refsList can include Bible refs, e,g, 'MRK_1:2', and word refs, e.g., 'HebLem/nāḩam'
            as well as headings, e.g., 'H3 Only God can do that'
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPage( {level}, {folder}, {topicNumber} {state.BibleVersions} )" )

    topic,topicFilename,refsList = TOPIC_LIST[topicNumber]

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createTopicPage for '{topic}' ({topicFilename}) with {len(refsList)} Bible passages…" )
    rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']

    leftLink = f'<a title="Previous topic: {TOPIC_LIST[topicNumber-1][0]}" href="{TOPIC_LIST[topicNumber-1][1]}#Top">←</a> ' if topicNumber>0 else ''
    rightLink = f' <a title="Next topic: {TOPIC_LIST[topicNumber+1][0]}" href="{TOPIC_LIST[topicNumber+1][1]}#Top">→</a>' if topicNumber<len(TOPIC_LIST)-1 else ''
    homeLink = f' <a title="Topic index" href="index.htm">⌂</a>'

    combinedHtmlChunks = []
    lvChapterCache = {}
    for rr,ref in enumerate( refsList, start=1 ):
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 5:
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"  {rr} ‘{topic}’ {ref=}")
        if ref.startswith( 'H3 '): # Then it's a heading (we'll remove this initial part of the string)
            combinedHtmlChunks.append( f'''<h3>{ref[3:]}</h3>
<h3> </h3>''' ) # Second one is to keep the number of columns matched - put a space in so checkHTML accepts it
        elif '/' in ref: # we'll assume it's a lemma reference
            path, word = ref.split( '/' )
            combinedHtmlChunks.append( f'''<p class="lemmaLink">See uses of <b>{'Hebrew' if 'Heb' in path else 'Greek'} word root <a href="{'../'*level}ref/{ref}.htm#Top">‘{word}’</a></b>.</p>
<p class="lemmaLink"> </p>''' ) # Second one is to keep the number of columns matched - put a space in so checkHTML accepts it
        else: # We'll assume it's a scripture reference
            BBB, refRest = ref.split( '_' ) # This split will fail if it's not a valid scripture reference
            # if BBB not in rvBible or BBB not in lvBible:
            #     continue # Don't force that book to be loaded

            try: C, Vs = refRest.split( ':' )
            except ValueError:
                assert refRest.isdigit()
                C, Vs = refRest, None
            # print( f"    {rr} {topic} {ref=} {BBB=} {refRest=} {C=} {Vs=}")
            startV = '1'
            try:
                if Vs is None: # then it's an entire chapter (no verses specified)
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                elif '-' in Vs: # then it's a verse range
                    startV, endV = Vs.split( '-' )
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseDataRange( (BBB,C,startV), (BBB,C,endV) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                elif '–' in Vs: # en-dash, then it's a chapter range
                    not_written_yet
                else: # assume it's a single verse
                    assert Vs and Vs.isdigit()
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C,Vs) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                    startV = Vs # Used to build the HTML anchor below
            except KeyError as error:
                error.add_note(f"While creating topic {topic!r} ({topicFilename}): "
                               f"could not retrieve {rvBible.abbreviation} passage {ref}")
                raise
            # print( f"{rvVerseEntryList=}" )
            # print( f"{lvVerseEntryList=}" )
            rvTextHtml = convertVerseEntryListToHtml( level, rvBible.abbreviation, (BBB,C), 'topicalPassage', rvContextList, rvVerseEntryList, basicOnly=False, state=state, livenWordLinks=BBB in rvBible, colouriseWordClasses=False )
            # rvTextHtml = livenIORs( BBB, rvTextHtml, sections )
            rvTextHtml = do_OET_RV_HTMLcustomisations( f'Topic={topic}@{BBB}_{C}', rvTextHtml )

            lvTextHtml, _ = renderOETLVPassage(level, lvBible, (BBB,C,startV),
                rvVerseEntryList, 'topicalPassage', state, lvChapterCache, rr)

            if rvTextHtml.startswith( '<div class="rightS1Box">' ):
                rvTextHtml = f'<div class="section">{rvTextHtml}' # This got removed above
            # Handle footnotes and cross-references so the same fn1 doesn't occur for both chunks if they both have footnotes
            rvTextHtml = rvTextHtml.replace( 'id="footnotes', f'id="footnotes{rr}RV' ).replace( 'id="fn', f'id="fn{rr}RV' ).replace( 'href="#fn', f'href="#fn{rr}RV' ) \
                                .replace( 'id="crossRefs', f'id="crossRefs{rr}RV' ).replace( 'id="xr', f'id="xr{rr}RV' ).replace( 'href="#xr', f'href="#xr{rr}RV' )
            lvTextHtml = lvTextHtml.replace( 'id="footnotes', f'id="footnotes{rr}LV' ).replace( 'id="fn', f'id="fn{rr}LV' ).replace( 'href="#fn', f'href="#fn{rr}LV' ) \
                                .replace( 'id="crossRefs', f'id="crossRefs{rr}LV' ).replace( 'id="xr', f'id="xr{rr}LV' ).replace( 'href="#xr', f'href="#xr{rr}LV' )
            combinedHtmlChunks.append( f'''<h3>OET <a title="View in context of whole book" href="{'../'*level}OET/byDoc/{BBB}.htm#C{C}V{startV}">{getOETTidyBBB(BBB,True,True,'\u202f',True)}</a> <a title="View in context of whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#V{startV}">{refRest}</a></h3>
<h3> </h3>
<div class="chunkRV">{rvTextHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvTextHtml}</div><!--chunkLV-->''' )
 # Second h3 above is to keep the number of columns matched - put a space in so checkHTML accepts it

    combinedHtml = f'''<div class="RVLVcontainer">
<h2>Readers’ Version</h2>
<h2>Literal Version <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>
{NEWLINE.join(combinedHtmlChunks)}</div><!--RVLVcontainer-->'''

    filepath = folder.joinpath( topicFilename )
    top = makeTop(level, None, 'topicPassages', None, state, metadata=(
        f'Bible passages on {topic}',
        f'Read selected Bible passages on {topic} in the Open English Translation, with links to the passages in context.'))
            # .replace( f'''<a title="{state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/rel/{sFilename}#Top">{thisRvBible.abbreviation}</a>''',
            #         f'''<a title="Up to {state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/index.htm#Top">↑{thisRvBible.abbreviation}</a>''' )
    topicHtml = f'''{top}<!--topic page-->
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
<h1 id="Top">{topic}</h1>
{topicGroupLink(topic)}<p>This page contains selected passages from the <em>Open English Translation</em> with the passage from the <em>OET Readers’ Version</em> on the left, and the <em>OET Literal Version</em> on the right. Minimal commentary is included (only some headings)—our aim is simply to conveniently list the passages in one place so that our readers can make up their own minds about what the writer of the passage was intending to communicate.</p>
{topicReferenceMaterial(level,topic,state)}{removeDuplicateCVids(combinedHtml)}
<p class="note"><small>Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any passages that you’d like us to add to this topic page, or any passages that need a little bit more context around them. (We encourage our readers to always view things in their context, so we discourage use of the word ‘verse’, especially in sayings like, “This verse says …”.)</small></p>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'topicPassages' )}'''
    assert checkHtml( f'{topic} Topic', topicHtml )
    assert '.htm#aC' not in topicHtml and '.htm#bC' not in topicHtml, topicHtml
    assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as topicHtmlFile:
        topicHtmlFile.write( topicHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(topicHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    createTopicPage() finished processing '{topic}' with {len(refsList):,} references." )
    return True
# end of createTopicPages.createTopicPage



# The following KINGDOM_LIST is used to determine the number of pages and their titles
#   The second reference(s) are used to include the maps that would occur at those references
KINGDOM_LIST = (('Promised land',[('JOS','13','1')]),
                ('Full kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Northern kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Southern kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Both kingdoms',[('KI2','14','25')]))
# Editorial readings approved separately from the existing map selections.
KINGDOM_READINGS = {
    'Promised land':('GEN_12:1-7','JOS_21:43-45'),
    'Full kingdom':('SA2_7:8-16',),
    'Northern kingdom':('KI1_12:25-33',),
    'Southern kingdom':('KI2_18:1-7','KI2_25:1-12'),
    'Both kingdoms':('EZE_37:21-28',),
}
# The following KINGDOM_INFO_HTML_DICT contains the HTML prose paragraphs to go on each page
KINGDOM_INFO_HTML_DICT = {
    'Promised land':'''<p>After four hundred years in Egypt (Heb. Mitsrayim) and ending up as slaves there, Yahweh told Mosheh (Moses) that he would lead the descendants of Yakov/Yisrael (Jacob/Israel) to the land that he’d promised to them.</p>''',
    'Intro':'''<p>Yakov (Jacob) was the patriarch of Yisrael (Israel).
After his descendants left Egypt (Heb. Mitsrayim) and moved into ‘the promised land’, they were guided by the prophets and by various heroes and guides (traditionally known in English as ‘Judges’, although that describes their role poorly) before they had a king. Shaul (Saul) was their first king, succeeded by King David and then his son King Shelomoh (Solomon).
However, the more northern tribes disagreed with the leaders of the southern tribes of Yehudah (Judah, David’s tribe) and Benyamin over succession plans.
They also resented having to travel to Yerushalem (Jerusalem, located in Yehudah's area) several times per year.
All of that and more eventually resulted in Yisrael splitting into two kingdoms: the northern kingdom which continued to be known as <b>Yisrael</b> with <b>Samaria</b> as its capital city,
and a southern kingdom that became known by the name of the dominant tribe of <b>Yehudah</b> (Benyamin was a relative small tribe) and which retained <b>Yerushalem</b> (Jerusalem) as its capital.</p>''',
    'Full kingdom':'''<p>By the ‘Full kingdom’, we mean the full kingdom of Yisrael encompassing all the tribes descending from Yakov's twelve sons plus Yosef's (Joseph's) two sons. The three kings of this kingdom were King Shaul, then King David, and his son King Shelomoh.</p>
<p>The prophets who spoke to the full kingdom of Yisrael include __SAMUEL_LINK__, Gad, Natan (Nathan), and Ahiyah (Ahijah).</p>''',
    'Northern kingdom':'''<p>By the ‘Northern kingdom’, we mean the northern area occupied by the majority ten tribes who then established Samaria as their capital and worship centre.
Sometimes the northern kingdom also goes by the name ‘Efraim’ (Ephraim, one of the ten tribes).</p>
<p>The prophets who spoke to the northern kingdom of Yisrael include Eliyyyah (Elijah), Elisha, Yonah (Jonah), Amos, and Hoshea (Hosea).</p>''',
    'Southern kingdom':'''<p>By the ‘Southern kingdom’, we mean the southern area of what was originally part of the Kingdom of Israel, but when the very large tribe of Yehudah (Judah) and the very small tribe of Benyamin (Benjamin) split off to stay loyal to David’s descendants who continued to rule from Yerushalim (Jerusalem).
This kingdom of Yehudah continued to be ruled by David’s descendants, although we often saw a pattern of ‘good king’, ‘bad king’ (unlike the Northern Kingdom which pretty much had all bad kings).</p>
<p>The prophets who spoke to the southern kingdom of Yehudah include Eliyyyah (Elijah), Isaiah, Mikah (Micah), Zefanyah (Zephaniah), Ovadyah (Obadiah), Nahum, Yeremyah (Jeremiah), Yoel (Joel), and Habakkuk.</p>''',
    'Both kingdoms':'''<p>By the term ‘Both kingdoms’, we mean that the narrative covers both of the two kingdoms of Yisrael and Yehudah (that had originally been united after the Israelis in the ‘<a href="PromisedLand.htm#Top">promised land</a>’ demanded a king, but which split after the death of King Shelomoh).</p>
<p>The prophets who spoke to both kingdoms (after they had been divided) include Isaiah, ...</p>''',
    }
def createKingdomPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createKingdomPages( {level}, {folder}, {state.BibleVersions} )" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateKingdomPages( {level}, {folder} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    entities = loadReferenceEntities(ENTITY_FOLDER,state)
    indexList = []
    for kk, (kingdomName,mapRefList) in enumerate( KINGDOM_LIST ):
        oneWordKingdomName = kingdomName.replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )
        filename = f'{oneWordKingdomName}.htm'
        indexList.append( (kingdomName, oneWordKingdomName, filename) )
        filepath = folder.joinpath( filename )
        top = makeTop(level, None, 'kingdom', None, state, metadata=(
            f'{kingdomName} — biblical history and readings',
            f'Explore the {kingdomName.lower()} through the selected readings, people and places recorded on this page.'))
        leftLink = f'<a title="Previous kingdom" href="{KINGDOM_LIST[kk-1][0].replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )}.htm#Top">←</a> ' if kk>0 else ''
        rightLink = f' <a title="Next kingdom" href="{KINGDOM_LIST[kk+1][0].replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )}.htm#Top">→</a>' if kk<len(KINGDOM_LIST)-1 else ''
        homeLink = f' <a title="Kingdom index" href="index.htm">⌂</a>'

        # Handle BibleMapper maps and notes
        kingdomHtml = ''
        for mm, (BBB,C,V) in enumerate( mapRefList ):
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    Checking {oneWordKingdomName} maps at {BBB} {C}:{V}…" )
            # This can fail if not all books are loaded, e.g., in TEST_MODE_FLAG
            bmmHtml = getBibleMapperMaps( level, BBB, C, V, None, None, state.preloadedBibles['OET-RV'], state )
            # assert bmmHtml, f"{kk=} {kingdomName=} {mapRefList=} {mm=} {BBB} {C}:{V}"
            if bmmHtml:
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"     Got some map HTML for {oneWordKingdomName} using {BBB} {C}:{V}" )
                bmmHtml = f'''<div {'id="BMM" ' if mm==0 else ''}class="parallelBMM"><a title="Go to BMM copyright page" href="{'../'*level}BMM/details.htm#Top">BMM</a> <b><a href="https://BibleMapper.com" target="_blank" rel="noopener noreferrer">BibleMapper.com</a> Maps</b>: {bmmHtml}</div><!--end of BMM-->'''
                if not kingdomHtml:
                    kingdomHtml = '<hr style="width:50%;margin-left:0;margin-top: 0.3em">'
                kingdomHtml = f'{kingdomHtml}\n{bmmHtml}'

        kingdomInfo = KINGDOM_INFO_HTML_DICT[kingdomName]
        if '__SAMUEL_LINK__' in kingdomInfo:
            samuelLink = scriptureLink(level, ('SA1','7','2'), 'OET-RV', 'OET', 'byC',
                'Shemuel (Samuel)', state, title='Read about Shemuel in context')
            if state.TEST_MODE_FLAG and 'SA1' not in state.booksToLoad['OET']:
                samuelLink = 'Shemuel (Samuel)'
            kingdomInfo = kingdomInfo.replace('__SAMUEL_LINK__', samuelLink)
        intro = KINGDOM_INFO_HTML_DICT['Intro']+NEWLINE if 'kingdom' in kingdomName else ''
        kingdomInfo = kingdomArticleLinks(intro+kingdomInfo,level,entities)
        entityLinks = ' · '.join(entityLink(key,level,entities) for key in KINGDOM_ENTITIES[oneWordKingdomName]
                               if key in entities['records'])
        selections = []
        for citation in KINGDOM_READINGS[kingdomName]:
            BBB,selection = citation.split('_',1)
            selections.append((citation.replace('_',' ').replace('-','–'),parseReferenceSelection(BBB,selection,'eng')))
        readings = '<h2>Selected readings</h2>'+renderReferencePassageGroup(level,selections,'eng',state,
            instancePrefix=f'kingdom-{oneWordKingdomName}-')
        html = f'''{top}<div class="{oneWordKingdomName}"><a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 class="{oneWordKingdomName}" id="Top">{kingdomName} details</h1>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
{kingdomInfo}
<h2>People and places</h2><p>{entityLinks}</p>
{readings}
</div>
{kingdomHtml if kingdomHtml else ''}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'kingdom' )}'''
        assert checkHtml( f'{oneWordKingdomName}', html )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
            indexHtmlFile.write( html )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(html):,} characters written to {filepath}" )

    # Now make an index page
    filename = f'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop(level, None, 'kingdom', None, state, metadata=(
        'Kingdoms of Israel and Judah — Bible study index',
        'Explore the promised land, the united kingdom and the northern and southern kingdoms through Bible readings.'))
    indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<p class="note"><b><a href="../index.htm#Top">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/index.htm#Top">Hebrew words index</a> <a href="../HebWrd/transIndex.htm#Top">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/index.htm#Top">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm#Top">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../HebStrng/index.htm#Top">Hebrew Strong\'s numbers index</a></p>
<p class="note"><a href="../GrkWrd/index.htm#Top">Greek words index</a> <a href="../GrkWrd/transIndex.htm#Top">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/index.htm#Top">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm#Top">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../GrkStrng/index.htm#Top">Greek Strong\'s numbers index</a></p>
<p class="note"><a href="../Per/importantPeopleAlphabeticalIndex.htm#Top">Important people alphabetical index</a> <a href="../Per/importantPeopleChronologicalIndex.htm#Top">Important people chronological index</a> <a href="../Per/index.htm#Top">All people index</a> <a href="../Loc/index.htm#Top">Locations index</a></p>
<p class="note"><span class="selectedBook">Promised land kingdoms index</span></p>
<p class="note"><a href="../Stats/index.htm#Top">Bible statistics</a></p>
{referenceIndexLinks(level,state)}<h1 id="Top">Index to ‘Kingdom’ pages</h1>
<h2>These pages describe the kingdoms after the Israelis entered the ‘promised land’</h2>
{'\n'.join([f'<div class="{oneWordKingdomName}"><p class="note"><a href="{kFilename}">{kingdomName}</a></p></div>' for kingdomName, oneWordKingdomName, kFilename in indexList])}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'kingdomIndex' )}'''
    assert checkHtml( 'kingdomIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(html):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createKingdomPages() finished processing {len(KINGDOM_LIST)} kingdom pages plus index." )
    return True
# end of createTopicPages.createKingdomPages


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
