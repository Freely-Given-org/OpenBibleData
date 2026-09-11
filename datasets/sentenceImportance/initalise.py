#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2024 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# initialise.py
#
# Module handling SentenceImportance initialisation
#
# Copyright (C) 2024-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal. 
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling SentenceImportance initialisation.

This bit of code is only ever intended to be run once

Sets:
    Importance
        V   Vital
        I   Important
        M   Medium (default)
        T   Trivial
    TextualIssue
        0   None (default)
        1   Spelling differences
        2   Small word differences
        3   Major issues 
    Clarity
        C   Clear (default)
        U   Unclear
        O   Obscure
    Speakers
        @   Narrator (default)
        Otherwise there's a comma-separated list of names, e.g. 'Yeshua' or '@,Yahweh'

TODO: Define what versification these references are in

CHANGELOG:
    2024-05-22 Use SR and Translatable SR-GNT collation columns from CNTR
    2025-04-10 Use crossTestamentQuotes info
    2025-07-09 Tried to make more allowance for partial verses
    2025-09-11 Find Q footnotes in UHB
    2025-10-13 Find appropriate footnotes in OSHB via OET-LV OT files
    2026-01-05 Handle a range crossing a chapter boundary (using en-dash –)
    2026-03-29 Updated for latest collation DB from GreekCNTR
    2026-09-08 Added Speakers column to the output (auto-detected from OET-RV \\wj markers, \\sp speaker markers, and speech attribution patterns)
