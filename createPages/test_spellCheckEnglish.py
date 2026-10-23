#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for translated Luther and Vulgate vocabulary.

CHANGELOG:
    2026-10-23 Check combined OET formatting titles through the spelling pipeline
    2026-10-21 Check full optional -ies plurals without hiding misspellings
    2026-10-20 Check residual translations and separate spelling totals from repetition warnings
    2026-10-20 Distinguish accidental repeated words from punctuated speech and glosses
    2026-10-18 Check modernised ordinary vocabulary without hiding damaged spellings
    2026-10-17 Check part-of-speech labels and Jubilee in both modernised-English page paths
    2026-10-17 Check reviewed names without accepting untranslated or damaged words
"""
from types import SimpleNamespace
from collections import defaultdict
from pathlib import Path
import ast
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import spellCheckEnglish as spelling
from BibleOrgSys.Reference.OldBiblicalEnglish import moderniseEnglishWords
from BibleOrgSys.Reference.LutherGermanToEnglish import translateGerman
from BibleOrgSys.Reference.VulgateLatinToEnglish import translateLatin


class TestTranslatedVocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_verbosity = BibleOrgSysGlobals.verbosityLevel
        BibleOrgSysGlobals.verbosityLevel = 0
        spelling.load_dict_sources()
        cls.state = SimpleNamespace(BibleLanguages={'Luth': 'GER', 'ClVg': 'LAT', 'Wycl': 'EN-UK', 'OET-RV': 'EN-UK', 'OET-LV': 'EN-UK'})

    @classmethod
    def tearDownClass(cls):
        BibleOrgSysGlobals.verbosityLevel = cls.old_verbosity

    def check_text(self, version, text):
        source = f'<span class="{version}_trans">{text}</span>'
        return spelling.spellCheckAndMarkHTMLText(version, 'MAT_1:1', source, source, self.state)

    def test_combined_oet_titles_do_not_enter_spelling_text(self):
        from html import do_OET_RV_HTMLcustomisations, do_OET_LV_HTMLcustomisations
        for version, customise, marker in (
            ('OET-RV', do_OET_RV_HTMLcustomisations, '≈'),
            ('OET-LV', do_OET_LV_HTMLcustomisations, '='),
        ):
            with self.subTest(version=version):
                source = ('<span class="add">' + marker
                          + '<a title="λόγος (logos)" href="../ref/GrkWrd/test.htm">word</a></span>')
                formatted = customise('test', source)
                self.assertEqual(self.check_text(version, formatted),
                                 f'<span class="{version}_trans">{formatted}</span>')

    def assert_repetitions(self, version, text, expected):
        reports = {'Luth': spelling.BAD_GERMAN_WORD_LIST,
                   'ClVg': spelling.BAD_LATIN_WORD_LIST,
                   'Wycl': spelling.BAD_ENGLISH_WORD_LIST,
                   'OET-RV': spelling.BAD_ENGLISH_WORD_LIST}[version]
        start = len(reports)
        result = self.check_text(version, text)
        pairs = [word for word, _ in reports[start:] if ' ' in word]
        self.assertEqual(pairs, expected)
        return result

    def test_punctuated_repetitions_are_not_accidental_duplicates(self):
        for version in ('Wycl', 'Luth', 'ClVg', 'OET-RV'):
            for text in ('Lord, Lord', 'Master, Master', 'holy, holy, holy',
                         'No! No!', 'go. go', 'go: go', 'go; go',
                         'go—go', 'go … go', 'go / go', 'love(n)/love(v)',
                         'go-go', 'in in-laws', 'God God’s people',
                         'God God\'s people', 'go “go”',
                         'Lord, <i>Lord</i>', 'had had', 'that that'):
                with self.subTest(version=version, text=text):
                    self.assertNotIn('class="duplicate"',
                                     self.assert_repetitions(version, text, []))

    def test_unpunctuated_repetitions_still_report_and_mark(self):
        for version in ('Wycl', 'Luth', 'ClVg', 'OET-RV'):
            for text in ('went into into the wilderness',
                         'went into  into the wilderness',
                         'went into&nbsp;into the wilderness',
                         'went into <i>into</i> the wilderness',
                         '“into into,”', 'into into.'):
                with self.subTest(version=version, text=text):
                    result = self.assert_repetitions(version, text, ['into into'])
                    self.assertEqual(result.count('class="duplicate"'), 2)

    def test_repetition_counts_keep_each_actual_occurrence(self):
        self.assert_repetitions('Wycl', 'go go go', ['go go', 'go go'])
        self.assert_repetitions('Wycl', 'Lord, Lord; go go.', ['go go'])
        self.assert_repetitions('Wycl', 'go, go; go go.', ['go go'])
        self.assert_repetitions('Wycl', 'go <i>far</i> go', [])

    def test_marked_ies_plurals_use_full_plural_dictionary_forms(self):
        for ending in ('(es)', '[es]'):
            for stem in ('furi', 'loyalti', 'sanctuari', 'prosperiti', 'antiquiti'):
                for capitalised in (False, True):
                    word = (stem.capitalize() if capitalised else stem) + ending
                    with self.subTest(word=word):
                        source = f'<span class="OET-LV_trans">{word}</span>'
                        before = len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'])
                        self.assertEqual(self.check_text('OET-LV', word), source)
                        self.assertEqual(len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV']), before)

    def test_marked_ies_plurals_check_the_plural_not_the_singular(self):
        for ending in ('(es)', '[es]'):
            for stem, singular, plural in (('furi', 'fury', 'furies'),
                                           ('loyalti', 'loyalty', 'loyalties')):
                word = stem + ending
                with self.subTest(word=word):
                    with patch.object(spelling, 'BRITISH_WORD_SET', {plural}):
                        before = len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'])
                        self.assertNotIn('class="spelling"', self.check_text('OET-LV', word))
                        self.assertEqual(len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV']), before)
                    with patch.object(spelling, 'BRITISH_WORD_SET', {singular}):
                        self.assertIn(f'class="spelling">{stem}</span>', self.check_text('OET-LV', word))

    def test_marked_plurals_preserve_existing_separators_and_endings(self):
        for text in ('the_furi(es)_of your foes', 'covenant-loyalti(es)',
                     '“sanctuari(es),” prosperiti[es].', "loyalti(es)'s",
                     'word(s) box(es) word[s] box[es]'):
            with self.subTest(text=text):
                source = f'<span class="OET-LV_trans">{text}</span>'
                before = len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'])
                self.assertEqual(self.check_text('OET-LV', text), source)
                self.assertEqual(len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV']), before)

    def test_marked_plurals_do_not_hide_misspellings(self):
        for word, stem in (('fuurri(es)', 'fuurri'), ('loyallti[es]', 'loyallti'),
                           ('furi', 'furi'), ('loyalti', 'loyalti')):
            with self.subTest(word=word):
                before = len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'])
                checked = self.check_text('OET-LV', word)
                self.assertIn(f'class="spelling">{stem}</span>', checked)
                self.assertEqual(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'][before:],
                                 [(stem, 'MAT_1:1')])
        before = len(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'])
        self.check_text('OET-LV', 'furi furi(es)')
        self.assertEqual(spelling.MISPELLING_VERSION_REF_DICT['OET-LV'][before:],
                         [('furi', 'MAT_1:1')])

    def test_luther_title_and_region(self):
        self.assertNotIn('class="spelling"', self.check_text('Luth', 'Tsevaot Syrophoenicia'))

    def test_reported_residual_translations_pass_spelling(self):
        for version, translator, text in (
                ('Luth', translateGerman, 'Schalksauge, beging'),
                ('ClVg', translateLatin, 'vigilares, nive, institue, pisciculis; '
                 'hirco ohgr, id est, emissario')):
            with self.subTest(version=version):
                source = f'<span class="{version}_trans">{text}</span>'
                translated = translator(source)
                checked = spelling.spellCheckAndMarkHTMLText(version, 'MAT_1:1', translated, source, self.state)
                self.assertNotIn('class="spelling"', checked)

    def test_vulgate_commentator_names_and_terms(self):
        self.assertNotIn('class="spelling"', self.check_text(
            'ClVg', 'Cassiodorus Origen Yeduthun Yeconiah catechumens schismatics tetrarchies'))

    def test_untranslated_and_damaged_words_remain_flagged(self):
        for version, word in (('Luth', 'vipersgezüchte'), ('ClVg', 'aquas'), ('ClVg', 'authortate')):
            with self.subTest(version=version, word=word):
                self.assertIn(f'class="spelling">{word}</span>', self.check_text(version, word))

    def test_parts_of_speech_do_not_become_spelling_warnings(self):
        for version in ('Luth', 'ClVg', 'Wycl'):
            with self.subTest(version=version):
                self.assertNotIn('class="spelling"', self.check_text(
                    version, 'love(n), love(v); fair(aj). sound(n) light(aj) watch(v)'))

    def test_reviewed_english_dictionary_omissions(self):
        self.assertNotIn('class="spelling"', self.check_text(
            'Wycl', 'suretyship Suretyship whoremongers Whoremongers'))
        for word in ('suretyshipp', 'whoremongerrs', 'wy?dome'):
            with self.subTest(word=word):
                self.assertIn('class="spelling"', self.check_text('Wycl', word))

    def test_jubilee_survives_the_page_name_pronunciation_step(self):
        # Evaluate the actual small postprocessing expression from each page builder,
        # without loading the Bible resources required by the full site generator.
        for filename in ('createParallelVersePages.py', 'createVerseListPages.py'):
            with self.subTest(filename=filename):
                tree = ast.parse(Path(__file__).with_name(filename).read_text())
                expressions = [node.value for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'modernisedTextHtml'
                            for target in node.targets)
                    and "'YDG'" in ast.unparse(node.value)]
                self.assertEqual(len(expressions), 1)
                namespace = {'modernisedTextHtml': moderniseEnglishWords(
                    '<span>Iubile and Iubilee, Ioseph and Yonas</span>', allowOptions=True)}
                actual = eval(compile(ast.Expression(expressions[0]), filename, 'eval'), namespace)
                self.assertEqual(actual, '<span>Jubilee and Jubilee, Yoseph and Yonas</span>')


class TestSpellCheckSummary(unittest.TestCase):
    def summary(self, english_checked=100, german_checked=100538, latin_checked=324037):
        replacements = {'MISPELLING_VERSION_REF_DICT': defaultdict(list)}
        for language, checked, counts, repetitions, unique_pairs in (
                ('ENGLISH', english_checked, {'speling': 1}, 4, 2),
                ('GERMAN', german_checked, {'mischievious': 1, 'beging': 1}, 45, 8),
                ('LATIN', latin_checked, dict.fromkeys(('ohgr','watchs','nive','institue','fishs'), 1), 35, 23)):
            if not checked:
                counts, repetitions, unique_pairs = {}, 0, 0
            reports = [(word, 'MAT_1:1') for word, count in counts.items() for _ in range(count)]
            reports += [(f'word{i % unique_pairs} word{i % unique_pairs}', 'MAT_1:1') for i in range(repetitions)]
            replacements.update({
                f'TOTAL_{language}_WORDS_CHECKED_COUNT': checked,
                f'TOTAL_{language}_MISSPELLING_COUNT': sum(counts.values()),
                f'BAD_{language}_COUNTS': counts,
                f'BAD_{language}_WORD_LIST': reports,
                f'BAD_{language}_WORD_SET': {word for word, _ in reports}})
        state = SimpleNamespace(BibleLanguages=dict.fromkeys(('OET-RV','OET-LV','KJB-1611','Wycl'), 'EN-UK'))
        with patch.multiple(spelling, **replacements), \
                patch.object(BibleOrgSysGlobals, 'verbosityLevel', 3), \
                patch.object(spelling, 'vPrint') as output:
            spelling.printSpellCheckSummary(state)
        return '\n'.join(call.args[2] for call in output.call_args_list)

    def test_spelling_and_repetition_counts_are_separate(self):
        output = self.summary()
        self.assertIn('TOTAL ENGLISH WORDS CHECKED = 100 BAD_ENGLISH WORDS 1 = 1.00% (1 unique)', output)
        self.assertIn('POSSIBLE REPEATED ENGLISH WORDS = 4 (2 unique pairs)', output)
        self.assertIn('TOTAL GERMAN WORDS CHECKED = 100,538 BAD_GERMAN WORDS 2 = <0.01% (2 unique)', output)
        self.assertIn('TOTAL BAD GERMAN WORDS = 2 ', output)
        self.assertIn('POSSIBLE REPEATED GERMAN WORDS = 45 (8 unique pairs)', output)
        self.assertIn('TOTAL LATIN WORDS CHECKED = 324,037 BAD_LATIN WORDS 5 = <0.01% (5 unique)', output)
        self.assertIn('TOTAL BAD LATIN WORDS = 5 ', output)
        self.assertIn('POSSIBLE REPEATED LATIN WORDS = 35 (23 unique pairs)', output)
        spelling_lines = [line for line in output.splitlines() if 'WORDS CHECKED' in line]
        self.assertTrue(all('word0 word0' not in line for line in spelling_lines))

    def test_empty_results_do_not_divide_by_zero(self):
        output = self.summary(english_checked=0, german_checked=0, latin_checked=0)
        self.assertNotIn('BAD_ENGLISH WORDS', output)
        self.assertNotIn('BAD_GERMAN WORDS', output)
        self.assertNotIn('BAD_LATIN WORDS', output)


if __name__ == '__main__':
    unittest.main()
