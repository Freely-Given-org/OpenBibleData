#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_verse_to_html.py
#
# Tests for verse_to_html Rust implementation (footnote and xref processing)

import unittest
from settings import State
from openbibledata_rust import process_footnotes, process_cross_references


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


if __name__ == "__main__":
    unittest.main()
