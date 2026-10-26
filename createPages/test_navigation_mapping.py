#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0

"""Offline mapping tests, including the production Rust bridge when available.
CHANGELOG:
    2026-10-16 Cover Luther mapping; use KJV for count-only failure fixtures.
    2026-10-22 Use Original for unverified-profile fixtures after KJV OT support.
    2026-10-23 Distinguish shared OET/RV section links from version switching.
    2026-10-26 Cover unnumbered Psalm headings and their exact interlinear word rows.
"""
import ast
from collections import defaultdict
from functools import cache
import logging
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
import bos_books_codes_py

from settings import State, CNTR_BOOK_ID_MAP
import navigation as nav
import oetWords as words
import versification as vf
from oetPassages import _namespaceIds

try:
    import openbibledata_rust as rust
except ImportError:
    rust = None


def functionFromFile(filename, name, namespace):
    source = Path(__file__).with_name(filename)
    function = next(n for n in ast.parse(source.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace[name]


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.addCleanup(vf._mapReference.cache_clear)

    def test_native_links_and_labels_with_idempotent_conversion(self):
        html = '<a href="../../par/MAL/C3V19.htm#Top">19</a><a href="../../ref/HebWrd/381095.htm#Top">word</a>'
        mapped = nav.mapHtmlLinks(html, 'OET-LV', 2, self.state)
        self.assertIn('par/MAL/C4V1.htm#Top">19</a>', mapped)
        self.assertIn('HebWrd/381095.htm#Top', mapped)
        self.assertEqual(nav.mapHtmlLinks(mapped, 'OET-LV', 2, self.state), mapped)

    def test_version_switch_english_to_native_chapter(self):
        html = '<a href="../../OET-LV/byC/MAL_C4.htm">LV</a>'
        mapped = nav.mapHtmlLinks(html, 'OET', 2, self.state, versionBar=True)
        self.assertIn('OET-LV/byC/MAL_C3.htm#C3V19', mapped)

    def test_native_chapter_controls_to_english(self):
        html = '<a href="../../OET/byC/JOL_C4.htm#Top">OET</a><a href="JOL_C3.htm#Top">Previous</a>'
        mapped = nav.mapHtmlLinks(html, 'OET-LV', 2, self.state, segmentType='chapter')
        self.assertIn('OET/byC/JOL_C3.htm#C3V1', mapped)
        self.assertIn('href="JOL_C3.htm#Top"', mapped)

    def test_cross_references_and_introduction_links(self):
        for href, kind, expected in (
            ('../../OET/byC/MAL_C3.htm#C3V19', 'parallelVerse', 'OET/byC/MAL_C4.htm#C4V1'),
            ('../MAL/C3V19.htm#Top', 'parallelVerse', 'par/MAL/C4V1.htm#Top'),
            ('MAL_C3.htm#C3V19', 'chapter', 'OET/byC/MAL_C4.htm#C4V1'),
            ('../../OET/bySec/MAL_S0.htm#C3V19', 'parallelVerse', 'OET/byC/MAL_C4.htm#C4V1'),
            ('../byC/MAL_C3.htm#C3V19', 'section', 'OET/byC/MAL_C4.htm#C4V1'),
        ):
            with self.subTest(href=href):
                result = nav.mapHtmlLinks(f'<a href="{href}">ref</a>', 'OET-LV', 2,
                    self.state, segmentType=kind, reference=('MAL','3','19'), navigationVersion='OET')
                self.assertIn(expected, result)

    def test_local_native_footnote_returns_survive_for_namespacing(self):
        html = '<span id="C3V19">text</span><a href="#C3V19">back</a>'
        result = nav.mapHtmlLinks(html, 'OET-LV', 2, self.state, reference=('MAL','3','19'), navigationVersion='OET')
        self.assertIn('href="#LV_C3V19"', _namespaceIds(result, 'LV_'))

    def test_combined_oet_sections_keep_rv_addresses(self):
        html = '<a title="Jump to section" href="../../OET/bySec/MRK_S0.htm#C1V1">1:1-13</a>'
        mapped = nav.mapHtmlLinks(html, 'OET-RV', 2, self.state, segmentType='parallelVerse')
        self.assertEqual(mapped, html.replace('href=', 'data-vref="mapped" href='))
        self.assertEqual(nav.mapHtmlLinks(mapped, 'OET-RV', 2, self.state), mapped)
        # Version-bar links still select a chapter in the target edition.
        switched = nav.mapHtmlLinks(html, 'OET-RV', 2, self.state, versionBar=True)
        self.assertIn('OET/byC/MRK_C1.htm#C1V1', switched)
        self.assertNotIn('bySec', switched)

    def test_unsupported_mapping_is_not_a_guessed_link(self):
        self.state.BibleVersifications = dict(self.state.BibleVersifications, **{'OET-LV':'Original'})
        self.assertEqual(nav.mapHtmlLinks('<a href="../../par/PSA/C3V2.htm">2</a>', 'OET-LV', 2, self.state), '2')

    def test_json_metadata_keeps_native_ref_and_separate_english_ref(self):
        original = {'ref':'MAL_3:19w1', 'word_number':381095}
        original.update(nav.wordReferenceMetadata(original['ref'], self.state))
        self.assertEqual(original['ref'], 'MAL_3:19w1')
        self.assertEqual(original['word_number'], 381095)
        self.assertEqual(original['navigation_references'], ['MAL_4:1'])
        self.assertEqual(original['versification'], 'OET-LV')

    def test_one_native_reference_can_have_several_english_destinations(self):
        self.state.BibleVersifications = dict(self.state.BibleVersifications, **{'OET-LV':'org'})
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[3]}}, {
            'org':{'maxVerses':{'GEN':[3]},'identityBooks':{'GEN':'GEN'}},
            'eng':{'maxVerses':{'GEN':[4]},'groupMappings':[{'source':'GEN 1:1-2','target':'GEN 1:1'}]},
        })
        with patch.object(vf, 'get_default_mapping_engine', return_value=engine):
            html = nav.scriptureLink(2, ('GEN','1','1'), 'OET-LV','OET','par','1',self.state)
        self.assertIn('C1V1.htm', html)
        self.assertIn('C1V2.htm', html)


class WordMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = State()
        self.state.preloadedBibles = {}
        self.state.OETRefData = {'word_tables':{}, 'word_table_indexes':{}}
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def bible(self, version, BBB, content):
        folder = self.root/version/BBB
        folder.mkdir(parents=True)
        (folder/f'{BBB}.esfm').write_text(f'\\id {BBB}\n\\h {BBB}\n{content}')
        bible = ESFMBible(folder, givenAbbreviation=version, versification=self.state.BibleVersifications[version])
        bible.loadBooks()
        self.state.preloadedBibles[version] = bible
        return bible

    def table(self):
        rows = ['header']
        for ref, word, gloss in [('MAL_3:1w1','אַ','wrong'), ('MAL_3:19w1','קוֹל','voice'),
                                  ('MAL_3:19w2','אֵל','God'), ('MAL_3:20w1','בָּא','comes')]:
            fields = ['']*19
            fields[0],fields[6],fields[7],fields[10] = ref,word,word,gloss
            rows.append('\t'.join(fields))
        name = words.wordTableName('MAL')
        self.state.OETRefData['word_tables'][name] = rows
        self.state.OETRefData['word_table_indexes'][name] = {'MAL_3:1':(1,1),'MAL_3:19':(2,3),'MAL_3:20':(4,4)}
        return rows

    def test_mapped_quote_text_rows_and_word_ids(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 1 Wrong¦1.\n\\v 19 voice¦2 God¦3.\n')
        self.table()
        texts, rows = words.translationNoteQuoteData('MAL','4','1',self.state)
        self.assertEqual(rows, [2,3])
        self.assertIn('voice¦2', ''.join(texts))
        self.assertNotIn('Wrong', ''.join(texts))
        self.assertEqual(words.matchedHebrewWordRows('MAL','4','1',['קול','אל'],self.state), [2,3])
        with self.assertRaises(ValueError):
            words.matchedHebrewWordRows('MAL','4','1',['בא','אל'],self.state)

    def test_disjoint_rows_do_not_include_intervening_verses(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 1 First¦1.\n\\v 19 Middle¦2.\n\\v 20 Last¦4.\n')
        self.table()
        self.assertEqual(words.nativeWordRows((('MAL','3','1',None),('MAL','3','20',None)),self.state),(1,4))

    def test_combined_acts_passage_preserves_all_native_word_rows(self):
        bible = self.bible('OET-LV','ACT','\\c 19\n\\v 40 Speech¦98355. Dismissal¦98365.\n')
        name = words.wordTableName('ACT')
        self.state.OETRefData['word_table_indexes'][name] = {'ACT_19:40':(98355,98368)}
        for verse in ('40','41'):
            passage = bible.getMappedPassage('eng',[('ACT','19',verse)],expandGroups=True)
            self.assertEqual(words.passageWordRows(passage,self.state),tuple(range(98355,98369)))
            texts,rows = words.translationNoteQuoteData('ACT','19',verse,self.state)
            self.assertEqual(rows,list(range(98355,98369)))
            self.assertIn('Speech¦98355. Dismissal¦98365.',' '.join(texts))
            self.assertIn('Combined passage: English ACT 19:40–41',vf.combinedPassageLabel(passage))

    def test_suffix_rows_require_exact_stored_text(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 19a voice¦2.\n\\v 19b God¦3.\n')
        self.table()
        self.assertEqual(words.nativeWordRows((('MAL','3','19','a'),),self.state),(2,))
        self.assertEqual(words.nativeWordRows((('MAL','3','19','b'),),self.state),(3,))
        with self.assertRaises(KeyError):
            words.nativeWordRows((('MAL','3','19','c'),),self.state)

    def test_reference_page_rv_quote_is_mapped_from_native_word_reference(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 19 Native¦2.\n')
        self.bible('OET-RV','MAL','\\c 3\n\\v 19 Wrong.\n\\c 4\n\\v 1 Correct.\n')
        namespace = dict(globals(), state=self.state, VersificationMappingError=vf.VersificationMappingError,
            convertVerseEntryListToHtml=lambda l,v,r,k,c,entries,**kw:' '.join(e.getCleanText() for e in entries if e.getMarker()=='v~'),
            do_OET_RV_HTMLcustomisations=lambda _,s:s)
        generate = functionFromFile('createOETReferencePages.py','get_OET_RV_verse_HTML',namespace)
        html = generate(2,'MAL','3','19')
        self.assertIn('Correct',html)
        self.assertIn('MAL 4:1',html)
        self.assertNotIn('Wrong',html)

    def test_missing_portion_prevents_partial_quote(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 1 Wrong¦1.\n')
        self.table()
        self.assertEqual(words.translationNoteQuoteData('MAL','4','1',self.state), ([],[]))

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_rust_note_matcher_uses_mapped_text_and_rows(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 1 Wrong¦1.\n\\v 19 voice¦2 God¦3.\n')
        self.table()
        with patch.dict(sys.modules, html=SimpleNamespace(checkHtml=lambda *a,**k:True)):
            quote = rust.findOLQuoteInLV(2,'MAL','4','1',1,'קוֹל אֵל',self.state)
        self.assertEqual(quote, 'voice God')

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_rust_renderer_maps_native_verse_links(self):
        bible = self.bible('OET-LV','MAL','\\c 3\n\\v 19 voice.\n')
        entries, context = bible.getContextVerseData(('MAL','3','19'))
        html = rust.convertVerseEntryListToHtml(2,'OET-LV',('MAL','3','19'),'chapter',context,entries,state=self.state)
        self.assertIn('par/MAL/C4V1.htm', html)
        self.assertNotIn('par/MAL/C3V19.htm', html)

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_rust_introduction_keeps_verse_before_mapping(self):
        bible = self.bible('OET-LV','MAL','\\ip See (3:19).\n\\io1 End \\ior 3:19\\ior*\n\\c 3\n\\v 19 voice.\n')
        entries, context = bible.getContextVerseData(('MAL','-1'))
        for segment in ('section','parallelVerse'):
            with self.subTest(segment=segment):
                html = rust.convertVerseEntryListToHtml(2,'OET-LV',('MAL','-1'),segment,context,entries,
                                                       state=self.state,navigationVersion='OET')
                self.assertIn('OET/byC/MAL_C4.htm#C4V1',html)
                self.assertNotIn('MAL_C3.htm',html)

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_interlinear_page_uses_same_mapped_words_in_both_orders(self):
        self.bible('OET-LV','MAL','\\c 3\n\\v 1 Wrong¦1.\n\\v 19 voice¦2 God¦3.\n')
        self.bible('OET-RV','MAL','\\c 4\n\\v 1 voice¦2 God¦3.\n')
        self.table()
        self.state.booksToLoad = {'OET':['MAL']}
        html = self.interlinearGenerator()(2,'MAL',4,1,self.state)
        self.assertNotIn('Wrong',html)
        self.assertIn('OET-LV/byC/MAL_C3.htm#C3V19',html)
        self.assertIn('ref/HebWrd/2.htm',html)
        self.assertIn('ref/HebWrd/3.htm',html)
        self.assertNotIn('ref/HebWrd/1.htm',html)
        ids = re.findall(r'\bid="([^"]+)"', html)
        self.assertEqual(len(ids),len(set(ids)))

    def interlinearGenerator(self):
        namespace = dict(globals(), State=State, DEBUGGING_THIS_MODULE=False, NEWLINE='\n',
            vPrint=lambda *a:None, dPrint=lambda *a:None, fnPrint=lambda *a:None,
            findSectionNumber=lambda *a:0, getOETTidyBBB=lambda BBB,**kw:BBB,
            referenceHref=nav.referenceHref, passageWordRows=words.passageWordRows,
            combinedPassageLabel=vf.combinedPassageLabel, _mapReference=vf._mapReference,
            parallelVersePassage=vf.parallelVersePassage,
            getGreekWordpageFilename=lambda n,s:f'{n}.htm',
            VersificationMappingError=vf.VersificationMappingError,
            getPositiveLeadingInt=lambda s:int(re.match(r'\d+',s)[0]),
            getFormattedSILOpenTranslationNotes=lambda *a:'', formatUnfoldingWordTranslationNotes=lambda *a:'',
            formatTyndaleNotes=lambda *a:'', checkHtml=lambda *a,**k:True,
            do_OET_LV_HTMLcustomisations=lambda _,s:s, do_OET_RV_HTMLcustomisations=lambda _,s:s,
            convertVerseEntryListToHtml=lambda l,v,r,k,c,entries,**kw:' '.join(e.getCleanText() for e in entries if e.getMarker() in ('v~','d')),
            splitOETLVInterlinearWords=rust.splitOETLVInterlinearWords,
            splitOETRVInterlinearWords=rust.splitOETRVInterlinearWords,
            buildInterlinearWordRows=rust.buildInterlinearWordRows)
        return functionFromFile('createOETInterlinearPages.py','createOETInterlinearVerseInner',namespace)

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_unnumbered_psalm_heading_keeps_rv_text_and_only_its_hebrew_rows(self):
        self.bible('OET-LV','PSA','\\c 11\n\\v 1 Director¦1. David¦2. Refuge¦3.\n')
        self.bible('OET-RV','PSA','\\c 11\n\\d Director¦1. David¦2.\n\\q1\n\\v 1 Refuge¦3.\n')
        name = words.wordTableName('PSA')
        self.state.OETRefData['word_tables'][name] = ['header', *[
            f'PSA_11:1w{n}\tw\t\t\t\t\tדוד\tדוד\tDavid\tDavid\tDavid\tDavid\t\t\t\t\t1\tNcmsa\t'
            for n in (1,2,3)]]
        self.state.OETRefData['word_table_indexes'][name] = {'PSA_11:1':(1,3)}
        self.state.booksToLoad = {'OET':['PSA']}
        html = self.interlinearGenerator()(2,'PSA',11,0,self.state)
        self.assertIn('Director¦1. David¦2.', html)
        self.assertNotIn('Refuge¦3.', html)
        for n in (1,2):
            self.assertIn(f'ref/HebWrd/{n}.htm', html)
        self.assertNotIn('ref/HebWrd/3.htm', html)
        self.assertNotIn('No OET-RV', html)

    @unittest.skipIf(rust is None, 'Build the OBD Rust extension for this integration test')
    def test_combined_acts_interlinear_has_native_rows_in_both_orders(self):
        self.bible('OET-LV','ACT','\\c 19\n\\v 40 Speech¦1. Dismissal¦2.\n')
        self.bible('OET-RV','ACT','\\c 19\n\\v 40 Speech¦1.\n\\v 41 Dismissal¦2.\n')
        name = words.wordTableName('ACT')
        self.state.OETRefData['word_tables'][name] = ['header',
            'ACT_19:40w1\tλόγος\tλόγος\tλόγος\tSpeech\tSpeech\t\tX\t30560\tN\tNMS\t',
            'ACT_19:40w2\tἀπέλυσεν\tἀπολύω\tἀπολύω\tDismissal\tDismissal\t\tX\t6300\tV\tIAA3S\t']
        self.state.OETRefData['word_table_indexes'][name] = {'ACT_19:40':(1,2)}
        self.state.booksToLoad = {'OET':['ACT']}
        generate = self.interlinearGenerator()
        for verse in (40,41):
            with self.subTest(verse=verse):
                html = generate(2,'ACT',19,verse,self.state)
                self.assertIn('Combined passage: English ACT 19:40–41',html)
                self.assertIn('native ACT 19:40',html)
                self.assertNotIn('alignment unavailable',html)
                self.assertIn('OET-LV/byC/ACT_C19.htm#C19V40',html)
                for word in (1,2):
                    self.assertEqual(html.count(f'ref/GrkWrd/{word}.htm#Top'),2)


if __name__ == '__main__':
    unittest.main()
