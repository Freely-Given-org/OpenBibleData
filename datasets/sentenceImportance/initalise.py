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

CHANGELOG:
    2023-03-23 Not sure why unicodedata.name(LF) fails, but catch it now
"""
from pathlib import Path
import logging
from csv import  DictReader

import sys
sys.path.append( '../../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint



LAST_MODIFIED_DATE = '2024-05-21' # by RJH
SHORT_PROGRAM_NAME = "SentenceImportance_initialisation"
PROGRAM_NAME = "Sentence Importance initialisation"
PROGRAM_VERSION = '0.01'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

TSV_FILENAME = 'sentenceImportance.tsv'
NUM_EXPECTED_DATA_LINES = 41_899

# Default values are M2=Medium importance, 0:no textual issue, C3:clear enough
defaultImportance, defaultTextualIssue, defaultClarity = 'M', '0', 'C'
vitalRefs = ['GEN_1:1','GEN_1:2','GEN_1:3', 'EXO_20:11', 'DEU_31:6', 'PSA_46:1', 'PRO_3:5','PRO_3:6', 'ISA_53:4','ISA_53:5','ISA_53:6', 'JER_29:11', 'MAT_6:33', 'MAT_28:19','MAT_28:20', 'JHN_3:16','JHN_5:24','JHN_11:25', 'ROM_3:23','ROM_6:23','ROM_8:28', 'ROM_12:2', 'CO2_5:21','CO2_12:9', 'GAL_5:22','GAL_5:23', 'EPH_2:9', 'PHP_4:6','PHP_4:7','PHP_4:8', 'PHP_4:13', 'TI2_3:16', 'HEB_11:6','HEB_13:5', 'PE1_3:15', 'PE1_5:7']
importantRefs = ['JHN_16:33']



def init() -> bool:
    """
    """
    with open( TSV_FILENAME, 'rt', encoding='utf-8') as inputFile:
        initialTSVLines = inputFile.read().rstrip().split( '\n' )
    assert len(initialTSVLines) == NUM_EXPECTED_DATA_LINES, f"{NUM_EXPECTED_DATA_LINES:,=} {len(initialTSVLines):,=}"

    BibleOrgSysGlobals.backupAnyExistingFile( TSV_FILENAME, numBackups=3 )

    numLinesWritten = 0
    with open( TSV_FILENAME, 'wt', encoding='utf-8') as outputFile:
        outputFile.write( "FGRef\tImportance\tTextualIssue\tClarity\n")
        numLinesWritten += 1
        for line in initialTSVLines:
            UUU = line.split(' ')[0]
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( UUU )
            fgRef = f'{BBB}_{line[4:]}'
            print( f"{line=} {fgRef=}" )

            importance, textualIssue, clarity = defaultImportance, defaultTextualIssue, defaultClarity
            if fgRef in vitalRefs:
                importance = 'V' # vital = 4
                vitalRefs.remove( fgRef )
            elif fgRef in importantRefs:
                importance = 'I' # important = 3
                importantRefs.remove( fgRef )

            outputFile.write( f"{fgRef}\t{importance}\t{textualIssue}\t{clarity}\n" )
            numLinesWritten += 1
    assert numLinesWritten == NUM_EXPECTED_DATA_LINES+1, f"{NUM_EXPECTED_DATA_LINES=:,} {numLinesWritten=:,}"
    assert len(vitalRefs) == 0, f"({len(vitalRefs)}) {vitalRefs=}" # They should all have been used
    assert len(importantRefs) == 0, f"({len(importantRefs)}) {importantRefs=}" # They should all have been used

    return True
# end of load_transliteration_table()



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    init()
# end of BibleTransliterations.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    init()
# end of BibleTransliterations.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleTransliterations.py
