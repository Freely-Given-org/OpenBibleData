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
"""
from gettext import gettext as _
from typing import Dict, List, Tuple
from pathlib import Path
import os
from collections import defaultdict
import re
import json
import logging

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint

import sys
sys.path.append( '../../BibleTransliterations/Python/' )
from BibleTransliterations import transliterate_Greek

from settings import State, TEST_MODE, ALL_TEST_REFERENCE_PAGES, SITE_NAME
from html import makeTop, makeBottom, checkHtml
from Bibles import getOurTidyBBB


LAST_MODIFIED_DATE = '2024-02-20' # by RJH
SHORT_PROGRAM_NAME = "createOETReferencePages"
PROGRAM_NAME = "OpenBibleData createOETReferencePages functions"
PROGRAM_VERSION = '0.58'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# BACKSLASH = '\\'
NEWLINE = '\n'
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

COMMON_ENGLISH_WORDS_LIST = ( # Ignore the most common words
    'God','Jesus','Lord', 'Joshua',
    'the','¬the','that','this','which','¬which','these',
    'and','for','but','if','as','therefore','in_order_that','because',
    'is','also',
    'to','in','with','from','by','on','into',
    'not','all','saying','said','having',
    'what','who',
    'you', 'he','we','they','I','she','you_all',
            'him','us','them','me','her',
    'your','his','our','their','my',
    )
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
    (('cry','cries','crying','cried'),('weep','weeps','weeping','weeped','mourn','mourns','mourning','mourned')),
    (('daughter','daughters'),('child','children')),
    (('devil',),('Satan',)),
    (('disbelief',),('unbelief','disbelieve')),
    (('enlighten','enlightened','enlightening'),('light','illuminate','illuminated','illuminating')),
    (('few',),('remnant','remainder')),
    (('flesh',),('body','bodies','carnal','meat')),
    (('fleshly',),('worldly',)),
    (('fulfilment','fulfillment'),('fullness',)),
    (('fullness',),('fulfillment','fulfilment')),
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
    (('logical',),('sensible','logic','logically')),
    (('light','lights'),('lamp','lamps')),
    (('lip','lips'),('mouth','mouths')),
    (('mind','minds'),('heart','hearts')),
    (('mourn','mourns','mourning','mourned'),('weep','weeps','weeping','weeped','cry','cries','crying','cried')),
    (('mouth','mouths'),('lips','lip','tongue')),
    (('pagan','pagans'),('Gentile','Gentiles','Greeks')),
    (('path','paths'),('way','ways','road','roads')),
    (('patriach','patriarchs'),('ancestor','ancestors','elders')),
    (('priest','priests'),('chief_priest','chief_priests')),
    (('purity',),('holiness',)),
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
    (('slave','slaves'),('servant','house_servant','servants','house_servants','attendant','attendants')),
    (('son','sons'),('child','children')),
    (('sperm',),('seed',)),
    (('suddenly',),('immediately',)),
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

    # Here we create our Dicts and Lists that we'll make the reference pages from
    # First make a list of each place the same Greek word (and matching morphology) is used
    # NOTE: The word table has Matthew at the beginning (whereas the OET places John and Mark at the beginning) so we do them first
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Finding all uses of {len(state.OETRefData['word_table'])-1:,} words…" )
    state.OETRefData['formUsageDict'], state.OETRefData['lemmaDict'] = defaultdict(list), defaultdict(list)
    state.OETRefData['lemmaFormsDict'] = defaultdict(set)
    state.OETRefData['formGlossesDict'], state.OETRefData['lemmaGlossesDict'] = defaultdict(set), defaultdict(set)
    state.OETRefData['glossWordDict'] = defaultdict(list)
    state.OETRefData['lemmaGreekDict'] = {}
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'JHN' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma
        elif state.OETRefData['formUsageDict']: break # Must have already finished John
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if columns_string.startswith( 'MRK' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma
        elif columns_string.startswith( 'LUK' ): break # Must have already finished Mark
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        if not columns_string.startswith( 'JHN' ) and not columns_string.startswith( 'MRK' ):
            _ref, greekWord, SRLemma, GrkLemma, glossWordsStr, _glossCaps, probability, _extendedStrongs, roleLetter, morphology, _tagsStr = columns_string.split( '\t' )
            if probability:
                formattedGlossWords = formatSpansGlossWords( glossWordsStr )
                formMorph3Tuple = (greekWord, roleLetter, None if morphology=='None' else morphology)
                state.OETRefData['formUsageDict'][formMorph3Tuple].append( n )
                state.OETRefData['lemmaDict'][SRLemma].append( n )
                state.OETRefData['lemmaFormsDict'][SRLemma].add( formMorph3Tuple )
                state.OETRefData['formGlossesDict'][formMorph3Tuple].add( formattedGlossWords )
                state.OETRefData['lemmaGlossesDict'][SRLemma].add( formattedGlossWords )
                for someGlossWord in glossWordsStr.split( ' '):
                    if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                        assert n not in state.OETRefData['glossWordDict'][someGlossWord]
                        state.OETRefData['glossWordDict'][someGlossWord].append( n )
                if SRLemma in state.OETRefData['lemmaGreekDict']:
                    # assert state.OETRefData['lemmaGreekDict'][SRLemma] == GrkLemma, f"{n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}"
                    if state.OETRefData['lemmaGreekDict'][SRLemma] != GrkLemma:
                        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    {n=} {_ref} {SRLemma=} {GrkLemma=} {state.OETRefData['lemmaGreekDict'][SRLemma]=}" )
                state.OETRefData['lemmaGreekDict'][SRLemma] = GrkLemma

    make_Greek_word_pages( level+1, outputFolderPath.joinpath( 'GrkWrd/' ), state )
    make_Greek_lemma_pages( level+1, outputFolderPath.joinpath( 'GrkLem/' ), state )

    make_person_pages( level+1, outputFolderPath.joinpath( 'Per/' ), state )
    make_location_pages( level+1, outputFolderPath.joinpath( 'Loc/' ), state )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'referenceIndex', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}OpenBibleData Reference Index" ) \
            .replace( '__KEYWORDS__', 'Bible, reference' )
    indexHtml = f'''{top}
<h1 id="Top">Reference Pages</h1>
<h2>{SITE_NAME}</h2>
<p class="note"><a href="GrkWrd/">Greek words pages</a></p>
<p class="note"><a href="GrkLem/">Greek lemmas pages</a></p>
<p class="note"><a href="Per/">Bible people pages</a></p>
<p class="note"><a href="Loc/">Bible locations pages</a></p>
{makeBottom( level, 'referenceIndex', state )}'''
    checkHtml( 'referenceIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    del state.OETRefData # No longer needed
    return True
# end of createOETReferencePages.createOETReferencePages


def formatSpansGlossWords( glossWords:str ) -> str:
    """
    Put HTML spans about the various parts of the gloss Words string
        to replace our pre, helper, and post special character markers.
    """
    return glossWords \
                .replace( '/', '<span class="glossHelper">', 1 ).replace( '/', '</span>', 1 ) \
                .replace( '˱', '<span class="glossPre">', 1 ).replace( '˲', '</span>', 1 ) \
                .replace( '‹', '<span class="glossPost">', 1 ).replace( '›', '</span>', 1 )
# end of createOETReferencePages.formatSpansGlossWords


NUM_BEFORE_AND_AFTER = 3
def formatContextSpansGlossWords( rowNum:int, state:State ) -> str:
    """
    Get this and previous gloss words in context.

    TODO: Need to take GlossOrder into account
    """
    fOriginalWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][rowNum].split( '\t' )
    # print( f"formatContextSpansGlossWords( {rowNum:,} ) at {fOriginalWordRef}" )
    fOriginalBCV = fOriginalWordRef.split( 'w', 1 )[0]

    glossWordsList = [f'<b>{formatSpansGlossWords(fGlossWords)}</b>']

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN -= 1
        if fN < 1: break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability == 'None': fProbability = None
        if fProbability and fGlossWords[0]!='¬':
            glossWordsList.insert( 0, formatSpansGlossWords(fGlossWords) )
            rowCount += 1

    rowCount, fN = 0, rowNum
    while rowCount < NUM_BEFORE_AND_AFTER:
        fN += 1
        if fN >= len(state.OETRefData['word_table']): break
        fWordRef, _fGreekWord, _fSRLemma, _fGrkLemma, fGlossWords, _fGlossCaps, fProbability, _fExtendedStrongs, _fRoleLetter, _fMorphology, _fTagsStr = state.OETRefData['word_table'][fN].split( '\t' )
        if not fWordRef.startswith( fOriginalBCV ): break # Stay in this verse
        # print( f"{fWordRef} {fProbability=} {fGlossWords=}" )
        if fProbability == 'None': fProbability = None
        if fProbability and fGlossWords[0]!='¬':
            glossWordsList.append( formatSpansGlossWords(fGlossWords) )
            rowCount += 1

    return ' '.join( glossWordsList )
# end of createOETReferencePages.formatSpansGlossWords


def make_Greek_word_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"make_Greek_word_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Checking {len(state.OETRefData['word_table'])-1:,} word pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    # Now make a page for each Greek word (including the variants not used in the translation)
    numWordPagesMade = 0
    wordLinks:List[str] = []
    for n, columns_string in enumerate( state.OETRefData['word_table'][1:], start=1 ):
        # print( n, columns_string )
        usedRoleLetters, usedMorphologies = set(), set()
        output_filename = f'{n}.htm'
        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Got '{columns_string}' for '{output_filename}'" )
        if columns_string: # not a blank line (esp. at end)
            ref, greekWord, SRLemma, _GrkLemma, glossWordsStr, glossCaps, probability, extendedStrongs, roleLetter, morphology, tagsStr = columns_string.split( '\t' )
            formattedGlossWords = formatSpansGlossWords( glossWordsStr )
            formattedContextGlossWords = formatContextSpansGlossWords( n, state )
            mainGlossWord = None
            for someGlossWord in glossWordsStr.split( ' '):
                if '/' not in someGlossWord and '˱' not in someGlossWord and '‹' not in someGlossWord: # We only want the main words
                    assert not mainGlossWord
                    mainGlossWord = someGlossWord
            if extendedStrongs == 'None': extendedStrongs = None
            if roleLetter == 'None': roleLetter = None
            if morphology == 'None': morphology = None

            BBB, CVW = ref.split( '_', 1 )
            if TEST_MODE and not ALL_TEST_REFERENCE_PAGES and BBB not in state.preloadedBibles['OET-RV']:
                continue # In some test modes, we only make the relevant word pages
            C, VW = CVW.split( ':', 1 )
            V, W = VW.split( 'w', 1 )
            ourTidyBBB = getOurTidyBBB( BBB )
            ourTidyBbb = getOurTidyBBB( BBB, titleCase=True )

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
            translation = '<small>(no English gloss here)</small>' if glossWordsStr=='-' else f'''‘{formattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
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
            lemmaLink = f'<a title="View Greek root word" href="../GrkLem/{SRLemma}.htm#Top">{SRLemma}</a>'
            lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][SRLemma] )
            wordGlossesList = sorted( state.OETRefData['formGlossesDict'][(greekWord,roleLetter,morphology)] )

            prevN = nextN = None
            if n > 1:
                if TEST_MODE and not ALL_TEST_REFERENCE_PAGES: 
                    for nN in range( n-1, 0, -1 ):
                        nWordRef = state.OETRefData['word_table'][nN].split( '\t', 1 )[0]
                        nBBB = nWordRef.split( '_', 1 )[0]
                        if nBBB in state.preloadedBibles['OET-RV']:
                            prevN = nN
                            break
                else: prevN = n-1
            if n<len(state.OETRefData['word_table']):
                if TEST_MODE and not ALL_TEST_REFERENCE_PAGES:
                    for nN in range( n+1, len(state.OETRefData['word_table']) ):
                        nWordRef = state.OETRefData['word_table'][nN].split( '\t', 1 )[0]
                        nBBB = nWordRef.split( '_', 1 )[0]
                        if nBBB in state.preloadedBibles['OET-RV']:
                            nextN = nN
                            break
                else: nextN = n+1
            prevLink = f'<b><a title="Previous word" href="{prevN}.htm#Top">←</a></b> ' if prevN else ''
            nextLink = f' <b><a title="Next word" href="{nextN}.htm#Top">→</a></b>' if nextN else ''
            oetLink = f''' <a title="View whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#C{C}">{ourTidyBbb}{NARROW_NON_BREAK_SPACE}{C}</a>'''
            parallelLink = f''' <b><a title="View verse in many parallel versions" href="{'../'*level}par/{BBB}/C{C}V{V}.htm#Top">║</a></b>'''
            interlinearLink = f''' <b><a title="View interlinear verse word-by-word" href="{'../'*level}ilr/{BBB}/C{C}V{V}.htm#Top">═</a></b>''' if BBB in state.booksToLoad['OET'] else ''
            wordsHtml = f'''{'' if probability else '<div class="unusedWord">'}<h2>Open English Translation (OET)</h2>\n<h1 id="Top">Wordlink #{n}{'' if probability else ' <small>(Unused Greek word variant)</small>'}</h1>
<p class="pNav">{prevLink}<b>{greekWord}</b> <a href="index.htm">↑</a>{nextLink}{oetLink}{parallelLink}{interlinearLink}</p>
<p class="link"><a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[BBB]}{C.zfill(3)}{V.zfill(3)}">SR GNT {ourTidyBBB} {C}:{V}</a>
 {probabilityField if TEST_MODE else ''}<b>{greekWord}</b> ({transliterate_Greek(greekWord)}) {translation}{capsField if TEST_MODE else ''}
 Strongs=<a title="Goes to Strongs dictionary" href="https://BibleHub.com/greek/{strongs}.htm">{extendedStrongs}</a> Lemma=<b>{lemmaLink}</b><br>
 {roleField}{moodField}{tenseField}{voiceField}{personField}{caseField}{genderField}{numberField}{f'<br>  {semanticExtras}' if semanticExtras else ''}</p>
<p class="note"><small>Note: With the help of a companion website, these word pages enable you to click through all the way back to photographs of the original manuscripts that the <em>Open English Translation</em> New Testament is translated from.
If you go to the <em>Statistical Restoration</em> Greek page (by clicking on the SR Bible reference above), from there you can click on the original manuscript numbers (e.g., 𝔓1, 01, 02, etc.) in the <i>Witness</i> column there, to see their transcription of the original Greek page.
From there, you can click on the 🔍 magnifying glass icon to view a photograph of the actual leaf of the codex.
This is all part of the commitment of the <em>Open English Translation</em> team to be transparent about all levels of the Bible translation process right back to the original manuscripts.</small></p>{'' if probability else f'{NEWLINE}</div><!--unusedWord-->'}'''

            if probability: # Now list all the other places where this same Greek word is used
                # other_count = 0
                thisWordNumberList = state.OETRefData['formUsageDict'][(greekWord,roleLetter,morphology)]
                if len(thisWordNumberList) > 100: # too many to list
                    maxWordsToShow = 50
                    wordsHtml = f'{wordsHtml}\n<h2>Showing the first {maxWordsToShow} out of ({len(thisWordNumberList)-1:,}) uses of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                    if len(wordGlossesList)>1:
                        wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [glossWordsStr], f"{wordGlossesList}  vs {[glossWordsStr]}"
                        wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{glossWordsStr}</b>’.</p>'
                else: # we can list all uses of the word
                    maxWordsToShow = 100
                    if len(thisWordNumberList) == 1:
                        wordsHtml = f'{wordsHtml}\n<h2>Only use of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                        # lemmaRowsList = state.OETRefData['lemmaDict'][lemma]
                        # lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][lemma] )
                        # if len(lemmaRowsList) == 1:
                        #     # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {lemmaRowsList=} {lemmaFormsList=} {lemmaGlossesList=}" )
                        #     assert len(lemmaFormsList) == 1
                        #     assert len(lemmaGlossesList) == 1
                        #     html = f'''{html.replace(lemmaLink, f'{lemmaLink}<sup>*</sup>')}\n<p class="note"><sup>*</sup>Note: This is also the only occurrence of the word root <small>(lemma)</small> '{lemma}' in the Greek originals.</p>'''
                    else:
                        wordsHtml = f'{wordsHtml}\n<h2>Other uses ({len(thisWordNumberList)-1:,}) of identical word form {greekWord} <small>({tidyRoleMorphology})</small> in the Greek originals</h2>'
                    if len(wordGlossesList)>1:
                        wordsHtml = f'''{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> has {len(wordGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(wordGlossesList)}</b>’.</p>'''
                    else:
                        assert wordGlossesList == [formattedGlossWords], f"{n} {BBB} {C}:{V} {greekWord=} {roleLetter=} {morphology=}: {wordGlossesList}  vs {[formattedGlossWords]}"
                        wordsHtml = f'{wordsHtml}\n<p class="summary">The word form ‘{greekWord}’ <small>({tidyRoleMorphology})</small> is always and only glossed as ‘<b>{formattedGlossWords}</b>’.</p>'
                displayCounter = 0 # Don't use enumerate on the next line, because there is a condition inside the loop
                for oN in thisWordNumberList:
                    if oN==n: continue # don't duplicate the word we're making the page for
                    oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, _oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                    oFormattedContextGlossWords = formatContextSpansGlossWords( oN, state )
                    oBBB, oCVW = oWordRef.split( '_', 1 )
                    oC, oVW = oCVW.split( ':', 1 )
                    oV, oW = oVW.split( 'w', 1 )
                    oTidyBBB = getOurTidyBBB( oBBB )
                    # if other_count == 0:
                    translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''‘{oFormattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
                    wordsHtml = f'''{wordsHtml}\n<p class="wordLine"><a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBB} {oC}:{oV}</a>''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>''' \
                        if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else \
                        f'''{wordsHtml}\n<p class="wordLine">{oTidyBBB} {oC}:{oV}''' \
f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
                    # other_count += 1
                    # if other_count >= 120:
                    #     html = f'{html}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                    #     break
                    displayCounter += 1
                    if displayCounter >= maxWordsToShow: break
                if len(lemmaGlossesList) > len(wordGlossesList):
                    wordsHtml = f'''{wordsHtml}\n<p class="lemmaGlossesSummary">The various word forms of the root word (lemma) ‘{lemmaLink}’ have {len(lemmaGlossesList):,} different glosses: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>'''
                elif len(thisWordNumberList) == 1:
                    lemmaRowsList = state.OETRefData['lemmaDict'][SRLemma]
                    lemmaFormsList = state.OETRefData['lemmaFormsDict'][SRLemma]
                    if len(lemmaRowsList) == 1:
                        # print( f"{ref} '{greek}' ({glossWords}) {lemma=} {lemmaRowsList=} {lemmaFormsList=} {lemmaGlossesList=}" )
                        assert len(lemmaFormsList) == 1
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
                        nList = state.OETRefData['glossWordDict'][similarWord]
                        # print( f'''    {n} {ref} {greekWord} '{mainGlossWord}' {f'{similarWord=} ' if similarWord!=mainGlossWord else ''}({len(nList)}) {nList[:8]=}{'…' if len(nList)>8 else ''}''' )
                        if len(nList) > 1:
                            if similarWord==mainGlossWord: assert n in nList
                            if len(nList)>400:
                                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"EXCESSIVE {len(nList):,} entries for '{mainGlossWord}' from {similarWord=}")
                            for thisN in nList:
                                if thisN == n: continue # That's the current word row
                                eWordRef, eGreekWord, eSRLemma, _eGrkLemma, eGlossWordsStr, _eGlossCaps, _eProbability, _eExtendedStrongs, eRoleLetter, eMorphology, _eTagsStr = state.OETRefData['word_table'][thisN].split( '\t' )
                                if eRoleLetter == 'None': eRoleLetter = None
                                if eMorphology == 'None': eMorphology = None
                                if eGreekWord!=greekWord or eRoleLetter!=roleLetter or eMorphology!=morphology:
                                    eBBB, eCVW = eWordRef.split( '_', 1 )
                                    eC, eVW = eCVW.split( ':', 1 )
                                    eV, eW = eVW.split( 'w', 1 )
                                    eTidyBBB = getOurTidyBBB( eBBB )

                                    eGreekPossibleLink = f'<a title="Go to word page" href="{thisN}.htm#Top">{eGreekWord}</a>' if ALL_TEST_REFERENCE_PAGES or eBBB in state.preloadedBibles['OET-RV'] else eGreekWord
                                    eLemmaLink = f'<a title="View Greek root word" href="../GrkLem/{eSRLemma}.htm#Top">{eSRLemma}</a>' if eSRLemma!=SRLemma else ''
                                    eFormattedContextGlossWords = formatContextSpansGlossWords( thisN, state )
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
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBBB} {eC}:{eV} word {eW}</a></p>'''
                                        if not TEST_MODE or eBBB in state.preloadedBibles['OET-RV'] else
                                            f'''<p class="wordLine">{eTidyBBB} {eC}:{eV} ‘{eGreekPossibleLink}’ <small>({eTidyRoleMorphology})</small>{f' Lemma={eLemmaLink}' if eLemmaLink else ''}''' \
f''' ‘{eFormattedContextGlossWords}’''' \
f''' <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[eBBB]}{eC.zfill(3)}{eV.zfill(3)}">SR GNT {eTidyBBB} {eC}:{eV} word {eW}</a></p>''' )
                                    extraWordSet.add( eGreekPossibleLink )
                                    extraLemmaSet.add( eLemmaLink if eLemmaLink else lemmaLink )
                    if extraHTMLList:
                        wordsHtml = f'''{wordsHtml}\n<h2 class="otherGreek">Greek words ({len(extraHTMLList):,}) other than {greekWord} <small>({tidyRoleMorphology})</small> with a gloss related to ‘{mainGlossWord}’</h2>'''
                        if len(extraHTMLList) > 10:
                            wordsHtml = f'''{wordsHtml}\n<p class="summary">Have {len(extraWordSet):,} other words{f" ({', '.join(extraWordSet)})" if len(extraWordSet)<30 else ''} with {len(extraLemmaSet):,} lemma{'' if len(extraLemmaSet)==1 else 's'} altogether ({', '.join(sorted(extraLemmaSet))})</p>'''
                        wordsHtml = f'''{wordsHtml}\n{NEWLINE.join(extraHTMLList)}'''

            if usedRoleLetters or usedMorphologies: # Add a key at the bottom
                keyHtml = '<p class="key" id="Bottom"><b>Key</b>:'
                for usedRoleLetter in sorted( usedRoleLetters ):
                    keyHtml = f'{keyHtml} <b>{usedRoleLetter}</b>={CNTR_ROLE_NAME_DICT[usedRoleLetter]}'
                for usedMorphology in sorted( usedMorphologies ):
                    try:
                        keyHtml = f"{keyHtml} <b>{usedMorphology}</b>={CNTR_MORPHOLOGY_NAME_DICT[usedMorphology.upper()]}"
                    except KeyError:
                        logging.warning( f"make_Greek_word_pages: Missing {usedMorphology=}")
                keyHtml = f'{keyHtml}</p>'

            # Now put it all together
            top = makeTop( level, None, 'word', None, state ) \
                            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek word ‘{greekWord}’" ) \
                            .replace( '__KEYWORDS__', 'Bible, word' ) \
                            .replace( 'par/"', f'par/{BBB}/C{C}V{V}.htm#Top"' )
            wordsHtml = f'''{top}{wordsHtml}
{keyHtml}
{makeBottom( level, 'word', state )}'''
            with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
                html_output_file.write( wordsHtml )
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"      Wrote {len(wordsHtml):,} characters to {output_filename}" )
            wordLinks.append( f'<a href="{output_filename}">{greekWord}</a>')
            numWordPagesMade += 1
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"    Created {numWordPagesMade:,} word pages." )

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'wordIndex', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek Word Index" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, words' )
    indexHtml = f'''{top}
<p class="note"><a href="../">Reference pages</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas pages</a></p>
<p class="note"><a href="../Per/">Bible people pages</a></p>
<p class="note"><a href="../Loc/">Bible locations pages</a></p>
<h1 id="Top">Greek Words Index</h1>
<p class="note">{' '.join(sorted(wordLinks))}</p>
{makeBottom( level, 'wordIndex', state )}'''
    checkHtml( 'wordIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.make_Greek_word_pages


def make_Greek_lemma_pages( level:int, outputFolderPath:Path, state:State ) -> None:
    """
    These end up in OBD/ref/GrkLem/abc.htm

    TODO: Add related lemma info (not just prefixed ones, but adding synonyms, etc.)
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"make_Greek_lemma_pages( {outputFolderPath}, {state.BibleVersions} )" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Making {len(state.OETRefData['lemmaDict']):,} lemma pages…" )

    try: os.makedirs( outputFolderPath )
    except FileExistsError: pass # it was already there

    lemmaList = sorted( [lemma for lemma in state.OETRefData['lemmaDict']] )

    # Now make a page for each Greek lemma (including the variants not used in the translation)
    lemmaLinks:List[str] = []
    for ll, lemma in enumerate( lemmaList ):
        # print( ll, lemma )
        grkLemma = state.OETRefData['lemmaGreekDict'][lemma]
        lemmaRowsList = state.OETRefData['lemmaDict'][lemma]
        lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][lemma] )
        lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][lemma] )

        def getFirstWordNumber(grk:str,roleLetter:str,morph:str):
            return state.OETRefData['formUsageDict'][(grk,roleLetter,morph)][0]

        usedRoleLetters, usedMorphologies = set(), set()
        output_filename = f'{lemma}.htm'

        prevLink = f'<b><a title="Previous lemma" href="{lemmaList[ll-1]}.htm#Top">←</a></b> ' if ll>0 else ''
        nextLink = f' <b><a title="Next lemma" href="{lemmaList[ll+1]}.htm#Top">→</a></b>' if ll<len(lemmaList)-1 else ''
        lemmasHtml = f'''<h1 id="Top">Greek root word <small>(lemma)</small> ‘{grkLemma}’ ({lemma})</h1>
<p class="pNav">{prevLink}<b>{lemma}</b> <a href="index.htm">↑</a>{nextLink}</p>
<p class="summary">This root form (lemma) ‘{grkLemma}’ is used in {'only one form' if len(lemmaFormsList)==1 else f'{len(lemmaFormsList):,} different forms'} in the Greek originals: {', '.join([f'<a title="View Greek word form" href="../GrkWrd/{getFirstWordNumber(grk,roleLetter,morph)}.htm#Top">{grk}</a> <small>({roleLetter}-{morph[4:] if morph.startswith("....") else morph})</small>' for grk,roleLetter,morph in lemmaFormsList])}.</p>
<p class="summary">It is glossed in {'only one way' if len(lemmaGlossesList)==1 else f'{len(lemmaGlossesList):,} different ways'}: ‘<b>{"</b>’, ‘<b>".join(lemmaGlossesList)}</b>’.</p>
'''

        def makeLemmaHTML( thisLemmaStr:str, thisLemmaRowsList ) -> str:
            """
            The guts of making the lemma page
                put into a function so that we can also re-use it for related words

            Side-effects: udates usedRoleLetters and usedMorphologies
            """
            oRoleSet = set()
            for oN in thisLemmaRowsList:
                _oWordRef, _oGreekWord, _oSRLemma, _oGrkLemma, _oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, _oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
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
                oWordRef, oGreekWord, _oSRLemma, _oGrkLemma, oGlossWords, _oGlossCaps,_oProbability, _oExtendedStrongs, oRoleLetter, oMorphology, _oTagsStr = state.OETRefData['word_table'][oN].split( '\t' )
                oFormattedContextGlossWords = formatContextSpansGlossWords( oN, state )
                oBBB, oCVW = oWordRef.split( '_', 1 )
                oC, oVW = oCVW.split( ':', 1 )
                oV, oW = oVW.split( 'w', 1 )
                oTidyBBB = getOurTidyBBB( oBBB )
                oTidyMorphology = oMorphology[4:] if oMorphology.startswith('....') else oMorphology
                usedRoleLetters.add( oRoleLetter )
                if oTidyMorphology != '...': usedMorphologies.add( oTidyMorphology )
                # if other_count == 0:
                oOETLink = f'''<a title="View OET {oTidyBBB} text" href="{'../'*level}OET/byC/{oBBB}_C{oC}.htm#C{oC}V{oV}">{oTidyBBB} {oC}:{oV}</a>''' \
                                if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] \
                                    else f'{oTidyBBB} {oC}:{oV}'
                oGreekWordLink = f'<a title="Go to word page" href="../GrkWrd/{oN}.htm#Top">{oGreekWord}</a>' if not TEST_MODE or oBBB in state.preloadedBibles['OET-RV'] else oGreekWord
                translation = '<small>(no English gloss here)</small>' if oGlossWords=='-' else f'''‘{oFormattedContextGlossWords.replace('_','<span class="ul">_</span>')}’'''
                lemmaHTML = f'''{lemmaHTML}\n<p class="lemmaLine">{oOETLink} <b>{oGreekWordLink}</b> ({transliterate_Greek(oGreekWord)})''' \
                    f"{f' {CNTR_ROLE_NAME_DICT[oRoleLetter].title()}' if len(oRoleSet)>1 else ''} {oTidyMorphology}" \
                    f''' {translation} <a title="Go to Statistical Restoration Greek page" href="https://GreekCNTR.org/collation/?v={CNTR_BOOK_ID_MAP[oBBB]}{oC.zfill(3)}{oV.zfill(3)}">SR GNT {oTidyBBB} {oC}:{oV} word {oW}</a></p>'''
                # other_count += 1
                # if other_count >= 120:
                #     lemmaHTML = f'{lemmaHTML}\n<p class="summary">({len(thisWordNumberList)-other_count-1:,} more examples not listed)</p>'
                #     break
                if displayCounter >= maxWordsToShow: break
            return lemmaHTML
        # end of createOETReferencePages.make_Greek_lemma_pages.makeLemmaHTML

        lemmasHtml = f"{lemmasHtml}\n{makeLemmaHTML(lemma, lemmaRowsList)}"

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
                        # print(f"make_Greek_lemma_pages also got lemma '{this_second_lemma}' with prefix '{prefix}' (cf. '{lemma}')")
                        lemmaRowsList = state.OETRefData['lemmaDict'][this_second_lemma]
                        # lemmaFormsList = sorted( state.OETRefData['lemmaFormsDict'][this_second_lemma] )
                        # lemmaGlossesList = sorted( state.OETRefData['lemmaGlossesDict'][this_second_lemma] )
                        this_second_lemma_link = f'<a title="Go to lemma page" href="{this_second_lemma}.htm#Top">{this_second_lemma}</a>'
                        if len(this_extended_lemma_list) == 1:
                            lemmasHtml = f"{lemmasHtml}\n<h1>Other possible lexically-related lemmas</h1>"
                        lemmasHtml = f'''{lemmasHtml}
<h2>Greek root word <small>(lemma)</small> ‘{this_second_lemma}’ <small>with prefix=‘{prefix}’</small></h2>
{makeLemmaHTML(this_second_lemma_link, lemmaRowsList)}'''
                        this_extended_lemma_list.append( this_second_lemma )
                    # else:
                    #     print(f"make_Greek_lemma_pages ignored potential lemma '{this_second_lemma}' with unrecognised prefix '{prefix}' (cf. '{lemma}')")
        # if len(this_extended_lemma_list) > 1:
        #     print( f"Got {this_extended_lemma_list=}" )

        # Consider other lemmas with similar English glosses
        similarLemmaSet = set()
        for lemmaGloss in lemmaGlossesList:
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed similarly
                try:
                    similarWords = (lemmaGloss,) + SIMILAR_GLOSS_WORDS_DICT[lemmaGloss]
                    # print( f"      {lemmaGloss=} {similarWords=} {ll} {lemma=} {lemmaGlossesList=}")
                except KeyError: similarWords = (lemmaGloss,)
                for similarWord in similarWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['lemmaGlossesDict'].items():
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
                lemmasHtml = f"{lemmasHtml}\n{makeLemmaHTML(extra_lemma_link, state.OETRefData['lemmaDict'][extraLemma])}"

        # Consider other lemmas with constrastive English glosses
        contrastiveLemmaSet = set()
        for lemmaGloss in lemmaGlossesList:
            if lemmaGloss not in COMMON_ENGLISH_WORDS_LIST: # Ignore the most common words
                # List other lemmas that are glossed as antonyms
                try:
                    contrastiveWords = CONTRASTIVE_GLOSS_WORDS_DICT[lemmaGloss]
                    # print( f"      {lemmaGloss=} {contrastiveWords=} {ll} {lemma=} {lemmaGlossesList=}")
                except KeyError: contrastiveWords = []
                for contrastiveWord in contrastiveWords:
                    for otherLemma,otherLemmaGlosses in state.OETRefData['lemmaGlossesDict'].items():
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
                lemmasHtml = f"{lemmasHtml}\n{makeLemmaHTML(extra_lemma_link, state.OETRefData['lemmaDict'][contrastiveLemma])}"

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
                        .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek lemma ‘{lemma}’" ) \
                        .replace( '__KEYWORDS__', 'Bible, word' )
        lemmasHtml = f'''{top}{lemmasHtml}
{keyHtml}
{makeBottom( level, 'lemma', state )}'''
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( lemmasHtml )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(lemmasHtml):,} characters to {output_filename}" )
        lemmaLinks.append( f'<a href="{output_filename}">{lemma}</a>')

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'lemmaIndex', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Greek Lemma Index" ) \
            .replace( '__KEYWORDS__', 'Bible, Greek, lemmas' )
    indexHtml = f'''{top}
<p class="note"><a href="../">Reference pages</a></p>
<p class="note"><a href="../GrkWrd/">Greek words pages</a></p>
<p class="note"><a href="../Per/">Bible people pages</a></p>
<p class="note"><a href="../Loc/">Bible locations pages</a></p>
<h1 id="Top">Greek Lemmas Index</h1>
<p class="note">{' '.join(sorted(lemmaLinks))}</p>
{makeBottom( level, 'lemmaIndex', state )}'''
    checkHtml( 'lemmaIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.make_Greek_lemma_pages


def make_person_pages( level:int, outputFolderPath:Path, state:State ) -> int:
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
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{personName}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} <a href="index.htm">↑</a> {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'person', state )}'''
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
        personLinks.append( f'<a href="{output_filename}">{personName}</a>')

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'personIndex', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Bible Person Index" ) \
            .replace( '__KEYWORDS__', 'Bible, person, people' )
    indexHtml = f'''{top}
