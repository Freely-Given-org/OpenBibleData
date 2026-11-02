#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Regressions for OET and traditional navigation, including generated pages.

CHANGELOG:
    2026-10-24 Match navigation classes when book subgroups and selection share a span.
    2026-10-24 Cover book order, names, destinations and selected-book labels.
    2026-11-01 Cover OET-only 66-book menus, adjacent links and continued generation of extra books.
    2026-11-01 Check selected books on generated reading pages, including GHT.
"""
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

import createBookPages as books
import createChapterPages as chapters
import createSectionPages as sections
from html import makeBookNavListParagraph
from navigation import VERSE_BOOK_NAVIGATION_VIEWS, bookNavigationOrder, oetBookNavigationLinks
from settings import State


def text(element):
    return ''.join(element.itertext())


def links(bookCodes, template='{BBB}.htm#Top'):
    # Deliberately stale labels: the destination determines the book identity.
    return [f'<a title="Old title" href="{template.format(BBB=BBB)}">{BBB}</a>' for BBB in bookCodes]


class BookNavigationTests(unittest.TestCase):
    def setUp(self):
        self.state = SimpleNamespace(TEST_MODE_FLAG=False,
            preloadedBibles={version: None for version in ('OET-RV','OET-LV','BSB','Luth','KJB-1611')})
        self.inputBooks = ['JN3','MAT','GAL','JAM','JHN','JNA','MRK','JN1','JDE','JN2','PSA']
        self.oetOrder = ['PSA','JNA','JHN','MRK','MAT','JAM','GAL','JDE','JN1','JN2','JN3']
        self.traditionalOrder = ['PSA','JNA','MAT','MRK','JHN','GAL','JAM','JN1','JN2','JN3','JDE']

    def test_all_oet_views_include_traditional_abbreviations_in_oet_order(self):
        for version in ('OET','OET-RV','OET-LV','Related OET-RV', *VERSE_BOOK_NAVIGATION_VIEWS):
            with self.subTest(version=version):
                verseView = version in VERSE_BOOK_NAVIGATION_VIEWS
                template = '../{BBB}/index.htm#Top' if verseView else '{BBB}/' if version=='Related OET-RV' else '{BBB}.htm#Top'
                paragraph = ElementTree.fromstring(makeBookNavListParagraph(links(self.inputBooks, template), version, self.state))
                anchors = paragraph.findall('.//a')
                expected = [f'../{BBB}/C1V1.htm#chLst' if verseView else template.format(BBB=BBB) for BBB in self.oetOrder]
                self.assertEqual([a.get('href') for a in anchors], expected)
                byBook = dict(zip(self.oetOrder, anchors))
                for BBB, label in (('JNA','YNA (JNA)'), ('JHN','YHN (JHN)'), ('JAM','YAC (JAM)'), ('JDE','YUD (JUD)'),
                                   ('JN1','1\u202fYHN (1\u202fJHN)'), ('JN2','2\u202fYHN (2\u202fJHN)'), ('JN3','3\u202fYHN (3\u202fJHN)')):
                    self.assertEqual(text(byBook[BBB]), label)
                self.assertEqual(byBook['JHN'].get('title'), 'Yohan/(John)')

    def test_other_versions_use_only_traditional_labels_titles_and_order(self):
        for version in ('BSB','Luth','KJB-1611'):
            with self.subTest(version=version):
                paragraph = ElementTree.fromstring(makeBookNavListParagraph(links(self.inputBooks), version, self.state))
                anchors = paragraph.findall('.//a')
                self.assertEqual([a.get('href') for a in anchors], [f'{BBB}.htm#Top' for BBB in self.traditionalOrder])
                byBook = dict(zip(self.traditionalOrder, anchors))
                for BBB, label, title in (('JNA','JNA','Jonah'), ('JHN','JOHN','John'), ('JAM','JAM','James'), ('JDE','JUDE','Jude'),
                                          ('JN1','1\u202fJHN','1 John'), ('JN2','2\u202fJHN','2 John'), ('JN3','3\u202fJHN','3 John')):
                    self.assertEqual(text(byBook[BBB]), label)
                    self.assertEqual(byBook[BBB].get('title'), title)
                self.assertNotIn('YHN', text(paragraph))

    def test_selected_book_retains_both_names_without_a_self_link(self):
        for version in ('ParallelVerse','InterlinearVerse','VerseList'):
            for BBB, label in (('JHN','YHN (JHN)'), ('JN2','2\u202fYHN (2\u202fJHN)')):
                with self.subTest(version=version, book=BBB):
                    paragraph = ElementTree.fromstring(makeBookNavListParagraph(
                        links(self.inputBooks, '../{BBB}/index.htm#Top'), version, self.state, currentBBB=BBB))
                    selected = next(span for span in paragraph.findall('./span') if 'selectedBook' in span.get('class').split())
                    self.assertEqual(text(selected), label)
                    self.assertIsNone(selected.find('.//a'))
                    self.assertFalse(any(f'/{BBB}/' in a.get('href') for a in paragraph.findall('.//a')))

    def test_front_matter_and_deuterocanonical_books_keep_destinations_and_groups(self):
        for version in ('OET', 'BSB', 'ParallelIndex', 'InterlinearIndex', 'VerseListIndex'):
            with self.subTest(version=version):
                paragraph = ElementTree.fromstring(makeBookNavListParagraph(links(['JHN','TOB','FRT','GEN']), version, self.state))
                self.assertIn('TOB', text(paragraph.find('./span[@class="DC"]')))
                self.assertIn('GEN', text(next(span for span in paragraph.findall('./span') if 'OT' in span.get('class').split())))
                self.assertEqual(any('XX' in span.get('class').split() for span in paragraph.findall('./span')), version not in VERSE_BOOK_NAVIGATION_VIEWS)
                if version in VERSE_BOOK_NAVIGATION_VIEWS:
                    self.assertEqual(paragraph.find('.//a').get('href'), 'GEN/C1V1.htm#chLst')

    def test_processing_order_matches_navigation_without_mutating_input(self):
        original = self.inputBooks.copy()
        self.assertEqual(bookNavigationOrder(self.inputBooks, 'OET-LV'), self.oetOrder)
        self.assertEqual(bookNavigationOrder(self.inputBooks, 'BSB'), self.traditionalOrder)
        self.assertEqual(self.inputBooks, original)

    def test_66_book_preference_only_marks_extra_books_in_oet_menus(self):
        extraBooks = ['FRT','TOB','JDT','LAO','GLS']
        for version in ('OET','OET-RV','OET-LV','Related OET-RV', *VERSE_BOOK_NAVIGATION_VIEWS, 'BSB','KJB-1611'):
            with self.subTest(version=version):
                paragraph = ElementTree.fromstring(makeBookNavListParagraph(
                    links(BibleOrgSysGlobals.BOOKLIST_66 + extraBooks), version, self.state, currentBBB='TOB'))
                spans = paragraph.findall('./span')
                hidden = [span for span in spans if span.get('data-oet-books') == 'all']
                if version in ('BSB','KJB-1611'):
                    self.assertEqual(hidden, [])
                else:
                    visible = [span for span in spans if span not in hidden]
                    self.assertEqual(len(visible), 66)
                    self.assertEqual(len(hidden), 4 if version in VERSE_BOOK_NAVIGATION_VIEWS else 5)
                    self.assertTrue(all({'OT','NT'} & set(span.get('class').split()) for span in visible))
                    self.assertTrue(all(span.text.startswith(' ') for span in hidden))
                    self.assertTrue(any('selectedBook' in span.get('class').split() for span in hidden))

    def test_oet_adjacent_book_links_skip_extra_books_in_both_directions(self):
        bookList = ['index','FRT','GEN','TOB','JDT','JHN','LAO']
        for version in ('OET','OET-RV','OET-LV'):
            for sectionIndex in (False, True):
                for BBB, previous, following in (('GEN','index','JHN'), ('JHN','GEN',None), ('TOB','GEN','JHN')):
                    with self.subTest(version=version, sectionIndex=sectionIndex, book=BBB):
                        sourceBooks = bookList[1:] if sectionIndex else bookList
                        oldPrevious = '<a href="FRT.htm#Top">previous</a>'
                        oldNext = '<a href="LAO.htm#Top">next</a>'
                        result = oetBookNavigationLinks(sourceBooks, BBB, version, oldPrevious, oldNext, sectionIndex=sectionIndex)
                        for rendered, old, expected in zip(result, (oldPrevious,oldNext), (None if sectionIndex and previous=='index' else previous, following)):
                            root = ElementTree.fromstring(f'<div>{rendered}</div>')
                            self.assertEqual(root.find('./span[@data-oet-books="all"]/a').get('href'), ElementTree.fromstring(old).get('href'))
                            limited = root.find('./span[@data-oet-books="66"]/a')
                            self.assertEqual(limited.get('href') if limited is not None else None, f'{expected}.htm#Top' if expected else None)
        self.assertEqual(bookList, ['index','FRT','GEN','TOB','JDT','JHN','LAO'])
        self.assertEqual(oetBookNavigationLinks(bookList, 'GEN', 'KJB-1611', 'previous', 'next'), ('previous','next'))
        missing = oetBookNavigationLinks(['index','GEN'], 'INT', 'OET', 'previous', 'next')
        self.assertIn('href="index.htm#Top"', missing[0])
        self.assertIn('href="GEN.htm#Top"', missing[1])

    def test_version_folder_is_not_mistaken_for_the_book_code(self):
        for version in ('OET','BSB'):
            with self.subTest(version=version):
                href = f'../../{version}/byC/JHN.htm#Top'
                paragraph = ElementTree.fromstring(makeBookNavListParagraph(links(['JHN'], href), version, self.state))
                anchor = paragraph.find('.//a')
                self.assertEqual(anchor.get('href'), href)
                self.assertEqual(text(anchor), 'YHN (JHN)' if version=='OET' else 'JOHN')

    def test_generated_version_chapter_document_and_section_pages(self):
        with TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)
            stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
            for module in (books, chapters, sections):
                stack.enter_context(patch.object(module, 'makeTop', return_value='<html><head><title>__TITLE__</title></head><body>'))
                stack.enter_context(patch.object(module, 'makeBottom', return_value='</body></html>'))
                stack.enter_context(patch.object(module, 'checkHtml', return_value=True))
            for version in ('KJB-1769', 'OET-RV', 'OET-LV', 'GHT'):
                with self.subTest(version=version):
                    source = root / version
                    source.mkdir()
                    for BBB in ('JHN','MRK','MAT','JAM','TOB'):
                        (source / f'{BBB}.usfm').write_text(
                            f'\\id {"JAS" if BBB=="JAM" else BBB}\n\\h {BBB}\n\\mt1 Example\n\\c 1\n\\s1 Example section\n\\p\n\\v 1 Example verse.\n')
                    bible = USFMBible(source, givenAbbreviation=version, versification='eng')
                    bible.loadBooks()
                    self.assertEqual(set(bible.books), {'JHN','MRK','MAT','JAM','TOB'})
                    bible.discover()
                    bible.makeSectionIndex()
                    state = State()
                    state.TEST_MODE_FLAG = False
                    state.preloadedBibles = {version: bible}
                    state.booksToLoad = {version: ['ALL'], 'OET': []}
                    state.BBBsToProcess = {version: bookNavigationOrder(bible.books, version)}
                    state.BBBLinks = {version: links(bible.books)}
                    state.sectionsLists = {}
                    state.sectionsListsForSections = {version: {}}
                    state.sectionsListsForHeaders = {'OET-RV': {}}
                    for view, build in (('byDoc',books.createBookPages), ('byC',chapters.createChapterPages), ('bySec',sections.createSectionPages)):
                        destination = source / view
                        build(2, destination, bible, state)
                        self.assertTrue((destination / ('TOB_C1.htm' if view=='byC' else 'TOB.htm')).is_file())
                        for page in destination.glob('*.htm'):
                            rendered = page.read_text()
                            paragraph = ElementTree.fromstring(re.search(r'<p class="bkLst">.*?</p>', rendered)[0])
                            anchors = paragraph.findall('.//a')
                            traditional=version in ('KJB-1769','GHT')
                            expected = ['TOB','MAT','MRK','JHN','JAM'] if traditional else ['TOB','JHN','MRK','MAT','JAM']
                            current=page.stem.split('_')[0] if page.stem!='index' else None
                            selected=[span for span in paragraph.findall('./span') if 'selectedBook' in span.get('class').split()]
                            self.assertEqual(len(selected), int(current is not None), page)
                            if current:
                                self.assertIsNone(selected[0].find('.//a'), page)
                                self.assertIn(text(selected[0]), text(paragraph), page)
                            self.assertEqual([a.get('href') for a in anchors], [f'{BBB}.htm#Top' for BBB in expected if BBB!=current], page)
                            self.assertIn('JOHN' if traditional else 'YHN (JHN)', text(paragraph), page)
                            if traditional:
                                self.assertNotIn('YHN', rendered, page)
                                self.assertNotIn('YAC', rendered, page)


if __name__ == '__main__':
    unittest.main()
