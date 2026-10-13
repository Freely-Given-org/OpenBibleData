"""Small, offline BOS integration tests; no site datasets or OBD Rust renderer.

From OpenBibleData:
    ../BibleOrgSys/.venv/bin/python -m unittest discover -s createPages -p test_versification.py
"""
import ast
from collections import defaultdict
import logging
import os
from pathlib import Path
import pickle
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, VersificationMappingEngine, VersificationMappingError,
)
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
import bos_books_codes_py
from bible_organisational_system import getSmallLeadingInt

from settings import State
import versification as vf


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.original = Bible(versification='org')

    def refs(self, reference, bible=None, version='OET-LV'):
        return vf.parallelVerseReferences(version, self.original if bible is None else bible, reference, self.state)

    def test_psalm_titles_and_one_and_two_verse_offsets(self):
        for source, target in ((('3','0'),('3','1')), (('3','1'),('3','2')),
                               (('3','8'),('3','9')), (('51','1'),('51','3')),
                               (('51','19'),('51','21')), (('98','1'),('98','1'))):
            with self.subTest(source=source):
                self.assertEqual(self.refs(('PSA',*source)), (('PSA',*target,None),))

    def test_chapter_boundaries_beyond_psalms(self):
        for source, target in ((('MAL','4','1'),('MAL','3','19')),
                               (('MAL','4','6'),('MAL','3','24')),
                               (('GEN','31','55'),('GEN','32','1')),
                               (('JOL','2','28'),('JOL','3','1'))):
            with self.subTest(source=source):
                self.assertEqual(self.refs(source), ((*target,None),))

    def test_lxx_psalm_and_reordered_jeremiah(self):
        lxx = Bible(versification='lxx')
        self.assertEqual(self.refs(('PSA','51','1'), lxx), (('PSA','50','3',None),))
        self.assertEqual(self.refs(('JER','31','1'), lxx), (('JER','38','1',None),))

    def test_english_navigation_even_with_only_original_source(self):
        self.assertEqual(vf.navigationVersification().getNumChapters('MAL'), 4)
        self.assertEqual(vf.navigationVersification().getNumVerses('MAL','4'), 6)

    def test_lxx_combined_book_uses_each_imports_storage_layout(self):
        lxx = Bible(versification='lxx')
        self.assertEqual(self.refs(('NEH','1','1'), lxx, 'BrLXX'), (('EZR','11','1',None),))
        self.assertEqual(self.refs(('NEH','1','1'), lxx, 'BrTr'), (('NEH','1','1',None),))
        self.assertEqual(self.refs(('EZR','1','1'), lxx, 'BrTr'), (('EZR','1','1',None),))

    def test_editorial_intros_are_not_guessed_at_chapter_boundaries(self):
        self.assertEqual(self.refs(('GEN','-1','0')), (('GEN','-1','0',None),))
        self.assertEqual(self.refs(('GEN','1','0')), (('GEN','1','0',None),))
        self.assertEqual(self.refs(('MAL','4','0')), ())

    def test_selected_excerpts_and_uhb_keep_english_numbering(self):
        for version in self.state.selectedVersesOnlyVersions:
            self.assertEqual(vf.parallelVerseReferences(version, {}, ('PSA','3','1'), self.state),
                             (('PSA','3','1',None),))
        uhb = vf.configureBibleVersification(Bible(), 'UHB', self.state)
        self.assertEqual(vf.parallelVerseReferences('UHB', uhb, ('MAL','4','1'), self.state),
                         (('MAL','4','1',None),))

    def test_cached_declarations_are_refreshed(self):
        old = pickle.loads(pickle.dumps(Bible(versification='eng')))
        vf.configureBibleVersification(old, 'OET-LV', self.state)
        self.assertEqual(old.getVersificationSystemName(), 'org')
        old = pickle.loads(pickle.dumps(Bible()))
        vf.configureBibleVersification(old, 'OET-RV', self.state)
        self.assertEqual(old.getVersificationSystemName(), 'eng')

    def test_wycliffe_confirmed_mark_boundary_after_cache_loading(self):
        wycliffe = pickle.loads(pickle.dumps(Bible()))
        vf.configureBibleVersification(wycliffe, 'Wycl', self.state)
        self.assertEqual(self.refs(('MRK','9','1'), wycliffe, 'Wycl'),
                         (('MRK','8','39',None),))
        self.assertEqual(self.refs(('MRK','9','2'), wycliffe, 'Wycl'),
                         (('MRK','9','1',None),))

    def test_unavailable_and_ambiguous_results_never_fall_back(self):
        for bible, reference, status in (
            (Bible(versification='Luther'), ('PSA','3','1'), MappingStatus.UNSUPPORTED),
            (Bible(), ('GEN','1','1'), MappingStatus.UNSUPPORTED),
            (Bible(versification='vul'), ('TOB','1','1'), MappingStatus.UNSUPPORTED),
            (Bible(versification='eng'), ('PSA','13','5'), MappingStatus.AMBIGUOUS),
        ):
            with self.subTest(reference=reference, system=bible.getVersificationSystemName()):
                with self.assertRaises(VersificationMappingError) as caught:
                    vf.parallelVerseReferences('OET-LV', bible, reference, self.state)
                self.assertEqual(caught.exception.result.status, status)
                self.assertEqual(caught.exception.result.references, ())

    def test_conflicting_metadata_stays_ambiguous(self):
        bible = Bible()
        bible.suppliedMetadata = {'File': {'Versification':'eng'}, 'Project': {'Versification':'org'}}
        bible.applySuppliedMetadata('File')
        bible.applySuppliedMetadata('Project')
        with self.assertRaises(VersificationMappingError) as caught:
            self.refs(('GEN','1','1'), bible)
        self.assertEqual(caught.exception.result.status, MappingStatus.AMBIGUOUS)

    def test_complete_group_preserved_and_partial_group_refused(self):
        engine = VersificationMappingEngine({'maxVerses': {'GEN':[3]}}, {
            'eng': {'maxVerses': {'GEN':[2]},
                    'groupMappings': [{'source':'GEN 1:1','target':'GEN 1:1-2'}],
                    'mappedVerses': {'GEN 1:2':'GEN 1:3'}},
            'org': {'maxVerses': {'GEN':[3]}, 'identityBooks': {'GEN':'GEN'}},
        })
        vf._mapReference.cache_clear()
        try:
            with patch.object(vf, 'get_default_mapping_engine', return_value=engine):
                self.assertEqual(self.refs(('GEN','1','1')),
                                 (('GEN','1','1',None),('GEN','1','2',None)))
                with self.assertRaises(VersificationMappingError) as caught:
                    vf.parallelVerseReferences('OET-LV', Bible(versification='eng'),
                        ('GEN','1','1'), SimpleNamespace(navigationVersification='org'))
                self.assertEqual(caught.exception.result.status, MappingStatus.PARTIAL)
        finally:
            vf._mapReference.cache_clear()


class TextRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        Path(self.temp.name, '19PSA.usfm').write_text(
            '\\id PSA Test\n\\h Psalms\n\\c 3\n\\d Title only.\n\\q1\n'
            '\\v 1 Verse one.\n\\v 2-3 Verse bridge.\n\\v 4a First part.\n'
            '\\v 4b Second part.\n\\c 4\n\\p\n\\v 1 Next chapter.\n')
        self.bible = USFMBible(self.temp.name, versification='eng')
        self.bible.load()

    def text(self, portion):
        return ' '.join(e.getCleanText() for e in portion[1])

    def test_titles_are_separate_from_verse_one(self):
        title, verse = vf.getVersePortions(self.bible,
            (('PSA','3','0',None),('PSA','3','1',None)), {})
        self.assertIn('Title only.', self.text(title))
        self.assertNotIn('Title only.', self.text(verse))
        self.assertIn('Verse one.', self.text(verse))

    def test_bridges_render_once_with_bulk_or_scalar_index(self):
        refs = (('PSA','3','2',None),('PSA','3','3',None))
        for cache in ({}, {(id(self.bible),'PSA','3'): {'2-3':self.bible.getContextVerseData(('PSA','3','2'))}}):
            parts = vf.getVersePortions(self.bible, refs, cache)
            self.assertEqual(len(parts), 1)
            self.assertIn('Verse bridge.', self.text(parts[0]))

    def test_suffixes_are_exact_and_not_widened(self):
        parts = vf.getVersePortions(self.bible, (('PSA','3','4','b'),), {})
        self.assertEqual(parts[0][0], ('PSA','3','4b'))
        self.assertIn('Second part.', self.text(parts[0]))
        self.assertNotIn('First part.', self.text(parts[0]))
        with self.assertRaises(KeyError):
            vf.getVersePortions(self.bible, (('PSA','3','1','a'),), {})

    def test_whole_verse_includes_all_stored_suffixes(self):
        parts = vf.getVersePortions(self.bible, (('PSA','3','4',None),), {})
        self.assertEqual([p[0] for p in parts], [('PSA','3','4a'),('PSA','3','4b')])
        self.assertIn('First part.', self.text(parts[0]))
        self.assertIn('Second part.', self.text(parts[1]))

    def test_lazy_mapped_book_is_loaded_before_access(self):
        lazy = USFMBible(self.temp.name, versification='eng')
        lazy.preload()
        self.assertNotIn('PSA', lazy.books)
        parts = vf.getVersePortions(lazy, (('PSA','3','1',None),), {})
        self.assertIn('Verse one.', self.text(parts[0]))

    def test_native_chapter_cache_and_disjoint_order(self):
        cache = {}
        parts = vf.getVersePortions(self.bible,
            (('PSA','4','1',None),('PSA','3','1',None)), cache)
        self.assertIn('Next chapter.', self.text(parts[0]))
        self.assertIn('Verse one.', self.text(parts[1]))
        self.assertEqual(len(cache), 2)

    def test_group_with_missing_portion_is_not_returned_partially(self):
        with self.assertRaises(KeyError):
            vf.getVersePortions(self.bible, (('PSA','3','1',None),('PSA','3','99',None)), {})
        with self.assertRaises(vf.MissingMappedBookError):
            vf.getVersePortions(self.bible, (('GEN','1','1',None),), {})

    def test_portion_html_uses_native_label_and_unique_footnote_ids(self):
        html = '<p id="LV"><span><a href="LV/byC/MAL_C3.htm#V19">LV</a></span><a href="#fn1">†</a></p><p id="fn1"><a href="#C3V19">3:19</a></p>'
        result = vf.versePortionHtml(html, 'LV', ('MAL','3','19'), ('MAL','4','1'), 1)
        self.assertIn('(MAL 3:19)', result)
        self.assertIn('href="LV/byC/MAL_C3.htm#V19"', result)
        self.assertIn('id="fn1_part2"', result)
        self.assertIn('href="#fn1_part2"', result)
        self.assertIn('href="#LV_part2"', result)


