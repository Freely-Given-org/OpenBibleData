#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2024 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
#
# createTopicPages.py
#
# Module handling OpenBibleData createTopicPages functions
#
# Copyright (C) 2024-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+OBD@gmail.com>
# This source code is marked with CC0 1.0 Universal.
#    To view a copy of this license, visit http://creativecommons.org

"""
Module handling createTopicPages functions.

CHANGELOG:
    2024-11-01 First attempt
    2024-11-09 Added some headings
    2025-02-03 Accept and process lemma page links
    2025-06-27 Fix bug where we were forcing the load of Bible books where not wanted
    2025-09-07 Add Kingdom pages
    2025-10-29 Add an index for kingdom pages
    2026-01-07 Added OET Logo
    2026-03-01 Added IMPORTANT people index
    2026-06-01 Improve unusual book codes (like Yac) and improve navigation
    2026-08-22 Import convertVerseEntryListToHtml directly from openbibledata_rust (convert.py deleted)
    2026-08-25 The OETHandlers functions are now imported from the Rust openbibledata_rust module (the Python OETHandlers.py was deleted).
    2026-09-03 Stop applying the Heb/Grk grammatical colourisation classes on topic pages because their CSS doesn't style them -- the shared dark-mode rules were painting those words unreadably.
    2026-09-15 ESFM word-link livening is now fused (single-pass) into openbibledata_rust.convertVerseEntryListToHtml via its new livenWordLinks/colouriseWordClasses keyword args, so the old livenOETWordLinks calls in the topical-passage hot paths have been removed.
    2026-10-30 Add forty passage collections covering Christian doctrine and everyday discipleship, God’s character, discernment, service and daily relationships.
                    Prefer Yahweh in topic titles and headings when selected passages use the name.
    2026-10-30 Repair kingdom scripture and people-index destinations.
    2026-10-30 Identify the topic, edition and reference when passage retrieval fails.
    2026-10-30 Link the people, places and dictionary entries tagged in selected passages.
    2026-10-31 Add approved kingdom readings and verified person/place navigation.
    2026-10-31 Connect kingdom browsing to the available dictionary indexes.
"""
from pathlib import Path
import os

import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from bible_organisational_system import InternalBibleEntryList

from oetPassages import renderOETLVPassage
from navigation import scriptureLink
from studyReferences import topicFilename,topicReferenceMaterial,ENTITY_FOLDER
from referenceEntities import loadReferenceEntities,entityLink,kingdomArticleLinks,KINGDOM_ENTITIES
from referencePassages import parseReferenceSelection,renderReferencePassage
from referenceIndexes import referenceIndexLinks
from settings import State
from Bibles import getBibleMapperMaps
from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations, \
                    removeDuplicateCVids, \
                    makeTop, makeBottom, checkHtml
from openbibledata_rust import convertVerseEntryListToHtml, getOETTidyBBB


LAST_MODIFIED_DATE = '2026-10-30' # by RJH
SHORT_PROGRAM_NAME = "createTopicPages"
PROGRAM_NAME = "OpenBibleData createTopicPages functions"
PROGRAM_VERSION = '0.41'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

BACKSLASH = '\\'
NEWLINE = '\n'
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '


