#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Important people indexes share identities, valid passages and alphabetical aliases.

CHANGELOG:
    2026-11-02 Check the expanded selection, namesakes, counts and generated indexes.
    2026-11-02 Check both generated orders include the names-table RV spellings.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import createOETReferencePages as pages
from referencePassages import parseReferenceSelection
from settings import State


class ImportantPeopleTests(unittest.TestCase):
    def test_selection_counts_characters_and_covers_previous_people_and_major_omissions(self):
        rows = pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST
        identities = [personID or name for name,personID,_ in rows]
        self.assertGreaterEqual(len(rows),150)
        self.assertLessEqual(len(rows),200)
        self.assertEqual(len(identities),len(set(identities)))
        previous = {'Adam','Eve','Cain','Abel','Abraham','Lot','Melchisedec','Joseph','Moses',
                    'Aaron','Joshua','Balaam','Samson','Naomi','Ruth','Samuel','Saul','David',
                    'Solomon','Hezekiah','Jeremiah','Zacharias','Jesus','John2','Jonah',
                    'Matthew','Lazarus','Lazarus1','Barnabas'}
        additions = {'Noah','Sarah','Isaac','Israel','Rebekah','Deborah','Gideon','Esther',
                     'Elijah','Elisha','Isaiah','Ezekiel','Daniel','Job','Mary','Mary6',
                     'Joseph6','John','Simon','Paul','Stephen','Lydia','Priscilla','Aquila'}
        minorProphets = {'Hosea','Joel14','Amos','Obadiah12','Jonah','Micah3','Nahum',
                        'Habakkuk','Zephaniah2','Haggai','Zechariah14','Malachi'}
        apostles = {'Simon','Andrew','James','John2','Philip1','Bartholomew','Thomas',
                    'Matthew','James2','Lebbaeus','Simon2','Judas','Matthias'}
        self.assertFalse((previous | additions | minorProphets | apostles)-set(identities))

    def test_alphabetical_aliases_share_identity_passages_and_are_sorted(self):
        chronological = {personID or name:refs for name,personID,refs in pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST}
        alphabetical = pages.IMPORTANT_PEOPLE_ALPHABETICAL_LIST
        plainNames = [re.sub(r'<[^>]+>','',name) for name,_,_ in alphabetical]
        self.assertEqual(plainNames,sorted(plainNames,key=str.casefold))
        self.assertEqual(len(plainNames),len(set(plainNames)))
        self.assertEqual({personID or name for name,personID,_ in alphabetical},set(chronological))
        for name,personID,refs in alphabetical:
            with self.subTest(name=name):
                self.assertEqual(refs,chronological[personID or name])
        for prefix,personID in (('Abram/','Abraham'),('Abraham/','Abraham'),('Moses/','Moses'),
                ('Mosheh/','Moses'),('Ruth/','Ruth'),('Rut/','Ruth'),('Israel/','Israel'),
                ('Paul/','Paul'),('Saul/','Paul'),('Melchizedek/','Melchisedec')):
            self.assertTrue(any(name.startswith(prefix) and key==personID for name,key,_ in alphabetical),prefix)

    def test_namesakes_use_specific_identities_and_retain_qualifiers_on_aliases(self):
        rows = pages.IMPORTANT_PEOPLE_ALPHABETICAL_LIST
        for prefix,identities in (
                ('Mary/',{'Mary','Mary2','Mary6'}),
                ('Joseph/',{'Joseph','Joseph6','Joseph7'}),
                ('John/',{'John','John2'}),
                ('Zechariah/',{'Zacharias','Zechariah14'}),
                ('Philip ',{'Philip','Philip1'}),
                ('Lazarus ',{'Lazarus','Lazarus1'})):
            matching = [(name,personID) for name,personID,_ in rows if name.startswith(prefix)]
            self.assertEqual({personID for _,personID in matching},identities)
            self.assertTrue(all(' (' in name for name,_ in matching))
        references = {personID:refs for _,personID,refs in rows if personID}
        self.assertIn('GEN_30:24',references['Joseph'])
        self.assertNotIn('GEN_17:5',references['Joseph'])

    def test_selected_passages_exist_in_the_declared_english_versification(self):
        for name,_personID,refs in pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST:
            self.assertTrue(refs,name)
            for citation in refs:
                with self.subTest(name=name,citation=citation):
                    book,selection = citation.split('_')
                    self.assertTrue(parseReferenceSelection(book,selection,'eng'))

    def test_chronology_keeps_key_generations_and_testaments_in_order(self):
        identities = [personID for _,personID,_ in pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST]
        for earlier,later in (('Noah','Abraham'),('Abraham','Isaac'),('Isaac','Israel'),
                ('Israel','Joseph'),('Joseph','Moses'),('Moses','Joshua'),('Saul','David'),
                ('David','Solomon'),('Elijah','Elisha'),('Jonah','Jesus'),('John','John2'),
                ('Jesus','Paul')):
            self.assertLess(identities.index(earlier),identities.index(later))

    @unittest.skipUnless((pages.THEOGRAPHIC_INPUT_FOLDER_PATH/'normalised_People.json').is_file(),
                         'Local Theographic people data is not installed')
    def test_person_destinations_exist_in_the_actual_source_data(self):
        people = json.loads((pages.THEOGRAPHIC_INPUT_FOLDER_PATH/'normalised_People.json').read_text())
        for name,personID,_ in pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST:
            if personID:
                with self.subTest(name=name): self.assertIn('P'+personID,people)

    def test_both_generated_indexes_count_people_and_keep_all_passage_controls(self):
        rows = pages.IMPORTANT_PEOPLE_CHRONOLOGICAL_LIST
        with TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            people = {'P'+personID:{} for _,personID,_ in rows if personID}
            (root/'normalised_People.json').write_text(json.dumps(people))
            stack.enter_context(patch.object(pages,'THEOGRAPHIC_INPUT_FOLDER_PATH',root))
            stack.enter_context(patch.object(BibleOrgSysGlobals,'verbosityLevel',0))
            stack.enter_context(patch.object(pages,'makeTop',return_value=
                '<!DOCTYPE html><html><head><title>__TITLE__</title></head><body>'))
            stack.enter_context(patch.object(pages,'makeBottom',return_value='</body></html>'))
            state = State()
            state.booksToLoad = {'OET':[],'OET-RV':[],'OET-LV':[]}
            state.preloadedBibles = {}
            # Include an alias absent from the curated labels to exercise the table lookup.
            state.oetRVNameAliases = {'goliath':('Galyat',),'lazarus':('Lazaros',)}
            enrichedRows = pages._importantPeopleWithRVNames(rows,state.oetRVNameAliases)
            alphabetical = pages._importantPeopleAlphabeticalList(enrichedRows)
            pages.create_important_person_pages(2,root/'Per',state)
            for order,entries in (('Chronological',enrichedRows),('Alphabetical',alphabetical)):
                html = (root/'Per'/f'importantPeople{order}Index.htm').read_text()
                self.assertIn(f'Important Bible People {order} Index ({len(rows)})</h1>',html)
                self.assertEqual(html.count('title="Go to person details page"'),sum(bool(key) for _,key,_ in entries))
                for name,personID,refs in entries:
                    with self.subTest(order=order,name=name):
                        self.assertIn(name,html)
                        if personID: self.assertIn(f'href="{personID}.htm"',html)
                        for ref in refs:
                            book,selection = ref.split('_')
                            self.assertIn(f'{book} {selection}',html)
                self.assertIn('Galyat',html)
                self.assertIn('Lazaros',html)
                self.assertIn('(in parable)',html)
                self.assertIn('Samaritan woman (at the well)',html)
                self.assertNotIn('reference unavailable',html)
                self.assertNotIn('href=".htm"',html)
                self.assertNotIn('/byC/',html) # Omitted books must not gain broken chapter links.
            self.assertIn(f'{len(alphabetical)} names and alternative spellings',html)


if __name__ == '__main__': unittest.main()
