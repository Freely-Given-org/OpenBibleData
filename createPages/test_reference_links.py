#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Regression tests for reference navigation and generated scripture destinations.

CHANGELOG:
    2026-10-30 Check person/place navigation, chapter citations and kingdom links.
    2026-10-31 Check approved kingdom readings, retained maps and prophet identities.
    2026-11-02 Verify the same reading selections through the grouped preview renderer.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from BibleOrgSys import BibleOrgSysGlobals
import createOETReferencePages as pages
import createTopicPages as topics
import Dict as dictionaries
from urllib.parse import unquote
from settings import State


class ReferenceLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.booksToLoad = {'OET': ['GEN','SA1']}
        self.state.preloadedBibles = {'OET-RV': {}}
        self.state.OETRefData = {'word_tables': {}}
        self.stack.enter_context(patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0))
        for module in (pages, topics, dictionaries):
            self.stack.enter_context(patch.object(module, 'makeTop', return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            self.stack.enter_context(patch.object(module, 'makeBottom', return_value='</body></html>'))

    def test_chapter_and_verse_citations_resolve_outside_entity_directory(self):
        html = pages.livenMD(2, '[Ex. 3](/exod#Exod.3), [Gen. 1:2](/gen#Gen.1.2), [Jude 1](/jude#Jude.1)')
        self.assertEqual(re.findall(r'href="([^"]+)"', html), [
            '../../OET/byC/EXO_C3.htm#C3V1', '../../OET/byC/GEN_C1.htm#C1V2',
            '../../OET/byC/JDE_C1.htm#C1V1'])

    def test_invalid_article_citations_are_readable_and_diagnosable(self):
        with self.assertLogs(level='WARNING') as messages:
            html = pages.livenMD(2,'[1 Sam. 33:24](/1sam#1Sam.33.24), [John 15:44](/john#John.15.44)',self.state,'LExample')
        self.assertEqual(html,'1 Sam. 33:24, John 15:44')
        self.assertIn('LExample',messages.output[0])

    def test_entity_navigation_targets_existing_files_and_top_anchors(self):
        self.stack.enter_context(patch.object(pages, 'THEOGRAPHIC_INPUT_FOLDER_PATH', self.root))
        # Header-free data also exercises navigation independently of metadata ordering.
        people = {f'P{name}': dict(displayTitle=name, birthYear='', deathYear='',
                  dictText='A person.', gender='Male') for name in ('Aaron','Moses')}
        places = {f'L{name}': dict(displayTitle=name, comment='', dictText='A place.',
                  kjvName=name, esvName=name, featureType='City', featureSubType='')
                  for name in ('Jerusalem','Bethlehem')}
        (self.root/'normalised_People.json').write_text(json.dumps(people))
        (self.root/'normalised_Places.json').write_text(json.dumps(places))
        pages.create_person_pages(2, self.root/'ref/Per', self.state)
        pages.create_location_pages(2, self.root/'ref/Loc', self.state)
        selected = [('Aaron','Aaron',[]), ('Moses','Moses',[])]
        with patch.object(pages,'IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST',selected), \
             patch.object(pages,'IMPORTANT_PEOPLE_ALPHABETICAL_LIST',selected):
            pages.create_important_person_pages(2, self.root/'ref/Per', self.state)
        for folder, names in (('Per',('Aaron','Moses')), ('Loc',('Jerusalem','Bethlehem'))):
            for i,name in enumerate(names):
                path = self.root/'ref'/folder/f'{name}.htm'
                html = path.read_text()
                self.assertIn('<h1 id="Top">', html)
                nav = re.search(r'<p class="prevNextLinks">(.*?)</p>',html)[1]
                self.assertEqual('title="Previous ' in nav, i > 0)
                self.assertEqual('title="Next ' in nav, i < len(names)-1)
                for href in re.findall(r'href="([^"]+)"',nav):
                    filename, _, anchor = href.partition('#')
                    destination = path.parent/filename
                    self.assertTrue(destination.is_file(), (path,href))
                    if anchor:
                        self.assertIn(f'id="{anchor}"', destination.read_text(), (path,href))

    def test_reference_index_chronological_link_stays_inside_reference_tree(self):
        with ExitStack() as stack:
            for name in dir(pages):
                if name.startswith(('create_', 'preprocess')) and callable(getattr(pages,name)):
                    stack.enter_context(patch.object(pages,name))
            stack.enter_context(patch.object(pages.BibleLexicon,'getBibleLexicon',return_value=Mock()))
            pages.createOETReferencePages(1,self.root/'ref',self.state)
        html = (self.root/'ref/index.htm').read_text()
        self.assertIn('href="Per/importantPeopleChronologicalIndex.htm#Top"',html)
        self.assertNotIn('href="../Per/',html)

    def test_kingdom_scripture_link_and_index_use_current_destinations(self):
        with patch.object(topics,'getBibleMapperMaps',return_value=''):
            topics.createKingdomPages(2,self.root/'ref/Kingdoms',self.state)
        html = (self.root/'ref/Kingdoms/FullKingdom.htm').read_text()
        self.assertIn('href="../../OET/byC/SA1_C7.htm#C7V2"',html)
        self.assertNotIn('__SAMUEL_LINK__',html)
        index = (self.root/'ref/Kingdoms/index.htm').read_text()
        for order in ('Alphabetical','Chronological'):
            self.assertIn(f'../Per/importantPeople{order}Index.htm#Top',index)
        self.assertNotIn('importantIndex.htm',index)

    def test_reduced_kingdom_build_keeps_unbuilt_scripture_as_readable_text(self):
        self.state.TEST_MODE_FLAG = True
        self.state.booksToLoad = {'OET':['MRK']}
        with patch.object(topics,'getBibleMapperMaps',return_value=''):
            topics.createKingdomPages(2,self.root/'ref/Kingdoms',self.state)
        html = (self.root/'ref/Kingdoms/FullKingdom.htm').read_text()
        self.assertIn('Shemuel (Samuel)',html)
        self.assertNotIn('SA1_C7',html)

    def test_kingdom_readings_keep_full_ranges_and_distinct_prophet_identities(self):
        from referenceEntities import entityRelatedResources
        with patch.object(topics,'getBibleMapperMaps',return_value='<p>Existing map</p>') as maps, \
             patch('referencePassages._referencePassageParts',return_value=('preview','jump')) as render:
            topics.createKingdomPages(2,self.root/'ref/Kingdoms',self.state)
        self.assertEqual(maps.call_count,sum(len(refs) for _,refs in topics.KINGDOM_LIST))
        selections=[call.args[1] for call in render.call_args_list]
        self.assertEqual([(refs[0][:3],refs[-1][:3]) for refs in selections],[
            (('GEN','12','1'),('GEN','12','7')),(('JOS','21','43'),('JOS','21','45')),
            (('SA2','7','8'),('SA2','7','16')),(('KI1','12','25'),('KI1','12','33')),
            (('KI2','18','1'),('KI2','18','7')),(('KI2','25','1'),('KI2','25','12')),
            (('EZE','37','21'),('EZE','37','28'))])
        full=(self.root/'ref/Kingdoms/FullKingdom.htm').read_text()
        self.assertIn('Per/Gad2.htm#Top',full)
        self.assertNotIn('Per/Gad.htm#Top',full)
        southern=(self.root/'ref/Kingdoms/SouthernKingdom.htm').read_text()
        for prophet in ('Micah3','Zephaniah2','Obadiah12','Joel14'):
            self.assertIn(f'Per/{prophet}.htm#Top',southern)
            self.assertIn('Kingdoms/SouthernKingdom.htm#Top',entityRelatedResources(f'P{prophet}',2,self.state))
        self.assertIn('Existing map',southern)

    def test_ubs_articles_indexes_and_introductions_link_to_existing_anchors(self):
        self.state.UBS_GNT_DATA = [{'MainId':'1','Lemma': 'λόγος'}, {'MainId':'2','Lemma': 'ἀγάπη'}]
        self.state.UBS_HEB_DATA = [{'MainId':'1','Lemma': 'אָב'}, {'MainId':'2','Lemma': 'בֵּן'}]
        dictionaries.createUBSDictionaryPages(1,self.root/'UBS',self.state)
        for folder, lemmas in (('Grk',('λόγος','ἀγάπη')),('Heb',('אָב','בֵּן'))):
            for filename in ('index.htm','intro.htm',*[f'{lemma}.htm' for lemma in lemmas]):
                path = self.root/'UBS'/folder/filename
                html = path.read_text()
                self.assertIn('id="Top"',html)
                for href in re.findall(r'href="([^"]+)"',html):
                    if href.startswith(('../../','http')):
                        continue # Site chrome/licence pages are generated independently.
                    destination, _, anchor = unquote(href).partition('#')
                    target = path.parent/destination
                    self.assertTrue(target.is_file(),(path,href))
                    if anchor:
                        self.assertIn(f'id="{anchor}"',target.read_text(),(path,href))
        self.assertIn('Biblical Hebrew',(self.root/'UBS/Heb/index.htm').read_text())


if __name__ == '__main__':
    unittest.main()
