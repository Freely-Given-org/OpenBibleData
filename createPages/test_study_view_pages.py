#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Generate study views with notes, explicit verse zero, and GHT colours.

CHANGELOG:
    2026-10-30 Check available view links, omitted empty pages, and colour controls.
    2026-11-01 Check Simple-view note links against their full parallel destinations.
    2026-11-01 Verify beside-the-verse version links prefer available sections.
    2026-11-02 Keep internal introduction numbers out of titles and index labels.
    2026-11-02 Exclude Greek/Hebrew editions before processing Latin Laodiceans.
    2026-11-02 Start chapter jumps at verse 1 without removing verse-zero destinations.
"""
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.USFMBible import USFMBible
import createParallelVersePages as parallelPages
import createVerseListPages as listPages
import createOETInterlinearPages as interlinearPages
from settings import State


class StudyViewPageTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals,'verbosityLevel',0))
        self.state = State()
        self.state.navigationVersification = 'eng'
        self.state.BibleVersions = ['ASV','GHT']
        self.state.TEST_MODE_FLAG = True
        self.state.TEST_VERSIONS_ONLY = None
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.state.booksToLoad = {'OET':['MAT']}
        self.state.versionComments = {}
        self.state.versesWithImages = defaultdict(list)
        self.state.preloadedBibles = {}
        for version in ('ASV','GHT','OET-RV','OET-LV'):
            folder = self.root/version
            folder.mkdir()
            first = ('Book of{birth} to{David}. Not forgotten.' if version=='GHT'
                     else 'The first verse. \\f + \\fr 1:1 \\ft A useful note.\\f*')
            zero = '\\v 0 Actual verse zero.\n' if version=='ASV' else ''
            (folder/'40MAT.usfm').write_text(
                '\\id MAT\n\\h Matthew\n\\ip Book introduction.\n'
                '\\c 1\n\\cd An editorial chapter description.\n\\p\n'
                f'\\v 1 {first}\n\\v 2 The second verse.\n'
                f'\\c 2\n{zero}\\p\n\\v 1 Next chapter.\n\\v 2 Final verse.\n')
            bible = USFMBible(folder,givenAbbreviation=version,versification='eng')
            bible.loadBooks()
            self.state.preloadedBibles[version] = bible
        for module in (parallelPages,listPages,interlinearPages):
            self.stack.enter_context(patch.object(module,'navigationVersification',return_value=
                SimpleNamespace(getNumChapters=lambda b:2,getNumVerses=lambda b,c:2)))
            self.stack.enter_context(patch.object(module,'makeTop',return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'
                '<a href="../../ilr/">Interlinear</a>'))
            self.stack.enter_context(patch.object(module,'makeBottom',return_value='</body></html>'))
            for name in ('getVerseMetaInfoHtml','formatTyndaleBookIntro','formatTyndaleNotes',
                         'getFormattedSILOpenTranslationNotes','getBibleMapperMaps'):
                if hasattr(module,name):
                    self.stack.enter_context(patch.object(module,name,return_value=''))
        for module in (parallelPages,interlinearPages):
            self.stack.enter_context(patch.object(module,'formatUnfoldingWordTranslationNotes',
                side_effect=lambda level,book,c,v,*args:'<p>Chapter translation notes.</p>' if v=='0' else ''))
        self.stack.enter_context(patch.object(interlinearPages,'createOETInterlinearVerseInner',
                                             return_value='<p>Interlinear verse.</p>'))

    def render(self):
        links = ['<a title="Matthew" href="../MAT/index.htm#Top">MAT</a>']
        parallelPages.createParallelVersePagesForBook(1,self.root/'par','MAT',links,['ASV','GHT'],self.state)
        listPages.createVerseListPagesForBook(1,self.root/'lst','MAT',links,['ASV','GHT'],self.state)
        interlinearPages.createOETInterlinearVersePagesForBook(1,self.root/'ilr','MAT',links,self.state)

    def page(self,kind,filename):
        return (self.root/kind/'MAT'/filename).read_text()

    def test_version_abbreviations_open_available_sections(self):
        self.state.booksToLoad['ASV']=['ALL']
        self.state.sectionsListsForSections={'ASV':{'MAT':[
            (7,'1','1','1','2','Opening','s1',None,None,'MAT_S7.htm')]}}
        self.render()
        for kind in ('par','lst'):
            self.assertIn('../../ASV/bySec/MAT_S7.htm#C1V2',self.page(kind,'C1V2.htm'))
            self.assertIn('../../ASV/byC/MAT_C2.htm#C2V2',self.page(kind,'C2V2.htm'))

    def test_notes_and_real_verse_zero_have_only_existing_view_links(self):
        self.render()
        intro = self.page('par','Intro.htm')
        for kind in ('par','lst'):
            introduction=self.page(kind,'Intro.htm')
            self.assertIn('<title>MAT Intro ',introduction)
            self.assertNotIn('MAT -1',introduction)
            for index in (self.root/kind/'MAT/index.htm',self.root/kind/'MAT.htm'):
                indexHtml=index.read_text()
                self.assertRegex(indexHtml,r'href="(?:MAT/)?Intro.htm#Top">Intro</a>')
                self.assertNotIn('>-1:0</a>',indexHtml)
        self.assertNotIn('title="Simple verse list view"',intro)
        self.assertNotIn('title="Interlinear verse view"',intro)
        for chapter in (1,2):
            page = self.page('par',f'C{chapter}V0.htm')
            self.assertIn('Chapter translation notes.',page)
            self.assertNotIn('title="Interlinear verse view"',page)
            self.assertEqual('title="Simple verse list view"' in page, chapter==2)
        self.assertFalse((self.root/'lst/MAT/C1V0.htm').exists())
        self.assertFalse((self.root/'ilr/MAT/C1V0.htm').exists())
        self.assertFalse((self.root/'ilr/MAT/C2V0.htm').exists())
        self.assertIn('Actual verse zero.',self.page('lst','C2V0.htm'))
        self.assertNotIn('title="Interlinear verse view"',self.page('lst','C2V0.htm'))
        for anchor in ('Top','BottomNavs'):
            self.assertIn(f'href="C1V1.htm#{anchor}">→',self.page('lst','Intro.htm'))
            self.assertIn(f'href="Intro.htm#{anchor}">←',self.page('lst','C1V1.htm'))
            for kind in ('par','lst','ilr'):
                self.assertIn(f'href="C2V1.htm#{anchor}">→',self.page(kind,'C1V2.htm'))
            for kind in ('par','lst'):
                self.assertIn(f'href="C1V1.htm#{anchor}">→',self.page(kind,'Intro.htm'))
            self.assertIn(f'href="C2V0.htm#{anchor}">←',self.page('par','C2V1.htm'))
            self.assertIn(f'href="C2V0.htm#{anchor}">←',self.page('lst','C2V1.htm'))
        for kind in ('par','lst','ilr'):
            for path in (self.root/kind/'MAT').glob('*.htm'):
                html=path.read_text()
                chapters=re.search(r'<p class="chLst"[^>]*>.*?</p>',html)[0]
                self.assertNotRegex(chapters,r'C\d+V0\.htm')
                for href in re.findall(r'href="([^"]+)"',html):
                    target = href.split('#')[0]
                    if re.fullmatch(r'(?:C\d+V\d+|Intro)\.htm',target) or re.fullmatch(r'../../(?:par|lst|ilr)/MAT/[^/]+\.htm',target):
                        self.assertTrue((path.parent/target).is_file(), (path,href))

    def test_ght_colours_and_toggle_do_not_depend_on_a_greek_source_row(self):
        self.render()
        html = self.page('lst','C1V1.htm')
        for colour in ('grkGen','grkDat','grkNeg'):
            self.assertIn(f'class="{colour}"',html)
        self.assertEqual(html.count('id="coloursButton"'),1)
        self.assertIn('onclick="hide_show_colours()"',html)
        self.assertNotIn('id="coloursButton"',self.page('lst','C1V2.htm'))
        # Both views use the same GHT colour rules.
        for colour in ('grkGen','grkDat','grkNeg'):
            self.assertIn(f'class="{colour}"',self.page('par','C1V1.htm'))

    def test_excluded_translation_cannot_create_an_empty_verse_zero_page(self):
        self.state.TEST_VERSIONS_ONLY = ['GHT']
        self.render()
        self.assertFalse((self.root/'lst/MAT/C2V0.htm').exists())
        self.assertNotIn('title="Simple verse list view"',self.page('par','C2V0.htm'))

    def test_simple_note_callers_open_the_full_parallel_entry(self):
        self.render()
        simple = self.page('lst','C1V1.htm')
        self.assertIn('Note: A useful note.', simple)
        self.assertNotRegex(simple, r'href="#fn[^"]*"')
        self.assertIn('href="../../par/MAT/C1V1.htm#ASV"', simple)
        parallel = self.page('par','C1V1.htm')
        self.assertIn('id="ASV"', parallel)
        self.assertIn('id="fnASV1"', parallel)

    def test_latin_lao_does_not_request_greek_or_hebrew_editions(self):
        source=self.root/'LatinBook';source.mkdir()
        (source/'LAO.usfm').write_text('\\id LAO\n\\h Laodiceans\n\\c 1\n\\p\n\\v 1 First verse.\n\\v 2 Second verse.\n')
        bible=USFMBible(source,givenAbbreviation='ASV',versification='eng');bible.loadBooks()
        self.state.preloadedBibles={'ASV':bible,'OET-RV':None}
        self.state.booksToLoad={'OET':[],'ASV':['LAO']}
        versions=['ASV','SR-GNT','UGNT','SBL-GNT','RP-GNT','TC-GNT','UHB','BrLXX','BrTr']
        originalVersions=versions[:]
        with patch.object(parallelPages,'navigationVersification',return_value=
                SimpleNamespace(getNumChapters=lambda b:1,getNumVerses=lambda b,c:2)), \
             patch.object(parallelPages,'parallelVersePassage',wraps=parallelPages.parallelVersePassage) as passages, \
             patch.object(parallelPages,'verseNavigationFirstVerses',wraps=parallelPages.verseNavigationFirstVerses) as firstVerses:
            parallelPages.createParallelVersePagesForBook(1,self.root/'par','LAO',
                ['<a href="../LAO/index.htm#Top">LAO</a>'],versions,self.state)
        self.assertEqual(firstVerses.call_args.args[2],['ASV'])
        self.assertEqual({call.args[0] for call in passages.call_args_list},{'ASV'})
        page=(self.root/'par/LAO/C1V1.htm').read_text()
        self.assertIn('First verse.',page)
        for version in versions[1:]:self.assertNotIn(f'id="{version}"',page)
        self.assertEqual(versions,originalVersions)


if __name__ == '__main__':
    unittest.main()
