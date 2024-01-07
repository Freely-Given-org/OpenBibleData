#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSitePages.py
#
# Module handling OpenBibleData createSitePages functions
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
Module handling createSitePages functions.

Creates the OpenBibleData site with
    Whole document (‘book’) pages
    Section pages
    Whole chapter pages
    Parallel verse pages
and more pages to come hopefully.

CHANGELOG:
    2023-05-04 Added 'About OBD' page
    2023-05-31 Added BLB
    2023-06-01 Added TSN
    2023-07-19 Converted versions dictkeys to list for nicer display
    2023-07-30 Added selected verses from some other versions
    2023-08-16 Added PHM and put MRK between JHN and MAT
    2023-08-30 Added PHP for RV
    2023-08-31 Added COL for RV
    2023-09-06 Added list of selected versions on details pages (in TEST mode only)
    2023-09-25 Added search page
    2023-10-01 Added ROM for RV
    2023-10-10 Added German Luther 1545 Bible
    2023-10-20 Added CO2 for RV
    2023-10-24 Creates a BCV index into the OET-LV word table
    2023-12-29 Started adding OET OT
    2024-01-02 Make sure all HTML folders contain an index file
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import shutil
import glob
from datetime import date

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27

sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import load_transliteration_table

from Bibles import preloadVersions, tidyBBB #, preloadUwTranslationNotes
from createBookPages import createOETBookPages, createBookPages
from createChapterPages import createOETSideBySideChapterPages, createChapterPages
from createSectionPages import createOETSectionPages, createSectionPages
from createParallelPages import createParallelPages
from createOETInterlinearPages import createOETInterlinearPages
from createOETReferencePages import createOETReferencePages
from Dict import createTyndaleDictPages
from html import makeTop, makeBottom, checkHtml
# from selectedVersesVersions import fillSelectedVerses


LAST_MODIFIED_DATE = '2024-01-02' # by RJH
SHORT_PROGRAM_NAME = "createSitePages"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.90'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False # Adds debugging output

TEST_MODE = True # Writes website into Test subfolder
ALL_PRODUCTION_BOOKS = not TEST_MODE # If set to False, only selects one book per version for a faster test build
ALL_TEST_REFERENCE_PAGES = False # If in Test mode, make all word/lemma pages, or just the relevant ones
UPDATE_ACTUAL_SITE_WHEN_BUILT = True # The pages are initially built in a tmp folder so need to be copied to the final destination

TEMP_BUILD_FOLDER = Path( '/tmp/OBDHtmlPages/' )
NORMAL_DESTINATION_FOLDER = Path( '../htmlPages/' )
DEBUG_DESTINATION_FOLDER = NORMAL_DESTINATION_FOLDER.joinpath( 'Test/')
DESTINATION_FOLDER = DEBUG_DESTINATION_FOLDER if TEST_MODE or BibleOrgSysGlobals.debugFlag \
                        else NORMAL_DESTINATION_FOLDER

OET_BOOK_LIST = ['JNA', 'JHN','MRK','MAT','LUK','ACT', 'ROM','CO2', 'GAL','EPH','PHP','COL', 'TH1','TH2','TI1','TI2','TIT','PHM', 'HEB', 'JAM', 'PE1','PE2', 'JN1','JN2','JN3', 'JDE']
OET_BOOK_LIST_WITH_FRT = ['FRT'] + OET_BOOK_LIST # 'INT'
NT_BOOK_LIST_WITH_FRT = ['FRT'] + BOOKLIST_NT27
assert len(NT_BOOK_LIST_WITH_FRT) == 27+1
OT_BOOK_LIST_WITH_FRT = ['FRT'] + BOOKLIST_OT39
assert len(OT_BOOK_LIST_WITH_FRT) == 39+1

# The version to link to when the OET doesn't have that book (yet)
ALTERNATIVE_VERSION = 'WEB' # Should be a version with all books present