"""
from pathlib import Path
from csv import  DictReader
import re
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.USXXMLBible as USXXMLBible
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
import bos_books_codes_py

import sys
sys.path.append( '../crossTestamentQuotes/' )
from load import getIndividualQuotedOTRefs, getIndividualQuotingNTRefs



LAST_MODIFIED_DATE = '2026-09-10' # by RJH
SHORT_PROGRAM_NAME = "SentenceImportance_initialisation"
PROGRAM_NAME = "Sentence Importance initialisation"
PROGRAM_VERSION = '0.30'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


TSV_FILENAME = 'sentenceImportance.tsv'
NUM_EXPECTED_DATA_LINES = 41_899 # for initial vref.txt file with no split verses

COLLATION_PATHNAME = Path( '../../../CNTR-GNT/sourceExports/collation.csv' )
NUM_EXPECTED_COLLATION_COLUMNS = 30
BOS_BOOK_ID_MAP = {
    40: 'MAT', 41: 'MRK', 42: 'LUK', 43: 'JHN', 44: 'ACT',
    45: 'ROM', 46: 'CO1', 47: 'CO2', 48: 'GAL', 49: 'EPH', 50: 'PHP', 51: 'COL', 52: 'TH1', 53: 'TH2', 54: 'TI1', 55: 'TI2', 56: 'TIT', 57: 'PHM',
    58: 'HEB', 59: 'JAM', 60: 'PE1', 61: 'PE2', 62: 'JN1', 63: 'JN2', 64: 'JN3', 65: 'JDE', 66: 'REV', 99:None}

UHB_PATHNAME = Path( '../../copiedBibles/Original/unfoldingWord.org/UHB/' )
OET_LV_OT_PATHNAME = Path( '../../../OpenEnglishTranslation--OET/derivedTexts/auto_edited_OT_ESFM/' )
NET_PATHNAME = Path( '../../copiedBibles/English/NET/' )
OET_RV_PATHNAME = Path( '../../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/' )


# Default values are M2=Medium/normal importance, 0:no textual issue, C3:clear enough
defaultImportance, defaultTextualIssue, defaultClarity = 'M', '0', 'C'

# Speakers column: the default '@' represents the narrator (i.e., no particular speaker).
# Otherwise the column has names separated by commas, e.g. 'Yeshua' or '@,Yahweh'.
speakersDefault = '@'
vitalImportanceRefsWithRanges = [ # Often in doctrinal statements
    'GEN_1:1-3', 'GEN_3:16',
    'EXO_20:11',
    'DEU_4:6', 'DEU_6:4-5', 'DEU_9:4', 'DEU_31:6',
    'CH2_7:14',
    'PSA_22:1-2','PSA_22:7-18', 'PSA_46:1',
    'PRO_3:5','PRO_3:6',
    'ISA_9:6-7',
    'ISA_52:13–53:12', # The fourth and best-known servant song
    'ISA_55:11',
    'JER_29:11-13',
    'DAN_7:13-14',
    'MIC_5:2','MIC_6:8',
    'ZEC_12:10',
    'MAL_3:8-10',

    'MAT_6:33', 'MAT_24:35', 'MAT_28:19-20',
    'JHN_3:16','JHN_5:24','JHN_11:25','JHN_20:31',

    'ROM_3:23','ROM_6:23','ROM_8:28', 'ROM_12:2',
    'CO2_5:21','CO2_12:9',
    'GAL_3:10','GAL_3:13-14','GAL_5:22-23', 'EPH_2:9',
    'PHP_4:6-8', 'PHP_4:13',
    'TI2_3:16-17',

    'HEB_11:6','HEB_13:5',
    'PE1_3:15', 'PE1_5:7',
    'PE2_1:19-21',

    'JN1_5:11-13',
    ]
for ref in vitalImportanceRefsWithRanges:
    assert ref.count( '_' ) == 1, f"vitalImportanceRefsWithRanges {ref=}"

importantRefsWithRanges = [ # Often quoted and/or memorised by Christians
    'GEN_1:4-31', # Gen 1:1-3 is above
        'GEN_2:1-3', 'GEN_12:3',
    'DEU_29:24-29', 'DEU_30:3-5','DEU_30:19',
    'JOS_1:9',
    'EST_4:14',
    'PSA_9:17', 'PSA_23:1-6', 'PSA_51:5','PSA_51:10', 'PSA_119:89',
    'PRO_1:7', 'PRO_4:1-7', 'PRO_14:34',
    'ECC_8:15',
    'ISA_2:2-4','ISA_6:1-8','ISA_11:1-12','ISA_27:6','ISA_28:16','ISA_41:10', 'ISA_46:9-10',
    'ISA_42:1-9', 'ISA_48:12-13','ISA_48:16', 'ISA_49:1-13', 'ISA_50:4-11', # The other three servant songs 'ISA_52:13–53:12',
    'ISA_54:17', 'ISA_55:1-10','ISA_55:12-13', 'ISA_66:8',
    'JER_17:9', 'JER_23:5-6', 'JER_31:31-34', 'JER_33:2-3', 'JER_33:14-18',
    'DAN_7:10', 'DAN_9:5','DAN_9:19','DAN_9:24', 'DAN_12:1','DAN_12:4',
    'ZEC_12:8-9','ZEC_12:11',

    'MAT_4:4', 'MAT_16:1-3', 'MAT_24:32-33','MAT_24:44',
    'LUK_21:28','LUK_24:27',
    'JHN_1:1-18','JHN_3:18','JHN_6:68-69','JHN_7:16', 'JHN_8:36','JHN_8:58', 'JHN_10:28','JHN_16:33', 'JHN_17:5','JHN_17:23',
    'ACT_2:42',
    'CO1_10:6-11',
    'ROM_3:3-4','ROM_3:19-22', 'ROM_5:8','ROM_5:16-21', 'ROM_10:2','ROM_10:13', 'ROM_13:12', 'ROM_15:4', 'ROM_16:17',
    'CO1_2:12','CO1_2:14', 'CO1_3:14-15',
    'CO2_9:7',
    'GAL_3:21-22','GAL_3:24', 'GAL_6:16',
    'EPH_2:8','EPH_2:10', 'EPH_4:14','EPH_6:4','EPH_6:10-13','EPH_6:17',
    'PHP_2:12-13', 'PHP_3:20-21',
    'COL_3:2',
    'TH1_1:10','TH1_4:16-17','TH1_5:9',
    'TH2_2:9-12',
    'TI1_4:13','TI1_4:16','TI1_6:3',
    'TI2_2:15','TI2_4:3-4',
    'TIT_1:9','TIT_2:1',
    'HEB_4:12-13', 'HEB_5:12-14', 'HEB_13:9',
    'JAM_1:5',
    'PE1_2:2', 'PE1_2:9-10',
    'PE2_3:10','PE2_3:15-16',
    'JN1_2:19', 'JN1_4:1','JN1_4:4',
    'JN2_1:9',
    'REV_1:17-18', 'REV_3:5', 'REV_13:7', 'REV_20:12','REV_20:15',
    ]
for ref in importantRefsWithRanges:
    assert ref.count( '_' ) == 1, f"importantRefsWithRanges {ref=}"

listsOfNames = ['KI1_4:2','KI1_4:3','KI1_4:4','KI1_4:5','KI1_4:6',
                'KI1_4:8','KI1_4:9','KI1_4:10','KI1_4:11','KI1_4:12','KI1_4:13','KI1_4:14','KI1_4:15','KI1_4:16','KI1_4:17','KI1_4:18','KI1_4:19',
                ]
for ref in listsOfNames:
    assert ref.count( '_' ) == 1, f"listsOfNames {ref=}"

trivialImportanceRefs = listsOfNames + [
    'EXO_16:36',
    # Jdg 5 is Deborah and Barak's song
    'JDG_5:1','JDG_5:2','JDG_5:3','JDG_5:4','JDG_5:5','JDG_5:6','JDG_5:7','JDG_5:8','JDG_5:9','JDG_5:10',
        'JDG_5:11','JDG_5:12','JDG_5:13','JDG_5:14','JDG_5:15','JDG_5:16','JDG_5:17','JDG_5:18','JDG_5:19','JDG_5:20',
        'JDG_5:21','JDG_5:22','JDG_5:23','JDG_5:24','JDG_5:25','JDG_5:26','JDG_5:27','JDG_5:28','JDG_5:29','JDG_5:30',
        'JDG_5:31a',
    ]
for ref in trivialImportanceRefs:
    assert ref.count( '_' ) == 1, f"trivialImportanceRefs {ref=}"

obscureClarityRefs = [ # Not really at all sure what the Hebrew or Greek is trying to say
    'JDG_5:11a','JDG_5:14',
    'JOB_29:20','JOB_29:24',
    'PSA_22:16b', 'PSA_35:16a', 'PSA_56:10',
    'SNG_6:12',
    'JER_48:34','JER_50:36a',
    'MIC_6:14', # Two unknown Hebrew words
    ]
for ref in obscureClarityRefs:
    assert ref.count( '_' ) == 1, f"obscureClarityRefs {ref=}"

unclearClarityRefs = [ # Mostly sure what's in the Hebrew or Greek,
        # but not sure what it means, or what the cultural implications were
    'GEN_6:4',
    'EXO_15:25b',
    'LEV_19:16','LEV_19:20','LEV_21:4','LEV_25:33a','LEV_26:38b','LEV_27:2b','LEV_27:9b','LEV_27:20',
    'DEU_33:2b','DEU_33:3','DEU_33:6b','DEU_33:8a','DEU_33:12b','DEU_33:15','DEU_33:16',
    'JDG_5:13', 'JDG_13:19b', 'JDG_14:11', 'JDG_15:8a', 'JDG_17:3b',
    'SA1_2:23', 'SA1_17:6b', 'SA1_17:29b',
    'SA2_1:18', 'SA2_5:8', 'SA2_7:19', 'SA2_20:8b', 'SA2_23:5',
    'KI1_6:31b', 'KI1_6:33b', 'KI1_7:28', 'KI1_14:10a',
    'CH1_17:17b',
    'CH2_21:9b', 'CH2_35:5b',
    'JOB_30:6','JOB_30:7','JOB_30:11a','JOB_30:12','JOB_30:13','JOB_30:14','JOB_30:15','JOB_30:16a','JOB_30:17a','JOB_30:18','JOB_30:28a',
        'JOB_31:12','JOB_31:16b',
        'JOB_33:14','JOB_33:16',
        'JOB_34:24a',
        'JOB_36:8','JOB_36:16','JOB_36:17','JOB_36:18','JOB_36:19','JOB_36:27b','JOB_36:33',
        'JOB_37:22a',
        'JOB_38:20','JOB_38:36',
        'JOB_39:13b',
        'JOB_40:13b', 'JOB_40:19', 'JOB_40:24a',
        'JOB_41:9', 'JOB_41:11',
    'PSA_16:5', 'PSA_41:9b', 'PSA_55:15a','PSA_55:18', 'PSA_62:3b',
        'PSA_68:12b','PSA_68:13','PSA_68:15','PSA_68:21b', 'PSA_73:9','PSA_73:10',
        'PSA_92:11', 'PSA_93:3a', 'PSA_105:19','PSA_105:28b','PSA_105:32b', 'PSA_108:9', 'PSA_116:13a',
        'PSA_122:3b', 'PSA_129:4b', 'PSA_141:6',
    'PRO_2:18','PRO_12:26a','PRO_12:28b','PRO_13:6b','PRO_16:1b','PRO_17:8a','PRO_17:19b','PRO_17:24b','PRO_18:20','PRO_19:19',
        'PRO_21:6b','PRO_21:12','PRO_21:18','PRO_21:24','PRO_23:5','PRO_29:10b','PRO_29:24b','PRO_30:1',
    'ECC_5:9', 'ECC_10:15',
    'SNG_8:9',
    'ISA_4:4b','ISA_5:17b','ISA_9:1','ISA_9:20','ISA_10:18','ISA_10:27b','ISA_14:21','ISA_14:31b','ISA_17:3b','ISA_17:9',
        'ISA_19:10a','ISA_19:13b','ISA_22:3a','ISA_22:5','ISA_23:7','ISA_24:23b','ISA_25:7','ISA_25:11',
        'ISA_27:4','ISA_27:7','ISA_27:8','ISA_27:9','ISA_27:10b','ISA_28:10','ISA_28:16b','ISA_29:2b','ISA_29:17',
        'ISA_36:9','ISA_37:25','ISA_38:16a','ISA_41:1','ISA_41:2','ISA_41:3','ISA_48:2a','ISA_49:7','ISA_49:8b',
        'ISA_49:17a','ISA_53:11a','ISA_64:5b',
    'JER_1:15b','JER_6:2b','JER_6:18b','JER_6:27','JER_8:8b','JER_10:19','JER_14:18b','JER_15:12','JER_17:3',
        'JER_23:33','JER_23:34','JER_23:35','JER_23:36b','JER_23:37','JER_23:38','JER_23:39','JER_23:40',
        'JER_31:33b','JER_48:6b','JER_48:9a','JER_51:13b',
    'EZE_8:17b', 'EZE_16:24', 'EZE_21:13', 'EZE_24:12', 'EZE_24:17b', 'EZE_26:20b',
    'DAN_8:12','DAN_8:13a','DAN_11:43b',
    'HOS_11:7b',
    'JOL_2:6b',
    'AMO_6:3','AMO_8:7a',
    'OBA_1:16',
    'HAB_3:15',
    'ZEP_3:10b',
    ]
for ref in unclearClarityRefs:
    assert ref.count( '_' ) == 1, f"unclearClarityRefs {ref=}"

textualCriticismRefs = [ # Hebrew or Greek original manuscripts vary
    'SA1_4:2',
    'SA2_6:1',
    'CH1_24:26', # Beno
    'JOB_39:13a','JOB_39:13b','JOB_39:14','JOB_39:15','JOB_39:16','JOB_39:17','JOB_39:18', # Ostrich section
    'ISA_21:8a', # lion
    ]
for ref in textualCriticismRefs:
    assert ref.count( '_' ) == 1, f"textualCriticismRefs {ref=}"

allRefs, vitalImportanceRefs, importantRefs = [], [], []
def setup():
    """
    Docstring for setup
    """
    global allRefs, vitalImportanceRefs, importantRefs
    genericBibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-KJV-ENG' )

    # Handle ranges in some lists
    newList = []
    for entry in vitalImportanceRefsWithRanges:
        if '-' in entry:
            BBB,CVV = entry.split( '_' )
            C,VV = CVV.split( ':' )
            V1,V2 = VV.split( '-' )
            for newV in range( int(V1), int(V2)+1 ):
                newList.append( f'{BBB}_{C}:{newV}' )
        elif '–' in entry:
            ref1,CV2 = entry.split( '–' )
            BBB,CV1 = ref1.split( '_' )
            C1,V1 = CV1.split( ':' )
            assert '_' not in CV2
            C2,V2 = CV2.split( ':' )
            numVerses = genericBibleOrganisationalSystem.getNumVerses( BBB, C1 )
            for newV in range( int(V1), numVerses+1 ):
                newList.append( f'{BBB}_{C1}:{newV}' )
            intC1, intC2 = int(C1), int(C2)
            for newC in range( intC1+1, intC2+1 ):
                numVerses = genericBibleOrganisationalSystem.getNumVerses( BBB, str(newC) )
                for newV in range( 1, numVerses+1 ):
                    newList.append( f'{BBB}_{C1}:{newV}' )
                    if newC==intC2 and newV==int(V2):
                        break # Reached the desired verse in the final chapter
        else: newList.append( entry )
    vitalImportanceRefs = newList
    newList = []
    for entry in importantRefsWithRanges:
        if '-' in entry:
            BBB,CVV = entry.split( '_' )
            C,VV = CVV.split( ':' )
            V1,V2 = VV.split( '-' )
            for newV in range( int(V1), int(V2)+1 ):
                newList.append( f'{BBB}_{C}:{newV}' )
        elif '–' in entry:
            BBB,CVCV = entry.split( '_' )
            CV1,CV2 = CVCV.split( '–' )
            C1,V1 = CV1.split( ':' )
            assert '_' not in CV2
            C2,V2 = CV2.split( ':' )
            numVerses = genericBibleOrganisationalSystem.getNumVerses( BBB, C1 )
            for newV in range( int(V1), numVerses+1 ):
                newList.append( f'{BBB}_{C1}:{newV}' )
            intC1, intC2 = int(C1), int(C2)
            for newC in range( intC1+1, intC2+1 ):
                numVerses = genericBibleOrganisationalSystem.getNumVerses( BBB, str(newC) )
                for newV in range( 1, numVerses+1 ):
                    newList.append( f'{BBB}_{C1}:{newV}' )
                    if newC==intC2 and newV==int(V2):
                        break # Reached the desired verse in the final chapter
        else: newList.append( entry )
    importantRefs = newList

    # Just do some basic integrity checking
    importanceRefs = vitalImportanceRefs + importantRefs + trivialImportanceRefs
    assert len( set(importanceRefs) ) == len(importanceRefs), [ref for ref in importanceRefs if importanceRefs.count(ref)>1] # Otherwise there must be a duplicate
    clarityRefs = obscureClarityRefs + unclearClarityRefs
    assert len( set(clarityRefs) ) == len(clarityRefs) # Otherwise there must be a duplicate
    allRefs = importanceRefs + clarityRefs + textualCriticismRefs
    # assert len( set(allRefs) ) == len(allRefs) # Otherwise there must be a duplicate # SIMPLY NOT TRUE -- duplicates expected here
    halfRefs = [ref for ref in allRefs if ref[-1] in 'ab']
    # assert len( set(halfRefs) ) == len(halfRefs) # Otherwise there must be a duplicate # SIMPLY NOT TRUE -- duplicates expected here
    for ref in allRefs:
        assert 7 <= len(ref) <= 15, f"{ref=}"
        assert ref.count('_') == 1 and ref.count(':') >= 1, f"{ref=}"
        # Hopefully the following line is no longer required (2025-07-09)
        # if ref in halfRefs: assert ref[:-1] not in allRefs, f"Need to fix '{ref[:-1]}' in tables since we also have '{ref}'"



def run() -> bool:
    """
    """
    uhbBible = USFMBible.USFMBible( UHB_PATHNAME, givenAbbreviation='UHB', encoding='utf-8' )
    # uhbBible.uWencoded = True # TODO: Shouldn't be required ???
    uhbBible.loadBooks() # So we can iterate through them all later

    OETLVOTBible = ESFMBible.ESFMBible( OET_LV_OT_PATHNAME, givenAbbreviation='OET-LV' )
    OETLVOTBible.loadBooks() # So we can iterate through them all later

    netBible = USXXMLBible.USXXMLBible( NET_PATHNAME, givenAbbreviation='NET', encoding='utf-8' )
    netBible.loadBooks() # So we can iterate through them all later

    OETRVSpeakersDict = load_OET_RV_speakers()

    initialLines, splitVerseSet = load_previous_DB()

    collationVerseDict = load_CNTR_collation_DB( splitVerseSet )

    quotedOTRefs = getIndividualQuotedOTRefs()
    quotingNTRefs = getIndividualQuotingNTRefs()

    return create( initialLines, uhbBible, OETLVOTBible, netBible, collationVerseDict, splitVerseSet, quotedOTRefs, quotingNTRefs, OETRVSpeakersDict )
# end of initialise.run()


def load_previous_DB():
    """
    Load our previous DB
    """
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading original {TSV_FILENAME}…" )
    with open( TSV_FILENAME, 'rt', encoding='utf-8') as inputTSVFile:
        initialTSVLines = inputTSVFile.read().rstrip().split( '\n' )
    assert len(initialTSVLines) == NUM_EXPECTED_DATA_LINES, f"{NUM_EXPECTED_DATA_LINES=:,} {len(initialTSVLines)=:,}"
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(initialTSVLines):,} initial lines loaded from original {TSV_FILENAME}." )

    # Find the list of verses which must be split
    splitVerseSet = set()
    for ref in allRefs:
        if ref[-1] in 'ab':
            splitVerseSet.add( ref[:-1] )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{len(splitVerseSet):,} verses need to be split." )
    return initialTSVLines, splitVerseSet
# end of initialise.load_previous_DB()


def load_CNTR_collation_DB( splitVerseSet ):
    """
    Load the CNTR-GNT collation DB
    """
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
    assert 'CollationId' in collation_csv_column_headers, f"{collation_csv_column_headers=}"
    assert 'VerseId' in collation_csv_column_headers, f"{collation_csv_column_headers=}"
    assert 'SR' in collation_csv_column_headers, f"{collation_csv_column_headers=}"

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

        collation_id, verse_id = row['CollationId'], row['VerseId']
        assert len(collation_id) == 11 and collation_id.isdigit()
        assert collation_id.startswith( verse_id )
        book_number, chapter_number, verse_number, _word_number \
            = int(collation_id[:2]), int(collation_id[2:5]), int(collation_id[5:8]), int(collation_id[8:])

        # Use the original table row to put the gloss into the literal text
        if collation_id == '99999999999':
            this_verse_row_list = None
            never_happens_now
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
                this_verse_row_list = get_verse_collation_rows(collation_csv_rows, collation_row_number)
                last_verse_id = verse_id

                fgRef = f'{BBB}_{chapter_number}:{verse_number}'
                if fgRef in splitVerseSet:
                    fgRefA, fgRefB = f'{fgRef}a', f'{fgRef}b'
                    half = len(this_verse_row_list) // 2
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list[:half]:
                        if this_verse_row['SR'] != 'X':
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRefA] = '2' if translatable else '1' if haveVariants else '0'
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list[half:]:
                        if this_verse_row['SR'] != 'X':
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRefB] = '2' if translatable else '1' if haveVariants else '0'
                else: # no split
                    haveVariants = translatable = False
                    for this_verse_row in this_verse_row_list:
                        if this_verse_row['SR'] != 'X':
                            haveVariants = True
                        if this_verse_row['Translatable']:
                            translatable = True
                    collationVerseDict[fgRef] = '2' if translatable else '1' if haveVariants else '0'

    return collationVerseDict
# end of initialise.load_CNTR_collation_DB()


FOOTNOTE_REGEX = re.compile( '\\\\f (.+?)\\\\f\\*')
def get_OSHB_reference_text_critical_footnote_score( OETLV_ReferenceOTBible, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the Hebrew reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
    try: verseEntryList, _contextList = OETLV_ReferenceOTBible.getContextVerseData( (BBB,C,V) )
    except KeyError:
        logging.critical( f"Seems OET-LV reference OT has no verse for {BBB}_{C}:{V}")
        return False
    except TypeError:
        if C=='1' and V=='1':
            logging.critical( f"Seems OET-LV reference OT has no {BBB} book")
        return False

    havePossibleBHSReference = False
    for entry in verseEntryList:
        text = entry.getOriginalText()
        if text and '\\ft OSHB note: ' in text:
            startIndex = 0
            while True:
                match = FOOTNOTE_REGEX.search( text, startIndex)
                if not match: break # No (more) footnotes
                fnText = match.group( 1 )
                # print( f"get_OSHB_reference_text_critical_footnote_score for {BBB}_{C}:{V} got {fnText=}" )
                assert '\\f ' not in fnText
                if 'BHQ' in fnText or 'BHS' in fnText or 'anomalous' in fnText or 'reading' in fnText:
                    # print( f"get_OSHB_reference_text_critical_footnote_score for {BBB}_{C}:{V} got {fnText=}" )
                    if (('differ' in fnText or 'error' in fnText) and 'punctuation' not in fnText) \
                    or 'anomalous' in fnText:
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  get_OSHB_reference_text_critical_footnote_score for {BBB}_{C}:{V} accepted {fnText=}" )
                        havePossibleBHSReference = True
                        break
                startIndex = match.end()
            if havePossibleBHSReference:
                break
    return 1 if havePossibleBHSReference else False
# end of initialise.get_OSHB_reference_text_critical_footnote_score function


def get_UHB_Hebrew_reference_text_critical_footnote_score( HebrewReferenceBible, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the Hebrew reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
    try: verseEntryList, _contextList = HebrewReferenceBible.getContextVerseData( (BBB,C,V) )
    except KeyError:
        logging.critical( f"Seems Hebrew reference Bible has no verse for {BBB}_{C}:{V}")
        return False
    except TypeError:
        if C=='1' and V=='1':
            logging.critical( f"Seems Hebrew reference Bible has no {BBB} book")
        return False

    haveEarlyTranslationReference = False
    for entry in verseEntryList:
        text = entry.getOriginalText()
        if text:
            if '\\ft K ' in text or '\\ft Q ' in text: return 2
            # if 'LXX' in text or 'Syriac' in text or 'Peshitta' in text or 'Dead Sea Scrolls' in text or 'Targum' in text or 'Vulgate' in text:
            #     haveEarlyTranslationReference = True # return 1 Can't return straight away because next line might contain a TC footnote
    return 1 if haveEarlyTranslationReference else False
# end of initialise.get_UHB_Hebrew_reference_text_critical_footnote_score function


def get_English_reference_text_critical_footnote_score( EnglishReferenceBible, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the English reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
    try: verseEntryList, _contextList = EnglishReferenceBible.getContextVerseData( (BBB,C,V) )
    except KeyError:
        logging.critical( f"Seems English reference Bible has no verse for {BBB}_{C}:{V}")
        return False
    except TypeError:
        if C=='1' and V=='1':
            logging.critical( f"Seems English reference Bible has no {BBB} book")
        return False

    haveEarlyTranslationReference = False
    for entry in verseEntryList:
        text = entry.getOriginalText()
        if text:
            if 'Textual Criticism' in text: return 2
            if 'LXX' in text or 'Syriac' in text or 'Peshitta' in text or 'Dead Sea Scrolls' in text or 'Targum' in text or 'Vulgate' in text:
                haveEarlyTranslationReference = True # return 1 Can't return straight away because next line might contain a TC footnote
    return 1 if haveEarlyTranslationReference else False
# end of initialise.get_reference_English_text_critical_footnote_score function


def get_verse_collation_rows(given_collation_rows: list[dict], row_index: int) -> list[list]:
    """
    row_index should be the index of the first row for the particular verse

    Returns a list of rows for the verse
    """
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"get_verse_collation_rows({row_index})")
    this_verse_row_list = []
    this_verseID = given_collation_rows[row_index]['VerseId']
    if row_index > 0: assert given_collation_rows[row_index-1]['VerseId'] != this_verseID
    for ix in range(row_index, len(given_collation_rows)):
        row = given_collation_rows[ix]
        if row['VerseId'] == this_verseID:
            this_verse_row_list.append(row)
        else: # done
            break
    return this_verse_row_list
# end of initialise.get_verse_collation_rows


NOTES_REGEX = re.compile( r'\\[fx]\s.*?\\[fx]\*', re.DOTALL )
WJ_BLOCK_REGEX = re.compile( r'\\wj(?!\*).*?\\wj\*', re.DOTALL )
WORD_NUMBER_REGEX = re.compile( r'¦\d+' )
MARKUP_TOKEN_REGEX = re.compile( r'\\\+?[a-z0-9]{1,4}\*?' )
def to_plain_text( text ):
    """
    Remove USFM markers (and OET-style word-number chips like '¦123')
    to leave readable text for speaker detection.
    """
    text = NOTES_REGEX.sub( ' ', text ) # Remove any footnotes and cross-references
    text = MARKUP_TOKEN_REGEX.sub( ' ', text )
    text = WORD_NUMBER_REGEX.sub( ' ', text )
    text = text.replace( '≈', ' ' ) # OET uses this to mark approximate words added for readability
    return re.sub( r'\s+', ' ', text ).strip()
# end of initialise.to_plain_text function

def has_narration( text ) -> bool:
    """
    Whether the text contains any real words (rather than just punctuation or quote marks)
    """
    return bool( re.search( r'[A-Za-z0-9]', text ) )
# end of initialise.has_narration function


SPEECH_VERBS = 'said|says|speaks|spoke|spoken|questioned|replied|replies|asked|answers?|answered|responded|promised|warned|announced|challenged|calls? out|cried out|tells?|told|declared|shouted|commanded'
NON_NAME_WORDS = 'Who|What|When|Where|Why|How|Which|The|Then|So|Now|But|And|One|Thus|These|Those|I|We|You|It|He|She|They'
# e.g., 'Then Yahweh said to Mosheh, ...' or 'Mosheh asked Kayin, ...'
SPEAKER_ATTRIBUTION_REGEX = re.compile(
    r'\b(?!(?:'+NON_NAME_WORDS+r')\b)(?<!of\s)([A-Z][A-Za-z\'\-]{1,30})\s+(?:'+SPEECH_VERBS+r')\b[^“”‘’"\n]{0,40}[“”‘’"]' )
# e.g., '“...”, said David.' or '“...” answered Yeshua,'
TRAILING_ATTRIBUTION_REGEX = re.compile(
    r'\b(?:'+SPEECH_VERBS+r')\s+(?!(?:'+NON_NAME_WORDS+r')\b)([A-Z][A-Za-z\'\-]{1,30})\b(?=[.,;:)\]]|$)' )

def deduplicate_staying_ordered( items:list ):
    """
    Remove duplicates while maintaining their original order
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add( item )
            result.append( item )
    return result
