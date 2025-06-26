#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# spellCheckEnglish.py
#
# Script to spell check either the OET-RV or OET-LV.
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Script to spell check English Bible verses.

CHANGELOG:
    2024-03-13 Added check for duplicated words
    2025-03-10 Added support for a few more internal USFM markers
    2025-04-16 Added support for removing some technical English words, but which aren't used in Bibles and so should be spelling errors
"""
from gettext import gettext as _
from pathlib import Path
from collections import defaultdict
import re

if __name__ == '__main__':
    import sys
    sys.path.insert( 0, '../../BibleOrgSys/' )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint, fnPrint, dPrint, rreplace


LAST_MODIFIED_DATE = '2025-06-19' # by RJH
SHORT_PROGRAM_NAME = "spellCheckEnglish"
PROGRAM_NAME = "English Bible Spell Check"
PROGRAM_VERSION = '0.49'
PROGRAM_NAME_VERSION = '{} v{}'.format( SHORT_PROGRAM_NAME, PROGRAM_VERSION )

DEBUGGING_THIS_MODULE = False


TED_Dict_folderpath = Path( '../../../Documents/RobH123/TED_Dict/sourceDicts/')


# Globals
# Prepopulate the word set with our exceptions
INITIAL_BIBLE_WORD_LIST = ['3.0','UTF','USFM', '©', 'CC0',
                    'EN','ENG',
                    'b','c','d','e',
                    's1','s2','r','+','LXX','Grk',
                    'nomina','Nomina','sacra',
                    'Deutercanon','Deuterocanonicals',
                    'hb',

                    # OET-LV and OET-RV names
                    #   Note: OET-LV names often use special characters (e.g., macrons on vowels, plus unusual consonantal forms)
                    'Abimelek','Abraʼam','Abshalom','Ahimelek','Amatsyah',
                        'Asaf','Ayyalon','Azaryah',
                    'Bartimeus','Benyamin','Benyamite','Benyamites', 'Bethania', 'Beyt',
                    'Dammeseq',
                    'ʼEfrayim','Efraim','Efron','Elifaz','Eliyyah','Esaw',
                    'Far\'oh','Far’oh', 'Fəlishtiy', 'Finehas',
                    'Goliat',
                    'Hidutun','Hizkiyyah','Hofni','Hoshea',
                    'Isayah','Ishma\'el','Iyyov',
                    'Kaisar','Kasdiy','Kayin','Kush',
                    'Lavan','Lakish','Layish',
                    'Malaki','Manashsheh','Mənashsheh',
                    'Metushalah',
                    'Mikal','Milkah','Mitspah','Mitsrayim',
                    'Mordekai','Mosheh',
                    'Natan',
                    'Paulos','Petros','Potifar',
                    'Qoraḩ',
                    'Sha\'ul','Sha’ul', 'Shəkem', 'She’ol',
                    'Shekem','Shelomoh','Shəlomoh', 'Shemu\'el','Shemu’el',
                    'Shim’on','Shimshon',
                    'Shomron',
                    'Shushan',
                    'Tsevaot','Tsidon','Tsiklag',
                    'Tsiyyon','Syon',
                    'Uriyyah','Uzziyyah',
                    'Yacob','Yacov','Yakov', # Need a spelling decision here
                        'Yael',
                        'Yafet','Yafo',
                        'Yair',
                        'Yakob',
                        'Yareb','Yared',
                    'Yehoshafat','Yehoshua','Yehu','Yehud','Yericho','Yeroboam','Yerushalem','Yeshayah','Yetro',
                        'Yesse','Yesu','Yishay',
                        'Yisrael','Yisra\'el','Yisra’el', # Need a spelling decision here
                        'Yitshak','Yizre’el',
                        'Yoash','Yoav',
                        'Yhn','Yohan','Yohannes','Yochanan','Yohan-the-Immerser',
                        'Yoel','Yoktan','Yonah','Yonatan','Yoppa','Yordan','Yosef','Yoshua','Yotam',
                    'Yudah','Yehudah','Youdaia', # Need a spelling decision here
                    'Yudas','Youdas',
                    'Yude','Yudea','Yudean','Yudeans',
                    'Zebedaios','Zekaryah','Zofar',

                    # Parts of compound names, e.g., Beth-arbel gets split into two 'words'
                    'arbel','arbell',

                    # Specialist words
                    'black-grained','building-stone',
                    'efod','el','emerald-looking',
                    'false-teachers','finely-ground','finely-spun',
                    'Halleluyah','house-servants',
                    'law-breaker',
                    'maschil','maskil','michtam',
                    'non',
                    'pass-over',
                    'tashheth','tent-making',

                    # ALL CAPS are used in Psalm Titles by the LSV
                    #   plus some translations use ALL CAPS for things like the sign on the cross, etc.
                    'THE','THAT','THIS','THESE','THINGS','HERE','THERE',
                    'WHAT','WHICH','WHO','WHEN',
                    'IS','AM','ARE','SHALL','SHOULD','WILL',
                    'IN','OF','TO','FOR','UNTO','ACCORDING','WITH',
                    'THEY','THY','OUR','US','HIMSELF',
                    'AND','NOT','OR',

                    # T4T figurative speech abbreviations -- not required because they get deleted
                    # 'DOU','EUP','HYP','MET','MTY','PRS','RHQ','SIM',

                    # Various simple English words used in Psalm headings, etc.
                    'BEING','CAME','CAUSE','COME','COMING','DO','SENDING','WATCH','PUT','DEATH','DESTROY','BORN',
                    'PRAISE','GIVE','LOVE','SAW','SET','COMMONLY','CALLED','NOW','SILENT','DOVE','FAR','OFF','TAKING','HOLD',
                    'APOSTLE','APOSTLES','CHILD','GOSPEL','ST','PROPHET','PREACHER','BRANCH','EPISTLE','VALLEY','SALT','STRIKES',
                    'SAVE','SERVANT','SERVANTS','MAN','SONS','BURDEN','RIGHTEOUSNESS','LILY','TESTIMONY','TEACH','STRIVING',
                    'KING','JEWS','YEWS','HAPPY','HOLY','HOLINESS','THRONE','PEACE','MOTHER','WOMEN','EARTH','GREAT','MYSTERY',
                    'HARLOTS','PROSTITUTES','ABOMINATIONS','EVIL','UNCLEAN','SECRET','MEANING','WILDERNESS','WOMAN','REMEMBER',
                    'BOOK','ORIGINAL','BASE','TEXT','PARABLE','NATIONS','NOTES','RELEASE','STATUS','TAGS','WORD','WORDS','SECTION','PRAYER','VISION',
                    'AMEN','END','SAY','SING','BEHOLD','STAR','RISE','STRINGED','UNKNOWN','HIDING','HOUSE',
                    'GENERAL','GLORY','DIVINE','ELDER',

                    'ADAM','ADONAI','ASAPH',
                    'BABYLON','BETHLEHEM',
                    'CHRIST',
                    'DAVID',
                    'ISRAEL','ISRAELITES',
                    'JAH','JEHOVAH','JESUS','JOSEPH','JUDAH',
                    'MOAB','MOSES',
                    'NAZARETH','NAZARENE',
                    'PAUL',
                    'SETH','SOLOMON',
                    'YEHOVAH','YESHUA','YESUS','YEWES','YOHN',

                    'A.D','B.C',
                    'TC','TD', # in footnotes
                    'ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','TWELVE','THOUSAND',
                    'FIRST','SECOND','THIRD','FOURTH','FIFTH',
                    'II','III','IV','X',
                    'ALEPH','BETH','GIMMEL','GIMEL','DALETH','HE','VAV','VAU','ZAYIN','ZAIN',
                        'HETH','CHETH','TETH','YODH','JOD','YOD','CAPH','KAPF','LAMEDH','LAMED',
                        'MEM','NUN','SAMEKH','SAMECH','AYIN','AIN','PE','TSADDI','TZADHE','TZADE','TZADDI',
                        'QOPH','KOPH','RESH','SIN','SHIN','SCHIN','TAV','TAU',

                    'MENE','MANE','TEKEL','TEQEL','THECEL', 'UPHARSIN','PERES','PHERES','PHARES','PHARSIN','PARSIN',
                    'Tabitha','Talitha','cumi',

                    'ULT','UST','BSB','OEB','NET','NRSV','WEB','WEBBE','WMB','WMBB','LSV','FBV','T4T','LEB','BBE','JPS','VLT','KJV','KJB',
                    'OSHB',
                    'nlt',

                    'GENESIS','EXODUS','LEVITICUS','NUMBERS','DEUTERONOMY','JOSHUA','JUDGES','RUTH',
                    'SAMUEL','KINGS','CHRONICLES','EZRA','NEHEMIAH','ESTHER','JOB','PSALMS','PROVERBS',
                    'ECCLESIASTES','SONG','SONGS','ISAIAH','JEREMIAH','LAMENTATIONS','EZEKIEL',
                    'DANIEL','HOSEA','JOEL','AMOS','OBADIAH','JONAH','MICAH',
                    'NAHUM','HABAKKUK','ZEPHANIAH','HAGGAI','ZECHARIAH','MALACHI',
                    'MATTHEW','MARK','LUKE','JOHN','ACTS','ROMANS','CORINTHIANS',
                    'GALATIANS','EPHESIANS','PHILIPPIANS','COLOSSIANS','THESSALONIANS','TIMOTHY','TITUS','PHILEMON',
                    'HEBREWS','JAMES','PETER','JUDE','REVELATION',

                    'GEN','EXO','LEV','NUM','DEU','JOS','JDG','RUT','SA1','SA2','KI1','KI2','CH1','CH2','EZR','NEH','EST',
                    'PSA','PRO','ECC','SNG','ISA','JER','LAM','EZE','EZK','DAN','HOS','JOL',
                    'AMO','OBA','JNA','JON','MIC','NAH','NAM','HAB','ZEP','HAG','ZEC','MAL',
                    'LAO','GES','LES','ESG','ADE','PS2','TOB','WIS','SIR','BAR','PAZ','JDT','DAG','SUS',
                    'MAT','MRK','LUK','JHN','YHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT',
                    'PHM','HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV',
                    'Gen','Exo','Lev','Num','Deu','Chr','Rut','Psa','Prv','Hos','Zech','Mal',
                    'Mrk','Luk','Lk','Jhn','Jn','Act','Gal','Eph','Php','Col','Heb','Phm','Rev',

                    'v2','v3','v4','v5','v6','v8','v9','v13','v14','v15','v16','v19','v26','v27',

                    'ReMoV', # This is how we mark where we removed a complex word below
                    ]
INITIAL_BIBLE_WORD_SET = set( INITIAL_BIBLE_WORD_LIST )
assert len(INITIAL_BIBLE_WORD_SET) == len(INITIAL_BIBLE_WORD_LIST), f"{[w for w in INITIAL_BIBLE_WORD_LIST if INITIAL_BIBLE_WORD_LIST.count(w)>1]}" # Shouldn't be any duplicates above
# AMERICAN_SPELLINGS = ['baptized','baptizing','baptize','favors','favor','honors','honor','marvelous','neighbors','neighbor','realize','splendor','worshiped','worshiping']
# BRITISH_SPELLINGS = ['baptised','baptising','baptise','favours','favour','honours','honour','marvellous','neighbours','neighbour','realise','splendour','worshipped','worshipping']

PREAPPROVED_WORDS_TO_REMOVE = sorted(['God’s','GOD', 'LORD’S','LORD’s','LORD\'S','LORD\'s','LORDS','LORD', # Delete ALL CAPS versions

            # Hyphenated names (would have been split up down below)
            'Al-tashheth','al-tashcheth','Al-taschith','al- tashcheth',
                'Aram-zobah',
            'Beer-sheba',
                'Ben-hadad',
                'Beth-aven','Beth-eden', 'Beth-el','Beyt-El','Beth-lehem',
                'Bikath-Aven','Bikat-Aven',

            # Mangled names
            'Yoab','Yonathan',
            'Yesus', 'Yhesus', 'Yhesu', 'Yerusalem',
            'Yacob', 'Yames', 'Yohn', 'Yoseph', 'Yoses',

            # Fancy pronouns
            'you_all', #'you(sg)','you(ms)','you(fs)', 'your(sg)','your(pl)','your(ms)', 'yours(sg)','yours(pl)', 'yourself(m)',
            'You_all', #'You(sg)',
            #'it(f)', 'saying(ms)',

            'aren’t','Aren’t',
                'can’t','Can’t', 'couldn’t','Couldn’t',
                'didn’t','Didn’t', 'doesn’t','Doesn’t', 'don’t','Don’t',
                'hadn’t','hasn’t', 'haven’t','Haven’t',
                    'he’d','He’d', 'he’ll','He’ll', 'he’s','He’s',
                'I’d', 'I’ll', 'I’m', 'isn’t','Isn’t', 'it’ll','It’ll', 'I’ve',
                'mustn’t',
                'needn’t',
                'o’clock',
                'she’d', 'she’ll',
                    'shouldn’t','Shouldn’t',
                'that’ll','That’ll',
                    'there’ll','There’ll',
                    'they’d','They’d', 'they’ll','They’ll', 'they’re','They’re','they’ve','They’ve', '’twas',
                'you’d','You’d', 'you’ll','You’ll', 'you’re','You’re', 'you’ve','You’ve',
                'wasn’t','Wasn’t',
                    'we’d', 'we’ll','We’ll', 'we’re','We’re', 'weren’t','Weren’t', 'we’ve','We’ve',
                    'who’d', 'who’ll', 'who’re', 'who’ve', 'won’t','Won’t', 'would’ve', 'wouldn’t','Wouldn’t',

            # Other
            'EDOMITE','EDOM','DOM', # Gotta do that one first
            ], key=len, reverse=True) # Put longest first


BAD_ENGLISH_WORD_SET, BAD_GERMAN_WORD_SET, BAD_LATIN_WORD_SET = set(), set(), set()
BAD_ENGLISH_WORD_LIST, BAD_GERMAN_WORD_LIST, BAD_LATIN_WORD_LIST = [], [], []
TOTAL_ENGLISH_WORDS_CHECKED_COUNT = TOTAL_GERMAN_WORDS_CHECKED_COUNT = TOTAL_LATIN_WORDS_CHECKED_COUNT = 0
TOTAL_ENGLISH_MISSPELLING_COUNT = TOTAL_GERMAN_MISSPELLING_COUNT = TOTAL_LATIN_MISSPELLING_COUNT = 0
BAD_ENGLISH_COUNTS, BAD_GERMAN_COUNTS, BAD_LATIN_COUNTS = defaultdict(int), defaultdict(int), defaultdict(int)
MISPELLING_VERSION_REF_DICT = defaultdict( list )


AMERICAN_WORD_SET, BRITISH_WORD_SET = set(), set()
def load_dict_sources() -> bool:
    """
    Load the words from the SIL Toolbox source files.
    """
    global AMERICAN_WORD_SET, BRITISH_WORD_SET
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Load English and Bible words from source dictionaries in {TED_Dict_folderpath}…" )

    AMERICAN_WORD_SET, BRITISH_WORD_SET = set(INITIAL_BIBLE_WORD_SET), set(INITIAL_BIBLE_WORD_SET)
    for dictFilename in ('EnglishDict.db','BibleDict.db'):
        dictFilepath = TED_Dict_folderpath.joinpath( dictFilename )
        with open( dictFilepath, 'rt', encoding='utf-8' ) as dictSourceFile:
            dictText = dictSourceFile.read()
        dictWords = dictText.split( '\n\\wd ')
        # print( f"{dictWords[0]=} {dictWords[1]=} {dictWords[2]=} {dictWords[-1]=}"); halt
        for entryStr in dictWords[1:]:
            entryLines = entryStr.rstrip().split( '\n' )
            # print( f"{entryLines=}")
            word = entryLines[0].rstrip()
            if '*' in word:
                word, subscript = word.split( '*', 1 )
                assert subscript.isdigit()
            assert entryLines[1].startswith( '\\lg ')
            language = entryLines[1][4:]
            mispelling = False
            for entryLine in entryLines[2:]:
                if entryLine.startswith( '\\ms '):
                    mispelling = True
                    break
            if not mispelling \
            and word not in ('hade',): # Any technical or other English words which would be mispellings if used in a Bible
                if language != 'BRI':
                    AMERICAN_WORD_SET.add( word )
                if language != 'AME':
                    BRITISH_WORD_SET.add( word )
        # for line in dictSourceFile:
        #     line = line.rstrip( '\n' )
        #     if line.startswith( '\\wd '):
        #         word = line[4:]
        #         if '*' in word:
        #             word, subscript = word.split( '*', 1 )
        #             assert subscript.isdigit()
        #         BIBLE_WORD_SET.add( word )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded {len(AMERICAN_WORD_SET):,} American and {len(BRITISH_WORD_SET):,} British and Bible words." )
    # print( BIBLE_WORD_LIST[:10]); halt
    return True
# end of spellCheckEnglish.load_dict_sources


USFM_CLOSED_FIELDS_TO_COMPLETELY_REMOVED = ('x','fig')
FOOTNOTE_OR_XREF_CALLER_REGEX = re.compile( '<span class="(fn|xr)Caller".+?</span>' )
ANCHOR_LINK_REGEX = re.compile( '<a ([^>]+?)>' )
RV_ADD_REGEX = re.compile( '<span class="RVadd" [^>]+?>' )
FOOTNOTE_Ps_REGEX = re.compile( '<p class="fn" id="fn[1-9]">' )
FOOTNOTES_DIV_REGEX = re.compile( '<div id="footnotes" class="footnotes">.+?</div><!--footnotes-->' )
CROSSREFS_DIV_REGEX = re.compile( '<div id="crossRefs" class="crossRefs">.+?</div><!--crossRefs-->' )
def spellCheckAndMarkHTMLText( versionAbbreviation:str, ref:str, HTMLTextToCheck:str, originalHTMLText:str, state ) -> str:
    """
    Puts a span around suspected misspelt words

    Handles a number of different English traditions,
        e.g., both straight and typographic apostrophes and quotes, etc.
    """
    global TOTAL_ENGLISH_WORDS_CHECKED_COUNT, TOTAL_ENGLISH_MISSPELLING_COUNT, TOTAL_GERMAN_WORDS_CHECKED_COUNT, TOTAL_GERMAN_MISSPELLING_COUNT, TOTAL_LATIN_WORDS_CHECKED_COUNT, TOTAL_LATIN_MISSPELLING_COUNT

    BBB = ref[:3]
    # DEBUGGING_THIS_MODULE = 99 if BBB=='TOB' else False

    location = f'{versionAbbreviation} {ref}'
    if len(AMERICAN_WORD_SET) < 10_000:
        load_dict_sources()

    #if versionAbbreviation in ( 'ULT','UST', 'NET', 'BSB','BLB', 'WEB','WMB', 'LSV', 'FBV', 'LEB', 'ASV', 'Wbstr' ):
    if state.BibleLanguages[versionAbbreviation] == 'EN-USA':
         wordSetName = 'USA'
         wordSet = AMERICAN_WORD_SET
    # elif versionAbbreviation in ( 'OET-RV','OET-LV', 'OEB', 'WEBBE','WMBB', 'BBE','Moff','JPS','DRA','YLT','Drby','RV', 'KJB-1769','KJB-1611', 'Bshps','Gnva','Cvdl', 'TNT','Wycl', 'Luth','ClVg' ):
    elif state.BibleLanguages[versionAbbreviation] == 'EN-UK' \
    or state.BibleLanguages[versionAbbreviation] in ('GER','LAT'): # These ones should have been translated
         wordSetName = 'UK'
         wordSet = BRITISH_WORD_SET
    else:
        raise ValueError( f"Unknown spell-check language for {versionAbbreviation} {state.BibleLanguages[versionAbbreviation]=}" )
    

    # Specific words expected in specific versions
    if versionAbbreviation in ('OET','OET-RV','OET-LV'):
        wordSet.update( ('OET','ESFM','v0.6','Freely-Given.org','WORDTABLE','LV_NT_word_table.tsv','table.tsv',
                        'ScriptedBibleEditor',
                        '\\jmp', '_', '_\\em*about', '_\\em*all', '_\\em*caring\\em',
                        'href="https','openscriptures.org','en.wikipedia.org', # Website refererences
                        'wpmu2.azurewebsites.net', 'www.GotQuestions.org', 'www.biblicalarchaeology.org', 'www.billmounce.com', 'www.sil.org','textandcanon.org',
                        'armstronginstitute.org','bibleDifferences.net','bibleandtech.blogspot.com','bibledifferences.net','biblestudyresources','commentary.html','judas%E2%80%99','tongue%E2%80%9D', 'Yeshua%E2%80%99',
                        'mounce', 'openenglishbible', 'scrollandscreen.com', 'UASVBible.org', 'given.org', 'GitHub.com', 'GreekCNTR.org', # Websites
                        '%E2%80%9Cdivided','%E2%80%9Cjew%E2%80%9D','v=66013018',
                        'Amots','Tsor',
                        ) )
        if versionAbbreviation == 'OET-LV':
            wordSet.update( ('LV_OT_word_table.tsv',
                            'Dawid','Efrayim','Farisaios','Galilaia','Pilatos',
                            ) )
    elif versionAbbreviation in ('UST','ULT','UHB','UGNT'):
        wordSet.update( ('unfoldingWord®','unfoldingWord','tc','en',) )
    elif versionAbbreviation == 'LSV': # Allow their UPPER CASE Psalm headings
        wordSet.update( ('A','AN','ABIMELECH','ALL','AND','ASCENTS','AWAY','BEFORE','BEHAVIOR','BET','BY',
                         'CHANGING','DEDICATION','DAY','DOE','DRIVES',
                         'ENEMIES','FROM',
                         'HAS','HOUSE','INSTRUCTION','MIKTAM','MORNING','INSTRUMENTS','HIS',
                         'ON','OVERSEER','PRAYER','PSALM','SAUL','SAYS','SET','SPOKEN',
                         'HIM','GOES','ALEPH-BET','YAH','ALEPH','BETH','WHO',
                        ) )
    elif versionAbbreviation == 'KJB-1611': # Allow their U P P E R C A S E Book headings
        wordSet.update( ('B','C','D','E','F','G','H','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z') )
    # elif versionAbbreviation in ('RV','AST',): # Handle long UPPER CASE titles
    #     wordSet.update( ('FIRST','SECOND','THIRD','FOURTH','FIFTH','COMMONLY','CALLED','MOSES',) )
    elif versionAbbreviation in ('DRA','YLT','RV'):
        wordSet.update( ('baptized',) )
    elif versionAbbreviation == 'Luth':
        wordSet.update( ('Yuda',) )
    elif versionAbbreviation == 'ClVg':
        wordSet.update( ('Moyses','Yuda') )

    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Checking spelling of {versionAbbreviation} {ref} '{originalHTMLText}' …" )
    # if '0' not in ref and '-1' not in ref: halt
    checkedHTMLText = HTMLTextToCheck

    # Clean up spaces
    cleanedText =  ( HTMLTextToCheck
                    .replace( '\n<br>\u2002⇔\u202f', ' ' )
                    .replace( ' ', ' ' )
                    .replace( ' ', ' ' )
                    .replace( '&nbsp;', ' ' ).replace( '\xA0', ' ' )
                    .replace( '\u202f', ' ' )
                    .replace( '\n<br>', ' ' )
                    .replace( '<br>', ' ' )
                    .replace( '\n', ' ' )
                    .replace( '  ', ' ' )
                    )

    # Remove unwanted HTML crud
    if versionAbbreviation == 'T4T':
        cleanedText =  ( cleanedText
                    .replace( '<span title="alternative translation">◄</span>', '' )
                    .replace( '►', '' ) # Delete end of alternative translation
    
                    # Some of these can occur doubly, e.g., [MET, DOU], so that's what the second column here covers (without the square brackets)
                    .replace( '<span class="t4tFoS" title="apostrophe (figure of speech)">[APO]</span>', '' ).replace( '<span class="t4tFoS" title="apostrophe (figure of speech)">APO</span>', '' )
                    .replace( '<span class="t4tFoS" title="chiasmus (figure of speech)">[CHI]</span>', '' ).replace( '<span class="t4tFoS" title="chiasmus (figure of speech)">CHI</span>', '' )
                    .replace( '<span class="t4tFoS" title="doublet (figure of speech)">[DOU]</span>', '' ).replace( '<span class="t4tFoS" title="doublet (figure of speech)">DOU</span>', '' )
                    .replace( '<span class="t4tFoS" title="euphemism (figure of speech)">[EUP]</span>', '' ).replace( '<span class="t4tFoS" title="euphemism (figure of speech)">EUP</span>', '' )
                    .replace( '<span class="t4tFoS" title="hendiadys (figure of speech)">[HEN]</span>', '' )
                    .replace( '<span class="t4tFoS" title="hyperbole (figure of speech)">[HYP]</span>', '' ).replace( '<span class="t4tFoS" title="hyperbole (figure of speech)">HYP</span>', '' )
                    .replace( '<span class="t4tFoS" title="idiom (figure of speech)">[IDM]</span>', '' ).replace( '<span class="t4tFoS" title="idiom (figure of speech)">IDM</span>', '' )
                    .replace( '<span class="t4tFoS" title="irony (figure of speech)">[IRO]</span>', '' ).replace( '<span class="t4tFoS" title="irony (figure of speech)">IRO</span>', '' )
                    .replace( '<span class="t4tFoS" title="litotes (figure of speech)">[LIT]</span>', '' ).replace( '<span class="t4tFoS" title="litotes (figure of speech)">LIT</span>', '' )
                    .replace( '<span class="t4tFoS" title="metaphor (figure of speech)">[MET]</span>', '' ).replace( '<span class="t4tFoS" title="metaphor (figure of speech)">MET</span>', '' )
                    .replace( '<span class="t4tFoS" title="metonymy (figure of speech)">[MTY]</span>', '' ).replace( '<span class="t4tFoS" title="metonymy (figure of speech)">MTY</span>', '' )
                    .replace( '<span class="t4tFoS" title="personification (figure of speech)">[PRS]</span>', '' ).replace( '<span class="t4tFoS" title="personification (figure of speech)">PRS</span>', '' )
                    .replace( '<span class="t4tFoS" title="rhetorical question (figure of speech)">[RHQ]</span>', '' ).replace( '<span class="t4tFoS" title="rhetorical question (figure of speech)">RHQ</span>', '' )
                    .replace( '<span class="t4tFoS" title="sarcasm (figure of speech)">[SAR]</span>', '' ).replace( '<span class="t4tFoS" title="sarcasm (figure of speech)">SAR</span>', '' )
                    .replace( '<span class="t4tFoS" title="simile (figure of speech)">[SIM]</span>', '' ).replace( '<span class="t4tFoS" title="simile (figure of speech)">SIM</span>', '' )
                    .replace( '<span class="t4tFoS" title="symbol (figure of speech)">[SYM]</span>', '' )
                    .replace( '<span class="t4tFoS" title="synecdoche (figure of speech)">[SYN]</span>', '' ).replace( '<span class="t4tFoS" title="synecdoche (figure of speech)">SYN</span>', '' )
                    .replace( '<span class="t4tFoS" title="triple (figure of speech)">[TRI]</span>', '' )
                    )
    if 'OET' in versionAbbreviation:
        cleanedText =  ( cleanedText
                    .replace( '<span class="synonParr" title="synonymous parallelism">≈</span>', '' )
                    .replace( '<span class="antiParr" title="antithetic parallelism">^</span>', '' )
                    .replace( '<span class="synthParr" title="synthetic parallelism">→</span>', '' )

                    .replace( '<span class="addArticle" title="added article">', '' )
                    .replace( '<span class="addDirectObject" title="added direct object">', '' )
                    .replace( '<span class="addDirectObject unsure" title="added direct object (less certain)">', '' )
                    .replace( '<span class="addElided" title="added elided info">', '' )
                    .replace( '<span class="addExtra" title="added implied info">', '' )
                    .replace( '<span class="addNegated" title="negated">', '' )
                    .replace( '<span class="addOwner" title="added ‘owner’">', '' )
                    .replace( '<span class="addPluralised" title="changed number">', '' )
                    .replace( '<span class="addPronoun" title="used pronoun">', '' )
                    .replace( '<span class="addReferent" title="inserted referent">', '' )
                    .replace( '<span class="addReferent unsure" title="inserted referent (less certain)">', '' )
                    .replace( '<span class="addReword" title="reworded">', '' )
                    .replace( '<span class="addReword unsure" title="reworded (less certain)">', '' )
                    .replace( '<span class="RVadd unsure" title="added info (less certain)">', '' ) # (plain) RVadd is removed by RegEx
                    )
    cleanedText =  ( cleanedText
                    .replace( '<div>', '' )
                    .replace( f'<span class="{versionAbbreviation}_verseTextChunk">', '' ).replace( f'<span class="{versionAbbreviation}_trans">', '' )
                    .replace( '<span class="nd">L<span style="font-size:.75em;">ORD</span></span>', 'LORD' )
                    .replace( '<hr style="width:30%;margin-left:0;margin-top: 0.3em">', '' ).replace( '<hr style="width:35%;margin-left:0;margin-top: 0.3em">', '' )

                    .replace( '</span>s ', '</span> ' ).replace( '</span>s:', '</span>:' ) # LORDs
                    )
    for divMarker in ( 'bookHeader','bookIntro',
                      'iot',
                      's1',
                        ):
        cleanedText =  cleanedText.replace( f'<div class="{divMarker}">', '' ).replace( f'<!--{divMarker}-->', '' )
    for paragraphMarker in ( 'id','rem',
                        'mt1','mt2','mt3','mt4',
                        'imt1','iot','io1','io2','is1','is2','ip','im',
                        'ms1','ms2',
                        's1',
                        'p', # OEB CH1_-1:0 uses p instead of ip!
                        ):
        cleanedText =  cleanedText.replace( f'<p class="{paragraphMarker}">', '' )
    for spanMarker in ('add','addArticle','addExtra','addCopula','addDirectObject', # TODO: Why don't these have title fields???
                       'untr','nominaSacra',
                       'ior', 'vp',
                       'nd','wj','d','bk','qt','sc',
                       'qs','sig',
                        'ft', 'fnRef','fnText', # 'f', # We intentionally omit 'fr'
                        'li1','li2','li3',
                        'theb','va', # in NET
                        'ul',
                        ):
        cleanedText =  cleanedText.replace( f'<span class="{spanMarker}">', '' )
    cleanedText =  cleanedText.replace( f'<span class="{versionAbbreviation}_chapterIntro">', '' )
    for formatField in ('i','b','em','small','sup','sub'):
        cleanedText =  cleanedText.replace( f'<{formatField}>', '' ).replace( f'</{formatField}>', '' )
    cleanedText = FOOTNOTE_OR_XREF_CALLER_REGEX.sub( '', cleanedText )
    cleanedText = ANCHOR_LINK_REGEX.sub( '', cleanedText )
    cleanedText = RV_ADD_REGEX.sub( '', cleanedText )
    if versionAbbreviation in ('OET-RV','OET-LV'): # we want to check the actual footnote content
        cleanedText = cleanedText.replace( '<div id="footnotes" class="footnotes">', '' ).replace( '</div><!--footnotes-->', '' )
        cleanedText = FOOTNOTE_Ps_REGEX.sub( '', cleanedText )
    else: # we won't bother checking footnote content for most versions, so delete the whole thing
        cleanedText = FOOTNOTES_DIV_REGEX.sub( '', cleanedText )
    cleanedText = CROSSREFS_DIV_REGEX.sub( '', cleanedText )
    assert '<span' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    assert ' class="' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    assert ' title="' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    assert ' id="' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    assert ';margin' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    for htmlEntity in ('table','tr','td'):
        cleanedText =  cleanedText.replace( f'<{htmlEntity}>', '' ).replace( f'</{htmlEntity}>', '' )
    cleanedText = cleanedText.replace( '</span>', '' ).replace( '</p>', '' ).replace( '</div>', '' ).replace( '</a>', '' )
    assert '<' not in cleanedText and '>' not in cleanedText, f"Unexpected html markers in {versionAbbreviation} {ref} {cleanedText=}"

    # Now general or punctuation clean-ups
    cleanedText =  ( cleanedText
                    .replace( '\n', ' ' ) # Treat newlines as spaces
                    .replace( '—', ' ' ).replace( '–', ' ' ) # Treat em-dashes and en-dashes as spaces
                    .replace( '…', ' ').replace( '...', ' ') # Treat ellipsis as spaces
                    .replace( '/', ' ' ) # Treat forward slash as spaces (sometimes used to separate alternate words like 'dew/rain')
                    .replace( '_', ' ' ) # Treat underlines as spaces
                    .replace( '{', '' ).replace( '}', '' ) # Delete braces
                    .replace( '¶', '' ) # Delete pilcrow
                    .replace( '⇔', '' ).replace( '§', '' ).replace( '•', '' ) # Delete derived USFM format markers
                    .replace( '’s', "'s" ) # Change apostrophe
                    )
    if versionAbbreviation == 'OET-LV':
        cleanedText =  ( cleanedText
                        .replace( '˓', '' ).replace( '˒', '' ) # Around gloss-helpers
                        )
    elif versionAbbreviation == 'LEB':
        cleanedText =  ( cleanedText
                        .replace( '⌊', '' ).replace( '⌋', '' ) # Floor brackets ('idioms' from LEB)
                        .replace( '〚', '' ).replace( '〛', '' ) # White square brackets (from LEB)
                        )

    # Now tidy-up any USFM stuff                    )
    # for fieldName in USFM_CLOSED_FIELDS_TO_COMPLETELY_REMOVED:
    #     regex = re.compile( f'\\\\{fieldName}.+?\\\\{fieldName}\\*')
    #     cleanedText, numSubs = regex.subn( '', cleanedText )
    #     assert f'\\{fieldName}' not in cleanedText

    # cleanedText =  ( cleanedText
    #                 .replace( '\\f ', ' \\f ' ).replace( '\\x ', ' \\x ' )
    #                 .replace( '\\fr ', '###' ).replace( '\\xo ', '###' )
    #                 .replace( '\\x*', ' ' ).replace( '\\f*', ' ' ).replace( '\\fig*', ' ' )
    #                 .replace( '\\add*', '' )
    #                 .replace( '\\jmp ', ' \\jmp ' )
    #                 )

    # Final Bible clean-ups
    #   (Easier to remove these known-to-be-correct words here, rather than to handle them later)
    thingsToReallyDelete = ['(s)','(es)','[s]',
                            '(m)', '(f)', '(ms)', '(fs)',
                            '(sg)','(pl)',
                            '(aj)', '(n)', '(v)',
                            ]
    for thingToReallyDelete in thingsToReallyDelete:
        cleanedText = cleanedText.replace( thingToReallyDelete, '' )
    for wordToDelete in PREAPPROVED_WORDS_TO_REMOVE:
        cleanedText = cleanedText.replace( wordToDelete, 'ReMoV' ) # If we really delete them, then our repeated words check does weird things
    cleanedText =  ( cleanedText
                    .replace( '-', ' ' ) # Treat hyphens as spaces, i.e., split compound words (both good and bad like 'non-combatant')
                    .replace( '  ', ' ' )
                    )

    if versionAbbreviation in ('Luth','ClVg'):
        cleanedText = cleanedText.replace( '_', ' ' ) # Things like 'he_said'

    cleanedText = cleanedText.strip().replace( '  ', ' ' )
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    About to check spelling of '{cleanedText}' …" )
    adjWords = cleanedText.split( ' ' )

    lastLastWord = lastWord = ''
    for ww,word in enumerate( adjWords ):
        try: nextWord = adjWords[ww+1]
        except IndexError: nextWord = '' # at end

        if word in ('◙','…','…◙','◘'): continue # Untranslated or not-yet-translated verse
        if word.startswith( '###' ): continue # it's an fr or xo field
        if 'ā' in word or 'ē' in word or 'ī' in word or 'ō' in word or 'ū' in word: continue # It's a transliteration
        if 'Ā' in word or 'Ē' in word or 'Ī' in word or 'Ō' in word or 'Ū' in word: continue # It's a transliteration
        if 'ⱪ' in word or 'ʦ' in word or 'ʸ' in word: continue # It's a transliteration
        if 'ⱪ' in word or 'Ē' in word or 'Ī' in word or 'Ş' in word or 'Ū' in word: continue # It's a transliteration
        if 'ₐ' in word or 'ₑ' in word or 'ₒ' in word: continue # It's a transliteration
        if 'ˊ' in word or 'XXX' in word: continue # It's a transliteration
        for _x in range( 2 ):
            # We can have nested punctuation, especially at the end of a sentence
            while word.startswith('‘') or word.startswith('“') or word.startswith("'") or word.startswith('"') \
            or word.startswith('(')  or word.startswith('['):
                word = word[1:]
            while word.endswith('.') or word.endswith(',') \
                or word.endswith('’') or word.endswith('”') or word.endswith("'") or word.endswith('"') \
                or word.endswith('?') or word.endswith('!') \
                or word.endswith(':') or word.endswith(';') \
                or word.endswith(')') or word.endswith(']') \
                or word.endswith('…'): 
                    word = word[:-1]
            if not word: break

            # Remove \add markers
            if word[0] == '?': # This one can precede the others
                word = word[1:]
            if word[0] in '+<=>#@*^&≈?≡':
                word = word[1:]
            if not word: break

            # Get rid of possessives (using straight apostrophe ')
            if word.endswith("'"): word = word[:-1]
            elif word.endswith("'s"): word = word[:-2]
        if not word: continue
        if '¦' in word:
            assert word.count( '¦' ) == 1, f"{word=} @ {location}"
            word, number = word.split( '¦', 1 )
            assert number.isdigit(), f"'{word}¦{number}' from '{HTMLTextToCheck}' @ {location}"
        # Get rid of possessives (using straight apostrophe ')
        if word.endswith("'"): word = word[:-1]
        elif word.endswith("'s"): word = word[:-2]
        if not word: continue
        if word[0].isdigit(): continue # Probably a ior or fr or xo reference
        if word.startswith( 'http' ): continue # URL

        if versionAbbreviation == 'Luth': TOTAL_GERMAN_WORDS_CHECKED_COUNT += 1
        elif versionAbbreviation == 'ClVg': TOTAL_LATIN_WORDS_CHECKED_COUNT += 1
        else: TOTAL_ENGLISH_WORDS_CHECKED_COUNT += 1
        if word not in wordSet and f'{word[0].lower()}{word[1:]}' not in wordSet:
            if versionAbbreviation not in ('Luth','ClVg'): # native or modernised English
                vPrint( 'Normal' if ((versionAbbreviation!='LSV' and word.upper()==word)
                            or 'ReMoV' in word or 'honor' in word
                            or (word in ('s','heretage','yelde','deme','maden','virtuees','el','aha','loge','drede',
                                   'fortyth','fulness','digged',"'And",'baptized','holden','hous','stedfast',
                                   'schent','knowe','madist','clepe','veyn','hopide','thouyten','redy','spaken',
                                   'silf','nedi','modir','sunne','hygh','i','sprete','wyn','ethir','zobah','hode','honde','equite',
                                   'tashcheth','kindreds','tho','ynne','oute','wrooth','brak','thei','eere','hade','ioiyng',
                                   'stablish','puplis','nyle','hertli','drinke''vertu','eet','saten','gileful','hertli','greces')
                                        and 'PSA' not in location) # coz Wycl versification doesn't usually match anyway
                            or 'twas' in word )
                        and word not in ('OK','NOT','SURE','TOO','LITERAL')
                    else 'Info', DEBUGGING_THIS_MODULE, f'''    {word} is suspect {wordSetName} @ {location} from {originalHTMLText=}''' )
            else: # Luth or ClVg
                vPrint( 'Normal' if word.upper()==word
                       or word in ('illis','illi','tuum','eis','eo','tuis','aut','Ende','tuæ','mihi','Tu','tu','Domine','meam','yudgment',
                                   'ihn','als','tut','terra','es','childrens','Zeit','macht','loben','sind','yudgement','se','meas',
                                   'dico','tamquam','tuorum','sie','sich','nobis','auf','gentes','irh','nostri',
                                   'sua','suo','Wege','lobet','dich','fuit','regem','ac','seid','euer','er',)
                    else 'Info', DEBUGGING_THIS_MODULE, f'''    {word} is suspect @ {location} from {originalHTMLText=}''' )
            if versionAbbreviation == 'Luth':
                BAD_GERMAN_WORD_SET.add( word )
                BAD_GERMAN_WORD_LIST.append( (word,location) )
                BAD_GERMAN_COUNTS[word] += 1
                TOTAL_GERMAN_MISSPELLING_COUNT += 1
                if checkedHTMLText.count( word ) == 1:
                    # print( f"MARKING {versionAbbreviation} {word=} in {ref} {checkedHTMLText=}" )
                    checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible misspelt or untranslated word" class="spelling">{word}</span>', 1 )
            elif versionAbbreviation == 'ClVg':
                BAD_LATIN_WORD_SET.add( word )
                BAD_LATIN_WORD_LIST.append( (word,location) )
                BAD_LATIN_COUNTS[word] += 1
                TOTAL_LATIN_MISSPELLING_COUNT += 1
                if checkedHTMLText.count( word ) == 1:
                    # print( f"MARKING {versionAbbreviation} {word=} in {ref} {checkedHTMLText=}" )
                    checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible misspelt or untranslated word" class="spelling">{word}</span>', 1 )
            else: # assume it's English
                BAD_ENGLISH_WORD_SET.add( word )
                BAD_ENGLISH_WORD_LIST.append( (word,location) )
                BAD_ENGLISH_COUNTS[word] += 1
                TOTAL_ENGLISH_MISSPELLING_COUNT += 1
                if versionAbbreviation not in ('KJB-1611',) \
                or BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR(BBB): # We don't do this coz for KJB-1611 (except Apocrypha) it messes up later addition of hilites
                    if checkedHTMLText.count( word ) == 1:
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"MARKING {versionAbbreviation} {word=} in {ref} {checkedHTMLText=}" )
                        checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible misspelt word" class="spelling">{word}</span>', 1 )
                    elif versionAbbreviation=='OET-RV' and checkedHTMLText.count( word )==2 and len(word)>4: # The OET-RV text has footnotes included
                        # We want to be certain to replace the word in the actual footnote text, not in the caller popup
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"MARKING {versionAbbreviation} {word=} in {ref} {checkedHTMLText=}" )
                        checkedHTMLText = rreplace( checkedHTMLText, word, f'<span title="Possible misspelt word" class="spelling">{word}</span>', 1 )
            MISPELLING_VERSION_REF_DICT[versionAbbreviation].append( (word,ref) ) # We can save these to disk later
        if word == lastWord and word not in ('had','that'):
            vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f'''    Possible duplicated {word=} @ {location} with "{lastLastWord} {lastWord} {word} {nextWord}"''' )
            dupWord = f'{word} {word}'
            if versionAbbreviation == 'Luth':
                BAD_GERMAN_WORD_SET.add( dupWord )
                BAD_GERMAN_WORD_LIST.append( (dupWord,location) )
            elif versionAbbreviation == 'ClVg':
                BAD_LATIN_WORD_SET.add( dupWord )
                BAD_LATIN_WORD_LIST.append( (dupWord,location) )
            else: # assume it's English
                BAD_ENGLISH_WORD_SET.add( dupWord )
                BAD_ENGLISH_WORD_LIST.append( (dupWord,location) )
            if checkedHTMLText.count( word ) == 2:
                if versionAbbreviation not in ('KJB-1611',): # We don't do yet this coz it messes up later addition of hilites
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"MARKING {versionAbbreviation} {word=} in {ref} {checkedHTMLText=}" )
                    checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible duplicated word" class="duplicate">{word}</span>', 2 )
        lastLastWord = lastWord
        lastWord = word

    return checkedHTMLText
# end of spellCheckEnglish.spellCheckAndMarkHTMLText


def printSpellCheckSummary( state ) -> None:
    """
    Prints some summary results
    """
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\n\nSpell-check results:" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL LATIN WORDS CHECKED = {TOTAL_LATIN_WORDS_CHECKED_COUNT:,} BAD_LATIN WORDS {len(BAD_LATIN_WORD_LIST):,} = {len(BAD_LATIN_WORD_LIST)*100/TOTAL_LATIN_WORDS_CHECKED_COUNT:.1f}% ({len(BAD_LATIN_WORD_SET):,} unique){f': {BAD_LATIN_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    TOTAL BAD LATIN WORDS = {TOTAL_LATIN_MISSPELLING_COUNT:,} WORST LATIN WORDS {[(k, BAD_LATIN_COUNTS[k]) for k in sorted(BAD_LATIN_COUNTS, key=BAD_LATIN_COUNTS.get, reverse=True) if k.islower()][:13]}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL GERMAN WORDS CHECKED = {TOTAL_GERMAN_WORDS_CHECKED_COUNT:,} BAD_GERMAN WORDS {len(BAD_GERMAN_WORD_LIST):,} {len(BAD_GERMAN_WORD_LIST)*100/TOTAL_GERMAN_WORDS_CHECKED_COUNT:.1f}% ({len(BAD_GERMAN_WORD_SET):,} unique){f': {BAD_GERMAN_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    TOTAL BAD GERMAN WORDS = {TOTAL_GERMAN_MISSPELLING_COUNT:,} WORST GERMAN WORDS {[(k, BAD_GERMAN_COUNTS[k]) for k in sorted(BAD_GERMAN_COUNTS, key=BAD_GERMAN_COUNTS.get, reverse=True) if k.islower()][:13]}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL ENGLISH WORDS CHECKED = {TOTAL_ENGLISH_WORDS_CHECKED_COUNT:,} BAD_ENGLISH WORDS {len(BAD_ENGLISH_WORD_LIST):,} {len(BAD_ENGLISH_WORD_LIST)*100/TOTAL_ENGLISH_WORDS_CHECKED_COUNT:.2f}% ({len(BAD_ENGLISH_WORD_SET):,} unique){f': {BAD_ENGLISH_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    TOTAL BAD ENGLISH WORDS = {TOTAL_ENGLISH_MISSPELLING_COUNT:,} WORST ENGLISH WORDS {[(k, BAD_ENGLISH_COUNTS[k]) for k in sorted(BAD_ENGLISH_COUNTS, key=BAD_ENGLISH_COUNTS.get, reverse=True) if k.islower()][:14]}\n" )

    # for versionAbbreviation in ('OET-RV',): # Just out of curiousity # ,'OET-LV', 'ULT','UST'
    #     print( f"\n{versionAbbreviation} [Using {state.BibleLanguages[versionAbbreviation]} dictionary] ({len(MISPELLING_VERSION_REF_DICT[versionAbbreviation]):,}) {MISPELLING_VERSION_REF_DICT[versionAbbreviation]}\n")

    for versionAbbreviation in ('OET-RV','OET-LV', 'KJB-1611', 'Wycl'): # Just out of curiousity # 'ULT','UST', 'BSB',
        badDict = defaultdict(int)
        for word,_ref in MISPELLING_VERSION_REF_DICT[versionAbbreviation]:
            badDict[word] += 1
        sortedDict = sorted( badDict.items(), key=lambda item: item[1], reverse=True )
        displayList = [wordCountTuple for wordCountTuple in sortedDict if wordCountTuple[0].islower() and (wordCountTuple[1]>(len(sortedDict)//20) or len(sortedDict)<25)]
        if len(displayList)<10 and len(displayList)<len(sortedDict): displayList += [wordCountTuple for ww,wordCountTuple in enumerate(sortedDict) if ww<10] # Could cause some duplicates
        print( f"\n{versionAbbreviation} (using {state.BibleLanguages[versionAbbreviation]} dictionary) from {len(MISPELLING_VERSION_REF_DICT[versionAbbreviation]):,} refs got {len(sortedDict):,} unique words (showing {len(displayList):,}): {displayList}\n")

    totalWordsWithRef = 0
    for versionAbbreviation in MISPELLING_VERSION_REF_DICT:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    {versionAbbreviation} misspelt words (with references) = {len(MISPELLING_VERSION_REF_DICT[versionAbbreviation]):,}" )
        totalWordsWithRef += len( MISPELLING_VERSION_REF_DICT[versionAbbreviation] )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL misspelt words (with references) = {totalWordsWithRef:,}\n" )

    ethSet = set()
    for versionAbbreviation in MISPELLING_VERSION_REF_DICT:
        if versionAbbreviation not in ('Luth','ClVg'):
            for word,_ref in MISPELLING_VERSION_REF_DICT[versionAbbreviation]:
                if word.endswith( 'eth' ) or word.endswith( 'est' ):
                    ethSet.add( word )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  ALL English -eth or -est misspelt words: ({len(ethSet):,}) {sorted(ethSet)}\n" )
# end of spellCheckEnglish.printSpellCheckSummary()

# end of spellCheckEnglish.py
