#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Related columns preserve complete LV passages and independent note addresses.

CHANGELOG:
    2026-10-30 Exercise optional LV comparisons and cross-chapter numbering.
"""
import re
import unittest

import test_reference_passages as fixtures
from createParallelPassagePages import relatedLVPassage,relatedRVHtml


class RelatedPassageTests(unittest.TestCase):
    setUp=fixtures.ReferencePassageTests.setUp
    load=fixtures.ReferencePassageTests.load
    render=fixtures.ReferencePassageTests.render
    prepare=fixtures.ReferencePassageTests.prepare

    def test_repeated_columns_keep_complete_native_passage_and_unique_notes(self):
        self.prepare()
        entries,_=self.state.preloadedBibles['OET-RV'].getContextVerseData(('MAL','4'))
        html=''.join(relatedLVPassage(2,('MAL','4','1'),entries,self.state,{},column) for column in range(2))
        self.assertEqual(html.count('LV nineteen.'),2)
        self.assertEqual(html.count('LV twenty.'),2)
        self.assertEqual(html.count('<details class="relatedLV">'),2)
        self.assertIn('OET-LV/byC/MAL_C3.htm#C3V19',html)
        self.assertNotIn('OET-LV/byC/MAL_C4',html)
        ids=re.findall(r'id="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))
        for href in re.findall(r'href="#([^"]+)"',html):self.assertIn(href,ids)

    def test_missing_lv_keeps_available_rv_page_usable(self):
        self.prepare()
        del self.state.preloadedBibles['OET-LV']
        self.assertEqual(relatedLVPassage(2,('MAL','4','1'),[],self.state,{},0),'')

    def test_partial_rv_section_includes_the_whole_matching_lv_verse(self):
        self.prepare()
        entries,_=self.state.preloadedBibles['OET-RV'].getContextVerseData(('MAL','4'))
        entries=[entry for entry in entries if entry.getMarker()!='v' or entry.getCleanText()!='1']
        html=relatedLVPassage(2,('MAL','4','1b'),entries,self.state,{},0)
        self.assertIn('LV nineteen.',html)
        self.assertIn('LV twenty.',html)
        self.assertIn('includes that whole verse',html)

    def test_note_isolation_preserves_external_targets_and_primary_verse_anchors(self):
        self.prepare()
        source='<span id="V1"></span><span id="C4V1"></span><p id="fn1"><a href="#C4V1">Return</a></p><a href="../MAL/MAL_S3.htm#V1">Other section</a><a href="#C4V">4:</a>'
        primary=relatedRVHtml(source,2,'MAL',self.state,'a',primary=True)
        self.assertIn('id="V1"',primary)
        self.assertIn('id="afn1"',primary)
        self.assertIn('href="../MAL/MAL_S3.htm#V1"',primary)
        self.assertNotIn('href="#C4V"',primary)
        secondary=relatedRVHtml(source,2,'MAL',self.state,'b')
        self.assertIn('id="bV1"',secondary)
        self.assertIn('href="#bC4V1"',secondary)
        self.assertIn('href="../MAL/MAL_S3.htm#V1"',secondary)


if __name__=='__main__':unittest.main()
