#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests of shared version-specific HTML processing.

CHANGELOG:
    2026-10-23 Cover combined OET titles and preservation of LV URLs/notes
"""
#
# test_html_customisations.py
#
# Tests for the html.py customisation functions.
#
# The functions delegate to Rust. Historical fixtures retain the original
# formatting, with deliberate updates for sentence breaks and OET research titles.

import unittest

from openbibledata_rust import setStrictCheckingFlag
from html import (
    do_OET_RV_HTMLcustomisations,
    do_OET_LV_HTMLcustomisations,
    do_LSV_HTMLcustomisations,
    do_T4T_HTMLcustomisations,
    convert_adds_to_italics,
    handleAndExtractFootnotes,
)


class StrictCheckMixin:
    """Helpers to toggle the Rust extension's strict-checking static."""

    def setUp(self):
        setStrictCheckingFlag(False)

    def tearDown(self):
        setStrictCheckingFlag(False)


class TestOETLVVerseChunkClosingSpanPlacement(unittest.TestCase):
    """Test that a sentence-ending <br> does not end up inside a verse-text
    chunk's closing </span> (which would put the tag after the <br>, partly on
    the next line). Instead the <br> should come after the closing span."""

    def test_verse_end_closing_span_before_br(self):
        """A verse-text chunk ending in a period must close its span before
        the sentence-break <br>, not after it."""
        snippet = (
            '<span id="V1"></span><span class="v" id="C2V1"><a href="x.htm">1</a></span>'
            '<span class="OET-LV_verseTextChunk">And they came.</span> '
            '<span id="V2"></span><span class="v" id="C2V2"><a href="x.htm">2</a></span>'
            '<span class="OET-LV_verseTextChunk">being carried by four.</span>'
        )
        out = do_OET_LV_HTMLcustomisations('test', snippet)
        NEWLINE = '\n'
        # The bug put the closing span after the <br>:  ".\n<br></span>"
        self.assertNotIn(f'<br>{NEWLINE}</span>', out)
        self.assertNotIn(f'{NEWLINE}<br></span>', out)
        # The closing </span> should now sit before the <br>.
        self.assertIn(f'</span>{NEWLINE}<br>', out)
        # And the <br> must not be immediately followed by a newline (checkHtml
        # rejects "<br>\n").
        self.assertNotIn(f'<br>{NEWLINE}', out)

    def test_last_verse_before_footnote_break(self):
        """When the last verse-text chunk is right before the footnote <hr>
        (which begins on its own line), the reordered <br> must not be left
        immediately before a newline -- checkHtml forbids "<br>\n"."""
        snippet = (
            '<span class="OET-LV_verseTextChunk">He made vows.</span>'
            f'\n<hr class="line-before-footnotes"><div id="footnotes">'
        )
        out = do_OET_LV_HTMLcustomisations('test', snippet)
        NEWLINE = '\n'
        self.assertNotIn(f'<br>{NEWLINE}', out)
        # The redundant <br> is dropped; the chunk closes and the <hr> follows.
        self.assertIn('</span>' + NEWLINE, out)
        self.assertIn('<hr class="line-before-footnotes">', out)


class TestOETLVVerseTextDivBrPlacement(unittest.TestCase):
    """Paragraph-less verse flows (OET-LV, BLB, ...) are wrapped by the Rust
    converter in per-verse <div class="verseText"> blocks.  A sentence-ending
    <br> must not be left before that block's closing </div>; it should move
    after it so the block closes cleanly and the <br> breaks the line."""

    def test_verse_end_br_should_follow_closing_div(self):
        snippet = (
            '<div class="verseText">\n'
            '<span id="V2"></span><span class="v" id="C2V2"><a href="x.htm">2</a></span>'
            '<span class="OET-LV_verseTextChunk">being carried by four.</span>'
            '</div><!--verseText-->\n'
        )
        out = do_OET_LV_HTMLcustomisations('test', snippet)
        NEWLINE = '\n'
        # The whole closing block (plus its comment) must stay contiguous and not
        # be split by a sentence-break <br>.
        self.assertIn('</div><!--verseText-->', out)
        # No <br> left before the closing block.
        self.assertNotIn(f'<br>{NEWLINE}</div><!--verseText-->', out)
        # The <div> blocks remain balanced.
        self.assertEqual(out.count('<div class="verseText">'), out.count("</div><!--verseText-->"))


