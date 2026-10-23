#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for Hebrew alignment and parallel-page colour keys.

CHANGELOG:
    2026-10-21 Cover paragraph markers, genuine mismatches, and OET colour-key fallback.
"""
from contextlib import ExitStack
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Formats.USFMBible import USFMBible
import createParallelVersePages as pages
from oetWords import matchedHebrewWordRows
from settings import State


class HebrewParallelTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.state = State()
        self.state.BibleVersions = ['OET-LV', 'UHB']
        self.state.TEST_VERSIONS_ONLY = self.state.BibleVersions
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.state.booksToLoad = {'OET': []}
        self.state.preloadedBibles = {'OET-RV': None} # only passed to the disabled map provider
        self.state.possibleUnmatchedProperNames = set()
        self.state.versionComments = {}
        self.table = ['header']
        indexes = {}
        lvVerses, uhbVerses = [], []
        for verse, marker in ((1, 'פ'), (2, 'ס'), (3, '')):
            first = len(self.table)
            if verse < 3:
                # The verb/maqaf/noun/paragraph ending reproduces Gen 4:26.
                entries = [('w1', '', 'VPp3ms', 'יֻלַּד'), ('', 'seg', 'x-maqqef', '־'),
                           ('w2', '', 'Ncmsa', 'בֵּן')]
                lvVerses.append(f'\\v {verse} he/it_was_born¦{first} a_son¦{first+2}.')
                uhb = (r'\w יֻלַּד|lemma="ילד" strong="H3205" x-morph="He,VPp3ms"\w*־'
                       r'\w בֵּן|lemma="בן" strong="H1121" x-morph="He,Ncmsa"\w*׃')
            else:
                entries = [('w1', '', 'Ncmsa', 'סוּס')]
                lvVerses.append(f'\\v {verse} a_horse¦{first}.')
                uhb = r'\w סוּס|lemma="סוס" strong="H5483" x-morph="He,Ncmsa"\w*׃'
            entries.append(('', 'seg', 'x-sof-pasuq', '׃'))
            if marker:
                entries.append(('', 'seg', 'x-pe' if marker == 'פ' else 'x-samekh', marker))
            for suffix, kind, morph, word in entries:
                fields = [''] * 19
                fields[0:2] = [f'GEN_1:{verse}{suffix}', kind]
                fields[2] = str(len(self.table))
                fields[5:8] = [morph, word, word]
                self.table.append('\t'.join(fields))
            indexes[f'GEN_1:{verse}'] = first, len(self.table)-1
            uhbVerses.append(f'\\v {verse} {uhb}{marker}')
        name = 'OET-LV_OT_word_table.tsv'
        self.state.OETRefData = {'word_tables': {name: self.table}, 'word_table_indexes': {name: indexes}}
        for version, cls, verses in (('OET-LV', ESFMBible, lvVerses), ('UHB', USFMBible, uhbVerses)):
            folder = self.root / version
            folder.mkdir()
            (folder / '01-GEN.usfm').write_text('\\id GEN\n\\h Genesis\n\\mt1 Genesis\n\\c 1\n' + '\n'.join(verses) + '\n')
            bible = cls(folder, givenAbbreviation=version, versification=self.state.BibleVersifications[version])
            bible.loadBooks()
            self.state.preloadedBibles[version] = bible

    def uhb(self, verse):
        entries, context = self.state.preloadedBibles['UHB'].getContextVerseData(('GEN', '1', str(verse)))
        text = pages.convertVerseEntryListToHtml(2, 'UHB', ('GEN', '1', str(verse)),
            'parallelVerse', context, entries, basicOnly=True, state=self.state)
        return text, entries

    def test_paragraph_markers_preserve_links_colours_and_visible_endings(self):
        for verse, marker in ((1, 'פ'), (2, 'ס')):
            original, entries = self.uhb(verse)
            for spaced in (False, True):
                with self.subTest(marker=marker, spaced=spaced):
                    text = original.replace(f'׃{marker}', f'׃ {marker}') if spaced else original
                    html, keys = pages.brightenUHB('GEN', '1', str(verse), text, entries, self.state)
                    self.assertIn('class="hebVrb"', html)
                    self.assertEqual(keys, ['<span class="hebVrb">khaki</span>:verbs'])
                    self.assertEqual(html.count('ref/HebWrd/'), 2)
                    for word in (1, 2):
                        self.assertIn(f'GENc1v{verse}w{word}.htm#Top', html)
                    self.assertIn(f'׃{" " if spaced else ""}{marker}</span>', html)

    def test_separators_and_real_letters_are_not_discarded(self):
        for separator, morphology in (('־', 'x-maqqef'), ('׀', 'x-paseq')):
            with self.subTest(separator=separator):
                fields = self.table[2].split('\t')
                fields[5:7] = morphology, separator
                self.table[2] = '\t'.join(fields)
                self.assertEqual(matchedHebrewWordRows('GEN', '1', '1', ['יֻלַּד', separator, 'בֵּן'], self.state),
                                 [1, 2, 3])
        # This noun begins and ends with samekh; neither letter is a paragraph marker.
        text, entries = self.uhb(3)
        html, keys = pages.brightenUHB('GEN', '1', '3', text, entries, self.state)
        self.assertIn('>סוּס</a>', html)
        self.assertEqual(keys, [])

    def render(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(pages, 'navigationVersification', return_value=
                SimpleNamespace(getNumChapters=lambda b: 1, getNumVerses=lambda b, c: 3)))
            stack.enter_context(patch.object(pages, 'makeTop', return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            stack.enter_context(patch.object(pages, 'makeBottom', return_value='</body></html>'))
            for function in ('getVerseMetaInfoHtml', 'formatTyndaleBookIntro', 'formatTyndaleNotes',
                             'getFormattedSILOpenTranslationNotes', 'formatUnfoldingWordTranslationNotes',
                             'getBibleMapperMaps', 'getOpenBibleImages'):
                stack.enter_context(patch.object(pages, function, return_value=''))
            folder = self.root / 'par'
            pages.createParallelVersePagesForBook(1, folder, 'GEN',
                ['<a title="Genesis" href="../GEN.htm#Top">GEN</a>'],
                self.state.BibleVersions, self.state)
        return [(folder / 'GEN' / f'C1V{v}.htm').read_text() for v in (1, 2, 3)]

    def test_complete_pages_have_one_key_and_no_key_leaks_to_uncoloured_verse(self):
        first, second, third = self.render()
        for html in (first, second):
            self.assertEqual(html.count('khaki</span>:verbs'), 1)
            self.assertEqual(html.count('id="coloursButton"'), 1)
        self.assertNotIn('class="key"', third)
        self.assertNotIn('coloursButton', third)

    def test_genuine_mismatch_keeps_oet_key_without_inventing_hebrew_links(self):
        fields = self.table[1].split('\t')
        fields[6] = fields[7] = 'קָם' # different consonants, rather than a paragraph marker
        self.table[1] = '\t'.join(fields)
        with self.assertRaisesRegex(ValueError, 'GEN 1:1: mapped word rows differ'):
            matchedHebrewWordRows('GEN', '1', '1', ['יֻלַּד', '־', 'בֵּן'], self.state)
        with self.assertLogs(level='WARNING') as captured:
            first, _, _ = self.render()
        self.assertTrue(any('Hebrew word alignment unavailable for GEN_1:1' in line for line in captured.output))
        uhb = re.search(r'<p id="UHB".*?</p>', first, re.S)[0]
        self.assertNotIn('ref/HebWrd/', uhb)
        self.assertNotIn('class="hebVrb"', uhb)
        self.assertEqual(first.count('khaki</span>:verbs'), 1)
        self.assertIn('id="coloursButton"', first)


if __name__ == '__main__':
    unittest.main()
