#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# createOETReferencePages.py
#
# Module handling OpenBibleData createOETReferencePages functions
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
Module handling createOETReferencePages functions.

createOETReferencePages( level:int, outputFolderPath:Path, state:State ) -> bool
preprocessGreekWordsLemmasGlosses( BBBSelection:Union[str, List[str]], state ) -> bool
preprocessHebrewWordsLemmasGlosses( BBBSelection:Union[str, List[str]], state ) -> bool
formatNTSpansGlossWords( glossWords:str ) -> str
formatNTContextSpansOETGlossWords( rowNum:int, state:State ) -> str
create_Hebrew_word_pages( level:int, outputFolderPath:Path, state:State ) -> None
create_Hebrew_lemma_pages( level:int, outputFolderPath:Path, state:State ) -> None
create_Greek_word_pages( level:int, outputFolderPath:Path, state:State ) -> None
create_Greek_lemma_pages( level:int, outputFolderPath:Path, state:State ) -> None
create_person_pages( level:int, outputFolderPath:Path, state:State ) -> int
create_location_pages( level:int, outputFolderPath:Path, state:State ) -> int
livenMD( level:int, mdText:str ) -> str
removeHebrewVowelPointing( text:str, removeMetegOrSiluq=True ) -> str
briefDemo() -> None
fullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2023-07-30 Show first 40 word & lemma entries even if there's over 100 (didn't use to display any of them)
    2023-08-15 Remove '....' off front of displayed morphology field (if it's there)
                and put ‘typographic quotes’ around glosses
    2023-08-30 Add nomina sacra to word pages
    2023-10-09 Add role letter to word pages
    2023-10-13 For single-use Greek words, append a note if it's also the only use of that lemma.
    2023-10-16 Add other Greek words with similar glosses
    2023-12-31 Appended a key to word and lemma pages with roles and morphology abbreviations
    2024-01-03 Added other Greek lemmas with similar glosses
    2024-02-06 Remove some of the unnecessary static text on word and lemma pages
    2024-03-22 Add OT Hebrew word and lemma pages
    2024-04-23 Use ref for Heb and Grk word page filenames (instead of row number)
    2024-05-27 Try adding word connections for Hebrew roots
    2024-06-03 In test mode, only make connected lemma pages for Heb/Grk words used
    2024-06-19 Remove notes and segs from Hebrew words indexes
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Union
from pathlib import Path
import os
from collections import defaultdict
import re
import json
import logging
import unicodedata
from time import time

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27
from BibleOrgSys.OriginalLanguages import Hebrew

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Hebrew, transliterate_Greek

from settings import State, TEST_MODE, ALL_TEST_REFERENCE_PAGES, TEST_BOOK_LIST, SITE_NAME
from html import makeTop, makeBottom, checkHtml
from OETHandlers import getOETTidyBBB, getHebrewWordpageFilename, getGreekWordpageFilename


LAST_MODIFIED_DATE = '2024-07-09' # by RJH
SHORT_PROGRAM_NAME = "createOETReferencePages"
PROGRAM_NAME = "OpenBibleData createOETReferencePages functions"
PROGRAM_VERSION = '0.74'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
TAB = '\t'
# EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


project_folderpath = Path(__file__).parent.parent # Find folders relative to this module
FG_folderpath = project_folderpath.parent # Path to find parallel Freely-Given.org repos
THEOGRAPHIC_INPUT_FOLDER_PATH = FG_folderpath.joinpath( 'Bible_speaker_identification/outsideSources/TheographicBibleData/derivedFiles/' )


CNTR_BOOK_ID_MAP = {
    'MAT':40, 'MRK':41, 'LUK':42, 'JHN':43, 'ACT':44,
    'ROM':45, 'CO1':46, 'CO2':47, 'GAL':48, 'EPH':49, 'PHP':50, 'COL':51, 'TH1':52, 'TH2':53, 'TI1':54, 'TI2':55, 'TIT':56, 'PHM':57,
    'HEB':58, 'JAM':58, 'PE1':60, 'PE2':61, 'JN1':62, 'JN2':63, 'JN3':64, 'JDE':65, 'REV':66}
CNTR_ROLE_NAME_DICT = {'N':'noun', 'S':'substantive adjective', 'A':'adjective', 'E':'determiner/case-marker', 'R':'pronoun',
                  'V':'verb', 'I':'interjection', 'P':'preposition', 'D':'adverb', 'C':'conjunction', 'T':'particle'}
CNTR_MOOD_NAME_DICT = {'I':'indicative', 'M':'imperative', 'S':'subjunctive',
            'O':'optative', 'N':'infinitive', 'P':'participle', 'e':'e'}
CNTR_TENSE_NAME_DICT = {'P':'present', 'I':'imperfect', 'F':'future', 'A':'aorist', 'E':'perfect', 'L':'pluperfect', 'U':'U', 'e':'per'}
CNTR_VOICE_NAME_DICT = {'A':'active', 'M':'middle', 'P':'passive', 'p':'pass', 'm':'mid', 'a':'act'}
CNTR_PERSON_NAME_DICT = {'1':'1st', '2':'2nd', '3':'3rd', 'g':'g'}
CNTR_CASE_NAME_DICT = {'N':'nominative', 'G':'genitive', 'D':'dative', 'A':'accusative', 'V':'vocative', 'g':'gen', 'n':'nom', 'a':'acc', 'd':'dat', 'v':'voc', 'U':'U'}
CNTR_GENDER_NAME_DICT = {'M':'masculine', 'F':'feminine', 'N':'neuter', 'm':'masc', 'f':'fem', 'n':'neu'}
CNTR_NUMBER_NAME_DICT = {'S':'singular', 'P':'plural', 's':'sg', 'p':'pl'}
CNTR_MORPHOLOGY_NAME_DICT = { 'AFP':'accusative,feminine,plural', 'AFS':'accusative,feminine,singular',
                                    'AMP':'accusative,masculine,plural', 'AMS':'accusative,masculine,singular',
                                    'ANP':'accusative,neuter,plural', 'ANS':'accusative,neuter,singular',
                                'DFP':'dative,feminine,plural', 'DFS':'dative,feminine,singular',
                                    'DMP':'dative,masculine,plural', 'DMS':'dative,masculine,singular',
                                    'DNP':'dative,neuter,plural', 'DNS':'dative,neuter,singular',
                                'GFP':'genitive,feminine,plural', 'GFS':'genitive,feminine,singular',
                                    'GMP':'genitive,masculine,plural', 'GMS':'genitive,masculine,singular',
                                    'GNP':'genitive,neuter,plural', 'GNS':'genitive,neuter,singular',
                                'NFP':'nominative,feminine,plural', 'NFS':'nominative,feminine,singular', 'NMP':'nominative,masculine,plural', 'NMS':'nominative,masculine,singular', 'NNP':'nominative,neuter,plural', 'NNS':'nominative,neuter,singular',
                                'VFP':'vocative,feminine,plural', 'VFS':'vocative,feminine,singular',
                                    'VMP':'vocative,masculine,plural', 'VMS':'vocative,masculine,singular',
                                    'VNP':'vocative,neuter,plural', 'VNS':'vocative,neuter,singular',
                            '...1A.P':'1st person,accusative,plural', '...1A.S':'1st person,accusative,singular',
                                    '...1AFP':'1st person,accusative,feminine,plural', '...1AFS':'1st person,accusative,feminine,singular',
                                    '...1AMP':'1st person,accusative,masculine,plural', '...1AMS':'1st person,accusative,masculine,singular',
                                    '...1ANP':'1st person,accusative,neuter,plural', '...1ANS':'1st person,accusative,neuter,singular',
                                '...1D.P':'1st person,dative,plural', '...1D.S':'1st person,dative,singular',
                                    '...1DFP':'1st person,dative,feminine,plural', '...1DFS':'1st person,dative,feminine,singular',
                                    '...1DMP':'1st person,dative,masculine,plural', '...1DMS':'1st person,dative,masculine,singular',
                                    '...1DNP':'1st person,dative,neuter,plural', '...1DNS':'1st person,dative,neuter,singular',
                                    '...1G.P':'1st person,genitive,plural', '...1G.S':'1st person,genitive,singular',
                                        '...1GFP':'1st person,genitive,feminine,plural', '...1GFS':'1st person,genitive,feminine,singular',
                                        '...1GMP':'1st person,genitive,masculine,plural', '...1GMS':'1st person,genitive,masculine,singular',
                                        '...1GNP':'1st person,genitive,neuter,plural',
                                '...1N.P':'1st person,nominative,plural', '...1N.S':'1st person,nominative,singular',
                                        '...1NFS':'1st person,nominative,feminine,singular',
                                        '...1NMP':'1st person,nominative,masculine,plural', '...1NMS':'1st person,nominative,masculine,singular',
                                        '...1NNP':'1st person,nominative,neuter,plural', '...1NNS':'1st person,nominative,neuter,singular',
                            '...2A.S':'2nd person,accusative,singular', '...2A.P':'2nd person,accusative,plural',
                                    '...2AFP':'2nd person,accusative,feminine,plural', '...2AFS':'2nd person,accusative,feminine,singular',
                                    '...2AMP':'2nd person,accusative,masculine,plural', '...2AMS':'2nd person,accusative,masculine,singular',
                                    '...2ANP':'2nd person,accusative,neuter,plural', '...2ANS':'2nd person,accusative,neuter,singular',
                                '...2D.P':'2nd person,dative,plural', '...2D.S':'2nd person,dative,singular',
                                    '...2DFP':'2nd person,dative,feminine,plural', '...2DFS':'2nd person,dative,feminine,singular',
                                    '...2DMP':'2nd person,dative,masculine,plural', '...2DMS':'2nd person,dative,masculine,singular',
                                    '...2DNS':'2nd person,dative,neuter,singular',
                                '...2G.P':'2nd person,genitive,plural', '...2G.S':'2nd person,genitive,singular',
                                    '...2GFS':'2nd person,genitive,feminine,singular',
                                    '...2GMP':'2nd person,genitive,masculine,plural', '...2GMS':'2nd person,genitive,masculine,singular',
                                '...2N.P':'2nd person,nominative,plural', '...2N.S':'2nd person,nominative,singular',
                                    '...2NFP':'2nd person,nominative,feminine,plural',
                                    '...2NMP':'2nd person,nominative,masculine,plural', '...2NMS':'2nd person,nominative,masculine,singular',
                                    '...2NNP':'2nd person,nominative,neuter,plural', '...2NNS':'2nd person,nominative,meuter,singular',
                                '...2VFP':'2nd person,vocative,feminine,plural', '...2VFS':'2nd person,vocative,feminine,singular',
                                '...2VMP':'2nd person,vocative,masculine,plural', '...2VMS':'2nd person,vocative,masculine,singular',
                                '...2VNP':'2nd person,vocative,neuter,plural', '...2VNS':'2nd person,vocative,neuter,singular',
                            '...3AFP':'3rd person,accusative,feminine,plural', '...3AFS':'3rd person,accusative,feminine,singular',
                                    '...3AMP':'3rd person,accusative,masculine,plural', '...3AMS':'3rd person,accusative,masculine,singular',
                                    '...3ANP':'3rd person,accusative,neuter,plural', '...3ANS':'3rd person,accusative,neuter,singular',
                                    '...3DFP':'3rd person,dative,feminine,plural', '...3DFS':'3rd person,dative,feminine,singular',
                                    '...3DMP':'3rd person,dative,masculine,plural', '...3DMS':'3rd person,dative,masculine,singular',
                                    '...3DNP':'3rd person,dative,neuter,plural', '...3DNS':'3rd person,dative,neuter,singular',
                                    '...3GFP':'3rd person,genitive,feminine,plural', '...3GFS':'3rd person,genitive,feminine,singular',
                                    '...3GMP':'3rd person,genitive,masculine,plural', '...3GMS':'3rd person,genitive,masculine,singular',
                                    '...3GNP':'3rd person,genitive,neuter,plural', '...3GNS':'3rd person,genitive,neuter,singular',
                                    '...3NFS':'3rd person,nominative,feminine,singular',
                                    '...3NMP':'3rd person,nominative,masculine,plural', '...3NMS':'3rd person,nominative,masculine,singular',
                                    '...3NNS':'3rd person,nominative,neuter,singular',
                                'IAA1..P':'indicative,aorist,active,1st person plural', 'IAA1..S':'indicative,aorist,active,1st person singular',
                                            'IAA2..P':'indicative,aorist,active,2nd person plural', 'IAA2..S':'indicative,aorist,active,2nd person singular',
                                            'IAA3..P':'indicative,aorist,active,3rd person plural', 'IAA3..S':'indicative,aorist,active,3rd person singular',
                                        'IAM1..P':'indicative,aorist,middle,1st person plural', 'IAM1..S':'indicative,aorist,middle,1st person singular',
                                            'IAM2..P':'indicative,aorist,middle,2nd person plural', 'IAM2..S':'indicative,aorist,middle,2nd person singular',
                                            'IAM3..P':'indicative,aorist,middle,3rd person plural', 'IAM3..S':'indicative,aorist,middle,3rd person singular',
                                        'IAP1..P':'indicative,aorist,passive,1st person plural', 'IAP1..S':'indicative,aorist,passive,1st person singular',
                                            'IAP2..P':'indicative,aorist,passive,2nd person plural', 'IAP2..S':'indicative,aorist,passive,2nd person singular',
                                            'IAP3..P':'indicative,aorist,passive,3rd person plural', 'IAP3..S':'indicative,aorist,passive,3rd person singular',
                                    'IEA1..P':'indicative,perfect,active,1st person plural', 'IEA1..S':'indicative,perfect,active,1st person singular',
                                        'IEA2..P':'indicative,perfect,active,2nd person plural', 'IEA2..S':'indicative,perfect,active,2nd person singular',
                                        'IEA3..P':'indicative,perfect,active,3rd person plural', 'IEA3..S':'indicative,perfect,active,3rd person singular',
                                    'IEM1..P':'indicative,perfect,middle,1st person plural', 'IEM1..S':'indicative,perfect,middle,1st person singular',
                                        'IEM2..P':'indicative,perfect,middle,2nd person plural', 'IEM2..S':'indicative,perfect,middle,2nd person singular',
                                        'IEM3..P':'indicative,perfect,middle,3rd person plural', 'IEM3..S':'indicative,perfect,middle,3rd person singular',
                                    'IEP1..P':'indicative,perfect,passive,1st person plural', 'IEP1..S':'indicative,perfect,passive,1st person singular',
                                        'IEP2..P':'indicative,perfect,passive,2nd person plural', 'IEP2..S':'indicative,perfect,passive,2nd person singular',
                                        'IEP3..P':'indicative,perfect,passive,3rd person plural', 'IEP3..S':'indicative,perfect,passive,3rd person singular',
                                    'IFA1..P':'indicative,future,active,1st person plural', 'IFA1..S':'indicative,future,active,1st person singular',
                                        'IFA2..P':'indicative,future,active,2nd person plural', 'IFA2..S':'indicative,future,active,2nd person singular',
                                        'IFA3..P':'indicative,future,active,3rd person plural', 'IFA3..S':'indicative,future,active,3rd person singular',
                                    'IFM1..P':'indicative,future,middle,1st person plural', 'IFM1..S':'indicative,future,middle,1st person singular',
                                        'IFM2..P':'indicative,future,middle,2nd person plural', 'IFM2..S':'indicative,future,middle,2nd person singular',
                                        'IFM3..P':'indicative,future,middle,3rd person plural', 'IFM3..S':'indicative,future,middle,3rd person singular',
                                    'IFP1..P':'indicative,future,passive,1st person plural', 'IFP1..S':'indicative,future,passive,1st person singular',
                                        'IFP2..P':'indicative,future,passive,2nd person plural', 'IFP2..S':'indicative,future,passive,2nd person singular',
                                        'IFP3..P':'indicative,future,passive,3rd person plural', 'IFP3..S':'indicative,future,passive,3rd person singular',
                                    'IIA1..P':'indicative,imperfect,active,1st person plural', 'IIA1..S':'indicative,imperfect,active,1st person singular',
                                        'IIA2..P':'indicative,imperfect,active,2nd person plural', 'IIA2..S':'indicative,imperfect,active,2nd person singular',
                                        'IIA3..P':'indicative,imperfect,active,3rd person plural', 'IIA3..S':'indicative,imperfect,active,3rd person singular',
                                        'IIM1..P':'indicative,imperfect,middle,1st person plural', 'IIM1..S':'indicative,imperfect,middle,1st person singular',
                                            'IIM2..P':'indicative,imperfect,middle,2nd person plural', 'IIM2..S':'indicative,imperfect,middle,2nd person singular',
                                            'IIM3..P':'indicative,imperfect,middle,3rd person plural', 'IIM3..S':'indicative,imperfect,middle,3rd person singular',
                                        'IIP1..P':'indicative,imperfect,passive,1st person plural', 'IIP1..S':'indicative,imperfect,passive,1st person singular',
                                            'IIP2..P':'indicative,imperfect,passive,2nd person plural',
                                            'IIP3..P':'indicative,imperfect,passive,3rd person plural', 'IIP3..S':'indicative,imperfect,passive,3rd person singular',
                                    'ILA1..P':'indicative,pluperfect,active,1st person plural', 'ILA1..S':'indicative,pluperfect,active,1st person singular',
                                        'ILA2..P':'indicative,pluperfect,active,2nd person plural', 'ILA2..S':'indicative,pluperfect,active,2nd person singular',
                                        'ILA3..P':'indicative,pluperfect,active,3rd person plural', 'ILA3..S':'indicative,pluperfect,active,3rd person singular',
                                    'ILM3..P':'indicative,pluperfect,middle,3rd person plural', 'ILM3..S':'indicative,pluperfect,middle,3rd person singular',
                                    'ILP3..S':'indicative,pluperfect,passive,3rd person singular',
                                    'IPA1..P':'indicative,present,active,1st person plural', 'IPA1..S':'indicative,present,active,1st person singular',
                                        'IPA2..P':'indicative,present,active,2nd person plural', 'IPA2..S':'indicative,present,active,2nd person singular',
                                        'IPA3..P':'indicative,present,active,3rd person plural', 'IPA3..S':'indicative,present,active,3rd person singular',
                                    'IPM1..P':'indicative,present,middle,1st person plural', 'IPM1..S':'indicative,present,middle,1st person singular',
                                        'IPM2..P':'indicative,present,middle,2nd person plural', 'IPM2..S':'indicative,present,middle,2nd person singular',
                                        'IPM3..P':'indicative,present,middle,3rd person plural', 'IPM3..S':'indicative,present,middle,3rd person singular',
                                    'IPP1..P':'indicative,present,passive,1st person plural', 'IPP1..S':'indicative,present,passive,1st person singular',
                                        'IPP2..P':'indicative,present,passive,2nd person plural', 'IPP2..S':'indicative,present,passive,2nd person singular',
                                        'IPP3..P':'indicative,present,passive,3rd person plural', 'IPP3..S':'indicative,present,passive,3rd person singular',
                                    'IUA3..P':'indicative,UNKNOWN,active,3rd person plural',
                                    'IUM3..P':'indicative,UNKNOWN,middle,3rd person plural',
                                'MAA2..P':'imperative,aorist,active,2nd person plural', 'MAA2..S':'imperative,aorist,active,2nd person singular',
                                    'MAA3..P':'imperative,aorist,active,3rd person plural', 'MAA3..S':'imperative,aorist,active,3rd person singular',
                                'MAM2..P':'imperative,aorist,middle,2nd person plural', 'MAM2..S':'imperative,aorist,middle,2nd person singular',
                                    'MAM3..P':'imperative,aorist,middle,3rd person plural', 'MAM3..S':'imperative,aorist,middle,3rd person singular',
                                'MAP2..P':'imperative,aorist,passive,2nd person plural', 'MAP2..S':'imperative,aorist,passive,2nd person singular',
                                    'MAP3..P':'imperative,aorist,passive,3rd person plural', 'MAP3..S':'imperative,aorist,passive,3rd person singular',
                                'MEA2..P':'imperative,perfect,active,2nd person plural',
                                    'MEA3..S':'imperative,perfect,active,3rd person singular',
                                'MEP2..P':'imperative,perfect,passive,2nd person plural', 'MEP2..S':'imperative,perfect,passive,2nd person singular',
                                'MPA2..P':'imperative,present,active,2nd person plural', 'MPA2..S':'imperative,present,active,2nd person singular',
                                    'MPA3..P':'imperative,present,active,3rd person plural', 'MPA3..S':'imperative,present,active,3rd person singular',
                                'MPM2..P':'imperative,present,middle,2nd person plural', 'MPM2..S':'imperative,present,middle,2nd person singular',
                                    'MPM3..P':'imperative,present,middle,3rd person plural', 'MPM3..S':'imperative,present,middle,3rd person singular',
                                'MPP2..P':'imperative,present,passive,2nd person plural', 'MPP2..S':'imperative,present,passive,2nd person singular',
                                    'MPP3..P':'imperative,present,passive,3rd person plural', 'MPP3..S':'imperative,present,passive,3rd person singular',
                                'NAA....':'infinitive,aorist,active', 'NAM....':'infinitive,aorist,middle', 'NAP....':'infinitive,aorist,passive',
                                    'NEA....':'infinitive,perfect,active', 'NEM....':'infinitive,perfect,middle', 'NEP....':'infinitive,perfect,passive',
                                    'NFA....':'infinitive,future,active', 'NFM....':'infinitive,future,middle', 'NFP....':'infinitive,future,passive',
                                    'NPA....':'infinitive,present,active', 'NPM....':'infinitive,present,middle', 'NPP....':'infinitive,present,passive',
                                'OAA3..P':'optative,aorist,active,3rd person plural', 'OAA3..S':'optative,aorist,active,3rd person singular',
                                'OAM1..S':'optative,aorist,middle,1st person singular',
                                    'OAM2..P':'optative,aorist,middle,2nd person plural',
                                    'OAM3..S':'optative,aorist,middle,3rd person singular',
                                'OAP3..S':'optative,aorist,passive,3rd person singular',
                                'OFA3..S':'optative,future,active,3rd person singular',
                                'OPA2..P':'optative,present,active,2nd person plural', 'OPA2..S':'optative,present,active,2nd person singular',
                                    'OPA3..P':'optative,present,active,3rd person plural', 'OPA3..S':'optative,present,active,3rd person singular',
                                'OPM1..S':'optative,present,middle,1st person singular',
                                    'OPM3..P':'optative,present,middle,3rd person plural', 'OPM3..S':'optative,present,middle,3rd person singular',
                                'PAA.AFP':'participle,aorist,active,accusative,feminine,plural', 'PAA.AFS':'participle,aorist,active,accusative,feminine,singular',
                                    'PAA.AMP':'participle,aorist,active,accusative,masculine,plural', 'PAA.AMS':'participle,aorist,active,accusative,masculine,singular',
                                    'PAA.ANP':'participle,aorist,active,accusative,neuter,plural', 'PAA.ANS':'participle,aorist,active,accusative,neuter,singular',
                                    'PAA.DFP':'participle,aorist,active,dative,feminine,plural', 'PAA.DFS':'participle,aorist,active,dative,feminine,singular',
                                    'PAA.DMP':'participle,aorist,active,dative,masculine,plural', 'PAA.DMS':'participle,aorist,active,dative,masculine,singular',
                                    'PAA.DNS':'participle,aorist,active,dative,neuter,singular',
                                    'PAA.GFS':'participle,aorist,active,genitive,feminine,singular',
                                    'PAA.GMP':'participle,aorist,active,genitive,masculine,plural', 'PAA.GMS':'participle,aorist,active,genitive,masculine,singular',
                                    'PAA.GNP':'participle,aorist,active,genitive,neuter,plural', 'PAA.GNS':'participle,aorist,active,genitive,neuter,singular',
                                    'PAA.NFP':'participle,aorist,active,nominative,feminine,plural', 'PAA.NFS':'participle,aorist,active,nominative,feminine,singular',
                                    'PAA.NMP':'participle,aorist,active,nominative,masculine,plural', 'PAA.NMS':'participle,aorist,active,nominative,masculine,singular',
                                    'PAA.NNP':'participle,aorist,active,nominative,neuter,plural', 'PAA.NNS':'participle,aorist,active,nominative,neuter,singular',
                                'PAM.AFS':'participle,aorist,middle,accusative,feminine,singular',
                                    'PAM.AMP':'participle,aorist,middle,accusative,masculine,plural', 'PAM.AMS':'participle,aorist,middle,accusative,masculine,singular',
                                    'PAM.ANP':'participle,aorist,middle,accusative,neuter,plural', 'PAM.ANS':'participle,aorist,middle,accusative,neuter,singular',
                                    'PAM.DMP':'participle,aorist,middle,dative,masculine,plural',
                                    'PAM.DNP':'participle,aorist,middle,dative,neuter,plural',
                                    'PAM.GFP':'participle,aorist,middle,genitive,feminine,plural', 'PAM.GFS':'participle,aorist,middle,genitive,feminine,singular',
                                    'PAM.GMP':'participle,aorist,middle,genitive,masculine,plural', 'PAM.GMS':'participle,aorist,middle,genitive,masculine,singular',
                                    'PAM.GNP':'participle,aorist,middle,genitive,neuter,plural', 'PAM.GNS':'participle,aorist,middle,genitive,neuter,singular',
                                    'PAM.NFP':'participle,aorist,middle,nominative,feminine,plural', 'PAM.NFS':'participle,aorist,middle,nominative,feminine,singular',
                                    'PAM.NMP':'participle,aorist,middle,nominative,masculine,plural', 'PAM.NMS':'participle,aorist,middle,nominative,masculine,singular',
                                    'PAM.NNS':'participle,aorist,middle,nominative,neuter,singular',
                                'PAP.AFS':'participle,aorist,passive,accusative,feminine,singular',
                                    'PAP.AMP':'participle,aorist,passive,accusative,masculine,plural', 'PAP.AMS':'participle,aorist,passive,accusative,masculine,singular',
                                    'PAP.ANP':'participle,aorist,passive,accusative,neuter,plural', 'PAP.ANS':'participle,aorist,passive,accusative,neuter,singular',
                                    'PAP.DFP':'participle,aorist,passive,dative,feminine,plural', 'PAP.DFS':'participle,aorist,passive,dative,feminine,singular',
                                    'PAP.DMS':'participle,aorist,passive,dative,masculine,singular',
                                    'PAP.DNP':'participle,aorist,passive,dative,neuter,plural', 'PAP.DNS':'participle,aorist,passive,dative,neuter,singular',
                                    'PAP.GFP':'participle,aorist,passive,genitive,feminine,plural', 'PAP.GFS':'participle,aorist,passive,genitive,feminine,singular',
                                    'PAP.GMP':'participle,aorist,passive,genitive,masculine,plural', 'PAP.GMS':'participle,aorist,passive,genitive,masculine,singular',
                                    'PAP.GNP':'participle,aorist,passive,genitive,neuter,plural', 'PAP.GNS':'participle,aorist,passive,genitive,neuter,singular',
                                    'PAP.NFP':'participle,aorist,passive,nominative,feminine,plural', 'PAP.NFS':'participle,aorist,passive,nominative,feminine,singular',
                                    'PAP.NMP':'participle,aorist,passive,nominative,masculine,plural', 'PAP.NMS':'participle,aorist,passive,nominative,masculine,singular',
                                    'PAP.NNP':'participle,aorist,passive,nominative,neuter,plural', 'PAP.NNS':'participle,aorist,passive,nominative,neuter,singular',
                                'PEA.AFS':'participle,perfect,active,accusative,feminine,singular',
                                    'PEA.AMP':'participle,perfect,active,accusative,masculine,plural', 'PEA.AMS':'participle,perfect,active,accusative,masculine,singular',
                                    'PEA.ANP':'participle,perfect,active,accusative,neuter,plural', 'PEA.ANS':'participle,perfect,active,accusative,neuter,singular',
                                    'PEA.DFP':'participle,perfect,active,dative,feminine,plural',
                                    'PEA.DMP':'participle,perfect,active,dative,masculine,plural', 'PEA.DMS':'participle,perfect,active,dative,masculine,singular',
                                    'PEA.DNS':'participle,perfect,active,dative,neuter,singular',
                                    'PEA.GFS':'participle,perfect,active,genitive,feminine,singular',
                                    'PEA.GMP':'participle,perfect,active,genitive,masculine,plural', 'PEA.GMS':'participle,perfect,active,genitive,masculine,singular',
                                    'PEA.GNP':'participle,perfect,active,genitive,neuter,plural',
                                    'PEA.NFP':'participle,perfect,active,nominative,feminine,plural', 'PEA.NFS':'participle,perfect,active,nominative,feminine,singular',
                                    'PEA.NMP':'participle,perfect,active,nominative,masculine,plural', 'PEA.NMS':'participle,perfect,active,nominative,masculine,singular',
                                    'PEA.NNP':'participle,perfect,active,nominative,neuter,plural', 'PEA.NNS':'participle,perfect,active,nominative,neuter,singular',
                                'PEM.AFS':'participle,perfect,middle,accusative,feminine,singular',
                                    'PEM.AMP':'participle,perfect,middle,accusative,masculine,plural', 'PEM.AMS':'participle,perfect,middle,accusative,masculine,singular',
                                    'PEM.ANS':'participle,perfect,middle,accusative,neuter,singular',
                                    'PEM.DFP':'participle,perfect,middle,dative,feminine,plural',
                                    'PEM.DMP':'participle,perfect,middle,dative,masculine,plural', 'PEM.DMS':'participle,perfect,middle,dative,masculine,singular',
                                    'PEM.DNS':'participle,perfect,middle,dative,neuter,singular',
                                    'PEM.GFS':'participle,perfect,middle,genitive,feminine,singular',
                                    'PEM.GMP':'participle,perfect,middle,genitive,masculine,plural',
                                    'PEM.GNP':'participle,perfect,middle,genitive,neuter,plural',
                                    'PEM.NFS':'participle,perfect,middle,nominative,feminine,singular',
                                    'PEM.NMP':'participle,perfect,middle,nominative,masculine,plural', 'PEM.NMS':'participle,perfect,middle,nominative,masculine,singular',
                                'PEP.AFP':'participle,perfect,passive,accusative,feminine,plural', 'PEP.AFS':'participle,perfect,passive,accusative,feminine,singular',
                                    'PEP.AMS':'participle,perfect,passive,accusative,masculine,singular', 'PEP.AMP':'participle,perfect,passive,accusative,masculine,plural',
                                    'PEP.ANP':'participle,perfect,passive,accusative,neuter,plural', 'PEP.ANS':'participle,perfect,passive,accusative,neuter,singular',
                                    'PEP.DFS':'participle,perfect,passive,dative,feminine,singular',
                                    'PEP.DNP':'participle,perfect,passive,dative,neuter,plural', 'PEP.DNS':'participle,perfect,passive,dative,neuter,singular',
                                    'PEP.DMP':'participle,perfect,passive,dative,masculine,plural', 'PEP.DMS':'participle,perfect,passive,dative,masculine,singular',
                                    'PEP.GFP':'participle,perfect,passive,genitive,feminine,plural', 'PEP.GFS':'participle,perfect,passive,genitive,feminine,singular',
                                    'PEP.GMP':'participle,perfect,passive,genitive,masculine,plural', 'PEP.GMS':'participle,perfect,passive,genitive,masculine,singular',
                                    'PEP.GNP':'participle,perfect,passive,genitive,neuter,plural', 'PEP.GNS':'participle,perfect,passive,genitive,neuter,singular',
                                    'PEP.NFP':'participle,perfect,passive,nominative,feminine,plural', 'PEP.NFS':'participle,perfect,passive,nominative,feminine,singular',
                                    'PEP.NMP':'participle,perfect,passive,nominative,masculine,plural', 'PEP.NMS':'participle,perfect,passive,nominative,masculine,singular',
                                    'PEP.NNP':'participle,perfect,passive,nominative,neuter,plural', 'PEP.NNS':'participle,perfect,passive,nominative,neuter,singular',
                                    'PEP.VFS':'participle,perfect,passive,vocative,feminine,singular',
                                    'PEP.VMP':'participle,perfect,passive,vocative,masculine,plural', 'PEP.VMS':'participle,perfect,passive,vocative,masculine,singular',
                                    'PEP.VNS':'participle,perfect,passive,vocative,neuter,singular',
                                'PFA.AMP':'participle,future,active,accusative,masculine,plural', 'PFA.AMS':'participle,future,active,accusative,masculine,singular',
                                    'PFA.ANP':'participle,future,active,accusative,neuter,plural',
                                    'PFA.GMP':'participle,future,active,genitive,masculine,plural',
                                    'PFA.NMP':'participle,future,active,nominative,masculine,plural', 'PFA.NMS':'participle,future,active,nominative,masculine,singular',
                                'PFM.AMP':'participle,future,middle,accusative,masculine,plural', 'PFM.AMS':'participle,future,middle,accusative,masculine,singular',
                                    'PFM.ANP':'participle,future,middle,accusative,neuter,plural', 'PFM.ANS':'participle,future,middle,accusative,neuter,singular',
                                    'PFM.NMP':'participle,future,middle,nominative,masculine,plural', 'PFM.NMS':'participle,future,middle,nominative,masculine,singular',
                                'PFP.GNP':'participle,future,passive,genitive,neuter,plural',
                                'PPA.AFP':'participle,present,active,accusative,feminine,plural', 'PPA.AFS':'participle,present,active,accusative,feminine,singular',
                                    'PPA.AMP':'participle,present,active,accusative,masculine,plural', 'PPA.AMS':'participle,present,active,accusative,masculine,singular',
                                    'PPA.ANP':'participle,present,active,accusative,neuter,plural', 'PPA.ANS':'participle,present,active,accusative,neuter,singular',
                                    'PPA.DFP':'participle,present,active,dative,feminine,plural', 'PPA.DFS':'participle,present,active,dative,feminine,singular',
                                    'PPA.DMP':'participle,present,active,dative,masculine,plural', 'PPA.DMS':'participle,present,active,dative,masculine,singular',
                                    'PPA.DNP':'participle,present,active,dative,neuter,plural', 'PPA.DNS':'participle,present,active,dative,neuter,singular',
                                    'PPA.GFP':'participle,present,active,genitive,feminine,plural', 'PPA.GFS':'participle,present,active,genitive,feminine,singular',
                                        'PPA.GMP':'participle,present,active,genitive,masculine,plural', 'PPA.GMS':'participle,present,active,genitive,masculine,singular',
                                        'PPA.GNP':'participle,present,active,genitive,neuter,plural', 'PPA.GNS':'participle,present,active,genitive,neuter,singular',
                                    'PPA.NFP':'participle,present,active,nominative,feminine,plural', 'PPA.NFS':'participle,present,active,nominative,feminine,singular',
                                    'PPA.NMP':'participle,present,active,nominative,masculine,plural', 'PPA.NMS':'participle,present,active,nominative,masculine,singular',
                                    'PPA.NNP':'participle,present,active,nominative,neuter,plural', 'PPA.NNS':'participle,present,active,nominative,neuter,singular',
                                    'PPA.VFS':'participle,present,active,vocative,feminine,singular',
                                    'PPA.VMP':'participle,present,active,vocative,masculine,plural', 'PPA.VMS':'participle,present,active,vocative,masculine,singular',
                                'PPM.AFP':'participle,present,middle,accusative,feminine,plural', 'PPM.AFS':'participle,present,middle,accusative,feminine,singular',
                                    'PPM.AMP':'participle,present,middle,accusative,masculine,plural', 'PPM.AMS':'participle,present,middle,accusative,masculine,singular',
                                    'PPM.ANP':'participle,present,middle,accusative,neuter,plural', 'PPM.ANS':'participle,present,middle,accusative,neuter,singular',
                                    'PPM.DFP':'participle,present,middle,dative,feminine,plural', 'PPM.DFS':'participle,present,middle,dative,feminine,singular',
                                    'PPM.DMP':'participle,present,middle,dative,masculine,plural', 'PPM.DMS':'participle,present,middle,dative,masculine,singular',
                                    'PPM.DNP':'participle,present,middle,dative,neuter,plural', 'PPM.DNS':'participle,present,middle,dative,neuter,singular',
                                    'PPM.GFP':'participle,present,middle,genitive,feminine,plural', 'PPM.GFS':'participle,present,middle,genitive,feminine,singular',
                                    'PPM.GMP':'participle,present,middle,genitive,masculine,plural', 'PPM.GMS':'participle,present,middle,genitive,masculine,singular',
                                    'PPM.GNP':'participle,present,middle,genitive,neuter,plural', 'PPM.GNS':'participle,present,middle,genitive,neuter,singular',
                                    'PPM.NFP':'participle,present,middle,nominative,feminine,plural', 'PPM.NFS':'participle,present,middle,nominative,feminine,singular',
                                    'PPM.NMP':'participle,present,middle,nominative,masculine,plural', 'PPM.NMS':'participle,present,middle,nominative,masculine,singular',
                                    'PPM.NNP':'participle,present,middle,nominative,neuter,plural', 'PPM.NNS':'participle,present,middle,nominative,neuter,singular',
                                    'PPM.VMP':'participle,present,middle,vocative,masculine,plural', 'PPM.VMS':'participle,present,middle,vocative,masculine,singular',
                                'PPP.AFP':'participle,present,passive,accusative,feminine,plural', 'PPP.AFS':'participle,present,passive,accusative,feminine,singular',
                                    'PPP.AMP':'participle,present,passive,accusative,masculine,plural', 'PPP.AMS':'participle,present,passive,accusative,masculine,singular',
                                    'PPP.ANP':'participle,present,passive,accusative,neuter,plural', 'PPP.ANS':'participle,present,passive,accusative,neuter,singular',
                                    'PPP.DFS':'participle,present,passive,dative,feminine,singular',
                                    'PPP.DMP':'participle,present,passive,dative,masculine,plural', 'PPP.DMS':'participle,present,passive,dative,masculine,singular',
                                    'PPP.DNP':'participle,present,passive,dative,neuter,plural', 'PPP.DNS':'participle,present,passive,dative,neuter,singular',
                                    'PPP.GFS':'participle,present,passive,genitive,feminine,singular',
                                    'PPP.GMP':'participle,present,passive,genitive,masculine,plural', 'PPP.GMS':'participle,present,passive,genitive,masculine,singular',
                                    'PPP.GNP':'participle,present,passive,genitive,neuter,plural', 'PPP.GNS':'participle,present,passive,genitive,neuter,singular',
                                    'PPP.NFP':'participle,present,passive,nominative,feminine,plural', 'PPP.NFS':'participle,present,passive,nominative,feminine,singular',
                                    'PPP.NMP':'participle,present,passive,nominative,masculine,plural', 'PPP.NMS':'participle,present,passive,nominative,masculine,singular',
                                    'PPP.NNP':'participle,present,passive,nominative,neuter,plural', 'PPP.NNS':'participle,present,passive,nominative,neuter,singular',
                                'SAA1..P':'subjunctive,aorist,active,1st person plural', 'SAA1..S':'subjunctive,aorist,active,1st person singular',
                                'SAA2..P':'subjunctive,aorist,active,2nd person plural', 'SAA2..S':'subjunctive,aorist,active,2nd person singular',
                                'SAA3..P':'subjunctive,aorist,active,3rd person plural', 'SAA3..S':'subjunctive,aorist,active,3rd person singular',
                                'SAM1..P':'subjunctive,aorist,middle,1st person plural', 'SAM1..S':'subjunctive,aorist,middle,1st person singular',
                                    'SAM2..P':'subjunctive,aorist,middle,2nd person plural', 'SAM2..S':'subjunctive,aorist,middle,2nd person singular',
                                    'SAM3..P':'subjunctive,aorist,middle,3rd person plural', 'SAM3..S':'subjunctive,aorist,middle,3rd person singular',
                                'SAP1..P':'subjunctive,aorist,passive,1st person plural', 'SAP1..S':'subjunctive,aorist,passive,1st person singular',
                                    'SAP2..P':'subjunctive,aorist,passive,2nd person plural', 'SAP2..S':'subjunctive,aorist,passive,2nd person singular',
                                    'SAP3..P':'subjunctive,aorist,passive,3rd person plural', 'SAP3..S':'subjunctive,aorist,passive,3rd person singular',
                                'SEA1..P':'subjunctive,perfect,active,1st person plural', 'SEA1..S':'subjunctive,perfect,active,1st person singular',
                                    'SEA2..S':'subjunctive,perfect,active,2nd person singular',
                                    'SEA3..P':'subjunctive,perfect,active,3rd person plural',
                                'SPA1..P':'subjunctive,present,active,1st person plural', 'SPA1..S':'subjunctive,present,active,1st person singular',
                                    'SPA2..P':'subjunctive,present,active,2nd person plural', 'SPA2..S':'subjunctive,present,active,2nd person singular',
                                    'SPA3..P':'subjunctive,present,active,3rd person plural', 'SPA3..S':'subjunctive,present,active,3rd person singular',
                                'SPM1..P':'subjunctive,present,middle,1st person plural', 'SPM1..S':'subjunctive,present,middle,1st person singular',
                                    'SPM2..P':'subjunctive,present,middle,2nd person plural', 'SPM2..S':'subjunctive,present,middle,2nd person singular',
                                    'SPM3..P':'subjunctive,present,middle,3rd person plural', 'SPM3..S':'subjunctive,present,middle,3rd person singular',
                                'SPP1..P':'subjunctive,present,passive,1st person plural', 'SPP1..S':'subjunctive,present,passive,1st person singular',
                                    'SPP2..P':'subjunctive,present,passive,2nd person plural',
                                    'SPP3..P':'subjunctive,present,passive,3rd person plural', 'SPP3..S':'subjunctive,present,passive,3rd person singular',
                                }
for morphologyCode,morphologyDescription in CNTR_MORPHOLOGY_NAME_DICT.items():
    if '1' in morphologyCode: assert '1st person,' in morphologyDescription or '1st person ' in morphologyDescription, f"{morphologyCode=}"
    if '2' in morphologyCode: assert '2nd person,' in morphologyDescription or '2nd person ' in morphologyDescription
    if '3' in morphologyCode: assert '3rd person,' in morphologyDescription or '3rd person ' in morphologyDescription
    if '.S' in morphologyCode: assert ',singular' in morphologyDescription or ' singular' in morphologyDescription
    if '.P' in morphologyCode: assert ',plural' in morphologyDescription or ' plural' in morphologyDescription
    if morphologyCode.startswith('I'): assert morphologyDescription.startswith('indicative,')
    if morphologyCode.startswith('M'): assert morphologyDescription.startswith('imperative,')
    if morphologyCode.startswith('N') and len(morphologyCode)>3: assert morphologyDescription.startswith('infinitive,')
    if morphologyCode.startswith('P'): assert morphologyDescription.startswith('participle,')
    if 'aorist' in morphologyDescription: assert 'A' in morphologyCode, f"{morphologyCode=}"
    if 'imperfect' in morphologyDescription: assert 'I' in morphologyCode, f"{morphologyCode=}"
    if 'imperative' in morphologyDescription: assert morphologyCode.startswith('M'), f"{morphologyCode=}"
    if 'infinitive' in morphologyDescription: assert morphologyCode.startswith('N'), f"{morphologyCode=}"
    if ',perfect' in morphologyDescription: assert 'E' in morphologyCode, f"{morphologyCode=}"
    if 'present' in morphologyDescription: assert 'P' in morphologyCode
    if 'nominative,' in morphologyDescription: assert 'N' in morphologyCode, f"{morphologyCode=}"
    if 'accusative,' in morphologyDescription: assert 'A' in morphologyCode, f"{morphologyCode=}"
    if 'dative,' in morphologyDescription: assert 'D' in morphologyCode, f"{morphologyCode=}"
    if 'genitive,' in morphologyDescription: assert 'G' in morphologyCode, f"{morphologyCode=}"
    if 'vocative,' in morphologyDescription: assert 'V' in morphologyCode, f"{morphologyCode=}"
    if ',feminine' in morphologyDescription: assert 'F' in morphologyCode, f"{morphologyCode=}"
    if ',masculine' in morphologyDescription: assert 'M' in morphologyCode, f"{morphologyCode=}"
    if ',neuter' in morphologyDescription: assert 'N' in morphologyCode, f"{morphologyCode=}"
    if morphologyCode.endswith('S'): assert morphologyDescription.endswith(',singular') or morphologyDescription.endswith(' singular')
    if morphologyCode.endswith('P'): assert morphologyDescription.endswith(',plural') or morphologyDescription.endswith(' plural')
    assert list(CNTR_MORPHOLOGY_NAME_DICT.values()).count(morphologyDescription) == 1, f"{morphologyDescription=}"
# See https://www.publiconsulting.com/wordpress/ancientgreek/chapter/16-prepositions/ for a concise list
KNOWN_GREEK_PREFIXES = ('a','amfi','ana','anti','apo','arχ',
            'dia','eis','ek','en','epi','ex',
            'huper','hupo','kata','meta',
            'para','peri','pro','pros',
            'sun') # In the LEMMA character set

# See https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html
OSHB_POS_DICT = { 'A':'adjective', 'C':'conjunction', 'D':'adverb', 'N':'noun', 'P':'pronoun',
                  'R':'preposition', 'S':'suffix', 'T':'particle', 'V':'verb',
                  'x':'(unknown)' }
OSHB_NOUN_DICT = { 'N':'noun',
                   'Nc':'common_noun', 'Ng':'noun_(gentilic)', 'Np':'proper_noun', 
                   'Nx':'noun_(unknown_type)' }
OSHB_ADJECTIVE_DICT = { # 'A':'adjective',
                        'Aa':'adjective', 'Ac':'adjective_(cardinal_number)', 'Ag':'adjective_(gentilic)', 'Ao':'adjective_(ordinal_number)',
                        'Ax':'adjective_(unknown_type)' }
OSHB_HEBREW_VERB_STEM_DICT = { # 'V':'verb',
                  # Hebrew verb stems
                   'Vq':'qal_verb', 'VN':'niphal_verb', 'Vp':'piel_verb', 'VP':'pual_verb', 'Vh':'hiphil_verb', 'VH':'hophal_verb', 'Vt':'hithpael_verb',
                   'Vo':'polel_verb', 'VO':'polal_verb', 'Vr':'hithpolel_verb', 'Vm':'poel_verb', 'VM':'poel_verb', 'Vk':'pael_verb', 'VK':'pulal_verb',
                   'VQ':'qal_passive_verb', 'Vl':'pilpel_verb', 'VL':'polpal_verb', 'Vf':'hithpalpel_verb', 'VD':'nithpael_verb', 'Vj':'pealal_verb',
                   'Vi':'pilel_verb', 'Vu':'hothpaal', 'Vc':'tiphil_verb', 'Vv':'hishtaphel_verb', 'Vw':'nithpael_verb', 'Vy':'nithpoel_verb', 'Vz':'hithpoel_verb',
                   'Vx':'verb_(unknown_stem)' }
OSHB_ARAMAIC_VERB_STEM_DICT = { # 'V':'verb',
                  # Aramaic verb stems
                   'Vq':'peal_verb', 'VQ':'peil_verb', 'Vu':'hithpeel_verb', 'Vp':'pael_verb', 'VP':'ithpaal_verb', 'VM':'hithpaal_verb',
                   'Va':'aphel_verb', 'Vh':'haphel_verb', 'Vs':'shaphel_verb', 'Ve':'shaphel_verb', 'VH':'hophal_verb', 'Vi':'ithpeel_verb', 'Vt':'hishtaphel_verb',
                   'Vv':'ishtaphel_verb', 'Vw':'hithaphel_verb', 'Vo':'polel_verb', 'Vz':'ithpoel_verb', 'Vr':'hithpolel_verb', 'Vf':'hithpalpel_verb',
                   'Vb':'hephal_verb', 'Vc':'tiphel', 'Vm':'poel_verb', 'Vl':'palpel_verb', 'VL':'ithpalpel_verb', 'VO':'ithpolel_verb', 'VG':'ittaphal_verb',
                   'Vx':'verb_(unknown_stem)' }
OSHB_VERB_CONJUGATION_TYPE_DICT = { # 'V':'verb',
                    'p':'perfect_(<i>qatal</i>)', 'q':'sequential_perfect_(<i>weqatal</i>)', 'i':'imperfect_(<i>yiqtol</i>)', 'w':'sequential_imperfect_(<i>wayyiqtol</i>)',
                    'h':'cohortative', 'j':'jussive', 'v':'imperative', 'r':'active_participle', 's':'passive_participle', 'a':'infinitive_absolute', 'c':'infinitive_construct' }
OSHB_PRONOUN_DICT = { 'Pd':'demonstrative_pronoun', 'Pf':'indefinite_pronoun', 'Pi':'interrogative_pronoun', 'Pp':'personal_pronoun', 'Pr':'relative_pronoun' }
OSHB_PARTICLE_DICT = { 'T':'particle',
                       'Ta':'affirmation_particle', 'Td':'definite_article', 'Te':'exhortation_particle', 'Ti':'interrogative_particle', 'Tj':'interjection_particle',
                       'Tm':'demonstrative_particle', 'Tn':'negative_particle', 'To':'direct_object_marker', 'Tr':'relative_particle' }
OSHB_PREPOSITION_DICT = { 'R':'preposition', 'Rd':'preposition_with_definite_article' }
OSHB_SUFFIX_DICT = { 'Sd':'directional_<i>he</i>_suffix', 'Sh':'paragogic_<i>he</i>_suffix', 'Sn':'paragogic_<i>nun</i>_suffix', 'Sp':'pronominal_suffix' }
OSHB_VERB_CONJUGATION_TYPE_DICT = { # 'V':'verb',
                    'p':'perfect_(<i>qatal</i>)', 'q':'sequential_perfect_(<i>weqatal</i>)', 'i':'imperfect_(<i>yiqtol</i>)', 'w':'sequential_imperfect_(<i>wayyiqtol</i>)',
                    'h':'cohortative', 'j':'jussive', 'v':'imperative', 'r':'active_participle', 's':'passive_participle', 'a':'infinitive_absolute', 'c':'infinitive_construct' }
OSHB_PERSON_DICT = { '1':'first', '2':'second', '3':'third',
                     'x':'(unknown)' }
OSHB_GENDER_DICT = { 'b':'both', # for nouns
                     'c':'common', # for verbs
                     'f':'feminine', 'm':'masculine',
                     'x':'(unknown)' }
OSHB_NUMBER_DICT = { 'd':'dual', 'p':'plural', 's':'singular',
                     'x':'(unknown)' }
OSHB_STATE_DICT = { 'a':'absolute', 'c':'construct', 'd':'determined' }

LC_FACSIMILE_PAGE_INDEX = { # from https://openlibrary.org/books/OL24998735M/The_Leningrad_Codex
    # Can be used in links https://archive.org/details/Leningrad_Codex/page/n{value-1}/mode/1up
    # Books of Moses:
    'GEN':7, 'EXO':67, 'LEV':117, 'NUM':151, 'DEU':201, 'MosesMasorah':244,
    # Prophets:
    'JOS':247, 'JDG':276, 'SA1':304, 'SA2':341, 'KI1':372, 'KI2':409,
    'ISA':445, 'JER':495, 'EZE':557,
    'HOS':612, 'JOL':619, 'AMO':622, 'OBA':628, 'JNA':629, 'MIC':631, 'NAH':635, 'HAB':637, 'ZEP':639, 'HAG':641, 'ZEC':643, 'MAL':653,
    'ProphetsMasorah':656,
    # Writings:
    'CH1':659, 'CH2':693,
    'PSA':736, 'JOB':798, 'PRO':823,
    'RUT':846, 'SNG':850, 'ECC':854, 'LAM':864, 'EST':869, 'DAN':879, 'EZR':899, 'NEH':912,
    'WritingsMasorah':930,
    'ArtisticDesigns':952,
    'SongOfTheVine':986 # (Moses ben Asher’s original composition)
    }

COMMON_ENGLISH_WORDS_LIST = ( # Ignore the most common words
    'God','Jesus','Lord', 'Joshua',
    'a','an','the','¬the','that','this','which','¬which','these','those',
    'and','for','but','if','as','therefore','in_order_that','because','so','then',
    'also','again','just',
    'here','there',
    'some','any',
    'to','from','unto', 'with', 'in','out', 'by','on','upon','into','of','at', 'up','down', 'before','after', 'under','over',
    'not','all',
    'what','who',
    'you', 'he','we','they','I','she','you_all','it',
            'him','us','them','me','her',
    'your','his','our','their','my','its',
    'will','was','would','be','been','is','am','are','have','has','had','having','do','did','does','doing','can','may','let',
    'won\'t','didn\'t','don\'t',
    'I\'ll','we\'ll',
    'one', # Especially for LV
    'very',
    'say','saying','said','go','came','went', 'get','put',
    )
assert len(set(COMMON_ENGLISH_WORDS_LIST)) == len(COMMON_ENGLISH_WORDS_LIST) # No duplicates
SIMILAR_GLOSS_WORDS_TABLE = [
    # Each line (tuple) contains two tuples:
    #   The first is a list of words for existing glosses
    #   The second is a list of other glosses to also display as synonyms
    # NOTE: The glosses are the original VLT glosses -- not our adjusted OET-LV glosses
    # NOTE: Reversals are not automatic -- they have to be manually entered
    (('ancestor','ancestors'),('patriarch','patriarchs','elders')),
    (('anger',),('wrath',)),
    (('barley',),('grain','wheat')),
    (('blessed',),('blessing','blessings','bless','blesses','cursed')),
    (('boat','boats'),('ship','ships')),
    (('body','bodies'),('flesh',)),
    (('chief_priest','chief_priests'),('priest','priests')),
    (('child','children'),('son','sons','daughter','daughters')),
    (('clean',),('moral','permissible','pure','unclean')),
    (('coin','coins'),('money','silver')),
    (('cry','cries','crying','cried'),('weep','weeps','weeping','weeped','mourn','mourns','mourning','mourned')),
    (('daughter','daughters'),('child','children')),
    (('devil',),('Satan',)),
    (('disbelief',),('unbelief','disbelieve')),
    (('door','doors'),('doorway','doorways','gate','gates')),
    (('doorway','doorways'),('door','doors','gate','gates')),
    (('dread',),('fear','terror')),
    (('enlighten','enlightened','enlightening'),('light','illuminate','illuminated','illuminating')),
    (('fear',),('dread','terror')),
    (('few',),('remnant','remainder')),
    (('flesh',),('body','bodies','carnal','meat')),
    (('fleshly',),('worldly',)),
    (('fulfilment','fulfillment'),('fullness',)),
    (('fullness',),('fulfillment','fulfilment')),
    (('gate','gates'),('door','doors','doorway','doorways')),
    (('gift','gifts'),('reward','rewards')),
    (('glorious',),('honoured','honored','glory')),
    (('glory',),('honour','honor','glorious')),
    (('grain',),('wheat','barley')),
    (('heart','hearts'),('mind','minds')),
    (('holiness',),('purity',)),
    (('house_servant','house_servants'),('servant','servants','attendant','attendants','slave','slaves')),
    (('illuminate','illuminated','illuminating'),('light','enlighten','enlightened','enlightening')),
    (('immediately',),('suddenly',)),
    (('Jesus',),('Joshua','Yeshua')),
    (('joined_together',),('united',)),
    (('Joshua',),('Jesus','Yeshua')),
    (('lamp','lamps'),('light','lights')),
    (('law','laws'),('statute','statutes','regulation','regulations')),
    (('logical',),('sensible','logic','logically')),
    (('light','lights'),('lamp','lamps')),
    (('lip','lips'),('mouth','mouths')),
    (('mind','minds'),('heart','hearts')),
    (('money',),('silver','coin','coins')),
    (('mourn','mourns','mourning','mourned'),('weep','weeps','weeping','weeped','cry','cries','crying','cried')),
    (('mouth','mouths'),('lips','lip','tongue')),
    (('pagan','pagans'),('Gentile','Gentiles','Greeks')),
    (('path','paths'),('way','ways','road','roads')),
    (('patriach','patriarchs'),('ancestor','ancestors','elders')),
    (('priest','priests'),('chief_priest','chief_priests')),
    (('purity',),('holiness',)),
    (('regulation','regulations'),('law','laws','statute','statutes')),
    (('remnant',),('remainder','few')),
    (('reward','rewards'),('gift','gifts')),
    (('riches',),('wealth',)),
    (('road','roads'),('path','paths','way','ways')),
    (('Sabbath','Sabbaths'),('week','weeks','rest')),
    (('Satan',),('devil',)),
    (('scroll','scrolls'),('book','books','scipture','scriptures')),
    (('seed',),('sperm',)),
    (('servant','servants'),('slave','slaves','house_servant','house_servants','attendant','attendants')),
    (('ship','ships'),('boat','boats')),
    (('silver',),('money','coin','coins')),
    (('slave','slaves'),('servant','house_servant','servants','house_servants','attendant','attendants')),
    (('son','sons'),('child','children')),
    (('sperm',),('seed',)),
    (('statute','statutes'),('law','laws','regulation','regulations')),
    (('suddenly',),('immediately',)),
    (('terror',),('dread','fear')),
    (('unclean',),('immoral','prohibited','impure','clean')),
    (('united',),('joined_together',)),
    (('way','ways'),('path','paths','road','roads')),
    (('week','weeks'),('Sabbath','Sabbaths')),
    (('wealth',),('riches',)),
    (('weep','weeps''weeping','weeped'),('cry','cries','crying','cried','mourn','mourns','mourning','mourned')),
    (('wheat',),('grain','barley')),
    (('whence',),('therefore','accordingly','consequently')),
    (('worldly',),('fleshly',)),
    (('wrath',),('anger',)),
    ]
SIMILAR_GLOSS_WORDS_DICT = {} # We create this dict at load time as we check the above table
for firstWords,similarWords in SIMILAR_GLOSS_WORDS_TABLE:
    assert isinstance(firstWords,tuple) and isinstance(similarWords,tuple)
    for firstWord in firstWords:
        assert isinstance( firstWord, str )
        assert firstWord not in similarWords # No duplicates
        assert firstWord not in SIMILAR_GLOSS_WORDS_DICT # No duplicates
        fwList = list( firstWords )
        fwList.remove( firstWord )
        otherFirstWords = tuple( fwList )
        expandedSimilarWords = otherFirstWords + similarWords
        SIMILAR_GLOSS_WORDS_DICT[firstWord] = otherFirstWords + similarWords
    for similarWord in similarWords:
        assert isinstance( similarWord, str )
        assert similarWords.count(similarWord) == 1 # No duplicates
CONTRASTIVE_GLOSS_WORDS_TABLE = [
    # Each line (tuple) contains two tuples:
    #   The first is a list of words for existing glosses
    #   The second is a list of other glosses to also display as antonyms
    # NOTE: The glosses are the VLT glosses -- not our adjusted OET-LV glosses
    # NOTE: Reversals are not automatic -- they have to be manually entered
    (('sprinkle','sprinkled','sprinkling'),('baptize','baptized','baptizing')), (('baptize','baptized','baptizing'),('sprinkle','sprinkled','sprinkling')),
    (('dark','darkness'),('light',)), (('light',),('dark','darkness')),
    (('hot',),('cold',)), (('cold',),('hot',)),
    (('sexual_intercourse',),('homosexuals',)), (('homosexuals',),('sexual_intercourse',)), # both based on lemma koitē
    ]
CONTRASTIVE_GLOSS_WORDS_DICT = {} # We create this dict at load time as we check the above table
for firstWords,contrastiveWords in CONTRASTIVE_GLOSS_WORDS_TABLE:
    assert isinstance(firstWords,tuple) and isinstance(contrastiveWords,tuple)
    for firstWord in firstWords:
        assert isinstance( firstWord, str )
        assert firstWord not in contrastiveWords # No duplicates
        assert firstWord not in CONTRASTIVE_GLOSS_WORDS_DICT # No duplicates
        fwList = list( firstWords )
        fwList.remove( firstWord )
        otherFirstWords = tuple( fwList )
        expandedSimilarWords = otherFirstWords + contrastiveWords
        CONTRASTIVE_GLOSS_WORDS_DICT[firstWord] = otherFirstWords + contrastiveWords
    for contrastiveWord in contrastiveWords:
        assert isinstance( contrastiveWord, str )
        assert contrastiveWords.count(contrastiveWord) == 1 # No duplicates



def createOETReferencePages( level:int, outputFolderPath:Path, state:State ) -> bool:
    """
    Make pages for all the words and lemmas to link to.

    Sadly, there's almost identical code in make_table_pages() in OET convert_OET-LV_to_simple_HTML.py
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"createOETReferencePages( {level}, {outputFolderPath}, {state.BibleVersions} )" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nCreating {'TEST ' if TEST_MODE else ''}reference pages for OET…" )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Preprocessing word forms for OET…" )
    # Here we create our Dicts and Lists that we'll make the reference pages from
    # First make a list of each place the same Greek word (and matching morphology) is used
    state.OETRefData['OTFormUsageDict'], state.OETRefData['OTLemmaRowNumbersDict'] = defaultdict(list), defaultdict(list)
    state.OETRefData['OTWordRowNumbersDict'] = defaultdict(list)
    # state.OETRefData['OTLemmaFormsDict'] = defaultdict(set)
    state.OETRefData['OTFormOETGlossesDict'] = defaultdict(set)
    state.OETRefData['OTLemmaOETGlossesDict'] = defaultdict(set)
    state.OETRefData['OTLemmasForRootDict'] = defaultdict(set)
    state.OETRefData['OETOTGlossWordDict'] = defaultdict(list)
    state.OETRefData['OTLemmaGlossDict'] = {}
    # startTime = time()
    preprocessHebrewWordsLemmasGlosses( [], state ) # Ignores these ones
    # if TEST_MODE: vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      preprocessHebrewWordsLemmasGlosses() took {(time()-startTime)/60:.2f} minutes.")
    startTime = time()
    create_Hebrew_word_pages( level+1, outputFolderPath.joinpath( 'HebWrd/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Hebrew_word_pages() took {(time()-startTime)/60:.1f} minutes.")
    startTime = time()
    create_Hebrew_lemma_pages( level+1, outputFolderPath.joinpath( 'HebLem/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Hebrew_lemma_pages() took {(time()-startTime)/60:.1f} minutes.")
    del state.OETRefData['OTFormUsageDict'], state.OETRefData['OTLemmaRowNumbersDict'], state.OETRefData['OTWordRowNumbersDict']
    del state.OETRefData['OTFormOETGlossesDict'], state.OETRefData['OTLemmaOETGlossesDict'], state.OETRefData['OTLemmasForRootDict']
    del state.OETRefData['OETOTGlossWordDict'], state.OETRefData['OTLemmaGlossDict']

    state.OETRefData['NTFormUsageDict'], state.OETRefData['NTLemmaDict'] = defaultdict(list), defaultdict(list)
    state.OETRefData['NTLemmaFormsDict'] = defaultdict(set)
    state.OETRefData['NTFormOETGlossesDict'], state.OETRefData['NTFormVLTGlossesDict'] = defaultdict(set), defaultdict(set)
    state.OETRefData['NTLemmaOETGlossesDict'], state.OETRefData['NTLemmaVLTGlossesDict'] = defaultdict(set), defaultdict(set)
    state.OETRefData['OETNTGlossWordDict'], state.OETRefData['VLTGlossWordDict'] = defaultdict(list), defaultdict(list)
    state.OETRefData['NTGreekLemmaDict'] = {}
    # NOTE: The word table has Matthew at the beginning (whereas the OET places John and Mark at the beginning) so we do them first
    # startTime = time()
    preprocessGreekWordsLemmasGlosses( 'JHN', state ) # Only processes this book
    preprocessGreekWordsLemmasGlosses( 'MRK', state )
    preprocessGreekWordsLemmasGlosses( ['JHN','MRK'], state ) # Ignores these ones
    # if TEST_MODE: vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      preprocessGreekWordsLemmasGlosses() took {(time()-startTime)/60:.2f} minutes.")
    startTime = time()
    create_Greek_word_pages( level+1, outputFolderPath.joinpath( 'GrkWrd/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Greek_word_pages() took {(time()-startTime)/60:.1f} minutes.")
    startTime = time()
    create_Greek_lemma_pages( level+1, outputFolderPath.joinpath( 'GrkLem/' ), state )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"      create_Greek_lemma_pages() took {(time()-startTime)/60:.1f} minutes.")

    create_person_pages( level+1, outputFolderPath.joinpath( 'Per/' ), state )
    create_location_pages( level+1, outputFolderPath.joinpath( 'Loc/' ), state )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'referenceIndex', None, state) \
            .replace( '__TITLE__', f"OpenBibleData Reference Contents{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, reference' )
    indexHtml = f'''{top}
<h1 id="Top">Reference lists contents page</h1>
<h2>{SITE_NAME}</h2>
<p class="note"><a href="HebWrd/">Hebrew words index</a> <a href="HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="HebLem/">Hebrew lemmas index</a> <a href="HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="GrkWrd/">Greek words index</a> <a href="GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="GrkLem/">Greek lemmas index</a> <a href="GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="Per/">Bible people index</a></p>
<p class="note"><a href="Loc/">Bible locations index</a></p>
{makeBottom( level, 'referenceIndex', state )}'''
    checkHtml( 'referenceIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    del state.OETRefData # No longer needed
    return True
# end of createOETReferencePages.createOETReferencePages


HebrewWordFileName = 'OET-LV_OT_word_table.tsv'
def preprocessHebrewWordsLemmasGlosses( BBBSelection:Union[str, List[str]], state ) -> bool:
    """
    Makes all the lists and indexes of words, lemmas, and glosses
        to be used in words and lemma pages.

    If the first parameter is a string (BBB), only process that book.
    If the first parameter is a list (BBBs), ignore all those books.

    All results are written into lists and dicts in state.
    """
    if isinstance( BBBSelection, str ):
        processBBB = BBBSelection
        ignoreBBBs = BOOKLIST_OT39.remove( processBBB )
        assert BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( processBBB )
    else:
        assert isinstance( BBBSelection, list )
        processBBB = None
        ignoreBBBs = BBBSelection

    # morphemeFileName = 'OET-LV_OT_morpheme_table.tsv'
    lemmaFileName = 'OET-LV_OT_lemma_table.tsv'

    with open( os.path.join(state.preloadedBibles['OET-LV'].OTsourceFolder, lemmaFileName), 'rt', encoding='UTF-8' ) as lemmaTSVfile:
        lemmaFileText = lemmaTSVfile.read()
    if lemmaFileText.startswith( BibleOrgSysGlobals.BOM ):
        logging.info( f"loadESFMWordFile: Detected UTF-16 Byte Order Marker in {lemmaFileName}" )
        lemmaFileText = lemmaFileText[1:] # Remove the Unicode Byte Order Marker (BOM)
    state.OETRefData['OTLemmaFullRowTable'] = lemmaFileText.rstrip( '\n' ).split( '\n' ) # Remove any blank line at the end then split
    # state.OETRefData['OTLemmaGlossDict'] = {lemmaLine.split('\t')[0]:lemmaLine.split('\t')[1] for lemmaLine in state.OETRefData['OTLemmaFullRowTable'][1:]}
    # assert len(state.OETRefData['OTLemmaGlossDict']) == len(state.OETRefData['OTLemmaFullRowTable']) - 1 # So no duplicate/overwritten entries
    state.OETRefData['OTLemmaGlossDict'] = {}
    for lemmaLine in state.OETRefData['OTLemmaFullRowTable'][1:]: # Don't use a dict comprehension because we need to detect duplicates
        lemmaHebrewKey,lemmaGlossesValue = lemmaLine.split('\t')
        vowellessLemma = removeHebrewVowelPointing( lemmaHebrewKey )
        # print( f"{lemmaHebrewKey=} {vowellessLemma=} {lemmaGlossesValue=} from {lemmaLine=}")
        for char in lemmaHebrewKey:
            assert 'ACCENT' not in unicodedata.name(char), f"{unicodedata.name(char)=} {lemmaHebrewKey=} {lemmaGlossesValue=}"
        assert lemmaHebrewKey not in state.OETRefData['OTLemmaGlossDict']
        state.OETRefData['OTLemmaGlossDict'][lemmaHebrewKey] = lemmaGlossesValue
        state.OETRefData['OTLemmasForRootDict'][vowellessLemma].add( lemmaHebrewKey )
    state.OETRefData['OTHebLemmaList'] = [lemmaLine.split('\t')[0] for lemmaLine in state.OETRefData['OTLemmaFullRowTable']]
    state.OETRefData['OTTransLemmaList'] = [transliterate_Hebrew(hebLemma) for hebLemma in state.OETRefData['OTHebLemmaList']]
    # print( f"{len(state.OETRefData['OTLemmaFullRowTable'])=} {len(state.OETRefData['OTLemmaGlossDict'])=}" )

    # with open( os.path.join(state.preloadedBibles['OET-LV'].OTsourceFolder, morphemeFileName), 'rt', encoding='UTF-8' ) as morphemeTSVfile:
    #     morphemeFileText = morphemeTSVfile.read()
    # if morphemeFileText.startswith( BibleOrgSysGlobals.BOM ):
    #     logging.info( f"loadESFMWordFile: Detected UTF-16 Byte Order Marker in {morphemeFileName}" )
    #     morphemeFileText = morphemeFileText[1:] # Remove the Unicode Byte Order Marker (BOM)
    # state.OETRefData['OTLemmaFullRowTable'] = morphemeFileText.rstrip( '\n' ).split( '\n' ) # Remove any blank line at the end then split
    # # Uses less memory to keep the rows as single strings, rather than separating the columns at the tabs now

    started = False
    for n, columns_string in enumerate( state.OETRefData['word_tables'][HebrewWordFileName][1:], start=1 ):
        if (processBBB is not None and columns_string.startswith(processBBB)) \
        or (processBBB is None and columns_string[:3] not in ignoreBBBs):
            started = True
            _ref, rowType, _morphemeRowList, lemmaRowList, strongs, morphology, _word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tags = columns_string.split( '\t' )
            gloss = contextualWordGloss if contextualWordGloss else wordGloss if wordGloss else contextualMorphemeGlosses if contextualMorphemeGlosses else morphemeGlosses
            formMorph2Tuple = (noCantillations, morphology)
            state.OETRefData['OTFormUsageDict'][formMorph2Tuple].append( n )
            state.OETRefData['OTLemmaRowNumbersDict'][noCantillations] = []
            # print( f"{lemmaRowList=}" )
            for lemmaRowNumberStr in lemmaRowList.split( ',' ):
                # if 'MISSING' in lemmaRowNumberStr: continue
                try:
                    lemmaRowNumber = int( lemmaRowNumberStr )
                    state.OETRefData['OTLemmaRowNumbersDict'][noCantillations].append( lemmaRowNumber )
                    state.OETRefData['OTWordRowNumbersDict'][lemmaRowNumber].append( n )
                except ValueError: pass
            # print( f"{_word=} {noCantillations=} {_morphemeRowList=} {lemmaRowList=} {state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]=}" )
            # for lrn in state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]: print( f"  {lrn=}: {state.OETRefData['OTWordRowNumbersDict'][lrn]=}")
            # if noCantillations == 'נִין': halt
            # else:
            #     state.OETRefData['OTLemmaRowNumbersDict'][noCantillations].append( n )
            #     state.OETRefData['OTLemmaFormsDict'][noCantillations].add( formMorph2Tuple )
            if gloss:
                state.OETRefData['OTFormOETGlossesDict'][formMorph2Tuple].add( gloss )
                state.OETRefData['OTLemmaOETGlossesDict'][noCantillations].add( gloss )
                if gloss != 'DOM':
                    adjGloss = ( gloss.replace( '\\untr DOM\\untr*', '' ).replace( 'DOM', '' )
                                    .replace( '\\nd ', '' ).replace( '\\nd*', '' )
                                    .replace( '_~_', ' ' )
                                    .replace( '(cmp)', '' )
                                    .replace( '[s]', '' ).replace( '[es]', '' )
                                    .replace( '(ms)', '' ).replace( '(m)', '' ).replace( '(fs)', '' )
                                    .replace( '//', ' ' ).replace( '/', ' ' ).replace( '_', ' ' ).replace( '=', ' ' ).replace( ',', ' ' )
                                    .replace( '[', ' ' ).replace( ']', ' ' ).replace( '(', ' ' ).replace( ')', ' ' )
                                    .replace( '   ', ' ' ).replace( '  ', ' ' ).strip() )
                    if adjGloss:
                        for someGlossWord in adjGloss.split( ' ' ):
                            assert someGlossWord, f"{someGlossWord=} {gloss=} {adjGloss=}"
                            if someGlossWord not in COMMON_ENGLISH_WORDS_LIST:
                                # print( f"{n} {_ref} {someGlossWord=} from {gloss=}")
                                # assert n not in state.OETRefData['OETOTGlossWordDict'][someGlossWord] # There are some rare instances like the=time//this_time
                                state.OETRefData['OETOTGlossWordDict'][someGlossWord].append( n )
            # if noCantillations in state.OETRefData['OTHebrewLemmaDict']:
            #     # assert state.OETRefData['NTGreekLemmaDict'][noCantillations] == GrkLemma, f"{n=} {_ref} {noCantillations=} {GrkLemma=} {state.OETRefData['NTGreekLemmaDict'][SRLemma]=}"
            #     if state.OETRefData['OTHebrewLemmaDict'][noCantillations] != GrkLemma:
            #         dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {noCantillations=} {GrkLemma=} {state.OETRefData['OTHebrewLemmaDict'][noCantillations]=}" )
            # state.OETRefData['OTHebrewLemmaDict'][noCantillations] = noCantillations
        elif processBBB and started:
            break # Must have already finished the desired book(s)

    return True
# end of createOETReferencePages.preprocessHebrewWordsLemmasGlosses


GreekWordFileName = 'OET-LV_NT_word_table.tsv'
def preprocessGreekWordsLemmasGlosses( BBBSelection:Union[str, List[str]], state ) -> bool:
    """
    Makes all the lists and indexes of words, lemmas, and glosses
        to be used in words and lemmas pages.

    If the first parameter is a string (BBB), only process that book.
    If the first parameter is a list (BBBs), ignore all those books.

    Concerning glosses, it handles both the OET adjusted glosses
        and also the original VLT glosses for comparison.

    All results are written into lists and dicts in state.
    """
    if isinstance( BBBSelection, str ):
        processBBB = BBBSelection
        ignoreBBBs = BOOKLIST_NT27.remove( processBBB )
        assert BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( processBBB )
    else:
        assert isinstance( BBBSelection, list )
        processBBB = None
        ignoreBBBs = BBBSelection

    started = False
    for n, columns_string in enumerate( state.OETRefData['word_tables'][GreekWordFileName][1:], start=1 ):
        if (processBBB is not None and columns_string.startswith(processBBB)) \
        or (processBBB is None and columns_string[:3] not in ignoreBBBs):
            started = True
            _ref, greekWord, SRLemma, GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                OETFormattedGlossWords = formatNTSpansGlossWords( OETGlossWordsStr )
                VLTFormattedGlossWords = formatNTSpansGlossWords( VLTGlossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['NTFormUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['NTLemmaDict'][SRLemma].append( n )
                state.OETRefData['NTLemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['NTFormOETGlossesDict'][formMorph3Tuple].add( OETFormattedGlossWords )
                state.OETRefData['NTFormVLTGlossesDict'][formMorph3Tuple].add( VLTFormattedGlossWords )
                state.OETRefData['NTLemmaOETGlossesDict'][SRLemma].add( OETFormattedGlossWords )
                state.OETRefData['NTLemmaVLTGlossesDict'][SRLemma].add( VLTFormattedGlossWords )
                for someGlossWord in OETGlossWordsStr.split( ' ' ):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['OETNTGlossWordDict'][someGlossWord]
                        state.OETRefData['OETNTGlossWordDict'][someGlossWord].append( n )
                for someGlossWord in VLTGlossWordsStr.split( ' ' ):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['VLTGlossWordDict'][someGlossWord]
                        state.OETRefData['VLTGlossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['NTGreekLemmaDict']:
                    # assert state.OETRefData['NTGreekLemmaDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['NTGreekLemmaDict'][SRLemma]=}"
                    if state.OETRefData['NTGreekLemmaDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['NTGreekLemmaDict'][SRLemma]=}" )
                state.OETRefData['NTGreekLemmaDict'][SRLemma] = GrkLemma
        elif processBBB and started:
            break # Must have already finished the desired book(s)

    return True
# end of createOETReferencePages.preprocessGreekWordsLemmasGlosses


forward_slash_regex = re.compile( '[a-zⱪō]/[a-zA-Z[(]')
def formatNTSpansGlossWords( glossWords:str ) -> str:
    """
    Put HTML spans about the various parts of the gloss Words string
        to replace our pre, helper, and post special character markers.
    """
    # Because we have entries like 'Mōsaʸs/(Mosheh)', 'apprentices/followers', and 'chosen_one/messiah',
    #   we can get messed up with glossHelper spans
    adjustedGlossWords = glossWords
    if glossWords.count('/') in (1,3,5):
        while (match := forward_slash_regex.search( adjustedGlossWords )):
            # print( f"Found match {match} in {adjustedGlossWords=}")
            adjustedGlossWords = f'{adjustedGlossWords[:match.start()+1]}__SLASH__{adjustedGlossWords[match.end()-1:]}'
            # print( f"{adjustedGlossWords=}" ); halt
    assert adjustedGlossWords.count('/') in (0,2,4), f"{adjustedGlossWords=} from {glossWords=}"

    result = adjustedGlossWords \
                .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 ) \
                .replace('\\sup ','<sup>').replace('\\sup*','</sup>')
    assert result.count('<span ') == result.count('</span>'), f"{result=} from {glossWords=}"
    assert result.count('<sup>') == result.count('</sup>'), f"{result=} from {glossWords=}"
    return result.replace( '__SLASH__', '/' )
# end of createOETReferencePages.formatNTSpansGlossWords


NUM_BEFORE_AND_AFTER = 3
def formatNTContextSpansOETGlossWords( rowNum:int, state:State ) -> str:
    """
    Get this and previous gloss words in context.

    TODO: Need to take GlossOrder into account
    """
    # NT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )

    fOriginalWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, _fVLTGlossWords, fOETGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_tables'][GreekWordFileName][rowNum].split( '\t' )
    # print( f"formatNTContextSpansOETGlossWords( {rowNum:,} ) at {fOriginalWordRef}" )
    fOriginalBCV = fOriginalWordRef.split( 'w', 1 )[0]

    glossWordsList = [f'<b>{formatNTSpansGlossWords(fOETGlossWords)}</b>']

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN -= 1
        if fN < 1: break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, _fVLTGlossWords, fOETGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_tables'][GreekWordFileName][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability == 'None': fProbability = None
        if fProbability and fOETGlossWords[0]!='¬':
            glossWordsList.insert( 0, formatNTSpansGlossWords(fOETGlossWords) )
            rowCount += 1

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN += 1
        if fN >= len(state.OETRefData['word_tables'][GreekWordFileName]): break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, _fVLTGlossWords, fOETGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_tables'][GreekWordFileName][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability == 'None': fProbability = None
        if fProbability and fOETGlossWords[0]!='¬':
            glossWordsList.append( formatNTSpansGlossWords(fOETGlossWords) )
            rowCount += 1

    result = ' '.join( glossWordsList ).replace('\\sup ','<sup>').replace('\\sup*','</sup>')
    assert result.count('<span ') == result.count('</span>'), f"{result=} from {glossWordsList=}"
    assert result.count('<sup>') == result.count('</sup>'), f"{result=} from {glossWordsList=}"
    return result
# end of createOETReferencePages.formatNTContextSpansOETGlossWords


used_word_filenames = []
def create_Hebrew_word_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Hebrew_word_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Checking/Making {len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,} Hebrew word pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    def tidy_Hebrew_word_gloss( engGloss:str ) -> str:
        """
        """
        assert '<span class="ul">' not in engGloss # already
        result = engGloss \
            .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>') \
            .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>') \
            .replace( '_', '<span class="ul">_</span>')
        return result
    # end of createOETReferencePages.tidy_Hebrew_word_gloss

    def tidy_Hebrew_morphology( tHM_rowType:str, tHM_morphology:str ) -> str:
        """
        """
        tHM_tidyMorphologyField = ''
        for tHM_individualMorphology in tHM_morphology.split( ',' ):
            if tHM_individualMorphology:
                tHM_tidyMorphology = tHM_individualMorphology
                tHM_tidyMorphologyField = f'''{tHM_tidyMorphologyField}{'<br> ' if tHM_tidyMorphologyField else ''}<small><a title="Learn more about OSHB morphology" href="https://hb.OpenScriptures.org/HomeFiles/Morph.html">Morphology</a>=<a title="See OSHB morphology codes" href="https://hb.OpenScriptures.org/parsing/HebrewMorphologyCodes.html">{tHM_tidyMorphology}</a></small>'''
                # print( f"{ref} got '{hebrewWord}' morphology ({len(individualMorphology)}) = '{individualMorphology}' (from ({len(morphology)}) '{morphology}')" )
                tHM_PoS = tHM_individualMorphology[0] # individualMorphology is variable length, depending on the PoS, etc.
                tHM_PoS_with_type = tHM_individualMorphology[:2] # Two characters
                # posField = f'PoS=<b>{OSHB_POS_DICT[PoS]}</b>'
                tHM_word_details_field = ''
                if tHM_PoS == 'N': # noun
                    assert len(tHM_individualMorphology) in (2, 5)
                    noun_type = OSHB_NOUN_DICT[tHM_PoS_with_type]
                    tHM_word_details_field = f'PoS=<b>{noun_type}</b>'
                    if len(tHM_individualMorphology) > 2:
                        tHM_word_details_field = f'{tHM_word_details_field} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[2]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[3]]} State={OSHB_STATE_DICT[tHM_individualMorphology[4]]}'

                elif tHM_PoS == 'V': # verb: Generally verbs require no state. Participles, on the other hand, require no person, though they do take a state.
                    assert 3 <= len(tHM_individualMorphology) <= 7
                    # try:
                    verb_type = OSHB_ARAMAIC_VERB_STEM_DICT[tHM_PoS_with_type] if 'A' in tHM_rowType else OSHB_HEBREW_VERB_STEM_DICT[tHM_PoS_with_type]
                    # except KeyError: # 'Va'
                    #     print( f"Why did tidy_Hebrew_morphology({morphology}) fail with {rowType=} {PoS_with_type=} ???")
                    #     verb_type = f'UNKNOWN {PoS_with_type=}'
                    tHM_word_details_field = f'PoS=<b>{verb_type}</b> Type={OSHB_VERB_CONJUGATION_TYPE_DICT[tHM_individualMorphology[2]]}'
                    if len(tHM_individualMorphology) == 6:
                        if tHM_individualMorphology[2] in 'rs': # active or passive PARTICIPLE (has no person field but does have a state)
                            tHM_word_details_field = f'{tHM_word_details_field} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[3]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[4]]} State={OSHB_STATE_DICT[tHM_individualMorphology[5]]}'
                        else:
                            tHM_word_details_field = f'{tHM_word_details_field} Person={OSHB_PERSON_DICT[tHM_individualMorphology[3]]} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[4]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[5]]}'
                    elif len(tHM_individualMorphology) == 7: # then we have a state as well
                        tHM_word_details_field = f'{tHM_word_details_field} Person={OSHB_PERSON_DICT[tHM_individualMorphology[3]]} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[4]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[5]]} State={OSHB_STATE_DICT[tHM_individualMorphology[6]]}'
                    elif len(tHM_individualMorphology) == 3:
                        assert tHM_individualMorphology[2] in 'ac' # infinitive absolute or construct
                        # We've already got the verb + stem + conjugation type above

                elif tHM_PoS == 'A': # adjective
                    assert len(tHM_individualMorphology) == 5
                    adjective_type = OSHB_ADJECTIVE_DICT[tHM_PoS_with_type]
                    tHM_word_details_field = f'PoS=<b>{adjective_type}</b> Gender={OSHB_GENDER_DICT[tHM_individualMorphology[2]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[3]]} State={OSHB_STATE_DICT[tHM_individualMorphology[4]]}'
                elif tHM_PoS == 'P': # pronoun: person, gender, number and state are the same wherever they apply.
                    assert 2 <= len(tHM_individualMorphology) <= 5
                    pronoun_type = OSHB_PRONOUN_DICT[tHM_PoS_with_type]
                    tHM_word_details_field = f'PoS=<b>{pronoun_type}</b>'
                    if len(tHM_individualMorphology) > 2:
                        tHM_word_details_field = f'{tHM_word_details_field} Person={OSHB_PERSON_DICT[tHM_individualMorphology[2]]} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[3]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[4]]}'
                elif tHM_PoS == 'T': # particle
                    if len(tHM_individualMorphology) == 1: # e.g., at Aramaic DAN_4:12w11
                        tHM_word_details_field = f'PoS=<b>particle</b>'
                    else:
                        assert len(tHM_individualMorphology) == 2
                        particle_type = OSHB_PARTICLE_DICT[tHM_PoS_with_type]
                        tHM_word_details_field = f'PoS=<b>{particle_type}</b>'
                elif tHM_PoS == 'R': # preposition: the preposition type is only used when the inseparable preposition is pointed in such a way to indicate the presence of the definite article.
                    assert 1 <= len(tHM_individualMorphology) <= 2, f"'{tHM_PoS}' ({len(tHM_individualMorphology)}) {tHM_individualMorphology=}"
                    tHM_word_details_field = f'PoS=<b>{OSHB_PREPOSITION_DICT[tHM_PoS_with_type]}</b>' if len(tHM_individualMorphology)==2 else f'PoS=<b>{OSHB_POS_DICT[tHM_PoS]}</b>'
                elif tHM_PoS == 'S': # suffix
                    assert 2 <= len(tHM_individualMorphology) <= 5
                    suffix_type = OSHB_SUFFIX_DICT[tHM_PoS_with_type]
                    tHM_word_details_field = f'PoS=<b>{suffix_type}</b>'
                    if len(tHM_individualMorphology) > 2:
                        tHM_word_details_field = f'{tHM_word_details_field} Person={OSHB_PERSON_DICT[tHM_individualMorphology[2]]} Gender={OSHB_GENDER_DICT[tHM_individualMorphology[3]]} Number={OSHB_NUMBER_DICT[tHM_individualMorphology[4]]}'
                else:
                    if tHM_PoS in ('C','D'): # conjunction or adverb
                        assert len(tHM_individualMorphology) == 1 # We only have the PoS
                    tHM_word_details_field = f'PoS=<b>{OSHB_POS_DICT[tHM_PoS]}</b>'
                tHM_tidyMorphologyField = f'''{'Aramaic ' if 'A' in tHM_rowType else ''}{tHM_tidyMorphologyField} {tHM_word_details_field}'''
            else: # individualMorphology is blank (AMO_6:14w14)
                tHM_tidyMorphologyField = '(MISSING)'
                tHM_word_details_field = '(NONE)'
        return tHM_tidyMorphologyField
    # end of createOETReferencePages.tidy_Hebrew_morphology

    # Now make a page for each Hebrew word (including the note pages)
    numWordPagesMade = 0
    wordLinksForIndex:List[str] = [] # Used below to make an index page
    state.OETRefData['usedHebLemmas'] = set() # Used in next function to make lemma pages
    for n, columns_string in enumerate( state.OETRefData['word_tables'][HebrewWordFileName][1:], start=1 ):
        if not columns_string: continue # a blank line (esp. at end)
        # print( f"Word {n}: {columns_string}" )
        usedRoleLetters, usedMorphologies = set(), set()
        output_filename = getHebrewWordpageFilename( n, state )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: # NOTE: This makes the function MUCH slower
            # Check that we're not creating any duplicate filenames (that will then be overwritten)
            assert output_filename not in used_word_filenames, f"Hebrew {n} {output_filename}"
            used_word_filenames.append( output_filename )
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        ref, rowType, morphemeRowList, lemmaRowList, strongs, morphology, word, noCantillations, morphemeGlosses, contextualMorphemeGlosses, wordGloss, contextualWordGloss, glossCapitalisation, glossPunctuation, glossOrder, glossInsert, role, nesting, tags = columns_string.split( '\t' )

        BBB, CVW = ref.split( '_', 1 )
        if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and BBB not in TEST_BOOK_LIST:
            continue # In some test modes, we only make the relevant word pages
        C, VW = CVW.split( ':', 1 )
        V, W = VW.split( 'w', 1 ) if 'w' in VW else (VW, '') # Segs and Notes don't have word numbers
        ourTidyBBB = getOETTidyBBB( BBB )
        ourTidyBBBwithNotes = getOETTidyBBB( BBB, addNotes=True )
        ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
        ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
        OSISbookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )

        isMultipleLemmas = ',' in lemmaRowList
        # print( f"{ref} '{rowType}' ({lemmaRowList}) got '{word}' ({noCantillations}) morphology='{morphology}'" )
        hebrewWord = (noCantillations.replace( ',', '' ) # Remove morpheme breaks
                        if noCantillations else word ) # Segs and notes have nothing in the noCantillations field
        wordGloss = wordGloss.replace( '=', '_' )
        gloss = tidy_Hebrew_word_gloss( contextualWordGloss if contextualWordGloss else wordGloss if wordGloss else contextualMorphemeGlosses if contextualMorphemeGlosses else morphemeGlosses )
        if isMultipleLemmas:
            if contextualMorphemeGlosses:
                mainGlossWord = sorted(contextualMorphemeGlosses.replace('/',',').split( ',' ), key=len)[-1]
                # print( f"{ref} {mainGlossWord=} fromA {contextualMorphemeGlosses}" )
            elif morphemeGlosses:
                mainGlossWord = sorted(morphemeGlosses.replace('/',',').split( ',' ), key=len)[-1]
                # print( f"{ref} {mainGlossWord=} fromB {morphemeGlosses}" )
            else: mainGlossWord = gloss
        else: mainGlossWord = gloss

        tidyMorphologyField = translationField = capsField = ''
        if rowType!='seg' and 'note' not in rowType:
            # it's a proper Hebrew (or Aramaic) word
            assert morphemeRowList.count(',') == strongs.count(',') == morphology.count(',') == word.count(',') == noCantillations.count(',')
            tidyMorphologyField = tidy_Hebrew_morphology( rowType, morphology )

            if gloss:
                translationField = f'''‘{gloss[0].upper() if glossCapitalisation=='S' else gloss[0]}{gloss[1:]}’'''.replace(',',', ')
            else:
                translationField = "<small>Oops, no gloss available!</small>"
                logging.error( f"create_Hebrew_word_pages: {ref} {rowType} No gloss available for '{word}'" )
            if glossCapitalisation:
                capsField = f' <small>(Caps={glossCapitalisation})</small>'

        transliterationBit = f" ({transliterate_Hebrew(noCantillations.replace(',',', '))})" if noCantillations else ''

        strongsLinks = ''
        for originalStrongsBit in strongs.split( ',' ):
            possibleStrongsNumber = originalStrongsBit
            if ' ' in possibleStrongsNumber:
                if possibleStrongsNumber[-2] == ' ' and possibleStrongsNumber[-1] in 'abcdef':
                    possibleStrongsNumber = possibleStrongsNumber[:-2] # Remove suffix
                else:
                    logging.critical( f"create_Hebrew_word_pages {BBB} {C}:{V}w{W} {gloss=} {possibleStrongsNumber=} from {strongs=}" )
            if possibleStrongsNumber.isdigit():
                strongsLinks = f'''{strongsLinks}{', ' if strongsLinks else ''}<a title="Goes to Strongs dictionary" href="https://BibleHub.com/hebrew/{possibleStrongsNumber}.htm">{originalStrongsBit}</a>'''
            elif possibleStrongsNumber: # things like c, m, or b
                strongsLinks = f'''{strongsLinks}{', ' if strongsLinks else ''}{originalStrongsBit}'''
        StrongsBit = f' Strongs={strongsLinks}' if strongsLinks else ''

        # Add pointers to people, locations, etc.
        # semanticExtras = nominaSacraField
        # if tagsStr:
        #     for semanticTag in tagsStr.split( ';' ):
        #         tagPrefix, tag = semanticTag[0], semanticTag[1:]
        #         # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
        #         if tagPrefix == 'P':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../Per/{tag}.htm#Top">{tag}</a>'''
        #         elif tagPrefix == 'L':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../Loc/{tag}.htm#Top">{tag}</a>'''
        #         elif tagPrefix == 'Y':
        #             year = tag
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Year={year}{' AD' if int(year)>0 else ''}'''
        #         elif tagPrefix == 'T':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}TimeSeries={tag}'''
        #         elif tagPrefix == 'E':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Event={tag}'''
        #         elif tagPrefix == 'G':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Group={tag}'''
        #         elif tagPrefix == 'F':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Referred to from <a title="Go to referent word" href="{tag}.htm#Top">Word #{tag}</a>'''
        #         elif tagPrefix == 'R':
        #             semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Refers to <a title="Go to referred word" href="{tag}.htm#Top">Word #{tag}</a>'''
        #         else:
        #             logging.critical( f"Unknown '{tagPrefix}' word tag in {n}: {columns_string}")
        #             unknownTag
        lemmaLinksList = []
        for lemmaRowNumberStr in lemmaRowList.split( ',' ):
            # print( f"{lemmaRowNumberStr=}" )
            try: lemmaRowNumber = int(lemmaRowNumberStr)
            except ValueError: continue # could be empty string or '<<<MISSING>>>'
            lemmaHebrew = state.OETRefData['OTHebLemmaList'][lemmaRowNumber]
            state.OETRefData['usedHebLemmas'].add( lemmaHebrew ) # Used in next function to make lemma pages
            lemmaTrans = state.OETRefData['OTTransLemmaList'][lemmaRowNumber]
            lemmaLinksList.append( f'<a title="View Hebrew lemma" href="../HebLem/{lemmaTrans}.htm#Top">‘{lemmaHebrew}’</a>' )
        lemmaLinksStr = ( f'''Lemmas=<b>{', '.join(lemmaLinksList)}</b>''' if isMultipleLemmas else f'Lemma=<b>{lemmaLinksList[0]}</b>' ) if lemmaLinksList else ''
        # print( f"{len(state.OETRefData['OTLemmaOETGlossesDict'])=} {noCantillations=} {state.OETRefData['OTLemmaOETGlossesDict'][noCantillations]=}")
        lemmaGlossesList = sorted( state.OETRefData['OTLemmaOETGlossesDict'][noCantillations] )
        try: lemmaGlossesList.remove( '' ) # TODO: Check how this gets in there
        except ValueError: pass
        # print( f"{len(lemmaGlossesList)=}"); halt
        wordOETGlossesList = sorted( state.OETRefData['OTFormOETGlossesDict'][(hebrewWord,morphology)] )
        # wordVLTGlossesList = sorted( state.OETRefData['OTFormVLTGlossesDict'][(hebrewWord,morphology)] )

        prevN = nextN = None
        if n > 1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for nN in range( n-1, 0, -1 ):
                    nWordRef = state.OETRefData['word_tables'][HebrewWordFileName][nN].split( '\t', 1 )[0]
                    nBBB = nWordRef.split( '_', 1 )[0]
                    if nBBB in TEST_BOOK_LIST:
                        prevN = nN
                        break
            else: prevN = n-1
        if n<len(state.OETRefData['word_tables'][HebrewWordFileName])-1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for nN in range( n+1, len(state.OETRefData['word_tables'][HebrewWordFileName]) ):
                    nWordRef = state.OETRefData['word_tables'][HebrewWordFileName][nN].split( '\t', 1 )[0]
                    nBBB = nWordRef.split( '_', 1 )[0]
                    if nBBB in TEST_BOOK_LIST:
                        nextN = nN
                        break
            else: nextN = n+1
        prevLink = f'<b><a title="Previous word" href="{getHebrewWordpageFilename(prevN,state)}#Top">←</a></b> ' if prevN else ''
        nextLink = f' <b><a title="Next word" href="{getHebrewWordpageFilename(nextN,state)}#Top">→</a></b>' if nextN else ''
        oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbbWithNotes}{NARROW_NON_BREAK_SPACE}{C}</a>'''
        parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
        interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}ilr/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
        rowTypeField = 'Ketiv (marginal note)' if rowType=='K' else 'Segment punctuation' if rowType=='seg' else rowType.title() if rowType else ''
        wordsHtml = f'''<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Hebrew wordlink #{n}</h1>{f"{NEWLINE}<h2>{rowTypeField}</h2>" if rowTypeField else ''}
<p class="pNav">{prevLink}<b>{hebrewWord}</b> <a title="Go to Hebrew word index" href="index.htm">↑</a>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
<p class="link"><a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={OSISbookCode}&c={C}&v={V}">OSHB {ourTidyBbbWithNotes} {C}:{V}</a>
 <b>{hebrewWord}</b>{transliterationBit} {translationField}{capsField if TEST_MODE else ''}{StrongsBit} {lemmaLinksStr}<br> {tidyMorphologyField}<br>  </p>
<p class="note"><small>Note: These word pages enable you to click through to the <a href="https://hb.OpenScriptures.org">Open Scriptures Hebrew Bible</a> (OSHB) that the <em>Open English Translation</em> Old Testament is translated from.
The OSHB is based on the <a href="https://www.Tanach.us/Tanach.xml">Westminster Leningrad Codex</a> (WLC).
(We are still searching for a digitized facsimile of the Leningradensis manuscript that we can easily link to. See <a href="https://www.AnimatedHebrew.com/mss/index.html#leningrad">this list</a> and <a href="https://archive.org/details/Leningrad_Codex/">this archive</a> for now.)
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>'''
        assert '\\' not in wordsHtml, f"{wordsHtml=}"
        assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"

        other_count = 0
        thisWordNumberList = state.OETRefData['OTFormUsageDict'][(hebrewWord,morphology)]
        if len(wordOETGlossesList)>1:
            wordGlossesStr = tidy_Hebrew_word_gloss( "</b>’, ‘<b>".join(wordOETGlossesList) )
        if len(thisWordNumberList) > 100: # too many to list
            maxWordsToShow = 50
            wordsHtml = f'{wordsHtml}\n<h2>Showing the first {maxWordsToShow} out of ({len(thisWordNumberList)-1:,}) uses of identical word form {hebrewWord} <small>({tidyMorphologyField})</small> in the Hebrew originals</h2>'
            if len(wordOETGlossesList)>1:
                wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordGlossesStr}</b>’.</p>'''
                # if wordVLTGlossesList != wordOETGlossesList:
                #     wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
            else:
                # assert wordOETGlossesList == [gloss], f"{wordOETGlossesList}  vs {[gloss]}"
                wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> is always and only glossed as ‘<b>{gloss}</b>’.</p>'
                # if VLTGlossWordsStr != gloss:
                #     wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> was always and only glossed as ‘<b>{VLTGlossWordsStr}</b>’)</small>.</p>'
        else: # we can list all uses of the word
            maxWordsToShow = 100
            if len(thisWordNumberList) == 1:
                wordsHtml = f'{wordsHtml}\n<h2>Only use of identical word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> in the Hebrew originals</h2>'
                # hebLemmaWordRowsList = state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]
                # lemmaFormsList = sorted( state.OETRefData['OTLemmaFormsDict'][noCantillations] )
                # if len(hebLemmaWordRowsList) == 1:
                #     # print( f"{ref} '{hebrew}' ({glossWords}) {noCantillations=} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}" )
                #     assert len(lemmaFormsList) == 1
                #     assert len(morphemeGlossesList) == 1
                #     html = f'''{html.replace(morphemeLink, f'{morphemeLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Hebrew originals.</p>'''
            else:
                wordsHtml = f'{wordsHtml}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {hebrewWord} <small>({tidyMorphologyField})</small> in the Hebrew originals</h2>'
            if len(wordOETGlossesList)>1:
                wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordGlossesStr}</b>’.</p>'''
                # if wordVLTGlossesList != wordOETGlossesList:
                #     wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
            else:
                # assert wordOETGlossesList == [gloss], f"{n} {BBB} {C}:{V} {hebrewWord=} {morphology=}: {wordOETGlossesList}  vs {[gloss]}"
                wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> is always and only glossed as ‘<b>{gloss}</b>’.</p>'
                # if formattedVLTGlossWords != gloss:
                #     wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In the VLT, the word form ‘{hebrewWord}’ <small>({tidyMorphologyField})</small> was always and only glossed as ‘<b>{formattedVLTGlossWords}</b>’)</small>.</p>'
        displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
        for oN in thisWordNumberList:
            if oN==n: continue # don't duplicate the word we're making the page for
            # print( f"HERE: ({len(state.OETRefData['word_tables'][wordFileName][oN].split( TAB ))}) {state.OETRefData['word_tables'][wordFileName][oN]}")
            oWordRef, oRowType, oMorphemeRowList, oLemmaRowList, oStrongs, oMorphology, oWord, oNoCantillations, oMorphemeGlosses, oContextualMorphemeGlosses, oWordGloss, oContextualWordGloss, oGlossCapitalisation, oGlossPunctuation, oGlossOrder, oGlossInsert, oRole, oNesting, oTags = state.OETRefData['word_tables'][HebrewWordFileName][oN].split( '\t' )
            oHebrewWord = (oNoCantillations.replace( ',', '' ) # Remove morpheme breaks
                            if oNoCantillations else oWord ) # Segs and notes have nothing in the noCantillations field
            oWordGloss = oWordGloss.replace( '=', '_' )
            oGloss = tidy_Hebrew_word_gloss( oContextualWordGloss if oContextualWordGloss else oWordGloss if oWordGloss else oContextualMorphemeGlosses if oContextualMorphemeGlosses else oMorphemeGlosses )
            oBBB, oCVW = oWordRef.split( '_', 1 )
            oC, oVW = oCVW.split( ':', 1 )
            oV, oW = oVW.split( 'w', 1 )
            oTidyBBB = getOETTidyBBB( oBBB )
            oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
            oOSISbookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( oBBB )
            # if other_count == 0:
            translation = '<small>(no English gloss here)</small>' if oGloss=='-' else f'''‘{oGloss.replace('_','<span class="ul">_</span>')}’'''
            wordsHtml = f'''{wordsHtml}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBBwithNotes} {oC}:{oV}</a>''' \
f''' {translation} <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={oOSISbookCode}&c={oC}&v={oV}">OSHB {oTidyBBBwithNotes} {oC}:{oV} word {oW}</a></p>''' \
                if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else \
                f'''{wordsHtml}\n<p class="wordLine">{oTidyBBBwithNotes} {oC}:{oV}''' \
f''' {translation} <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={oOSISbookCode}&c={oC}&v={oV}">OSHB {oTidyBBBwithNotes} {oC}:{oV} word {oW}</a></p>'''
            # other_count += 1
            # if other_count >= 120:
            #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
            #     break
            displayCounter += 1
            if displayCounter >= maxWordsToShow: break
        if len(lemmaGlossesList) > len(wordOETGlossesList):
            # print( f"{n}/{len(state.OETRefData['word_tables'][HebrewWordFileName])-1} {hebrewWord=} {wordGloss=} ({len(lemmaGlossesList)}) {lemmaGlossesList=} ({len(wordOETGlossesList)}) {wordOETGlossesList=}")
            assert lemmaGlossesList != ['']
            # NEVER_HAPPENS_BUT_PROBABLY_SHOULD_MAYBE -- Oh, it does happen at least once for 25401 hebrewWord='וְאֵלֶּה' wordGloss='and_these' (1) lemmaGlossesList=['and=these'] (0) wordOETGlossesList=[]
            wordsHtml = f'''{wordsHtml}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLinksStr}’ have {len(lemmaGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>'''
        elif len(thisWordNumberList) == 1:
            hebLemmaWordRowsList = state.OETRefData['OTLemmaRowNumbersDict'][noCantillations]
            # lemmaFormsList = state.OETRefData['OTLemmaFormsDict'][noCantillations]
            if len(hebLemmaWordRowsList) == 1:
                thisSingleLemmaRowNumber = hebLemmaWordRowsList[0]
                if len( state.OETRefData['OTWordRowNumbersDict'][thisSingleLemmaRowNumber] ) == 1:
                    # print( f"{ref} '{hebrew}' ({glossWords}) {lemma=} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}" )
                    # assert len(lemmaFormsList) == 1, f"{ref} {hebLemmaWordRowsList=} {lemmaFormsList=} {morphemeGlossesList=}"
                    # assert len(morphemeGlossesList) == 1
                    wordsHtml = f'''{wordsHtml.replace(lemmaLinksStr, f'{lemmaLinksStr}<sup>*</sup>', 1)}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> ‘{noCantillations}’ in the Hebrew originals.</p>'''

        extraHTMLList = []
        if mainGlossWord not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
            # List other words that are glossed similarly
            try:
                similarWords = (mainGlossWord,) + SIMILAR_GLOSS_WORDS_DICT[mainGlossWord]
                # print( f"      {mainGlossWord=} {similarWords=}")
            except KeyError: similarWords = (mainGlossWord,)
            extraWordSet, extraLemmaSet = set(), set()
            for similarWord in similarWords:
                # print( f"{similarWord=} from {similarWords=} {len(state.OETRefData['OETOTGlossWordDict'])=}")
                nList = state.OETRefData['OETOTGlossWordDict'][similarWord]
                # print( f"{similarWord=} from {similarWords=} {len(state.OETRefData['OETOTGlossWordDict'])=} {nList=}")
                # print( f'''    {n} {ref} {hebrewWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nList[:8]=}{'…' if len(nList)>8 else ''}''' )
                if len(nList) > 1:
                    if similarWord==mainGlossWord:
                        # assert n in nList, f"{n=} {mainGlossWord=} ({len(nList)}) {nList=}"
                        logging.warning( f"Not sure why {n=} similarWord={mainGlossWord=} not in ({len(nList)})" )
                    # elif len(nList)>400:
                    else:
                        # print( f"This one {n=} similarWord={mainGlossWord=} was in ({len(nList)})" )
                        if len(nList)>400:
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"EXCESSIVE {len(nList):,} entries for {mainGlossWord=} from {similarWord=}")
                    for thisN in nList:
                        if thisN == n: continue # That's the current word row
                        eWordRef, eRowType, eMorphemeRowList, eLemmaRowList, eStrongs, eMorphology, eWord, eNoCantillations, eMorphemeGlosses, eContextualMorphemeGlosses, eWordGloss, eContextualWordGloss, eGlossCapitalisation, eGlossPunctuation, eGlossOrder, eGlossInsert, eRole, eNesting, eTags = state.OETRefData['word_tables'][HebrewWordFileName][thisN].split( '\t' )
                        eHebrewWord = (eNoCantillations.replace( ',', '' ) # Remove morpheme breaks
                                        if eNoCantillations else eWord ) # Segs and notes have nothing in the noCantillations field
                        eWordGloss = eWordGloss.replace( '=', '_' )
                        eGloss = tidy_Hebrew_word_gloss( eContextualWordGloss if eContextualWordGloss else eWordGloss if eWordGloss else eContextualMorphemeGlosses if eContextualMorphemeGlosses else eMorphemeGlosses )
                        if eHebrewWord!=hebrewWord or eMorphology!=morphology:
                            eBBB, eCVW = eWordRef.split( '_', 1 )
                            eC, eVW = eCVW.split( ':', 1 )
                            eV, eW = eVW.split( 'w', 1 )
                            eTidyBBB = getOETTidyBBB( eBBB )
                            eTidyBBBwithNotes = getOETTidyBBB( eBBB, addNotes=True )
                            eOSISbookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( eBBB )

                            eLemmaLinksList, eLemmaLinksStr = [], ''
                            for eLemmaRowNumberStr in eLemmaRowList.split( ',' ):
                                # print( f"{lemmaRowNumberStr=}" )
                                try: eLemmaRowNumber = int(eLemmaRowNumberStr)
                                except ValueError: continue # could be empty string or '<<<MISSING>>>'
                                eLemmaHebrew = state.OETRefData['OTHebLemmaList'][eLemmaRowNumber]
                                state.OETRefData['usedHebLemmas'].add( lemmaHebrew ) # Used in next function to make lemma pages
                                eLemmaTrans = state.OETRefData['OTTransLemmaList'][eLemmaRowNumber]
                                eLemmaLink = f'<a title="View Hebrew lemma" href="../HebLem/{eLemmaTrans}.htm#Top">‘{eLemmaHebrew}’</a>'
                                eLemmaLinksList.append( eLemmaLink )
                            if eLemmaLinksList:
                                eLemmaLinksStr = f'''Lemmas=<b>{', '.join(eLemmaLinksList)}</b>''' if len(eLemmaLinksList)>1 else f'Lemma=<b>{eLemmaLinksList[0]}</b>'
                                extraLemmaSet.add( eLemmaLinksStr )

                            eHebrewPossibleLink = f'<a title="Go to word page" href="{getHebrewWordpageFilename(thisN,state)}#Top">{eHebrewWord}</a>' if not TEST_MODE or ALL_TEST_REFERENCE_PAGES or eBBB in TEST_BOOK_LIST else eHebrewWord
                            extraWordSet.add( eHebrewPossibleLink )
                            eWordGloss = eWordGloss.replace( '=', '_' )
                            eGloss = tidy_Hebrew_word_gloss( eContextualWordGloss if eContextualWordGloss else eWordGloss if eWordGloss else eContextualMorphemeGlosses if eContextualMorphemeGlosses else eMorphemeGlosses )
                            assert '\\' not in eGloss, f"{n=} {eGloss=}"
                            etidyMorphologyField = '' #= eMoodField = eTenseField = eVoiceField = ePersonField = eCaseField = eGenderField = eNumberField = ''
                            if eMorphology:
                                eTidyMorphologyField = tidy_Hebrew_morphology( eRowType, eMorphology )
                                # eTidyMorphology = eMorphology[4:] if eMorphology.startswith('....') else eMorphology
                                # etidyMorphologyField = f'{eTidyMorphology}'
                                # if eTidyMorphology != '...': usedMorphologies.add( eTidyMorphology )
                            extraHTMLList.append( f'''<p class="wordLine"><a title="View OET {eTidyBBB} text" href="{'../'*level}OET/byC/{eBBB}_C{eC}.htm#C{eC}V{eV}">{eTidyBBB} {eC}:{eV}</a>''' \
f''' <b>{eHebrewPossibleLink}</b> ({transliterate_Hebrew(eHebrewWord)}) <small>{etidyMorphologyField}</small>{f' {eLemmaLinksStr}' if eLemmaLinksStr else ''}''' \
f''' ‘{eGloss}’''' \
f''' <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={eOSISbookCode}&c={eC}&v={eV}">OSHB {eTidyBBB} {eC}:{eV} word {eW}</a></p>'''
                                if not TEST_MODE or eBBB in state.preloadedBibles['OET-RV'] else
                                    f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eHebrewPossibleLink}’ <small>({etidyMorphologyField})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}''' \
f''' ‘{eGloss}’''' \
f''' <a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={eOSISbookCode}&c={eC}&v={eV}">OSHB {eTidyBBB} {eC}:{eV} word {eW}</a></p>''' )
        assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"
        if extraHTMLList:
            wordsHtml = f'''{wordsHtml}\n<h2 class="otherHebrew">Hebrew words ({len(extraHTMLList):,}) other than {hebrewWord} <small>({tidyMorphologyField})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
            if len(extraHTMLList) > 10:
                wordsHtml = f'''{wordsHtml}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemma{'' if len(extraLemmaSet)==1 else 's'} altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
            wordsHtml = f'''{wordsHtml}\n{NEWLINE.join(extraHTMLList)}'''

        wordsHtml = ( wordsHtml.replace( ' <small>(<br> ', '\n<br><small> (' )# Tidy up formatting of similar word morphologies
                     .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>')
                     .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>')
                     )
        assert '\\' not in wordsHtml, f"{wordsHtml=}"
        assert not wordsHtml.endswith('\n'), f"{wordsHtml=}"
        assert '</span>C1.htm' not in wordsHtml, f"{wordsHtml=}"

        keyHtml = ''
        if usedRoleLetters or usedMorphologies: # Add a key at the bottom
            keyHtml = '<p class="key" id="Bottom"><b>Key</b>:'
            for usedRoleLetter in sorted( usedRoleLetters ):
                keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
            for usedMorphology in sorted( usedMorphologies ):
                try:
                    keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
                except KeyError:
                    logging.warning( f"create_Hebrew_word_pages: Missing {usedMorphology=}")
            keyHtml = f'{keyHtml}</p>'
        assert not keyHtml.startswith('\n') and not keyHtml.endswith('\n'), f"{keyHtml=}"

        # Now put it all together
        top = makeTop( level, None, 'word', None, state ) \
                        .replace( '__TITLE__', f"Hebrew word ‘{hebrewWord}’{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' ) \
                        .replace( 'par/"', f'par/{BBB}/C{C}V{V}.htm#Top"' )
        wordsHtml = f'''{top}{wordsHtml}{keyHtml}{makeBottom( level, 'word', state )}'''
        checkHtml( 'HebrewWordPage', wordsHtml )
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( wordsHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(wordsHtml):,} characters to {output_filename}" )
        if rowType!='seg' and 'note' not in rowType:
            wordLinksForIndex.append( f'<a href="{output_filename}">{hebrewWord}</a>')
        numWordPagesMade += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {numWordPagesMade:,}{f"/{len(state.OETRefData['word_tables'][HebrewWordFileName])-1:,}" if numWordPagesMade < len(state.OETRefData['word_tables'][HebrewWordFileName])-1 else ''} Hebrew word pages (using {len(state.OETRefData['usedHebLemmas']):,} Hebrew lemmas).''' )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'wordIndex', None, state) \
            .replace( '__TITLE__', f"Hebrew Words Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Hebrew, words' )
    indexText = ' '.join( wordLinksForIndex )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note">Hebrew words index <a href="transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Hebrew Words Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'wordIndex', state )}'''
    checkHtml( 'wordIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    # Create transliterated index page for this folder
    filename = 'transIndex.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'wordIndex', None, state) \
            .replace( '__TITLE__', f"Transliterated Hebrew Words Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Hebrew, words, transliterated' )
    indexText = transliterate_Hebrew( indexText )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="index.htm">Hebrew words index</a> Transliterated Hebrew words index</p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Transliterated Hebrew Words Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'wordIndex', state )}'''
    checkHtml( 'wordIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_Hebrew_word_pages


def create_Hebrew_lemma_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    These end up in OBD/ref/HebLem/abc.htm

    TODO: Why does this take so long to run???
    TODO: Add related lemma info (not just prefixed ones, but adding synonyms, etc.)
    """
    # DEBUGGING_THIS_MODULE = 99
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Hebrew_lemma_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making {len(state.OETRefData['OTLemmaGlossDict']):,} Hebrew lemma pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    def tidy_Hebrew_lemma_gloss( engGloss:str ) -> str:
        """
        """
        assert '<span class="ul">' not in engGloss # already
        return engGloss \
            .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>') \
            .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>') \
            .replace( '_', '<span class="ul">_</span>')
    # end of createOETReferencePages.tidy_Hebrew_lemma_gloss


    # transliteratedLemmaList = [transliterate_Hebrew(lemma) for lemma in state.OETRefData['OTLemmaGlossDict']]
    # transliteratedLemmaList.insert( 0, None ) # Insert a dummy entry so that indexing is 1-based like other lists
    # print( f"{lemmaList[:50]=}" )
    # print( f"{state.OETRefData['OTHebLemmaList'][0]=} {state.OETRefData['OTHebLemmaList'][1]=} {state.OETRefData['OTHebLemmaList'][2]=}")
    # print( f"{state.OETRefData['OTTransLemmaList'][0]=} {state.OETRefData['OTTransLemmaList'][1]=} {state.OETRefData['OTTransLemmaList'][2]=}")
    # halt

    # Now make a page for each Hebrew lemma
    lemmaLinks:List[str] = [] # Used below to make an index page
    lemmaList = list( state.OETRefData['OTLemmaGlossDict'] )
    # lemmaListWithGlosses = list( state.OETRefData['OTLemmaGlossDict'].items() )
    # assert len(lemmaListWithGlosses) == len(lemmaList)
    for ll, hebLemma  in enumerate( lemmaList, start=1 ):
        transliteratedLemma = transliterate_Hebrew( hebLemma )
        if transliteratedLemma == 'pitgām': # One is at ll=5803 hebLemma='פִּתְגָם' ll=5804 hebLemma='פִּתְגָּם'
            print( f"      Found pitgām at {ll=} {hebLemma=} {transliteratedLemma=} wordRows={state.OETRefData['OTWordRowNumbersDict'][ll]}" )
        if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and hebLemma not in state.OETRefData['usedHebLemmas']:
            continue # Don't make this page
        vowellessLemma = removeHebrewVowelPointing( hebLemma )
        transliteratedVowellessLemma = transliterate_Hebrew( vowellessLemma )

        hebLemmaWordRowsList = state.OETRefData['OTWordRowNumbersDict'][ll]
        # print( f"\nLemma {mm}: {hebLemma=} {translemma=} {lemmaOETGlossesList=} {hebLemmaWordRowsList=}" )
        # lemmaFormsList = sorted( state.OETRefData['OTLemmaFormsDict'][hebLemma] )
        # lemmaOETGlossesList = state.OETRefData['OTLemmaGlossDict'][hebLemma].split( ';' )

        # def getFirstHebrewWordNumber(grk:str,morph:str):
        #     return state.OETRefData['OTFormUsageDict'][(grk,morph)][0]

        usedMorphologies = set()
        ll_output_filename = f"{'pitggām' if hebLemma=='פִּתְגָּם' else transliteratedLemma}.htm" # Hack to keep transliterations unique

        prevLL = nextLL = None
        if ll > 1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for LL in range( ll-2, 0, -1 ):
                    # MMLemma = lemmaListWithGlosses[MM][0]
                    # print( f"{mm=} {MM=} {lemmaListWithGlosses[MM]=} {MMLemma=} {list(state.OETRefData['usedHebLemmas'])[:20]=}")
                    # halt
                    if lemmaList[LL] in state.OETRefData['usedHebLemmas']:
                        prevLL = LL
                        break
            else: prevLL = ll-1
        if ll<len(lemmaList)-1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for LL in range( ll, len(lemmaList) ):
                    if lemmaList[LL] in state.OETRefData['usedHebLemmas']:
                        nextLL = LL
                        break
            else: nextLL = ll+1
        prevLink = f'<b><a title="Previous lemma" href="{transliterate_Hebrew(lemmaList[prevLL])}.htm#Top">←</a></b> ' if prevLL else ''
        nextLink = f' <b><a title="Next lemma" href="{transliterate_Hebrew(lemmaList[nextLL])}.htm#Top">→</a></b>' if nextLL else ''
        lemmasHtml = f'''<h1 id="Top">Hebrew root <small>(lemma)</small> ‘{hebLemma}’ ({transliteratedLemma})</h1>
<p class="pNav">{prevLink}<b>{hebLemma}</b> <a title="Go to Hebrew word index" href="index.htm">↑</a>{nextLink}</p>'''
# <p class="summary">This root form (lemma) ‘{hebLemma}’ is used in {'only one form' if len(lemmaFormsList)==1 else f'{len(lemmaFormsList):,} different forms'} in the Hebrew originals: {', '.join([f'<a title="View Hebrew word form" href="../HebWrd/{getFirstHebrewWordNumber(heb,morph)}.htm#Top">{heb}</a> <small>({morph[4:] if morph.startswith("....") else morph})</small>' for heb,morph in lemmaFormsList])}.</p>
# <p class="summary">It is glossed in {'only one way' if len(lemmaOETGlossesList)==1 else f'{len(lemmaOETGlossesList):,} different ways'}: ‘<b>{"</b>’, ‘<b>".join(lemmaOETGlossesList)}</b>’.</p>

        def makeHebrewLemmaHTML( thisLemmaStr:str, thisLemmaRowsList ) -> str:
            """
            The guts of making the lemma page
                put into a function so that we can also re-use it for related words

            Side-effects: udates usedRoleLetters and usedMorphologies
            """
            # for oN in thisLemmaRowsList:
            #     _oref, orowType, oMorphemeRowList, olemmaRowList, ostrongs, ocantillationHierarchy, omorphology, oword, _oNoCantillations, oMorphemeGlosses, oContextualMorphemeGlosses, oWordGloss, oContextualWordGloss, oglossCapitalisation, oglossPunctuation, oglossOrder, oglossInsert, oRole, oNesting, oTags = state.OETRefData['word_tables'][wordFileName][oN].split( '\t' )
            #     # usedRoleLetters.add( oRoleLetter )
            # # oRoleLetter remains set to the last value added to the set (which is the only value if len(oRoleSet)==1)

            if len(thisLemmaRowsList) > 100: # too many to list
                maxWordsToShow = 50
                lemmaHTML = f"<h2>Showing the first {maxWordsToShow} out of ({len(thisLemmaRowsList)-1:,}) uses of Hebrew root <small>(lemma)</small> ‘{thisLemmaStr}’ ({transliterate_Hebrew(thisLemmaStr)}) in the Hebrew originals</h2>"
            else: # we can list all uses of the word
                maxWordsToShow = 100
                lemmaHTML = f"<h2>Have {len(thisLemmaRowsList):,} {'use' if len(thisLemmaRowsList)==1 else 'uses'} of Hebrew root <small>(lemma)</small> ‘{thisLemmaStr}’ ({transliterate_Hebrew(thisLemmaStr)}) in the Hebrew originals</h2>"
            for displayCounter,oN in enumerate( thisLemmaRowsList, start=1 ):
                oWordRef, oRowType, oMorphemeRowList, oLemmaRowList, oStrongs, oMorphology, oWord, oNoCantillations, oMorphemeGlosses, oContextualMorphemeGlosses, oWordGloss, oContextualWordGloss, oGlossCapitalisation, oGlossPunctuation, oGlossOrder, oGlossInsert, oRole, oNesting, oTags = state.OETRefData['word_tables'][HebrewWordFileName][oN].split( '\t' )
                # print( f"    {oWordRef=} {oOSHBid=} {orowType=} {len(thisLemmaRowsList)=}" )
                oHebrewWord = oNoCantillations
                oWordGloss = oWordGloss.replace( '=', '_' )
                oGloss = tidy_Hebrew_lemma_gloss( oContextualWordGloss if oContextualWordGloss else oWordGloss if oWordGloss else oContextualMorphemeGlosses if oContextualMorphemeGlosses else oMorphemeGlosses )
                oFormattedContextGlossWords = oGloss # formatNTContextSpansOETGlossWords( oN, state )
                oBBB, oCVW = oWordRef.split( '_', 1 )
                oC, oVW = oCVW.split( ':', 1 )
                oV, oW = oVW.split( 'w', 1 ) if 'w' in oVW else (oVW, '')
                oOSISbookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( oBBB )
                oTidyBBB = getOETTidyBBB( oBBB )
                oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
                oOSISbookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( oBBB )
                oTidyMorphology = oMorphology[4:] if oMorphology.startswith('....') else oMorphology
                if oTidyMorphology != '...': usedMorphologies.add( oTidyMorphology )
                # if other_count == 0:
                oOETLink = f'''<a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBBwithNotes} {oC}:{oV}</a>''' \
                                if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] \
                                    else f'{oTidyBBBwithNotes} {oC}:{oV}'
                oHebrewWordLink = f'<a title="Go to word page" href="../HebWrd/{oN}.htm#Top">{oHebrewWord}</a>' if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else oHebrewWord
                translation = f'''‘{oFormattedContextGlossWords.replace(',',', ').replace('_','<span class="ul">_</span>')}’'''
                lemmaHTML = f'''{lemmaHTML}\n<p class="lemmaLine">{oOETLink} <b>{oHebrewWordLink}</b> ({transliterate_Hebrew(oHebrewWord.replace(',',', '))})''' \
                    f" {oTidyMorphology} {translation} " \
                    f'''<a title="Go to Open Scriptures Hebrew verse page" href="https://hb.OpenScriptures.org/structure/OshbVerse/index.html?b={oOSISbookCode}&c={oC}&v={oV}">OSHB {oTidyBBBwithNotes} {oC}:{oV} word {oW}</a></p>'''
                # other_count += 1
                # if other_count >= 120:
                #     lemmaHTML = f'{lemmaHTML}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                #     break
                if displayCounter >= maxWordsToShow: break
            assert '\\' not in lemmaHTML, f"{lemmaHTML=}"
            assert not lemmaHTML.endswith('\n'), f"{lemmaHTML=}"
            return lemmaHTML
        # end of createOETReferencePages.create_Hebrew_lemma_pages.makeHebrewLemmaHTML

        lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(hebLemma, hebLemmaWordRowsList)}" # Make all the Hebrew lemma pages

        # Consider related lemmas, e.g., with or without prefix
        this_extended_lemma_list = [hebLemma]
        for ll2, this_second_lemma in enumerate( lemmaList ):
            # print( f"  {mm} {this_second_lemma=}" )
            if this_second_lemma and len(this_second_lemma)>1 and this_second_lemma not in this_extended_lemma_list:
                prefix = None
                if this_second_lemma.endswith( hebLemma ):
                    prefix = this_second_lemma[:len(this_second_lemma)-len(hebLemma)]
                elif hebLemma.endswith( this_second_lemma ):
                    prefix = hebLemma[:len(hebLemma)-len(this_second_lemma)]
                if prefix and len(prefix) < 6:
                    if prefix in KNOWN_GREEK_PREFIXES:
                        # print(f"create_Hebrew_lemma_pages also got lemma '{this_second_lemma}' with prefix '{prefix}' (cf. '{lemma}')")
                        hebLemmaWordRowsList = state.OETRefData['OTLemmaRowNumbersDict'][this_second_lemma]
                        # lemmaFormsList = sorted( state.OETRefData['OTLemmaFormsDict'][this_second_lemma] )
                        # lemmaGlossesList = sorted( state.OETRefData['OTLemmaOETGlossesDict'][this_second_lemma] )
                        this_second_lemma_link = f'<a title="Go to lemma page" href="{this_second_lemma}.htm#Top">{this_second_lemma}</a>'
                        if len(this_extended_lemma_list) == 1:
                            lemmasHtml = f"{lemmasHtml}\n<h1>Other possible lexically-related lemmas</h1>"
                        lemmasHtml = f'''{lemmasHtml}
<h2>Hebrew root <small>(lemma)</small> ‘{this_second_lemma}’ <small>with prefix=‘{prefix}’</small></h2>
{makeHebrewLemmaHTML(this_second_lemma_link, hebLemmaWordRowsList)}'''
                        this_extended_lemma_list.append( this_second_lemma )
                    # else:
                    #     print(f"create_Hebrew_lemma_pages ignored potential lemma '{this_second_lemma}' with unrecognised prefix '{prefix}' (cf. '{lemma}')")
        # if len(this_extended_lemma_list) > 1:
        #     print( f"Got {this_extended_lemma_list=}" )

        # Consider other lemmas with similar English glosses
        similarLemmaSet = set()
        lemmaOETGlossesList = state.OETRefData['OTLemmaGlossDict'][hebLemma]
        for lemmaGloss in lemmaOETGlossesList:
            # print( f"  A {lemmaGloss=}" )
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed similarly
                try:
                    similarWords = (lemmaGloss,) + SIMILAR_GLOSS_WORDS_DICT[lemmaGloss]
                    # print( f"      {lemmaGloss=} {similarWords=} {ll} {lemma=} {lemmaGlossesList=}")
                except KeyError: similarWords = (lemmaGloss,)
                for similarWord in similarWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['OTLemmaOETGlossesDict'].items():
                        # NOTE: otherLemmaGlosses contains raw words and well as HTML spans for gloss helpers, etc.
                        if otherLemma != hebLemma:
                            # print( f"{otherLemma=} {otherLemmaGlosses=}")
                            if similarWord in otherLemmaGlosses:
                                similarLemmaSet.add( otherLemma )
        if similarLemmaSet:
            # print( f"{lemma=} {lemmaGlossesList=} {extraLemmaSet=}" )
            lemmasHtml = f'''{lemmasHtml}
<h1>Lemmas with similar glosses to ‘{hebLemma}’ ({transliteratedLemma})</h1>'''
            for extraLemma in similarLemmaSet:
                transliteratedExtraLemma = transliterate_Hebrew( extraLemma )
                extra_lemma_link = f'<a title="Go to lemma page" href="{transliteratedExtraLemma}.htm#Top">{extraLemma}</a>'
                hebExtraLemmaWordRowsListA = state.OETRefData['OTLemmaRowNumbersDict'][extraLemma]
                assert len(hebExtraLemmaWordRowsListA) == 1
                rowNum = list(state.OETRefData['OTLemmaGlossDict']).index(extraLemma)
                assert rowNum == hebExtraLemmaWordRowsListA[0] - 1
                hebExtraLemmaWordRowsListB = state.OETRefData['OTWordRowNumbersDict'][rowNum]
                # print( f"{extraLemma=} {transliteratedExtraLemma=} {rowNum=} ({len(hebExtraLemmaWordRowsListA)}) {hebExtraLemmaWordRowsListA=} ({len(hebExtraLemmaWordRowsListB)}) {hebExtraLemmaWordRowsListB}" )
                lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(extra_lemma_link, hebExtraLemmaWordRowsListB)}"
        assert not lemmasHtml.endswith('\n'), f"{lemmasHtml=}"

        # Consider other lemmas with contrastive English glosses
        contrastiveLemmaSet = set()
        for lemmaGloss in lemmaOETGlossesList:
            # print( f"  B {lemmaGloss=}" )
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed as antonyms
                try:
                    contrastiveWords = CONTRASTIVE_GLOSS_WORDS_DICT[lemmaGloss]
                    print( f"      {lemmaGloss=} {contrastiveWords=} {ll} {hebLemma=} {lemmaOETGlossesList=}")
                    NEVER_GETS_HERE
                except KeyError: contrastiveWords = []
                for contrastiveWord in contrastiveWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['OTLemmaOETGlossesDict'].items():
                        # NOTE: otherLemmaGlosses contains raw words and well as HTML spans for gloss helpers, etc.
                        if otherLemma != hebLemma:
                            print( f"{otherLemma=} {otherLemmaGlosses=}")
                            if contrastiveWord in otherLemmaGlosses:
                                assert otherLemma not in similarLemmaSet
                                contrastiveLemmaSet.add( otherLemma )
        if contrastiveLemmaSet:
            # print( f"{lemma=} {lemmaGlossesList=} {extraLemmaSet=}" )
            lemmasHtml = f'''{lemmasHtml}
<h1>Lemmas with contrastive glosses to ‘{hebLemma}’ ({transliteratedLemma})</h1>'''
            for contrastiveLemma in contrastiveLemmaSet:
                NEVER_GETS_HERE
                transliteratedContrastiveLemma = transliterate_Hebrew( contrastiveLemma )
                contrastive_lemma_link = f'<a title="Go to lemma page" href="{transliteratedContrastiveLemma}.htm#Top">{contrastiveLemma}</a>'
                hebContrastiveLemmaWordRowsListA = state.OETRefData['OTLemmaRowNumbersDict'][contrastiveLemma]
                assert len(hebContrastiveLemmaWordRowsListA) == 1
                rowNum = list(state.OETRefData['OTLemmaGlossDict']).index(contrastiveLemma)
                assert rowNum == hebContrastiveLemmaWordRowsListA[0] - 1
                hebContrastiveLemmaWordRowsListB = state.OETRefData['OTWordRowNumbersDict'][rowNum]
                print( f"{contrastiveLemma=} {transliteratedContrastiveLemma=} {rowNum=} ({len(hebContrastiveLemmaWordRowsListA)}) {hebContrastiveLemmaWordRowsListA=} ({len(hebContrastiveLemmaWordRowsListB)}) {hebContrastiveLemmaWordRowsListB}" )
                lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(contrastive_lemma_link, hebContrastiveLemmaWordRowsListB)}"
                # lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(contrastive_lemma_link, state.OETRefData['OTLemmaRowNumbersDict'][contrastiveLemma])}"
        assert '\\' not in lemmasHtml, f"{lemmasHtml=}"
        assert not lemmasHtml.endswith('\n'), f"{lemmasHtml=}"

        # Consider other lemmas with the same root consonants
        lemmaSet = state.OETRefData['OTLemmasForRootDict'][vowellessLemma]
        # print( f"{hebLemma=} {vowellessLemma=} count={len(lemmaSet)} {lemmaSet=}")
        assert hebLemma in lemmaSet
        if len(lemmaSet) > 1:
            lemmasHtml = f'''{lemmasHtml}
<h1>Lemmas with same root consonants as ‘{vowellessLemma}’ ({transliteratedVowellessLemma})</h1>'''
            for sameRootLemma in lemmaSet:
                if sameRootLemma == hebLemma: continue # This is already the page we're on
                transliteratedSameRootLemma = transliterate_Hebrew( sameRootLemma )
                # print( f"{sameRootLemma=} from {hebLemma=} {vowellessLemma=} count={len(lemmaSet)} {lemmaSet=}")
                other_lemma_link = f'<a title="Go to lemma page" href="{transliteratedSameRootLemma}.htm#Top">{sameRootLemma}</a>'
                # hebOtherLemmaWordRowsListA = state.OETRefData['OTLemmaRowNumbersDict'][sameRootLemma]
                # print( f"{vowellessLemma=} count={len(lemmaSet)} {sameRootLemma=} {transliteratedSameRootLemma=} ({len(hebOtherLemmaWordRowsListA)}) {hebOtherLemmaWordRowsListA=}" )
                # if hebOtherLemmaWordRowsListA: assert len(hebOtherLemmaWordRowsListA) == 1
                rowNum = list(state.OETRefData['OTLemmaGlossDict']).index(sameRootLemma) + 1
                # print( f"    {rowNum=}" )
                # if hebOtherLemmaWordRowsListA: assert rowNum == hebOtherLemmaWordRowsListA[0] - 1
                hebOtherLemmaWordRowsListB = state.OETRefData['OTWordRowNumbersDict'][rowNum]
                # print( f"    ({len(hebOtherLemmaWordRowsListB)}) {hebOtherLemmaWordRowsListB}" )
                lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(other_lemma_link, hebOtherLemmaWordRowsListB)}"
                # lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(other_lemma_link, state.OETRefData['OTLemmaRowNumbersDict'][sameRootLemma])}"
        assert '\\' not in lemmasHtml, f"{lemmasHtml=}"
        assert not lemmasHtml.endswith('\n'), f"{lemmasHtml=}"

        if len(vowellessLemma) > 3:
            lemmaSet = set()
            if vowellessLemma[0] in 'מכ': # Then it's possibly a derived root with a prefix
                # print( f"  {hebLemma=} {vowellessLemma=} count={len(lemmaSet)} {lemmaSet=}")
                adjVowellessLemma = vowellessLemma[1:]
                lemmaSet.update( state.OETRefData['OTLemmasForRootDict'][adjVowellessLemma] )
                # print( f"         {adjVowellessLemma=} *NOW count={len(lemmaSet)} {lemmaSet=}")
            if vowellessLemma[-1] in 'הן': # Then it's possibly a derived root with a suffix
                # print( f"  {hebLemma=} {vowellessLemma=} count={len(lemmaSet)} {lemmaSet=}")
                adjVowellessLemma = vowellessLemma[:-1] # Remove the final consonant
                if len(adjVowellessLemma) > 3 and adjVowellessLemma[-1] in 'ו':
                    adjVowellessLemma = adjVowellessLemma[:-1] # Remove the preceding vowel
                # Change (the now) final consonants where required
                if   adjVowellessLemma[-1] == 'נ': adjVowellessLemma = f'{adjVowellessLemma[:-1]}ן'
                elif adjVowellessLemma[-1] == 'כ': adjVowellessLemma = f'{adjVowellessLemma[:-1]}ך'
                elif adjVowellessLemma[-1] == 'מ': adjVowellessLemma = f'{adjVowellessLemma[:-1]}ם'
                elif adjVowellessLemma[-1] == 'פ': adjVowellessLemma = f'{adjVowellessLemma[:-1]}ף'
                elif adjVowellessLemma[-1] == 'צ': adjVowellessLemma = f'{adjVowellessLemma[:-1]}ץ'
                lemmaSet.update( state.OETRefData['OTLemmasForRootDict'][adjVowellessLemma] )
                # print( f"         {adjVowellessLemma=} NOW* count={len(lemmaSet)} {lemmaSet=}")
            if lemmaSet:
                lemmasHtml = f'''{lemmasHtml}
    <h1>Lemmas with some of the same root consonants as ‘{vowellessLemma}’ ({transliteratedVowellessLemma})</h1>'''
                for sameRootLemma in lemmaSet:
                    assert sameRootLemma != hebLemma
                    transliteratedSameRootLemma = transliterate_Hebrew( sameRootLemma )
                    # print( f"{sameRootLemma=} from {hebLemma=} {vowellessLemma=} count={len(lemmaSet)} {lemmaSet=}")
                    other_lemma_link = f'<a title="Go to lemma page" href="{transliteratedSameRootLemma}.htm#Top">{sameRootLemma}</a>'
                    # hebOtherLemmaWordRowsListA = state.OETRefData['OTLemmaRowNumbersDict'][sameRootLemma]
                    # print( f"{vowellessLemma=} count={len(lemmaSet)} {sameRootLemma=} {transliteratedSameRootLemma=} ({len(hebOtherLemmaWordRowsListA)}) {hebOtherLemmaWordRowsListA=}" )
                    # if hebOtherLemmaWordRowsListA: assert len(hebOtherLemmaWordRowsListA) == 1
                    rowNum = list(state.OETRefData['OTLemmaGlossDict']).index(sameRootLemma) + 1
                    # print( f"    {rowNum=}" )
                    # if hebOtherLemmaWordRowsListA: assert rowNum == hebOtherLemmaWordRowsListA[0] - 1
                    hebOtherLemmaWordRowsListB = state.OETRefData['OTWordRowNumbersDict'][rowNum]
                    # print( f"    ({len(hebOtherLemmaWordRowsListB)}) {hebOtherLemmaWordRowsListB}" )
                    lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(other_lemma_link, hebOtherLemmaWordRowsListB)}"
                    # lemmasHtml = f"{lemmasHtml}\n{makeHebrewLemmaHTML(other_lemma_link, state.OETRefData['OTLemmaRowNumbersDict'][sameRootLemma])}"
            assert '\\' not in lemmasHtml, f"{lemmasHtml=}"
            assert not lemmasHtml.endswith('\n'), f"{lemmasHtml=}"

        if usedMorphologies: # Add a key at the bottom
            keyHtml = '<p class="key" id="Bottom"><b>Key</b>:'
            for usedMorphology in sorted( usedMorphologies ):
                try:
                    keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
                except KeyError:
                    logging.warning( f"Missing {usedMorphology=}")
            keyHtml = f'{keyHtml}</p>'

        # Now put it all together
        top = makeTop( level, None, 'lemma', None, state ) \
                        .replace( '__TITLE__', f"Hebrew lemma ‘{hebLemma}’{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' )
        lemmasHtml = f'''{top}{lemmasHtml}{keyHtml}{makeBottom( level, 'lemma', state )}'''
        checkHtml( 'HebrewLemmaPage', lemmasHtml )
        filepath = outputFolderPath.joinpath( ll_output_filename )
        assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
        # if filepath.is_file():
        #     logging.critical( f"create_Hebrew_lemma_pages is about to overwrite {filepath} for {ll=} {hebLemma=} {transliteratedLemma=}" )
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( lemmasHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(lemmasHtml):,} characters to {ll_output_filename}" )
        lemmaLinks.append( f'<a href="{ll_output_filename}">{hebLemma}</a>')
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {len(lemmaLinks):,}{f"/{len(state.OETRefData['OTLemmaGlossDict']):,}" if len(lemmaLinks) < len(state.OETRefData['OTLemmaGlossDict']) else ''} Hebrew lemma pages.''' )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'lemmaIndex', None, state) \
            .replace( '__TITLE__', f"Hebrew Lemma Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Hebrew, lemmas' )
    indexText = ' '.join( lemmaLinks )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note">Hebrew lemmas index <a href="transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Hebrew Lemmas Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'lemmaIndex', state )}'''
    checkHtml( 'lemmaIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    # Create transliterated index page for this folder
    filename = 'transIndex.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'lemmaIndex', None, state) \
            .replace( '__TITLE__', f"Transliterated Hebrew Lemma Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Hebrew, lemmas' )
    indexText = transliterate_Hebrew( indexText )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="index.htm">Hebrew lemmas index</a> Transliterated Hebrew lemmas index</p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Transliterated Hebrew Lemmas Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'lemmaIndex', state )}'''
    checkHtml( 'lemmaIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_Hebrew_lemma_pages


def create_Greek_word_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Greek_word_pages( {outputFolderPath}, {state.BibleVersions} )" )

    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Checking/Making {len(state.OETRefData['word_tables'][GreekWordFileName])-1:,} Greek word pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    def tidyGlossOfGreekWord( engGloss:str ) -> str:
        """
        The gloss might be the OET-LV gloss,
            or the original VLT gloss.
        """
            # .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>') \
            # .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>') \
            # .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>') \
        assert '<span class="ul">' not in engGloss # already
        result = ( engGloss
            .replace( '\\add +', '<span class="addArticle">' )
            .replace( '\\add -', '<span class="unusedArticle">' )
            .replace( '\\add =', '<span class="addCopula">' )
            #.replace( '\\add <a title', '__PROTECT__' ) # Enable if required
            .replace( '\\add <', '<span class="addDirectObject">' )
            #.replace( '__PROTECT__', '\\add <a title' )
            .replace( '\\add >', '<span class="addExtra">' )
            .replace( '\\add &', '<span class="addOwner">' )
            .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>')
            .replace( '_', '<span class="ul">_</span>')
            )
        return result
    # end of createOETReferencePages.tidyGlossOfGreekWord


    # Now make a page for each Greek word (including the variants not used in the translation)
    numWordPagesMade = 0
    wordLinksForIndex:List[str] = [] # Used below to make an index page
    state.OETRefData['usedGrkLemmas'] = set() # Used in next function to make lemma pages
    for n, columns_string in enumerate( state.OETRefData['word_tables'][GreekWordFileName][1:], start=1 ):
        if not columns_string: continue # a blank line (esp. at end)
        # print( f"Word {n}: {columns_string}" )

        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        usedRoleLetters, usedMorphologies = set(), set()

        ref, greekWord, SRLemma, GrkLemma, VLTGlossWordsStr, OETGlossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = columns_string.split( '\t' )

        BBB, CVW = ref.split( '_', 1 )
        if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and BBB not in TEST_BOOK_LIST:
            continue # In some test modes, we only make the relevant word pages
        C, VW = CVW.split( ':', 1 )
        V, W = VW.split( 'w', 1 )
        # ourTidyBBB = getOETTidyBBB( BBB, addNotes=True )
        ourTidyBbb = getOETTidyBBB( BBB, titleCase=True )
        ourTidyBbbWithNotes = getOETTidyBBB( BBB, titleCase=True, addNotes=True )
        tidyBbbb = getOETTidyBBB( BBB, titleCase=True, allowFourChars=True )

        output_filename = getGreekWordpageFilename( n, state )
        if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag: # NOTE: this makes the function quite a bit slower
            # Check that we're not creating any duplicate filenames (that will then be overwritten)
            assert output_filename not in used_word_filenames, f"Greek {n} {output_filename}"
            used_word_filenames.append( output_filename )
        formattedOETGlossWords = formatNTSpansGlossWords( OETGlossWordsStr )
        formattedVLTGlossWords = formatNTSpansGlossWords( VLTGlossWordsStr )
        formattedContextGlossWords = formatNTContextSpansOETGlossWords( n, state )
        mainGlossWord = None
        for someGlossWord in OETGlossWordsStr \
                                .replace('\\add ','').replace('\\add*','') \
                                .replace('\\sup ','').replace('\\sup*','') \
                                .split( ' ' ):
            # print( f"{someGlossWord=}" )
            if '˱' not in someGlossWord and '‹' not in someGlossWord and someGlossWord[0]!='/': # We only want the main words not gloss helpers, etc.
                assert not mainGlossWord, f"{someGlossWord=} {mainGlossWord=}" # There should only be ONE mainGlossWord
                mainGlossWord = someGlossWord.split('/(')[0] # Throw away any Hebrew names #.replace('\\add_','\\add ')
        if mainGlossWord and ('\\' in mainGlossWord or '/' in mainGlossWord):
            if '\\' in mainGlossWord: print( f"{n=} {mainGlossWord=} from {OETGlossWordsStr=}"); halt
        if extendedStrongs == 'None': extendedStrongs = None
        if roleLetter == 'None': roleLetter = None
        if morphology == 'None': morphology = None

        strongs = extendedStrongs[:-1] if extendedStrongs else None # drop the last digit

        roleField = ''
        if roleLetter:
            roleName = CNTR_ROLE_NAME_DICT[roleLetter]
            if roleName=='noun' and 'U' in glossCaps:
                roleName = 'proper noun'
            roleField = f' Word role=<b>{roleName}</b>'
            usedRoleLetters.add( roleLetter )

        nominaSacraField = 'Marked with <b>Nomina Sacra</b>' if 'N' in glossCaps else ''

        probabilityField = f'<small>(P={probability}%)</small> ' if probability else ''

        # morphologyField =
        tidyRoleMorphology = tidyMorphology = moodField = tenseField = voiceField = personField = caseField = genderField = numberField = ''
        if morphology:
            # morphologyField = f' Morphology=<b>{morphology}</b>:' # Not currently used since we give all the following information instead
            tidyMorphology = morphology[4:] if morphology.startswith('....') else morphology
            tidyRoleMorphology = f'{roleLetter}-{tidyMorphology}'
            assert len(morphology) == 7, f"Got {ref} '{greekWord}' morphology ({len(morphology)}) = '{morphology}'"
            mood,tense,voice,person,case,gender,number = morphology
            if mood!='.': moodField = f' mood=<b>{CNTR_MOOD_NAME_DICT[mood]}</b>'
            if tense!='.': tenseField = f' tense=<b>{CNTR_TENSE_NAME_DICT[tense]}</b>'
            if voice!='.': voiceField = f' voice=<b>{CNTR_VOICE_NAME_DICT[voice]}</b>'
            if person!='.': personField = f' person=<b>{CNTR_PERSON_NAME_DICT[person]}</b>'
            if case!='.': caseField = f' case=<b>{CNTR_CASE_NAME_DICT[case]}</b>'
            if gender!='.': genderField = f' gender=<b>{CNTR_GENDER_NAME_DICT[gender]}</b>'
            if number!='.': numberField = f' number=<b>{CNTR_NUMBER_NAME_DICT[number]}</b>' # or № ???
            if tidyMorphology != '...': usedMorphologies.add( tidyMorphology )
        else:
            tidyRoleMorphology = roleLetter
        translation = '<small>(no English gloss here)</small>' if OETGlossWordsStr=='-' else f'''‘{tidyGlossOfGreekWord(formattedContextGlossWords)}’'''
        capsField = f' <small>(Caps={glossCaps})</small>' if glossCaps else ''

        # Add pointers to people, locations, etc.
        semanticExtras = nominaSacraField
        if tagsStr:
            for semanticTag in tagsStr.split( ';' ):
                tagPrefix, tag = semanticTag[0], semanticTag[1:]
                # print( f"{BBB} {C}:{V} '{semanticTag}' from {tagsStr=}" )
                if tagPrefix == 'P':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Person=<a title="View person details" href="../Per/{tag}.htm#Top">{tag}</a>'''
                elif tagPrefix == 'L':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Location=<a title="View place details" href="../Loc/{tag}.htm#Top">{tag}</a>'''
                elif tagPrefix == 'Y':
                    year = tag
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Year={year}{' AD' if int(year)>0 else ''}'''
                elif tagPrefix == 'T':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}TimeSeries={tag}'''
                elif tagPrefix == 'E':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Event={tag}'''
                elif tagPrefix == 'G':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Group={tag}'''
                elif tagPrefix == 'F':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Referred to from <a title="Go to referent word" href="{tag}.htm#Top">Word #{tag}</a>'''
                elif tagPrefix == 'R':
                    semanticExtras = f'''{semanticExtras}{' ' if semanticExtras else ''}Refers to <a title="Go to referred word" href="{tag}.htm#Top">Word #{tag}</a>'''
                else:
                    logging.critical( f"Unknown '{tagPrefix}' word tag in {n}: {columns_string}")
                    unknownTag
        state.OETRefData['usedGrkLemmas'].add( GrkLemma ) # Used in next function to make lemma pages
        lemmaLink = f'<a title="View Greek root word" href="../GrkLem/{SRLemma}.htm#Top">{SRLemma}</a>'
        lemmaGlossesList = sorted( state.OETRefData['NTLemmaOETGlossesDict'][SRLemma] )
        wordOETGlossesList = sorted( state.OETRefData['NTFormOETGlossesDict'][(greekWord,roleLetter,morphology)] )
        wordVLTGlossesList = sorted( state.OETRefData['NTFormVLTGlossesDict'][(greekWord,roleLetter,morphology)] )

        prevN = nextN = None
        if n > 1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for nN in range( n-1, 0, -1 ):
                    nWordRef = state.OETRefData['word_tables'][GreekWordFileName][nN].split( '\t', 1 )[0]
                    nBBB = nWordRef.split( '_', 1 )[0]
                    if nBBB in TEST_BOOK_LIST:
                        prevN = nN
                        break
            else: prevN = n-1
        if n<len(state.OETRefData['word_tables'][GreekWordFileName])-1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for nN in range( n+1, len(state.OETRefData['word_tables'][GreekWordFileName]) ):
                    nWordRef = state.OETRefData['word_tables'][GreekWordFileName][nN].split( '\t', 1 )[0]
                    nBBB = nWordRef.split( '_', 1 )[0]
                    if nBBB in TEST_BOOK_LIST:
                        nextN = nN
                        break
            else: nextN = n+1
        prevLink = f'<b><a title="Previous word" href="{getGreekWordpageFilename(prevN, state)}#Top">←</a></b> ' if prevN else ''
        nextLink = f' <b><a title="Next word" href="{getGreekWordpageFilename(nextN, state)}#Top">→</a></b>' if nextN else ''
        oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbbWithNotes}{NARROW_NON_BREAK_SPACE}{C}</a>'''
        parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
        interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}ilr/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
        wordsHtml = f'''{'' if probability else '<div class="unusedWord">'}<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Koine Greek wordlink #{n}{'' if probability else ' <small>(Unused Greek word variant)</small>'}</h1>
