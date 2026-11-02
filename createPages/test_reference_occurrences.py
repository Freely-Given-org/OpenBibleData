#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Strong's occurrences retain exact source identifiers and stable OET order.

CHANGELOG:
    2026-10-31 Check suffix codes, unused variants, order and multiword focus.
    2026-10-31 Cover formatted Hebrew/Greek glosses in summaries and filter data.
"""
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from pathlib import Path
import json
import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit

from referenceOccurrences import (orderedReferences,prepareStrongOccurrences,
    prepareOccurrenceNavigation,createOccurrencePages,occurrenceBrowseLink,lemmaOccurrenceSummary)
from settings import State
import createOETReferencePages as pages


class ReferenceOccurrenceTests(unittest.TestCase):
    def test_oet_order_and_numeric_verse_order_are_deterministic(self):
        refs={'MAT_1:10','JHN_1:2','GEN_1:1','MAT_1:2','MRK_1:1'}
        self.assertEqual(orderedReferences(refs),['GEN_1:1','JHN_1:2','MRK_1:1','MAT_1:2','MAT_1:10'])

    def test_strong_rows_keep_multiple_occurrences_and_omit_unused_greek_variants(self):
        heb=[]
        for number,code in enumerate(('07225 a','b,7225+','H7225b'),1):
            fields=['']*19;fields[0]=f'GEN_1:1w{number}';fields[1]='w';fields[4]=code
            heb.append('\t'.join(fields))
        grk=[]
        for number,probability in enumerate(('X','','X'),1):
            fields=['']*12;fields[0]=f'JHN_1:1w{number}';fields[7]=probability;fields[8]='30560'
            grk.append('\t'.join(fields))
        state=SimpleNamespace(OETRefData={'word_tables':{
            'OET-LV_OT_word_table.tsv':['header',*heb], 'OET-LV_NT_word_table.tsv':['header',*grk]}})
        index=prepareStrongOccurrences(state)
        self.assertEqual(index['H7225']['GEN_1:1'],[1,2,3])
        self.assertEqual(index['G3056']['JHN_1:1'],[1,3])

    def test_all_exact_words_in_one_verse_are_highlighted_without_prefix_matches(self):
        paths=('GrkWrd/JHNc1v1w1.htm','GrkWrd/JHNc1v1w3.htm')
        text=' '.join(f'<a href="../../ref/GrkWrd/JHNc1v1w{n}.htm#Top">word</a>' for n in (1,3,10))
        with patch.object(pages,'get_OET_LV_verse_HTML',return_value=text),patch.object(pages,'get_OET_RV_verse_HTML',return_value=text):
            lv,rv=pages.get_focused_OET_verse_HTML(2,'JHN','1','1',paths)
        self.assertEqual(lv.count('<b>'),2)
        self.assertEqual(rv,lv)
        self.assertNotIn('<b><a href="../../ref/GrkWrd/JHNc1v1w10.htm',lv)

    def manyOccurrences(self):
        state=State();state.TEST_MODE_FLAG=False
        table=['header']
        for word in range(1,206):
            fields=['']*12
            fields[0]=f'JHN_1:1w{word}';fields[1]='λόγος';fields[2]='logos';fields[3]='λόγος'
            fields[5]='word' if word%2 else 'message';fields[7]='X';fields[8]='30560'
            fields[9]='N';fields[10]='····NMS'
            table.append('\t'.join(fields))
        state.OETRefData={'word_tables':{'OET-LV_NT_word_table.tsv':table}}
        state.preloadedBibles={}
        return state

    def test_all_occurrences_have_bounded_static_pages_and_complete_filter_data(self):
        state=self.manyOccurrences()
        groups=prepareOccurrenceNavigation(state)
        self.assertEqual(len(groups),3)
        with TemporaryDirectory() as temporary, patch('referenceOccurrences.occurrenceContextLinks',return_value='JHN 1:1'), \
                patch('html.makeTop',return_value='<html><head><title>__TITLE__</title></head><body>'),patch('html.makeBottom',return_value='</body></html>'):
            folder=Path(temporary)
            self.assertEqual(createOccurrencePages(2,folder,state),9)
            group=groups['Grk','lemma','logos']
            pages=[folder/f'{group["stem"]}-{n}.htm' for n in range(1,4)]
            self.assertEqual([p.read_text().count('<li>') for p in pages],[100,100,5])
            data=json.loads((folder/f'{group["stem"]}.json').read_text())
            self.assertEqual(len(data),205)
            self.assertIn('JHNc1v1w205.htm',data[-1]['html'])
            for page in pages:
                for href in re.findall(r'href="([^"#]+)\.htm#Top"',page.read_text()):
                    if not href.startswith('../'):self.assertTrue((folder/f'{href}.htm').is_file())
            summaries=lemmaOccurrenceSummary(2,'Grk','logos',state)
            self.assertIn('?form=',summaries)
            self.assertIn('?gloss=message',summaries)

    def test_reduced_build_does_not_link_unbuilt_occurrence_groups(self):
        state=self.manyOccurrences();state.TEST_MODE_FLAG=True
        state.ALL_TEST_REFERENCE_PAGES_FLAG=False;state.TEST_BOOK_LIST=['MRK']
        self.assertEqual(prepareOccurrenceNavigation(state),{})
        self.assertEqual(occurrenceBrowseLink(2,'Grk','lemma','logos',state),'')

    def test_gloss_shortcuts_match_clean_filter_data_without_source_markup(self):
        examples={
            'Heb':[(r'and=\untr DOM\untr*','and DOM'),
                   (r'\untr DOM\untr*_him/it','DOM him/it'),
                   (r'\nd YHWH\nd*','YHWH'),
                   (r'ʼŪriy\sup yāh\sup*','ʼŪriyyāh'),
                   (r'\add >word\add*','word')],
            'Grk':[(r'˱of˲ Ourias/(ʼŪriy\sup yāh\sup*)','of Ourias/(ʼŪriyyāh)'),
                   (r'\add >the\add*_word','the word'),
                   ('˓a˒_word','a word')],
        }
        for language,glosses in examples.items():
            with self.subTest(language=language):
                state=self.manyOccurrences()
                lemma='אֵת' if language=='Heb' else 'logos'
                table=['header']
                for word in range(1,206):
                    sourceGloss=glosses[(word-1)%len(glosses)][0]
                    if language=='Heb':
                        fields=['']*19
                        fields[0]=f'GEN_1:1w{word}';fields[3]='1';fields[4]='853'
                        fields[5]='To';fields[7]=lemma;fields[10]=sourceGloss
                    else:
                        fields=state.OETRefData['word_tables']['OET-LV_NT_word_table.tsv'][word].split('\t')
                        fields[5]=sourceGloss
                    table.append('\t'.join(fields))
                state.OETRefData={'OTHebLemmaList':['header','אֵת'],'word_tables':{
                    f'OET-LV_{"OT" if language=="Heb" else "NT"}_word_table.tsv':table}}
                groups=prepareOccurrenceNavigation(state)
                summary=lemmaOccurrenceSummary(2,language,lemma,state)
                self.assertNotIn('\\',summary)
                shortcuts=[parse_qs(urlsplit(href).query)['gloss'][0]
                           for href in re.findall(r'href="([^"]+)"',summary) if '?gloss=' in href]
                self.assertEqual(set(shortcuts),{text for _,text in glosses})
                with TemporaryDirectory() as temporary, patch('referenceOccurrences.occurrenceContextLinks',return_value='Verse'), \
                        patch('html.makeTop',return_value='<html><head><title>__TITLE__</title></head><body>'), \
                        patch('html.makeBottom',return_value='</body></html>'):
                    folder=Path(temporary)
                    createOccurrencePages(2,folder,state)
                    stem=groups[language,'lemma',lemma]['stem']
                    records=json.loads((folder/f'{stem}.json').read_text())
                    self.assertEqual(len(records),205)
                    self.assertEqual({row['gloss'] for row in records},set(shortcuts))
                    self.assertTrue(all('\\' not in row['html'] for row in records))
                    self.assertTrue(all('\\' not in file.read_text() for file in folder.glob('*.htm')))


if __name__=='__main__':unittest.main()
