#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Regression tests for original-numbered sentence annotations.

CHANGELOG:
    2026-10-26 Cover Psalm/proverb authors, speaker changes, editorial halves and LV evidence.
    2026-10-26 Exercise BOS mappings, grouped annotations and safe regeneration.

Run from createPages: uv run ../datasets/sentenceImportance/test_initialise.py -v
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import initalise as initialise
from BibleOrgSys.Formats.USFMBible import USFMBible


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.audit = initialise.MappingAudit()

    def convert(self, text, profile='eng'):
        refs, half = initialise.expand_reference(text,profile)
        return self.audit.convert(profile,refs,'Test',half)

    def test_psalm_body_and_two_verse_title(self):
        self.assertEqual(self.convert('PSA_51:10'),('PSA_51:12',))
        self.assertEqual(self.convert('PSA_51:0'),('PSA_51:1','PSA_51:2'))

    def test_chapter_boundaries(self):
        self.assertEqual(self.convert('DEU_29:29'),('DEU_29:28',))
        self.assertEqual(self.convert('GEN_31:55'),('GEN_32:1',))
        self.assertEqual(self.convert('MAL_4:5'),('MAL_3:23',))

    def test_nt_original_numbering(self):
        self.assertEqual(self.convert('CO2_13:14'),('CO2_13:13',))
        self.assertEqual(self.convert('PHP_1:16','VLT'),('PHP_1:17',))
        self.assertEqual(self.convert('PHP_1:17','OET-RV'),('PHP_1:16',))

    def test_one_to_many_and_many_to_one(self):
        self.assertEqual(self.convert('NUM_26:1'),('NUM_25:19','NUM_26:1'))
        self.assertEqual(self.convert('ACT_19:41'),('ACT_19:40',))
        self.assertIn('ACT_19:40',self.audit.comments)
        self.assertIn('ACT_19:40, ACT_19:41',next(iter(self.audit.comments['ACT_19:40'])))

    def test_editorial_halves_are_not_bos_segments(self):
        self.assertEqual(self.convert('PSA_22:16b'),('PSA_22:17b',))
        with self.assertRaisesRegex(ValueError,'editorial half'):
            self.convert('NUM_26:1a')
        with self.assertRaisesRegex(ValueError,'editorial half'):
            self.convert('ACT_19:41b')

    def test_only_reviewed_absence_may_be_omitted(self):
        with self.assertLogs(level='WARNING'):
            self.assertEqual(self.convert('NEH_7:68'),())
        self.assertEqual(len(self.audit.omitted),1)
        for text, profile in [('PSA_51:99','eng'),('GEN_1:1','unknown'),('PSA_9:22','rsc')]:
            with self.assertRaises(ValueError):
                self.convert(text,profile)

    def test_source_range_counts_and_lists(self):
        refs,half = initialise.expand_reference('GEN_31:54–32:2','eng')
        self.assertEqual([initialise.fgref(r) for r in refs],
                         ['GEN_31:54','GEN_31:55','GEN_32:1','GEN_32:2'])
        refs,half = initialise.expand_reference('PSA_22:1,3-4;23:1-2','eng')
        self.assertEqual([initialise.fgref(r) for r in refs],
                         ['PSA_22:1','PSA_22:3','PSA_22:4','PSA_23:1','PSA_23:2'])

    def test_curated_lists_are_repeatable_and_mapped(self):
        with self.assertLogs(level='WARNING'):
            first = initialise.setup(self.audit)
        with self.assertLogs(level='WARNING'):
            second = initialise.setup()
        self.assertEqual(first,second)
        self.assertEqual(first[0]['PSA_51:12'],'I')
        self.assertEqual(first[0]['CO2_13:13'],'V')
        self.assertEqual(first[0]['NUM_25:19'],'T')
        self.assertIn('PSA_22:17b',first[2])

    def test_seed_reconciles_org_without_changing_book_scope(self):
        refs = initialise.load_original_inventory()
        self.assertEqual(len(refs),41899)
        self.assertEqual(len({r[0] for r in refs}),89)
        self.assertIn(('ESG','4','6',None),refs)
        self.assertNotIn(('ESG','8','40',None),refs)
        self.assertIn(('PSA','51','21',None),refs)
        self.assertNotIn(('CO2','13','14',None),refs)

    def test_quotation_source_conventions(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'quotes.tsv'
            path.write_text('NTRef\tOTRef\tStrength\n'
                            'MAT_27:35\tPSA_22:18\tQuote\n'
                            'JHN_19:24\tPSA_22:19\tQuote\n'
                            'PE1_5:7\tPSA_55:23\tAllusion\n'
                            'ACT_2:17-21\tJOL_2:28-32\tQuote\n')
            values = initialise.load_quoted_OT_annotations(self.audit,path)
        self.assertEqual(values['PSA_22:19'],'V')
        self.assertNotIn('PSA_22:20',values)
        self.assertEqual(values['PSA_55:23'],'I')
        self.assertEqual(values['JOL_3:1'],'V')

    def test_cntr_scores_follow_vlt_philippians_order(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'collation.csv'
            path.write_text('CollationId,VerseId,SR,Translatable\n'
                            '50001016001,50001016,X,\n'
                            '50001016002,50001016,,yes\n'
                            '50001017001,50001017,X,\n')
            values=initialise.load_CNTR_collation_DB(self.audit,path)
        self.assertEqual(values,{'PHP_1:17':'2','PHP_1:16':'0'})

    def test_net_profile_is_selected_per_book(self):
        self.assertEqual(initialise.net_profile('PSA'),'eng')
        self.assertEqual(initialise.net_profile('ACT'),'eng')
        for book in ('CO2','PHP','JN3','REV'):
            self.assertEqual(initialise.net_profile(book),'org')


class SourceAndOutputTests(unittest.TestCase):
    def test_net_omission_requires_its_actual_textual_note(self):
        xml = ('<usx><book code="MAT"/><chapter number="17"/><para>'
               '<verse number="20"/><note>Textual Criticism: Mt 17:21 is omitted.</note>'
               '</para></usx>')
        class MissingVerseBible:
            books = {'MAT':object()}
            def getPassageData(self,*args,**kwargs):
                raise KeyError('omitted')
        with TemporaryDirectory() as folder, patch.dict(initialise.NET_OMISSION_NOTES,
                {('MAT','17','21'):'20'},clear=True):
            path=Path(folder)/'MAT.usx';path.write_text(xml)
            audit=initialise.MappingAudit()
            with initialise.prepared_source('NET',Path(folder),audit):
                scores=initialise.score_bible(MissingVerseBible(),lambda b:'org',lambda *args:0,
                    (('MAT','17','21',None),),audit,'NET')
            self.assertEqual(scores,{'MAT_17:21':'2'})
            self.assertIn('NET omits',next(iter(audit.comments['MAT_17:21'])))
            path.write_text(xml.replace('Textual Criticism','Unrelated note'))
            with self.assertRaisesRegex(ValueError,'without its reviewed TC note'):
                with initialise.prepared_source('NET',Path(folder),initialise.MappingAudit()):
                    pass

    def test_net_missing_marker_repair_does_not_modify_source(self):
        original = ('<usx><book code="JON"/><chapter number="1"/>'
                    '<para>1:17 <char style="va">(2:1)</char> A fish.</para></usx>')
        with TemporaryDirectory() as folder:
            path=Path(folder)/'JON.usx';path.write_text(original)
            audit=initialise.MappingAudit()
            with initialise.prepared_source('NET',Path(folder),audit) as prepared:
                self.assertIn('number="17"',(prepared/'JON.usx').read_text())
                self.assertEqual(path.read_text(),original)
            self.assertEqual(len(audit.source_repairs),1)

    def test_speaker_parser_keeps_titles_and_source_bridges(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'PSA.ESFM'
            path.write_text('\\c 51\n\\d A psalm of David.\n'
                            '\\sp David\n\\v 1a First part.\n\\v 1b Second part.\n'
                            '\\s1 New section\n\\v 2-3 Narration.\n')
            values=initialise.read_speakers(path,'PSA')
        self.assertEqual(values[('PSA','51','0',None)],'@')
        self.assertEqual(values[('PSA','51','1',None)],'David')
        self.assertEqual(values[('PSA','51','2',None)],'David')
        self.assertEqual(values[('PSA','51','3',None)],'David')

    def test_mapped_native_footnotes_cover_the_complete_group(self):
        with TemporaryDirectory() as folder:
            Path(folder,'NUM.usfm').write_text('\\id NUM\n\\c 26\n\\p\n'
                '\\v 1 Census. \\f + \\ft Q differing reading\\f*\n')
            bible=USFMBible(folder,versification='eng')
            bible.loadBooks()
            refs=(('NUM','25','19',None),('NUM','26','1',None))
            audit=initialise.MappingAudit()
            scores=initialise.score_bible(bible,lambda b:'eng',
                initialise.get_UHB_Hebrew_reference_text_critical_footnote_score,refs,audit,'UHB')
        self.assertEqual(scores,{'NUM_25:19':'2','NUM_26:1':'2'})
        self.assertTrue(audit.comments['NUM_25:19'])

    def test_missing_numbered_source_verse_is_fatal(self):
        with TemporaryDirectory() as folder:
            Path(folder,'GEN.usfm').write_text('\\id GEN\n\\c 1\n\\p\n\\v 1 Text.\n')
            bible=USFMBible(folder,versification='eng')
            bible.loadBooks()
            with self.assertRaisesRegex(ValueError,'missing eng GEN_1:2'):
                initialise.score_bible(bible,lambda b:'eng',lambda *args:0,
                    (('GEN','1','2',None),),initialise.MappingAudit(),'Test')

    def test_row_aggregation_applies_whole_verse_annotations_to_halves(self):
        refs=[('PSA','22','17',None),('GEN','1','1',None)]
        curated=({'PSA_22:17':'V','GEN_1:1':'T'},{},{'PSA_22:17b':'O'})
        rows=initialise.build_rows(refs,curated,{'GEN_1:1':'M'},
            {'PSA_22:17':'1'},{},{'PSA_22:17':'2'},{},{'PSA_22:17':'David'},initialise.MappingAudit())
        self.assertEqual(rows[0][:5],('PSA_22:17a','V','2','C','David'))
        self.assertEqual(rows[1][:5],('PSA_22:17b','V','2','O','David'))
        self.assertEqual(rows[2][1],'M')

    def test_out_of_inventory_annotations_are_fatal(self):
        with self.assertRaisesRegex(ValueError,'outside output inventory'):
            initialise.build_rows([('GEN','1','1',None)],({'GEN_1:2':'V'},{},{}),
                                  {},{},{},{},{},{},initialise.MappingAudit())

    def test_validation_failure_preserves_database_and_report(self):
        with TemporaryDirectory() as folder:
            output=Path(folder)/'out.tsv';report=Path(folder)/'report.json'
            output.write_text('previous database');report.write_text('previous report')
            row=('GEN_1:1','V','0','C','@','')
            with self.assertRaisesRegex(ValueError,'duplicate'):
                initialise.write_database([row,row],initialise.MappingAudit(),output,report)
            self.assertEqual(output.read_text(),'previous database')
            self.assertEqual(report.read_text(),'previous report')

    def test_regeneration_is_repeatable_and_retains_original_backup(self):
        with TemporaryDirectory() as folder:
            output=Path(folder)/'out.tsv';report=Path(folder)/'report.json'
            output.write_text('previous database')
            row=('GEN_1:1','V','0','C','@','')
            initialise.write_database([row],initialise.MappingAudit(),output,report)
            first=(output.read_bytes(),report.read_bytes())
            initialise.write_database([row],initialise.MappingAudit(),output,report)
            self.assertEqual(first,(output.read_bytes(),report.read_bytes()))
            self.assertEqual(Path(str(output)+'.bak-before-regeneration').read_text(),'previous database')


class SpeakerTests(unittest.TestCase):
    def read(self,text,book='PSA',**kwargs):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'source.ESFM'
            path.write_text(text)
            return initialise.read_speakers(path,book,**kwargs)

    def test_heading_author_forms_and_names_merely_mentioned(self):
        for text, expected in (
            ('A psalm by David.','David'),("David's song about the death of the son.",'David'),
            ("A prayer of David's.",'David'),("One of David's #songs.",'David'),
            ("A song by Yahweh's servant David after Shaul pursued him.",'David'),
            ("A prayer by God's man Mosheh.",'Mosheh'),
            ("A song by Korah's descendants and a song by Heyman.","Korah's descendants,Heyman"),
            ('A song about David and Jonathan.',None),
            ('Remember David and his suffering.',None),
            ('For the musical director. A song.',None)):
            with self.subTest(text=text):
                self.assertEqual(initialise.psalm_author(text),expected)
        self.assertEqual(initialise.psalm_author('A¦1_song¦1 of¦2÷Dāvid¦2.',literal=True),'David')
        self.assertEqual(initialise.psalm_author('The_song_of the_ascents of÷Dāvid',literal=True),'David')
        self.assertEqual(initialise.psalm_author('A_song of_the_sons_of of÷Qoraḩ a_poem of÷Hēymān',literal=True),
                         "Korah's descendants,Heyman")

    def test_psalm_heading_is_narration_and_author_survives_sections_not_chapters(self):
        values=self.read('\\c 9\n\\d A song by David.\n\\v 1 I give thanks.\n'
                         '\\s1 Another stanza\n\\v 2 I rejoice.\n\\c 10\n\\v 1 Why?\n')
        self.assertEqual(values[('PSA','9','0',None)],'@')
        self.assertEqual(values[('PSA','9','1',None)],'David')
        self.assertEqual(values[('PSA','9','2',None)],'David')
        self.assertEqual(values[('PSA','10','1',None)],'@')

    def test_explicit_speaker_changes_inside_same_verse_keep_all_lines(self):
        values=self.read('\\c 1\n\\sp David\n\\v 1 First speech.\n'
                         '\\sp Jonathan\n\\q1 Second speech.\n\\v 2 Continued speech.\n','SA1')
        self.assertEqual(values[('SA1','1','1',None)],'David,Jonathan')
        self.assertEqual(values[('SA1','1','2',None)],'Jonathan')

    def test_explicit_speaker_overrides_psalm_author_and_titles_never_inherit_it(self):
        values=self.read('\\c 9\n\\sp Yahweh\n\\d A song by David.\n'
                         '\\v 1 My promise.\n\\c 10\n\\v 1 Narration.\n')
        self.assertEqual(values[('PSA','9','0',None)],'@')
        self.assertEqual(values[('PSA','9','1',None)],'Yahweh')
        self.assertEqual(values[('PSA','10','1',None)],'@')

    def test_named_speech_is_retained_with_the_author_default(self):
        self.assertEqual(initialise.get_speakers_from_verse_text('Yahweh said, “Go.”','David'),'David,Yahweh')
        self.assertEqual(initialise.get_speakers_from_verse_text('Yeshua said, “\\wj Go.\\wj*”'),'@,Yeshua')

    def test_proverb_author_crosses_chapters_but_changes_at_reviewed_sections(self):
        values=self.read('\\c 25\n\\v 1 More proverbs from Shelomoh copied by Hizkiyah.\n'
            '\\v 2 Wisdom.\n\\c 26\n\\v 1 More wisdom.\n'
            '\\c 30\n\\v 1 Sayings by Agur.\n\\v 2 I know.\n'
            '\\c 31\n\\v 1 Sayings of Lemuel which his mother taught.\n'
            '\\v 2 My son.\n\\v 10 Who can find a capable wife?\n\\v 11 Her husband.\n','PRO')
        for ref in (('25','1'),('30','1'),('31','1'),('31','10'),('31','11')):
            self.assertEqual(values[('PRO',*ref,None)],'@')
        self.assertEqual(values[('PRO','26','1',None)],'Shelomoh')
        self.assertEqual(values[('PRO','30','2',None)],'Agur')
        self.assertEqual(values[('PRO','31','2',None)],"Lemuel's mother")

    def test_proverb_header_and_body_in_same_verse_are_distinct_runs(self):
        values=self.read('\\c 10\n\\v 1 The proverbs by Shelomoh:\n'
                         '\\q1 A wise son delights his father.\n','PRO',detailed=True)
        self.assertEqual(values[('PRO','10','1',None)],[('@','title'),('Shelomoh','body')])
        with self.assertRaisesRegex(ValueError,'evidence changed'):
            self.read('\\c 10\n\\v 1 Unrelated new text.\n','PRO')

    def test_speaker_halves_create_rows_and_preserve_other_annotations(self):
        rows=initialise.build_rows([('PSA','25','1',None)],({'PSA_25:1':'I'},{},{}),
            {},{},{},{},{},{'PSA_25:1':'@,David','PSA_25:1a':'@','PSA_25:1b':'David'},initialise.MappingAudit())
        self.assertEqual([row[:5] for row in rows],
            [('PSA_25:1a','I','0','C','@'),('PSA_25:1b','I','0','C','David')])

    def test_lv_requires_subject_and_referent_on_speech_verb(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'words.tsv'
            path.write_text('Ref\tRole\tOETGlossWords\tTags\n'
                'JHN_1:1w1\tN\tJohn\tPJohn;R1\n'
                'JHN_1:2w1\tV\t˱he˲ said\tPJohn\n'
                'JHN_1:3w1\tV\t˱he˲ walked\tPJohn;R1\n'
                'JHN_1:4w1\tV\t˱you˲ said\tPJohn;R1\n'
                'JHN_1:5w1\tV\t˱he˲ said\tPJohn;R1\n')
            speakers={f'JHN_1:{v}':'@' for v in range(1,6)}
            initialise.supplement_LV_speakers(speakers,initialise.MappingAudit(),path)
        self.assertEqual(speakers['JHN_1:5'],'@,Yohan')
        self.assertTrue(all(speakers[f'JHN_1:{v}']=='@' for v in range(1,5)))

    def test_lv_numbering_and_preservation_of_rv_and_half_annotations(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'words.tsv'
            path.write_text('Ref\tRole\tOETGlossWords\tTags\n'
                'PHP_1:16w1\tV\t˱he˲ said\tPJohn;R1\n'
                'JHN_1:1w1\tV\t˱he˲ said\tPJohn;R1\n'
                'JHN_1:2w1\tV\t˱he˲ said\tPJohn;R1\n')
            speakers={'PHP_1:17':'@','JHN_1:1':'Yeshua','JHN_1:2':'@','JHN_1:2a':'@','JHN_1:2b':'David'}
            initialise.supplement_LV_speakers(speakers,initialise.MappingAudit(),path)
        self.assertEqual(speakers['PHP_1:17'],'@,Yohan')
        self.assertNotIn('PHP_1:16',speakers)
        self.assertEqual(speakers['JHN_1:1'],'Yeshua')
        self.assertEqual(speakers['JHN_1:2'],'@')
        self.assertEqual(speakers['JHN_1:2b'],'David')


class ActualSpeakerSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=initialise.MappingAudit()
        cls.speakers=initialise.load_OET_RV_speakers(cls.audit,existing_splits={'PRO_10:1'})

    def test_psalm_nine_and_two_verse_psalm_fifty_one_title(self):
        self.assertEqual(self.speakers['PSA_9:1'],'@')
        for verse in range(2,22):
            self.assertEqual(self.speakers[f'PSA_9:{verse}'],'David')
        self.assertEqual(self.speakers['PSA_51:1'],'@')
        self.assertEqual(self.speakers['PSA_51:2'],'@')
        self.assertEqual(self.speakers['PSA_51:3'],'David')

    def test_mixed_hebrew_title_gets_halves_but_existing_curated_halves_win(self):
        self.assertEqual(self.speakers['PSA_25:1a'],'@')
        self.assertEqual(self.speakers['PSA_25:1b'],'David')
        self.assertNotIn('PRO_10:1a',self.speakers)
        self.assertEqual(self.speakers['PRO_10:1'],'@,Shelomoh')
        self.assertIn('PRO_10:1',self.audit.speaker_unsplit)

    def test_three_turns_are_preserved_as_a_list(self):
        self.assertEqual(self.speakers['SNG_1:4'],"The bride,Yerushalem's young women,The bride")
        self.assertNotIn('SNG_1:4a',self.speakers)

    def test_actual_proverb_section_boundaries(self):
        for key,expected in {'PRO_22:16':'Shelomoh','PRO_22:17':'The wise',
            'PRO_24:23a':'@','PRO_24:23b':'The wise','PRO_25:1':'@','PRO_25:2':'Shelomoh',
            'PRO_30:1':'@','PRO_30:2':'Agur','PRO_31:1':'@',
            'PRO_31:2':"Lemuel's mother",'PRO_31:9':"Lemuel's mother",'PRO_31:10':'@'}.items():
            with self.subTest(key=key):
                self.assertEqual(self.speakers[key],expected)


if __name__ == '__main__':
    unittest.main()
