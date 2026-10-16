#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
#
# test_greek_hebrew.py
#
# Parity tests between the BibleOrgSys Python strip methods
# (BibleOrgSys.OriginalLanguages.Hebrew/Greek) and their Rust ports in
# openbibledata_rust. The Rust ports must be byte-identical.

import unittest

from BibleOrgSys.OriginalLanguages import Hebrew, Greek
from openbibledata_rust import (
    removeGreekAccents,
    removeHebrewCantillationMarks,
    removeHebrewVowelPointing,
    removeHebrewOtherMarks,
)

HEBREW_SAMPLES = (
    "בִּשְׁנַ֣ת שָׁל֔וֹשׁ לְמַלְכ֖וּת יְהוֹיָקִ֣ים מֶֽלֶךְ־יְהוּדָ֑ה",
    "וַיֹּ֣אמֶר הַמֶּ֔לֶךְ לְאַשְׁפְּנַ֖ז רַ֣ב סָרִיסָ֑יו",
    "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
    "מֶֽלֶךְ־יְהוּדָה",
    "שְׁנַ֣ת, לְאֶרֶץ־יִשְׂרָאֵ֑ל",
    "",
)

GREEK_SAMPLES = (
    "Ἀρχὴ τοῦ εὐαγγελίου ˚Ἰησοῦ ˚Χριστοῦ, Υἱοῦ ˚Θεοῦ.",
    "Καθὼς γέγραπται ἐν τῷ Ἠσαΐᾳ τῷ προφήτῃ: “Ἰδοὺ, ἀποστέλλω τὸν ἄγγελόν μου.”",
    "λόγος",
    "Ἐγένετο Ἰωάννης, ὁ βαπτίζων ἐν τῇ ἐρήμῳ",
    "",
)


class TestHebrewRustParity(unittest.TestCase):
    def test_removeVowelPointing(self):
        h = Hebrew.Hebrew('')
        for text in HEBREW_SAMPLES:
            for flag in (False, True):
                py = h.removeVowelPointing(text, flag)
                rs = removeHebrewVowelPointing(text, removeMetegOrSiluq=flag)
                self.assertEqual(py, rs, f"removeVowelPointing({text!r}, {flag})")

    def test_removeCantillationMarks(self):
        h = Hebrew.Hebrew('')
        for text in HEBREW_SAMPLES:
            for flag in (False, True):
                py = h.removeCantillationMarks(text, flag)
                rs = removeHebrewCantillationMarks(text, removeMetegOrSiluq=flag)
                self.assertEqual(py, rs, f"removeCantillationMarks({text!r}, {flag})")

    def test_removeOtherMarks(self):
        h = Hebrew.Hebrew('')
        for text in HEBREW_SAMPLES:
            for remove_dots in (True, False):
                py = h.removeOtherMarks(text, removeSinShinDots=remove_dots)
                rs = removeHebrewOtherMarks(text, removeSinShinDots=remove_dots)
                self.assertEqual(py, rs, f"removeOtherMarks({text!r}, removeSinShinDots={remove_dots})")


class TestGreekRustParity(unittest.TestCase):
    def test_removeAccents(self):
        g = Greek.Greek('')
        for text in GREEK_SAMPLES:
            py = g.removeAccents(text)
            rs = removeGreekAccents(text)
            self.assertEqual(py, rs, f"removeAccents({text!r})")


if __name__ == '__main__':
    unittest.main()
