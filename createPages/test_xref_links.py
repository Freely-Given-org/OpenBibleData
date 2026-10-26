#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0

"""Regression tests for abbreviated cross-references in the shared Rust linker.

CHANGELOG:
    2026-10-23 Cover KJB-1611 chapter/verse context across page families.
"""

import re
from types import SimpleNamespace
import unittest

from openbibledata_rust import (convertVerseEntryListToHtml,
                                process_cross_references, process_footnotes)


# Keep the original source spelling/punctuation: these are transcription fixtures.
REPORTED_REFS = (
    ('EZR', '3', '10', '1.Chro. 6.31. and cha. 16.7. and 25.1.',
     ('CH1_C6.htm#C6V31', 'CH1_C16.htm#C16V7', 'CH1_C25.htm#C25V1')),
    ('PSA', '25', '4', 'Psa.27.11. & 86.11. & 119.',
     ('PSA_C27.htm#C27V11', 'PSA_C86.htm#C86V11', 'PSA_C119.htm#C119V1')),
    ('PSA', '27', '11', 'Psal. 25.4 and 86.11 and 119.',
     ('PSA_C25.htm#C25V4', 'PSA_C86.htm#C86V11', 'PSA_C119.htm#C119V1')),
    ('PRO', '28', '12', 'Iohn 11.10. eccles. 10.6 and ver. 28.',
     ('JHN_C11.htm#C11V10', 'ECC_C10.htm#C10V6', 'PRO_C28.htm#C28V28')),
    ('PRO', '28', '28', 'Chap. 29.2. and ver. 12. of this chapter.',
     ('PRO_C29.htm#C29V2', 'PRO_C28.htm#C28V12')),
)


def targets(html, field='cross '):
    return re.findall(rf'<a title="View {field}reference" href="([^"]+)">', html)


