#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for reference-page verse focus and colour guidance.

CHANGELOG:
    2026-10-23 Cover exact occurrence highlighting and all four word/lemma page builders.
    2026-10-23 Validate punctuation, notes, unused variants, and unloaded TEST books.
"""
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import createOETReferencePages as pages
from html import loadCSSStyles
from openbibledata_rust import checkHtmlForMissingStyles
from settings import State


class ReferenceVerseTests(unittest.TestCase):
    def test_exact_occurrence_and_all_gloss_parts_in_mapped_portions(self):
        for folder in ('HebWrd', 'GrkWrd'):
            with self.subTest(folder=folder):
                word = f'{folder}/JHNc1v7w4.htm'
                target = f'<a class="grkVrb" href="../../ref/{word}#Top">came</a>'
                split = f'<a href="../../ref/{word}#Top"><span class="ul">_</span>along</a>'
                other = f'<a href="../../ref/{folder}/JHNc1v7w40.htm#Top">came</a>'
                lv = f'<p>{target}{split} {other}</p>'
                # A mapped RV passage can contain several verse portions, retaining LV word links.
                rv = f'<p>(JHN 1:8) {other}</p><p>{target}</p>'
                with patch.object(pages, 'get_OET_LV_verse_HTML', return_value=lv), \
                     patch.object(pages, 'get_OET_RV_verse_HTML', return_value=rv):
                    resultLV, resultRV = pages.get_focused_OET_verse_HTML(2, 'JHN', '1', '7', word)
                    self.assertEqual(resultLV, f'<p><b>{target}</b><b>{split}</b> {other}</p>')
                    self.assertEqual(resultRV, f'<p>(JHN 1:8) {other}</p><p><b>{target}</b></p>')
                    # Requesting the other occurrence must not retain the first occurrence's focus.
                    secondLV, _ = pages.get_focused_OET_verse_HTML(
                        2, 'JHN', '1', '7', f'{folder}/JHNc1v7w40.htm')
                    self.assertEqual(secondLV, f'<p>{target}{split} <b>{other}</b></p>')

    def test_unaligned_rv_is_not_guessed_from_matching_english(self):
        rv = '<p class="RVVerseText">for a testimony</p>'
        with patch.object(pages, 'get_OET_LV_verse_HTML', return_value=''), \
             patch.object(pages, 'get_OET_RV_verse_HTML', return_value=rv):
            self.assertEqual(pages.get_focused_OET_verse_HTML(
                2, 'JHN', '1', '7', 'GrkWrd/JHNc1v7w4.htm'), ('', rv))

    def test_key_describes_only_colours_present_and_preserves_morphology_key(self):
        original = ('<p class="btnBar">controls</p><a class="grkVrb other">go</a>'
                    '<span class="hebYhwh">Yahweh</span><span class="noLinkYet">unaligned</span>'
                    '<p class="key" id="Key">Morphology</p>')
        html = pages.add_reference_colour_key(original, 2)
        self.assertIn('<p class="btnBar">controls</p>\n<p class="key" id="ColourKey">', html)
        key = re.search(r'<p class="key" id="ColourKey">(.*?)</p>', html, re.DOTALL)[1]
        keyText = re.sub('<[^>]+>', '', key)
        self.assertIn('onclick="hide_show_colours()">C</button>', key)
        self.assertIn('khaki:verbs', keyText)
        self.assertIn('green:YHWH', keyText)
        self.assertIn('grey:word alignment not yet available', keyText)
        self.assertNotIn('accusative', keyText)
        self.assertIn('alignments are incomplete', keyText)
        self.assertIn('<p class="key" id="Key">Morphology</p>', html)

    def test_punctuation_page_has_no_orphan_control(self):
        html = '<h1>Hebrew segment punctuation</h1>'
        self.assertEqual(pages.add_reference_colour_key(html, 2), html)


class ReferencePageTests(unittest.TestCase):
    """Run the real four page builders with a small word-table fixture."""

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.state = State()
        self.state.TEST_MODE_FLAG = True
        self.state.ALL_TEST_REFERENCE_PAGES_FLAG = True
        self.state.booksToLoad = {'OET': ['GEN', 'JHN']}
        self.state.preloadedBibles = {'OET-LV': SimpleNamespace(OTsourceFolder=self.root),
                                      'OET-RV': {'GEN': None, 'JHN': None}}
        self.stack.enter_context(patch.object(pages, 'state', self.state))
        # Page chrome is independent of the word-table and example-rendering behaviour under test.
        self.stack.enter_context(patch.object(pages, 'makeTop', return_value=
            '<!DOCTYPE html><html lang="en"><head><title>__TITLE__</title>\n'
            '<link rel="stylesheet" href="../../BibleWord.css">\n</head><body>'))
        self.stack.enter_context(patch.object(pages, 'makeBottom', return_value='</body></html>'))
        self.stack.enter_context(patch.object(pages, 'get_OET_LV_verse_HTML', side_effect=self.verse))
        self.stack.enter_context(patch.object(pages, 'get_OET_RV_verse_HTML', side_effect=
            lambda *args: self.verse(*args).replace('LVVerseText', 'RVVerseText').replace('OET-LV', 'OET-RV')))
        data = self.state.OETRefData = {'word_tables': {}}
        for name in ('OTFormUsageDict', 'OTLemmaRowNumbersDict', 'OTWordRowNumbersDict',
                     'OETOTGlossWordDict', 'NTFormUsageDict', 'NTLemmaDict',
                     'OETNTGlossWordDict', 'VLTGlossWordDict'):
            data[name] = defaultdict(list)
        for name in ('OTLemmaFormsDict', 'OTFormOETGlossesDict', 'OTLemmaOETGlossesDict',
                     'OTLemmaGlossesDict', 'OTLemmasForRootDict', 'OTStrongsRefs',
                     'NTLemmaFormsDict', 'NTFormOETGlossesDict', 'NTFormVLTGlossesDict',
                     'NTLemmaOETGlossesDict', 'NTLemmaVLTGlossesDict', 'NTStrongsRefs'):
            data[name] = defaultdict(set)
        for name in ('OTLemmaFormsCountDict', 'OTFormOETGlossesCountDict', 'OTLemmaGlossesCountDict',
                     'NTLemmaFormsCountDict', 'NTFormOETGlossesCountDict', 'NTLemmaOETGlossesCountDict'):
            data[name] = defaultdict(int)
        for name in ('OTLemmaGlossDict', 'NTGreekLemmaDict'):
            data[name] = {}
        for name in ('usedHebLemmas', 'usedGrkLemmas', 'usedHebStrongsNumbers', 'usedGrkStrongsNumbers'):
            data[name] = set()
        self.hebrew = '\t'.join(['GEN_1:1w1', '', '1', '1', '1254', 'Vqp3ms', 'בָּרָא',
                                'בָּרָא', 'created', '', 'created', '', '', '', '1', '', '', '', ''])
        self.greek = '\t'.join(['JHN_1:1w1', 'λόγος', 'logos', 'λόγος', 'word', 'word',
                               '', '100', '30560', 'N', '····NMS', ''])
        data['word_tables'][pages.HebrewWordFileName] = ['header', self.hebrew]
        data['word_tables'][pages.GreekWordFileName] = ['header', self.greek]
        (self.root/pages.HebrewLemmaFileName).write_text('Lemma\tGlosses\nבָּרָא\tcreated\n')
        pages.preprocessHebrewWordsLemmasGlosses([], self.state)
        pages.preprocessGreekWordsLemmasGlosses([], self.state)

    @staticmethod
    def verse(level, BBB, C, V):
        folder, colour = ('HebWrd', 'hebVrb') if BBB == 'GEN' else ('GrkWrd', 'grkNom')
        return (f'<p class="LVVerseText"><b>OET-LV</b>: '
                f'<a class="{colour}" href="../../ref/{folder}/{BBB}c{C}v{V}w1.htm#Top">focused</a>'
                f' <a href="../../ref/{folder}/{BBB}c{C}v{V}w2.htm#Top">other</a></p>')

    def test_all_four_page_families_have_key_switch_and_focused_examples(self):
        for kind in ('HebWrd', 'HebLem', 'GrkWrd', 'GrkLem'):
            with self.subTest(kind=kind):
                filename = f'{kind}.htm'
                if kind == 'HebWrd':
                    pages.create_Hebrew_word_page(2, 1, 'בָּרָא', self.hebrew, self.root,
                                                 filename, self.state, [], [])
                elif kind == 'HebLem':
                    pages.create_Hebrew_lemma_page(2, 0, 'בָּרָא', '', '', self.root, filename)
                elif kind == 'GrkWrd':
                    pages.create_Greek_word_page(2, 1, self.greek, '', '', self.root,
                                                filename, self.state, [], [])
                else:
                    pages.create_Greek_lemma_page(2, 0, 'logos', '', '', self.root, filename)
                html = (self.root/filename).read_text()
                self.assertEqual(checkHtmlForMissingStyles(kind, html), [])
                self.assertEqual(html.count('id="coloursButton"'), 1)
                self.assertIn('onclick="hide_show_colours()">C</button>', html)
                key = re.search(r'<p class="key" id="ColourKey">(.*?)</p>', html, re.DOTALL)[1]
                self.assertIn('khaki:verbs' if kind.startswith('Heb') else 'light-green:nominative',
                              re.sub('<[^>]+>', '', key))
                verses = re.findall(r'<p class="(?:LV|RV)VerseText">.*?</p>', html, re.DOTALL)
                self.assertGreaterEqual(len(verses), 2)
                for verse in verses:
                    self.assertEqual(re.findall(r'<b><a [^>]*>(.*?)</a></b>', verse), ['focused'])
                if kind.endswith('Wrd'):
                    # The selected passage precedes the potentially truncated example list.
                    self.assertRegex(html, r'<p class="link">[\s\S]*?</p>\n<p class="LVVerseText">')

    def test_hebrew_punctuation_and_notes_pass_html_validation(self):
        self.state.ALL_TEST_REFERENCE_PAGES_FLAG = False
        self.state.TEST_BOOK_LIST = ['PSA']
        for rowType, morphology, word in (
            ('seg', 'x-maqqef', '־'),
            ('note', '', 'We read one or more accents in L differently than BHS.'),
        ):
            with self.subTest(rowType=rowType):
                fields = ['PSA_1:1', rowType, '350523', '', '', morphology, word] + ['']*12
                row = '\t'.join(fields)
                self.state.OETRefData['word_tables'][pages.HebrewWordFileName] = ['header', row]
                filename = f'{rowType}.htm'
                result, _, _ = pages._create_Hebrew_word_page_MP((2, 1, word, row, self.root, filename))
                self.assertTrue(result)
                html = (self.root/filename).read_text()
                self.assertTrue(pages.checkHtml('HebrewWordPage', html))
                self.assertNotIn('\n\n', html)
                self.assertNotIn('id="coloursButton"', html)
                self.assertNotIn('VerseText', html)

    def test_word_pages_without_loaded_test_book_pass_html_validation(self):
        self.state.preloadedBibles['OET-RV'] = {}
        for language in ('Hebrew', 'Greek'):
            with self.subTest(language=language):
                filename = f'{language}-unloaded.htm'
                if language == 'Hebrew':
                    pages.create_Hebrew_word_page(2, 1, 'בָּרָא', self.hebrew, self.root,
                                                 filename, self.state, [], [])
                else:
                    pages.create_Greek_word_page(2, 1, self.greek, '', '', self.root,
                                                filename, self.state, [], [])
                html = (self.root/filename).read_text()
                self.assertTrue(pages.checkHtml(f'{language}WordPage', html))
                self.assertNotIn('\n\n', html)
                self.assertNotIn('VerseText', html)

    def test_unused_greek_variant_passes_html_validation(self):
        fields = self.greek.split('\t')
        fields[7] = '' # No probability means this word is an unused variant.
        pages.create_Greek_word_page(2, 1, '\t'.join(fields), '', '', self.root,
                                    'unused.htm', self.state, [], [])
        html = (self.root/'unused.htm').read_text()
        self.assertTrue(pages.checkHtml('GreekWordPage', html))
        self.assertIn('Unused Greek word variant', html)
        self.assertNotIn('\n\n', html)
        self.assertNotIn('VerseText', html)


class ReferenceStyleTests(unittest.TestCase):
    def test_versification_reference_style_is_recognised(self):
        for stylesheet in ('BibleWord.css', 'ParallelVerses.css', 'InterlinearVerse.css'):
            with self.subTest(stylesheet=stylesheet):
                html = (f'<link rel="stylesheet" href="../../{stylesheet}">\n'
                        '<small class="versificationRef">Combined passage: Psalm 3:1–2</small>')
                self.assertEqual(checkHtmlForMissingStyles('HebrewWordPage', html), [])
                self.assertIn('small', loadCSSStyles(stylesheet)['versificationRef'])
                # A selector for small must not silently allow other elements.
                self.assertEqual(checkHtmlForMissingStyles('HebrewWordPage', html.replace('small', 'span')),
                                 [('span', 'versificationRef', stylesheet)])


if __name__ == '__main__':
    unittest.main()
