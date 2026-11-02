#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# selectedVersesVersions.py
#
# Module handling OpenBibleData selectedVersesVersions functions
#
# Copyright (C) 2023-2025 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling selectedVersesVersions functions.

"""
from pathlib import Path
import random
import requests
import time
import logging
import traceback
import re

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint, BOOKLIST_66
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem

LAST_MODIFIED_DATE = '2026-10-06' # by RJH
SHORT_PROGRAM_NAME = "selectedVersesVersions"
PROGRAM_NAME = "Handle Bible versions with only selected verses"
PROGRAM_VERSION = '0.59'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


SOURCE_FOLDER = Path( '/srv/Documents/FreelyGiven/OpenBibleData/copiedBibles/English/' )
VERSION_NAME_MAP = { # Does not include 1ST, 2DT, or TPT or JQT
                     'CEV':'Contemporary English Version', 'CSB':'Christian Standard Bible',
                     'ESV':'English Standard Version',
                     'LSB':'Legacy Standard Bible ', # Note the trailing space
                     'MSG':'The Message', # but BG not BH
                     'NAB':'New American Bible',
                        'NASB':'NASB 1995',
                        'NIV':'New International Version',
                        'NKJV':'New King James Version',
                        'NLT':'New Living Translation',
                        'NRSV':'New Revised Standard Version', }

SLEEP_SECONDS = 41 # So we don't hammer anyone's site -- we randomise this number upwards
LOAD_LIST = ( 'GEN_1:1','GEN_1:2','GEN_1:3','GEN_1:4','GEN_1:5',
        'GEN_1:27', 'GEN_2:7', 'GEN_2:10', 'GEN_3:7', 'GEN_3:16', 'GEN_14:22', 'GEN_15:6', 'GEN_25:25', 'GEN_27:33', 'GEN_49:10',
    'EXO_10:5', 'EXO_20:11', 'EXO_20:18', 'EXO_32:10', 'EXO_39:36',
    'LEV_1:3', 'LEV_18:22','LEV_18:23', 'LEV_19:28', 'LEV_19:33','LEV_19:34',
    'NUM_6:24','NUM_6:25','NUM_6:26', 'NUM_12:1', 'NUM_14:8', 'NUM_14:18', 'NUM_23:19', 'NUM_32:23',
    'DEU_3:22', 'DEU_4:29', 'DEU_5:7', 'DEU_5:16', 'DEU_6:4','DEU_6:5', 'DEU_7:9', 'DEU_28:6', 'DEU_31:6',
    'JOS_1:1', 'JOS_1:4','JOS_1:5', 'JOS_1:8','JOS_1:9','JOS_1:10','JOS_1:11','JOS_1:12', 'JOS_5:13','JOS_5:14', 'JOS_7:8', 'JOS_10:12', 'JOS_24:14','JOS_24:15',
    'JDG_1:1','JDG_1:2', 'JDG_2:1', 'JDG_5:3', 'JDG_6:12', 'JDG_6:14', 'JDG_6:22','JDG_6:23', 'JDG_8:23', 'JDG_13:24', 'JDG_16:28', 'JDG_18:6', 'JDG_18:10',
    'RUT_1:16', 'RUT_2:4', 'RUT_2:12', 'RUT_2:20', 'RUT_3:9','RUT_3:10','RUT_3:11', 'RUT_4:14','RUT_4:15', 'RUT_4:17',
    'SA1_1:4', 'SA1_1:10','SA1_1:11', 'SA1_2:1','SA1_2:2','SA1_2:3', 'SA1_2:8', 'SA1_3:18','SA1_3:19', 'SA1_12:14', 'SA1_16:7', 'SA1_24:4', 'SA1_25:22',
    'SA2_1:11','SA2_1:12', 'SA2_1:14', 'SA2_2:6', 'SA2_5:10', 'SA2_7:3', 'SA2_7:8','SA2_7:9', 'SA2_7:22', 'SA2_11:4','SA2_11:5', 'SA2_14:17', 'SA2_18:33',
    'KI1_1:3','KI1_1:4', 'KI1_2:3', 'KI1_3:4', 'KI1_8:9','KI1_8:10', 'KI1_17:1', 'KI1_19:1',
    'KI2_2:9', 'KI2_3:17', 'KI2_5:14', 'KI2_6:16', 'KI2_7:9', 'KI2_17:39', 'KI2_18:7', 'KI2_19:19', 'KI2_20:5',
    'CH1_4:10', 'CH1_10:12', 'CH1_15:16', 'CH1_16:17', 'CH1_21:22',
    'CH2_1:10', 'CH2_1:12', 'CH2_6:19', 'CH2_6:21', 'CH2_6:40', 'CH2_7:14', 'CH2_9:8', 'CH2_14:11', 'CH2_15:7', 'CH2_19:7', 'CH2_20:17',
    'EZR_1:1', 'EZR_1:4','EZR_1:5','EZR_1:6','EZR_1:7','EZR_1:8', 'EZR_3:11', 'EZR_7:10', 'EZR_8:21','EZR_8:22','EZR_8:23', 'EZR_9:10',
    'NEH_1:3','NEH_1:4','NEH_1:5', 'NEH_2:18', 'NEH_4:6', 'NEH_4:9', 'NEH_4:14', 'NEH_8:1', 'NEH_8:9','NEH_8:10', 'NEH_9:10','NEH_9:11',
    'EST_1:1', 'EST_1:3','EST_1:4', 'EST_1:10', 'EST_2:7', 'EST_2:10', 'EST_2:15', 'EST_2:17', 'EST_3:4', 'EST_4:3', 'EST_4:13','EST_4:14',
    'JOB_1:8', 'JOB_1:21', 'JOB_2:10', 'JOB_3:25', 'JOB_5:9', 'JOB_19:25', 'JOB_26:7', 'JOB_38:4', 'JOB_40:15', 'JOB_40:18', 'JOB_41:1',
    'PSA_1:1','PSA_1:2','PSA_1:3',
        'PSA_23:1','PSA_23:2','PSA_23:3','PSA_23:4','PSA_23:5','PSA_23:6',
        'PSA_46:10',
        'PSA_91:1','PSA_91:2','PSA_91:3','PSA_91:4','PSA_91:5','PSA_91:6','PSA_91:7','PSA_91:8','PSA_91:9','PSA_91:10','PSA_91:11',
    'PRO_3:5','PRO_3:6', 'PRO_4:23', 'PRO_8:22', 'PRO_22:6',
    'ECC_1:2','ECC_1:3', 'ECC_1:11','ECC_1:12', 'ECC_3:1', 'ECC_3:4', 'ECC_3:11', 'ECC_4:9', 'ECC_5:6', 'ECC_9:5', 'ECC_9:10', 'ECC_12:1', 'ECC_12:13',
    'SNG_1:15', 'SNG_2:1','SNG_2:2', 'SNG_2:6', 'SNG_2:16', 'SNG_4:7', 'SNG_4:10', 'SNG_4:12', 'SNG_5:10', 'SNG_5:16', 'SNG_6:3', 'SNG_7:6', 'SNG_8:3',
    'ISA_9:6', 'ISA_26:3', 'ISA_34:14', 'ISA_40:31', 'ISA_41:10', 'ISA_43:19', 'ISA_51:9', 'ISA_53:5', 'ISA_53:11', 'ISA_54:17',
    'JER_4:4', 'JER_28:6', 'JER_29:11', 'JER_33:3',
    'LAM_3:22','LAM_3:23',
    'EZE_3:10', 'EZE_3:21', 'EZE_9:4', 'EZE_16:60', 'EZE_18:9', 'EZE_20:41', 'EZE_22:30', 'EZE_28:22', 'EZE_30:3', 'EZE_33:9', 'EZE_38:12',
    'DAN_1:8','DAN_1:9', 'DAN_2:19', 'DAN_2:27','DAN_2:28', 'DAN_2:48', 'DAN_4:37', 'DAN_6:3', 'DAN_9:4','DAN_9:5', 'DAN_10:12',
    'HOS_1:2', 'HOS_1:4', 'HOS_1:6', 'HOS_2:3', 'HOS_4:5','HOS_4:6', 'HOS_6:6', 'HOS_11:1',
    'JOL_1:4','JOL_1:5', 'JOL_2:1', 'JOL_2:3','JOL_2:4', 'JOL_2:12', 'JOL_2:28', 'JOL_2:32', 'JOL_3:1', 'JOL_3:4',
    'AMO_3:3','AMO_3:4', 'AMO_3:7', 'AMO_4:1', 'AMO_4:6', 'AMO_5:21', 'AMO_7:16','AMO_7:17', 'AMO_8:11', 'AMO_9:11',
    'OBA_1:2','OBA_1:3','OBA_1:4','OBA_1:5','OBA_1:6','OBA_1:7', 'OBA_1:9','OBA_1:10', 'OBA_1:21',
    'JNA_1:17', 'JNA_2:1','JNA_2:2', 'JNA_2:6','JNA_2:7', 'JNA_2:9','JNA_2:10', 'JNA_3:5', 'JNA_3:10', 'JNA_4:2', 'JNA_4:9','JNA_4:10','JNA_4:11',
    'MIC_1:2', 'MIC_4:1', 'MIC_4:5', 'MIC_5:2', 'MIC_5:6', 'MIC_6:7','MIC_6:8', 'MIC_7:18',
    'NAH_1:2','NAH_1:3', 'NAH_1:5', 'NAH_1:7', 'NAH_1:12', 'NAH_1:15', 'NAH_2:1','NAH_2:2',
    'HAB_2:4', 'HAB_3:17','HAB_3:18','HAB_3:19',
    'ZEP_2:2','ZEP_2:3', 'ZEP_3:5', 'ZEP_3:9', 'ZEP_3:12', 'ZEP_3:14','ZEP_3:15', 'ZEP_3:17', 'ZEP_3:19','ZEP_3:20',
    'HAG_1:3','HAG_1:4','HAG_1:5','HAG_1:6','HAG_1:7', 'HAG_1:11','HAG_1:12', 'HAG_2:3','HAG_2:4','HAG_2:5',
    'ZEC_1:2','ZEC_1:3','ZEC_1:4', 'ZEC_4:6', 'ZEC_9:9','ZEC_9:10', 'ZEC_11:12', 'ZEC_12:10', 'ZEC_14:1', 'ZEC_14:4',
    'MAL_1:3','MAL_1:4', 'MAL_2:3', 'MAL_3:1', 'MAL_3:4', 'MAL_3:6', 'MAL_3:8', 'MAL_3:10', 'MAL_4:1','MAL_4:2',
    'MAT_2:23', 'MAT_5:4', 'MAT_5:16', 'MAT_6:33','MAT_6:34', 'MAT_11:28','MAT_11:29', 'MAT_16:18', 'MAT_28:19','MAT_28:20',
    'MRK_1:1', 'MRK_10:9', 'MRK_11:24', 'MRK_13:14', 'MRK_16:1',
    'LUK_1:37', 'LUK_6:27','LUK_6:28', 'LUK_9:3', 'LUK_11:9','LUK_11:10', 'LUK_18:27', 'LUK_22:15', 'LUK_22:40',
    'JHN_1:1','JHN_1:2','JHN_1:3', 'JHN_1:14', 'JHN_3:3', 'JHN_3:14','JHN_3:15','JHN_3:16', 'JHN_6:33', 'JHN_10:10',
        'JHN_14:6', 'JHN_14:16', 'JHN_14:27', 'JHN_15:5', 'JHN_16:33', 'JHN_20:1',
    'ACT_1:8', 'ACT_3:19', 'ACT_7:23', 'ACT_10:44', 'ACT_15:20', 'ACT_18:17', 'ACT_26:10', 'ACT_28:11',
    'ROM_3:23', 'ROM_5:8', 'ROM_6:23', 'ROM_8:26', 'ROM_8:28', 'ROM_8:31', 'ROM_8:39', 'ROM_11:17', 'ROM_12:1','ROM_12:2',
    'CO1_10:13', 'CO1_13:4','CO1_13:5','CO1_13:6','CO1_13:7','CO1_13:8',
    'CO2_5:17', 'CO2_10:5', 'CO2_12:9', 'CO2_13:1',
    'GAL_2:20', 'GAL_5:22','GAL_5:23', 'GAL_6:9',
    'EPH_2:8','EPH_2:9','EPH_2:10', 'EPH_3:20', 'EPH_6:12',
    'PHP_1:1', 'PHP_1:6', 'PHP_4:6','PHP_4:7','PHP_4:8', 'PHP_4:13', 'PHP_4:19',
    'COL_1:15','COL_1:16', 'COL_1:13', 'COL_2:8','COL_2:9', 'COL_3:1', 'COL_3:12', 'COL_3:16', 'COL_3:23',
    'TH1_2:3', 'TH1_4:5', 'TH1_4:13', 'TH1_4:16', 'TH1_5:6', 'TH1_5:16','TH1_5:17','TH1_5:18', 'TH1_5:21', 'TH1_5:23',
    'TH2_1:11','TH2_1:12', 'TH2_2:13','TH2_2:14', 'TH2_2:16','TH2_2:17', 'TH2_3:3', 'TH2_3:5', 'TH2_3:13', 'TH2_3:16', 'TH2_3:18',
    'TI1_1:3','TI1_1:4', 'TI1_1:15', 'TI1_2:1','TI1_2:2', 'TI1_2:5','TI1_2:6', 'TI1_3:2','TI1_3:3', 'TI1_4:1','TI1_4:2', 'TI1_4:12','TI1_4:13',
    'TI2_1:2', 'TI2_1:7', 'TI2_1:13', 'TI2_2:15', 'TI2_3:1', 'TI2_3:15','TI2_3:16', 'TI2_4:1','TI2_4:2','TI2_4:3',
    'TIT_1:2','TIT_1:5', 'TIT_1:9', 'TIT_2:3', 'TIT_2:11', 'TIT_2:13', 'TIT_3:4','TIT_3:5',
    'PHM_1:2','PHM_1:3','PHM_1:4','PHM_1:5','PHM_1:6','PHM_1:7','PHM_1:8', 'PHM_1:21',
    'HEB_4:12', 'HEB_11:1', 'HEB_11:6', 'HEB_12:1','HEB_12:2',
    'JAM_1:1','JAM_1:2', 'JAM_1:5', 'JAM_1:17', 'JAM_1:22', 'JAM_1:27', 'JAM_2:14', 'JAM_5:14', 'JAM_5:16',
    'PE1_2:9', 'PE1_3:15', 'PE1_5:7','PE1_5:8', 'PE1_5:10',
    'PE2_1:3', 'PE2_1:6', 'PE2_1:11', 'PE2_1:20','PE2_1:21', 'PE2_2:1', 'PE2_2:4', 'PE2_3:4', 'PE2_3:9',
    'JN1_1:8','JN1_1:9', 'JN1_2:1', 'JN1_3:6','JN1_3:7',
    'JN2_1:4', 'JN2_1:8','JN2_1:9',
    'JN3_1:2', 'JN3_1:4', 'JN3_1:11',
    'JDE_1:20', 'JDE_1:24','JDE_1:25',
    'REV_1:1','REV_1:2','REV_1:3', 'REV_1:8', 'REV_2:1', 'REV_2:23', 'REV_13:8', 'REV_14:2', 'REV_22:18','REV_22:19','REV_22:20','REV_22:21',
    )
for ref in LOAD_LIST:
    assert ref.count('_') == 1
    assert ref.count(':') == 1
    assert LOAD_LIST.count(ref) == 1 # No duplicates

BOOK_NAME_MAP = { 'GEN':'genesis', 'EXO':'exodus', 'LEV':'leviticus', 'NUM':'numbers', 'DEU':'deuteronomy',
                  'JOS':'joshua', 'JDG':'judges', 'RUT':'ruth',
                  'SA1':'1_samuel', 'SA2':'2_samuel', 'KI1':'1_kings', 'KI2':'2_kings', 'CH1':'1_chronicles', 'CH2':'2_chronicles',
                  'EZR':'ezra', 'NEH':'nehemiah', 'EST':'esther',
                  'JOB':'job', 'PSA':'psalms', 'PRO':'proverbs', 'ECC':'ecclesiastes', 'SNG':'songs', 'ISA':'isaiah', 'JER':'jeremiah', 'LAM':'lamentations',
                  'EZE':'ezekiel', 'DAN':'daniel', 'HOS':'hosea', 'JOL':'joel', 'AMO':'amos', 'OBA':'obadiah', 'JNA':'jonah',
                  'MIC':'micah', 'NAH':'nahum', 'HAB':'habakkuk', 'ZEP':'zephaniah', 'HAG':'haggai', 'ZEC':'zechariah', 'MAL':'malachi',
                  'MAT':'matthew', 'MRK':'mark', 'LUK':'luke', 'JHN':'john', 'ACT':'acts',
                  'ROM':'romans', 'CO1':'1_corinthians','CO2':'2_corinthians',
                  'GAL':'galatians', 'EPH':'ephesians', 'PHP':'philippians', 'COL':'colossians',
                  'TH1':'1_thessalonians', 'TH2':'2_thessalonians', 'TI1':'1_timothy', 'TI2':'2_timothy', 'TIT':'titus', 'PHM':'philemon',
                  'HEB':'hebrews', 'JAM':'james', 'PE1':'1_peter', 'PE2':'2_peter',
                  'JN1':'1_john', 'JN2':'2_john', 'JN3':'3_john',
                  'JDE':'jude', 'REV':'revelation',
                  }

NARROW_NON_BREAK_SPACE = ' '



class DemoState:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    # Specific short lists
    # Copied from settings.py
    selectedVersesOnlyVersions = ('CSB','NLT','NIV','CEV','ESV','MSG','NAB','NASB','LSB','JQT','2DT','1ST','TPT','NRSV','NKJV', 'NETS' ) # These ones have .tsv sources (and don't produce Bible objects)
    numAllowedSelectedVerses   = (  300,  500,  500,  500,  500,  500,  2500,   500, 1000,   20,  300,  300,  250,   300,   300,    250  ) # Order must match above list
    assert len(numAllowedSelectedVerses) == len(selectedVersesOnlyVersions)
# end of class DemoState


verseCache = {}
def fillSelectedVerses( state:DemoState ) -> None:
    """
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, "fillSelectedVerses( … )" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"fillSelectedVerses( {state.selectedVersesOnlyVersions} )…" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  We have {len(LOAD_LIST):,} individual verses in our list…" )

    addedVerseList, addedVersionList = [], []
    for j,versionAbbreviation in enumerate( state.selectedVersesOnlyVersions ):
        filename = f'{versionAbbreviation}_verses.tsv'
        filepath = SOURCE_FOLDER.joinpath( filename )
        with open( filepath, 'rt', encoding='utf-8' ) as inputFile:
            inputLines = inputFile.read().rstrip( '\n' ).split( '\n' )
        assert inputLines[0] == 'Reference\tVerseText'
        # print( f"{inputLines=}" )
        numFoundSelectedVerses = len(inputLines) - 1

        numAllowedSelectedVerses = int( state.numAllowedSelectedVerses[j] )
        if versionAbbreviation not in VERSION_NAME_MAP:
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Unable to fillSelectedVerses for {versionAbbreviation} (Have{numFoundSelectedVerses:,}/{numAllowedSelectedVerses:,} verses)" )
            continue
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"fillSelectedVerses for {versionAbbreviation} (Have {numFoundSelectedVerses:,}/{numAllowedSelectedVerses:,} verses)" )

        maxSearchVerses = numAllowedSelectedVerses - numFoundSelectedVerses
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {versionAbbreviation} already has {numFoundSelectedVerses:,} verses so we can load up to {maxSearchVerses} more." )
        if maxSearchVerses <= 0:
            # print()
            continue

        # Put the existing verse lines into a dict
        verseDict = {}
        for inputLine in inputLines[1:]:
            assert inputLine.count( '\t' ) == 1
            ref,text = inputLine.split( '\t', 1 )
            assert ref.count( '_' ) == 1, f"{versionAbbreviation} {ref=}"
            assert ref.count( ':' ) == 1, f"{versionAbbreviation} {ref=}"
            assert text.strip() == text, f"{versionAbbreviation} {ref} {text=}"
            verseDict[ref] = text

        fillFunction = fillSelectedVerseBG if versionAbbreviation in ('MSG',) else fillSelectedVerseBH

        numAddedVerses = 0
        interruptedFlag = False
        for loadReference in LOAD_LIST:
            if loadReference in verseDict:
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
                    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  (We already have {loadReference} for {versionAbbreviation}: {verseDict[loadReference]})" )
            if loadReference not in verseDict:
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  We need to load {loadReference} for {versionAbbreviation}…" )
                try:
                    if fillFunction( versionAbbreviation, loadReference, verseDict ):
                        addedVerseList.append( (versionAbbreviation,loadReference) )
                        numAddedVerses += 1
                except (ValueError, KeyError, AssertionError) as err:
                    logging.critical( f"Got error fetching {loadReference} for {versionAbbreviation}" )
                    tracebackTxt = str( traceback.format_exc() ).replace( '\\\\n', '__PROTECT__' ).replace( '\\n', '\n' ).replace( '__PROTECT__', '\\\\n' )
                    logging.critical( f"  {tracebackTxt}" )
                    # excInfoText = str( sys.exc_info() ).replace( '\\n', '\n' )
                    # logging.critical( f"  {excInfoText}" )
                except KeyboardInterrupt:
                    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 1:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Interrupted by user when fetching {versionAbbreviation} with {numAddedVerses=}…" )
                    interruptedFlag = True
                    break
            if numAddedVerses >= maxSearchVerses:
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Stopped downloading verses for {versionAbbreviation} because already added {numAddedVerses:,}" )
                break

        # Maybe we went thru our list but still have permission for more verses ???
        if 0 and not interruptedFlag \
        and numAddedVerses < maxSearchVerses: # Seems we can download some more
            bvs = BibleVersificationSystem( 'KJV' )
            BBB = 'JHN' # So we'll download verses for this book
            numChapters = bvs.getNumChapters( BBB )
            for c in range( 1, numChapters+1 ):
                numVerses = bvs.getNumVerses( BBB, c )
                for v in range( 1, numVerses+1 ):
                    loadReference = f'{BBB}_{c}:{v}'
                    if loadReference in verseDict:
                        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  (We already have {loadReference} for {versionAbbreviation}: {verseDict[loadReference]})" )
                    if loadReference not in verseDict:
                        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  We need to load {loadReference} for {versionAbbreviation}…" )
                        try:
                            if fillFunction( versionAbbreviation, loadReference, verseDict ):
                                addedVerseList.append( (versionAbbreviation,loadReference) )
                                numAddedVerses += 1
                        except (ValueError, KeyError, AssertionError) as err:
                            logging.critical( f"Got error fetching {loadReference} for {versionAbbreviation}" )
                            tracebackTxt = str( traceback.format_exc() ).replace( '\\\\n', '__PROTECT__' ).replace( '\\n', '\n' ).replace( '__PROTECT__', '\\\\n' )
                            logging.critical( f"  {tracebackTxt}" )
                            # excInfoText = str( sys.exc_info() ).replace( '\\n', '\n' )
                            # logging.critical( f"  {excInfoText}" )
                        except KeyboardInterrupt:
                            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 1:
                                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Interrupted by user when fetching {versionAbbreviation} with {numAddedVerses=}…" )
                            interruptedFlag = True
                            break

                    if numAddedVerses >= maxSearchVerses:
                        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Stopped downloading verses for {versionAbbreviation} because already added {numAddedVerses:,}" )
                        break
                if numAddedVerses >= maxSearchVerses:
                    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Stopped downloading verses for {versionAbbreviation} because already added {numAddedVerses:,}" )
                    break

        # Save the verses that we downloaded
        if len(verseDict) > len(inputLines)-1: # then we need to rewrite the file
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Writing {len(verseDict):,} verses for {versionAbbreviation}" )
            BibleOrgSysGlobals.backupAnyExistingFile( filepath, numBackups=3 )
            assert not filepath.is_file() # Check that we're not overwriting anything
            with open( filepath, 'wt', encoding='utf-8' ) as outputFile:
                outputFile.write( 'Reference\tVerseText\n' )
                # We want to output the verses in the correct order
                for orderedBBB in BOOKLIST_66:
                    bookReferencesList = []
                    for ref in verseDict:
                        if ref.startswith( f'{orderedBBB}_' ):
                            assert ref not in bookReferencesList # Duplicates should never occur
                            CV = ref.split( '_', 1 )[1]
                            C,V = CV.split( ':', 1 )
                            bookReferencesList.append( (int(C),int(V)) )
                    for C,V in sorted(bookReferencesList):
                        ref = f'{orderedBBB}_{C}:{V}'
                        outputFile.write( f'{ref}\t{verseDict[ref]}\n' )
            addedVersionList.append( versionAbbreviation )

    if addedVerseList:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 2:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Added {len(addedVerseList):,} individual verses to {len(addedVersionList)} different versions: {addedVersionList}" )