# end of initialise.deduplicate_staying_ordered function

def deduplicate_consecutive( items:list ):
    """
    Remove items which are duplicates of their immediate predecessor (so the same
    speaker speaking again after someone else has spoken is kept)
    """
    result = []
    for item in items:
        if not result or result[-1] != item:
            result.append( item )
    return result
# end of initialise.deduplicate_consecutive function

def detect_other_speakers( plainText:str ) -> list[str]:
    """
    Best-effort detection of other speakers (e.g., Mosheh, David, Yahweh, Yohan, Paul...)
    in a verse's narration text, by looking for attribution patterns like
    'Mosheh said, “...”' or '“...” replied Yohan,'
    """
    found = []
    for match in SPEAKER_ATTRIBUTION_REGEX.finditer( plainText ):
        found.append( (match.start(), match.group(1)) )
    for match in TRAILING_ATTRIBUTION_REGEX.finditer( plainText ):
        found.append( (match.start(), match.group(1)) )
    return deduplicate_staying_ordered( [name for _pos, name in sorted(found)] )
# end of initialise.detect_other_speakers function


def get_speakers_from_verse_text( rawVerseText:str ) -> str:
    r"""
    Determine who speaks in a verse from its raw ESFM text:
      * Each \wj ...\wj* block gives 'Yeshua', and any narration before,
        between, or after such blocks gives '@' (the narrator) plus other
        named speakers detected from speech-attribution patterns.
      * e.g. 'Yeshua said, “\wj ...\wj*”'        gives '@,Yeshua';
        '“\wj ...\wj*” he answered, “\wj ...\wj*”' gives 'Yeshua,@,Yeshua';
        '“\wj ...\wj*” And then Yeshua left.'   gives 'Yeshua,@'.
      * If there are no \wj blocks, a simple '@,...' list of any detected
        named speakers is returned, e.g. 'Yohan said, “...”' gives '@,Yohan'.
    Returns a comma-separated list where '@' represents the narrator.
    """
    text = NOTES_REGEX.sub( '', rawVerseText ) # Ignore footnotes and cross-references
    if not WJ_BLOCK_REGEX.search( text ): # No words of Yeshua to detect
        names = detect_other_speakers( to_plain_text( text ) )
        return '@' if not names else '@,' + ','.join( names )

    # Step through the verse, alternating between the \wj blocks (words of Yeshua)
    # and the narrator's narration surrounding them.
    speakers = []
    previousEnd = 0
    for match in WJ_BLOCK_REGEX.finditer( text ):
        wjStart, wjEnd = match.start(), match.end()
        narrationText = to_plain_text( text[previousEnd:wjStart] )
        if has_narration( narrationText ):
            speakers.append( '@' ) # The narrator speaks here
            # A 'Yeshua' detected in narration right next to a \wj block is just
            # an attribution ('... answered Yeshua,'), so don't repeat it
            speakers.extend( name for name in detect_other_speakers( narrationText ) if name != 'Yeshua' )
        speakers.append( 'Yeshua' )
        previousEnd = wjEnd
    trailingText = to_plain_text( text[previousEnd:] )
    if has_narration( trailingText ):
        speakers.append( '@' ) # The narrator speaks last
        speakers.extend( name for name in detect_other_speakers( trailingText ) if name != 'Yeshua' )
    return ','.join( deduplicate_consecutive( speakers ) )
