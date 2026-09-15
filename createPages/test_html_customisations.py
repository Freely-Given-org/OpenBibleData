#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_html_customisations.py
#
# Tests for the html.py customisation functions.
#
# do_OET_RV_*, do_OET_LV_*, do_LSV_* and do_T4T_* now delegate to byte-identical
# Rust ports (createPages/Rust/src/html_customisations.rs); the expected outputs
# below were captured from the Python originals so they pin the byte-identity.

import unittest

from html import (
    do_OET_RV_HTMLcustomisations,
    do_OET_LV_HTMLcustomisations,
    do_LSV_HTMLcustomisations,
    do_T4T_HTMLcustomisations,
)


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
                    '<span class="addExtra" title="added implied info">'
                    '<span class="addArticle unsure" title="added article (less certain)">'
                    '<span class="addArticle" title="added article"></span></span></span></span>')
        self.assertEqual(do_OET_RV_HTMLcustomisations('test', input_html), expected)

    def test_parallelism_markers(self):
        out = do_OET_RV_HTMLcustomisations('test', '≈ and ^ and →')
        nnbs = '\u202f'
        self.assertIn(f'<span class="synonParr" title="synonymous parallelism">≈{nnbs}</span>', out)
        self.assertIn(f'<span class="antiParr" title="antithetic parallelism">^{nnbs}</span>', out)
        self.assertIn(f'<span class="synthParr" title="synthetic parallelism">→{nnbs}</span>', out)

    def test_preexisting_rvadd_left_untouched(self):
        self.assertEqual(
            do_OET_RV_HTMLcustomisations('test', '<span class="RVadd"><span class="wj">w</span></span>'),
            '<span class="RVadd"><span class="wj">w</span></span>')


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
        expected = ('<span class="addArticle">art</span><span class="addCopula">cop</span>'
                    '<span class="add"><a title="x">deep</a></span>'
                    '<span class="addDirectObject">x></span>'
                    '<span class="addExtra">extra</span><span class="addOwner">own</span>')
        self.assertEqual(do_OET_LV_HTMLcustomisations('test', input_html), expected)


class TestLSVHTMLcustomisations(unittest.TestCase):
    """LSV parallel lines ' || ' become <br>."""

    def test_spaced_double_pipes(self):
        self.assertEqual(do_LSV_HTMLcustomisations('test', 'a || b'), 'a<br>b')

    def test_tight_double_pipes(self):
        self.assertEqual(do_LSV_HTMLcustomisations('test', 'x||y'), 'x<br>y')


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


if __name__ == '__main__':
    unittest.main()
