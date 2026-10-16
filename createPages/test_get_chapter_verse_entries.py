#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_get_chapter_verse_entries.py
#
# Item 3: bulk per-chapter fetch `getChapterVerseEntriesWithContext` (one
# Rust call per chapter per version) must produce byte-identical
# (entries, context) to per-verse `thisBible.getContextVerseData((BBB,C,V))`.

import unittest

from settings import State
from Bibles import preloadVersions


class TestGetChapterVerseEntriesWithContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        preloadVersions(State)

    def check_book(self, versionAbbreviation, BBB, chapter):
        thisBible = State.preloadedBibles[versionAbbreviation]
        by_verse = thisBible.books[BBB]._CVIndex.getChapterVerseEntriesWithContext(chapter)
        numVerses = thisBible.getNumVerses(BBB, int(chapter))
        self.assertIsNotNone(numVerses)
        for v in range(0, numVerses + 1):
            V = str(v)
            try:
                entries, context = thisBible.getContextVerseData((BBB, chapter, V))
            except KeyError:
                self.assertNotIn(V, by_verse, f"bulk dict has {versionAbbreviation} {BBB} {chapter}:{V} but index lookup failed")
                continue
            self.assertIn(V, by_verse, f"missing {versionAbbreviation} {BBB} {chapter}:{V} in bulk fetch")
            bEntries, bContext = by_verse[V]
            self.assertEqual(len(entries), len(bEntries), f"{versionAbbreviation} {BBB} {chapter}:{V} entry count")
            for aEntry, bEntry in zip(entries, bEntries):
                self.assertEqual(aEntry.getMarker(), bEntry.getMarker())
                self.assertEqual(aEntry.getCleanText(), bEntry.getCleanText())
            self.assertEqual(context, bContext)

    def test_OET_RV_MRK_1(self):
        self.check_book('OET-RV', 'MRK', '1')

    def test_OET_LV_MRK_1(self):
        self.check_book('OET-LV', 'MRK', '1')

    def test_PSA_23(self):
        self.check_book('OET-RV', 'PSA', '23')


if __name__ == '__main__':
    unittest.main()