class TestXrefLinks(unittest.TestCase):
    def test_reported_references_in_each_view(self):
        for bbb, c, v, text, expected in REPORTED_REFS:
            for segment, prefix in (
                ('chapter', ''), ('book', '../byC/'), ('section', '../byC/'),
                ('parallelVerse', '../../OET/byC/'),
                ('interlinearVerse', '../../OET/byC/'),
                ('topicalPassage', '../OET/byC/'),
            ):
                with self.subTest(ref=(bbb, c, v), segment=segment):
                    ref = (bbb,) if segment == 'book' else (bbb, c, v)
                    note = f'\\x + \\xo {c}:{v} \\xt {text}\\x*'
                    entries = [SimpleNamespace(marker=m, full_text=t, clean_text='')
                               for m, t in (('v', v), ('v~', f'Text {note}'), ('¬v', v))]
                    html = convertVerseEntryListToHtml(
                        2, 'KJB-1611', ref, segment, ['chapters', 'c'], entries)
                    self.assertEqual(targets(html), [prefix + t for t in expected])
                    # Only add anchors; do not rewrite the historical wording.
                    xr_text = html.split('<span class="xrText">', 1)[1].split('</span>', 1)[0]
                    self.assertEqual(re.sub(r'</?a\b[^>]*>', '', xr_text), text)

    def test_footnote_xt_uses_the_same_rules(self):
        for bbb, c, v, text, expected in REPORTED_REFS:
            with self.subTest(ref=(bbb, c, v)):
                _, footnotes = process_footnotes(
                    f'Text \\f + \\fr {c}:{v} \\xt {text}\\f*',
                    'KJB-1611', bbb, None, 'book', '../byC/', 11500)
                self.assertEqual(targets(footnotes, ''), ['../byC/' + t for t in expected])

    def test_related_shorthand_keeps_its_book_and_chapter(self):
        cases = (
            ('CH2', '35:4', '1.Chron. 9.10. and chap. 23.24,25, and 26.',
             ('CH1_C9.htm#C9V10', 'CH1_C23.htm#C23V24',
              'CH1_C23.htm#C23V25', 'CH1_C23.htm#C23V26')),
            ('EZE', '44:30', 'Exod. 13.2. and 22.29. and ver. 30. numb.3.13. and 18.12.',
             ('EXO_C13.htm#C13V2', 'EXO_C22.htm#C22V29', 'EXO_C22.htm#C22V30',
              'NUM_C3.htm#C3V13', 'NUM_C18.htm#C18V12')),
            ('PRO', '19:13', 'Chap. 10.1. & 15.20. and 17.21. & 25. and chap. 21.9.',
             ('PRO_C10.htm#C10V1', 'PRO_C15.htm#C15V20', 'PRO_C17.htm#C17V21',
              'PRO_C17.htm#C17V25', 'PRO_C21.htm#C21V9')),
            ('ECC', '7:19', 'Prou. 21.22. and 24.5. cha. 9.16.',
             ('PRO_C21.htm#C21V22', 'PRO_C24.htm#C24V5', 'ECC_C9.htm#C9V16')),
            ('PRO', '16:1', 'Vers.9. and chap. 19.21. and 20.24. ier. 10.23.',
             ('PRO_C16.htm#C16V9', 'PRO_C19.htm#C19V21', 'PRO_C20.htm#C20V24', 'JER_C10.htm#C10V23')),
        )
        for bbb, origin, text, expected in cases:
            with self.subTest(origin=origin, text=text):
                _, refs = process_cross_references(
                    f'\\x + \\xo {origin} \\xt {text}\\x*',
                    'KJB-1611', bbb, None, 'book', '')
                self.assertEqual(targets(refs), list(expected))

    def test_general_lists_and_single_chapter_books(self):
        for version in ('KJB-1611', 'NET', 'RV'):
            for text, expected in (
                ('Exod 17:2,7, 8 and 9 & 10', ('EXO_C17.htm#C17V2', 'EXO_C17.htm#C17V7',
                    'EXO_C17.htm#C17V8', 'EXO_C17.htm#C17V9', 'EXO_C17.htm#C17V10')),
                ('Psal 119:105 and 119', ('PSA_C119.htm#C119V105', 'PSA_C119.htm#C119V119')),
                ('Jude 5 and 7', ('JDE_C1.htm#C1V5', 'JDE_C1.htm#C1V7')),
                ('Gen 1 and 2', ('GEN_C1.htm#C1V1', 'GEN_C2.htm#C2V1')),
            ):
                with self.subTest(version=version, text=text):
                    _, refs = process_cross_references(
                        f'\\x + \\xo 1:1 \\xt {text}\\x*', version, 'GEN', '1', 'chapter', '')
                    self.assertEqual(targets(refs), list(expected))

    def test_origin_chapter_is_not_the_first_chapter_of_a_section(self):
        _, refs = process_cross_references(
            r'\x + \xo 28:28 \xt Verse 12.\x*', 'KJB-1611', 'PRO', '27', 'section', '')
        self.assertEqual(targets(refs), ['PRO_C28.htm#C28V12'])

    def test_list_does_not_consume_the_number_of_the_next_book(self):
        _, refs = process_cross_references(
            r'\x + \xo 22:20 \xt Deut. 13.13,14,15. 1.Mac. 2.24.\x*',
            'KJB-1611', 'EXO', '22', 'chapter', '')
        self.assertEqual(targets(refs), ['DEU_C13.htm#C13V13', 'DEU_C13.htm#C13V14',
                                       'DEU_C13.htm#C13V15', 'MA1_C2.htm#C2V24'])

    def test_historical_continuation_with_a_missing_chapter_verse_dot(self):
        for text, expected in (
            ('Psal.86.15. and 103 8,9.',
             ('PSA_C86.htm#C86V15', 'PSA_C103.htm#C103V8', 'PSA_C103.htm#C103V9')),
            ('Psal.42.11. and 79.10. and 115 2.',
             ('PSA_C42.htm#C42V11', 'PSA_C79.htm#C79V10', 'PSA_C115.htm#C115V2')),
        ):
            with self.subTest(text=text):
                _, refs = process_cross_references(
                    f'\\x + \\xo 1:1 \\xt {text}\\x*', 'KJB-1611', 'GEN', '1', 'chapter', '')
                self.assertEqual(targets(refs), list(expected))

    def test_invalid_chapter_does_not_replace_the_previous_target(self):
        _, refs = process_cross_references(
            r'\x + \xo 1:1 \xt Gen 2:3; Exod 99:1; 4:5.\x*',
            'NET', 'PRO', '1', 'chapter', '')
        self.assertEqual(targets(refs), ['GEN_C2.htm#C2V3', 'GEN_C4.htm#C4V5'])

    def test_unresolved_source_numbers_stay_visible_without_dead_links(self):
        for bbb, origin, text, expected in (
            ('SA1', '7:3', 'Iosh. 14.15,23.', ('JOS_C14.htm#C14V15',)),
            ('PSA', '43:5', 'Psal. 42.6. and 12.', ('PSA_C42.htm#C42V6',)),
            ('JER', '4:6', 'Chap. 1.13, 14, 23. chap. 6.26.',
             ('JER_C1.htm#C1V13', 'JER_C1.htm#C1V14', 'JER_C6.htm#C6V26')),
        ):
            with self.subTest(ref=(bbb, origin)):
                _, refs = process_cross_references(
                    f'\\x + \\xo {origin} \\xt {text}\\x*', 'KJB-1611', bbb, None, 'book', '')
                self.assertEqual(targets(refs), list(expected))
                xr_text = refs.split('<span class="xrText">', 1)[1].split('</span>', 1)[0]
                self.assertEqual(re.sub(r'</?a\b[^>]*>', '', xr_text), text)


if __name__ == '__main__':
    unittest.main()