# end of initialise.get_speakers_from_verse_text function


def load_OET_RV_speakers() -> dict:
    r"""
    Read the OET-RV (Readers' Version) files
    keeping track of the chapter (\c) and verse (\v) numbers, and detect the
    speakers for each verse (see get_speakers_from_verse_text above).

    In a few books (e.g., SNG and JER) a USFM '\sp' marker explicitly states the
    current speaker, and that name is then used for all following verses until the
    next '\sp' or '\s1' marker.

    Returns a dict of BBB_C:V references to comma-separated speaker lists.
    (Verses not found in OET-RV default to just the narrator, '@'.)
    """
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading OET-RV speakers data from {OET_RV_PATHNAME}…" )
    speakersDict = {}
    for BBB in bos_books_codes_py.get_all_bos_book_codes():
        # if not (bos_books_codes_py.is_old_testament_nr( BBB ) or bos_books_codes_py.is_new_testament_nr( BBB )):
        #     continue # We skip deuterocanon and any non-Bible (introductory, etc.) books
        if BBB in ('FRT','INT','XXA','XXB','XXC','XXD'):
            continue # skip non-chapter books
        ESFMFilename = OET_RV_PATHNAME / f'OET-RV_{BBB}.ESFM'
        if not ESFMFilename.exists():
            logging.warning( f"Didn't find OET-RV ESFM file {ESFMFilename}" )
            continue
        currentChapter = currentVerse = None
        currentSpeaker = None # Set whenever a '\sp' speaker marker is seen
        verseSpeaker = None # The '\sp' speaker in effect when the pending verse started
        verseTextBits = []
        def flushPendingVerse():
            """
            Store the speakers for the currently-pending verse (if there is one)
            """
            if currentChapter is not None and currentVerse is not None and verseTextBits:
                # A '\sp' marker explicitly identifies the speaker, so it takes precedence
                speakersDict[f'{BBB}_{currentChapter}:{currentVerse}'] = \
                        verseSpeaker if verseSpeaker else get_speakers_from_verse_text( ' '.join(verseTextBits) )
        with open( ESFMFilename, 'rt', encoding='utf-8') as ESFMFile:
            for line in ESFMFile:
                chapterMatch = re.match( r'^\\c\s+(\d+)', line )
                if chapterMatch:
                    flushPendingVerse()
                    currentChapter = int( chapterMatch.group(1) )
                    currentVerse = None
                    verseTextBits = []
                    continue
                verseMatch = re.match( r'^\\v\s+(\d+)[a-z]?\s?(.*)$', line )
                if verseMatch:
                    flushPendingVerse()
                    currentVerse = int( verseMatch.group(1) )
                    verseSpeaker = currentSpeaker # Capture the speaker at the verse start
                    verseTextBits = [verseMatch.group(2)]
                    continue
                sectionMatch = re.match( r'^\\s[1]\s', line ) # was [12]
                if sectionMatch:
                    flushPendingVerse()
                    currentSpeaker = None # A new '\s1'/'\s2' section ends the range of any '\sp' speaker
                    continue
                speakerMatch = re.match( r'^\\sp\s+(.+)$', line )
                if speakerMatch:
                    currentSpeaker = WORD_NUMBER_REGEX.sub( '', speakerMatch.group(1) ).strip()
                    continue
                verseTextBits.append( line.strip() )
            flushPendingVerse()
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(speakersDict):,} OET-RV verses loaded with speaker data." )
    return speakersDict
