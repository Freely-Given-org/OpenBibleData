#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Check search metadata in the HTML delivered to readers.

CHANGELOG:
    2026-11-05 Cover dictionary pages, passage ranges, word positions and HTML escaping.
    2026-11-05 Check lexical entries with and without a marked gloss.
    2026-11-05 Verify configured canonical URLs for production and local builds.
    2026-11-05 Check the grammar article head, stylesheet and source summary together.
    2026-11-05 Verify that the release audit accepts a canonical pair and reports broken metadata.
    2026-11-09 Check directory canonical URLs against their generated landing pages.
"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import Dict
from html import makeTop
from pageMetadata import sectionMetadata, strongsMetadata, wordMetadata
from searchText import FragmentParser
from test_makeTop import get_stub_state
from auditPageMetadata import audit


class HeadReader(FragmentParser):
    def __init__(self, page):
        super().__init__()
        self.titles = []
        self.descriptions = []
        self.inTitle = False
        self.feed(page.split('</head>', 1)[0])
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.titles.append('')
            self.inTitle = True
        if tag == 'meta' and dict(attrs).get('name') == 'description':
            self.descriptions.append(dict(attrs)['content'])

    def handle_endtag(self, tag):
        if tag == 'title':
            self.inTitle = False

    def handle_data(self, data):
        if self.inTitle:
            self.titles[-1] += data


