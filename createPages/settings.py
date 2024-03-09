#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# settings.py
#
# Module handling OpenBibleData settings functions
#
# Copyright (C) 2023-2024 Robert Hunt
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

Creates the OpenBibleData site with
    Whole document (‘book’) pages
    Section pages
    Whole chapter pages
    Parallel verse pages
and more pages to come hopefully.

CHANGELOG:
    2024-01-11 Load all OET-LV NT books
"""
from gettext import gettext as _
from typing import List
from pathlib import Path

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27


LAST_MODIFIED_DATE = '2024-02-23' # by RJH
SHORT_PROGRAM_NAME = "settings"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.94'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False # Adds debugging output

OET_VERSION = 'v0.04'

TEST_MODE = True # Writes website into Test subfolder
ALL_PRODUCTION_BOOKS = not TEST_MODE # If set to False, only selects one book per version for a faster test build
ALL_TEST_REFERENCE_PAGES = False # If in Test mode, make ALL word/lemma pages, or just the RELEVANT ones
UPDATE_ACTUAL_SITE_WHEN_BUILT = True # The pages are initially built in a tmp folder so need to be copied to the final destination

TEMP_BUILD_FOLDER = Path( '/tmp/OBDHtmlPages/' )
NORMAL_DESTINATION_FOLDER = Path( '../htmlPages/' )
DEBUG_DESTINATION_FOLDER = NORMAL_DESTINATION_FOLDER.joinpath( 'Test/')
DESTINATION_FOLDER = DEBUG_DESTINATION_FOLDER if TEST_MODE or BibleOrgSysGlobals.debugFlag \
                        else NORMAL_DESTINATION_FOLDER

TEST_OT_BOOK_LIST = ['GEN','RUT'] # RUT plus books in progress
TEST_NT_BOOK_LIST = ['MRK','REV'] # MRK plus books in progress
TEST_BOOK_LIST = TEST_OT_BOOK_LIST + TEST_NT_BOOK_LIST

OET_LV_BOOK_LIST = ['RUT','JNA','EST'] + BOOKLIST_NT27
OET_RV_BOOK_LIST = ['RUT','JNA','EST'] + (
    ['JHN','MRK','MAT','LUK','ACT', 'ROM','CO1','CO2', 'GAL','EPH','PHP','COL', 'TH1','TH2', 'TI1','TI2','TIT','PHM', 'HEB', 'JAM', 'PE1','PE2', 'JN1','JN2','JN3', 'JDE', 'REV']
    if TEST_MODE else
    ['JHN','MRK','MAT','LUK','ACT', 'ROM','CO1','CO2', 'GAL','EPH','PHP','COL', 'TH1','TH2', 'TI1','TI2','TIT','PHM', 'HEB', 'JAM', 'PE1','PE2', 'JN1','JN2','JN3', 'JDE'] )
# TODO: What about 'INT' ?
OET_RV_BOOK_LIST_WITH_FRT = ['FRT'] + OET_RV_BOOK_LIST
# NT_BOOK_LIST_WITH_FRT = ['FRT'] + BOOKLIST_NT27
# assert len(NT_BOOK_LIST_WITH_FRT) == 27+1
# OT_BOOK_LIST_WITH_FRT = ['FRT'] + BOOKLIST_OT39
# assert len(OT_BOOK_LIST_WITH_FRT) == 39+1

SITE_NAME = 'Open Bible Data'
SITE_ABBREVIATION = 'OBD'

# The version to link to when the OET doesn't have that book (yet)
ALTERNATIVE_VERSION = 'WEB' # Should be a version with all books present

NUM_EXTRA_MODES = 5 # Related, parallel and interlinear verses, dictionary, and search

UNFINISHED_WARNING_TEXT = 'This is still a very early look into the unfinished text of the <em>Open English Translation</em> of the Bible. Please double-check the text in advance before using in public.'
UNFINISHED_WARNING_PARAGRAPH = f'<p class="rem">{UNFINISHED_WARNING_TEXT}</p>'

JAMES_NOTE_TEXT = 'Note that the <em>OET</em> uses ‘Yacob’ for ‘The Letter of Jacob’ (wrongly called ‘James’ in older Bibles).'
JAMES_NOTE_PARAGRAPH = f'<p class="rem">{JAMES_NOTE_TEXT}</p>'

BY_DOCUMENT_TEXT = 'Remember that ancient letters were meant to be read in their entirety, just like modern letters. We provide a byChapter mode for convenience only, but mostly recommend the byDocument and bySection modes for personal reading.'
BY_DOCUMENT_PARAGRAPH = f'<p class="rem">{BY_DOCUMENT_TEXT}</p>'



class State:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    # This first one specifies the order in which everything is processed
    BibleVersions = ['OET', # NOTE: OET is a "pseudo-version" containing both OET-RV and OET-LV side-by-side and handled separately in many places
                'OET-RV','OET-LV',
                'ULT','UST',
                'BSB','BLB',
                'OEB','ISV','CSB','NLT',
                'NIV','CEV','ESV','NASB','LSB',
                'JQT','2DT','1ST','TPT',
                'WEB','WMB','NET','LSV','FBV','TCNT','T4T','LEB','NRSV','NKJV','BBE',
                'JPS','ASV','DRA','YLT','DBY','RV','WBS','KJB','BB','GNV','CB',
                'TNT','WYC',
                'LUT','CLV',
                'SR-GNT','UGNT','SBL-GNT','TC-GNT',
                'BRN','BrLXX', 'UHB',
                # NOTES:
                'TOSN','UTN',
                ]
    # NOTE: The above list has entries deleted by preloadBibles() if they fail to load
    #           (often because we temporarily remove the BibleLocation below)
    allBibleVersions = BibleVersions[:] # Keep a copy with the full list

    # Specific short lists
    auxilliaryVersions = ('OET','TTN','TOBD') # These ones don't have their own Bible locations at all
    # The following three lines are also in selectedVersesVersions.py
    selectedVersesOnlyVersions = ('CSB','NLT','NIV','CEV','ESV','NASB','LSB','JQT','2DT','1ST','TPT','NRSV','NKJV' ) # These ones have .tsv sources (and don't produce Bible objects)
    numAllowedSelectedVerses   = (  300,  500,  500,  500,  500,   500, 1000,   20, 300,  300,  250,   300,   300 ) # Order must match above list
    assert len(numAllowedSelectedVerses) == len(selectedVersesOnlyVersions)
    versionsWithoutTheirOwnPages = selectedVersesOnlyVersions + ('LUT','CLV', 'UGNT','SBL-GNT','TC-GNT', 'BRN','BrLXX', 'TOSN','TTN','UTN')

    # NOTE: We don't display the versionsWithoutTheirOwnPages, so don't need decorations for them
    BibleVersionDecorations = { 'OET':('<b>','</b>'),'OET-RV':('<b>','</b>'),'OET-LV':('<b>','</b>'),
                'ULT':('',''),'UST':('',''),
                'BSB':('',''),'BLB':('',''),
                'OEB':('',''),'ISV':('',''),
                'WEB':('',''),'WMB':('',''),'NET':('',''),'LSV':('',''),'FBV':('',''),'TCNT':('<small>','</small>'),'T4T':('',''),'LEB':('',''),'BBE':('',''),
                'JPS':('<small>','</small>'),'ASV':('',''),'DRA':('<small>','</small>'),'YLT':('',''),'DBY':('',''),'RV':('',''),
                'WBS':('<small>','</small>'),
                'KJB':('',''),'BB':('',''),'GNV':('',''),'CB':('',''),
                'TNT':('',''),'WYC':('',''), #'CLV':('<small>','</small>'),
                'SR-GNT':('<b>','</b>'), # 'UGNT':('<small>','</small>'),'SBL-GNT':('<small>','</small>'),'TC-GNT':('<small>','</small>'),
                # 'BRN':('<small>','</small>'),'BrLXX':('',''),
                'UHB':('<b>','</b>'),
                'Related':('<b>','</b>'), 'Parallel':('<b>','</b>'), 'Interlinear':('<b>','</b>'), 'Dictionary':('<b>','</b>'), 'Search':('<b>','</b>'),
                # NOTES:
                'TOSN':('',''),'UTN':('',''),
                }

                ## 'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.osis.xml', # OSIS
                ## 'WYC': '../copiedBibles/English/eBible.org/Wycliffe/',
    BibleLocations = {
                'OET-RV': '../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',
                'OET-LV-OT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_OT_USFM/', # Not ESFM yet
                'OET-LV-NT': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_ESFM/', # No OT here
                'SR-GNT': '../../Forked/CNTR-SR/SR usfm/', # We moved these up in the list because they're now compulsory
                'UHB': '../copiedBibles/Original/unfoldingWord.org/UHB/',
                # NOTE: The program will still run if some of these below are commented out or removed
                # (e.g., this can be done quickly for a faster test)
                'ULT': '../copiedBibles/English/unfoldingWord.org/ULT/',
                'UST': '../copiedBibles/English/unfoldingWord.org/UST/',
                # However, if they're all commented out, 'assert doneHideablesDiv' will fail in createParallelVersePages.py
                'BSB': '../copiedBibles/English/Berean.Bible/BSB/',
                'BLB': '../copiedBibles/English/Berean.Bible/BLB/blb.modified.txt', # NT only so far
                'OEB': '../copiedBibles/English/OEB/',
                # 'ISV': '',
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
                'WEB': '../copiedBibles/English/eBible.org/WEB/',
                'WMB': '../copiedBibles/English/eBible.org/WMB/',
                'NET': '../copiedBibles/English/eBible.org/NET/',
                'LSV': '../copiedBibles/English/eBible.org/LSV/',
                'FBV': '../copiedBibles/English/eBible.org/FBV/',
                'TCNT': '../copiedBibles/English/eBible.org/TCNT/',
                'T4T': '../copiedBibles/English/eBible.org/T4T/',
                'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.xml', # not OSIS
                'NRSV': '../copiedBibles/English/NRSV_verses.tsv',
                'NKJV': '../copiedBibles/English/NKJV_verses.tsv',
                'BBE': '../copiedBibles/English/eBible.org/BBE/',
                'JPS': '../copiedBibles/English/eBible.org/JPS/',
                'ASV': '../copiedBibles/English/eBible.org/ASV/',
                'DRA': '../copiedBibles/English/eBible.org/DRA/',
                'YLT': '../copiedBibles/English/eBible.org/YLT/',
                'DBY': '../copiedBibles/English/eBible.org/DBY/',
                'RV': '../copiedBibles/English/eBible.org/RV/', # with deuterocanon
                'WBS': '../copiedBibles/English/eBible.org/RV/',
                'KJB': '../copiedBibles/English/eBible.org/KJB/', # with deuterocanon
                'BB': '/mnt/SSDs/Bibles/DataSets/BibleSuperSearch.com/v5.0/TXT/bishops.txt',
                'GNV': '../copiedBibles/English/eBible.org/GNV/',
                'CB': '/mnt/SSDs/Bibles/DataSets/BibleSuperSearch.com/v5.0/TXT/coverdale.txt',
                'TNT': '../copiedBibles/English/eBible.org/TNT/',
                'WYC': '/mnt/SSDs/Bibles/Zefania modules/SF_2009-01-20_ENG_BIBLE_WYCLIFFE_(JOHN WYCLIFFE BIBLE).xml',
                'LUT': '../copiedBibles/German/Zefania/LUT1545/SF_2009-01-20_GER_LUTH1545STR_(LUTHER 1545 MIT STRONGS).xml',
                'CLV': '../copiedBibles/Latin/eBible.org/CLV/',
                'UGNT': '../copiedBibles/Original/unfoldingWord.org/UGNT/',
                'SBL-GNT': '../../Forked/SBLGNT/data/sblgnt/text/',
                'TC-GNT': '../copiedBibles/Greek/eBible.org/TC-GNT/',
                'BRN': '../copiedBibles/English/eBible.org/Brenton/', # with deuterocanon and OTH,XXA,XXB,XXC,
                'BrLXX': '../copiedBibles/Greek/eBible.org/BrLXX/',
                # NOTE: Dictionary and notes are special cases here at the end (skipped in many parts of the program)
                'TOSN': '../copiedBibles/English/Tyndale/OSN/', # This one also loads TTN (Tyndale Theme Notes)
                'UTN': '../copiedBibles/English/unfoldingWord.org/UTN/',
                }

    BibleNames = {
                'OET': 'Open English Translation (2030)',
                'OET-RV': 'Open English Translation—Readers’ Version (2030)',
                'OET-LV': 'Open English Translation—Literal Version (2025)',
                'ULT': 'unfoldingWord® Literal Text (2023)',
                'UST': 'unfoldingWord® Simplified Text (2023)',
                'BSB': 'Berean Study/Standard Bible (2020)',
                'BLB': 'Berean Literal Bible NT (2022)',
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
                'WEB': 'World English Bible (2023)',
                'WMB': 'World Messianic Bible (2023) / Hebrew Names Version (HNV)',
                'NET': 'New English Translation (2016)',
                'LSV': 'Literal Standard Version (2020)',
                'FBV': 'Free Bible Version (2018)',
                'TCNT': 'Text-Critical New Testament (2022, Byzantine)',
                'T4T': 'Translation for Translators (2017)',
                'LEB': 'Lexham English Bible (2010,2012)',
                'NRSV': 'New Revised Standard Version (1989)',
                'NKJV': 'New King James Version (1982)',
                'BBE': 'Bible in Basic English (1965)',
                'JPS': 'Jewish Publication Society TaNaKH (1917)',
                'ASV': 'American Standard Version (1901)',
                'DRA': 'Douay-Rheims American Edition (1899)',
                'YLT': 'Youngs Literal Translation (1898)',
                'DBY': 'Darby Translation (1890)',
                'RV': 'English Revised Version (1885)',
                'WBS': 'Webster Bible (American, 1833)',
                'KJB': 'King James Bible (1769)',
                'BB': 'Bishops Bible (1568,1602)',
                'GNV': 'Geneva Bible (1557-1560,1599)',
                'GB': 'Great Bible (1539)', # Not in OBD yet
                'CB': 'Coverdale Bible (1535-1553)',
                'TNT': 'Tyndale New Testament (1526)',
                'WYC': 'Wycliffe Bible (1382)',
                'LUT': 'Luther Bible (1545)',
                'CLV': 'Clementine Vulgate (Latin, 1592)',
                'SR-GNT': 'Statistical Restoration Greek New Testament (2022)',
                'UGNT': 'unfoldingWord® Greek New Testament (2022)',
                'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2020???)',
                'TC-GNT': 'Text-Critical Greek New Testament (2010, Byzantine)',
                'BRN': 'Brenton Septuagint Translation (1851)',
                'BrLXX': '(Brenton’s) Ancient Greek translation of the Hebrew Scriptures (~250 BC)',
                'UHB': 'unfoldingWord® Hebrew Bible (2022)',
                'TOSN': 'Tyndale Open Study Notes (2022)',
                'TOBD': 'Tyndale Open Bible Dictionary (2023)',
                'UTN': 'unfoldingWord® Translation Notes (2023)',
                'UBS': 'United Bible Societies open-license resources (2023)',
                }

    booksToLoad = {
                'OET': OET_RV_BOOK_LIST_WITH_FRT,
                'OET-RV': ['ALL'], # Load ALL coz we use related sections anyway OET_RV_BOOK_LIST_WITH_FRT,
                'OET-LV': OET_LV_BOOK_LIST,
                'ULT': ['ALL'],
                'UST': ['ALL'], # MRK 13:13 gives \\add error (24Jan2023)
                'BSB': ['ALL'],
                'BLB': ['NT'],
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
                'WEB': ['ALL'],
                'WMB': ['ALL'],
                'NET': ['ALL'],
                'LSV': ['ALL'],
                'FBV': ['ALL'],
                'TCNT': ['ALL'],
                'T4T': ['ALL'],
                'LEB': ['ALL'],
                'NRSV': ['ALL'],
                'NKJV': ['ALL'],
                'BBE': ['ALL'],
                'JPS': ['ALL'],
                'ASV': ['ALL'],
                'DRA': ['ALL'],
                'YLT': ['ALL'],
                'DBY': ['ALL'],
                'RV': ['ALL'],
                'WBS': ['ALL'],
                'KJB': ['ALL'],
                'BB': ['ALL'],
                'GNV': ['ALL'],
                'CB': ['ALL'],
                'TNT': ['ALL'],
                'WYC': ['ALL'],
                'LUT': ['ALL'],
                'CLV': ['ALL'],
                'SR-GNT': ['ALL'],
                'UGNT': ['ALL'],
                'SBL-GNT': ['ALL'],
                'TC-GNT': ['ALL'],
                'BRN': ['ALL'],
                'BrLXX': ['ALL'],
                'UHB': ['ALL'],
                # NOTES:
                'TOSN': ['ALL'],
                'UTN': ['ALL'],
            } if ALL_PRODUCTION_BOOKS else {
                'OET': ['FRT'] + TEST_BOOK_LIST,
                'OET-RV': ['ALL'], # Load ALL coz we use related sections anyway ['FRT'] + TEST_BOOK_LIST,
                'OET-LV': TEST_BOOK_LIST,
                'ULT': ['FRT'] + TEST_BOOK_LIST,
                'UST': TEST_BOOK_LIST, # Has no FRT for some reason
                'BSB': TEST_BOOK_LIST,
                'BLB': TEST_NT_BOOK_LIST, # NT only
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
                'WEB': TEST_BOOK_LIST,
                'WMB': TEST_BOOK_LIST,
                'NET': TEST_BOOK_LIST,
                'LSV': TEST_BOOK_LIST,
                'FBV': TEST_BOOK_LIST,
                'TCNT': TEST_NT_BOOK_LIST, # NT only
                'T4T': TEST_BOOK_LIST,
                'LEB': TEST_BOOK_LIST,
                'NRSV': TEST_BOOK_LIST,
                'NKJV': TEST_BOOK_LIST,
                'BBE': TEST_BOOK_LIST,
                'JPS': TEST_OT_BOOK_LIST,
                'ASV': TEST_BOOK_LIST,
                'DRA': TEST_BOOK_LIST,
                'YLT': TEST_BOOK_LIST,
                'DBY': TEST_BOOK_LIST,
                'RV': TEST_BOOK_LIST,
                'WBS': TEST_BOOK_LIST,
                'KJB': TEST_BOOK_LIST,
                'BB': TEST_BOOK_LIST,
                'GNV': TEST_BOOK_LIST,
                'CB': TEST_BOOK_LIST,
                'TNT': TEST_NT_BOOK_LIST, # NT only
                'WYC': TEST_BOOK_LIST,
                'LUT': TEST_BOOK_LIST,
                'CLV': TEST_BOOK_LIST,
                'SR-GNT': TEST_NT_BOOK_LIST, # NT only
                'UGNT': TEST_NT_BOOK_LIST, # NT only
                'SBL-GNT': TEST_NT_BOOK_LIST, # NT only
                'TC-GNT': TEST_NT_BOOK_LIST, # NT only
                'BRN': TEST_OT_BOOK_LIST, # OT only
                'BrLXX': TEST_OT_BOOK_LIST, # OT only
                'UHB': TEST_OT_BOOK_LIST, # OT only
                # NOTES:
                'TOSN': TEST_BOOK_LIST,
                'UTN': TEST_BOOK_LIST,
            }

    detailsHtml = {
        'OET': {'about': f'''<p class="about">The (still unfinished) <em>Open English Translation</em> ({OET_VERSION}) consists of a <em>Readers’ Version</em> and a <em>Literal Version</em> side-by-side.
You can read more about the design of the <em>OET</em> at <a href="https://OpenEnglishTranslation.Bible/Design/Overview">OpenEnglishTranslation.Bible/Design/Overview</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010-2024 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, radical, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</p>' },
        'OET-RV': {'about': '''<p class="about">The (still unfinished) <em>Open English Translation Readers’ Version</em> is a new, modern-English easy-to-read translation of the Bible.
You can read more about the design of the <em>OET-RV</em> at <a href="https://OpenEnglishTranslation.Bible/Design/ReadersVersion">OpenEnglishTranslation.Bible/Design/ReadersVersion</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010-2024 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</p>' },
        'OET-LV': {'about': '''<p class="about">The (still unfinished) <em>Open English Translation Literal Version</em> is a tool designed to give a look into what was actually written in the original Hebrew or Greek manuscripts.
You can read more about the design of the <em>OET-LV</em> at <a href="https://OpenEnglishTranslation.Bible/Design/LiteralVersion">OpenEnglishTranslation.Bible/Design/LiteralVersion</a>.</p>''',
                'copyright': '<p class="copyright">Copyright © 2010-2024 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '''<p class="acknwldg">Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.
We are very grateful to Dr. Alan Bunning of the <a href="https://GreekCNTR.org">Center for New Testament Restoration</a> whose many years of hard work this <em>OET-LV</em> is based on.
We’re also grateful to the <a href="https://www.Biblica.com/clear/">Biblica Clear Bible team</a> who provide the pronoun referential information as part of their <a href="https://GitHub.com/Clear-Bible/macula-greek">Macula Greek</a> project.</p>''' },
        'ULT': {'about': '<p class="about">unfoldingWord® Literal Text (2023) and derived from the 1901 ASV.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating this Bible translation which is designed to be a tool for Bible translators.</p>' },
        'UST': {'about': '<p class="about">unfoldingWord® Simplified Text (2023). The UST has all passive constructions changed to active forms, and all idioms replaced with their English meanings.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by unfoldingWord.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://www.unfoldingword.org/">unfoldingWord</a> for creating this specialised Bible translation which is designed to be a tool for Bible translators.</p>' },
        'BSB': {'about': '<p class="about">Berean Standard Bible (2020).</p>',
                'copyright': '<p class="copyright">Copyright © 2016, 2020 by Bible Hub. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">The Berean Bible text is <a href="https://berean.bible/terms.htm#Top">free to use</a> in any electronic form to promote the reading, learning, and understanding of the Holy Bible as the Word of God.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://biblehub.com/">BibleHub</a> for the <a href="https://berean.bible/">BSB</a>.</p>' },
        'BLB': {'about': '<p class="about">Berean Literal Bible (2022).</p>',
                'copyright': '<p class="copyright">Copyright © 2022 by Bible Hub. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">The Berean Bible text is <a href="https://berean.bible/terms.htm#Top">free to use</a> in any electronic form to promote the reading, learning, and understanding of the Holy Bible as the Word of God.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://biblehub.com/">BibleHub</a> for the <a href="https://berean.bible/">BLB</a>.</p>' },
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
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'NLT': {'about': '<p class="about">New Living Translation (2015).</p>',
                'copyright': '<p class="copyright">Holy Bible, New Living Translation, copyright © 1996, 2004, 2015 by Tyndale House Foundation. Used by permission of Tyndale House Publishers. All rights reserved.</p>',
                'licence': '<p class="licence">five hundred (500) verses without the express written permission of the publisher, providing the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five percent (25%) or more of the total text of the work in which they are quoted.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'NIV': {'about': '<p class="about">New International Version (2011).</p>',
                'copyright': '<p class="copyright">Scripture quotations taken from The Holy Bible, New International Version® NIV®. Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.™ Used by permission. All rights reserved worldwide.</p>',
                'licence': '<p class="licence">The NIV® text may be quoted in any form (written, visual, electronic or audio), up to and inclusive of five hundred (500) verses without the express written permission of the publisher, providing the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five percent (25%) or more of the total text of the work in which they are quoted.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'CEV': {'about': '<p class="about">Contemporary English Version, Second Edition (2006).</p>',
                'copyright': '<p class="copyright">Scripture quotations marked (CEV) are from the Contemporary English Version Copyright © 1991, 1992, 1995 by American Bible Society. Used by Permission.</p>',
                'licence': '<p class="licence">Text from the Contemporary English Version (CEV) may be quoted in any form (written, visual, electronic or audio) up to and inclusive of five hundred (500) verses without written permission, providing the verses quoted do not amount to 50% of a complete book of the Bible nor do the verses account for twenty-five percent (25%) or more of the total text of the work in which they are quoted and the work is available for non-commercial use.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'ESV': {'about': '<p class="about">English Standard Version (2001).</p>',
                'copyright': '<p class="copyright">Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), copyright © 2001 by Crossway Bibles, a publishing ministry of Good News Publishers. Used by permission. All rights reserved.</p>',
                'licence': '<p class="licence">The ESV text may be quoted (in written, visual, or electronic form) up to and inclusive of five hundred (500) verses without express written permission of the publisher, providing that the verses quoted do not amount to a complete book of the Bible nor do the verses quoted account for twenty-five (25%) percent or more of the total text of the work in which they are quoted.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'NASB': {'about': '<p class="about">New American Standard Bible (1995): A revision of the American Standard Version (ASV) incorporating information from the Dead Sea Scrolls.</p>',
                'copyright': '<p class="copyright">Scripture taken from the NEW AMERICAN STANDARD BIBLE, © Copyright The Lockman Foundation 1960, 1962, 1963, 1968, 1971, 1972, 1973, 1975, 1977, 1995. Used by permission.</p>',
                'licence': '<p class="licence">The text of the New American Standard Bible® may be quoted and/or reprinted up to and inclusive of five hundred (500) verses without express written permission of The Lockman Foundation, providing that the verses do not amount to a complete book of the Bible nor do the verses quoted account for more than 25% of the total work in which they are quoted.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'LSB': {'about': '<p class="about"><a href="https://LSBible.org/">Legacy Standard Bible</a> (2021): A revision of the 1995 New American Standard Bible (NASB) completed in October 2021.</p>',
                'copyright': '<p class="copyright">Copyright © 2021 by The Lockman Foundation. All Rights Reserved.</p>',
                'licence': '<p class="licence">The text of the LSB® (Legacy Standard Bible®) may be quoted in any form (written, visual, electronic, or audio) up to and inclusive of one thousand (1,000) verses providing the verses do not amount to a complete book of the Bible, nor do the verses quoted account for more than 50% of the total text of the work in which they are quoted, nor may more than 1,000 verses be stored in an electronic retrieval system. <small>(Downloaded from <a href="https://LSBible.org/permission-to-quote-the-lsb/">LSBible.org/permission-to-quote-the-lsb/</a> January 2024)</small></p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'JQT': {'about': '<p class="about">James Quiggle Translation New Testament (2023).</p>',
                'copyright': '<p class="copyright">Translated and published by James D. Quiggle, copyright 2023.</p>',
                'licence': '<p class="licence">Limited to twenty verses.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        '2DT': {'about': '<p class="about">The Second Testament: A new translation (2023) by Scot McKnight.</p>',
                'copyright': '<p class="copyright">Copyright © 2023 by IVP Academic. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">Up to 300 verses may be used.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        '1ST': {'about': '<p class="about">The First Testament: A new translation (2018) by John Goldingay.</p>',
                'copyright': '<p class="copyright">Copyright © 2018 by IVP Academic. Used by Permission. All Rights Reserved Worldwide.</p>',
                'licence': '<p class="licence">Up to 300 verses may be used.</p>',
                'acknowledgements': '<p class="acknwldg"></p>' },
        'TPT': {'about': '<p class="about">The Passion Translation (2017) by Brian Simmons.</p>',
                'copyright': '<p class="copyright">Scripture quotations marked TPT are from The Passion Translation®. Copyright © 2017, 2018, 2020 by Passion & Fire Ministries, Inc. Used by permission. All rights reserved. ThePassionTranslation.com.</p>',
                'licence': '<p class="licence">Up to 250 verses may be used.</p>',
                'acknowledgements': '<p class="acknwldg">A few selected verses included here for reference purposes only—this is not a recommended as a reliable Bible translation.</p>' },
        'WEB': {'about': '<p class="about">World English Bible (2023).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WMB': {'about': '<p class="about">World Messianic Bible (2023) also known as the HNV: Hebrew Names Version.</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'NET': {'about': '<p class="about">New English Translation (2016).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence"><a href="https://bible.org/downloads">Free</a> (without their notes).</p>',
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
        'LEB': {'about': '<p class="about">Lexham English Bible (2010,2012).</p>',
                'copyright': '<p class="copyright">Copyright © 2012 <a href="http://www.logos.com/">Logos Bible Software</a>. Lexham is a registered trademark of <a href="http://www.logos.com/">Logos Bible Software</a>.</p>',
                'licence': '<p class="licence">You can give away the <a href="https://lexhampress.com/LEB-License">Lexham English Bible</a>, but you can’t sell it on its own. If the LEB comprises less than 25% of the content of a larger work, you can sell it as part of that work.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="http://www.logos.com/">Logos Bible Software</a> for supplying a XML file.</p>' },
        'NRSV': {'about': '<p class="about">New Revised Standard Version (1989).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'NKJV': {'about': '<p class="about">New King James Version (1979).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'BBE': {'about': '<p class="about">Bible in Basic English (1965).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'JPS': {'about': '<p class="about">Jewish Publication Society TaNaKH (1917).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'ASV': {'about': '<p class="about">American Standard Version (1901).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'DRA': {'about': '<p class="about">Douay-Rheims American Edition (1899).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'YLT': {'about': '<p class="about">Youngs Literal Translation (1898).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'DBY': {'about': '<p class="about">Darby Translation (1890).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'RV': {'about': '''<p class="about">The English Revised Version (1885) was an officially authorised revision of the King James Bible.
                            (See <a href="https://en.wikipedia.org/wiki/Revised_Version">Wikipedia entry</a>.)</p>''',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WBS': {'about': '<p class="about">Webster Bible (1833).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'KJB': {'about': '<p class="about">King James Bible (1611-1769).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'BB': {'about': '<p class="about">Bishops Bible (1568,1602).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">Public Domain.</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'GNV': {'about': '<p class="about">Geneva Bible (1557-1560,1599).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'CB': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Coverdale_Bible">Coverdale Bible</a> (1535-1553).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">Public Domain.</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'TNT': {'about': '<p class="about">Tyndale New Testament (1526).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">(coming).</p>' },
        'WYC': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Wycliffe%27s_Bible">Wycliffe Bible</a> (1382).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">Public Domain.</p>',
                'acknowledgements': '<p class="acknwldg">The entire English-speaking world is indebted to <a href="https://en.wikipedia.org/wiki/John_Wycliffe">John Wycliffe</a> for his brave work to make the Bible available in the language of the common people at a time when priests insisted that the Bible was only valid in Latin.</p>' },
        'LUT': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Luther_Bible">Luther’s German Bible</a> (1545).</p>',
                'copyright': '<p class="copyright">Public Domain.</p>',
                'licence': '<p class="licence">Public Domain.</p>',
                'acknowledgements': '<p class="acknwldg">The entire German-speaking world is indebted to <a href="https://en.wikipedia.org/wiki/Martin_Luther">Martin Luther</a> for his brave work to make the Bible available in the language of the common people at a time when priests insisted that the Bible was only valid in Latin.</p>' },
        'CLV': {'about': '<p class="about"><a href="https://en.wikipedia.org/wiki/Sixto-Clementine_Vulgate">Clementine Vulgate Bible</a> (Latin, 1592).</p>',
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
        'SBL-GNT': {'about': '<p class="about">Society for Biblical Literature Greek New Testament (2023).</p>',
                'copyright': '<p class="copyright">Copyright © 2010 by the Society of Biblical Literature and <a href="http://www.logos.com/">Logos Bible Software</a>.</p>',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://sblgnt.com/">SBL</a> and <a href="https://www.logos.com/">Logos Bible Software</a> for supplying <a href="https://github.com/LogosBible/SBLGNT/">this GNT</a>.</p>' },
        'TC-GNT': {'about': '<p class="about">Text-Critical Greek New Testament (2010) based on Robinson/Pierpont Byzantine priority GNT (RP2018).</p>',
                'copyright': '<p class="copyright">Copyright © (coming).</p>',
                'licence': '<p class="licence">(coming).</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://eBible.org/Scriptures/details.php?id=grctcgnt">eBible.org</a> for supplying the USFM files.</p>' },
        'BRN': {'about': '<p class="about">Sir Lancelot C. L. Brenton’s 1851 translation of the ancient Greek Septuagint (LXX) translation of the Hebrew scriptures.</p>',
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
        'UBS': {'about': '<p class="about">United Bible Societies (2023).</p>',
                'copyright': '''<p class="copyright">UBS Dictionary of Biblical Hebrew, Copyright © United Bible Societies, 2023. Adapted from Semantic Dictionary of Biblical Hebrew © 2000-2023 United Bible Societies.</p>
<p class="copyright">UBS Dictionary of New Testament Greek, Copyright © United Bible Societies, 2023. Adapted from Semantic Dictionary of Biblical Greek: © United Bible Societies 2018-2023, which is adapted from Greek-English Lexicon of the New Testa­ment: Based on Semantic Domains, Eds. J P Louw, Eugene Albert Nida © United Bible Societies 1988, 1989.</p>''',
                'licence': '<p class="licence"><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p class="acknwldg">Thanks to <a href="https://github.com/Freely-Given-org/ubs-open-license">UBS</a> for making these available.</p>' },
    }

    if not TEST_MODE: assert len(BibleLocations) >= 51, len(BibleLocations)
    for versionLocation in BibleLocations.values():
        assert versionLocation.startswith('../copiedBibles/') \
            or versionLocation.startswith('../../OpenEnglishTranslation--OET/') \
            or versionLocation.startswith('../../Forked/') \
            or versionLocation.startswith('/mnt/SSDs/Bibles/'), f"{versionLocation=}"
    assert len(BibleVersionDecorations) == len(BibleVersions) + len(auxilliaryVersions) + NUM_EXTRA_MODES - len(versionsWithoutTheirOwnPages), \
        f"{len(BibleVersionDecorations)=} {len(BibleVersions)=} {len(auxilliaryVersions)=} {len(versionsWithoutTheirOwnPages)=} sum={len(BibleVersions)+len(auxilliaryVersions)+4-len(versionsWithoutTheirOwnPages)}"
        # Above adds Parallel and Interlinear and Dictionary but subtracts selected-verses-only versions and TTN
    assert len(BibleVersions)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(BibleNames)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad)-1 >= len(BibleLocations) # OET is a pseudo-version

    preloadedBibles = {}
    sectionsLists = {}
# end of State class

state = State()


def reorderBooksForOETVersions( givenBookList:List[str] ) -> List[str]:
    """
    OET needs to put JHN and MRK before MAT
    """
    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"reorderBooksForOETVersions( {type(givenBookList)} ({len(givenBookList)}) {givenBookList} )" )

    if not isinstance( givenBookList, list ):
        givenBookList = list( givenBookList )

    try: ixJHN = givenBookList.index('JHN')
    except ValueError: return givenBookList # Might not have all books included
    try: ixFirstGospel = givenBookList.index('MAT')
    except ValueError: ixFirstGospel = givenBookList.index('MRK')
    if ixFirstGospel<ixJHN:
        # print( f"{ixFirstGospel=} {ixJHN=} {givenBookList}")
        givenBookList.remove( 'JHN' )
        givenBookList.remove( 'MRK' )
        givenBookList.insert( ixFirstGospel, 'MRK' )
        givenBookList.insert( ixFirstGospel, 'JHN' )
        # print( f"Returning ({len(givenBookList)}) {givenBookList}" )

    return givenBookList
# end of createSitePages.reorderBooksForOETVersions



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the settings object
    settings()
# end of settings.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the settings object
    settings()
# end of settings.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of settings.py
