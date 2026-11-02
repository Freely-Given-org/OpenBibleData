#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check cached Bible section indexes before the site creates section pages.

CHANGELOG:
    2026-10-26 Cover caches saved after discovery but before section indexing.
"""
from contextlib import ExitStack
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Internals.InternalBibleBook import InternalBibleBook

import Bibles
from createSectionPages import createSectionLists
from settings import State


class CachedSectionIndexTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'maxProcesses', 1))
        for book in ('GEN', 'MRK'):
            (self.root / f'{book}.usfm').write_text(
                f'\\id {book}\n\\h {book}\n\\c 1\n\\s1 Opening section\n'
                '\\p\n\\v 1 First verse.\n\\s1 Next section\n\\p\n\\v 2 Second verse.\n')
        self.bible = USFMBible(self.root, givenAbbreviation='NET', versification='eng')
        self.bible.loadBooks()
        self.bible.discover()
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.ALL_PRODUCTION_BOOKS_FLAG = True
        self.state.TEST_VERSIONS_ONLY = None
        self.state.BibleVersions = ['NET']
        self.state.BibleLocations = {'NET': str(self.root)}
        self.state.booksToLoad = {'NET': ['ALL']}
        self.state.BBBsToProcess = {'NET': ['GEN', 'MRK']}
        self.state.preloadedBibles = {}
        self.state.sectionsLists = {}
        self.state.sectionsListsForSections = {}
        self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = True
        self.state.PICKLE_FILENAME_END = '.OBD_Bible.pickle'
        self.state.CACHE_SUBSTITUTED_VERSIONS_FLAG = False
        self.state.SUBSTITUTED_VERSIONS_FOLDER = self.root / 'derived-cache'

    def loadCache(self):
        with (self.root / 'NET.OBD_Bible.pickle').open('wb') as output:
            pickle.dump(self.bible, output)
        with patch.object(Bibles, 'preloadVersion',
                          side_effect=AssertionError('Cached text must not be reloaded')):
            Bibles.preloadVersions(self.state)
        return self.state.preloadedBibles['NET']

    def checkSections(self, bible):
        createSectionLists(2, bible, self.state)
        for book in ('GEN', 'MRK'):
            self.assertTrue(bible[book]._indexedSectionsFlag)
            headings = [section[5] for section in self.state.sectionsListsForSections['NET'][book]]
            self.assertIn('Opening section', headings)
            self.assertIn('Next section', headings)

    def test_discovered_cache_without_indexes_can_build_section_lists(self):
        self.assertTrue(self.bible.discoveryResults['ALL']['haveSectionHeadings'])
        self.assertFalse(hasattr(self.bible['GEN'], '_SectionIndex'))
        loaded = self.loadCache()
        self.checkSections(loaded)

    def test_partial_cache_rebuilds_only_the_missing_book(self):
        self.bible.makeSectionIndex()
        del self.bible['MRK']._SectionIndex
        # Also exercise an inconsistent old cache whose ready flag survived.
        original = InternalBibleBook._makeBookSectionIndex
        rebuilt = []
        def rebuild(book):
            rebuilt.append(book.BBB)
            return original(book)
        with patch.object(InternalBibleBook, '_makeBookSectionIndex', rebuild), \
                patch.object(BibleOrgSysGlobals, 'debugFlag', True):
            loaded = self.loadCache()
        self.assertEqual(rebuilt, ['MRK'])
        self.checkSections(loaded)

    def test_complete_cache_reuses_existing_indexes(self):
        self.bible.makeSectionIndex()
        with patch.object(InternalBibleBook, '_makeBookSectionIndex',
                          side_effect=AssertionError('Complete indexes must be reused')):
            loaded = self.loadCache()
        self.checkSections(loaded)


if __name__ == '__main__':
    unittest.main()