TOPIC_TABLE = {
    'Advent week one': ['JER_33:14-16', 'PSA_25:1-9', 'TH1_3:9-13', 'LUK_21:25-36'],
    'Advent week two': ['MAL_3:1-4', 'LUK_1:67-79', 'PHP_1:3-11', 'LUK_3:1-6', 'PSA_80'],
    'Advent week three': ['ZEP_3:14-20', 'ISA_12:2-6', 'PHP_4:4-7', 'LUK_3:7-18'],
    'Advent week four': ['MIC_5:2-5a', 'LUK_1:39-56', 'HEB_10:5-10', 'REV_22:6-21'],
    'Advent Christmas': ['ISA_9:2-7', 'PSA_96', 'TIT_2:11-14', 'LUK_2:1-20'],
    'Advent revelation (epiphany)': ['ISA_60:1-6', 'PSA_72', 'EPH_3:1-12', 'MAT_2:1-12'],
    'Advent (all)': ['JER_33:14-16', 'PSA_25:1-9', 'TH1_3:9-13', 'LUK_21:25-36',
                        'MAL_3:1-4', 'LUK_1:67-79', 'PHP_1:3-11', 'LUK_3:1-6', 'PSA_80',
                        'ZEP_3:14-20', 'ISA_12:2-6', 'PHP_4:4-7', 'LUK_3:7-18',
                        'MIC_5:2-5a', 'LUK_1:39-56', 'HEB_10:5-10', 'REV_22:6-21',
                        'ISA_9:2-7', 'PSA_96', 'TIT_2:11-14', 'LUK_2:1-20',
                        'ISA_60:1-6', 'PSA_72', 'EPH_3:1-12', 'MAT_2:1-12'],
    'Basic salvation': ['ROM_6:22-23', 'ROM_3:22-23', 'JHN_3:14-16', 'REV_3:19-21'],
    'Repentance': ['MRK_1:14-15','MRK_6:12',
                        'MAT_3:1-2','MAT_3:8','MAT_4:17','MAT_9:13','MAT_12:41','LUK_5:32','LUK_13:3-5','LUK_17:3','LUK_24:46-47',
                        'ACT_2:38','ACT_3:19','ACT_5:31','ACT_11:18','ACT_17:30','ACT_20:21','ACT_26:19-20',
                        'ROM_2:4',
                        'CO2_7:9-10','CO2_12:20-21',
                        'TI2_2:25','PE2_3:9','HEB_6:1',
                        'REV_2:5','REV_3:3','REV_3:19',
                    'H3 For further word studies:',
                        'HebLem/shūⱱ','HebLem/nāḩam',
                        'GrkLem/metanoia','GrkLem/strefō'],
    # Coverage informed by common statements of faith and discipleship outlines:
    # https://www.eauk.org/about-us/how-we-work/basis-of-faith
    # https://www.navigators.org/resource/the-wheel-illustration/
    # These are passage collections, with brief thematic headings rather than doctrinal conclusions.
    # References use Readers’ Version chapter/verse numbering; the renderer maps the Literal Version.
    # Prefer Yahweh in titles and headings when any selected passage on that page uses the name.
    'Scripture and Yahweh’s word': [
                    'H3 Yahweh speaking through the scriptures',
                        'EXO_24:3-8','TI2_3:14-17','PE2_1:16-21',
                    'H3 Truth and lasting authority',
                        'ISA_40:6-8','MAT_5:17-20','JHN_17:14-19',
                    'H3 The scriptures and Yeshua/Jesus',
                        'LUK_24:25-32','JHN_5:36-40'],
    'Yahweh, Father, Son and Holy Spirit (Trinity)': [
                    'H3 Yahweh, the one God',
                        'DEU_6:4-9','ISA_45:18-23',
                    'H3 The Father and the Son',
                        'JHN_1:1-18','JHN_10:25-30','CO1_8:4-6',
                    'H3 The Father, the Son and the Holy Spirit',
                        'MAT_3:13-17','MAT_28:16-20','JHN_14:15-26','CO2_13:11-13'], # OET numbers the closing blessing as 13:13.
    'Creation and humanity in Yahweh’s image': [
                    'H3 Yahweh creating and sustaining the world',
                        'GEN_1:1-5','PSA_104:24-30','COL_1:15-20',
                    'H3 Human dignity and responsibility',
                        'GEN_1:26-31','GEN_2:15-25','PSA_8:3-9',
                    'H3 Treating people as Yahweh’s image-bearers',
                        'GEN_9:1-7','JAM_3:7-12'],
    'Sin and our need of salvation': [
                    'H3 Disobedience and the human heart',
                        'GEN_3:1-19','MRK_7:14-23',
                    'H3 The reach and consequences of sin',
                        'ISA_59:1-8','ROM_3:9-26','ROM_5:12-21',
                    'H3 Mercy and confession',
                        'PSA_51:1-12','EPH_2:1-10','JN1_1:5-10'],
    'Yeshua/Jesus, divine and human': [
                    'H3 His birth',
                        'MAT_1:18-25','LUK_1:26-38',
                    'H3 His identity',
                        'JHN_1:1-18','JHN_20:24-31','COL_2:6-10','HEB_1:1-12',
                    'H3 His humanity and humility',
                        'PHP_2:5-11','HEB_2:14-18','HEB_4:14-16'],
    'The cross, atonement and reconciliation with Yahweh': [
                    'H3 Suffering and giving his life',
                        'ISA_53:4-12','MRK_10:35-45','LUK_23:32-49',
                    'H3 Forgiveness and reconciliation',
                        'ROM_3:21-26','ROM_5:6-11','CO2_5:14-21',
                    'H3 Sacrifice, victory and a changed life',
                        'COL_2:13-15','HEB_9:11-15','PE1_2:21-25'],
    'The resurrection and ascension of Yeshua/Jesus': [
                    'H3 The empty tomb and the risen Yeshua/Jesus',
                        'LUK_24:1-12','LUK_24:36-49','JHN_20:19-31',
                    'H3 The resurrection and our hope',
                        'CO1_15:1-8','CO1_15:12-28','ROM_6:3-11',
                    'H3 Ascension and intercession',
                        'ACT_1:1-11','EPH_1:15-23','HEB_7:23-28'],
    'Grace, faith and good works': [
                    'H3 Receiving Yahweh’s gift',
                        'ROM_3:21-31','ROM_4:1-8','EPH_2:1-10',
                    'H3 Faith expressed in action',
                        'GAL_5:1-6','JAM_2:14-26',
                    'H3 Grace shaping our lives',
                        'TIT_2:11-14','TIT_3:3-8','PHP_2:12-16'],
    'New birth, adoption and assurance': [
                    'H3 New birth and new life',
                        'JHN_1:9-13','JHN_3:1-21','TIT_3:3-7','PE1_1:3-9',
                    'H3 Becoming God’s children',
                        'ROM_8:12-17','GAL_4:4-7','JN1_3:1-3',
                    'H3 Confidence in God',
                        'JHN_10:22-30','ROM_8:31-39','JN1_5:9-13'],
    'The Holy Spirit and spiritual gifts': [
                    'H3 The promised Spirit',
                        'EZE_36:25-27','JHN_14:15-26','JHN_16:7-15','ACT_2:1-21',
                    'H3 Life and witness by the Spirit',
                        'ACT_1:6-8','ROM_8:1-17','GAL_5:16-26',
                    'H3 Gifts used to build others up',
                        'CO1_12:4-27','CO1_13:1-13','PE1_4:7-11'],
    'The church, fellowship and unity': [
                    'H3 A people gathered around Yeshua/Jesus',
                        'MAT_16:13-20','ACT_2:41-47','EPH_2:11-22','PE1_2:4-10',
                    'H3 One body with many members',
                        'JHN_17:20-26','CO1_12:12-27','EPH_4:1-16',
                    'H3 Sharing life and encouraging one another',
                        'ROM_12:3-13','COL_3:12-17','HEB_10:19-25'],
    'Baptism': [
                    'H3 Yeshua/Jesus and baptism',
                        'MAT_3:13-17','MAT_28:16-20',
                    'H3 Baptism in the early assemblies',
                        'ACT_2:36-41','ACT_8:26-40','ACT_10:44-48','ACT_16:25-34',
                    'H3 Baptism and life in the Messiah',
                        'ROM_6:1-14','GAL_3:23-29','COL_2:8-15','PE1_3:18-22'],
    'The Lord’s dinner (communion)': [
                    'H3 Passover and the last dinner',
                        'EXO_12:1-14','MAT_26:17-30','LUK_22:14-20',
                    'H3 Sharing the bread and the cup',
                        'ACT_2:42-47','ACT_20:7-12','CO1_10:14-22',
                    'H3 Remembering, proclaiming and examining ourselves',
                        'CO1_11:17-34'],
    'The return of Yeshua/Jesus, judgement and new creation': [
                    'H3 His return and our readiness',
                        'MAT_24:36-51','ACT_1:6-11','TH1_4:13-18','TH1_5:1-11',
                    'H3 Resurrection and judgement',
                        'DAN_12:1-3','JHN_5:24-29','MAT_25:31-46','REV_20:11-15',
                    'H3 New creation and lasting hope',
                        'ROM_8:18-25','PE2_3:8-13','REV_21:1-8','REV_22:1-5'],
    'Following Yeshua/Jesus and obeying him': [
                    'H3 The call and cost of following',
                        'MRK_1:16-20','LUK_9:23-26','LUK_14:25-33',
                    'H3 Hearing and doing',
                        'MAT_7:21-27','JHN_14:15-24','JAM_1:22-27',
                    'H3 Remaining in him and serving others',
                        'JHN_15:1-17','MRK_10:35-45','ROM_12:1-2'],
    'Reading, studying and living the scriptures': [
                    'H3 Learning and remembering',
                        'DEU_6:4-9','JOS_1:7-9','PSA_1:1-6','PSA_119:9-16',
                    'H3 Reading carefully and together',
                        'NEH_8:1-12','ACT_17:10-12','TI1_4:11-16',
                    'H3 Putting the message into practice',
                        'TI2_3:14-17','COL_3:12-17','JAM_1:19-27'],
    'Prayer and fasting': [
                    'H3 Learning to pray',
                        'MAT_6:5-18','LUK_11:1-13',
                    'H3 Persistence, humility and God’s will',
                        'LUK_18:1-14','LUK_22:39-46','JN1_5:14-15',
                    'H3 Prayer and fasting in community',
                        'ACT_13:1-3','PHP_4:4-9','TI1_2:1-8','JAM_5:13-18'],
    'Worship and thanksgiving': [
                    'H3 Praising Yahweh together',
                        'PSA_95:1-7','PSA_100','PSA_150',
                    'H3 Worship in spirit, truth and daily life',
                        'JHN_4:19-26','ROM_12:1-2','HEB_13:15-16',
                    'H3 Gratitude and praise in the assembly',
                        'EPH_5:15-21','COL_3:12-17','TH1_5:16-24','REV_5:9-14'],
    'Holiness, spiritual growth and the fruit of the Spirit': [
                    'H3 A life set apart for Yahweh',
                        'LEV_19:1-18','PE1_1:13-21','TH1_4:1-12',
                    'H3 Putting off the old life and putting on the new',
                        'EPH_4:17-32','COL_3:1-17',
                    'H3 Growing in character and love',
                        'GAL_5:13-26','PHP_1:3-11','PE2_1:3-11'],
    'Forgiveness and reconciliation with others': [
                    'H3 Receiving and extending forgiveness',
                        'MAT_6:9-15','MAT_18:21-35','COL_3:12-15',
                    'H3 Addressing wrongs and restoring relationships',
                        'MAT_5:21-26','MAT_18:15-20','LUK_17:1-4','GAL_6:1-5',
                    'H3 Kindness and peace instead of revenge',
                        'EPH_4:25-32','ROM_12:14-21'],
    'Loving neighbours and enemies': [
                    'H3 Love of Yahweh and neighbour',
                        'LEV_19:9-18','MRK_12:28-34','LUK_10:25-37',
                    'H3 Love for enemies',
                        'MAT_5:38-48','LUK_6:27-36','ROM_12:14-21',
                    'H3 Compassion, justice and practical care',
                        'MIC_6:6-8','JAM_2:1-17','JN1_3:11-18'],
    'Stewardship, contentment and generosity': [
                    'H3 Caring for what Yahweh entrusts to us',
                        'GEN_2:15-17','PSA_24:1-6','PE1_4:7-11',
                    'H3 Money, possessions and contentment',
                        'MAT_6:19-34','LUK_12:13-21','TI1_6:6-19',
                    'H3 Sharing willingly and caring for people in need',
                        'DEU_15:7-11','ACT_4:32-37','CO2_8:1-15','CO2_9:6-15'],
    'Evangelism, mission and making disciples': [
                    'H3 Good news for all nations',
                        'GEN_12:1-3','ISA_49:5-6','MAT_28:16-20','LUK_24:44-49',
                    'H3 Witness through words and conduct',
                        'ACT_1:6-8','ROM_10:9-17','COL_4:2-6','PE1_3:13-16',
                    'H3 Teaching and equipping others',
                        'TH1_2:7-12','TI2_2:1-7','EPH_4:11-16'],
    'Trials, temptation and perseverance': [
                    'H3 Resisting temptation',
                        'MAT_4:1-11','CO1_10:1-13','JAM_1:12-18','EPH_6:10-18',
                    'H3 Trusting Yahweh in suffering',
                        'PSA_46:1-11','ROM_5:1-5','JAM_1:2-8','PE1_4:12-19',
                    'H3 Endurance and hope',
                        'ROM_8:18-39','CO2_4:7-18','HEB_12:1-13'],
    'Yahweh’s holiness and majesty': [
                    'H3 Encountering Yahweh’s holiness',
                        'EXO_3:1-6','ISA_6:1-8',
                    'H3 Yahweh’s greatness and glory',
                        'PSA_99:1-9','ISA_40:12-26','REV_4:1-11',
                    'H3 Approaching Yahweh with reverence',
                        'HEB_12:18-29','REV_15:1-4'],
    'Yahweh’s love, mercy and faithfulness': [
                    'H3 Yahweh’s compassion and patience',
                        'EXO_34:5-9','PSA_103:8-18',
                    'H3 Remembering Yahweh’s promises',
                        'DEU_7:6-11','PSA_89:1-8','LAM_3:19-26',
                    'H3 Knowing and responding to Yahweh’s love',
                        'ROM_5:6-11','EPH_3:14-21','JN1_4:7-21'],
    'Yahweh’s sovereignty and providence': [
                    'H3 Yahweh’s rule over the world',
                        'PSA_115:1-11','DAN_4:34-37','ACT_17:22-31',
                    'H3 Human plans and Yahweh’s purposes',
                        'GEN_50:15-21','PRO_16:1-9','ROM_8:26-30',
                    'H3 Trusting Yahweh’s care for our lives',
                        'MAT_6:25-34','MAT_10:26-31','JAM_4:13-17'],
    'Wisdom, guidance and decision-making': [
                    'H3 Seeking wisdom from Yahweh',
                        'PRO_2:1-15','PRO_3:1-12','JAM_1:5-8',
                    'H3 Listening to counsel and deciding together',
                        'PRO_15:22-33','ACT_15:22-29',
                    'H3 Learning to choose what is good',
                        'ROM_12:1-2','PHP_1:9-11','JAM_3:13-18'],
    'Testing teaching and spiritual discernment': [
                    'H3 Examining claims and their fruit',
                        'DEU_13:1-5','MAT_7:15-23','ACT_17:10-12',
                    'H3 Holding to the good message about the Messiah',
                        'GAL_1:6-10','COL_2:6-10',
                    'H3 Testing messages and holding on to what is good',
                        'JN1_4:1-6','TH1_5:19-22','TI2_4:1-5'],
    'Humility and serving others': [
                    'H3 Giving up pride and self-importance',
                        'LUK_18:9-14','PHP_2:1-11',
                    'H3 The example of Yeshua/Jesus',
                        'JHN_13:1-17',
                    'H3 Humility in our choices and relationships',
                        'LUK_14:7-14','GAL_5:13-15','JAM_4:6-10','PE1_5:5-7'],
    'Leadership and care in the church': [
                    'H3 Leading by serving and caring',
                        'MRK_10:35-45','JHN_21:15-19','PE1_5:1-4',
                    'H3 Character and qualifications',
                        'TI1_3:1-13','TIT_1:5-9',
                    'H3 Responsibility, accountability and support',
                        'ACT_20:17-35','TI1_5:17-22','HEB_13:7-17'],
    'The priesthood and ministry of all believers': [
                    'H3 A people called to belong to Yahweh',
                        'EXO_19:3-6','PE1_2:4-10','REV_1:4-6',
                    'H3 Approaching Yahweh and offering our service',
                        'HEB_10:19-25','HEB_13:15-16',
                    'H3 Every member contributing',
                        'ROM_12:3-8','CO1_12:12-27','PE1_4:7-11'],
    'Hospitality and welcoming strangers': [
                    'H3 Welcoming the foreigner',
                        'LEV_19:33-34','DEU_10:17-19',
                    'H3 Sharing our tables and our lives',
                        'LUK_14:12-24','ROM_12:9-13','HEB_13:1-3',
                    'H3 Receiving and supporting fellow workers',
                        'ACT_16:11-15','PE1_4:7-11','JN3_1:5-8'],
    'Work, diligence and everyday witness': [
                    'H3 Work, skill and useful service',
                        'GEN_2:15-17','EXO_35:30-35','EPH_4:25-28',
                    'H3 Diligence and responsible conduct',
                        'PRO_6:6-11','TH1_4:9-12','TH2_3:6-13',
                    'H3 Honesty, fair treatment and our public witness',
                        'DEU_25:13-16','JAM_5:1-6','COL_4:5-6'],
    'Truthfulness and wise speech': [
                    'H3 Speaking truth and building others up',
                        'EXO_23:1-3','PRO_12:17-22','EPH_4:25-32',
                    'H3 Listening before speaking',
                        'JAM_1:19-21','PRO_15:1-7','PRO_18:13-21',
                    'H3 The power and responsibility of our words',
                        'MAT_12:33-37','JAM_3:1-12','COL_4:2-6'],
    'Christian freedom, conscience and disagreements': [
                    'H3 Commands, traditions and differing convictions',
                        'MAT_15:1-20','ROM_14:1-12',
                    'H3 Considering how our choices affect others',
                        'ROM_14:13-23','CO1_8:1-13','CO1_10:23-33',
                    'H3 Freedom and loving service',
                        'GAL_5:1-6','GAL_5:13-15','COL_2:16-23'],
    'Marriage, singleness and faithfulness': [
                    'H3 Marriage and its commitments',
                        'GEN_2:18-25','MAT_19:3-12',
                    'H3 Love, faithfulness and mutual care',
                        'PRO_5:15-23','EPH_5:21-33','HEB_13:1-6',
                    'H3 Marriage, singleness and devotion to Yahweh',
                        'CO1_7:1-16','CO1_7:25-35'],
    'Family life and passing on faith': [
                    'H3 Teaching and remembering across generations',
                        'DEU_6:4-9','PSA_78:1-8','TI2_1:3-7',
                    'H3 Children, parents and care in the home',
                        'MRK_10:13-16','EPH_6:1-4','COL_3:18-21',
                    'H3 Honouring and supporting relatives',
                        'MRK_7:6-13','TI1_5:3-8'],
    'Justice and defending the vulnerable': [
                    'H3 Worship and the practice of justice',
                        'ISA_1:10-20','AMO_5:21-24','ZEC_7:8-14',
                    'H3 Fair hearings and honest judgements',
                        'EXO_23:1-9','DEU_16:18-20','PRO_31:8-9',
                    'H3 Defending people who are mistreated',
                        'PSA_82:1-8','JER_22:13-17','JAM_1:22-27'],
    'Rest and the Sabbath': [
                    'H3 Creation, rest and the Sabbath command',
                        'GEN_2:1-3','EXO_20:8-11','DEU_5:12-15',
                    'H3 Yeshua/Jesus, the Sabbath and doing good',
                        'MRK_2:23-28','MRK_3:1-6','LUK_13:10-17',
                    'H3 Finding rest and considering special days',
                        'MAT_11:25-30','ROM_14:1-6','COL_2:16-23','HEB_4:1-11'],
    'Predestination and ‘once saved, always saved’': ['PSA_136:1-2','PSA_138:7-8',
                                'MAT_7:21-23', 'MAT_10:21-22', 'MAT_25:40-41',
                                'MRK_4:16-17',
                                'JHN_6:35-37', 'JHN_6:44-45', 'JHN_10:28-29','JHN_14:16-17',
                                'ROM_5:9-10', 'ROM_8:5-8', 'ROM_8:38-39', 'ROM_11:17-22',
                                'CO1_2:14-15', 'CO1_9:26-27',
                                'GAL_5:3-4',
                                'EPH_1:4-9', 'EPH_1:13-14','EPH_4:29-30',
                                'TI1_2:1-8', 'TI1_4:1-2',
                                'TI2_2:10',
                                'TIT_2:9-12',
                                'HEB_3:11-12','HEB_6:1-8','HEB_9:11-12','HEB_10:26-31',
                                'PE2_2:20-22','PE2_3:1-18',
                                'JN1_1:6-7','JN1_5:11-13',
                                'JAM_5:19-20',
                                'REV_3:4-5'],
    'Yeshua/Jesus not God (Christadelphian)': ['H3 Claim: <span style="background-color:khaki;">Jesus died</span>', 'CO1_15:3-4', 'H3 Claim: <span style="background-color:lightBlue;">God cannot die</span>', 'TI1_1:17',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was tempted </span>', 'HEB_4:14-15', 'H3 Claim: <span style="background-color:lightBlue;">God cannot be tempted</span>', 'JAM_1:13',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was seen</span>', 'JHN_1:29', 'H3 Claim: <span style="background-color:lightBlue;">No man has ever seen God</span>', 'JN1_4:12',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus was and is a man</span>', 'TI1_2:5', 'H3 Claim: <span style="background-color:lightBlue;">God is not a man</span>', 'NUM_23:18-19',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus had to grow and learn</span>', 'HEB_5:8-9', 'H3 Claim: <span style="background-color:lightBlue;">God doesn’t ever need to learn</span>', 'ISA_40:28',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus needs salvation</span>', 'HEB_5:7', 'H3 Claim: <span style="background-color:lightBlue;">God does not</span>', 'HEB_5:7',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus grew weary</span>', 'JHN_4:5-6', 'H3 Claim: <span style="background-color:lightBlue;">God can’t grow weary</span>', 'ISA_40:28',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus slept</span>', 'MAT_8:23-24', 'H3 Claim: <span style="background-color:lightBlue;">God doesn’t slumber</span>', 'PSA_121:2-4',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus wasn’t all powerful</span>', 'JHN_5:18-19', 'H3 Claim: <span style="background-color:lightBlue;">God is all powerful (omnipotent)</span>', 'ISA_45:5-7',
                                        'H3 Claim: <span style="background-color:khaki;">Jesus wasn’t all knowing</span>', 'MRK_13:31-32', 'H3 Claim: <span style="background-color:lightBlue;">God is all knowing (omniscient)</span>', 'ISA_46:9-10',
                                        'H3 Only God can do that', 'MRK_2:1-12', 'MAT_9:1-9', 'LUK_5:17-26',
                                        ]
    }
