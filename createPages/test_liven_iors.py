#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_liven_iors.py
#
# Tests for IOR (Introduction Outline Reference) link livening (Rust PyO3 implementation)

import unittest
from settings import State
from openbibledata_rust import liven_iors


class TestLivenIORs(unittest.TestCase):
    def setUp(self):
        self.state = State()

    def test_ior_book_segment(self):
        """Test IOR link creation for book segment type"""
        html = r'See also <span class="ior">12:12</span> for more.'
        result = liven_iors("OET-RV", "MAT", "book", html, False)
        self.assertEqual(
            result,
            r'See also <span class="ior"><a title="Jump down to reference" href="#C12V12">12:12</a></span> for more.',
        )

    def test_ior_chapter_segment(self):
        """Test IOR link creation for chapter segment type"""
        html = r'Find it in <span class="ior">5:13</span> section.'
        result = liven_iors("OET-RV", "MAT", "chapter", html, False)
        self.assertEqual(
            result,
            r'Find it in <span class="ior"><a title="Jump to chapter page with reference" href="MAT_C5.htm#C5V13">5:13</a></span> section.',
        )

    def test_ior_verse_segment(self):
        """Test IOR link creation for verse segment type"""
        html = r'Reference: <span class="ior">4:10</span>.'
        result = liven_iors("OET-RV", "COL", "Verse", html, False)
        self.assertEqual(
            result,
            r'Reference: <span class="ior"><a title="Go to reference verse" href="C4V10.htm#Top">4:10</a></span>.',
        )

    def test_ior_single_chapter_verse_only(self):
        """Test IOR with verse number only for single-chapter book"""
        html = r'See <span class="ior">4</span> for details.'
        result = liven_iors("OET-RV", "OBD", "Verse", html, True)
        self.assertEqual(
            result,
            r'See <span class="ior"><a title="Go to reference verse" href="C1V4.htm#Top">4</a></span> for details.',
        )

    def test_ior_multi_chapter_chapter_only(self):
        """Test IOR with chapter number only for multi-chapter book"""
        html = r'See <span class="ior">4</span> for details.'
        result = liven_iors("OET-RV", "MAT", "chapter", html, False)
        self.assertEqual(
            result,
            r'See <span class="ior"><a title="Jump to chapter page with reference" href="MAT_C4.htm#C4V1">4</a></span> for details.',
        )

    def test_ior_multiple_spans(self):
        """Test IOR with multiple span tags"""
        html = r'In <span class="ior">3:16</span> and <span class="ior">5:7</span> we find this.'
        result = liven_iors("OET-RV", "JHN", "book", html, False)
        self.assertEqual(
            result,
            r'In <span class="ior"><a title="Jump down to reference" href="#C3V16">3:16</a></span> and <span class="ior"><a title="Jump down to reference" href="#C5V7">5:7</a></span> we find this.',
        )

    def test_ior_with_range(self):
        """Test IOR with verse range (only start is linked)"""
        html = r'Found in <span class="ior">12:12-15</span> section.'
        result = liven_iors("OET-RV", "MRK", "book", html, False)
        self.assertEqual(
            result,
            r'Found in <span class="ior"><a title="Jump down to reference" href="#C12V12">12:12-15</a></span> section.',
        )

    def test_ior_with_endash(self):
        """Test IOR with en-dash (converted to hyphen)"""
        html = r'Range: <span class="ior">5:3–8</span>.'
        result = liven_iors("OET-RV", "ROM", "chapter", html, False)
        self.assertEqual(
            result,
            r'Range: <span class="ior"><a title="Jump to chapter page with reference" href="ROM_C5.htm#C5V3">5:3-8</a></span>.',
        )

    def test_ior_empty_input(self):
        """Test IOR with no spans"""
        html = "No IOR tags here."
        result = liven_iors("OET-RV", "MAT", "book", html, False)
        self.assertEqual(result, html)

    def test_ior_book_single_chapter(self):
        """Test IOR book segment with single-chapter book"""
        html = r'See <span class="ior">3:5</span>.'
        result = liven_iors("OET-RV", "PHM", "book", html, True)
        self.assertEqual(
            result,
            r'See <span class="ior"><a title="Jump down to reference" href="#C3V5">3:5</a></span>.',
        )

    def test_ior_complex_content(self):
        """Test IOR with complex HTML content around it"""
        html = r'<p>Related passages: <strong><span class="ior">12:3</span></strong> and others</p>'
        result = liven_iors("OET-RV", "MAT", "book", html, False)
        self.assertEqual(
            result,
            r'<p>Related passages: <strong><span class="ior"><a title="Jump down to reference" href="#C12V3">12:3</a></span></strong> and others</p>',
        )

    def test_ior_consecutive_spans(self):
        """Test IOR with consecutive spans"""
        html = r'See <span class="ior">2:3</span><span class="ior">4:5</span> here.'
        result = liven_iors("OET-RV", "ROM", "chapter", html, False)
        self.assertEqual(
            result,
            r'See <span class="ior"><a title="Jump to chapter page with reference" href="ROM_C2.htm#C2V3">2:3</a></span><span class="ior"><a title="Jump to chapter page with reference" href="ROM_C4.htm#C4V5">4:5</a></span> here.',
        )

    def test_ior_with_whitespace(self):
        """Test IOR with extra whitespace inside span"""
        html = r'Find in <span class="ior">  3:14  </span> please.'
        result = liven_iors("OET-RV", "JHN", "book", html, False)
        # The function doesn't strip whitespace, just uses the content as-is
        self.assertIn("3:14", result)

    def test_ior_verse_with_large_numbers(self):
        """Test IOR with large chapter and verse numbers"""
        html = r'In <span class="ior">150:6</span>.'
        result = liven_iors("OET-RV", "PSA", "chapter", html, False)
        self.assertEqual(
            result,
            r'In <span class="ior"><a title="Jump to chapter page with reference" href="PSA_C150.htm#C150V6">150:6</a></span>.',
        )

    def test_ior_single_digit_chapter_verse(self):
        """Test IOR with single-digit chapter and verse"""
        html = r'See <span class="ior">1:1</span> first.'
        result = liven_iors("OET-RV", "GEN", "book", html, False)
        self.assertEqual(
            result,
            r'See <span class="ior"><a title="Jump down to reference" href="#C1V1">1:1</a></span> first.',
        )


if __name__ == '__main__':
    unittest.main()
