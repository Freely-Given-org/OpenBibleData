#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# settings.py
#
# Module handling OpenBibleData settings functions
#
# Copyright (C) 2023-2025 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
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
Module handling settings functions.

CHANGELOG:
    2024-01-11 Load all OET-LV NT books
    2024-04-05 Add more acknowledgements for the OT part
    2024-04-18 Added AICNT (have emailed permission)
    2024-04-25 Added some Moffat books
    2024-05-06 Added some NETS verses
    2024-06-25 Added BibleMapper copyright details
    2024-09-23 Change OET OT book order
    2024-10-24 Change WEB and WMB to British spelling WEBBE and WMBB
    2024-11-01 Added topics pages
    2025-06-29 v0.41 Added SLT
    2025-07-05 v0.42 Added HAP (links)
    2025-08-24 Move rest of settings into State
    2025-09-02 Added RP (Byz) GNT
    2025-09-26 Added MSB
"""
from pathlib import Path

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import dPrint, fnPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39


LAST_MODIFIED_DATE = '2025-10-30' # by RJH
SHORT_PROGRAM_NAME = "settings"
PROGRAM_NAME = "OpenBibleData (OBD) Settings"
PROGRAM_VERSION = '0.99'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False # Adds debugging output


class State:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    OET_VERSION_NUMBER_STRING = 'v0.45.44' # Incremented on most runs

    TEST_MODE_FLAG = True # Writes website into 'Test' subfolder if True
    TEST_OT_BOOK_LIST = ['CH2','PRO'] # Books in progress
    TEST_NT_BOOK_LIST = ['MRK'] # Shortest gospel
    NEW_BOOK_IN_TEST_LIST_FLAG = False # So that word pages will get rebuilt for TEST_MODE_FLAG

    # Many of these settings are used to omit some processing so as to get a speedier conclusion for debugging
    TEST_VERSIONS_ONLY = None #['OET','OET-RV','OET-LV', 'RV', 'KJB-1611', 'TOSN','UTN'] # Usually None. Also stops actual site being built
    ALL_PRODUCTION_BOOKS_FLAG = not TEST_MODE_FLAG # If set to False, uses the TEST book list (with many less books) for a faster test build
    CREATE_PARALLEL_VERSE_PAGES = 'LAST' # 'FIRST','LAST', or None -- depending on debugging needs
    CREATE_BOOK_AND_OTHER_PAGES_FLAG = True # Can be turned off for debugging
    DO_SPELL_CHECKS_FLAG = True #TEST_MODE_FLAG # On parallel pages
    REUSE_EXISTING_WORD_PAGES_FLAG = TEST_MODE_FLAG and not NEW_BOOK_IN_TEST_LIST_FLAG # Don't recreate word pages
    ALL_TEST_REFERENCE_PAGES_FLAG = False # If in TEST_MODE_FLAG, make ALL word/lemma pages, or just the RELEVANT ones
    UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG = True # The pages are initially built in a tmp folder so need to be copied to the final destination

    OET_RV_OT_BOOK_LIST = ['GEN','EXO','JOS','JDG','RUT',
                    'SA1','SA2','KI1','KI2','CH1','CH2',
                    'EZR','NEH','EST','JOB','PSA','PRO','ECC','SNG','LAM',
                    'EZE','DAN','HOS','JOL','AMO','OBA','JNA',
                    'MIC','NAH','HAB','ZEP','HAG','ZEC','MAL'] # 'LEV','NUM','DEU','ISA','JER'

    TEMP_BUILD_FOLDER = Path( '../buildingHtmlPages/' )
    NORMAL_DESTINATION_FOLDER = Path( '../htmlPages/' )
    DEBUG_DESTINATION_FOLDER = NORMAL_DESTINATION_FOLDER.joinpath( 'Test/' )
    DESTINATION_FOLDER = DEBUG_DESTINATION_FOLDER if TEST_MODE_FLAG or BibleOrgSysGlobals.debugFlag \
                            else NORMAL_DESTINATION_FOLDER

    SITE_NAME = 'Open Bible Data'
    SITE_ABBREVIATION = 'OBD'

    # We use a rough logical, then chronological 'book' order
    # For the OT, we keep SA1/SA2, etc. together (as a single document) rather than splitting them chronologically
    OET_OT_BOOK_ORDER = ['GEN','EXO','LEV','NUM','DEU',
                            'JOB', # Where does this belong?
                            'JOS','JDG','RUT',
                            'SA1','SA2', 'PSA', 'AMO','HOS',
                            'KI1','KI2', 'CH1','CH2', 'PRO','ECC','SNG',
                            'JOL', 'MIC', 'ISA', 'ZEP', 'HAB', 'JER','LAM',
                            'JNA', 'NAH', 'OBA',
                            'DAN', 'EZE',
                            'EZR','EST','NEH', 'HAG','ZEC','MAL',
                            ]
    assert len(OET_OT_BOOK_ORDER) == 39
    # The following are not necessarily all included in the OET
    OET_APOCRYPHA_BOOK_ORDER = ['LAO',
                            'GES','LES','ESG','DNG','PS2',
                            'TOB','JDT','ESA','WIS','SIR','BAR','LJE','PAZ','SUS','BEL','MAN',
                            'MA1','MA2','MA3','MA4',
                            'GLS']
    # For the NT, we put JHN first as a parallel to GEN, then ACT ends up better because immediately following LUK
    OET_NT_BOOK_ORDER = ['JHN','MRK','MAT','LUK','ACT',
                            'JAM', 'GAL', 'TH1','TH2', 'CO1','CO2', 'ROM', 'COL', 'PHM', 'EPH', 'PHP',
                            'TI1','TIT', 'PE1','PE2',
                            'TI2', 'HEB', 'JDE',
                            'JN1','JN2','JN3', 'REV']
    assert len(OET_NT_BOOK_ORDER) == 27
    OET_BOOK_ORDER = ['FRT','INT'] + OET_OT_BOOK_ORDER + OET_APOCRYPHA_BOOK_ORDER + OET_NT_BOOK_ORDER + ['XXA','XXB','XXC','XXD','XXE','CNC','GLO','TDX','NDX','OTH','BAK']
    assert len(OET_BOOK_ORDER) > 68

    TEST_BOOK_LIST = TEST_OT_BOOK_LIST + TEST_NT_BOOK_LIST
    OET_LV_BOOK_LIST = BOOKLIST_OT39 + OET_NT_BOOK_ORDER
    OET_RV_BOOK_LIST = TEST_BOOK_LIST if TEST_MODE_FLAG else (OET_RV_OT_BOOK_LIST + OET_NT_BOOK_ORDER)
    # TODO: What about 'INT' ?
    OET_RV_BOOK_LIST_WITH_FRT = ['FRT'] + OET_RV_BOOK_LIST

    # The version to link to when the OET doesn't have that book (yet)
    ALTERNATIVE_VERSION = 'WEB' # Should be a version with all books present

    VERSIONS_WITHOUT_NT = ['UHB','JPS', 'BrLXX','BrTr']
    VERSIONS_WITHOUT_OT = ['BLB','AICNT','TCNT','TNT','Wymth', 'SR-GNT','UGNT','SBL-GNT','TC-GNT']
    VERSIONS_WITH_APOCRYPHA = ( 'KJB-1611', 'WEBBE','WEB', 'BrLXX','BrTr')

    NUM_EXTRA_MODES = 7 # Related passages, topics, parallel and interlinear verses, reference and (Tyndale Bible) dictionary, and search

    OET_UNFINISHED_WARNING_HTML_TEXT = 'This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.'
    OET_UNFINISHED_WARNING_HTML_PARAGRAPH = f'<p class="rem">{OET_UNFINISHED_WARNING_HTML_TEXT}</p>'
    OET_SINGLE_VERSE_HTML_TEXT = 'This view shows ‘verses’ which are not natural language units and hence sometimes only part of a sentence will be visible. Normally the OET discourages the reading of individual ‘verses’, but this view is only designed as a tool for doing comparisons of different translations.'
    OETS_UNFINISHED_WARNING_HTML_TEXT = 'The OET segments on this page are still very early looks into the unfinished texts of the <em>Open English Translation</em> of the Bible. Please double-check these texts in advance before using in public.'
    # OETS_UNFINISHED_WARNING_HTML_PARAGRAPH = f'<p class="rem">{OETS_UNFINISHED_WARNING_HTML_TEXT}</p>'

    JAMES_NOTE_HTML_TEXT = 'Note that the <em>OET</em> uses ‘Yacob’ for ‘The Letter of Jacob’ (wrongly called ‘James’ in older Bibles).'
    JAMES_NOTE_HTML_PARAGRAPH = f'<p class="rem">{JAMES_NOTE_HTML_TEXT}</p>'

    BLACK_LETTER_FONT_HTML_TEXT = 'Note that this page will look best (more authentic) if you’ve downloaded a black-letter font like <a href="https://fonts.google.com/specimen/UnifrakturCook">Google’s UnifrakturCook</a>.'
    BLACK_LETTER_FONT_HTML_PARAGRAPH = f'<p class="rem">{BLACK_LETTER_FONT_HTML_TEXT}</p>'

    BY_DOCUMENT_HTML_TEXT = 'Remember that ancient letters were meant to be read in their entirety, just like modern letters. We provide a byChapter mode for convenience only, but mostly <b>recommend the byDocument and bySection modes</b> for personal reading.'
    BY_DOCUMENT_HTML_PARAGRAPH = f'<p class="rem">{BY_DOCUMENT_HTML_TEXT}</p>'

    PICKLE_FILENAME_END = '.OBD_Bible.pickle'


    # This first one specifies the order in which everything is processed
    # NOTE: OET is a "pseudo-version" containing both OET-RV and OET-LV side-by-side and handled separately in many places
    BibleVersions = ['OET',
        'OET-RV','OET-LV',
        'ULT','UST','NET', # We move NET up nearer the top for TEST_MODE_FLAG
        'BSB','MSB','BLB',
        'AICNT','OEB','ISV','CSB','NLT',
        'NIV','CEV','ESV','NASB','LSB',
        'JQT','2DT','1ST','TPT',
        'WEBBE','WEB','WMBB','WMB','MSG','LSV','FBV','TCNT','T4T','LEB','NRSV','NKJV','NAB','BBE',
        'Moff','JPS','Wymth','ASV','DRA','YLT','Drby','RV','SLT','Wbstr','KJB-1769','KJB-1611','Bshps','Gnva','Cvdl',
        'TNT','Wycl',
        'Luth','ClVg',
        'SR-GNT','UGNT','SBL-GNT','RP-GNT','TC-GNT',
        'UHB', 'BrLXX','BrTr', 'NETS',
        # NOTES:
        'TOSN','UTN',
        ] if TEST_MODE_FLAG else \
        ['OET',
        'OET-RV','OET-LV',
        'ULT','UST',
        'BSB','MSB','BLB',
        'AICNT','OEB','ISV','CSB','NLT',
        'NIV','CEV','ESV','NASB','LSB',
        'JQT','2DT','1ST','TPT',
        'WEBBE','WEB','WMBB','WMB','MSG','NET','LSV','FBV','TCNT','T4T','LEB','NRSV','NKJV','NAB','BBE',
        'Moff','JPS','Wymth','ASV','DRA','YLT','Drby','RV','SLT','Wbstr','KJB-1769','KJB-1611','Bshps','Gnva','Cvdl',
        'TNT','Wycl',
        'Luth','ClVg',
        'SR-GNT','UGNT','SBL-GNT','RP-GNT','TC-GNT',
        'UHB', 'BrLXX','BrTr', 'NETS',
        # NOTES:
        'TOSN','UTN',
        ]    # NOTE: The above list has entries deleted by preloadBibles() if they fail to load
#           (often because we temporarily remove the BibleLocation below)
    allPossibleBibleVersions = BibleVersions[:] # Keep a copy with the full list

    # Specific short lists
    auxilliaryVersions = ('OET','TOBD') # These ones don't have their own Bible locations at all
    # The following three lines are also in selectedVersesVersions.py
    selectedVersesOnlyVersions = ('CSB','NLT','NIV','CEV','ESV','MSG','NASB','LSB','JQT','2DT','1ST','TPT','NRSV','NKJV','NAB', 'NETS' ) # These ones have .tsv sources (and don't produce Bible objects)
    numAllowedSelectedVerses   = (  300,  500,  500,  500,  500,  500,   500, 1000,   20,  300,  300,  250,   300,   300,  250,    250  ) # Order must match above list
    assert len(numAllowedSelectedVerses) == len(selectedVersesOnlyVersions)
    # We want these versions on our parallel pages, but are not interested enough in them for them to have their own version pages
    versionsWithoutTheirOwnPages = selectedVersesOnlyVersions + ('Luth','ClVg', 'UGNT','SBL-GNT','RP-GNT','TC-GNT', 'TOSN','UTN')
#     if not TEST_MODE_FLAG: versionsWithoutTheirOwnPages += 'KJB-1611'

    # NOTE: We don't display the versionsWithoutTheirOwnPages, so don't need/allow decorations for them
    BibleVersionDecorations = { 'OET':('<b>','</b>'),'OET-RV':('<b>','</b>'),'OET-LV':('<b>','</b>'),
        'ULT':('',''),'UST':('',''),
        'BSB':('',''),'MSB':('<small>','</small>'),'BLB':('',''),
        'AICNT':('',''), 'OEB':('',''), 'ISV':('',''),
        'WEBBE':('',''),'WEB':('',''),'WMB':('',''),'WMBB':('',''), 'NET':('',''), 'LSV':('',''), 'FBV':('',''), 'TCNT':('<small>','</small>'), 'T4T':('',''),'LEB':('',''),'BBE':('',''),
        'Moff':('<small>','</small>'), 'JPS':('<small>','</small>'), 'Wymth':('<small>','</small>'), 'ASV':('',''), 'DRA':('<small>','</small>'),'YLT':('',''),'Drby':('',''),'RV':('',''),
        'SLT':('',''),'Wbstr':('<small>','</small>'),
        'KJB-1769':('',''),'KJB-1611':('',''), 'Bshps':('',''), 'Gnva':('',''), 'Cvdl':('',''),
        'TNT':('',''), 'Wycl':('',''), #'ClVg':('<small>','</small>'),
        'SR-GNT':('<b>','</b>'), # 'UGNT':('<small>','</small>'),'SBL-GNT':('<small>','</small>'),'TC-GNT':('<small>','</small>'),
        'UHB':('<b>','</b>'),
        'BrTr':('<small>','</small>'),'BrLXX':('',''),
        'Related':('<b>','</b>'), 'Topics':('<b>','</b>'), 'Parallel':('<b>','</b>'), 'Interlinear':('<b>','</b>'), 'Reference':('<b>','</b>'), 'Dictionary':('<b>','</b>'), 'Search':('<b>','</b>'),
        # NOTES:
        'TOSN':('',''),'UTN':('',''),
        }

        ## 'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.osis.xml', # OSIS
        ## 'Wycl': '../copiedBibles/English/eBible.org/Wycliffe/',
    BibleLocations = {
        'OET-RV': '../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',
        'OET-LV': '../../OpenEnglishTranslation--OET/intermediateTexts/', # Only .pickle here
        'OET-LV-OT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_OT_ESFM/', # No NT here
        'OET-LV-NT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_ESFM/', # No OT here
        'SR-GNT': '../../Forked/CNTR-SR/SR usfm/', # We moved these up in the list because they're now compulsory
        'UHB': '../copiedBibles/Original/unfoldingWord.org/UHB/',
        # NOTE: The program will still run if some of these below are commented out or removed
        # (e.g., this can be done quickly for a faster test run)
        'ULT': '../copiedBibles/English/unfoldingWord.org/ULT/',
        'UST': '../copiedBibles/English/unfoldingWord.org/UST/',
        #'BSB': '../copiedBibles/English/Berean.Bible/BSB/PTX_USFM/',
        'BSB': '../copiedBibles/English/Berean.Bible/BSB/bsb_tables.exported.modified.tsv',
        'MSB': ('../copiedBibles/English/Berean.Bible/MSB/','../copiedBibles/English/Berean.Bible/MSB/bsb_tables.exportedOT.modified.tsv','../copiedBibles/English/Berean.Bible/MSB/msb_nt_tables.exported.modified.tsv'),
        'BLB': '../copiedBibles/English/Berean.Bible/BLB/blb.modified.txt', # NT only so far
        # However, if they're all commented out, 'assert doneHideablesDiv' will fail in createParallelVersePages.py if not in test mode
        'AICNT': '../copiedBibles/English/AICNT/', # NT only
        'OEB': '../copiedBibles/English/OEB/',
        # 'ISV': '', # Seems dead and gone :-(
        'CSB': '../copiedBibles/English/CSB_verses.tsv',
        'NLT': '../copiedBibles/English/NLT_verses.tsv',
        'NIV': '../copiedBibles/English/NIV_verses.tsv',
        'CEV': '../copiedBibles/English/CEV_verses.tsv',
        'ESV': '../copiedBibles/English/ESV_verses.tsv',
        'NASB': '../copiedBibles/English/NASB_verses.tsv',
        'LSB': '../copiedBibles/English/LSB_verses.tsv',
        'JQT': '../copiedBibles/English/JQT_verses.tsv',
        '2DT': '../copiedBibles/English/2DT_verses.tsv',
        '1ST': '../copiedBibles/English/1ST_verses.tsv',
        'TPT': '../copiedBibles/English/TPT_verses.tsv',
        'WEBBE': '../copiedBibles/English/eBible.org/WEBBE/', # British spelling  # 'WEB': '../copiedBibles/English/eBible.org/WEB/', # USA spelling
        'WMBB': '../copiedBibles/English/eBible.org/WMBB/', # British spelling  # 'WMB': '../copiedBibles/English/eBible.org/WMB/', #USA spelling
        'MSG': '../copiedBibles/English/MSG_verses.tsv',
        'NET': '../copiedBibles/English/NET/' if TEST_MODE_FLAG else '../copiedBibles/English/eBible.org/NET/',
        'LSV': '../copiedBibles/English/eBible.org/LSV/',
        'FBV': '../copiedBibles/English/eBible.org/FBV/',
        'TCNT': '../copiedBibles/English/eBible.org/TCNT/',
        'T4T': '../copiedBibles/English/eBible.org/T4T/',
        'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.updated.xml', # not OSIS
        'NRSV': '../copiedBibles/English/NRSV_verses.tsv',
        'NKJV': '../copiedBibles/English/NKJV_verses.tsv',
        'NAB': '../copiedBibles/English/NAB_verses.tsv',
        'BBE': '../copiedBibles/English/eBible.org/BBE/',
        'Moff': '../copiedBibles/English/Moffat/',
        'JPS': '../copiedBibles/English/eBible.org/JPS/',
        'Wymth': '../Bibles/EnglishTranslations/Weymouth_NT-1903/',
        'ASV': '../copiedBibles/English/eBible.org/ASV/',
        'DRA': '../copiedBibles/English/eBible.org/DRA/',
        'YLT': '../copiedBibles/English/eBible.org/YLT/',
        'Drby': '../copiedBibles/English/eBible.org/DBY/',
        'RV': '../copiedBibles/English/eBible.org/RV/', # with deuterocanon
        'SLT': '../copiedBibles/English/Berean.Bible/slt.txt',
        'Wbstr': '../copiedBibles/English/eBible.org/WBS/',
        'KJB-1769': '../copiedBibles/English/eBible.org/KJB/', # with deuterocanon -- ALWAYS NEEDED if KJB-1611 and some others are included
        'KJB-1611': '../Bibles/EnglishTranslations/KJB-1611/', # with deuterocanon
        'Bshps': '../copiedBibles/English/BibleSuperSearch/BB/bishops.txt',
        'Gnva': '../copiedBibles/English/eBible.org/GNV/',
        'Cvdl': '../copiedBibles/English/BibleSuperSearch/CB/coverdale.txt',
        'TNT': '../copiedBibles/English/eBible.org/TNT/',
        'Wycl': '../copiedBibles/English/Zefania/WYC/SF_2009-01-20_ENG_BIBLE_WYCLIFFE_(JOHN WYCLIFFE BIBLE).xml',
        'Luth': '../copiedBibles/German/Zefania/LUT1545/SF_2009-01-20_GER_LUTH1545STR_(LUTHER 1545 MIT STRONGS).xml',
        'ClVg': '../copiedBibles/Latin/eBible.org/CLV/',
        'UGNT': '../copiedBibles/Original/unfoldingWord.org/UGNT/',
        'SBL-GNT': '../../Forked/SBLGNT/data/sblgnt/text/',
        'RP-GNT': '../../Forked/byzantine-majority-text/csv-unicode/no-variants/',
        'TC-GNT': '../copiedBibles/Greek/eBible.org/TC-GNT/',
        'NETS': '../copiedBibles/English/NETS_verses.tsv',
        'BrTr': '../copiedBibles/English/eBible.org/Brenton/', # with deuterocanon and OTH,XXA,XXB,XXC,
        'BrLXX': '../copiedBibles/Greek/eBible.org/BrLXX/',
        # NOTE: Dictionary and notes are special cases here at the end (skipped in many parts of the program)
        'TOSN': '../copiedBibles/English/Tyndale/OSN/', # This one also loads TTN (Tyndale Theme Notes)
        'UTN': '../copiedBibles/English/unfoldingWord.org/UTN/',
        }
    WholeBibleVersions = ('BSB','MSB','LEB','SLT','Bshps','Cvdl','Wycl','Luth') # These versions get all books loaded -- no individual book files

    BibleNames = {
        'OET': 'Open English Translation (2030)',
        'OET-RV': 'Open English Translation—Readers’ Version (2030)',
        'OET-LV': 'Open English Translation—Literal Version (2026)',
        'ULT': 'unfoldingWord® Literal Text (2023)',
        'UST': 'unfoldingWord® Simplified Text (2023)',
        'BSB': 'Berean Study/Standard Bible (v3, 2025)',
        'MSB': 'Majority Standard Bible (2025)',
        'BLB': 'Berean Literal Bible NT (2022)',
        'AICNT': 'AI Critical NT (2023)',
        'OEB': 'Open English Bible (in progress)',
        'ISV': 'International Standard Version (2020?)',
        'CSB': 'Christian Standard Bible (2017)',
        'NLT': 'New Living Translation (2015)',
        'NIV': 'New International Version (2011)',
        'CEV': 'Contemporary English Version (2006)',
        'ESV': 'English Standard Version (2001)',
        'NASB': 'New American Standard Bible (1995)',
        'LSB': 'Legacy Standard Bible (2021)',
        'JQT': 'James Quiggle Translation New Testament (2023)',
        '2DT': 'The Second Testament (2023)',
        '1ST': 'The First Testament (2018)',
        'TPT': 'The Passion Translation (2017)',
        'WEBBE': 'World English Bible (2023) British Edition',
        'WEB': 'World English Bible (2023)',
        'WMBB': 'World Messianic Bible (2023) British Edition / Hebrew Names Version (HNV)',
        'WMB': 'World Messianic Bible (2023) / Hebrew Names Version (HNV)',
        'MSG': 'The Message (2018)',
        'NET': 'New English Translation (2016)',
        'LSV': 'Literal Standard Version (2020)',
        'FBV': 'Free Bible Version (2018)',
        'TCNT': 'Text-Critical New Testament (2022, Byzantine)',
        'T4T': 'Translation for Translators (2017)',
        'LEB': 'Lexham English Bible (2010, 2012)',
        'NRSV': 'New Revised Standard Version (1989)',
        'NKJV': 'New King James Version (1982)',
        'NAB': 'New American Bible (1970, revised 2010)',
        'BBE': 'Bible in Basic English (1965)',
        'Moff': 'The Moffatt Translation of the Bible (1922)',
        'JPS': 'Jewish Publication Society TaNaKH (1917)',
        'Wymth': 'Weymouth New Testament (1903)',
        'ASV': 'American Standard Version (1901)',
        'DRA': 'Douay-Rheims American Edition (1899)',
        'YLT': 'Youngs Literal Translation (1898)',
        'Drby': 'Darby Translation (1890)',
        'RV': 'English Revised Version (1885)',
        'SLT':'Smith’s Literal Translation (1855)',
        'Wbstr': 'Webster Bible (American, 1833)',
        'KJB-1769': 'King James Bible (1769)',
        'KJB-1611': 'King James Bible (1611)',
        'Bshps': 'Bishops Bible (1568, 1602)',
        'Gnva': 'Geneva Bible (1557-1560, 1599)',
        'Great': 'Great Bible (1539)', # Not in OBD yet
        'Cvdl': 'Coverdale Bible (1535-1553)',
        'TNT': 'Tyndale New Testament (1526)',
        'Wycl': 'Wycliffe Bible (middle-English, 1382)',
        'Luth': 'Luther Bible (German, 1545)',
        'ClVg': 'Clementine Vulgate (Latin, 1592)',
        'SR-GNT': 'Statistical Restoration Greek New Testament (2022)',
        'UGNT': 'unfoldingWord® Greek New Testament (2022)',
        'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2010)',
        'RP-GNT': 'Robinson-Pierpont Greek New Testament (2018, Byzantine/Majority text)',
        'TC-GNT': 'Text-Critical Greek New Testament (2010, Byzantine)',
        'NETS': 'New English Translation of the Septuagint (2009,2014)',
        'BrTr': 'Brenton Septuagint Translation (1851)',
        'BrLXX': '(Brenton’s) Ancient Greek translation of the Hebrew Scriptures (~250 BC)',
        'UHB': 'unfoldingWord® Hebrew Bible (2022)',
        'PLBL': 'Psalms Layer-by-Layer from Scriptura.org',
        'HAP': 'Hebrew Accents and Phrasing (ongoing)',
        'TOSN': 'Tyndale Open Study Notes (2022)',
        'TOBD': 'Tyndale Open Bible Dictionary (2023)',
        'UTN': 'unfoldingWord® Translation Notes (2023)',
        'UBS': 'United Bible Societies open-licenced resources (2023)',
        'THBD': 'Theographic Bible Database',
        'BMM': 'BibleMapper.com Maps',
        }

    BibleLanguages = {
        'OET': 'EN-UK',
        'OET-RV': 'EN-UK',
        'OET-LV': 'EN-UK',
        'ULT': 'EN-USA',
        'UST': 'EN-USA',
        'BSB': 'EN-USA',
        'MSB': 'EN-USA',
        'BLB': 'EN-USA',
        'AICNT': 'EN-USA',
        'OEB': 'EN-UK',
        'ISV': 'EN-USA',
        'CSB': 'EN-USA',
        'NLT': 'EN-USA',
        'NIV': 'EN-USA',
        'CEV': 'EN-USA',
        'ESV': 'EN-USA',
        'NASB': 'EN-USA', # A stands for American
        'LSB': 'EN-USA',
        'JQT': 'EN-USA',
        '2DT': 'EN-USA',
        '1ST': 'EN-USA',
        'TPT': 'EN-USA',
        'WEBBE': 'EN-UK',
        'WEB': 'EN-USA',
        'WMBB': 'EN-UK',
        'WMB': 'EN-USA',
        'MSG': 'EN-USA',
        'NET': 'EN-USA',
        'LSV': 'EN-USA',
        'FBV': 'EN-USA',
        'TCNT': 'EN-UK',
        'T4T': 'EN-USA',
        'LEB': 'EN-USA',
        'NRSV': 'EN-UK',
        'NKJV': 'EN-UK',
        'NAB': 'EN-USA', # A stands for American
        'BBE': 'EN-UK',
        'Moff': 'EN-UK',
        'JPS': 'EN-UK',
        'Wymth': 'EN-UK',
        'ASV': 'EN-USA', # A stands for American
        'DRA': 'EN-UK', # A stands for American so why British spelling???
        'YLT': 'EN-UK',
        'Drby': 'EN-UK',
        'RV': 'EN-UK',
        'SLT': 'EN-USA',
        'Wbstr': 'EN-USA',
        'KJB-1769': 'EN-UK', # modernised
        'KJB-1611': 'EN-UK', # modernised
        'Bshps': 'EN-UK', # modernised
        'Gnva': 'EN-UK', # modernised
        'Great': None, # Not in OBD yet
        'Cvdl': 'EN-UK', # modernised
        'TNT': 'EN-UK', # modernised
        'Wycl': 'EN-UK', # modernised
        'Luth': 'GER',
        'ClVg': 'LAT',
        'SR-GNT': 'GRK',
        'UGNT': 'GRK',
        'SBL-GNT': 'GRK',
        'RP-GNT': 'GRK',
        'TC-GNT': 'GRK',
        'NETS': None,
        'BrTr': None,
        'BrLXX': 'GRK',
        'UHB': 'HEB',
        'PLBL': 'EN-USA',
        'HAP': 'EN-USA',
        'TOSN': 'EN-USA',
        'TOBD': 'EN-USA',
        'UTN': 'EN-USA',
        'UBS': 'EN-USA',
        'THBD': 'EN-USA',
        'BMM': 'EN-USA',
        }

    booksToLoad = {
        'OET': OET_RV_BOOK_LIST_WITH_FRT,
        'OET-RV': ['ALL'], # Load ALL coz we use related sections anyway OET_RV_BOOK_LIST_WITH_FRT,
        'OET-LV': OET_LV_BOOK_LIST,
        'ULT': ['ALL'],
        'UST': ['ALL'], # MRK 13:13 gives \\add error (24Jan2023)
        'BSB': ['ALL'],
        'MSB': ['ALL'],
        'BLB': ['ALL'], # NT only
        'AICNT': ['ALL'], # NT only
        'OEB': ['ALL'],
        'ISV': ['ALL'],
        'CSB': ['ALL'],
        'NLT': ['ALL'],
        'NIV': ['ALL'],
        'CEV': ['ALL'],
        'ESV': ['ALL'],
        'NASB': ['ALL'],
        'LSB': ['ALL'],
        'JQT': ['ALL'],
        '2DT': ['ALL'],
        '1ST': ['ALL'],
        'TPT': ['ALL'],
        'WEBBE': ['ALL'],
        'WEB': ['ALL'],
        'WMBB': ['ALL'],
        'WMB': ['ALL'],
        'MSG': ['ALL'],
        'NET': ['ALL'],
        'LSV': ['ALL'],
        'FBV': ['ALL'],
        'TCNT': ['ALL'],
        'T4T': ['ALL'],
        'LEB': ['ALL'],
        'NRSV': ['ALL'],
        'NKJV': ['ALL'],
        'NAB': ['ALL'],
        'BBE': ['ALL'],
        'Moff': ['ALL'],
        'JPS': ['ALL'],
        'Wymth':['ALL'], # NT only
        'ASV': ['ALL'],
        'DRA': ['ALL'],
        'YLT': ['ALL'],
        'Drby': ['ALL'],
        'RV': ['ALL'],
        'SLT': ['ALL'],
        'Wbstr': ['ALL'],
        'KJB-1769': ['ALL'],
        'KJB-1611': ['ALL'],
        'Bshps': ['ALL'],
        'Gnva': ['ALL'],
        'Cvdl': ['ALL'],
        'TNT': ['ALL'],
        'Wycl': ['ALL'],
        'Luth': ['ALL'],
        'ClVg': ['ALL'],
        'SR-GNT': ['ALL'],
        'UGNT': ['ALL'],
        'SBL-GNT': ['ALL'],
        'RP-GNT': ['ALL'],
        'TC-GNT': ['ALL'],
        'NETS': ['ALL'],
        'BrTr': ['ALL'],
        'BrLXX': ['ALL'],
        'UHB': ['ALL'],
        # NOTES:
        'TOSN': ['ALL'],
        'UTN': ['ALL'],
    } if ALL_PRODUCTION_BOOKS_FLAG else {
        'OET': ['FRT'] + TEST_BOOK_LIST,
        'OET-RV': ['FRT'] + TEST_BOOK_LIST, #['ALL'], # Load ALL coz we use related sections anyway ['FRT'] + TEST_BOOK_LIST,
        'OET-LV': TEST_BOOK_LIST,
        'ULT': ['FRT'] + TEST_BOOK_LIST,
        'UST': TEST_BOOK_LIST, # Has no FRT for some reason
        'BSB': TEST_BOOK_LIST,
        'MSB': TEST_BOOK_LIST,
        'BLB': TEST_NT_BOOK_LIST, # NT only
        'AICNT': TEST_NT_BOOK_LIST, # NT only
        'OEB': TEST_BOOK_LIST,
        'ISV': TEST_BOOK_LIST,
        'CSB': TEST_BOOK_LIST,
        'NLT': TEST_BOOK_LIST,
        'NIV': TEST_BOOK_LIST,
        'CEV': TEST_BOOK_LIST,
        'ESV': TEST_BOOK_LIST,
        'NASB': TEST_BOOK_LIST,
        'LSB': TEST_BOOK_LIST,
        'JQT': TEST_BOOK_LIST,
        '2DT': TEST_BOOK_LIST,
        '1ST': TEST_BOOK_LIST,
        'TPT': TEST_BOOK_LIST,
        'WEBBE': TEST_BOOK_LIST,
        'WEB': TEST_BOOK_LIST,
        'WMBB': TEST_BOOK_LIST,
        'WMB': TEST_BOOK_LIST,
        'MSG': TEST_BOOK_LIST,
        'NET': TEST_BOOK_LIST,
        'LSV': TEST_BOOK_LIST,
        'FBV': TEST_BOOK_LIST,
        'TCNT': TEST_NT_BOOK_LIST, # NT only
        'T4T': TEST_BOOK_LIST,
        'LEB': TEST_BOOK_LIST,
        'NRSV': TEST_BOOK_LIST,
        'NKJV': TEST_BOOK_LIST,
        'NAB': TEST_BOOK_LIST,
        'BBE': TEST_BOOK_LIST,
        'Moff': TEST_BOOK_LIST,
        'JPS': TEST_OT_BOOK_LIST,
        'Wymth': TEST_NT_BOOK_LIST, # NT only
        'ASV': TEST_BOOK_LIST,
        'DRA': TEST_BOOK_LIST,
        'YLT': TEST_BOOK_LIST,
        'Drby': TEST_BOOK_LIST,
        'RV': TEST_BOOK_LIST,
        'SLT': TEST_BOOK_LIST,
        'Wbstr': TEST_BOOK_LIST,
        'KJB-1769': TEST_BOOK_LIST,
        'KJB-1611': ['FRT'] + TEST_BOOK_LIST,
        'Bshps': TEST_BOOK_LIST,
        'Gnva': TEST_BOOK_LIST,
        'Cvdl': TEST_BOOK_LIST,
        'TNT': TEST_NT_BOOK_LIST, # NT only
        'Wycl': TEST_BOOK_LIST,
        'Luth': TEST_BOOK_LIST,
        'ClVg': TEST_BOOK_LIST,
        'SR-GNT': TEST_NT_BOOK_LIST, # NT only
        'UGNT': TEST_NT_BOOK_LIST, # NT only
        'SBL-GNT': TEST_NT_BOOK_LIST, # NT only
        'RP-GNT': TEST_NT_BOOK_LIST, # NT only
        'TC-GNT': TEST_NT_BOOK_LIST, # NT only
        'NETS': TEST_OT_BOOK_LIST, # OT only
        'BrTr': TEST_OT_BOOK_LIST, # OT only
        'BrLXX': TEST_OT_BOOK_LIST, # OT only
        'UHB': TEST_OT_BOOK_LIST, # OT only
        # NOTES:
        'TOSN': TEST_BOOK_LIST,
        'UTN': TEST_BOOK_LIST,
        }

    detailsHtml = {
        'OET': {'about': f'''<p class="about">The (still unfinished) <em>Open English Translation</em> ({OET_VERSION_NUMBER_STRING}) consists of a <em>Readers’ Version</em> and a <em>Literal Version</em> side-by-side.
You can read a lot more about the design of the <em>OET</em> at <a href="https://OpenEnglishTranslation.Bible/Design/Overview">OpenEnglishTranslation.Bible/Design/Overview</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010–2025 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '''<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, radical, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible/Reader">OpenEnglishTranslation.Bible</a>.
We are very grateful to Dr. Alan Bunning of the <a href="https://GreekCNTR.org">Center for New Testament Restoration</a> whose many years of hard work the New Testament part of the <em>OET-LV</em> is adapted from.
The Old Testament part of the <em>OET-LV</em> uses the morphology analysis from the work of the <a href="https://hb.OpenScriptures.org/">Open Scriptures Hebrew Bible</a> team.
We’re also grateful to the <a href="https://www.Biblica.com/clear/">Biblica Clear Bible team</a> who provide the pronoun referential information as part of their <a href="https://GitHub.com/Clear-Bible/macula-greek">Macula Greek</a> project and also some of the OT glosses as part of their <a href="https://GitHub.com/Clear-Bible/macula-hebrew">Macula Hebrew</a> project.
Also, the Bible translation resources created by <a href="https://www.unfoldingWord.org">unfoldingWord</a> have proven very helpful.</p>''' },
        'OET-RV': {'about': '''<p class="about">The (still unfinished) <em>Open English Translation Readers’ Version</em> is a new, modern-English, easy-to-read translation of the Bible.
You can read a lot more about the design of the <em>OET-RV</em> at <a href="https://OpenEnglishTranslation.Bible/Design/ReadersVersion">OpenEnglishTranslation.Bible/Design/ReadersVersion</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010–2025 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible/Reader">OpenEnglishTranslation.Bible</a>.</p>' },
        'OET-LV': {'about': '''<p class="about">The (still unfinished) <em>Open English Translation Literal Version</em> is a tool designed to give a look into what was actually written in the original Hebrew or Greek manuscripts.
You can read a lot more about the design of the <em>OET-LV</em> at <a href="https://OpenEnglishTranslation.Bible/Design/LiteralVersion">OpenEnglishTranslation.Bible/Design/LiteralVersion</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010–2025 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '''<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible/Reader">OpenEnglishTranslation.Bible</a>.
We are very grateful to Dr. Alan Bunning of the <a href="https://GreekCNTR.org">Center for New Testament Restoration</a> whose many years of hard work this literal New Testament is adapted from.
The Old Testament Hebrew text (and the morphology analysis) is adapted from the work of the <a href="https://hb.OpenScriptures.org/">Open Scriptures Hebrew Bible</a> team.
We’re also grateful to the <a href="https://www.Biblica.com/clear/">Biblica Clear Bible team</a> who provide the pronoun referential information as part of their <a href="https://GitHub.com/Clear-Bible/macula-greek">Macula Greek</a> project and also some of the OT glosses as part of their <a href="https://GitHub.com/Clear-Bible/macula-hebrew">Macula Hebrew</a> project.</p>''',
                'notes' : '''<p class="note">Note that the <em>OET-LV</em> is VERY literal (even including Hebrew and Greek words that are not normally translated into English) because it’s designed to be used in conjunction with our <em>Readers’ Version</em>.</p>''' },
        'ULT': {'about': '<p class="about">unfoldingWord® Literal Text (2023) and derived from the 1901 ASV.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating this Bible translation which is designed to be a tool for Bible translators.</p>' },
        'UST': {'about': '<p class="about">unfoldingWord® Simplified Text (2023). The UST has all passive constructions changed to active forms, and all idioms replaced with their English meanings.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating this specialised Bible translation which is designed to be a tool for Bible translators.</p>' },
        'BSB': {'about': '<p class="about">Berean Standard Bible (Version 3, 2025).</p>',
                'copyright': '<p class="copyright"><a href="https://berean.bible/terms.htm">Public domain</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a> licence. All uses are freely permitted.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to John Isett and <a href="https://biblehub.com/">BibleHub</a> for the <a href="https://berean.bible/">BSB</a>.</p>',
                'notes': '<p class="note">According to Dr. Gray Hill, the BSB (originally called ‘The Berean Study Bible’) is intentionally designed <a href="https://www.youtube.com/watch?v=qX-2IMNzUbE">to preserve past traditions</a>. (Full video <a href="https://www.youtube.com/watch?v=hKooIYSq8Ys">here</a>.)</p>' },
        'MSB': {'about': '<p class="about">Majority Standard Bible (September, 2025).</p>',
                'copyright': '<p class="copyright"><a href="https://berean.bible/terms.htm">Public domain</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a> licence. All uses are freely permitted.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to John Isett and <a href="https://biblehub.com/">BibleHub</a> for the <a href="https://berean.bible/">MSB</a>.</p>',
                'notes': '<p class="note">This version has an identical Old Testament to the BSB, but the New Testament has some changes as it follows the ‘majority’ text rather than the critical text (used by the <em>OET</em>) or the ‘received’ text.</p>' },
        'BLB': {'about': '<p class="about">Berean Literal Bible New Testament (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by Bible Hub. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">The Berean Bible text is <a href="https://berean.bible/terms.htm#Top">free to use</a> in any electronic form to promote the reading, learning, and understanding of the Holy Bible as the Word of God.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://biblehub.com/">BibleHub</a> for the <a href="https://berean.bible/">BLB</a>.</p>' },
        'AICNT': {'about': '<p class="about">The <a href="https://AICNT.org/">AI Critical New Testament</a> (AICNT) is a critical English edition carefully compiled to indicate the text of the earliest manuscripts in contrast to later changes and in reference to Greek critical editions. The AICNT provides readers with a rich source of vital information and leverages AI (GPT-4) to translate with optimal transparency. See the preface at <a href="https://aicnt.org/preface">AICNT.org/preface</a>. The site <a href="https://GPT.Bible">GPT.Bible</a> offers enhanced search and viewing functionality for exploring the AICNT.</p>',
                'copyright': '<p class="copyright">Copyright 2023 <a href="https://IntegritySyndicate.com/">Integrity Syndicate</a>.</p>',
                'licence': '<p class="licence">Copyrighted. Used with permission.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to Theophilus Josiah, founder.</p>' },
        'OEB': {'about': '<p class="about">Open English Bible (in progress).</p>',
                'copyright': '<p class="copyright">Copyright © 2010-2021 Russell Allen.</p>',
                'licence': '<p class="licence"><a href="http://creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero licence</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://openenglishbible.org/">Russell Allen and team</a> for generously providing <a href="https://github.com/openenglishbible/Open-English-Bible">this English translation</a>.</p>' },
        'ISV': {'about': '<p class="about">International Standard Version (2020?).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'CSB': {'about': '<p class="about">(Holmes) Christian Standard Bible (2017).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>' },
        'NLT': {'about': '<p class="about">New Living Translation (2015).</p>',
                'copyright': '<p class="copyright">Holy Bible, New Living Translation, copyright © 1996, 2004, 2015 by Tyndale House Foundation. Used by permission of Tyndale House Publishers. All rights reserved.</p>',
                'licence': '<p class="licence">five hundred (500) verses without the express written permission of the publisher, providing the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five percent (25%) or more of the total text of the work in which they are quoted.</p>',
                 },
        'NIV': {'about': '<p class="about">New International Version (2011).</p>',
                'copyright': '<p class="copyright">Scripture quotations taken from The Holy Bible, New International Version® NIV®. Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.™ Used by permission. All rights reserved worldwide.</p>',
                'licence': '<p class="licence">The NIV® text may be quoted in any form (written, visual, electronic or audio), up to and inclusive of five hundred (500) verses without the express written permission of the publisher, providing the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five percent (25%) or more of the total text of the work in which they are quoted.</p>',
                 },
        'CEV': {'about': '<p class="about">Contemporary English Version, Second Edition (2006).</p>',
                'copyright': '<p class="copyright">Scripture quotations marked (CEV) are from the Contemporary English Version Copyright © 1991, 1992, 1995 by American Bible Society. Used by Permission.</p>',
                'licence': '<p class="licence">Text from the Contemporary English Version (CEV) may be quoted in any form (written, visual, electronic or audio) up to and inclusive of five hundred (500) verses without written permission, providing the verses quoted do not amount to 50% of a complete book of the Bible nor do the verses account for twenty-five percent (25%) or more of the total text of the work in which they are quoted and the work is available for non-commercial use.</p>',
                 },
        'ESV': {'about': '<p class="about">English Standard Version (2001).</p>',
                'copyright': '<p class="copyright">Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), copyright © 2001 by Crossway Bibles, a publishing ministry of Good News Publishers. Used by permission. All rights reserved.</p>',
                'licence': '<p class="licence">The ESV text may be quoted (in written, visual, or electronic form) up to and inclusive of five hundred (500) verses without express written permission of the publisher, providing that the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five (25%) percent or more of the total text of the work in which they are quoted.</p>',
                 },
        'NASB': {'about': '<p class="about">New American Standard Bible (1995): A revision of the American Standard Version (ASV) incorporating information from the Dead Sea Scrolls.</p>',
                'copyright': '<p class="copyright">Scripture taken from the NEW AMERICAN STANDARD BIBLE, © Copyright The Lockman Foundation 1960, 1962, 1963, 1968, 1971, 1972, 1973, 1975, 1977, 1995. Used by permission.</p>',
                'licence': '<p class="licence">The text of the New American Standard Bible® may be quoted and/or reprinted up to and inclusive of five hundred (500) verses without express written permission of The Lockman Foundation, providing that the verses do not amount to a complete book of the Bible nor do the verses quoted account for more than 25% of the total work in which they are quoted.</p>',
                 },
        'LSB': {'about': '<p class="about"><a href="https://LSBible.org/">Legacy Standard Bible</a> (2021): A revision of the 1995 New American Standard Bible (NASB) completed in October 2021.</p>',
                'copyright': '<p class="copyright">Copyright © 2021 by The Lockman Foundation. All Rights Reserved.</p>',
                'licence': '<p class="licence">The text of the LSB® (Legacy Standard Bible®) may be quoted in any form (written, visual, electronic, or audio) up to and inclusive of one thousand (1,000) verses providing the verses do not amount to a complete book of the Bible, nor do the verses quoted account for more than 50% of the total text of the work in which they are quoted, nor may more than 1,000 verses be stored in an electronic retrieval system. <small>(Downloaded from <a href="https://LSBible.org/permission-to-quote-the-lsb/">LSBible.org/permission-to-quote-the-lsb/</a> January 2024)</small></p>',
                 },
        'JQT': {'about': '<p class="about">James Quiggle Translation New Testament (2023).</p>',
                'copyright': '<p class="copyright">Translated and published by James D. Quiggle, copyright 2023.</p>',
                'licence': '<p class="licence">Limited to twenty verses.</p>',
                 },
        '2DT': {'about': '<p class="about">The Second Testament: A new translation (2023) by Scot McKnight.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by IVP Academic. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">Up to 300 verses may be used.</p>',
                 },
        '1ST': {'about': '<p class="about">The First Testament: A new translation (2018) by John Goldingay.</p>',
                'copyright': '<p class="copyright">Copyright © 2018 by IVP Academic. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">Up to 300 verses may be used.</p>',
                 },
        'TPT': {'about': '<p class="about">The Passion Translation (2017) by Brian Simmons.</p>',
                'copyright': '<p class="copyright">Scripture quotations marked TPT are from The Passion Translation®. Copyright © 2017, 2018, 2020 by Passion & Fire Ministries, Inc. Used by permission. All rights reserved. ThePassionTranslation.com.</p>',
                'licence': '<p class="licence">Up to 250 verses may be used.</p>',
                'notes': '<p class="note">A few selected verses included here for reference purposes only—this is not a recommended as a reliable Bible translation.</p>' },
        'WEBBE': {'about': '<p class="about">World English Bible (2023) British Edition.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WEB': {'about': '<p class="about">World English Bible (2023).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WMBB': {'about': '<p class="about">World Messianic Bible (2023) British Edition also known as the HNV: Hebrew Names Version.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WMB': {'about': '<p class="about">World Messianic Bible (2023) also known as the HNV: Hebrew Names Version.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'MSG': {'about': '<p class="about">The Message (2018).</p>',
                'copyright': '<p class="copyright">Copyright © 1993,2002,2018 by Eugene H. Peterson. Used by permission of NavPress. All rights reserved. Represented by Tyndale House Publishers, Inc.</p>',
                'licence': '''<p class="licence">The Message text may be quoted in any form (written, visual, electronic, or audio), up to and inclusive of five hundred (500) verses, without express written permission of the publisher, NavPress Publishing Group, providing the verses quoted do not amount to a complete book of the Bible and do not account for twenty-five percent (25%) or more of the total text of the work in which they are quoted.</p>''' },
        'NET': {'about': '<p class="about">New English Translation (2016).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '''<p class="licence"><a href="https://bible.org/downloads">Free</a> (without their many notes, which we’re unable to include, sadly as we’ve discovered that a few of them are actually essential for qualifying or clarifying their translation).</p>''',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'LSV': {'about': '<p class="about">Literal Standard Version (2020).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'FBV': {'about': '<p class="about">Free Bible Version (2018).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="http://www.freebibleversion.org/">Free Bible Ministry</a> for this translation. (coming).</p>' },
        'TCNT': {'about': '''<p class="about">Text-Critical New Testament: Byzantine Text Version (2022) from their own Byzantine-priority Greek New Testament.</p>
<p class="about">Adam Boyd released the Byzantine Text Version in 2022. It is based on the Robinson-Pierpont third edition (RP2018). Boyd describes it as following the “‘optimal equivalence’ philosophy of translation, employing a literary style that is reminiscent of the Tyndale-King James legacy while flowing smoothly and naturally in modern English.” He added: “On the literal to dynamic scale, I would put it somewhere between ESV and CSB (but closer to ESV).”</p>''',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://byzantinetext.com/study/translations/">ByzantineText.com</a> for this work. (coming).</p>' },
        'T4T': {'about': '<p class="about">Translation for Translators (2017).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a> as per <a href="https://ebible.org/t4t/copyright.htm#Top">here</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to the late <a href="https://tahlequah.hartfuneralhome.net/obituary/Ellis-Deibler">Ellis Deibler</a> for his work in preparing this specialised text to be used as a Bible translation tool. (coming).</p>' },
        'LEB': {'about': '<p class="about">Lexham English Bible (2010, 2012).</p>',
                'copyright': '<p class="copyright">Copyright © 2012 <a href="http://www.logos.com/">Logos Bible Software</a>. Lexham is a registered trademark of <a href="http://www.logos.com/">Logos Bible Software</a>.</p>',
                'licence': '<p class="licence">You can give away the <a href="https://lexhampress.com/LEB-License">Lexham English Bible</a>, but you can’t sell it on its own. If the LEB comprises less than 25% of the content of a larger work, you can sell it as part of that work.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="http://www.logos.com/">Logos Bible Software</a> for supplying a XML file.</p>' },
        'NRSV': {'about': '<p class="about">New Revised Standard Version (1989).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>' },
        'NKJV': {'about': '<p class="about">New King James Version (1979).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>' },
        'NAB': {'about': '<p class="about">New American Bible (1970, revised 2010).</p>',
                'copyright': '<p class="copyright">New American Bible, revised edition © 2010, 1991, 1986, 1970 Confraternity of Christian Doctrine, Inc., Washington, DC All Rights Reserved.</p>',
                'licence': '<p class="licence">No permission is required for use of less than 5,000 words of the NAB in print, sound, or electronic formats.</p>' },
        'BBE': {'about': '<p class="about">Bible in Basic English (1965).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'Moff': {'about': '<p class="about">The <a href="https://en.wikipedia.org/wiki/Moffatt,_New_Translation">Moffatt Translation</a> of the Bible (1922).</p>',
                'copyright': '<p class="copyright">Copyright © 1922 James Moffatt.</p>',
                'licence': '<p class="licence">Copyright expired. Public domain.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to the <a href="https://github.com/openenglishbible/usfm-bibles/tree/master/Moffat">OEB team</a> for their <a href="https://github.com/openenglishbible/Open-English-Bible/discussions/348">USFM transcriptions</a> of Moffat’s work.</p>',
                'notes': '''<p class="note">Please note that including Moffat’s work on these pages doesn’t mean that we endorse <a href="https://en.wikipedia.org/wiki/Documentary_hypothesis">The Documentary Hypothesis</a> or other things that he espoused.
However, Moffat wasn’t just a <em>follow the crowd</em> person, so he’s likely to have had at least <em>some</em> good ideas that we all might be able to learn from.</p>''' },
        'JPS': {'about': '<p class="about">Jewish Publication Society TaNaKH (1917).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'Wymth': {'about': '<p class="about">Weymouth New Testament (1903). Also known as “The New Testament in Modern Speech” or “The Modern Speech New Testament”.</p>',
                'copyright': '<p class="copyright">Copyright © 1903.</p>',
                'licence': '<p class="licence">Copyright expired. Public domain.</p>',
                'acknowledgements': '''<p class="acknwldg">Thanks to Richard Weymouth for his work 120 years ago to bring English Bible translations back to the modern English of the time—the end of the 19th century and start of the 20th.
(Our own <a href="https://OpenEnglishTranslation.Bible">Open English Translation</a> continues this concept, but now into the 21st century.)</p>''',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Weymouth_New_Testament">Wikipedia</a> and <a href="https://www.bible-researcher.com/weymouth.html">here</a>.</p>''' },
        'ASV': {'about': '<p class="about">American Standard Version (1901).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'DRA': {'about': '<p class="about">Douay-Rheims American Edition (1899), named after two French cities where it was first translated from the Latin Vulgate in the early 1600’s.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Douay%E2%80%93Rheims_Bible">Wikipedia</a>.</p>''' },
        'YLT': {'about': '<p class="about">Youngs Literal Translation (1898).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Young%27s_Literal_Translation">Wikipedia</a>.</p>''' },
        'Drby': {'about': '<p class="about">Darby Translation (1890).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Darby_Bible">Wikipedia</a>.</p>''' },
        'RV': {'about': '''<p class="about">The English Revised Version (1885) was an officially authorised revision of the King James Bible.
                            (See <a href="https://en.wikipedia.org/wiki/Revised_Version">Wikipedia entry</a>.)</p>''',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'SLT': {'about': '<p class="about">Smiths Literal Translation (1855).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '''<p class="acknwldg">Thanks to <a href='https://OpenBible.com/downloads.htm'>OpenBible.com</a> for this download.</p>''',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Julia_E._Smith_Parker_Translation">Wikipedia</a>.</p>''' },
        'Wbstr': {'about': '<p class="about">Webster Bible (1833).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>',
                'notes': '''<p class="note">See <a href="https://en.wikipedia.org/wiki/Webster%27s_Revision">Wikipedia</a>.</p>''' },
        'KJB-1769': {'about': '<p class="about">King James Bible (1611-1769).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">Public domain outside of the United Kingdom.</p>',
                'acknowledgements': '''<p class="acknwldg">We’re all very grateful that after disgracing John Wycliffe and brutally executing William Tyndale, England finally got a king who would authorise a quality Bible translation.
This was the printed book that had more influence on our modern world than any other, and remains a world-wide best-selling publication.
Thanks to <a href="https://eBible.org/Scriptures/">eBible.org</a> for supplying the USFM files.</p>''',
                'notes': '''<p class="note">Note that after the publication of Samuel Johnson’s dictionary in 1755, the 1769 editions of the KJV are very different from the 1611 edition,
including major typographic and formatting changes, and major spelling changes (including gaining the letter ‘j’), as well as hundreds of corrections.
There are also some verse number changes and some changes to the italicised words, and the marginal notes from 1611 were removed.
(There’s a lot of information online, but you can start by reading more details <a href="https://www.wayoflife.org/reports/changes_to_kjv_since_1611.html">here</a>.)</p>
<p class="note">Also note that the ‘apocryphal books’ were officially removed later in 1885, leaving only 66 ‘books’.
        (The marginal footnotes in all books were also removed.)</p>''' },
        'KJB-1611': {'about': '<p class="about">King James Bible (1611).</p>',
                'copyright': '<p class="copyright">No copyright statement was included in the early printings as can be seen <a href="https://Archive.org/details/1611TheAuthorizedKingJamesBible/page/n2/mode/1up">here</a>.</p>',
                'licence': '<p class="licence">None required outside of the United Kingdom.</p>',
                'acknowledgements': '''<p class="acknwldg">We’re all very grateful that after disgracing John Wycliffe and brutally executing William Tyndale, England finally got a king who would authorise a quality Bible translation.
This was the printed book that had more influence on our modern world than any other.</p>''',
                'notes': '''<p class="note">There were a number of printings of the KJB in 1611—the most famous being the ‘He-Bible’ and the ‘She-Bible’ (named after the ‘he/she went into town’ in <a href="__LEVEL__par/RUT/C3V15.htm#Top">Ruth 3:15</a>).
You’ll notice that there are no speech marks in the 1611 KJB (just as there are none in the Hebrew and Greek original manuscripts),
        but they were added by the time of the 1769 printings.
Also note that there was no letter ‘J’ in the 1611 KJB, e.g., ‘John’ was spelt as ‘Iohn’ (and would have most likely still been pronounced as ‘Yon’ although that pronunciation was probably already beginning to change).
Footnote markers PRECEDE the text that they concern,
        rather than the modern practice of having footnote markers follow the text.</p>
<p class="note">The 1611 KJB will look more original/authentic on your computer/device if you install a black-letter font such as <a href="https://fonts.google.com/specimen/UnifrakturCook">Unifraktur Cook from Google</a>.</p>
<p class="note">Finally, note that the KJB included ‘The Bookes called Apocrypha’ as can be seen <a href="https://archive.org/details/1611TheAuthorizedKingJamesBible/page/n37/mode/1up">here</a>, so an additional fourteen ‘bookes’ beyond the often-expected sixty-six.</p>''' },
        'Bshps': {'about': '<p class="about">Bishops Bible (1568, 1602).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'Gnva': {'about': '<p class="about">Geneva Bible (1557-1560, 1599).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'Cvdl': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Coverdale_Bible">Coverdale Bible</a> (1535-1553).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'TNT': {'about': '<p class="about">Tyndale New Testament (1526).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'Wycl': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Wycliffe%27s_Bible">Wycliffe Bible</a> (middle-English, 1382).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '<p class="acknwldg">The entire English-speaking world is indebted to <a href="https://en.wikipedia.org/wiki/John_Wycliffe">John Wycliffe</a> for his brave work to make the Bible available in the language of the common people at a time when most priests insisted that the Bible was only valid in Latin.</p>',
                'notes': '''<p class="note">The earliest editions were hand-copied because Gutenberg’s printing press didn’t come along until the 1450’s. Chapter divisions had been developed in the 1220’s and the Wycliffe Bible was the first to use those. (Verse divisions didn’t really come until the 1550’s.)</p>''' },
        'Luth': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Luther_Bible">Luther’s German Bible</a> (1545).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '<p class="acknwldg">The entire German-speaking world is indebted to <a href="https://en.wikipedia.org/wiki/Martin_Luther">Martin Luther</a> for his brave work to make the Bible available in the language of the common people at a time when most priests insisted that the Bible was only valid in Latin.</p>' },
        'ClVg': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Sixto-Clementine_Vulgate">Clementine Vulgate Bible</a> (Latin, 1592).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'SR-GNT': {'about': '<p class="about">Statistical Restoration Greek New Testament (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by Alan Bunning.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Grateful thanks to Dr. Alan Bunning who founded the <a href="https://GreekCNTR.org">Center for New Testament Restoration</a> and gave around twenty years of his free time (plus a few full-time years at the end) to make this new, high-quality Greek New Testament freely available.</p>' },
        'UGNT': {'about': '<p class="about">unfoldingWord® Greek New Testament (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating <a href="https://git.door43.org/unfoldingWord/el-x-koine_ugnt">this GNT</a> from the <a href="https://github.com/Center-for-New-Testament-Restoration/BHP">Bunnings Heuristic Prototype GNT</a>.</p>' },
        'SBL-GNT': {'about': '<p class="about">Society for Biblical Literature Greek New Testament (Michael Holmes, 2010).</p>',
                'copyright': '<p class="copyright">Copyright © 2010 by the Society of Biblical Literature and <a href="http://www.logos.com/">Logos Bible Software</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://sblgnt.com/">SBL</a> and <a href="https://www.logos.com/">Logos Bible Software</a> for supplying <a href="https://github.com/LogosBible/SBLGNT/">this GNT</a>.</p>' },
        'RP-GNT': {'about': '<p class="about">Robinson-Pierpont Greek New Testament (2018) Byzantine priority GNT (also known as ‘Majority text’).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">None required.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to Dr. Maurice A. Robinson for donating their work to the public domain so that it’s available for us all to use and for supplying the <a href="https://github.com/Freely-Given-org/byzantine-majority-text/blob/master/csv-unicode/ccat/no-variants/">CSV files</a>.</p>' },
        'TC-GNT': {'about': '<p class="about">Text-Critical Greek New Testament (2010) based on Robinson/Pierpont Byzantine priority GNT (RP2018).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://eBible.org/Scriptures/details.php?id=grctcgnt">eBible.org</a> for supplying the USFM files.</p>' },
        'NETS': {'about': '<p class="about">NETS is a new translation of the Greek Jewish Scriptures, entitled <em>A New English Translation of the Septuagint and the Other Greek Translations Traditionally Included Under that Title</em>. For more information on this project, see the <a href="https://ccat.sas.upenn.edu/nets/">main NETS webpage</a>.</p>',
                'copyright': '<p class="copyright">Copyright © 2007 by the International Organization for Septuagint and Cognate Studies, Inc. All rights reserved.</p>',
                'licence': '<p class="licence">The text of A New English Translation of the Septuagint (NETS) may be quoted in any form (written, visual, electronic, or audio) up to and inclusive of 250 verses without written permission from Oxford University Press, provided that the verses quoted do not account for more than 20% of the work in which they are quoted and provided that a complete book of NETS is not quoted.</p>' },
        'BrTr': {'about': '<p class="about">Sir Lancelot C. L. Brenton’s 1851 translation of the ancient Greek Septuagint (LXX) translation of the Hebrew scriptures.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'BrLXX': {'about': '<p class="about">μετάφραση των εβδομήκοντα: Ancient Greek translation of the Hebrew Scriptures (~250 BC) compiled by Sir Lancelot C. L. Brenton.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'UHB': {'about': '<p class="about">unfoldingWord® Hebrew Bible (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating <a href="https://git.door43.org/unfoldingWord/hbo_uhb">this HB</a> from the <a href="https://hb.openscriptures.org/">OSHB</a>.</p>' },
        'PLBL': {'about': '<p class="about">Scriptura Psalms Layer-by-Layer (2025).</p>',
                'copyright': '<p class="copyright">Copyright owned by <a href="https://www.Scriptura.org/">Scriptura.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://psalms.scriptura.org/w/About">Scriptura</a> for their generous open-licensing of their work on the Songs/Psalms.</p>',
                'notes': '''<p class="note">The current progress of their ongoing analysis of Songs/Psalms can be seen <a href="https://psalms.scriptura.org/w/Welcome">here</a>.</p>''' },
        'HAP': {'about': '<p class="about">Hebrew Accents and Phrasing (ongoing).</p>',
                'copyright': '<p class="copyright">Copyright owned by Allan Johnson.</p>',
                'licence': '<p class="licence">Coming...</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to Allan Johnson for all this hard work analysing Hebrew cantillation marks.</p>' },
        'TOSN': {'about': '<p class="about">Tyndale Open Study Notes (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by Tyndale House Publishers.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://TyndaleOpenResources.com/">Tyndale House Publishers</a> for their generous open-licensing of these Bible study and related notes.</p>' },
        'TOBD': {'about': '<p class="about">Tyndale Open Bible Dictionary (2023).</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by Tyndale House Publishers.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://TyndaleOpenResources.com/">Tyndale House Publishers</a> for their generous open-licensing of this Bible dictionary.</p>' },
        'UTN': {'about': '<p class="about">unfoldingWord® Translation Notes (2023).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating <a href="https://git.door43.org/unfoldingWord/en_tn">these notes</a> to assist Bible translators.</p>' },
        'UBS': {'about': '<p class="about">United Bible Societies open-licenced dictionaries (2023).</p>',
                'copyright': '''<p class="copyright"><b>UBS Dictionary of Biblical Hebrew</b>, Copyright © United Bible Societies, 2023. Adapted from Semantic Dictionary of Biblical Hebrew © 2000-2023 United Bible Societies.</p>
<p class="copyright"><b>UBS Dictionary of New Testament Greek</b>, Copyright © United Bible Societies, 2023. Adapted from Semantic Dictionary of Biblical Greek: © United Bible Societies 2018-2023, which is adapted from Greek-English Lexicon of the New Testa­ment: Based on Semantic Domains, Eds. J P Louw, Eugene Albert Nida © United Bible Societies 1988, 1989.</p>''',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://github.com/Freely-Given-org/ubs-open-license">UBS</a> for making these available.</p>' },
        'THBD': {'about': '<p class="about"><a href="https://devpost.com/software/theographic">Theographic Bible Database</a>.</p>',
                'copyright': '''<p class="copyright">Developed by Robert Rouse and others, but no copyright statement discovered.</p>''',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a> according to <a href="https://github.com/robertrouse/theographic-bible-metadata#license">this</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to Robert Rouse for being an early and innovative <a href="https://www.airtable.com/universe/expnj1m8PhSHJ5W3M/theographic-bible-database-info">collector and organiser</a> of this information, as well as his impressive presentations and designs at <a href="https://Viz.Bible/">Viz.Bible</a>.</p>' },
        'BMM': {'about': '<p class="about"><a href="https://BibleMapper.com">BibleMapper.com</a> Maps.</p>',
                'copyright': '''<p class="copyright">All maps and text, copyright © by David P. Barrett. All rights reserved.</p>''',
                'licence': '<p class="licence">You are welcome to use these maps for any non-commercial purposes.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to David Barrett for researching and designing these and making them available (in his spare time).</p>' },
    }

    if not TEST_MODE_FLAG and UPDATE_ACTUAL_SITE_WHEN_BUILT_FLAG:
        assert len(BibleLocations) >= 57, len(BibleLocations)
    for versionLocation in BibleLocations.values():
        assert isinstance( versionLocation, tuple ) \
            or versionLocation.startswith('../copiedBibles/') \
            or versionLocation.startswith('../Bibles/') \
            or versionLocation.startswith('../../OpenEnglishTranslation--OET/') \
            or versionLocation.startswith('../../Forked/'), f"{versionLocation=}"
    assert len(BibleVersionDecorations) == len(BibleVersions) + len(auxilliaryVersions) + NUM_EXTRA_MODES - len(versionsWithoutTheirOwnPages), \
        f"{len(BibleVersionDecorations)=} {len(BibleVersions)=} + {len(auxilliaryVersions)=} + {NUM_EXTRA_MODES=} - {len(versionsWithoutTheirOwnPages)=} sum={len(BibleVersions)+len(auxilliaryVersions)+NUM_EXTRA_MODES-len(versionsWithoutTheirOwnPages)}"
        # Above adds Parallel and Interlinear and Dictionary but subtracts selected-verses-only versions
    assert len(BibleVersions) >= len(BibleLocations) # OET is a pseudo-version
    assert len(BibleNames)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad) >= len(BibleLocations) # OET is a pseudo-version

    preloadedBibles = {}
    sectionsLists = {}
# end of State class

state = State()

CNTR_BOOK_ID_MAP = {
    'MAT':40, 'MRK':41, 'LUK':42, 'JHN':43, 'ACT':44,
    'ROM':45, 'CO1':46, 'CO2':47, 'GAL':48, 'EPH':49, 'PHP':50, 'COL':51, 'TH1':52, 'TH2':53, 'TI1':54, 'TI2':55, 'TIT':56, 'PHM':57,
    'HEB':58, 'JAM':58, 'PE1':60, 'PE2':61, 'JN1':62, 'JN2':63, 'JN3':64, 'JDE':65, 'REV':66}

def reorderBooksForOETVersions( givenBookList:list[str] ) -> list[str]:
    """
    OET OT needs to put EZR NEH after MAL
    OET NT needs to put JHN and MRK before MAT
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"reorderBooksForOETVersions( {type(givenBookList)} ({len(givenBookList)}) {givenBookList} )" )

    newBookList = []
    for BBB in state.OET_BOOK_ORDER:
        if BBB in givenBookList:
            newBookList.append( BBB )

    assert len(newBookList) == len(givenBookList), f"createSitePages.reorderBooksForOETVersions ({len(newBookList)}) {newBookList=} from ({len(givenBookList)}) {givenBookList=} {[BBB for BBB in givenBookList if BBB not in newBookList]}"
    return newBookList
# end of createSitePages.reorderBooksForOETVersions



def briefDemo() -> None:
    """
    Brief demo to check module is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the settings
    print( f"({len(state.OET_BOOK_ORDER)}) {state.OET_BOOK_ORDER=}" )
# end of settings.briefDemo

def fullDemo() -> None:
    """
    Full demo to check module is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the settings
    print( f"({len(state.OET_BOOK_ORDER)}) {state.OET_BOOK_ORDER=}" )
# end of settings.fullDemo

if __name__ == '__main__':
    # Main program to handle command line parameters and then run what they want.
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of settings.py