for topic,refs in TOPIC_TABLE.items():
    assert isinstance( topic, str )
    assert isinstance( refs, list )
    for ref in refs:
        assert isinstance( ref, str )
        if not ref.startswith( 'H3 ' ):
            if '/' in ref: # assume it's a lemma page link
                assert ref.count( '/' ) == 1
                part1, part2 = ref.split( '/' )
                assert part1 in ('HebLem','GrkLem')
            else: # assume it's a reference -- either a verse or a verse or chapter range
                assert ' ' not in ref, f"{ref=}"
                BBB, refRest = ref.split( '_' ) # This split will fail if it's not a valid scripture reference
                try:
                    C, Vs = refRest.split( ':' )
                    assert C.isdigit()
                except ValueError:
                    assert refRest.isdigit()

TOPIC_LIST = []
def createTopicPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    global TOPIC_LIST
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPages( {level}, {folder}, {state.BibleVersions} )" )
    assert level == 1

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateTopicPages( {level}, {folder} with {state.booksToLoad['OET']} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    # First make our list of topics (mostly for the Prev/Next links)
    assert len(TOPIC_LIST) == 0
    for topic,refsList in TOPIC_TABLE.items():
        TOPIC_LIST.append( (topic,topicFilename(topic),refsList) )

    topicsHtmlsForIndex = []
    for tt in range( 0, len(TOPIC_LIST) ):
        createTopicPage( level, folder, tt, state )
        topicsHtmlsForIndex.append( f'''<a href="{TOPIC_LIST[tt][1]}">{TOPIC_LIST[tt][0]}</a>''' )

    # Create topic index page
    filename = 'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'topicsIndex', None, state ) \
            .replace( '__TITLE__', f"Topic View{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', 'Bible, topic, topics, topical' )
    indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 id="Top">Topic pages</h1>