<p class="pNav">{prevLink}<b>{greekWord}</b> <a title="Go to Greek word index" href="index.htm">↑</a>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
<p class="link"><a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {tidyBbbb} {C}:{V}</a>
 {probabilityField if TEST_MODE else ''}<b>{greekWord}</b> ({transliterate_Greek(greekWord)}) {translation}{capsField if TEST_MODE else ''}
 Strongs=<a title="Goes to Strongs dictionary" href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a> Lemma=<b>{lemmaLink}</b>
<br> {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}{f'{NEWLINE}<br>  {semanticExtras}' if semanticExtras else ''}</p>
<p class="note"><small>Note: With the help of a companion website, these word pages enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>{'' if probability else f'{NEWLINE}</div><!--unusedWord-->'}'''
        assert '\\' not in wordsHtml, f"{wordsHtml=}"

        if probability: # Now list all the other places where this same Greek word is used
            # other_count = 0
            if len(wordOETGlossesList)>1:
                wordOETGlossesStr = tidyGlossOfGreekWord( "</b>’, ‘<b>".join( wordOETGlossesList ) )
            thisWordNumberList = state.OETRefData['NTFormUsageDict'][(greekWord,roleLetter,morphology)]
            if len(thisWordNumberList) > 100: # too many to list
                maxWordsToShow = 50
                wordsHtml = f'{wordsHtml}\n<h2>Showing the first {maxWordsToShow} out of ({len(thisWordNumberList)-1:,}) uses of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                if len(wordOETGlossesList)>1:
                    wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordOETGlossesStr}</b>’.</p>'''
                    if wordVLTGlossesList != wordOETGlossesList:
                        wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
                else:
                    assert wordOETGlossesList == [OETGlossWordsStr], f"{wordOETGlossesList}  vs {[OETGlossWordsStr]}"
                    wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{OETGlossWordsStr}</b>’.</p>'
                    if VLTGlossWordsStr != OETGlossWordsStr:
                        wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> was always and only glossed as ‘<b>{VLTGlossWordsStr}</b>’)</small>.</p>'
            else: # we can list all uses of the word
                maxWordsToShow = 100
                if len(thisWordNumberList) == 1:
                    wordsHtml = f'{wordsHtml}\n<h2>Only use of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                    # grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][lemma]
                    # lemmaFormsList = sorted( state.OETRefData['NTLemmaFormsDict'][lemma] )
                    # if len(grkLemmaWordRowsList) == 1:
                    #     # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {grkLemmaWordRowsList=} {grkLmmaFormsList=} {lemmaGlossesList=}" )
                    #     assert len(lemmaFormsList) == 1
                    #     assert len(lemmaGlossesList) == 1
                    #     html = f'''{html.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Greek originals.</p>'''
                else:
                    wordsHtml = f'{wordsHtml}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                if len(wordOETGlossesList)>1:
                    wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordOETGlossesList):,} different glosses: ‘<b>{wordOETGlossesStr}</b>’.</p>'''
                    if wordVLTGlossesList != wordOETGlossesList:
                        wordsHtml = f'''{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordVLTGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordVLTGlossesList)}</b>’)</small>.</p>'''
                else:
                    assert wordOETGlossesList == [formattedOETGlossWords], f"{n} {BBB} {C}:{V} {greekWord=} {roleLetter=} {morphology=}: {wordOETGlossesList}  vs {[formattedOETGlossWords]}"
                    wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{tidyGlossOfGreekWord(formattedOETGlossWords)}</b>’.</p>'
                    if formattedVLTGlossWords != formattedOETGlossWords:
                        wordsHtml = f'{wordsHtml}\n<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, the word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> was always and only glossed as ‘<b>{formattedVLTGlossWords}</b>’)</small>.</p>'
            displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
            for oN in thisWordNumberList:
                if oN==n: continue # don't duplicate the word we're making the page for
                oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, _oVLTGlossWords, oOETGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, _oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_tables'][GreekWordFileName][oN].split( '\t' )
                oFormattedContextGlossWords = formatNTContextSpansOETGlossWords( oN, state )
                oBBB, oCVW = oWordRef.split( '_', 1 )
                oC, oVW = oCVW.split( ':', 1 )
                oV, oW = oVW.split( 'w', 1 )
                oTidyBBB = getOETTidyBBB( oBBB )
                oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
                oTidyBbbb = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True )
                oTidyBbbbWithNotes = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True, addNotes=True )
                # if other_count == 0:
                translation = '<small>(no English gloss here)</small>' if oOETGlossWords=='-' else f'''‘{tidyGlossOfGreekWord(oFormattedContextGlossWords)}’'''
                wordsHtml = f'''{wordsHtml}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBbbbWithNotes} {oC}:{oV}</a>''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBbbbWithNotes} {oC}:{oV} word {oW}</a></p>''' \
                    if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else \
                    f'''{wordsHtml}\n<p class="wordLine">{oTidyBbbbWithNotes} {oC}:{oV}''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBbbbWithNotes} {oC}:{oV} word {oW}</a></p>'''
                # other_count += 1
                # if other_count >= 120:
                #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                #     break
                displayCounter += 1
                if displayCounter >= maxWordsToShow: break
            if len(lemmaGlossesList) > len(wordOETGlossesList):
                wordsHtml = f'''{wordsHtml}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLink}’ have {len(lemmaGlossesList):,} different glosses: ‘<b>{tidyGlossOfGreekWord("</b>’, ‘<b>".join(lemmaGlossesList))}</b>’.</p>'''
            elif len(thisWordNumberList) == 1:
                grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][SRLemma]
                grkLemmaFormsList = state.OETRefData['NTLemmaFormsDict'][SRLemma]
                if len(grkLemmaWordRowsList) == 1:
                    # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {grkLemmaWordRowsList=} {grkLemmaFormsList=} {lemmaGlossesList=}" )
                    assert len(grkLemmaFormsList) == 1
                    assert len(lemmaGlossesList) == 1
                    wordsHtml = f'''{wordsHtml.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>', 1)}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> ‘{SRLemma}’ in the Greek originals.</p>'''

            if mainGlossWord not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other words that are glossed similarly
                try:
                    similarWords = (mainGlossWord,) + SIMILAR_GLOSS_WORDS_DICT[mainGlossWord]
                    # print( f"      {mainGlossWord=} {similarWords=}")
                except KeyError: similarWords = (mainGlossWord,)
                extraHTMLList = []
                extraWordSet, extraLemmaSet = set(), set()
                for similarWord in similarWords:
                    nList = state.OETRefData['OETNTGlossWordDict'][similarWord]
                    # print( f'''    {n} {ref} {greekWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nList[:8]=}{'…' if len(nList)>8 else ''}''' )
                    if len(nList) > 1:
                        if similarWord==mainGlossWord: assert n in nList
                        if len(nList)>400:
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"EXCESSIVE {len(nList):,} entries for '{mainGlossWord}' from {similarWord=}")
                        for thisN in nList:
                            if thisN == n: continue # That's the current word row
                            eWordRef, eGreekWord, eSRLemma, _eGrkLemma, _eVLTGlossWordsStr, _eOETGlossWordsStr, _eGlossCaps, _eProbability, _eExtendedStrongs, eRoleLetter, eMorphology, _eTagsStr = state.OETRefData['word_tables'][GreekWordFileName][thisN].split( '\t' )
                            if eRoleLetter == 'None': eRoleLetter = None
                            if eMorphology == 'None': eMorphology = None
                            if eGreekWord!=greekWord or eRoleLetter!=roleLetter or eMorphology!=morphology:
                                eBBB, eCVW = eWordRef.split( '_', 1 )
                                eC, eVW = eCVW.split( ':', 1 )
                                eV, eW = eVW.split( 'w', 1 )
                                eTidyBBB = getOETTidyBBB( eBBB )
                                eTidyBbbb = getOETTidyBBB( eBBB, titleCase=True, allowFourChars=True )

                                eGreekPossibleLink = f'<a title="Go to word page" href="{getGreekWordpageFilename(thisN, state)}#Top">{eGreekWord}</a>' if not TEST_MODE or ALL_TEST_REFERENCE_PAGES or eBBB in TEST_BOOK_LIST else eGreekWord
                                eLemmaLink = f'<a title="View Greek root word" href="../GrkLem/{eSRLemma}.htm#Top">{eSRLemma}</a>' if eSRLemma!=SRLemma else ''
                                eFormattedContextGlossWords = tidyGlossOfGreekWord( formatNTContextSpansOETGlossWords( thisN, state ) )
                                assert '\\' not in eFormattedContextGlossWords, f"{n=} {eFormattedContextGlossWords=}"
                                eTidyRoleMorphology = eTidyMorphology = '' #= eMoodField = eTenseField = eVoiceField = ePersonField = eCaseField = eGenderField = eNumberField = ''
                                if eMorphology:
                                    assert len(eMorphology) == 7, f"Got {eWordRef} '{eGreekWord}' morphology ({len(eMorphology)}) = '{eMorphology}'"
                                    eTidyMorphology = eMorphology[4:] if eMorphology.startswith('....') else eMorphology
                                    eTidyRoleMorphology = f'{eRoleLetter}-{eTidyMorphology}'
                                    usedRoleLetters.add( eRoleLetter )
                                    if eTidyMorphology != '...': usedMorphologies.add( eTidyMorphology )
                                else:
                                    eTidyRoleMorphology = eRoleLetter
                                extraHTMLList.append( f'''<p class="wordLine"><a title="View OET {eTidyBBB} text" href="{'../'*level}OET/byC/{eBBB}_C{eC}.htm#C{eC}V{eV}">{eTidyBBB} {eC}:{eV}</a>'''
f''' <b>{eGreekPossibleLink}</b> ({transliterate_Greek(eGreekWord)}) <small>{eTidyRoleMorphology}</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}'''
f''' ‘{eFormattedContextGlossWords}’'''
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBbbb} {eC}:{eV} word {eW}</a></p>'''
                                    if not TEST_MODE or eBBB in state.preloadedBibles['OET-RV'] else
                                        f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eGreekPossibleLink}’ <small>({eTidyRoleMorphology})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}''' \
