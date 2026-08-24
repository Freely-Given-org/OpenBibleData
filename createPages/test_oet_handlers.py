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
        self.assertEqual(getOETTidyBBB('SA1'), f'1\u202fSAM')
        self.assertEqual(getOETTidyBBB('CO2', insertChar=' '), '2 COR')
        self.assertEqual(getOETTidyBBB('JN3'), f'3\u202fYHN') # renamed after tidying

    def test_fourCharsDisallowed(self):
        self.assertEqual(getOETTidyBBB('MRK', allowFourChars=False), 'MRK')
        self.assertEqual(getOETTidyBBB('SA1', allowFourChars=False), f'1\u202fSA')

    def test_titleCase(self):
        self.assertEqual(getOETTidyBBB('GEN', titleCase=True), 'Gen')
        self.assertEqual(getOETTidyBBB('SA1', titleCase=True), f'1\u202fSam')
        self.assertEqual(getOETTidyBBB('MRK', titleCase=True), 'Mark')

    def test_OET_renames(self):
        self.assertEqual(getOETTidyBBB('JNA'), 'YNA')
        self.assertEqual(getOETTidyBBB('JHN'), 'YHN')
        self.assertEqual(getOETTidyBBB('JOHN'), 'YHN')  # even this spelling
        self.assertEqual(getOETTidyBBB('JAM'), 'YAC')
        self.assertEqual(getOETTidyBBB('ACTS'), 'ACTs')
        self.assertEqual(getOETTidyBBB('JDE'), 'YUD')
        self.assertEqual(getOETTidyBBB('JN1'), f'1\u202fYHN') # JN1 tidies to 1 JHN, then renamed
        self.assertEqual(getOETTidyBBB('TI2', titleCase=True), f'2\u202fTim')

    def test_addNotes(self):
        self.assertEqual(getOETTidyBBB('JAM', addNotes=True), 'YAC (JAM)')
        self.assertEqual(getOETTidyBBB('JNA', addNotes=True),
                         '<span title="Yonah (which is closer to the Hebrew יוֹנָה/Yōnāh)">YNA</span> (JNA)')
        self.assertEqual(getOETTidyBBB('JDE', addNotes=True),
                         '<span title="Yudas (which is closer to the Greek Ἰούδας/Youdas)">YUD</span> (JUD)')


class TestGetOETBookName(unittest.TestCase):
    """Handle our different spelling of well-known book names."""

    def test_knownBooks(self):
        self.assertEqual(getOETBookName('GEN'), 'Genesis')
        self.assertEqual(getOETBookName('JNA'), 'Yonah/(Jonah)')
        self.assertEqual(getOETBookName('JAM'), 'Yacob/Jacob/(James)')
        self.assertEqual(getOETBookName('JOB'), 'Iyyov/(Job)')
        self.assertEqual(getOETBookName('PSA'), 'Songs/(Psalms)')

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

    def test_bereanInvalidBookUnbound(self):
        # Faithfully replicates the Python UnboundLocalError for non-OT/NT books
        entries = self.rvBible.getContextVerseData(('MRK', '1', '1'))[0]
        with self.assertRaises(UnboundLocalError):
            livenOETCompatibleBereanWordLinks(2, self.lvBible, 'FRT', entries, State)

    def test_bereanLoadsTablesOnDemand(self):
        class LazyBible:
            abbreviation = 'OET-RV'

            def __init__(self):
                self.ESFMWordTables = {'OET-LV_OT_word_table.tsv': None, 'OET-LV_NT_word_table.tsv': None}
                self.loadedFiles = []

            def loadESFMWordFile(self, filename):
                self.loadedFiles.append(filename)
                self.ESFMWordTables[filename] = self.lvBible.ESFMWordTables[filename]
                columnNames = getattr(self, 'ESFMColumnNameList', {})
                columnNames[filename] = self.ESFMWordTables[filename][0].split('\t')
                self.ESFMColumnNameList = columnNames

        lazyBible = LazyBible()
        lazyBible.lvBible = self.lvBible
        entries = self.rvBible.getContextVerseData(('GAL', '1', '3'))[0]
        revisedList = livenOETCompatibleBereanWordLinks(2, lazyBible, 'GAL', entries, State)
        self.assertEqual(lazyBible.loadedFiles, ['OET-LV_NT_word_table.tsv'])
        self.assertIn('<a ', ''.join(entry.getOriginalText() for entry in revisedList))


if __name__ == '__main__':
    unittest.main()
