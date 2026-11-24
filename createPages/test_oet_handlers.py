#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_oet_handlers.py
#
# Integration tests for the former OETHandlers.py functions, which are now
# Rust PyO3 implementations in the openbibledata_rust module
# (Rust/src/oet_handlers.rs plus wrappers in Rust/src/lib.rs).
#
# These tests exercise the wrappers against real State/Bible objects
# (loaded from the cached pickles) as well as small stubs for edge cases.
#
# CHANGELOG:
# 2026-09-10: wordlinks are now livented natively in a single pass
#     (oet_handlers::liven_esfm_word_links), so the §«OrigWord»§ / ►NNNN◄
#     placeholder round-trip and the Berean loadESFMWordFile-on-demand
#     plumbing are gone; test_bereanLoadsTablesOnDemand was rewritten as
#     test_bereanTablesComeFromState to assert no table loading happens
#     (rows come from state.OETRefData['word_tables']).
# 2026-09-14: livenOETWordLinks and livenOETCompatibleBereanWordLinks now share
#     one Rust implementation in lib.rs; the UnboundLocalError quirk for
#     non-OT/NT books was dropped (FRT now passes through unchanged).
# 2026-11-20: getOETTidyBBB now also renames NUM, SA1/SA2, JOB, PSA, ISA, LAM,
#     EZE, OBA, HAB, ZEP and ZEC (and Title-case JOS) to match the OET-RV names,
#     and getOETBookName now returns the OET-RV name for every book that has one.
# 2026-11-20: getOETTidyBBB renames now follow the OET-RV \toc3 abbreviations for every renamed book.

import logging
import unittest

from settings import State
from Bibles import preloadVersions
from openbibledata_rust import (getBBBFromOETBookName, getGreekWordpageFilename,
                                getHebrewWordpageFilename, getOETBookName,
                                getOETTidyBBB, livenOETCompatibleBereanWordLinks,
                                livenOETWordLinks)


class TestGetOETTidyBBB(unittest.TestCase):
    """Our customised tidyBBB."""

    def test_plainCodes(self):
        self.assertEqual(getOETTidyBBB('GEN'), 'GEN')
        self.assertEqual(getOETTidyBBB('MRK'), 'MARK') # four chars allowed by default
        self.assertEqual(getOETTidyBBB('REV'), 'REV')

    def test_numberedBooks(self):
        # Default insertChar is a narrow non-breaking space
        self.assertEqual(getOETTidyBBB('KI1'), f'1\u202fKI')
        self.assertEqual(getOETTidyBBB('SA1'), f'1\u202fSHM') # renamed
        self.assertEqual(getOETTidyBBB('CO2', insertChar=' '), '2 KOR') # renamed
        self.assertEqual(getOETTidyBBB('JN3'), f'3\u202fYN') # renamed

    def test_fourCharsDisallowed(self):
        self.assertEqual(getOETTidyBBB('MRK', allowFourChars=False), 'MRK')
        self.assertEqual(getOETTidyBBB('KI1', allowFourChars=False), f'1\u202fKI')
        self.assertEqual(getOETTidyBBB('SA1', allowFourChars=False), f'1\u202fSHM') # our renames don't change

    def test_titleCase(self):
        self.assertEqual(getOETTidyBBB('GEN', titleCase=True), 'Gen')
        self.assertEqual(getOETTidyBBB('KI1', titleCase=True), f'1\u202fKi')
        self.assertEqual(getOETTidyBBB('SA1', titleCase=True), f'1\u202fShm') # renamed
        self.assertEqual(getOETTidyBBB('MRK', titleCase=True), 'Mark')
        self.assertEqual(getOETTidyBBB('TI2', titleCase=True), f'2\u202fTim')

    def test_OET_renames(self):
        """These follow the \\toc3 abbreviations in the OET-RV ESFM files."""
        for BBB, expected, expectedTitleCase in (
                ('NUM', 'CEN', 'Cen'), ('JOS', 'YEHO', 'Yeho'), ('JDG', 'H&amp;G', 'H&amp;G'),
                ('SA2', '2\u202fSHM', '2\u202fShm'), ('JOB', 'IYOV', 'Iyov'),
                ('PSA', 'SONGS', 'Songs'), ('ECC', 'REFL', 'Refl'), ('ISA', 'YESH', 'Yesh'),
                ('JER', 'YIR', 'Yir'), ('LAM', 'SOR', 'Sor'), ('EZE', 'YEHEZ', 'Yehez'),
                ('JOL', 'YOEL', 'Yoel'), ('OBA', 'OVAD', 'Ovad'), ('JNA', 'YONAH', 'Yonah'),
                ('MIC', 'MIK', 'Mik'), ('HAB', 'HAV', 'Hav'), ('ZEP', 'TSEF', 'Tsef'), ('ZEC', 'ZEK', 'Zek'),
                ('TOB', 'TOVI', 'Tovi'), ('JDT', 'YDT', 'Ydt'), ('ESG', 'ESG', 'EsG'),
                ('GES', '1\u202fES', '1\u202fEs'), ('LES', '2\u202fES', '2\u202fEs'), ('DNG', 'DAG', 'DaG'),
                ('JHN', 'YHN', 'Yhn'), ('JAM', 'YAK', 'Yak'), ('CO1', '1\u202fKOR', '1\u202fKor'),
                ('EPH', 'EFE', 'Efe'), ('PHP', 'FILI', 'Fili'), ('COL', 'KOL', 'Kol'),
                ('PHM', 'FILEM', 'Filem'), ('HEB', 'IVR', 'Ivr'), ('PE1', '1\u202fKEF', '1\u202fKef'),
                ('JN1', '1\u202fYN', '1\u202fYn'), ('JDE', 'YEHU', 'Yehu'),
                ):
            with self.subTest(BBB=BBB):
                self.assertEqual(getOETTidyBBB(BBB), expected)
                self.assertEqual(getOETTidyBBB(BBB, titleCase=True), expectedTitleCase)
                self.assertIn('<span title="', getOETTidyBBB(BBB, addNotes=True))
        self.assertEqual(getOETTidyBBB('ACT'), 'ACTs')
        # Not renamed
        for BBB in ('GEN', 'KI1', 'SNG', 'PS2', 'DAN', 'MAL', 'MAT', 'ROM', 'GAL', 'REV'):
            with self.subTest(BBB=BBB):
                self.assertNotIn('<span', getOETTidyBBB(BBB, addNotes=True))

    def test_addNotes(self):
        self.assertEqual(getOETTidyBBB('JAM', addNotes=True),
                         '<span title="Ya’akov (commonly called ‘James’)">YAK</span> (JAM)')
        self.assertEqual(getOETTidyBBB('JNA', addNotes=True),
                         '<span title="Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)">YONAH</span> (JNA)')
        self.assertEqual(getOETTidyBBB('JDE', addNotes=True),
                         '<span title="Yehudah (commonly called ‘Jude’)">YEHU</span> (JUDE)')
        self.assertEqual(getOETTidyBBB('NUM', addNotes=True),
                         '<span title="Census (commonly called ‘Numbers’)">CEN</span> (NUM)')
        self.assertEqual(getOETTidyBBB('SA1', addNotes=True),
                         '1\u202f<span title="Shmuel (which is closer to the Hebrew שְׁמוּאֵל/Shəmūʼēl)">SHM</span> (1\u202fSAM)')
        self.assertEqual(getOETTidyBBB('EZE', titleCase=True, insertChar=' ', addNotes=True),
                         '<span title="Yehezkel (which is closer to the Hebrew יְחֶזְקֵאל/Yəḩezqēʼl)">Yehez</span> (Eze)')