f''' ‘{eFormattedContextGlossWords}’''' \
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBbbb} {eC}:{eV} word {eW}</a></p>''' )
                                extraWordSet.add( eGreekPossibleLink )
                                extraLemmaSet.add( eLemmaLink if eLemmaLink else lemmaLink )
                if extraHTMLList:
                    wordsHtml = f'''{wordsHtml}\n<h2 class="otherGreek">Greek words ({len(extraHTMLList):,}) other than {greekWord} <small>({tidyRoleMorphology})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
                    if len(extraHTMLList) > 10:
                        wordsHtml = f'''{wordsHtml}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemma{'' if len(extraLemmaSet)==1 else 's'} altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
                    wordsHtml = f'''{wordsHtml}\n{NEWLINE.join(extraHTMLList)}'''
        assert '\\' not in wordsHtml, f"{wordsHtml=}"
        assert '</span>C1.htm' not in wordsHtml, f"{wordsHtml=}"

        if usedRoleLetters or usedMorphologies: # Add a key at the bottom
            keyHtml = '<p class="key" id="Bottom"><b>Key</b>:'
            for usedRoleLetter in sorted( usedRoleLetters ):
                keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
            for usedMorphology in sorted( usedMorphologies ):
                try:
                    keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
                except KeyError:
                    logging.warning( f"create_Greek_word_pages: Missing {usedMorphology=}")
            keyHtml = f'{keyHtml}</p>'

        # Now put it all together
        top = makeTop( level, None, 'word', None, state ) \
                        .replace( '__TITLE__', f"Greek word ‘{greekWord}’{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' ) \
                        .replace( 'par/"', f'par/{BBB}/C{C}V{V}.htm#Top"' )
        wordsHtml = f'''{top}{wordsHtml}
{keyHtml}
{makeBottom( level, 'word', state )}'''
        checkHtml( 'GreekWordPage', wordsHtml )
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( wordsHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(wordsHtml):,} characters to {output_filename}" )
        wordLinksForIndex.append( f'<a href="{output_filename}">{greekWord}</a>')
        numWordPagesMade += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'''    Created {numWordPagesMade:,}{f"/{len(state.OETRefData['word_tables'][GreekWordFileName])-1:,}" if numWordPagesMade < len(state.OETRefData['word_tables'][GreekWordFileName])-1 else ''} Greek word pages (using {len(state.OETRefData['usedGrkLemmas']):,} Greek lemmas).''' )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'wordIndex', None, state) \
            .replace( '__TITLE__', f"Greek Words Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, words' )
    indexText = ' '.join( wordLinksForIndex )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note">Greek words index <a href="transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Greek Words Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'wordIndex', state )}'''
    checkHtml( 'wordIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    # Create a transliterated index page for this folder
    filename = 'transIndex.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'wordIndex', None, state) \
            .replace( '__TITLE__', f"Transliterated Greek Words Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, words, transliterated' )
    indexText = transliterate_Greek( indexText )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="index.htm">Greek words index</a> Transliterated Greek words index</p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Transliterated Greek Words Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'wordIndex', state )}'''
    checkHtml( 'wordIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_Greek_word_pages


def create_Greek_lemma_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    These end up in OBD/ref/GrkLem/abc.htm

    TODO: Add related lemma info (not just prefixed ones, but adding synonyms, etc.)
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"create_Greek_lemma_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making {len(state.OETRefData['NTLemmaDict']):,} Greek lemma pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    def tidy_Greek_lemma_gloss( engGloss:str ) -> str:
        """
        """
            # .replace( '\\untr ', '<span class="untr">').replace( '\\untr*', '</span>') \
            # .replace( '\\nd ', '<span class="nd">').replace( '\\nd*', '</span>') \
            # .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>') \
        assert '<span class="ul">' not in engGloss # already
        result = ( engGloss
            # .replace( '\\add +', '<span class="addArticle">' )
            # .replace( '\\add -', '<span class="unusedArticle">' )
            # .replace( '\\add =', '<span class="addCopula">' )
            # .replace( '\\add <a title', '__PROTECT__' ) # Enable if required
            # .replace( '\\add <', '<span class="addDirectObject">' )
            # .replace( '__PROTECT__', '\\add <a title' )
            # .replace( '\\add >', '<span class="addExtra">' )
            # .replace( '\\add &', '<span class="addOwner">' )
            .replace( '\\add ', '<span class="add">').replace( '\\add*', '</span>')
            # .replace( '_', '<span class="ul">_</span>')
            )
        return result
    # end of createOETReferencePages.tidy_Greek_lemma_gloss


    lemmaList = sorted( [lemma for lemma in state.OETRefData['NTLemmaDict']] )

    # Now make a page for each Greek lemma (including the variants not used in the translation)
    lemmaLinks:List[str] = [] # Used below to make an index page
    for ll, lemma in enumerate( lemmaList ):
        # print( f"Lemma {ll}: {lemma}" )
        grkLemma = state.OETRefData['NTGreekLemmaDict'][lemma]
        if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and grkLemma not in state.OETRefData['usedGrkLemmas']:
            continue # Don't make this page
        grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][lemma]
        grkLemmaFormsList = sorted( state.OETRefData['NTLemmaFormsDict'][lemma] )
        grkLemmaOETGlossesList = sorted( state.OETRefData['NTLemmaOETGlossesDict'][lemma] )
        grkLemmaVLTGlossesList = sorted( state.OETRefData['NTLemmaVLTGlossesDict'][lemma] )

        def getFirstGreekWordNumber(grk:str,roleLetter:str,morph:str):
            return state.OETRefData['NTFormUsageDict'][(grk,roleLetter,morph)][0]

        usedRoleLetters, usedMorphologies = set(), set()
        output_filename = f'{lemma}.htm'

        prevLL = nextLL = None
        if ll > 1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for LL in range( ll-1, 0, -1 ):
                    LLLemma = lemmaList[LL]
                    LLGrkLemma = state.OETRefData['NTGreekLemmaDict'][LLLemma]
                    if LLGrkLemma in state.OETRefData['usedGrkLemmas']:
                        prevLL = LL
                        break
            else: prevLL = ll-1
        if ll<len(lemmaList)-1:
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                for LL in range( ll+1, len(lemmaList) ):
                    LLLemma = lemmaList[LL]
                    LLGrkLemma = state.OETRefData['NTGreekLemmaDict'][LLLemma]
                    if LLGrkLemma in state.OETRefData['usedGrkLemmas']:
                        nextLL = LL
                        break
            else: nextLL = ll+1
        prevLink = f'<b><a title="Previous lemma" href="{lemmaList[prevLL]}.htm#Top">←</a></b> ' if prevLL else ''
        nextLink = f' <b><a title="Next lemma" href="{lemmaList[nextLL]}.htm#Top">→</a></b>' if nextLL else ''
        lemmasHtml = f'''<h1 id="Top">Greek root word <small>(lemma)</small> ‘{grkLemma}’ ({lemma})</h1>
