#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Derived-edition persistence, invalidation and fork-worker regression tests.

CHANGELOG:
    2026-10-21 Verify ten editions, zero warm substitutions and automatic rebuilds.
"""
import multiprocessing
import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import substitutedVersions as cache


def _worker(editions, reference):
    editions.startWorker()
    editions.get('Wycl', reference, 'olde text')
    return editions.workerResult()


class SubstitutedVersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.locations = {}
        for version in cache.SUBSTITUTED_VERSIONS:
            source = self.root / version / 'MRK.usfm'
            source.parent.mkdir()
            source.write_text('original')
            self.locations[version] = source.parent
        self.tables = {}
        for name in ('OldBiblicalEnglish', 'LutherGermanToEnglish', 'VulgateLatinToEnglish'):
            path = self.root / f'{name}.py'
            path.write_text('word table')
            self.tables[name] = path
        self.addCleanup(patch.stopall)
        patch.object(cache, 'wordTablePath', side_effect=lambda v: self.tables[cache._TABLE_MODULES[v]]).start()
        self.converter = patch.object(cache, 'substitute',
            side_effect=lambda v, text, options: f'{v}: {text} ({options})').start()

    def editions(self, **options):
        return cache.SubstitutedVersions(self.root / 'cache', self.locations, **options)

    def populate(self):
        editions = self.editions()
        for version in self.locations:
            editions.get(version, 'MRK_1:1', 'olde text')
        editions.save()
        return editions

    def changeDate(self, path, *, backwards=False):
        stat = path.stat()
        delta = -10_000_000_000 if backwards else 10_000_000_000
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + delta))

    def test_all_ten_warm_editions_are_identical_with_zero_substitutions(self):
        cold = self.populate()
        self.assertEqual(cold.substitutions, 10)
        self.assertEqual(len(list((self.root / 'cache').glob('*.pickle'))), 10)
        self.converter.side_effect = AssertionError('unchanged build attempted a substitution')
        warm = self.editions()
        before = {p: p.stat().st_mtime_ns for p in (self.root / 'cache').glob('*.pickle')}
        for version in self.locations:
            self.assertEqual(warm.get(version, 'MRK_1:1', 'olde text'),
                             next(iter(cold.entries[version].values())))
        warm.save()
        self.assertEqual(warm.substitutions, 0)
        self.assertEqual(warm.hits, 10)
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})

    def test_each_table_invalidates_only_its_editions(self):
        for name, path in self.tables.items():
            with self.subTest(table=name):
                self.populate()
                self.changeDate(path)
                rebuilt = self.editions()
                for version in self.locations:
                    rebuilt.get(version, 'MRK_1:1', 'olde text')
                self.assertEqual(rebuilt.substitutions, 8 if name == 'OldBiblicalEnglish' else 1)
                rebuilt.save()
                self.assertEqual(self.editions().entries, rebuilt.entries)

    def test_source_date_in_either_direction_invalidates_only_that_version(self):
        for backwards in (False, True):
            with self.subTest(backwards=backwards):
                self.populate()
                self.changeDate(self.locations['Wycl'] / 'MRK.usfm', backwards=backwards)
                rebuilt = self.editions()
                for version in self.locations:
                    rebuilt.get(version, 'MRK_1:1', 'olde text')
                self.assertEqual(rebuilt.substitutions, 1)

    def test_added_deleted_and_nested_sources_invalidate(self):
        self.populate()
        nested = self.locations['ClVg'] / 'extra'
        nested.mkdir()
        source = nested / 'MAT.usfm'
        source.write_text('another book')
        rebuilt = self.editions()
        self.assertFalse(rebuilt.entries['ClVg'])
        rebuilt.get('ClVg', 'MRK_1:1', 'olde text')
        rebuilt.save()
        source.unlink()
        self.assertFalse(self.editions().entries['ClVg'])

    def test_source_size_change_with_preserved_date_invalidates(self):
        self.populate()
        source = self.locations['Luth'] / 'MRK.usfm'
        stat = source.stat()
        source.write_text('a longer source')
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertFalse(self.editions().entries['Luth'])

    def test_single_file_sources_and_missing_sources(self):
        self.locations['Luth'] /= 'MRK.usfm'
        self.populate()
        self.changeDate(self.locations['Luth'])
        self.assertFalse(self.editions().entries['Luth'])
        self.locations['Luth'].unlink()
        with self.assertRaises(FileNotFoundError):
            self.editions()

    def test_generated_files_do_not_invalidate_their_own_sources(self):
        original = cache.sourceManifest(self.locations['Wycl'])
        for name in ('Wycl.OBD_Bible.pickle', 'run.log', 'MRK.usfm.bak', '.hidden'):
            (self.locations['Wycl'] / name).write_text('generated')
        self.assertEqual(original, cache.sourceManifest(self.locations['Wycl']))

    def test_reference_input_options_and_footnotes_are_separate_variants(self):
        editions = self.editions()
        calls = [('MRK_1:1', 'text', 'olde text', False),
                 ('MRK_1:1', 'text', '<i>olde text</i>', False),
                 ('MRK_1:1', 'text', 'olde text', True),
                 ('MRK_1:1', 'footnotes', 'olde text', False),
                 ('MRK_1:2', 'text', 'olde text', False)]
        expected = [editions.get('Wycl', ref, text, kind=kind, allowOptions=options)
                    for ref, kind, text, options in calls]
        editions.save()
        warm = self.editions()
        self.converter.side_effect = AssertionError('unexpected miss')
        self.assertEqual(expected, [warm.get('Wycl', ref, text, kind=kind, allowOptions=options)
                                    for ref, kind, text, options in calls])
        self.assertEqual(warm.substitutions, 0)

    def test_partial_build_adds_missing_references_without_losing_old_ones(self):
        self.populate()
        partial = self.editions()
        partial.get('Wycl', 'MAT_24:50', 'new book')
        partial.save()
        self.assertEqual(len(self.editions().entries['Wycl']), 2)

    def test_corrupt_incompatible_or_invalid_payload_rebuilds(self):
        for payload in (b'broken', b'', pickle.dumps({'format': -1}),
                        pickle.dumps({'format': cache.FORMAT_VERSION, 'entries': {1: None}})):
            with self.subTest(payload=payload):
                editions = self.populate()
                editions.path('Wycl').write_bytes(payload)
                with self.assertLogs(level='WARNING'):
                    rebuilt = self.editions()
                rebuilt.get('Wycl', 'MRK_1:1', 'olde text')
                self.assertEqual(rebuilt.substitutions, 1)

    def test_cache_bypass_and_forced_rebuild(self):
        self.populate()
        disabled = self.editions(enabled=False)
        disabled.get('Wycl', 'MRK_1:1', 'olde text')
        disabled.get('Wycl', 'MRK_1:1', 'olde text')
        self.assertEqual(disabled.substitutions, 2)
        self.assertFalse(disabled.entries['Wycl'])
        forced = self.editions(load=False)
        forced.get('Wycl', 'MRK_1:1', 'olde text')
        self.assertEqual(forced.substitutions, 1)
        forced.save()
        self.assertTrue(self.editions().entries['Wycl'])

    def test_failed_atomic_write_keeps_previous_edition(self):
        editions = self.populate()
        before = editions.path('Wycl').read_bytes()
        editions.get('Wycl', 'MRK_1:2', 'more text')
        with patch.object(cache.os, 'replace', side_effect=OSError('interrupted write')):
            with self.assertRaises(OSError):
                editions.save()
        self.assertEqual(before, editions.path('Wycl').read_bytes())
        self.assertFalse(list(editions.folder.glob('*.tmp')))

    def test_mid_build_source_change_cannot_publish_stale_results(self):
        editions = self.editions()
        editions.get('Wycl', 'MRK_1:1', 'olde text')
        self.changeDate(self.locations['Wycl'] / 'MRK.usfm')
        with self.assertRaisesRegex(RuntimeError, 'changed during the build'):
            editions.save()
        self.assertFalse(editions.path('Wycl').exists())

    def test_independent_builds_merge_additions(self):
        first, second = self.editions(), self.editions()
        first.get('Wycl', 'MRK_1:1', 'olde text')
        second.get('Wycl', 'MRK_1:2', 'other text')
        first.save()
        second.save()
        self.assertEqual(len(self.editions().entries['Wycl']), 2)

    def test_forked_workers_return_additions_and_warm_workers_do_no_substitution(self):
        editions = self.editions()
        with multiprocessing.get_context('fork').Pool(2) as pool:
            results = pool.starmap(_worker, [(editions, 'MRK_1:1'), (editions, 'MRK_1:2')])
        for result in results:
            editions.mergeWorkerResult(result)
        editions.save()
        self.assertEqual(editions.substitutions, 2)
        self.converter.side_effect = AssertionError('warm worker attempted a substitution')
        warm = self.editions()
        with multiprocessing.get_context('fork').Pool(2) as pool:
            results = pool.starmap(_worker, [(warm, 'MRK_1:1'), (warm, 'MRK_1:2')])
        for result in results:
            warm.mergeWorkerResult(result)
        self.assertEqual((warm.hits, warm.substitutions), (2, 0))


if __name__ == '__main__':
    unittest.main()