class TestGetOETBookName(unittest.TestCase):
    """Handle our different spelling of well-known book names."""

    def test_knownBooks(self):
        self.assertEqual(getOETBookName('GEN'), 'Genesis')
        self.assertEqual(getOETBookName('JNA'), 'Yonah/(Jonah)')
        self.assertEqual(getOETBookName('JAM'), 'Ya’akov/Jacob/(James)')
        self.assertEqual(getOETBookName('JOB'), 'Iyov/(Job)')
        self.assertEqual(getOETBookName('PSA'), 'Songs/(Psalms)')
        self.assertEqual(getOETBookName('SA2'), '2 Shmuel/(Samuel)')
        self.assertEqual(getOETBookName('MRK'), 'Markos/(Mark)')
        self.assertEqual(getOETBookName('AMO'), 'Amos')
        self.assertEqual(getOETBookName('MA1'), '1 Maccabees')

    def test_unknownBookRaises(self):
        with self.assertRaises(ValueError):
            getOETBookName('ZZZ')


class TestGetBBBFromOETBookName(unittest.TestCase):
    """Can return None; also handles punctuation and OET names."""

    def test_simpleNames(self):
        self.assertEqual(getBBBFromOETBookName('Matthew', 'test'), 'MAT')
        self.assertEqual(getBBBFromOETBookName('Genesis', 'test'), 'GEN')

    def test_punctuationRemoved(self):
        self.assertEqual(getBBBFromOETBookName('2 Kings.', 'test'), 'KI2')
        self.assertEqual(getBBBFromOETBookName('Matthew.', 'test'), 'MAT')

    def test_canReturnNone(self):
        self.assertIsNone(getBBBFromOETBookName('Songs', 'test'))
        self.assertIsNone(getBBBFromOETBookName('xyzzy', 'test'))


