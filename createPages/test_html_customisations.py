#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_html_customisations.py
#
# Tests for the html.py customisation functions.

import unittest

from html import do_OET_LV_HTMLcustomisations


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


if __name__ == '__main__':
    unittest.main()
