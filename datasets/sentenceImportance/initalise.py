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
# Noth this source code and the generated dataset are marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling SentenceImportance initialisation.

Regenerate sentenceImportance.tsv from the immutable .tsv.init inventory and
the source annotations. Paths are relative to this script, not the working
directory; run from createPages with uv run ../datasets/sentenceImportance/initalise.py.

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

VERSIFICATION CONTRACT:
    Output FGRefs use BOS's explicit 'org' profile (original Hebrew/Greek),
    including numbered Hebrew Psalm titles. 'org' is not the legacy count-only
    'Original' system, nor the composite 'BOSReference' mapping pivot.
    Curated lists below and cross-testament OT quotations use 'eng', except
    the two explicitly documented quotation corrections in QUOTE_PROFILES.
    UHB stores English numbers (Hebrew numbers in \\va); OET-LV OT uses its
    'OET-LV' profile; speakers use 'OET-RV' and explicit OET-LV evidence.
    Psalm/proverb headings remain narrator; their authors supply the default
    voice of the following body. Two explicit speaker runs may create editorial
    a/b rows only across a one-to-one mapping; existing curated halves take
    precedence. More complex changes retain all known speakers in one list.
    CNTR VerseIds match 'VLT', including
    its PHP 1:16-17 order. NET USX uses 'eng' in OT/Acts and 'org' elsewhere in NT.
    Every join uses BOS mappings. Whole indivisible groups share annotations;
    the strongest importance/textual issue and least clarity win. Speaker
    sequences are concatenated in source order. Group coverage is recorded in
    Comment. Unsupported/ambiguous mappings fail; reviewed no-counterpart
    source verses are reported and omitted, never assigned to a neighbour.
    NET's explicitly omitted NT verses are scored only after verifying their
    explanatory TC notes. Its malformed printed Jonah 1:17 label is restored
    in a temporary import copy; source files are never edited.
    a/b are our editorial half-verse labels, NOT BOS segment declarations:
    retain them only across an exact one-to-one whole-verse mapping, otherwise
    fail for editorial review. Whole-verse annotations apply to both halves.
    See README.md and sentenceImportance.build.json for source conventions,
    seed corrections, mapping versions, diagnostics, and regeneration details.

CHANGELOG:
    2024-05-22 Use SR and Translatable SR-GNT collation columns from CNTR
    2025-04-10 Use crossTestamentQuotes info
    2025-07-09 Tried to make more allowance for partial verses
    2025-09-11 Find Q footnotes in UHB
    2025-10-13 Find appropriate footnotes in OSHB via OET-LV OT files
    2026-01-05 Handle a range crossing a chapter boundary (using en-dash –)
    2026-03-29 Updated for latest collation DB from GreekCNTR
    2026-09-08 Added Speakers column to the output (auto-detected from OET-RV \\wj markers, \\sp speaker markers, and speech attribution patterns)
    2026-10-03 More updates to tables
    2026-10-26 Attribute Psalm/proverb bodies, preserve within-verse speaker
               changes and heading halves, and use LV tagged speech evidence.
    2026-10-26 Map all annotations to org when building the TSV database
