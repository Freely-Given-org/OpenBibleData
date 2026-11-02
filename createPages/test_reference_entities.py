#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Entity navigation is based on explicit identities, including reciprocal data.

CHANGELOG:
    2026-10-30 Check person/place lookups, reciprocal relationships and ambiguity.
    2026-11-02 Keep grouped preview coverage and readable invalid citations.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from referenceEntities import (loadReferenceEntities, entityRelationships, entityPassages, selectedPassageControls,
                               entityTaggedWords, prepareEntityWordIndex, entityRelatedResources)
from settings import State


class ReferenceEntityTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.state = SimpleNamespace()
        self.people = {
            'PMoses':dict(displayTitle='Moses',mother='PJochebed',father='PAmram',siblings=['PAaron'],
                          birthPlace='egypt_lookup',partners=['PZipporah']),
            'PJochebed':dict(displayTitle='Jochebed'), 'PAmram':dict(displayTitle='Amram'),
            'PAaron':dict(displayTitle='Aaron'), 'PZipporah':dict(displayTitle='Zipporah',TBDPersonLookup='zipporah_lookup'),
            'PAbdi1':dict(displayTitle='Abdi',verses=['CH1_6:44']),
            'PAbdi2':dict(displayTitle='Abdi',verses=['EZR_10:26']),
        }
        self.places = {'LEgypt':dict(displayTitle='Egypt',TBDPlaceLookup='egypt_lookup',hasBeenHere='zipporah_lookup',peopleBorn=['PAbdi2'])}

    def load(self):
        (self.root/'normalised_People.json').write_text(json.dumps(self.people))
        (self.root/'normalised_Places.json').write_text(json.dumps(self.places))
        return loadReferenceEntities(self.root,self.state)

    def test_family_and_birthplace_links_resolve_and_are_reciprocal(self):
        data = self.load()
        html = entityRelationships('PMoses',2,data)
        for target in ('Per/Jochebed','Per/Amram','Per/Aaron','Per/Zipporah','Loc/Egypt'):
            self.assertIn(f'../../ref/{target}.htm#Top',html)
        self.assertIn('Per/Moses.htm#Top',entityRelationships('PAmram',2,data))
        self.assertIn('Per/Moses.htm#Top',entityRelationships('LEgypt',2,data))
        self.assertIn('Loc/Egypt.htm#Top',entityRelationships('PZipporah',2,data))

    def test_identically_named_people_are_not_conflated(self):
        html = entityRelationships('LEgypt',2,self.load())
        self.assertIn('Per/Abdi2.htm#Top">Abdi (EZR 10:26)',html)
        self.assertNotIn('Abdi1.htm',html)

    def test_unresolved_slug_produces_diagnostic_without_guessed_filename(self):
        self.people['PMoses']['deathPlace'] = 'missing_place'
        with self.assertLogs(level='WARNING') as messages: data = self.load()
        self.assertIn('PMoses',messages.output[0])
        self.assertIn('missing_place',messages.output[0])
        self.assertNotIn('missing_place',entityRelationships('PMoses',2,data))

    def test_person_without_article_gets_examples_and_all_recorded_references(self):
        self.people['PAbdi1'].update(dictText='',verses=['CH1_6:44','GEN_1:2','GEN_1:1','GEN_1:3','GEN_1:4'])
        data = self.load()
        with patch('referencePassages._referencePassageParts',return_value=('preview','jump')) as render:
            html = entityPassages('PAbdi1',2,data,self.state)
        self.assertIn('Recorded scripture occurrences (5)',html)
        self.assertIn('GEN: all 4 recorded references',html)
        self.assertEqual(sum(call.kwargs.get('preview',True) for call in render.call_args_list),3)
        self.assertEqual(render.call_args_list[0].args[1],(('GEN','1','1',None),))

    def test_tag_index_preserves_native_word_identity_and_reduced_build_availability(self):
        data = self.load()
        state = State()
        state.TEST_MODE_FLAG = True
        state.ALL_TEST_REFERENCE_PAGES_FLAG = True
        state.booksToLoad = {'OET':['MRK']}
        row = '\t'.join(['GEN_1:1w1','','1','1','1254','Vqp3ms','בָּרָא','בָּרָא','created','','created','','','','1','','','','PMoses;LEgypt'])
        state.OETRefData = {'word_tables':{'OET-LV_OT_word_table.tsv':['header',row]}}
        prepareEntityWordIndex(data,state)
        self.assertEqual(data['passageEntities']['GEN_1:1'],('LEgypt','PMoses'))
        html = entityTaggedWords('PMoses',2,data,state)
        self.assertIn('ref/HebWrd/GENc1v1w1.htm#Top',html)
        self.assertNotIn('OET/byC/GEN',html)
        state.ALL_TEST_REFERENCE_PAGES_FLAG = False
        state.TEST_BOOK_LIST = ['MRK']
        self.assertEqual(entityTaggedWords('PMoses',2,data,state),'')

    def test_dictionary_associations_require_a_known_article_and_identity(self):
        state = SimpleNamespace(TOBDData={'Articles':{'Moses':'Article'}})
        self.assertIn('dct/Moses.htm#Top',entityRelatedResources('PMoses',2,state))
        self.assertNotIn('dct/',entityRelatedResources('PAbdi1',2,state))
        state.TOBDData = {}
        self.assertNotIn('dct/',entityRelatedResources('PMoses',2,state))

    def test_source_ezekiel_alias_resolves_and_invalid_citations_remain_readable(self):
        with patch('referencePassages._referencePassageParts',return_value=('preview','linked')) as render, \
             self.assertLogs(level='WARNING'):
            html = selectedPassageControls(['EZK_1:1','ISA_18:23'],2,self.state,'sample')
        self.assertEqual(render.call_args.args[1],(('EZE','1','1',None),))
        self.assertIn('ISA 18:23 (reference unavailable)',html)


if __name__ == '__main__': unittest.main()
