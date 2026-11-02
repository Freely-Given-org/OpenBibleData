#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Study associations use explicit topics, native word tags and verified identities.

CHANGELOG:
    2026-10-30 Check reverse topics and entity links across different verse numbers.
"""
import json
import unittest
from urllib.parse import unquote

import test_reference_passages as fixtures
from studyReferences import (prepareTopicAssociations,prepareStudyAssociations,
                             passageReferenceMaterial,topicReferenceMaterial,lemmaTopics,topicFilename)


class StudyReferenceTests(unittest.TestCase):
    setUp=fixtures.ReferencePassageTests.setUp
    load=fixtures.ReferencePassageTests.load
    render=fixtures.ReferencePassageTests.render
    prepare=fixtures.ReferencePassageTests.prepare

    def associations(self):
        self.prepare()
        people={'PMoses':dict(displayTitle='Moses'),
                'PAbdi1':dict(displayTitle='Abdi',verses=['MAL_3:19']),
                'PAbdi2':dict(displayTitle='Abdi',verses=['MAL_3:20'])}
        places={'LEgypt':dict(displayTitle='Egypt')}
        (self.root/'normalised_People.json').write_text(json.dumps(people))
        (self.root/'normalised_Places.json').write_text(json.dumps(places))
        table=[]
        for verse,tags in ((19,'PMoses;PAbdi1;LEgypt'),(20,'PAbdi2')):
            fields=['']*19;fields[0]=f'MAL_3:{verse}w1';fields[1]='w';fields[10]='Moses';fields[-1]=tags
            table.append('\t'.join(fields))
        name='OET-LV_OT_word_table.tsv'
        self.state.OETRefData=dict(word_tables={name:['header',*table]},word_table_indexes={name:{'MAL_3:19':(1,1),'MAL_3:20':(2,2)}})
        self.state.TOBDData={'Articles':{'Moses':'article','Egypt':'article'}}
        prepareTopicAssociations(self.state,{'A selected topic':['H3 Heading','MAL_4:1-2','GrkLem/logos']})
        return prepareStudyAssociations(self.state,self.root)

    def test_english_page_maps_to_native_lv_word_tags_and_reverse_topic(self):
        self.associations()
        html=unquote(passageReferenceMaterial(2,('MAL','4','1'),'eng',self.state))
        self.assertIn('ref/Per/Abdi1.htm#Top',html)
        self.assertNotIn('Abdi2.htm',html)
        self.assertIn('ref/Loc/Egypt.htm#Top',html)
        self.assertIn('dct/Moses.htm#Top',html)
        self.assertIn('tpc/ASelectedTopic.htm#Top',html)

    def test_topic_associations_keep_distinct_people_with_the_same_name(self):
        self.associations()
        html=topicReferenceMaterial(1,'A selected topic',self.state)
        self.assertIn('ref/Per/Abdi1.htm#Top',html)
        self.assertIn('ref/Per/Abdi2.htm#Top',html)
        self.assertIn('Abdi (MAL 3:19)',html)
        self.assertIn('Abdi (MAL 3:20)',html)

    def test_lemma_reverse_link_requires_explicit_topic_lemma(self):
        self.associations()
        self.assertIn('tpc/ASelectedTopic.htm#Top',lemmaTopics(2,'Grk','logos',self.state))
        self.assertEqual(lemmaTopics(2,'Grk','unlisted',self.state),'')

    def test_english_gloss_does_not_create_an_entity_or_dictionary_association(self):
        graph=self.associations()
        graph['wordEntities']={}
        html=passageReferenceMaterial(2,('MAL','4','1'),'eng',self.state)
        self.assertNotIn('Moses.htm',html)
        self.assertIn('Used in these topics',html)

    def test_unavailable_passage_does_not_get_empty_controls(self):
        self.associations()
        self.assertEqual(passageReferenceMaterial(2,('GEN','1','1'),'eng',self.state),'')
        self.assertEqual(passageReferenceMaterial(2,('MAL','-1','0'),'eng',self.state),'')


if __name__=='__main__':unittest.main()
