#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createSitePages.py
#
# Module handling OpenBibleData createSitePages functions
#
# Copyright (C) 2023 Robert Hunt
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
Module handling createSitePages functions.

Creates the OpenBibleData site with
        Whole document ("book") pages
        Whole chapter pages
        Parallel verse pages
and more pages to come hopefully.
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
import shutil
import glob
from datetime import date
import logging

import sys
sys.path.append( '../../BibleOrgSys/' )
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

from Bibles import preloadVersions
from createBookPages import createOETBookPages, createBookPages
from createChapterPages import createOETChapterPages, createChapterPages
from createSectionPages import createOETSectionPages, createSectionPages
from createParallelPages import createParallelPages
from createInterlinearPages import createInterlinearPages
from html import makeTop, makeBottom, checkHtml


LAST_MODIFIED_DATE = '2023-03-03' # by RJH
SHORT_PROGRAM_NAME = "createSitePages"
PROGRAM_NAME = "OpenBibleData Create Pages"
PROGRAM_VERSION = '0.31'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False # Adds debugging statements and writes website into Test folder if True
ALL_PRODUCTION_BOOKS = True # Set to False only for a faster test build

TEMP_BUILD_FOLDER = Path( '/tmp/OBDHtmlPages/' )
NORMAL_DESTINATION_FOLDER = Path( '../htmlPages/' )
DEBUG_DESTINATION_FOLDER = NORMAL_DESTINATION_FOLDER.joinpath( 'Test/')
DESTINATION_FOLDER = DEBUG_DESTINATION_FOLDER if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE \
                        else NORMAL_DESTINATION_FOLDER


OET_BOOK_LIST = ['MRK','JHN','ACT', 'EPH','TIT', 'JN3']
OET_BOOK_LIST_WITH_FRT = ['FRT','INT'] + OET_BOOK_LIST
NT_BOOK_LIST_WITH_FRT = ['FRT','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL',
                'TH1','TH2','TI1','TI2','TIT','PHM','HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV']
assert len(NT_BOOK_LIST_WITH_FRT) == 27+1
OT_BOOK_LIST_WITH_FRT = ['FRT','GEN','EXO','LEV','NUM','DEU',
                'JOS','JDG','RUT','SA1','SA2','KI1','KI2','CH1','CH2',
                'EZR','NEH','EST','JOB','PSA','PRO','ECC','SNG','ISA','JER','LAM',
                'EZE','DAN','HOS','JOL','AMO','OBA','JNA', 'MIC','NAH','HAB','ZEP','HAG','ZEC','MAL']
assert len(OT_BOOK_LIST_WITH_FRT) == 39+1

# EM_SPACE = ' '


