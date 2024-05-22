#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# initialise.py
#
# Module handling SentenceImportance initialisation
#
# Copyright (C) 2024 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module handling SentenceImportance initialisation.

This bit of code is only ever intended to be run once

CHANGELOG:
    2023-05-22 Use VariantID and Translatable SR-GNT collation columns from CNTR
"""
from typing import List
from pathlib import Path
import logging
from csv import  DictReader

import sys
sys.path.append( '../../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint



LAST_MODIFIED_DATE = '2024-05-22' # by RJH
SHORT_PROGRAM_NAME = "SentenceImportance_initialisation"
PROGRAM_NAME = "Sentence Importance initialisation"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


TSV_FILENAME = 'sentenceImportance.tsv'
NUM_EXPECTED_DATA_LINES = 41_899

COLLATION_PATHNAME = Path( '../../../CNTR-GNT/sourceExports/collation.csv' )
NUM_EXPECTED_COLLATION_COLUMNS = 35
BOS_BOOK_ID_MAP = {
    40: 'MAT', 41: 'MRK', 42: 'LUK', 43: 'JHN', 44: 'ACT',
    45: 'ROM', 46: 'CO1', 47: 'CO2', 48: 'GAL', 49: 'EPH', 50: 'PHP', 51: 'COL', 52: 'TH1', 53: 'TH2', 54: 'TI1', 55: 'TI2', 56: 'TIT', 57: 'PHM',
    58: 'HEB', 59: 'JAM', 60: 'PE1', 61: 'PE2', 62: 'JN1', 63: 'JN2', 64: 'JN3', 65: 'JDE', 66: 'REV', 99:None}


# Default values are M2=Medium importance, 0:no textual issue, C3:clear enough
defaultImportance, defaultTextualIssue, defaultClarity = 'M', '0', 'C'
vitalRefs = ['GEN_1:1','GEN_1:2','GEN_1:3',
             'EXO_20:11', 'DEU_31:6', 'PSA_46:1',
             'PRO_3:5','PRO_3:6',
             'ISA_53:4','ISA_53:5','ISA_53:6',
             'JER_29:11',
             'MAT_6:33', 'MAT_28:19','MAT_28:20',
             'JHN_3:16','JHN_5:24','JHN_11:25',
             'ROM_3:23','ROM_6:23','ROM_8:28', 'ROM_12:2', 'CO2_5:21','CO2_12:9',
             'GAL_5:22','GAL_5:23', 'EPH_2:9',
             'PHP_4:6','PHP_4:7','PHP_4:8', 'PHP_4:13', 'TI2_3:16',
             'HEB_11:6','HEB_13:5',
             'PE1_3:15', 'PE1_5:7']
importantRefs = ['JHN_16:33']
obscureRefs = ['JOB_29:20','JOB_29:24',]
unclearRefs = ['JOB_30:6','JOB_30:7','JOB_30:11a','JOB_30:12','JOB_30:13','JOB_30:14','JOB_30:15','JOB_30:16a','JOB_30:17a','JOB_30:18','JOB_30:28a']



def run() -> bool:
    """
    """
    initialLines, collationVerseDict, splitVerseSet = load()
    create( initialLines, collationVerseDict, splitVerseSet )
# end of initalise.run()


def load():
    """
    """
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading original {TSV_FILENAME}…" )
    with open( TSV_FILENAME, 'rt', encoding='utf-8') as inputTSVFile:
        initialTSVLines = inputTSVFile.read().rstrip().split( '\n' )
    assert len(initialTSVLines) == NUM_EXPECTED_DATA_LINES, f"{NUM_EXPECTED_DATA_LINES:,=} {len(initialTSVLines):,=}"
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(initialTSVLines):,} initial lines loaded from original {TSV_FILENAME}." )

    # Find the list of verses which must be split
    splitVerseSet = set()
    for ref in vitalRefs + importantRefs + obscureRefs + unclearRefs:
        if ref[-1] in 'ab':
            splitVerseSet.add( ref[:-1] )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{len(splitVerseSet):,} verses need to be split." )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {COLLATION_PATHNAME}…" )
    with open( COLLATION_PATHNAME, 'rt', encoding='utf-8') as input_csv_file:
        csv_lines = input_csv_file.readlines()

    # Remove any BOM
    if csv_lines[0].startswith("\ufeff"):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Handling Byte Order Marker (BOM) at start of collation CSV file…")
        csv_lines[0] = csv_lines[0][1:]

    # Get the headers before we start
    collation_csv_column_headers = [header for header in csv_lines[0].strip().split(',')] # assumes no commas in headings
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Column headers: ({len(collation_csv_column_headers)}): {collation_csv_column_headers}")
    assert len(collation_csv_column_headers) == NUM_EXPECTED_COLLATION_COLUMNS, f"{len(collation_csv_column_headers)=} {NUM_EXPECTED_COLLATION_COLUMNS=}"
    # Check that the columns we use are still there somewhere
    assert 'CollationID' in collation_csv_column_headers
    assert 'VerseID' in collation_csv_column_headers
    assert 'VariantID' in collation_csv_column_headers

    # Read, check the number of columns, and summarise row contents all in one go
    collation_csv_rows = []
    dict_reader = DictReader(csv_lines)
    for n, row in enumerate(dict_reader):
        if len(row) != NUM_EXPECTED_COLLATION_COLUMNS:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Collation line {n} has {len(row)} columns instead of {NUM_EXPECTED_COLLATION_COLUMNS}!!!")
        collation_csv_rows.append(row)
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(collation_csv_rows):,} collation data lines loaded from {COLLATION_PATHNAME}." )

    collationVerseDict = {}
    last_book_number = 39 # Start here coz we only do NT
    last_chapter_number = last_verse_number = last_word_number = 0
    last_verse_id = None
    for collation_row_number, row in enumerate( collation_csv_rows ):
        assert len(row) == len(collation_csv_column_headers)

        collation_id, verse_id, variant_id = row['CollationID'], row['VerseID'], row['VariantID']
        assert len(collation_id) == 11 and collation_id.isdigit()
        assert collation_id.startswith( verse_id )
        book_number, chapter_number, verse_number, _word_number \
            = int(collation_id[:2]), int(collation_id[2:5]), int(collation_id[5:8]), int(collation_id[8:])

        # Use the original table row to put the gloss into the literal text
        if collation_id == '99999999999':
            this_verse_row_list = None
        else:
            if book_number != last_book_number:  # we've started a new book
                if book_number != 99:
                    assert book_number == last_book_number + 1
                if book_number == 99:
                    break  # all done!
                BBB = BOS_BOOK_ID_MAP[book_number]
                last_book_number = book_number

            assert len(verse_id) == 8 and verse_id.isdigit()
            if verse_id != last_verse_id:
                this_verse_row_list = get_verse_rows(collation_csv_rows, collation_row_number)
                last_verse_id = verse_id

                fgRef = f'{BBB}_{chapter_number}:{verse_number}'
                if fgRef in splitVerseSet:
                    fgRefA, fgRefB = f'{fgRef}a', f'{fgRef}b'
                    half = len(this_verse_row_list) // 2
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list[:half]:
                        if this_verse_row['VariantID']:
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRefA] = '2' if translatable else '1' if haveVariants else '0'
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list[half:]:
                        if this_verse_row['VariantID']:
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRefB] = '2' if translatable else '1' if haveVariants else '0'
                else: # no split
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list:
                        if this_verse_row['VariantID']:
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRef] = '2' if translatable else '1' if haveVariants else '0'

    return initialTSVLines, collationVerseDict, splitVerseSet
# end of initalise.load()


def get_verse_rows(given_collation_rows: List[dict], row_index: int) -> List[list]:
    """
    row_index should be the index of the first row for the particular verse

    Returns a list of rows for the verse
    """
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"get_verse_rows({row_index})")
    this_verse_row_list = []
    this_verseID = given_collation_rows[row_index]['VerseID']
    if row_index > 0: assert given_collation_rows[row_index-1]['VerseID'] != this_verseID
    for ix in range(row_index, len(given_collation_rows)):
        row = given_collation_rows[ix]
        if row['VerseID'] == this_verseID:
            this_verse_row_list.append(row)
        else: # done
            break
    return this_verse_row_list
# end of extract_VLT_NT_to_ESFM.get_verse_rows


def create( initialTSVLines, collationVerseDict, splitVerseSet ) -> bool:
    """
    """
    BibleOrgSysGlobals.backupAnyExistingFile( TSV_FILENAME, numBackups=3 )

    numLinesWritten = 0
    with open( TSV_FILENAME, 'wt', encoding='utf-8') as outputFile:
        outputFile.write( "FGRef\tImportance\tTextualIssue\tClarity\n")
        numLinesWritten += 1
        for line in initialTSVLines:
            UUU = line.split(' ')[0]
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( UUU )
            fgRef = f'{BBB}_{line[4:]}'
            # print( f"{line=} {fgRef=}" )
            subRefs = [f'{fgRef}a',f'{fgRef}b'] if fgRef in splitVerseSet else [fgRef]

            for subRef in subRefs: # either one or two lines per verse
                importance, clarity = defaultImportance, defaultClarity
                textualIssue = collationVerseDict[subRef] if subRef in collationVerseDict else defaultTextualIssue

                if subRef in vitalRefs:
                    importance = 'V' # vital = 4/4
                    vitalRefs.remove( subRef )
                elif subRef in importantRefs:
                    importance = 'I' # important = 3/4
                    importantRefs.remove( subRef )
                if subRef in obscureRefs:
                    clarity = 'O' # obscure = 1/3
                    obscureRefs.remove( subRef )
                elif subRef in unclearRefs:
                    clarity = 'U' # unclear = 2/3
                    unclearRefs.remove( subRef )

                outputFile.write( f"{subRef}\t{importance}\t{textualIssue}\t{clarity}\n" )
                numLinesWritten += 1

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {numLinesWritten:,} lines written to {TSV_FILENAME}." )
    assert numLinesWritten == 1+NUM_EXPECTED_DATA_LINES+len(splitVerseSet), f"{NUM_EXPECTED_DATA_LINES=:,} {len(splitVerseSet)=:,} {numLinesWritten=:,}"
    assert len(vitalRefs) == 0, f"({len(vitalRefs)}) {vitalRefs=}" # They should all have been used
    assert len(importantRefs) == 0, f"({len(importantRefs)}) {importantRefs=}" # They should all have been used
    assert len(obscureRefs) == 0, f"({len(obscureRefs)}) {obscureRefs=}" # They should all have been used
    assert len(unclearRefs) == 0, f"({len(unclearRefs)}) {unclearRefs=}" # They should all have been used

    return True
# end of initalise.create()


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    run()
# end of initalise.briefDemo()

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    run()
# end of initalise.fullDemo()

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of initalise.py
