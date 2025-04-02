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
"""
from gettext import gettext as _
from pathlib import Path
import re
import os

if __name__ == '__main__':
    import sys
    sys.path.insert( 0, '../../BibleOrgSys/' )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint, fnPrint, dPrint


LAST_MODIFIED_DATE = '2025-04-02' # by RJH
SHORT_PROGRAM_NAME = "spellCheckEnglish"
PROGRAM_NAME = "English Bible Spell Check"
PROGRAM_VERSION = '0.21'
PROGRAM_NAME_VERSION = '{} v{}'.format( SHORT_PROGRAM_NAME, PROGRAM_VERSION )

DEBUGGING_THIS_MODULE = 99


TED_Dict_folderpath = Path( '../../../Documents/RobH123/TED_Dict/sourceDicts/')


# Globals
# Prepopulate the word set with our exceptions
BIBLE_WORD_SET = set(['3.0','UTF','ESFM','v0.6','Freely-Given.org',
                      'OET','WORDTABLE','LV_OT_word_table.tsv','LV_NT_word_table.tsv',
                      'b','c','d','e',
                      's1','s2','r','+','LXX','Grk',
                      'nomina','Nomina','sacra',
                      'Deutercanon','Deuterocanonicals',

                      'href="https', # Website refererences
                      '\\jmp', '_', '_\\em*about', '_\\em*all', '_\\em*caring\\em',
                      'wpmu2.azurewebsites.net', 'www.GotQuestions.org', 'www.biblicalarchaeology.org', 'www.billmounce.com', 'www.sil.org','textandcanon.org',
                      'armstronginstitute.org','bibleDifferences.net','bibleandtech.blogspot.com','bibledifferences.net','biblestudyresources','commentary.html','judas%E2%80%99','tongue%E2%80%9D', 'Yeshua%E2%80%99',
                      'mounce', 'openenglishbible', 'scrollandscreen.com', 'UASVBible.org', 'given.org', 'GitHub.com', 'GreekCNTR.org', # Websites
                      '%E2%80%9Cdivided','%E2%80%9Cjew%E2%80%9D','v=66013018'

                      'Abimelek','Abshalom','Ahimelek','Amatsyah','Ayyalon','Azaryah',
                      'Benyamin','Benyamite','Benyamites', 'Beyt',
                      'Efraim','Efron','Elifaz','Eliyyah','Esaw',
                      'Far\'oh','Finehas',
                      'Goliat',
                      'Hizkiyyah','Hofni',
                      'Isayah','Ishma\'el','Iyyov',
                      'Kayin',
                      'Lavan','Lakish','Layish',
                      'Malaki','Manashsheh',
                        'Metushalah',
                        'Mikal','Milkah','Mitspah','Mitsrayim',
                        'Mordekai','Mosheh',
                      'Natan',
                      'Potifar',
                      'Sha\'ul',
                        'Shekem','Shelomoh','Shemu\'el',
                        'Shimshon',
                        'Shomron',
                        'Shushan',
                      'Tsidon','Tsiklag','Tsiyyon',
                      'Uriyyah','Uzziyyah'
                      'Yacob',
                            'Yael',
                            'Yafet','Yafo',
                            'Yair',
                            'Yakob',
                            'Yared',
                        'Yehoshafat','Yehoshua','Yehud','Yericho','Yerushalem','Yeshayah','Yesse','Yetro',
                        'Yhn',
                        'Yishay','Yisra\'el','Yitshak',
                        'Yoav','Yohan','Yohan-the-Immerser','Yoel','Yoktan','Yonah','Yonatan','Yoppa','Yordan','Yosef','Yoshua','Yotam',
                        'Yudah','Yudas','Yude','Yudea','Yudean','Yudeans',
                      'Zekaryah','Zofar',

                      'black-grained','building-stone',
                      'efod','emerald-looking',
                      'false-teachers','finely-ground','finely-spun',
                      'house-servants',
                      'law-breaker',
                      'non',
                      'pass-over',
                      'tent-making',

                      'nlt',

                      'v2','v3','v4','v5','v6','v8','v9','v13','v14','v15','v16','v19','v26','v27',
                      'GEN','EXO','LEV','NUM','DEU','JOS','JDG','RUT','SA1','SA2','KI1','KI2','CH1','CH2','EZR','NEH',
                        'JOB','PSA','PRO','ECC','SNG','ISA','JER','LAM','EZE','DAN','HOS','JOL','AMO','OBA','JNA','MIC','NAH','HAB','ZEP','HAB','ZEC','MAL',
                      'MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','TH1','TH2','TI1','TI2','TIT',
                        'PHM','HEB','JAM','PE1','PE2','JN1','JN2','JN3','JDE','REV',
                      'Gen','Exo','Lev','Num','Deu','Chr','Rut','Psa','Prv','Hos','Zech','Mal',
                        'Mrk','Luk','Lk','Jhn','Jn','Act','Gal','Eph','Php','Col','Heb','Phm','Rev',
                    ])
BAD_ENGLISH_WORD_SET, BAD_GERMAN_WORD_SET, BAD_LATIN_WORD_SET = set(), set(), set()
BAD_ENGLISH_WORD_LIST, BAD_GERMAN_WORD_LIST, BAD_LATIN_WORD_LIST = [], [], []
TOTAL_ENGLISH_MISSPELLING_COUNT = TOTAL_GERMAN_MISSPELLING_COUNT = TOTAL_LATIN_MISSPELLING_COUNT = 0


def load_dict_sources() -> bool:
    """
    Load the words from the SIL Toolbox source files.
    """
    global BIBLE_WORD_SET
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Load English and Bible words from source dictionaries in {TED_Dict_folderpath}…" )

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
            if language != 'AME' and not mispelling:
                BIBLE_WORD_SET.add( word )
        # for line in dictSourceFile:
        #     line = line.rstrip( '\n' )
        #     if line.startswith( '\\wd '):
        #         word = line[4:]
        #         if '*' in word:
        #             word, subscript = word.split( '*', 1 )
        #             assert subscript.isdigit()
        #         BIBLE_WORD_SET.add( word )

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Loaded {len(BIBLE_WORD_SET):,} English and Bible words." )
    # print( BIBLE_WORD_LIST[:10]); halt
    return True
# end of spellCheckEnglish.load_dict_sources


USFM_CLOSED_FIELDS_TO_COMPLETELY_REMOVED = ('x','fig')
def spellCheckText( versionAbbreviation:str, ref:str, originalHTMLText:str ) -> str:
    """
    Puts a span around suspected misspelt words
    """
    location = f'{versionAbbreviation} {ref}'
    if len(BIBLE_WORD_SET) < 10_000:
        load_dict_sources()

    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Checking spelling of {versionAbbreviation} {ref} '{originalHTMLText}' …" )
    # if '0' not in ref and '-1' not in ref: halt
    checkedHTMLText = originalHTMLText

    # Remove unwanted HTML crud
    cleanedText =  ( originalHTMLText
                    .replace( '<div>', '' )
                    .replace( '<div class="bookHeader">', '' ).replace( '<!--bookHeader-->', '' )
                    .replace( '<p class="id">', '' ).replace( '<p class="mt1">', '' )
                    .replace( f'<span class="{versionAbbreviation}_verseTextChunk">', '' ).replace( f'<span class="{versionAbbreviation}_trans">', '' )
                    .replace( '<span class="add">', '' ).replace( '<span class="nd">', '' ).replace( '<span class="wj">', '' ).replace( '<span class="d">', '' )
                    .replace( '<span style="font-size:.75em;">', '' )
                    .replace( '</span>', '' ).replace( '</p>', '' ).replace( '</div>', '' )
                    )
    assert '<span' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"
    assert 'class="' not in cleanedText, f"{versionAbbreviation} {ref} {cleanedText=}"

    # Now general or punctuation clean-ups
    cleanedText =  ( cleanedText
                    .replace( '\n<br>\u2002⇔\u202f', ' ')
                    .replace( '\n', ' ' ) # Treat newlines as spaces
                    .replace( '—', ' ' ) # Treat em-dashes as spaces
                    .replace( '-', ' ' ) # Treat hyphens as spaces, i.e., split compound words (both good and bad like 'non-combatant')
                    .replace( '/', ' ' ) # Treat forward slash as spaces (sometimes used to separate alternate words like 'dew/rain')
                    .replace( '¶', '' ) # Delete pilcrow
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
    cleanedText =  ( cleanedText
                    .replace( 'LORD', '' ) # Delete ALL CAPS version
                    .replace( 'Yesus', '' ).replace( 'Yhesus', '' ).replace( 'Yhesu', '' ).replace( 'Yerusalem', '' ) # Mangled names
                        .replace( 'Yacob', '' ).replace( 'Yames', '' ).replace( 'Yohn', '' ).replace( 'Yoseph', '' ).replace( 'Yoses', '' )
                    .replace( 'you_all', '' ).replace( 'you(sg)', '' ).replace( 'your(pl)', '' ) # Fancy pronouns
                    .replace( '  ', ' ' )
                    )

    cleanedText = cleanedText.strip().replace( '  ', ' ' )
    # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    About to check spelling of '{cleanedText}' …" )
    adjWords = cleanedText.split( ' ' )

    lastLastWord = lastWord = ''
    for ww,word in enumerate( adjWords ):
        try: nextWord = adjWords[ww+1]
        except IndexError: nextWord = '' # at end

        if word in ('◙','…','…◙','◘'): continue # Untranslated or not-yet-translated verse
        if word.startswith( '###' ): continue # it's an fr or xo field
        for _x in range( 3 ):
            # We can have nested things, especially at the end of a sentence
            #   e.g., 'my¦141837 heart¦141839 in \+add the\+add* \+nd messiah¦141841\+nd*.\sig*'
            while word.startswith('‘') or word.startswith('“') \
            or word.startswith('(')  or word.startswith('['):
                word = word[1:]
            for charMarker in ('add','+add','em','+em','nd','+nd','sc','wj','+wj','bd','it','+it','bdit','tl',
                                'ior','bk','sig','sup','qs',
                                'f','ft', # We intentionally omit 'fr'
                                'x','xt'): # We intentionally omit 'xo'
                if word == f'\\{charMarker}': # These are the character fields that we use in the OET
                    word = None
                    break
                while word.endswith('.') or word.endswith(',') \
                or word.endswith('’') or word.endswith('”') \
                or word.endswith('?') or word.endswith('!') \
                or word.endswith(':') or word.endswith(';') \
                or word.endswith(')') or word.endswith(']') \
                or word.endswith('…'): 
                    word = word[:-1]
                if word.endswith( f'\\{charMarker}*' ):
                    word = word[:-len(charMarker)-2]
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
            assert number.isdigit(), f"'{word}¦{number}' from '{originalHTMLText}' @ {location}"
        # Get rid of possessives (using straight apostrophe ')
        if word.endswith("'"): word = word[:-1]
        elif word.endswith("'s"): word = word[:-2]
        if not word: continue
        if word[0].isdigit(): continue # Probably a ior or fr or xo reference
        if word.startswith( 'http' ): continue # URL
        if word not in BIBLE_WORD_SET and f'{word[0].lower()}{word[1:]}' not in BIBLE_WORD_SET:
            if versionAbbreviation not in ('Luth','ClVg'):
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f'''    {word} is suspect @ {location} with {lastLastWord=} {lastWord=} {word=} {nextWord=} from {originalHTMLText=}''' )
            if versionAbbreviation == 'Luth':
                BAD_GERMAN_WORD_SET.add( word )
                BAD_GERMAN_WORD_LIST.append( (word,location) )
                TOTAL_GERMAN_MISSPELLING_COUNT += 1
            elif versionAbbreviation == 'ClVg':
                BAD_LATIN_WORD_SET.add( word )
                BAD_LATIN_WORD_LIST.append( (word,location) )
                TOTAL_LATIN_MISSPELLING_COUNT += 1
            else: # assume it's English
                BAD_ENGLISH_WORD_SET.add( word )
                BAD_ENGLISH_WORD_LIST.append( (word,location) )
                TOTAL_ENGLISH_MISSPELLING_COUNT += 1
                if checkedHTMLText.count( word ) == 1:
                    if versionAbbreviation not in ('KJB-1611',): # We don't do this coz it messes up later addition of hilites
                        checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible misspelt word" class="spelling">{word}</span>', 1 )
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
                if versionAbbreviation not in ('KJB-1611',): # We don't do this coz it messes up later addition of hilites
                    checkedHTMLText = checkedHTMLText.replace( word, f'<span title="Possible duplicated word" class="duplicate">{word}</span>', 2 )
        lastLastWord = lastWord
        lastWord = word

    return checkedHTMLText
# end of spellCheckEnglish.spellCheckText


def printSpellCheckSummary() -> None:
    """
    Prints some summary results
    """
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL BAD_LATIN_WORDS = {TOTAL_LATIN_MISSPELLING_COUNT:,}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  BAD_LATIN_WORDS ({len(BAD_LATIN_WORD_LIST):,}) ({len(BAD_LATIN_WORD_SET):,} unique){f': {BAD_LATIN_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL BAD_GERMAN_WORDS = {TOTAL_GERMAN_MISSPELLING_COUNT:,}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  BAD_GERMAN_WORDS ({len(BAD_GERMAN_WORD_LIST):,}) ({len(BAD_GERMAN_WORD_SET):,} unique){f': {BAD_GERMAN_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  TOTAL BAD_ENGLISH_WORDS = {TOTAL_ENGLISH_MISSPELLING_COUNT:,}" )
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  BAD_ENGLISH_WORDS ({len(BAD_ENGLISH_WORD_LIST):,}) ({len(BAD_ENGLISH_WORD_SET):,} unique){f': {BAD_ENGLISH_WORD_SET}' if BibleOrgSysGlobals.verbosityLevel>2 else ''}\n" )
# end of spellCheckEnglish.printSpellCheckSummary()

# end of spellCheckEnglish.py
