#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
# -*- coding: utf-8 -*-
#
# test_verse_to_html.py
#
# Tests for verse_to_html Rust implementation (footnote and xref processing)

"""CHANGELOG:
2026-10-16 Test malformed-note diagnostics and isolation from later notes.
"""

import unittest
from types import SimpleNamespace
from settings import State
from openbibledata_rust import (convertVerseEntryListToHtml,
                                process_footnotes, process_cross_references)


class TestProcessFootnotes(unittest.TestCase):
    def setUp(self):
        self.state = State()

    def test_no_footnotes(self):
        """No footnotes in input returns unchanged HTML"""
        html = "Some text with no footnotes."
        result, fn_html = process_footnotes(html, "KJB", "GEN", "1", "chapter", "", 11500, self.state)
        self.assertEqual(result, html)
        self.assertEqual(fn_html, "")

    def test_simple_footnote(self):
        """Basic footnote is extracted and caller inserted"""
        html = r"Text \f + \fr 1:1 \ft Footnote content.\f* here"
        result, fn_html = process_footnotes(html, "KJB", "GEN", "1", "chapter", "", 11500, self.state)
        self.assertNotIn("\\f ", result)
        self.assertIn("fnCaller", result)
        self.assertIn("fnText", fn_html)
        self.assertIn("Footnote content.", fn_html)

    def test_footnote_with_backref(self):
        """Footnote with \fr reference gets back-reference link"""
        html = r"Text \f + \fr 1:5 \ft Cross ref.\f* end"
        result, fn_html = process_footnotes(html, "KJB", "GEN", "1", "chapter", "", 11500, self.state)
        self.assertIn("fnRef", fn_html)
        self.assertIn("#C1V5", fn_html)

    def test_multiple_footnotes(self):
        """Multiple footnotes are all processed"""
        html = r"First \f + \fr 1:1 \ft Note one.\f* middle \f + \fr 1:2 \ft Note two.\f* end"
        result, fn_html = process_footnotes(html, "KJB", "GEN", "1", "chapter", "", 11500, self.state)
        self.assertNotIn("\\f ", result)
        self.assertIn("Note one.", fn_html)
        self.assertIn("Note two.", fn_html)

    def test_footnote_with_internal_xt(self):
        r"""Footnote with \xt cross-reference marker gets livened"""
        html = r"Text \f + \fr 1:1 \ft See also \xt Gen 2:3.\f* end"
        result, fn_html = process_footnotes(html, "KJB", "GEN", "1", "chapter", "", 11500, self.state)
        self.assertNotIn("\\f ", result)
        self.assertIn("fnCaller", result)


