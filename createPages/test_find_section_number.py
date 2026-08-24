#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_find_section_number.py
#
# Tests for findSectionNumber -- now a Rust PyO3 implementation
# (openbibledata_rust.findSectionNumber / Rust/src/section_numbers.rs)
# with a thin Python wrapper left in createSectionPages.py.
#
# The tests cross-check the Rust implementation against an inline copy of the
# original Python search loop to guarantee identical behaviour.

import unittest

from bible_organisational_system import getSmallLeadingInt
from settings import State
from openbibledata_rust import findSectionNumber


def makeSectionsList( sectionSpecTuples ):
    """
    Build sectionsListsForSections-style entries
        (n,startC,startV,endC,endV,sectionName,reasonMarker,contextList,verseEntryList,filename)
    from simple (startC,startV,endC,endV,reasonMarker) tuples.
    """
    return [(n, startC, startV, endC, endV, f'Section name {n}', reasonMarker, [], [], f'BKB_S{n}.htm')
            for n,(startC, startV, endC, endV, reasonMarker) in enumerate( sectionSpecTuples )]


def referenceImplementation( sectionsList, refC, refV ):
    """
    Inline copy of the ORIGINAL Python search loop from
    createSectionPages.findSectionNumber (before the Rust conversion)
        -- used to check that the Rust port behaves identically.
    """
    if refV == '0':
        refV = '1'
    intRefV = getSmallLeadingInt( refV )

    for n,entry in enumerate( sectionsList ):
        startC,startV,endC,endV = entry[1],entry[2],entry[3],entry[4]
        reasonName = entry[6]
        if reasonName.startswith( 'Alternate ' ): continue # ignore these ones

        if startC==refC and endC==refC: # This section only spans a single chapter (or part of a chapter)
            if getSmallLeadingInt(startV) <= intRefV <= getSmallLeadingInt(endV): # It's in this single chapter
                return n
        else: # This section spans two or more chapters
            if startC==refC and intRefV>=getSmallLeadingInt(startV): # It's in the first chapter
                return n
            elif endC==refC and intRefV<=getSmallLeadingInt(endV): # It's in the last chapter
                return n
            elif int(startC) < int(refC) < int(endC): # It's in one of the middle chapters
                return n

    return None


# Simple one-section-per-chapter book (like GEN has 31:25, 2:25, 3:10)
SINGLE_CHAPTER_SECTIONS = makeSectionsList( [
                        ('1', '1', '1', '31', 's1'),
                        ('2', '1', '2', '25', 's1'),
                        ('3', '1', '3', '10', 's1'),
                    ] )

# A more complex book with introduction, multi-chapter sections,
# and alternate headings that must be skipped but keep their index
COMPLEX_SECTIONS = makeSectionsList( [
                        ('-1', '0', '-1', '12', 'Headers'),
                        ('-1', '14', '-1', '30', 'is1'),
                        ('1', '1', '2', '25', 's1/c'),
                        ('1', '5', '1', '99', 'Alternate section heading'),
                        ('3', '10', '4', '20', 's1'),
                    ] )


