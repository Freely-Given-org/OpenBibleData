#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Lexical associations preserve morpheme alignment and dictionary alternatives.

CHANGELOG:
    2026-10-30 Check Strong's senses, Aramaic entries and UBS lemma indexes.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote

import Dict as dictionaries
from lexicalLinks import (normaliseStrongs, lemmaFilename, prepareLexicalAssociations,
                         lexicalResourceLinks, ubsRelatedLinks, livenUBSLemmaReferences, interlinearReferenceCells)


class LexicalLinkTests(unittest.TestCase):
    def state(self, filtered=False):
        hebrew = '\t'.join(['GEN_1:1w1','','1,2','1,2','1,2','Ncms,Ncms','אָב,בֵּן','אָב,בֵּן','father,son','','father_son','','','','1','','','',''])
        greek = '\t'.join(['JHN_1:1w1','λόγος','logos','λόγος','word','word','','100','30560','N','····NMS',''])
        return SimpleNamespace(TEST_MODE_FLAG=filtered,ALL_TEST_REFERENCE_PAGES_FLAG=False,TEST_BOOK_LIST=['JHN'],
            OETRefData={'OTHebLemmaList':['Lemma','אָב','בֵּן'],'word_tables':{
                'OET-LV_OT_word_table.tsv':['header',hebrew],'OET-LV_NT_word_table.tsv':['header',greek]}},
            UBS_HEB_DATA=[dict(MainId='001',Lemma='אָב',StrongCodes=['H0001a'],BaseForms=[]),
                          dict(MainId='002',Lemma='אָב II',StrongCodes=['H0001b'],BaseForms=[])],
            UBS_GNT_DATA=[dict(MainId='003',Lemma='λόγος',StrongCodes=['G3056'],BaseForms=[])])

    def test_codes_retain_senses_and_aramaic_identity(self):
        self.assertEqual(normaliseStrongs('H0001a'),('H1','H1a'))
        self.assertEqual(normaliseStrongs('A0671b'),('H671','A671b'))
        self.assertEqual(normaliseStrongs('5788 a+'),('H5788','H5788a'))
        for value in ('b','None','0','G9999'): self.assertIsNone(normaliseStrongs(value))

    def test_morpheme_slots_do_not_create_false_lemma_associations(self):
        graph = prepareLexicalAssociations(self.state())
        self.assertEqual(graph['lemmaCodes'][('Heb','אָב')],{'H1'})
        self.assertEqual(graph['lemmaCodes'][('Heb','בֵּן')],{'H2'})
        self.assertEqual(graph['strongLemmas']['G3056'],{('Grk','logos')})
        self.assertEqual(graph['ubsByStrong']['H1'],{('Heb','001'),('Heb','002')})
        self.assertEqual(graph['ubsByCode']['H1a'],{('Heb','001')})

    def test_unequal_morpheme_slots_leave_unverified_strongs_association_empty(self):
        state = self.state()
        state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'][1] = state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'][1].replace('\t1,2\tNcms','\t1\tNcms')
        graph = prepareLexicalAssociations(state)
        self.assertNotIn(('Heb','אָב'),graph['lemmaCodes'])
        self.assertIn(('Heb','אָב'),graph['availableLemmas'])

    def test_reduced_build_retains_associations_but_marks_omitted_destinations(self):
        graph = prepareLexicalAssociations(self.state(filtered=True))
        self.assertNotIn(('Heb','אָב'),graph['availableLemmas'])
        self.assertNotIn('H1',graph['availableStrongs'])
        self.assertIn(('Grk','logos'),graph['availableLemmas'])
        self.assertIn('G3056',graph['availableStrongs'])
        self.assertIn(('Heb','אָב'),graph['strongLemmas']['H1'])

    def test_lemma_filename_uses_generator_transliteration_exception(self):
        self.assertEqual(lemmaFilename('Heb','פִּתְגָּם'),'pitggām.htm')
        self.assertEqual(lemmaFilename('Grk','logos'),'logos.htm')

    def test_unused_greek_variant_does_not_advertise_an_unbuilt_lemma_page(self):
        state = self.state()
        table = state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv']
        table[1] = table[1].replace('\t100\t','\t\t')
        graph = prepareLexicalAssociations(state)
        self.assertNotIn(('Grk','logos'),graph['availableLemmas'])
        self.assertIn('G3056',graph['availableStrongs'])
        self.assertIn(('Grk','logos'),graph['strongLemmas']['G3056'])

    def test_both_ubs_loaders_index_actual_lemmas(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'UBSHebrewDicLexicalDomains-v0.9.1-en.JSON').write_text('[]')
            entries = [dict(MainId=str(n),Lemma=lemma,BaseForms=[]) for n,lemma in enumerate(('first','second'))]
            state = SimpleNamespace()
            with patch.object(dictionaries,'state',state):
                for filename,loader,attribute in (
                    ('UBSGreekNTDic-v1.0-en.JSON',dictionaries.loadAndIndexUBSGreekDictJSON,'UBS_GNT_LEMMA_INDEX'),
                    ('UBSHebrewDic-v0.9.1-en.JSON',dictionaries.loadAndIndexUBSHebrewDictJSON,'UBS_HEB_LEMMA_INDEX')):
                    (root/filename).write_text(json.dumps(entries))
                    loader('test',root)
                    self.assertEqual(getattr(state,attribute),{'first':0,'second':1})

    def test_lemma_and_strongs_pages_keep_dictionary_alternatives(self):
        state = self.state()
        html = unquote(lexicalResourceLinks(2,'Heb',state,lemma='אָב'))
        self.assertIn('ref/HebStrng/H1.htm#Top',html)
        self.assertIn('UBS/Heb/אָב.htm#Top',html)
        self.assertIn('UBS/Heb/אָב II.htm#Top',html)
        self.assertIn('H0001a',html)
        self.assertIn('H0001b',html)
        html = unquote(lexicalResourceLinks(2,'Grk',state,strong='G3056'))
        self.assertIn('ref/GrkLem/logos.htm#Top',html)
        self.assertIn('UBS/Grk/λόγος.htm#Top',html)
        self.assertNotIn('GrkStrng/G3056',html)

    def test_word_links_and_ubs_links_are_reciprocal(self):
        state = self.state()
        fields = state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'][1].split('\t')
        html = unquote(lexicalResourceLinks(2,'Grk',state,wordFields=fields))
        self.assertIn('UBS/Grk/λόγος.htm#Top',html)
        html = unquote(lexicalResourceLinks(2,'Grk',state,ubsId='003'))
        self.assertIn('ref/GrkLem/logos.htm#Top',html)
        self.assertIn('ref/GrkStrng/G3056.htm#Top',html)
        self.assertNotIn('UBS/Grk/λόγος.htm',html)

    def test_reduced_build_keeps_codes_without_advertising_missing_resources(self):
        html = lexicalResourceLinks(2,'Heb',self.state(filtered=True),ubsId='001')
        self.assertNotIn('ref/Heb',html)
        self.assertIn('H1a',html)

    def test_related_and_encoded_lemmas_require_verified_identifiers(self):
        state = self.state()
        html = unquote(ubsRelatedLinks(2,'Grk',[{'Word':'λόγος'},{'Word':'missing'}],state))
        self.assertIn('UBS/Grk/λόγος.htm#Top',html)
        self.assertTrue(html.endswith('missing'))
        html = unquote(livenUBSLemmaReferences('{L:word<SDBG:λόγος:000000>} {L:unknown<SDBH:missing>}',2,state))
        self.assertIn('λόγος.htm#Top">word</a>',html)
        self.assertTrue(html.endswith(' unknown'))
        self.assertNotIn('SDB',html)

    def test_interlinear_cells_use_lemma_rows_and_actual_strongs_column(self):
        state=self.state()
        fields=state.OETRefData['word_tables']['OET-LV_OT_word_table.tsv'][1].split('\t')
        fields[2]='9999,9998' # Morpheme row numbers are neither lemmas nor Strong’s codes.
        fields[5]='Vqp3ms,Ncms'
        lemma,strong,morph=map(unquote,interlinearReferenceCells(2,'Heb',fields,state))
        self.assertIn('ref/HebLem/',lemma)
        self.assertIn('ref/HebStrng/H1.htm',strong)
        self.assertIn('ref/HebStrng/H2.htm',strong)
        self.assertNotIn('9999',lemma+strong)
        self.assertIn('BibleHub.com/hebrew/1.htm',strong)
        self.assertIn('ref/UHG/stem_qal.htm#Top',morph)
        fields[1]='A'
        self.assertNotIn('stem_qal',interlinearReferenceCells(2,'Heb',fields,state)[2])

    def test_greek_interlinear_cells_use_local_resources_and_grammar(self):
        state=self.state()
        fields=state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'][1].split('\t')
        lemma,strong,morph=interlinearReferenceCells(2,'Grk',fields,state)
        self.assertIn('ref/GrkLem/logos.htm#Top',lemma)
        self.assertIn('ref/GrkStrng/G3056.htm#Top',strong)
        self.assertIn('ref/UGG/case_nominative.htm#Top',morph)
        self.assertIn('ref/UGG/noun.htm#Top',morph)


if __name__ == '__main__': unittest.main()