class TestProcessCrossReferences(unittest.TestCase):
    def setUp(self):
        self.state = State()

    def test_no_xrefs(self):
        """No cross-references in input returns unchanged HTML"""
        html = "Some text with no xrefs."
        result, xr_html = process_cross_references(html, "KJB", "GEN", "1", "chapter", "", self.state)
        self.assertEqual(result, html)
        self.assertEqual(xr_html, "")

    def test_simple_xref(self):
        """Basic cross-reference is extracted and caller inserted"""
        html = r"Text \x \xo 1:1 \xt Gen 1:1.\x* end"
        result, xr_html = process_cross_references(html, "KJB", "GEN", "1", "chapter", "", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xrCaller", result)
        self.assertIn("xrText", xr_html)

    def test_xref_no_xo(self):
        r"""Cross-reference without \xo origin gets processed"""
        html = r"Text \x \xt John 3:16.\x* end"
        result, xr_html = process_cross_references(html, "KJB", "JHN", "3", "chapter", "", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xrText", xr_html)

    def test_multiple_xrefs(self):
        """Multiple cross-references are all processed"""
        html = r"First \x \xo 1:1 \xt Gen 1:1.\x* middle \x \xo 2:3 \xt Gen 2:3.\x* done"
        result, xr_html = process_cross_references(html, "KJB", "GEN", "1", "chapter", "", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xr1", xr_html)
        self.assertIn("xr2", xr_html)

    def test_xref_with_oet_rv(self):
        """Cross-references work with OET-RV version (uses section lookup)"""
        html = r"Text \x \xo 1:1 \xt Gen 1:1.\x* end"
        result, xr_html = process_cross_references(html, "OET-RV", "GEN", "1", "chapter", "", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xrCaller", result)


class TestNoneChapter(unittest.TestCase):
    """Tests that c=None and c='' work correctly (book-level processing)."""

    def setUp(self):
        self.state = State()

    def test_footnotes_with_none_c(self):
        """process_footnotes accepts c=None without crashing"""
        html = r"Text \f + \fr 3:16 \ft For God so loved.\f* here"
        result, fn_html = process_footnotes(html, "KJB", "JHN", None, "book", "../byC/", 11500, self.state)
        self.assertNotIn("\\f ", result)
        self.assertIn("fnCaller", result)
        self.assertIn("For God so loved.", fn_html)

    def test_footnotes_with_empty_c(self):
        """process_footnotes accepts c='' without crashing"""
        html = r"Text \f + \fr 3:16 \ft For God so loved.\f* here"
        result, fn_html = process_footnotes(html, "KJB", "JHN", "", "book", "../byC/", 11500, self.state)
        self.assertNotIn("\\f ", result)
        self.assertIn("fnCaller", result)
        self.assertIn("For God so loved.", fn_html)

    def test_xrefs_with_none_c(self):
        """process_cross_references accepts c=None without crashing"""
        html = r"Text \x \xo 1:1 \xt Gen 1:1.\x* end"
        result, xr_html = process_cross_references(html, "KJB", "GEN", None, "book", "../byC/", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xrCaller", result)

    def test_xrefs_with_empty_c(self):
        """process_cross_references accepts c='' without crashing"""
        html = r"Text \x \xo 1:1 \xt Gen 1:1.\x* end"
        result, xr_html = process_cross_references(html, "KJB", "GEN", "", "book", "../byC/", self.state)
        self.assertNotIn("\\x ", result)
        self.assertIn("xrCaller", result)


class TestNoteErrorLocations(unittest.TestCase):
    """Errors must identify the source entry, even without HTML verse anchors."""

    def convert(self, entries, reference=('PSA', '44'), segment='chapter', basic=False):
        return convertVerseEntryListToHtml(
            2, 'KJB-1611', reference, segment, [],
            [SimpleNamespace(marker=marker, full_text=text, clean_text='')
             for marker, text in entries], basicOnly=basic,
        )

    def test_missing_target_reports_actual_verse_and_entry(self):
        entries = [
            ('v', '22'), ('v~', r'Good.\x + \xo 44:22 \xt Gen 1:1.\x*'),
            ('v', '23'), ('v~', r'Awake.\x + \xo 99:9 Broken reference.\x*'),
            ('v', '24'), ('v~', r'Later.\x + \xo 44:24 \xt Gen 1:2.\x*'),
        ]
        with self.assertRaises(ValueError) as caught:
            self.convert(entries)
        message = str(caught.exception)
        self.assertIn('KJB-1611 PSA 44:23', message)
        self.assertIn("chapter, processed entry 4, marker 'v~'", message)
        self.assertIn("missing required marker '\\xt'", message)
        self.assertIn('byte offset 6', message)
        self.assertIn('Broken reference.', message)

    def test_book_and_section_follow_chapter_and_verse_range(self):
        for segment in ('book', 'section'):
            with self.subTest(segment=segment):
                entries = [('c', '43'), ('v', '5'), ('v~', 'Earlier chapter.'),
                           ('c', '44'), ('v', '23-24'),
                           ('v~', r'Awake.\x + Broken reference.\x*')]
                with self.assertRaisesRegex(ValueError, 'KJB-1611 PSA 44:23-24'):
                    self.convert(entries, ('PSA',), segment)

    def test_verse_reference_used_without_number_entry(self):
        with self.assertRaisesRegex(ValueError, 'KJB-1611 PSA 44:23'):
            self.convert([('v~', r'Text.\f + \ft Unclosed footnote.')],
                         ('PSA', '44', '23'), 'parallelVerse', basic=True)

    def test_chapter_intro_does_not_reuse_previous_verse(self):
        entries = [('c', '43'), ('v', '5'), ('v~', 'Earlier chapter.'),
                   ('c', '44'), ('d', r'Title.\x + Broken reference.\x*')]
        with self.assertRaisesRegex(ValueError, 'KJB-1611 PSA 44:0'):
            self.convert(entries, ('PSA',), 'book')

    def test_introduction_with_no_cv_is_identified(self):
        with self.assertRaisesRegex(ValueError, r'KJB-1611 PSA introduction \(no C:V\)'):
            self.convert([('ip', r'Introduction.\f + \ft Unclosed.')], ('PSA',), 'book')

    def test_missing_end_markers_include_safe_unicode_excerpt(self):
        for opener, closer in ((r'\x + \xt ', r'\x*'), (r'\f + \ft ', r'\f*')):
            with self.subTest(closer=closer):
                with self.assertRaises(ValueError) as caught:
                    self.convert([('v', '23'), ('v~', '“Awake!” ' + opener + 'é' * 200)])
                message = str(caught.exception)
                self.assertIn('KJB-1611 PSA 44:23', message)
                self.assertIn(f"missing end marker '{closer}'", message)
                self.assertIn('nearby text:', message)
                self.assertIn('é', message)
                self.assertIn('…', message)
                self.assertLess(len(message), 500)

    def test_basic_only_still_omits_cross_references(self):
        result = self.convert([('v', '23'), ('v~', r'Awake.\x + No target.\x*')], basic=True)
        self.assertIn('Awake.', result)
        self.assertNotIn('No target.', result)

    def test_xref_processor_does_not_borrow_later_target_or_end(self):
        for first, missing in ((r'\x + \xo 44:23 Broken.\x*', r'\xt'),
                               (r'\x + \xt Gen 1:1.', r'\x*')):
            with self.subTest(missing=missing):
                html = first + r' Later.\x + \xo 44:24 \xt Gen 1:2.\x*'
                with self.assertRaises(ValueError) as caught:
                    process_cross_references(html, 'KJB-1611', 'PSA', '44', 'chapter', '')
                self.assertIn(f"marker '{missing}'", str(caught.exception))

    def test_footnote_processor_does_not_borrow_later_end(self):
        html = r'\f + \ft Unclosed. Later.\f + \ft Valid.\f*'
        with self.assertRaisesRegex(ValueError, 'missing end marker'):
            process_footnotes(html, 'KJB-1611', 'PSA', '44', 'chapter', '', 11500)


if __name__ == "__main__":
    unittest.main()
