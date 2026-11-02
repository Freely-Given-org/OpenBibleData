#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""UBS source senses retain their identifiers and original scripture numbering.

CHANGELOG:
    2026-10-30 Check readable senses, internal references and bounded OET examples.
    2026-10-31 Preserve note passage context without duplicate numeric reference lists.
    2026-11-02 Expect hyphenated LV-only passage labels.
    2026-11-02 Expect a single combined OET link in prose and metadata references.
"""
import re
import unittest
from urllib.parse import unquote
from unittest.mock import patch

from ubsDictionary import parseUBSReference,renderUBSEntry,ubsText
import test_reference_passages as fixtures


class UBSDictionaryTests(unittest.TestCase):
    setUp=fixtures.ReferencePassageTests.setUp
    load=fixtures.ReferencePassageTests.load
    render=fixtures.ReferencePassageTests.render
    prepare=fixtures.ReferencePassageTests.prepare

    def entry(self):
        entry=dict(MainId='001',Lemma='אָב',StrongCodes=['H0001'],BaseForms=[dict(BaseFormID='001001',
            PartsOfSpeech=['noun'],LEXMeanings=[dict(LEXID='001001001',LEXEntryCode='1.1',
                LEXDomains=[dict(Domain='Relatives',DomainCode='123')],
                LEXSenses=[dict(LanguageCode='en',Glosses=['father'],DefinitionShort='A father & parent.',Comments='See {S:03900301900001}.')],
                LEXReferences=['03900301900001','03900301900003','03900302000001','03900302100001'])])])
        self.state.UBS_HEB_DATA=[entry]
        self.state.UBS_GNT_DATA=[]
        return entry

    def test_original_numbering_and_position_field_are_separate(self):
        self.assertEqual(parseUBSReference('03900302400008'),('MAL','3','24',None))
        self.assertEqual(parseUBSReference('04701301300028{N:001}'),('CO2','13','13',None))
        self.assertEqual(parseUBSReference('00301100000000'),('LEV','11','0',None))
        with self.assertRaises(ValueError):parseUBSReference('03909999900001')

    def test_readable_sense_has_two_examples_and_all_other_passages(self):
        self.prepare()
        html=renderUBSEntry(2,'Heb',self.entry(),self.state)
        self.assertIn('Sense 1: father',html)
        self.assertIn('A father &amp; parent.',html)
        self.assertIn('Relatives (123)',html)
        self.assertIn('RV one.',html)
        self.assertIn('LV nineteen.',html)
        self.assertEqual(html.count('Show passage in OET'),2)
        self.assertIn('All 3 recorded passages for this sense',html)
        self.assertIn('id="sense001001001"',html)
        self.assertNotIn('LEXReferences',html)
        self.assertNotIn('{S:',html)

    def test_repeated_verses_in_different_senses_have_unique_ids(self):
        self.prepare();entry=self.entry()
        meaning=dict(entry['BaseForms'][0]['LEXMeanings'][0],LEXID='001001002')
        entry['BaseForms'][0]['LEXMeanings'].append(meaning)
        html=renderUBSEntry(2,'Heb',entry,self.state)
        ids=re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertIn('id="sense001001002"',html)

    def test_internal_dictionary_and_semantic_entry_links_target_emitted_anchors(self):
        self.prepare();entry=self.entry()
        html=unquote(ubsText('{L:father<SDBH:אָב>} · {D:1.1}',2,'Heb',self.state,'test'))
        self.assertIn('UBS/Heb/אָב.htm#Top">father</a>',html)
        self.assertIn('UBS/Heb/אָב.htm#sense001001001',html)
        rendered=renderUBSEntry(2,'Heb',entry,self.state)
        self.assertIn('id="sense001001001"',rendered)

    def test_unknown_source_token_is_safe_readable_text(self):
        self.prepare();self.entry()
        html=ubsText('a < b {L:missing<SDBH:no-entry>} {D:9999} {S:bad}',2,'Heb',self.state,'test')
        self.assertIn('a &lt; b missing',html)
        self.assertIn('Semantic domain 9999',html)
        self.assertNotIn('href=',html)

    def test_note_omits_metadata_references_already_cited_in_prose(self):
        self.prepare();entry=self.entry();entry['BaseForms']=[]
        entry['Notes']=[dict(Caller=1,LanguageCode='en',
            References=['03900301900001','03900301900003{N:001}'],
            Content='Compare {S:03900301900028}.')]
        html=renderUBSEntry(2,'Heb',entry,self.state)
        self.assertIn('<b>Notes:</b> Compare ',html)
        self.assertEqual(html.count('OET/byC/MAL_C4.htm#C4V1'),1)
        self.assertNotIn('OET-LV/byC/',html)
        self.assertNotIn('039003019',html)
        self.assertNotIn('<b>Passage',html)

    def test_note_keeps_readable_links_for_references_missing_from_prose(self):
        self.prepare();entry=self.entry();entry['BaseForms']=[]
        entry['Notes']=[dict(Caller=1,LanguageCode='en',
            References=['03900301900001','03900302000001{N:006}','03900302000003'],
            Content='Compare {S:03900301900028}.'),
            dict(Caller=2,LanguageCode='zhT',References=['03900302100001'],Content='Other language')]
        html=renderUBSEntry(2,'Heb',entry,self.state)
        for verse in (1,2):self.assertEqual(html.count(f'OET/byC/MAL_C4.htm#C4V{verse}'),1)
        self.assertIn('<b>Passage:</b>',html)
        self.assertIn('OET MAL 4:2',html)
        self.assertNotIn('0390030',html)
        self.assertNotIn('Other language',html)
        self.assertNotIn(';</p>',html)

    def test_note_with_only_metadata_references_still_has_passage_context(self):
        self.prepare();entry=self.entry();entry['BaseForms']=[]
        entry['Notes']=[dict(Caller=1,LanguageCode='en',References=['03900301900001'],Content='')]
        html=renderUBSEntry(2,'Heb',entry,self.state)
        self.assertIn('OET/byC/MAL_C4.htm#C4V1',html)
        self.assertNotIn('OET-LV/byC/',html)
        self.assertNotIn('039003019',html)


if __name__=='__main__':unittest.main()