<p class="note"><a href="../">Reference pages</a></p>
<p class="note"><a href="../GrkWrd/">Greek words pages</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas pages</a></p>
<p class="note"><a href="../Loc/">Bible locations pages</a></p>
<h1 id="Top">Bible People Index</h1>
<p class="note">{' '.join(personLinks)}</p>
{makeBottom( level, 'personIndex', state )}'''
    checkHtml( 'personIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.make_person_pages function


def make_location_pages( level:int, outputFolderPath:Path, state:State ) -> int:
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
                                    .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}{placeName}" )
                                    .replace( '__KEYWORDS__', 'Bible, word' )
                                    }
<p class="prevNextLinks">{previousLink} <a href="index.htm">↑</a> {nextLink}</p>
{bodyHtml}
<p class="thanks"><small>Grateful thanks to <a href="https://Viz.Bible">Viz.Bible</a> for these links and this data.</small></p>
{makeBottom( level, 'location', state )}'''
        with open( outputFolderPath.joinpath(output_filename), 'wt', encoding='utf-8' ) as html_output_file:
            html_output_file.write( html )
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Wrote {len(html):,} characters to {output_filename}" )
        locationLinks.append( f'<a href="{output_filename}">{placeName}</a>')

    # Create index page for this folder
    filename = 'index.htm'
    filepath = outputFolderPath.joinpath( filename )
    top = makeTop( level, None, 'locationIndex', None, state) \
            .replace( '__TITLE__', f"{'TEST ' if TEST_MODE else ''}Bible Location Index" ) \
            .replace( '__KEYWORDS__', 'Bible, location, locations, place, places' )
    indexHtml = f'''{top}
<p class="note"><a href="../">Reference pages</a></p>
<p class="note"><a href="../GrkWrd/">Greek words pages</a></p>
<p class="note"><a href="../GrkLem/">Greek lemmas pages</a></p>
<p class="note"><a href="../Per/">Bible people pages</a></p>
<h1 id="Top">Bible Locations Index</h1>
<p class="note">{' '.join(locationLinks)}</p>
{makeBottom( level, 'locationIndex', state )}'''
    checkHtml( 'locationIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )
# end of createOETReferencePages.make_location_pages function


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