<p>These pages contain selected passages from the <em>Open English Translation</em> for the given topics. Each page contains the passage from the <em>OET Readers’ Version</em> on the left, with the <em>OET Literal Version</em> on the right. No notes or commentary is included—our aim is simply to conveniently list the passages in one place so that readers can make up their own minds about how the passages should be interpreted.</p>
<h2>Index of topics</h2>
<p>\n{'<br>'.join(topicsHtmlsForIndex)}</p>
<p class="note">Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any topics that you’d like us to add, or any passages that you’d like us to add to any topic page.</p>
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'topicsIndex' )}'''
    assert checkHtml( 'topicsIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(indexHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createTopicPages() finished processing {len(TOPIC_TABLE)} topics: {str(TOPIC_TABLE.keys()).replace('dict_keys([','').replace('])','')}" )
    return True
# end of createTopicPages.createTopicPages


def createTopicPage( level:int, folder:Path, topicNumber:int, state:State ) -> bool:
    """
    Create a page for each Bible topic.

    topicNumber is an index into the global TOPIC_LISTS[ (topic,topicFilename,refsList) ]

    Note: The above refsList can include Bible refs, e,g, 'MRK_1:2', and word refs, e.g., 'HebLem/nāḩam'
            as well as headings, e.g., 'H3 Only God can do that'
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createTopicPage( {level}, {folder}, {topicNumber} {state.BibleVersions} )" )

    topic,topicFilename,refsList = TOPIC_LIST[topicNumber]

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  createTopicPage for '{topic}' ({topicFilename}) with {len(refsList)} Bible passages…" )
    rvBible, lvBible = state.preloadedBibles['OET-RV'], state.preloadedBibles['OET-LV']

    leftLink = f'<a title="Previous kingdom" href="{TOPIC_LIST[topicNumber-1][1]}#Top">←</a> ' if topicNumber>0 else ''
    rightLink = f' <a title="Next kingdom" href="{TOPIC_LIST[topicNumber+1][1]}#Top">→</a>' if topicNumber<len(TOPIC_LIST)-1 else ''
    homeLink = f' <a title="Topic index" href="index.htm">⌂</a>'

    combinedHtmlChunks = []
    lvChapterCache = {}
    for rr,ref in enumerate( refsList, start=1 ):
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 5:
            dPrint( 'Never', DEBUGGING_THIS_MODULE, f"  {rr} ‘{topic}’ {ref=}")
        if ref.startswith( 'H3 '): # Then it's a heading (we'll remove this initial part of the string)
            combinedHtmlChunks.append( f'''<h3>{ref[3:]}</h3>
