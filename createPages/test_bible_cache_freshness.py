#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Keep independent Bible caches fresh according to sources, not other caches.

CHANGELOG:
    2026-10-27 Cover public/private cache coexistence and nested OET-LV sources.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible

import Bibles


class BibleCacheFreshnessTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'debugFlag', False))

    def prepareCache(self, *, testMode=False, version='YLT'):
        folder = self.root / f'{version}-{testMode}' / 'derivedTexts'
        folder.mkdir(parents=True)
        self.state = SimpleNamespace(
            TEST_MODE_FLAG=testMode, ALL_PRODUCTION_BOOKS_FLAG=not testMode,
            TEST_BOOK_LIST=['MRK'], TEST_VERSIONS_ONLY=None,
            PICKLE_FILENAME_END='.OBD_Private_Bible.pickle' if testMode else '.OBD_Bible.pickle',
            BibleVersions=[version], BibleLocations={version: str(folder)},
            BibleVersifications={version: 'eng'}, selectedVersesOnlyVersions=(),
            LOAD_RESOURCES_FROM_PICKLES_FLAG=True, preloadedBibles={},
            CACHE_SUBSTITUTED_VERSIONS_FLAG=False, SUBSTITUTED_VERSIONS_FOLDER=self.root / 'cache',
        )
        if version == 'OET-LV':
            for testament, name in (('OT', 'auto_edited_OT_ESFM'), ('NT', 'auto_edited_VLT_ESFM')):
                sourceFolder = folder / name
                sourceFolder.mkdir()
                self.state.BibleLocations[f'OET-LV-{testament}'] = str(sourceFolder)
        filename = f'{version}__MRK.OBD_Private_Bible.pickle' if testMode else f'{version}.OBD_Bible.pickle'
        bible = Bible(versification='eng')
        bible.name = 'Expected cached edition'
        bible.discoveryResults = {}
        with (folder / filename).open('wb') as output:
            pickle.dump(bible, output)
        os.utime(folder / filename, (1_000_000_100, 1_000_000_100))
        return folder

    def newerFile(self, path):
        path.write_text('Newer source or unrelated cache', encoding='utf-8')
        os.utime(path, (1_000_000_200, 1_000_000_200))

    def checkCacheIsReused(self, version):
        with patch.object(Bibles, 'preloadVersion',
                          side_effect=AssertionError('Unchanged sources must not be reloaded')):
            self.assertEqual(Bibles.preloadVersions(self.state), 1)
        self.assertEqual(self.state.preloadedBibles[version].name, 'Expected cached edition')

    def test_public_and_private_caches_do_not_invalidate_each_other(self):
        for testMode in (False, True):
            with self.subTest(testMode=testMode):
                folder = self.prepareCache(testMode=testMode)
                other = 'YLT.OBD_Bible.pickle' if testMode else 'YLT__MRK.OBD_Private_Bible.pickle'
                self.newerFile(folder / other)
                self.checkCacheIsReused('YLT')

    def test_other_subset_and_derived_pickles_do_not_invalidate_cache(self):
        folder = self.prepareCache()
        for filename in ('YLT__MAT.OBD_Bible.pickle', 'YLT.OBD_Substituted.pickle'):
            self.newerFile(folder / filename)
        self.checkCacheIsReused('YLT')

    def test_newer_source_invalidates_both_cache_variants(self):
        for testMode in (False, True):
            with self.subTest(testMode=testMode):
                folder = self.prepareCache(testMode=testMode)
                self.newerFile(folder / '41MRK.usfm')
                with patch.object(Bibles, 'preloadVersion', side_effect=RuntimeError('Source reload requested')) as loader:
                    with self.assertRaisesRegex(RuntimeError, 'Source reload requested'):
                        Bibles.preloadVersions(self.state)
                loader.assert_called_once_with('YLT', str(folder), self.state)

    def test_nested_oet_lv_pickles_do_not_invalidate_combined_cache(self):
        for testMode in (False, True):
            with self.subTest(testMode=testMode):
                folder = self.prepareCache(testMode=testMode, version='OET-LV')
                other = 'OET-LV.OBD_Bible.pickle' if testMode else 'OET-LV__MRK.OBD_Private_Bible.pickle'
                for name in ('auto_edited_OT_ESFM', 'auto_edited_VLT_ESFM'):
                    self.newerFile(folder / name / other)
                self.checkCacheIsReused('OET-LV')

    def test_newer_nested_oet_lv_source_invalidates_combined_cache(self):
        for testament, filename in (('OT', '01GEN.ESFM'), ('NT', '41MRK.ESFM')):
            with self.subTest(testament=testament):
                # Give each case its own source directory.
                self.prepareCache(testMode=testament == 'NT', version='OET-LV')
                self.newerFile(Path(self.state.BibleLocations[f'OET-LV-{testament}']) / filename)
                with patch.object(Bibles, 'preloadVersion', side_effect=RuntimeError('Source reload requested')) as loader:
                    with self.assertRaisesRegex(RuntimeError, 'Source reload requested'):
                        Bibles.preloadVersions(self.state)
                loader.assert_called_once_with('OET-LV', self.state.BibleLocations['OET-LV-OT'], self.state)


if __name__ == '__main__':
    unittest.main()
