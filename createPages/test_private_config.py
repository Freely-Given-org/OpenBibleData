#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check private/public build isolation using synthetic translation fixtures.

CHANGELOG:
    2026-10-23 Cover configuration, source overrides, staging and cache isolation.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from privateConfig import configurePrivateBuild


class PrivateConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / 'privateSettings.toml'
        self.state = SimpleNamespace(
            TEST_MODE_FLAG=True, ALL_PRODUCTION_BOOKS_FLAG=False,
            TEST_BOOK_LIST=['MRK'], TEST_OT_BOOK_LIST=['PSA'], TEST_NT_BOOK_LIST=['MRK'],
            NORMAL_DESTINATION_FOLDER=self.root / 'htmlPages',
            DESTINATION_FOLDER=self.root / 'htmlPages', TEMP_BUILD_FOLDER=self.root / 'buildingHtmlPages',
            SUBSTITUTED_VERSIONS_FOLDER=self.root / 'cache', PICKLE_FILENAME_END='.OBD_Bible.pickle',
            BibleVersions=['BASE', 'QUOTES'], allPossibleBibleVersions=['BASE', 'QUOTES'],
            BibleLocations={'BASE': '/public/source', 'QUOTES': '/public/quotes.tsv'},
            BibleNames={'BASE': 'Public edition', 'QUOTES': 'Quoted edition'},
            BibleLanguages={'BASE': 'EN-UK', 'QUOTES': 'EN-UK'},
            BibleVersifications={'BASE': 'eng', 'QUOTES': 'eng'}, BibleSourceFormats={},
            BibleVersionDecorations={'BASE': ('', '')},
            booksToLoad={'BASE': ['MRK'], 'QUOTES': ['MRK']},
            detailsHtml={version: {'about': 'Public about', 'copyright': 'Public copyright',
                                  'licence': 'Public licence'} for version in ('BASE', 'QUOTES')},
            VERSIONS_WITHOUT_OT=[], VERSIONS_WITHOUT_NT=[], auxilliaryVersions=('OET',),
            selectedVersesOnlyVersions=('QUOTES',), numAllowedSelectedVerses=(20,),
            versionsWithoutTheirOwnPages=('QUOTES',), navigationVersification='eng',
        )

    def configure(self, extra='', *, folder='local-preview', debug=False):
        self.config.write_text(f'destination_folder = "{folder}"\n{extra}', encoding='utf-8')
        configurePrivateBuild(self.state, configPath=self.config, debug=debug)

    def test_production_does_not_even_read_private_configuration(self):
        self.state.TEST_MODE_FLAG = False
        public = deepcopy(vars(self.state))
        with patch.object(Path, 'open', side_effect=AssertionError('read private configuration')):
            configurePrivateBuild(self.state, configPath=self.config)
        self.assertEqual(vars(self.state), public)

    def test_missing_and_malformed_settings_stop_test_build(self):
        with self.assertRaisesRegex(RuntimeError, 'privateSettings.example.toml'):
            configurePrivateBuild(self.state, configPath=self.config)
        self.config.write_text('this is not TOML')
        with self.assertRaisesRegex(ValueError, 'Invalid privateSettings.toml'):
            configurePrivateBuild(self.state, configPath=self.config)

    def test_private_destination_staging_and_caches_are_separate(self):
        original = deepcopy(self.state)
        self.configure()
        self.assertEqual(self.state.DESTINATION_FOLDER, self.root / 'htmlPages/local-preview')
        self.assertFalse(self.state.TEMP_BUILD_FOLDER.is_relative_to(original.TEMP_BUILD_FOLDER))
        self.assertFalse(self.state.TEMP_BUILD_FOLDER.is_relative_to(original.NORMAL_DESTINATION_FOLDER))
        self.assertNotEqual(self.state.PICKLE_FILENAME_END, original.PICKLE_FILENAME_END)
        self.assertNotEqual(self.state.SUBSTITUTED_VERSIONS_FOLDER, original.SUBSTITUTED_VERSIONS_FOLDER)

    def test_unsafe_or_public_destination_is_rejected(self):
        for folder in ('', '.', '..', '../public', '/tmp/output', 'a/b', 'BASE', 'base', 'par'):
            with self.subTest(folder=folder), self.assertRaisesRegex(ValueError, 'destination_folder'):
                self.configure(folder=folder)

    def test_destination_symlink_cannot_alias_public_output(self):
        self.state.NORMAL_DESTINATION_FOLDER.mkdir()
        for folder, target in (('escape', self.root), ('alias', self.state.NORMAL_DESTINATION_FOLDER / 'BASE')):
            (self.state.NORMAL_DESTINATION_FOLDER / folder).symlink_to(target, target_is_directory=True)
            with self.subTest(folder=folder), self.assertRaisesRegex(ValueError, 'symbolic link'):
                self.configure(folder=folder)

    def test_debug_only_build_does_not_enable_private_sources(self):
        self.state.TEST_MODE_FLAG = False
        original = deepcopy(self.state)
        self.configure('[versions.BASE]\nlocation = "/private/source"\nformat = "USX"', debug=True)
        self.assertNotEqual(self.state.DESTINATION_FOLDER, original.DESTINATION_FOLDER)
        self.assertEqual(self.state.BibleLocations, original.BibleLocations)
        self.assertEqual(self.state.BibleSourceFormats, {})

    def test_existing_edition_override_preserves_metadata_and_changes_order(self):
        original = self.state.BibleLocations
        self.configure('[versions.BASE]\nlocation = "/private/source"\nformat = "USX"\nafter = "QUOTES"')
        self.assertEqual(self.state.BibleVersions, ['QUOTES', 'BASE'])
        self.assertEqual(self.state.allPossibleBibleVersions, self.state.BibleVersions)
        self.assertEqual(self.state.BibleLocations['BASE'], '/private/source')
        self.assertEqual(original['BASE'], '/public/source')
        self.assertEqual(self.state.BibleNames['BASE'], 'Public edition')
        self.assertEqual(self.state.BibleSourceFormats['BASE'], 'USX')

    def test_full_private_edition_can_replace_selected_verses(self):
        self.configure('[versions.QUOTES]\nlocation = "/private/full"\nformat = "USFM"\nown_pages = true')
        self.assertNotIn('QUOTES', self.state.selectedVersesOnlyVersions)
        self.assertEqual(self.state.numAllowedSelectedVerses, ())
        self.assertNotIn('QUOTES', self.state.versionsWithoutTheirOwnPages)

    def test_add_new_private_translation_with_all_page_metadata(self):
        self.configure('''[versions.LOCAL]
location = "/private/new"
format = "USFM"
name = "Local edition"
language = "EN-UK"
versification = "eng"
after = "BASE"
testament = "NT"
own_pages = false
[versions.LOCAL.details]
about = "Local about"
copyright = "Local copyright"
licence = "Local licence"
''')
        self.assertEqual(self.state.BibleVersions, ['BASE', 'LOCAL', 'QUOTES'])
        self.assertEqual(self.state.booksToLoad['LOCAL'], ['MRK'])
        self.assertIn('LOCAL', self.state.VERSIONS_WITHOUT_OT)
        self.assertIn('LOCAL', self.state.versionsWithoutTheirOwnPages)
        self.assertEqual(self.state.detailsHtml['LOCAL']['licence'], 'Local licence')
        self.assertEqual(self.state.BibleVersionDecorations['LOCAL'], ('', ''))

    def test_invalid_version_settings_give_context(self):
        cases = (
            ('LOCAL', 'location = "/private/new"\nformat = "USFM"', 'missing'),
            ('BASE', 'location = "/private/new"\nformat = "UNKNOWN"', 'format'),
            ('BASE', 'location = "/private/new"\nformat = "USFM"\nafter = "MISSING"', 'after'),
            ('BASE', 'location = "/private/new"\nformat = "USFM"\nbooks = "MRK"', 'books'),
            ('BASE', 'location = "/private/new"\nformat = "USFM"\nown_pages = "false"', 'own_pages'),
            ('BASE', 'location = "/private/new"\nformat = "USFM"\nunknown = true', 'unsupported'),
            ('par', 'location = "/private/new"\nformat = "USFM"', 'page-folder'),
        )
        for version, definition, message in cases:
            with self.subTest(version=version, message=message), self.assertRaisesRegex(ValueError, message):
                self.configure(f'[versions.{version}]\n{definition}')

    def test_real_source_loaders_accept_private_usfm_and_usx_with_notes(self):
        import Bibles
        from BibleOrgSys import BibleOrgSysGlobals

        usfm = '\\id MRK\n\\h Mark\n\\c 1\n\\p\n\\v 1 Sample verse. \\f + \\fr 1:1 \\ft Local note.\\f*\n'
        usx = '''<?xml version="1.0" encoding="utf-8"?>
<usx version="2.5"><book code="MRK" style="id">Sample</book>
<para style="h">Mark</para><chapter number="1" style="c"/>
<para style="p"><verse number="1" style="v"/>Sample verse. <note caller="+" style="f"><char style="fr">1:1 </char><char style="ft">Local note.</char></note></para></usx>'''
        for sourceFormat, filename, content in (('USFM', '41MRK.usfm', usfm), ('USX', '041MRK.usx', usx)):
            with self.subTest(format=sourceFormat):
                folder = self.root / sourceFormat
                folder.mkdir()
                (folder / filename).write_text(content, encoding='utf-8')
                self.configure(f'[versions.QUOTES]\nlocation = "{folder}"\nformat = "{sourceFormat}"')
                with patch.object(Bibles, 'WRITE_PICKLES_FLAG', False), \
                        patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0):
                    bible = Bibles.preloadVersion('QUOTES', str(folder), self.state)
                self.assertIn('MRK', bible.books)
                entries, _ = bible.getContextVerseData(('MRK', '1', '1'))
                self.assertTrue(any('Local note.' in entry.getOriginalText() for entry in entries))

    def test_real_production_settings_import_ignores_local_file(self):
        import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals

        sourcePath = Path(__file__).with_name('settings.py')
        source = sourcePath.read_text().replace('TEST_MODE_FLAG = True', 'TEST_MODE_FLAG = False', 1)
        namespace = {'__name__': 'production_settings_test', '__file__': str(sourcePath)}
        with patch.object(BibleOrgSysGlobals, 'debugFlag', False), \
                patch.object(Path, 'open', side_effect=AssertionError('read private configuration')):
            exec(compile(source, str(sourcePath), 'exec'), namespace)
        state = namespace['State']
        self.assertEqual(state.DESTINATION_FOLDER, state.NORMAL_DESTINATION_FOLDER)
        self.assertEqual(state.BibleSourceFormats, {})
        self.assertEqual(state.PICKLE_FILENAME_END, '.OBD_Bible.pickle')
        self.assertIsNone(state.DEBUG_DESTINATION_FOLDER_NAME)


if __name__ == '__main__':
    unittest.main()
