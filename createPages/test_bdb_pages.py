#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""BDB citation and Hebrew Strong's page regressions.

CHANGELOG:
    2026-10-30 Verify original-numbered citations and the complete H3 page integration.
    2026-10-31 Supply the source word for complete Strong's index coverage.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

from BibleOrgSys.OriginalLanguages.HebrewLexicon import HebrewLexiconSimple
import createOETReferencePages as pages
from html import loadCSSStyles
from openbibledata_rust import checkHtmlForMissingStyles
from settings import State


class BDBPageTests(unittest.TestCase):
    def setUp(self):
        self.state = SimpleNamespace(navigationVersification='eng', TEST_MODE_FLAG=False)

    def renderRef(self, osis, label='citation'):
        return f'<span class="ref" data-osis="{osis}" title="{osis}">{label}</span>'

    def link(self, osis, label='citation'):
        return pages.livenBDBReferences(self.renderRef(osis, label), 2, 'H3', self.state)

    def test_h3_references_and_abbreviated_labels(self):
        self.assertIn('href="../../par/JOB/C8V12.htm#Top">Jb 8:12</a>', self.link('Job.8.12', 'Jb 8:12'))
        self.assertIn('href="../../par/SNG/C6V11.htm#Top">Ct 6:11</a>', self.link('Song.6.11', 'Ct 6:11'))

    def test_original_numbering_and_no_second_mapping(self):
        self.assertIn('/PSA/C3V1.htm#Top', self.link('Ps.3.2'))
        self.assertIn('/LEV/C6V3.htm#Top', self.link('Lev.5.22'))
        linked = self.link('Ps.3.2')
        state = State()
        self.assertEqual(pages.mapHtmlLinks(linked, 'OET-LV', 2, state), linked)

    def test_range_chapter_and_subverse_citations(self):
        self.assertIn('/EXO/C3V12.htm#Top', self.link('Exod.3.12-Exod.3.15'))
        self.assertIn('/OET/byC/PSA_C33.htm#C33V1', self.link('Ps.33'))
        self.assertIn('/CH1/C9V8.htm#Top', self.link('1Chr.9.8!a'))

    def test_malformed_unknown_and_unmapped_citations_keep_their_text(self):
        for osis in ('Exod24.17', 'Job.37:23', 'Ezra.814', 'Unknown.1.1', 'Job.999.1'):
            with self.subTest(osis=osis), self.assertLogs(level='WARNING') as log:
                self.assertEqual(self.link(osis), self.renderRef(osis))
            self.assertIn('BDB H3:', log.output[0])
            self.assertIn(osis, log.output[0])

    def test_test_build_does_not_link_unbuilt_books(self):
        self.state.TEST_MODE_FLAG = True
        self.state.TEST_BOOK_LIST = ['PSA']
        self.assertEqual(self.link('Job.8.12'), self.renderRef('Job.8.12'))
        self.assertIn('/PSA/C3V1.htm#Top', self.link('Ps.3.2'))

    def test_full_hebrew_page_uses_bdb_renderer_links_and_styles(self):
        source = ET.fromstring('<entry xmlns="http://openscriptures.github.com/morphhb/namespace" id="a.ab.ab">'
            '[<w>אֵב</w>] <def>freshness</def>, <def>fresh green</def>; '
            '<w>אָחוּ</w>, reed <ref r="Job.8.12">Jb 8:12</ref>; '
            '<ref r="Song.6.11">Ct 6:11</ref>.<status p="1">ref</status></entry>')
        hebrew = HebrewLexiconSimple()
        hebrew.BrownDriverBriggsEntries = {'heb': {'a.ab.ab': ('', '', '')}, 'arc': {}}
        hebrew.BrownDriverBriggsXMLEntries = {'heb': {'a.ab.ab': source}, 'arc': {}}
        lexicon = Mock()
        lexicon.getStrongsEntryField.return_value = ('אָב','','','ʼāⱱ',None)
        lexicon.getStrongsEntryHTML.return_value = '<p>Strong\'s entry</p>'
        lexicon.getBrDrBrEntryHTML.return_value = hebrew.getBrDrBrEntryHTML('a.ab.ab', getFull=True)
        state = State()
        state.TEST_MODE_FLAG = False
        state.OETRefData = {'OTStrongsRefs': {'3': set()}}
        loadCSSStyles('BibleWord.css')
        with TemporaryDirectory() as folder, \
                patch.object(pages, 'makeTop', return_value='<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'), \
                patch.object(pages, 'makeBottom', return_value='</body></html>'):
            made, _ = pages.create_Hebrew_Strongs_page(2, 3, 8674, 100, Path(folder), lexicon, state)
            self.assertTrue(made)
            html = Path(folder, 'H3.htm').read_text()
        self.assertIn('<div class="BDB">', html)
        self.assertIn('[<span class="word" lang="he" dir="rtl">אֵב</span>]', html)
        self.assertIn('/par/JOB/C8V12.htm#Top', html)
        self.assertIn('/par/SNG/C6V11.htm#Top', html)
        self.assertNotIn('class="ref""', html)
        self.assertNotIn('None', html)
        self.assertTrue(pages.checkHtml('BDB H3', html))
        self.assertEqual(checkHtmlForMissingStyles('BDB H3', html), [])


if __name__ == '__main__':
    unittest.main()
