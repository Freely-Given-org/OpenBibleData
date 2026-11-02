#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""People and places remain discoverable by names-table aliases and traditional names.

CHANGELOG:
    2026-11-02 Cover duplicate table rows, namesakes, qualifiers and generated indexes.
"""
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from BibleOrgSys import BibleOrgSysGlobals
import createOETReferencePages as pages
import referenceEntities as entities
from settings import State


class EntityNameIndexTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.table = self.root/'names.tsv'
        self.table.write_text('\ufeffTraditionalName\tGrkName\tRVName\tExplained\tComment\n'
            'Goliath\t\tGalyat\tY\tMan\n'
            'Jerusalem\t\tHierousalaim\t\tCity\n'
            'Jerusalem\t\tYerushalem\tY\tCity\n'
            'Jerusalem\t\tYerushalem\tY\tRepeated row\n'
            'Abdi\t\tAvdi\t\tPeople\n'
            'Peter\t\tKefa\t\tMan\n'
            'Lebanon\t\tLevanon\t\tPlace\n',encoding='utf-8')
        self.patch = patch.object(entities,'OET_RV_NAMES_TABLE_PATH',self.table)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.state = State()
        self.state.preloadedBibles = {}
        self.state.booksToLoad = {'OET':[],'OET-RV':[],'OET-LV':[]}
        self.state.OETRefData = {'word_tables':{}}

    def test_repeated_rows_retain_all_spellings_and_reload_for_each_build(self):
        aliases = entities.loadOETRVNameAliases(self.state)
        self.assertEqual(aliases['jerusalem'],('Hierousalaim','Yerushalem'))
        self.assertIs(aliases,entities.loadOETRVNameAliases(self.state))
        self.table.write_text('TraditionalName\tRVName\nGoliath\tChangedName\n')
        self.assertEqual(entities.loadOETRVNameAliases(SimpleNamespace())['goliath'],('ChangedName',))

    def test_malformed_table_identifies_the_source_and_row(self):
        self.table.write_text('TraditionalName\tRVName\nGoliath\t\n')
        with self.assertRaisesRegex(ValueError,r'names.tsv:2: missing'):
            entities.loadOETRVNameAliases(self.state)

    def test_name_fields_match_without_borrowing_names_from_qualifiers(self):
        aliases = entities.loadOETRVNameAliases(self.state)
        self.assertIn('Kefa',entities.entityNames(dict(displayTitle='Simon Peter',name='Simon',surname='Peter'),aliases))
        self.assertNotIn('Galyat',entities.entityNames(dict(displayTitle='Lahmi (brother of Goliath)',name='Lahmi'),aliases))
        self.assertIn('Mount Levanon',entities.entityNames(dict(displayTitle='Mount Lebanon'),aliases))
        self.assertIn('Yerushalem’s',entities.entityNames(dict(displayTitle='Jerusalem’s'),aliases))
        self.assertEqual(entities.oetRVNameVariants('Beth Shan',{'bethshan':('Beyt-Shan',)}),('Beyt-Shan',))

    def test_alias_collisions_keep_distinct_destinations_and_reference_qualifiers(self):
        records = {'PAbdi1':dict(displayTitle='Abdi',verses=['CH1_6:44']),
                   'PAbdi2':dict(displayTitle='Abdi',verses=['EZR_10:26'])}
        data = dict(records=records,nameCounts=Counter(entry['displayTitle'] for entry in records.values()))
        links = entities.entityIndexLinks(records,data,self.state)
        self.assertEqual(len(links),4)
        self.assertTrue(any('Abdi1.htm#Top">Avdi' in link and 'CH1 6:44' in link for link in links))
        self.assertTrue(any('Abdi2.htm#Top">Avdi' in link and 'EZR 10:26' in link for link in links))

    def test_generated_indexes_browse_and_filter_both_names_with_valid_destinations(self):
        people = {'PGoliath':dict(displayTitle='Goliath',name='Goliath',dictText='',gender='Male',birthYear='',deathYear='')}
        places = {'LJerusalem':dict(displayTitle='Jerusalem',kjvName='Jerusalem',esvName='Jerusalem',
                    dictText='',comment='',featureType='City',featureSubType='')}
        for filename,records in (('normalised_People.json',people),('normalised_Places.json',places)):
            (self.root/filename).write_text(json.dumps(records))
        with ExitStack() as stack:
            stack.enter_context(patch.object(pages,'THEOGRAPHIC_INPUT_FOLDER_PATH',self.root))
            stack.enter_context(patch.object(BibleOrgSysGlobals,'verbosityLevel',0))
            stack.enter_context(patch.object(pages,'makeTop',return_value='<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            stack.enter_context(patch.object(pages,'makeBottom',return_value='</body></html>'))
            pages.create_person_pages(2,self.root/'Per',self.state)
            pages.create_location_pages(2,self.root/'Loc',self.state)
        for folder,title,expected in (
                ('Per','All Bible People',('Galyat','Goliath')),
                ('Loc','Bible Locations',('Hierousalaim','Jerusalem','Yerushalem'))):
            html = (self.root/folder/'index.htm').read_text()
            self.assertIn(f'{title} Index (1)</h1>',html)
            self.assertIn('referenceIndex.js',html)
            entries = html.split('<div class="referenceIndexEntries">',1)[1].split('</div>',1)[0]
            links = re.findall(r'<a href="([^"]+)">(.+?)</a>',entries)
            self.assertEqual(len(links),len(expected))
            for (href,label),name in zip(links,expected):
                self.assertTrue(label.startswith(name),label)
                self.assertTrue((self.root/folder/unquote(href.split('#')[0])).is_file(),href)
            self.assertEqual(len({href for href,_label in links}),1)


if __name__ == '__main__': unittest.main()