"""
from pathlib import Path
from csv import  DictReader
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from itertools import groupby
import hashlib
import json
import re
import logging
import shutil
import tempfile
import xml.etree.ElementTree as ElementTree

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
import BibleOrgSys.Formats.USFMBible as USFMBible
import BibleOrgSys.Formats.ESFMBible as ESFMBible
import BibleOrgSys.Formats.USXXMLBible as USXXMLBible
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, VersificationMappingError, get_default_mapping_engine,
)
import bos_books_codes_py

LAST_MODIFIED_DATE = '2026-10-26'
SHORT_PROGRAM_NAME = "SentenceImportance_initialisation"
PROGRAM_NAME = "Sentence Importance initialisation"
PROGRAM_VERSION = '1.0.0'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


DATA_FOLDER = Path(__file__).resolve().parent
REPO_FOLDER = DATA_FOLDER.parents[1]
TSV_FILENAME = DATA_FOLDER / 'sentenceImportance.tsv'
SEED_FILENAME = DATA_FOLDER / 'sentenceImportance.tsv.init'
REPORT_FILENAME = DATA_FOLDER / 'sentenceImportance.build.json'
QUOTES_FILENAME = DATA_FOLDER.parent / 'crossTestamentQuotes/crossTestamentQuotes.tsv'
OUTPUT_PROFILE = 'org'
CURATED_PROFILE = 'eng'
CNTR_PROFILE = 'VLT'
NUM_EXPECTED_DATA_LINES = 41_899 # for initial vref.txt file with no split verses

COLLATION_PATHNAME = REPO_FOLDER.parent / 'CNTR-GNT/sourceExports/collation.csv'
BOS_BOOK_ID_MAP = {
    40: 'MAT', 41: 'MRK', 42: 'LUK', 43: 'JHN', 44: 'ACT',
    45: 'ROM', 46: 'CO1', 47: 'CO2', 48: 'GAL', 49: 'EPH', 50: 'PHP', 51: 'COL', 52: 'TH1', 53: 'TH2', 54: 'TI1', 55: 'TI2', 56: 'TIT', 57: 'PHM',
    58: 'HEB', 59: 'JAM', 60: 'PE1', 61: 'PE2', 62: 'JN1', 63: 'JN2', 64: 'JN3', 65: 'JDE', 66: 'REV', 99:None}

UHB_PATHNAME = REPO_FOLDER / 'copiedBibles/Original/unfoldingWord.org/UHB'
OET_LV_OT_PATHNAME = REPO_FOLDER.parent / 'OpenEnglishTranslation--OET/derivedTexts/auto_edited_OT_ESFM'
OET_LV_NT_WORD_TABLE = REPO_FOLDER.parent / 'OpenEnglishTranslation--OET/derivedTexts/auto_edited_VLT_ESFM/OET-LV_NT_word_table.tsv'
NET_PATHNAME = REPO_FOLDER / 'copiedBibles/English/NET'
OET_RV_PATHNAME = REPO_FOLDER.parent / 'OpenEnglishTranslation--OET/translatedTexts/ReadersVersion'


# Defaults are M=normal importance, 0=no textual issue, C=clear, @=narrator.

# These curated input tables use common English/OET-RV versification ('eng').
# Their references are converted to original Hebrew/Greek versification ('org') in the output TSV.
vitalImportanceRefsWithRanges = [ # Often in doctrinal statements
    'GEN_1:1-3', 'GEN_3:15', 'GEN_3:16', # Gen 3:15 is the protoevangelium
    'EXO_3:14', 'EXO_20:11', # EXO 3:14 'I AM WHO I AM' -- God's self-revelation
    'DEU_4:6', 'DEU_6:4-5', 'DEU_9:4', 'DEU_31:6',
    'CH2_7:14',
    'PSA_19:7-11', 'PSA_22:1-2','PSA_22:7-18', 'PSA_46:1',
    'PRO_3:5','PRO_3:6',
    'ISA_7:14', # The virgin birth prophecy
    'ISA_9:6-7',
    'ISA_52:13–53:12', # The fourth and best-known servant song
    'ISA_55:11',
    'JER_29:11-13',
    'DAN_7:13-14',
    'MIC_5:2','MIC_6:8',
    'HAB_2:4', # 'The just shall live by faith' -- key to the Reformation
    'ZEC_12:10',
    'MAL_3:8-10',

    'MAT_3:16-17', 'MAT_6:33', 'MAT_24:35', 'MAT_28:19-20', # MAT 3:16-17 Trinitarian baptism
    'MAT_22:37-40', # The Great Commandment
    'MAT_26:26-29', # The institution of the Lord's Supper
    'JHN_1:1-5','JHN_3:3','JHN_3:16', 'JHN_5:24', 'JHN_11:25', 'JHN_20:31',
    'JHN_10:30','JHN_14:6', 'JHN_14:9', 'JHN_17:17', # Key Christology/sanctification statements
    'ACT_1:11', 'ACT_4:12', # Ascension/return promise; salvation in no other name

    'ROM_1:16', 'ROM_3:23','ROM_5:1','ROM_6:23', 'ROM_8:1','ROM_8:28', 'ROM_8:38-39', 'ROM_10:9-10', 'ROM_12:2',
    'CO1_13:4-8', 'CO1_15:3-4', 'CO1_15:17', 'CO1_15:20', # The gospel and the resurrection
    'CO2_5:21','CO2_12:9', 'CO2_13:14', # 2 Cor 13:14 Trinitarian benediction
    'GAL_3:10','GAL_3:13-14','GAL_5:22-23', 'EPH_2:9',
    'PHP_2:6-11', 'PHP_4:6-8', 'PHP_4:13', # PHP 2:6-11 the Christ hymn
    'COL_1:15-20', 'COL_2:9', # The Christ hymn and the fullness of the deity
    'TI1_1:15', # 'Christ Jesus came into the world to save sinners'
    'TI2_3:16-17',

    'HEB_1:3', 'HEB_11:1','HEB_11:6','HEB_13:5',
    'PE1_2:24', 'PE1_3:15', 'PE1_5:7',
    'PE2_1:19-21',

    'JN1_1:9', 'JN1_4:8', 'JN1_5:11-13', # 1 John 1:9 confession; 4:8 'God is love'
    'REV_21:4', # Consummation -- no more death, mourning, crying or pain
    ]
for ref in vitalImportanceRefsWithRanges:
    assert ref.count( '_' ) == 1, f"vitalImportanceRefsWithRanges {ref=}"

importantRefsWithRanges = [ # Often quoted and/or memorised by Christians
    'GEN_1:4-31', # Gen 1:1-3 is above
        'GEN_2:1-3', 'GEN_12:3',
    'DEU_29:24-29', 'DEU_30:3-5','DEU_30:19',
    'JOS_1:9',
    'EST_4:14',
    'PSA_9:17', 'PSA_23:1-6', 'PSA_51:5','PSA_51:10', 'PSA_119:89', 'PSA_119:105',
    'PRO_1:7', 'PRO_4:1-7', 'PRO_14:34',
    'ECC_8:15',
    'ISA_2:2-4','ISA_6:1-8','ISA_11:1-12','ISA_27:6','ISA_28:16','ISA_40:31','ISA_41:10', 'ISA_46:9-10',
    'ISA_42:1-9', 'ISA_48:12-13','ISA_48:16', 'ISA_49:1-13', 'ISA_50:4-11', # The other three servant songs 'ISA_52:13–53:12',
    'ISA_54:17', 'ISA_55:1-10','ISA_55:12-13', 'ISA_66:8',
    'JER_17:9', 'JER_23:5-6', 'JER_31:31-34', 'JER_33:2-3', 'JER_33:14-18',
    'DAN_7:10', 'DAN_9:5','DAN_9:19','DAN_9:24', 'DAN_12:1','DAN_12:4',
    'ZEC_12:8-9','ZEC_12:11',

    'MAT_1:23', # Immanuel
    'MAT_4:4', 'MAT_5:3-12', 'MAT_16:1-3', 'MAT_24:32-33','MAT_24:44', # MAT 5:3-12 the Beatitudes
    'LUK_21:28','LUK_24:27',
    'JHN_1:6-18', 'JHN_3:18','JHN_6:68-69','JHN_7:16', 'JHN_8:36','JHN_8:58', 'JHN_10:18','JHN_10:28','JHN_16:33', 'JHN_17:5','JHN_17:23',
    'ACT_2:38', 'ACT_2:42', 'ACT_15:10', 'ACT_16:31', # ACT 2:38 baptism; ACT 16:31 'Believe on the Lord Jesus Christ'
    'CO1_6:19-20', 'CO1_10:6-11','CO1_2:12','CO1_2:14', 'CO1_3:14-15', 'CO1_15:58', # 1 Cor 6:19-20 body as God's temple
    'ROM_3:3-4','ROM_3:19-22', 'ROM_5:8','ROM_5:16-21', 'ROM_8:3', 'ROM_10:2','ROM_10:13', 'ROM_11:1-2','ROM_11:11-12','ROM_11:29', 'ROM_13:12', 'ROM_15:4', 'ROM_16:17',
    'CO2_5:17','CO2_9:7', # 2 Cor 5:17 new creation
    'GAL_3:21-22','GAL_3:24', 'GAL_6:16',
    'EPH_2:8','EPH_2:10', 'EPH_4:14','EPH_6:4','EPH_6:10-13','EPH_6:17',
    'PHP_2:12-13', 'PHP_3:20-21',
    'COL_3:2',
    'TH1_1:10','TH1_4:16-17','TH1_5:9',
    'TH2_2:9-12',
    'TI1_4:13','TI1_4:16','TI1_6:3',
    'TI2_2:15','TI2_4:3-4',
    'TIT_1:9','TIT_2:1',
    'HEB_4:12-13', 'HEB_5:12-14', 'HEB_9:22', 'HEB_11:2-5','HEB_11:7-40', 'HEB_13:9',
    'JAM_1:5', 'JAM_2:14-26', # JAM 2:14-26 faith without works
    'PE1_2:2', 'PE1_2:9-10',
    'PE2_3:10','PE2_3:15-16',
    'JN1_2:19', 'JN1_4:1','JN1_4:4',
    'JN2_1:9',
    'REV_1:17-18', 'REV_3:5', 'REV_13:7', 'REV_20:12','REV_20:15',
    ]
for ref in importantRefsWithRanges:
    assert ref.count( '_' ) == 1, f"importantRefsWithRanges {ref=}"

listsOfNames = [ # Long lists of people's names (genealogies, censuses, rosters) -- classic preaching-skips
    'KI1_4:2-19', # Solomon's officials
    'NUM_1:1-54', # The census at Sinai
    'NUM_26:1-65', # The second census on the plains of Moab
    'NUM_7:10-88', # The twelve tribal leaders' offerings, repeated verbatim
    'JOS_12:9-24', # The list of conquered kings
    'JOS_15:21-62','JOS_16:5-10','JOS_17:11-13','JOS_18:11-28','JOS_19:1-48', # Town rosters for each tribe
    'JOS_21:1-42', # The cities given to the Levites
    'CH1_1:1–9:34', # Nine chapters of genealogies from Adam down to post-exilic Jews
    'CH1_23:1–26:32', # The Levitical duty rosters
    'EZR_2:2-70', # The returning exiles and their goods (NEH 7 is the same list)
    'NEH_7:5-73', # Duplicate of the EZR 2 roster
    'NEH_11:3-36', # Who lived in Jerusalem and the towns
    'NEH_12:1-26', # The priests and Levites of the return
    ]
for ref in listsOfNames:
    assert ref.count( '_' ) == 1, f"listsOfNames {ref=}"

trivialImportanceRefs = listsOfNames + [
    'EXO_16:36',
    # Purim casualty tallies, including the list of Haman's sons
    'EST_9:6-16',
    # Jdg 5 is Deborah and Barak's song
    'JDG_5:1-31',
    # OT sacrificial festival calendar and the rarely-
    # preached skin, mildew and body-discharge laws
    'NUM_28:1–29:40',
    'LEV_13:1-59', 'LEV_14:33-57', 'LEV_15:1-33',
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
    'MAT_6:13', # End of Lord's Prayer doxology omitted in some witnesses
    'MRK_16:9-20', # Mark's longer ending
    'JHN_7:53–8:11', # The woman caught in adultery
    'JN1_5:7-8', # Comma Johanneum
    ]
for ref in textualCriticismRefs:
    assert ref.count( '_' ) == 1, f"textualCriticismRefs {ref=}"

# These two quotation rows use Hebrew Psalm numbering, unlike the rest of
# the quotation table: lots for clothing (22:19), and casting burdens (55:23).
# Keep this correction local; do not silently change the shared source dataset.
QUOTE_PROFILES = {('JHN_19:24', 'PSA_22:19'): 'org',
                  ('PE1_5:7', 'PSA_55:23'): 'org'}
# NET omits these numbered verses and explains each in a TC footnote at the
# stated native verse. Validate that evidence in the actual USX before allowing
# absent text to contribute a score; an arbitrary missing verse still fails.
NET_OMISSION_NOTES = {
    ('MAT','17','21'): '20', ('MAT','18','11'): '10', ('MAT','23','14'): '13',
    ('MRK','7','16'): '15', ('MRK','9','44'): '43', ('MRK','9','46'): '43',
    ('MRK','11','26'): '25', ('MRK','15','28'): '27',
    ('LUK','17','36'): '35', ('LUK','23','17'): '16', ('JHN','5','4'): '3',
    ('ACT','8','37'): '36', ('ACT','15','34'): '33', ('ACT','24','7'): '6',
    ('ACT','28','29'): '28', ('ROM','16','24'): '23',
}
# The 2024 seed predates the current org Greek Esther inventory. Reconcile the
# selected books against BOS counts (do not add other books to the dataset).
SEED_REMOVED = {('ESG','8','40'), ('ESG','8','41'), ('ESG','10','14')}
SEED_ADDED = {('ESG','4','6'), ('ESG','9','5'), ('ESG','9','30')}
HEADER = 'FGRef\tImportance\tTextualIssue\tClarity\tSpeakers\tComment\n'


def fgref(reference):
    BBB, C, V, *suffix = reference
    return f'{BBB}_{C}:{V}{suffix[0] if suffix and suffix[0] else ""}'


@lru_cache(maxsize=65536)
def mapped_references(source, references):
    """BOS owns correspondence, including complete indivisible groups."""
    return get_default_mapping_engine().convert_passage(source, OUTPUT_PROFILE, references)


class MappingAudit:
    def __init__(self):
        self.comments = defaultdict(set)
        self.omitted = set()
        self.editorial_titles = set()
        self.source_repairs = set()
        self.net_omissions = {}
        self.inputs = {}
        self.speaker_evidence = {}
        self.speaker_splits = {}
        self.speaker_unsplit = {}

    def input_file(self, path):
        path = Path(path).resolve()
        self.inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

    def convert(self, source, references, label, half=''):
        result = mapped_references(source, tuple(references))
        if result.status != MappingStatus.EXACT:
            # This is a reviewed absence, not an arbitrary missing/invalid verse.
            if result.diagnostics and all(d.code == 'NO_REFERENCE_COUNTERPART' for d in result.diagnostics):
                message = f'{label}: {source} {", ".join(map(fgref, references))}: no org counterpart'
                if message not in self.omitted:
                    logging.warning(message)
                    self.omitted.add(message)
                return ()
            raise ValueError(f'{label}: {source} {", ".join(map(fgref, references))}: '
                             f'{VersificationMappingError(result)}')
        if half and (len(result.source_references) != 1 or len(result.references) != 1
                     or result.references[0][3] is not None):
            raise ValueError(f'{label}: editorial half {half!r} needs review across a split/merged mapping: {result}')
        if result.is_expanded or len(result.references) != len(result.source_references):
            note = (f'{label}: shared annotation from {source} '
                    f'{", ".join(map(fgref, result.source_references))} '
                    f'to org {", ".join(map(fgref, result.references))}')
            for ref in result.references:
                self.comments[fgref(ref)].add(note)
        return tuple(fgref(ref) + half for ref in result.references)


def expand_reference(text, profile):
    """Expand a curated/quotation range in its SOURCE numbering, never KJV counts.

    Returns whole reference tuples plus an optional editorial a/b half. Handles
    comma lists, semicolon chapter lists and en-dash cross-chapter ranges.
    """
    BBB, CVs = text.replace('&c', '').split('_')
    refs = []
    half = ''
    for CV in CVs.split(';'):
        C, verses = CV.strip().split(':', 1)
        for piece in verses.split(','):
            piece = piece.strip()
            if '–' in piece or '-' in piece:
                first, last = re.split('[-–]', piece)
                endC, endV = last.split(':') if ':' in last else (C, last)
                result = get_default_mapping_engine().convert_range(
                    profile, profile, (BBB,C,first), (BBB,endC,endV))
                if result.status != MappingStatus.EXACT:
                    raise ValueError(f'{profile} range {text}: {VersificationMappingError(result)}')
                refs.extend(result.references)
            else:
                match = re.fullmatch(r'(\d+)([ab]?)', piece)
                if not match:
                    raise ValueError(f'Invalid {profile} reference {text!r}')
                V, suffix = match.groups()
                if suffix:
                    if refs or len(CVs.split(';')) != 1 or ',' in verses:
                        raise ValueError(f'Editorial half must be a single reference: {text}')
                    half = suffix
                refs.append((BBB,C,V,None))
    return tuple(dict.fromkeys(refs)), half


def setup(audit=None):
    """Build fresh org annotations; safe to call repeatedly (no list mutation)."""
    audit = audit if audit is not None else MappingAudit()
    importance, textual, clarity = {}, {}, {}
    for entries, score, destination, label in (
        (trivialImportanceRefs, 'T', importance, 'importance'),
        (importantRefsWithRanges, 'I', importance, 'importance'),
        (vitalImportanceRefsWithRanges, 'V', importance, 'importance'),
        (unclearClarityRefs, 'U', clarity, 'clarity'),
        (obscureClarityRefs, 'O', clarity, 'clarity'),
        (textualCriticismRefs, '2', textual, 'textual issue'),
    ):
        for entry in entries:
            references, half = expand_reference(entry, CURATED_PROFILE)
            # Map each whole verse independently so an annotation is shared only
            # across its actual atomic group, not across an entire chapter range.
            for ref in references:
                for key in audit.convert(CURATED_PROFILE, (ref,), f'Curated {label}', half):
                    destination[key] = score # ordered weakest to strongest above
    return importance, textual, clarity


def load_original_inventory(seed_path=SEED_FILENAME):
    """Use the immutable seed for book order; validate its numbered org domain."""
    lines = Path(seed_path).read_text(encoding='utf-8').splitlines()
    if len(lines) != NUM_EXPECTED_DATA_LINES:
        raise ValueError(f'{seed_path}: expected {NUM_EXPECTED_DATA_LINES} seed verses, got {len(lines)}')
    refs = [(bos_books_codes_py.usfm_abbrev_to_bos_book_code(BBB), *CV.split(':'))
            for BBB,CV in (line.split() for line in lines)]
    if len(set(refs)) != len(refs):
        raise ValueError(f'{seed_path}: duplicate seed references')
    books = tuple(dict.fromkeys(ref[0] for ref in refs))
    counts = get_default_mapping_engine().get_legacy_tables(OUTPUT_PROFILE)['CV']
    expected = [(BBB,str(C),str(V),None) for BBB in books
                for C in range(1,int(counts[BBB]['numChapters'])+1)
                for V in range(1,int(counts[BBB][str(C)])+1)]
    target = {ref[:3] for ref in expected}
    if set(refs)-target != SEED_REMOVED or target-set(refs) != SEED_ADDED:
        raise ValueError(f'Unexpected seed/org differences: removed={set(refs)-target}; added={target-set(refs)}')
    for ref in expected:
        result = get_default_mapping_engine().convert(OUTPUT_PROFILE, OUTPUT_PROFILE, (ref,))
        if result.status != MappingStatus.EXACT:
            raise ValueError(f'Invalid org output address {ref}: {VersificationMappingError(result)}')
    return expected


def load_quoted_OT_annotations(audit, path=QUOTES_FILENAME):
    """Read the source rows directly, preserving ranges and their provenance."""
    importance = {}
    ranks = 'TMIV'
    audit.input_file(path)
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = DictReader(source, delimiter='\t')
        if reader.fieldnames != ['NTRef','OTRef','Strength']:
            raise ValueError(f'{path}: unexpected quotation columns {reader.fieldnames}')
        for line_number, row in enumerate(reader, 2):
            profile = QUOTE_PROFILES.get((row['NTRef'],row['OTRef']), 'eng')
            label = f'Quotation {row["NTRef"]} ({row["Strength"]})'
            try:
                score = {'Quote':'V', 'Allusion':'I', 'Possible':'M', 'Allusion+Possible':'M'}[row['Strength']]
                refs, half = expand_reference(row['OTRef'], profile)
                for ref in refs:
                    for key in audit.convert(profile, (ref,), label, half):
                        importance[key] = max(importance.get(key,'T'), score, key=ranks.index)
            except (ValueError, KeyError) as error:
                raise ValueError(f'{path}:{line_number}: {row}: {error}') from error
    return importance


def load_CNTR_collation_DB(audit, path=COLLATION_PATHNAME):
    """Stream native VLT-numbered CNTR verse scores and map them to org.

    The local source's combined ACT 19:40/CO2 13:12, separate JN3 1:15 and
    REV 12:18, and selfish/loving PHP 1:16/17 agree with the VLT profile.
    Whole-verse TC scores apply to both editorial halves, without inventing
    word-level correspondence from a row-count midpoint.
    """
    audit.input_file(path)
    scores = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = DictReader(source)
        required = {'CollationId','VerseId','SR','Translatable'}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError(f'{path}: missing collation columns {required-set(reader.fieldnames or ())}')
        for verse_id, rows in groupby(reader, key=lambda row:row['VerseId']):
            if verse_id.startswith('99'):
                break
            if len(verse_id) != 8 or not verse_id.isdigit():
                raise ValueError(f'{path}: malformed VerseId {verse_id!r}')
            ref = (BOS_BOOK_ID_MAP[int(verse_id[:2])], str(int(verse_id[2:5])), str(int(verse_id[5:])), None)
            score = '0'
            for row in rows:
                if not row['CollationId'].startswith(verse_id):
                    raise ValueError(f'{path}: mismatched collation row {row["CollationId"]} at {verse_id}')
                score = max(score, '2' if row['Translatable'] else '1' if row['SR'] != 'X' else '0')
            for key in audit.convert(CNTR_PROFILE, (ref,), 'CNTR textual issue'):
                if key in scores:
                    raise ValueError(f'{path}: duplicate/noncontiguous CNTR verse at {verse_id}: {key}')
                scores[key] = score
    return scores


FOOTNOTE_REGEX = re.compile( '\\\\f (.+?)\\\\f\\*')
def get_OSHB_reference_text_critical_footnote_score( verseEntryList, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the Hebrew reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
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
                        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  get_OSHB_reference_text_critical_footnote_score for {BBB}_{C}:{V} accepted {fnText=}" )
                        havePossibleBHSReference = True
                        break
                startIndex = match.end()
            if havePossibleBHSReference:
                break
    return 1 if havePossibleBHSReference else False
# end of initialise.get_OSHB_reference_text_critical_footnote_score function


def get_UHB_Hebrew_reference_text_critical_footnote_score( verseEntryList, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the Hebrew reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
    haveEarlyTranslationReference = False
    for entry in verseEntryList:
        text = entry.getOriginalText()
        if text:
            if '\\ft K ' in text or '\\ft Q ' in text: return 2
            # if 'LXX' in text or 'Syriac' in text or 'Peshitta' in text or 'Dead Sea Scrolls' in text or 'Targum' in text or 'Vulgate' in text:
            #     haveEarlyTranslationReference = True # return 1 Can't return straight away because next line might contain a TC footnote
    return 1 if haveEarlyTranslationReference else False
# end of initialise.get_UHB_Hebrew_reference_text_critical_footnote_score function


def get_English_reference_text_critical_footnote_score( verseEntryList, BBB:str, C:str, V:str ) -> int:
    """
    Returns 2 (stronger) if the English reference Bible has a TC footnote for this verse.
    Returns 1 (weaker) if no TC footnote, but the LXX or similar is mentioned
    """
    haveEarlyTranslationReference = False
    for entry in verseEntryList:
        text = entry.getOriginalText()
        if text:
            if 'Textual Criticism' in text: return 2
            if 'LXX' in text or 'Syriac' in text or 'Peshitta' in text or 'Dead Sea Scrolls' in text or 'Targum' in text or 'Vulgate' in text:
                haveEarlyTranslationReference = True # return 1 Can't return straight away because next line might contain a TC footnote
    return 1 if haveEarlyTranslationReference else False
# end of initialise.get_reference_English_text_critical_footnote_score function


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


def get_speakers_from_verse_text( rawVerseText:str, default_speaker='@' ) -> str:
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
        return ','.join(deduplicate_staying_ordered([*default_speaker.split(','), *names]))

    # Step through the verse, alternating between the \wj blocks (words of Yeshua)
    # and the narrator's narration surrounding them.
    speakers = []
    previousEnd = 0
    for match in WJ_BLOCK_REGEX.finditer( text ):
        wjStart, wjEnd = match.start(), match.end()
        narrationText = to_plain_text( text[previousEnd:wjStart] )
        if has_narration( narrationText ):
            speakers.extend(default_speaker.split(','))
            # A 'Yeshua' detected in narration right next to a \wj block is just
            # an attribution ('... answered Yeshua,'), so don't repeat it
            speakers.extend( name for name in detect_other_speakers( narrationText ) if name != 'Yeshua' )
        speakers.append( 'Yeshua' )
        previousEnd = wjEnd
    trailingText = to_plain_text( text[previousEnd:] )
    if has_narration( trailingText ):
        speakers.extend(default_speaker.split(','))
        speakers.extend( name for name in detect_other_speakers( trailingText ) if name != 'Yeshua' )
    return ','.join( deduplicate_consecutive( speakers ) )
# end of initialise.get_speakers_from_verse_text function


PSALM_AUTHOR_NAMES = {
    'David':'David', 'Dāvid':'David', 'Asaf':'Asaf', 'ʼĀsāf':'Asaf', 'ʼĀşāf':'Asaf',
    'Shelomoh':'Shelomoh', 'Solomon':'Shelomoh', 'Shəlomoh':'Shelomoh',
    'Mosheh':'Mosheh', 'Mōsheh':'Mosheh', 'Heyman':'Heyman', 'Hēmān':'Heyman', 'Hēymān':'Heyman',
    'Eytan':'Eytan', 'ʼĒytān':'Eytan',
}


def literal_plain_text(text):
    """Remove LV word-joining characters, retaining words and name diacritics."""
    return re.sub(r'\s+', ' ', to_plain_text(text).translate(str.maketrans(dict.fromkeys('_÷=+>#',' ')))).strip()


def psalm_author(title, literal=False):
    """Read attribution grammar, never infer authorship from a name mentioned."""
    text = literal_plain_text(title) if literal else to_plain_text(title).replace('#','')
    names = '|'.join(map(re.escape, PSALM_AUTHOR_NAMES))
    author = rf"(?:Korah['’]s descendants|(?:the )?(?:sons|children) of (?:of )?(?:Qōraḩ|Qoraḩ|Korah)|{names})"
    qualifier = r"(?:(?:Yahweh['’]s servant|God['’]s man|King)\s+)?"
    patterns = (
        rf'\bby\s+{qualifier}({author})\b',
        rf'\b(?:song|psalm|prayer|poem)\s+(?:of|by)\s+{qualifier}({author})\b',
        rf"({author})['’]s\s+(?:songs?|psalms?|prayers?)\b",
        rf'^(?:Of|of|To|to|For|for)\s+({author})\b' if literal else r'(?!)',
        # Literal title syntax can separate the genre and attribution with
        # "the ascents", "the dedication of the house", etc. This rule is
        # only applied to the verified title, never the Psalm's body.
        rf'\bof\s+({author})\b' if literal else r'(?!)',
    )
    found = sorted((match.start(),match[1]) for pattern in patterns for match in re.finditer(pattern,text))
    return ','.join(deduplicate_staying_ordered(
        PSALM_AUTHOR_NAMES.get(name,"Korah's descendants") for _,name in found)) or None


def raw_verse_texts(path):
    """Minimal native text reader for LV title evidence (no English renumbering)."""
    records = {}
    chapter = key = None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('\\c '):
            chapter, key = line.split()[1], None
        elif line.startswith('\\v '):
            label, *bits = line[3:].split(maxsplit=1)
            key = (chapter,label)
            records[key] = ' '.join(bits)
        elif key and not re.match(r'^\\(?:s\d|r|rem|ms\d?|mr|cl|cd|qa)\b',line):
            records[key] += ' ' + line
    return records


def psalm_heading_evidence(rv_path, lv_path, audit):
    """Find authors and verify titles sharing LV verse 1 with the body.

    A numbered title is mapped normally. For a title inside verse 1, require
    the LV's explicit KJB boundary note and shared RV/LV source-word numbers;
    do not invent a verse-zero mapping. An RV heading takes precedence over
    LV corroboration; discrepancies are recorded for editorial review.
    """
    audit.input_file(lv_path)
    literal = raw_verse_texts(lv_path)
    authors, mixed = {}, set()
    chapter = None
    for line in Path(rv_path).read_text(encoding='utf-8').splitlines():
        if line.startswith('\\c '):
            chapter = line.split()[1]
        elif line.startswith('\\d '):
            rv_title = line[3:]
            mapping = get_default_mapping_engine().convert_passage('OET-RV','OET-LV',(('PSA',chapter,'0',None),))
            if mapping.status == MappingStatus.EXACT:
                lv_title = ' '.join(literal[C,V] for _,C,V,_ in mapping.references)
            elif any(d.code == 'UNDECLARED_TITLE' for d in mapping.diagnostics):
                first = literal[chapter,'1']
                boundary = re.search(r'\\f\s[^\n]*?\\ft Note: KJB: Ps\.'+chapter+r'\.1\\f\*',first)
                lv_title = first[:boundary.start()] if boundary else ''
                shared = set(WORD_NUMBER_REGEX.findall(rv_title)) & set(WORD_NUMBER_REGEX.findall(lv_title))
                if lv_title and shared and has_narration(to_plain_text(first[boundary.end():])):
                    mixed.add(chapter)
            else:
                raise ValueError(f'Psalm title {chapter}: {VersificationMappingError(mapping)}')
            rv_author, lv_author = psalm_author(rv_title), psalm_author(lv_title,literal=True)
            selected = rv_author or lv_author
            if selected:
                authors[chapter] = selected
                audit.speaker_evidence[f'PSA {chapter} author'] = {
                    'speaker':selected, 'OET-RV':to_plain_text(rv_title),
                    'OET-LV':literal_plain_text(lv_title), 'LV_author':lv_author,
                    'mixed_title_and_body':chapter in mixed}
    return authors, mixed


# Reviewed native OET-RV section boundaries. Check the source's own attribution
# before applying it. Collectors (e.g. Hezekiah's men) are not the speakers.
# The final anonymous poem is a new section, not a continuation by Lemuel's mother.
PROVERB_SECTIONS = {
    ('1','1'): ('Shelomoh',r'proverbs.*Solomon',True),
    ('10','1'): ('Shelomoh',r'proverbs by Shelomoh',True),
    ('22','17'): ('The wise',r'wise.*people',False),
    ('24','23'): ('The wise',r'sayings of the wise',True),
    ('25','1'): ('Shelomoh',r'proverbs from Shelomoh',True),
    ('30','1'): ('Agur',r'sayings.*Agur',True),
    ('31','1'): ("Lemuel's mother",r'Lemuel.*mother.*taught',True),
    ('31','10'): ('@',r'capable.*wife',False),
}


def read_speakers(path, BBB, *, detailed=False, psalm_authors=None):
    r"""Read native verse labels, bridges, suffixes and Psalm \d titles.

    OET's a/b source segments are recombined into the whole native verse here;
    they are unrelated to the dataset's editorial halves. Flush before section
    and speaker changes, retaining every within-verse speaker run. A run is
    (speaker list, kind); exactly two explicit runs can later form editorial
    a/b rows. Textual attribution guesses do not establish a split boundary.
    """
    records = {}
    chapter = None
    pending = ()
    bits = []
    speaker = verse_speaker = None
    author = '@'
    kind = 'body'

    def flush_segment():
        nonlocal bits
        if pending and has_narration(to_plain_text(' '.join(bits))):
            value = verse_speaker or get_speakers_from_verse_text(' '.join(bits),author)
            for ref in pending:
                records.setdefault(ref,[]).append((value,kind))
        bits = []

    def flush():
        nonlocal pending
        flush_segment()
        pending = ()

    with Path(path).open(encoding='utf-8') as source:
        for line in source:
            line = line.rstrip()
            if line.startswith('\\c '):
                flush()
                chapter = line.split()[1]
                if BBB == 'PSA':
                    author = (psalm_authors or {}).get(chapter,'@')
                    speaker = None
            elif line.startswith('\\v '):
                flush()
                label, *text = line[3:].split(maxsplit=1)
                # Physical source suffixes partition the same whole verse.
                label = re.sub(r'(?<=\d)[a-z]', '', label)
                pending, _ = expand_reference(f'{BBB}_{chapter}:{label}', 'OET-RV')
                verse_speaker = speaker
                bits = text
                kind = 'body'
                if BBB == 'PRO' and (chapter,label) in PROVERB_SECTIONS:
                    author, evidence, heading = PROVERB_SECTIONS[chapter,label]
                    if not re.search(evidence,to_plain_text(' '.join(bits)),re.IGNORECASE):
                        raise ValueError(f'PRO {chapter}:{label}: author-section evidence changed')
                    if heading:
                        verse_speaker, kind = '@', 'title'
                        flush_segment() # Remaining lines of this verse belong to the body.
                        verse_speaker, kind = speaker, 'body'
            elif line.startswith('\\d '):
                flush()
                pending = ((BBB,chapter,'0',None),)
                verse_speaker, kind = '@', 'title'
                bits = [line[3:]]
                if BBB == 'PSA' and psalm_authors is None:
                    author = psalm_author(line[3:]) or '@'
            elif line.startswith('\\s1 '):
                flush()
                speaker = None
            elif line.startswith('\\sp '):
                flush_segment() # Keep pending refs for speech later in the SAME verse.
                speaker = verse_speaker = to_plain_text(line[4:])
                kind = 'explicit speaker'
            elif pending and not re.match(r'^\\(?:s\d|r|rem|ms\d?|mr|cl|cd|qa)\b', line):
                bits.append(line)
    flush()
    return records if detailed else {ref:','.join(deduplicate_consecutive(
        [name for value,_ in runs for name in value.split(',')])) for ref,runs in records.items()}


def load_OET_RV_speakers(audit, source_folder=OET_RV_PATHNAME, *, existing_splits=(),
                         lv_psalm_path=OET_LV_OT_PATHNAME / 'OET-LV_PSA.ESFM'):
    """Map OET-RV speaker sequences into org; scope is its reviewed 66 books."""
    records = {}
    authors, mixed_titles = psalm_heading_evidence(source_folder/'OET-RV_PSA.ESFM',lv_psalm_path,audit)
    for BBB in get_default_mapping_engine().get_legacy_tables('OET-RV')['CV']:
        path = source_folder / f'OET-RV_{BBB}.ESFM'
        if not path.is_file():
            raise FileNotFoundError(f'Missing required OET-RV speaker source: {path}')
        audit.input_file(path)
        records.update(read_speakers(path, BBB, detailed=True, psalm_authors=authors))
    # These headings have no separate org verse. LV word evidence above proves
    # they precede the body inside verse 1, so carry that narrator run with it.
    for chapter in mixed_titles:
        title, body = ('PSA',chapter,'0',None), ('PSA',chapter,'1',None)
        records[body] = [*records.pop(title), *records[body]]
    result = {}
    visited = set()
    for ref in records:
        if ref[2] == '0':
            title = get_default_mapping_engine().convert('OET-RV','OET-RV',(ref,))
            if title.diagnostics and all(d.code == 'UNDECLARED_TITLE' for d in title.diagnostics):
                # A source heading without a separate org scripture address.
                # Do not attach it to the following numbered verse by guesswork.
                audit.editorial_titles.add(fgref(ref))
                continue
        keys = audit.convert('OET-RV', (ref,), 'OET-RV speakers')
        if not keys:
            continue # reviewed source-only verse
        mapping = mapped_references('OET-RV', (ref,))
        group = mapping.source_references
        if group in visited:
            continue
        visited.add(group)
        missing = [source_ref for source_ref in group if source_ref not in records]
        if missing:
            raise ValueError(f'OET-RV speaker mapping requires missing native verses: {missing}')
        runs = [run for source_ref in group for run in records[source_ref]]
        speakers = ','.join(deduplicate_consecutive(
            [name for value,_ in runs for name in value.split(',')]))
        for key in keys:
            if key in result and result[key] != speakers:
                raise ValueError(f'Conflicting speaker groups at org {key}')
            result[key] = speakers
        distinct = [value for value,_ in groupby(value for value,_kind in runs)]
        if len(distinct) == 2:
            if len(group) == len(keys) == 1 and keys[0] not in existing_splits:
                key = keys[0]
                result[key+'a'], result[key+'b'] = distinct
                audit.speaker_splits[key] = {'source':fgref(ref),'speakers':distinct,
                    'reason':'two explicit text runs (heading/body or speaker change)'}
                audit.comments[key].add(f'Speaker portions: a={distinct[0]}; b={distinct[1]} '
                    f'(two explicit text runs in OET-RV {fgref(ref)})')
            else:
                audit.speaker_unsplit[fgref(ref)] = 'Existing curated halves or indivisible mapping group; retained complete speaker list'
    return result


LV_PERSON_NAMES = {'Jesus':'Yeshua', 'John':'Yohan', 'Peter':'Petros',
                   'James':'Yacob', 'Moses':'Mosheh', 'Solomon':'Shelomoh'}
LV_SPEECH_REGEX = re.compile(r'\b(?:said|says|say|saying|speaks?|speaking|spoken|'
    r'answered|answering|replied|replying|declared|declaring|cried_out|shouted)\b')


def supplement_LV_speakers(speakers, audit, path=OET_LV_NT_WORD_TABLE):
    """Use person/referent tags ON a speech verb with an explicit subject.

    NT OET-LV word rows carry Macula pronoun referents (R...) and their person
    identities (P...). A person tag on an ordinary noun is not speaker evidence.
    Require a first/third-person subject in the gloss and a speech verb; avoid
    second-person addresses, infinitives and generic references to speaking.
    This remains a conservative fallback for whole verses still marked only @.
    Never overwrite an RV speaker, a narrator heading or an editorial half.
    """
    audit.input_file(path)
    native = defaultdict(list)
    evidence = defaultdict(list)
    with Path(path).open(encoding='utf-8') as source:
        reader = DictReader(source,delimiter='\t')
        required = {'Ref','Role','OETGlossWords','Tags'}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError(f'{path}: missing LV speaker evidence columns')
        for row in reader:
            gloss, tags = row['OETGlossWords'], row['Tags'].split(';')
            if (row['Role'] != 'V' or not LV_SPEECH_REGEX.search(gloss)
                    or not re.search(r'˱(?:he|she|they|I|we)˲',gloss)
                    or not any(re.fullmatch(r'R\d+',tag) for tag in tags)):
                continue
            names = [re.sub(r'\d+$','',tag[1:]).replace('_',' ')
                     for tag in tags if re.fullmatch(r'P[A-Za-z][A-Za-z_\d]*',tag)]
            names = [LV_PERSON_NAMES.get(name,name) for name in names]
            if not names:
                continue
            reference = row['Ref'].split('w')[0]
            refs,half = expand_reference(reference,'OET-LV')
            if len(refs) != 1 or half:
                raise ValueError(f'Invalid LV speech word reference: {row["Ref"]}')
            native[refs[0]].extend(names)
            evidence[refs[0]].append(f'{row["Ref"]}: {gloss}; {row["Tags"]}')
    visited = set()
    for ref in native:
        mapping = mapped_references('OET-LV',(ref,))
        keys = audit.convert('OET-LV',(ref,),'OET-LV tagged speech')
        if not keys or mapping.source_references in visited:
            continue
        visited.add(mapping.source_references)
        names = deduplicate_staying_ordered([name for source_ref in mapping.source_references
                                             for name in native.get(source_ref,())])
        for key in keys:
            if speakers.get(key,'@') == '@' and key+'a' not in speakers:
                speakers[key] = '@,' + ','.join(names)
                audit.speaker_evidence[key] = {'speaker':speakers[key], 'source_profile':'OET-LV',
                    'word_evidence':[item for source_ref in mapping.source_references
                                     for item in evidence.get(source_ref,())]}
    return speakers


def net_profile(BBB):
    """The local NET USX's actual numbering, checked against boundary text.

    NET explicitly describes NA/UBS numbering in its 2 Corinthians 13:12 note;
    3 John has 15 verses, Revelation 12 has 18, and PHP 1:16 is loving preaching.
    Acts alone retains the English 19:40-41 division. OT uses English numbers.
    """
    return 'org' if bos_books_codes_py.is_new_testament_nr(BBB) and BBB != 'ACT' else 'eng'


@contextmanager
def prepared_source(label, folder, audit):
    """Restore NET's printed 1:17 label in a temporary copy, never source data.

    The old Jonah USX has <para>1:17 <char style="va">(2:1)</char>...
    instead of a verse element. BOS otherwise attaches that paragraph to 1:16.
    This is a verified storage repair, not a hand-written versification mapping.
    """
    if label != 'NET':
        yield folder
        return
    with tempfile.TemporaryDirectory(prefix='sentence-importance-net-') as temporary:
        prepared = Path(temporary)
        for path in sorted(folder.glob('*.usx')):
            shutil.copy2(path,prepared/path.name)
            tree = ElementTree.parse(path)
            root = tree.getroot()
            BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code(root.find('book').get('code'))
            chapter = verse = None
            present, notes = set(), defaultdict(list)
            for element in root.iter():
                if element.tag == 'chapter' and element.get('number'):
                    chapter,verse = element.get('number'),None
                elif element.tag == 'verse' and element.get('number'):
                    verse = element.get('number')
                    present.add((BBB,chapter,verse))
                elif element.tag == 'note':
                    notes[(BBB,chapter,verse)].append(''.join(element.itertext()))
            for omitted,note_verse in NET_OMISSION_NOTES.items():
                if omitted[0] != BBB or omitted in present:
                    continue
                _,C,V = omitted
                note_ref = (BBB,C,note_verse)
                evidence = [note for note in notes[note_ref] if 'Textual Criticism' in note
                            and re.search(rf'\b{C}:{V}\b|\bverses? {V}\b',note,re.IGNORECASE)]
                if not evidence:
                    raise ValueError(f'{path}: missing NET {fgref(omitted)} without its reviewed TC note at {fgref(note_ref)}')
                audit.net_omissions[(*omitted,None)] = fgref(note_ref)
            if root.find('book').get('code') != 'JON':
                continue
            chapter = None
            repaired = False
            for element in root:
                if element.tag == 'chapter':
                    chapter = element.get('number')
                if (chapter == '1' and element.tag == 'para' and element.text == '1:17 '
                        and len(element) and element[0].tag == 'char'
                        and element[0].get('style') == 'va' and element[0].text == '(2:1)'):
                    element.text = None
                    element.insert(0,ElementTree.Element('verse',number='17',style='v'))
                    repaired = True
            if repaired:
                tree.write(prepared/path.name,encoding='utf-8',xml_declaration=True)
                note = 'NET USX source repair: restored explicit Jonah 1:17 marker from printed 1:17 (2:1) label'
                audit.source_repairs.add(note)
                audit.comments['JNA_2:1'].add(note)
                logging.warning(note)
        yield prepared


def score_bible(bible, profile_for_book, scorer, references, audit, label):
    """Map each output verse to all corresponding native portions before scoring."""
    scores = {}
    chapter_cache = {}
    group_scores = {}
    for ref in references:
        BBB,C,V,_ = ref
        if BBB not in bible.books:
            continue # Explicit source scope: e.g. UHB/OET-LV OT have no NT/DC.
        profile = profile_for_book(BBB)
        mapping = get_default_mapping_engine().convert_passage(OUTPUT_PROFILE, profile, (ref,))
        if mapping.status != MappingStatus.EXACT:
            raise ValueError(f'{label}: org {fgref(ref)} -> {profile}: {VersificationMappingError(mapping)}')
        if mapping.is_expanded or len(mapping.references) > 1:
            note = (f'{label}: shared annotation from {profile} '
                    f'{", ".join(map(fgref, mapping.references))} '
                    f'to org {", ".join(map(fgref, mapping.source_references))}')
            for output_ref in mapping.source_references:
                audit.comments[fgref(output_ref)].add(note)
        group = mapping.references
        if group not in group_scores:
            # NET/UHB unnumbered titles may contain no stored text. Only these
            # explicitly mapped title coordinates may be absent without error.
            entries = []
            minimum_score = 0
            for native_ref in group:
                try:
                    portions = bible.getPassageData((native_ref,), chapterCache=chapter_cache)
                except KeyError:
                    if label == 'NET' and native_ref in audit.net_omissions:
                        minimum_score = 2
                        note = (f'NET omits {fgref(native_ref)}; textual-criticism evidence at '
                                f'{audit.net_omissions[native_ref]} ({profile})')
                        for output_ref in mapping.source_references:
                            audit.comments[fgref(output_ref)].add(note)
                        continue
                    if native_ref[2] != '0':
                        raise ValueError(f'{label}: org {fgref(ref)} maps to missing {profile} {fgref(native_ref)}')
                    continue
                entries.extend(entry for portion in portions for entry in portion.entries)
            group_scores[group] = str(max(minimum_score,int(scorer(entries, BBB,C,V))))
        scores[fgref(ref)] = group_scores[group]
    return scores


def annotation_value(values, key, ranks, default):
    """Whole-verse annotations apply to both editorial halves; strongest wins."""
    parent = key[:-1] if key[-1] in 'ab' else key
    return max(values.get(key,default), values.get(parent,default), key=ranks.index)


def build_rows(references, curated, quotes, collation, oshb, uhb, net, speakers, audit):
    importance, textual, clarity = curated
    split = {key[:-1] for values in (*curated,speakers) for key in values if key[-1] in 'ab'}
    inventory = {fgref(ref) for ref in references}
    for label,values in (('importance',importance), ('textual issue',textual), ('clarity',clarity),
                         ('quotations',quotes), ('CNTR',collation), ('OET-LV',oshb),
                         ('UHB',uhb), ('NET',net), ('speakers',speakers)):
        outside = {key for key in values if (key[:-1] if key[-1] in 'ab' else key) not in inventory}
        if outside:
            raise ValueError(f'{label}: mapped annotations outside output inventory: {sorted(outside)}')
    rows = []
    for ref in references:
        parent = fgref(ref)
        for key in (parent+'a',parent+'b') if parent in split else (parent,):
            # Explicit T replaces default M, but quotes can promote T back to M.
            imp = annotation_value(importance,key,'TMIV','T') if key in importance or parent in importance else 'M'
            imp = max(imp, quotes.get(parent,'T'), key='TMIV'.index)
            tc = max(annotation_value(textual,key,'0123','0'), collation.get(parent,'0'),
                     oshb.get(parent,'0'), uhb.get(parent,'0'), net.get(parent,'0'))
            cl = annotation_value(clarity,key,'CUO','C')
            comment = '; '.join(sorted(audit.comments.get(parent,())))
            rows.append((key,imp,tc,cl,speakers.get(key,speakers.get(parent,'@')),comment))
    return rows


def write_database(rows, audit, output=TSV_FILENAME, report_path=REPORT_FILENAME):
    """Validate everything before replacing the database; retain a full backup."""
    keys = set()
    for row in rows:
        if (len(row) != 6 or row[0] in keys or row[1] not in ('T','M','I','V')
                or row[2] not in ('0','1','2','3') or row[3] not in ('C','U','O') or not row[4]
                or any('\t' in field or '\n' in field for field in row)):
            raise ValueError(f'Invalid/duplicate output row: {row}')
        keys.add(row[0])
    content = HEADER + ''.join('\t'.join(row)+'\n' for row in rows)
    identity = get_default_mapping_engine().convert('org','org',(('GEN','1','1'),))
    report = {
        'output_versification': OUTPUT_PROFILE,
        'reference_version': identity.reference_version,
        'mapping_data_revision': identity.data_revision,
        'mapping_policy_version': identity.mapping_policy_version,
        'source_profiles': {'curated':CURATED_PROFILE, 'quotations':'eng, with QUOTE_PROFILES overrides',
                            'UHB':'eng', 'OET-LV OT':'OET-LV', 'NET':'eng OT/Acts; org other NT',
                            'CNTR':CNTR_PROFILE, 'speakers':'OET-RV; OET-LV title and tagged-speech evidence'},
        'speaker_evidence': audit.speaker_evidence,
        'speaker_editorial_splits': audit.speaker_splits,
        'speaker_unsplit_boundaries': audit.speaker_unsplit,
        'seed_removed': sorted(map(fgref, SEED_REMOVED)),
        'seed_added': sorted(map(fgref, SEED_ADDED)),
        'omitted_source_annotations': sorted(audit.omitted),
        'unnumbered_OET_RV_headings_without_title_coordinate': sorted(audit.editorial_titles),
        'temporary_source_repairs': sorted(audit.source_repairs),
        'NET_omitted_verses_with_TC_note': {fgref(ref):note for ref,note in sorted(audit.net_omissions.items())},
        'input_sha256': dict(sorted(audit.inputs.items())),
        'output_sha256': hashlib.sha256(content.encode('utf-8')).hexdigest(),
        'data_rows': len(rows),
        'whole_verses': len({key[:-1] if key[-1] in 'ab' else key for key in keys}),
        'rows_with_group_comments': sum(bool(row[-1]) for row in rows),
    }
    # Stage both files first. A mapping/read/validation failure above leaves the
    # existing database untouched. replace() is atomic within this filesystem.
    staged = []
    try:
        for destination, text in ((Path(output),content),
                (Path(report_path),json.dumps(report,ensure_ascii=False,indent=2)+'\n')):
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=destination.parent,
                                             prefix=destination.name+'.',suffix='.tmp',delete=False) as handle:
                handle.write(text)
                staged.append((Path(handle.name),destination))
        if Path(output).exists():
            backup = Path(str(output)+'.bak-before-regeneration')
            # Never overwrite the first pre-regeneration snapshot on repeat runs.
            if not backup.exists():
                shutil.copy2(output,backup)
        for temporary,destination in staged:
            temporary.chmod(0o664)
            temporary.replace(destination)
    finally:
        for temporary,_ in staged:
            temporary.unlink(missing_ok=True)
    vPrint('Quiet',DEBUGGING_THIS_MODULE,f'Wrote {len(rows):,} data rows in org versification to {output}')
    return report


def run():
    audit = MappingAudit()
    audit.input_file(Path(__file__))
    audit.input_file(SEED_FILENAME)
    references = load_original_inventory()
    curated = setup(audit)
    quotes = load_quoted_OT_annotations(audit)
    collation = load_CNTR_collation_DB(audit)
    existing_splits = {key[:-1] for values in curated for key in values if key[-1] in 'ab'}
    speakers = load_OET_RV_speakers(audit,existing_splits=existing_splits)
    supplement_LV_speakers(speakers,audit)
    score_tables = []
    # Load and release one source at a time to keep regeneration memory bounded.
    for label,folder,loader,profile,scorer,extension in (
        ('OET-LV OT',OET_LV_OT_PATHNAME,ESFMBible.ESFMBible,lambda BBB:'OET-LV',get_OSHB_reference_text_critical_footnote_score,'.ESFM'),
        ('UHB',UHB_PATHNAME,USFMBible.USFMBible,lambda BBB:'eng',get_UHB_Hebrew_reference_text_critical_footnote_score,'.usfm'),
        ('NET',NET_PATHNAME,USXXMLBible.USXXMLBible,net_profile,get_English_reference_text_critical_footnote_score,'.usx'),
    ):
        if not folder.is_dir():
            raise FileNotFoundError(f'Missing {label} source directory: {folder}')
        source_files = sorted(path for path in folder.iterdir() if path.suffix.lower()==extension.lower())
        if not source_files:
            raise FileNotFoundError(f'No {label} {extension} source files in {folder}')
        for path in source_files:
            audit.input_file(path)
        vPrint('Normal',DEBUGGING_THIS_MODULE,f'Loading and mapping {label} annotations…')
        with prepared_source(label,folder,audit) as source_folder:
            bible = loader(source_folder,givenAbbreviation=label)
            if label == 'UHB':
                bible.uWencoded = True # Required for unfoldingWord's word markup.
            bible.loadBooks()
            expected_books = {ref[0] for ref in references if bos_books_codes_py.is_old_testament_nr(ref[0])
                              or label=='NET' and bos_books_codes_py.is_new_testament_nr(ref[0])}
            missing_books = expected_books-set(bible.books)
            if missing_books:
                raise ValueError(f'{label} missing required books: {sorted(missing_books)}')
            score_tables.append(score_bible(bible,profile,scorer,references,audit,label))
            del bible
    rows = build_rows(references,curated,quotes,collation,*score_tables,speakers,audit)
    return write_database(rows,audit)


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    run()
# end of initialise.briefDemo()

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

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