class TestOETRVHTMLcustomisations(unittest.TestCase):
    """OET-RV '/add' subfield markers and poetry parallelism symbols."""

    def test_plain_add(self):
        self.assertEqual(
            do_OET_RV_HTMLcustomisations('test', '<span class="add">word</span>'),
            '<span class="RVadd" title="added info">word</span>')

    def test_unsure_add(self):
        self.assertEqual(
            do_OET_RV_HTMLcustomisations('test', '<span class="add">?<a title="x">w</a></span>'),
            '<span class="RVadd unsure" title="added info (less certain)"><a title="x">w</a></span>')

    def test_direct_object(self):
        self.assertEqual(
            do_OET_RV_HTMLcustomisations('test', '<span class="add"><strong>x</strong></span>'),
            '<span class="addDirectObject" title="added direct object">strong>x</strong></span>')

    def test_symbol_chain(self):
        input_html = ('<span class="add">?><span class="add">><span class="add">?+'
                      '<span class="add">+</span></span></span></span>')
        expected = ('<span class="addExtra unsure" title="added implied info (less certain)">'
                    '<span class="addExtra" title="added implied info (less certain); added implied info">'
                    '<span class="addArticle unsure" title="added implied info (less certain); added implied info; added article (less certain)">'
                    '<span class="addArticle" title="added implied info (less certain); added implied info; added article (less certain); added article"></span></span></span></span>')
        self.assertEqual(do_OET_RV_HTMLcustomisations('test', input_html), expected)

    def test_parallelism_markers(self):
        out = do_OET_RV_HTMLcustomisations('test', '≈ and ^ and →')
        nnbs = '\u202f'
        self.assertIn(f'<span class="synonParr" title="synonymous parallelism">≈{nnbs}</span>', out)
        self.assertIn(f'<span class="antiParr" title="antithetic parallelism">^{nnbs}</span>', out)
        self.assertIn(f'<span class="synthParr" title="synthetic parallelism">→{nnbs}</span>', out)

    def test_preexisting_rvadd_receives_description(self):
        self.assertEqual(
            do_OET_RV_HTMLcustomisations('test', '<span class="RVadd"><span class="wj">w</span></span>'),
            '<span class="RVadd" title="added info"><span class="wj">w</span></span>')


class TestOETLVHTMLcustomisations(unittest.TestCase):
    """OET-LV sentence-per-line breaking with field protection."""

    def test_digit_punct_digit_preserved(self):
        self.assertEqual(do_OET_LV_HTMLcustomisations('test', '12:30 and JOB_1:2 and v0.1'),
                         '12:30 and JOB<span class="ul">_</span>1:2 and v0.1')

    def test_paths_and_backslash_f_preserved(self):
        self.assertEqual(
            do_OET_LV_HTMLcustomisations('test', r'../x.htm and ../../y.org/index.html and data.tsv and z.\f*'),
            r'../x.htm and ../../y.org/index.html and data.tsv and z.\f*')

    def test_add_markers(self):
        input_html = ('<span class="add">+art</span><span class="add">=cop</span>'
                      '<span class="add"><a title="x">deep</a></span><span class="add"><x></span>'
                      '<span class="add">>extra</span><span class="add">&own</span>')
        expected = ('<span class="addArticle" title="added article">art</span><span class="addCopula" title="added copula">cop</span>'
                    '<span class="add" title="added info"><a title="x">deep</a></span>'
                    '<span class="addDirectObject" title="added direct object">x></span>'
                    '<span class="addExtra" title="added implied info">extra</span><span class="addOwner" title="added ‘owner’">own</span>')
        self.assertEqual(do_OET_LV_HTMLcustomisations('test', input_html), expected)


