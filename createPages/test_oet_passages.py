"""Offline passage and page-builder regressions, using real BOS ESFM text/indexes.

The recording renderer exercises addresses, grouping, links and note isolation;
it does not replace the server's full-site HTML/layout validation.

CHANGELOG:
    2026-10-16 Cover Luther mapping; use KJV for count-only failure fixtures.
    2026-10-22 Use Original for unverified-profile fixtures after KJV OT support.
"""
import ast
from collections import defaultdict
import logging
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
import BibleOrgSys.Reference.BibleVersification as bv
from BibleOrgSys.Internals.InternalBiblePassages import passageReferencesFromEntries
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, VersificationMappingEngine, VersificationMappingError,
)
import bos_books_codes_py

import oetPassages as op
from navigation import mapHtmlLinks
import versification as vf
from settings import State


class OETPassageTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = State()
        self.rendered = []
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.addCleanup(vf._mapReference.cache_clear)
        renderer = SimpleNamespace(convertVerseEntryListToHtml=self.render)
        customisations = SimpleNamespace(do_OET_RV_HTMLcustomisations=lambda _,h: h,
                                        do_OET_LV_HTMLcustomisations=lambda _,h: h)
        self.mocks = patch.dict(sys.modules, openbibledata_rust=renderer, html=customisations)
        self.mocks.start()
        self.addCleanup(self.mocks.stop)

    def load(self, BBB, version, text):
        folder = self.root / f'{version}-{BBB}'
        folder.mkdir()
        (folder / f'{BBB}.esfm').write_text(
            f'\\id {BBB}\n\\h {BBB}\n\\mt1 {version} header.\n'
            f'\\is1 Introduction\n\\ip {version} introduction.\n{text}')
        bible = ESFMBible(folder, givenAbbreviation=version,
                         versification='eng' if version == 'OET-RV' else 'org')
        bible.loadBooks()
        return bible

    def render(self, level, version, reference, kind, context, entries, **kwargs):
        self.rendered.append((version, reference, tuple((e.getMarker(),e.getCleanText()) for e in entries)))
        BBB, C, *_ = reference
        bits = []
        for entry in entries:
            marker, value = entry.getMarker(), entry.getCleanText()
            if marker == 'c':
                C = value
            elif marker == 'v':
                bits.append(f'<span id="C{C}V{value}"><a title="Go to verse in parallel view" '
                            f'href="../../par/{BBB}/C{C}V{value}.htm#Top">{value}</a></span>')
            elif marker in ('v~','d','ip','mt1'):
                bits.append(f'<p>{value}</p>')
        # Real converter note counters restart on each invocation.
        bits.append('<a href="#fn1">note</a><p id="fn1">A note</p>'
                    '<a href="#xr1">ref</a><p id="xr1">A reference</p>')
        if len(reference) == 3 and reference[1] != '-1':
            bits.append(f'<a href="#C{reference[1]}V{reference[2]}">Return</a>')
        return mapHtmlLinks(''.join(bits), version, level, kwargs['state'],
            segmentType=kind, reference=reference, navigationVersion=kwargs.get('navigationVersion'))

    def renderLV(self, lv, rv, reference):
        entries, _context = rv.getContextVerseData(reference)
        return op.renderOETLVPassage(2, lv, reference, entries, 'section', self.state, {})

    def test_malachi_four_maps_all_six_verses_to_chapter_three(self):
        rv = self.load('MAL','OET-RV', '\\c 4\n\\s1 Ending\n\\p\n' +
                       ''.join(f'\\v {v} RV-{v}.\n' for v in range(1,7)))
        lv = self.load('MAL','OET-LV', '\\c 3\n\\nb\n' +
                       ''.join(f'\\v {v} LV-{v}.\n' for v in range(1,25)))
        html, first = self.renderLV(lv,rv,('MAL','4'))
        self.assertEqual(first, ('MAL','3','19'))
        self.assertIn('LV-19.', html)
        self.assertIn('LV-24.', html)
        self.assertNotIn('LV-18.', html)
        self.assertIn('par/MAL/C4V1.htm', html)
        self.assertIn('Literal Version MAL 3:19', html)
        self.assertNotIn('par/MAL/C3V19.htm', html)
        self.assertIn('id="LV0_0_C3V19"', html)
        self.assertIn('href="#LV0_0_C3V19"', html)

    def test_chapter_boundary_and_disjoint_native_chapters(self):
        rv = self.load('GEN','OET-RV', '\\c 31\n\\p\n\\v 54 RV-54.\n\\v 55 RV-55.\n')
        lv = self.load('GEN','OET-LV', '\\c 31\n\\nb\n\\v 54 Last.\n'
                       '\\c 32\n\\nb\n\\v 1 Boundary.\n\\v 2 Not requested.\n')
        html, first = self.renderLV(lv,rv,('GEN','31'))
        self.assertEqual(first, ('GEN','31','54'))
        self.assertIn('Boundary.',html)
        self.assertNotIn('Not requested.',html)
        self.assertEqual([r for v,r,e in self.rendered], [('GEN','31','54'),('GEN','32','1')])
        self.assertIn('par/GEN/C31V55.htm',html)

    def test_titles_declared_separately_or_included_in_verse_one(self):
        rv = self.load('PSA','OET-RV', '\\c 3\n\\d Title three.\n\\q1\n\\v 1 RV three.\n'
                       '\\c 98\n\\d Title ninety-eight.\n\\q1\n\\v 1 RV ninety-eight.\n')
        lv = self.load('PSA','OET-LV', '\\c 3\n\\nb\n\\v 1 Separate title.\n\\v 2 LV three.\n'
                       '\\c 98\n\\nb\n\\v 1 Title and LV ninety-eight.\n')
        html, _ = self.renderLV(lv,rv,('PSA','3'))
        self.assertIn('Separate title.',html)
        self.assertIn('LV three.',html)
        self.assertIn('par/PSA/C3V0.htm',html)
        html, _ = self.renderLV(lv,rv,('PSA','98'))
        self.assertIn('Title and LV ninety-eight.',html)
        self.assertNotIn('unavailable',html)
        allEntries, _ = rv.getContextVerseData(('PSA',))
        self.assertEqual(passageReferencesFromEntries(('PSA','-1'),allEntries,'eng'),
                         (('PSA','3','0',None),('PSA','3','1',None),('PSA','98','1',None)))

    def test_whole_merged_group_is_mapped_together(self):
        rv = self.load('GEN','OET-RV','\\c 1\n\\p\n\\v 1 One.\n\\v 2 Two.\n')
        lv = self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1 Merged.\n')
        engine = VersificationMappingEngine({'maxVerses': {'GEN':[1]}}, {
            'eng': {'maxVerses': {'GEN':[2]}, 'groupMappings':[{'source':'GEN 1:1-2','target':'GEN 1:1'}]},
            'org': {'maxVerses': {'GEN':[1]}, 'identityBooks': {'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            entries,_ = rv.getContextVerseData(('GEN','1'))
            parts = op.mappedOETLVPortions(lv,('GEN','1'),entries,self.state,{})
            self.assertEqual(len(parts),1)
            one,_ = rv.getContextVerseData(('GEN','1','1'))
            html,_ = op.renderOETLVPassage(2,lv,('GEN','1','1'),one,'section',self.state,{})
            self.assertIn('Merged.',html)
            self.assertIn('Combined passage: English GEN 1:1–2',html)
            self.assertIn('native GEN 1:1',html)

    def test_disjoint_group_never_fetches_intervening_text(self):
        rv = self.load('GEN','OET-RV','\\c 1\n\\p\n\\v 1 Source.\n\\v 2 Also source.\n')
        lv = self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1 First.\n\\v 2 Excluded.\n\\v 3 Last.\n')
        engine = VersificationMappingEngine({'maxVerses': {'GEN':[3]}}, {
            'eng': {'maxVerses': {'GEN':[2]},
                    'mappedVerses':{'GEN 1:1':'GEN 1:1','GEN 1:2':'GEN 1:3'}},
            'org': {'maxVerses': {'GEN':[3]},'identityBooks': {'GEN':'GEN'}},
        })
        with patch.object(bv,'get_default_mapping_engine',return_value=engine):
            html,_ = self.renderLV(lv,rv,('GEN','1'))
        self.assertIn('First.',html)
        self.assertIn('Last.',html)
        self.assertNotIn('Excluded.',html)
        self.assertEqual(len(self.rendered),2)

    def test_stored_bridges_and_whole_verses_with_suffixes(self):
        rv = self.load('GEN','OET-RV','\\c 1\n\\p\n\\v 1 One.\n\\v 2 Two.\n\\v 3 Three.\n')
        lv = self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1-2 Bridge.\n'
                       '\\v 3a First half.\n\\v 3b Second half.\n')
        html,_ = self.renderLV(lv,rv,('GEN','1'))
        self.assertEqual(html.count('Bridge.'),1)
        self.assertEqual(html.count('First half.'),1)
        self.assertEqual(html.count('Second half.'),1)

    def test_chunking_preserves_every_source_entry_and_unique_note_ids(self):
        rv = self.load('GEN','OET-RV','\\c 1\n\\s1 First\n\\p\n\\v 1 One.\n'
                       '\\s1 Second\n\\p\n\\v 2 Two.\n\\c 2\n\\p\n\\v 1 Three.\n')
        lv = self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1 Uno.\n\\v 2 Dos.\n'
                       '\\c 2\n\\nb\n\\v 1 Tres.\n')
        chunks=list(op.oetRVChunks(rv,'GEN'))
        full,_=rv.getContextVerseData(('GEN',))
        flatten=lambda entries: [(e.getMarker(),e.getCleanText()) for e in entries]
        self.assertEqual([item for r,e,c in chunks for item in flatten(e)],flatten(full))
        html,_=op.renderOETSideBySideChunks(2,rv,lv,'GEN','book',self.state)
        ids=re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))
        for target in re.findall(r'href="#([^"]+)"',html):
            if 'fn' in target or 'xr' in target:
                self.assertIn(target,ids)
        self.assertEqual(html.count('OET-LV header.'),1)
        self.assertEqual(html.count('OET-LV introduction.'),1)

    def test_no_fallback_or_partial_text_when_mapping_or_text_unavailable(self):
        rv = self.load('MAL','OET-RV','\\c 4\n\\p\n\\v 1 First.\n\\v 2 Second.\n')
        lv = self.load('MAL','OET-LV','\\c 3\n\\nb\n\\v 19 Incomplete.\n')
        html,_=self.renderLV(lv,rv,('MAL','4'))
        self.assertIn('not available',html)
        self.assertNotIn('Incomplete.',html)
        self.assertEqual(self.rendered,[])
        lv.setVersificationSystem('Original')
        html,_=self.renderLV(lv,rv,('MAL','4'))
        self.assertIn('alignment unavailable (unsupported)',html)
        self.assertEqual(self.rendered,[])

    def builder(self, filename, name, section=False):
        namespace=dict(globals(),
            defaultdict=defaultdict, os=os, BibleOrgSysGlobals=BibleOrgSysGlobals,
            bos_books_codes_py=bos_books_codes_py,
            DEBUGGING_THIS_MODULE=False, NEWLINE='\n',
            ESFMBible=ESFMBible if section else SimpleNamespace(ESFMBible=ESFMBible),
            vPrint=lambda *a: None,dPrint=lambda *a: None,fnPrint=lambda *a: None,
            getOETTidyBBB=lambda b,**k: b,
            makeBookNavListParagraph=lambda *a: '',
            makeTop=lambda *a: '<html><body>',makeBottom=lambda *a: '</body></html>',
            checkHtml=lambda *a,**k: True,removeDuplicateCVids=lambda h: h,
            convertVerseEntryListToHtml=self.render,
            do_OET_RV_HTMLcustomisations=lambda _,h:h,
            getBibleMapperMaps=lambda *a:'',findSectionNumber=lambda *a:0,
            SECTION_REASON_NAME_DICT={},
            **{name:getattr(op,name) for name in ('renderOETSideBySideChunks','renderOETLVPassage','oetLVSourceLink')})
        source=Path(__file__).with_name(filename)
        function=next(n for n in ast.parse(source.read_text()).body
                      if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        return namespace[name]

    def test_topic_range_and_whole_chapter_use_mapped_passages(self):
        rv = self.load('ISA','OET-RV','\\c 9\n\\p\n' + ''.join(f'\\v {v} RV-{v}.\n' for v in range(2,8)))
        lv = self.load('ISA','OET-LV','\\c 9\n\\p\n' + ''.join(f'\\v {v} LV-{v}.\n' for v in range(1,8)))
        self.state.preloadedBibles = {'OET-RV':rv,'OET-LV':lv}
        namespace = dict(globals(), State=State, DEBUGGING_THIS_MODULE=False, NEWLINE='\n',
            TOPIC_LIST=[('Advent','advent.htm',['ISA_9:2-7'])],
            fnPrint=lambda *a:None, vPrint=lambda *a:None, dPrint=lambda *a:None,
            getOETTidyBBB=lambda b,*a,**k:b, makeTop=lambda *a:'<html>', makeBottom=lambda *a:'</html>',
            convertVerseEntryListToHtml=self.render, do_OET_RV_HTMLcustomisations=lambda _,h:h,
            renderOETLVPassage=op.renderOETLVPassage, checkHtml=lambda *a,**k:True,
            removeDuplicateCVids=lambda h:h)
        source=Path(__file__).with_name('createTopicPages.py')
        function=next(n for n in ast.parse(source.read_text()).body
                      if isinstance(n,ast.FunctionDef) and n.name=='createTopicPage')
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        namespace['createTopicPage'](1,self.root,0,self.state)
        html=(self.root/'advent.htm').read_text()
        self.assertIn('LV-1.',html)
        self.assertIn('LV-6.',html)
        self.assertNotIn('LV-7.',html)
        # A whole English chapter can be stored under a different LV chapter.
        rv = self.load('MAL','OET-RV','\\c 4\n\\p\n'+''.join(f'\\v {v} RV-{v}.\n' for v in range(1,7)))
        lv = self.load('MAL','OET-LV','\\c 3\n\\p\n'+''.join(f'\\v {v} LV-{v}.\n' for v in range(19,25)))
        self.state.preloadedBibles = {'OET-RV':rv,'OET-LV':lv}
        namespace['TOPIC_LIST']=[('Ending','ending.htm',['MAL_4'])]
        namespace['createTopicPage'](1,self.root,0,self.state)
        html=(self.root/'ending.htm').read_text()
        self.assertIn('LV-19.',html)
        self.assertIn('LV-24.',html)

    def test_all_three_page_builders_use_mapped_malachi_passage(self):
        rv=self.load('MAL','OET-RV',''.join(
            f'\\c {c}\n\\s1 Chapter {c}\n\\p\n' +
            ''.join(f'\\v {v} English-{c}-{v}.\n' for v in range(1,7 if c==4 else 2))
            for c in range(1,5)))
        lv=self.load('MAL','OET-LV',''.join(
            f'\\c {c}\n\\nb\n'+''.join(f'\\v {v} Native-{c}-{v}.\n' for v in range(1,25 if c==3 else 2))
            for c in range(1,4)))
        for bible in (rv,lv):
            bible.discover(); bible.makeSectionIndex()
        self.state.BBBLinks={'OET':[]}
        self.state.BBBsToProcess={'OET':['MAL']}
        self.state.booksToLoad={'OET':['MAL'],'OET-RV':['MAL'],'OET-LV':['MAL']}
        self.state.preloadedBibles={'OET-RV':rv,'OET-LV':lv}
        entries,context=rv.getContextVerseData(('MAL','4'))
        self.state.sectionsListsForSections={'OET-RV':{'MAL':[(0,'4','1','4','6','Ending','s1',context,entries,'MAL_S0.htm')]}}
        self.state.sectionsListsForHeaders={'OET-RV':{'MAL':[('4','1','Ending','s1','MAL_S0.htm')]}}
        for filename,name,output in (
            ('createBookPages.py','_createOETBookPagesForBook','MAL.htm'),
            ('createChapterPages.py','_writeOETSideBySideChapterBook','MAL_C4.htm'),
            ('createSectionPages.py','createOETSectionPages','MAL_S0.htm')):
            with self.subTest(builder=filename):
                folder=self.root/filename;folder.mkdir()
                section=filename=='createSectionPages.py'
                args=(2,folder,rv,lv,self.state)
                self.builder(filename,name,section)(*args,*(() if section else ('MAL',)))
                html=(folder/output).read_text()
                self.assertIn('Native-3-19.',html)
                self.assertIn('Native-3-24.',html)
                self.assertIn('par/MAL/C4V1.htm',html)
                self.assertNotIn('Unsolved versification',html)
                if filename!='createBookPages.py':
                    self.assertNotIn('Native-3-18.',html)
                    self.assertIn('OET-LV/byDoc/MAL.htm#C3V19',html)
                    self.assertNotIn('OET-LV/byC/MAL_C4.htm',html)


if __name__ == '__main__':
    unittest.main()
