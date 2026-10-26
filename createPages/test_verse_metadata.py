#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Exercise metadata loading, BOS conversion and both real page-generation loops.

CHANGELOG:
    2026-10-26 Cover original-numbered metadata on English and native OET pages.
"""
from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingError
import Bibles
import test_versification as pageFixtures


NORMAL = ('M','0','C','@')
VITAL = ('V','2','O','David')
HEADER = 'FGRef\tImportance\tTextualIssue\tClarity\tSpeakers\tComment\n'


class VerseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        self.table={'GEN_1:1':NORMAL}
        self.stack.enter_context(patch.object(Bibles,'VERSE_DETAILS_TABLE',self.table))
        self.stack.enter_context(patch.object(Bibles,'VERSE_DETAILS_BOOKS',
            frozenset(Bibles.BOOKLIST_OT39+Bibles.BOOKLIST_NT27)))
        Bibles._verseMetadataMapping.cache_clear()
        self.addCleanup(Bibles._verseMetadataMapping.cache_clear)
        Bibles._reportMissingMetadataBook.cache_clear()
        self.addCleanup(Bibles._reportMissingMetadataBook.cache_clear)

    def render(self,book,chapter,verse,profile='eng'):
        return Bibles.getVerseMetaInfoHtml(book,str(chapter),str(verse),profile)

    def test_english_psalm_uses_original_reference_not_numeric_match(self):
        self.table.update({'PSA_51:10':NORMAL,'PSA_51:12':VITAL})
        html=self.render('PSA',51,10)
        self.assertIn('Original PSA 51:12',html)
        self.assertIn('>vital</span>',html)
        self.assertNotIn('>normal</span>',html)

    def test_nt_verse_count_shift_and_native_oet_order(self):
        self.table.update({'CO2_13:13':VITAL,'CO2_13:14':NORMAL,
                           'PHP_1:16':NORMAL,'PHP_1:17':VITAL})
        self.assertIn('>vital</span>',self.render('CO2',13,14))
        self.assertIn('>vital</span>',self.render('PHP',1,16,'OET-LV'))
        self.assertIn('>normal</span>',self.render('PHP',1,16,'org'))
        self.assertIn('Original PHP 1:17',self.render('PHP',1,16,'OET-LV'))

    def test_chapter_shift(self):
        self.table['MAL_3:23']=VITAL
        self.assertIn('Original MAL 3:23',self.render('MAL',4,5))

    def test_one_page_preserves_every_mapped_metadata_row(self):
        self.table.update({'NUM_25:19':NORMAL,'NUM_26:1':VITAL})
        html=self.render('NUM',26,1)
        self.assertLess(html.index('Original NUM 25:19'),html.index('Original NUM 26:1'))
        self.assertEqual(html.count('Importance to us'),2)
        self.assertIn('>normal</span>',html)
        self.assertIn('>vital</span>',html)

    def test_indivisible_passage_is_explicitly_labelled(self):
        self.table['ACT_19:40']=VITAL
        for verse in (40,41):
            with self.subTest(verse=verse):
                html=self.render('ACT',19,verse)
                self.assertIn('Verse details cover English ACT 19:40–41 together.',html)
                self.assertEqual(html.count('Importance to us'),1)

    def test_editorial_halves_are_found_after_whole_verse_conversion(self):
        self.table.update({'PSA_22:17a':NORMAL,'PSA_22:17b':VITAL})
        html=self.render('PSA',22,16)
        self.assertIn('Original PSA 22:17',html)
        self.assertLess(html.index('Part <b>a</b>'),html.index('Part <b>b</b>'))
        self.assertEqual(html.count('Importance to us'),2)

    def test_numbered_psalm_title_is_metadata_but_editorial_intro_is_not(self):
        self.table.update({'PSA_51:1':NORMAL,'PSA_51:2':VITAL})
        html=self.render('PSA',51,0)
        self.assertIn('Original PSA 51:1',html)
        self.assertIn('Original PSA 51:2',html)
        self.assertEqual(self.render('GEN',1,0),'')
        self.assertEqual(self.render('GEN',-1,0),'')

    def test_reviewed_absence_has_no_numeric_fallback(self):
        self.table['NEH_7:68']=VITAL
        with self.assertLogs(level='WARNING') as log:
            html=self.render('NEH',7,68)
        self.assertIn('Verse details unavailable',html)
        self.assertNotIn('>vital</span>',html)
        self.assertIn('eng NEH 7:68 -> org',log.output[0])

    def test_unsupported_and_ambiguous_bridges_are_reported(self):
        for book,c,v,profile in (('TOB',7,18,'eng'),('ESG',1,1,'eng'),('PSA',9,22,'rsc')):
            with self.subTest(book=book), self.assertLogs(level='WARNING'):
                self.table[f'{book}_{c}:{v}']=VITAL
                html=self.render(book,c,v,profile)
                self.assertIn('Verse details unavailable',html)
                self.assertNotIn('>vital</span>',html)

    def test_bad_reference_and_unknown_source_profile_fail(self):
        with self.assertRaises(VersificationMappingError):
            self.render('PSA',51,99)
        with self.assertRaises(VersificationMappingError):
            self.render('GEN',1,1,'typo')
        with self.assertRaises(TypeError):
            Bibles.getVerseMetaInfoHtml('GEN','1','1')

    def test_book_outside_dataset_is_unavailable_even_if_mapping_exists(self):
        with self.assertLogs(level='WARNING') as log:
            html=self.render('JSA',1,1)
        self.assertIn('outside the metadata dataset',html)
        self.assertIn('org JSA',log.output[0])

    def test_missing_numbered_row_or_incomplete_halves_is_an_error(self):
        with self.assertRaisesRegex(KeyError,'org metadata for PSA_51:12'):
            self.render('PSA',51,10)
        self.table['PSA_22:17a']=NORMAL
        with self.assertRaisesRegex(KeyError,'org metadata for PSA_22:17'):
            self.render('PSA',22,16)


class VerseMetadataLoadingTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'sentenceImportance.tsv'
        self.report=self.path.with_suffix('.build.json')
        self.path.write_text(HEADER+'GEN_1:1\tV\t0\tC\t@\t\n')
        self.report.write_text(json.dumps({'output_versification':'org'}))
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Bibles,'VERSE_DETAILS_TABLE_FILEPATH',self.path))
        self.stack.enter_context(patch.object(Bibles,'VERSE_DETAILS_TABLE',{}))
        self.stack.enter_context(patch.object(Bibles,'VERSE_DETAILS_BOOKS',frozenset()))

    def test_declared_org_table_is_loaded_once(self):
        Bibles.loadVerseDetailsTable()
        self.assertEqual(Bibles.VERSE_DETAILS_TABLE,{'GEN_1:1':('V','0','C','@')})
        self.assertEqual(Bibles.VERSE_DETAILS_BOOKS,{'GEN'})
        self.path.unlink()
        self.report.unlink()
        Bibles.loadVerseDetailsTable() # Forked workers can reuse the inherited table.

    def test_wrong_missing_or_undeclared_profile_is_not_guessed(self):
        for profile in ('eng','OET-LV','Original',None):
            with self.subTest(profile=profile):
                self.report.write_text(json.dumps({'output_versification':profile}))
                with self.assertRaisesRegex(ValueError,'expected sentence metadata'):
                    Bibles.loadVerseDetailsTable()
                self.assertEqual(Bibles.VERSE_DETAILS_TABLE,{})
        self.report.unlink()
        with self.assertRaises(FileNotFoundError):
            Bibles.loadVerseDetailsTable()

    def test_invalid_rows_do_not_leave_a_partially_loaded_cache(self):
        for last in ('GEN_1:1\tM\t0\tC\t@\t\n',
                     'GEN_1:2\tX\t0\tC\t@\t\n','GEN_1:2\tM\t0\tC\n'):
            with self.subTest(last=last):
                self.path.write_text(HEADER+'GEN_1:1\tV\t0\tC\t@\t\n'+last)
                with self.assertRaisesRegex(ValueError,':3: invalid/duplicate'):
                    Bibles.loadVerseDetailsTable()
                self.assertEqual(Bibles.VERSE_DETAILS_TABLE,{})


class VerseMetadataPageTests(unittest.TestCase):
    def test_both_page_loops_render_mapped_metadata_from_the_actual_database(self):
        for fixtureClass in (pageFixtures.ParallelPageTests,pageFixtures.VerseListPageTests):
            with self.subTest(builder=fixtureClass.builder):
                fixture=fixtureClass()
                fixture.setUp()
                try:
                    fixture.namespace['getVerseMetaInfoHtml']=Bibles.getVerseMetaInfoHtml
                    fixture.load('MAL','\\c 3\n\\p\n'+''.join(
                        f'\\v {v} Native verse {v}.\n' for v in range(1,25)))
                    fixture.runBook('MAL')
                    html=(fixture.output/'MAL/C4V5.htm').read_text()
                    self.assertIn('Original MAL 3:23',html)
                    self.assertIn('Importance to us',html)
                    self.assertIn('Native verse 23.',html)
                finally:
                    fixture.doCleanups()

    def test_both_page_loops_pass_a_non_english_navigation_profile(self):
        for fixtureClass in (pageFixtures.ParallelPageTests,pageFixtures.VerseListPageTests):
            with self.subTest(builder=fixtureClass.builder):
                fixture=fixtureClass()
                fixture.setUp()
                try:
                    fixture.state.navigationVersification='OET-LV'
                    fixture.namespace['getVerseMetaInfoHtml']=Bibles.getVerseMetaInfoHtml
                    fixture.namespace['navigationVersification']=lambda name: SimpleNamespace(
                        getNumChapters=lambda book:1,getNumVerses=lambda book,c:17)
                    fixture.load('PHP','\\c 1\n\\p\n'+''.join(
                        f'\\v {v} Native verse {v}.\n' for v in range(1,18)))
                    fixture.runBook('PHP')
                    html=(fixture.output/'PHP/C1V16.htm').read_text()
                    self.assertIn('Original PHP 1:17',html)
                    self.assertIn('Native verse 17.',html)
                finally:
                    fixture.doCleanups()

    def test_regenerated_psalm_database_displays_the_correct_importance(self):
        html=Bibles.getVerseMetaInfoHtml('PSA','51','10','eng')
        self.assertIn('Original PSA 51:12',html)
        self.assertIn('>important</span>',html)
        self.assertNotIn('>normal</span>',html)


if __name__ == '__main__':
    unittest.main()
