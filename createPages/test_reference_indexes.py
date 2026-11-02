#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Reference indexes retain all static entries and advertise available targets.

CHANGELOG:
    2026-10-31 Cover gloss search data, unsampled Strong's entries and reduced builds.
    2026-11-01 Cover grouped occurrences, parallel writers, DC selection and Latin identity.
"""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import createOETReferencePages as pages
import Dict as dictionaries
from referenceIndexes import (referenceIndexLinks,strongIndexEntry,transliterateIndexLinks,lemmaIndexLink,filterableIndex,
    wordIndexRecord,groupWordIndex,wordIndex,dcWordIndexRecords)
from settings import State


class ReferenceIndexTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.state=State();self.state.TEST_MODE_FLAG=True
        self.state.booksToLoad={'OET':['MRK'],'OET-RV':['MRK'],'OET-LV':['MRK','TOB']}
        self.state.preloadedBibles={'OET-RV':{'MRK':object()},'OET-LV':{'MRK':object(),'TOB':object(),'PSS':object()}}
        self.state.OETRefData={'word_tables':{}}
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(BibleOrgSysGlobals,'verbosityLevel',0))
        for module in (pages,dictionaries):
            stack.enter_context(patch.object(module,'makeTop',return_value='<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            stack.enter_context(patch.object(module,'makeBottom',return_value='</body></html>'))

    def test_statistics_choose_combined_or_lv_and_keep_omitted_books_plain(self):
        pages.create_statistics_pages(2,self.root/'Stats',self.state)
        html=(self.root/'Stats/Chapters.htm').read_text()
        self.assertIn('OET/byC/MRK.htm#Top',html)
        self.assertIn('OET-LV/byC/TOB.htm#Top',html)
        self.assertNotIn('OET/byC/TOB',html)
        self.assertNotIn('/byC/GEN',html)
        self.assertNotIn('/byC/PSS',html) # Loaded in memory, omitted from this build.

    def test_ubs_index_keeps_all_entries_without_javascript_and_english_glosses(self):
        entries=[dict(MainId=str(number),Lemma=f'λόγος{number}',BaseForms=[dict(LEXMeanings=[dict(LEXSenses=[
            dict(LanguageCode='en',Glosses=['word & speech']),dict(LanguageCode='zhT',Glosses=['unrelated translation'])])])])
            for number in range(205)]
        folder=self.root/'UBS/Grk';folder.mkdir(parents=True)
        self.state.UBS_GNT_DATA=entries
        dictionaries.createUBSNavigationPages(2,folder,entries,'Greek',self.state)
        html=(folder/'index.htm').read_text()
        self.assertEqual(html.count('<li>'),205)
        self.assertIn('word &amp; speech',html)
        self.assertNotIn('unrelated translation',html)
        self.assertIn('referenceIndex.js',html)
        self.assertIn('ref/GrkLem/index.htm#Top',html)
        self.assertIn('ref/UGG/index.htm#Top',html)
        self.assertIn('205',html)

    def test_resource_navigation_only_includes_dc_when_a_chapter_will_be_built(self):
        self.state.OETRefData['word_tables']['OET-LV_DC_word_table.tsv']=['header','TOB_1:1w1']
        self.assertIn('ref/DCWrd/index.htm#Top',referenceIndexLinks(2,self.state))
        self.state.booksToLoad['OET-LV']=['MRK']
        self.assertNotIn('DCWrd',referenceIndexLinks(2,self.state))

    def test_strongs_index_includes_entries_between_the_old_sample_points(self):
        class Lexicon:
            def getStrongsEntryField(self,code,field):
                return ('λόγος','logos','') if code=='G3056' else None
        self.assertIn('G3056.htm#Top',strongIndexEntry('G3056',Lexicon()))
        self.assertIsNone(strongIndexEntry('G0000',Lexicon()))

    def test_transliterated_indexes_preserve_urls_and_english_glosses(self):
        original=lemmaIndexLink('dauid.htm','Δαυίδ',['David / Paul'])
        result=transliterateIndexLinks(original,pages.transliterate_Greek)
        self.assertIn('href="dauid.htm#Top"',result)
        self.assertIn('David / Paul',result)
        self.assertNotIn('Δαυίδ',result)

    def test_large_index_bounds_initial_page_and_preserves_every_search_and_static_entry(self):
        items=[lemmaIndexLink(f'λόγος{number}.htm','λόγος',['word & speech']) for number in range(10_001)]
        rendered=filterableIndex(2,'<p>'+' · '.join(items)+'</p>',outputFolder=self.root,stem='transIndex')
        self.assertIn('data-source="transIndex.json"',rendered)
        self.assertIn('href="transIndex-all.htm#Top"',rendered)
        self.assertEqual(rendered.count('<a '),201) # 200 entries and the full-list fallback.
        records=json.loads((self.root/'transIndex.json').read_text())
        self.assertEqual([row['html'] for row in records],items)
        self.assertIn('word & speech',records[-1]['text'])
        self.assertIn('λόγος10000.htm#Top',records[-1]['text'])
        complete=(self.root/'transIndex-all.htm').read_text()
        self.assertIn('href="transIndex.htm#Top"',complete)
        self.assertEqual(re.findall(r'<a\b[^>]*>.*?</a>',complete)[1:],items)

    def test_grouped_words_keep_exact_targets_glosses_and_numeric_occurrence_order(self):
        rows=[dict(word=word,language='Greek',href=f'MRKc1v{verse}w1.htm#Top',ref=f'MRK_1:{verse}w1',gloss='for & because')
              for word,verse in (('γάρ',10),('Γάρ',2),('γάρ',1))]
        groups=groupWordIndex(rows,pages.transliterate_Greek)
        self.assertEqual(len(groups),1)
        self.assertEqual([row['ref'] for row in groups[0]['occurrences']],['MRK_1:1w1','MRK_1:2w1','MRK_1:10w1'])
        for transliterated in (False,True):
            result=wordIndex(2,groups,self.root,transliterated=transliterated)
            self.assertIn('data-source="words.json"',result)
            self.assertIn('Barakiou',result)
            complete=(self.root/('transIndex-all.htm' if transliterated else 'index-all.htm')).read_text()
            self.assertEqual(complete.count('<details>'),1)
            self.assertIn('MRK 1:2, word 1 — for &amp; because',complete)
            self.assertIn('href="MRKc1v10w1.htm#Top" title=',complete)
        self.assertEqual(json.loads((self.root/'words.json').read_text()),groups)

    def test_unused_nt_variants_are_labelled_and_gloss_markup_is_plain(self):
        fields=['MRK_1:2w1','γάρ','lemma','lemma','for','for','','','10630','C','','']
        record=wordIndexRecord('Grk','variant.htm','γάρ',fields)
        self.assertEqual(record['status'],'Unused NT variant')
        fields[7]='100'
        self.assertNotIn('status',wordIndexRecord('Grk','used.htm','γάρ',fields))
        hebrew=['GEN_1:1w1','w','','','','','אֵת','אֵת',r'\untr DOM\untr*','','','','','','','','','','']
        self.assertEqual(wordIndexRecord('Heb','dom.htm','אֵת',hebrew)['gloss'],'DOM')

    def test_dc_search_preserves_aliases_row_anchors_and_latin_without_transliteration(self):
        self.state.preloadedBibles['OET-LV'].update({'GES':object(),'LAO':object()})
        self.state.booksToLoad['OET-LV']=['GES','LAO']
        self.state.OETRefData['word_tables']['OET-LV_DC_word_table.tsv']=['header']+[
            '\t'.join([ref,word,'lemma','morphology','lexicon gloss',gloss,'draft','source','[]','source ref','source file','',''])
            for ref,word,gloss in [('ES1_1:1w2','λόγος','word'),('LAO_1:1w1','Paulus','Paul'),('TOB_1:1w1','λόγος','omitted')]]
        records=dcWordIndexRecords(self.state,'../DCWrd/')
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['href'],'../DCWrd/GES_C1.htm#W1')
        self.assertEqual(records[0]['ref'],'GES_1:1w2')
        self.assertEqual(records[1]['href'],'../DCWrd/LAO_C1.htm#W2')
        groups=groupWordIndex(records,pages.transliterate_Greek)
        latin=next(group for group in groups if group['language']=='Latin')
        self.assertEqual(latin['transliteration'],'Paulus')
        self.assertEqual(latin['occurrences'][0]['status'],'DC draft')

    def test_word_writers_keep_context_in_sequential_and_parallel_paths(self):
        self.state.TEST_MODE_FLAG=False
        for language,word in (('Heb','עַם'),('Grk','γάρ')):
            fields=(["MRK_1:2w1",'w','','','','',word,word,'people','','','', '', '', '', '', '', '', ''] if language=='Heb'
                    else ['MRK_1:2w1',word,'lemma','lemma','for','because','', '100','10630','C','',''])
            self.state.OETRefData['word_tables'][f'OET-LV_{"OT" if language=="Heb" else "NT"}_word_table.tsv']=['header','\t'.join(fields)]
            full='Hebrew' if language=='Heb' else 'Greek'
            for processes in (1,4):
                with self.subTest(language=language,processes=processes), ExitStack() as stack:
                    stack.enter_context(patch.object(BibleOrgSysGlobals,'maxProcesses',processes))
                    stack.enter_context(patch.object(BibleOrgSysGlobals,'alreadyMultiprocessing',False))
                    stack.enter_context(patch.object(pages,f'get{full}WordpageFilename',return_value='actual-word.htm'))
                    stack.enter_context(patch.object(pages,f'create_{full}_word_page',return_value=True))
                    stack.enter_context(patch.object(pages,'runParallelPages',return_value=[(True,[],[])]))
                    folder=self.root/f'{language}-{processes}'
                    getattr(pages,f'create_{full}_word_pages')(2,folder,self.state)
                    groups=json.loads((folder/'words.json').read_text())
                    self.assertEqual(len(groups),1)
                    occurrence=groups[0]['occurrences'][0]
                    self.assertEqual(occurrence['href'],'actual-word.htm#Top')
                    self.assertEqual(occurrence['gloss'],'people' if language=='Heb' else 'because')
                    self.assertEqual(occurrence['ref'],'MRK_1:2w1')


if __name__=='__main__':
    unittest.main()