# end of initialise.load_OET_RV_speakers function


def create( initialTSVLines, HebrewReferenceBible, OET_LT_ReferenceOTBible, EnglishReferenceBible, collationVerseDict, splitVerseSet, individualQuotedOTRefs, individualQuotingNTRefs, OETRVSpeakersDict ) -> bool:
    """
    """
    BibleOrgSysGlobals.backupAnyExistingFile( TSV_FILENAME, numBackups=3 )

    numLinesWritten = 0
    with open( TSV_FILENAME, 'wt', encoding='utf-8') as outputFile:
        outputFile.write( "FGRef\tImportance\tTextualIssue\tClarity\tSpeakers\tComment\n")
        numLinesWritten += 1
        for line in initialTSVLines:
            UUU, CV = line.split(' ')
            BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code( UUU )
            C, V = CV.split( ':' )
            fgRef = f'{BBB}_{CV}'
            # print( f"{fgRef}" )

            isOT = bos_books_codes_py.is_old_testament_nr( BBB )
            if isOT:
                oshb_TC_footnote_value = get_OSHB_reference_text_critical_footnote_score( OET_LT_ReferenceOTBible, BBB, C, V )
            heb_TC_footnote_value = get_UHB_Hebrew_reference_text_critical_footnote_score( HebrewReferenceBible, BBB, C, V )
            eng_TC_footnote_value = get_English_reference_text_critical_footnote_score( EnglishReferenceBible, BBB, C, V )
            # print( f"  {has_TC_footnote}")
            # if BBB=='EXO' and has_TC_footnote: print( f"{fgRef} has TC" ); assert False, "We want to stop here"
            # print( f"{line=} {fgRef=}" )
            subRefs = [f'{fgRef}a',f'{fgRef}b'] if fgRef in splitVerseSet else [fgRef]

            for subRef in subRefs: # either one or two lines per verse
                importance, clarity, comment = defaultImportance, defaultClarity, ''

                # Look at textual issues 0=None/1=Minor spelling/2=Minor words/3-Major
                textualIssue = collationVerseDict[subRef] if subRef in collationVerseDict else defaultTextualIssue
                if heb_TC_footnote_value==2 or eng_TC_footnote_value==2 or subRef in textualCriticismRefs:
                    if textualIssue==defaultTextualIssue: # default is '0'
                        textualIssue = '2' # textualIssue ranges from 0 (None) to 4 (Major)
                    elif textualIssue == '1':
                        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Increased {subRef} TC from 1 to 2")
                        textualIssue = '2' # textualIssue ranges from 0 (None) to 4 (Major)
                    else:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{subRef} TC was already {textualIssue}")
                elif oshb_TC_footnote_value==1 or eng_TC_footnote_value==1:
                    if textualIssue==defaultTextualIssue: # default is '0'
                        textualIssue = '1' # textualIssue ranges from 0 (None) to 4 (Major)
                    else:
                        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{subRef} TC was already {textualIssue}")

                # Look at importance Trival/Medium/Important/Vital
                if subRef in vitalImportanceRefs:
                    importance = 'V' # vital = 3/3
                    vitalImportanceRefs.remove( subRef )
                elif fgRef in vitalImportanceRefs:
                    importance = 'V' # vital = 3/3
                    if subRef[-1] == 'b':
                        vitalImportanceRefs.remove( fgRef )
                elif subRef in importantRefs:
                    importance = 'I' # important = 2/3
                    importantRefs.remove( subRef )
                elif fgRef in importantRefs:
                    importance = 'I' # important = 2/3
                    if subRef[-1] == 'b':
                        importantRefs.remove( fgRef )
                elif subRef in trivialImportanceRefs:
                    importance = 'T' # trivial = 0/3
                    trivialImportanceRefs.remove( subRef )
                elif fgRef in trivialImportanceRefs:
                    importance = 'T' # trivial = 0/3
                    if subRef[-1] == 'b':
                        trivialImportanceRefs.remove( fgRef )
                # Now adjust if we have OT quotes
                if (BBB,C,V) in individualQuotedOTRefs['Possible'] or (BBB,C,V) in individualQuotedOTRefs['Allusion+Possible']:
                    if importance not in ('V','I'): # already
                        importance = 'M' # medium = 1/3
                if (BBB,C,V) in individualQuotedOTRefs['Allusion']:
                    if importance != 'V': # already
                        importance = 'I' # important = 2/3
                if (BBB,C,V) in individualQuotedOTRefs['Quote']:
                    importance = 'V' # vital = 3/3


                # Look at clarity Obscure/Unclear/Clear
                if subRef in obscureClarityRefs:
                    clarity = 'O' # obscure = 1/3
                    obscureClarityRefs.remove( subRef )
                elif fgRef in obscureClarityRefs:
                    clarity = 'O' # obscure = 1/3
                    if subRef[-1] == 'b':
                        obscureClarityRefs.remove( fgRef )
                elif subRef in unclearClarityRefs:
                    clarity = 'U' # unclear = 2/3
                    unclearClarityRefs.remove( subRef )
                elif fgRef in unclearClarityRefs:
                    clarity = 'U' # unclear = 2/3
                    if subRef[-1] == 'b':
                        unclearClarityRefs.remove( fgRef )

                speakers = OETRVSpeakersDict.get( fgRef, speakersDefault )
                outputFile.write( f"{subRef}\t{importance}\t{textualIssue}\t{clarity}\t{speakers}\t{comment}\n" )
                numLinesWritten += 1

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {numLinesWritten:,} lines written to {TSV_FILENAME}." )
    assert numLinesWritten == 1+NUM_EXPECTED_DATA_LINES+len(splitVerseSet), f"{NUM_EXPECTED_DATA_LINES=:,} {len(splitVerseSet)=:,} {numLinesWritten=:,}"
    assert len(vitalImportanceRefs) == 0, f"({len(vitalImportanceRefs)}) {vitalImportanceRefs=}" # They should all have been used
    assert len(importantRefs) == 0, f"({len(importantRefs)}) {importantRefs=}" # They should all have been used (but might have versification issues with Deu 29:29, etc.)
    assert len(trivialImportanceRefs) == 0, f"({len(trivialImportanceRefs)}) {trivialImportanceRefs=}" # They should all have been used
    assert len(obscureClarityRefs) == 0, f"({len(obscureClarityRefs)}) {obscureClarityRefs=}" # They should all have been used
    assert len(unclearClarityRefs) == 0, f"({len(unclearClarityRefs)}) {unclearClarityRefs=}" # They should all have been used

    return True
# end of initialise.create()


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    setup()
    run()
# end of initialise.briefDemo()

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    setup()
    run()
# end of initialise.fullDemo()

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of initialise.py
