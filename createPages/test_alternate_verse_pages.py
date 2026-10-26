#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Offline alternate-address tests using BOS mappings and actual page writers.

CHANGELOG:
    2026-10-26 Cover alternate URLs, grouped/conflicting mappings and generator integration.
"""
import ast
from collections import defaultdict
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine
import alternateVersePages as av
from html import checkHtml
from parallel import runParallelPages
from navigation import navigationBookList
from substitutedVersions import prepareSubstitutedVersions, saveSubstitutedVersions


class AlternateVersePageTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / 'par'
        self.folder.mkdir()
        self.state = SimpleNamespace(navigationVersification='eng',
            BibleVersions=['OET-LV'], BibleVersifications={'OET-LV':'OET-LV'},
            preloadedBibles={'OET-LV':SimpleNamespace(availableBBBs={'MAL','PSA','JOL'}, books={})},
            BibleSourceBookLayouts={})

    def page(self, book, chapter, verse, text='Verse text with native word links.'):
        path = self.folder / book / f'C{chapter}V{verse}.htm'
        path.parent.mkdir(parents=True, exist_ok=True)
        document = (f'<!DOCTYPE html><html lang="en-US"><head><title>{book} {chapter}:{verse}</title>'
            '<meta charset="utf-8"><link rel="stylesheet" href="../../common.css">'
            '<script src="../../theme.js"></script></head><body>'
            f'<h1>{book} {chapter}:{verse}</h1><p id="Top">{text}</p>'
            '<p><a href="C1V1.htm#Top">Chapter</a> <a href="#fn1">Note</a> '
            '<a href="../../ref/word.htm#Top">Word</a></p><p id="fn1">Footnote</p>'
            '<img src="picture.png" alt="Diagram"><p id="Bottom">End</p></body></html>')
        path.write_text(document, encoding='utf-8')
        return document

    def malachi(self):
        for verse in range(1,7):
            self.page('MAL',4,verse,f'Malachi text {verse}.')

    def test_malachi_copies_text_and_explains_numbering_for_both_views(self):
        for view in ('parallel','interlinear'):
            with self.subTest(view=view):
                self.folder = self.root / view
                self.folder.mkdir()
                self.malachi()
                original = (self.folder/'MAL/C4V1.htm').read_bytes()
                self.assertEqual(av.createAlternateVersePages(self.folder,['MAL'],self.state,view),6)
                page = (self.folder/'MAL/C3V19.htm').read_text()
                self.assertIn('<title>MAL 3:19 — alternate verse numbering',page)
                self.assertIn('About verse numbering: MAL 3:19',page)
                self.assertIn('OET-LV',page)
                self.assertIn('OET-RV / English MAL 4:1',page)
                self.assertIn('<link rel="canonical" href="C4V1.htm">',page)
                self.assertIn('<h1>MAL 4:1</h1>',page)
                self.assertIn('Malachi text 1.',page)
                self.assertIn('href="#fn1"',page)
                self.assertIn('href="../../ref/word.htm#Top"',page)
                self.assertIn('src="../../theme.js"',page)
                self.assertEqual(page.count('id="Top"'),1)
                self.assertLess(page.index('id="Top"'),page.index('<h1>'))
                self.assertTrue(checkHtml('Alternate fixture',page))
                self.assertEqual((self.folder/'MAL/C4V1.htm').read_bytes(),original)
                self.assertEqual(av.createAlternateVersePages(self.folder,['MAL'],self.state,view),0)

    def test_existing_and_ordinary_addresses_are_never_replaced(self):
        self.page('PSA',51,18)
        self.page('PSA',51,19)
        original = self.page('PSA',51,20,'Existing page must remain.')
        with self.assertLogs(level='WARNING'):
            av.createAlternateVersePages(self.folder,['PSA'],self.state,'parallel')
        self.assertEqual((self.folder/'PSA/C51V20.htm').read_text(),original)
        self.assertTrue((self.folder/'PSA/C51V21.htm').exists())
        self.assertFalse((self.folder/'PSA/C51V10.htm').exists()) # Valid English address reserved.
        self.assertFalse((self.folder/'PSA/C51V0.htm').exists())

    def test_new_chapter_maps_back_to_ordinary_joel_chapter(self):
        for verse in range(1,22):
            self.page('JOL',3,verse)
        self.assertEqual(av.createAlternateVersePages(self.folder,['JOL'],self.state,'parallel'),21)
        page = (self.folder/'JOL/C4V21.htm').read_text()
        self.assertIn('href="C3V21.htm#Top"',page)

    def test_no_alias_without_every_target_page(self):
        self.page('MAL',4,1)
        with self.assertLogs(level='WARNING') as messages:
            self.assertEqual(av.createAlternateVersePages(self.folder,['MAL'],self.state,'parallel'),1)
        self.assertIn('target page not built',' '.join(messages.output))
        self.assertFalse((self.folder/'MAL/C3V20.htm').exists())

    def engine(self, *definitions):
        self.state.BibleVersions = [name for name,_ in definitions]
        self.state.BibleVersifications = {name:name for name,_ in definitions}
        self.state.preloadedBibles = {name:SimpleNamespace(availableBBBs={'GEN'}, books={})
                                     for name,_ in definitions}
        return VersificationMappingEngine({'maxVerses':{'GEN':[2]}}, {
            'eng':{'maxVerses':{'GEN':[2]},'identityBooks':{'GEN':'GEN'}},
            **dict(definitions)})

    def test_multi_page_group_lists_all_pages_without_copying_first(self):
        engine = self.engine(('native',{'maxVerses':{'GEN':[3]},
            'groupMappings':[{'source':'GEN 1:3','target':'GEN 1:1-2'}]}))
        self.page('GEN',1,1,'First target text.')
        self.page('GEN',1,2,'Second target text.')
        with patch.object(av,'get_default_mapping_engine',return_value=engine):
            self.assertEqual(av.createAlternateVersePages(self.folder,['GEN'],self.state,'parallel'),1)
        page = (self.folder/'GEN/C1V3.htm').read_text()
        self.assertIn('href="C1V1.htm#Top"',page)
        self.assertIn('href="C1V2.htm#Top"',page)
        self.assertNotIn('First target text.',page)
        self.assertNotIn('rel="canonical"',page)
        self.assertTrue(checkHtml('Group fixture',page))

    def test_expanded_source_group_is_explained(self):
        engine = self.engine(('native',{'maxVerses':{'GEN':[4]},
            'groupMappings':[{'source':'GEN 1:3-4','target':'GEN 1:1'}]}))
        self.page('GEN',1,1)
        with patch.object(av,'get_default_mapping_engine',return_value=engine):
            self.assertEqual(av.createAlternateVersePages(self.folder,['GEN'],self.state,'parallel'),2)
        page = (self.folder/'GEN/C1V3.htm').read_text()
        self.assertIn('complete passage is GEN 1:3–4',page)

    def test_conflicting_profiles_get_labelled_choices(self):
        engine = self.engine(
            ('first',{'maxVerses':{'GEN':[3]},'mappedVerses':{'GEN 1:3':'GEN 1:1'}}),
            ('second',{'maxVerses':{'GEN':[3]},'mappedVerses':{'GEN 1:3':'GEN 1:2'}}))
        self.page('GEN',1,1)
        self.page('GEN',1,2)
        with patch.object(av,'get_default_mapping_engine',return_value=engine):
            self.assertEqual(av.createAlternateVersePages(self.folder,['GEN'],self.state,'parallel'),1)
        page = (self.folder/'GEN/C1V3.htm').read_text()
        self.assertIn('In first (first numbering)',page)
        self.assertIn('In second (second numbering)',page)
        self.assertIn('href="C1V1.htm#Top"',page)
        self.assertIn('href="C1V2.htm#Top"',page)
        self.assertNotIn('rel="canonical"',page)

    def test_unmapped_reference_is_reported_not_guessed(self):
        engine = self.engine(('native',{'maxVerses':{'GEN':[3]}}))
        self.page('GEN',1,1)
        with patch.object(av,'get_default_mapping_engine',return_value=engine), self.assertLogs(level='WARNING'):
            self.assertEqual(av.createAlternateVersePages(self.folder,['GEN'],self.state,'parallel'),0)
        self.assertFalse((self.folder/'GEN/C1V3.htm').exists())

    def test_cross_book_copy_preserves_relative_and_fragment_links(self):
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[1]}}, {
            'eng':{'maxVerses':{'GEN':[1]},'identityBooks':{'GEN':'GEN'}},
            'native':{'maxVerses':{'EXO':[1]},'mappedVerses':{'EXO 1:1':'GEN 1:1'}}})
        self.state.BibleVersions = ['LV']
        self.state.BibleVersifications = {'LV':'native'}
        self.state.preloadedBibles = {'LV':SimpleNamespace(availableBBBs={'EXO'},books={})}
        self.page('GEN',1,1)
        with patch.object(av,'get_default_mapping_engine',return_value=engine):
            self.assertEqual(av.createAlternateVersePages(self.folder,['EXO'],self.state,'parallel'),1)
        page = (self.folder/'EXO/C1V1.htm').read_text()
        self.assertIn('rel="canonical" href="../GEN/C1V1.htm"',page)
        self.assertIn('href="../GEN/C1V1.htm#Top"',page)
        self.assertIn('src="../GEN/picture.png"',page)
        self.assertIn('href="#fn1"',page)
        self.assertIn('href="../../ref/word.htm#Top"',page)

    def test_non_english_navigation_uses_its_own_targets_and_explanation(self):
        self.state.navigationVersification = 'OET-LV'
        self.state.BibleVersifications['OET-LV'] = 'eng'
        for verse in range(19,25):
            self.page('MAL',3,verse)
        self.assertEqual(av.createAlternateVersePages(self.folder,['MAL'],self.state,'parallel'),6)
        page = (self.folder/'MAL/C4V1.htm').read_text()
        self.assertIn('OET-LV MAL 3:19',page)
        self.assertNotIn('OET-RV / English',page)

    def test_profiles_respect_build_books_and_explicit_source_layouts(self):
        self.state.BibleVersions.append('BrTr')
        self.state.BibleVersifications['BrTr'] = 'lxx'
        self.state.preloadedBibles['BrTr'] = SimpleNamespace(availableBBBs={'EZR','NEH'},books={})
        self.state.BibleSourceBookLayouts['BrTr'] = {'EZN':((1,10,'EZR',0),(11,23,'NEH',-10))}
        profiles = av._sourceProfiles(self.state,['MAL','NEH'])
        self.assertEqual(profiles, {('OET-LV','MAL'):{'OET-LV'}, ('lxx','EZN'):{'BrTr'}})

    def test_combined_lxx_storage_address_maps_to_other_book(self):
        self.state.BibleVersions = ['BrLXX']
        self.state.BibleVersifications = {'BrLXX':'lxx'}
        self.state.preloadedBibles = {'BrLXX':SimpleNamespace(availableBBBs={'EZR'},books={})}
        self.state.BibleSourceBookLayouts = {'BrLXX':{'EZN':((1,23,'EZR',0),)}}
        self.page('NEH',1,1)
        with self.assertLogs(level='WARNING'):
            av.createAlternateVersePages(self.folder,['EZR','NEH'],self.state,'parallel')
        page = (self.folder/'EZR/C11V1.htm').read_text()
        self.assertIn('About verse numbering: EZR 11:1',page)
        self.assertIn('href="../NEH/C1V1.htm#Top"',page)
        self.assertFalse((self.folder/'EZN').exists())

    def test_parent_generators_add_aliases_after_serial_and_forked_jobs(self):
        # Execute the real parent functions; tiny book jobs stand in for the
        # expensive verse renderers. The final alias pass and files are real.
        builders = (('createParallelVersePages','createParallelVersePagesForBook'),
                    ('createOETInterlinearPages','createOETInterlinearVersePagesForBook'))
        for module, perBook in builders:
            for processes in (1,2):
                with self.subTest(module=module,processes=processes):
                    self.folder = self.root / f'{module}{processes}'
                    self.state.allBBBs = ['MAL']
                    self.state.booksToLoad = {'OET':['MAL']}
                    self.state.TEST_MODE_FLAG = False
                    self.state.DO_SPELL_CHECKS_FLAG = False
                    self.state.BibleLocations = {}
                    self.state.SUBSTITUTED_VERSIONS_FOLDER = self.root/'cache'
                    self.state.CACHE_SUBSTITUTED_VERSIONS_FLAG = True
                    self.state.LOAD_RESOURCES_FROM_PICKLES_FLAG = True
                    self.state.UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG = False
                    self.state.versesWithImages = defaultdict(list)
                    self.state.possibleUnmatchedProperNames = set()
                    def writeBook(*args):
                        self.malachi()
                        return True
                    namespace = dict(globals(),state=self.state, DEBUGGING_THIS_MODULE=False,
                        createAlternateVersePages=av.createAlternateVersePages,
                        reorderBooksForOETVersions=lambda books:books,
                        getOETTidyBBB=lambda book,**kwargs:book,getOETBookName=lambda book:book,
                        makeBookNavListParagraph=lambda *args:'',
                        makeTop=lambda *args:'<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>',
                        makeBottom=lambda *args:'</body></html>',checkHtml=lambda *args:True,
                        vPrint=lambda *args:None,fnPrint=lambda *args:None,
                        getVerseMetaInfoHtml=lambda *args:'',collectSpellCheckResults=lambda:(),
                        mergeSpellCheckResults=lambda *args:None,
                        **{perBook:writeBook})
                    source = Path(__file__).with_name(module+'.py')
                    functions = [node for node in ast.parse(source.read_text()).body
                        if isinstance(node,ast.FunctionDef) and node.name in (module,f'_{perBook}_MP')]
                    exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),namespace)
                    with patch.object(BibleOrgSysGlobals,'maxProcesses',processes), \
                         patch.object(BibleOrgSysGlobals,'alreadyMultiprocessing',False):
                        self.assertTrue(namespace[module](1,self.folder,self.state))
                    self.assertIn('Malachi text 1.',(self.folder/'MAL/C3V19.htm').read_text())


if __name__ == '__main__':
    unittest.main()
