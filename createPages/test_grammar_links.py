#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Regression tests for grammar contents and explicit section references.

CHANGELOG:
    2026-10-30 Check local grammar article and section destinations.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from docutils.core import publish_parts
from docutils.parsers.rst import roles
from grammarLinks import expandGrammarContents, grammarReferenceRole, addGrammarPassages, localiseGrammarLinks, _quotedWordLinks, grammarMorphologyExamples


class GrammarLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.previousRoles = roles._roles.copy()
        self.addCleanup(self.restoreRoles)
        (self.root/'stem.rst').write_text('.. _stem-voice-active:\n\nActive voice\n============\n\nAn example.\n')
        (self.root/'noun.rst').write_text('Noun\n====\n')
        roles.register_local_role('ref', grammarReferenceRole(self.root))

    def restoreRoles(self):
        roles._roles.clear()
        roles._roles.update(self.previousRoles)

    def render(self, source):
        return publish_parts(source=source, writer_name='html', settings_overrides={'report_level':5})['html_body']

    def test_explicit_reference_preserves_label_and_real_section_destination(self):
        html = self.render(':ref:`active verbs <stem-voice-active>` and :ref:`noun`.')
        self.assertIn('href="stem.htm#stem-voice-active">active verbs</a>', html)
        self.assertIn('href="noun.htm#Top">noun</a>', html)
        self.assertIn('id="stem-voice-active"',self.render((self.root/'stem.rst').read_text()))

    def test_unknown_reference_is_readable_and_reports_label(self):
        with self.assertLogs(level='WARNING') as messages:
            html = self.render(':ref:`readable label <unknown-target>`.')
        self.assertIn('readable label',html)
        self.assertNotIn('href=',html)
        self.assertIn('unknown-target',messages.output[0])

    def test_contents_preserve_nested_named_entries_without_empty_links(self):
        source = '.. toctree::\n   :maxdepth: 2\n\n   stem\n      My noun <noun>\n\nAfter the contents.\n'
        html = self.render(expandGrammarContents(source,self.root))
        self.assertIn('href="stem.htm#Top"',html)
        self.assertIn('href="noun.htm#Top">My noun</a>',html)
        self.assertNotIn('href=".htm',html)
        self.assertIn('After the contents.',html)

    def test_missing_contents_target_warns_and_remains_plain_text(self):
        with self.assertLogs(level='WARNING'):
            html = self.render(expandGrammarContents('.. toctree::\n\n   Missing <absent>\n',self.root))
        self.assertIn('Missing',html)
        self.assertNotIn('absent.htm',html)

    def test_examples_keep_original_text_and_use_source_english_numbering(self):
        original = '<table><caption>Example: PSA 38:10 (PSA 38:11 in Hebrew)</caption><tr><td>Original gloss</td></tr></table>'
        with patch('grammarLinks.renderReferencePassage',return_value='<details>OET comparison</details>') as render:
            result = addGrammarPassages(original,2,'UHG/stem_pealal.rst',SimpleNamespace())
        self.assertTrue(result.startswith(original))
        self.assertEqual(render.call_args.args[1],(('PSA','38','10',None),))
        self.assertEqual(render.call_args.args[2],'eng')

    def test_source_abbreviations_and_range_are_not_confused_with_bos_aliases(self):
        for citation,book in (('EZR 9:12','EZR'),('1 CHR 29:22','CH1'),('JUD 19:27','JDG'),('2 Corinthians 12:7-9','CO2')):
            original = f'<table><caption>{citation}</caption><tr><td>Example</td></tr></table>'
            with patch('grammarLinks.renderReferencePassage',return_value='') as render:
                addGrammarPassages(original,2,'UHG/example.rst',SimpleNamespace())
            self.assertEqual(render.call_args.args[1][0][0],book)
            if book=='CO2': self.assertEqual(len(render.call_args.args[1]),3)

    def test_external_links_are_rewritten_only_for_verified_named_sections(self):
        folder = self.root/'UGG'
        folder.mkdir()
        (folder/'case.htm').write_text('<h1 id="Top">Case</h1><h2 id="dative">Dative</h2>')
        page = folder/'index.htm'
        page.write_text(' '.join(f'<a href="https://ugg.readthedocs.io/en/latest/case.html#{anchor}">{anchor}</a>'
                                 for anchor in ('dative','missing','id2')))
        localiseGrammarLinks(folder,self.root)
        html = page.read_text()
        self.assertIn('href="case.htm#dative"',html)
        self.assertIn('https://ugg.readthedocs.io/en/latest/case.html#missing',html)
        self.assertIn('https://ugg.readthedocs.io/en/latest/case.html#id2',html)

    def test_only_unique_whole_example_words_get_occurrence_links(self):
        row = '\t'.join(['GEN_1:1w1','','1','1','1254','Vqp3ms','בָּרָא','בָּרָא','created','','created','','','','1','','','',''])
        state = SimpleNamespace(TEST_MODE_FLAG=False,OETRefData={
            'word_tables':{'OET-LV_OT_word_table.tsv':['header',row]},'word_table_indexes':{'present':{}}})
        with patch('oetWords.mappedWordRows',return_value=(1,)):
            links = _quotedWordLinks('<strong>בָּרָא</strong>',(('GEN','1','1',None),),2,state)
            self.assertIn('ref/HebWrd/GENc1v1w1.htm#Top',links)
            self.assertEqual(_quotedWordLinks('<strong>בָּ רָא</strong>',(('GEN','1','1',None),),2,state),'')
        state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'].append(row.replace('w1','w2'))
        with patch('oetWords.mappedWordRows',return_value=(1,2)):
            self.assertEqual(_quotedWordLinks('<strong>בָּרָא</strong>',(('GEN','1','1',None),),2,state),'')
        examples = grammarMorphologyExamples('UHG/stem_qal.rst',2,state)
        self.assertIn('GENc1v1w1.htm#Top',examples)
        self.assertNotIn('semantic',examples)


if __name__ == '__main__':
    unittest.main()
