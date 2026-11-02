#!/usr/bin/env -S uv run
# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+OBD@gmail.com>
# SPDX-License-Identifier: CC0-1.0
"""Check generated resource licence destinations.

CHANGELOG:
    2026-11-01 Cover dictionary details with and without the TTN resource.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from BibleOrgSys import BibleOrgSysGlobals
import createSitePages as pages
from settings import State


class DetailsLinkTests(unittest.TestCase):
    def test_dictionary_details_exist_independently_of_ttn(self):
        for preloaded in ({}, {'TTN': {}}):
            with self.subTest(preloaded=preloaded), TemporaryDirectory() as folder:
                state = State()
                state.preloadedBibles = preloaded
                state.BibleLocations = {}
                with patch.object(pages, 'makeTop', return_value='<html><body>'), \
                     patch.object(pages, 'makeBottom', return_value='</body></html>'), \
                     patch.object(pages, 'checkHtml', return_value=True), \
                     patch.object(BibleOrgSysGlobals, 'verbosityLevel', 0):
                    pages._createDetailsPages(0, Path(folder), state)
                self.assertTrue((Path(folder)/'TOBD/details.htm').is_file())
                self.assertEqual((Path(folder)/'AllDetails.htm').read_text().count('id="TOBD"'), 1)


if __name__ == '__main__':
    unittest.main()