<h3> </h3>''' ) # Second one is to keep the number of columns matched - put a space in so checkHTML accepts it
        elif '/' in ref: # we'll assume it's a lemma reference
            path, word = ref.split( '/' )
            combinedHtmlChunks.append( f'''<p class="lemmaLink">See uses of <b>{'Hebrew' if 'Heb' in path else 'Greek'} word root <a href="{'../'*level}ref/{ref}.htm#Top">‘{word}’</a></b>.</p>
<p class="lemmaLink"> </p>''' ) # Second one is to keep the number of columns matched - put a space in so checkHTML accepts it
        else: # We'll assume it's a scripture reference
            BBB, refRest = ref.split( '_' ) # This split will fail if it's not a valid scripture reference
            # if BBB not in rvBible or BBB not in lvBible:
            #     continue # Don't force that book to be loaded

            try: C, Vs = refRest.split( ':' )
            except ValueError:
                assert refRest.isdigit()
                C, Vs = refRest, None
            # print( f"    {rr} {topic} {ref=} {BBB=} {refRest=} {C=} {Vs=}")
            startV = '1'
            try:
                if Vs is None: # then it's an entire chapter (no verses specified)
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                elif '-' in Vs: # then it's a verse range
                    startV, endV = Vs.split( '-' )
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseDataRange( (BBB,C,startV), (BBB,C,endV) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                elif '–' in Vs: # en-dash, then it's a chapter range
                    not_written_yet
                else: # assume it's a single verse
                    assert Vs and Vs.isdigit()
                    if BBB in rvBible: # TODO: Why is RV handled differently here than LV ???
                        rvVerseEntryList, rvContextList = rvBible.getContextVerseData( (BBB,C,Vs) )
                    else: rvVerseEntryList, rvContextList = InternalBibleEntryList(), []
                    startV = Vs # Used to build the HTML anchor below
            except KeyError as error:
                error.add_note(f"While creating topic {topic!r} ({topicFilename}): "
                               f"could not retrieve {rvBible.abbreviation} passage {ref}")
                raise
            # print( f"{rvVerseEntryList=}" )
            # print( f"{lvVerseEntryList=}" )
            rvTextHtml = convertVerseEntryListToHtml( level, rvBible.abbreviation, (BBB,C), 'topicalPassage', rvContextList, rvVerseEntryList, basicOnly=False, state=state, livenWordLinks=BBB in rvBible, colouriseWordClasses=False )
            # rvTextHtml = livenIORs( BBB, rvTextHtml, sections )
            rvTextHtml = do_OET_RV_HTMLcustomisations( f'Topic={topic}@{BBB}_{C}', rvTextHtml )

            lvTextHtml, _ = renderOETLVPassage(level, lvBible, (BBB,C,startV),
                rvVerseEntryList, 'topicalPassage', state, lvChapterCache, rr)

            if rvTextHtml.startswith( '<div class="rightS1Box">' ):
                rvTextHtml = f'<div class="section">{rvTextHtml}' # This got removed above
            # Handle footnotes and cross-references so the same fn1 doesn't occur for both chunks if they both have footnotes
            rvTextHtml = rvTextHtml.replace( 'id="footnotes', f'id="footnotes{rr}RV' ).replace( 'id="fn', f'id="fn{rr}RV' ).replace( 'href="#fn', f'href="#fn{rr}RV' ) \
                                .replace( 'id="crossRefs', f'id="crossRefs{rr}RV' ).replace( 'id="xr', f'id="xr{rr}RV' ).replace( 'href="#xr', f'href="#xr{rr}RV' )
            lvTextHtml = lvTextHtml.replace( 'id="footnotes', f'id="footnotes{rr}LV' ).replace( 'id="fn', f'id="fn{rr}LV' ).replace( 'href="#fn', f'href="#fn{rr}LV' ) \
                                .replace( 'id="crossRefs', f'id="crossRefs{rr}LV' ).replace( 'id="xr', f'id="xr{rr}LV' ).replace( 'href="#xr', f'href="#xr{rr}LV' )
            combinedHtmlChunks.append( f'''<h3>OET <a title="View in context of whole book" href="{'../'*level}OET/byDoc/{BBB}.htm#C{C}V{startV}">{getOETTidyBBB(BBB,True,True,'\u202f',True)}</a> <a title="View in context of whole chapter" href="{'../'*level}OET/byC/{BBB}_C{C}.htm#V{startV}">{refRest}</a></h3>
