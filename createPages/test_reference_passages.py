#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Reference previews use real BOS mappings and preserve complete selections.

CHANGELOG:
    2026-10-30 Cover ranges, alternate numbering, omitted books and unique IDs.
    2026-10-31 Preserve native verse suffixes in excerpt context links.
    2026-10-31 Check OET-first controls while preserving native reference labels.
    2026-11-01 Check general generated links use the same RV and bridge destinations.
    2026-11-02 Expect hyphenated edition labels and a nonbreaking gap after OET.
    2026-11-02 Cover single reading links, preview order and mapped section destinations.
"""
import re
import unittest
from unittest.mock import patch

import BibleOrgSys.Reference.BibleVersification as bv
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine
import referencePassages
from navigation import mapHtmlLinks
from referencePassages import parseReferenceSelection, renderReferencePassage, referenceCitationLink
import test_oet_passages as passageFixtures


class ReferencePassageTests(unittest.TestCase):
    setUp = passageFixtures.OETPassageTests.setUp
    load = passageFixtures.OETPassageTests.load
    render = passageFixtures.OETPassageTests.render

    def prepare(self, BBB='MAL'):
        rv = self.load(BBB,'OET-RV','\\c 4\n\\p\n\\v 1 RV one.\n\\v 2 RV two.\n')
        lv = self.load(BBB,'OET-LV','\\c 3\n\\nb\n\\v 19 LV nineteen.\n\\v 20 LV twenty.\n')
        self.state.preloadedBibles = {'OET-RV':rv,'OET-LV':lv}
        self.state.OETRefData = {'word_tables':{'OET-LV_OT_word_table.tsv':[]}}
        self.state.booksToLoad = {version:[BBB] for version in ('OET','OET-RV','OET-LV')}
        # These minimal fixtures explicitly declare English and original numbering.
        self.state.BibleVersifications = {'OET':'eng','OET-RV':'eng','OET-LV':'org'}

    def test_verse_zero_heading_context_uses_existing_chapter_top(self):
        self.prepare('PSA')
        href=referencePassages.passageContextHref(2,('PSA','3','0'),'OET-RV',self.state)
        self.assertEqual(href,'../../OET-RV/byC/PSA_C3.htm#Top')

    def test_suffix_labels_from_stored_portions_keep_their_exact_anchor(self):
        lv=self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1a First segment.\n\\v 1b Second segment.\n')
        self.state.preloadedBibles={'OET-LV':lv}
        self.state.booksToLoad={'OET-LV':['GEN']}
        for reference in (('GEN','1','1a'),('GEN','1','1','a')):
            self.assertEqual(referencePassages.passageContextHref(2,reference,'OET-LV',self.state),
                             '../../OET-LV/byC/GEN_C1.htm#C1V1a')

    def test_jump_outside_excerpt_leads_to_version_context(self):
        self.prepare()
        html=referencePassages._externaliseExcerptJumps('<a title="later" href="#C4V2">later</a> <a href="#named_fn1">note</a>',2,'MAL','OET-RV',self.state)
        self.assertIn('href="../../OET-RV/byC/MAL_C4.htm#C4V2"',html)
        self.assertIn('href="#named_fn1"',html)
        self.assertEqual(mapHtmlLinks(html,'OET-LV',2,self.state,segmentType='reference'),html)
        html=referencePassages._externaliseExcerptJumps('<a href="#C99V9">missing</a>',2,'MAL','OET-RV',self.state)
        self.assertEqual(html,'missing')

    def test_same_component_accepts_grammar_person_and_native_lexical_references(self):
        self.prepare()
        for instance,system,selection in (('grammar','eng','4:1-2'),('person','eng','4:1-2'),('word','org','3:19-20')):
            html = renderReferencePassage(2,parseReferenceSelection('MAL',selection,system),system,
                                           self.state,instanceId=instance)
            self.assertIn('RV one.',html)
            self.assertIn('LV nineteen.',html)
            self.assertIn('LV twenty.',html)
            self.assertIn('OET-RV/byC/MAL_C4.htm#C4V1',html)
            self.assertIn('OET-LV/byC/MAL_C3.htm#C3V19',html)
            self.assertNotIn('OET-LV/byC/MAL_C4.htm',html)
            controls=html.split('</details>',1)[1]
            self.assertIn('>OET MAL 4:1–2 chapter.</a>',controls)
            self.assertEqual(controls.count('<a '),1)
            self.assertIn('<details><summary>Show passage in OET:',html)

    def test_repeated_excerpts_namespace_notes_and_return_links(self):
        self.prepare()
        references = parseReferenceSelection('MAL','4:1','eng')
        html = ''.join(renderReferencePassage(2,references,'eng',self.state,instanceId=f'example{n}') for n in range(2))
        ids = re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))
        for target in re.findall(r'href="#([^"]+)"',html): self.assertIn(target,ids)

    def test_disjoint_selection_and_cross_chapter_range_keep_all_addresses(self):
        self.assertEqual(parseReferenceSelection('GEN','31:54-32:2,5;33:1','eng'), (
            ('GEN','31','54',None),('GEN','31','55',None),('GEN','32','1',None),
            ('GEN','32','2',None),('GEN','32','5',None),('GEN','33','1',None)))
        self.assertEqual(len(parseReferenceSelection('MAL','4','eng')),6)

    def test_unbuilt_books_have_no_dead_destinations(self):
        self.prepare()
        self.state.booksToLoad = {version:['MRK'] for version in ('OET','OET-RV','OET-LV')}
        html = renderReferencePassage(2,parseReferenceSelection('MAL','4:1','eng'),'eng',self.state,instanceId='missing')
        self.assertNotIn('href=',html)
        self.assertIn('unavailable in this build',html)

    def test_long_selection_keeps_range_link_without_rendering_truncated_text(self):
        self.prepare()
        html = renderReferencePassage(2,parseReferenceSelection('MAL','4','eng'),'eng',self.state,
                                      instanceId='chapter',maxPreviewVerses=2)
        self.assertIn('OET MAL 4:1–6 chapter.',html)
        self.assertEqual(html.count('<a '),1)
        self.assertNotIn('<details>',html)
        self.assertEqual(self.rendered,[])

    def test_complete_mapping_group_is_labelled_and_never_split(self):
        self.prepare()
        self.state.preloadedBibles = {
            'OET-RV':self.load('GEN','OET-RV','\\c 1\n\\p\n\\v 1 First.\n\\v 2 Second.\n'),
            'OET-LV':self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1 Combined.\n')}
        self.state.booksToLoad = {version:['GEN'] for version in self.state.BibleVersifications}
        engine = VersificationMappingEngine({'maxVerses':{'GEN':[1]}}, {
            'eng':{'maxVerses':{'GEN':[2]},'groupMappings':[{'source':'GEN 1:1-2','target':'GEN 1:1'}]},
            'org':{'maxVerses':{'GEN':[1]},'identityBooks':{'GEN':'GEN'}}})
        with patch.object(bv,'get_default_mapping_engine',return_value=engine), \
             patch.object(referencePassages,'get_default_mapping_engine',return_value=engine):
            html = renderReferencePassage(2,(('GEN','1','1',None),),'eng',self.state,instanceId='merged')
        self.assertIn('Combined.',html)
        self.assertIn('Combined passage: English GEN 1:1–2',html)

    def test_real_html_renderer_keeps_balanced_preview_markup(self):
        self.prepare()
        self.mocks.stop()
        from html import checkHtml
        html = renderReferencePassage(2,parseReferenceSelection('MAL','4:1-2','eng'),'eng',self.state,instanceId='real')
        self.assertIn('LV nineteen.',html)
        self.assertTrue(checkHtml('reference preview',html,segmentOnly=True))

    def test_stored_verse_bridge_links_to_first_real_chapter_anchor(self):
        self.prepare()
        self.state.preloadedBibles = {
            'OET-RV':self.load('GEN','OET-RV','\\c 1\n\\p\n\\v 1-2 RV bridge.\n'),
            'OET-LV':self.load('GEN','OET-LV','\\c 1\n\\nb\n\\v 1 First.\n\\v 2 Second.\n')}
        self.state.booksToLoad = {version:['GEN'] for version in self.state.BibleVersifications}
        html = renderReferencePassage(2,(('GEN','1','1',None),),'eng',self.state,instanceId='bridge')
        self.assertIn('OET-RV GEN 1:1-2</a>',html)
        self.assertIn('OET-RV/byC/GEN_C1.htm#C1V1"',html)
        self.assertNotIn('byC/GEN_C1.htm#C1V1-2',html)
        interior = renderReferencePassage(2,(('GEN','1','2',None),),'eng',self.state,instanceId='interior')
        self.assertIn('OET-RV/byC/GEN_C1.htm#C1V1"',interior)
        self.assertNotIn('OET-RV/byC/GEN_C1.htm#C1V2"',interior)
        self.assertIn('OET/byC/GEN_C1.htm#C1V1"',interior)
        general = mapHtmlLinks('<a href="../../OET/byC/GEN_C1.htm#C1V2">second verse</a>',
                               'OET-LV', 2, self.state)
        self.assertIn('OET/byC/GEN_C1.htm#C1V1"', general)
        self.assertNotIn('#C1V2', general)

    def test_read_together_uses_actual_rv_anchors_when_numbering_differs(self):
        self.prepare()
        rv = self.load('CO2','OET-RV','\\c 13\n\\p\n\\v 13 Blessing.\n')
        rv.setVersificationSystem('OET-RV')
        self.state.preloadedBibles['OET-RV'] = rv
        self.state.BibleVersifications['OET-RV'] = 'OET-RV'
        self.state.booksToLoad['OET'] = ['CO2']
        html = referenceCitationLink(2,('CO2','13','14'),'eng','OET','2 Corinthians 13:14',self.state)
        self.assertIn('OET/byC/CO2_C13.htm#C13V13',html)
        self.assertNotIn('#C13V14',html)
        general = mapHtmlLinks('<a href="../../OET/byC/CO2_C13.htm#C13V14">blessing</a>',
                               'OET', 2, self.state)
        self.assertIn('OET/byC/CO2_C13.htm#C13V13', general)
        self.assertNotIn('#C13V14', general)

    def test_sections_use_mapped_rv_numbering_and_preserve_explicit_chapter_navigation(self):
        self.prepare()
        self.mocks.stop()
        self.state.sectionsListsForSections={'OET-RV':{'MAL':[
            (0,'4','1','4','6','Final promise','s1',[],[],'MAL_S0.htm')]}}
        for native,anchor in (('19','Top'),('20','C4V2')):
            html=renderReferencePassage(2,(('MAL','3',native,None),),'org',self.state,instanceId=f'mapped{native}')
            jump=html.split('</details>',1)[1]
            self.assertIn(f'OET/bySec/MAL_S0.htm#{anchor}',jump)
            self.assertIn(f'OET MAL 4:{int(native)-18} section.',jump)
            original=f'<a href="../../OET/byC/MAL_C3.htm#C3V{native}">passage</a>'
            self.assertIn(f'OET/bySec/MAL_S0.htm#{anchor}',
                          mapHtmlLinks(original,'OET-LV',2,self.state,segmentType='reference'))
            self.assertIn(f'OET/byC/MAL_C4.htm#C4V{int(native)-18}',
                          mapHtmlLinks(original,'OET-LV',2,self.state))
            # Already resolved preview links must not be mapped a second time.
            self.assertEqual(mapHtmlLinks(html,'OET-LV',2,self.state,segmentType='reference'),html)

    def test_group_keeps_all_previews_before_all_jumps(self):
        self.prepare()
        from referenceEntities import selectedPassageControls
        html=selectedPassageControls(['MAL_4:1','MAL_4:2'],2,self.state,'person')
        self.assertEqual(html.count('<details>'),2)
        self.assertLess(html.rindex('</details>'),html.index('Jump to '))
        self.assertEqual(html[html.rindex('</details>'):].count('<a '),2)
        for verse in (1,2):self.assertIn(f'Show passage in OET: MAL 4:{verse}',html)

    def test_single_available_edition_remains_accessible(self):
        self.prepare()
        self.state.booksToLoad['OET']=self.state.booksToLoad['OET-RV']=[]
        html=renderReferencePassage(2,(('MAL','3','19',None),),'org',self.state,instanceId='lvOnly')
        jump=html.split('</details>',1)[1]
        self.assertIn('OET-LV MAL 3:19 chapter.',jump)
        self.assertEqual(jump.count('<a '),1)


if __name__ == '__main__':
    unittest.main()
