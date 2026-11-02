#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Generate small Parallel and Interlinear books and follow their Psalm links.

CHANGELOG:
    2026-10-26 Cover numbered/unnumbered headings, boundaries and selector lists.
    2026-10-30 Expect Parallel Psalm 1 to link back through its introduction pages.
    2026-10-30 Check title-only verse lists and Parallel navigation through note-only introductions.
    2026-11-02 Start Psalms at verse zero only when heading text exists.
"""
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.USFMBible import USFMBible
import createParallelVersePages as parallelPages
import createOETInterlinearPages as interlinearPages
import createVerseListPages as listPages
from navigation import verseNavigationFirstVerses
from settings import State
from versification import navigationVersification


class PsalmNavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        self.state = State()
        self.state.navigationVersification = 'eng'
        self.state.BibleVersions = ['ASV']
        self.state.TEST_MODE_FLAG = True
        self.state.TEST_VERSIONS_ONLY = None
        self.state.DO_SPELL_CHECKS_FLAG = False
        self.state.booksToLoad = {'OET':['PSA']}
        self.state.versionComments = {}
        self.state.versesWithImages = defaultdict(list)
        self.system = navigationVersification('eng')
        source = self.root/'source'
        source.mkdir()
        # Psalm 11 has an unnumbered d heading; Psalms 1, 2 and 10 have none.
        self.headings = set(range(3,19)) - {10}
        text = '\\id PSA\n\\h Psalms\n'
        for c in range(1,19):
            text += f'\\c {c}\n'
            if c in self.headings:
                text += f'\\d Heading for Psalm {c}.\n'
            text += '\\q1\n' + ''.join(f'\\v {v} Psalm {c} verse {v}.\n'
                for v in range(1,self.system.getNumVerses('PSA',c)+1))
        (source/'19PSA.usfm').write_text(text)
        self.bible = USFMBible(source, givenAbbreviation='ASV', versification='eng')
        self.bible.loadBooks()
        self.state.preloadedBibles = {v:self.bible for v in ('ASV','OET-LV','OET-RV')}
        for module in (parallelPages, interlinearPages, listPages):
            self.stack.enter_context(patch.object(module, 'navigationVersification', return_value=
                SimpleNamespace(getNumChapters=lambda b:18, getNumVerses=self.system.getNumVerses)))
            self.stack.enter_context(patch.object(module, 'makeTop', return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            self.stack.enter_context(patch.object(module, 'makeBottom', return_value='</body></html>'))
            for function in ('getVerseMetaInfoHtml','formatTyndaleBookIntro','formatTyndaleNotes',
                             'getFormattedSILOpenTranslationNotes','formatUnfoldingWordTranslationNotes',
                             'getBibleMapperMaps'):
                if hasattr(module, function):
                    self.stack.enter_context(patch.object(module, function, return_value=''))
        # Navigation uses the real outer loop. Word rendering has separate integration tests.
        self.stack.enter_context(patch.object(interlinearPages, 'createOETInterlinearVerseInner',
                                             return_value='<p>Interlinear fixture.</p>'))

    def render(self, kind):
        folder = self.root/kind
        links = ['<a title="Psalms" href="../PSA/index.htm#Top">PSA</a>']
        if kind == 'par':
            parallelPages.createParallelVersePagesForBook(1, folder, 'PSA', links, ['ASV'], self.state)
        elif kind == 'lst':
            listPages.createVerseListPagesForBook(1, folder, 'PSA', links, ['ASV'], self.state)
        else:
            interlinearPages.createOETInterlinearVersePagesForBook(1, folder, 'PSA', links, self.state)
        return folder

    def paragraph(self, folder, c, v, paragraphId):
        html = (folder/f'PSA/C{c}V{v}.htm').read_text()
        return ElementTree.fromstring(re.search(fr'<p[^>]*id="{paragraphId}"[^>]*>.*?</p>', html)[0])

    def test_chapter_links_prefer_existing_psalm_headings_and_skip_empty_intro_pages(self):
        for kind in ('par','ilr','lst'):
            with self.subTest(kind=kind):
                folder = self.render(kind)
                for anchor in ('Top','BottomNavs'):
                    def arrows(c,v):
                        return {a.text:a.get('href') for a in self.paragraph(folder,c,v,anchor).findall('a')}
                    for c in (3,4,11,14):
                        previousLast = self.system.getNumVerses('PSA',c-1)
                        self.assertEqual(arrows(c,1)['←'], f'C{c}V0.htm#{anchor}')
                        self.assertEqual(arrows(c,0)['↨'], f'C{c-1}V{previousLast}.htm#{anchor}')
                        self.assertEqual(arrows(c,0)['→'], f'C{c}V1.htm#{anchor}')
                        self.assertEqual(arrows(c-1,previousLast)['→'], f'C{c}V0.htm#{anchor}')
                        self.assertEqual(arrows(c-1,1)['►'], f'C{c}V0.htm#{anchor}')
                    self.assertEqual(arrows(4,1)['◄'], f'C3V0.htm#{anchor}')
                    if kind=='par':
                        self.assertEqual(arrows(2,1)['←'], f'C2V0.htm#{anchor}')
                        self.assertEqual(arrows(2,0)['↨'], f'C1V6.htm#{anchor}')
                    else:
                        self.assertEqual(arrows(2,1)['↨'], f'C1V6.htm#{anchor}')
                    self.assertEqual(arrows(9,1)['►'], f'C10V1.htm#{anchor}')
                    if kind == 'par':
                        self.assertEqual(arrows(1,1)['←'], f'C1V0.htm#{anchor}')
                        self.assertEqual(arrows(1,0)['←'], f'Intro.htm#{anchor}')
                    elif kind == 'lst':
                        self.assertEqual(arrows(1,1)['←'], f'Intro.htm#{anchor}')
                    else:
                        self.assertNotIn('←', arrows(1,1))
                    self.assertNotIn('→', arrows(18,50))
                    self.assertNotIn('►', arrows(18,50))
                    if kind in ('par','lst'):
                        self.assertEqual(arrows(3,4)['◄'], f'C3V0.htm#{anchor}')
                for c in (3,11,18): # Psalm 18 also exercises the abbreviated verse list.
                    verses = self.paragraph(folder,c,1,'vsLst')
                    self.assertIn(f'C{c}V0.htm#Top', [a.get('href') for a in verses.findall('a')])
                for c in (1,2,10):
                    verses = self.paragraph(folder,c,1,'vsLst')
                    self.assertEqual(any('V0.htm' in a.get('href') for a in verses.findall('a')), kind=='par')
                for filename in ('PSA/index.htm','PSA.htm','PSA/C1V1.htm'):
                    html = (folder/filename).read_text()
                    for c in (3,11):
                        self.assertRegex(html, fr'href="(?:PSA/)?C{c}V0.htm#[^"]+">Sg{c}</a>')
                    for c in (2,10):
                        self.assertRegex(html, fr'href="(?:PSA/)?C{c}V1.htm#[^"]+">Sg{c}</a>')
                # Every intra-book link created by either loop resolves to a built file.
                for page in (folder/'PSA').glob('*.htm'):
                    for href in re.findall(r'href="(C\d+V\d+\.htm)#[^"]*"', page.read_text()):
                        self.assertTrue((page.parent/href).is_file(), (page.name,href))
                if kind == 'par':
                    self.assertIn('Heading for Psalm 11.', (folder/'PSA/C11V0.htm').read_text())
                    for c in (3,11):
                        page = (folder/f'PSA/C{c}V0.htm').read_text()
                        self.assertIn(f'lst/PSA/C{c}V0.htm#Top',page)
                        self.assertIn(f'ilr/PSA/C{c}V0.htm#Top',page)
                else:
                    self.assertFalse((folder/'PSA/C10V0.htm').exists())

    def test_heading_detection_respects_navigation_numbering_and_source_presence(self):
        first = verseNavigationFirstVerses('PSA',18,['ASV'],self.state)
        self.assertEqual({c for c,v in first.items() if v==0}, self.headings)
        self.state.navigationVersification = 'Luth'
        first = verseNavigationFirstVerses('PSA',4,['ASV'],self.state)
        self.assertEqual(first, {1:1,2:1,3:1,4:1}) # Native numbered headings already belong to v1.
        self.assertEqual(verseNavigationFirstVerses('MRK',1,[],self.state), {1:1})
        self.state.navigationVersification = 'eng'
        self.state.preloadedBibles = {}
        first = verseNavigationFirstVerses('PSA',11,[],self.state)
        self.assertEqual(first[3],0) # Declared title remains addressable without source text.
        self.assertEqual(first[11],1) # No supplied unnumbered heading.
        first = verseNavigationFirstVerses('PSA',11,[],self.state,requireVerseZeroText=True)
        self.assertTrue(all(v==1 for v in first.values())) # No empty title pages in text-only views.


if __name__ == '__main__':
    unittest.main()
