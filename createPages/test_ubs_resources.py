#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check the UBS handbooks, HOTTP notes, MARBLE index, and parallel passages handling.

CHANGELOG:
    2026-11-19 First version
    2026-11-19 Check that handbook images are placed together at the top of the article.
    2026-11-19 Check the bulleted handbook list for the Reference contents page.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import ubsHOTTP
import ubsResources
from ubsHandbooks import HandbookImage
from lexicalLinks import _ubsMarbleByWordRef


def marbleWord(word, segment, senses=(), thematic=()):
    return ubsResources.MARBLEWord(word, segment, list(senses), [], list(thematic), [], [], [])


class UBSReferenceTests(unittest.TestCase):
    def test_word_references_including_deuterocanonical_books(self):
        self.assertEqual(ubsHOTTP.parseUBSWordReference('00100201900010'), ('GEN','2','19',10))
        self.assertEqual(ubsHOTTP.parseUBSWordReference('H00100402101000'), ('GEN','4','21',1000))
        self.assertEqual(ubsHOTTP.parseUBSWordReference('06600100100002'), ('REV','1','1',2))
        self.assertEqual(ubsHOTTP.parseUBSWordReference('06900100100008')[0], 'ESG') # USFM 70
        self.assertEqual(ubsHOTTP.parseUBSWordReference('07700100100002')[0], 'MA1') # USFM 78
        self.assertIsNone(ubsHOTTP.parseUBSWordReference('‘alah'))

    def test_parallel_references(self):
        self.assertEqual(ubsResources.parseParallelReference('MRK 10:7-8'), ('MRK',[('MRK','10','7'),('MRK','10','8')]))
        self.assertEqual(ubsResources.parseParallelReference('ACT 2:17,19')[1], [('ACT','2','17'),('ACT','2','19')])
        self.assertEqual(ubsResources.parseParallelReference('1SA 16:1')[0], 'SA1')
        self.assertIsNone(ubsResources.parseParallelReference('Nonsense'))

    def test_holam_waw_normalisation(self):
        self.assertEqual(ubsResources.normaliseHebrewLemma('יֹום'), 'יוֹם')
        self.assertEqual(ubsResources.normaliseHebrewLemma('גֹּוי'), 'גּוֹי')
        self.assertEqual(ubsResources.normaliseHebrewLemma('מִצְוָה'), 'מִצְוָה') # Waw with its own vowel is unchanged


class MARBLETests(unittest.TestCase):
    def test_sense_codes_use_lexid_digits_not_list_positions(self):
        dictionary = [dict(MainId='000396000000000', Lemma='אוֹת', BaseForms=[dict(LEXMeanings=[
                        dict(LEXID='000396001001000'), dict(LEXID='000396001003000'), dict(LEXID='000396001002000')])])]
        with TemporaryDirectory() as directory:
            Path(directory, 'MARBLELinks-GEN.json').write_text(json.dumps([
                dict(ID='o010010010012', LexicalLinks=['SDBH:אֹות:000001:Signs'], TextualLinks=['HOTTP12']),
                dict(ID='o010010020011 o010010020021', LexicalLinks=['SDBH:אוֹת:000002:Signs'])]), encoding='utf-8')
            index = ubsResources.loadMARBLEIndex(directory, dictionary)
        word = index[('GEN','1','1')][0]
        self.assertEqual((word.word, word.segment), (1, 2))
        self.assertEqual(word.senses, [('000396000000000','000396001002000')]) # Second meaning (by its digits), via holam-waw normalisation
        self.assertEqual(word.textual, ['00012'])
        self.assertEqual([w.word for w in index[('GEN','1','2')]], [1, 2]) # Multi-word phrase IDs
        self.assertEqual(index[('GEN','1','2')][0].senses, [('000396000000000','000396001003000')])

    def test_ketiv_qere_offset(self):
        table = ['Ref\tRowType\tRest', 'XXX_1:1w1\t\tx', 'XXX_1:1w2\tK\tx', 'XXX_1:1\tseg\tx', 'XXX_1:1w3\t\tx']
        state = SimpleNamespace(OETRefData={'word_tables':{'OET-LV_OT_word_table.tsv':table},
                                            'word_table_indexes':{'OET-LV_OT_word_table.tsv':{'XXX_1:1':(1,4)}}},
                                UBS_MARBLE_INDEX={('XXX','1','1'):[marbleWord(1,1,[('m1','l1')]), marbleWord(3,1,[('m3','l3')]),
                                                                    marbleWord(4,2,[('m4','l4')])]})
        result = _ubsMarbleByWordRef(state)
        self.assertEqual(result['XXX_1:1w1']['senses'], [(0,'m1','l1')])
        self.assertEqual(result['XXX_1:1w2']['senses'], [(0,'m3','l3')]) # MACULA word 3 is the qere of our ketiv w2
        self.assertEqual(result['XXX_1:1w3']['senses'], [(1,'m4','l4')]) # MACULA word 4 is our w3 (second segment)


