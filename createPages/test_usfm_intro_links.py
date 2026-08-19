#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_usfm_intro_links.py
#
# Tests for USFM introduction link livening (Rust PyO3 implementation)

import unittest
from settings import State
from openbibledata_rust import liven_introduction_links, to_roman_numerals


class TestUsfmIntroLinks(unittest.TestCase):
    def setUp(self):
        self.state = State()

    def test_bcv_book_segment(self):
        text = "was named Mary (Acts 12:12)"
        out = liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "book", text, self.state)
        self.assertEqual(
            out,
            'was named Mary (<a title="Go to reference document" href="ACT.htm#C12V12">Acts 12:12</a>)',
        )

    def test_bcv_chapter_segment(self):
        text = "accompanied Peter (1 Peter 5:13)"
        out = liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "chapter", text, self.state)
        self.assertEqual(
            out,
            'accompanied Peter (<a title="Go to reference chapter" href="PE1_C5.htm#C5V13">1 Peter 5:13</a>)',
        )

    def test_bcv_verse_segment_same_book_a(self):
        text = "see 4:10."
        out = liven_introduction_links("OET-RV", ("COL", "-1", "1"), "Verse", text, self.state)
        self.assertEqual(
            out,
            'see <a title="Go to reference verse" href="C4V10.htm#Top">4:10</a>.',
        )

    def test_bcv_verse_segment_same_book_b(self):
        text = "something. (4:10)"
        out = liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "Verse", text, self.state)
        self.assertEqual(
            out,
            'something. (<a title="Go to reference verse" href="C4V10.htm#Top">4:10</a>)',
        )

    def test_bcv_verse_segment_different_book_a(self):
        text = "see Col. 4:10."
        out = liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "Verse", text, self.state)
        self.assertEqual(
            out,
            'see <a title="Go to reference verse" href="../COL/C4V10.htm#Top">Col. 4:10</a>.',
        )

    def test_bcv_verse_segment_different_book_b(self):
        text = "something. (Col. 4:10)"
        out = liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "Verse", text, self.state)
        self.assertEqual(
            out,
            'something. (<a title="Go to reference verse" href="../COL/C4V10.htm#Top">Col. 4:10</a>)',
        )

    def test_bcv_prefixes(self):
        text = "(See Acts 12:12) and (as in Matt 5:3)"
        out = liven_introduction_links("OET-RV", ("GEN", "1", "1"), "book", text, self.state)
        self.assertEqual(
            out,
            '(<a title="Go to reference document" href="ACT.htm#C12V12">See Acts 12:12</a>) and (<a title="Go to reference document" href="MAT.htm#C5V3">as in Matt 5:3</a>)',
        )

    def test_cv_book_and_chapter(self):
        text = "in this book (12:12) or (16:9-20)"
        out_book = liven_introduction_links("OET-RV", ("MRK", "-1", "1"), "book", text, self.state)
        self.assertEqual(
            out_book,
            'in this book (<a title="Jump down to reference" href="#C12V12">12:12</a>) or (<a title="Jump down to reference" href="#C16V9">16:9-20</a>)',
        )

        out_chap = liven_introduction_links("OET-RV", ("MRK", "-1", "1"), "chapter", text, self.state)
        self.assertEqual(
            out_chap,
            'in this book (<a title="Jump to chapter page with reference" href="MRK_C12.htm#C12V12">12:12</a>) or (<a title="Jump to chapter page with reference" href="MRK_C16.htm#C16V9">16:9-20</a>)',
        )

    def test_multiple_bcv_and_cv(self):
        text = "about Yeshua the messiah (Acts 12:25, 13:13)."
        out_book = liven_introduction_links("OET-RV", ("MRK", "-1", "1"), "book", text, self.state)
        self.assertEqual(
            out_book,
            'about Yeshua the messiah (<a title="Go to reference document" href="ACT.htm#C12V25">Acts 12:25</a>, <a title="Go to reference document" href="ACT.htm#C13V13">13:13</a>).',
        )

        out_chap = liven_introduction_links("OET-RV", ("MRK", "-1", "1"), "chapter", text, self.state)
        self.assertEqual(
            out_chap,
            'about Yeshua the messiah (<a title="Go to reference chapter" href="ACT_C12.htm#C12V25">Acts 12:25</a>, <a title="Go to reference chapter" href="ACT_C13.htm#C13V13">13:13</a>).',
        )

    def test_to_roman_numerals(self):
        self.assertEqual(to_roman_numerals(1), "I")
        self.assertEqual(to_roman_numerals(4), "IV")
        self.assertEqual(to_roman_numerals(9), "IX")
        self.assertEqual(to_roman_numerals(14), "XIV")
        self.assertEqual(to_roman_numerals(40), "XL")
        self.assertEqual(to_roman_numerals(50), "L")
        self.assertEqual(to_roman_numerals(90), "XC")
        self.assertEqual(to_roman_numerals(99), "XCIX")
        self.assertEqual(to_roman_numerals(100), "C")
        self.assertEqual(to_roman_numerals(119), "CXIX")
        self.assertEqual(to_roman_numerals(150), "CL")
        self.assertEqual(to_roman_numerals("151"), "CLI")
        self.assertEqual(to_roman_numerals(0), "")

    def test_ior_assertions(self):
        with self.assertRaises(AssertionError):
            liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "book", r"Some \ior text", self.state)

        with self.assertRaises(AssertionError):
            liven_introduction_links("OET-RV", ("MAT", "-1", "1"), "book", '<span class="ior">text</span>', self.state)


if __name__ == "__main__":
    unittest.main()
