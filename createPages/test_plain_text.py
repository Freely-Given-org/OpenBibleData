#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_plain_text.py
#
# Parity test: InternalBibleEntryList.plain_text (Rust, added 2026-10-04)
# must match the old Python getPlainText loop that walked entries calling
# getMarker()/getCleanText() per entry.

import unittest

from BibleOrgSys.Internals.InternalBible import InternalBibleEntryList, InternalBibleEntry
from createParallelVersePages import getPlainText


def oldPyGetPlainText( givenVerseEntryList ) -> str:
    plainTextStringBits = []
    for entry in givenVerseEntryList:
        marker, cleanText = entry.getMarker(), entry.getCleanText()
        if marker == 'v~':
            plainTextStringBits.append( cleanText )
    return ' '.join( plainTextStringBits )


def make_entry( marker: str, text: str ) -> InternalBibleEntry:
    return InternalBibleEntry( marker, marker, text, text, None, text )


class TestPlainText(unittest.TestCase):
    def test_parity_with_old_python(self):
        entries = [
            make_entry('v',  '1'),
            make_entry('v~', 'In the beginning God created the heavens and the earth.'),
            make_entry('p',  ''),
            make_entry('v~', 'Now the earth was formless and empty'),
            make_entry('¬v', '1'),
            make_entry('v~', ''),
        ]
        eList = InternalBibleEntryList(entries)
        self.assertEqual(getPlainText(eList), oldPyGetPlainText(eList))
        self.assertEqual(eList.plain_text('v~'), oldPyGetPlainText(eList))
        self.assertEqual(getPlainText(eList), 'In the beginning God created the heavens and the earth. Now the earth was formless and empty v~')
        # (NB: InternalBibleEntry.getCleanText returns the marker for empty-text entries — a quirk retained for parity)

    def test_empty(self):
        eList = InternalBibleEntryList([])
        self.assertEqual(getPlainText(eList), '')

    def test_no_matching_marker(self):
        eList = InternalBibleEntryList([make_entry('p', 'hello')])
        self.assertEqual(getPlainText(eList), '')


if __name__ == '__main__':
    unittest.main()
