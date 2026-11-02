#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Dictionary citations preserve the source selection and valid HTML structure.

CHANGELOG:
    2026-10-30 Cover full Tyndale selections, bounded previews and alternate numbering.
    2026-10-31 Check compact OET-first links with RV/LV-only alternatives.
    2026-11-02 Expect hyphenated edition labels and a nonbreaking gap after OET.
    2026-11-02 Check linked prose and one final reading link without edition alternatives.
"""
import re
import unittest

from dictionaryPassages import parseTyndaleCitation,livenTyndaleCitations
import test_reference_passages as fixtures


class DictionaryPassageTests(unittest.TestCase):
    setUp = fixtures.ReferencePassageTests.setUp
    load = fixtures.ReferencePassageTests.load
    render = fixtures.ReferencePassageTests.render
    prepare = fixtures.ReferencePassageTests.prepare

    def test_complete_cross_chapter_range_and_disjoint_list(self):
        refs = parseTyndaleCitation('Mark.1.44-2.2,5,7-8')
        self.assertEqual(len(refs),7)
        self.assertEqual(refs[-1],('MRK','2','8',None))
        self.assertNotIn(('MRK','2','6',None),refs)
        self.assertEqual(len(parseTyndaleCitation('Ps.117')),2)

    def test_previews_follow_paragraphs_and_map_the_entire_selection(self):
        self.prepare()
        html = livenTyndaleCitations('<p>See <a href="?bref=Mal.4.1-2">Malachi 4:1–2</a>.</p>',1,'TOBD:test',self.state,previews=True)
        self.assertIn('LV nineteen.',html)
        self.assertIn('LV twenty.',html)
        self.assertIn('MAL_C3.htm#C3V19',html)
        self.assertIn('>Malachi 4:1–2</a>',html)
        self.assertNotIn('RV-only',html)
        self.assertNotIn('LV-only',html)
        self.assertLess(html.index('</details>'),html.index('Jump to '))
        self.assertNotIn('<small>(',html)
        self.assertLess(html.index('</p>'),html.index('<details>'))
        self.assertNotIn('?bref=',html)

    def test_repeated_citations_share_preview_and_ids(self):
        self.prepare()
        citation='<p><a href="?bref=Mal.4.1">Malachi 4:1</a></p>'
        html=livenTyndaleCitations(citation*2,1,'TOBD:test',self.state,previews=True)
        self.assertEqual(html.count('Show passage in OET'),1)
        ids=re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))

    def test_invalid_citation_is_readable_without_a_guessed_destination(self):
        self.prepare()
        html=livenTyndaleCitations('<p><a href="?bref=Mal.99.9">Malachi 99:9</a></p>',1,'TOBD:test',self.state,previews=True)
        self.assertEqual(html,'<p>Malachi 99:9</p>')

    def test_non_dictionary_caller_gets_no_embedded_previews(self):
        self.prepare()
        html=livenTyndaleCitations('<a href="?bref=Mal.4.1-2">4:1–2</a>',1,'TOSN:test',self.state)
        self.assertIn('OET/byC/MAL_C4.htm#C4V1',html)
        self.assertIn('>4:1–2</a>',html)
        self.assertEqual(html.count('<a '),1)
        self.assertNotIn('<details>',html)


if __name__=='__main__': unittest.main()
