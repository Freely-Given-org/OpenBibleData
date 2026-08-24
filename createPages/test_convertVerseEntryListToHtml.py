#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_convertVerseEntryListToHtml.py
#
# Integration tests for the full convertVerseEntryListToHtml pipeline,
# verifying that the Rust implementation works correctly end-to-end.

import unittest
from BibleOrgSys.Internals.InternalBible import InternalBibleEntryList, InternalBibleEntry
from settings import State
from openbibledata_rust import convertVerseEntryListToHtml


def make_entry( marker: str, original_text: str, clean_text: str | None = None ) -> InternalBibleEntry:
    """Create an InternalBibleEntry.
    For end markers (¬v), the original_text is the verse number text.
    For content markers, original_text is the full USFM text.
    clean_text must NOT contain backslashes.
    InternalBibleEntry(marker, originalMarker, originalText, adjustedText, extras, cleanText)"""
    if clean_text is None:
        clean_text = ''
        for ch in original_text:
            if ch != '\\':
                clean_text += ch
    if marker.startswith('\u00ac'):
        return InternalBibleEntry( marker, marker, original_text, original_text, None, clean_text )
    return InternalBibleEntry( marker, marker, original_text, original_text, None, clean_text )


class TestConvertVerseEntryListToHtml_Integration(unittest.TestCase):
    """End-to-end tests for convertVerseEntryListToHtml with the Rust backend."""

    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = True

    def test_simple_verse_kjb(self):
        """Simple verse text from KJB — no footnotes, no xrefs."""
        entry_list = InternalBibleEntryList()
        entry_list.append( make_entry( 'v', '1' ) )
        entry_list.append( make_entry( 'v~', 'In the beginning God created the heaven and the earth.' ) )
        entry_list.append( InternalBibleEntry( '\u00acv', '1' ) )  # 2-arg end marker form
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entry_list,
            basicOnly=False, state=self.state,
        )
        self.assertIn('In the beginning God created', result)

    def test_verse_with_footnote(self):
        """Verse with a footnote — the Rust footnote processor should handle it."""
        entry_list = InternalBibleEntryList()
        entry_list.append( make_entry( 'v', '1' ) )
        entry_list.append( make_entry( 'v~',
            'In the beginning God created the heaven and the earth.\\f + \\fr 1:1 \\ft The Creator.\\f*' ) )
        entry_list.append( InternalBibleEntry( '\u00acv', '1' ) )
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entry_list,
            basicOnly=False, state=self.state,
        )
        self.assertIn('In the beginning God created', result)
        self.assertIn('fnCaller', result)
        self.assertNotIn('\\f ', result)
        self.assertIn('The Creator.', result)

    def test_verse_with_xref(self):
        """Verse with a cross-reference — the Rust xref processor should handle it."""
        entry_list = InternalBibleEntryList()
        entry_list.append( make_entry( 'v', '1' ) )
        entry_list.append( make_entry( 'v~',
            'God created the heavens.\\x \\xo 1:1 \\xt Gen 2:4.\\x*' ) )
        entry_list.append( InternalBibleEntry( '\u00acv', '1' ) )
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entry_list,
            basicOnly=False, state=self.state,
        )
        self.assertIn('God created the heavens', result)
        self.assertIn('xrCaller', result)
        self.assertNotIn('\\x ', result)

    def test_verse_with_footnote_and_xref(self):
        """Verse with both footnote and cross-reference."""
        entry_list = InternalBibleEntryList()
        entry_list.append( make_entry( 'v', '1' ) )
        entry_list.append( make_entry( 'v~',
            'In the beginning.\\f + \\fr 1:1 \\ft Note.\\f* God created.\\x \\xo 1:2 \\xt Gen 2:4.\\x*' ) )
        entry_list.append( InternalBibleEntry( '\u00acv', '1' ) )
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entry_list,
            basicOnly=False, state=self.state,
        )
        self.assertIn('fnCaller', result)
        self.assertIn('xrCaller', result)
        self.assertNotIn('\\f ', result)
        self.assertNotIn('\\x ', result)

    def test_basic_only_strips_xrefs(self):
        """basicOnly=True should remove cross-references from the text."""
        entry_list = InternalBibleEntryList()
        entry_list.append( make_entry( 'v', '1' ) )
        entry_list.append( make_entry( 'v~',
            'God created.\\x \\xo 1:1 \\xt Gen 2:4.\\x*' ) )
        entry_list.append( InternalBibleEntry( '\u00acv', '1' ) )
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entry_list,
            basicOnly=True, state=self.state,
        )
        self.assertIn('God created', result)
        self.assertNotIn('xrCaller', result)


# ── Simple entry class for direct Rust tests ────────────────────────────────

class _SimpleEntry:
    """Minimal object with marker/full_text/clean_text attributes for the Rust wrapper."""
    __slots__ = ('marker', 'full_text', 'clean_text')
    def __init__(self, marker, full_text, clean_text=None):
        self.marker = marker
        self.full_text = full_text
        self.clean_text = clean_text if clean_text is not None else full_text


class TestRustConvertVerseEntryListToHtml(unittest.TestCase):
    """Direct tests of the Rust convertVerseEntryListToHtml via PyO3."""

    def test_simple_verse(self):
        entries = [
            _SimpleEntry('v', '1'),
            _SimpleEntry('v~', 'In the beginning God created the heaven and the earth.'),
            _SimpleEntry('\u00acv', ''),
        ]
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entries,
            basicOnly=False,
        )
        self.assertIn('In the beginning God created', result)

    def test_basic_only_mode(self):
        entries = [
            _SimpleEntry('v', '1'),
            _SimpleEntry('v~', 'God created the heavens and the earth.'),
            _SimpleEntry('\u00acv', ''),
        ]
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entries,
            basicOnly=True,
        )
        self.assertIn('God created the heavens and the earth', result)

    def test_footnotes_in_rust(self):
        """Verify footnotes are processed when invoked from Rust directly."""
        entries = [
            _SimpleEntry('v', '1'),
            _SimpleEntry('v~', 'God created the heavens.\\f + \\fr 1:1 \\ft Creator.\\f*'),
            _SimpleEntry('\u00acv', ''),
        ]
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entries,
            basicOnly=False,
        )
        self.assertIn('God created the heavens', result)
        self.assertNotIn('\\f ', result)
        self.assertIn('Creator.', result)

    def test_xrefs_in_rust(self):
        """Verify cross-references are processed when invoked from Rust directly."""
        entries = [
            _SimpleEntry('v', '1'),
            _SimpleEntry('v~', 'God created.\\x \\xo 1:1 \\xt Gen 2:4.\\x*'),
            _SimpleEntry('\u00acv', ''),
        ]
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('GEN', '1', '1'), segmentType='parallelVerse',
            contextList=['chapters'], verseEntryList=entries,
            basicOnly=False,
        )
        self.assertIn('God created', result)
        self.assertNotIn('\\x ', result)

    def test_single_chapter_book_lookup(self):
        """The single-chapter-book flag is looked up in Rust via bos_books_codes (PHM has one chapter)."""
        entries = [
            _SimpleEntry('v', '1'),
            _SimpleEntry('v~', 'Paul, a prisoner.'),
            _SimpleEntry('\u00acv', ''),
        ]
        result = convertVerseEntryListToHtml(
            level=1, versionAbbreviation='KJB',
            refTuple=('PHM', '1'), segmentType='chapter',
            contextList=['chapters'], verseEntryList=entries,
            basicOnly=False,
        )
        self.assertIn('id="V1"', result)  # Anchor added because PHM is a single chapter book


if __name__ == '__main__':
    unittest.main()