<p class="pNav">{prevLink}<b>{lemma}</b> <a title="Go to Greek word index" href="index.htm">↑</a>{nextLink}</p>
<p class="summary">This root form (lemma) ‘{grkLemma}’ is used in {'only one form' if len(grkLemmaFormsList)==1 else f'{len(grkLemmaFormsList):,} different forms'} in the Greek originals: {', '.join([f'<a title="View Greek word form" href="../GrkWrd/{getGreekWordpageFilename(getFirstGreekWordNumber(grk,roleLetter,morph), state)}#Top">{grk}</a> <small>({roleLetter}-{morph[4:] if morph.startswith("....") else morph})</small>' for grk,roleLetter,morph in grkLemmaFormsList])}.</p>
<p class="summary">It is glossed in {'only one way' if len(grkLemmaOETGlossesList)==1 else f'{len(grkLemmaOETGlossesList):,} different ways'}: ‘<b>{tidy_Greek_lemma_gloss("</b>’, ‘<b>".join(grkLemmaOETGlossesList))}</b>’.</p>'''
        if grkLemmaVLTGlossesList != grkLemmaOETGlossesList:
            lemmasHtml = f'''{lemmasHtml}<p class="summary"><small>(In <span title="the forthcoming Verified Literal Translation">the VLT</span>, it was glossed in {'only one way' if len(grkLemmaVLTGlossesList)==1 else f'{len(grkLemmaVLTGlossesList):,} different ways'}: ‘<b>{"</b>’, ‘<b>".join(grkLemmaVLTGlossesList)}</b>’.)</small></p>'''

        def makeGreekLemmaHTML( thisLemmaStr:str, thisLemmaRowsList ) -> str:
            """
            The guts of making the lemma page
                put into a function so that we can also re-use it for related words

            Side-effects: udates usedRoleLetters and usedMorphologies
            """
            oRoleSet = set()
            for oN in thisLemmaRowsList:
                _oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, _oVLTGlossWords, _oOETGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_tables'][GreekWordFileName][oN].split( '\t' )
                oRoleSet.add( oRoleLetter )
                # usedRoleLetters.add( oRoleLetter )
            # oRoleLetter remains set to the last value added to the set (which is the only value if len(oRoleSet)==1)

            if len(thisLemmaRowsList) > 100: # too many to list
                maxWordsToShow = 50
                lemmaHTML = f"<h2>Showing the first {maxWordsToShow} out of ({len(thisLemmaRowsList)-1:,}) uses of Greek root word <small>(lemma)</small> ‘{thisLemmaStr}’ {f'<small>({CNTR_ROLE_NAME_DICT[oRoleLetter]})</small> ' if len(oRoleSet)==1 else ''}in the Greek originals</h2>"
            else: # we can list all uses of the word
                maxWordsToShow = 100
                lemmaHTML = f"<h2>Have {len(thisLemmaRowsList):,} {'use' if len(thisLemmaRowsList)==1 else 'uses'} of Greek root word <small>(lemma)</small> ‘{thisLemmaStr}’ {f'<small>({CNTR_ROLE_NAME_DICT[oRoleLetter]})</small> ' if len(oRoleSet)==1 else ''}in the Greek originals</h2>"
            for displayCounter,oN in enumerate( thisLemmaRowsList, start=1 ):
                oWordRef, oGreekWord, _oSRLemma, _oGrkLemma, oVLTGlossWords, oOETGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, oMorphology, _oTagsStr = state.OETRefData['word_tables'][GreekWordFileName][oN].split( '\t' )
                oFormattedContextGlossWords = formatNTContextSpansOETGlossWords( oN, state )
                oBBB, oCVW = oWordRef.split( '_', 1 )
                oC, oVW = oCVW.split( ':', 1 )
                oV, oW = oVW.split( 'w', 1 )
                oTidyBBB = getOETTidyBBB( oBBB )
                oTidyBBBwithNotes = getOETTidyBBB( oBBB, addNotes=True )
                oTidyBbbb = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True )
                oTidyBbbbWithNotes = getOETTidyBBB( oBBB, titleCase=True, allowFourChars=True, addNotes=True )
                oTidyMorphology = oMorphology[4:] if oMorphology.startswith('....') else oMorphology
                usedRoleLetters.add( oRoleLetter )
                if oTidyMorphology != '...': usedMorphologies.add( oTidyMorphology )
                # if other_count == 0:
                oOETLink = f'''<a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBbbbWithNotes} {oC}:{oV}</a>''' \
                                if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] \
                                    else f'{oTidyBbbbWithNotes} {oC}:{oV}'
                oGreekWordLink = f'<a title="Go to word page" href="../GrkWrd/{getGreekWordpageFilename(oN, state)}#Top">{oGreekWord}</a>' if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else oGreekWord
                translation = '<small>(no English gloss here)</small>' if oVLTGlossWords=='-' else f'''‘{tidy_Greek_lemma_gloss(oFormattedContextGlossWords)}’'''
                lemmaHTML = f'''{lemmaHTML}\n<p class="lemmaLine">{oOETLink} <b>{oGreekWordLink}</b> ({transliterate_Greek(oGreekWord)})''' \
                    f"{f' {CNTR_ROLE_NAME_DICT[oRoleLetter].title()}' if len(oRoleSet)>1 else ''} {oTidyMorphology}" \
                    f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBbbb} {oC}:{oV} word {oW}</a></p>'''
                # other_count += 1
                # if other_count >= 120:
                #     lemmaHTML = f'{lemmaHTML}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                #     break
                if displayCounter >= maxWordsToShow: break
            assert '\\' not in lemmaHTML, f"{lemmaHTML=}"
            return lemmaHTML
        # end of createOETReferencePages.create_Greek_lemma_pages.makeGreekLemmaHTML

        lemmasHtml = f"{lemmasHtml}\n{makeGreekLemmaHTML(lemma, grkLemmaWordRowsList)}"

        # Consider related lemmas, e.g., with or without prefix
        this_extended_lemma_list = [lemma]
        for mm, this_second_lemma in enumerate( lemmaList ):
            if this_second_lemma and len(this_second_lemma)>1 and this_second_lemma not in this_extended_lemma_list:
                prefix = None
                if this_second_lemma.endswith( lemma ):
                    prefix = this_second_lemma[:len(this_second_lemma)-len(lemma)]
                elif lemma.endswith( this_second_lemma ):
                    prefix = lemma[:len(lemma)-len(this_second_lemma)]
                if prefix and len(prefix) < 6:
                    if prefix in KNOWN_GREEK_PREFIXES:
                        # print(f"create_Greek_lemma_pages also got lemma '{this_second_lemma}' with prefix '{prefix}' (cf. '{lemma}')")
                        grkLemmaWordRowsList = state.OETRefData['NTLemmaDict'][this_second_lemma]
                        # lemmaFormsList = sorted( state.OETRefData['NTLemmaFormsDict'][this_second_lemma] )
                        # lemmaGlossesList = sorted( state.OETRefData['NTLemmaOETGlossesDict'][this_second_lemma] )
                        this_second_lemma_link = f'<a title="Go to lemma page" href="{this_second_lemma}.htm#Top">{this_second_lemma}</a>'
                        if len(this_extended_lemma_list) == 1:
                            lemmasHtml = f"{lemmasHtml}\n<h1>Other possible lexically-related lemmas</h1>"
                        lemmasHtml = f'''{lemmasHtml}
<h2>Greek root word <small>(lemma)</small> ‘{this_second_lemma}’ <small>with prefix=‘{prefix}’</small></h2>
{makeGreekLemmaHTML(this_second_lemma_link, grkLemmaWordRowsList)}'''
                        this_extended_lemma_list.append( this_second_lemma )
                    # else:
                    #     print(f"create_Greek_lemma_pages ignored potential lemma '{this_second_lemma}' with unrecognised prefix '{prefix}' (cf. '{lemma}')")
        # if len(this_extended_lemma_list) > 1:
        #     print( f"Got {this_extended_lemma_list=}" )

        # Consider other lemmas with similar English glosses
        similarLemmaSet = set()
        for lemmaGloss in grkLemmaOETGlossesList:
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed similarly
                try:
                    similarWords = (lemmaGloss,) + SIMILAR_GLOSS_WORDS_DICT[lemmaGloss]
                    # print( f"      {lemmaGloss=} {similarWords=} {ll} {lemma=} {lemmaGlossesList=}")
                except KeyError: similarWords = (lemmaGloss,)
                for similarWord in similarWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['NTLemmaOETGlossesDict'].items():
                        # NOTE: otherLemmaGlosses contains raw words and well as HTML spans for gloss helpers, etc.
                        if otherLemma != lemma:
                            # print( f"{otherLemma=} {otherLemmaGlosses=}")
                            if similarWord in otherLemmaGlosses:
                                similarLemmaSet.add( otherLemma )
        if similarLemmaSet:
            # print( f"{lemma=} {lemmaGlossesList=} {extraLemmaSet=}" )
            lemmasHtml = f'''{lemmasHtml}
<h1>Lemmas with similar glosses to ‘{grkLemma}’ ({lemma})</h1>'''
            for extraLemma in similarLemmaSet:
                extra_lemma_link = f'<a title="Go to lemma page" href="{extraLemma}.htm#Top">{extraLemma}</a>'
                lemmasHtml = f"{lemmasHtml}\n{makeGreekLemmaHTML(extra_lemma_link, state.OETRefData['NTLemmaDict'][extraLemma])}"

        # Consider other lemmas with contrastive English glosses
        contrastiveLemmaSet = set()
        for lemmaGloss in grkLemmaOETGlossesList:
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed as antonyms
                try:
                    contrastiveWords = CONTRASTIVE_GLOSS_WORDS_DICT[lemmaGloss]
                    # print( f"      {lemmaGloss=} {contrastiveWords=} {ll} {lemma=} {lemmaGlossesList=}")
                except KeyError: contrastiveWords = []
                for contrastiveWord in contrastiveWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['NTLemmaOETGlossesDict'].items():
                        # NOTE: otherLemmaGlosses contains raw words and well as HTML spans for gloss helpers, etc.
                        if otherLemma != lemma:
                            # print( f"{otherLemma=} {otherLemmaGlosses=}")
                            if contrastiveWord in otherLemmaGlosses:
                                assert otherLemma not in similarLemmaSet
                                contrastiveLemmaSet.add( otherLemma )
        if contrastiveLemmaSet:
            # print( f"{lemma=} {lemmaGlossesList=} {extraLemmaSet=}" )
            lemmasHtml = f'''{lemmasHtml}
<h1>Lemmas with contrastive glosses to ‘{grkLemma}’ ({lemma})</h1>'''
            for contrastiveLemma in contrastiveLemmaSet:
                extra_lemma_link = f'<a title="Go to lemma page" href="{contrastiveLemma}.htm#Top">{contrastiveLemma}</a>'
                lemmasHtml = f"{lemmasHtml}\n{makeGreekLemmaHTML(extra_lemma_link, state.OETRefData['NTLemmaDict'][contrastiveLemma])}"
        assert '\\' not in lemmasHtml, f"{lemmalemmasHtmlHTML=}"

        if usedRoleLetters or usedMorphologies: # Add a key at the bottom
            keyHtml = '<p class="key" id="Bottom"><b>Key</b>:'
            for usedRoleLetter in sorted( usedRoleLetters ):
                keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
            for usedMorphology in sorted( usedMorphologies ):
                try:
                    keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
                except KeyError:
                    logging.warning( f"Missing {usedMorphology=}")
            keyHtml = f'{keyHtml}</p>'

        # Now put it all together
        top = makeTop( level, None, 'lemma', None, state ) \
                        .replace( '__TITLE__', f"Greek lemma ‘{lemma}’{' TEST' if TEST_MODE else ''}" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' )
        lemmasHtml = f'''{top}{lemmasHtml}
{keyHtml}
{makeBottom( level, 'lemma', state )}'''
        checkHtml( 'GreekLemmaPage', lemmasHtml )
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( lemmasHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(lemmasHtml):,} characters to {output_filename}" )
        lemmaLinks.append( f'<a href="{output_filename}">{lemma}</a>')
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Created {len(lemmaLinks):,}{f'/{len(lemmaList):,}' if len(lemmaLinks) < len(lemmaList) else ''} Greek lemma pages." )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'lemmaIndex', None, state) \
            .replace( '__TITLE__', f"Greek Lemma Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, lemmas' )
    indexText = ' '.join( lemmaLinks )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note">Greek lemmas index <a href="transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Greek Lemmas Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'lemmaIndex', state )}'''
    checkHtml( 'lemmaIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    # Create transliterated index page for this folder
    filename = 'transIndex.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'lemmaIndex', None, state) \
            .replace( '__TITLE__', f"Transliterated Greek Lemma Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, lemmas, transliterated' )
    indexText = transliterate_Greek( indexText)
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="index.htm">Greek lemmas index</a> Transliterated Greek lemmas index</p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Greek Lemmas Index</h1>
<p class="note">{indexText}</p>
{makeBottom( level, 'lemmaIndex', state )}'''
    checkHtml( 'lemmaIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_Greek_lemma_pages


def create_person_pages( level:int, outputFolderPath:Path, state:State ) -> int:
    """
    Make pages for all the words to link to.

    There's almost identical code in createOETReferencePages() in OpenBibleData createOETReferencePages.py (sadly)
    """
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making person pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    with open( THEOGRAPHIC_INPUT_FOLDER_PATH.joinpath( 'normalised_People.json' ), 'rb' ) as people_file:
        peopleDict = json.load( people_file )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded {len(peopleDict):,} person entries." )

    # Firstly, make a list of all the keys
    peopleKeys = []
    personLinks:List[str] = []
    for personKey in peopleDict:
        if personKey == '__HEADERS__': continue
        if personKey == '__COLUMN_HEADERS__': continue
        peopleKeys.append( personKey )

    # Now make a page for each person
    for n,(personKey,entry) in enumerate( peopleDict.items() ):
        if personKey == '__HEADERS__': continue
        if personKey == '__COLUMN_HEADERS__': continue

        previousLink = f'''<a title="Previous person" href="{peopleKeys[n-3][1:]}.htm#Top">←</a>''' if n>3 else ''
        nextLink = f'''<a title="Next person" href="{peopleKeys[n-1][1:]}.htm#Top">→</a>''' if n<len(peopleDict)-1 else ''

        personName = entry['displayTitle']
        bornYear = f"{entry['birthYear']}" if entry['birthYear'] else ''
        diedYear = f"{entry['deathYear']}" if entry['deathYear'] else ''
        if bornYear.startswith('-'): bornYear = f'{bornYear[1:]} BC' # These are narrow spaces
        elif bornYear: bornYear = f'{bornYear} AD'
        if diedYear.startswith('-'): diedYear = f'{diedYear[1:]} BC'
        elif diedYear: diedYear = f'{diedYear} AD'
        bornStr = f' Born: {bornYear}' if bornYear else '' # These are em-spaces
        diedStr = f' Died: {diedYear}' if diedYear else ''

        bodyHtml = f'''<h1>{personName.replace( "'", '’' )}</h1>
<p class="personName">{livenMD(level, entry['dictText'])}</p>
<p class="personGender">{entry['gender']}{bornStr}{diedStr}</p>'''

        # Now put it all together
        output_filename = f"{personKey[1:]}.htm"
        html = f'''{makeTop( level, None, 'person', None, state )
                                    .replace( '__TITLE__', f"{personName}{' TEST' if TEST_MODE else ''}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} <a title="Go to person index" href="index.htm">↑</a> {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'person', state )}'''
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
        personLinks.append( f'<a href="{output_filename}">{personName}</a>')

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'personIndex', None, state) \
            .replace( '__TITLE__', f"Bible Person Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, person, people' )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Loc/">Bible locations index</a></p>
<h1 id="Top">Bible People Index</h1>
<p class="note">{' '.join(personLinks)}</p>
{makeBottom( level, 'personIndex', state )}'''
    checkHtml( 'personIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_person_pages function


def create_location_pages( level:int, outputFolderPath:Path, state:State ) -> int:
    """
    Make pages for all the words to link to.

    There's almost identical code in createOETReferencePages() in OpenBibleData createOETReferencePages.py (sadly)
    """
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making location pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    with open( THEOGRAPHIC_INPUT_FOLDER_PATH.joinpath( 'normalised_Places.json' ), 'rb' ) as locations_file:
        locationsDict = json.load( locations_file )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Loaded {len(locationsDict):,} location entries." )

    # Firstly, make a list of all the keys
    placeKeys = []
    locationLinks:List[str] = []
    for placeKey in locationsDict:
        if placeKey == '__HEADERS__': continue
        if placeKey == '__COLUMN_HEADERS__': continue
        placeKeys.append( placeKey )

    # Now make a page for each location
    for n,(placeKey,entry) in enumerate( locationsDict.items() ):
        if placeKey == '__HEADERS__': continue
        if placeKey == '__COLUMN_HEADERS__': continue

        previousLink = f'''<a title="Previous location" href="{placeKeys[n-3][1:]}.htm#Top">←</a>''' if n>3 else ''
        nextLink = f'''<a title="Next location" href="{placeKeys[n-1][1:]}.htm#Top">→</a>''' if n<len(locationsDict)-1 else ''

        placeName = entry['displayTitle']
        commentStr = f" {entry['comment']}" if entry['comment'] else ''

        adjustedArticleText = entry['dictText'].replace( 'Authorized Version', 'King James Bible' )
        locationVersions = f'''<p class="locationVersions">KJB,ESV = ‘{entry['kjvName']}’</p>''' \
                        if entry['kjvName']==entry['esvName'] else \
                       f'''<p class="locationVersions">KJB=‘{entry['kjvName']}’ ESV=‘{entry['esvName']}’</p>'''

        bodyHtml = f'''<h1>{placeName.replace( "'", '’' )}</h1>
<p class="locationName">{livenMD(level, adjustedArticleText)}</p>
<p class="locationType">{entry['featureType']}{f"/{entry['featureSubType']}" if entry['featureSubType'] else ''}{f' {commentStr}' if commentStr else ''}</p>
{locationVersions}'''

        # Now put it all together
        output_filename = f"{placeKey[1:]}.htm"
        html = f'''{makeTop( level, None, 'location', None, state )
                                    .replace( '__TITLE__', f"{placeName}{' TEST' if TEST_MODE else ''}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} <a title="Go to locations index" href="index.htm">↑</a> {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'location', state )}'''
        filepath = outputFolderPath.joinpath( output_filename )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
        locationLinks.append( f'<a href="{output_filename}">{placeName}</a>')

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'locationIndex', None, state) \
            .replace( '__TITLE__', f"Bible Location Index{' TEST' if TEST_MODE else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, location, locations, place, places' )
    indexHtml = f'''{top}
<p class="note"><b><a href="../">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/">Hebrew words index</a> <a href="../HebWrd/transIndex.htm">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../GrkWrd/">Greek words index</a> <a href="../GrkWrd/transIndex.htm">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../Per/">Bible people index</a></p>
<h1 id="Top">Bible Locations Index</h1>
<p class="note">{' '.join(locationLinks)}</p>
{makeBottom( level, 'locationIndex', state )}'''
    checkHtml( 'locationIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.create_location_pages function


mdLinkRegex = re.compile( '\\[(.+?)\\]\\((.+?)\\)' )
def livenMD( level:int, mdText:str ) -> str:
    """
    Take markdown style links like '[Gen. 35:16](/gen#Gen.35.16)'
        from person and location pages
        and convert them to HTML links.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"livenMD( {level}, {mdText[:140]}… )" )

    # Firstly, try to improve the overall formatting
    mdText = mdText.replace( '\n\n', '</p><p class="markdown">' ).replace( '\n', '<br>' )
    mdText = mdText.replace( "'", '’' ) # Improve apostrophes

    # Now liven links
    count = 0
    searchStartIndex = 0
    while True: # Look for links that we could maybe liven
        match = mdLinkRegex.search( mdText, searchStartIndex )
        if not match:
            break
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  {match=} {match.groups()=}" )
        readableRef, mdLinkTarget = match.group(1), match.group(2)
        mdLinkTarget = mdLinkTarget.split( '#', 1 )[1]
        if mdLinkTarget.count( '.' ) == 2: # Then it's almost certainly an OSIS B/C/V ref
            OSISBkCode, C, V = mdLinkTarget.split( '.' )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISBkCode )
            ourLinkTarget = f"{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}V{V}"
        else:
            assert mdLinkTarget.count( '.' ) == 1 # Then it's almost certainly an OSIS B/C ref
            OSISBkCode, C = mdLinkTarget.split( '.' )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISBkCode )
            ourLinkTarget = f'{BBB}.htm#C{C}'
        ourLink = f'<a title="View OET reference" href="{ourLinkTarget}">{readableRef}</a>'
        mdText = f'''{mdText[:match.start()]}{ourLink}{mdText[match.end():]}'''
        searchStartIndex = match.end() + 10 # We've added at least that many characters
        count += 1
    return mdText
# end of createOETReferencePages.livenMD function


def removeHebrewVowelPointing( text:str ) -> str:
    """
    Return the text with vowel pointing removed.
    """
    h = Hebrew.Hebrew( text )
    resultA = h.removeVowelPointing( removeMetegOrSiluq=True )
    return h.removeOtherMarks( resultA, removeSinShinDots=False )
# end of apply_Clear_Macula_OT_glosses.removeHebrewVowelPointing



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETReferencePages object
    pass
# end of createOETReferencePages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the createOETReferencePages object
    pass
# end of createOETReferencePages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createOETReferencePages.py
