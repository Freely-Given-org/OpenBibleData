#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_get_chapter_verse_entries.py
#
# Item 3: bulk per-chapter fetch `getChapterVerseEntriesWithContext` (one
# Rust call per chapter per version) must produce byte-identical
# (entries, context) to per-verse `thisBible.getContextVerseData((BBB,C,V))`.
#
# CHANGELOG:
# 2026-11-22: Check that word-aligned USFM (SR-GNT, UGNT) loads with its verse text,
#     since loading without the BibleOrgSys USFM marker lists once pickled textless Bibles.

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

    def test_word_aligned_USFM_keeps_verse_text(self):
        # Every SR-GNT and UGNT word line starts with \w, which BibleOrgSys drops
        #   if its USFM marker lists weren't loaded (giving textless Bibles that then get pickled).
        for versionAbbreviation in ('SR-GNT', 'UGNT'):
            with self.subTest(versionAbbreviation):
                if versionAbbreviation not in State.preloadedBibles:
                    self.skipTest(f"{versionAbbreviation} isn't loaded in this configuration")
                entries, _context = State.preloadedBibles[versionAbbreviation].getContextVerseData(('MRK', '1', '1'))
                verseText = ''.join(entry.getCleanText() for entry in entries if entry.getMarker() == 'v~')
                self.assertTrue(verseText.strip(), f"{versionAbbreviation} MRK 1:1 loaded without any text: {[entry.getMarker() for entry in entries]}")


if __name__ == '__main__':
    unittest.main()
