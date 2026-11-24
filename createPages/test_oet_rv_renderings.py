#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Tests for oetRVRenderings: how the OET-RV translates each OET-LV source word.

CHANGELOG:
    2026-11-24 Created.
"""
import unittest

from oetRVRenderings import extractRVRenderings, rvRenderingsSummaryHtml, tidyRVWord


class ExtractRVRenderingsTests(unittest.TestCase):
    def test_adjacent_and_separated_words(self):
        renderings = extractRVRenderings(
            r"\v 2 These¦5593 are the¦5586 names¦5591 of¦5588 the twelve¦5588: Shim'on¦5595 \add !(Simon¦5595,\add* nicknamed¦5597 Kefa¦5598 \add !(Peter¦5598; Grk. Petros¦5598)\add*)" )
        self.assertEqual( renderings[5588], 'of … twelve' )
        self.assertEqual( renderings[5595], "Shim'on" ) # Alternative names are ignored
        self.assertEqual( renderings[5598], 'Kefa' )

    def test_add_markers_and_notes(self):
        renderings = extractRVRenderings(
            r"\v 2 Avraham¦9 \add ≈was¦10 the¦10 father¦10 of¦10\add* Yitshak¦12.\f + \fr 1:2 \ft A note¦77.\f* \x + \xo 3:2: \xt Mat 4:17¦78.\x*" )
        self.assertEqual( renderings[10], 'was the father of' )
        self.assertEqual( renderings[12], 'Yitshak' )
        self.assertNotIn( 77, renderings )
        self.assertNotIn( 78, renderings )

    def test_only_the_part_after_a_dash_is_linked(self):
        self.assertEqual( extractRVRenderings( 'himself—once¦5 for¦5 everyone¦5' )[5], 'once for everyone' )

    def test_tidy_word(self):
        self.assertEqual( tidyRVWord( '“Where’s' ), 'Where’s' )
        self.assertEqual( tidyRVWord( '(Zebedaios’' ), 'Zebedaios’' )
        self.assertEqual( tidyRVWord( 'brothers’,' ), 'brothers’' )
        self.assertEqual( tidyRVWord( 'king’' ), 'king' )


class SummaryTests(unittest.TestCase):
    def test_partly_aligned(self):
        html = rvRenderingsSummaryHtml( [1,2,3,4,5], {1:'Apostles', 2:'Apostles', 4:'apostles', 3:'messengers'}, 'it' )
        self.assertEqual( html, '<p class="summary">In the <em>OET-RV</em>, it is translated in 2 different ways'
            ' <small>(4 of 5 occurrences linked so far: 80%)</small>: ‘<b>apostles</b>’(3), ‘<b>messengers</b>’(1).</p>' )

    def test_always(self):
        self.assertEqual( rvRenderingsSummaryHtml( [1,2], {1:'apostles', 2:'apostles'}, 'it' ),
            '<p class="summary">In the <em>OET-RV</em>, it is always translated as ‘<b>apostles</b>’ <small>(all 2 occurrences linked)</small>.</p>' )
        self.assertEqual( rvRenderingsSummaryHtml( [1], {1:'apostle'}, 'it' ),
            '<p class="summary">In the <em>OET-RV</em>, it is translated as ‘<b>apostle</b>’ <small>(its only occurrence is linked)</small>.</p>' )

    def test_not_aligned(self):
        self.assertEqual( rvRenderingsSummaryHtml( [1], {}, 'the word form ‘X’' ),
            '<p class="summary">In the <em>OET-RV</em>, the only occurrence of the word form ‘X’ isn’t linked to its source word yet.</p>' )
        self.assertEqual( rvRenderingsSummaryHtml( [1,2], {}, 'it' ),
            '<p class="summary">In the <em>OET-RV</em>, none of the 2 occurrences of it are linked to its source word yet.</p>' )

    def test_percentage_rounds_down(self):
        self.assertIn( '(199 of 200 occurrences linked so far: 99%)', rvRenderingsSummaryHtml( list(range(200)), {n:'x' for n in range(199)} ) )
        self.assertIn( '(1 of 200 occurrences linked so far: 1%)', rvRenderingsSummaryHtml( list(range(200)), {0:'x'} ) )

    def test_limit(self):
        html = rvRenderingsSummaryHtml( list(range(1,6)), {n:f'w{n}' for n in range(1,6)}, maxShown=3 )
        self.assertIn( '‘<b>w3</b>’(1), and 2 others.', html )


if __name__ == '__main__':
    unittest.main()
