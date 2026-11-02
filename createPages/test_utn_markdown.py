#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Regression tests for UTN lists and OBD scripture destinations.

CHANGELOG:
    2026-10-30 Cover Matthew 24 introduction formatting and mapped section links.
    2026-11-01 Cover malformed HTTP prefixes on relative scripture paths.
    2026-11-02 Present occurrence -1 as All occurrences while preserving quote lookup.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from xml.etree import ElementTree

from Bibles import formatUnfoldingWordTranslationNotes
from settings import State
from utnMarkdown import formatUTNMarkdownBlocks, livenUTNMarkdownLinks


def section(number, chapter, first, last, filename):
    return (number, chapter, first, chapter, last, 'Heading', 's1', [], [], filename)


class UTNMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.sectionsListsForSections = {'OET-RV': {
            'MAT': [section(0, '23', '1', '39', 'MAT_S0.htm'),
                    section(1, '24', '1', '3', 'MAT_S1.htm'),
                    section(2, '24', '4', '28', 'MAT_S2.htm'),
                    section(3, '24', '29', '51', 'MAT_S3.htm')],
            'MRK': [section(0, '14', '12', '26', 'MRK_S0.htm')],
        }}

    def render(self, text, *, segment='parallelVerse', level=2):
        entries = [SimpleNamespace(getMarker=lambda m=m: m, getFullText=lambda t=t: t)
                   for m,t in [('v', '0'), ('p', ''), ('v~', text)]]
        self.state.preloadedBibles = {'UTN': Mock(getVerseDataList=Mock(return_value=entries))}
        html = formatUnfoldingWordTranslationNotes(level, 'MAT', '24', '0', segment, self.state)
        return ElementTree.fromstring(f'<div>{html}</div>')

    def links(self, text, **kwargs):
        return self.render(text, **kwargs).findall('.//a')

    def test_all_occurrences_label_preserves_original_quote_lookup(self):
        for occurrence,label in ((-1,'(All occurrences) '),(1,''),(2,'(Occurrence 2) ')):
            with self.subTest(occurrence=occurrence):
                entries=[SimpleNamespace(getMarker=lambda m=m:m,getFullText=lambda t=t:t)
                    for m,t in [('v','1'),('pi1',''),('v~',str(occurrence)),('q1',''),('v~','λόγος')]]
                self.state.preloadedBibles={'UTN':Mock(getVerseDataList=Mock(return_value=entries))}
                with patch('Bibles.findOLQuoteInLV',return_value='word') as quote:
                    rendered=formatUnfoldingWordTranslationNotes(2,'MAT','1','1','parallelVerse',self.state)
                quote.assert_called_once_with(2,'MAT','1','1',occurrence,'λόγος',self.state)
                self.assertIn(f'<p class="OL">{label}λόγος</p>',rendered)
                self.assertNotIn('Occurrence -1',rendered)

    def test_matthew_outline_and_following_numbered_list(self):
        soup = self.render(
            '# Matthew 24 Chapter Introduction\\n\\n## Structure and Formatting\\n\\n'
            '10. Jesus teaches ([23:1–25:46](../23/01.md))\\n'
            '      * The disciples ask ([24:1–3](../24/01.md))\\n'
            '      * Jesus teaches ([24:4–35](../24/04.md))\\n'
            '        * Things before the destruction ([24:4–14](../24/04.md))\\n'
            '        * Things immediately before ([24:15–28](../24/15.md))\\n'
            '      * The end of the age ([24:36–51](../24/36.md))\\n\\n'
            '### When Jesus speaks\\n\\n'
            'When they speak in [24:3](../24/03.md), he could:\\n'
            '1. Finish at [24:35](../24/35.md)\\n'
            '2. Speak about [24:4–28](../24/04.md)\\n\\n'
            'Since Christians disagree, allow several interpretations.')
        ordered = soup.findall('.//ol')
        self.assertEqual(len(ordered), 2)
        self.assertEqual(ordered[0].get('start'), '10')
        self.assertEqual(len(ordered[0].findall('li')), 1)
        outerBullets = ordered[0].find('li/ul')
        self.assertEqual(len(outerBullets.findall('li')), 3)
        self.assertEqual(len(outerBullets.findall('.//ul')), 1)
        self.assertEqual(len(ordered[1].findall('li')), 2)
        self.assertTrue(soup[-1].text.startswith('Since Christians'))
        for tag in ('ul', 'ol', 'h3'):
            self.assertFalse(soup.findall(f'.//p/{tag}'))
        self.assertNotIn('.md)', ''.join(soup.itertext()))
        self.assertNotIn('* ', ''.join(soup.itertext()))

    def test_single_verses_from_both_page_families(self):
        for segment in ('parallelVerse', 'interlinearVerse'):
            for level in (2, 3):
                with self.subTest(segment=segment, level=level):
                    links = self.links('[24:3](../24/03.md) [24:4](./04.md) '
                                       '[Mark 14:22](../mrk/14/22.md)', segment=segment, level=level)
                    self.assertEqual([a.get('href') for a in links], [
                        '../'*level + 'par/MAT/C24V3.htm#Top',
                        '../'*level + 'par/MAT/C24V4.htm#Top',
                        '../'*level + 'par/MRK/C14V22.htm#Top'])

    def test_ranges_use_starting_section_and_keep_the_label(self):
        for separator in ('–', '-', '—'):
            label = f'24:4{separator}28'
            link = self.links(f'[{label}](../24/04.md)')[0]
            self.assertEqual(link.text, label)
            self.assertEqual(link.get('href'), '../../OET/bySec/MAT_S2.htm#C24V4')
        link = self.links('[23:1–25:46](../23/01.md)')[0]
        self.assertEqual(link.get('href'), '../../OET/bySec/MAT_S0.htm#C23V1')
        link = self.links('[Mark 14:22–25](../mrk/14/22.md)')[0]
        self.assertEqual(link.get('href'), '../../OET/bySec/MRK_S0.htm#C14V22')

    def test_cross_book_links_with_two_parent_directories(self):
        links = self.links('[Mark 14:22](../../mrk/14/22.md) '
                           '[Mark 14:22–25](../../mrk/14/22.md)')
        self.assertEqual([link.get('href') for link in links], [
            '../../par/MRK/C14V22.htm#Top', '../../OET/bySec/MRK_S0.htm#C14V22'])

    def test_introduction_and_external_links(self):
        links = self.links('[Book introduction](../front/intro.md) '
                           '[Chapter introduction](../03/intro.md) '
                           '[Article](https://example.org/article?a=1&b=2)')
        self.assertEqual([link.get('href') for link in links], [
            '../../par/MAT/Intro.htm#Top', '../../par/MAT/C3V0.htm#Top',
            'https://example.org/article?a=1&b=2'])

    def test_relative_path_with_http_prefix_is_a_scripture_link(self):
        with self.assertLogs(level='WARNING') as warnings:
            result = livenUTNMarkdownLinks('[10:9](http://../10/09.md)', 2, 'ISA', '28', '25', self.state)
        self.assertIn('href="../../par/ISA/C10V9.htm#Top"', result)
        self.assertIn('ISA 28:25', warnings.output[0])

    def test_range_maps_to_native_rv_section_before_looking_up_filename(self):
        self.state.sectionsListsForSections['OET-RV']['MAT'] = [
            section(0, '25', '8', '20', 'MAT_S0.htm')]
        with patch('utnMarkdown.mappedReferences', return_value=(('MAT','25','8',None),)) as mapped:
            link = self.links('[24:4–28](../24/04.md)')[0]
        mapped.assert_called_once_with(('MAT','24','4'), 'UTN', 'OET-RV', self.state)
        self.assertEqual(link.get('href'), '../../OET/bySec/MAT_S0.htm#C25V8')
        self.assertEqual(link.get('data-vref'), 'mapped')

    def test_missing_section_falls_back_without_inventing_section_zero(self):
        for testMode in (False, True):
            self.state.TEST_MODE_FLAG = testMode
            self.state.sectionsListsForSections = {}
            with self.assertLogs(level='WARNING') as messages:
                link = self.links('[24:4–28](../24/04.md)')[0]
            self.assertEqual(link.get('href'), '../../par/MAT/C24V4.htm#Top')
            self.assertIn('UTN MAT 24:0', messages.output[0])

    def test_heading_links_and_existing_inline_markup(self):
        soup = self.render('### “This generation” in [24:34](../24/34.md)\\n\\n'
                           '**Bold** and {added} words. Alternate translation: [ ]\\n\\n'
                           'See [[rc://*/ta/man/translate/figs-parables]].')
        self.assertEqual(soup.find('h3/a').get('href'), '../../par/MAT/C24V34.htm#Top')
        self.assertEqual(soup.find('.//b').text, 'Bold')
        self.assertEqual(soup.find('.//span[@class="add"]').text, 'added')
        self.assertIn('[ ]', ''.join(soup.itertext()))
        self.assertTrue(soup.findall('.//a')[-1].get('href').endswith('#figs-parables'))

    def test_paragraphs_and_soft_line_breaks(self):
        soup = self.render('First line\\ncontinues here.\\n\\nSecond paragraph.')
        self.assertEqual([p.text for p in soup.findall('p')],
                         ['First line continues here.', 'Second paragraph.'])

    def test_list_type_changes_and_indented_continuations(self):
        html = formatUTNMarkdownBlocks(
            '* One\n  continued\n\n  Another paragraph.\n* Two\n'
            '3. Three\n  + Child\n4. Four\n\nAfter.', 'MAT_24:0')
        soup = ElementTree.fromstring(f'<div>{html}</div>')
        self.assertEqual([node.tag for node in soup], ['ul','ol','p'])
        self.assertIn('One\n continued', soup.find('ul/li').text)
        self.assertEqual(soup.find('ul/li/p').text, 'Another paragraph.')
        self.assertEqual(soup.find('ol').get('start'), '3')
        self.assertEqual(len(soup.findall('ol/li')), 2)
        self.assertEqual(soup.find('ol/li/ul/li').text, 'Child\n')

    def test_many_links_have_no_arbitrary_limit(self):
        links = self.links(' '.join(['[24:3](../24/03.md)'] * 120))
        self.assertEqual(len(links), 120)

    def test_bad_target_reports_note_location_and_keeps_label(self):
        with self.assertLogs(level='WARNING') as messages:
            html = livenUTNMarkdownLinks('[reference](../nonsense/xx.md)', 2, 'MAT', '24', '0', self.state)
        self.assertEqual(html, 'reference')
        self.assertIn('UTN MAT 24:0', messages.output[0])


if __name__ == '__main__':
    unittest.main()
