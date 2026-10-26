#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Shared keys for the grammatical backgrounds used in Bible and reference pages.

CHANGELOG:
    2026-10-23 Share the parallel-verse colour keys with word and lemma pages.
"""

GREEK_CASE_CLASS_KEY_DICT = {
    'grkVrb': '<span class="grkVrb">khaki</span>:verbs',
    'grkNom': '<span class="grkNom">light-green</span>:nominative/subject',
    'grkAcc': '<span class="grkAcc">orange</span>:accusative/object',
    'grkGen': '<span class="grkGen">pink</span>:genitive/possessor',
    'grkDat': '<span class="grkDat">cyan</span>:dative/indirect object',
    'grkVoc': '<span class="grkVoc">magenta</span>:vocative',
    'grkNeg': '<span class="grkNeg">red</span>:negative',
}
HEBREW_CASE_CLASS_KEY_DICT = {
    'hebVrb': '<span class="hebVrb">khaki</span>:verbs',
    'hebNeg': '<span class="hebNeg">red</span>:negative',
    'hebEl': '<span class="hebEl">blue</span>:Elohim',
    'hebYhwh': '<span class="hebYhwh">green</span>:YHWH',
}
