#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check the topic-page data: grouping, filenames, OET-RV wording and that every reference exists.

The reference check reads the OET-RV ESFM source files directly (so it doesn't need the Bibles loaded),
    and is skipped if they're not available.

CHANGELOG:
    2026-11-18 First version, for the grouped and expanded topic table.
    2026-11-19 Allow ‘Rest Day/Sabbath’ (like ‘Immersion/Baptism’ and ‘Yeshua/Jesus’), but not a bare ‘Sabbath’.
"""
from pathlib import Path
import re
import unittest

from settings import State
from studyReferences import topicFilename
from topicTable import TOPIC_GROUPS, TOPIC_TABLE, TOPIC_GROUP_OF
from createTopicPages import topicGroupId, topicGroupLink, makeTopicIndexHtml


RV_FOLDER = Path( State.BibleLocations['OET-RV'] )


def loadRVVerses( BBB:str, cache:dict={} ) -> dict:
    """
    Return {chapterNumber: set of verse numbers} for the OET-RV book (expanding verse bridges).
    """
    if BBB not in cache:
        chapters, C = {}, None
        filepath = RV_FOLDER.joinpath( f'OET-RV_{BBB}.ESFM' )
        if filepath.is_file():
            for match in re.finditer( r'\\([cv]) (\d+)(?:-(\d+))?', filepath.read_text( encoding='utf-8' ) ):
                if match[1] == 'c':
                    C = int( match[2] ); chapters[C] = set()
                elif C is not None:
                    chapters[C].update( range( int(match[2]), int(match[3] or match[2])+1 ) )
        cache[BBB] = chapters
    return cache[BBB]


def checkReference( ref:str ) -> str|None:
    """
    Return None if the reference exists in the OET-RV, else a description of the problem.
    """
    BBB, refRest = ref.split( '_' )
    chapters = loadRVVerses( BBB )
    if not chapters: return f"no OET-RV book {BBB}"
    if ':' not in refRest:
        return None if int(refRest) in chapters else f"no chapter {refRest}"
    C, Vs = refRest.split( ':' )
    if int(C) not in chapters: return f"no chapter {C}"
    verses = [int( V.rstrip('abc') ) for V in Vs.split( '-' )]
    for V in verses:
        if V not in chapters[int(C)]: return f"no verse {C}:{V} (last verse is {max(chapters[int(C)])})"
    if len(verses) == 2 and verses[0] >= verses[1]: return "verse range isn't ascending"
    return None


class TopicTableTests( unittest.TestCase ):

    def test_every_topic_is_in_exactly_one_group( self ):
        self.assertEqual( sum( len(topics) for topics in TOPIC_GROUPS.values() ), len(TOPIC_TABLE) )
        self.assertEqual( set(TOPIC_GROUP_OF), set(TOPIC_TABLE) )
        self.assertLessEqual( len(TOPIC_TABLE), 300 )
        self.assertEqual( TOPIC_GROUP_OF['Advent week one'], 'Christmas/Advent' )

    def test_filenames_are_unique_and_tidy( self ):
        filenames = [topicFilename(topic) for topic in TOPIC_TABLE]
        self.assertEqual( len(set(filenames)), len(filenames) )
        self.assertNotIn( 'index.htm', filenames )
        for topic,filename in zip( TOPIC_TABLE, filenames ):
            self.assertNotIn( '_', filename, f"{topic!r} gives an awkward filename" )

    def test_group_ids_are_unique( self ):
        ids = [topicGroupId(group) for group in TOPIC_GROUPS]
        self.assertEqual( len(set(ids)), len(ids) )
        self.assertTrue( all( re.fullmatch( r'[A-Za-z0-9]+', id ) for id in ids ) )

    def test_titles_and_headings_use_OET_RV_wording( self ):
        for topic,items in TOPIC_TABLE.items():
            if 'Christadelphian' in topic: continue # This page quotes other people's claims
            for text in [topic] + [item[3:] for item in items if item.startswith('H3 ')]:
                with self.subTest( topic=topic, text=text ):
                    self.assertIsNone( re.search( r'(?<!Rest Day/)\bSabbath', text ), "Use ‘Rest Day/Sabbath’" )
                    self.assertIsNone( re.search( r'(?<!/)\b[Bb]aptis', text ), "Use ‘Immersion/Baptism’" )
                    self.assertIsNone( re.search( r'(?<!Yeshua/)\bJesus\b', text ), "Use ‘Yeshua/Jesus’" )

    def test_every_reference_exists_in_the_OET_RV( self ):
        if not RV_FOLDER.is_dir():
            self.skipTest( f"OET-RV source not found at {RV_FOLDER}" )
        for topic,items in TOPIC_TABLE.items():
            for item in items:
                if item.startswith( 'H3 ' ) or '/' in item: continue
                with self.subTest( topic=topic, reference=item ):
                    self.assertIsNone( checkReference( item ) )

    def test_index_lists_every_topic_under_its_group( self ):
        indexHtml = makeTopicIndexHtml()
        for group in TOPIC_GROUPS:
            self.assertEqual( indexHtml.count( f'<h2 id="{topicGroupId(group)}">' ), 1 )
            self.assertEqual( indexHtml.count( f'href="#{topicGroupId(group)}"' ), 1 )
        for topic in TOPIC_TABLE:
            self.assertEqual( indexHtml.count( f'href="{topicFilename(topic)}#Top"' ), 1, topic )
        # Topics appear in group order
        positions = [indexHtml.index( f'href="{topicFilename(topic)}#Top"' ) for topic in TOPIC_TABLE]
        self.assertEqual( positions, sorted(positions) )

    def test_topic_page_links_back_to_its_group( self ):
        self.assertIn( 'href="index.htm#ChristmasAdvent"', topicGroupLink( 'Advent week one' ) )
        self.assertEqual( topicGroupLink( 'Not a real topic' ), '' )


if __name__ == '__main__':
    unittest.main()