<h3> </h3>
<div class="chunkRV">{rvTextHtml}</div><!--chunkRV-->
<div class="chunkLV">{lvTextHtml}</div><!--chunkLV-->''' )
 # Second h3 above is to keep the number of columns matched - put a space in so checkHTML accepts it

    combinedHtml = f'''<div class="RVLVcontainer">
<h2>Readers’ Version</h2>
<h2>Literal Version <button type="button" id="marksButton" title="Hide/Show underline and strike-throughs" onclick="hide_show_marks()">Hide marks</button></h2>
{NEWLINE.join(combinedHtmlChunks)}</div><!--RVLVcontainer-->'''

    filepath = folder.joinpath( topicFilename )
    top = makeTop( level, None, 'topicPassages', None, state ) \
            .replace( '__TITLE__', f"{topic}{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, topic, {topic.replace(' ',', ')}' )
            # .replace( f'''<a title="{state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/rel/{sFilename}#Top">{thisRvBible.abbreviation}</a>''',
            #         f'''<a title="Up to {state.BibleNames[thisRvBible.abbreviation]}" href="{'../'*2}{BibleOrgSysGlobals.makeSafeString(thisRvBible.abbreviation)}/index.htm#Top">↑{thisRvBible.abbreviation}</a>''' )
    topicHtml = f'''{top}<!--topic page-->
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
<h1 id="Top">{topic}</h1>
<p>This page contains selected passages from the <em>Open English Translation</em> with the passage from the <em>OET Readers’ Version</em> on the left, and the <em>OET Literal Version</em> on the right. Minimal commentary is included (only some headings)—our aim is simply to conveniently list the passages in one place so that our readers can make up their own minds about what the writer of the passage was intending to communicate.</p>
{topicReferenceMaterial(level,topic,state)}{removeDuplicateCVids(combinedHtml)}
<p class="note"><small>Please contact us at <b>Freely</b> dot <b>Given</b> dot <b>org</b> (at) <b>gmail</b> dot <b>com</b> if there’s any passages that you’d like us to add to this topic page, or any passages that need a little bit more context around them. (We encourage our readers to always view things in their context, so we discourage use of the word ‘verse’, especially in sayings like, “This verse says …”.)</small></p>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'topicPassages' )}'''
    assert checkHtml( f'{topic} Topic', topicHtml )
    assert '.htm#aC' not in topicHtml and '.htm#bC' not in topicHtml, topicHtml
    assert not filepath.is_file(), f"{filepath=}" # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as topicHtmlFile:
        topicHtmlFile.write( topicHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(topicHtml):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 3:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    createTopicPage() finished processing '{topic}' with {len(refsList):,} references." )
    return True
# end of createTopicPages.createTopicPage



# The following KINGDOM_LIST is used to determine the number of pages and their titles
#   The second reference(s) are used to include the maps that would occur at those references
KINGDOM_LIST = (('Promised land',[('JOS','13','1')]),
                ('Full kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Northern kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Southern kingdom',[('JOS','13','1'),('JDG','4','4')]),
                ('Both kingdoms',[('KI2','14','25')]))
# Editorial readings approved separately from the existing map selections.
KINGDOM_READINGS = {
    'Promised land':('GEN_12:1-7','JOS_21:43-45'),
    'Full kingdom':('SA2_7:8-16',),
    'Northern kingdom':('KI1_12:25-33',),
    'Southern kingdom':('KI2_18:1-7','KI2_25:1-12'),
    'Both kingdoms':('EZE_37:21-28',),
}
# The following KINGDOM_INFO_HTML_DICT contains the HTML prose paragraphs to go on each page
KINGDOM_INFO_HTML_DICT = {
    'Promised land':'''<p>After four hundred years in Egypt (Heb. Mitsrayim) and ending up as slaves there, Yahweh told Mosheh (Moses) that he would lead the descendants of Yakov/Yisrael (Jacob/Israel) to the land that he’d promised to them.</p>''',
    'Intro':'''<p>Yakov (Jacob) was the patriarch of Yisrael (Israel).