class ParallelPageTests(unittest.TestCase):
    builder = "createParallelVersePages"
    pageTitle = "Parallel"
    """Run the real page loop with real BOS text and a recording HTML renderer.

    Loading only this function avoids the site's unavailable dictionaries/maps
    and compiled OBD renderer. This checks integration, not Rust HTML styling.
    """
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'par'
        self.output.mkdir()
        self.rendered = []
        self.state = State()
        self.state.TEST_MODE_FLAG = True
        self.state.TEST_VERSIONS_ONLY = None
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.state.BibleVersions = ['OET-LV']
        self.state.preloadedBibles = {'OET-RV': None}
        self.state.versionComments = {}
        self.state.versesWithImages = defaultdict(list)
        self.state.booksToLoad = {'OET': []}

        def render(level, version, reference, kind, context, entries, **kwargs):
            self.rendered.append((version, reference))
            words = ' '.join(e.getCleanText() for e in entries if e.getMarker() in ('v~','d'))
            return f'<span class="{version}_verseTextChunk">{words}</span>'

        namespace = dict(globals(),
            os=os, bos_books_codes_py=bos_books_codes_py, getSmallLeadingInt=getSmallLeadingInt,
            DEBUGGING_THIS_MODULE=False, NEWLINE='\n', ESFMBible=SimpleNamespace(ESFMBible=ESFMBible),
            ENTIRE_FOOTNOTE_REGEX=re.compile(r'\\f .+?\\f\*'),
            FIRST_PAIRED_VERSIONS=('BSB','WEBBE'), SECOND_PAIRED_VERSIONS=('MSB','WMBB'),
            BOOKLIST_66=BibleOrgSysGlobals.BOOKLIST_66,
            vPrint=lambda *args: None, dPrint=lambda *args: None, fnPrint=lambda *args: None,
            rreplace=BibleOrgSysGlobals.rreplace,
            getOETTidyBBB=lambda book, **kwargs: book,
            getOETBookName=lambda book: book,
            makeBookNavListParagraph=lambda links,*args: ''.join(links),
            makeTop=lambda *args: '<html><head><title>__TITLE__</title></head><body>',
            makeBottom=lambda *args: '</body></html>',
            checkHtml=lambda *args,**kwargs: True,
            getVerseMetaInfoHtml=lambda *args: '',
            convertVerseEntryListToHtml=render,
            handleAndExtractFootnotes=lambda version,text: (text,text,''),
            do_OET_LV_HTMLcustomisations=lambda location,text: text,
            convert_adds_to_italics=lambda text,*args: text,
            rememberPossibleUnmatchedProperNames=lambda *args: None,
            formatTyndaleBookIntro=lambda *args: '', formatTyndaleNotes=lambda *args: '',
            formatUnfoldingWordTranslationNotes=lambda *args: '',
            getFormattedSILOpenTranslationNotes=lambda *args: '',
            getBibleMapperMaps=lambda *args: '',
            UntranslatedVerseError=type('UntranslatedVerseError',(Exception,),{}),
            **{name:getattr(vf,name) for name in ('navigationVersification','parallelVerseReferences',
                'getVersePortions','versePortionHtml','MissingMappedBookError')},
        )
        source = Path(__file__).with_name(self.builder + '.py')
        function = next(node for node in ast.parse(source.read_text()).body
                        if isinstance(node,ast.FunctionDef) and node.name==self.builder+'ForBook')
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        self.generate = namespace[function.name]
        self.namespace = namespace
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def load(self, BBB, text):
        folder = self.root / BBB
        folder.mkdir()
        (folder / f'{BBB}.esfm').write_text(f'\\id {BBB}\n\\h {BBB}\n{text}')
        bible = ESFMBible(folder, givenAbbreviation='OET-LV', versification='org')
        bible.loadBooks()
        self.state.preloadedBibles['OET-LV'] = bible
        return bible

    def runBook(self, BBB):
        self.assertTrue(self.generate(1, self.output, BBB,
            [f'<a title="{BBB}" href="../{BBB}/C1V1.htm#chLst">{BBB}</a>'],
            self.state.BibleVersions, self.state))

    def test_malachi_navigation_native_rendering_and_source_link(self):
        self.load('MAL', '\\c 3\n\\p\n' + ''.join(f'\\v {v} Native verse {v}.\n' for v in range(1,25)))
        self.runBook('MAL')
        page = (self.output/'MAL/C4V1.htm').read_text()
        self.assertIn(self.pageTitle + ' MAL 4:1', page)
        self.assertIn('Native verse 19.', page)
        self.assertNotIn('Native verse 1.', page)
        self.assertIn('OET-LV/byC/MAL_C3.htm#V19', page)
        self.assertIn('(MAL 3:19)', page)
        self.assertIn(('OET-LV',('MAL','3','19')), self.rendered)
        self.assertTrue((self.output/'MAL/C4V6.htm').exists())
        self.assertFalse((self.output/'MAL/C3V24.htm').exists())

    def test_split_group_renders_every_portion_with_unique_version_ids(self):
        self.load('GEN', '\\c 1\n\\p\n\\v 1 First portion.\n\\v 2 Second portion.\n\\v 3 Next passage.\n')
        engine = VersificationMappingEngine({'maxVerses': {'GEN':[2]}}, {
            'eng': {'maxVerses': {'GEN':[2]}, 'identityBooks': {'GEN':'GEN'}},
            'org': {'maxVerses': {'GEN':[3]},
                    'groupMappings': [{'source':'GEN 1:1-2','target':'GEN 1:1'}],
                    'mappedVerses': {'GEN 1:3':'GEN 1:2'}},
        })
        vf._mapReference.cache_clear()
        try:
            self.namespace['navigationVersification'] = lambda name: SimpleNamespace(
                getNumChapters=lambda book: 1, getNumVerses=lambda book,chapter: 2)
            with patch.object(vf, 'get_default_mapping_engine', return_value=engine):
                self.runBook('GEN')
        finally:
            vf._mapReference.cache_clear()
        page = (self.output/'GEN/C1V1.htm').read_text()
        self.assertIn('First portion.', page)
        self.assertIn('Second portion.', page)
        self.assertNotIn('Next passage.', page)
        self.assertEqual(page.count('id="OET-LV"'), 1)
        self.assertEqual(page.count('id="OET-LV_part2"'), 1)
        self.assertIn('GEN_C1.htm#V2', page)

    def test_unsupported_alignment_is_visible_without_wrong_text(self):
        bible = self.load('MAL', '\\c 3\n\\p\n\\v 1 Wrong if used on page 4:1.\n')
        bible.setVersificationSystem('Luther')
        self.runBook('MAL')
        page = (self.output/'MAL/C4V1.htm').read_text()
        self.assertIn('Verse alignment unavailable (unsupported)', page)
        self.assertNotIn('Wrong if used', page)


class VerseListPageTests(ParallelPageTests):
    builder = 'createVerseListPages'
    pageTitle = 'Simple verse list for'


if __name__ == '__main__':
    unittest.main()