class HOTTPTests(unittest.TestCase):
    def entry(self):
        return ubsHOTTP.HOTTPEntry('00010', ['03900302400010'], 'Read <span class="hebrew">עוד</span> & see.', 'See Remark',
                    [ubsHOTTP.HOTTPAlternative('[-]', '', [], ['14'], ''),
                     ubsHOTTP.HOTTPAlternative('מן־האדמה', 'B', [ubsHOTTP.HOTTPVersion('RSV','out of the ground')], [], 'out of the ground')])

    def test_entry_html(self):
        html = ubsHOTTP.formatHOTTPEntry(self.entry(), {'14':'Conjectural form of the text'})
        self.assertLess(html.index('מן־האדמה'), html.index('[-]')) # Rated reading first
        self.assertIn('<span class="HOTTPrating" title="This form of the text probably', html)
        self.assertIn('<span class="hebrew">עוד</span> &amp; see.', html) # Keeps the source's Hebrew span but escapes the rest
        self.assertIn('title="Conjectural form of the text">14</span>', html)
        self.assertNotIn('See Remark', html)

    def test_notes_use_original_numbering(self):
        state = SimpleNamespace(navigationVersification='eng', UBS_HOTTP_ENTRIES={'00010':self.entry()},
                                UBS_HOTTP_VERSE_INDEX={('MAL','3','24'):['00010']}, UBS_HOTTP_FACTORS={})
        self.assertTrue(ubsHOTTP.formatHOTTPNotes(2, 'MAL', '4', '6', state)) # English MAL 4:6 = Hebrew 3:24
        self.assertFalse(ubsHOTTP.formatHOTTPNotes(2, 'MAL', '3', '18', state))
        self.assertEqual(ubsHOTTP.formatHOTTPNotes(2, 'MAL', '4', '6', SimpleNamespace(navigationVersification='eng')), '')


class HandbookAndParallelTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(navigationVersification='eng', TEST_MODE_FLAG=False, TEST_BOOK_LIST=[],
                    UBS_HANDBOOKS={'Flora':{'2.1':SimpleNamespace(title='Almond', referenceCodes=lambda: ['00102402400002'])}}, UBS_HEB_LEMMA_INDEX={}, UBS_GNT_LEMMA_INDEX={},
                    UBS_PARALLEL_GROUPS=[[ubsResources.ParallelVerse('GEN','GEN 2:24',[('GEN','2','24')],'HEB','222'),
                                          ubsResources.ParallelVerse('MAT','MAT 19:5',[('MAT','19','5')],'GRK','222')],
                                         [ubsResources.ParallelVerse('MAT','MAT 19:5',[('MAT','19','5')],'GRK','2'),
                                          ubsResources.ParallelVerse('MRK','MRK 10:7-8',[('MRK','10','7'),('MRK','10','8')],'GRK','2')]])

    def test_handbook_paragraph_markup(self):
        from ubsHandbookPages import HandbookRenderer
        renderer = HandbookRenderer(2, 'Flora', self.state(), {'almond.jpg'})
        html = renderer.paragraph('<Image Id="A" />In <s>00103003700018</s> see <l target="FLORA:2.1">Almond</l> (<a>FFB</a>).',
                                  {'A':HandbookImage('A','WEB','almond.jpg','© Someone','Almond nut')})
        self.assertTrue(html.startswith('<p class="hbPara">In ')) # The image is collected for the top of the article
        self.assertTrue(renderer.articleFigures[0].startswith('<div class="hbImage"><img src="../img/almond.jpg"'))
        self.assertIn('(© Someone)', renderer.articleFigures[0])
        self.assertIn('href="../../par/GEN/C30V37.htm#Top">GEN 30:37</a>', html)
        self.assertIn('<a href="../Flora/2.1.htm#Top">Almond</a>', html)
        self.assertIn('<cite>FFB</cite>', html)
        self.assertEqual(renderer.paragraph('<Image Id="B" />', {'B':HandbookImage('B','OPEN-AI','missing.jpg','','')}), '') # Not available
        self.assertEqual(renderer.articleFigures[-1], '')

    def test_handbook_article_images_at_top(self):
        from ubsHandbookPages import HandbookRenderer
        from ubsHandbooks import HandbookEntry, HandbookSection
        renderer = HandbookRenderer(2, 'Flora', self.state(), {'almond.jpg', 'tree.jpg'})
        entry = HandbookEntry('Flora', '2.1', 'Almond', [], [
            HandbookSection('discussion', 'Discussion', '', [], ['First.', 'Second <Image Id="A" />here.'],
                            {'A':HandbookImage('A','WEB','almond.jpg','',''), 'B':HandbookImage('B','WEB','tree.jpg','','Tree')})])
        html = renderer.article(entry)
        self.assertTrue(html.startswith('<div class="hbArticle"><div class="hbImages"><div class="hbImage"><img src="../img/almond.jpg"'))
        self.assertLess(html.index('tree.jpg'), html.index('<h3>')) # Unplaced images also go at the top
        self.assertTrue(html.endswith('</div><!--hbArticle-->'))
        self.assertEqual(renderer.article(HandbookEntry('Flora', '9', 'Empty', [])), '')

    def test_handbooks_index_is_a_bulleted_list(self):
        from ubsHandbookPages import ubsHandbooksIndexHtml
        html = ubsHandbooksIndexHtml(1, self.state())
        self.assertIn('<ul><li><a href="../UBS/Flora/index.htm#Top">Plants and Trees in the Bible</a></li></ul>', html)
        self.assertEqual(ubsHandbooksIndexHtml(1, SimpleNamespace(UBS_HANDBOOKS={})), '')

    def test_parallels_and_quotations(self):
        from ubsStudyLinks import ubsPassageResources, ubsSectionParallelsHtml
        state = self.state()
        html = ubsPassageResources(2, [('MAT','19','5')], state)
        self.assertIn('UBS parallel passages: <a', html)
        self.assertIn('>MARK 10:7–8</a>', html) # OET book abbreviation
        self.assertIn('Quotes from the Old Testament (UBS): <a', html)
        self.assertIn('par/GEN/C2V24.htm', html)
        self.assertNotIn('MARK', html.split('Quotes from the Old Testament')[1]) # NT verses are parallels, not quotations
        sectionHtml = ubsSectionParallelsHtml(2, 'GEN', '2', '18', '2', '25', state)
        self.assertIn('Quoted in the New Testament: <a', sectionHtml)
        self.assertEqual(ubsSectionParallelsHtml(2, 'GEN', '3', '1', '3', '24', state), '')


if __name__ == '__main__':
    unittest.main()