# end of selectedVersesVersions.fillSelectedVerses


def fillSelectedVerseBH( thisVersionAbbreviation:str, BCVReference:str, theDict:dict[str,str] ) -> bool:
    """
    Scrapes the BibleHub web page to get the basic verse (without footnotes, etc.)
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"fillSelectedVerseBH( {thisVersionAbbreviation}, {BCVReference}, {len(theDict)} )" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    fillSelectedVerseBH {thisVersionAbbreviation} {BCVReference}…" )

    try:
        versePage = verseCache[BCVReference]
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Got {len(versePage):,} chars from cache for {thisVersionAbbreviation} {BCVReference}" )
    except KeyError: # it's not in the cache yet
        OUR_SITE_TEMPLATE = 'https://BibleHub.com/BOOK/CHAPTER-VERSE.htm'
        BBB,CV = BCVReference.split( '_', 1 )
        C,V = CV.split( ':', 1 )
        url = OUR_SITE_TEMPLATE.replace( 'BOOK', BOOK_NAME_MAP[BBB] ).replace( 'CHAPTER', C ).replace( 'VERSE', V )

        requestResult = requests.get( url )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Received {len(requestResult.text):,} chars from {url} for {thisVersionAbbreviation} {BCVReference}" )
        # print( requestResult.text )

        versePage = ( requestResult.text.replace( '&#8212;', '—' ).replace( '&#8212', '—' )
                                        .replace( '&#8216;', '‘' ).replace( '&#8216', '‘' )
                                        .replace( '&#8217;', '’' ).replace( '&#8217', '’' )
                                        .replace( '&#8220;', '“' ).replace( '&#8220', '“' )
                                        .replace( '&#8221;', '”' ).replace( '&#8221', '”' )
                                        .replace( '&#8239;', NARROW_NON_BREAK_SPACE )
                    )
        verseCache[BCVReference] = versePage # Cache the page in case this same reference is required by another version

        # We don't want to hammer the site
        sleepSeconds = random.randint( SLEEP_SECONDS, int(SLEEP_SECONDS*1.9) )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Sleeping for {sleepSeconds:,} seconds…" )
        time.sleep( sleepSeconds )
    assert 1000 < len(versePage) < 100_000 # Typically 30-40k chars

    searchString = f'>{VERSION_NAME_MAP[thisVersionAbbreviation]}</a></span><br />'
    startIx = versePage.index( searchString ) + len( searchString )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Found1  '{versePage[startIx:startIx+50]}…' for {thisVersionAbbreviation} {BCVReference}" )
    endIx = versePage.index( '<span class="p"><br /><br /></span>', startIx )
    verseText = versePage[startIx:endIx]
    verseText = verseText.replace( '<i>', '\\add ' ).replace( '</i>', '\\add*' )
    verseText = verseText.replace( 'LORD', '\\nd LORD\\nd*' )
    if thisVersionAbbreviation in ('CEV','NAB'): # not sure why these ones are bad
        verseText = verseText.rstrip()
    elif thisVersionAbbreviation == 'LSB' and BCVReference=='REV_22:21':
        verseText = verseText.rstrip()
    if len(verseText) <= 80:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found2a ({len(verseText)}) '{verseText}' for {thisVersionAbbreviation} {BCVReference}" )
    else:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found2b ({len(verseText)}) '{verseText[:40]}…{verseText[-40:]}' for {thisVersionAbbreviation} {BCVReference}" )
    assert '&#' not in verseText, f"{thisVersionAbbreviation} {BCVReference} {verseText=}"
    assert '<' not in verseText
    assert '>' not in verseText
    assert verseText.strip() == verseText, f"{thisVersionAbbreviation} {BCVReference} {verseText=}"

    assert 11 < len(verseText) < 400, f"({len(verseText)=}) {verseText=}" # 352 is longest so far
    assert BCVReference not in theDict # Don't want duplicates
    theDict[BCVReference] = verseText

    return True
# end of selectedVersesVersions.fillSelectedVerseBH


def fillSelectedVerseBG( thisVersionAbbreviation:str, BCVReference:str, theDict:dict[str,str] ) -> bool:
    """
    Scrapes the BibleGateway web page to get the basic verse (without footnotes, etc.)
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"fillSelectedVerseBG( {thisVersionAbbreviation}, {BCVReference}, {len(theDict)} )" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 2:
        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    fillSelectedVerseBG {thisVersionAbbreviation} {BCVReference}…" )

    BBB,CV = BCVReference.split( '_', 1 )
    C,V = CV.split( ':', 1 )

    try:
        versePage = verseCache[BCVReference]
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 2:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      Got {len(versePage):,} chars from cache for {thisVersionAbbreviation} {BCVReference}" )
    except KeyError: # it's not in the cache yet
        OUR_SITE_TEMPLATE = 'https://www.biblegateway.com/passage/?search=BOOK+CHAPTER%3AVERSE&version=MSG'
        url = OUR_SITE_TEMPLATE.replace( 'BOOK', BOOK_NAME_MAP[BBB] ).replace( 'CHAPTER', C ).replace( 'VERSE', V )

        requestResult = requests.get( url )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 2:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      Received {len(requestResult.text):,} chars from {url} for {thisVersionAbbreviation} {BCVReference}" )
        # print( requestResult.text )

        versePage = ( requestResult.text
                        .replace( '&#8212;', '—' ).replace( '&#8212', '—' )
                        .replace( '&#8216;', '‘' ).replace( '&#8216', '‘' )
                        .replace( '&#8217;', '’' ).replace( '&#8217', '’' )
                        .replace( '&#8220;', '“' ).replace( '&#8220', '“' )
                        .replace( '&#8221;', '”' ).replace( '&#8221', '”' )
                    )
        verseCache[BCVReference] = versePage # Cache the page in case this same reference is required by another version

        # We don't want to hammer the site
        sleepSeconds = random.randint( SLEEP_SECONDS, int(SLEEP_SECONDS*1.9) )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 2:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"        Sleeping for {sleepSeconds:,} seconds…" )
        try: time.sleep( sleepSeconds )
        except KeyboardInterrupt:
            raise KeyboardInterrupt
    assert 10_000 < len(versePage) < 160_000, f"{len(versePage)=:,}" # Typically 130-140k chars

    searchString = f'<span id="en-{thisVersionAbbreviation}-'
    startIx = versePage.index( searchString ) + len( searchString )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Found1  '{versePage[startIx:startIx+50]}…' for {thisVersionAbbreviation} {BCVReference}" )

    # Fetch and check the ref
    refIx = versePage.index( ' class="text ', startIx )
    endRefIx = versePage.index( '">', refIx )
    refText = versePage[refIx+13:endRefIx]
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Found2 {refText=} for {thisVersionAbbreviation} {BCVReference}" )
    assert refText.count( '-' ) in (2,5), f"{refText=}" # Either John-3-15 or John-3-16-John-3-18 (or similar)
    refBits = refText.split( '-' )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Got3 ({len(refBits)}) {refBits=} for {thisVersionAbbreviation} {BCVReference}" )
    refs = []
    if len(refBits) == 6: # It's a verse range
        bk1, bk2 = refBits[0], refBits[3]
        assert bk1 == bk2, f"{refBits=}" # Same book name
        C1, V1 = refBits[1], refBits[2]
        C2, V2 = refBits[4], refBits[5]
        assert C1 == C2, f"{refBits=}" # Not a verse range across a chapter break
        for v in range( int(V1), int(V2)+1 ):
            refs.append( f'{BBB}_{C1}:{v}')
    elif len(refBits) == 3: # It's a single verse
        refs.append( f'{BBB}_{refBits[1]}:{refBits[2]}')
    else: need_more_code
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        Got4 ({len(refs)}) {refs=} for {thisVersionAbbreviation} {BCVReference}" )
    assert BCVReference in refs, f"{BCVReference=} {refs=}"

    # Fetch and parse the verse(s)
    endIx = versePage.index( '<a class="full-chap-link" href="', endRefIx )
    wholeText = versePage[endRefIx+2:endIx].rstrip() # There might be 0,1,2 spaces before that string
    # verseText = verseText.replace( 'LORD', '\\nd LORD\\nd*' )
    if len(wholeText) <= 80:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found2a ({len(wholeText)}) '{wholeText}' for {thisVersionAbbreviation} {BCVReference}" )
    else:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found2b ({len(wholeText)}) '{wholeText[:40]}…{wholeText[-40:]}' for {thisVersionAbbreviation} {BCVReference}" )
    assert '&#' not in wholeText
    # assert '<' not in verseText
    # assert '>' not in verseText
    assert wholeText.strip() == wholeText, f"{thisVersionAbbreviation} {BCVReference} {wholeText[0]=} {wholeText[-1]=} {wholeText=}"
    assert 50 < len(wholeText) < 8_000, f"({len(wholeText)=}) {wholeText=}" # 6588 is longest so far

    # Break the verse into fields (may include the section header, etc.)
    adjWholeText = wholeText.replace( '"versenum mid-line"', '"versenum"' ) # For easier processing below
    vnumCount = adjWholeText.count( '<sup class="versenum">' )
    if vnumCount==0 and adjWholeText.count( '<span class="chapternum">' )==1:
        adjWholeText = ( adjWholeText.replace( '<span class="chapternum">', '<sup class="versenum">' ) # Because there's no verse number for the first verse in a chapter (so we put one in for our purposes)
                                    .replace( '\xa0', '</sup>', 1 )
                        )
        vnumCount = adjWholeText.count( '<sup class="versenum">' )
    if vnumCount != 1:
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f'''        Found unexpected {vnumCount} versenum's ({len(wholeText)}) '{wholeText}' for {thisVersionAbbreviation} {BCVReference}''' )
    try:
        if vnumCount == 2:
            part1, part2, _part3 = adjWholeText.split( '<sup class="versenum">' )
        else:
            part1, part2 = adjWholeText.split( '<sup class="versenum">' )
    except ValueError: # too many values to unpack
        logging.critical( f"Why do we have multiple verse numbers in {wholeText=} for {thisVersionAbbreviation} {BCVReference}" )
        raise ValueError
    s1 = None
    if '</h3>' in part1:
        p1Ix = part1.index( '</h3>' )
        s1 = part1[:p1Ix].replace( '</span>', '' ) # Has a span at the end
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found3 s1 ({len(s1)}) '{s1}' for {thisVersionAbbreviation} {BCVReference}" )
        while '<span style="font-variant: small-caps" class="small-caps divine-name">' in s1:
            ix = s1.index( '<span style="font-variant: small-caps" class="small-caps divine-name">' )
            s1 = s1.replace( '<span style="font-variant: small-caps" class="small-caps divine-name">', '\\\\nd ', 1 )
            vT1, vT2 = s1[:ix], s1[ix:].replace( '</span>', '\\\\nd*', 1 )
            s1 = f'{vT1}{vT2}'
        assert s1 and '<' not in s1 and '>' not in s1 and '&' not in s1 and '"' not in s1, f"{s1=}"
    verseText = part2
    try:
        p2Ix = verseText.index( '</sup>' ) # We assume that this follows the verse number(s) (which we already know)
    except ValueError: # substring not found
        logging.critical( f"Why was no </sup> found at end of verse number in {wholeText=} for {thisVersionAbbreviation} {BCVReference}" )
        raise ValueError
    verseText = ( verseText[p2Ix+6:].removesuffix( '</div' ).rstrip().removesuffix( '</p>' ).removesuffix( '</span>' )
                    .replace( '<div class="poetry top-1"><p class="line">', '\\n\\\\q1 ' )
                    .replace( '<div class="poetry"><p class="line">', '\\n\\\\q1 ' )
                    .replace( '<div class="list left-1 top-1">', '\\n' )
                    .replace( '<br /><span class="indent-1">', '\\n\\\\q1 ' )
                    .replace( '<p class="first-line-none left-1 top-1">', '\\n\\\\m ' ).replace( '<p class="first-line-none top-1">', '\\n\\\\m ' )
                    .replace( '<br />', '\\n\\\\m ' )
                    .replace( '<p>', '\\n\\\\p ' )
                    .replace( '<p class="center">', '\\n\\\\pc ' )
                    .replace( '<p class="top-1">', '\\n\\\\m ' )
                    .replace( '<p class="hang-1 top-none">', '\\n\\\\li1 ' ).replace( '<p class="hang-1">', '\\n\\\\li1 ' )
                    .replace( '<p class="left-1 hang-2 top-none">', '\\n\\\\li2 ' ).replace( '<p class="left-1 hang-2">', '\\n\\\\li2 ' )
                    .replace( '<p class="left-1 hang-3 top-none">', '\\n\\\\li3 ' ).replace( '<p class="left-1 hang-3">', '\\n\\\\li3 ' )
                    .replace( '<p class="first-line-none">', '\\n' )
                    .replace( '<h3>', '\\n\\\\s3 ' ).replace( '</h3>', '\\n' )
                    .replace( '\\n\\\\m \\n\\\\m ', '\\n\\\\m ' ) # Just in case
                    .replace( '\\n\\n', '\\n' )
                    .rstrip().removesuffix( '\\\\m' ).rstrip().removesuffix( '\\\\p' ).rstrip().removesuffix( '\\\\q1' ).rstrip().removesuffix( '\\n' ).rstrip()
                )
    while '<span style="font-variant: small-caps" class="small-caps divine-name">' in verseText:
        ix = verseText.index( '<span style="font-variant: small-caps" class="small-caps divine-name">' )
        verseText = verseText.replace( '<span style="font-variant: small-caps" class="small-caps divine-name">', '\\\\nd ', 1 )
        vT1, vT2 = verseText[:ix], verseText[ix:].replace( '</span>', '\\\\nd*', 1 )
        verseText = f'{vT1}{vT2}'
    verseText = verseText.replace( '<i>', '\\\\add ' ).replace( '</i>', '\\\\add*' )
    if part1: dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found4a part1 ({len(part1)}) '{part1}' for {thisVersionAbbreviation} {BCVReference}" )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"        Found4b verseText ({len(verseText)}) '{verseText}' for {thisVersionAbbreviation} {BCVReference}" )
    if BCVReference != 'SNG_7:6':
        assert '</h3>' not in verseText, f"{thisVersionAbbreviation} {BCVReference} {verseText=}"
    verseText = verseText.replace( '</span>', '' ).replace( '</p>', '' ).replace( '</div>', '' ).replace( '&nbsp;', '' ).rstrip()
    ourRe = re.compile( '<span class=\\"[^">]+?">' )
    verseText, count = ourRe.subn( '', verseText )
    assert verseText and '<' not in verseText and '>' not in verseText and '&' not in verseText and '"' not in verseText, f"{verseText=}\n***FROM*** {part2=}"
    assert 11 < len(verseText) < 3_000, f"({len(verseText)=}) {verseText=}" # 2126 is longest so far
    if len(refs) > 1:
        verseText = f'({V1}-{V2}) {verseText}' # Add the verse range back in

    for rr,ref in enumerate( refs ):
        assert ref not in theDict # Don't want duplicates
        if rr==0 and s1:
            theDict[ref] = f'\\\\s1 {s1}\\n{verseText}' # Prepend the section heading
        else:
            theDict[ref] = verseText # Duplicate the verse for all verses in the range

    return True
# end of selectedVersesVersions.fillSelectedVerseBG



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the selectedVersesVersions object
    state = DemoState()
    fillSelectedVerses( state )
# end of selectedVersesVersions.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the selectedVersesVersions object
    state = DemoState()
    fillSelectedVerses( state )
# end of selectedVersesVersions.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of selectedVersesVersions.py