After his descendants left Egypt (Heb. Mitsrayim) and moved into ‘the promised land’, they were guided by the prophets and by various heroes and guides (traditionally known in English as ‘Judges’, although that describes their role poorly) before they had a king. Shaul (Saul) was their first king, succeeded by King David and then his son King Shelomoh (Solomon).
However, the more northern tribes disagreed with the leaders of the southern tribes of Yehudah (Judah, David’s tribe) and Benyamin over succession plans.
They also resented having to travel to Yerushalem (Jerusalem, located in Yehudah's area) several times per year.
All of that and more eventually resulted in Yisrael splitting into two kingdoms: the northern kingdom which continued to be known as <b>Yisrael</b> with <b>Samaria</b> as its capital city,
and a southern kingdom that became known by the name of the dominant tribe of <b>Yehudah</b> (Benyamin was a relative small tribe) and which retained <b>Yerushalem</b> (Jerusalem) as its capital.</p>''',
    'Full kingdom':'''<p>By the ‘Full kingdom’, we mean the full kingdom of Yisrael encompassing all the tribes descending from Yakov's twelve sons plus Yosef's (Joseph's) two sons. The three kings of this kingdom were King Shaul, then King David, and his son King Shelomoh.</p>
<p>The prophets who spoke to the full kingdom of Yisrael include __SAMUEL_LINK__, Gad, Natan (Nathan), and Ahiyah (Ahijah).</p>''',
    'Northern kingdom':'''<p>By the ‘Northern kingdom’, we mean the northern area occupied by the majority ten tribes who then established Samaria as their capital and worship centre.
Sometimes the northern kingdom also goes by the name ‘Efraim’ (Ephraim, one of the ten tribes).</p>
<p>The prophets who spoke to the northern kingdom of Yisrael include Eliyyyah (Elijah), Elisha, Yonah (Jonah), Amos, and Hoshea (Hosea).</p>''',
    'Southern kingdom':'''<p>By the ‘Southern kingdom’, we mean the southern area of what was originally part of the Kingdom of Israel, but when the very large tribe of Yehudah (Judah) and the very small tribe of Benyamin (Benjamin) split off to stay loyal to David’s descendants who continued to rule from Yerushalim (Jerusalem).
This kingdom of Yehudah continued to be ruled by David’s descendants, although we often saw a pattern of ‘good king’, ‘bad king’ (unlike the Northern Kingdom which pretty much had all bad kings).</p>
<p>The prophets who spoke to the southern kingdom of Yehudah include Eliyyyah (Elijah), Isaiah, Mikah (Micah), Zefanyah (Zephaniah), Ovadyah (Obadiah), Nahum, Yeremyah (Jeremiah), Yoel (Joel), and Habakkuk.</p>''',
    'Both kingdoms':'''<p>By the term ‘Both kingdoms’, we mean that the narrative covers both of the two kingdoms of Yisrael and Yehudah (that had originally been united after the Israelis in the ‘<a href="PromisedLand.htm#Top">promised land</a>’ demanded a king, but which split after the death of King Shelomoh).</p>
<p>The prophets who spoke to both kingdoms (after they had been divided) include Isaiah, ...</p>''',
    }
def createKingdomPages( level:int, folder:Path, state:State ) -> bool:
    """
    """
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag:
        fnPrint( DEBUGGING_THIS_MODULE, f"createKingdomPages( {level}, {folder}, {state.BibleVersions} )" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\ncreateKingdomPages( {level}, {folder} )" )
    try: os.makedirs( folder )
    except FileExistsError: pass # they were already there

    entities = loadReferenceEntities(ENTITY_FOLDER,state)
    indexList = []
    for kk, (kingdomName,mapRefList) in enumerate( KINGDOM_LIST ):
        oneWordKingdomName = kingdomName.replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )
        filename = f'{oneWordKingdomName}.htm'
        indexList.append( (kingdomName, oneWordKingdomName, filename) )
        filepath = folder.joinpath( filename )
        top = makeTop( level, None, 'kingdom', None, state ) \
                .replace( '__TITLE__', f"{kingdomName}{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
                .replace( '__KEYWORDS__', f'Bible, {kingdomName.split()[0]}, kingdom' )
        leftLink = f'<a title="Previous kingdom" href="{KINGDOM_LIST[kk-1][0].replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )}.htm#Top">←</a> ' if kk>0 else ''
        rightLink = f' <a title="Next kingdom" href="{KINGDOM_LIST[kk+1][0].replace( ' ', '' ).replace( 'king', 'King' ).replace( 'land', 'Land' )}.htm#Top">→</a>' if kk<len(KINGDOM_LIST)-1 else ''
        homeLink = f' <a title="Kingdom index" href="index.htm">⌂</a>'

        # Handle BibleMapper maps and notes
        kingdomHtml = ''
        for mm, (BBB,C,V) in enumerate( mapRefList ):
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 4:
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    Checking {oneWordKingdomName} maps at {BBB} {C}:{V}…" )
            # This can fail if not all books are loaded, e.g., in TEST_MODE_FLAG
            bmmHtml = getBibleMapperMaps( level, BBB, C, V, None, None, state.preloadedBibles['OET-RV'], state )
            # assert bmmHtml, f"{kk=} {kingdomName=} {mapRefList=} {mm=} {BBB} {C}:{V}"
            if bmmHtml:
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel >= 3:
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"     Got some map HTML for {oneWordKingdomName} using {BBB} {C}:{V}" )
                bmmHtml = f'''<div {'id="BMM" ' if mm==0 else ''}class="parallelBMM"><a title="Go to BMM copyright page" href="{'../'*level}BMM/details.htm#Top">BMM</a> <b><a href="https://BibleMapper.com" target="_blank" rel="noopener noreferrer">BibleMapper.com</a> Maps</b>: {bmmHtml}</div><!--end of BMM-->'''
                if not kingdomHtml:
                    kingdomHtml = '<hr style="width:50%;margin-left:0;margin-top: 0.3em">'
                kingdomHtml = f'{kingdomHtml}\n{bmmHtml}'

        kingdomInfo = KINGDOM_INFO_HTML_DICT[kingdomName]
        if '__SAMUEL_LINK__' in kingdomInfo:
            samuelLink = scriptureLink(level, ('SA1','7','2'), 'OET-RV', 'OET', 'byC',
                'Shemuel (Samuel)', state, title='Read about Shemuel in context')
            if state.TEST_MODE_FLAG and 'SA1' not in state.booksToLoad['OET']:
                samuelLink = 'Shemuel (Samuel)'
            kingdomInfo = kingdomInfo.replace('__SAMUEL_LINK__', samuelLink)
        intro = KINGDOM_INFO_HTML_DICT['Intro']+NEWLINE if 'kingdom' in kingdomName else ''
        kingdomInfo = kingdomArticleLinks(intro+kingdomInfo,level,entities)
        entityLinks = ' · '.join(entityLink(key,level,entities) for key in KINGDOM_ENTITIES[oneWordKingdomName]
                               if key in entities['records'])
        readings = '<h2>Selected readings</h2>'
        for number,citation in enumerate(KINGDOM_READINGS[kingdomName],1):
            BBB,selection = citation.split('_',1)
            readings += renderReferencePassage(level,parseReferenceSelection(BBB,selection,'eng'),'eng',state,
                instanceId=f'kingdom-{oneWordKingdomName}-{number}',label=citation.replace('_',' ').replace('-','–'))
        html = f'''{top}<div class="{oneWordKingdomName}"><a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<h1 class="{oneWordKingdomName}" id="Top">{kingdomName} details</h1>
<p class="pageNav">{leftLink} {homeLink} {rightLink}</p>
{kingdomInfo}
<h2>People and places</h2><p>{entityLinks}</p>
{readings}
</div>
{kingdomHtml if kingdomHtml else ''}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'kingdom' )}'''
        assert checkHtml( f'{oneWordKingdomName}', html )
        assert not filepath.is_file() # Check that we're not overwriting anything
        with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
            indexHtmlFile.write( html )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(html):,} characters written to {filepath}" )

    # Now make an index page
    filename = f'index.htm'
    filepath = folder.joinpath( filename )
    top = makeTop( level, None, 'kingdom', None, state ) \
            .replace( '__TITLE__', f"Kingdoms index{' TEST' if state.TEST_MODE_FLAG else ''}" ) \
            .replace( '__KEYWORDS__', f'Bible, kingdoms, Israel, Judah' )
    indexHtml = f'''{top}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img class="OETWideLogo" src="{'../'*level}oet-logo-wide.png" alt="OET wide logo"></a>