class TestOETResearchMarkup(StrictCheckMixin, unittest.TestCase):
    """Exercise the public shared functions used by all OET page families."""

    def test_jeremiah_rv_rewording_and_source_word_share_title(self):
        source = ('<span class="add">≈is able to '
                  '<a title="יַעֲמֹד (yaˊₐmod, Vqi3ms)" '
                  'href="../../ref/HebWrd/JERc50v44w26.htm#Top" class="hebVrb">resist</a></span>')
        result = do_OET_RV_HTMLcustomisations('ParallelVerseTxt=JER_50:44', source)
        self.assertEqual(result,
            '<span class="addReword" title="reworded">is able to '
            '<a title="reworded; יַעֲמֹד (yaˊₐmod, Vqi3ms)" '
            'href="../../ref/HebWrd/JERc50v44w26.htm#Top" class="hebVrb">resist</a></span>')

    def test_lv_linked_and_unlinked_additions_receive_titles(self):
        source = ('<span class="add">+the</span> '
                  '<span class="add"><a title="אֵיתָן (ʼēytān, Aamsa)" '
                  'href="../../ref/HebWrd/JERc50v44w8.htm#Top">stream</a></span>')
        result = do_OET_LV_HTMLcustomisations('Chapter=JER_50', source)
        self.assertIn('<span class="addArticle" title="added article">the</span>', result)
        self.assertIn('<span class="add" title="added info"><a title="added info; אֵיתָן (ʼēytān, Aamsa)"', result)

    def test_lv_jeremiah_footnote_metadata_and_backlink_remain_intact(self):
        note = ('<div id="footnotesOET-LV" class="footnotes">'
                '<p class="fn" id="fnOET-LV1"><span class="fnRef">'
                '<a title="Return to text" data-vref="mapped" '
                'href="../../OET/byC/JER_C50.htm#C50V44">50:44</a></span> '
                '<span class="fnText"><span class="ft">OSHB variant note: ארוצ/ם: '
                '(x-qere) ’אֲרִיצֵ/ם֙’: lemma=7323 n=1.1.0 morph=HVhi1cs/Sp3mp '
                'id=24eYS source_name=a_b. What?! <i>More: metadata.</i></span></span>'
                '</p><!--fn--></div><!--footnotes-->')
        self.assertEqual(do_OET_LV_HTMLcustomisations('ParallelVerseFN=JER_50:44', note), note)
        result = do_OET_LV_HTMLcustomisations('Book=JER', 'word_word.\n' + note + ' next=word.')
        self.assertIn(note, result)
        self.assertIn('word<span class="ul">_</span>word.', result)
        self.assertIn('next<span class="ul">_</span>word.', result)

    def test_lv_attributes_and_comments_survive_text_formatting(self):
        start = ('<!-- Leave a_b=c.?! intact -->'
                 '<span id="part_a" class="OET-LV_verseTextChunk">'
                 '<a title="word: a_b=c.?! &quot;quoted&quot; &gt;" '
                 'data-value="a_b=c" href="../../OET/byC/JER_C50.htm?q=a_b&amp;x=y#C50V44">')
        source = start + 'he=will÷stand</a></span>'
        expected = start + 'he<span class="ul">_</span>will<span class="ul">_</span>stand</a></span>'
        self.assertEqual(do_OET_LV_HTMLcustomisations('Interlinear=JER_50:44', source), expected)

    def test_lv_legacy_popup_placeholders_restore_after_protection(self):
        source = ('<span class="fnCaller">[<a title="OSHB note--fnCOLON-- '
                  'lemma--fnEQUAL--7323 n--fnEQUAL--1--fnPERIOD--1--fnPERIOD--0 '
                  'a--fnUNDERLINE--b" href="#fn1">fn</a>]</span>')
        expected = ('<span class="fnCaller">[<a title="OSHB note: '
                    'lemma=7323 n=1.1.0 a_b" href="#fn1">fn</a>]</span>')
        self.assertEqual(do_OET_LV_HTMLcustomisations('ParallelVerseTxt=JER_50:44', source), expected)

    def test_nested_formats_inside_a_word_link_include_source_information(self):
        source = ('<span class="add">≈<a title="source (untranslated)" href="../ref/GrkWrd/word.htm">'
                  '<span class="add">?#words</span></a></span>')
        result = do_OET_RV_HTMLcustomisations('DictVerse=MRK_1:1', source)
        self.assertIn('title="reworded; source (untranslated)"', result)
        self.assertIn('title="reworded; changed number (less certain); source (untranslated)"', result)

    def test_long_word_title_still_valid_with_formatting_prefix(self):
        setStrictCheckingFlag(True)
        source = ('<span class="add">?≈<a title="' + 'א' * 74 + '" '
                  'href="../ref/HebWrd/test.htm">word</a></span>')
        result = do_OET_RV_HTMLcustomisations('Chapter=GEN_1', source)
        self.assertIn('title="reworded (less certain); ' + 'א' * 74 + '"', result)


class TestLSVHTMLcustomisations(unittest.TestCase):
    """LSV parallel lines become HTML breaks preceded by source newlines."""

    def test_spaced_double_pipes(self):
        self.assertEqual(do_LSV_HTMLcustomisations('test', 'a || b'), 'a\n<br>b')

    def test_tight_double_pipes(self):
        self.assertEqual(do_LSV_HTMLcustomisations('test', 'x||y'), 'x\n<br>y')


class TestT4THTMLcustomisations(unittest.TestCase):
    """T4T figure-of-speech codes and '◄' alternative markers."""

    def test_single_fos(self):
        self.assertEqual(
            do_T4T_HTMLcustomisations('test', 'world [SYM] so much'),
            'world <span class="t4tFoS" title="symbol (figure of speech)">[SYM]</span> so much')

    def test_fos_pair(self):
        self.assertEqual(
            do_T4T_HTMLcustomisations('test', '[APO, CHI]'),
            '[<span class="t4tFoS" title="apostrophe (figure of speech)">APO</span>, '
            '<span class="t4tFoS" title="chiasmus (figure of speech)">CHI</span>]')

    def test_alternative_marker(self):
        self.assertEqual(
            do_T4T_HTMLcustomisations('test', 'No figures here. ◄'),
            'No figures here. <span title="alternative translation">◄</span>')