class State:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    BibleVersions = ['OET','OET-RV','OET-LV', # NOTE: OET is a "pseudo-version" containing both OET-RV and OET-LV side-by-side
                'ULT','UST', 'OEB',
                'BSB','ISV',
                'WEB','NET','LSV','FBV','T4T','LEB','BBE',
                'ASV','YLT','DBY','RV','WBS','KJB','GNV','BB','CB',
                'TNT','WYC','CLV',
                'JPS','DRA','BRN',
                'UHB',
                'SR-GNT','UGNT','SBL-GNT']
    
    BibleVersionDecorations = { 'OET':('<b>','</b>'),'OET-RV':('<b>','</b>'),'OET-LV':('<b>','</b>'),
                'ULT':('',''),'UST':('',''),'OEB':('',''),
                'BSB':('',''),'ISV':('',''),
                'WEB':('',''),'NET':('',''),'LSV':('',''),'FBV':('',''),'T4T':('',''),'LEB':('',''),'BBE':('',''),
                'ASV':('',''),'YLT':('',''),'DBY':('',''),'RV':('',''),
                'WBS':('<small>','</small>'),
                'KJB':('',''),'GNV':('',''),'BB':('',''),'CB':('',''),
                'TNT':('',''),'WYC':('',''),'CLV':('<small>','</small>'),
                'JPS':('<small>','</small>'),'DRA':('<small>','</small>'),'BRN':('<small>','</small>'),
                'UHB':('',''),
                'SR-GNT':('<b>','</b>'),'UGNT':('<small>','</small>'),'SBL-GNT':('<small>','</small>'),
                'Parallel':('<b>','</b>'), 'Interlinear':('<small>','</small>'),
                }
    
                ## 'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.osis.xml', # OSIS
                ## 'WYC': '../copiedBibles/English/eBible.org/Wycliffe/',
    BibleLocations = {
                'OET-RV': '../../OpenEnglishTranslation--OET/translatedTexts/ReadersVersion/',
                'OET-LV': '../../OpenEnglishTranslation--OET/intermediateTexts/auto_edited_VLT_USFM/', # No OT here yet
                # NOTE: The program will still run if some of these below are commented out or removed
                # (e.g., this can be done quickly for a faster test)
                'ULT': '../copiedBibles/English/unfoldingWord.org/ULT/',
                'UST': '../copiedBibles/English/unfoldingWord.org/UST/',
                'OEB': '../copiedBibles/English/OEB/',
                'BSB': '../copiedBibles/English/Berean.Bible/BSB/',
                #'ISV': '',
                'WEB': '../copiedBibles/English/eBible.org/WEB/',
                'NET': '../copiedBibles/English/eBible.org/NET/',
                'LSV': '../copiedBibles/English/eBible.org/LSV/',
                'FBV': '../copiedBibles/English/eBible.org/FBV/',
                'T4T': '../copiedBibles/English/eBible.org/T4T/',
                'LEB': '../copiedBibles/English/LogosBibleSoftware/LEB/LEB.xml', # not OSIS
                'BBE': '../copiedBibles/English/eBible.org/BBE/',
                'ASV': '../copiedBibles/English/eBible.org/ASV/',
                'YLT': '../copiedBibles/English/eBible.org/YLT/',
                'DBY': '../copiedBibles/English/eBible.org/DBY/',
                'RV': '../copiedBibles/English/eBible.org/RV/', # with deuterocanon
                'WBS': '../copiedBibles/English/eBible.org/RV/',
                'KJB': '../copiedBibles/English/eBible.org/KJB/', # with deuterocanon
                'GNV': '../copiedBibles/English/eBible.org/GNV/',
                'BB': '/mnt/SSDs/Bibles/DataSets/BibleSuperSearch.com/v5.0/TXT/bishops.txt',
                'CB': '/mnt/SSDs/Bibles/DataSets/BibleSuperSearch.com/v5.0/TXT/coverdale.txt',
                'TNT': '../copiedBibles/English/eBible.org/TNT/',
                'WYC': '/mnt/SSDs/Bibles/Zefania modules/SF_2009-01-20_ENG_BIBLE_WYCLIFFE_(JOHN WYCLIFFE BIBLE).xml',
                'CLV': '../copiedBibles/Latin/eBible.org/CLV/',
                'JPS': '../copiedBibles/English/eBible.org/JPS/',
                'DRA': '../copiedBibles/English/eBible.org/DRA/',
                'BRN': '../copiedBibles/English/eBible.org/Brenton/', # with deuterocanon and OTH,XXA,XXB,XXC,
                'UHB': '../copiedBibles/Original/unfoldingWord.org/UHB/',
                'SR-GNT': '../../Forked/CNTR-SR/SR usfm/',
                'UGNT': '../copiedBibles/Original/unfoldingWord.org/UGNT/',
                'SBL-GNT': '../../Forked/SBLGNT/data/sblgnt/text/',
                }
    
    BibleNames = {
                'OET': 'Open English Translation (2027)',
                'OET-RV': 'Open English Translation—Readers’ Version (2027)',
                'OET-LV': 'Open English Translation—Literal Version (2025)',
                'ULT': 'unfoldingWord Literal Text (2023)',
                'UST': 'unfoldingWord Simplified Text (2023)',
                'OEB': 'Open English Bible (in progress)',
                'BSB': 'Berean Study/Standard Bible (2020)',
                'ISV': 'International Standard Version (2020?)',
                'WEB': 'World English Bible (2020)',
                'NET': 'New English Translation (2016)',
                'LSV': 'Literal Standard Version (2020)',
                'FBV': 'Free Bible Version (2018)',
                'T4T': 'Translation for Translators (2017)',
                'LEB': 'Lexham English Bible (2010,2012)',
                'BBE': 'Bible in Basic English (1965)',
                'ASV': 'American Standard Version (1901)',
                'YLT': 'Youngs Literal Translation (1898)',
                'DBY': 'Darby Translation (1890)',
                'RV': 'Revised Version (1885)',
                'WBS': 'Webster Bible (American, 1833)',
                'KJB': 'King James Bible (1611-1769)',
                'GNV': 'Geneva Bible (1557-1560,1599)',
                'BB': 'Bishops Bible (1568,1602)',
                'GB': 'Great Bible (1539)', # Not in OBD yet
                'CB': 'Coverdale Bible (1535-1553)',
                'TNT': 'Tyndale New Testament (1526)',
                'WYC': 'Wycliffe Bible (1382)',
                'CLV': 'Clementine Vulgate (Latin, 1592)',
                'JPS': 'Jewish Publication Society TaNaKH (1917)',
                'DRA': 'Douay-Rheims American Edition (1899)',
                'BRN': 'Brenton Septuagint Translation (1851)',
                'UHB': 'unfoldingWord Hebrew Bible (2022)',
                'SR-GNT': 'Statistical Restoration Greek New Testament (2022)',
                'UGNT': 'unfoldingWord Greek New Testament (2022)',
                'SBL-GNT': 'Society for Biblical Literature Greek New Testament (2020???)',
                }
    
    booksToLoad = {
                'OET': OET_BOOK_LIST_WITH_FRT,
                'OET-RV': OET_BOOK_LIST_WITH_FRT,
                'OET-LV': OET_BOOK_LIST,
                'ULT': ['ALL'],
                'UST': ['ALL'], # MRK 13:13 gives \add error (24Jan2023)
                'OEB': ['ALL'],
                'BSB': ['ALL'],
                'ISV': ['ALL'],
                'WEB': ['ALL'],
                'NET': ['ALL'],
                'LSV': ['ALL'],
                'FBV': ['ALL'],
                'T4T': ['ALL'],
                'LEB': ['ALL'],
                'BBE': ['ALL'],
                'ASV': ['ALL'],
                'YLT': ['ALL'],
                'DBY': ['ALL'],
                'RV': ['ALL'],
                'WBS': ['ALL'],
                'KJB': ['ALL'],
                'GNV': ['ALL'],
                'BB': ['ALL'],
                'CB': ['ALL'],
                'TNT': ['ALL'],
                'WYC': ['ALL'],
                'CLV': ['ALL'],
                'JPS': ['ALL'],
                'DRA': ['ALL'],
                'BRN': ['ALL'],
                'UHB': ['ALL'],
                'SR-GNT': ['ALL'],
                'UGNT': ['ALL'],
                'SBL-GNT': ['ALL'],
            } if ALL_PRODUCTION_BOOKS else {
                'OET': ['FRT','MRK'],
                'OET-RV': ['FRT','MRK'],
                'OET-LV': ['MRK'],
                'ULT': ['FRT','MRK'],
                'UST': ['MRK'], # MRK 13:13 gives \add error (24Jan2023)
                'OEB': ['MRK'],
                'BSB': ['MRK'],
                'ISV': ['MRK'],
                'WEB': ['MRK'],
                'NET': ['MRK'],
                'LSV': ['MRK'],
                'FBV': ['MRK'],
                'T4T': ['MRK'],
                'LEB': ['MRK'],
                'BBE': ['MRK'],
                'ASV': ['MRK'],
                'YLT': ['MRK'],
                'DBY': ['MRK'],
                'RV': ['MRK'],
                'WBS': ['MRK'],
                'KJB': ['MRK'],
                'GNV': ['MRK'],
                'BB': ['MRK'],
                'CB': ['MRK'],
                'TNT': ['MRK'],
                'WYC': ['MRK'],
                'CLV': ['MRK'],
                'JPS': ['RUT'],
                'DRA': ['MRK'],
                'BRN': ['RUT'],
                'UHB': ['RUT'],
                'SR-GNT': ['MRK'],
                'UGNT': ['MRK'],
                'SBL-GNT': ['MRK'],
            }

    detailsHtml = {
        'OET': {'about': '<p>The (still unfinished) <em>Open English Translation</em> consists of a <em>Readers’ Version</em> and a <em>Literal Version</em> side by side.</p>',
                'copyright': '<p>Copyright © 2010-2023 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</p>' },
        'OET-RV': {'about': '<p>The (still unfinished) <em>Open English Translation Readers’ Version</em> is a new, modern-English easy-to-read translation of the Bible.</p>',
                'copyright': '<p>Copyright © 2010-2023 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</p>' },
        'OET-LV': {'about': '<p>The (still unfinished) <em>Open English Translation Literal Version</em> is a tool designed to give a look into what was actually written in the original Hebrew or Greek manuscripts.</p>',
                'copyright': '<p>Copyright © 2010-2023 <a href="https://Freely-Given.org">Freely-Given.org</a>.</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>Thanks to <a href="https://Freely-Given.org/">Freely-Given.org</a> for creating this exciting, new Bible translation which is viewable from <a href="https://OpenEnglishTranslation.Bible">OpenEnglishTranslation.Bible</a>.</p>' },
        'ULT': {'about': '<p>unfoldingWord Literal Text (2023).</p>',
                'copyright': '<p>Copyright © 2022 by unfoldingWord.</p>',
                'licence': '<p><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'UST': {'about': '<p>unfoldingWord Simplified Text (2023).</p>',
                'copyright': '<p>Copyright © 2022 by unfoldingWord.</p>',
                'licence': '<p><a href="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'OEB': {'about': '<p>Open English Bible (in progress).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'BSB': {'about': '<p>Berean Study/Standard Bible (2020).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'ISV': {'about': '<p>International Standard Version (2020?).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'WEB': {'about': '<p>World English Bible (2020).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'NET': {'about': '<p>New English Translation (2016).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'LSV': {'about': '<p>Literal Standard Version (2020).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'FBV': {'about': '<p>Free Bible Version (2018).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'T4T': {'about': '<p>Translation for Translators (2017).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'LEB': {'about': '<p>Lexham English Bible (2010,2012).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>You can give away the Lexham English Bible, but you can’t sell it on its own. If the LEB comprises less than 25% of the content of a larger work, you can sell it as part of that work.</p>',
                'acknowledgements': '<p>Thanks to Logos Bible Software for supplying a XML file.</p>' },
        'BBE': {'about': '<p>Bible in Basic English (1965).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'ASV': {'about': '<p>American Standard Version (1901).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'YLT': {'about': '<p>Youngs Literal Translation (1898).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'DBY': {'about': '<p>Darby Translation (1890).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'RV': {'about': '<p>Revised Version (1885).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'WBS': {'about': '<p>Webster Bible (1833).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'KJB': {'about': '<p>King James Bible (1611-1769).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'GNV': {'about': '<p>Geneva Bible (1557-1560,1599).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'BB': {'about': '<p>Bishops Bible (1568,1602).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>Public Domain.</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'CB': {'about': '<p><a href="https://en.wikipedia.org/wiki/Coverdale_Bible">Coverdale Bible</a> (1535-1553).</p>',
                'copyright': '<p>Copyright © Miles Coverdale.</p>',
                'licence': '<p>Public Domain.</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'TNT': {'about': '<p>Tyndale New Testament (1526).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'WYC': {'about': '<p><a href="https://en.wikipedia.org/wiki/Wycliffe%27s_Bible">Wycliffe Bible</a> (1382).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'CLV': {'about': '<p><a href="https://en.wikipedia.org/wiki/Sixto-Clementine_Vulgate">Clementine Vulgate Bible</a> (Latin, 1592).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'JPS': {'about': '<p>Jewish Publication Society TaNaKH (1917).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'DRA': {'about': '<p>Douay-Rheims American Edition (1899).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'BRN': {'about': '<p>Brenton Septuagint Translation (1851).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'UHB': {'about': '<p>unfoldingWord Hebrew Bible (2022).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'SR-GNT': {'about': '<p>Statistical Restoration Greek New Testament (2022).</p>',
                'copyright': '<p>Copyright © 2022 by Alan Bunning.</p>',
                'licence': '<p><a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.</p>',
                'acknowledgements': '<p>Grateful thanks to Dr. Alan Bunning who founded the <a href="https://greekcntr.org">Center for New Testament Restoration</a> and gave around twenty years of his free time (plus a few full-time years at the end) to make this new, high-quality Greek New Testament freely available.</p>' },
        'UGNT': {'about': '<p>unfoldingWord Greek New Testament (2022).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
        'SBL-GNT': {'about': '<p>Society for Biblical Literature Greek New Testament (2020???).</p>',
                'copyright': '<p>Copyright © (coming).</p>',
                'licence': '<p>(coming).</p>',
                'acknowledgements': '<p>(coming).</p>' },
    }

    assert len(BibleVersionDecorations) == len(BibleVersions)+2, f"{len(BibleVersionDecorations)=} {len(BibleVersions)=}" # Adds Parallel and Interlinear
    assert len(BibleVersions)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(BibleNames)-1 >= len(BibleLocations) # OET is a pseudo-version
    assert len(booksToLoad)-1 >= len(BibleLocations) # OET is a pseudo-version
    preloadedBibles = {}
# end of State class

state = State()


def createSitePages() -> bool:
    """
    Build all the pages in a temporary location
    """
    fnPrint( DEBUGGING_THIS_MODULE, "createSitePages()")

    # Preload our various Bibles
    numLoadedVersions = preloadVersions( state )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nPreloaded {len(state.preloadedBibles)} Bible versions: {state.preloadedBibles.keys()}" )

    try: os.makedirs( TEMP_BUILD_FOLDER )
    except FileExistsError: pass # they were already there
    cleanHTMLFolders( TEMP_BUILD_FOLDER )

    versionsFolder = TEMP_BUILD_FOLDER.joinpath( 'versions/' )
    try: os.makedirs( versionsFolder )
    except FileExistsError: pass # they were already there

    # Ok, let's go create some static pages
    if 'OET' in state.BibleVersions: # this is a special case
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating version pages for OET…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/OET/' )
        createOETVersionPages( versionFolder, state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV'], state )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating version pages for {thisBible.abbreviation}…" )
        versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/{thisBible.abbreviation}/' )
        createVersionPages( versionFolder, thisBible, state )

    # Find our inclusive list of books
    allBBBs = set()
    for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
        for versionAbbreviation in state.BibleVersions:
            if versionAbbreviation == 'OET': continue # OET is a pseudo version (OET-RV plus OET-LV)
            for entry in state.booksToLoad[versionAbbreviation]:
                if entry == BBB or entry == 'ALL':
                    if BBB in state.preloadedBibles[versionAbbreviation]:
                        allBBBs.add( BBB )
    # Now put them in the proper print order
    state.allBBBs = BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( allBBBs )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nDiscovered {len(state.allBBBs)} books across {len(state.preloadedBibles)} versions: {state.allBBBs}" )

    # We do this later than the createVersionPages above
    #   because we need all versions to have all books loaded and 'discovered', i.e., analysed
    #   so we know in advance which versions have section headings
    if 'OET' in state.BibleVersions: # this is a special case
        rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']
        if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings']:
            versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/OET/' )
            createOETSectionPages( versionFolder.joinpath('bySection/'), rvBible, lvBible, state )
    for versionAbbreviation, thisBible in state.preloadedBibles.items(): # doesn't include OET pseudo-translation
        if thisBible.discoveryResults['ALL']['haveSectionHeadings']:
            versionFolder = TEMP_BUILD_FOLDER.joinpath( f'versions/{thisBible.abbreviation}/' )
            createSectionPages( versionFolder.joinpath('bySection/'), thisBible, state )

    createParallelPages( TEMP_BUILD_FOLDER.joinpath('parallel/'), state )
    createInterlinearPages( TEMP_BUILD_FOLDER.joinpath('interlinear/'), state )

    createDetailsPages( 1, versionsFolder, state )

    createMainIndexPages( 0, TEMP_BUILD_FOLDER, state )

    # Now move the site from our temporary build location to overwrite the destination location
    try: os.makedirs( DESTINATION_FOLDER )
    except FileExistsError: # they were already there
        cleanHTMLFolders( DESTINATION_FOLDER )
    count = 0
    for fileOrFolderPath in glob.glob( f'{TEMP_BUILD_FOLDER}/*' ):
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Moving {fileOrFolderPath} to {DESTINATION_FOLDER}…" )
        # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
        shutil.move( fileOrFolderPath, DESTINATION_FOLDER, copy_function=shutil.copy2)
        count += 1
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Moved {count} folders and files into {DESTINATION_FOLDER}." )

    # In DEBUG mode, we need to copy the .css files across
    if DESTINATION_FOLDER != NORMAL_DESTINATION_FOLDER:
        count = 0
        for filepath in glob.glob( f'{NORMAL_DESTINATION_FOLDER}/*.css' ):
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Copying {filepath}…" )
            # Note: shutil.copy2 is the same as copy but keeps metadata like creation and modification times
            shutil.copy2( filepath, DESTINATION_FOLDER )
            count += 1
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Copied {count} stylesheets to {DESTINATION_FOLDER}." )
# end of createSitePages.createSitePages


def cleanHTMLFolders( folder:Path ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"cleanHTMLFolders( {folder} )")
    try: os.unlink( folder.joinpath( 'index.html' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'versions/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'parallel/' ) )
    except FileNotFoundError: pass
    try: shutil.rmtree( folder.joinpath( 'interlinear/' ) )
    except FileNotFoundError: pass
    return True
# end of createSitePages.cleanHTMLFolders


def createOETVersionPages( folder:Path, rvBible, lvBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETVersionPages( {folder}, {rvBible.abbreviation}, {lvBible.abbreviation} )")
    createOETBookPages( folder.joinpath('byDocument/'), rvBible, lvBible, state )
    createOETChapterPages( folder.joinpath('byChapter/'), rvBible, lvBible, state )
    rvBible.discover() # Now that all required books are loaded
    lvBible.discover() #     ..ditto..
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvBible.discoveryResults['ALL']['haveSectionHeadings']=}" )

    indexHtml = f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a> <a href="bySection">By Section</a> <a href="byChapter">By Chapter</a> <a href="details.html">Details</a></p>
''' if rvBible.discoveryResults['ALL']['haveSectionHeadings'] or lvBible.discoveryResults['ALL']['haveSectionHeadings'] else f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a> <a href="byChapter">By Chapter</a> <a href="details.html">Details</a></p>
'''
    versionName = state.BibleNames['OET']
    filepath = folder.joinpath( 'index.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( makeTop( 2, 'site', None, state ) \
                                    .replace( '__TITLE__', f"{versionName}" ) \
                                    .replace( '__KEYWORDS__', f"Bible, OET, {versionName}" ) \
                                    .replace( f'''<a title="{versionName}" href="{'../'*2}versions/OET">OET</a>''', 'OET' ) \
                                + indexHtml + '\n' + makeBottom( 1, 'site', state ) )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages.createOETVersionPages

def createVersionPages( folder:Path, thisBible, state:State ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createVersionPages( {folder}, {thisBible.abbreviation} )")
    createBookPages( folder.joinpath('byDocument/'), thisBible, state )
    createChapterPages( folder.joinpath('byChapter/'), thisBible, state )
    thisBible.discover() # Now that all required books are loaded
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{thisBible.discoveryResults['ALL']['haveSectionHeadings']=}" )

    indexHtml = f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a> <a href="bySection">By Section</a> <a href="byChapter">By Chapter</a> <a href="details.html">Details</a></p>
''' if thisBible.discoveryResults['ALL']['haveSectionHeadings'] else f'''<p class="rem">Remember that ancient letters were meant to be read in their entirety just like modern letters. We provide a byChapter mode for convenience only, but recommend the byDocument mode for personal reading.</p>
<p class="viewNav"><a href="byDocument">By Document</a> <a href="byChapter">By Chapter</a> <a href="details.html">Details</a></p>
'''
    versionName = state.BibleNames[thisBible.abbreviation]
    filepath = folder.joinpath( 'index.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( makeTop( 2, 'site', None, state ) \
                                    .replace( '__TITLE__', f'{versionName}' ) \
                                    .replace( '__KEYWORDS__', f'Bible, {versionName}' ) \
                                    .replace( f'''<a title="{versionName}" href="{'../'*2}versions/{BibleOrgSysGlobals.makeSafeString(thisBible.abbreviation)}">{thisBible.abbreviation}</a>''', thisBible.abbreviation ) \
                                + indexHtml + makeBottom( 1, 'site', state ) )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {len(indexHtml):,} characters written to {filepath}" )
    return True
# end of createSitePages.createVersionPages


def createMainIndexPages( level, folder:Path, state ) -> bool:
    """
    Creates and saves the main index page
        and the versions index page.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createMainIndexPage( {level}, {folder}, {state.BibleVersions} )" )

    # Create the very top level index file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Creating main {'TEST ' if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else ''}index page for {len(state.BibleVersions)} versions…" )
    html = makeTop( level, 'topIndex', None, state ) \
            .replace( '__TITLE__', 'TEST Open Bible Data' if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else 'Open Bible Data') \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        html = html.replace( '<body>', '<body><p><a href="../">UP TO MAIN NON-TEST SITE</a></p>')
    bodyHtml = """<!--createMainIndexPage--><h1>Open Bible Data TEST</h1>
""" if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else """<!--createMainIndexPage--><h1>Open Bible Data</h1>
"""
    html += bodyHtml + f'<p><small>Last rebuilt: {date.today()}</small></p>\n' + makeBottom( level, 'topIndex', state )
    checkHtml( 'TopIndex', html )

    filepath = folder.joinpath( 'index.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

    # Create the versions index file (in case it's needed)
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Creating versions {'TEST ' if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else ''}index page for {len(state.BibleVersions)} versions…" )
    html = makeTop( level+1, 'topIndex', None, state ) \
            .replace( '__TITLE__', 'TEST Open Bible Data Versions' if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else 'Open Bible Data Versions') \
            .replace( '__KEYWORDS__', 'Bible, translation, English, OET' )
    if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE:
        html = html.replace( '<body>', '<body><p><a href="../../versions/">UP TO MAIN NON-TEST SITE</a></p>')
    bodyHtml = """<!--createVersionsIndexPage--><h1>Open Bible Data TEST Versions</h1>
""" if BibleOrgSysGlobals.debugFlag or DEBUGGING_THIS_MODULE else """<!--createMainIndexPage--><h1>Open Bible Data Versions</h1>
"""

    bodyHtml = f'{bodyHtml}<p>Select one of the above Bible version abbreviations for views of entire documents (‘<i>books</i>’) or sections or chapters, or else select either of the Parallel or Interlinear verse views.</p>\n<ol>\n'
    for versionAbbreviation in state.BibleVersions:
        bodyHtml = f'{bodyHtml}<li><b>{versionAbbreviation}</b>: {state.BibleNames[versionAbbreviation]}</li>\n'
    bodyHtml = f'{bodyHtml}</ol>\n'

    html += bodyHtml + f'<p><small>Last rebuilt: {date.today()}</small></p>\n' + makeBottom( level, 'topIndex', state )
    checkHtml( 'VersionIndex', html )

    filepath = folder.joinpath( 'versions/', 'index.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of html.createMainIndexPage


def createDetailsPages( level:int, versionsFolder:Path, state ) -> bool:
    """
    Creates and saves details (copyright, licence, etc.) pages for each version
        plus a summary page of all the versions.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createDetailsPages( {level}, {versionsFolder}, {state.BibleVersions} )" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Creating details pages for {len(state.BibleVersions)} versions…" )

    allDetailsHTML = ''
    for versionAbbreviation in ['OET'] + [versAbbrev for versAbbrev in state.preloadedBibles]:
        versionName = state.BibleNames[versionAbbreviation]

        if versionAbbreviation != 'OET': # it doesn't have a BibleLocation
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

        topHtml = makeTop( level+1, 'details', 'details.html', state ) \
                .replace( '__TITLE__', f'{versionName} Details' ) \
                .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' ) \
                .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.html">{versionAbbreviation}</a>''',
                            f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )
        
        extraHTML = '''<h2>Key to Abbreviations</h2>
<p>See key and more information <a href="byDocument/FRT.html">here</a>.</p>
''' if versionAbbreviation == 'T4T' else ''

        detailsHtml = f"""{extraHTML}<h2>About</h2>{state.detailsHtml[versionAbbreviation]['about']}
<h2>Copyright</h2>{state.detailsHtml[versionAbbreviation]['copyright']}
<h2>Licence</h2>{state.detailsHtml[versionAbbreviation]['licence']}
<h2>Acknowledgements</h2>{state.detailsHtml[versionAbbreviation]['acknowledgements']}
"""
        bodyHtml = f'''<!--createDetailsPages--><h1>{versionName} Details</h1>
{detailsHtml}'''

        allDetailsHTML = f'''{allDetailsHTML}<h2>{versionName}</h2>
{detailsHtml.replace('h2','h3')}'''

        html = f"{topHtml}{bodyHtml}{makeBottom( level+1, 'details', state )}"
        checkHtml( f'{versionAbbreviation} details', html )

        versionFolder = versionsFolder.joinpath( f'{versionAbbreviation}/' )
        try: os.makedirs( versionFolder )
        except FileExistsError: pass # they were already there

        filepath = versionFolder.joinpath( 'details.html' )
        with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
            htmlFile.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )

    # Make a summary page with details for all versions
    topHtml = makeTop( level, 'allDetails', 'details.html', state ) \
            .replace( '__TITLE__', 'All Versions Details' ) \
            .replace( '__KEYWORDS__', 'Bible, details, about, copyright, licence, acknowledgements' )
            # .replace( f'''<a title="{state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/details.html">{versionAbbreviation}</a>''',
            #             f'''<a title="Up to {state.BibleNames[versionAbbreviation]}" href="{'../'*(level+1)}versions/{BibleOrgSysGlobals.makeSafeString(versionAbbreviation)}/">↑{versionAbbreviation}</a>''' )
    html = f'''{topHtml}<h1>Details for all versions</h1>
{allDetailsHTML}{makeBottom( level, 'allDetails', state )}'''
    checkHtml( 'AllDetails', html )
    
    filepath = versionsFolder.joinpath( 'allDetails.html' )
    with open( filepath, 'wt', encoding='utf-8' ) as htmlFile:
        htmlFile.write( html )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {len(html):,} characters written to {filepath}" )
# end of html.createDetailsPages


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