<p class="note"><b><a href="../index.htm#Top">Reference lists contents page</a></b></p>
<p class="note"><a href="../HebWrd/index.htm#Top">Hebrew words index</a> <a href="../HebWrd/transIndex.htm#Top">Transliterated Hebrew words index</a></p>
<p class="note"><a href="../HebLem/index.htm#Top">Hebrew lemmas index</a> <a href="../HebLem/transIndex.htm#Top">Transliterated Hebrew lemmas index</a></p>
<p class="note"><a href="../HebStrng/index.htm#Top">Hebrew Strongs numbers index</a></p>
<p class="note"><a href="../GrkWrd/index.htm#Top">Greek words index</a> <a href="../GrkWrd/transIndex.htm#Top">Transliterated Greek words index</a></p>
<p class="note"><a href="../GrkLem/index.htm#Top">Greek lemmas index</a> <a href="../GrkLem/transIndex.htm#Top">Transliterated Greek lemmas index</a></p>
<p class="note"><a href="../GrkStrng/index.htm#Top">Greek Strongs numbers index</a></p>
<p class="note"><a href="../Per/importantPeopleAlphabeticalIndex.htm#Top">Important people alphabetical index</a> <a href="../Per/importantPeopleChronologicalIndex.htm#Top">Important people chronological index</a> <a href="../Per/index.htm#Top">All people index</a> <a href="../Loc/index.htm#Top">Locations index</a></p>
<p class="note"><span class="selectedBook">Promised land kingdoms index</span></p>
<p class="note"><a href="../Stats/index.htm#Top">Bible statistics</a></p>
{referenceIndexLinks(level,state)}<h1 id="Top">Index to ‘Kingdom’ pages</h1>
<h2>These pages describe the kingdoms after the Israelis entered the ‘promised land’</h2>
{'\n'.join([f'<div class="{oneWordKingdomName}"><p class="note"><a href="{kFilename}">{kingdomName}</a></p></div>' for kingdomName, oneWordKingdomName, kFilename in indexList])}<a title="Go to OET main site" href="https://OpenEnglishTranslation.Bible"><img src="{'../'*level}OET-LogoMark-RGB-FullColor.png" alt="OET logo mark" height="15" style="float:right; margin-left:10px;"></a>
{makeBottom( level, None, 'kingdomIndex' )}'''
    assert checkHtml( 'kingdomIndex', indexHtml )
    assert not filepath.is_file() # Check that we're not overwriting anything
    with open( filepath, 'wt', encoding='utf-8' ) as indexHtmlFile:
        indexHtmlFile.write( indexHtml )
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 4:
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"        {len(html):,} characters written to {filepath}" )

    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  createKingdomPages() finished processing {len(KINGDOM_LIST)} kingdom pages plus index." )
    return True
# end of createTopicPages.createKingdomPages


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createTopicPages.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the html object
    pass
# end of createTopicPages.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of createTopicPages.py