class PageMetadataTests(unittest.TestCase):
    def setUp(self):
        self.state = get_stub_state()
        self.state.TEST_MODE_FLAG = False

    def test_strongs_entries_preserve_the_source_word_and_available_definition(self):
        title, description = strongsMetadata('H1', ('אָב', 'n-m', 'awb', 'ʼâb', None), '<def>father</def>, literally or figuratively.')
        self.assertEqual(title, 'Strong’s H1 — אָב (ʼâb) — father')
        self.assertIn('father, literally or figuratively.', description)
        title, description = strongsMetadata('G26', ('ἀγάπη', 'agápē', ''), 'from <StrongsRef>G25</StrongsRef>; love')
        self.assertIn('ἀγάπη (agápē)', title)
        self.assertIn('from G25; love', description)
        self.assertIn('unused number', strongsMetadata('G2717', None, 'Not Used')[0])

    def test_metadata_is_plain_text_in_one_head_in_both_build_modes(self):
        title = 'A & B <word>'
        description = 'A "quoted" term & a literal <tag>.'
        for testMode in (True, False):
            self.state.TEST_MODE_FLAG = testMode
            page = makeTop(1, None, 'dictionaryEntry', None, self.state, metadata=(title, description))
            head = HeadReader(page)
            self.assertEqual(head.titles, [title + (' TEST' if testMode else '')])
            self.assertEqual(head.descriptions, [description])
            self.assertNotIn('__KEYWORDS__', page)
            self.assertNotIn('__TITLE__', page)

    def test_preferred_url_uses_public_base_only_in_production(self):
        for testMode,base,expected in (
                (False, 'https://example.org/custom', 'https://example.org/custom/par/GEN/index.htm'),
                (True, 'https://example.org/custom/', None), (False, None, None)):
            self.state.TEST_MODE_FLAG, self.state.PUBLIC_BASE_URL = testMode, base
            page = makeTop(1, None, 'site', None, self.state, metadata=('Genesis', 'Browse Genesis.'),
                           canonicalPath='par/GEN/index.htm')
            self.assertEqual(page.count('rel="canonical"'), int(expected is not None))
            if expected:
                self.assertIn(f'<link rel="canonical" href="{expected}">', page.split('</head>')[0])

    def test_grammar_article_has_one_document_and_a_plain_summary(self):
        from createOETReferencePages import grammarArticleHtml
        source = ':github_url: example\n\nNominative case\n===============\n\nSummary\n-------\n\nA *subject* can be marked with the nominative.'
        page = grammarArticleHtml(2, Path('case_nominative.rst'), source, {}, 'Greek', 'UGG', self.state)
        head = HeadReader(page)
        self.assertEqual(head.titles, ['Nominative case — unfoldingWord Greek Grammar'])
        self.assertEqual(head.descriptions, ['A subject can be marked with the nominative.'])
        for element in ('<head>', '</head>', '<body', '</body>', 'id="Top"'):
            self.assertEqual(page.count(element), 1)
        self.assertLess(page.index('<style'), page.index('</head>'))

    def test_release_audit_accepts_index_copies_and_rejects_wrong_targets_and_titles(self):
        self.state.PUBLIC_BASE_URL = 'https://example.org/OBD/'
        top = makeTop(1, None, 'site', None, self.state, metadata=('Genesis index', 'Browse Genesis.'),
                      canonicalPath='par/GEN/index.htm')
        with TemporaryDirectory() as temp, redirect_stdout(StringIO()) as output:
            root = Path(temp)
            (root/'par/GEN').mkdir(parents=True)
            (root/'par/GEN/index.htm').write_text(top)
            (root/'par/GEN.htm').write_text(top)
            self.assertTrue(audit(root, self.state.PUBLIC_BASE_URL))
            (root/'par/GEN.htm').write_text(top.replace('par/GEN/index.htm','par/missing.htm'))
            (root/'About.htm').write_text('<head><title>Genesis index</title></head>')
            self.assertFalse(audit(root, self.state.PUBLIC_BASE_URL))
            for problem in ('invalid canonical', 'incorrect book-index canonical', 'invalid description', 'title collision'):
                self.assertIn(problem, output.getvalue())

    def test_release_audit_resolves_directory_canonicals(self):
        self.state.PUBLIC_BASE_URL = 'https://example.org/OBD/'
        top = makeTop(1, None, 'site', None, self.state,
                      metadata=('Open English Translation', 'Read the OET.'), canonicalPath='OET/')
        with TemporaryDirectory() as temp, redirect_stdout(StringIO()) as output:
            root = Path(temp)
            (root/'OET').mkdir()
            landing = root/'OET/index.htm'
            landing.write_text(top)
            self.assertTrue(audit(root, self.state.PUBLIC_BASE_URL))
            landing.write_text(top.replace('/OBD/OET/', '/OBD/missing/'))
            self.assertFalse(audit(root, self.state.PUBLIC_BASE_URL))
            self.assertIn('invalid canonical', output.getvalue())

    def test_actual_dictionary_writers(self):
        self.state.TOBDData = {
            'Intro': '<p>Introduction</p>', 'Textboxes': {}, 'Maps': {},
            'Letters': {'B': [('BethEl', 'Beth El')]},
            'Articles': {'BethEl': '<p class="h1">BETH EL</p><p class="fl"></p><p class="list">1. A <i>place</i> called “house of God”.</p>'}}
        sense = dict(LanguageCode='en', Glosses=['love'], DefinitionShort='Love & affection.')
        self.state.UBS_GNT_DATA = [dict(MainId='1', Lemma='ἀγάπη', BaseForms=[dict(LEXMeanings=[dict(LEXSenses=[sense])])])]
        self.state.UBS_HEB_DATA = [dict(MainId='2', Lemma='אָב', BaseForms=[])]
        with TemporaryDirectory() as folder:
            root = Path(folder)
            Dict.createTyndaleDictPages(1, root/'dct', self.state)
            Dict.createUBSDictionaryPages(1, root/'UBS', self.state)
            heads = {p.relative_to(root).as_posix(): HeadReader(p.read_text()) for p in root.rglob('*.htm')}
            self.assertEqual(len(heads), 10)
            for name, head in heads.items():
                with self.subTest(name=name):
                    self.assertEqual(len(head.titles), 1)
                    self.assertEqual(len(head.descriptions), 1)
                    self.assertTrue(head.descriptions[0].strip())
            self.assertEqual(len({head.titles[0] for head in heads.values()}), len(heads))
            self.assertEqual(heads['dct/BethEl.htm'].titles, ['Beth El — Tyndale Open Bible Dictionary'])
            self.assertIn('A place called “house of God”.', heads['dct/BethEl.htm'].descriptions[0])
            self.assertIn('Entries under B', heads['dct/index_B.htm'].titles[0])
            self.assertIn('love', heads['UBS/Grk/ἀγάπη.htm'].titles[0])
            self.assertIn('Love & affection.', heads['UBS/Grk/ἀγάπη.htm'].descriptions[0])
            self.assertIn('אָב', heads['UBS/Heb/אָב.htm'].descriptions[0])

    def test_sections_and_occurrences_identify_the_passage_and_view(self):
        section = ('OET', 'JHN', '2', '1', '2', '12', 'The <i>wine</i> miracle')
        title, description = sectionMetadata(*section, paired=True)
        self.assertEqual(title, 'Yohan (John) 2:1–12 — The wine miracle | OET')
        self.assertIn('side by side', description)
        self.assertIn('related passages', sectionMetadata(*section, related=True)[0])
        self.assertIn('John 2:25–3:4', sectionMetadata('BSB', 'JHN', '2', '25', '3', '4', 'Heading')[0])
        self.assertIn('John 2:1 —', sectionMetadata('BSB', 'JHN', '2', '1', '2', '1', 'Heading')[0])
        self.assertIn('introduction, lines 14–34', sectionMetadata('OET', 'JHN', '-1', '14', '-1', '34', 'Author')[0])
        first = wordMetadata('Greek', 'JHN', '3', '16', '1', 'οὕτως', '<i>thus</i>')
        self.assertIn('John 3:16, word 1', first[0])
        self.assertIn('“thus”', first[1])
        self.assertNotEqual(first[0], wordMetadata('Greek', 'JHN', '3', '16', '2', 'οὕτως', '')[0])


if __name__ == '__main__':
    unittest.main()
