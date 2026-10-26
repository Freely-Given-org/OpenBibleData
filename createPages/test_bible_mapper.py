#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Regression checks for BibleMapper index loading and fork inheritance.

CHANGELOG:
    2026-10-16 Verify map ranges, lazy loading, and parent-side chapter preloading.
"""
import builtins
from collections import defaultdict
import multiprocessing
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import Bibles
import createChapterPages


class ReferenceBible(dict):
    abbreviation = 'OET-RV'

    def getNumVerses(self, BBB, chapter):
        return self[BBB][str(chapter)]


class BibleMapperTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.indexFile = self.folder / 'mapIndex.tsv'
        self.reference = ReferenceBible(GEN={'1':4, '2':3, '3':4, '4':2, '5':3})
        for target, name, value in (
            (Bibles, 'BIBLE_MAPPER_PATH', self.folder),
            (Bibles, 'BMM_INDEX', defaultdict(set)),
            (Bibles, 'BMM_INDEX_LOADED', False),
            (BibleOrgSysGlobals, 'verbosityLevel', 0),
            (BibleOrgSysGlobals, 'debugFlag', False),
        ):
            self.enterContext(patch.object(target, name, value))

    def test_index_preserves_ranges_and_skips_unloaded_books(self):
        self.indexFile.write_text(
            'ReferenceRange\tHiRes\tLowRes\tSupplementary\tOptionalComment\n'
            'GEN_1:2\tSingle_high.jpg\tSingle_low.jpg\tExtra\tA comment\n'
            'GEN_1:3-4\tVerses_high.jpg\t\t\n'
            'GEN_2\tChapter_high.jpg\t\t\n'
            'GEN_2:2–3:2\tAcross_high.jpg\t\t\n'
            'GEN_4–5\tChapters_high.jpg\t\t\n'
            'EXO_1\tUnloaded_high.jpg\t\t\n', encoding='utf-8')
        Bibles.preloadBibleMapperIndex(self.reference)
        expected = {
            'Single': {'GEN_1:2', 'GEN_1:None'},
            'Verses': {'GEN_1:3', 'GEN_1:4', 'GEN_1:None'},
            'Chapter': {'GEN_2:1', 'GEN_2:2', 'GEN_2:3', 'GEN_2:None'},
            'Across': {'GEN_2:2', 'GEN_2:3', 'GEN_3:1', 'GEN_3:2', 'GEN_2:None', 'GEN_3:None'},
            'Chapters': {'GEN_4:1', 'GEN_4:2', 'GEN_5:1', 'GEN_5:2', 'GEN_5:3', 'GEN_4:None', 'GEN_5:None'},
        }
        actual = defaultdict(set)
        for reference, maps in Bibles.BMM_INDEX.items():
            for name, *_ in maps:
                actual[name].add(reference)
        self.assertEqual(actual, expected)
        self.assertEqual(Bibles.BMM_INDEX['GEN_1:2'],
                         {('Single', 'Single_high.jpg', 'Single_low.jpg', 'Extra')})
        self.assertTrue(Bibles.BMM_INDEX_LOADED)

    def test_get_maps_still_loads_lazily_once(self):
        self.indexFile.write_text('GEN_1:2\tSingle_high.jpg\t\t\n', encoding='utf-8')
        with patch.object(Bibles, 'open', wraps=builtins.open, create=True) as opened:
            for _ in range(2):
                self.assertEqual(Bibles.getBibleMapperMaps(
                    2, 'GEN', '-1', None, None, None, self.reference, None), '')
            opened.assert_called_once_with(self.indexFile, 'rt', encoding='utf-8')
        self.assertEqual(len(Bibles.BMM_INDEX), 2)

    def test_failed_load_does_not_cache_partial_index(self):
        self.indexFile.write_text('GEN_1:2\tSingle_high.jpg\t\t\nMalformed row\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            Bibles.preloadBibleMapperIndex(self.reference)
        self.assertFalse(Bibles.BMM_INDEX_LOADED)
        self.assertFalse(Bibles.BMM_INDEX)
        self.indexFile.write_text('GEN_1:2\tSingle_high.jpg\t\t\n', encoding='utf-8')
        Bibles.preloadBibleMapperIndex(self.reference)
        self.assertTrue(Bibles.BMM_INDEX_LOADED)
        self.assertEqual(len(Bibles.BMM_INDEX), 2)

    def check_chapter_workers(self, indexText, expectedSize):
        self.indexFile.write_text(indexText, encoding='utf-8')
        parentPID = os.getpid()
        books = ['GEN', 'EXO', 'LEV', 'NUM', 'DEU']
        state = SimpleNamespace(
            BBBLinks={'OET':[]}, BBBsToProcess={'OET':books}, TEST_MODE_FLAG=True,
            BibleNames={'OET':'Open English Translation'}, OET_UNFINISHED_WARNING_HTML_PARAGRAPH='')

        def parent_only_open(*args, **kwargs):
            if os.getpid() != parentPID:
                raise AssertionError('A chapter worker tried to reload the map index')
            return builtins.open(*args, **kwargs)

        def chapter_worker(parameters):
            level, folder, BBB = parameters
            assert os.getpid() != parentPID
            assert Bibles.BMM_INDEX_LOADED
            assert len(Bibles.BMM_INDEX) == expectedSize
            assert Bibles.getBibleMapperMaps(
                level, BBB, '-1', None, None, None, self.reference, state) == ''
            return True, BBB, [f'{BBB}.htm']

        with patch.object(BibleOrgSysGlobals, 'alreadyMultiprocessing', False), \
             patch.object(BibleOrgSysGlobals, 'maxProcesses', 2), \
             patch.object(Bibles, 'open', side_effect=parent_only_open, create=True) as opened, \
             patch.object(createChapterPages, '_createOETSideBySideChapterBook_MP', chapter_worker), \
             patch.object(createChapterPages, 'makeBookNavListParagraph', return_value=''), \
             patch.object(createChapterPages, 'makeTop', return_value='<html><body>'), \
             patch.object(createChapterPages, 'makeBottom', return_value='</body></html>'), \
             patch.object(createChapterPages, 'checkHtml', return_value=True):
            filenames = createChapterPages.createOETSideBySideChapterPages(
                2, self.folder / 'byC', self.reference, SimpleNamespace(abbreviation='OET-LV'), state)
            opened.assert_called_once_with(self.indexFile, 'rt', encoding='utf-8')
        self.assertEqual(filenames, [f'{BBB}.htm' for BBB in books] + ['index.htm'])

    @unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(), 'OBD requires fork')
    def test_chapter_workers_inherit_index(self):
        self.check_chapter_workers('GEN_1:2\tSingle_high.jpg\t\t\n', 2)

    @unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(), 'OBD requires fork')
    def test_chapter_workers_inherit_empty_index(self):
        self.check_chapter_workers('EXO_1\tUnloaded_high.jpg\t\t\n', 0)


if __name__ == '__main__':
    unittest.main()
