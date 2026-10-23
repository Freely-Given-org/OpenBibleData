#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise both complete page builders with all ten derived editions.

Use real BOS Bible entries, the Rust HTML renderer and the real word tables.
Only unrelated site chrome, maps and study-note resources are replaced. Files
are built in temporary directories; no production output/settings are changed.

CHANGELOG:
    2026-10-21 Compare uncached/cold/warm pages and require zero warm substitutions.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.USFMBible import USFMBible
import createParallelVersePages as parallelPages
import createVerseListPages as listPages
from settings import State
import substitutedVersions as cache
import Bibles


class SubstitutedPageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = State()
        self.state.BibleVersions = [*cache.SUBSTITUTED_VERSIONS, 'UTN']
        self.state.TEST_VERSIONS_ONLY = cache.SUBSTITUTED_VERSIONS
        self.state.TEST_MODE_FLAG = True
        self.state.TEST_BOOK_LIST = ['MRK']
        self.state.UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG = False
        self.state.SUBSTITUTED_VERSIONS_FOLDER = self.root / 'cache'
        self.state.BibleLocations = {}
        self.state.preloadedBibles = {'OET-RV': None} # only passed to the disabled map provider
        self.state.booksToLoad = {'OET': []}
        self.state.allBBBs = ['MRK']
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'maxProcesses', 1))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'alreadyMultiprocessing', False))
        for version in cache.SUBSTITUTED_VERSIONS:
            folder = self.root / version
            folder.mkdir()
            if version == 'Luth':
                verses = (r'Im Anfang war das Wort, und das Wort war bei GOtt.',
                          r'JEsus sprach: \add zu ihnen\add* \f + \fr 1:2 \ft Die Gnade und Wahrheit.\f*',
                          r'Und das Licht scheinet in der Finsternis.')
            elif version == 'ClVg':
                verses = (r'In principio erat Verbum, et Verbum erat apud Deum.',
                          r'Et lux in tenebris lucet. \f + \fr 1:2 \fk AUG.\fk* \ft In principio erat Verbum.\f*',
                          r'Et Verbum caro factum est.')
            else:
                verses = (r'In the begynnynge was the worde, and the worde was with God.',
                          r'He sayde \add unto them\add*, loue thy neighbour. \f + \fr 1:2 \ft An olde note.\f*',
                          r'And the light shineth in darknesse.')
            (folder / '41MRK.usfm').write_text('\\id MRK\n\\h Mark\n\\c 1\n' +
                '\n'.join(f'\\v {i} {text}' for i, text in enumerate(verses, 1)) + '\n')
            bible = USFMBible(folder, givenAbbreviation=version,
                             versification=self.state.BibleVersifications[version])
            bible.loadBooks()
            bible._OBDSourceManifest = cache.sourceManifest(folder)
            self.state.BibleLocations[version] = folder
            self.state.preloadedBibles[version] = bible
        for module in (parallelPages, listPages):
            self.stack.enter_context(patch.object(module, 'state', self.state))
            originalPassage = module.parallelVersePassage
            def passage(version, bible, reference, state, chapterMap, original=originalPassage):
                # The real Wycliffe XML has no USFM book-header div. Its page
                # branch deliberately rejects such headers, so omit this fixture's.
                if version == 'Wycl' and reference[1] == '-1':
                    raise KeyError(reference)
                return original(version, bible, reference, state, chapterMap)
            self.stack.enter_context(patch.object(module, 'parallelVersePassage', side_effect=passage))
            self.stack.enter_context(patch.object(module, 'navigationBookList', return_value=['MRK']))
            self.stack.enter_context(patch.object(module, 'navigationVersification', return_value=
                SimpleNamespace(getNumChapters=lambda b: 1, getNumVerses=lambda b, c: 3)))
            self.stack.enter_context(patch.object(module, 'makeTop', return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            self.stack.enter_context(patch.object(module, 'makeBottom', return_value='</body></html>'))
            for function in ('getVerseMetaInfoHtml', 'formatTyndaleBookIntro', 'formatTyndaleNotes',
                             'getFormattedSILOpenTranslationNotes', 'formatUnfoldingWordTranslationNotes',
                             'getBibleMapperMaps', 'getOpenBibleImages'):
                if hasattr(module, function):
                    self.stack.enter_context(patch.object(module, function,
                        return_value='<p>Metadata</p>' if function == 'getVerseMetaInfoHtml' else ''))

    def render(self, label, *, enabled=True, processes=1):
        self.state.CACHE_SUBSTITUTED_VERSIONS_FLAG = enabled
        self.state.__dict__.pop('substitutedVersions', None)
        destination = self.root / label
        with patch.object(BibleOrgSysGlobals, 'maxProcesses', processes):
            parallelPages.createParallelVersePages(1, destination / 'par', self.state)
            listPages.createVerseListPages(1, destination / 'lst', self.state)
        files = {str(path.relative_to(destination)): path.read_bytes()
                 for path in destination.rglob('*.htm')}
        return files, self.state.substitutedVersions

    def test_both_page_families_identical_and_warm_run_performs_zero_substitutions(self):
        baseline, uncached = self.render('uncached', enabled=False)
        cold, editions = self.render('cold')
        self.assertGreater(uncached.substitutions, 0)
        self.assertGreater(editions.substitutions, 0)
        self.assertGreater(editions.hits, 0) # verse-list reuses parallel results immediately
        self.assertEqual(cold, baseline)
        for version in cache.SUBSTITUTED_VERSIONS:
            self.assertTrue(editions.entries[version], version)
        self.assertTrue(any(key[1] == 'footnotes' for key in editions.entries['ClVg']))
        with patch.object(cache, 'substitute', side_effect=AssertionError('warm build substituted')):
            warm, editions = self.render('warm')
        self.assertEqual(warm, baseline)
        self.assertEqual(editions.substitutions, 0)
        self.assertGreater(editions.hits, 0)

    def test_forked_page_builders_persist_and_reuse_every_result(self):
        baseline, _ = self.render('baseline', enabled=False)
        cold, editions = self.render('fork-cold', processes=2)
        self.assertEqual(cold, baseline)
        self.assertGreater(editions.substitutions, 0)
        with patch.object(cache, 'substitute', side_effect=AssertionError('warm worker substituted')):
            warm, editions = self.render('fork-warm', processes=2)
        self.assertEqual(warm, baseline)
        self.assertEqual(editions.substitutions, 0)

    def test_fresh_process_warm_load_never_imports_the_word_tables(self):
        editions = cache.prepareSubstitutedVersions(self.state)
        expected = {version: editions.get(version, 'probe', ' olde text ')
                    for version in cache.SUBSTITUTED_VERSIONS}
        editions.save()
        code = '''
import json, sys
from pathlib import Path
import substitutedVersions as cache
root = Path(sys.argv[1])
import createParallelVersePages, createVerseListPages
editions = cache.SubstitutedVersions(root / 'cache',
    {version: root / version for version in cache.SUBSTITUTED_VERSIONS})
def forbidden(*args, **kwargs):
    raise AssertionError('warm process attempted substitution')
cache.substitute = forbidden
results = {version: editions.get(version, 'probe', ' olde text ')
           for version in cache.SUBSTITUTED_VERSIONS}
assert editions.substitutions == 0
for module in cache._TABLE_MODULES.values():
    assert 'BibleOrgSys.Reference.' + module not in sys.modules
print(json.dumps(results))
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.root)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_source_change_refreshes_original_pickle_before_substituting(self):
        self.state.BibleVersions = ['RV']
        self.state.TEST_VERSIONS_ONLY = ['RV']
        self.state.booksToLoad = {'RV': ['MRK']}
        self.state.BibleLocations['RV'] = str(self.state.BibleLocations['RV'])
        self.state.preloadedBibles = {}
        with patch.object(Bibles, 'WRITE_PICKLES_FLAG', True):
            Bibles.preloadVersions(self.state)
        oldText = self.state.preloadedBibles['RV'].getVerseText(('MRK', '1', '1'))
        cache.getSubstitutedText(self.state, 'RV', 'MRK_1:1', oldText)
        cache.saveSubstitutedVersions(self.state)
        self.state.preloadedBibles = {}
        with patch.object(Bibles, 'preloadVersion', side_effect=AssertionError('unchanged source reloaded')):
            Bibles.preloadVersions(self.state)
        with patch.object(cache, 'substitute', side_effect=AssertionError('unchanged text substituted')):
            cache.getSubstitutedText(self.state, 'RV', 'MRK_1:1', oldText)

        # Deliberately move the date backwards: the old newer-than-pickle check
        # alone would incorrectly keep serving the original parsed Bible.
        source = Path(self.state.BibleLocations['RV']) / '41MRK.usfm'
        stat = source.stat()
        source.write_text(source.read_text().replace('begynnynge', 'seruaunt'))
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns - 10_000_000_000))
        self.state.preloadedBibles = {}
        with patch.object(Bibles, 'preloadVersion', wraps=Bibles.preloadVersion) as reloadSource:
            Bibles.preloadVersions(self.state)
            self.assertEqual(reloadSource.call_count, 1)
        newText = self.state.preloadedBibles['RV'].getVerseText(('MRK', '1', '1'))
        self.assertIn('seruaunt', newText)
        self.assertNotEqual(oldText, newText)
        self.assertFalse(self.state.substitutedVersions.entries['RV'])
        cache.getSubstitutedText(self.state, 'RV', 'MRK_1:1', newText)
        self.assertEqual(self.state.substitutedVersions.substitutions, 1)

    def test_original_reload_does_not_mistake_subset_pickles_for_source_books(self):
        folder = Path(self.state.BibleLocations['KJB-1769'])
        (folder / '18-EST.usfm').write_text('\\id EST\n\\h Esther\n\\c 1\n\\v 1 The real Esther source.\n')
        (folder / 'KJB-1769__INT_FRT_EST_PSA_MAT_MRK.OBD_Bible.pickle').write_bytes(b'\x80not USFM')
        self.state.BibleVersions = self.state.TEST_VERSIONS_ONLY = ['KJB-1769']
        self.state.booksToLoad = {'KJB-1769': ['MRK', 'EST']}
        self.state.TEST_BOOK_LIST = ['MRK', 'EST']
        self.state.BibleLocations['KJB-1769'] = str(folder)
        self.state.preloadedBibles = {}
        Bibles.preloadVersions(self.state)
        bible = self.state.preloadedBibles['KJB-1769']
        self.assertIn('real Esther source', bible.getVerseText(('EST', '1', '1')))
        self.assertFalse(any(name.endswith('.pickle') for name in bible.possibleFilenameDict.values()))


if __name__ == '__main__':
    unittest.main()