class TestConvertAddsToItalics(StrictCheckMixin, unittest.TestCase):
    """html.convert_adds_to_italics → Rust convertAddsToItalics."""

    def test_plain_add(self):
        self.assertEqual(convert_adds_to_italics('<span class="add">word</span>'), '<i>word</i>')

    def test_multiple_adds(self):
        self.assertEqual(
            convert_adds_to_italics('a<span class="add">one</span>b<span class="add">two</span>c'),
            'a<i>one</i>b<i>two</i>c')

    def test_no_adds_untouched(self):
        self.assertEqual(convert_adds_to_italics('plain text'), 'plain text')

    def test_root_add(self):
        self.assertEqual(
            convert_adds_to_italics('בְּרֵאשִׁית <span class="add">x</span>'),
            'בְּרֵאשִׁית <i>x</i>')

    def test_thirty_adds_name_error(self):
        # Py for-else `not_enough_loops` — a NameError in every build mode.
        with self.assertRaises(NameError):
            convert_adds_to_italics('<span class="add">a</span>' * 30)


class TestHandleAndExtractFootnotes(StrictCheckMixin, unittest.TestCase):
    """html.handleAndExtractFootnotes → Rust handleAndExtractFootnotes."""

    def test_no_footnotes_passthrough(self):
        self.assertEqual(handleAndExtractFootnotes('ABC', 'plain'), ('plain', 'plain', ''))

    def test_full_split_and_namespacing(self):
        verse, free, notes = handleAndExtractFootnotes(
            'ABC',
            't <span class="fnCaller">[<a title="K" href="#fnUHB1">fn</a>]</span>\n'
            '<div id="footnotes" class="footnotes">\n<hr class="none">\n'
            '<div id="fnUHB1">1</div>\n</div>\n',
        )
        self.assertEqual(
            verse,
            't <span class="fnCaller">[<a title="K" href="#fnABCUHB1">fn</a>]</span>\n'
            '<div id="footnotesABC" class="footnotes">')
        self.assertEqual(
            free,
            't \n<div id="footnotesABC" class="footnotes">')
        self.assertEqual(notes, '<hr class="none">\n<div id="fnABCUHB1">1</div>\n</div>\n')

    def test_fncaller_across_newline_survives(self):
        # Python's '.' excludes '\n', so a multiline caller is not stripped.
        verse, free, _ = handleAndExtractFootnotes(
            'ABC',
            'a<span class="fnCaller">one\ntwo</span>b\n'
            '<div id="footnotes" class="footnotes">\n<hr x>\n</div>\n',
        )
        self.assertIn('<span class="fnCaller">one\ntwo</span>', verse)
        self.assertIn('<span class="fnCaller">one\ntwo</span>', free)

    def test_strict_missing_hr_assert(self):
        setStrictCheckingFlag(True)
        with self.assertRaises(AssertionError):
            handleAndExtractFootnotes('ABC', '<div id="footnotes" class="footnotes">\n</div>\n')

    def test_strict_unbalanced_divs_assert(self):
        setStrictCheckingFlag(True)
        with self.assertRaises(AssertionError):
            handleAndExtractFootnotes('ABC', '<div id="footnotes" class="footnotes">\n<hr x>\n</div></div>\n')

    def test_strict_stray_hr_non_oetrv_assert(self):
        setStrictCheckingFlag(True)
        with self.assertRaises(AssertionError):
            handleAndExtractFootnotes('ABC', 'stray <hr here')

    def test_strict_stray_hr_oetrv_allowed(self):
        setStrictCheckingFlag(True)
        self.assertEqual(
            handleAndExtractFootnotes('OET-RV', 'stray <hr here'),
            ('stray <hr here', 'stray <hr here', ''))

    def test_strict_stop_here_trap(self):
        setStrictCheckingFlag(True)
        with self.assertRaises(AssertionError):
            handleAndExtractFootnotes('ABC', 'x class="footnotes" y')

    def test_non_strict_missing_hr_value_error(self):
        # With asserts off (matching python -O) the split() ValueError surfaces.
        setStrictCheckingFlag(False)
        with self.assertRaises(ValueError):
            handleAndExtractFootnotes('ABC', '<div id="footnotes" class="footnotes">\n</div>\n')

    def test_non_strict_stray_hr_allowed(self):
        setStrictCheckingFlag(False)
        self.assertEqual(
            handleAndExtractFootnotes('ABC', 'stray <hr here'),
            ('stray <hr here', 'stray <hr here', ''))


if __name__ == '__main__':
    unittest.main()