NEWLINE = '\n'


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
    numAllowedSelectedVerses   = (  300,  500,  500,  500,  500,   500,  300,   20, 300,  300,  250,   300,   300 ) # Order must match above list
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
                'UHB':('',''),
                'Parallel':('<b>','</b>'), 'Interlinear':('<b>','</b>'), 'Dictionary':('<b>','</b>'), 'Search':('<b>','</b>'),
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
                'BSB': '../copiedBibles/English/Berean.Bible/BSB/',
                'BLB': '../copiedBibles/English/Berean.Bible/BLB/blb.modified.txt', # NT only so far
                'OEB': '../copiedBibles/English/OEB/',
                # # 'ISV': '',
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
                }

    booksToLoad = {
                'OET': OET_BOOK_LIST_WITH_FRT,
                'OET-RV': OET_BOOK_LIST_WITH_FRT,
                'OET-LV': OET_BOOK_LIST,
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
                'OET': ['FRT','JNA','MRK'],
                'OET-RV': ['FRT','JNA','MRK'],
                'OET-LV': ['JNA','MRK'],
                'ULT': ['FRT','RUT','JNA','MRK'],
                'UST': ['RUT','JNA','MRK'], # MRK 13:13 gives \\add error (24Jan2023)
                'BSB': ['JNA','MRK'],
                'BLB': ['MRK'], # NT only
                'OEB': ['JNA','MRK'],
                'ISV': ['JNA','MRK'],
                'CSB': ['JNA','MRK'],
                'NLT': ['JNA','MRK'],
                'NIV': ['JNA','MRK'],
                'CEV': ['JNA','MRK'],
                'ESV': ['JNA','MRK'],
                'NASB': ['JNA','MRK'],
                'LSB': ['JNA','MRK'],
                'JQT': ['JNA','MRK'],
                '2DT': ['JNA','MRK'],
                '1ST': ['JNA','MRK'],
                'TPT': ['JNA','MRK'],
                'WEB': ['JNA','MRK'],
                'WMB': ['JNA','MRK'],
                'NET': ['JNA','MRK'],
                'LSV': ['JNA','MRK'],
                'FBV': ['JNA','MRK'],
                'TCNT': ['MRK'], # NT only
                'T4T': ['JNA','MRK'],
                'LEB': ['JNA','MRK'],
                'NRSV': ['JNA','MRK'],
                'NKJV': ['JNA','MRK'],
                'BBE': ['JNA','MRK'],
                'JPS': ['RUT','JNA'],
                'ASV': ['JNA','MRK'],
                'DRA': ['JNA','MRK'],
                'YLT': ['JNA','MRK'],
                'DBY': ['JNA','MRK'],
                'RV': ['JNA','MRK'],
                'WBS': ['JNA','MRK'],
                'KJB': ['JNA','MRK'],
                'BB': ['JNA','MRK'],
                'GNV': ['JNA','MRK'],
                'CB': ['JNA','MRK'],
                'TNT': ['MRK'], # NT only
                'WYC': ['JNA','MRK'],
                'LUT': ['JNA','MRK'],
                'CLV': ['RUT','JNA','MRK'],
                'SR-GNT': ['MRK'],
                'UGNT': ['MRK'],
                'SBL-GNT': ['MRK'],
                'TC-GNT': ['MRK'],
                'BRN': ['RUT','JNA'],
                'BrLXX': ['RUT','JNA'],
                'UHB': ['RUT','JNA'],
                # NOTES:
                'TOSN': ['RUT','JNA','MRK'],
                'UTN': ['RUT','JNA','MRK'],
            }

    detailsHtml = {
        'OET': {'about': '''<p class="about">The (still unfinished) <em>Open English Translation</em> consists of a <em>Readers’ Version</em> and a <em>Literal Version</em> side-by-side.
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
        'LSB': {'about': '<p class="about">Legacy Standard Bible (2021): A revision of the 1995 New American Standard Bible (NASB) completed in October 2021.</p>',
                'copyright': '<p class="copyright">Copyright © 2021 by The Lockman Foundation. All Rights Reserved.</p>',
                'licence': '<p class="licence">Up to ??? verses may be used.</p>',
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
    }

    if not TEST_MODE: assert len(BibleLocations) >= 51, len(BibleLocations)
    for versionLocation in BibleLocations.values():
        assert versionLocation.startswith('../copiedBibles/') \
            or versionLocation.startswith('../../OpenEnglishTranslation--OET/') \
            or versionLocation.startswith('../../Forked/') \
            or versionLocation.startswith('/mnt/SSDs/Bibles/'), f"{versionLocation=}"
    # +4 is for parallel, interlinear, dictionary, search
    assert len(BibleVersionDecorations) == len(BibleVersions) + len(auxilliaryVersions) + 4 - len(versionsWithoutTheirOwnPages), \
        f"{len(BibleVersionDecorations)=} {len(BibleVersions)=} {len(auxilliaryVersions)=} {len(versionsWithoutTheirOwnPages)=} sum={len(BibleVersions)+len(auxilliaryVersions)+4-len(versionsWithoutTheirOwnPages)}"
        # Above adds Parallel and Interlinear and Dictionary but subtracts selected-verses-only versions and TTN
    assert len(BibleVersions)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(BibleNames)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad)-1 >= len(BibleLocations) # OET is a pseudo-version

    preloadedBibles = {}
    sectionsLists = {}
# end of State class

state = State()


def createSitePages() -> bool:
    """
    Build all the pages in a temporary location
    """
    fnPrint( DEBUGGING_THIS_MODULE, "createSitePages()")
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createSitePages() running in {'TEST' if TEST_MODE else 'production'} mode with {'all production books' if ALL_PRODUCTION_BOOKS else 'reduced books being loaded'} for {len(state.BibleLocations):,} Bible versions…" )

    try: os.makedirs( TEMP_BUILD_FOLDER )
    except FileExistsError:
        assert os.path.isdir( TEMP_BUILD_FOLDER )
        cleanHTMLFolders( TEMP_BUILD_FOLDER, state )

    # Preload our various Bibles
    numLoadedVersions = preloadVersions( state )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nPreloaded {len(state.preloadedBibles)} Bible versions: {list(state.preloadedBibles.keys())}" )
    # preloadUwTranslationNotes( state )
    # fillSelectedVerses( state )

    # Load our OET worddata table
    state.OETRefData = {} # This is where we will store all our temporary ref data
    lvBible = state.preloadedBibles['OET-LV']
    assert len(lvBible.ESFMWordTables) == 1
    wordFileName = list(lvBible.ESFMWordTables.keys())[0]
    assert wordFileName.endswith( '.tsv' )
    if lvBible.ESFMWordTables[wordFileName] is None:
        lvBible.loadESFMWordFile( wordFileName )
    state.OETRefData['word_table'] = list(lvBible.ESFMWordTables.values())[0]
    columnHeaders = state.OETRefData['word_table'][0]
    assert columnHeaders == 'Ref\tGreekWord\tSRLemma\tGreekLemma\tGlossWords\tGlossCaps\tProbability\tStrongsExt\tRole\tMorphology\tTags' # If not, probably need to fix some stuff

    # Make a BCV index to the OET word table
    state.OETRefData['word_table_index'] = {}
    lastBCVref = None
    startIx = 1
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        wordRef = columns_string.split( '\t', 1 )[0] # Something like 'MAT_1:1w1'
        BCVref = wordRef.split( 'w', 1 )[0] # Something like 'MAT_1:1'
        if BCVref != lastBCVref:
            if lastBCVref is not None:
                state.OETRefData['word_table_index'][lastBCVref] = (startIx,n-1)
            startIx = n
            lastBCVref = BCVref
    state.OETRefData['word_table_index'][lastBCVref] = (startIx,n) # Save the final one

    load_transliteration_table( 'Greek' )
    load_transliteration_table( 'Hebrew' )

    # Determine our inclusive list of books for all versions
    allBBBs = set()
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        for versionAbbreviation in state.BibleVersions:
            if versionAbbreviation == 'OET': continue # OET is a pseudo version (OET-RV plus OET-LV)
            # if versionAbbreviation not in ('TTN',) \
            if versionAbbreviation in state.versionsWithoutTheirOwnPages:
                continue # We don't worry about these few selected verses here
            for entry in state.booksToLoad[versionAbbreviation]:
                if entry == BBB or entry == 'ALL':
                    if BBB in state.preloadedBibles[versionAbbreviation]:
                        allBBBs.add( BBB )
    # Now put them in the proper print order
    state.allBBBs = BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( allBBBs )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDiscovered {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )

    # Determine our list of books to process for each version
    state.BBBsToProcess, state.BBBLinks = {}, {}
    for versionAbbreviation in state.BibleVersions:
        if versionAbbreviation == 'OET': continue # This isn't a real version
        thisBible = state.preloadedBibles[versionAbbreviation]
        thisBibleBooksToLoad = state.booksToLoad[versionAbbreviation]
        print( f'{versionAbbreviation}: {thisBible=} {thisBibleBooksToLoad=}' )
        # if versionAbbreviation in state.selectedVersesOnlyVersions:
        #     state.BBBsToProcess[versionAbbreviation] = []
        #     assert isinstance( thisBible, dict )
        #     for BBB,_C,_V in thisBible: # a dict with keys like ('REV', '1', '3')
        #         if BBB not in state.BBBsToProcess[versionAbbreviation]:
        #             state.BBBsToProcess[versionAbbreviation].append( BBB )
        # else: # not selectedVersesOnlyVersions
        if versionAbbreviation not in state.selectedVersesOnlyVersions:
            state.BBBsToProcess[versionAbbreviation] = thisBible.books.keys() if thisBibleBooksToLoad==['ALL'] \
                    else BOOKLIST_NT27 if thisBibleBooksToLoad==['NT'] \
                    else thisBibleBooksToLoad
            if 'OET' in versionAbbreviation:
                state.BBBsToProcess[versionAbbreviation] = reorderBooksForOETVersions( state.BBBsToProcess[versionAbbreviation] )
            state.BBBLinks[versionAbbreviation] = []
            for BBB in state.BBBsToProcess[versionAbbreviation]:
                # We include FRT here if there is one, but it will be excluded later where irrelevant
                if BBB=='FRT' \
                or 'ALL' in thisBibleBooksToLoad \
                or BBB in thisBibleBooksToLoad:
                    filename = f'{BBB}.htm'
                    ourTidyBBB = tidyBBB( BBB )
                    state.BBBLinks[versionAbbreviation].append( f'''<a title="{BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).replace('James','Jacob/(James)')}" href="{filename}#Top">{ourTidyBBB}</a>''' )

    # Ok, let's go create some static pages
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDoing discovery on OET…" )
        state.preloadedBibles['OET-RV'].discover() # Now that all required books are loaded
        state.preloadedBibles['OET-LV'].discover() #     ..ditto..
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}version pages for OET…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'OET/' )
        createOETVersionPages( 1, versionFolder, state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV'], state )
        createOETMissingVersePage( 1, versionFolder )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        # if versionAbbreviation not in ('TTN',) \
        if versionAbbreviation in state.versionsWithoutTheirOwnPages:
            if versionAbbreviation == 'TTN': continue # These ones don't even have a folder
            # We just write a very bland index page here
            versionName = state.BibleNames[versionAbbreviation]
            indexHtml = f'<h1 id="Top">{versionName}</h1>\n'
            top = makeTop( 1, None, 'site', None, state ) \
                            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                            .replace( '__KEYWORDS__', f'Bible, {versionAbbreviation}, {versionName}' )
            folder = TEMP_BUILD_FOLDER.joinpath( f'{versionAbbreviation}/' )
            os.makedirs( folder )
            filepath = folder.joinpath( 'index.htm' )
            with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
                indexHtmlFile.write( f'''{top}{indexHtml}\n<p class="note"><a href="details.htm">See copyright details.</p>\n{makeBottom( 1, 'site', state )}''' )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
        else:
            thisBible.discover() # Now that all required books are loaded
        # if versionAbbreviation not in ('TOSN','TTN','UTN'): # We don't make separate notes pages
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}version pages for {thisBible.abbreviation}…" )
            versionFolder = TEMP_BUILD_FOLDER.joinpath( f'{thisBible.abbreviation}/' )
            createVersionPages( 1, versionFolder, thisBible, state )

    # We do this later than the createVersionPages above
    #   because we need all versions to have all books loaded and 'discovered', i.e., analysed
    #   so we know in advance which versions have section headings
    if 'OET' in state.BibleVersions: # this is a special case
        rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']
        if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings']:
            versionFolder = TEMP_BUILD_FOLDER.joinpath( f'OET/' )
            createOETSectionPages( 2, versionFolder.joinpath('bySec/'), rvBible, lvBible, state )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        if versionAbbreviation not in ('TTN',) \
        and versionAbbreviation in state.versionsWithoutTheirOwnPages: continue # We don't worry about these few selected verses here
        if versionAbbreviation not in ('TOSN','TTN','UTN'): # We don't make separate notes pages
            if thisBible.discoveryResults['ALL']['haveSectionHeadings']:
                versionFolder = TEMP_BUILD_FOLDER.joinpath( f'{thisBible.abbreviation}/' )
                createSectionPages( 2, versionFolder.joinpath('bySec/'), thisBible, state )

    # TODO: We could use multiprocessing to do all these at once
    #   (except that state is quite huge with all preloaded versions and hence expensive to pickle)
    createParallelPages( 1, TEMP_BUILD_FOLDER.joinpath('par/'), state )
    createOETInterlinearPages( 1, TEMP_BUILD_FOLDER.joinpath('il/'), state )

    createTyndaleDictPages( 1, TEMP_BUILD_FOLDER.joinpath('dct/'), state )
    createOETReferencePages( 1, TEMP_BUILD_FOLDER.joinpath('ref/'), state )

    createDetailsPages( 0, TEMP_BUILD_FOLDER, state )
    createSearchPage( 0, TEMP_BUILD_FOLDER, state )
    createAboutPage( 0, TEMP_BUILD_FOLDER, state )

    createMainIndexPage( 0, TEMP_BUILD_FOLDER, state )

    state.preloadedBibles = None # Reduce memory use now

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\n{TEMP_BUILD_FOLDER} is {getFolderSize(TEMP_BUILD_FOLDER)//1_000_000:,} MB" )

    if UPDATE_ACTUAL_SITE_WHEN_BUILT:
        # Clean away any existing folders so we can copy in the newly built stuff
        try: os.makedirs( f'{DESTINATION_FOLDER}/' )
        except FileExistsError: # they were already there
            assert os.path.isdir( DESTINATION_FOLDER )
            cleanHTMLFolders( DESTINATION_FOLDER, state )

        # Now move the site from our temporary build location to overwrite the destination location
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Moving files and folders from {TEMP_BUILD_FOLDER}/ to {DESTINATION_FOLDER}/…" )
        count = 0
        for fileOrFolderPath in glob.glob( f'{TEMP_BUILD_FOLDER}/*' ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Moving {fileOrFolderPath} to {DESTINATION_FOLDER}/…" )
            # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
            shutil.move( fileOrFolderPath, f'{DESTINATION_FOLDER}/', copy_function=shutil.copy2)
            count += 1
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Moved {count:,} folders and files into {DESTINATION_FOLDER}/." )

        # We also need to copy the TOBD maps across
        TOBDmapSourceFolder = os.path.join( state.BibleLocations['TOSN'], '../OBD/Maps/artfiles/' )
        TOBDmapDestinationFolder = DESTINATION_FOLDER.joinpath( 'dct/' )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copying TOBD maps from {TOBDmapSourceFolder} to {TOBDmapDestinationFolder}/…" )
        count = 0
        for imgFilepath in glob.glob( f'{TOBDmapSourceFolder}/*.png' ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Copying {imgFilepath} to {TOBDmapDestinationFolder}/…" )
            # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
            shutil.copy2( imgFilepath, f'{TOBDmapDestinationFolder}/' )
            count += 1
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Copied {count:,} maps into {TOBDmapDestinationFolder}/." )

        # In TEST mode, we need to copy the .css files and Bible.js across
        if DESTINATION_FOLDER != NORMAL_DESTINATION_FOLDER:
            count = 0
            for filepath in glob.glob( f'{NORMAL_DESTINATION_FOLDER}/*.css' ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Copying {filepath}…" )
                # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
                shutil.copy2( filepath, DESTINATION_FOLDER )
                count += 1
                shutil.copy2( f'{NORMAL_DESTINATION_FOLDER}/Bible.js', DESTINATION_FOLDER )
                count += 1
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copied {count:,} stylesheets and scripts into {DESTINATION_FOLDER}/." )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f'''\nNOW RUN "npx pagefind --glob "{{OET,par,ref}}/**/*.{{htm}}" --site ../htmlPages{'/Test' if TEST_MODE else ''}/" to create search index!''' )
    else:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"NOT UPDATING the actual {'TEST ' if TEST_MODE else ''}site (as requested)." )
# end of createSitePages.createSitePages


def cleanHTMLFolders( folder:Path, state ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"cleanHTMLFolders( {folder} )")
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Cleaning away any existing folders at {folder}/…")

    try: os.unlink( folder.joinpath( 'index.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'allDetails.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'about.htm' ) )
    except FileNotFoundError: pass
    try: os.unlink( folder.joinpath( 'search.htm' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'par/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'il/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'ref/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'dct/' ) )
    except FileNotFoundError: pass
    for versionAbbreviation in state.allBibleVersions + ['UTN','TOSN','TOBD']:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Removing tree at {folder.joinpath( f'{versionAbbreviation}/' )}/…")
        try: shutil.rmtree( folder.joinpath( f'{versionAbbreviation}/' ) )
        except FileNotFoundError: pass
    return True
# end of createSitePages.cleanHTMLFolders


def createOETVersionPages( level:int, folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETVersionPages( {level}, {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    createOETBookPages( level+1, folder.joinpath('byDoc/'), rvBible, lvBible, state )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    createOETSideBySideChapterPages( level+1, folder.joinpath('byC/'), rvBible, lvBible, state )

    versionName = state.BibleNames['OET']
    indexHtml = f'''<h1 id="Top">{versionName}</h1>
<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but mostly recommend the byDocument mode for personal reading.</p>
<p class="viewLst">OET <a href="byDoc">By Document</a> <a href="bySec">By Section</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
''' if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings'] else \
f'''<h1 id="Top">{versionName}</h1>
<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but mostly recommend the byDocument mode for personal reading.</p>
<p class="viewLst">OET <a href="byDoc">By Document</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                    .replace( '__KEYWORDS__', f'Bible, OET, {versionName}' ) \
                    .replace( f'''<a title="{versionName}" href="{'../'*level}OET">OET</a>''', 'OET' )
    filepath = folder.joinpath( 'index.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{indexHtml}
{makeBottom( level, 'site', state )}''' )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages.createOETVersionPages

def createVersionPages( level:int, folder:Path, thisBible, state:State ) -> bool:
    """
    Create a page for the given Bible version
        that then allows the user to choose by document/section/chapter or display version details
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVersionPages( {level}, {folder}, {thisBible.abbreviation} )")
    createBookPages( level+1, folder.joinpath('byDoc/'), thisBible, state )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    createChapterPages( level+1, folder.joinpath('byC/'), thisBible, state )

    versionName = state.BibleNames[thisBible.abbreviation]
    indexHtml = f'''<h1 id="Top">{versionName}</h1>
<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but mostly recommend the byDocument mode for personal reading.</p>
<p class="viewLst">{thisBible.abbreviation} <a href="byDoc">By Document</a> <a href="bySec">By Section</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
''' if thisBible.discoveryResults['ALL']['haveSectionHeadings'] else \
f'''<h1 id="Top">{versionName}</h1>
<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but mostly recommend the byDocument mode for personal reading.</p>
<p class="viewLst">{thisBible.abbreviation} <a href="byDoc">By Document</a> <a href="byC">By Chapter</a> <a href="details.htm#Top">Details</a></p>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName}" ) \
                    .replace( '__KEYWORDS__', f'Bible, {versionName}' ) \
                    .replace( f'''<a title="{versionName}" href="{'../'*level}{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation )
    filepath = folder.joinpath( 'index.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{indexHtml}{makeBottom( level, 'site', state )}''' )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages.createVersionPages


def createOETMissingVersePage( level:int, buildFolder:Path ) -> bool:
    """
    """
    textHtml = '''<h1>OET Missing Verse page</h1>
<p class="missingVerses">The <em>Open English Translation Readers’ Version</em> uses the <b>≈</b> symbol
to indicate places where we intentionally did not include the translation of an entire verse.
This is not because we’re trying to trying to hide anything that was in the original scriptures,
but rather it’s because the majority of scholars believe that the verse was added later by a scribe
and most likely was not written by the original author of the book or letter.</p>
<p class="missingVerses">It’s clear that the oldest copies of the manuscripts that we have, are not the originals which were first dictated by their authors,
but rather they’re copies made over the next few centuries.
Often, the copyists wanted to fix errors which they believed earlier copyists may have made,
or add additional information that they thought would help the reader.
And then of course, some of them introduced accidental errors of their own,
especially in the New Testament era where scribes often were not professionals.</p>
<p class="missingVerses"><small>Note: The back button should return you to your previous page.</small></p>
<p class="missingVerses">Here is a list of the verses that we didn’t include:</p>
<ul>
<li><a href="byC/MRK_C15.htm#V28">Mark 15:28</a>: and the scripture was fulfilled which says, He was counted as one of the lawless ones. (<a href="byC/ISA_C53.htm#V12">Isa 53:12</a>)</li>
<li>More to come…</li>
</ul>
'''
    top = makeTop( level, None, 'site', None, state ) \
                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OET Missing Verses" ) \
                    .replace( '__KEYWORDS__', 'Bible, OET, missing, verses' ) \
                    .replace( f'''<a title="OET" href="{'../'*level}OET">OET</a>''', 'OET' )
    filepath = buildFolder.joinpath( 'missingVerse.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( f'''{top}{textHtml}{makeBottom( level, 'site', state )}''' )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    {len(textHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages.createOETMissingVersePage


def createDetailsPages( level:int, buildFolder:Path, state ) -> bool:
    """
    Creates and saves details (copyright, licence, etc.) pages for each version
        plus a summary page of all the versions.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createDetailsPages( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}details pages for {len(state.BibleVersions)} versions…" )

    allDetailsHTML = ''
    for versionAbbreviation in ['OET'] + [versAbbrev for versAbbrev in state.preloadedBibles]:
        if versionAbbreviation == 'TTN': # we only need the one for TOSN I think
            versionAbbreviation = 'TOBD' # Put this one in instead

        versionName =  state.BibleNames[versionAbbreviation]

        if 'OET' not in versionAbbreviation and versionAbbreviation not in ('TOBD',): # (These don't have a BibleLocation)
            if 'eBible' in state.BibleLocations[versionAbbreviation]:
                # This code scrapes info from eBible.org copr.htm files, and hence is very fragile (susceptible to upstream changes)
                with open( os.path.join(state.BibleLocations[versionAbbreviation], 'copr.htm'), 'rt', encoding='utf-8' ) as coprFile:
                        fullCoprText = coprFile.read()
                ixStart = fullCoprText.index( '''<p align="center"><a href='copyright.htm'>''' ) + 42
                ixEnd = fullCoprText.index( '</a>', ixStart )
                actualCoprText = fullCoprText[ixStart:ixEnd]
                # print( f"  {ixStart=} {ixEnd=} '{actualCoprText}'")
                state.detailsHtml[versionAbbreviation]['copyright'] = \
                        state.detailsHtml[versionAbbreviation]['copyright'].replace( '(coming)', actualCoprText ) \
                                .replace( '© ©', '©' ).replace( 'Copyright © Public Domain', 'Public Domain' )
                if 'Public Domain' in actualCoprText:
                        state.detailsHtml[versionAbbreviation]['licence'] = \
                        state.detailsHtml[versionAbbreviation]['licence'].replace( '(coming)', 'Public Domain' )
                elif 'creativecommons.org/licenses/by-sa/4.0' in actualCoprText:
                        state.detailsHtml[versionAbbreviation]['licence'] = \
                        state.detailsHtml[versionAbbreviation]['licence'].replace( '(coming)', '<a href="https://CreativeCommons.org/licenses/by-sa/4.0/">Creative Commons Attribution Share-Alike license 4.0</a>' )
                else: dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Unrecognised eBible {versionAbbreviation} copyright: '{actualCoprText}'")
                state.detailsHtml[versionAbbreviation]['acknowledgements'] = \
                        state.detailsHtml[versionAbbreviation]['acknowledgements'].replace( '(coming)',
                            'Thanks to <a href="https://eBible.org/Scriptures/">eBible.org</a> for supplying the USFM files' )
            elif '/TXT/' in state.BibleLocations[versionAbbreviation]:
                state.detailsHtml[versionAbbreviation]['acknowledgements'] = \
                        state.detailsHtml[versionAbbreviation]['acknowledgements'].replace( '(coming)',
                            'Thanks to <a href="https://www.BibleSuperSearch.com/bible-downloads/">BibleSuperSearch.com</a> for supplying the source file' )

        topHtml = makeTop( level+1, versionAbbreviation, 'details', 'details.htm', state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{versionName} Details" ) \
                .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' ) \
                .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.htm#Top">{versionAbbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )

        extraHTML = '''<h2>Key to Abbreviations</h2>
<p class="note">See key and more information <a href="byDoc/FRT.htm#Top">here</a>.</p>
''' if versionAbbreviation == 'T4T' else ''

        detailsHtml = f'''{extraHTML}<h2>About the {versionAbbreviation}</h2>{state.detailsHtml[versionAbbreviation]['about']}
<h2>Copyright</h2>{state.detailsHtml[versionAbbreviation]['copyright']}
<h2>Licence</h2>{state.detailsHtml[versionAbbreviation]['licence']}
<h2>Acknowledgements</h2>{state.detailsHtml[versionAbbreviation]['acknowledgements']}
'''
        if TEST_MODE and versionAbbreviation in state.selectedVersesOnlyVersions:
            # Add a list of links to verses containing this version
            selectedVerseLinksList = [f'<a href="../par/{BBB}/C{C}V{V}.htm#Top">{tidyBBB( BBB, titleCase=True )} {C}:{V}</a>' for BBB,C,V in state.preloadedBibles[versionAbbreviation]]
        #     for BBB,C,V in state.preloadedBibles[versionAbbreviation]:
        #         ourTidyBBB = tidyBBB( BBB, titleCase=True )
        #         selectedVerseLinksList.append( f'<a href="../par/{BBB}/C{C}V{V}.htm#Top">{tidyBBB( BBB, titleCase=True )} {C}:{V}</a>' )
            detailsHtml = f'''{detailsHtml}<h2>Available selections</h2>
<p class="rem">The following parallel verse pages feature this version:</p>
<p class="selectedLinks">{' '.join(selectedVerseLinksList)}</p>
'''

        bodyHtml = f'''<!--createDetailsPages--><h1 id="Top">{versionName} Details</h1>
{detailsHtml}<hr>
<p class="note">See details for ALL included versions <a title="All versions’ details" href="../allDetails.htm#Top">here</a>.</p>
'''

        allDetailsHTML = f'''{allDetailsHTML}{'<hr>' if allDetailsHTML else ''}<h2 id="{versionAbbreviation}">{versionName}</h2>
{detailsHtml.replace('h2','h3')}'''

        html = f"{topHtml}{bodyHtml}{makeBottom( level+1, 'details', state )}"
        checkHtml( f'{versionAbbreviation} details', html )

        versionFolder = buildFolder.joinpath( f'{versionAbbreviation}/' )
        try: os.makedirs( versionFolder )
        except FileExistsError: pass # they were already there

        filepath = versionFolder.joinpath( 'details.htm' )
        with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
            htmlFile.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

    # Make a summary page with details for all versions
    topHtml = makeTop( level, None, 'allDetails', 'details.htm', state ) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}All Versions Details" ) \
            .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' )
            # .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.htm#Top">{versionAbbreviation}</a>''',
            #             f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )
    html = f'''{topHtml}<h1 id="Top">Details for all versions</h1>
<p class="note">If you’re the copyright owner of a Bible translation and would like to see it listed on this site,
  please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
{allDetailsHTML}{makeBottom( level, 'allDetails', state )}'''
    checkHtml( 'AllDetails', html )

    filepath = buildFolder.joinpath( 'allDetails.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages.createDetailsPages


def createSearchPage( level:int, buildFolder:Path, state ) -> bool:
    """
    Creates and saves the OBD search page.

    We use https://pagefind.app/
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createSearchPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}search page…" )

    searchHTML = f'''<h1 id="Top">Search Open Bible Data</h1>
<p class="note">Searching should find English and Latin words, plus Hebrew and Greek words and their English transliterations.</p>
{('<p class="note">Note that only limited Bible books are indexed on these TEST pages.</p>'+NEWLINE) if TEST_MODE else ''}<div id="search"></div>
<script>
    window.addEventListener('DOMContentLoaded', (event) => {{
        new PagefindUI({{ element: "#search", showSubResults: false }});
    }});
</script>
'''
    topHtml = makeTop( level, None, 'search', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Search OBD" ) \
                .replace( '__KEYWORDS__', 'Bible, search, OBD' ) \
                .replace( '</head>', '''  <link rel="stylesheet" href="pagefind/pagefind-ui.css">
  <script src="pagefind/pagefind-ui.js"></script>
</head>''')
    html = f'''{topHtml}{searchHTML}<p class="note">Search functionality is provided thanks to <a href="https://Pagefind.app/">Pagefind</a>.</p>
<p class="note"><small>OBD pages last rebuilt: {date.today()}</small></p>{makeBottom( level, 'search', state )}'''
    checkHtml( 'Search', html )

    filepath = buildFolder.joinpath( 'search.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages.createSearchPage


def createAboutPage( level:int, buildFolder:Path, state ) -> bool:
    """
    Creates and saves the About OBD page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createAboutPage( {level}, {buildFolder}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating {'TEST ' if TEST_MODE else ''}about page…" )

    aboutHTML = '''<h1 id="Top">About Open Bible Data</h1>
<p class="about">Open Bible Data (OBD) is a large set of static webpages created for several main reasons:</p>
<ol>
<li>As a way to <b>showcase the <em>Open English Translation</em></b> of the Bible which is designed to be read with the <em>Readers’ Version</em> and the very <em>Literal Version</em> side-by-side.
    (Most existing Bible apps don’t allow for this.)
    Also, the <em>OET</em> renames some Bible ‘books’ and places them into a different order,
        and even modernises terminology like ‘Old Testament’ and ‘New Testament’
            with ‘The Hebrew Scriptures’ and ‘The Messianic Update’.</li>
<li>To <b>showcase how <em>OET-RV</em> section headings are formatted</b> so as not to break the flow of the text.
    Section headings are available as a help to the reader, but were not in the original manuscripts,
        and the original flow of the text was not designed to be arbitrarily divided into sections.</li>
<li>To <b>promote other open-licenced Bible translations</b>, including those developed as resources for Bible translators themselves. We believe that God’s Message should be freely available to all.</li>
<li>As a way to <b>showcase open-licenced Bible datasets</b>.
    Hence every word in the <em>OET-LV</em> is linked to the Greek word that they are translated from.
    In addition, most pronouns like ‘he’ or ‘she’ are linked to the earlier referrents in the text.</li>
<li>For the <b>comparison and evaluation of the history and quality and distinctives of various Bible translations</b>.
    So on the parallel verse pages, you can track Biblical wording right from the Biblical Hebrew or Greek (near the bottom of the page),
        up through the Latin and then Wycliffe's and Tyndale's early English translations,
        then right up through more modern translations all the way up to the OET at the top.</li>
<li>We try to <b>downplay chapter and verse divisions</b>, and encourage readers to read narratives as narratives and letters as letters—would
        you take a letter or email from your mother, draw lines through it to divide it into random sections/chapters,
        and then read different sections on different days?</li>
</ol>
<p class="about">You might especially note the following features:</p>
<ul>
<li>Our <b>Parallel view</b> shows individual <em>OET</em> verses at the top,
        but if you're interested in English Bible translation history,
        go to the bottom of the page (and then scroll up through any Study Notes) until you find the original language (Hebrew or Greek) versions.
    Then work your way upwards, through the Latin to the Wycliffe and Tyndale translations,
        and then other early English translations until you see that English spelling becomes standardised by the 1769 KJB.
    As you work upwards in chronological order, it's fascinating to see two things:
    <ol>
    <li>how spelling in early English books was phonetic (sounding out the words) and quite variable
            <small>(and so we try to help you with a conversion to modern English in parentheses)</small>, and</li>
    <li>how translators often reused phrases from earlier English translations, but sometimes chose to disagree.</li>
    </ol></li>
<li>Our <b>Interlinear view</b> shows word-for-word interlinear and reverse-interlinear views.</li>
<li>Our <b>Search page</b> allows you to search for English, Latin, Hebrew, and Greek words.</li>
</ul>
<p class="about">We would welcome any others who would like to contribute open datasets or code to this endeavour.
    Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
<p class="about"><b>Acknowledgement</b>: The overall design of the site was influenced by <a href="https://BibleHub.com/">BibleHub.com</a>
        and their <a href="https://OpenBible.com/">OpenBible.com</a> which have many features that we like
        (and likely many overlapping goals).</p>
<h3>Technical details</h3>
<p class="about">These pages are created by a Python program that takes the open-licenced resources and combines them in different ways on different pages.
    The program is still being developed, and hence this site (or this part of the site), is still at the prototype stage,
        especially with respect to navigation around the pages which is still being improved.</p>
<p class="about">If you are the copyright owner of a Bible translation and would like to see it listed on this site,
        please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b>.</p>
<p class="about">The source code for the Python program can be found at <a href="https://github.com/Freely-Given-org/OpenBibleData">GitHub.com/Freely-Given-org/OpenBibleData</a>.
    You can also advise us of any errors by clicking on <em>New issue</em> <a href="https://github.com/Freely-Given-org/OpenBibleData/issues">here</a> and telling us the problem.</p>
'''
    topHtml = makeTop( level, None, 'about', None, state ) \
                .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}About OBD" ) \
                .replace( '__KEYWORDS__', 'Bible, about, OBD' )
    html = f'''{topHtml}{aboutHTML}<p class="note"><small>Last rebuilt: {date.today()}</small></p>{makeBottom( level, 'about', state )}'''
    checkHtml( 'About', html )

    filepath = buildFolder.joinpath( 'about.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages.createAboutPage


def createMainIndexPage( level, folder:Path, state ) -> bool:
    """
    Creates and saves the main index page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createMainIndexPage( {level}, {folder}, {state.BibleVersions} )" )

    # Create the very top level index file
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating main {'TEST ' if TEST_MODE else ''}index page for {len(state.BibleVersions)} versions…" )
    html = makeTop( level, None, 'topIndex', None, state ) \
            .replace( '__TITLE__', 'TEST Open Bible Data Home' if TEST_MODE else 'Open Bible Data Home') \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    if TEST_MODE:
        html = html.replace( '<body>', '<body><p class="note"><a href="../">UP TO MAIN NON-TEST SITE</a></p>')
    bodyHtml = """<!--createMainIndexPage--><h1 id="Top">Open Bible Data Home TEST</h1>
""" if TEST_MODE else """<!--createMainIndexPage--><h1 id="Top">Open Bible Data Home</h1>
"""
    html = f'''{html}{bodyHtml}
<p class="note">Welcome to this <em>Open Bible Data</em> site created to share God’s fantastic message with everyone,
    and with a special interest in helping Bible translators around the world.</p>
<p class="note">Choose a version above to view <b>by document</b> or <b>by section</b> or <b>chapter</b>, or else the <b>parallel</b> or <b>interlinear verse</b> views.</p>
<p class="note">The <b>Dictionary</b> link takes you to the <i>Tyndale Bible Dictionary</i>, and the <b>Search</b> link allows you to find words within the Bible text.</p>
<p class="note"><small>Last rebuilt: {date.today()}</small></p>
{makeBottom( level, 'topIndex', state )}'''
    checkHtml( 'TopIndex', html )

    filepath = folder.joinpath( 'index.htm' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

#     # Create the versions index file (in case it's needed)
#     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Creating versions {'TEST ' if TEST_MODE else ''}index page for {len(state.BibleVersions)} versions…" )
#     html = makeTop( level+1, None, 'topIndex', None, state ) \
#             .replace( '__TITLE__', 'TEST Open Bible Data Versions' if TEST_MODE else 'Open Bible Data Versions') \
#             .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
#     if TEST_MODE:
#         html = html.replace( '<body>', '<body><p class="index"><a href="{'../'*level}">UP TO MAIN NON-TEST SITE</a></p>')
#     bodyHtml = """<!--createVersionsIndexPage--><h1 id="Top">Open Bible Data TEST Versions</h1>
# """ if TEST_MODE else """<!--createMainIndexPage--><h1 id="Top">Open Bible Data Versions</h1>
# """

#     bodyHtml = f'{bodyHtml}<p class="index">Select one of the above Bible version abbreviations for views of entire documents (‘<i>books</i>’) or sections or chapters, or else select either of the Parallel or Interlinear verse views.</p>\n<ol>\n'
#     for versionAbbreviation in state.BibleVersions:
#         bodyHtml = f'{bodyHtml}<li><b>{versionAbbreviation}</b>: {state.BibleNames[versionAbbreviation]}</li>\n'
#     bodyHtml = f'{bodyHtml}</ol>\n'

#     html += bodyHtml + f'<p class="index"><small>Last rebuilt: {date.today()}</small></p>\n' + makeBottom( level, 'topIndex', state )
#     checkHtml( 'VersionIndex', html )

#     filepath = folder.joinpath( 'index.htm' )
#     with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
#         htmlFile.write( html )
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of createSitePages.createMainIndexPage


def reorderBooksForOETVersions( givenBookList:List[str] ) -> List[str]:
    """
    OET needs to put JHN and MRK before MAT
    """
    dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"reorderBooksForOETVersions( {type(givenBookList)} ({len(givenBookList)}) {givenBookList} )" )


    try: ixJHN = givenBookList.index('JHN')
    except ValueError: return givenBookList # Might not have all books included
    try: ixFirstGospel = givenBookList.index('MAT')
    except ValueError: ixFirstGospel = givenBookList.index('MRK')
    if isinstance( givenBookList, tuple ):
        givenBookList = list( givenBookList )
    if ixFirstGospel<ixJHN:
        # print( f"{ixFirstGospel=} {ixJHN=} {givenBookList}")
        givenBookList.remove( 'JHN' )
        givenBookList.remove( 'MRK' )
        givenBookList.insert( ixFirstGospel, 'MRK' )
        givenBookList.insert( ixFirstGospel, 'JHN' )
        # print( f"Returning ({len(givenBookList)}) {givenBookList}" )
    return givenBookList
# end of createSitePages.reorderBooksForOETVersions

def getFolderSize( start_path='.' ) -> int:
    """
    Adapted from https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size
# end of createSitePages.getFolderSize


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    createSitePages()
# end of createSitePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createSitePages object
    createSitePages()
# end of createSitePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createSitePages.py