class TestFindSectionNumberBasics(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = False # Avoid defaulting missing books to the introduction
        self.state.sectionsListsForSections = {
            'TST': { 'GEN': SINGLE_CHAPTER_SECTIONS, 'DAN': COMPLEX_SECTIONS } }


    def test_empty_bbb_returns_none(self):
        """No refBBB parameter given can't produce a result"""
        self.assertIsNone( findSectionNumber( 'TST', '', '1', '1', self.state ) )


    def test_noncanonical_book_without_apocrypha_version_returns_none(self):
        """A deuterocanonical book is refused for versions without apocrypha"""
        self.assertIsNone( findSectionNumber( 'TST', 'TOB', '1', '1', self.state ) )
        self.assertIsNone( findSectionNumber( 'TST', 'JDT', '3', '7', self.state ) )


    def test_apocrypha_version_allows_deuterocanonical_books(self):
        """A version with apocrypha proceeds even for deuterocanonical books"""
        self.state.sectionsListsForSections['DRA'] = { 'TOB': makeSectionsList([('1','1','1','22','s1')]) }
        self.assertEqual( findSectionNumber( 'DRA', 'TOB', '1', '5', self.state ), 0 )
        # Still no sectionsLists for this version's TOB -> None (not a refusal)
        self.assertIsNone( findSectionNumber( 'DRA', 'MAN', '1', '1', self.state ) )


    def test_missing_version_raises_key_error(self):
        """An unknown version abbreviation raises KeyError (as the Python code always did)"""
        with self.assertRaises( KeyError ):
            findSectionNumber( 'NOPE', 'GEN', '1', '1', self.state )


    def test_missing_book_returns_none_outside_test_mode(self):
        """No sectionsLists for a book returns None when not in TEST_MODE"""
        self.assertIsNone( findSectionNumber( 'TST', 'MRK', '1', '1', self.state ) )


    def test_missing_book_defaults_to_introduction_in_test_mode(self):
        """In TEST_MODE_FLAG mode, a missing book defaults to the introduction (section 0)"""
        self.state.TEST_MODE_FLAG = True
        self.assertEqual( findSectionNumber( 'TST', 'MRK', '1', '1', self.state ), 0 )


class TestFindSectionNumberMatching(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.sectionsListsForSections = {
            'TST': { 'GEN': SINGLE_CHAPTER_SECTIONS, 'DAN': COMPLEX_SECTIONS } }


    def test_single_chapter_sections(self):
        self.assertEqual( findSectionNumber( 'TST', 'GEN', '1', '15', self.state ), 0 )
        self.assertEqual( findSectionNumber( 'TST', 'GEN', '1', '31', self.state ), 0 )
        self.assertEqual( findSectionNumber( 'TST', 'GEN', '2', '25', self.state ), 1 )
        self.assertEqual( findSectionNumber( 'TST', 'GEN', '3', '1', self.state ), 2 )


    def test_single_chapter_misses(self):
        self.assertIsNone( findSectionNumber( 'TST', 'GEN', '1', '32', self.state ) )
        self.assertIsNone( findSectionNumber( 'TST', 'GEN', '9', '9', self.state ) )

    def test_verse_zero_is_adjusted_to_verse_one(self):
        self.assertEqual( findSectionNumber( 'TST', 'GEN', '2', '0', self.state ), 1 )


    def test_multi_chapter_first_last_and_middle(self):
        # DAN sections: (-1:0--1:12), (-1:14--1:30), (1:1-2:25 s1/c),
        #               (skipped Alternate), (3:10-4:20 s1)
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '-1', '5', self.state ), 0 )
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '-1', '20', self.state ), 1 )
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '1', '1', self.state ), 2 ) # First chapter
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '2', '25', self.state ), 2 ) # Last chapter
        # Note: the first-chapter rule (intRefV >= startV) has no upper limit,
        # exactly like the original Python code
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '1', '30', self.state ), 2 )
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '3', '15', self.state ), 4 ) # Not 3 -- that's the skipped Alternate entry
        self.assertEqual( findSectionNumber( 'TST', 'DAN', '4', '20', self.state ), 4 )
        self.assertIsNone( findSectionNumber( 'TST', 'DAN', '4', '21', self.state ) )


class TestFindSectionNumberPythonWrapper(unittest.TestCase):
    def setUp(self):
        from createSectionPages import findSectionNumber as pythonWrapped
        self.wrappedFindSectionNumber = pythonWrapped
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.sectionsListsForSections = {
            'TST': { 'GEN': SINGLE_CHAPTER_SECTIONS, 'DAN': COMPLEX_SECTIONS } }


    def test_python_wrapper_delegates_to_rust(self):
        """createSectionPages.findSectionNumber still works (delegates to Rust)"""
        self.assertEqual( self.wrappedFindSectionNumber( 'TST', 'GEN', '1', '15', self.state ), 0 )
        self.assertEqual( self.wrappedFindSectionNumber( 'TST', 'DAN', '-1', '20', self.state ), 1 )
        self.assertIsNone( self.wrappedFindSectionNumber( 'TST', 'GEN', '1', '99', self.state ) )
        self.assertIsNone( self.wrappedFindSectionNumber( 'TST', '', '1', '1', self.state ) )


class TestRustMatchesReferenceImplementation(unittest.TestCase):
    """
    Exhaustively compare the Rust implementation against an inline copy of the
    original Python algorithm over grids of chapter/verse references.
    """
    VERSES = ('0','1','4','5','10','11','13','14','21','24','25','26','29','30','31','32','99')
    CHAPTERS = ('-1','0','1','2','3','4','5')


    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = False
        self.state.sectionsListsForSections = {
            'TST': { 'GEN': SINGLE_CHAPTER_SECTIONS, 'DAN': COMPLEX_SECTIONS } }


    def test_parity_on_single_chapter_sections(self):
        for refC in self.CHAPTERS:
            for refV in self.VERSES:
                expected = referenceImplementation( SINGLE_CHAPTER_SECTIONS, refC, refV )
                self.assertEqual( findSectionNumber( 'TST', 'GEN', refC, refV, self.state ),
                                  expected, f'GEN {refC}:{refV}' )


    def test_parity_on_complex_sections(self):
        for refC in self.CHAPTERS:
            for refV in self.VERSES:
                expected = referenceImplementation( COMPLEX_SECTIONS, refC, refV )
                self.assertEqual( findSectionNumber( 'TST', 'DAN', refC, refV, self.state ),
                                  expected, f'DAN {refC}:{refV}' )


if __name__ == '__main__':
    unittest.main()
# end of test_find_section_number.py
