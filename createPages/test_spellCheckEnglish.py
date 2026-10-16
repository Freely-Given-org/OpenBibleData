#!/usr/bin/env -S uv run
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for translated Luther and Vulgate vocabulary.

CHANGELOG:
    2026-10-17 Check reviewed names without accepting untranslated or damaged words
"""
from types import SimpleNamespace
import unittest

from BibleOrgSys import BibleOrgSysGlobals
import spellCheckEnglish as spelling


class TestTranslatedVocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_verbosity = BibleOrgSysGlobals.verbosityLevel
        BibleOrgSysGlobals.verbosityLevel = 0
        spelling.load_dict_sources()
        cls.state = SimpleNamespace(BibleLanguages={'Luth': 'GER', 'ClVg': 'LAT'})

    @classmethod
    def tearDownClass(cls):
        BibleOrgSysGlobals.verbosityLevel = cls.old_verbosity

    def check_text(self, version, text):
        source = f'<span class="{version}_trans">{text}</span>'
        return spelling.spellCheckAndMarkHTMLText(version, 'MAT_1:1', source, source, self.state)

    def test_luther_title_and_region(self):
        self.assertNotIn('class="spelling"', self.check_text('Luth', 'Tsevaot Syrophoenicia'))

    def test_vulgate_commentator_names_and_terms(self):
        self.assertNotIn('class="spelling"', self.check_text(
            'ClVg', 'Cassiodorus Origen Yeduthun Yeconiah catechumens schismatics tetrarchies'))

    def test_untranslated_and_damaged_words_remain_flagged(self):
        for version, word in (('Luth', 'vipersgezüchte'), ('ClVg', 'aquas'), ('ClVg', 'authortate')):
            with self.subTest(version=version, word=word):
                self.assertIn(f'class="spelling">{word}</span>', self.check_text(version, word))


if __name__ == '__main__':
    unittest.main()
