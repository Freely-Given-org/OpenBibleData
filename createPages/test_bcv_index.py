#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_bcv_index.py
#
# Verifies that the Rust build_word_table_index (openbibledata_rust)
# produces exactly the same dict as the original Python loop in createSitePages.py.

import unittest

from openbibledata_rust import build_word_table_index


def oldPythonIndex( wordTable: list ) -> dict:
    """The original loop, pasted from createSitePages.py."""
    index = {}
    lastBCVref = None
    startIx = 1
    for n, columns_string in enumerate( wordTable[1:], start=1 ):
        wordRef = columns_string.split( '\t', 1 )[0] # Something like 'MAT_1:1w1'
        BCVref = wordRef.split( 'w', 1 )[0] # Something like 'MAT_1:1'
        if BCVref != lastBCVref:
            if lastBCVref is not None:
                index[lastBCVref] = (startIx, n-1)
            startIx = n
            lastBCVref = BCVref
    if lastBCVref is not None:
        index[lastBCVref] = (startIx, n) # Save the final one
    return index


WORD_TABLE = [
    'Ref\tRowType\tMorphemeRowList', # header row 0 (skipped)
    'MAT_1:1w1\tA\tx',
    'MAT_1:1w2\tA\ty',
    'MAT_1:2w1\tB\tz',
    'MAT_1:2w2\tB\tu',
    'MAT_1:2w3\tB\tv',
    'PHP_2:9w1\tC\tw',
    'PHP_2:9w2\tC\ts',
]


class TestBCVIndex(unittest.TestCase):
    def test_matches_old_python_loop(self):
        self.assertEqual( build_word_table_index( WORD_TABLE ), oldPythonIndex( WORD_TABLE ) )
        self.assertEqual( build_word_table_index( WORD_TABLE ), {
            'MAT_1:1': (1, 2),
            'MAT_1:2': (3, 5),
            'PHP_2:9': (6, 7),
        } )

    def test_ref_without_w(self):
        rows = ['Ref\tRowType', 'FRT_0\tA', 'FRT_0\tB']
        self.assertEqual( build_word_table_index( rows ), oldPythonIndex( rows ) )

    def test_empty_data_rows(self):
        rows = ['Ref\tRowType']
        self.assertEqual( build_word_table_index( rows ), oldPythonIndex( rows ) )
        self.assertEqual( build_word_table_index( rows ), {} )


if __name__ == '__main__':
    unittest.main()
