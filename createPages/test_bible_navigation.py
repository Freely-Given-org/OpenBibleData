#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Bible navigation preserves modes and mapped references without guessing targets.

CHANGELOG:
    2026-11-01 Cover native sections, missing books/verses and the navigation hierarchy.
    2026-11-01 Check that script URLs identify the current navigation content.
    2026-11-01 Keep independent views above the version-specific reading modes.
    2026-11-02 Cover section starts stored as verse bridges and invalid references.
    2026-11-03 Check build-time chapter/verse choices, spacing thresholds and primary anchors.
"""
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
import re
import unittest
from unittest.mock import patch
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats.ESFMBible import ESFMBible
from bibleNavigation import addReferenceNavigation,navigationRoutes,pageReference,preferredReadingHref,studyHref
from html import makeTop
from openbibledata_rust import checkHtmlForMissingStyles
from settings import State
from xml.etree import ElementTree


class StaticReferenceNavigationTests(unittest.TestCase):
    def page(self,mode='byC',chapter='1',verse='1',counts=(4,),chapterBar=''):
        attrs=f' data-chapter="{chapter}" data-verse="{verse}"' if chapter else ''
        verses=''.join(f'<span id="C{c}V{v}">{v}</span>'
            for c,count in enumerate(counts,1) for v in range(1,count+1))
        return ('<html><head></head><body><div class="header" id="bibleNavigation"'
            f' data-mode="{mode}" data-version="OET" data-test="true" data-book="MRK"{attrs}>'
            '<p class="wrkLst"><b aria-current="true">OET</b></p>'
            '<p class="viewLst"><b aria-current="true">By Chapter</b></p></div><!--header-->'
            '<p class="bkLst">TEST OET <span class="selectedBook">MARK</span></p><!--bkLst-->'
            f'{chapterBar}{verses}</body></html>')

    def test_reading_modes_have_static_links_to_existing_verse_anchors(self):
        for mode in ('byC','bySec','byDoc','rel'):
            with self.subTest(mode=mode):
                page=addReferenceNavigation(self.page(mode=mode))
                root=ElementTree.fromstring(page)
                row=root.find('.//p[@data-nav-verses="1"]')
                self.assertEqual([a.get('href') for a in row.findall('.//a')],
                                 ['#C1V1','#C1V2','#C1V3','#C1V4'])
                self.assertEqual(row.find('./span[@data-nav-current="true"]').get('data-nav-verse'),'C1V1')
                self.assertIn('data-nav-chapter="1" data-nav-current="true"',page)
                self.assertNotIn('aria-current',ElementTree.tostring(row,encoding='unicode'))
                self.assertEqual(checkHtmlForMissingStyles(mode,page),[])

    def test_long_document_rows_keep_spacing_and_all_chapters_available_in_html(self):
        page=addReferenceNavigation(self.page(mode='byDoc',chapter=None,counts=(40,41,61,81,101)))
        root=ElementTree.fromstring(page)
        for chapter,step,last in ((1,1,40),(2,2,41),(3,3,61),(4,4,81),(5,5,101)):
            row=root.find(f'.//p[@data-nav-verses="{chapter}"]')
            self.assertEqual([a.text for a in row.findall('.//a')],
                             [f'V{v}' for v in range(1,last+1,step)])
            self.assertTrue(all(span.text=='\u2003' for span in row.findall('span')))
            self.assertIsNone(row.find('./span[@data-nav-current]'))
        self.assertEqual([a.get('href') for a in root.findall('.//p[@aria-label="Chapters"]//a')],
                         [f'#C{c}V1' for c in range(1,6)])

    def test_section_top_and_bottom_bars_keep_other_chapter_destinations(self):
        bar='<p class="chLst"><a href="MRK_S2.htm#Top">C1</a> <a href="MRK_S4.htm#Top">C2</a></p><!--chLst-->'
        original=self.page(mode='bySec',counts=(4,3),chapterBar=bar).replace('</body>',bar+'</body>')
        page=addReferenceNavigation(original)
        root=ElementTree.fromstring(page)
        for row in root.findall('.//p[@class="chLst"]'):
            self.assertEqual(row.find('./span[@data-nav-current="true"]/a').get('href'),'MRK_S2.htm#Top')
            self.assertEqual(row.find('./span[@data-nav-chapter="2"]/a').get('href'),'MRK_S4.htm#Top')
        for name in ('wrkLst','viewLst','bkLst'):
            pattern=fr'<p class="{name}">.*?</p>'
            self.assertEqual(re.search(pattern,page)[0],re.search(pattern,original)[0])

    def test_primary_verse_anchors_are_deduplicated_without_inventing_bridge_members(self):
        page=self.page(mode='rel',counts=()).replace('</body>',
            '<span id="aC1V0"></span><span id="aC1V1"></span><span id="aC1V3a"></span>'
            '<span id="C1V1"></span></body>')
        root=ElementTree.fromstring(addReferenceNavigation(page))
        row=root.find('.//p[@data-nav-verses="1"]')
        self.assertEqual([a.get('href') for a in row.findall('.//a')],['#aC1V0','#aC1V1','#aC1V3a'])

    def test_introductions_and_study_pages_do_not_gain_reading_controls(self):
        for mode,chapter in (('byC','-1'),('par','1'),('lst','1'),('ilr','1')):
            with self.subTest(mode=mode,chapter=chapter):
                self.assertNotIn('bibleReferenceChoices',addReferenceNavigation(self.page(mode=mode,chapter=chapter)))
        page=self.page(mode='ilr',chapterBar='<p class="chLst"><a href="C2V1.htm">Sg2</a></p><!--chLst-->')
        self.assertIn('<p class="chLst">TEST InterlinearVerse MRK <a',addReferenceNavigation(page))

    def test_legacy_verse_and_chapter_targets_identify_the_same_choices(self):
        page=self.page(counts=()).replace('</body>',
            '<span id="V1"></span><span id="aC1"></span><span class="c" id="C1V1"></span>'
            '<span id="V2"></span><span class="v" id="C1V2"></span></body>')
        result=addReferenceNavigation(page)
        root=ElementTree.fromstring(result)
        for anchor in ('V1','V2','aC1','C1V1','C1V2'):
            self.assertEqual(root.find(f'.//span[@id="{anchor}"]').get('data-nav-reference'),'1')
        self.assertIn('body:has(#C1V2:target, #V2:target)',result)


class BibleNavigationTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.folder=Path(temp.name)
        self.state=State();self.state.TEST_MODE_FLAG=True
        self.state.BibleVersions=['OET','OET-RV','OET-LV','T4T','SR-GNT']
        self.state.booksToLoad={version:['ALL'] for version in self.state.BibleVersions}
        self.state.preloadedBibles={};self.state.allBBBs=['MAL','MRK']
        self.state.sectionsListsForSections={}
        self.state.TEST_VERSIONS_ONLY=None
        for version,book,content in (
            ('OET-RV','MAL','\\c 4\n\\s1 A section\n\\v 1 Coming.\n\\v 2 Dawn.\n'),
            ('OET-LV','MAL','\\c 3\n\\s1 A different section\n\\v 19 Coming.\n\\v 20 Dawn.\n'),
            ('T4T','MAL','\\c 4\n\\v 1 Coming.\n'),
            ('SR-GNT','MRK','\\c 1\n\\v 1 Beginning.\n')):
            folder=self.folder/version;folder.mkdir()
            (folder/f'{book}.ESFM').write_text(f'\\id {book}\n\\h Example\n{content}')
            bible=ESFMBible(folder,givenAbbreviation=version,versification=self.state.BibleVersifications[version])
            with patch.object(BibleOrgSysGlobals,'verbosityLevel',0):bible.loadBooks()
            self.state.preloadedBibles[version]=bible
        self.state.sectionsListsForSections={
            'OET-RV':{'MAL':[(7,'4','1','4','2','Section','s1',None,None,'MAL_S7.htm')]},
            'OET-LV':{'MAL':[(9,'3','19','3','20','Section','s1',None,None,'MAL_S9.htm')]}}

    def test_switch_keeps_section_mode_and_uses_target_section_number(self):
        routes=navigationRoutes(2,('MAL','4','1'),'OET-RV','OET-LV',self.state)
        self.assertEqual(routes['bySec'],'../../OET-LV/bySec/MAL_S9.htm#Top')
        self.assertEqual(routes['byC'],'../../OET-LV/byC/MAL_C3.htm#C3V19')
        top=makeTop(2,'OET-RV','section','bySec/MAL.htm#C4V1',self.state)
        link=re.search(r'<a[^>]*data-bible-version="OET-LV"[^>]*>',top)[0]
        self.assertIn('href="../../OET-LV/bySec/MAL_S9.htm#Top"',link)
        self.assertNotIn('MAL_S7',link)

    def test_combined_oet_uses_rv_section_and_chapter_anchors(self):
        routes=navigationRoutes(2,('MAL','3','19'),'OET-LV','OET',self.state)
        self.assertEqual(routes['bySec'],'../../OET/bySec/MAL_S7.htm#Top')
        self.assertEqual(routes['byDoc'],'../../OET/byDoc/MAL.htm#C4V1')

    def test_missing_modes_and_books_keep_valid_parent_destinations(self):
        routes=navigationRoutes(2,('MAL','4','1'),'OET-RV','T4T',self.state)
        self.assertNotIn('bySec',routes)
        self.assertEqual(routes['byC'],'../../T4T/byC/MAL_C4.htm#C4V1')
        missing=navigationRoutes(2,('MAL','4','1'),'OET-RV','SR-GNT',self.state)
        self.assertEqual(missing['byC'],'../../SR-GNT/byC/')
        self.assertNotIn('MAL',' '.join(missing.values()))
        self.state.booksToLoad['OET-LV']=['MRK']
        omitted=navigationRoutes(2,('MAL','4','1'),'OET-RV','OET-LV',self.state)
        self.assertNotIn('MAL',' '.join(omitted.values()))

    def test_missing_verse_falls_back_to_book_without_a_false_anchor(self):
        routes=navigationRoutes(2,('MAL','4','2'),'OET-RV','T4T',self.state)
        self.assertEqual(routes['byC'],'../../T4T/byC/MAL.htm#Top')

    def test_all_bible_page_types_put_modes_after_versions_and_keep_context(self):
        for pageType,version,filename,reference in (
            ('chapter','OET-RV','byC/MAL_C4.htm',()),('book','OET-RV','byDoc/MAL.htm',()),
            ('section','OET-RV','bySec/MAL.htm#C4V1',()),
            ('parallelVerse',None,None,('MAL','4','1')),('simpleVerse',None,None,('MAL','4','1')),
            ('interlinearVerse',None,None,('MAL','4','1')),('relatedPassage','OET-RV',None,('MAL','4','1'))):
            with self.subTest(pageType=pageType):
                top=makeTop(2,version,pageType,filename,self.state,reference)
                if pageType in ('parallelVerse','simpleVerse','interlinearVerse','relatedPassage'):
                    self.assertNotIn('class="viewLst"',top)
                else:
                    self.assertLess(top.index('class="wrkLst"'),top.index('class="viewLst"'))
                    modes=re.search(r'<p class="viewLst">(.*?)</p>',top)[1]
                    self.assertTrue(modes.startswith('TEST\u2003OET-RV\u2003'))
                    self.assertNotIn('>Parallel<',modes)
                versions=re.search(r'<p class="wrkLst">(.*?)</p>',top)[1]
                self.assertIn('>Parallel<',versions)
                self.assertEqual(versions.count('class="independentView"'),8)
                scriptVersion=sha256(Path(__file__).with_name('bibleNavigation.js').read_bytes()).hexdigest()[:12]
                self.assertIn(f'bibleNavigation.js?v={scriptVersion}"',top)
                self.assertEqual(checkHtmlForMissingStyles(pageType,top),[])
                self.assertIn('data-book="MAL"',top)
                if pageType=='book':self.assertIn('OET-LV/byDoc/MAL.htm#Top',top)
                else:self.assertIn('OET-LV/byC/MAL_C3.htm#C3V19',top)
                if pageType in ('parallelVerse','simpleVerse','interlinearVerse','relatedPassage'):
                    link=re.search(r'<a[^>]*data-bible-version="OET-LV"[^>]*>',top)[0]
                    self.assertIn('href="../../OET-LV/"',link)

    def test_beside_the_verse_links_prefer_sections_and_keep_interior_anchors(self):
        self.assertEqual(preferredReadingHref(2,'OET-LV','MAL','3','20',self.state),
                         '../../OET-LV/bySec/MAL_S9.htm#C3V20')
        self.assertEqual(preferredReadingHref(2,'T4T','MAL','4','1',self.state),
                         '../../T4T/byC/MAL_C4.htm#C4V1')

    def test_study_links_reverse_imported_book_layout(self):
        self.state.BibleSourceBookLayouts={'OET-LV':{'MAL':[(1,3,'EST',0)]}}
        self.assertEqual(studyHref(2,'par',('EST','3','19'),'OET-LV',self.state),
                         '../../par/MAL/C4V1.htm#Top')

    def test_related_header_uses_first_verse_of_bridge(self):
        for verse in ('1-2','1–2'):
            with self.subTest(verse=verse):
                top=makeTop(2,'OET-RV','relatedPassage',None,self.state,('MAL','4',verse))
                self.assertIn('data-chapter="4" data-verse="1"',top)
                for mode in ('par','lst','ilr'):
                    self.assertIn(f'data-bible-mode="{mode}" href="../../{mode}/MAL/C4V1.htm#Top"',top)
                self.assertIn('data-nav-byc="../../OET-LV/byC/MAL_C3.htm#C3V19"',top)

    def test_bridge_start_is_mapped_before_choosing_navigation_destination(self):
        self.assertEqual(studyHref(2,'par',('MAL','3','19-20'),'OET-LV',self.state),
                         '../../par/MAL/C4V1.htm#Top')
        for source,reference in (('OET-RV',('MAL','4','1-2')),(None,('MAL','4','1-2'))):
            with self.subTest(source=source):
                routes=navigationRoutes(2,reference,source,'OET-LV',self.state)
                self.assertEqual(routes['byC'],'../../OET-LV/byC/MAL_C3.htm#C3V19')
                self.assertEqual(routes['bySec'],'../../OET-LV/bySec/MAL_S9.htm#Top')

    def test_unrecognised_reference_keeps_safe_parent_navigation(self):
        for reference in (('MAL','4','?'),('MAL','4','1-'),('MAL','4','2-1'),('MAL','?','1')):
            for source in ('OET-RV',None):
                with self.subTest(reference=reference,source=source):
                    self.assertEqual(studyHref(2,'par',reference,source,self.state),'../../par/')
                    routes=navigationRoutes(2,reference,source,'OET-LV',self.state)
                    self.assertEqual(routes['byC'],'../../OET-LV/byC/MAL.htm#Top')
                    self.assertNotIn('#C',' '.join(routes.values()))

    def test_page_reference_parsing_retains_selected_book(self):
        self.assertEqual(pageReference('byC/MRK.htm'),('MRK',))
        self.assertEqual(pageReference('byDoc/MRK.htm'),('MRK',))
        self.assertEqual(pageReference('byC/MRK_Intro.htm'),('MRK','-1','0'))
        self.assertEqual(pageReference('bySec/MAL.htm#C3V19'),('MAL','3','19'))


if __name__=='__main__':unittest.main()
