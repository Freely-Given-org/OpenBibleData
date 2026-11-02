#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""OET-LV three-folder loading and DC word/page regressions.

CHANGELOG:
    2026-10-29 Cover DC-only books, separate word tables, and older caches.
    2026-10-29 Cover RV source aliases and refreshing caches that can omit Greek Daniel.
    2026-10-31 Check native verse links, grouped previews and unambiguous Greek lemma navigation.
    2026-10-31 Cover draft colour agreement, disabled colours, parallel keys and unparsed Latin.
    2026-11-01 Keep the draft key below the last coloured version, ahead of uncoloured versions.
"""
from contextlib import ExitStack
from pathlib import Path
import os
import pickle
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from openbibledata_rust import convertVerseEntryListToHtml, livenOETWordLinks
import Bibles
from navigation import bookNavigationOrder
from oetDeuterocanon import createDCWordPages, dcGrammaticalColourKey, DC_WORD_TABLE, DC_COLUMN_HEADERS
from settings import State


class OETDCTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Bibles, 'WRITE_PICKLES_FLAG', False))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'maxProcesses', 1))
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.ALL_PRODUCTION_BOOKS_FLAG = True
        self.state.TEST_VERSIONS_ONLY = None
        self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = False
        self.state.BibleVersions = ['OET-LV']
        self.state.booksToLoad = {'OET-LV': ['GEN','TOB','PSS','ODE','JHN'], 'OET': []}
        self.state.BibleLocations = {'OET-LV': str(self.root)}
        self.state.preloadedBibles = {}
        self.state.sectionsLists = {}
        self.state.sectionsListsForHeaders = {'OET-RV': {}}
        self.state.sectionsListsForSections = {}
        self.table = [DC_COLUMN_HEADERS]
        for number, BBB in enumerate(('TOB','PSS','ODE'), 1):
            self.table.append('\t'.join((f'{BBB}_1:1w1','λόγος','λόγος','N-NSM','word','word',
                'form-lexical','STEPBible','[]',f'{BBB}_1:1','source.xml','',' ')))
        for part, books in (('OT', ('GEN',)), ('DC', ('TOB','PSS','ODE')), ('NT', ('JHN',))):
            folder = self.root / f'auto_edited_{part}_ESFM'
            folder.mkdir()
            self.state.BibleLocations[f'OET-LV-{part}'] = str(folder)
            for BBB in books:
                tableName = f'OET-LV_{part}_word_table.tsv'
                content = (f'\\id {"ODA" if BBB == "ODE" else BBB}\n\\rem ESFM v0.6 {BBB}\n\\rem WORDTABLE {tableName}\n'
                    f'\\h {BBB}\n\\mt1 {BBB}\n\\c 1\n\\p\n\\v 1 ')
                content += f'word¦{("TOB","PSS","ODE").index(BBB)+1}.\n' if part == 'DC' else 'Example.\n'
                (folder / f'OET-LV_{BBB}.ESFM').write_text(content, encoding='utf-8')
            (folder / tableName).write_text('\n'.join(self.table) if part == 'DC' else 'Ref\n', encoding='utf-8')
            if part == 'OT':
                (folder / 'OET-LV_OT_lemma_table.tsv').write_text('Lemma\tGloss\n',encoding='utf-8')

    def load(self):
        self.assertEqual(Bibles.preloadVersions(self.state), 1)
        self.bible = self.state.preloadedBibles['OET-LV']
        for name,table in tuple(self.bible.ESFMWordTables.items()):
            if table is None: self.bible.loadESFMWordFile(name)
        self.state.OETRefData = {'word_tables': dict(self.bible.ESFMWordTables)}
        self.state.allBBBs = set(self.bible.books)
        self.state.BBBsToProcess = {'OET-LV': bookNavigationOrder(self.bible.books, 'OET-LV')}
        self.state.BBBLinks = {'OET-LV': [f'<a href="{BBB}.htm#Top">{BBB}</a>' for BBB in self.bible.books]}
        return self.bible

    def test_merges_all_three_sources_and_preserves_dc_table(self):
        bible = self.load()
        self.assertEqual(set(bible.books), {'GEN','TOB','PSS','ODE','JHN'})
        self.assertEqual(bible.ESFMWordTables[DC_WORD_TABLE], self.table)
        self.assertEqual(len(bible.ESFMWordTables), 3)
        for book in bible:
            self.assertIs(book.containerBibleObject, bible)
        self.assertEqual(bookNavigationOrder(bible.books, 'OET-LV'), ['GEN','TOB','PSS','ODE','JHN'])

    def test_subset_does_not_pull_in_unrequested_dc_books(self):
        self.state.booksToLoad['OET-LV'] = ['GEN','TOB','JHN']
        self.assertEqual(set(self.load().books), {'GEN','TOB','JHN'})

    def test_production_selection_includes_all_seventeen_dc_books(self):
        self.assertEqual(len(State.OET_LV_BOOK_LIST), 83)
        self.assertEqual(len(State.OET_LV_DC_BOOK_LIST), 17)
        self.assertTrue(set(State.OET_LV_DC_BOOK_LIST) <= set(State.OET_LV_BOOK_LIST))
        self.assertEqual(set(bookNavigationOrder(State.OET_LV_BOOK_LIST, 'OET-LV')), set(State.OET_LV_BOOK_LIST))
        self.assertIn('LAO', State.OET_LV_DC_BOOK_LIST)
        self.assertIn('LAO', State.OET_RV_DC_BOOK_LIST)
        self.assertEqual(State.OET_BOOK_ORDER[State.OET_BOOK_ORDER.index('COL')+1], 'LAO')
        self.assertTrue({'PSS','ODE'} <= set(State.OET_LV_DC_BOOK_LIST) - set(State.OET_RV_DC_BOOK_LIST))
        self.assertTrue(set(State.OET_RV_DC_BOOK_LIST + State.OET_LV_DC_BOOK_LIST)
            <= set(State.OET_APOCRYPHA_BOOK_ORDER) | {'LAO'})

    def test_explicit_source_aliases_load_greek_esdras_and_daniel(self):
        folder = Path(self.state.BibleLocations['OET-LV-DC'])
        for source in ('ES1','DAG'):
            BBB = State.OET_SOURCE_BOOK_ALIASES[source]
            (folder / f'OET-LV_{source}.ESFM').write_text(
                f'\\id {"1ES" if source == "ES1" else source}\n\\rem ESFM v0.6 {source}\n'
                f'\\h {source}\n\\mt1 {source}\n\\c 1\n\\p\n\\v 1 Example.\n')
            self.state.booksToLoad['OET-LV'].append(BBB)
        bible = self.load()
        self.assertTrue({'GES','DNG'} <= set(bible.books))
        self.assertFalse({'ES1','DAG'} & set(bible.books))

    def prepareRV(self):
        folder = self.root / 'ReadersVersion'
        folder.mkdir()
        for source, usfm in (('ES1','1ES'), ('ES2','2ES'), ('DAG','DAG'), ('PS2','PS2')):
            (folder / f'OET-RV_{source}.ESFM').write_text(
                f'\\id {usfm}\n\\h {source}\n\\mt1 {source}\n'
                '\\is1 Introduction\n\\ip Example introduction.\n'
                '\\c 1\n\\s1 Example section\n\\p\n\\v 1 Example verse.\n')
        self.state.BibleVersions = ['OET-RV']
        self.state.BibleLocations = {'OET-RV': str(folder)}
        self.state.booksToLoad = {'OET-RV': ['ALL']}
        return folder

    def test_rv_production_selection_and_loading_include_all_four_omissions(self):
        self.prepareRV()
        self.assertEqual(len(State.OET_RV_DC_BOOK_LIST), 16)
        self.assertTrue({'GES','LES','DNG','PS2'} <= set(State.OET_RV_DC_BOOK_LIST))
        Bibles.preloadVersions(self.state)
        self.assertEqual(set(self.state.preloadedBibles['OET-RV'].books), {'GES','LES','DNG','PS2'})

    def test_old_rv_cache_reloads_with_explicit_book_identities(self):
        folder = self.prepareRV()
        old = ESFMBible(folder, givenAbbreviation='OET-RV')
        old.discoveryResults = {}
        with (folder / f'OET-RV{self.state.PICKLE_FILENAME_END}').open('wb') as output:
            pickle.dump(old, output)
        self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = True
        Bibles.preloadVersions(self.state)
        self.assertEqual(set(self.state.preloadedBibles['OET-RV'].books), {'GES','LES','DNG','PS2'})
        self.assertEqual(self.state.preloadedBibles['OET-RV']._OBDSourceBookAliases, State.OET_SOURCE_BOOK_ALIASES)

    def test_newer_dc_source_or_table_invalidates_combined_cache(self):
        bible = self.load()
        cachePath = self.root / f'OET-LV{self.state.PICKLE_FILENAME_END}'
        self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = True
        for filename in ('OET-LV_PSS.ESFM', DC_WORD_TABLE):
            with self.subTest(source=filename):
                with cachePath.open('wb') as output:
                    pickle.dump(bible, output)
                source = Path(self.state.BibleLocations['OET-LV-DC']) / filename
                timestamp = cachePath.stat().st_mtime + 10
                os.utime(source, (timestamp, timestamp))
                with patch.object(Bibles, 'preloadVersion', side_effect=RuntimeError('Reload requested')):
                    with self.assertRaisesRegex(RuntimeError, 'Reload requested'):
                        Bibles.preloadVersions(self.state)
                os.utime(source, (1, 1))

    def test_old_cache_reloads_even_when_sources_are_older(self):
        old = ESFMBible(self.state.BibleLocations['OET-LV-OT'], givenAbbreviation='OET-LV')
        old.discoveryResults = {}
        with (self.root / f'OET-LV{self.state.PICKLE_FILENAME_END}').open('wb') as output:
            pickle.dump(old, output)
        self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = True
        self.assertIn('PSS', self.load())

    def test_dc_words_link_to_generated_details_without_rv(self):
        bible = self.load()
        createDCWordPages(2, self.root / 'ref' / 'DCWrd', self.state)
        for number, BBB in enumerate(('TOB','PSS','ODE'), 1):
            with self.subTest(book=BBB):
                entries, context = bible.getContextVerseData((BBB,'1','1'))
                rendered = convertVerseEntryListToHtml(2, 'OET-LV', (BBB,'1','1'), 'verse',
                    context, entries, basicOnly=True, state=self.state, livenWordLinks=True)
                expected = f'ref/DCWrd/{BBB}_C1.htm#W{number}'
                self.assertIn(expected, rendered)
                self.assertIn('class="grkNom"', rendered)
                self.assertIn('Draft grammatical colour:', rendered)
                self.assertNotIn('¦', rendered)
                self.assertNotIn('ref/HebWrd/', rendered)
                linked = livenOETWordLinks(2, bible, (BBB,'1','1'), entries, self.state)
                self.assertTrue(any(expected in entry.getOriginalText() for entry in linked))
                self.assertTrue(any('class="grkNom"' in entry.getOriginalText() for entry in linked))
                plain = convertVerseEntryListToHtml(2, 'OET-LV', (BBB,'1','1'), 'verse',
                    context, entries, basicOnly=True, state=self.state, livenWordLinks=True,
                    colouriseWordClasses=False)
                self.assertIn(expected, plain)
                self.assertNotIn('class="grk', plain)
                plainEntries = livenOETWordLinks(2, bible, (BBB,'1','1'), entries, self.state,
                    colouriseWordClasses=False)
                self.assertFalse(any('class="grk' in entry.getOriginalText() for entry in plainEntries))
                details = (self.root / 'ref' / 'DCWrd' / f'{BBB}_C1.htm').read_text()
                self.assertIn(f'id="W{number}"', details)
                self.assertIn('λόγος', details)
                self.assertNotIn('OET-RV/by', details)
                self.assertIn(f'OET-LV/byC/{BBB}_C1.htm#C1V1',details)
                self.assertIn('id="V1"',details)
                self.assertIn('Show passage in OET',details)
                ids=re.findall(r'\bid="([^"]+)"',details)
                self.assertEqual(len(ids),len(set(ids)))

    def test_dc_lemma_links_require_one_exact_available_greek_match(self):
        from oetDeuterocanon import dcLemmaLinks
        self.load()
        self.state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'] = ['header',
            '\t'.join(('JHN_1:1w1','λόγος','logos','λόγος','word','message','','1','30560','N','','')),
            '\t'.join(('JHN_1:1w2','τίς','tis1','τίς','who','who','','1','51010','R','','')),
            '\t'.join(('JHN_1:1w3','τίς','tis2','τίς','what','what','','1','51010','R','',''))]
        self.state.UBS_GNT_DATA=[dict(MainId='1',Lemma='λόγος'),dict(MainId='2',Lemma='τίς'),dict(MainId='3',Lemma='τίς')]
        links=dcLemmaLinks(2,self.state)
        self.assertIn('ref/GrkLem/logos.htm#Top',links['λόγος'])
        self.assertIn('UBS/Grk/',links['λόγος'])
        self.assertNotIn('τίς',links)
        createDCWordPages(2,self.root/'ref/DCWrd',self.state)
        self.assertIn('ref/GrkLem/logos.htm#Top',(self.root/'ref/DCWrd/TOB_C1.htm').read_text())

    def test_draft_colour_key_lists_only_present_colours_and_reuses_control(self):
        text = '<a class="grkGen" href="word.htm">word</a><a class="grkVrb">speaks</a>'
        key = dcGrammaticalColourKey(text)
        self.assertIn('Draft grammatical colours', key)
        self.assertIn('grammar in this passage has not been reviewed', key)
        self.assertIn('khaki', key)
        self.assertIn('pink', key)
        self.assertNotIn('nominative', key)
        self.assertEqual(key.count('id="coloursButton"'), 1)
        self.assertNotIn('id="coloursButton"', dcGrammaticalColourKey(text+'<button id="coloursButton">C</button>'))
        self.assertEqual(dcGrammaticalColourKey('<a href="word.htm">word</a>'), '')

    def test_parallel_pages_explain_colours_without_colouring_ambiguous_or_missing_analyses(self):
        import createParallelVersePages as pages
        folder = Path(self.state.BibleLocations['OET-LV-DC'])
        for verse, morphology in ((2,'T-ASN | T-NSN | T-VSN'), (3,'')):
            self.table.append('\t'.join((f'TOB_1:{verse}w1','τό','ὁ',morphology,'the','the',
                'form-lexical','STEPBible','[]',f'TOB_1:{verse}','source.usfm','','')))
        self.table.append('\t'.join(('TOB_1:2w2','λόγου','λόγος','N-GSM','word','word',
            'form-lexical','STEPBible','[]','TOB_1:2','source.usfm','','')))
        (folder/DC_WORD_TABLE).write_text('\n'.join(self.table)+'\n')
        with (folder/'OET-LV_TOB.ESFM').open('a') as output:
            output.write('\\v 2 the¦4.\n\\v 3 the¦5.\n')
        self.load()
        versions = ['OET-RV','OET-LV','BrTr']
        for version, text in (
            ('OET-RV', '\\v 1 word¦1.\n\\v 2 word¦6.\n\\v 3 Plain RV text.\n'),
            ('BrTr', '\\v 1 Plain Brenton text.\n\\v 2 Plain Brenton text.\n\\v 3 Plain Brenton text.\n'),
        ):
            source = self.root/version
            source.mkdir()
            (source/f'{version}_TOB.ESFM').write_text('\\id TOB\n\\h Tobit\n\\mt1 Tobit\n'
                '\\is1 Introduction\n\\ip Example introduction.\n\\c 1\n\\p\n'+text)
            bible = ESFMBible(source, givenAbbreviation=version,
                versification=self.state.BibleVersifications[version])
            bible.loadBooks()
            bible.ESFMWordTables = dict(self.bible.ESFMWordTables)
            self.state.preloadedBibles[version] = bible
        self.state.TEST_VERSIONS_ONLY = versions
        self.state.UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG = False
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.state.possibleUnmatchedProperNames = set()
        self.state.versionComments = {}
        with ExitStack() as stack:
            stack.enter_context(patch.object(pages, 'navigationVersification', return_value=
                SimpleNamespace(getNumChapters=lambda b: 1, getNumVerses=lambda b,c: 3)))
            stack.enter_context(patch.object(pages, 'makeTop', return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            stack.enter_context(patch.object(pages, 'makeBottom', return_value='</body></html>'))
            stack.enter_context(patch.object(pages, 'findSectionNumber', return_value=0))
            for function in ('getVerseMetaInfoHtml', 'formatTyndaleBookIntro', 'formatTyndaleNotes',
                             'getFormattedSILOpenTranslationNotes', 'formatUnfoldingWordTranslationNotes',
                             'getBibleMapperMaps', 'getOpenBibleImages'):
                stack.enter_context(patch.object(pages, function, return_value=''))
            pages.createParallelVersePagesForBook(1, self.root/'par', 'TOB',
                ['<a title="Tobit" href="../TOB.htm#Top">TOB</a>'], versions, self.state)
        first = (self.root/'par/TOB/C1V1.htm').read_text()
        self.assertIn('class="grkNom"', first)
        self.assertEqual(first.count('id="coloursButton"'), 1)
        self.assertEqual(first.count('<b>Draft grammatical colours</b>'), 1)
        paragraphs = re.findall(r'<p\b[^>]*>.*?</p>', first, re.DOTALL)
        keyIndex = next(i for i,p in enumerate(paragraphs) if '<b>Draft grammatical colours</b>' in p)
        self.assertTrue(paragraphs[keyIndex-1].startswith('<p id="OET-LV"'))
        self.assertTrue(paragraphs[keyIndex+1].startswith('<p id="BrTr"'))
        for verse in (2,3):
            page = (self.root/f'par/TOB/C1V{verse}.htm').read_text()
            self.assertIn(f'DCWrd/TOB_C1.htm#W{verse+2}', page)
            paragraphs = re.findall(r'<p\b[^>]*>.*?</p>', page, re.DOTALL)
            lvParagraph = next(p for p in paragraphs if p.startswith('<p id="OET-LV"'))
            self.assertNotIn('class="grk', lvParagraph)
            if verse == 2:
                keyIndex = next(i for i,p in enumerate(paragraphs) if '<b>Draft grammatical colours</b>' in p)
                self.assertTrue(paragraphs[keyIndex-1].startswith('<p id="OET-RV"'))
                self.assertTrue(paragraphs[keyIndex+1].startswith('<p id="OET-LV"'))
                self.assertEqual(page.count('id="coloursButton"'), 1)
                self.assertIn('genitive/possessor', paragraphs[keyIndex])
            else:
                self.assertNotIn('class="grk', page)
                self.assertNotIn('coloursButton', page)
            self.assertNotIn('<!--DC draft colour key-->', page)

    def test_sirach_prologue_groups_link_to_the_stored_introduction(self):
        folder=Path(self.state.BibleLocations['OET-LV-DC'])
        self.table.append('\t'.join(('SIR_0:1w1','λόγος','λόγος','','word','word',
            'draft','source','[]','SIR_1:1','source.usfm','','')))
        (folder/DC_WORD_TABLE).write_text('\n'.join(self.table))
        (folder/'OET-LV_SIR.ESFM').write_text('\\id SIR\n\\rem WORDTABLE '+DC_WORD_TABLE+
            '\n\\h Sirach\n\\is1 Prologue\n\\ip Prologue word¦4.\n\\c 1\n\\p\n\\v 1 Body text.\n')
        self.state.booksToLoad['OET-LV'].append('SIR')
        self.load()
        createDCWordPages(2,self.root/'ref/DCWrd',self.state)
        html=(self.root/'ref/DCWrd/SIR_C0.htm').read_text()
        self.assertIn('OET-LV/byC/SIR_Intro.htm#Top',html)
        self.assertNotIn('OET-LV/byC/SIR_C0.htm',html)
        self.assertIn('prologue (complete)',html)
        self.assertIn('Prologue word',re.sub(r'<[^>]+>','',html))
        self.assertIn('id="W4"',html)

    def test_dc_details_do_not_advertise_books_omitted_from_this_build(self):
        self.load()
        self.state.booksToLoad['OET-LV']=['TOB']
        createDCWordPages(2,self.root/'ref/DCWrd',self.state)
        self.assertTrue((self.root/'ref/DCWrd/TOB_C1.htm').is_file())
        self.assertFalse((self.root/'ref/DCWrd/PSS_C1.htm').exists())
        self.assertNotIn('PSS_C1.htm',(self.root/'ref/DCWrd/index.htm').read_text())

    def test_explicit_rv_dc_word_tags_use_dc_rows_in_both_rendering_paths(self):
        self.load()
        folder=self.root/'ReadersVersion';folder.mkdir()
        (folder/DC_WORD_TABLE).write_text('\n'.join(self.table))
        (folder/'OET-RV_TOB.ESFM').write_text('\\id TOB\n\\rem ESFM v0.6 TOB\n\\rem WORDTABLE '+DC_WORD_TABLE+
            '\n\\h Tobit\n\\c 1\n\\p\n\\v 1 The word¦1.\n')
        rv=ESFMBible(folder,givenAbbreviation='OET-RV',versification=self.state.BibleVersifications['OET-RV'])
        rv.loadBooks();self.state.preloadedBibles['OET-RV']=rv
        rv.ESFMWordTables=dict(self.bible.ESFMWordTables)
        entries,context=rv.getContextVerseData(('TOB','1','1'))
        html=convertVerseEntryListToHtml(2,'OET-RV',('TOB','1','1'),'verse',context,entries,
                                       basicOnly=True,state=self.state,livenWordLinks=True)
        self.assertIn('ref/DCWrd/TOB_C1.htm#W1',html)
        self.assertIn('λόγος',html)
        self.assertIn('class="grkNom"',html)
        self.assertNotIn('HebWrd',html)
        linked=livenOETWordLinks(2,rv,('TOB','1','1'),entries,self.state)
        self.assertTrue(any('ref/DCWrd/TOB_C1.htm#W1' in entry.getOriginalText() for entry in linked))
        self.assertTrue(any('class="grkNom"' in entry.getOriginalText() for entry in linked))


    def test_lao_loads_maps_renders_and_links_latin_word_details(self):
        from oetPassages import renderOETLVPassage, renderOETSideBySideChunks
        from versification import parallelVersePassage
        folder = Path(self.state.BibleLocations['OET-LV-DC'])
        words = {15: 'integra', 16: 'retinete', 17: 'pax', 18: 'sancti', 19: 'Gratia', 20: 'Colosensibus'}
        latin = '\\id LAO\n\\rem ESFM v0.6 LAO\n\\rem WORDTABLE '+DC_WORD_TABLE+'\n\\h Laodiceans\n\\mt1 Laodiceans\n\\c 1\n\\p\n'
        for verse in range(1,21):
            number = verse+3
            latin += f'\\v {verse} Latin{verse}¦{number}.\n'
            self.table.append('\t'.join((f'LAO_1:{verse}w1',words.get(verse,'Paulus'),'','','',f'Latin{verse}',
                'latin-editorial-draft','OET Latin gloss','[]',f'LAO_1:{verse}','Lightfoot-1875.html','','.')))
        (folder/'OET-LV_LAO.ESFM').write_text(latin)
        (folder/DC_WORD_TABLE).write_text('\n'.join(self.table)+'\n')
        self.state.booksToLoad['OET-LV'].append('LAO')
        lv = self.load()
        self.assertIn('LAO',lv)
        rvFolder = self.root/'ReadersVersion';rvFolder.mkdir()
        (rvFolder/'OET-RV_LAO.ESFM').write_text('\\id LAO\n\\h Laodiceans\n\\mt1 Laodiceans\n\\c 1\n\\s1 Greeting\n\\p\n'
            + ''.join(f'\\v {v} Readers{v}.\n' for v in range(1,21)))
        self.state.BibleLocations['OET-RV'] = str(rvFolder)
        self.state.BibleVersions = ['OET-RV']
        self.state.booksToLoad['OET-RV'] = ['LAO']
        self.assertEqual(Bibles.preloadVersions(self.state),2)
        rv = self.state.preloadedBibles['OET-RV']
        for version,bible in [('OET-RV',rv),('OET-LV',lv)]:
            for verse in range(1,21):
                portions,label = parallelVersePassage(version,bible,('LAO','1',str(verse)),self.state,{})
                self.assertEqual([p[0] for p in portions],[('LAO','1',str(verse))])
                self.assertEqual(label,'')
        for verse in (15,16,17,18,19,20):
            entries,_ = rv.getContextVerseData(('LAO','1',str(verse)))
            rendered,_ = renderOETLVPassage(2,lv,('LAO','1',str(verse)),entries,'verse',self.state,{})
            self.assertIn(f'Latin{verse}',rendered)
            self.assertIn(f'ref/DCWrd/LAO_C1.htm#W{verse+3}',rendered)
            self.assertNotIn('ref/HebWrd/',rendered)
            self.assertNotIn('¦',rendered)
            self.assertNotIn('class="grk',rendered)
            self.assertEqual(dcGrammaticalColourKey(rendered), '')
        combined,_ = renderOETSideBySideChunks(2,rv,lv,'LAO','chapter',self.state,chapter='1')
        for verse in range(1,21):
            self.assertIn(f'Readers{verse}.',combined)
            self.assertIn(f'Latin{verse}',combined)
        createDCWordPages(2,self.root/'ref/DCWrd',self.state)
        details=(self.root/'ref/DCWrd/LAO_C1.htm').read_text()
        self.assertIn('Latin word details',details)
        self.assertIn('<th>Latin form</th>',details)
        self.assertIn('Lightfoot',details)
        self.assertNotIn('STEPBible',details)
        self.assertNotIn('Greek form',details)
        self.assertIn('Latin morphology is not yet available', details)
        for verse in range(1,21): self.assertIn(f'id="W{verse+3}"',details)
        self.assertIn('LAO_C1.htm#Top',(self.root/'ref/DCWrd/index.htm').read_text())
        self.assertEqual(bookNavigationOrder(['PHM','LAO','COL'],'OET-LV'),['COL','LAO','PHM'])


if __name__ == '__main__':
    unittest.main()
