#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# test_createSectionIndexParagraphs.py
#
# Copyright (C) 2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal. 
#    To view a copy of this license, visit http://creativecommons.org

"""
Regression tests for createNonOETSectionIndexParagraphs (the builder that creates
the '<Index of sections>' <p class=…> links for non-OET Bible versions such as BSB).

Historical note (2026-09-05): the old inline 'else' loop in createSectionPages
unpacked each entry's own section filename into a variable called `indexFilename`
but then linked using a *stale* `sectionFilename` left over from the section-page
creation loop -- which still held the FINAL section's filename (e.g. MRK_S96.htm).
The result was that every line of e.g. BSB/bySec/MRK.htm linked to MRK_S96.htm.

That logic was extracted into this helper so it can be unit-tested against synthetic
sectionsListsForSections data without needing a full site build (see repro_rel.py and
test_find_section_number.py for the same minimal-state pattern).

CHANGELOG:
    2026-09-05 Created to lock down the per-section linking behaviour.
"""

import unittest

from settings import State
from createSectionPages import createNonOETSectionIndexParagraphs


def makeSectionsList( sectionSpecTuples ):
    """
    Build sectionsListsForSections-style entries
        (n,startC,startV,endC,endV,sectionName,reasonMarker,contextList,verseEntryList,filename)
    from simple (startC,startV,endC,endV,reasonMarker,filename) tuples.
    """
    return [(n, startC, startV, endC, endV, f'Section name {n}', reasonMarker, [], [], filename)
            for n,(startC, startV, endC, endV, reasonMarker, filename) in enumerate( sectionSpecTuples )]


# BSB-style MARK data with explicit, deliberately NON-sequential filenames
# (mirrors reality where MRK has ~90+ section files);
#   the last entry exercises the old stale-`sectionFilename` bug.
MARK_SECTIONS = makeSectionsList( [
                        ('-1', '0',  '-1', '12', 'Headers', 'MRK_S0.htm'),
                        ('1',  '1',  '1',  '11', 's1/c',    'MRK_S1.htm'),
                        ('1',  '12', '1',  '15', 's1',      'MRK_S2.htm'),
                        ('1',  '16', '16', '20', 's1/c',    'MRK_SLAST.htm'),
                    ] )


class TestNonOETSectionIndexParagraphs(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = True # Report the '(Section heading)' appendages


    def paragraphs( self ):
        return createNonOETSectionIndexParagraphs( MARK_SECTIONS, self.state )


    def test_each_paragraph_links_to_its_own_section_page(self):
        """Every index entry must link to the section file named in ITS OWN tuple."""
        expectedLinks = ['MRK_S0.htm#Top', 'MRK_S1.htm#Top', 'MRK_S2.htm#Top', 'MRK_SLAST.htm#Top']
        for paragraph, expectedLink in zip( self.paragraphs(), expectedLinks ):
            self.assertIn( f'href="{expectedLink}"', paragraph )


    def test_no_paragraph_links_to_a_different_sections_file(self):
        """Regression: none of the entries may be hijacked to the LAST section's file."""
        paragraphs = self.paragraphs()
        self.assertNotIn( 'MRK_SLAST.htm', paragraphs[0] )
        self.assertNotIn( 'MRK_SLAST.htm', paragraphs[1] )
        self.assertNotIn( 'MRK_SLAST.htm', paragraphs[2] )
        self.assertNotIn( 'MRK_S1.htm', paragraphs[0] )
        self.assertNotIn( 'MRK_S0.htm', paragraphs[3] )


    def test_intro_section_is_labeled_intro(self):
        self.assertTrue( self.paragraphs()[0].startswith( '<p class="alternativeHeading"' )
                         or self.paragraphs()[0].startswith( '<p class="alternateHeading"' ) )
        self.assertIn( 'Intro:0', self.paragraphs()[0] )


    def test_reason_marker_is_normalised_to_a_heading_name(self):
        """The raw marker (e.g. 's1/c') must be shown as a descriptive reason name."""
        para2 = self.paragraphs()[2]
        self.assertNotIn( '(s1)', para2 )
        self.assertIn( '(Section heading)', para2 )


    def test_headers_marker_is_shown_as_headers(self):
        self.assertIn( '(Headers)', self.paragraphs()[0] )


    def test_section_heading_class_for_section_reasons(self):
        self.assertIn( 'class="sectionHeading"', self.paragraphs()[1] )
        self.assertIn( 'class="sectionHeading"', self.paragraphs()[2] )


    def test_non_section_reasons_get_alternate_heading_class(self):
        self.assertIn( 'class="alternateHeading"', self.paragraphs()[0] )


    def test_section_heading_reason_suppressed_outside_test_mode(self):
        """In production ((TEST_MODE_FLAG off) the '(Section heading)' text is suppressed."""
        self.state.TEST_MODE_FLAG = False
        para2 = self.paragraphs()[2]
        self.assertIn( '<b>Section name 2</b>', para2 )
        self.assertNotIn( '(Section heading)', para2 )
        # ...but more specific reasons like '(Headers)' are still shown
        self.assertIn( '(Headers)', self.paragraphs()[0] )


class TestNonOETSectionIndexParagraphsEmpty(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.state.TEST_MODE_FLAG = False


    def test_empty_sections_list_gives_no_paragraphs(self):
        self.assertEqual( createNonOETSectionIndexParagraphs( [], self.state ), [] )


if __name__ == '__main__':
    unittest.main()
# end of test_createSectionIndexParagraphs.py