class TestWordpageFilenames(unittest.TestCase):
    """
    Take a word-table row number and make it into a wordpage filename.
    Uses the real word tables loaded by the State pickle data.
    """

    @classmethod
    def setUpClass(cls):
        cls._loadState()

    @staticmethod
    def _loadState():
        global state
        preloadVersions(State)
        lvBible = State.preloadedBibles['OET-LV']
        if not hasattr(State, 'OETRefData') or 'word_tables' not in State.OETRefData:
            State.OETRefData = {'word_tables': {}}
        for wordTableFilename in lvBible.ESFMWordTables:
            if lvBible.ESFMWordTables[wordTableFilename] is None:
                lvBible.loadESFMWordFile(wordTableFilename)
            State.OETRefData['word_tables'][wordTableFilename] = lvBible.ESFMWordTables[wordTableFilename]

    def test_hebrewFilename(self):
        filename = getHebrewWordpageFilename(1, State)
        self.assertRegex(filename, r'^[A-Z0-9]{2,4}c\d+v\d+w\d+\.htm$')

    def test_greekFilename(self):
        filename = getGreekWordpageFilename(1, State)
        self.assertRegex(filename, r'^[A-Z0-9]{2,4}c\d+v\d+w\d+\.htm$')

    def test_badRowNumbers(self):
        with self.assertRaises(IndexError):
            getHebrewWordpageFilename(99_999_999, State)
        with self.assertRaises(IndexError):
            getGreekWordpageFilename(-99_999_999, State)

    def test_negativeIndexing(self):
        # Python list indexing semantics are supported
        lastOTrow = len(State.OETRefData['word_tables']['OET-LV_OT_word_table.tsv']) - 1
        self.assertEqual(getHebrewWordpageFilename(lastOTrow, State),
                         getHebrewWordpageFilename(-1, State))


class TestLivenWordLinks(unittest.TestCase):
    """Livens ESFM wordlinks in the OET versions using real Bible objects."""

    @classmethod
    def setUpClass(cls):
        TestWordpageFilenames._loadState()
        cls.rvBible = State.preloadedBibles['OET-RV']
        cls.lvBible = State.preloadedBibles['OET-LV']
        logging.disable(logging.CRITICAL)  # our ports log errors via logging

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def test_levelChecked(self):
        entries = self.rvBible.getContextVerseData(('MRK', '1', '1'))[0]
        with self.assertRaises(AssertionError):
            livenOETWordLinks(0, self.rvBible, ('MRK', '1', '1'), entries, State)
        with self.assertRaises(AssertionError):
            livenOETWordLinks(9, self.rvBible, ('MRK', '1', '1'), entries, State)

    def test_refTupleMustBeTuple(self):
        entries = self.rvBible.getContextVerseData(('MRK', '1', '1'))[0]
        with self.assertRaises(TypeError):
            livenOETWordLinks(2, self.rvBible, ['MRK', '1', '1'], entries, State)

    def test_livenRVverse(self):
        entries = self.rvBible.getContextVerseData(('GAL', '1', '3'))[0]
        revisedList = livenOETWordLinks(2, self.rvBible, ('GAL', '1', '3'), entries, State)
        joinedText = ''.join(entry.getOriginalText() for entry in revisedList)
        self.assertIn('<a ', joinedText)
        self.assertIn('title="', joinedText)

    def test_livenLVverse(self):
        entries = self.lvBible.getContextVerseData(('PSA', '23', '1'))[0]
        revisedList = livenOETCompatibleBereanWordLinks(2, self.lvBible, 'PSA', entries, State)
        joinedText = ''.join(entry.getOriginalText() for entry in revisedList)
        self.assertIn('<a ', joinedText)
        self.assertIn('title="', joinedText)

    def test_bereanNonCanonicalBookPassesThrough(self):
        # Non-OT/NT books no longer raise (the old UnboundLocalError quirk is
        # gone); they fall back to the OT word table, which is never queried
        # when no entry carries a '¦' wordlink, so the list passes through.
        revisedList = livenOETCompatibleBereanWordLinks(2, self.lvBible, 'FRT', [], State)
        self.assertEqual(len(revisedList), 0)

    def test_bereanTablesComeFromState(self):
        # The native livening reads word rows from
        # state.OETRefData['word_tables'] (the same data the old decode pass
        # read), so the BibleOrgSys loadESFMWordFile-on-demand plumbing is
        # gone. ESFMWordTables is still consulted only for its length guard.
        class LazyBible:
            abbreviation = 'OET-RV'

            def __init__(self):
                self.ESFMWordTables = {'OET-LV_OT_word_table.tsv': None, 'OET-LV_NT_word_table.tsv': None}
                self.loadedFiles = []

            def loadESFMWordFile(self, filename):
                self.loadedFiles.append(filename)

        lazyBible = LazyBible()
        entries = self.rvBible.getContextVerseData(('GAL', '1', '3'))[0]
        revisedList = livenOETCompatibleBereanWordLinks(2, lazyBible, 'GAL', entries, State)
        self.assertEqual(lazyBible.loadedFiles, [])
        self.assertIn('<a ', ''.join(entry.getOriginalText() for entry in revisedList))


if __name__ == '__main__':
    unittest.main()
